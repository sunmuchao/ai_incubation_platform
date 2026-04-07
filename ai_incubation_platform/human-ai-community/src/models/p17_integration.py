"""
P17 跨平台集成 - 数据模型

包含：
- 邮件通知配置
- 短信通知配置
- OAuth 提供商配置
- SSO 配置
- 社交分享配置
- 跨平台身份映射
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ==================== 枚举类型 ====================

class OAuthProvider(str, Enum):
    """OAuth 提供商"""
    GOOGLE = "google"
    GITHUB = "github"
    WECHAT = "wechat"
    WEIBO = "weibo"
    DISCORD = "discord"
    SLACK = "slack"
    CUSTOM = "custom"


class SSOProtocol(str, Enum):
    """SSO 协议类型"""
    SAML2 = "saml2"
    OIDC = "oidc"
    CAS = "cas"
    LDAP = "ldap"


class IntegrationStatus(str, Enum):
    """集成状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    FAILED = "failed"


class NotificationChannel(str, Enum):
    """通知渠道"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    PUSH = "push"


# ==================== 邮件通知模型 ====================

class EmailProvider(str, Enum):
    """邮件服务提供商"""
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    ALIYUN = "aliyun"
    TENCENT = "tencent"


class EmailTemplate(BaseModel):
    """邮件模板"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject: str
    content: str
    template_type: str  # welcome, notification, digest, verification, etc.
    variables: List[str] = Field(default_factory=list)  # 模板变量
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class EmailConfig(BaseModel):
    """邮件配置"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: EmailProvider = EmailProvider.SMTP
    status: IntegrationStatus = IntegrationStatus.PENDING

    # SMTP 配置
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None  # 加密存储
    use_tls: bool = True
    use_ssl: bool = False

    # API 配置（用于 SendGrid/Mailgun 等）
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

    # 发件人配置
    sender_email: Optional[str] = None
    sender_name: str = "Human-AI-Community"

    # 速率限制
    rate_limit_per_minute: int = 60
    daily_limit: int = 10000

    # 统计
    total_sent: int = 0
    total_failed: int = 0

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None


class EmailSendRecord(BaseModel):
    """邮件发送记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recipient_email: str
    subject: str
    template_id: Optional[str] = None
    template_type: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, sent, failed, bounced
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None  # 邮件打开时间
    clicked_at: Optional[datetime] = None  # 链接点击时间
    created_at: datetime = Field(default_factory=datetime.now)


# ==================== 短信通知模型 ====================

class SMSProvider(str, Enum):
    """短信服务提供商"""
    TWILIO = "twilio"
    ALIYUN = "aliyun"
    TENCENT = "tencent"
    YUNPIAN = "yunpian"
    CUSTOM = "custom"


class SMSConfig(BaseModel):
    """短信配置"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: SMSProvider = SMSProvider.ALIYUN
    status: IntegrationStatus = IntegrationStatus.PENDING

    # Twilio 配置
    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    from_number: Optional[str] = None

    # 阿里云/腾讯云配置
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    sign_name: Optional[str] = None  # 短信签名

    # 模板配置
    templates: Dict[str, str] = Field(default_factory=dict)  # 模板 ID 映射

    # 速率限制
    rate_limit_per_minute: int = 10
    daily_limit_per_user: int = 50

    # 统计
    total_sent: int = 0
    total_failed: int = 0

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None


class SMSSendRecord(BaseModel):
    """短信发送记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recipient_phone: str
    template_code: str
    template_params: Dict[str, str] = Field(default_factory=dict)
    content: str
    status: str = "pending"  # pending, sent, delivered, failed
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    provider_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


# ==================== OAuth 模型 ====================

class OAuthConfig(BaseModel):
    """OAuth 提供商配置"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: OAuthProvider
    status: IntegrationStatus = IntegrationStatus.PENDING

    # OAuth 凭证
    client_id: str
    client_secret: str  # 加密存储

    # 端点配置
    authorize_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    redirect_uri: str

    # 权限范围
    scopes: List[str] = Field(default_factory=list)

    # 用户映射配置
    user_mapping: Dict[str, str] = Field(default_factory=dict)
    # 示例：{"email": "email", "name": "nickname", "avatar": "picture"}

    # 自动注册配置
    auto_register: bool = True
    default_role: str = "member"

    # 统计
    total_logins: int = 0
    total_registrations: int = 0

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None


class OAuthState(BaseModel):
    """OAuth 状态（用于 CSRF 防护）"""
    state: str
    redirect_uri: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)


class OAuthToken(BaseModel):
    """OAuth 访问令牌"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider: OAuthProvider
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    expires_at: datetime
    scopes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    refreshed_at: Optional[datetime] = None


