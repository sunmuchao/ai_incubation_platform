"""
隐私安全中心 Pydantic 实体 - v1.21 隐私安全中心

用于 API 请求/响应验证
"""
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr


# ==================== 登录设备相关实体 ====================

class LoginDeviceBase(BaseModel):
    """登录设备基础实体"""
    device_name: Optional[str] = None
    device_type: str = "unknown"
    device_model: Optional[str] = None
    os_info: Optional[str] = None
    browser_info: Optional[str] = None
    ip_address: Optional[str] = None
    location_info: Optional[str] = None


class LoginDeviceCreate(LoginDeviceBase):
    """创建登录设备"""
    user_id: str
    is_trusted: bool = False


class LoginDeviceResponse(LoginDeviceBase):
    """登录设备响应"""
    device_id: str
    user_id: str
    is_current: bool
    is_trusted: bool
    first_login_at: datetime
    last_login_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class LoginDeviceListResponse(BaseModel):
    """登录设备列表响应"""
    success: bool
    devices: List[LoginDeviceResponse]
    current_device_id: Optional[str] = None


# ==================== 登录日志相关实体 ====================

class LoginLogBase(BaseModel):
    """登录日志基础实体"""
    login_type: str = "success"
    ip_address: Optional[str] = None
    location_info: Optional[str] = None
    user_agent: Optional[str] = None
    risk_level: str = "low"
    risk_reason: Optional[str] = None


class LoginLogResponse(LoginLogBase):
    """登录日志响应"""
    log_id: str
    user_id: str
    device_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LoginLogListResponse(BaseModel):
    """登录日志列表响应"""
    success: bool
    logs: List[LoginLogResponse]
    total: int


# ==================== 用户举报相关实体 ====================

class UserReportBase(BaseModel):
    """用户举报基础实体"""
    report_type: str = Field(..., description="举报类型：harassment, fraud, spam, fake_profile, inappropriate_content, other")
    report_reason: Optional[str] = Field(None, max_length=500, description="举报原因")
    evidence_urls: List[str] = Field(default_factory=list, description="证据 URL 列表")
    related_task_id: Optional[str] = None
    related_message_id: Optional[str] = None


class UserReportCreate(UserReportBase):
    """创建举报"""
    reported_id: str = Field(..., description="被举报人 ID")


class UserReportResponse(UserReportBase):
    """举报响应"""
    report_id: str
    reporter_id: str
    reported_id: str
    status: str
    priority: str
    assigned_to: Optional[str]
    resolution_notes: Optional[str]
    processed_at: Optional[datetime]
    processed_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserReportListResponse(BaseModel):
    """举报列表响应"""
    success: bool
    reports: List[UserReportResponse]
    total: int
    has_more: bool = False


class UserReportDetailResponse(BaseModel):
    """举报详情响应"""
    success: bool
    report: UserReportResponse


# ==================== 举报处理相关实体 ====================

class ReportProcessRequest(BaseModel):
    """举报处理请求"""
    status: str = Field(..., description="处理结果：resolved, rejected")
    resolution_notes: str = Field(..., max_length=1000, description="处理说明")
    priority: Optional[str] = Field(None, description="优先级调整")


class ReportStatistics(BaseModel):
    """举报统计"""
    total_reports: int
    pending_reports: int
    reviewing_reports: int
    resolved_reports: int
    rejected_reports: int
    urgent_reports: int


class ReportStatisticsResponse(BaseModel):
    """举报统计响应"""
    success: bool
    statistics: ReportStatistics


# ==================== 安全知识点相关实体 ====================

class SafetyTipBase(BaseModel):
    """安全知识点基础实体"""
    title: str = Field(..., max_length=200)
    content: str
    tip_type: str = Field(default="general", description="类型：fraud_prevention, privacy_protection, account_security, payment_security, task_security")
    risk_level: str = Field(default="medium", description="风险等级：low, medium, high")
    target_audience: str = Field(default="all", description="目标受众：all, employer, worker")


