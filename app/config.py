import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseModel):
    name: str = "Feishu Task Bot"
    version: str = "0.1.0"

class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: str = "info"
    public_url: Optional[str] = None

class FeishuSettings(BaseModel):
    app_id: str
    app_secret: str
    verification_token: Optional[str] = None
    encrypt_key: Optional[str] = None

class BitableSettings(BaseModel):
    app_token: str
    task_table_id: str
    person_table_id: str

class GithubSettings(BaseModel):
    webhook_secret: Optional[str] = None

class LLMProviderSettings(BaseModel):
    api_key: Optional[str] = None
    model: str
    base_url: Optional[str] = None

class LLMSettings(BaseModel):
    default_provider: str
    providers: Dict[str, LLMProviderSettings]

class MatchSettings(BaseSettings):
    weights: Dict[str, float] = Field(default_factory=lambda: {
        "skill": 0.6, "availability": 0.2, "performance": 0.1, "recency": 0.1
    })

class CISettings(BaseSettings):
    enabled: bool = False
    webhook_secret: Optional[str] = None

class LoggingSettings(BaseSettings):
    level: str = "INFO"
    rotation: str = "10 MB"
    retention: str = "7 days"

class Settings(BaseSettings):
    """
    主设置类，合并YAML和环境变量。
    """
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore'
    )

    app: AppSettings = Field(default_factory=AppSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    feishu: FeishuSettings
    bitable: BitableSettings
    github: GithubSettings = Field(default_factory=GithubSettings)
    llm: LLMSettings
    match: MatchSettings = Field(default_factory=MatchSettings)
    ci: CISettings = Field(default_factory=CISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

# 创建一个全局的设置实例，供其他模块导入
settings = Settings() 