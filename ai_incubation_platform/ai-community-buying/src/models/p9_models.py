"""
P9 多平台/小程序集成 - Pydantic 数据模型

定义多平台集成相关的 API 请求/响应模型
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============= Enums =============

class PlatformType(str, Enum):
    """支持的平台类型"""
    WECHAT = "wechat"  # 微信小程序
    ALIPAY = "alipay"  # 支付宝小程序
    DOUYIN = "douyin"  # 抖音小程序
    BAIDU = "baidu"  # 百度小程序
    QUICK_APP = "quick_app"  # 快应用


class PaymentStatus(str, Enum):
    """支付状态"""
    UNPAID = "unpaid"
    PAID = "paid"
    REFUNDING = "refunding"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"
    PAID = "paid"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class SyncStatus(str, Enum):
    """同步状态"""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


class NotificationType(str, Enum):
    """通知类型"""
    SUBSCRIBE_MSG = "subscribe_msg"  # 订阅消息 (微信)
    TEMPLATE_MSG = "template_msg"  # 模板消息 (支付宝)
    UNIFORM_MSG = "uniform_msg"  # 统一消息


class SendStatus(str, Enum):
    """发送状态"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class SyncDirection(str, Enum):
    """同步方向"""
    INBOUND = "inbound"  # 平台 -> 内部
    OUTBOUND = "outbound"  # 内部 -> 平台


