"""
隐私安全中心 ORM 模型 - v1.21 隐私安全中心

支持登录设备管理、登录日志、用户举报、安全知识点、隐私设置增强
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


# ==================== 登录设备表 ====================

class LoginDeviceDB(Base):
    """登录设备表"""
    __tablename__ = "login_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    # 设备信息
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 如 "iPhone 14 Pro"
    device_type: Mapped[str] = mapped_column(String(50), default="unknown")  # mobile, desktop, web, tablet
    device_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    os_info: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 如 "iOS 16.0"
    browser_info: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 如 "Chrome 120.0"

    # 网络信息
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location_info: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 如 "北京市朝阳区"

    # 设备状态
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否当前使用设备
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否受信任设备

    # 时间
    first_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)

    # 索引
    __table_args__ = (
        Index('idx_devices_user_id', 'user_id'),
        Index('idx_devices_last_login', 'last_login_at'),
    )


# ==================== 登录日志表 ====================

class LoginLogDB(Base):
    """登录日志表"""
    __tablename__ = "login_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    log_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    device_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 登录信息
    login_type: Mapped[str] = mapped_column(String(50), default="success")  # success, failed, blocked
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location_info: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 风险评估
    risk_level: Mapped[str] = mapped_column(String(50), default="low")  # low, medium, high
    risk_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)

    # 索引
    __table_args__ = (
        Index('idx_logs_user_id', 'user_id'),
        Index('idx_logs_created_at', 'created_at'),
    )


# ==================== 用户举报表 ====================

class UserReportDB(Base):
    """用户举报表"""
    __tablename__ = "user_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)

    # 举报双方
    reporter_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)  # 举报人
    reported_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)  # 被举报人

    # 举报信息
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # harassment, fraud, spam, fake_profile, inappropriate_content, other
    report_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    evidence_urls: Mapped[Dict] = mapped_column(JSON, default=list)  # 证据图片/链接

    # 关联内容
    related_task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    related_message_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 处理状态
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, reviewing, resolved, rejected
    priority: Mapped[str] = mapped_column(String(50), default="normal")  # low, normal, high, urgent

    # 处理信息
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 分配给哪个管理员
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 处理说明
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 处理人

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index('idx_reports_reporter', 'reporter_id'),
        Index('idx_reports_reported', 'reported_id'),
        Index('idx_reports_status', 'status'),
        Index('idx_reports_created_at', 'created_at'),
    )


# ==================== 安全知识点表 ====================

class SafetyTipDB(Base):
    """安全知识点表"""
    __tablename__ = "safety_tips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tip_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)

    # 内容
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 分类
    tip_type: Mapped[str] = mapped_column(String(50), default="general")  # fraud_prevention, privacy_protection, account_security, payment_security, task_security
    risk_level: Mapped[str] = mapped_column(String(50), default="medium")  # low, medium, high

    # 目标受众
    target_audience: Mapped[str] = mapped_column(String(50), default="all")  # all, employer, worker

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index('idx_tips_type', 'tip_type'),
        Index('idx_tips_active', 'is_active'),
    )


# ==================== 隐私设置扩展表 ====================

class PrivacySettingsExtensionDB(Base):
    """隐私设置扩展表 - 补充现有隐私设置"""
    __tablename__ = "privacy_settings_extensions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # 在线状态
    hide_online_status: Mapped[bool] = mapped_column(Boolean, default=False)  # 隐藏在线状态
    hide_distance: Mapped[bool] = mapped_column(Boolean, default=True)  # 隐藏精确距离

    # 匿名模式
    anonymous_mode: Mapped[bool] = mapped_column(Boolean, default=False)  # 匿名浏览模式

    # 消息过滤
    block_keywords: Mapped[Dict] = mapped_column(JSON, default=list)  # 屏蔽关键词列表
    message_filter_level: Mapped[str] = mapped_column(String(50), default="normal")  # strict, normal, loose

    # 数据导出
    data_export_requested: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否请求过数据导出
    last_data_export_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 账号注销
    account_deletion_requested: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否请求过账号注销
    deletion_scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # 计划注销时间

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


# ==================== 用户已读安全知识点表 ====================

class UserSafetyTipReadDB(Base):
    """用户已读安全知识点表"""
    __tablename__ = "user_safety_tip_reads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    tip_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # 时间
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)

    # 唯一约束：同一用户不能重复标记同一知识点
    __table_args__ = (
        Index('idx_user_tip_read', 'user_id', 'tip_id'),
    )
