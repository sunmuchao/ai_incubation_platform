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

# 加载.env 文件（从项目根目录加载）
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_base_dir, '.env'))


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

    # LLM 配置（核心 AI 引擎，默认启用）
    llm_enabled: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    llm_provider: str = os.getenv("LLM_PROVIDER", "qwen")  # qwen, glm, openai
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_api_base: str = os.getenv("LLM_API_BASE", "https://dashscope.aliyun.com/compatible-mode/v1")
    llm_model: str = os.getenv("LLM_MODEL", "qwen-plus")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1000"))
    llm_request_timeout: int = int(os.getenv("LLM_REQUEST_TIMEOUT", "30"))
    llm_retry_count: int = int(os.getenv("LLM_RETRY_COUNT", "3"))
    llm_confidence_threshold: float = float(os.getenv("LLM_CONFIDENCE_THRESHOLD", "0.6"))  # 置信度阈值

    # LLM 降级方案配置
    llm_fallback_enabled: bool = os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"
    llm_fallback_mode: str = os.getenv("LLM_FALLBACK_MODE", "local")  # local（本地规则）/ mock（模拟数据）
    llm_cache_enabled: bool = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"

    # 外部 API 配置 - 高德地图（用于地理编码、距离计算、地点搜索）
    amap_api_key: str = os.getenv("AMAP_API_KEY", "")
    amap_api_secret: str = os.getenv("AMAP_API_SECRET", "")
    amap_enabled: bool = os.getenv("AMAP_ENABLED", "false").lower() == "true"

    # 外部 API 配置 - 天气服务（用于穿搭推荐、约会建议）
    weather_provider: str = os.getenv("WEATHER_PROVIDER", "qweather")  # qweather, openweathermap, mock
    openweathermap_api_key: str = os.getenv("OPENWEATHERMAP_API_KEY", "")
    qweather_api_key: str = os.getenv("QWEATHER_API_KEY", "")

    # 外部 API 配置 - 预订服务（用于约会策划）
    reservation_restaurant_provider: str = os.getenv("RESERVATION_RESTAURANT_PROVIDER", "dianping")
    reservation_cinema_provider: str = os.getenv("RESERVATION_CINEMA_PROVIDER", "maoyan")
    dianping_api_key: str = os.getenv("DIANPING_API_KEY", "")
    dianping_api_secret: str = os.getenv("DIANPING_API_SECRET", "")
    maoyan_api_key: str = os.getenv("MAOYAN_API_KEY", "")

    # 外部 API 配置 - 极光推送（用于移动端推送通知）
    jpush_app_key: str = os.getenv("JPUSH_APP_KEY", "")
    jpush_master_secret: str = os.getenv("JPUSH_MASTER_SECRET", "")
    jpush_enabled: bool = os.getenv("JPUSH_ENABLED", "false").lower() == "true"

    # 外部 API 配置 - 短信服务（用于手机号登录、验证码）
    sms_enabled: bool = os.getenv("ALIYUN_SMS_ENABLED", "false").lower() == "true"
    aliyun_sms_enabled: bool = os.getenv("ALIYUN_SMS_ENABLED", "false").lower() == "true"
    aliyun_sms_access_key_id: str = os.getenv("ALIYUN_SMS_ACCESS_KEY_ID", "")
    aliyun_sms_access_key_secret: str = os.getenv("ALIYUN_SMS_ACCESS_KEY_SECRET", "")
    aliyun_sms_sign_name: str = os.getenv("ALIYUN_SMS_SIGN_NAME", "")
    aliyun_sms_template_code: str = os.getenv("ALIYUN_SMS_TEMPLATE_CODE", "")

    # 外部 API 配置 - 支付
    wechat_pay_enabled: bool = os.getenv("WECHAT_PAY_ENABLED", "false").lower() == "true"
    wechat_pay_appid: str = os.getenv("WECHAT_PAY_APPID", "")
    wechat_pay_mchid: str = os.getenv("WECHAT_PAY_MCHID", "")
    wechat_pay_api_v3_key: str = os.getenv("WECHAT_PAY_API_V3_KEY", "")
    alipay_enabled: bool = os.getenv("ALIPAY_ENABLED", "false").lower() == "true"
    alipay_app_id: str = os.getenv("ALIPAY_APP_ID", "")
    alipay_private_key: str = os.getenv("ALIPAY_PRIVATE_KEY", "")
    alipay_public_key: str = os.getenv("ALIPAY_PUBLIC_KEY", "")

    # JWT 配置
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    jwt_refresh_expire_days: int = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))

    # 数据库配置
    # 生产环境推荐使用 PostgreSQL，开发环境可使用 SQLite
    # 数据库 URL 格式：
    #   PostgreSQL: postgresql://user:password@host:port/database
    #   SQLite: sqlite:///./path/to/database.db
    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    database_url: str = os.getenv(
        "DATABASE_URL",
        # 开发环境默认使用 SQLite，生产环境应设置 DATABASE_URL 环境变量
        f"sqlite:///{os.path.join(_base_dir, 'matchmaker.db')}"
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

    # 日志清理配置（系统重启时自动清理）
    log_cleaner_enabled: bool = os.getenv("LOG_CLEANER_ENABLED", "true").lower() == "true"
    log_cleaner_max_age_days: int = int(os.getenv("LOG_CLEANER_MAX_AGE_DAYS", "7"))
    log_cleaner_max_size_mb: int = int(os.getenv("LOG_CLEANER_MAX_SIZE_MB", "50"))
    log_cleaner_max_files: int = int(os.getenv("LOG_CLEANER_MAX_FILES", "20"))

    # 日志备份配置（系统重启时自动备份）
    log_backup_keep_count: int = int(os.getenv("LOG_BACKUP_KEEP_COUNT", "10"))

    # 管理员配置
    admin_emails: List[str] = [
        e.strip()
        for e in os.getenv("ADMIN_EMAILS", "admin@example.com").split(",")
        if e.strip()
    ]

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
# 生产环境强制关闭 DEBUG 模式
if settings.environment == "production" and settings.debug:
    raise ValueError("DEBUG mode must be disabled in production environment for security. Set DEBUG=false")

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

# LLM 配置验证
if settings.llm_enabled and not settings.llm_api_key:
    if settings.environment == "production":
        raise ValueError("LLM_API_KEY must be set when LLM is enabled in production environment")
    else:
        warnings.warn(
            f"LLM is enabled but LLM_API_KEY is not set. LLM features will use fallback mode (rules/mock). "
            f"Current provider: {settings.llm_provider}, model: {settings.llm_model}. "
            f"Get API key from provider dashboard or set LLM_ENABLED=false to disable."
        )

# 数据库配置验证
if settings.environment == "production":
    # 生产环境建议使用 PostgreSQL 而非 SQLite
    if "sqlite" in settings.database_url:
        warnings.warn(
            "Production environment is using SQLite. For production workloads, PostgreSQL is strongly recommended. "
            "SQLite does not support concurrent writes and may cause locking issues under high traffic. "
            "Set DATABASE_URL=postgresql://user:password@host:port/database for production. "
            "See .env.example for PostgreSQL setup instructions."
        )
    # 生产环境必须配置 Redis
    if not settings.redis_url:
        warnings.warn(
            "Redis is not configured for production environment. Redis is recommended for caching and session management. "
            "Set REDIS_URL environment variable (e.g., redis://localhost:6379/0). "
            "Without Redis, the application will use in-memory caching which is not shared across instances."
        )

# 外部服务密钥验证（生产环境）
if settings.environment == "production":
    # 高德地图验证
    if settings.amap_enabled and not settings.amap_api_key:
        raise ValueError("AMAP_API_KEY must be set when AMAP_ENABLED=true in production environment")
    # 天气服务验证
    if settings.weather_provider != "mock" and not settings.qweather_api_key and not settings.openweathermap_api_key:
        warnings.warn(
            f"Weather provider is set to '{settings.weather_provider}' but no API key is configured. "
            f"Set QWEATHER_API_KEY or OPENWEATHERMAP_API_KEY, or use WEATHER_PROVIDER=mock for testing."
        )
    # 推送服务验证
    if settings.jpush_enabled and (not settings.jpush_app_key or not settings.jpush_master_secret):
        raise ValueError("JPUSH_APP_KEY and JPUSH_MASTER_SECRET must be set when JPUSH_ENABLED=true in production environment")

if settings.environment == "production":
    if not settings.cors_allowed_origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must be set in production environment (comma-separated)")
    if "*" in settings.cors_allowed_origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must not include '*' in production environment")
