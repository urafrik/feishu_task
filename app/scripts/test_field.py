#!/usr/bin/env python3
"""
测试飞书多维表字段创建
"""
import os
import json
import logging
import asyncio
from typing import Optional
import argparse

import httpx
from dotenv import load_dotenv
from app.scripts.add_fields import BitableFieldCreator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

async def get_tenant_access_token() -> Optional[str]:
    """获取租户访问令牌"""
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        logger.error("请设置环境变量: FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        return None
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "app_id": app_id,
                    "app_secret": app_secret
                }
            )
            
            data = response.json()
            logger.info(f"获取租户访问令牌响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                
            if data.get("code") == 0:
                token = data.get("tenant_access_token")
                logger.info(f"成功获取租户访问令牌，有效期: {data.get('expire')}秒")
                return token
            else:
                logger.error(f"获取租户访问令牌失败: {data}")
                return None
                
    except Exception as e:
        logger.exception(f"获取租户访问令牌异常: {str(e)}")
        return None

async def test_field_creation():
    """测试字段创建"""
    # 获取访问令牌
    access_token = await get_tenant_access_token()
    if not access_token:
        logger.error("无法获取访问令牌，退出")
        return
    
    # 使用环境变量或者手动指定
    app_token = os.environ.get("BITABLE_APP_TOKEN", "OyHsbrVTEavY21sj1GMc0Hnsnye")
    table_id = os.environ.get("BITABLE_TASK_TABLE_ID", "tblRmRDudKMSScMn")
    
    logger.info(f"使用 app_token={app_token}, table_id={table_id}")
    
    # 尝试不同的字段创建格式
    field_formats = [
        # 格式1: 标准格式
        {
            "field_name": "test_field1",
            "type": "text"
        },
        # 格式2: 使用数字类型
        {
            "field_name": "test_field2",
            "type": 1  # 假设1代表文本
        },
        # 格式3: 嵌套在field内
        {
            "field": {
                "name": "test_field3",
                "type": "text"
            }
        },
        # 格式4: 直接使用name而非field_name
        {
            "name": "test_field4",
            "type": "text"
        },
        # 格式5: 使用API文档推荐格式
        {
            "field_name": "test_field5",
            "field_type": 1,  # 1可能代表文本类型
        }
    ]
    
    # 依次尝试各种格式
    for i, payload in enumerate(field_formats):
        logger.info(f"尝试格式 {i+1}: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    json=payload
                )
                
                status_code = response.status_code
                logger.info(f"响应状态码: {status_code}")
                
                try:
                    data = response.json()
                    logger.info(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                    if data.get("code") == 0:
                        logger.info(f"格式 {i+1} 成功!")
                    else:
                        logger.error(f"格式 {i+1} 失败: {data.get('msg')}")
                        
                        # 检查是否有详细错误信息
                        if "error" in data and "field_violations" in data["error"]:
                            for violation in data["error"]["field_violations"]:
                                logger.error(f"字段错误: {violation['field']} - {violation['description']}")
                    
                except Exception as e:
                    logger.error(f"解析响应失败: {str(e)}")
                    logger.error(f"原始响应: {response.text}")
                    
                # 等待一小段时间，避免过于频繁的请求
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.exception(f"请求异常: {str(e)}")

async def main():
    """
    一个用于单独测试字段创建功能的小脚本。
    """
    parser = argparse.ArgumentParser(description="测试飞书多维表字段创建")
    parser.add_argument("--app-token", required=True, help="多维表应用的 App Token")
    parser.add_argument("--table-id", required=True, help="要添加字段的表的 Table ID")
    parser.add_argument("--field-name", default="TestFieldFromScript", help="要创建的字段名")
    parser.add_argument("--field-type", default="1", help="要创建的字段类型 (数字)")
    args = parser.parse_args()

    creator = BitableFieldCreator(debug=True)

    logging.info(f"正在尝试在表格 {args.table_id} 中创建字段 '{args.field_name}' (类型: {args.field_type})")

    # 注意：我们将 field_type 转换为整数
    field_id = await creator.create_field(
        app_token=args.app_token,
        table_id=args.table_id,
        field_name=args.field_name,
        field_type=int(args.field_type), # <--- 关键改动在这里
        property={}
    )

    if field_id:
        logging.info(f"🎉 字段创建成功！Field ID: {field_id}")
    else:
        logging.error("💀 字段创建失败。请检查上面的日志输出。")

if __name__ == "__main__":
    asyncio.run(main()) 