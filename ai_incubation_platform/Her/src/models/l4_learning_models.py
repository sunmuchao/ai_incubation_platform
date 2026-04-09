"""
L4: AI 持续学习模型

功能包括：
- 用户偏好记忆
- 历史行为学习
- 个性化推荐权重调整
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base


class UserPreferenceMemory(Base):
    """
    用户偏好记忆

    存储从用户历史行为中学习到的偏好
    """
    __tablename__ = "user_preference_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)

    # 偏好类别
    category = Column(String(50), nullable=False)  # matching/date/gift/communication/topic
    subcategory = Column(String(50))  # 子类别

    # 偏好内容
    preference_type = Column(String(50))  # like/dislike/neutral
    preference_key = Column(String(100), nullable=False)  # 偏好键，如"旅行地点"
    preference_value = Column(JSON)  # 偏好值，如["山区", "海边"]

    # 偏好强度 (0-1)
    confidence_score = Column(Float, default=0.5)

    # 来源
    source_events = Column(JSON, default=list)  # 来源事件 ID 列表
    inference_method = Column(String(50))  # 推断方法：rule_based/ml/llm

    # 状态
    is_active = Column(Boolean, default=True)
    last_verified_at = Column(DateTime)  # 最后验证时间

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_user_pref_category", "user_id", "category"),
        Index("idx_user_pref_key", "user_id", "preference_key"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category,
            "subcategory": self.subcategory,
            "preference_type": self.preference_type,
            "preference_key": self.preference_key,
            "preference_value": self.preference_value,
            "confidence_score": self.confidence_score,
            "source_events": self.source_events,
            "inference_method": self.inference_method,
            "is_active": self.is_active,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BehaviorLearningPattern(Base):
    """
    行为学习模式

    从用户历史行为中学习到的模式
    """
    __tablename__ = "behavior_learning_patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)

    # 模式类型
    pattern_type = Column(String(50), nullable=False)
    # online_time: 活跃时间段
    # response_style: 回复风格
    # matching_preference: 匹配偏好
    # communication_habit: 沟通习惯
    # dating_preference: 约会偏好

    # 模式数据
    pattern_data = Column(JSON, nullable=False, default=dict)

    # 模式强度 (0-1)
    pattern_strength = Column(Float, default=0.0)

    # 观察次数
    observation_count = Column(Integer, default=1)

    # 最后观察到时间
    last_observed_at = Column(DateTime)

    # 状态
    is_validated = Column(Boolean, default=False)  # 是否已验证
    validation_source = Column(String(50))  # 验证来源：explicit/implicit

    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_user_behavior_pattern", "user_id", "pattern_type"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "pattern_type": self.pattern_type,
            "pattern_data": self.pattern_data,
            "pattern_strength": self.pattern_strength,
            "observation_count": self.observation_count,
            "last_observed_at": self.last_observed_at.isoformat() if self.last_observed_at else None,
            "is_validated": self.is_validated,
            "validation_source": self.validation_source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MatchingWeightAdjustment(Base):
    """
    匹配权重调整记录

    记录 AI 根据用户行为学习的匹配权重调整
    """
    __tablename__ = "ai_matching_weight_adjustments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)

    # 调整原因
    adjustment_reason = Column(String(100))
    # "values_shift_detected" - 价值观偏移
    # "behavior_pattern_learned" - 行为模式学习
    # "explicit_feedback" - 显式反馈
    # "implicit_preference" - 隐式偏好

    # 调整内容
    before_weights = Column(JSON, default=dict)  # 调整前权重
    after_weights = Column(JSON, default=dict)  # 调整后权重

    # 调整幅度
    adjustment_magnitude = Column(Float, default=0.0)

    # 触发事件
    trigger_event_id = Column(String(64))  # 触发事件 ID
    trigger_event_type = Column(String(50))  # 触发事件类型

    # AI 分析
    ai_reasoning = Column(Text)  # AI 推理说明
    confidence_score = Column(Float, default=0.0)  # 置信度

    # 用户反馈
    user_feedback = Column(String(20))  # approved/rejected/no_response
    user_feedback_at = Column(DateTime)

    # 状态
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_user_weight_adj", "user_id", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "adjustment_reason": self.adjustment_reason,
            "before_weights": self.before_weights,
            "after_weights": self.after_weights,
            "adjustment_magnitude": self.adjustment_magnitude,
            "trigger_event_id": self.trigger_event_id,
            "trigger_event_type": self.trigger_event_type,
            "ai_reasoning": self.ai_reasoning,
            "confidence_score": self.confidence_score,
            "user_feedback": self.user_feedback,
            "user_feedback_at": self.user_feedback_at.isoformat() if self.user_feedback_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserLearningProfile(Base):
    """
    用户学习画像汇总

    汇总用户的学习状态和 AI 认知进度
    """
    __tablename__ = "user_learning_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, unique=True, index=True)

    # 学习阶段
    learning_stage = Column(String(20), default="initial")
    # initial: 初始阶段
    # exploring: 探索阶段
    # learning: 学习阶段
    # personalized: 个性化阶段
    # mastered: 精通阶段

    # 学习进度 (0-100)
    learning_progress = Column(Integer, default=0)

    # 已学习偏好数量
    learned_preferences_count = Column(Integer, default=0)

    # 已验证模式数量
    validated_patterns_count = Column(Integer, default=0)

    # AI 理解度评分 (0-100)
    ai_understanding_score = Column(Float, default=0.0)

    # 用户满意度评分 (0-100)
    user_satisfaction_score = Column(Float, default=0.0)

    # 偏好摘要
    preference_summary = Column(JSON, default=dict)
    # {
    #     "matching": {"top_likes": [...], "top_dislikes": [...]},
    #     "communication": {"style": "...", "preferences": [...]},
    #     "dating": {"preferred_activities": [...], "avoided_places": [...]}
    # }

    # 最后学习时间
    last_learning_at = Column(DateTime)

    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "learning_stage": self.learning_stage,
            "learning_progress": self.learning_progress,
            "learned_preferences_count": self.learned_preferences_count,
            "validated_patterns_count": self.validated_patterns_count,
            "ai_understanding_score": self.ai_understanding_score,
            "user_satisfaction_score": self.user_satisfaction_score,
            "preference_summary": self.preference_summary,
            "last_learning_at": self.last_learning_at.isoformat() if self.last_learning_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
