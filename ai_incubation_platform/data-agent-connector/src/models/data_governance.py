"""
数据治理模型

实现：
- 数据分类与标签
- 敏感数据识别
- 脱敏策略
- 治理指标
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, Index, Integer, JSON, Float, Text, ForeignKey
from models.lineage_db import Base
import uuid

# Base imported from lineage_db


class DataClassificationModel(Base):
    """数据分类模型"""
    __tablename__ = "data_classifications"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 分类信息
    name = Column(String(128), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(String(64), ForeignKey("data_classifications.id"), nullable=True, index=True)

    # 分类级别 (L1-L4)
    level = Column(Integer, default=1, nullable=False)  # 1=一级分类，2=二级分类...

    # 分类标签
    tags = Column(JSON, nullable=True, default=list)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "level": self.level,
            "tags": self.tags or [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }


class DataLabelModel(Base):
    """数据标签模型"""
    __tablename__ = "data_labels"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 标签目标
    datasource = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    column_name = Column(String(128), nullable=True, index=True)

    # 标签信息
    label_type = Column(String(32), nullable=False, index=True)  # classification, sensitivity, business, custom
    label_key = Column(String(128), nullable=False)
    label_value = Column(String(256), nullable=True)

    # 标签来源 (auto=自动识别，manual=手动标注)
    source = Column(String(16), default="manual", nullable=False)
    confidence = Column(Float, nullable=True)  # 自动识别的置信度

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_label_datasource_table', 'datasource', 'table_name'),
        Index('idx_label_type_key', 'label_type', 'label_key'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "label_type": self.label_type,
            "label_key": self.label_key,
            "label_value": self.label_value,
            "source": self.source,
            "confidence": self.confidence,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }


class SensitivityLevelModel(Base):
    """敏感数据级别模型"""
    __tablename__ = "sensitivity_levels"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 级别定义
    name = Column(String(64), nullable=False, unique=True)  # public, internal, confidential, restricted
    level = Column(Integer, nullable=False, unique=True)  # 1=公开，2=内部，3=机密，4=绝密
    description = Column(Text, nullable=True)
    color = Column(String(16), nullable=True)  # 显示颜色

    # 处理要求
    encryption_required = Column(Boolean, default=False)
    masking_required = Column(Boolean, default=False)
    audit_required = Column(Boolean, default=True)
    access_control = Column(String(32), default="rbac")  # none, rbac, abac

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "description": self.description,
            "color": self.color,
            "encryption_required": self.encryption_required,
            "masking_required": self.masking_required,
            "audit_required": self.audit_required,
            "access_control": self.access_control,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


class MaskingPolicyModel(Base):
    """脱敏策略模型"""
    __tablename__ = "masking_policies"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 策略信息
    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # 适用条件
    sensitivity_level = Column(String(64), nullable=True)  # 适用的敏感级别
    data_type = Column(String(32), nullable=True)  # 适用的数据类型 (string, number, date, email, phone)
    column_pattern = Column(String(128), nullable=True)  # 列名匹配模式 (如：*email*, *phone*)

    # 脱敏方法
    masking_type = Column(String(32), nullable=False)  # full, partial, hash, encrypt, redact
    masking_params = Column(JSON, nullable=True)  # 脱敏参数

    # 脱敏规则示例
    # full: 完全遮蔽 -> "******"
    # partial: {"keep_first": 2, "keep_last": 2, "mask_char": "*"} -> "张*"
    # hash: {"algorithm": "sha256"}
    # encrypt: {"algorithm": "aes256"}
    # redact: {"replacement": "[REDACTED]"}

    # 优先级
    priority = Column(Integer, default=100, nullable=False)  # 数值越小优先级越高

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sensitivity_level": self.sensitivity_level,
            "data_type": self.data_type,
            "column_pattern": self.column_pattern,
            "masking_type": self.masking_type,
            "masking_params": self.masking_params or {},
            "priority": self.priority,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }


class GovernanceMetricModel(Base):
    """治理指标模型"""
    __tablename__ = "governance_metrics"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 指标维度
    datasource = Column(String(128), nullable=True, index=True)
    table_name = Column(String(128), nullable=True, index=True)

    # 指标类型
    metric_type = Column(String(32), nullable=False, index=True)
    # governance_score, classification_coverage, sensitivity_coverage
    # quality_score, lineage_coverage, policy_compliance

    # 指标值
    metric_value = Column(Float, nullable=False)  # 0-100
    target_value = Column(Float, nullable=True)  # 目标值

    # 时间维度
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(16), nullable=False)  # hour, day, week, month

    # 趋势
    previous_value = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    trend = Column(String(16), nullable=True)  # improving, declining, stable

    # 详情
    details = Column(JSON, nullable=True)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_metric_datasource_period', 'datasource', 'period_start'),
        Index('idx_metric_type_period', 'metric_type', 'period_start'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "metric_type": self.metric_type,
            "metric_value": self.metric_value,
            "target_value": self.target_value,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "period_type": self.period_type,
            "previous_value": self.previous_value,
            "change_percent": self.change_percent,
            "trend": self.trend,
            "details": self.details or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


class SensitiveDataRecordModel(Base):
    """敏感数据记录模型"""
    __tablename__ = "sensitive_data_records"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 数据位置
    datasource = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    column_name = Column(String(128), nullable=False, index=True)

    # 敏感信息
    sensitivity_level = Column(String(64), nullable=False, index=True)
    sensitivity_score = Column(Float, default=0, nullable=False)  # 0-1

    # 识别信息
    detection_method = Column(String(32), nullable=False)  # pattern, ml, manual, rule
    pattern_type = Column(String(64), nullable=True)  # email, phone, ssn, credit_card, etc.
    confidence = Column(Float, nullable=True)  # 识别置信度

    # 样本信息 (不存储实际数据，只存储样本数量等统计信息)
    sample_count = Column(Integer, default=0)
    total_rows = Column(Integer, default=0)

    # 处理状态
    is_masked = Column(Boolean, default=False)
    masking_policy_id = Column(String(64), ForeignKey("masking_policies.id"), nullable=True)
    is_reviewed = Column(Boolean, default=False)
    reviewed_by = Column(String(128), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    # 审计字段
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_sensitive_datasource_table', 'datasource', 'table_name'),
        Index('idx_sensitive_level_masked', 'sensitivity_level', 'is_masked'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "sensitivity_level": self.sensitivity_level,
            "sensitivity_score": self.sensitivity_score,
            "detection_method": self.detection_method,
            "pattern_type": self.pattern_type,
            "confidence": self.confidence,
            "sample_count": self.sample_count,
            "total_rows": self.total_rows,
            "is_masked": self.is_masked,
            "masking_policy_id": self.masking_policy_id,
            "is_reviewed": self.is_reviewed,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "created_by": self.created_by
        }
