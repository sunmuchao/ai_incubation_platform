"""
SQLAlchemy 数据模型 - 用户画像领域

包含：用户向量画像、画像推断记录、第三方授权、游戏测试等
"""
from db.models.base import *

class UserVectorProfileDB(Base):
    """用户向量画像"""
    __tablename__ = "user_vector_profiles"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    vector = Column(Text, nullable=False)
    dimensions_detail = Column(Text, default="")

    completeness_ratio = Column(Float, default=0.0)
    weighted_completeness = Column(Float, default=0.0)
    recommended_strategy = Column(String(20), default="cold_start")

    category_completeness = Column(Text, default="")

    critical_dimensions_filled = Column(Boolean, default=False)
    missing_critical_dimensions = Column(Text, default="")

    source_stats = Column(Text, default="")

    version = Column(String(20), default="v1.0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ProfileInferenceRecordDB(Base):
    """画像推断记录"""
    __tablename__ = "profile_inference_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    inference_source = Column(String(50), nullable=False)
    inference_method = Column(String(100), nullable=False)

    inferred_dimensions = Column(Text, nullable=False)
    overall_confidence = Column(Float, default=0.0)

    evidence = Column(Text, nullable=True)
    sample_size = Column(Integer, default=0)

    llm_model = Column(String(100), nullable=True)
    llm_tokens_used = Column(Integer, default=0)

    inferred_at = Column(DateTime(timezone=True), server_default=func.now())


class ThirdPartyAuthRecordDB(Base):
    """第三方授权记录"""
    __tablename__ = "third_party_auth_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    provider = Column(String(50), nullable=False, index=True)

    provider_user_id = Column(String(100), nullable=True)
    access_token_hash = Column(String(64), nullable=True)

    auth_scope = Column(Text, default="")

    status = Column(String(20), default="active")

    data_used_for = Column(Text, default="")

    authorized_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class GameTestRecordDB(Base):
    """游戏化测试记录"""
    __tablename__ = "game_test_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    test_type = Column(String(50), nullable=False, index=True)

    dimension_scores = Column(Text, nullable=False)
    test_report = Column(Text, nullable=True)

    answers = Column(Text, default="")

    reward_given = Column(Boolean, default=False)
    reward_type = Column(String(50), nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    time_spent_seconds = Column(Integer, default=0)


class UserSocialMetricsDB(Base):
    """用户社会认同指标"""
    __tablename__ = "user_social_metrics"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    like_count = Column(Integer, default=0)
    pass_count = Column(Integer, default=0)
    dislike_count = Column(Integer, default=0)
    like_rate = Column(Float, default=0.5)

    chat_initiated_count = Column(Integer, default=0)
    chat_response_count = Column(Integer, default=0)
    chat_response_rate = Column(Float, default=0.5)
    avg_chat_duration_minutes = Column(Float, default=0.0)

    success_match_count = Column(Integer, default=0)
    avg_relationship_duration = Column(Float, default=0.0)

    reputation_score = Column(Float, default=0.5)

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_calculated_at = Column(DateTime(timezone=True), nullable=True)

__all__ = [
    "UserVectorProfileDB", "ProfileInferenceRecordDB",
    "ThirdPartyAuthRecordDB", "GameTestRecordDB", "UserSocialMetricsDB"
]