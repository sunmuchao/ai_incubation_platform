"""
数据质量监控模型

实现：
- 质量规则定义
- 质量检查结果
- 异常检测记录
- 质量指标统计
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, Index, Integer, JSON, Float, Text, ForeignKey
from models.lineage_db import Base
import uuid

# Base imported from lineage_db


class QualityRuleModel(Base):
    """质量规则模型"""
    __tablename__ = "quality_rules"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)

    # 规则目标
    datasource = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    column_name = Column(String(128), nullable=True)

    # 规则定义
    rule_type = Column(String(32), nullable=False, index=True)  # completeness, accuracy, consistency, timeliness, anomaly
    rule_expression = Column(Text, nullable=False)  # 规则表达式/SQL
    threshold = Column(Float, nullable=True)  # 阈值
    operator = Column(String(16), default=">=", nullable=True)  # >=, <=, >, <, =

    # 严重级别
    severity = Column(String(16), default="warning", nullable=False)  # info, warning, error, critical

    # 调度配置
    schedule_enabled = Column(Boolean, default=False, nullable=False)
    schedule_cron = Column(String(64), nullable=True)  # cron 表达式
    schedule_interval_seconds = Column(Integer, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)
    last_checked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_rule_datasource_table', 'datasource', 'table_name'),
        Index('idx_rule_type_active', 'rule_type', 'is_active'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "rule_type": self.rule_type,
            "rule_expression": self.rule_expression,
            "threshold": self.threshold,
            "operator": self.operator,
            "severity": self.severity,
            "schedule_enabled": self.schedule_enabled,
            "schedule_cron": self.schedule_cron,
            "schedule_interval_seconds": self.schedule_interval_seconds,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None
        }


class QualityResultModel(Base):
    """质量检查结果模型"""
    __tablename__ = "quality_results"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    rule_id = Column(String(64), ForeignKey("quality_rules.id"), nullable=False, index=True)

    # 检查结果
    status = Column(String(16), nullable=False, index=True)  # passed, failed, warning, error
    actual_value = Column(Float, nullable=True)  # 实际检测值
    expected_value = Column(Float, nullable=True)  # 期望值/阈值

    # 详细指标
    metrics = Column(JSON, nullable=True, default=dict)  # 检测指标详情

    # 错误样本
    error_count = Column(Integer, default=0, nullable=False)
    total_count = Column(Integer, default=0, nullable=False)
    error_rate = Column(Float, nullable=True)  # 错误率
    error_samples = Column(JSON, nullable=True)  # 错误样本（前 N 条）

    # 执行信息
    execution_time_ms = Column(Integer, nullable=True)  # 执行耗时
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 审计字段
    created_by = Column(String(128), nullable=True)  # 执行者（系统/用户）

    __table_args__ = (
        Index('idx_result_rule_time', 'rule_id', 'checked_at'),
        Index('idx_result_status_time', 'status', 'checked_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "status": self.status,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "metrics": self.metrics or {},
            "error_count": self.error_count,
            "total_count": self.total_count,
            "error_rate": self.error_rate,
            "error_samples": self.error_samples or [],
            "execution_time_ms": self.execution_time_ms,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "created_by": self.created_by
        }


class AnomalyModel(Base):
    """异常记录模型"""
    __tablename__ = "data_anomalies"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 数据位置
    datasource = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    column_name = Column(String(128), nullable=False, index=True)
    row_id = Column(String(256), nullable=True)  # 异常行标识

    # 异常类型
    anomaly_type = Column(String(32), nullable=False, index=True)  # value, distribution, trend, pattern
    detection_method = Column(String(32), nullable=False)  # statistical, ml, rule

    # 异常评分
    anomaly_score = Column(Float, nullable=False)  # 异常分数 0-1
    confidence = Column(Float, nullable=True)  # 置信度

    # 异常值
    expected_value = Column(String(256), nullable=True)
    actual_value = Column(String(256), nullable=True)
    deviation = Column(Float, nullable=True)  # 偏离程度

    # 上下文信息
    context = Column(JSON, nullable=True)  # 异常上下文
    time_series_window = Column(JSON, nullable=True)  # 时间序列窗口数据

    # 处理状态
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(128), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # 审计字段
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String(128), nullable=True)  # 检测系统

    __table_args__ = (
        Index('idx_anomaly_datasource_time', 'datasource', 'detected_at'),
        Index('idx_anomaly_type_resolved', 'anomaly_type', 'is_resolved'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "row_id": self.row_id,
            "anomaly_type": self.anomaly_type,
            "detection_method": self.detection_method,
            "anomaly_score": self.anomaly_score,
            "confidence": self.confidence,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "deviation": self.deviation,
            "context": self.context or {},
            "is_resolved": self.is_resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "created_by": self.created_by
        }


class QualityDashboardModel(Base):
    """质量仪表盘聚合模型"""
    __tablename__ = "quality_dashboard"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 聚合维度
    datasource = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=True, index=True)
    rule_type = Column(String(32), nullable=True, index=True)

    # 时间维度
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(16), nullable=False)  # hour, day, week, month

    # 聚合指标
    total_rules = Column(Integer, default=0, nullable=False)
    passed_rules = Column(Integer, default=0, nullable=False)
    failed_rules = Column(Integer, default=0, nullable=False)
    warning_rules = Column(Integer, default=0, nullable=False)

    # 质量分数
    quality_score = Column(Float, default=100.0, nullable=False)  # 0-100

    # 趋势
    score_change = Column(Float, nullable=True)  # 相比上一周期的变化
    trend = Column(String(16), nullable=True)  # improving, declining, stable

    # 详情
    top_failed_rules = Column(JSON, nullable=True)  # 失败规则 TOP N
    recent_anomalies = Column(JSON, nullable=True)  # 最近异常

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_dashboard_datasource_period', 'datasource', 'period_start'),
        Index('idx_dashboard_table_period', 'table_name', 'period_start'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "rule_type": self.rule_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "period_type": self.period_type,
            "total_rules": self.total_rules,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "warning_rules": self.warning_rules,
            "quality_score": self.quality_score,
            "score_change": self.score_change,
            "trend": self.trend,
            "top_failed_rules": self.top_failed_rules or [],
            "recent_anomalies": self.recent_anomalies or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
