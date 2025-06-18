import logging
import hashlib
import hmac
from enum import Enum
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CIState(str, Enum):
    """CI状态枚举"""
    UNKNOWN = "Unknown"
    PENDING = "Pending"
    GREEN = "Green"  # 通过
    RED = "Red"  # 失败


class CIService:
    """CI服务接口"""
    
    def __init__(self):
        """初始化CI服务"""
        self.github_secret = None  # GitHub Webhook密钥
    
    def set_github_secret(self, secret: str):
        """设置GitHub Webhook密钥"""
        self.github_secret = secret
    
    def verify_github_signature(self, payload: bytes, signature: str) -> bool:
        """
        验证GitHub Webhook签名
        
        Args:
            payload: 请求体
            signature: GitHub提供的签名，格式为"sha256=xxx"
            
        Returns:
            是否验证通过
        """
        if not self.github_secret:
            logger.warning("GitHub Secret未设置，忽略签名验证")
            return True
        
        try:
            # 从签名头提取算法和签名
            algo, sig = signature.split("=", 1)
            
            # 计算HMAC
            if algo.lower() == "sha1":
                mac = hmac.new(
                    key=self.github_secret.encode(),
                    msg=payload,
                    digestmod=hashlib.sha1
                )
            elif algo.lower() == "sha256":
                mac = hmac.new(
                    key=self.github_secret.encode(),
                    msg=payload,
                    digestmod=hashlib.sha256
                )
            else:
                logger.error(f"不支持的签名算法: {algo}")
                return False
                
            computed_sig = mac.hexdigest()
            return hmac.compare_digest(computed_sig, sig)
            
        except Exception as e:
            logger.exception(f"验证GitHub签名异常: {str(e)}")
            return False
    
    def parse_github_status(self, payload: Dict[str, Any]) -> Optional[CIState]:
        """
        解析GitHub状态事件
        
        Args:
            payload: GitHub Webhook负载
            
        Returns:
            解析后的CI状态
        """
        try:
            event_type = payload.get("action")
            
            # 处理workflow_run事件
            if "workflow_run" in payload:
                status = payload["workflow_run"]["conclusion"]
                if status == "success":
                    return CIState.GREEN
                elif status in ("failure", "cancelled", "timed_out"):
                    return CIState.RED
                elif status in ("waiting", "queued", "in_progress"):
                    return CIState.PENDING
                    
            # 处理check_suite事件
            elif "check_suite" in payload:
                status = payload["check_suite"]["conclusion"]
                if status == "success":
                    return CIState.GREEN
                elif status in ("failure", "cancelled", "timed_out"):
                    return CIState.RED
                elif status in ("waiting", "queued", "in_progress"):
                    return CIState.PENDING
                    
            # 处理status事件
            elif event_type == "status":
                state = payload.get("state")
                if state == "success":
                    return CIState.GREEN
                elif state in ("failure", "error"):
                    return CIState.RED
                elif state == "pending":
                    return CIState.PENDING
            
            # 其他情况
            logger.warning(f"未知的GitHub事件或状态: {event_type}")
            return CIState.UNKNOWN
            
        except Exception as e:
            logger.exception(f"解析GitHub状态异常: {str(e)}")
            return None
    
    def extract_commit_info(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """
        提取提交信息
        
        Args:
            payload: GitHub Webhook负载
            
        Returns:
            提交相关信息，包括sha, message, url等
        """
        result = {
            "sha": "",
            "message": "",
            "url": "",
            "branch": "",
            "repo": ""
        }
        
        try:
            # 从不同类型的事件中提取信息
            if "repository" in payload:
                result["repo"] = payload["repository"].get("full_name", "")
            
            # workflow_run事件
            if "workflow_run" in payload:
                run = payload["workflow_run"]
                result["sha"] = run.get("head_sha", "")
                result["url"] = run.get("html_url", "")
                result["branch"] = run.get("head_branch", "")
                # 提交消息通常不在workflow_run中
                
            # check_suite事件
            elif "check_suite" in payload:
                suite = payload["check_suite"]
                result["sha"] = suite.get("head_sha", "")
                result["url"] = suite.get("html_url", "")
                result["branch"] = suite.get("head_branch", "")
                
            # status事件
            elif "status" in payload:
                result["sha"] = payload.get("sha", "")
                if "commit" in payload:
                    result["message"] = payload["commit"].get("message", "")
                    result["url"] = payload["commit"].get("html_url", "")
                
            # 从commits数组中提取
            if "commits" in payload and payload["commits"]:
                commit = payload["commits"][0]
                if not result["sha"]:
                    result["sha"] = commit.get("id", "")
                if not result["message"]:
                    result["message"] = commit.get("message", "")
                if not result["url"]:
                    result["url"] = commit.get("url", "")
                    
            return result
            
        except Exception as e:
            logger.exception(f"提取提交信息异常: {str(e)}")
            return result


# 全局CI服务实例
ci_service = CIService() 