"""
统一配置管理模块
所有配置从环境变量读取，支持.env 文件
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from dotenv import load_dotenv
import secrets
import warnings

# 加载.env 文件
load_dotenv()


class Settings(BaseSettings):
    """应用配置"""

    # 服务配置
    app_version: str = "0.5.0"
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", os.getenv("PORT", "8007")))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # 孵化器门户集成配置
    portal_enabled: bool = os.getenv("PORTAL_ENABLED", "false").lower() == "true"
    portal_api_url: str = os.getenv("PORTAL_API_URL", "")
    portal_api_key: str = os.getenv("PORTAL_API_KEY", "")
    portal_jwt_secret: str = os.getenv("PORTAL_JWT_SECRET", "")

    # LLM 配置
    llm_enabled: bool = os.getenv("LLM_ENABLED", "false").lower() == "true"
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")  # openai, qwen, glm
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_api_base: str = os.getenv("LLM_API_BASE", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "500"))

    # JWT 配置
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    jwt_refresh_expire_days: int = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))

    # 数据库配置
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./matchmaker_agent.db"
    )
    # 数据库连接池配置（生产环境优化）
    database_pool_size: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    database_max_overflow: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
    database_pool_timeout: int = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
    database_pool_recycle: int = int(os.getenv("DATABASE_POOL_RECYCLE", "1800"))

    # Redis 配置（缓存和会话管理）
    redis_url: Optional[str] = os.getenv("REDIS_URL")

    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "text")

    # 敏感字段脱敏配置
    sensitive_fields: list = [
        "password", "password_hash", "token", "secret", "key",
        "email", "phone", "id_card", "bank_card", "location"
    ]

    # CORS 配置
    # 生产环境禁止使用 "*"，必须在 CORS_ALLOWED_ORIGINS 中显式配置可信域名列表（逗号分隔）。
    cors_allowed_origins: List[str] = [
        o.strip()
        for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()

# 配置验证
if not settings.jwt_secret_key or len(settings.jwt_secret_key) < 32:
    if settings.environment == "production":
        raise ValueError(
            "JWT_SECRET_KEY must be set in production environment "
            "and be at least 32 characters long"
        )
    else:
        # 非生产环境：避免使用已知固定默认密钥，改为启动期临时密钥
        settings.jwt_secret_key = secrets.token_urlsafe(32)
        warnings.warn(
            "JWT_SECRET_KEY is missing or too short; generated a temporary in-memory secret for non-production. "
            "Set JWT_SECRET_KEY environment variable with a strong secret for any real deployment."
        )

if settings.environment == "production":
    if not settings.cors_allowed_origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must be set in production environment (comma-separated)")
    if "*" in settings.cors_allowed_origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must not include '*' in production environment")
