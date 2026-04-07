"""
增强配置管理
支持多环境配置、配置验证和敏感信息加密
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, SecretStr
from typing import Optional, List
from enum import Enum
import os


class Environment(str, Enum):
    """环境枚举"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class EnhancedSettings(BaseSettings):
    """增强配置类"""

    # ==================== 基础配置 ====================
    APP_NAME: str = Field(default="AI Traffic Booster", description="应用名称")
    APP_VERSION: str = Field(default="0.1.0", description="应用版本")
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT, description="运行环境")
    DEBUG: bool = Field(default=False, description="调试模式")

    # ==================== 服务配置 ====================
    HOST: str = Field(default="0.0.0.0", description="监听地址")
    PORT: int = Field(default=8008, ge=1, le=65535, description="监听端口")
    WORKERS: int = Field(default=1, ge=1, description="工作进程数")

    # ==================== 数据库配置 ====================
    DATABASE_URL: Optional[str] = Field(default=None, description="数据库连接 URL")
    DATABASE_POOL_SIZE: int = Field(default=10, ge=1, description="数据库连接池大小")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, ge=0, description="数据库连接池最大溢出数")
    REDIS_URL: Optional[str] = Field(default=None, description="Redis 连接 URL")

    # ==================== 安全配置 ====================
    SECRET_KEY: Optional[SecretStr] = Field(default=None, description="密钥")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, description="访问令牌过期时间（分钟）")
    CORS_ORIGINS: List[str] = Field(default=["*"], description="CORS 允许的来源")

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """验证密钥强度"""
        if v is None:
            return None
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError("SECRET_KEY 长度必须至少为 32 字符")
        return v

    # ==================== 日志配置 ====================
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FILE: Optional[str] = Field(default=None, description="日志文件路径")
    LOG_FORMAT: str = Field(default="json", description="日志格式 (json/text)")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL 必须是 {valid_levels} 之一")
        return v.upper()

    # ==================== 外部服务配置 ====================
    # OpenAI
    OPENAI_API_KEY: Optional[SecretStr] = Field(default=None, description="OpenAI API 密钥")
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI 模型")

    # Google API
    GOOGLE_SEARCH_API_KEY: Optional[SecretStr] = Field(default=None, description="Google Search API 密钥")
    GOOGLE_SEARCH_ENGINE_ID: Optional[str] = Field(default=None, description="Google Search 引擎 ID")
    GOOGLE_SERVICE_ACCOUNT_KEY_PATH: Optional[str] = Field(default=None, description="Google 服务账号密钥文件路径")
    GOOGLE_SEARCH_CONSOLE_SITE_URL: Optional[str] = Field(default=None, description="Google Search Console 网站 URL")
    GOOGLE_ADS_CREDENTIALS_PATH: Optional[str] = Field(default=None, description="Google Ads 凭证文件路径")
    GOOGLE_ADS_CUSTOMER_ID: Optional[str] = Field(default=None, description="Google Ads 客户 ID")
    GOOGLE_ADS_DEVELOPER_TOKEN: Optional[SecretStr] = Field(default=None, description="Google Ads 开发者令牌")

    # Ahrefs API
    AHREFS_API_KEY: Optional[SecretStr] = Field(default=None, description="Ahrefs API 密钥")

    # SEMrush API
    SEMRUSH_API_KEY: Optional[SecretStr] = Field(default=None, description="SEMrush API 密钥")

    # ==================== SEO 配置 ====================
    MIN_CONTENT_LENGTH: int = Field(default=300, ge=100, description="最小内容长度")
    MAX_CONTENT_LENGTH: int = Field(default=10000, ge=1000, description="最大内容长度")
    MIN_KEYWORD_DENSITY: float = Field(default=1.0, ge=0, le=10, description="最小关键词密度 (%)")
    MAX_KEYWORD_DENSITY: float = Field(default=5.0, ge=1, le=20, description="最大关键词密度 (%)")
    OPTIMAL_KEYWORD_DENSITY_MIN: float = Field(default=1.0, ge=0, le=5, description="最佳关键词密度最小值 (%)")
    OPTIMAL_KEYWORD_DENSITY_MAX: float = Field(default=3.0, ge=1, le=10, description="最佳关键词密度最大值 (%)")

    # ==================== A/B 测试配置 ====================
    DEFAULT_CONFIDENCE_LEVEL: float = Field(default=0.95, ge=0.8, le=0.99, description="默认置信水平")
    DEFAULT_MIN_SAMPLE_SIZE: int = Field(default=1000, ge=100, description="默认最小样本量")

    # ==================== 数据源配置 ====================
    DEFAULT_KEYWORD_SOURCE: str = Field(default="mock", description="默认关键词数据源")
    DEFAULT_COMPETITOR_SOURCE: str = Field(default="mock", description="默认竞品数据源")

    # ==================== 限流配置 ====================
    RATE_LIMIT_ENABLED: bool = Field(default=False, description="是否启用限流")
    RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1, description="限流请求数")
    RATE_LIMIT_WINDOW: int = Field(default=60, ge=1, description="限流时间窗口（秒）")

    # ==================== 缓存配置 ====================
    CACHE_ENABLED: bool = Field(default=False, description="是否启用缓存")
    CACHE_TTL: int = Field(default=3600, ge=60, description="缓存过期时间（秒）")

    # ==================== 监控配置 ====================
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN")
    METRICS_ENABLED: bool = Field(default=False, description="是否启用指标收集")

    # ==================== 模型配置 ====================
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.ENVIRONMENT == Environment.TESTING

    def get_secret_value(self, secret: Optional[SecretStr]) -> Optional[str]:
        """安全获取密钥值"""
        if secret is None:
            return None
        return secret.get_secret_value()


# 全局配置实例
enhanced_settings = EnhancedSettings()


def get_settings() -> EnhancedSettings:
    """获取配置实例"""
    return enhanced_settings


def validate_settings() -> bool:
    """
    验证配置是否合法

    Returns:
        bool: 验证是否通过
    """
    try:
        # 生产环境必须有 SECRET_KEY
        if enhanced_settings.is_production() and not enhanced_settings.SECRET_KEY:
            raise ValueError("生产环境必须设置 SECRET_KEY")

        # 生产环境必须关闭 DEBUG
        if enhanced_settings.is_production() and enhanced_settings.DEBUG:
            raise ValueError("生产环境必须关闭 DEBUG 模式")

        return True
    except Exception as e:
        print(f"配置验证失败：{e}")
        return False
