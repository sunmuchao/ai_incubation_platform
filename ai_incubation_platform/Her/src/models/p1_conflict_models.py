"""
P1: 冲突处理模型

从"静态标签匹配"转向"动态共鸣演算法"的核心组件。

功能包括：
- 冲突处理风格识别（回避型/对抗型/协商型）
- 冲突兼容性评估
- 冲突历史追踪
- 冲突化解建议生成
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from db.database import Base
from typing import Optional, Dict, Any
from datetime import datetime
import json


# ============= P1: 冲突处理模型 =============

class ConflictStyleDB(Base):
    """用户冲突处理风格"""
    __tablename__ = "conflict_styles"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 主要冲突处理风格
    primary_style = Column(String(30), nullable=False)
    # 风格类型:
    # - avoiding: 回避型（倾向于避免冲突）
    # - competing: 对抗型（倾向于坚持己见）
    # - accommodating: 迁就型（倾向于让步）
    # - compromising: 妥协型（倾向于折中）
    # - collaborating: 协商型（倾向于共同解决）

    # 各风格得分（0-100）
    avoiding_score = Column(Integer, default=0)
    competing_score = Column(Integer, default=0)
    accommodating_score = Column(Integer, default=0)
    compromising_score = Column(Integer, default=0)
    collaborating_score = Column(Integer, default=0)

    # 风格描述
    style_description = Column(Text, nullable=True)

    # 冲突触发点
    conflict_triggers = Column(Text, default="")  # JSON 字符串，容易引发冲突的话题

    # 评估方式
    assessment_method = Column(String(50), default=" questionnaire")
    # questionnaire (问卷), behavior_analysis (行为分析), ai_assessment (AI 评估)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_assessed_at = Column(DateTime(timezone=True), nullable=True)


class ConflictHistoryDB(Base):
    """用户冲突历史记录"""
    __tablename__ = "conflict_histories"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 冲突类型
    conflict_type = Column(String(50), nullable=False)
    # 类型列表:
    # - values_mismatch: 价值观分歧
    # - communication_issue: 沟通问题
    # - expectation_gap: 期望落差
    # - boundary_violation: 边界侵犯
    # - resource_dispute: 资源争议
    # - personality_clash: 性格冲突

    # 冲突主题
    conflict_topic = Column(String(200), nullable=True)  # 具体争议话题

    # 冲突描述
    conflict_description = Column(Text, nullable=True)

    # 处理方式
    handling_style = Column(String(30), nullable=True)  # 本次采用的处理方式
    handling_effectiveness = Column(Integer, default=0)  # 处理效果评分 (1-10)

    # 冲突结果
    resolution_status = Column(String(20), default="unresolved")
    # unresolved, resolved, escalated, abandoned

    resolution_description = Column(Text, nullable=True)  # 解决结果描述

    # 关系影响
    relationship_impact = Column(Integer, default=0)  # 对关系的影响 (-10 到 +10)

    # 学习与成长
    lessons_learned = Column(Text, nullable=True)  # 从中学到的经验

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class ConflictCompatibilityDB(Base):
    """双方冲突兼容性评估"""
    __tablename__ = "conflict_compatibility"

    id = Column(String(36), primary_key=True, index=True)

    # 双方用户
    user_a_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_b_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 兼容性评分
    compatibility_score = Column(Float, default=0.5)  # 0-1

    # 各维度兼容性
    style_compatibility = Column(Float, default=0.5)  # 风格兼容性
    trigger_compatibility = Column(Float, default=0.5)  # 触发点兼容性
    resolution_compatibility = Column(Float, default=0.5)  # 解决方式兼容性

    # 兼容性详情
    compatibility_details = Column(Text, default="")  # JSON 字符串

    # 风险提示
    risk_factors = Column(Text, default="")  # JSON 字符串，潜在冲突风险

    # 建议
    suggestions = Column(Text, default="")  # JSON 字符串，相处建议

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 索引
    __table_args__ = (
        UniqueConstraint('user_a_id', 'user_b_id', name='uniq_user_pair_conflict'),
    )


class ConflictResolutionTipDB(Base):
    """冲突化解建议库"""
    __tablename__ = "conflict_resolution_tips"

    id = Column(String(36), primary_key=True, index=True)

    # 冲突类型
    conflict_type = Column(String(50), nullable=False, index=True)

    # 风格组合
    style_combination = Column(String(100), nullable=True)
    # 如："avoiding_vs_competing", "collaborating_vs_collaborating"

    # 建议内容
    tip_title = Column(String(200), nullable=False)
    tip_content = Column(Text, nullable=False)

    # 建议类型
    tip_type = Column(String(30), default="general")
    # general (通用), prevention (预防), intervention (干预), recovery (修复)

    # 适用场景
    applicable_scenarios = Column(Text, default="")  # JSON 字符串

    # 心理学依据
    psychological_basis = Column(Text, nullable=True)

    # 有效性评分
    effectiveness_rating = Column(Float, default=0.0)  # 用户评分
    effectiveness_count = Column(Integer, default=0)  # 评分次数

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class CommunicationPatternDB(Base):
    """沟通模式识别"""
    __tablename__ = "communication_patterns"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 沟通风格
    communication_style = Column(String(50), nullable=True)
    # direct (直接型), indirect (委婉型), analytical (分析型), emotional (情感型)

    # 沟通频率偏好
    preferred_frequency = Column(String(30), nullable=True)
    # daily, several_times_week, weekly, as_needed

    # 沟通渠道偏好
    preferred_channels = Column(Text, default="")  # JSON 字符串

    # 沟通时间偏好
    preferred_time = Column(String(50), nullable=True)  # morning, afternoon, evening, night

    # 响应模式
    response_pattern = Column(String(30), nullable=True)
    # immediate (即时回复), delayed (延迟回复), batch (批量回复)

    # 沟通深度
    depth_preference = Column(String(30), nullable=True)
    # superficial (表面), moderate (中等), deep (深度)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================
# 模型导出
# ============================================

__all__ = [
    'ConflictStyleDB',
    'ConflictHistoryDB',
    'ConflictCompatibilityDB',
    'ConflictResolutionTipDB',
    'CommunicationPatternDB',
]
