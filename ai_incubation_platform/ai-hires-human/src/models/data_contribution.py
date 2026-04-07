"""
用户贡献数据模型 - 用于记录用户提交的数据贡献。
"""
from datetime import datetime
from typing import Dict, Optional, List

from sqlalchemy import Boolean, DateTime, String, Text, JSON, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DataContributionDB(Base):
    """用户数据贡献表。"""
    __tablename__ = "data_contributions"

    contribution_id: Mapped[str] = mapped_column(String(36), primary_key=True, unique=True)

    # 贡献者信息
    contributor_id: Mapped[str] = mapped_column(String(255), index=True)
    contributor_type: Mapped[str] = mapped_column(String(20), default="worker")  # worker, developer, enterprise

    # 贡献数据类型
    contribution_type: Mapped[str] = mapped_column(String(50), index=True)  # task_template, golden_standard, training_data, feedback, bug_report

    # 贡献内容
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    content: Mapped[Dict] = mapped_column(JSON, default=dict)  # 实际贡献的数据内容

    # 关联
    related_task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    related_batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 审核状态
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, under_review, approved, rejected
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 质量评分
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    usefulness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100（用户投票）

    # 奖励信息
    reward_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 奖励金额
    reward_currency: Mapped[str] = mapped_column(String(3), default="CNY")
    reward_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, paid, rejected

    # 使用统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0)  # 被使用次数
    upvotes: Mapped[int] = mapped_column(Integer, default=0)  # 点赞数
    downvotes: Mapped[int] = mapped_column(Integer, default=0)  # 点踩数

    # 版本控制
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_contribution_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # 父版本 ID

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class ContributionVoteDB(Base):
    """贡献投票表。"""
    __tablename__ = "contribution_votes"

    vote_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    contribution_id: Mapped[str] = mapped_column(String(36), index=True)
    voter_id: Mapped[str] = mapped_column(String(255))

    # 投票类型
    vote_type: Mapped[str] = mapped_column(String(10))  # upvote, downvote

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class TaskTemplateContributionDB(Base):
    """任务模板贡献表（特殊类型的贡献）。"""
    __tablename__ = "task_template_contributions"

    template_id: Mapped[str] = mapped_column(String(36), primary_key=True, unique=True)
    contribution_id: Mapped[str] = mapped_column(String(36), index=True)

    # 模板信息
    template_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50))  # 分类（如 data_collection, verification, transcription 等）

    # 模板内容
    title_template: Mapped[str] = mapped_column(Text)
    description_template: Mapped[str] = mapped_column(Text)
    acceptance_criteria_template: Mapped[Dict] = mapped_column(JSON, default=list)
    requirements_template: Mapped[Dict] = mapped_column(JSON, default=list)
    required_skills_template: Mapped[Dict] = mapped_column(JSON, default=dict)

    # 使用统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 使用该模板的任务成功率

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class GoldenStandardContributionDB(Base):
    """黄金标准测试贡献表（特殊类型的贡献）。"""
    __tablename__ = "golden_standard_contributions"

    gs_template_id: Mapped[str] = mapped_column(String(36), primary_key=True, unique=True)
    contribution_id: Mapped[str] = mapped_column(String(36), index=True)

    # 测试模板信息
    test_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(50))  # 分类（如 data_annotation, content_moderation 等）

    # 测试题目模板
    questions_template: Mapped[Dict] = mapped_column(JSON, default=list)
    passing_score_template: Mapped[float] = mapped_column(Float, default=80.0)

    # 使用统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    average_worker_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class ContributorAchievementDB(Base):
    """贡献者成就表。"""
    __tablename__ = "contributor_achievements"

    achievement_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    contributor_id: Mapped[str] = mapped_column(String(255), index=True)

    # 成就信息
    achievement_type: Mapped[str] = mapped_column(String(50))  # first_contribution, top_contributor, template_master, etc.
    achievement_name: Mapped[str] = mapped_column(String(255))
    achievement_description: Mapped[str] = mapped_column(Text)

    # 成就等级
    achievement_level: Mapped[str] = mapped_column(String(20), default="bronze")  # bronze, silver, gold, diamond

    # 进度
    progress: Mapped[int] = mapped_column(Integer, default=0)
    target: Mapped[int] = mapped_column(Integer, default=1)

    # 状态
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class ContributionRewardDB(Base):
    """贡献奖励记录表。"""
    __tablename__ = "contribution_rewards"

    reward_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    contribution_id: Mapped[str] = mapped_column(String(36), index=True)
    contributor_id: Mapped[str] = mapped_column(String(255), index=True)

    # 奖励信息
    reward_type: Mapped[str] = mapped_column(String(20))  # cash, points, badge, recognition
    reward_amount: Mapped[float] = mapped_column(Float, default=0.0)
    reward_currency: Mapped[str] = mapped_column(String(3), default="CNY")
    reward_points: Mapped[int] = mapped_column(Integer, default=0)

    # 奖励原因
    reward_reason: Mapped[str] = mapped_column(String(255))  # approved_contribution, template_used, top_contributor, etc.

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, paid, failed

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
