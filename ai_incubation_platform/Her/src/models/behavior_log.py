"""
用户行为日志数据模型

从 behavior_log_service.py 迁移，建立单一真相来源。
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Index, func
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime


class UserBehaviorEventDB(Base):
    """用户行为事件表"""
    __tablename__ = "user_behavior_events"

    id = Column(String(36), primary_key=True, default=lambda: f"ube-{datetime.now().timestamp()}")
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 事件类型
    event_type = Column(String(50), nullable=False, index=True)  # swipe, message, profile_view, match, etc.

    # 事件数据（JSON）
    event_data = Column(JSON, nullable=True)
    """
    不同类型事件的数据结构示例:

    swipe: {
        "target_user_id": "user-xxx",
        "action": "like" | "pass",
        "swipe_duration_seconds": 5,
        "viewed_sections": ["photo", "bio", "interests"]
    }

    message: {
        "conversation_id": "conv-xxx",
        "message_length": 50,
        "response_time_seconds": 120,
        "contains_media": false
    }

    profile_view: {
        "viewed_user_id": "user-xxx",
        "view_duration_seconds": 30,
        "sections_viewed": ["photo", "bio"]
    }

    match: {
        "matched_user_id": "user-xxx",
        "compatibility_score": 0.85,
        "match_reason": "common_interests"
    }
    """

    # 会话信息
    session_id = Column(String(64), nullable=True, index=True)
    device_id = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 索引
    __table_args__ = (
        Index("idx_user_event_time", "user_id", "event_type", "created_at"),
    )


class UserBehaviorDailyStatsDB(Base):
    """用户行为日统计表"""
    __tablename__ = "user_behavior_daily_stats"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    stat_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # 行为统计
    swipe_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    pass_count = Column(Integer, default=0)
    message_count = Column(Integer, default=0)
    message_sent_count = Column(Integer, default=0)
    message_received_count = Column(Integer, default=0)
    profile_view_count = Column(Integer, default=0)
    profile_viewed_by_others_count = Column(Integer, default=0)
    match_count = Column(Integer, default=0)
    active_minutes = Column(Integer, default=0)

    # 时间统计
    first_active_time = Column(DateTime(timezone=True), nullable=True)
    last_active_time = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_user_date", "user_id", "stat_date", unique=True),
    )