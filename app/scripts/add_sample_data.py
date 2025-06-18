#!/usr/bin/env python3
"""
向飞书多维表中添加示例数据
"""
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

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

class BitableSampleData:
    """飞书多维表示例数据创建器"""
    
    def __init__(self):
        """初始化"""
        self.app_id = os.environ.get("FEISHU_APP_ID")
        self.app_secret = os.environ.get("FEISHU_APP_SECRET")
        
        if not self.app_id or not self.app_secret:
            raise ValueError("请设置环境变量: FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        
        # 多维表配置，这些应从命令行参数或环境变量获取
        self.app_token = os.environ.get("BITABLE_APP_TOKEN", "")
        self.task_table_id = os.environ.get("BITABLE_TASK_TABLE_ID", "")
        self.person_table_id = os.environ.get("BITABLE_PERSON_TABLE_ID", "")
        
        if not self.app_token or not self.task_table_id or not self.person_table_id:
            logger.warning("未设置多维表信息，请通过命令行参数提供")
        
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
    
    async def create_record(self, table_id: str, fields: Dict[str, Any]) -> Optional[str]:
        """
        创建记录
        
        Args:
            table_id: 表ID
            fields: 字段值
            
        Returns:
            记录ID 或 None (失败时)
        """
        if not self.access_token:
            await self.get_tenant_access_token()
            if not self.access_token:
                return None
                
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{table_id}/records"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json={"fields": fields}
                )
                
                data = response.json()
                if data.get("code") == 0:
                    record_id = data.get("data", {}).get("record_id")
                    logger.info(f"成功创建记录: {record_id}")
                    return record_id
                else:
                    logger.error(f"创建记录失败: {data}")
                    return None
                    
        except Exception as e:
            logger.exception(f"创建记录异常: {str(e)}")
            return None
    
    async def add_sample_persons(self) -> List[str]:
        """
        添加示例人员数据
        
        Returns:
            添加的人员ID列表
        """
        # 示例人员数据
        sample_persons = [
            {
                "user_id": "ou_abc123",  # 这是模拟的用户ID，实际使用需要真实的飞书用户ID
                "name": "张三",
                "skill_tags": "Python, FastAPI, 数据分析",
                "hours_available": 30,
                "performance": 85,
                "last_done_at": (datetime.now() - timedelta(days=3)).isoformat()
            },
            {
                "user_id": "ou_def456",
                "name": "李四",
                "skill_tags": "React, TypeScript, 前端开发",
                "hours_available": 20,
                "performance": 90,
                "last_done_at": (datetime.now() - timedelta(days=5)).isoformat()
            },
            {
                "user_id": "ou_ghi789",
                "name": "王五",
                "skill_tags": "UI设计, Figma, 用户研究",
                "hours_available": 25,
                "performance": 88,
                "last_done_at": (datetime.now() - timedelta(days=2)).isoformat()
            },
            {
                "user_id": "ou_jkl012",
                "name": "赵六",
                "skill_tags": "Java, Spring Boot, 后端开发",
                "hours_available": 35,
                "performance": 92,
                "last_done_at": (datetime.now() - timedelta(days=7)).isoformat()
            },
            {
                "user_id": "ou_mno345",
                "name": "钱七",
                "skill_tags": "DevOps, Docker, Kubernetes",
                "hours_available": 40,
                "performance": 95,
                "last_done_at": (datetime.now() - timedelta(days=1)).isoformat()
            }
        ]
        
        person_ids = []
        for person in sample_persons:
            record_id = await self.create_record(self.person_table_id, person)
            if record_id:
                person_ids.append(record_id)
        
        logger.info(f"添加了 {len(person_ids)}/{len(sample_persons)} 个示例人员")
        return person_ids
    
    async def add_sample_tasks(self) -> List[str]:
        """
        添加示例任务数据
        
        Returns:
            添加的任务ID列表
        """
        # 获取当前时间作为基准
        now = datetime.now()
        
        # 示例任务数据
        sample_tasks = [
            {
                "title": "开发飞书机器人API对接",
                "desc": "实现与飞书API的对接，包括消息收发、群组创建等功能",
                "skill_tags": "Python, FastAPI, 飞书API",
                "deadline": (now + timedelta(days=7)).isoformat(),
                "status": "Draft",
                "created_at": now.isoformat()
            },
            {
                "title": "设计任务管理系统UI",
                "desc": "为任务管理系统设计一套美观易用的UI界面，包括任务列表、详情页等",
                "skill_tags": "UI设计, Figma",
                "deadline": (now + timedelta(days=5)).isoformat(),
                "status": "Draft",
                "created_at": now.isoformat()
            },
            {
                "title": "实现前端交互组件",
                "desc": "开发任务管理前端页面，包括任务列表、过滤、排序等功能",
                "skill_tags": "React, TypeScript",
                "deadline": (now + timedelta(days=10)).isoformat(),
                "status": "Draft",
                "created_at": now.isoformat()
            },
            {
                "title": "搭建CI/CD流水线",
                "desc": "配置GitHub Actions工作流，实现代码提交自动测试和部署",
                "skill_tags": "DevOps, GitHub Actions",
                "deadline": (now + timedelta(days=3)).isoformat(),
                "status": "Draft",
                "created_at": now.isoformat()
            },
            {
                "title": "编写API文档",
                "desc": "为系统API编写详细的接口文档，包括参数说明、返回值等",
                "skill_tags": "技术文档, API设计",
                "deadline": (now + timedelta(days=6)).isoformat(),
                "status": "Draft",
                "created_at": now.isoformat()
            }
        ]
        
        task_ids = []
        for task in sample_tasks:
            record_id = await self.create_record(self.task_table_id, task)
            if record_id:
                task_ids.append(record_id)
        
        logger.info(f"添加了 {len(task_ids)}/{len(sample_tasks)} 个示例任务")
        return task_ids
    
    async def add_all_samples(self, app_token: str = None, task_table_id: str = None, person_table_id: str = None):
        """添加所有示例数据"""
        # 设置表信息，如果提供的话
        if app_token:
            self.app_token = app_token
        if task_table_id:
            self.task_table_id = task_table_id
        if person_table_id:
            self.person_table_id = person_table_id
            
        # 验证必要信息
        if not self.app_token or not self.task_table_id or not self.person_table_id:
            logger.error("缺少必要的多维表信息，请提供app_token和表ID")
            return
            
        # 获取访问令牌
        if not await self.get_tenant_access_token():
            logger.error("无法获取访问令牌，退出")
            return
            
        # 添加示例人员
        await self.add_sample_persons()
        
        # 添加示例任务
        await self.add_sample_tasks()
        
        logger.info("示例数据添加完成！")
        

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='向飞书多维表添加示例数据')
    parser.add_argument('--app-token', help='多维表应用Token')
    parser.add_argument('--task-table-id', help='任务表ID')
    parser.add_argument('--person-table-id', help='人员表ID')
    
    args = parser.parse_args()
    
    creator = BitableSampleData()
    await creator.add_all_samples(
        app_token=args.app_token,
        task_table_id=args.task_table_id,
        person_table_id=args.person_table_id
    )


if __name__ == "__main__":
    asyncio.run(main()) 