#!/usr/bin/env python3
"""
自动创建飞书多维表应用及表结构
"""
import os
import argparse
import json
import logging
from typing import Dict, Any, List, Optional

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

class BitableCreator:
    """飞书多维表创建器"""
    
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
    
    async def create_bitable_app(self, name: str, description: str = "") -> Optional[str]:
        """
        创建多维表应用
        
        Args:
            name: 应用名称
            description: 应用描述
            
        Returns:
            应用Token 或 None (失败时)
        """
        if not self.access_token:
            await self.get_tenant_access_token()
            if not self.access_token:
                return None
                
        url = f"{self.base_url}/bitable/v1/apps"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json={
                        "name": name,
                        "description": description
                    }
                )
                
                data = response.json()
                if self.debug:
                    logger.info(f"创建多维表应用响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                if data.get("code") == 0:
                    # 根据响应格式提取app_token (在app对象中)
                    app_token = data.get("data", {}).get("app", {}).get("app_token")
                    if app_token:
                        logger.info(f"成功创建多维表应用: {name}, token: {app_token}")
                        return app_token
                    else:
                        logger.error(f"创建多维表应用成功但未返回token，完整响应: {data}")
                        return None
                else:
                    error_msg = data.get("msg", "未知错误")
                    logger.error(f"创建多维表应用失败，错误码: {data.get('code')}, 错误信息: {error_msg}")
                    
                    # 检查特定错误码
                    if data.get("code") == 1069902:
                        logger.error("权限错误: 没有权限创建多维表应用，请检查应用权限设置")
                    elif data.get("code") == 1382401:
                        logger.error("资源限制: 可能已达到多维表应用的创建上限")
                        
                    return None
                    
        except Exception as e:
            logger.exception(f"创建多维表应用异常: {str(e)}")
            return None
    
    async def create_table(self, app_token: str, name: str, description: str = "") -> Optional[str]:
        """
        创建数据表
        
        Args:
            app_token: 应用Token
            name: 表名称
            description: 表描述
            
        Returns:
            表ID 或 None (失败时)
        """
        if not self.access_token:
            await self.get_tenant_access_token()
            if not self.access_token:
                return None
                
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables"
        
        try:
            async with httpx.AsyncClient() as client:
                # 根据API文档要求，字段名应为table_name而非name
                payload = {
                    "table": {
                        "name": name
                    }
                }
                
                if description:
                    payload["table"]["description"] = description
                
                if self.debug:
                    logger.info(f"创建表请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")
                
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=payload
                )
                
                data = response.json()
                if self.debug:
                    logger.info(f"创建表响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                if data.get("code") == 0:
                    # 根据实际响应格式，table_id直接在data对象中
                    table_id = data.get("data", {}).get("table_id")
                    logger.info(f"成功创建表: {name}, ID: {table_id}")
                    return table_id
                else:
                    error_msg = data.get("msg", "未知错误")
                    logger.error(f"创建表失败，错误码: {data.get('code')}, 错误信息: {error_msg}")
                    return None
                    
        except Exception as e:
            logger.exception(f"创建表异常: {str(e)}")
            return None
    
    async def create_field(self, app_token: str, table_id: str, field_name: str, 
                         field_type: int, property: Optional[Dict] = None) -> Optional[str]:
        """
        创建字段
        
        Args:
            app_token: 应用Token
            table_id: 表ID
            field_name: 字段名称
            field_type: 字段类型对应的整数编码 (例如: 1 for text, 2 for number)
            property: 字段属性，不同类型有不同属性
            
        Returns:
            字段ID 或 None (失败时)
        """
        if not self.access_token:
            await self.get_tenant_access_token()
            if not self.access_token:
                return None
        
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        
        # 修正: 根据飞书文档，field_name 和 type 应在顶层
        field_data = {
            "field_name": field_name,
            "type": field_type
        }
        
        if property:
            field_data["property"] = property
            
        try:
            async with httpx.AsyncClient() as client:
                if self.debug and field_name == "title":
                    logger.info(f"创建字段请求体: {json.dumps(field_data, ensure_ascii=False, indent=2)}")
                
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=field_data
                )
                
                data = response.json()
                if self.debug and field_name == "title":  # 只对第一个字段输出详细信息，避免日志过多
                    logger.info(f"创建字段响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                if data.get("code") == 0:
                    field_id = data.get("data", {}).get("field", {}).get("field_id")
                    logger.info(f"成功创建字段: {field_name}, 类型: {field_type}, ID: {field_id}")
                    return field_id
                else:
                    error_msg = data.get("msg", "未知错误")
                    logger.error(f"创建字段失败: {field_name}, 错误码: {data.get('code')}, 错误信息: {error_msg}")
                    return None
                    
        except Exception as e:
            logger.exception(f"创建字段异常: {str(e)}")
            return None
    
    async def create_task_table_fields(self, app_token: str, table_id: str) -> bool:
        """
        创建任务表所需字段
        
        Args:
            app_token: 应用Token
            table_id: 表ID
            
        Returns:
            是否成功
        """
        # 诊断步骤: 移除所有日期字段的 property，用 None 代替，以定位错误根源
        fields = [
            {"name": "title", "type": 1, "property": None},
            {"name": "desc", "type": 1, "property": None},
            {"name": "skill_tags", "type": 1, "property": None},
            {"name": "deadline", "type": 5, "property": None},
            {"name": "assignee_id", "type": 1, "property": None},
            {"name": "child_chat_id", "type": 1, "property": None},
            {"name": "status", "type": 3, "property": {
                "options": [
                    {"name": "Draft", "color": 1},
                    {"name": "Assigned", "color": 2},
                    {"name": "InProgress", "color": 3},
                    {"name": "Returned", "color": 4},
                    {"name": "Done", "color": 5},
                    {"name": "Archived", "color": 6}
                ]
            }},
            {"name": "ci_state", "type": 3, "property": {
                "options": [
                    {"name": "Unknown", "color": 7},
                    {"name": "Pending", "color": 3},
                    {"name": "Green", "color": 5},
                    {"name": "Red", "color": 4}
                ]
            }},
            {"name": "ci_commit_sha", "type": 1, "property": None},
            {"name": "ai_score", "type": 2, "property": {"formatter": "0"}},
            {"name": "submission_url", "type": 15, "property": None},
            {"name": "created_at", "type": 5, "property": None},
            {"name": "assigned_at", "type": 5, "property": None},
            {"name": "done_at", "type": 5, "property": None}
        ]
        
        success_count = 0
        for i, field in enumerate(fields):
            try:
                logger.info(f"正在创建任务表字段 [{i+1}/{len(fields)}]: {field['name']}")
                field_id = await self.create_field(
                    app_token, 
                    table_id, 
                    field["name"], 
                    field["type"], 
                    field["property"]
                )
                if field_id:
                    success_count += 1
                else:
                    logger.error(f"字段 {field['name']} 创建失败")
            except Exception as e:
                logger.exception(f"创建字段 {field['name']} 时发生异常: {str(e)}")
                
        logger.info(f"任务表字段创建完成: {success_count}/{len(fields)} 个成功")
        return success_count == len(fields)
    
    async def create_person_table_fields(self, app_token: str, table_id: str) -> bool:
        """
        创建人员表所需字段
        
        Args:
            app_token: 应用Token
            table_id: 表ID
            
        Returns:
            是否成功
        """
        # 诊断步骤: 移除所有日期字段的 property
        fields = [
            {"name": "user_id", "type": 1, "property": None},
            {"name": "name", "type": 1, "property": None},
            {"name": "skill_tags", "type": 1, "property": None},
            {"name": "hours_available", "type": 2, "property": {"formatter": "0"}},
            {"name": "performance", "type": 2, "property": {"formatter": "0.0"}},
            {"name": "last_done_at", "type": 5, "property": None}
        ]
        
        success_count = 0
        for i, field in enumerate(fields):
            try:
                logger.info(f"正在创建人员表字段 [{i+1}/{len(fields)}]: {field['name']}")
                field_id = await self.create_field(
                    app_token, 
                    table_id, 
                    field["name"], 
                    field["type"], 
                    field["property"]
                )
                if field_id:
                    success_count += 1
                else:
                    logger.error(f"字段 {field['name']} 创建失败")
            except Exception as e:
                logger.exception(f"创建字段 {field['name']} 时发生异常: {str(e)}")
                
        logger.info(f"人员表字段创建完成: {success_count}/{len(fields)} 个成功")
        return success_count == len(fields)
    
    async def create_all(self):
        """创建完整的多维表应用和所有表结构"""
        # 获取访问令牌
        if not await self.get_tenant_access_token():
            logger.error("无法获取访问令牌，退出")
            return
        
        # 创建应用
        app_token = await self.create_bitable_app("任务管理系统", "飞书任务Bot的数据存储")
        if not app_token:
            logger.error("创建应用失败，退出")
            return
        
        # 创建任务表
        task_table_id = await self.create_table(app_token, "任务表", "存储所有任务数据")
        if not task_table_id:
            logger.error("创建任务表失败，退出")
            return
        
        # 创建人员表
        person_table_id = await self.create_table(app_token, "人员表", "存储所有人员数据")
        if not person_table_id:
            logger.error("创建人员表失败，退出")
            return
        
        # 创建任务表字段
        if not await self.create_task_table_fields(app_token, task_table_id):
            logger.error("创建任务表字段失败")
        
        # 创建人员表字段
        if not await self.create_person_table_fields(app_token, person_table_id):
            logger.error("创建人员表字段失败")
        
        # 输出结果
        logger.info(f"\n多维表创建完成！请在配置中使用以下值：")
        logger.info(f"app_token: {app_token}")
        logger.info(f"task_table_id: {task_table_id}")
        logger.info(f"person_table_id: {person_table_id}")
        
        # 打印配置示例
        logger.info(f"\n配置示例：")
        logger.info(f"bitable_client.set_app_token(\"{app_token}\")")
        logger.info(f"bitable_client.set_table_ids(\"{task_table_id}\", \"{person_table_id}\")")
        
        # 打印.env配置示例
        logger.info(f"\n.env配置示例：")
        logger.info(f"BITABLE_APP_TOKEN={app_token}")
        logger.info(f"BITABLE_TASK_TABLE_ID={task_table_id}")
        logger.info(f"BITABLE_PERSON_TABLE_ID={person_table_id}")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='创建飞书多维表应用及表结构')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，输出更多信息')
    args = parser.parse_args()
    
    creator = BitableCreator(debug=args.debug)
    await creator.create_all()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 