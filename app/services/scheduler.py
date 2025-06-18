import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json

from app.bitable import BitableClient, TaskStatus
from app.services.feishu import FeishuClient


logger = logging.getLogger(__name__)

async def check_inactive_tasks(feishu_client: FeishuClient, bitable_client: BitableClient):
    """检查并提醒不活跃的任务"""
    logger.info("Running job: check_inactive_tasks")
    try:
        all_tasks = await bitable_client.get_all_tasks()
        now = datetime.now()
        
        # 筛选需要检查状态的任务
        tasks_to_check = [
            t for t in all_tasks 
            if t.get("status") in [TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value]
        ]

        for task in tasks_to_check:
            last_modified_timestamp = task.get("last_modified_time")
            if not last_modified_timestamp:
                continue

            # Bitable返回的是毫秒级时间戳
            last_modified_time = datetime.fromtimestamp(last_modified_timestamp / 1000)
            
            if now - last_modified_time > timedelta(hours=48):
                child_chat_id = task.get("child_chat_id")
                assignee_id = task.get("assignee_id")
                
                if not child_chat_id or not assignee_id:
                    continue
                
                logger.info(f"Task {task.get('record_id')} is inactive. Sending reminder.")
                
                message_text = f"滴滴！请注意，任务「{task.get('title', '未命名')}」已超过48小时无更新，请及时处理。\n\n<at user_id=\"{assignee_id}\"></at>"
                
                await feishu_client.send_message(
                    receive_id_type="chat_id",
                    receive_id=child_chat_id,
                    content=json.dumps({"text": message_text})
                )

    except Exception as e:
        logger.exception(f"Error during check_inactive_tasks job: {e}")


# 初始化调度器
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

# 注意：实际的任务添加和参数传递已移至 app/main.py 的 lifespan 中
# scheduler.add_job(check_inactive_tasks, 'interval', hours=1) 