class SafetyTipCreate(SafetyTipBase):
    """创建安全知识点"""
    sort_order: int = 0


class SafetyTipResponse(SafetyTipBase):
    """安全知识点响应"""
    tip_id: str
    is_active: bool
    sort_order: int
    view_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SafetyTipListResponse(BaseModel):
    """安全知识点列表响应"""
    success: bool
    tips: List[SafetyTipResponse]
    total: int


class SafetyTipDetailResponse(BaseModel):
    """安全知识点详情响应"""
    success: bool
    tip: SafetyTipResponse


class MarkTipReadRequest(BaseModel):
    """标记已读请求"""
    tip_id: str


class MarkTipReadResponse(BaseModel):
    """标记已读响应"""
    success: bool
    message: str = "标记成功"


# ==================== 隐私设置扩展相关实体 ====================

class PrivacySettingsExtensionBase(BaseModel):
    """隐私设置扩展基础实体"""
    hide_online_status: bool = False
    hide_distance: bool = True
    anonymous_mode: bool = False
    block_keywords: List[str] = Field(default_factory=list)
    message_filter_level: str = Field(default="normal", description="消息过滤级别：strict, normal, loose")


class PrivacySettingsExtensionUpdate(BaseModel):
    """更新隐私设置扩展"""
    hide_online_status: Optional[bool] = None
    hide_distance: Optional[bool] = None
    anonymous_mode: Optional[bool] = None
    block_keywords: Optional[List[str]] = None
    message_filter_level: Optional[str] = None


class PrivacySettingsExtensionResponse(PrivacySettingsExtensionBase):
    """隐私设置扩展响应"""
    user_id: str
    data_export_requested: bool
    last_data_export_at: Optional[datetime]
    account_deletion_requested: bool
    deletion_scheduled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PrivacySettingsResponse(BaseModel):
    """隐私设置响应"""
    success: bool
    settings: PrivacySettingsExtensionResponse


# ==================== 屏蔽管理相关实体 ====================

class BlockUserRequest(BaseModel):
    """拉黑用户请求"""
    user_id: str = Field(..., description="要拉黑的用户 ID")


class BlockUserResponse(BaseModel):
    """拉黑用户响应"""
    success: bool
    message: str


class UnblockUserRequest(BaseModel):
    """取消拉黑请求"""
    user_id: str = Field(..., description="要取消拉黑的用户 ID")


class BlockedUserItem(BaseModel):
    """拉黑用户项"""
    blocked_id: str
    blocked_name: Optional[str]
    blocked_at: datetime


class BlockedUserListResponse(BaseModel):
    """拉黑用户列表响应"""
    success: bool
    blocked_users: List[BlockedUserItem]
    total: int


# ==================== 隐身模式相关实体 ====================

class InvisibleModeRequest(BaseModel):
    """隐身模式请求"""
    enable: bool = Field(..., description="是否启用隐身模式")


class InvisibleModeResponse(BaseModel):
    """隐身模式响应"""
    success: bool
    invisible_mode: bool
    message: str


# ==================== 账号安全相关实体 ====================

class RemoveDeviceRequest(BaseModel):
    """移除设备请求"""
    device_id: str = Field(..., description="要移除的设备 ID")


class RemoveDeviceResponse(BaseModel):
    """移除设备响应"""
    success: bool
    message: str


class TrustDeviceRequest(BaseModel):
    """信任设备请求"""
    device_id: str = Field(..., description="要信任的设备 ID")


class TrustDeviceResponse(BaseModel):
    """信任设备响应"""
    success: bool
    message: str


class LoginAlertConfig(BaseModel):
    """登录提醒配置"""
    enable_alerts: bool = True
    alert_methods: List[str] = Field(default=["notification"], description="提醒方式：notification, email, sms")


class LoginAlertConfigResponse(BaseModel):
    """登录提醒配置响应"""
    success: bool
    config: LoginAlertConfig


# ==================== 综合响应 ====================

class PrivacySecurityDashboardResponse(BaseModel):
    """隐私安全仪表板响应"""
    success: bool
    data: dict
