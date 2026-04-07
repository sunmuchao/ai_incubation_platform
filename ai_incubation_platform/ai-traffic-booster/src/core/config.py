"""
配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    # 基础配置
    APP_NAME: str = "AI Traffic Booster"
    APP_VERSION: str = "v2.2"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8008
    WORKERS: int = 1

    # 数据库配置
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: list[str] = ["*"]

    # 外部服务配置
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_ENGINE_ID: Optional[str] = None

    # SEO配置
    MIN_CONTENT_LENGTH: int = 300
    MAX_CONTENT_LENGTH: int = 10000
    MIN_KEYWORD_DENSITY: float = 1.0
    MAX_KEYWORD_DENSITY: float = 5.0
    OPTIMAL_KEYWORD_DENSITY_MIN: float = 1.0
    OPTIMAL_KEYWORD_DENSITY_MAX: float = 3.0

    # A/B测试配置
    DEFAULT_CONFIDENCE_LEVEL: float = 0.95
    DEFAULT_MIN_SAMPLE_SIZE: int = 1000

    # 数据源配置
    DEFAULT_KEYWORD_SOURCE: str = "mock"
    DEFAULT_COMPETITOR_SOURCE: str = "mock"

    # Google API 配置
    GOOGLE_SERVICE_ACCOUNT_KEY_PATH: Optional[str] = None
    GOOGLE_SEARCH_CONSOLE_SITE_URL: Optional[str] = None
    GOOGLE_ADS_CREDENTIALS_PATH: Optional[str] = None
    GOOGLE_ADS_CUSTOMER_ID: Optional[str] = None
    GOOGLE_ADS_DEVELOPER_TOKEN: Optional[str] = None

    # Ahrefs API 配置
    AHREFS_API_KEY: Optional[str] = None

    # SEMrush API 配置
    SEMRUSH_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings
