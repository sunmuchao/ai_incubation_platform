"""
SQLAlchemy 数据模型 - AI预沟通领域

包含：AI预沟通会话、预沟通消息等
"""
from db.models.base import *

class AIPreCommunicationSessionDB(Base):
    """AI 预沟通会话"""
    __tablename__ = "ai_pre_communication_sessions"

    id = Column(String(36), primary_key=True, index=True)

    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String(20), default="pending")

    hard_check_passed = Column(Boolean, default=False)
    hard_check_result = Column(Text, default="")

    values_check_passed = Column(Boolean, default=False)
    values_check_result = Column(Text, default="")

    conversation_rounds = Column(Integer, default=0)
    target_rounds = Column(Integer, default=50)

    compatibility_score = Column(Float, nullable=True)
    compatibility_report = Column(Text, default="")

    extracted_insights = Column(Text, default="")

    recommendation = Column(String(20), nullable=True)
    recommendation_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AIPreCommunicationMessageDB(Base):
    """AI 预沟通对话消息"""
    __tablename__ = "ai_pre_communication_messages"

    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("ai_pre_communication_sessions.id"), nullable=False, index=True)

    agent_id_1 = Column(String(36), nullable=False)
    agent_id_2 = Column(String(36), nullable=False)

    sender_agent = Column(String(36), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")

    topic_tag = Column(String(50), nullable=True)
    sentiment = Column(Float, nullable=True)
    key_info_extracted = Column(Text, default="")

    round_number = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

__all__ = ["AIPreCommunicationSessionDB", "AIPreCommunicationMessageDB"]