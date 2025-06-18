import logging
import json
import asyncio
from typing import Callable
from fastapi import Request, Response
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import P2ImMessageReceiveV1
import lark_oapi as lark

from app.services.feishu import FeishuClient
from app.bitable import BitableClient, TaskStatus
from app.config import Settings
from app.services.match import match_service

logger = logging.getLogger(__name__)

def create_event_handler(feishu_client: FeishuClient, bitable_client: BitableClient, settings: Settings) -> EventDispatcherHandler:
    """
    创建并配置事件处理器，适配 lark-oapi v1.4.18。
    """
    def handle_message_receive(data: P2ImMessageReceiveV1):
        """
        这是传递给 SDK 的同步回调函数。
        """
        async def _handle_async(event_data: P2ImMessageReceiveV1):
            """
            这里是真正的异步业务逻辑。
            """
            content = json.loads(event_data.event.message.content)
            # 实际的业务逻辑...
            logger.info(f"成功处理消息事件, message_id: {event_data.event.message.message_id}")

        # 在当前事件循环中创建一个任务来执行异步处理函数
        asyncio.create_task(_handle_async(data))


    handler = EventDispatcherHandler.builder(
        settings.feishu.encrypt_key,
        settings.feishu.verification_token,
        lark.LogLevel.DEBUG
    ).register_p2_im_message_receive_v1(handle_message_receive).build()

    return handler

async def handle_feishu_event(request: Request, dispatcher: EventDispatcherHandler):
    """
    处理飞书事件回调的 FastAPI 端点。
    手动处理请求、验证和分发。
    """
    resp = await dispatcher.dispatch(
        headers=dict(request.headers), 
        body=await request.body()
    )

    return Response(content=resp.body, status_code=resp.status_code, media_type="application/json")

async def handle_github_webhook(request: Request):
    return Response(status_code=200) 