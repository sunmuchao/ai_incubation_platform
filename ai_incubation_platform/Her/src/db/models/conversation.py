"""
SQLAlchemy 数据模型 - 对话领域

包含：对话历史、行为事件、画像更新、会话状态等
"""
from db.models.base import *

class ConversationDB(Base):
    """对话历史记录"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), nullable=False, index=True)
    user_id_2 = Column(String(36), nullable=False, index=True)

    message_content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")
    sender_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    topic_tags = Column(Text, default="")
    sentiment_score = Column(Float, nullable=True)
    is_sensitive = Column(Boolean, default=False)
    safety_flags = Column(Text, default="")


class BehaviorEventDB(Base):
    """用户行为事件记录"""
    __tablename__ = "behavior_events"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    event_type = Column(String(50), nullable=False, index=True)
    target_id = Column(String(36), nullable=True, index=True)

    event_data = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserProfileUpdateDB(Base):
    """动态用户画像更新记录"""
    __tablename__ = "user_profile_updates"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    update_type = Column(String(50), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=False)

    source = Column(String(50), nullable=False)
    confidence = Column(Float, default=1.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied = Column(Boolean, default=False)


class ConversationSessionDB(Base):
    """AI Native 对话会话状态持久化"""
    __tablename__ = "conversation_sessions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    conversation_history = Column(Text, default="[]")
    knowledge_base = Column(Text, default="{}")

    current_topic = Column(String(100), nullable=True)
    understanding_level = Column(Float, default=0.0)
    is_completed = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now())

__all__ = [
    "ConversationDB", "BehaviorEventDB",
    "UserProfileUpdateDB", "ConversationSessionDB"
]