import logging
import json
from typing import List, Optional

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    PatchMessageRequest,
    PatchMessageRequestBody,
    CreateChatRequest,
    CreateChatRequestBody,
)

from app.config import Settings, settings

class FeishuClient:
    """飞书 API 客户端 (适配 lark-oapi, 异步)"""

    def __init__(self, settings: Settings):
        self.settings = settings.feishu
        self.client = lark.Client.builder() \
            .app_id(self.settings.app_id) \
            .app_secret(self.settings.app_secret) \
            .enable_set_token(True) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()

    async def send_message(self, receive_id_type: str, receive_id: str, content: str, msg_type: str = "interactive"):
        """发送消息 (异步)"""
        req = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(receive_id)
                .content(content)
                .msg_type(msg_type)
                .build()
            ).build()
        try:
            resp = await self.client.im.v1.message.create(req)
            if not resp.success():
                logging.error(f"发送消息失败: {resp.code} {resp.msg}")
            else:
                logging.info(f"成功向 {receive_id} 发送消息")
        except Exception as e:
            logging.exception(f"发送消息时出错: {e}")

    async def send_card(self, receive_id_type: str, receive_id: str, card_content: dict):
        """发送卡片消息 (异步)"""
        content_str = json.dumps(card_content)
        await self.send_message(receive_id_type, receive_id, content_str, "interactive")

    async def update_card(self, message_id: str, card_content: dict):
        """更新卡片消息 (异步)"""
        req = PatchMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(PatchMessageRequestBody.builder().content(json.dumps(card_content)).build()) \
            .build()

        try:
            resp = await self.client.im.v1.message.patch(req)
            if not resp.success():
                logging.error(f"更新卡片失败: {resp.code} {resp.msg} {resp.error}")
                return None
            logging.info(f"卡片更新成功: {message_id}")
            return resp.data
        except Exception as e:
            logging.exception(f"更新卡片异常: {e}")
            return None

    async def create_chat(self, name: str, description: Optional[str], user_ids: List[str]):
        """创建群聊 (异步)"""
        req = CreateChatRequest.builder() \
            .request_body(CreateChatRequestBody.builder()
                .name(name)
                .description(description)
                .user_id_list(user_ids)
                .build()) \
            .build()

        try:
            resp = await self.client.im.v1.chat.create(req)
            if not resp.success():
                logging.error(f"创建群聊失败: {resp.code} {resp.msg} {resp.error}")
                return None
            chat_id = resp.data.chat_id
            logging.info(f"群聊创建成功: {chat_id}")
            return chat_id
        except Exception as e:
            logging.exception(f"创建群聊异常: {e}")
            return None

# 创建一个全局的飞书客户端实例
feishu_client = FeishuClient(settings) 