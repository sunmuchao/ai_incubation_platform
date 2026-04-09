"""
AI 反馈数据库模型

用于记录用户对 AI 建议的反馈数据，支持后续分析和模型优化。
"""
from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, Index, Integer
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime


class AIFeedbackDB(Base):
    """AI 建议反馈记录表"""

    __tablename__ = "ai_feedback"

    # 基础信息
    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), nullable=False, index=True)  # 用户 ID
    partner_id = Column(String(36), nullable=True)  # 聊天对象 ID
    suggestion_id = Column(String(36), nullable=False, index=True)  # 建议 ID

    # 反馈内容
    feedback_type = Column(String(20), nullable=False, index=True)  # adopted/ignored/modified
    suggestion_content = Column(Text, nullable=True)  # AI 建议内容
    suggestion_style = Column(String(50), nullable=True)  # 建议风格（幽默/真诚/延续话题等）
    suggestion_category = Column(String(50), nullable=True)  # 建议类别（破冰/深入/告别等）

    # 用户行为
    user_actual_reply = Column(Text, nullable=True)  # 用户实际发送的内容
    reply_latency_ms = Column(Integer, nullable=True)  # 用户回复延迟（毫秒）

    # 元数据
    metadata_json = Column(Text, nullable=True)  # 额外元数据（JSON 格式）
    session_id = Column(String(36), nullable=True, index=True)  # 会话 ID
    conversation_round = Column(Integer, default=0)  # 对话回合数

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index('idx_ai_feedback_user_partner', 'user_id', 'partner_id'),
        Index('idx_ai_feedback_created_at', 'created_at'),
        Index('idx_ai_feedback_type_created', 'feedback_type', 'created_at'),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        import json
        return {
            "id": self.id,
            "user_id": self.user_id,
            "partner_id": self.partner_id,
            "suggestion_id": self.suggestion_id,
            "feedback_type": self.feedback_type,
            "suggestion_content": self.suggestion_content,
            "suggestion_style": self.suggestion_style,
            "suggestion_category": self.suggestion_category,
            "user_actual_reply": self.user_actual_reply,
            "reply_latency_ms": self.reply_latency_ms,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "session_id": self.session_id,
            "conversation_round": self.conversation_round,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AIFeedbackOutcomeDB(Base):
    """AI 建议采纳后的结果追踪表"""

    __tablename__ = "ai_feedback_outcomes"

    # 基础信息
    id = Column(String(36), primary_key=True)
    feedback_id = Column(String(36), nullable=False, index=True)  # 关联的反馈 ID
    user_id = Column(String(36), nullable=False, index=True)  # 用户 ID

    # 结果信息
    outcome_type = Column(String(20), nullable=False, index=True)  # positive/neutral/negative
    outcome_description = Column(Text, nullable=True)  # 结果描述

    # 量化指标
    conversation_duration_min = Column(Integer, nullable=True)  # 对话持续时长（分钟）
    user_satisfaction_score = Column(Float, nullable=True)  # 用户满意度评分 (0-1)
    follow_up_messages = Column(Integer, default=0)  # 后续消息数量

    # 元数据
    metadata_json = Column(Text, nullable=True)  # 额外元数据（JSON 格式）

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_outcome_feedback_user', 'feedback_id', 'user_id'),
        Index('idx_outcome_created_at', 'created_at'),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        import json
        return {
            "id": self.id,
            "feedback_id": self.feedback_id,
            "user_id": self.user_id,
            "outcome_type": self.outcome_type,
            "outcome_description": self.outcome_description,
            "conversation_duration_min": self.conversation_duration_min,
            "user_satisfaction_score": self.user_satisfaction_score,
            "follow_up_messages": self.follow_up_messages,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
