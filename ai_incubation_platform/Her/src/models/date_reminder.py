"""
约会提醒数据库模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from db.database import Base


class DateReminderPlanDB(Base):
    """约会提醒计划（用于提醒服务，区别于 AI 约会策划的 DatePlanDB）"""
    __tablename__ = "date_reminder_plans"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_id = Column(String(36), nullable=False, index=True)

    # 约会信息
    date_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(200), nullable=False)
    activity = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)

    # 提醒设置
    reminder_settings = Column(JSON, nullable=True)  # {"one_day_before": true, ...}

    # 提醒发送状态
    one_day_reminder_sent = Column(Boolean, default=False)
    three_hours_reminder_sent = Column(Boolean, default=False)
    one_hour_reminder_sent = Column(Boolean, default=False)

    # 状态
    status = Column(String(20), default="scheduled")  # scheduled/completed/cancelled/postponed
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DateFeedbackDB(Base):
    """约会反馈"""
    __tablename__ = "date_feedbacks"

    id = Column(String(36), primary_key=True, index=True)
    plan_id = Column(String(36), ForeignKey("date_plans.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 反馈内容
    rating = Column(Integer, nullable=False)  # 1-5
    feedback = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())