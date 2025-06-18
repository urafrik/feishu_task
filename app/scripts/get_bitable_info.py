#!/usr/bin/env python3
"""
获取飞书多维表应用信息
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

class BitableInfoGetter:
    """飞书多维表信息获取器"""
    
    def __init__(self, debug=False):
        """初始化"""
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
                    logger.info(f"获取租户访问令牌响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
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
    
    async def list_apps(self, page_size: int = 100) -> List[Dict]:
        """
        列出所有多维表应用
        
        Args:
            page_size: 每页数量
            
        Returns:
            应用列表
        """
        if not self.access_token:
            await self.get_tenant_access_token()
            if not self.access_token:
                return []
        
        # 尝试不同的API端点
        url = f"{self.base_url}/bitable/v1/apps"
        apps = []
        page_token = None
        
        try:
            while True:
                params = {"page_size": page_size}
                if page_token:
                    params["page_token"] = page_token
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        params=params,
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
                    
                    if self.debug:
                        logger.info(f"获取应用列表请求URL: {url}")
                        logger.info(f"响应状态码: {response.status_code}")
                        logger.info(f"响应头: {response.headers}")
                        logger.info(f"响应内容: {response.text}")
                    
                    try:
                        data = response.json()
                    except Exception as e:
                        logger.error(f"解析响应JSON失败: {e}")
                        logger.error(f"原始响应: {response.text}")
                        break
                    
                    if data.get("code") == 0:
                        items = data.get("data", {}).get("items", [])
                        apps.extend(items)
                        
                        page_token = data.get("data", {}).get("page_token")
                        if not page_token:
                            break
                    else:
                        logger.error(f"获取应用列表失败: {data}")
                        break
            
            # 如果第一个API失败，尝试使用另一个URL模式
            if not apps:
                logger.info("使用备用API尝试获取应用列表")
                url = f"{self.base_url}/drive/explorer/v2/folder/list_all"
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        params={"type": "bitable"}
                    )
                    
                    if self.debug:
                        logger.info(f"备用API请求URL: {url}")
                        logger.info(f"响应状态码: {response.status_code}")
                        logger.info(f"响应内容: {response.text}")
                    
                    try:
                        data = response.json()
                        if data.get("code") == 0:
                            items = data.get("data", {}).get("files", [])
                            apps = [item for item in items if item.get("type") == "bitable"]
                    except Exception as e:
                        logger.error(f"解析备用API响应失败: {e}")
            
            logger.info(f"成功获取 {len(apps)} 个多维表应用")
            return apps
            
        except Exception as e:
            logger.exception(f"获取应用列表异常: {str(e)}")
            return []
    
    async def get_tables(self, app_token: str) -> List[Dict]:
        """
        获取指定应用下的所有表
        
        Args:
            app_token: 应用Token
            
        Returns:
            表列表
        """
        if not self.access_token:
            await self.get_tenant_access_token()
            if not self.access_token:
                return []
        
        # 尝试三种可能的URL格式
        urls = [
            f"{self.base_url}/bitable/v1/apps/{app_token}/tables",
            f"{self.base_url}/bitable/v1/bases/{app_token}/tables"
        ]
        
        tables = []
        
        for url in urls:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
                    
                    if self.debug:
                        logger.info(f"获取表格列表请求URL: {url}")
                        logger.info(f"响应状态码: {response.status_code}")
                        logger.info(f"响应内容: {response.text[:300]}...")  # 只显示部分内容
                    
                    if response.status_code != 200:
                        continue
                        
                    try:
                        data = response.json()
                        if data.get("code") == 0:
                            tables = data.get("data", {}).get("items", [])
                            logger.info(f"使用URL {url} 成功获取 {len(tables)} 个表格")
                            break
                    except Exception as e:
                        logger.error(f"解析表格列表响应失败: {e}")
                
            except Exception as e:
                logger.exception(f"获取表格列表异常: {str(e)}")
        
        return tables
    
    async def get_fields(self, app_token: str, table_id: str) -> List[Dict]:
        """
        获取指定表的所有字段
        
        Args:
            app_token: 应用Token
            table_id: 表ID
            
        Returns:
            字段列表
        """
        if not self.access_token:
            await self.get_tenant_access_token()
            if not self.access_token:
                return []
        
        # 尝试两种可能的URL格式
        urls = [
            f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            f"{self.base_url}/bitable/v1/bases/{app_token}/tables/{table_id}/fields"
        ]
        
        fields = []
        
        for url in urls:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
                    
                    if self.debug:
                        logger.info(f"获取字段列表请求URL: {url}")
                        logger.info(f"响应状态码: {response.status_code}")
                        logger.info(f"响应内容: {response.text[:300]}...")  # 只显示部分内容
                    
                    if response.status_code != 200:
                        continue
                    
                    try:
                        data = response.json()
                        if data.get("code") == 0:
                            fields = data.get("data", {}).get("items", [])
                            logger.info(f"使用URL {url} 成功获取 {len(fields)} 个字段")
                            break
                    except Exception as e:
                        logger.error(f"解析字段列表响应失败: {e}")
                    
            except Exception as e:
                logger.exception(f"获取字段列表异常: {str(e)}")
        
        return fields
    
    async def get_direct_info(self, app_token: str):
        """
        直接通过应用token获取信息
        
        Args:
            app_token: 应用Token
        """
        # 获取表格
        tables = await self.get_tables(app_token)
        
        if not tables:
            logger.error(f"未找到应用 {app_token} 的任何表格")
            return
        
        task_table = None
        person_table = None
        
        for table in tables:
            if table.get("name") == "任务表":
                task_table = table
            elif table.get("name") == "人员表":
                person_table = table
        
        # 输出配置信息
        logger.info("\n=== 配置信息 ===")
        logger.info(f"app_token: {app_token}")
        
        if task_table:
            logger.info(f"task_table_id: {task_table.get('table_id')}")
            # 获取字段
            logger.info("\n=== 任务表字段 ===")
            fields = await self.get_fields(app_token, task_table.get("table_id"))
            for field in fields:
                logger.info(f"字段: {field.get('name')}, 类型: {field.get('type')}, ID: {field.get('field_id')}")
        else:
            logger.warning("未找到任务表")
            
        if person_table:
            logger.info(f"person_table_id: {person_table.get('table_id')}")
            # 获取字段
            logger.info("\n=== 人员表字段 ===")
            fields = await self.get_fields(app_token, person_table.get("table_id"))
            for field in fields:
                logger.info(f"字段: {field.get('name')}, 类型: {field.get('type')}, ID: {field.get('field_id')}")
        else:
            logger.warning("未找到人员表")
            
        # 输出.env配置示例
        if app_token and task_table and person_table:
            logger.info(f"\n=== .env 配置示例 ===")
            logger.info(f"BITABLE_APP_TOKEN={app_token}")
            logger.info(f"BITABLE_TASK_TABLE_ID={task_table.get('table_id')}")
            logger.info(f"BITABLE_PERSON_TABLE_ID={person_table.get('table_id')}")
    
    async def get_info_by_name(self, app_name: str = "任务管理系统"):
        """
        通过应用名称获取信息
        
        Args:
            app_name: 应用名称
        """
        apps = await self.list_apps()
        
        if self.debug:
            logger.info(f"获取到的应用列表: {json.dumps(apps, ensure_ascii=False, indent=2)}")
        
        target_app = None
        for app in apps:
            if app.get("name") == app_name:
                target_app = app
                break
        
        if not target_app:
            logger.error(f"未找到名为 '{app_name}' 的应用")
            
            # 如果没找到应用但有应用列表，显示可用的应用
            if apps:
                logger.info("可用的应用列表:")
                for i, app in enumerate(apps):
                    logger.info(f"{i+1}. {app.get('name')} (token: {app.get('app_token') or app.get('base_token')})")
            return
        
        # 尝试获取token (可能是app_token或base_token)
        app_token = target_app.get("app_token") or target_app.get("base_token")
        logger.info(f"找到应用: {app_name}, token: {app_token}")
        
        await self.get_direct_info(app_token)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='获取飞书多维表应用信息')
    parser.add_argument('--app-name', default='任务管理系统', help='指定应用名称')
    parser.add_argument('--app-token', help='直接指定应用token')
    parser.add_argument('--debug', action='store_true', help='开启调试模式')
    args = parser.parse_args()
    
    getter = BitableInfoGetter(debug=args.debug)
    
    if args.app_token:
        await getter.get_direct_info(args.app_token)
    else:
        await getter.get_info_by_name(args.app_name)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 