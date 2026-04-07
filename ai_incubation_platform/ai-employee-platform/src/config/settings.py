"""
应用配置管理
统一管理所有配置项
"""
import os
import secrets
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# 加载.env 文件
load_dotenv()


class Settings(BaseModel):
    """应用配置"""

    # ==================== 应用基础配置 ====================
    app_name: str = Field(default="AI Employee Platform", description="应用名称")
    app_version: str = Field(default="0.7.0", description="应用版本")  # P6 阶段版本
    debug: bool = Field(default=False, description="调试模式")
    environment: str = Field(default="development", description="运行环境：development/staging/production")

    # 服务配置
    host: str = Field(default="0.0.0.0", description="监听主机")
    port: int = Field(default=8003, description="监听端口")

    # ==================== JWT 配置 (安全增强) ====================
    jwt_secret: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET", ""),
        description="JWT 密钥 (必须通过环境变量 JWT_SECRET 设置，长度 >= 32)"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT 算法")
    jwt_access_token_expire_minutes: int = Field(default=60, description="Access Token 过期时间（分钟）")
    jwt_refresh_token_expire_days: int = Field(default=7, description="Refresh Token 过期时间（天）")

    # ==================== 加密配置 ====================
    encryption_key: str = Field(
        default_factory=lambda: os.getenv("ENCRYPTION_KEY", ""),
        description="敏感数据加密密钥 (Fernet 密钥，32 字节 URL-safe base64 编码)"
    )

    # ==================== 数据库配置 ====================
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./ai_employee_platform.db"),
        description="数据库 URL (必须通过环境变量 DATABASE_URL 设置)"
    )

    # Redis 配置（可选）
    redis_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("REDIS_URL"),
        description="Redis URL"
    )

    # ==================== 密码加密配置 ====================
    bcrypt_rounds: int = Field(default=12, description="bcrypt 加密轮数")

    # ==================== 平台配置 ====================
    platform_fee_rate: float = Field(default=0.1, description="平台费率（10%）")

    # ==================== 风控配置 ====================
    max_order_duration_hours: int = Field(default=168, description="最大订单时长（小时）")
    max_hourly_rate: float = Field(default=1000.0, description="最大小时费率")
    risk_score_block_threshold: float = Field(default=80.0, description="风险评分封禁阈值")
    risk_score_high_threshold: float = Field(default=50.0, description="风险评分高风险阈值")
    risk_score_medium_threshold: float = Field(default=30.0, description="风险评分中风险阈值")

    # ==================== 限额配置 ====================
    default_trial_days: int = Field(default=14, description="默认试用期天数")
    default_max_employees: int = Field(default=10, description="默认最大员工数")
    default_max_concurrent_jobs: int = Field(default=5, description="默认最大并发任务数")
    default_storage_quota_gb: int = Field(default=10, description="默认存储配额 GB")

    # ==================== 账单配置 ====================
    invoice_due_days: int = Field(default=30, description="账单到期天数")

    # ==================== DeerFlow 配置 ====================
    deerflow_gateway_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("DEERFLOW_GATEWAY_URL"),
        description="DeerFlow 网关 URL"
    )
    deerflow_available: bool = Field(default=False, description="DeerFlow 是否可用")

    # ==================== 日志配置 ====================
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )

    # ==================== 安全配置 (增强) ====================
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="CORS 允许的来源列表"
    )
    allow_force_https_redirect: bool = Field(
        default=True,
        description="是否强制 HTTPS 重定向（生产环境应为 True）"
    )

    # ==================== 支付配置 ====================
    alipay_app_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("ALIPAY_APP_ID"),
        description="支付宝 App ID"
    )
    alipay_private_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("ALIPAY_PRIVATE_KEY"),
        description="支付宝应用私钥"
    )
    alipay_public_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("ALIPAY_PUBLIC_KEY"),
        description="支付宝公钥"
    )
    alipay_notify_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("ALIPAY_NOTIFY_URL"),
        description="支付宝异步通知 URL"
    )

    wechat_pay_mch_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("WECHAT_PAY_MCH_ID"),
        description="微信支付商户号"
    )
    wechat_pay_app_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("WECHAT_PAY_APP_ID"),
        description="微信支付 App ID"
    )
    wechat_pay_api_v3_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("WECHAT_PAY_API_V3_KEY"),
        description="微信支付 API v3 密钥"
    )
    wechat_pay_private_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("WECHAT_PAY_PRIVATE_KEY"),
        description="微信支付商户私钥"
    )
    wechat_pay_serial_number: Optional[str] = Field(
        default_factory=lambda: os.getenv("WECHAT_PAY_SERIAL_NUMBER"),
        description="微信支付商户证书序列号"
    )
    wechat_pay_notify_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("WECHAT_PAY_NOTIFY_URL"),
        description="微信支付异步通知 URL"
    )

    stripe_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("STRIPE_API_KEY"),
        description="Stripe API 密钥"
    )
    stripe_webhook_secret: Optional[str] = Field(
        default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET"),
        description="Stripe Webhook 密钥"
    )
    stripe_notify_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("STRIPE_NOTIFY_URL"),
        description="Stripe 异步通知 URL"
    )

    # ==================== 通知配置 ====================
    sendgrid_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("SENDGRID_API_KEY"),
        description="SendGrid API 密钥"
    )
    sendgrid_from_email: Optional[str] = Field(
        default_factory=lambda: os.getenv("SENDGRID_FROM_EMAIL"),
        description="SendGrid 发件人邮箱"
    )

    aliyun_sms_access_key_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("ALIYUN_SMS_ACCESS_KEY_ID"),
        description="阿里云短信 Access Key ID"
    )
    aliyun_sms_access_key_secret: Optional[str] = Field(
        default_factory=lambda: os.getenv("ALIYUN_SMS_ACCESS_KEY_SECRET"),
        description="阿里云短信 Access Key Secret"
    )
    aliyun_sms_sign_name: Optional[str] = Field(
        default_factory=lambda: os.getenv("ALIYUN_SMS_SIGN_NAME"),
        description="阿里云短信签名"
    )
    aliyun_sms_template_code: Optional[str] = Field(
        default_factory=lambda: os.getenv("ALIYUN_SMS_TEMPLATE_CODE"),
        description="阿里云短信模板代码"
    )

    class Config:
        env_prefix = ""
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

    # ==================== 验证器 ====================
    @validator("jwt_secret")
    def validate_jwt_secret(cls, v):
        """验证 JWT 密钥"""
        if not v:
            raise ValueError("JWT_SECRET 必须通过环境变量设置")
        if len(v) < 32:
            raise ValueError("JWT_SECRET 长度必须 >= 32")
        if v == "ai-employee-platform-secret-key-change-in-production":
            raise ValueError("必须修改默认 JWT 密钥")
        return v

    @validator("database_url")
    def validate_database_url(cls, v):
        """验证数据库 URL"""
        if not v:
            raise ValueError("DATABASE_URL 必须通过环境变量设置")
        return v

    @validator("cors_origins")
    def validate_cors_origins(cls, v):
        """验证 CORS 配置"""
        if "*" in v and len(v) > 1:
            raise ValueError("CORS 配置不能同时包含 '*' 和其他域名")
        # 生产环境不允许使用 *
        if os.getenv("ENVIRONMENT") == "production" and "*" in v:
            raise ValueError("生产环境 CORS 不允许使用 '*'")
        return v

    @validator("environment")
    def validate_environment(cls, v):
        """验证运行环境"""
        if v not in ["development", "staging", "production"]:
            raise ValueError("ENVIRONMENT 必须是 development/staging/production 之一")
        return v

    def is_production(self) -> bool:
        """是否生产环境"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """是否开发环境"""
        return self.environment == "development"

    def generate_encryption_key(self) -> str:
        """生成 Fernet 加密密钥"""
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()


# ==================== 配置加载 ====================
def load_settings() -> Settings:
    """
    加载配置并验证
    """
    # 从环境变量加载
    settings = Settings()

    # 如果加密密钥为空，生成一个（仅开发环境）
    if not settings.encryption_key and settings.is_development():
        # 注意：生产环境必须手动设置 ENCRYPTION_KEY
        pass

    return settings


# 全局配置实例
try:
    settings = load_settings()
except ValueError as e:
    # 配置验证失败时，如果是开发环境，尝试使用默认配置
    import sys
    if os.getenv("ENVIRONMENT") == "development" or "--allow-dev-defaults" in sys.argv:
        # 开发环境允许使用默认配置
        class DevSettings(Settings):
            jwt_secret: str = Field(
                default_factory=lambda: os.getenv("JWT_SECRET", "dev-secret-key-" + secrets.token_hex(16)),
                description="JWT 密钥"
            )
            database_url: str = Field(
                default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./ai_employee_platform_dev.db"),
                description="数据库 URL"
            )
        settings = DevSettings()
    else:
        print(f"\n❌ 配置验证失败：{e}")
        print("\n请设置以下环境变量:")
        print("  - JWT_SECRET (长度 >= 32)")
        print("  - DATABASE_URL")
        print("\n或使用 --allow-dev-defaults 启动开发环境")
        sys.exit(1)


def get_settings() -> Settings:
    """获取配置实例"""
    return settings
