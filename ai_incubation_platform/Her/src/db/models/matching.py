"""
SQLAlchemy 数据模型 - 匹配领域

包含：匹配历史、滑动动作、用户偏好、反馈学习等
"""
from db.models.base import *

class MatchHistoryDB(Base):
    """匹配历史记录"""
    __tablename__ = "match_history"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), nullable=False, index=True)
    user_id_2 = Column(String(36), nullable=False, index=True)
    compatibility_score = Column(Float, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    match_reasoning = Column(Text, default="")
    common_interests = Column(Text, default="")
    score_breakdown = Column(Text, default="")

    interaction_count = Column(Integer, default=0)
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)
    relationship_stage = Column(String(20), default="matched")


class SwipeActionDB(Base):
    """用户滑动动作记录"""
    __tablename__ = "swipe_actions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(20), nullable=False)
    is_matched = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserPreferenceDB(Base):
    """用户匹配偏好设置"""
    __tablename__ = "user_preferences"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    preferred_age_range = Column(JSON, default=[18, 60])
    preferred_location_range = Column(Integer, default=50)
    preferred_distance = Column(Integer, default=100)
    preferred_height_range = Column(JSON, nullable=True)
    preferred_education = Column(Text, default="")
    preferred_income_range = Column(JSON, nullable=True)

    preference_weights = Column(JSON, default={
        "age": 0.2, "location": 0.2, "interests": 0.3, "values": 0.3
    })

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserRelationshipPreferenceDB(Base):
    """用户关系类型偏好"""
    __tablename__ = "user_relationship_preferences"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    relationship_types = Column(Text, default="")
    current_status = Column(String(50), nullable=True)
    expectation_description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MatchInteractionDB(Base):
    """匹配交互反馈"""
    __tablename__ = "match_interactions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    interaction_type = Column(String(50), nullable=False)
    dwell_time_seconds = Column(Integer, default=0)
    positive_signal = Column(Boolean, default=True)
    signal_strength = Column(Float, default=1.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QuickStartRecordDB(Base):
    """快速入门记录"""
    __tablename__ = "quick_start_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    location = Column(String(200), nullable=False)
    relationship_goal = Column(String(50), nullable=False)

    initial_match_ids = Column(Text, default="")
    initial_match_count = Column(Integer, default=0)

    viewed_count = Column(Integer, default=0)
    liked_count = Column(Integer, default=0)
    disliked_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)

    first_like_at = Column(DateTime(timezone=True), nullable=True)
    first_chat_at = Column(DateTime(timezone=True), nullable=True)
    completed_quick_start = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserFeedbackLearningDB(Base):
    """用户反馈学习记录"""
    __tablename__ = "user_feedback_learning"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    feedback_type = Column(String(20), nullable=False)
    target_match_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    dislike_reason = Column(String(50), nullable=True)
    dislike_detail = Column(Text, nullable=True)

    learned_preference_dimension = Column(String(50), nullable=True)
    learned_preference_value = Column(JSON, nullable=True)
    confidence_score = Column(Float, default=0.5)

    vector_dims_before = Column(Text, nullable=True)
    vector_dims_after = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImplicitInferenceDB(Base):
    """隐性偏好推断记录"""
    __tablename__ = "implicit_inferences"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    inference_source = Column(String(50), nullable=False)
    inferred_dimension = Column(String(50), nullable=False)
    inferred_value = Column(JSON, nullable=False)
    confidence = Column(Float, default=0.5)

    behavior_evidence = Column(Text, nullable=True)
    vector_dim_index = Column(Integer, nullable=True)

    inferred_at = Column(DateTime(timezone=True), server_default=func.now())

__all__ = [
    "MatchHistoryDB", "SwipeActionDB", "UserPreferenceDB",
    "UserRelationshipPreferenceDB", "MatchInteractionDB",
    "QuickStartRecordDB", "UserFeedbackLearningDB", "ImplicitInferenceDB"
]