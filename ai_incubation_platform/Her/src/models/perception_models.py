"""
Values: 感知层 - 用户向量表示模型

数字潜意识引擎的核心组件。

功能包括：
- 用户价值观向量（128 维）
- 兴趣偏好向量（64 维）
- 沟通风格向量（32 维）
- 行为模式向量（64 维）
- 向量偏移追踪
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from db.database import Base
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


# ============= Values: 感知层向量模型 =============

class UserVectorDB(Base):
    """用户向量表示"""
    __tablename__ = "user_vectors"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 价值观向量 (128 维)
    # 编码用户的核心价值观和信念
    values_vector = Column(Text, nullable=True)  # JSON 字符串，存储 128 维浮点数列表

    # 兴趣偏好向量 (64 维)
    # 编码用户的兴趣爱好和偏好
    interests_vector = Column(Text, nullable=True)  # JSON 字符串，存储 64 维浮点数列表

    # 沟通风格向量 (32 维)
    # 编码用户的沟通模式和风格
    communication_style_vector = Column(Text, nullable=True)  # JSON 字符串，存储 32 维浮点数列表

    # 行为模式向量 (64 维)
    # 编码用户的行为习惯和模式
    behavior_pattern_vector = Column(Text, nullable=True)  # JSON 字符串，存储 64 维浮点数列表

    # 向量维度
    values_dimension = Column(Integer, default=128)
    interests_dimension = Column(Integer, default=64)
    communication_style_dimension = Column(Integer, default=32)
    behavior_pattern_dimension = Column(Integer, default=64)

    # 向量版本（用于追踪更新）
    vector_version = Column(Integer, default=1)

    # 来源
    # static (静态计算), incremental (增量更新), ml_inferred (ML 推断)
    vector_source = Column(String(30), default="static")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_computed_at = Column(DateTime(timezone=True), nullable=True)

    # 索引
    __table_args__ = (
        UniqueConstraint('user_id', name='uniq_user_id_vector'),
    )


class VectorUpdateHistoryDB(Base):
    """向量更新历史"""
    __tablename__ = "vector_update_history"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 更新的向量类型
    # values, interests, communication_style, behavior_pattern
    vector_type = Column(String(30), nullable=False, index=True)

    # 更新前的向量
    previous_vector = Column(Text, nullable=True)  # JSON 字符串

    # 更新后的向量
    new_vector = Column(Text, nullable=False)  # JSON 字符串

    # 向量变化量（欧几里得距离）
    vector_drift = Column(Float, default=0.0)

    # 更新原因
    # behavior_event (行为事件), periodic_update (定期更新), manual_adjustment (手动调整)
    update_reason = Column(String(30), default="behavior_event")

    # 触发更新的事件 ID（如果有）
    trigger_event_id = Column(String(36), nullable=True)

    # 更新详情
    update_details = Column(Text, default="")  # JSON 字符串

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VectorSimilarityCacheDB(Base):
    """向量相似度缓存"""
    __tablename__ = "vector_similarity_cache"

    id = Column(String(36), primary_key=True, index=True)

    # 用户 A
    user_a_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 用户 B
    user_b_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 相似度类型
    # values, interests, communication_style, behavior_pattern, overall
    similarity_type = Column(String(30), nullable=False, index=True)

    # 相似度分数 (0-1)
    similarity_score = Column(Float, nullable=False)

    # 计算详情
    calculation_details = Column(Text, default="")  # JSON 字符串

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 索引
    __table_args__ = (
        UniqueConstraint('user_a_id', 'user_b_id', 'similarity_type', name='uniq_user_pair_similarity'),
    )


class DigitalSubconsciousProfileDB(Base):
    """数字潜意识画像"""
    __tablename__ = "digital_subconscious_profiles"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 潜意识特征标签
    # 基于向量分析得出的隐性特征
    # 如："security_seeking"（寻求安全感）, "achievement_oriented"（成就导向）
    subconscious_traits = Column(Text, default="")  # JSON 字符串

    # 隐性需求
    # 用户未明确表达但通过行为推断的需求
    hidden_needs = Column(Text, default="")  # JSON 字符串

    # 情感倾向
    # positive (积极), neutral (中性), negative (消极), anxious (焦虑)
    emotional_tendency = Column(String(20), default="neutral")

    # 依恋风格
    # secure (安全型), anxious (焦虑型), avoidant (回避型), disorganized (混乱型)
    attachment_style = Column(String(20), nullable=True)

    # 关系模式
    # 用户在关系中反复出现的行为模式
    relationship_patterns = Column(Text, default="")  # JSON 字符串

    # 成长建议
    # 基于潜意识分析的个人成长建议
    growth_suggestions = Column(Text, default="")  # JSON 字符串

    # 置信度
    confidence_score = Column(Float, default=0.5)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)


class BehaviorVectorMappingDB(Base):
    """行为 - 向量映射规则"""
    __tablename__ = "behavior_vector_mappings"

    id = Column(String(36), primary_key=True, index=True)

    # 行为类型
    behavior_type = Column(String(50), nullable=False, unique=True, index=True)

    # 影响的向量类型
    affected_vector_types = Column(Text, nullable=False)  # JSON 字符串

    # 映射规则
    # 定义行为如何影响向量各维度
    mapping_rules = Column(Text, nullable=False)  # JSON 字符串

    # 影响权重
    impact_weights = Column(Text, default="")  # JSON 字符串

    # 是否激活
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================
# 常量定义
# ============================================

# 向量维度配置
VECTOR_DIMENSIONS = {
    "values": 128,
    "interests": 64,
    "communication_style": 32,
    "behavior_pattern": 64,
}

# 潜意识特征标签库
SUBCONSCIOUS_TRAITS_LIBRARY = {
    "security_seeking": "寻求安全感，偏好稳定和可预测性",
    "achievement_oriented": "成就导向，追求目标和成功",
    "connection_seeking": "寻求连接，渴望深度关系",
    "autonomy_valuing": "重视自主，需要独立空间",
    "growth_minded": "成长型思维，乐于接受挑战",
    "comfort_seeking": "寻求舒适，避免不适",
    "validation_seeking": "寻求认可，需要他人肯定",
    "meaning_seeking": "寻求意义，追求深层价值",
    "novelty_seeking": "寻求新奇，喜欢尝试新事物",
    "harmony_seeking": "寻求和谐，避免冲突",
}

# 依恋风格描述
ATTACHMENT_STYLE_DESCRIPTIONS = {
    "secure": "安全型：能够建立健康、稳定的亲密关系",
    "anxious": "焦虑型：渴望亲密但担心被抛弃",
    "avoidant": "回避型：倾向于保持情感距离，避免过度依赖",
    "disorganized": "混乱型：对亲密关系感到矛盾和困惑",
}


# ============================================
# 模型导出
# ============================================

__all__ = [
    'UserVectorDB',
    'VectorUpdateHistoryDB',
    'VectorSimilarityCacheDB',
    'DigitalSubconsciousProfileDB',
    'BehaviorVectorMappingDB',
    'VECTOR_DIMENSIONS',
    'SUBCONSCIOUS_TRAITS_LIBRARY',
    'ATTACHMENT_STYLE_DESCRIPTIONS',
]
