"""
API Key 模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import secrets


class APIKeyType(str, Enum):
    """API Key 类型"""
    DEVELOPER = "developer"      # 开发者密钥 (默认限额)
    PROFESSIONAL = "professional"  # 专业版密钥 (中等限额)
    ENTERPRISE = "enterprise"     # 企业版密钥 (高限额)
    INTERNAL = "internal"        # 内部服务密钥 (无限额)


class APIKeyStatus(str, Enum):
    """API Key 状态"""
    ACTIVE = "active"       # 激活
    INACTIVE = "inactive"   # 未激活
    REVOKED = "revoked"     # 已撤销
    EXPIRED = "expired"     # 已过期


class APIKeyTier(str, Enum):
    """API Key 等级"""
    FREE = "free"           # 免费版
    BASIC = "basic"         # 基础版
    PRO = "pro"             # 专业版
    ENTERPRISE = "enterprise"  # 企业版


class APIKey(BaseModel):
    """API Key 模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # 密钥名称
    key: str = Field(default_factory=lambda: f"sk_{secrets.token_urlsafe(32)}")  # 密钥值
    owner_id: str  # 所有者 ID
    owner_type: str = "member"  # 所有者类型：member, application

    # 密钥类型和等级
    key_type: APIKeyType = APIKeyType.DEVELOPER
    tier: APIKeyTier = APIKeyTier.FREE

    # 速率限制配置 (每秒请求数)
    rate_limit: int = 10  # 默认每秒 10 次请求
    daily_limit: int = 10000  # 每日请求上限

    # 状态
    status: APIKeyStatus = APIKeyStatus.ACTIVE

    # 权限范围
    scopes: List[str] = Field(default_factory=list)  # 允许的 API 范围

    # IP 白名单 (可选)
    ip_whitelist: Optional[List[str]] = None

    # 时间
    expires_at: Optional[datetime] = None  # 过期时间
    last_used_at: Optional[datetime] = None  # 最后使用时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 统计
    total_requests: int = 0
    today_requests: int = 0

    # 元数据
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at and datetime.now() > self.expires_at:
            return True
        return False

    def is_active(self) -> bool:
        """检查是否可用"""
        return self.status == APIKeyStatus.ACTIVE and not self.is_expired()

    def has_scope(self, scope: str) -> bool:
        """检查是否有指定权限"""
        if not self.scopes:  # 空 scopes 表示拥有所有权限
            return True
        return scope in self.scopes or "*" in self.scopes

    def to_dict(self, hide_key: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "id": self.id,
            "name": self.name,
            "key": self.key if not hide_key else f"{self.key[:8]}...{self.key[-4:]}",
            "owner_id": self.owner_id,
            "owner_type": self.owner_type,
            "key_type": self.key_type.value,
            "tier": self.tier.value,
            "rate_limit": self.rate_limit,
            "daily_limit": self.daily_limit,
            "status": self.status.value,
            "scopes": self.scopes,
            "ip_whitelist": self.ip_whitelist,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_requests": self.total_requests,
            "today_requests": self.today_requests,
            "description": self.description,
            "metadata": self.metadata,
        }
        return data


class APIKeyCreate(BaseModel):
    """创建 API Key 请求"""
    name: str
    key_type: APIKeyType = APIKeyType.DEVELOPER
    tier: APIKeyTier = APIKeyTier.FREE
    scopes: List[str] = Field(default_factory=list)
    ip_whitelist: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class APIKeyUpdate(BaseModel):
    """更新 API Key 请求"""
    name: Optional[str] = None
    status: Optional[APIKeyStatus] = None
    rate_limit: Optional[int] = None
    daily_limit: Optional[int] = None
    scopes: Optional[List[str]] = None
    ip_whitelist: Optional[List[str]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class APIKeyUsage(BaseModel):
    """API Key 使用统计"""
    api_key_id: str
    period: str  # day, week, month
    total_requests: int
    successful_requests: int
    failed_requests: int
    rate_limited_requests: int
    avg_response_time_ms: float
    requests_by_endpoint: Dict[str, int]
    requests_by_status: Dict[str, int]
    peak_requests_per_second: float
    created_at: datetime = Field(default_factory=datetime.now)
