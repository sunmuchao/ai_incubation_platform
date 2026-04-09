"""
P2: 数字分身预聊模型

功能包括：
- 数字分身配置
- 分身对话模拟
- 复盘报告生成
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base


class DigitalTwinProfile(Base):
    """
    数字分身配置

    存储用于模拟的用户分身配置
    """
    __tablename__ = "digital_twin_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)

    # 基础信息
    display_name = Column(String(100), nullable=False)
    avatar_url = Column(String(500))

    # 性格特征（用于 AI 模拟）
    personality_traits = Column(JSON, default=dict)  # 大五人格等
    communication_style = Column(String(50))  # direct/indirect/warm/reserved

    # 价值观和兴趣
    core_values = Column(JSON, default=list)  # 核心价值观
    interests = Column(JSON, default=list)  # 兴趣爱好
    deal_breakers = Column(JSON, default=list)  # 不可接受的行为

    # 行为模式
    response_patterns = Column(JSON, default=list)  # 常见回复模式
    topic_preferences = Column(JSON, default=list)  # 喜欢的话题
    conversation_starters = Column(JSON, default=list)  # 开场白偏好

    # 模拟配置
    simulation_temperature = Column(Float, default=0.7)  # AI 创造性 0-1
    response_length_preference = Column(String(20), default="medium")  # short/medium/long

    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "personality_traits": self.personality_traits,
            "communication_style": self.communication_style,
            "core_values": self.core_values,
            "interests": self.interests,
            "deal_breakers": self.deal_breakers,
            "response_patterns": self.response_patterns,
            "topic_preferences": self.topic_preferences,
            "conversation_starters": self.conversation_starters,
            "simulation_temperature": self.simulation_temperature,
            "response_length_preference": self.response_length_preference,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DigitalTwinSimulation(Base):
    """
    数字分身模拟会话

    存储两个分身之间的模拟对话
    """
    __tablename__ = "digital_twin_simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 参与用户
    user_a_id = Column(String(64), nullable=False, index=True)
    user_b_id = Column(String(64), nullable=False, index=True)

    # 会话状态
    status = Column(String(20), default="pending")  # pending/running/completed/cancelled
    total_rounds = Column(Integer, default=10)  # 模拟轮数
    completed_rounds = Column(Integer, default=0)

    # 对话记录
    conversation_log = Column(JSON, default=list)  # 完整对话记录

    # 分析结果
    compatibility_score = Column(Float, default=0.0)  # 兼容性评分 0-100
    chemistry_score = Column(Float, default=0.0)  # 化学反应评分 0-100
    communication_match = Column(Float, default=0.0)  # 沟通匹配度 0-100
    values_alignment = Column(Float, default=0.0)  # 价值观一致性 0-100

    # 关键发现
    highlights = Column(JSON, default=list)  # 契合点
    potential_conflicts = Column(JSON, default=list)  # 潜在冲突
    conversation_highlights = Column(JSON, default=list)  # 精彩对话片段

    # AI 分析
    ai_analysis = Column(JSON, default=dict)  # AI 完整分析报告
    ai_suggestions = Column(JSON, default=list)  # AI 建议

    # 元数据
    simulation_config = Column(JSON, default=dict)  # 模拟配置
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_twin_sim_users", "user_a_id", "user_b_id", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_a_id": self.user_a_id,
            "user_b_id": self.user_b_id,
            "status": self.status,
            "total_rounds": self.total_rounds,
            "completed_rounds": self.completed_rounds,
            "conversation_log": self.conversation_log,
            "compatibility_score": self.compatibility_score,
            "chemistry_score": self.chemistry_score,
            "communication_match": self.communication_match,
            "values_alignment": self.values_alignment,
            "highlights": self.highlights,
            "potential_conflicts": self.potential_conflicts,
            "conversation_highlights": self.conversation_highlights,
            "ai_analysis": self.ai_analysis,
            "ai_suggestions": self.ai_suggestions,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DigitalTwinReport(Base):
    """
    数字分身复盘报告

    存储模拟后生成的复盘报告
    """
    __tablename__ = "digital_twin_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("digital_twin_simulations.id"), nullable=False)

    # 关联
    simulation = relationship("DigitalTwinSimulation", backref="reports")

    # 用户
    user_id = Column(String(64), nullable=False, index=True)

    # 报告内容
    report_title = Column(String(200))
    report_summary = Column(Text)
    report_content = Column(JSON, default=dict)  # 完整报告内容

    # 评分
    overall_compatibility = Column(Float)  # 整体兼容性 0-100

    # 维度评分
    dimension_scores = Column(JSON, default=dict)  # 各维度评分
    # {
    #     "communication": 85,
    #     "values": 90,
    #     "lifestyle": 75,
    #     "personality": 80
    # }

    # 建议
    strengths = Column(JSON, default=list)  # 优势
    growth_areas = Column(JSON, default=list)  # 需要成长的领域
    date_suggestions = Column(JSON, default=list)  # 约会建议

    # 对话片段
    conversation_snippets = Column(JSON, default=list)  # 精选对话片段

    # 状态
    is_generated = Column(Boolean, default=False)
    is_viewed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "simulation_id": self.simulation_id,
            "user_id": self.user_id,
            "report_title": self.report_title,
            "report_summary": self.report_summary,
            "report_content": self.report_content,
            "overall_compatibility": self.overall_compatibility,
            "dimension_scores": self.dimension_scores,
            "strengths": self.strengths,
            "growth_areas": self.growth_areas,
            "date_suggestions": self.date_suggestions,
            "conversation_snippets": self.conversation_snippets,
            "is_generated": self.is_generated,
            "is_viewed": self.is_viewed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
