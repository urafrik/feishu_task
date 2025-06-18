import logging
from typing import Optional, Dict, List, Any
from enum import Enum

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import (
    AppTableRecord,
    CreateAppTableRecordRequest,
    ListAppTableRecordRequest,
    BatchUpdateAppTableRecordRequest,
)

from app.config import settings
# from app.services.feishu import feishu_client # This is unused and points to a non-existent global client

# 任务状态枚举
class TaskStatus(str, Enum):
    DRAFT = "Draft"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "InProgress"
    RETURNED = "Returned"
    DONE = "Done"
    ARCHIVED = "Archived"
    CI_PASS = "CI Pass"
    CI_FAIL = "CI Fail"

class BitableClient:
    """多维表操作客户端 (适配 lark-oapi v2, 异步)"""

    def __init__(self, settings, feishu_client: lark.Client):
        self.app_token = settings.bitable.app_token
        self.task_table_id = settings.bitable.task_table_id
        self.person_table_id = settings.bitable.person_table_id
        self.client = feishu_client

    async def _get_all_records(self, table_id: str, filter_formula: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取指定表格的所有记录 (异步)"""
        all_records = []
        page_token = None
        while True:
            builder = ListAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(table_id) \
                .page_size(100)
            
            if page_token:
                builder.page_token(page_token)
            if filter_formula:
                builder.filter(filter_formula)

            try:
                resp = await self.client.bitable.v1.app_table_record.list(builder.build())
                if not resp.success():
                    logging.error(f"列出记录失败: {resp.code} {resp.msg} {resp.error}")
                    break
                
                items = resp.data.items or []
                for item in items:
                    record_data = item.fields
                    record_data['record_id'] = item.record_id
                    all_records.append(record_data)
                
                if resp.data.has_more:
                    page_token = resp.data.page_token
                else:
                    break
            except Exception as e:
                logging.exception(f"从表 {table_id} 获取记录时出错: {e}")
                break
        return all_records

    async def create_record(self, table_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """向指定表格添加一条记录 (异步)"""
        record = AppTableRecord(fields=fields)
        req = CreateAppTableRecordRequest.builder() \
            .app_token(self.app_token) \
            .table_id(table_id) \
            .request_body(record) \
            .build()
        try:
            resp = await self.client.bitable.v1.app_table_record.create(req)
            if not resp.success():
                logging.error(f"添加记录失败: {resp.code} {resp.msg} {resp.error}")
                return None
            
            logging.info(f"成功向表 {table_id} 添加记录")
            record_data = resp.data.record.fields
            record_data['record_id'] = resp.data.record.record_id
            return record_data
        except Exception as e:
            logging.exception(f"向表 {table_id} 添加记录时出错: {e}")
            return None
            
    async def update_record(self, table_id: str, record_id: str, fields: Dict[str, Any]) -> bool:
        """更新指定表格的一条记录 (异步)"""
        record = AppTableRecord(record_id=record_id, fields=fields)
        req = BatchUpdateAppTableRecordRequest.builder() \
            .app_token(self.app_token) \
            .table_id(table_id) \
            .request_body([record]) \
            .build()
        try:
            resp = await self.client.bitable.v1.app_table_record.batch_update(req)
            if not resp.success():
                logging.error(f"更新记录 {record_id} 失败: {resp.code} {resp.msg} {resp.error}")
                return False
            
            logging.info(f"成功更新表 {table_id} 中的记录 {record_id}")
            return True
        except Exception as e:
            logging.exception(f"更新表 {table_id} 中的记录 {record_id} 时出错: {e}")
            return False

    async def get_all_persons(self) -> List[Dict[str, Any]]:
        """获取人员表中的所有记录"""
        return await self._get_all_records(self.person_table_id)

    async def create_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建一条新的任务记录"""
        return await self.create_record(self.task_table_id, task_data)

    async def update_task(self, record_id: str, task_data: Dict[str, Any]) -> bool:
        """更新一条任务记录"""
        return await self.update_record(self.task_table_id, record_id, task_data)

    async def update_task_status(self, record_id: str, status: TaskStatus) -> bool:
        """更新任务的状态"""
        return await self.update_task(record_id, {"status": status.value})

    async def get_task_by_chat_id(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """通过群聊ID获取任务"""
        records = await self._get_all_records(
            self.task_table_id,
            filter_formula=f'CurrentValue.[child_chat_id]="{chat_id}"'
        )
        return records[0] if records else None

    async def get_task_by_commit(self, commit_sha: str) -> Optional[Dict[str, Any]]:
        """通过Commit SHA获取任务"""
        records = await self._get_all_records(
            self.task_table_id,
            filter_formula=f'CurrentValue.[github_commit_sha]="{commit_sha}"'
        )
        return records[0] if records else None

# 全局客户端实例不应在此处创建，以避免循环依赖
# 它应该由应用主逻辑或使用它的服务来按需创建。