# ==================== SSO 模型 ====================

class SSOConfig(BaseModel):
    """SSO 配置"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    protocol: SSOProtocol
    status: IntegrationStatus = IntegrationStatus.PENDING

    # SAML 2.0 配置
    idp_entity_id: Optional[str] = None  # IdP 实体 ID
    idp_sso_url: Optional[str] = None  # IdP SSO URL
    idp_metadata_url: Optional[str] = None  # IdP 元数据 URL
    sp_entity_id: Optional[str] = None  # SP 实体 ID
    assertion_consumer_service_url: Optional[str] = None  # ACS URL

    # OIDC 配置
    oidc_issuer: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_redirect_uri: Optional[str] = None

    # LDAP 配置
    ldap_host: Optional[str] = None
    ldap_port: Optional[int] = None
    ldap_bind_dn: Optional[str] = None
    ldap_bind_password: Optional[str] = None
    ldap_base_dn: Optional[str] = None
    ldap_user_filter: Optional[str] = None

    # 用户属性映射
    attribute_mapping: Dict[str, str] = Field(default_factory=dict)
    # 示例：{"user_id": "uid", "email": "mail", "name": "cn"}

    # 同步配置
    auto_sync_users: bool = False
    sync_schedule: Optional[str] = None  # Cron 表达式

    # 统计
    total_logins: int = 0
    total_users_synced: int = 0

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_sync_at: Optional[datetime] = None


class SSOSession(BaseModel):
    """SSO 会话"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sso_config_id: str
    user_id: str
    session_id: str
    assertion_id: Optional[str] = None  # SAML Assertion ID
    name_id: Optional[str] = None  # SAML NameID
    attributes: Dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity_at: datetime = Field(default_factory=datetime.now)


# ==================== 社交分享模型 ====================

class SharePlatform(str, Enum):
    """分享平台"""
    WECHAT = "wechat"
    WEIBO = "weibo"
    QQ = "qq"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"


class ShareConfig(BaseModel):
    """社交分享配置"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: SharePlatform
    status: IntegrationStatus = IntegrationStatus.PENDING

    # 平台凭证
    app_id: Optional[str] = None
    app_secret: Optional[str] = None

    # 分享卡片配置
    default_title: str = "Human-AI-Community"
    default_description: str = "人类与 AI 共享身份的社区平台"
    default_image: Optional[str] = None

    # URL 配置
    base_url: str = "https://community.example.com"
    url_template: str = "/posts/{id}"

    # 统计
    total_shares: int = 0
    total_clicks: int = 0

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ShareRecord(BaseModel):
    """分享记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    platform: SharePlatform
    content_type: str  # post, comment
    content_id: str
    content_title: str
    share_url: str
    share_text: Optional[str] = None
    share_image: Optional[str] = None
    share_token: Optional[str] = None  # 用于追踪
    created_at: datetime = Field(default_factory=datetime.now)


# ==================== 跨平台身份映射模型 ====================

class CrossPlatformIdentity(BaseModel):
    """跨平台身份映射"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    local_user_id: str
    local_user_type: str = "member"

    # 外部平台身份
    external_platform: str  # discord, slack, etc.
    external_user_id: str
    external_username: str
    external_metadata: Dict[str, Any] = Field(default_factory=dict)

    # 身份验证
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    # 同步状态
    is_linked: bool = True
    linked_at: datetime = Field(default_factory=datetime.now)
    last_synced_at: Optional[datetime] = None

    # 信誉携带
    reputation_synced: bool = False
    reputation_score: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ==================== 请求/响应模型 ====================

class EmailSendRequest(BaseModel):
    """邮件发送请求"""
    recipient_email: str
    subject: str
    content: str
    template_type: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    is_html: bool = False
    attachments: Optional[List[str]] = None  # 附件路径


class SMSSendRequest(BaseModel):
    """短信发送请求"""
    recipient_phone: str
    template_code: str
    template_params: Dict[str, str] = Field(default_factory=dict)


class OAuthCallbackRequest(BaseModel):
    """OAuth 回调请求"""
    code: str
    state: str


class SSOLogoutRequest(BaseModel):
    """SSO 登出请求"""
    session_id: str
    return_to: Optional[str] = None


class CrossPlatformLinkRequest(BaseModel):
    """跨平台绑定请求"""
    platform: str
    redirect_uri: Optional[str] = None


class IntegrationTestResult(BaseModel):
    """集成测试结果"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