class SyncAction(str, Enum):
    """同步动作"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"


# ============= Platform Account Models =============

class PlatformAccountBase(BaseModel):
    """平台账号基础模型"""
    platform: PlatformType
    platform_user_id: str = Field(..., max_length=128, description="平台用户 ID")
    union_id: Optional[str] = Field(None, max_length=128, description="UnionID")


class PlatformAccountCreate(PlatformAccountBase):
    """创建平台账号请求"""
    user_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    session_key: Optional[str] = None
    avatar_url: Optional[str] = None
    nickname: Optional[str] = None
    gender: Optional[int] = None
    phone: Optional[str] = None
    is_primary: bool = False


class PlatformAccountUpdate(BaseModel):
    """更新平台账号请求"""
    avatar_url: Optional[str] = None
    nickname: Optional[str] = None
    gender: Optional[int] = None
    phone: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class PlatformAccountResponse(PlatformAccountBase):
    """平台账号响应"""
    id: str
    user_id: str
    avatar_url: Optional[str]
    nickname: Optional[str]
    gender: Optional[int]
    phone: Optional[str]
    is_primary: bool
    is_active: bool
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlatformLoginRequest(BaseModel):
    """平台登录请求"""
    platform: PlatformType
    code: str = Field(..., description="登录 code (微信 js_code / 支付宝 auth_code)")
    encrypted_data: Optional[str] = None
    iv: Optional[str] = None
    raw_user_info: Optional[Dict[str, Any]] = None


class PlatformLoginResponse(BaseModel):
    """平台登录响应"""
    success: bool
    user_id: str
    platform_account_id: str
    is_new_user: bool
    access_token: str  # 系统访问令牌
    user_info: Optional[Dict[str, Any]] = None


class PlatformBindRequest(BaseModel):
    """绑定平台账号请求"""
    platform: PlatformType
    code: str
    user_id: str  # 当前登录用户 ID


class PlatformBindResponse(BaseModel):
    """绑定平台账号响应"""
    success: bool
    platform_account_id: str
    message: str


# ============= Platform Order Models =============

class PlatformOrderBase(BaseModel):
    """平台订单基础模型"""
    platform: PlatformType
    platform_order_id: str = Field(..., max_length=128)


class PlatformOrderCreate(PlatformOrderBase):
    """创建平台订单映射"""
    global_order_id: str
    platform_order_no: Optional[str] = None
    transaction_id: Optional[str] = None
    payment_amount: Optional[int] = None
    platform_metadata: Optional[Dict[str, Any]] = None


class PlatformOrderUpdate(BaseModel):
    """更新平台订单状态"""
    order_status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    payment_time: Optional[datetime] = None
    refund_amount: Optional[int] = None
    refund_time: Optional[datetime] = None
    refund_reason: Optional[str] = None
    sync_status: Optional[SyncStatus] = None


class PlatformOrderResponse(PlatformOrderBase):
    """平台订单响应"""
    id: str
    global_order_id: str
    platform_order_no: Optional[str]
    transaction_id: Optional[str]
    order_status: str
    payment_status: str
    payment_amount: Optional[int]
    payment_time: Optional[datetime]
    refund_amount: Optional[int]
    refund_time: Optional[datetime]
    refund_reason: Optional[str]
    sync_status: str
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlatformOrderSyncRequest(BaseModel):
    """同步订单状态到平台请求"""
    global_order_id: str
    platform: PlatformType
    order_status: Optional[OrderStatus] = None
    notify_user: bool = True


class PlatformOrderSyncResponse(BaseModel):
    """同步订单状态响应"""
    success: bool
    platform_order_id: str
    sync_result: str
    message: str


# ============= Platform Notification Models =============

class PlatformNotificationBase(BaseModel):
    """平台通知基础模型"""
    platform: PlatformType
    notification_type: NotificationType
    template_id: str


class PlatformNotificationCreate(PlatformNotificationBase):
    """创建平台通知请求"""
    user_id: str
    template_name: Optional[str] = None
    content: Dict[str, Any] = Field(..., description="通知内容数据")
    page_path: Optional[str] = None
    title: Optional[str] = None


class PlatformNotificationSendRequest(BaseModel):
    """发送平台通知请求"""
    user_id: str
    platform: PlatformType
    template_id: str
    template_name: Optional[str] = None
    content: Dict[str, Any]
    page_path: Optional[str] = None
    title: Optional[str] = None
    retry_count: int = 0


class PlatformNotificationResponse(BaseModel):
    """平台通知响应"""
    id: str
    user_id: str
    platform: str
    notification_type: str
    template_id: str
    template_name: Optional[str]
    title: Optional[str]
    content: Optional[Dict[str, Any]]
    page_path: Optional[str]
    send_status: str
    send_time: Optional[datetime]
    read_status: bool
    read_time: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class PlatformTemplateModel(BaseModel):
    """平台模板模型"""
    template_id: str
    template_name: str
    platform: str
    fields: List[str]
    description: Optional[str] = None


# ============= Platform Config Models =============

class PlatformConfigBase(BaseModel):
    """平台配置基础模型"""
    platform: PlatformType
    platform_name: Optional[str] = None
    app_id: str
    api_version: Optional[str] = None
    api_base_url: Optional[str] = None


class PlatformConfigCreate(PlatformConfigBase):
    """创建平台配置请求"""
    app_secret: str
    encoding_aes_key: Optional[str] = None
    mch_id: Optional[str] = None
    mch_key: Optional[str] = None
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_token: Optional[str] = None
    is_enabled: bool = True
    config_json: Optional[Dict[str, Any]] = None
    remarks: Optional[str] = None


class PlatformConfigUpdate(BaseModel):
    """更新平台配置请求"""
    platform_name: Optional[str] = None
    app_secret: Optional[str] = None
    encoding_aes_key: Optional[str] = None
    mch_id: Optional[str] = None
    mch_key: Optional[str] = None
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    api_version: Optional[str] = None
    api_base_url: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_token: Optional[str] = None
    is_enabled: Optional[bool] = None
    config_json: Optional[Dict[str, Any]] = None
    remarks: Optional[str] = None


class PlatformConfigResponse(PlatformConfigBase):
    """平台配置响应 (不包含敏感信息)"""
    id: str
    platform_name: Optional[str]
    app_id: str
    api_version: Optional[str]
    api_base_url: Optional[str]
    webhook_url: Optional[str]
    is_enabled: bool
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= Platform Sync Log Models =============

class PlatformSyncLogBase(BaseModel):
    """平台同步日志基础模型"""
    sync_type: str
    platform: PlatformType
    sync_direction: SyncDirection
    sync_action: SyncAction


class PlatformSyncLogCreate(PlatformSyncLogBase):
    """创建平台同步日志请求"""
    platform_resource_id: Optional[str] = None
    internal_resource_id: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    operator_id: Optional[str] = None
    operator_type: Optional[str] = None


class PlatformSyncLogResponse(PlatformSyncLogBase):
    """平台同步日志响应"""
    id: str
    platform_resource_id: Optional[str]
    internal_resource_id: Optional[str]
    sync_status: str
    request_data: Optional[Dict[str, Any]]
    response_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    duration_ms: Optional[int]
    operator_id: Optional[str]
    operator_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PlatformSyncLogQuery(BaseModel):
    """平台同步日志查询参数"""
    sync_type: Optional[str] = None
    platform: Optional[PlatformType] = None
    sync_status: Optional[str] = None
    internal_resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


# ============= Unified Response Models =============

class PlatformApiResponse(BaseModel):
    """平台 API 统一响应"""
    success: bool
    message: str
    data: Optional[Any] = None
    error_code: Optional[str] = None
    platform: Optional[str] = None


class PlatformAuthInfo(BaseModel):
    """平台认证信息"""
    access_token: str
    expires_in: int
    refresh_token: Optional[str] = None
    openid: Optional[str] = None
    unionid: Optional[str] = None
    session_key: Optional[str] = None


class WechatUserInfo(BaseModel):
    """微信用户信息"""
    openid: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[int] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None


class AlipayUserInfo(BaseModel):
    """支付宝用户信息"""
    user_id: str
    avatar: Optional[str] = None
    nick_name: Optional[str] = None
    gender: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None


class PlatformStats(BaseModel):
    """平台统计信息"""
    platform: str
    total_accounts: int
    active_accounts: int
    total_orders: int
    pending_orders: int
    total_notifications: int
    failed_notifications: int
