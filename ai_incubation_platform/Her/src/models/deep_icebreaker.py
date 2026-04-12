"""
深度破冰话题数据库模型

记录话题生成历史和反馈
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from db.database import Base


class IcebreakerTopicHistoryDB(Base):
    """话题生成历史"""
    __tablename__ = "icebreaker_topic_history"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_id = Column(String(36), nullable=False, index=True)

    # 话题内容
    topic_content = Column(Text, nullable=False)
    topic_type = Column(String(20), nullable=False)  # question/story_share/game/challenge/reflection
    depth_level = Column(Integer, default=1)  # 1-5

    # 生成方式
    generation_method = Column(String(20), default="ai_generated")  # ai_generated/template/custom

    # 使用状态
    is_used = Column(Boolean, default=False)  # 是否已使用
    used_at = Column(DateTime(timezone=True), nullable=True)
    effectiveness_score = Column(Float, nullable=True)  # 效果评分（0-1）

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IcebreakerTopicFeedbackDB(Base):
    """话题反馈"""
    __tablename__ = "icebreaker_topic_feedback"

    id = Column(String(36), primary_key=True, index=True)
    topic_id = Column(String(36), ForeignKey("icebreaker_topic_history.id"), nullable=False, index=True)

    # 反馈内容
    feedback_type = Column(String(20), nullable=False)  # positive/negative/neutral
    feedback_detail = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())