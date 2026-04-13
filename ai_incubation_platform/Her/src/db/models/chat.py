"""
SQLAlchemy 数据模型 - 实时聊天领域

包含：聊天消息、聊天会话等
"""
from db.models.base import *

class ChatMessageDB(Base):
    """实时聊天消息"""
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), nullable=False, index=True)

    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    message_type = Column(String(20), default="text")
    content = Column(Text, nullable=False)

    status = Column(String(20), default="sent")
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    message_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChatConversationDB(Base):
    """聊天会话"""
    __tablename__ = "chat_conversations"

    id = Column(String(36), primary_key=True, index=True)

    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String(20), default="active")
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    last_message_preview = Column(Text, nullable=True)

    unread_count_user1 = Column(Integer, default=0)
    unread_count_user2 = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

__all__ = ["ChatMessageDB", "ChatConversationDB"]