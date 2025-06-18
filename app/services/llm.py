import json
import logging
import os
from typing import Dict, List, Any, Optional, Literal

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

class LLMProvider:
    """LLM提供商基类"""
    
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
    
    async def generate(self, prompt: str, system: str = None, temperature: float = 0.7) -> Optional[str]:
        """生成文本方法，需由子类实现"""
        raise NotImplementedError("子类必须实现generate方法")
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Optional[str]:
        """聊天方法，需由子类实现"""
        raise NotImplementedError("子类必须实现chat方法")
    
    async def parse_json(self, prompt: str, system: str = None) -> Optional[Dict]:
        """解析JSON，自动重试"""
        try:
            # 添加明确要求返回JSON的提示
            if system:
                system = f"{system}\n请返回有效的JSON格式数据。"
            else:
                system = "请返回有效的JSON格式数据。"
            
            result = await self.generate(prompt, system, temperature=0.1)
            
            if not result:
                return None
                
            # 提取JSON部分
            result = result.strip()
            if result.startswith("```json"):
                result = result.split("```json")[1]
                if "```" in result:
                    result = result.split("```")[0]
            elif result.startswith("```"):
                result = result.split("```")[1]
                if "```" in result:
                    result = result.split("```")[0]
            
            return json.loads(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}, 原文: {result}")
            # 可以添加重试逻辑
            return None
        except Exception as e:
            logger.exception(f"解析JSON异常: {str(e)}")
            return None


class DeepseekProvider(LLMProvider):
    """DeepSeek提供商实现"""
    
    async def generate(self, prompt: str, system: str = None, temperature: float = 0.7) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                data = {
                    "model": self.model_name,
                    "temperature": temperature,
                    "messages": []
                }
                
                # 添加系统消息
                if system:
                    data["messages"].append({"role": "system", "content": system})
                
                # 添加用户消息
                data["messages"].append({"role": "user", "content": prompt})
                
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                content = result.get("choices", [{}])[0].get("message", {}).get("content")
                return content
                
        except Exception as e:
            logger.exception(f"DeepSeek API调用异常: {str(e)}")
            return None
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                data = {
                    "model": self.model_name,
                    "temperature": temperature,
                    "messages": messages
                }
                
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                content = result.get("choices", [{}])[0].get("message", {}).get("content")
                return content
                
        except Exception as e:
            logger.exception(f"DeepSeek API调用异常: {str(e)}")
            return None


