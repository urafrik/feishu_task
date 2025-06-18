import logging
from typing import Dict, List, Any, Optional

from app.config import settings
from app.services.llm import llm_service
from app.bitable import BitableClient
from app.services.feishu import feishu_client

logger = logging.getLogger(__name__)

# 在服务内部创建依赖的实例
bitable_client = BitableClient(settings, feishu_client)

class MatchService:
    """任务-人员匹配服务"""
    
    def __init__(self):
        self.weights = settings.match.weights
    
    async def find_candidates_for_task(self, task_data: Dict[str, Any], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        为任务寻找最合适的候选人
        
        Args:
            task_data: 任务数据
            top_n: 返回前N个候选人
            
        Returns:
            候选人列表，按匹配度排序
        """
        # 1. 从多维表获取所有可用人员
        persons = await bitable_client.get_all_persons()
        if not persons:
            logger.warning("没有找到可用人员")
            return []
        
        # 2. 使用LLM进行匹配
        matched_candidates = await llm_service.match_candidates(task_data, persons)
        
        # 3. 返回前N个候选人
        return matched_candidates[:min(top_n, len(matched_candidates))]
    
    def create_candidate_card(self, task_id: str, candidates: List[Dict[str, Any]]) -> Dict:
        """
        创建候选人卡片
        
        Args:
            task_id: 任务ID
            candidates: 候选人列表
            
        Returns:
            飞书卡片配置
        """
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🔍 任务匹配结果"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**系统已为该任务推荐以下最佳人选：**"
                    }
                },
                {
                    "tag": "hr"
                }
            ]
        }
        
        # 为每个候选人添加信息块
        for idx, candidate in enumerate(candidates):
            match_score = candidate.get("match_score", 0)
            name = candidate.get("name", "未知人员")
            skill_tags = candidate.get("skill_tags", "")
            hours_available = candidate.get("hours_available", 0)
            performance = candidate.get("performance", 0)
            user_id = candidate.get("user_id", "")
            
            # 创建候选人信息块
            candidate_element = {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**#{idx+1} {name}**"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**匹配度：{match_score}%**"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"技能：{skill_tags}"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"可用时间：{hours_available}小时/周"
                        }
                    }
                ]
            }
            
            # 添加候选人区块
            card["elements"].append(candidate_element)
            
            # 添加选择按钮
            action_element = {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": f"✅ 选TA"
                        },
                        "type": "primary",
                        "value": {
                            "task_id": task_id,
                            "user_id": user_id,
                            "user_name": name,
                            "action": "select_candidate"
                        }
                    }
                ]
            }
            card["elements"].append(action_element)
            
            # 如果不是最后一个候选人，添加分割线
            if idx < len(candidates) - 1:
                card["elements"].append({"tag": "hr"})
        
        return card


# 全局匹配服务实例
match_service = MatchService() 