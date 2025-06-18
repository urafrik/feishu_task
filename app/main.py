from fastapi import FastAPI, Request, Response, Header, Depends
from contextlib import asynccontextmanager
import logging
import hashlib

from lark_oapi.core.model import RawRequest

from app.config import settings
from app.services.feishu import feishu_client
from app.bitable import BitableClient, TaskStatus
from app.handlers import create_event_handler
from app.services.scheduler import scheduler, check_inactive_tasks
from app.services.ci import ci_service, CIService, CIState
from starlette.responses import PlainTextResponse

# 初始化应用
app = FastAPI(title=settings.app.name, version=settings.app.version)

# 在应用主模块中统一创建和管理服务实例
bitable_client = BitableClient(settings, feishu_client)
event_handler = create_event_handler(feishu_client, bitable_client, settings)

# 配置日志
logging.basicConfig(level=settings.logging.level.upper())
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时，将服务实例作为参数传递给定时任务
    scheduler.add_job(
        check_inactive_tasks,
        'interval',
        hours=1,
        args=[feishu_client, bitable_client]
    )
    scheduler.start()
    logger.info("Scheduler started.")
    yield
    scheduler.shutdown()
    logger.info("Scheduler shut down.")

app.router.lifespan_context = lifespan

@app.post("/feishu/event")
async def feishu_event(request: Request):
    """飞书事件回调处理"""
    headers = dict(request.headers)
    body = await request.body()

    # 1. 检查这是否是飞书为了验证URL有效性而发送的 challenge 请求
    if b'"type":"url_verification"' in body:
        # 如果是，直接构建 RawRequest 交给 SDK 处理即可
        raw_req = RawRequest()
        raw_req.headers = headers
        raw_req.body = body
        resp = event_handler.do(raw_req)
        return Response(content=resp.content, status_code=resp.status_code, headers=resp.headers)

    # 2. 对所有非 challenge 的真实事件，执行我们手动编写的签名校验
    timestamp = headers.get("x-lark-request-timestamp")
    nonce = headers.get("x-lark-request-nonce")
    received_signature = headers.get("x-lark-signature")
    
    if not all([timestamp, nonce, received_signature]):
        return Response(content="Missing signature headers", status_code=403)

    encrypt_key = settings.feishu.encrypt_key
    safe_encrypt_key = encrypt_key or ""
    signature_string = timestamp.encode('utf-8') + nonce.encode('utf-8') + safe_encrypt_key.encode('utf-8') + body
    calculated_signature = hashlib.sha1(signature_string).hexdigest()

    if received_signature != calculated_signature:
        return Response(content="Signature verification failed", status_code=403)

    # 3. 验证通过后，构建 RawRequest 并猴子补丁 SDK 的验证方法
    raw_req = RawRequest()
    raw_req.uri = str(request.url)
    raw_req.body = body
    
    # 复制 header，并确保 SDK 需要的大写键存在
    final_headers = headers.copy()
    final_headers["X-Lark-Request-Timestamp"] = timestamp
    final_headers["X-Lark-Request-Nonce"] = nonce
    final_headers["X-Lark-Signature"] = received_signature
    raw_req.headers = final_headers
    
    # 猴子补丁：用一个空操作替换掉 SDK 有问题的验证方法
    original_verify = event_handler._verify_sign
    event_handler._verify_sign = lambda req: None
    
    # 3. 调用 SDK 处理事件
    try:
        resp = event_handler.do(raw_req)
    finally:
        # 恢复原始方法，避免影响后续请求
        event_handler._verify_sign = original_verify

    return Response(content=resp.content, status_code=resp.status_code, headers=resp.headers)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Git/CI Webhook (如果启用)
if settings.ci.enabled:
    # 初始化CI服务，设置密钥
    ci_service.set_github_secret(settings.ci.webhook_secret)

    @app.post("/webhook/ci", tags=["Webhooks"])
    async def github_webhook_endpoint(
        request: Request,
        x_github_event: str = Header(...),
        x_hub_signature_256: str = Header(...)
    ):
        # 1. 验证签名
        body = await request.body()
        if not ci_service.verify_github_signature(body, x_hub_signature_256):
            return PlainTextResponse("Signature verification failed", status_code=403)

        payload = await request.json()
        
        # 2. 目前只处理 'check_suite' 事件
        if x_github_event != 'check_suite':
            return PlainTextResponse(f"Ignoring event: {x_github_event}", status_code=200)
            
        # 3. 解析CI状态
        status = ci_service.parse_github_status(payload)
        commit_info = ci_service.extract_commit_info(payload)
        commit_sha = commit_info.get("sha")

        if not commit_sha:
            return PlainTextResponse("Could not extract commit SHA", status_code=400)
        
        # 4. 根据SHA查找任务
        task = await bitable_client.get_task_by_commit(commit_sha)
        if not task:
            logger.info(f"No task found for commit SHA: {commit_sha}")
            return PlainTextResponse("No task found for commit SHA", status_code=200)

        # 5. 更新任务状态并发送通知
        record_id = task.get("record_id")
        if status == CIState.GREEN:
            await bitable_client.update_task_status(record_id, TaskStatus.CI_PASS)
            message = f"✅ CI/CD 成功: {commit_info.get('repo')} at {commit_sha[:7]}"
        elif status == CIState.RED:
            await bitable_client.update_task_status(record_id, TaskStatus.CI_FAIL)
            message = f"❌ CI/CD 失败: {commit_info.get('repo')} at {commit_sha[:7]}"
        else: # PENDING or UNKNOWN
            return PlainTextResponse("Ignoring pending or unknown status", status_code=200)

        # 在子群中发送通知
        if task.get("child_chat_id"):
            await feishu_client.send_message(task["child_chat_id"], message)

        return PlainTextResponse("Webhook processed successfully", status_code=204)
    logger.info("CI webhook endpoint enabled at /webhook/ci")
