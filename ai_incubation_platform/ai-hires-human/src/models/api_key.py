"""
API 密钥管理模型 - 用于开放 API 认证。
"""
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import Boolean, DateTime, String, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class APIKeyDB(Base):
    """API 密钥表。"""
    __tablename__ = "api_keys"

    key_id: Mapped[str] = mapped_column(String(36), primary_key=True, unique=True)
    key_hash: Mapped[str] = mapped_column(String(64), index=True, unique=True)  # SHA256 哈希
    key_prefix: Mapped[str] = mapped_column(String(8), index=True)  # 密钥前缀用于标识

    # 所有者信息
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    owner_type: Mapped[str] = mapped_column(String(20), default="developer")  # developer, enterprise, internal

    # 密钥元数据
    name: Mapped[str] = mapped_column(String(255))  # 密钥名称（用户自定义）
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 权限范围
    scopes: Mapped[Dict] = mapped_column(JSON, default=list)  # 如 ["tasks:read", "tasks:write", "workers:read"]

    # 限流配置
    rate_limit: Mapped[int] = mapped_column(Integer, default=1000)  # 每分钟请求数
    rate_limit_daily: Mapped[int] = mapped_column(Integer, default=10000)  # 每日请求数

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 使用统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reset_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD


class DeveloperProfileDB(Base):
    """开发者档案表。"""
    __tablename__ = "developer_profiles"

    developer_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # 基本信息
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 开发者类型
    developer_type: Mapped[str] = mapped_column(String(20), default="individual")  # individual, enterprise, organization

    # 认证状态
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 应用信息
    applications: Mapped[Dict] = mapped_column(JSON, default=list)  # 应用列表 [{"name": "...", "description": "...", "url": "..."}]

    # 统计信息
    total_api_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_tasks_created: Mapped[int] = mapped_column(Integer, default=0)
    total_workers_hired: Mapped[int] = mapped_column(Integer, default=0)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class APIUsageLogDB(Base):
    """API 使用日志表。"""
    __tablename__ = "api_usage_logs"

    log_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 请求信息
    api_key_id: Mapped[str] = mapped_column(String(36), index=True)
    endpoint: Mapped[str] = mapped_column(String(500), index=True)
    method: Mapped[str] = mapped_column(String(10))  # GET, POST, PUT, DELETE

    # 请求详情
    request_params: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    request_body: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    response_status: Mapped[int] = mapped_column(Integer, default=200)
    response_size: Mapped[int] = mapped_column(Integer, default=0)

    # 性能指标
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)  # 请求耗时（毫秒）

    # 客户端信息
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)


class OAuthApplicationDB(Base):
    """OAuth2 应用表。"""
    __tablename__ = "oauth_applications"

    app_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 应用信息
    client_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    client_secret_hash: Mapped[str] = mapped_column(String(64))  # 客户端密钥哈希

    # 所有者
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    app_name: Mapped[str] = mapped_column(String(255))
    app_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 重定向 URI
    redirect_uris: Mapped[Dict] = mapped_column(JSON, default=list)  # 允许的重定向 URI 列表

    # 权限范围
    scopes: Mapped[Dict] = mapped_column(JSON, default=list)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class OAuthAccessTokenDB(Base):
    """OAuth2 访问令牌表。"""
    __tablename__ = "oauth_access_tokens"

    token_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 令牌信息
    access_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # 关联
    app_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)

    # 权限
    scopes: Mapped[Dict] = mapped_column(JSON, default=list)

    # 状态
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    # 时间戳
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
