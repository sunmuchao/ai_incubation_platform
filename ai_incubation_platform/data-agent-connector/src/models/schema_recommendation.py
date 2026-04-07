"""
智能 Schema 推荐模型

实现：
- 推荐规则定义
- 推荐结果存储
- 查询模式分析
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, Index, Integer, JSON, Float, Text, ForeignKey
from models.lineage_db import Base
import uuid

# Base imported from lineage_db


class RecommendationRuleModel(Base):
    """推荐规则模型"""
    __tablename__ = "recommendation_rules"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)

    # 规则类型
    rule_type = Column(String(32), nullable=False, index=True)  # index, partition, normalization, type, redundancy

    # 规则配置
    condition_expression = Column(Text, nullable=True)  # 条件表达式
    recommendation_template = Column(Text, nullable=True)  # 推荐模板

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=50, nullable=False)  # 优先级 0-100

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type,
            "condition_expression": self.condition_expression,
            "recommendation_template": self.recommendation_template,
            "is_active": self.is_active,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }


class RecommendationModel(Base):
    """推荐结果模型"""
    __tablename__ = "recommendations"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 推荐目标
    datasource = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    column_name = Column(String(128), nullable=True)

    # 推荐类型
    recommendation_type = Column(String(32), nullable=False, index=True)  # index, partition, normalization, type, redundancy

    # 推荐内容
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)  # 推荐理由

    # SQL 建议
    suggested_sql = Column(Text, nullable=True)  # 建议执行的 SQL

    # 预期收益
    expected_improvement = Column(String(256), nullable=True)  # 预期提升
    impact_score = Column(Float, nullable=True)  # 影响分数 0-1
    effort_level = Column(String(16), nullable=True)  # low, medium, high

    # 状态
    status = Column(String(16), default="pending", nullable=False, index=True)  # pending, accepted, rejected, applied
    priority = Column(String(16), default="medium", nullable=False)  # low, medium, high, critical

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    applied_at = Column(DateTime, nullable=True)
    applied_by = Column(String(128), nullable=True)
    rejected_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_recommendation_datasource_table', 'datasource', 'table_name'),
        Index('idx_recommendation_type_status', 'recommendation_type', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "recommendation_type": self.recommendation_type,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "suggested_sql": self.suggested_sql,
            "expected_improvement": self.expected_improvement,
            "impact_score": self.impact_score,
            "effort_level": self.effort_level,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "applied_by": self.applied_by,
            "rejected_reason": self.rejected_reason
        }


class QueryPatternModel(Base):
    """查询模式模型"""
    __tablename__ = "query_patterns"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 模式信息
    datasource = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    pattern_type = Column(String(32), nullable=False, index=True)  # frequent_column, join_pattern, filter_pattern, order_pattern

    # 模式内容
    pattern_data = Column(JSON, nullable=False)  # 模式数据
    frequency = Column(Integer, default=0, nullable=False)  # 出现频率

    # 统计信息
    avg_execution_time_ms = Column(Float, nullable=True)
    total_execution_count = Column(Integer, default=0, nullable=False)

    # 时间信息
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_pattern_datasource_table_type', 'datasource', 'table_name', 'pattern_type'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "pattern_type": self.pattern_type,
            "pattern_data": self.pattern_data,
            "frequency": self.frequency,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "total_execution_count": self.total_execution_count,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None
        }


class IndexUsageModel(Base):
    """索引使用统计模型"""
    __tablename__ = "index_usage_stats"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)

    # 索引信息
    datasource = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    index_name = Column(String(128), nullable=False)
    columns = Column(JSON, nullable=False)  # 索引列

    # 使用统计
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # 性能统计
    avg_query_time_ms = Column(Float, nullable=True)
    total_size_bytes = Column(Integer, default=0, nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "index_name": self.index_name,
            "columns": self.columns,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "avg_query_time_ms": self.avg_query_time_ms,
            "total_size_bytes": self.total_size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
