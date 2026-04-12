"""
Your Turn 提醒数据模型

从 your_turn_service.py 迁移，建立单一真相来源。
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from db.database import Base


class YourTurnReminderDB(Base):
    """Your Turn 提醒记录"""
    __tablename__ = "your_turn_reminders"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(String(36), nullable=False, index=True)

    # 提醒状态
    shown_count = Column(Integer, default=0)  # 显示次数
    last_shown_at = Column(DateTime(timezone=True), nullable=True)
    dismissed = Column(Boolean, default=False)  # 是否已忽略
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())