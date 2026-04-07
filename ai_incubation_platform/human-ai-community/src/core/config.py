"""
配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    # 服务配置
    service_name: str = "human-ai-community"
    environment: str = "development"
    debug: bool = True
    port: int = 8007

    # 数据库配置 - 支持直接传入 DATABASE_URL 或使用分项配置
    database_url: Optional[str] = None  # 直接指定数据库 URL（优先使用）
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "human_ai_community"
    db_echo: bool = False  # 是否打印 SQL 语句

    # 统一账号体系配置
    unified_auth_url: str = "http://account.example.com/api"
    unified_auth_app_id: str = "community-app"
    unified_auth_app_secret: str = "your-secret-key"

    # JWT 配置
    jwt_secret: str = "your-jwt-secret-key"
    jwt_expire_hours: int = 24

    # Redis 配置（可选，用于缓存和速率限制）
    redis_host: Optional[str] = None
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    @property
    def effective_database_url(self) -> str:
        """获取有效的数据库连接 URL"""
        # 优先使用直接指定的 DATABASE_URL
        if self.database_url:
            return self.database_url
        # 否则使用 PostgreSQL 连接
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()
