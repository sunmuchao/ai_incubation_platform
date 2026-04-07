"""
企业级功能模型

包含：
- 列级权限控制
- 行级策略控制
- 租户配额管理
- 租户使用统计
- 增强审计日志
"""
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, Index, Integer, JSON, ForeignKey, UniqueConstraint, Text, Float, Date
from models.lineage_db import Base
from sqlalchemy.orm import relationship
import uuid

# Base imported from lineage_db


# ==================== 列级权限 ====================

class ColumnPermissionModel(Base):
    """列权限模型"""
    __tablename__ = "enterprise_column_permissions"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    role_id = Column(String(64), ForeignKey("rbac_roles.id"), nullable=False)
    datasource_name = Column(String(128), nullable=False)
    table_name = Column(String(128), nullable=False)
    column_name = Column(String(128), nullable=False)

    # 访问类型：allow(允许访问) / deny(禁止访问)
    access_type = Column(String(16), default="deny", nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint('role_id', 'datasource_name', 'table_name', 'column_name', name='uq_col_perm_unique'),
        Index('idx_col_perm_role', 'role_id'),
        Index('idx_col_perm_datasource_table', 'datasource_name', 'table_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role_id": self.role_id,
            "datasource_name": self.datasource_name,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "access_type": self.access_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


# ==================== 行级策略 ====================

class RowLevelPolicyModel(Base):
    """行级策略模型"""
    __tablename__ = "enterprise_row_level_policies"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    role_id = Column(String(64), ForeignKey("rbac_roles.id"), nullable=False)
    datasource_name = Column(String(128), nullable=False)
    table_name = Column(String(128), nullable=False)

    # SQL WHERE 条件（不包含 WHERE 关键字）
    # 例如："region = 'east' AND status = 'active'"
    filter_condition = Column(Text, nullable=False)

    description = Column(Text, nullable=True)
    priority = Column(Integer, default=0, nullable=False)  # 优先级，数字越大优先级越高
    is_active = Column(Boolean, default=True, nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_row_policy_role', 'role_id'),
        Index('idx_row_policy_datasource_table', 'datasource_name', 'table_name'),
        Index('idx_row_policy_active', 'is_active'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role_id": self.role_id,
            "datasource_name": self.datasource_name,
            "table_name": self.table_name,
            "filter_condition": self.filter_condition,
            "description": self.description,
            "priority": self.priority,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }


# ==================== 租户配额 ====================

class TenantQuotaModel(Base):
    """租户配额模型"""
    __tablename__ = "enterprise_tenant_quotas"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False, unique=True)

    # 查询配额
    daily_query_limit = Column(Integer, default=10000, nullable=False)  # 每日查询次数限制
    monthly_query_limit = Column(Integer, default=300000, nullable=False)  # 每月查询次数限制

    # 并发限制
    max_concurrent_queries = Column(Integer, default=50, nullable=False)  # 最大并发查询数

    # 存储限制
    max_storage_gb = Column(Float, default=100.0, nullable=False)  # 最大存储空间 (GB)

    # 数据源限制
    max_datasources = Column(Integer, default=20, nullable=False)  # 最大数据源数量

    # 配额重置配置
    reset_day = Column(Integer, default=1, nullable=False)  # 每月几号重置月度配额 (1-28)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_tenant_quota_tenant', 'tenant_id', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "daily_query_limit": self.daily_query_limit,
            "monthly_query_limit": self.monthly_query_limit,
            "max_concurrent_queries": self.max_concurrent_queries,
            "max_storage_gb": self.max_storage_gb,
            "max_datasources": self.max_datasources,
            "reset_day": self.reset_day,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }


# ==================== 租户使用统计 ====================

class TenantUsageModel(Base):
    """租户使用统计模型"""
    __tablename__ = "enterprise_tenant_usage"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)
    stat_date = Column(Date, nullable=False)  # 统计日期

    # 查询统计
    query_count = Column(Integer, default=0, nullable=False)  # 当日查询次数
    failed_query_count = Column(Integer, default=0, nullable=False)  # 失败查询次数
    avg_query_duration_ms = Column(Float, default=0.0, nullable=False)  # 平均查询耗时 (ms)

    # 存储统计
    storage_used_gb = Column(Float, default=0.0, nullable=False)  # 已用存储空间 (GB)

    # 并发统计
    peak_concurrent = Column(Integer, default=0, nullable=False)  # 当日峰值并发数

    # 数据源统计
    active_datasources = Column(Integer, default=0, nullable=False)  # 活跃数据源数量

    # 用户统计
    active_users = Column(Integer, default=0, nullable=False)  # 当日活跃用户数

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'stat_date', name='uq_tenant_usage_date'),
        Index('idx_tenant_usage_tenant_date', 'tenant_id', 'stat_date'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "stat_date": self.stat_date.isoformat() if self.stat_date else None,
            "query_count": self.query_count,
            "failed_query_count": self.failed_query_count,
            "avg_query_duration_ms": self.avg_query_duration_ms,
            "storage_used_gb": self.storage_used_gb,
            "peak_concurrent": self.peak_concurrent,
            "active_datasources": self.active_datasources,
            "active_users": self.active_users,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ==================== 增强审计日志 ====================

class AuditLogEnhancedModel(Base):
    """增强审计日志模型"""
    __tablename__ = "enterprise_audit_logs_enhanced"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 链路追踪
    trace_id = Column(String(64), nullable=False, index=True)  # 链路追踪 ID
    session_id = Column(String(64), nullable=True, index=True)  # 会话 ID
    span_id = Column(String(64), nullable=True)  # Span ID

    # 用户信息
    user_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)

    # 操作信息
    action = Column(String(64), nullable=False, index=True)  # 操作类型
    resource_type = Column(String(32), nullable=False)  # 资源类型
    resource_id = Column(String(128), nullable=True)  # 资源 ID

    # 请求/响应
    request_method = Column(String(16), nullable=True)  # HTTP 方法
    request_path = Column(String(256), nullable=True)  # 请求路径
    request_body = Column(JSON, nullable=True)  # 请求体
    response_status = Column(Integer, nullable=True)  # 响应状态码
    response_body = Column(JSON, nullable=True)  # 响应体

    # 状态对比（用于数据变更操作）
    before_state = Column(JSON, nullable=True)  # 操作前状态
    after_state = Column(JSON, nullable=True)  # 操作后状态

    # 环境信息
    ip_address = Column(String(64), nullable=True)  # IP 地址
    user_agent = Column(String(512), nullable=True)  # User-Agent
    referer = Column(String(512), nullable=True)  # Referer

    # 性能信息
    duration_ms = Column(Integer, nullable=True)  # 耗时 (ms)
    db_query_count = Column(Integer, default=0, nullable=True)  # 数据库查询次数
    db_query_duration_ms = Column(Integer, nullable=True)  # 数据库查询耗时 (ms)

    # 安全信息
    risk_score = Column(Float, default=0.0, nullable=True)  # 风险评分 (0-1)
    is_anomaly = Column(Boolean, default=False, nullable=True)  # 是否异常
    anomaly_reason = Column(Text, nullable=True)  # 异常原因

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_audit_enhanced_user_time', 'user_id', 'created_at'),
        Index('idx_audit_enhanced_action', 'action'),
        Index('idx_audit_enhanced_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_enhanced_anomaly', 'is_anomaly'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "span_id": self.span_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "request_body": self.request_body,
            "response_status": self.response_status,
            "response_body": self.response_body,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "referer": self.referer,
            "duration_ms": self.duration_ms,
            "db_query_count": self.db_query_count,
            "db_query_duration_ms": self.db_query_duration_ms,
            "risk_score": self.risk_score,
            "is_anomaly": self.is_anomaly,
            "anomaly_reason": self.anomaly_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ==================== 合规报告 ====================

class ComplianceReportModel(Base):
    """合规报告模型"""
    __tablename__ = "enterprise_compliance_reports"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)

    # 报告类型
    report_type = Column(String(32), nullable=False)  # soc2, gdpr, hipaa, custom

    # 报告周期
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # 报告状态
    status = Column(String(32), default="pending", nullable=False)  # pending, generating, completed, failed

    # 报告内容
    report_data = Column(JSON, nullable=True)  # 报告数据（JSON 格式）
    report_file_path = Column(String(256), nullable=True)  # 报告文件路径

    # 统计摘要
    summary = Column(JSON, nullable=True)  # 报告摘要

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_compliance_tenant_type', 'tenant_id', 'report_type'),
        Index('idx_compliance_date', 'start_date', 'end_date'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "report_type": self.report_type,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "report_data": self.report_data,
            "report_file_path": self.report_file_path,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by
        }
