"""
监控指标模型

实现监控数据的数据库存储和查询
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Float, Integer, Text, Boolean, Index, JSON
from models.lineage_db import Base
import uuid

# Base imported from lineage_db


class MetricModel(Base):
    """监控指标模型"""
    __tablename__ = "metrics"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(128), nullable=False, index=True)  # 指标名称
    value = Column(Float, nullable=False)  # 指标值
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 标签 - 用于维度区分
    labels = Column(JSON, nullable=True, default=dict)

    # 数据源/连接器名称
    datasource = Column(String(128), nullable=True, index=True)

    # 指标类型
    metric_type = Column(String(32), nullable=False, index=True)  # counter, gauge, histogram

    __table_args__ = (
        Index('idx_metric_name_time', 'name', 'timestamp'),
        Index('idx_metric_datasource_time', 'datasource', 'timestamp'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "labels": self.labels or {},
            "datasource": self.datasource,
            "metric_type": self.metric_type
        }


class AlertRuleModel(Base):
    """告警规则模型"""
    __tablename__ = "alert_rules"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(256), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # 规则配置
    metric_name = Column(String(128), nullable=False, index=True)
    operator = Column(String(8), nullable=False)  # >, <, >=, <=, ==, !=
    threshold = Column(Float, nullable=False)
    duration_seconds = Column(Integer, default=0, nullable=False)  # 持续时间超过阈值才告警

    # 告警级别
    severity = Column(String(32), default="warning", nullable=False)  # info, warning, error, critical

    # 通知配置
    notify_channels = Column(JSON, nullable=True, default=list)  # email, dingtalk, wechat, slack
    notify_receivers = Column(JSON, nullable=True, default=list)  # 接收人列表

    # 状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    silenced = Column(Boolean, default=False, nullable=False)  # 静默状态
    silenced_until = Column(DateTime, nullable=True)  # 静默直到

    # 审计
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_rule_metric', 'metric_name', 'enabled'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "operator": self.operator,
            "threshold": self.threshold,
            "duration_seconds": self.duration_seconds,
            "severity": self.severity,
            "notify_channels": self.notify_channels or [],
            "notify_receivers": self.notify_receivers or [],
            "enabled": self.enabled,
            "silenced": self.silenced,
            "silenced_until": self.silenced_until.isoformat() if self.silenced_until else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }


class AlertModel(Base):
    """告警记录模型"""
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    rule_id = Column(String(64), nullable=False, index=True)  # 关联的告警规则 ID
    rule_name = Column(String(256), nullable=False)

    # 告警信息
    metric_name = Column(String(128), nullable=False)
    metric_value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    operator = Column(String(8), nullable=False)

    # 告警级别
    severity = Column(String(32), nullable=False)

    # 告警状态
    status = Column(String(32), default="firing", nullable=False, index=True)  # firing, resolved, acknowledged
    message = Column(Text, nullable=True)

    # 时间
    fired_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(128), nullable=True)

    # 通知记录
    notifications_sent = Column(Integer, default=0, nullable=False)
    last_notification_at = Column(DateTime, nullable=True)

    # 附加信息
    labels = Column(JSON, nullable=True, default=dict)
    annotations = Column(JSON, nullable=True, default=dict)

    __table_args__ = (
        Index('idx_alert_status_time', 'status', 'fired_at'),
        Index('idx_alert_rule_time', 'rule_id', 'fired_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "operator": self.operator,
            "severity": self.severity,
            "status": self.status,
            "message": self.message,
            "fired_at": self.fired_at.isoformat() if self.fired_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "notifications_sent": self.notifications_sent,
            "last_notification_at": self.last_notification_at.isoformat() if self.last_notification_at else None,
            "labels": self.labels or {},
            "annotations": self.annotations or {}
        }


class SystemHealthModel(Base):
    """系统健康状态快照"""
    __tablename__ = "system_health"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 系统状态
    status = Column(String(32), default="healthy", nullable=False)  # healthy, degraded, unhealthy

    # 连接池状态
    active_connections = Column(Integer, default=0, nullable=False)
    max_connections = Column(Integer, default=100, nullable=False)
    connection_pool_usage = Column(Float, default=0.0, nullable=False)

    # 查询性能
    current_qps = Column(Float, default=0.0, nullable=False)
    avg_latency_ms = Column(Float, default=0.0, nullable=False)
    p99_latency_ms = Column(Float, default=0.0, nullable=False)
    error_rate = Column(Float, default=0.0, nullable=False)

    # 限流状态
    rate_limit_enabled = Column(Boolean, default=True, nullable=False)
    rate_limit_triggered = Column(Integer, default=0, nullable=False)
    current_concurrent = Column(Integer, default=0, nullable=False)

    # 血缘追踪状态
    total_lineage_nodes = Column(Integer, default=0, nullable=False)
    total_lineage_edges = Column(Integer, default=0, nullable=False)

    # 时间
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_health_status_time', 'status', 'timestamp'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "active_connections": self.active_connections,
            "max_connections": self.max_connections,
            "connection_pool_usage": self.connection_pool_usage,
            "current_qps": self.current_qps,
            "avg_latency_ms": self.avg_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "error_rate": self.error_rate,
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_limit_triggered": self.rate_limit_triggered,
            "current_concurrent": self.current_concurrent,
            "total_lineage_nodes": self.total_lineage_nodes,
            "total_lineage_edges": self.total_lineage_edges,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