class GeminiProvider(LLMProvider):
    """Gemini提供商实现"""
    
    async def generate(self, prompt: str, system: str = None, temperature: float = 0.7) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json"
                }
                
                # 构建消息
                messages = []
                if system:
                    messages.append({
                        "role": "system",
                        "parts": [{"text": system}]
                    })
                
                messages.append({
                    "role": "user",
                    "parts": [{"text": prompt}]
                })
                
                data = {
                    "contents": messages,
                    "generationConfig": {
                        "temperature": temperature
                    }
                }
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
                response = await client.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # 提取文本内容
                content = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return content
                
        except Exception as e:
            logger.exception(f"Gemini API调用异常: {str(e)}")
            return None
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Optional[str]:
        try:
            # 将标准消息格式转换为Gemini格式
            gemini_messages = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                
                # Gemini使用不同的角色命名
                if role == "system":
                    role = "system"  # Gemini Beta现在支持system
                elif role == "user":
                    role = "user"
                elif role == "assistant":
                    role = "model"
                
                gemini_messages.append({
                    "role": role,
                    "parts": [{"text": content}]
                })
            
            async with httpx.AsyncClient() as client:
                data = {
                    "contents": gemini_messages,
                    "generationConfig": {
                        "temperature": temperature
                    }
                }
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
                response = await client.post(
                    url,
                    json=data,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # 提取文本内容
                content = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return content
                
        except Exception as e:
            logger.exception(f"Gemini API调用异常: {str(e)}")
            return None


class OpenAIProvider(LLMProvider):
    """OpenAI提供商实现"""
    
    async def generate(self, prompt: str, system: str = None, temperature: float = 0.7) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                
                messages.append({"role": "user", "content": prompt})
                
                data = {
                    "model": self.model_name,
                    "temperature": temperature,
                    "messages": messages
                }
                
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                content = result.get("choices", [{}])[0].get("message", {}).get("content")
                return content
                
        except Exception as e:
            logger.exception(f"OpenAI API调用异常: {str(e)}")
            return None
    
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                data = {
                    "model": self.model_name,
                    "temperature": temperature,
                    "messages": messages
                }
                
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                content = result.get("choices", [{}])[0].get("message", {}).get("content")
                return content
                
        except Exception as e:
            logger.exception(f"OpenAI API调用异常: {str(e)}")
            return None


class LLMService:
    """LLM服务，管理多个提供商和提示"""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.prompts: Dict[str, Dict[str, str]] = {}
        self._load_providers()
        self._load_prompt_templates()

    def _load_providers(self):
        """从配置加载并初始化所有LLM提供商"""
        provider_factories = {
            "deepseek": DeepseekProvider,
            "gemini": GeminiProvider,
            "openai": OpenAIProvider,
        }
        
        for name, provider_config in settings.llm.providers.items():
            if name in provider_factories:
                api_key = provider_config.api_key
                model = provider_config.model
                
                if not api_key:
                    logger.warning(f"提供商 '{name}' 的 API key 未配置，已跳过加载。")
                    continue

                self.providers[name] = provider_factories[name](api_key, model)
                logger.info(f"成功加载LLM提供商: {name}")

    def _load_prompt_templates(self):
        """加载提示词模板"""
        self.prompts = {
            "match": {
                "system": "你是智能人才匹配助手，根据任务需求和人员技能进行最佳匹配。",
                "user": "任务需求: {skill_tags}, 截止: {deadline}, 描述: {description}\n"
                        "候选人列表:\n{candidates}"
            },
            "evaluate": {
                "system": "你是质量评审助手，根据任务验收标准对提交结果进行评分。",
                "user": "任务说明 = «{description}»\n"
                        "验收标准 = «{acceptance}»\n"
                        "提交链接 = {url}"
            }
        }
    
    def get_provider(self, provider_name: Optional[str] = None) -> Optional[LLMProvider]:
        """获取指定的LLM提供商，默认返回默认提供商"""
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name]
        return None
    
    def get_prompt(self, template_name: str, **kwargs) -> Dict[str, str]:
        """获取格式化后的提示词模板"""
        if template_name not in self.prompts:
            raise ValueError(f"未找到提示词模板: {template_name}")
            
        template = self.prompts[template_name]
        
        # 格式化模板
        system = template.get("system", "")
        user = template.get("user", "").format(**kwargs)
        
        return {
            "system": system,
            "user": user
        }
    
    async def match_candidates(self, task_data: Dict[str, Any], 
                             candidates: List[Dict[str, Any]], 
                             provider_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        匹配最佳候选人
        
        Args:
            task_data: 任务数据
            candidates: 候选人列表
            provider_name: LLM提供商名称，可选
            
        Returns:
            匹配的候选人列表，按匹配分数排序
        """
        provider = self.get_provider(provider_name)
        if not provider:
            logger.error("没有可用的LLM提供商")
            return []
        
        # 格式化候选人列表
        candidates_text = "\n".join([
            f"{i+1}) {json.dumps(p, ensure_ascii=False)}"
            for i, p in enumerate(candidates)
        ])
        
        # 获取提示词
        prompt = self.get_prompt(
            "match",
            skill_tags=task_data.get("skill_tags", ""),
            deadline=task_data.get("deadline", "尽快"),
            description=task_data.get("desc", task_data.get("description", "")),
            candidates=candidates_text
        )
        
        # 调用LLM
        result = await provider.parse_json(prompt["user"], prompt["system"])
        
        if not result:
            logger.error("LLM返回结果解析失败")
            return []
        
        # 处理结果
        matches = []
        if isinstance(result, list):
            # 可能直接返回列表
            for item in result:
                if isinstance(item, dict) and "user_id" in item:
                    matches.append(item)
        elif isinstance(result, dict):
            # 可能返回包含列表的对象
            if "matches" in result and isinstance(result["matches"], list):
                matches = result["matches"]
            elif "top3" in result and isinstance(result["top3"], list):
                matches = result["top3"]
        
        # 找出对应的候选人信息
        matched_candidates = []
        for match in matches:
            user_id = match.get("user_id")
            match_score = match.get("matchScore", match.get("score", 0))
            
            for candidate in candidates:
                if candidate.get("user_id") == user_id:
                    # 复制候选人信息并添加匹配分数
                    matched_candidate = candidate.copy()
                    matched_candidate["match_score"] = match_score
                    matched_candidates.append(matched_candidate)
                    break
        
        # 按匹配分数降序排序
        matched_candidates.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return matched_candidates
    
    async def evaluate_submission(self, task_data: Dict[str, Any], 
                                submission_url: str,
                                provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        评估任务提交
        
        Args:
            task_data: 任务数据
            submission_url: 提交链接
            provider_name: LLM提供商名称，可选
            
        Returns:
            评估结果，包含分数和失败原因
        """
        provider = self.get_provider(provider_name)
        if not provider:
            logger.error("没有可用的LLM提供商")
            return {"score": 0, "failedReasons": ["无法连接评估模型"]}
        
        # 获取提示词
        prompt = self.get_prompt(
            "evaluate",
            description=task_data.get("desc", task_data.get("description", "")),
            acceptance=task_data.get("acceptance_criteria", "按时完成，功能正确"),
            url=submission_url
        )
        
        # 调用LLM
        result = await provider.parse_json(prompt["user"], prompt["system"])
        
        if not result:
            logger.error("LLM返回评估结果解析失败")
            return {"score": 0, "failedReasons": ["评估结果解析失败"]}
        
        # 标准化结果
        score = result.get("score", 0)
        failed_reasons = result.get("failedReasons", result.get("reasons", []))
        
        return {
            "score": score,
            "failedReasons": failed_reasons
        }


# 全局LLM服务实例
llm_service = LLMService() 