"""
消息解读数据库模型

记录用户对消息的解读请求和结果
"""
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from db.database import Base


class MessageInterpretationDB(Base):
    """消息解读记录"""
    __tablename__ = "message_interpretations"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    message_id = Column(String(36), nullable=False, index=True)  # 解读的消息 ID
    partner_id = Column(String(36), nullable=False, index=True)  # 消息发送者 ID

    # 解读内容
    interpretation_type = Column(String(20), nullable=False)  # meaning/emotion/intent/suggestion/context
    result = Column(Text, nullable=False)  # 解读结果摘要
    details = Column(JSON, nullable=True)  # 详细解读结果（JSON）
    confidence = Column(Float, default=0.8)  # 置信度

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<MessageInterpretationDB(id={self.id}, type={self.interpretation_type})>"