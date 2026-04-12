"""
共同活动推荐数据库模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from db.database import Base


class ActivityRecommendationHistoryDB(Base):
    """活动推荐历史"""
    __tablename__ = "activity_recommendation_history"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_id = Column(String(36), nullable=False, index=True)

    # 活动信息
    activity_name = Column(String(100), nullable=False)
    activity_type = Column(String(30), nullable=False)

    # 使用状态
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ActivityFeedbackDB(Base):
    """活动反馈"""
    __tablename__ = "activity_feedback"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    activity_name = Column(String(100), nullable=False)

    # 反馈内容
    rating = Column(Integer, nullable=False)  # 1-5
    feedback = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())