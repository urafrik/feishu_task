#!/usr/bin/env python3
"""
为已存在的多维表添加字段
"""
import os
import json
import argparse
import logging
from typing import Dict, List, Optional

import httpx
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 根据飞书文档，字段类型需要用数字表示
# https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/guide
FIELD_TYPE_MAP = {
    "text": 1,
    "number": 2,
    "singleSelect": 3,
    "multiSelect": 4,
    "datetime": 5, # 日期时间类型
    "checkbox": 7,
    "person": 11,
    "phone": 13,
    "url": 15,
    "attachment": 17,
    "link": 18,
    "date": 5, # 日期也用5
}

class BitableFieldCreator:
    """飞书多维表字段创建器"""
    
    def __init__(self, debug=False):
        """初始化创建器"""
        self.app_id = os.environ.get("FEISHU_APP_ID")
        self.app_secret = os.environ.get("FEISHU_APP_SECRET")
        self.debug = debug
        
        if not self.app_id or not self.app_secret:
            raise ValueError("请设置环境变量: FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        
        self.access_token = None
        self.base_url = "https://open.feishu.cn/open-apis"
    
    async def get_tenant_access_token(self) -> Optional[str]:
        """获取租户访问令牌"""
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret
                    }
                )
                
                data = response.json()
                if self.debug:
                    logger.info(f"租户访问令牌响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                if data.get("code") == 0:
                    self.access_token = data.get("tenant_access_token")
                    logger.info(f"成功获取租户访问令牌，有效期: {data.get('expire')}秒")
                    return self.access_token
                else:
                    logger.error(f"获取租户访问令牌失败: {data}")
                    return None
                    
        except Exception as e:
            logger.exception(f"获取租户访问令牌异常: {str(e)}")
            return None
    
    async def get_existing_fields(self, app_token: str, table_id: str) -> Dict[str, Dict]:
        """获取已存在的字段列表，返回一个以字段名为key的字典"""
        if not self.access_token:
            await self.get_tenant_access_token()
            if not self.access_token:
                return {}
        
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        existing_fields = {}
        page_token = None
        
        try:
            async with httpx.AsyncClient() as client:
                while True:
                    params = {"page_size": 100}
                    if page_token:
                        params["page_token"] = page_token
                        
                    response = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        params=params
                    )
                    data = response.json()

                    if data.get("code") == 0:
                        items = data.get("data", {}).get("items", [])
                        for item in items:
                            existing_fields[item.get("field_name")] = item
                        
                        if data.get("data", {}).get("has_more"):
                            page_token = data.get("data", {}).get("page_token")
                        else:
                            break
                    else:
                        logger.error(f"获取字段列表失败: {data}")
                        break
            logger.info(f"成功获取表格 {table_id} 的 {len(existing_fields)} 个现有字段。")
            return existing_fields
        except Exception as e:
            logger.exception(f"获取现有字段时出错: {e}")
            return {}

    async def create_field(self, app_token: str, table_id: str, field_name: str,
                         field_type: int, property: Dict = None) -> Optional[str]:
        """
        创建字段 (field_type已修改为int)
        """
        if not self.access_token:
            await self.get_tenant_access_token()
            if not self.access_token:
                return None
        
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        
        # 根据API要求，field_name和type需要在顶层
        field_data = {
            "field_name": field_name,
            "type": field_type
        }
        
        if property:
            field_data["property"] = property
            
        try:
            async with httpx.AsyncClient() as client:
                if self.debug:
                    logger.info(f"创建字段请求体: {json.dumps(field_data, ensure_ascii=False, indent=2)}")
                
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=field_data
                )
                
                data = response.json()
                if self.debug:
                    logger.info(f"创建字段响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                if data.get("code") == 0:
                    field_id = data.get("data", {}).get("field_id")
                    logger.info(f"成功创建字段: {field_name}, 类型: {field_type}")
                    return field_id
                else:
                    error_msg = data.get("msg", "未知错误")
                    # 特殊处理字段名重复的错误
                    if data.get("code") == 1254014: # FieldNameDuplicated
                        error_msg = f"字段名 '{field_name}' 已存在。"
                    logger.error(f"创建字段失败: {field_name}, 错误码: {data.get('code')}, 错误信息: {error_msg}")
                    return None
                    
        except Exception as e:
            logger.exception(f"创建字段异常: {str(e)}")
            return None
    
    async def create_table_fields_base(self, app_token: str, table_id: str, fields_to_create: List[Dict]) -> bool:
        """创建表格字段的基础函数"""
        existing_fields = await self.get_existing_fields(app_token, table_id)
        existing_field_names = existing_fields.keys()
        
        success_count = 0
        total_fields = len(fields_to_create)
        
        for i, field_spec in enumerate(fields_to_create):
            field_name = field_spec["name"]
            field_type_name = field_spec["type"]
            
            logger.info(f"正在处理字段 [{i+1}/{total_fields}]: {field_name}")
            
            if field_name in existing_field_names:
                logger.info(f"字段 '{field_name}' 已存在，跳过创建。")
                success_count += 1
                continue

            field_type_code = FIELD_TYPE_MAP.get(field_type_name)
            if not field_type_code:
                logger.error(f"字段 '{field_name}' 的类型 '{field_type_name}' 未知，跳过。")
                continue

            try:
                field_id = await self.create_field(
                    app_token,
                    table_id,
                    field_name,
                    field_type_code,
                    field_spec.get("property", {})
                )
                if field_id:
                    success_count += 1
                else:
                    logger.error(f"字段 {field_name} 创建失败")
            except Exception as e:
                logger.exception(f"创建字段 {field_name} 时发生异常: {str(e)}")

        logger.info(f"字段创建完成: {success_count}/{total_fields} 个成功处理。")
        return success_count == total_fields
        
    async def create_task_table_fields(self, app_token: str, table_id: str) -> bool:
        """
        创建任务表所需字段
        """
        # 定义任务表字段
        fields = [
            {"name": "title", "type": "text"},
            {"name": "desc", "type": "text", "property": {"is_multiline": True}},
            {"name": "skill_tags", "type": "text"},
            {"name": "deadline", "type": "date"},
            {"name": "assignee_id", "type": "text"},
            {"name": "child_chat_id", "type": "text"},
            {"name": "status", "type": "singleSelect", "property": {
                "options": [
                    {"name": "Draft"}, {"name": "Assigned"}, {"name": "InProgress"},
                    {"name": "Returned"}, {"name": "Done"}, {"name": "Archived"}
                ]
            }},
            {"name": "ci_state", "type": "singleSelect", "property": {
                "options": [
                    {"name": "Unknown"}, {"name": "Pending"}, {"name": "Green"}, {"name": "Red"}
                ]
            }},
            {"name": "ci_commit_sha", "type": "text"},
            {"name": "ai_score", "type": "number"},
            {"name": "submission_url", "type": "url"},
            {"name": "created_at", "type": "datetime"},
            {"name": "assigned_at", "type": "datetime"},
            {"name": "done_at", "type": "datetime"}
        ]
        
        # 移除字段定义中的property，由基础函数处理
        for field in fields:
            if "property" not in field:
                field["property"] = {}

        return await self.create_table_fields_base(app_token, table_id, fields)
    
    async def create_person_table_fields(self, app_token: str, table_id: str) -> bool:
        """
        创建人员表所需字段
        """
        # 定义人员表字段
        fields = [
            {"name": "user_id", "type": "text"},
            {"name": "name", "type": "text"},
            {"name": "skill_tags", "type": "text"},
            {"name": "hours_available", "type": "number"},
            {"name": "performance", "type": "number"},
            {"name": "last_done_at", "type": "datetime"}
        ]
        
        for field in fields:
            if "property" not in field:
                field["property"] = {}
                
        return await self.create_table_fields_base(app_token, table_id, fields)
    
    async def add_all_fields(self, app_token: str, task_table_id: str, person_table_id: str):
        """添加所有字段"""
        # 获取访问令牌
        if not await self.get_tenant_access_token():
            logger.error("无法获取访问令牌，退出")
            return
            
        # 创建任务表字段
        logger.info(f"开始创建任务表字段...")
        task_success = await self.create_task_table_fields(app_token, task_table_id)
        if not task_success:
            logger.warning("部分任务表字段创建失败")
            
        # 创建人员表字段
        logger.info(f"开始创建人员表字段...")
        person_success = await self.create_person_table_fields(app_token, person_table_id)
        if not person_success:
            logger.warning("部分人员表字段创建失败")
            
        logger.info("字段创建完成")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='为已存在的多维表添加字段')
    parser.add_argument('--app-token', required=True, help='多维表应用token')
    parser.add_argument('--task-table-id', required=True, help='任务表ID')
    parser.add_argument('--person-table-id', required=True, help='人员表ID')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()
    
    creator = BitableFieldCreator(debug=args.debug)
    await creator.add_all_fields(args.app_token, args.task_table_id, args.person_table_id)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 