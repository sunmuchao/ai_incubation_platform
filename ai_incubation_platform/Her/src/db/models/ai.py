"""
SQLAlchemy 数据模型 - AI 集成领域

包含：AI陪伴、语义分析、LLM指标、行为特征等
"""
from db.models.base import *

class AICompanionSessionDB(Base):
    """AI 陪伴会话记录"""
    __tablename__ = "ai_companion_sessions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    session_type = Column(String(50), default="chat")
    companion_persona = Column(String(50), default="gentle_advisor")

    session_summary = Column(Text, nullable=True)
    key_insights = Column(Text, default="")

    user_mood = Column(String(50), nullable=True)
    sentiment_score = Column(Float, nullable=True)

    duration_minutes = Column(Integer, default=0)
    message_count = Column(Integer, default=0)

    user_rating = Column(Integer, nullable=True)
    user_feedback = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)


class AICompanionMessageDB(Base):
    """AI 陪伴消息记录"""
    __tablename__ = "ai_companion_messages"

    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("ai_companion_sessions.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    emotion = Column(String(50), nullable=True)
    sentiment = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SemanticAnalysisDB(Base):
    """LLM 语义分析结果持久化"""
    __tablename__ = "semantic_analyses"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    analysis_type = Column(String(50), nullable=False)

    result = Column(JSON, nullable=False)

    original_text_preview = Column(String(500), nullable=True)

    overall_confidence = Column(Float, nullable=True)

    llm_model = Column(String(100), nullable=True)

    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMMetricsDB(Base):
    """LLM 调用指标记录"""
    __tablename__ = "llm_metrics"

    id = Column(String(36), primary_key=True, index=True)

    endpoint = Column(String(100), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)

    estimated_cost = Column(Float, nullable=True)

    response_status = Column(String(20), default="success")
    error_message = Column(Text, nullable=True)

    response_time_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserBehaviorFeatureDB(Base):
    """用户行为特征向量"""
    __tablename__ = "user_behavior_features"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    feature_vector = Column(Text, default="")

    similar_users = Column(Text, default="")
    user_cluster = Column(String(50), nullable=True)

    preference_weights = Column(Text, default="")

    model_version = Column(String(50), default="v1")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_trained_at = Column(DateTime(timezone=True), nullable=True)

__all__ = [
    "AICompanionSessionDB", "AICompanionMessageDB",
    "SemanticAnalysisDB", "LLMMetricsDB", "UserBehaviorFeatureDB"
]