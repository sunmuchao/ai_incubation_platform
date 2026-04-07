"""
数据库模型
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, JSON, Enum as SQLAlchemyEnum, DateTime, func
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.member import (
    MemberType, MemberRole, ContentType, ReviewStatus, ReportType,
    ReportStatus, BanStatus, OperationType
)


class DBCommunityMember(BaseModel):
    """社区成员表"""
    __tablename__ = "community_members"

    id = Column(String(36), primary_key=True, index=True, comment="用户ID")
    name = Column(String(100), nullable=False, comment="显示名称")
    email = Column(String(100), unique=True, index=True, comment="邮箱")
    member_type = Column(SQLAlchemyEnum(MemberType), nullable=False, comment="成员类型")
    role = Column(SQLAlchemyEnum(MemberRole), nullable=False, default=MemberRole.MEMBER, comment="角色")

    # AI成员特有字段
    ai_model = Column(String(100), comment="AI模型标识")
    ai_persona = Column(Text, comment="AI人格设定")

    # 统计字段
    post_count = Column(Integer, nullable=False, default=0, comment="发帖数")
    join_date = Column(DateTime(timezone=True), server_default=func.now(), comment="加入时间")

    # 用户等级系统字段
    experience_points = Column(Integer, nullable=False, default=0, comment="经验值")
    level = Column(Integer, nullable=False, default=1, comment="用户等级 (1-18 级)")
    last_checkin_date = Column(DateTime(timezone=True), comment="最后签到时间")

    # 关系
    posts = relationship("DBPost", back_populates="author")
    comments = relationship("DBComment", back_populates="author")
    reports = relationship("DBReport", foreign_keys="DBReport.reporter_id", back_populates="reporter")
    handled_reports = relationship("DBReport", foreign_keys="DBReport.handler_id", back_populates="handler")
    ban_records = relationship("DBBanRecord", foreign_keys="DBBanRecord.user_id", back_populates="user")
    operated_bans = relationship("DBBanRecord", foreign_keys="DBBanRecord.operator_id", back_populates="operator")
    audit_logs = relationship("DBAuditLog", back_populates="operator")


class DBPost(BaseModel):
    """帖子表"""
    __tablename__ = "posts"

    id = Column(String(36), primary_key=True, index=True, comment="帖子ID")
    author_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="作者ID")
    author_type = Column(SQLAlchemyEnum(MemberType), nullable=False, comment="作者类型")
    title = Column(String(200), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="内容")
    tags = Column(JSON, nullable=False, default=list, comment="标签列表")
    status = Column(String(20), nullable=False, default="published", comment="状态：draft/published/archived/deleted")

    # 关系
    author = relationship("DBCommunityMember", back_populates="posts")
    comments = relationship("DBComment", back_populates="post")
    # reviews 和 reports 关系在 DBContentReview 和 DBReport 中设置为 viewonly=True，所以这里也需要设置
    reviews = relationship(
        "DBContentReview",
        primaryjoin="and_(DBContentReview.content_type == 'post', DBContentReview.content_id == DBPost.id)",
        viewonly=True,
        foreign_keys="DBContentReview.content_id"
    )
    reports = relationship(
        "DBReport",
        primaryjoin="and_(DBReport.reported_content_type == 'post', DBReport.reported_content_id == DBPost.id)",
        viewonly=True,
        foreign_keys="DBReport.reported_content_id"
    )


class DBComment(BaseModel):
    """评论表"""
    __tablename__ = "comments"

    id = Column(String(36), primary_key=True, index=True, comment="评论ID")
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False, comment="所属帖子ID")
    author_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="作者ID")
    author_type = Column(SQLAlchemyEnum(MemberType), nullable=False, comment="作者类型")
    content = Column(Text, nullable=False, comment="评论内容")
    parent_id = Column(String(36), ForeignKey("comments.id"), comment="父评论ID")
    status = Column(String(20), nullable=False, default="published", comment="状态：published/deleted/hidden")

    # 关系
    post = relationship("DBPost", back_populates="comments")
    author = relationship("DBCommunityMember", back_populates="comments")
    parent = relationship("DBComment", remote_side=[id], back_populates="replies")
    replies = relationship("DBComment", back_populates="parent")
    # reviews 和 reports 关系在 DBContentReview 和 DBReport 中设置为 viewonly=True，所以这里也需要设置
    reviews = relationship(
        "DBContentReview",
        primaryjoin="and_(DBContentReview.content_type == 'comment', DBContentReview.content_id == DBComment.id)",
        viewonly=True,
        foreign_keys="DBContentReview.content_id"
    )
    reports = relationship(
        "DBReport",
        primaryjoin="and_(DBReport.reported_content_type == 'comment', DBReport.reported_content_id == DBComment.id)",
        viewonly=True,
        foreign_keys="DBReport.reported_content_id"
    )


class DBContentReview(BaseModel):
    """内容审核表"""
    __tablename__ = "content_reviews"

    id = Column(String(36), primary_key=True, index=True, comment="审核记录ID")
    content_id = Column(String(36), nullable=False, index=True, comment="内容ID")
    content_type = Column(SQLAlchemyEnum(ContentType), nullable=False, comment="内容类型")
    content = Column(Text, nullable=False, comment="待审核内容")
    author_id = Column(String(36), nullable=False, comment="作者ID")
    author_type = Column(SQLAlchemyEnum(MemberType), nullable=False, comment="作者类型")
    status = Column(SQLAlchemyEnum(ReviewStatus), nullable=False, default=ReviewStatus.PENDING, comment="审核状态")
    review_result = Column(JSON, comment="审核结果")
    submit_time = Column(DateTime(timezone=True), server_default=func.now(), comment="提交时间")

    # 关系
    post = relationship("DBPost", back_populates="reviews", foreign_keys=[content_id],
                       primaryjoin="and_(DBContentReview.content_type == 'post', DBContentReview.content_id == DBPost.id)",
                       viewonly=True)
    comment = relationship("DBComment", back_populates="reviews", foreign_keys=[content_id],
                          primaryjoin="and_(DBContentReview.content_type == 'comment', DBContentReview.content_id == DBComment.id)",
                          viewonly=True)


class DBReviewRule(BaseModel):
    """审核规则表"""
    __tablename__ = "review_rules"

    id = Column(String(36), primary_key=True, index=True, comment="规则ID")
    name = Column(String(100), nullable=False, comment="规则名称")
    description = Column(Text, comment="规则描述")
    rule_type = Column(String(50), nullable=False, comment="规则类型")
    config = Column(JSON, nullable=False, default=dict, comment="规则配置")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    risk_score = Column(Float, nullable=False, default=0.5, comment="风险分数")
    action = Column(String(20), nullable=False, default="flag", comment="触发动作")


class DBReport(BaseModel):
    """举报表"""
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, index=True, comment="举报ID")
    reporter_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="举报人ID")
    reported_content_id = Column(String(36), nullable=False, index=True, comment="被举报内容ID")
    reported_content_type = Column(SQLAlchemyEnum(ContentType), nullable=False, comment="内容类型")
    report_type = Column(SQLAlchemyEnum(ReportType), nullable=False, comment="举报类型")
    description = Column(Text, comment="举报描述")
    evidence = Column(JSON, default=list, comment="证据列表")
    status = Column(SQLAlchemyEnum(ReportStatus), nullable=False, default=ReportStatus.PENDING, comment="处理状态")
    handler_id = Column(String(36), ForeignKey("community_members.id"), comment="处理人ID")
    handler_note = Column(Text, comment="处理备注")

    # 关系
    reporter = relationship("DBCommunityMember", foreign_keys=[reporter_id], back_populates="reports")
    handler = relationship("DBCommunityMember", foreign_keys=[handler_id], back_populates="handled_reports")
    post = relationship("DBPost", back_populates="reports", foreign_keys=[reported_content_id],
                       primaryjoin="and_(DBReport.reported_content_type == 'post', DBReport.reported_content_id == DBPost.id)",
                       viewonly=True)
    comment = relationship("DBComment", back_populates="reports", foreign_keys=[reported_content_id],
                          primaryjoin="and_(DBReport.reported_content_type == 'comment', DBReport.reported_content_id == DBComment.id)",
                          viewonly=True)


class DBBanRecord(BaseModel):
    """封禁记录表"""
    __tablename__ = "ban_records"

    id = Column(String(36), primary_key=True, index=True, comment="封禁记录ID")
    user_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="被封禁用户ID")
    reason = Column(Text, nullable=False, comment="封禁原因")
    ban_type = Column(String(20), nullable=False, default="all", comment="封禁类型")
    duration_hours = Column(Integer, comment="封禁时长（小时）")
    status = Column(SQLAlchemyEnum(BanStatus), nullable=False, default=BanStatus.ACTIVE, comment="封禁状态")
    operator_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="操作人ID")
    expire_time = Column(DateTime(timezone=True), comment="过期时间")
    lifted_at = Column(DateTime(timezone=True), comment="解封时间")
    lift_reason = Column(Text, comment="解封原因")

    # 关系
    user = relationship("DBCommunityMember", foreign_keys=[user_id], back_populates="ban_records")
    operator = relationship("DBCommunityMember", foreign_keys=[operator_id], back_populates="operated_bans")


class DBAuditLog(BaseModel):
    """审计日志表"""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, index=True, comment="日志ID")
    operator_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="操作者ID")
    operator_type = Column(SQLAlchemyEnum(MemberType), nullable=False, comment="操作者类型")
    operation_type = Column(SQLAlchemyEnum(OperationType), nullable=False, comment="操作类型")
    resource_type = Column(String(50), comment="资源类型")
    resource_id = Column(String(36), comment="资源ID")
    before = Column(JSON, comment="操作前状态")
    after = Column(JSON, comment="操作后状态")
    ip_address = Column(String(50), comment="IP地址")
    user_agent = Column(Text, comment="客户端信息")
    status = Column(String(20), nullable=False, default="success", comment="操作状态")
    error_message = Column(Text, comment="错误信息")

    # 关系
    operator = relationship("DBCommunityMember", back_populates="audit_logs")


class DBRateLimitConfig(BaseModel):
    """速率限制配置表"""
    __tablename__ = "rate_limit_configs"

    id = Column(String(36), primary_key=True, index=True, comment="配置ID")
    resource = Column(String(50), nullable=False, comment="受限资源")
    limit = Column(Integer, nullable=False, comment="限制次数")
    window_seconds = Column(Integer, nullable=False, comment="时间窗口（秒）")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")


class DBAgentCallRecord(BaseModel):
    """AI Agent调用记录表"""
    __tablename__ = "agent_call_records"

    id = Column(String(36), primary_key=True, index=True, comment="记录ID")
    agent_name = Column(String(100), nullable=False, index=True, comment="Agent名称")
    action = Column(String(50), nullable=False, comment="动作类型")
    content_id = Column(String(36), comment="关联内容ID")
    input_params = Column(JSON, nullable=False, default=dict, comment="调用参数")
    output_result = Column(JSON, nullable=False, default=dict, comment="返回结果")
    status = Column(String(20), nullable=False, default="success", comment="调用状态")
    error_message = Column(Text, comment="错误信息")
    call_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="调用时间")
    response_time = Column(Float, nullable=False, default=0, comment="响应时间（毫秒）")


# ==================== P3 新增模型 ====================

class DBFollow(BaseModel):
    """用户关注关系表"""
    __tablename__ = "follows"

    id = Column(String(36), primary_key=True, index=True, comment="关注记录 ID")
    follower_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="关注者 ID")
    following_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="被关注者 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="关注时间")

    # 关系
    follower = relationship("DBCommunityMember", foreign_keys=[follower_id], back_populates="following")
    following = relationship("DBCommunityMember", foreign_keys=[following_id], back_populates="followers")

    __table_args__ = (
        __import__('sqlalchemy').UniqueConstraint('follower_id', 'following_id', name='uq_follow_follower_following'),
    )


class DBLike(BaseModel):
    """点赞记录表"""
    __tablename__ = "likes"

    id = Column(String(36), primary_key=True, index=True, comment="点赞记录 ID")
    user_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="点赞用户 ID")
    content_id = Column(String(36), nullable=False, index=True, comment="内容 ID（帖子或评论 ID）")
    content_type = Column(SQLAlchemyEnum(ContentType), nullable=False, comment="内容类型")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="点赞时间")

    # 关系
    user = relationship("DBCommunityMember", back_populates="likes")

    __table_args__ = (
        __import__('sqlalchemy').UniqueConstraint('user_id', 'content_id', 'content_type', name='uq_like_user_content'),
    )


class DBBookmark(BaseModel):
    """收藏记录表"""
    __tablename__ = "bookmarks"

    id = Column(String(36), primary_key=True, index=True, comment="收藏记录 ID")
    user_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="收藏用户 ID")
    content_id = Column(String(36), nullable=False, index=True, comment="内容 ID（帖子或评论 ID）")
    content_type = Column(SQLAlchemyEnum(ContentType), nullable=False, comment="内容类型")
    folder = Column(String(50), default="default", comment="收藏夹名称")
    note = Column(Text, comment="收藏备注")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="收藏时间")

    # 关系
    user = relationship("DBCommunityMember", back_populates="bookmarks")

    __table_args__ = (
        __import__('sqlalchemy').UniqueConstraint('user_id', 'content_id', 'content_type', name='uq_bookmark_user_content'),
    )


class DBNotification(BaseModel):
    """站内通知表"""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, index=True, comment="通知 ID")
    recipient_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="接收用户 ID")
    sender_id = Column(String(36), ForeignKey("community_members.id"), comment="发送用户 ID")
    notification_type = Column(String(50), nullable=False, comment="通知类型")
    title = Column(String(200), comment="通知标题")
    content = Column(Text, nullable=False, comment="通知内容")
    related_content_id = Column(String(36), comment="关联内容 ID")
    related_content_type = Column(String(50), comment="关联内容类型")
    is_read = Column(Boolean, nullable=False, default=False, comment="是否已读")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    read_at = Column(DateTime(timezone=True), comment="阅读时间")

    # 关系
    recipient = relationship("DBCommunityMember", foreign_keys=[recipient_id], back_populates="received_notifications")
    sender = relationship("DBCommunityMember", foreign_keys=[sender_id], back_populates="sent_notifications")


# 更新 DBCommunityMember 添加新的关系
DBCommunityMember.following = relationship(
    "DBFollow",
    foreign_keys="DBFollow.follower_id",
    back_populates="follower"
)
DBCommunityMember.followers = relationship(
    "DBFollow",
    foreign_keys="DBFollow.following_id",
    back_populates="following"
)
DBCommunityMember.likes = relationship("DBLike", back_populates="user")
DBCommunityMember.bookmarks = relationship("DBBookmark", back_populates="user")
DBCommunityMember.received_notifications = relationship(
    "DBNotification",
    foreign_keys="DBNotification.recipient_id",
    back_populates="recipient"
)
DBCommunityMember.sent_notifications = relationship(
    "DBNotification",
    foreign_keys="DBNotification.sender_id",
    back_populates="sender"
)
# 用户等级系统关系
DBCommunityMember.experience_logs = relationship(
    "DBExperienceLog",
    back_populates="user"
)


# ==================== P6 新增模型：AI 信誉体系与行为追溯链 ====================

class DBAgentReputation(BaseModel):
    """AI Agent 信誉表"""
    __tablename__ = "agent_reputation"

    id = Column(String(36), primary_key=True, index=True, comment="信誉记录 ID")
    agent_id = Column(String(100), nullable=False, unique=True, index=True, comment="Agent 标识")
    agent_name = Column(String(100), nullable=False, comment="Agent 名称")
    agent_type = Column(String(50), nullable=False, comment="Agent 类型：moderator, assistant, recommender")
    model_provider = Column(String(100), comment="模型提供方")
    model_name = Column(String(100), comment="模型名称")
    operator_id = Column(String(36), comment="运营者 ID")

    # 信誉评分
    reputation_score = Column(Float, nullable=False, default=0.5, comment="信誉分数 (0-1)")
    total_actions = Column(Integer, nullable=False, default=0, comment="总行为数")
    positive_actions = Column(Integer, nullable=False, default=0, comment="正面行为数")
    negative_actions = Column(Integer, nullable=False, default=0, comment="负面行为数")

    # 细分评分
    accuracy_score = Column(Float, nullable=False, default=0.5, comment="准确性评分")
    fairness_score = Column(Float, nullable=False, default=0.5, comment="公平性评分")
    transparency_score = Column(Float, nullable=False, default=0.5, comment="透明性评分")
    response_time_score = Column(Float, nullable=False, default=0.5, comment="响应速度评分")

    # 统计
    avg_response_time_ms = Column(Float, nullable=False, default=0, comment="平均响应时间 (毫秒)")
    user_feedback_count = Column(Integer, nullable=False, default=0, comment="用户反馈数")
    user_feedback_positive = Column(Integer, nullable=False, default=0, comment="正面反馈数")

    # 状态
    is_active = Column(Boolean, nullable=False, default=True, comment="是否活跃")
    last_action_time = Column(DateTime(timezone=True), comment="最后行为时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class DBBehaviorTrace(BaseModel):
    """AI 行为追溯链表"""
    __tablename__ = "behavior_traces"

    id = Column(String(36), primary_key=True, index=True, comment="追溯记录 ID")
    trace_id = Column(String(36), nullable=False, unique=True, index=True, comment="追溯链 ID")
    parent_trace_id = Column(String(36), index=True, comment="父追溯 ID，用于关联多步决策")

    # AI 标识
    agent_id = Column(String(100), nullable=False, index=True, comment="Agent 标识")
    agent_name = Column(String(100), nullable=False, comment="Agent 名称")
    model_provider = Column(String(100), comment="模型提供方")
    model_name = Column(String(100), comment="模型名称")
    model_version = Column(String(50), comment="模型版本")
    operator_id = Column(String(36), comment="运营者 ID")

    # 行为信息
    action_type = Column(String(50), nullable=False, index=True, comment="行为类型")
    action_description = Column(Text, comment="行为描述")
    resource_type = Column(String(50), comment="资源类型")
    resource_id = Column(String(36), comment="资源 ID")

    # 决策过程
    input_data = Column(JSON, nullable=False, default=dict, comment="输入数据")
    decision_process = Column(JSON, nullable=False, default=dict, comment="决策过程详情")
    output_result = Column(JSON, nullable=False, default=dict, comment="输出结果")

    # 决策依据
    rules_applied = Column(JSON, default=list, comment="应用的规则列表")
    confidence_score = Column(Float, comment="置信度分数 (0-1)")
    risk_assessment = Column(JSON, comment="风险评估结果")

    # 时间与性能
    started_at = Column(DateTime(timezone=True), nullable=False, comment="开始时间")
    completed_at = Column(DateTime(timezone=True), comment="完成时间")
    duration_ms = Column(Float, comment="耗时 (毫秒)")

    # 状态与反馈
    status = Column(String(20), nullable=False, default="completed", comment="状态：completed, failed, timeout")
    error_message = Column(Text, comment="错误信息")
    user_feedback = Column(JSON, comment="用户反馈")
    review_result = Column(JSON, comment="复核结果")

    # 审计
    ip_address = Column(String(50), comment="IP 地址")
    trace_metadata = Column(JSON, default=dict, comment="元数据")


class DBGovernanceReport(BaseModel):
    """治理报告表"""
    __tablename__ = "governance_reports"

    id = Column(String(36), primary_key=True, index=True, comment="报告 ID")
    report_type = Column(String(50), nullable=False, comment="报告类型：daily, weekly, monthly")
    report_title = Column(String(200), nullable=False, comment="报告标题")

    # 时间范围
    start_time = Column(DateTime(timezone=True), nullable=False, comment="开始时间")
    end_time = Column(DateTime(timezone=True), nullable=False, comment="结束时间")
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), comment="生成时间")

    # 生成者
    generated_by = Column(String(100), nullable=False, comment="生成者：AI/用户 ID")
    agent_id = Column(String(100), index=True, comment="AI Agent 标识")

    # 报告内容
    summary = Column(Text, comment="报告摘要")
    content = Column(JSON, nullable=False, default=dict, comment="报告内容")
    metrics = Column(JSON, nullable=False, default=dict, comment="关键指标")

    # 统计数据
    total_posts = Column(Integer, default=0, comment="总帖子数")
    total_comments = Column(Integer, default=0, comment="总评论数")
    total_reports = Column(Integer, default=0, comment="总举报数")
    auto_processed = Column(Integer, default=0, comment="AI 自动处理数")
    manual_reviewed = Column(Integer, default=0, comment="人工审核数")

    # 治理效果
    violation_rate = Column(Float, default=0, comment="违规率")
    auto_resolution_rate = Column(Float, default=0, comment="AI 解决率")
    avg_response_time = Column(Float, default=0, comment="平均响应时间")
    user_satisfaction = Column(Float, default=0, comment="用户满意度")

    # 状态
    status = Column(String(20), nullable=False, default="draft", comment="状态：draft, published, archived")
    visibility = Column(String(20), nullable=False, default="admin", comment="可见性：admin, moderator, public")


# 关系 - 注释掉有问题的关系定义
# DBBehaviorTrace.governance_report = relationship(
#     "DBGovernanceReport",
#     primaryjoin="DBGovernanceReport.id == DBBehaviorTrace.id",
#     viewonly=True
# )


# ==================== P8 新增模型：开放 API 平台 ====================

class DBAPIKey(BaseModel):
    """API Key 表"""
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, index=True, comment="API Key ID")
    name = Column(String(100), nullable=False, comment="密钥名称")
    key = Column(String(100), nullable=False, unique=True, index=True, comment="密钥值")
    owner_id = Column(String(36), nullable=False, index=True, comment="所有者 ID")
    owner_type = Column(String(50), nullable=False, default="member", comment="所有者类型")

    # 密钥类型和等级
    key_type = Column(String(50), nullable=False, default="developer", comment="密钥类型")
    tier = Column(String(50), nullable=False, default="free", comment="等级")

    # 速率限制配置
    rate_limit = Column(Integer, nullable=False, default=10, comment="每秒请求数限制")
    daily_limit = Column(Integer, nullable=False, default=10000, comment="每日请求上限")

    # 状态
    status = Column(String(50), nullable=False, default="active", comment="状态")

    # 权限范围
    scopes = Column(JSON, nullable=False, default=list, comment="允许的 API 范围")

    # IP 白名单
    ip_whitelist = Column(JSON, comment="IP 白名单")

    # 时间
    expires_at = Column(DateTime(timezone=True), comment="过期时间")
    last_used_at = Column(DateTime(timezone=True), comment="最后使用时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 统计
    total_requests = Column(Integer, nullable=False, default=0, comment="总请求数")
    today_requests = Column(Integer, nullable=False, default=0, comment="今日请求数")

    # 元数据
    description = Column(Text, comment="描述")
    key_metadata = Column(JSON, default=dict, comment="元数据")


class DBAPIKeyUsage(BaseModel):
    """API Key 使用统计表"""
    __tablename__ = "api_key_usage"

    id = Column(String(36), primary_key=True, index=True, comment="记录 ID")
    api_key_id = Column(String(36), ForeignKey("api_keys.id"), nullable=False, index=True, comment="API Key ID")
    period = Column(String(20), nullable=False, comment="统计周期：day, week, month")
    period_start = Column(DateTime(timezone=True), nullable=False, comment="周期开始时间")
    period_end = Column(DateTime(timezone=True), nullable=False, comment="周期结束时间")

    # 请求统计
    total_requests = Column(Integer, nullable=False, default=0, comment="总请求数")
    successful_requests = Column(Integer, nullable=False, default=0, comment="成功请求数")
    failed_requests = Column(Integer, nullable=False, default=0, comment="失败请求数")
    rate_limited_requests = Column(Integer, nullable=False, default=0, comment="被限流请求数")

    # 性能统计
    avg_response_time_ms = Column(Float, nullable=False, default=0, comment="平均响应时间")
    peak_requests_per_second = Column(Float, nullable=False, default=0, comment="峰值 QPS")

    # 详细统计
    requests_by_endpoint = Column(JSON, default=dict, comment="按端点统计")
    requests_by_status = Column(JSON, default=dict, comment="按状态码统计")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class DBAPIRequestLog(BaseModel):
    """API 请求日志表"""
    __tablename__ = "api_request_logs"

    id = Column(String(36), primary_key=True, index=True, comment="日志 ID")
    request_id = Column(String(36), nullable=False, unique=True, index=True, comment="请求 ID")
    api_key_id = Column(String(36), ForeignKey("api_keys.id"), nullable=False, index=True, comment="API Key ID")

    # 请求信息
    method = Column(String(10), nullable=False, comment="HTTP 方法")
    path = Column(String(500), nullable=False, comment="请求路径")
    endpoint = Column(String(100), comment="端点名称")

    # 响应信息
    status_code = Column(Integer, nullable=False, comment="HTTP 状态码")
    response_time_ms = Column(Float, nullable=False, comment="响应时间 (毫秒)")

    # 客户端信息
    ip_address = Column(String(50), comment="IP 地址")
    user_agent = Column(Text, comment="客户端信息")

    # 限流信息
    is_rate_limited = Column(Boolean, nullable=False, default=False, comment="是否被限流")
    rate_limit_remaining = Column(Integer, comment="剩余请求数")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="创建时间")

    # 关系
    api_key = relationship("DBAPIKey", back_populates="request_logs")


# 添加关系
DBAPIKey.request_logs = relationship("DBAPIRequestLog", back_populates="api_key")


# ==================== P9 新增模型：AI 内容标注与身份标识系统 ====================

class DBContentLabel(BaseModel):
    """内容标签表"""
    __tablename__ = "content_labels"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="标签记录 ID")
    content_id = Column(String(36), nullable=False, unique=True, index=True, comment="内容 ID")
    content_type = Column(String(50), nullable=False, comment="内容类型：post/comment")

    # 作者类型
    author_type = Column(String(50), nullable=False, default="human", comment="作者类型：human/ai/hybrid")

    # AI 辅助程度
    ai_assist_level = Column(String(50), nullable=False, default="none", comment="AI 辅助程度")
    ai_assist_types = Column(JSON, default=list, comment="AI 辅助类型列表")
    ai_participation_rate = Column(Float, nullable=False, default=0.0, comment="AI 参与度百分比 (0-100)")

    # AI 模型信息
    ai_models = Column(JSON, comment="AI 模型信息列表")

    # 辅助记录引用
    assist_record_ids = Column(JSON, default=list, comment="关联的 AI 辅助记录 ID 列表")

    # 透明度信息
    is_verified = Column(Boolean, nullable=False, default=False, comment="是否已验证")
    verified_at = Column(DateTime(timezone=True), comment="验证时间")
    verified_by = Column(String(36), comment="验证者 ID")

    # 元数据
    badge_text = Column(String(100), comment="显示徽章文本")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class DBAIAssistRecord(BaseModel):
    """AI 辅助创作记录表"""
    __tablename__ = "ai_assist_records"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="记录 ID")
    record_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4()), comment="唯一记录 ID")

    # 内容引用
    content_id = Column(String(36), nullable=False, index=True, comment="内容 ID")
    content_type = Column(String(50), nullable=False, comment="内容类型")
    author_id = Column(String(36), nullable=False, index=True, comment="作者 ID")

    # 辅助类型
    assist_type = Column(String(50), nullable=False, comment="AI 辅助类型")

    # 辅助前后内容
    original_content = Column(Text, nullable=False, comment="原始内容")
    assisted_content = Column(Text, nullable=False, comment="辅助后内容")

    # AI 模型信息
    model_provider = Column(String(100), nullable=False, comment="模型提供方")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    model_version = Column(String(50), comment="模型版本")

    # 辅助详情
    assist_details = Column(JSON, default=dict, comment="辅助详情")
    changes_made = Column(JSON, default=list, comment="修改列表")
    confidence_score = Column(Float, nullable=False, default=0.8, comment="置信度")

    # 耗时
    duration_ms = Column(Float, comment="耗时（毫秒）")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


# ==================== P14 新增模型：声誉系统增强 ====================

class DBMemberReputation(BaseModel):
    """成员声誉表（人类与 AI 共享）"""
    __tablename__ = "member_reputation"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="声誉记录 ID")
    member_id = Column(String(36), nullable=False, unique=True, index=True, comment="成员 ID（人类或 AI）")
    member_type = Column(String(50), nullable=False, comment="成员类型：human/ai")

    # 总体声誉
    total_score = Column(Integer, nullable=False, default=100, comment="总分 0-1000")
    level = Column(String(50), nullable=False, default="newcomer", comment="声誉等级")

    # 多维度评分（各维度 0-100）
    content_quality_score = Column(Float, nullable=False, default=50.0, comment="内容质量评分")
    community_contribution_score = Column(Float, nullable=False, default=50.0, comment="社区贡献评分")
    collaboration_score = Column(Float, nullable=False, default=50.0, comment="协作能力评分")
    trustworthiness_score = Column(Float, nullable=False, default=50.0, comment="可信度评分")

    # 行为统计
    total_posts = Column(Integer, nullable=False, default=0, comment="总发帖数")
    total_comments = Column(Integer, nullable=False, default=0, comment="总评论数")
    total_upvotes_received = Column(Integer, nullable=False, default=0, comment="收到的总点赞")
    total_downvotes_received = Column(Integer, nullable=False, default=0, comment="收到的总踩")
    helpful_actions = Column(Integer, nullable=False, default=0, comment="有益行为数")
    violation_actions = Column(Integer, nullable=False, default=0, comment="违规行为数")

    # 声誉历史
    positive_actions = Column(Integer, nullable=False, default=0, comment="正面行为数")
    negative_actions = Column(Integer, nullable=False, default=0, comment="负面行为数")

    # 恢复机制
    probation_mode = Column(Boolean, nullable=False, default=False, comment="观察模式")
    probation_end_date = Column(DateTime(timezone=True), comment="观察期结束日期")
    restoration_progress = Column(Float, nullable=False, default=0.0, comment="恢复进度 0-1")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    last_action_at = Column(DateTime(timezone=True), comment="最后行为时间")


class DBReputationBehaviorLog(BaseModel):
    """声誉行为日志表"""
    __tablename__ = "reputation_behavior_logs"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="日志 ID")
    member_id = Column(String(36), nullable=False, index=True, comment="成员 ID")
    member_type = Column(String(50), nullable=False, comment="成员类型：human/ai")

    # 行为信息
    behavior_type = Column(String(50), nullable=False, index=True, comment="行为类型")
    is_positive = Column(Boolean, nullable=False, default=True, comment="是否为正面行为")
    description = Column(Text, comment="行为描述")

    # 关联内容
    content_id = Column(String(36), index=True, comment="关联内容 ID")
    content_type = Column(String(50), comment="关联内容类型")

    # 影响
    score_delta = Column(Integer, nullable=False, comment="分数变化")
    dimension_affected = Column(String(50), comment="影响的维度")

    # 上下文
    context = Column(JSON, default=dict, comment="上下文信息")
    ip_address = Column(String(50), comment="IP 地址")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class DBReputationRestoration(BaseModel):
    """声誉恢复记录表"""
    __tablename__ = "reputation_restorations"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="恢复记录 ID")
    member_id = Column(String(36), nullable=False, index=True, comment="成员 ID")
    member_type = Column(String(50), nullable=False, comment="成员类型")

    # 恢复前状态
    previous_score = Column(Integer, nullable=False, comment="恢复前分数")
    previous_level = Column(String(50), nullable=False, comment="恢复前等级")

    # 恢复原因
    reason = Column(Text, nullable=False, comment="恢复原因")
    reason_type = Column(String(50), nullable=False, comment="原因类型：appeal, auto_restore, admin_action")

    # 恢复动作
    restoration_actions = Column(JSON, default=list, comment="恢复动作列表")
    completed_actions = Column(JSON, default=list, comment="已完成动作")

    # 恢复进度
    progress = Column(Float, nullable=False, default=0.0, comment="恢复进度 0-1")
    target_score = Column(Integer, nullable=False, comment="目标分数")

    # 状态
    status = Column(String(50), nullable=False, default="in_progress", comment="状态：in_progress, completed, failed")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    completed_at = Column(DateTime(timezone=True), comment="完成时间")

    # 审核
    reviewer_id = Column(String(36), comment="审核者 ID")
    reviewer_note = Column(Text, comment="审核备注")


# ==================== P16 新增模型：社区活动系统 ====================
# 活动相关关系添加到 DBCommunityMember
DBCommunityMember.organized_activities = relationship(
    "DBActivity",
    foreign_keys="DBActivity.organizer_id",
    back_populates="organizer",
    viewonly=True
)
DBCommunityMember.activity_registrations = relationship(
    "DBActivityRegistration",
    foreign_keys="DBActivityRegistration.user_id",
    back_populates="user",
    viewonly=True
)
DBCommunityMember.activity_interactions = relationship(
    "DBActivityInteraction",
    foreign_keys="DBActivityInteraction.user_id",
    back_populates="user",
    viewonly=True
)


# ==================== P17 新增模型：跨平台集成 ====================

class DBEmailConfig(BaseModel):
    """邮件配置表"""
    __tablename__ = "email_configs"

    id = Column(String(36), primary_key=True, index=True, comment="配置 ID")
    provider = Column(String(50), nullable=False, default="smtp", comment="邮件服务提供商")
    status = Column(String(50), nullable=False, default="pending", comment="集成状态")

    # SMTP 配置
    smtp_host = Column(String(200), comment="SMTP 主机")
    smtp_port = Column(Integer, comment="SMTP 端口")
    smtp_user = Column(String(200), comment="SMTP 用户")
    smtp_password = Column(String(500), comment="SMTP 密码（加密存储）")
    use_tls = Column(Boolean, nullable=False, default=True, comment="使用 TLS")
    use_ssl = Column(Boolean, nullable=False, default=False, comment="使用 SSL")

    # API 配置
    api_key = Column(String(500), comment="API 密钥")
    api_secret = Column(String(500), comment="API 密钥（加密）")

    # 发件人配置
    sender_email = Column(String(200), comment="发件人邮箱")
    sender_name = Column(String(200), nullable=False, default="Human-AI-Community", comment="发件人名称")

    # 速率限制
    rate_limit_per_minute = Column(Integer, nullable=False, default=60, comment="每分钟发送限制")
    daily_limit = Column(Integer, nullable=False, default=10000, comment="每日发送限制")

    # 统计
    total_sent = Column(Integer, nullable=False, default=0, comment="总发送数")
    total_failed = Column(Integer, nullable=False, default=0, comment="总失败数")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    last_used_at = Column(DateTime(timezone=True), comment="最后使用时间")


class DBEmailSendRecord(BaseModel):
    """邮件发送记录表"""
    __tablename__ = "email_send_records"

    id = Column(String(36), primary_key=True, index=True, comment="记录 ID")
    recipient_email = Column(String(200), nullable=False, index=True, comment="收件人邮箱")
    subject = Column(String(500), nullable=False, comment="邮件主题")
    template_id = Column(String(36), comment="模板 ID")
    template_type = Column(String(50), comment="模板类型")
    variables = Column(JSON, nullable=False, default=dict, comment="模板变量")
    status = Column(String(50), nullable=False, default="pending", comment="发送状态")
    error_message = Column(Text, comment="错误信息")
    sent_at = Column(DateTime(timezone=True), comment="发送时间")
    opened_at = Column(DateTime(timezone=True), comment="打开时间")
    clicked_at = Column(DateTime(timezone=True), comment="点击时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class DBEmailTemplate(BaseModel):
    """邮件模板表"""
    __tablename__ = "email_templates"

    id = Column(String(36), primary_key=True, index=True, comment="模板 ID")
    name = Column(String(200), nullable=False, comment="模板名称")
    subject = Column(String(500), nullable=False, comment="邮件主题")
    content = Column(Text, nullable=False, comment="邮件内容")
    template_type = Column(String(50), nullable=False, comment="模板类型")
    variables = Column(JSON, nullable=False, default=list, comment="模板变量列表")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class DBSMSConfig(BaseModel):
    """短信配置表"""
    __tablename__ = "sms_configs"

    id = Column(String(36), primary_key=True, index=True, comment="配置 ID")
    provider = Column(String(50), nullable=False, default="aliyun", comment="短信服务提供商")
    status = Column(String(50), nullable=False, default="pending", comment="集成状态")

    # Twilio 配置
    account_sid = Column(String(200), comment="Twilio 账户 SID")
    auth_token = Column(String(500), comment="Twilio 令牌")
    from_number = Column(String(50), comment="发送号码")

    # 阿里云/腾讯云配置
    api_key = Column(String(500), comment="API 密钥")
    api_secret = Column(String(500), comment="API 密钥（加密）")
    sign_name = Column(String(100), comment="短信签名")

    # 模板配置
    templates = Column(JSON, nullable=False, default=dict, comment="模板 ID 映射")

    # 速率限制
    rate_limit_per_minute = Column(Integer, nullable=False, default=10, comment="每分钟发送限制")
    daily_limit_per_user = Column(Integer, nullable=False, default=50, comment="每用户每日限制")

    # 统计
    total_sent = Column(Integer, nullable=False, default=0, comment="总发送数")
    total_failed = Column(Integer, nullable=False, default=0, comment="总失败数")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    last_used_at = Column(DateTime(timezone=True), comment="最后使用时间")


class DBSMSSendRecord(BaseModel):
    """短信发送记录表"""
    __tablename__ = "sms_send_records"

    id = Column(String(36), primary_key=True, index=True, comment="记录 ID")
    recipient_phone = Column(String(50), nullable=False, index=True, comment="收件人手机号")
    template_code = Column(String(100), nullable=False, comment="模板代码")
    template_params = Column(JSON, nullable=False, default=dict, comment="模板参数")
    content = Column(Text, nullable=False, comment="短信内容")
    status = Column(String(50), nullable=False, default="pending", comment="发送状态")
    error_code = Column(String(50), comment="错误代码")
    error_message = Column(Text, comment="错误信息")
    provider_message_id = Column(String(200), comment="服务商消息 ID")
    sent_at = Column(DateTime(timezone=True), comment="发送时间")
    delivered_at = Column(DateTime(timezone=True), comment="送达时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class DBOAuthConfig(BaseModel):
    """OAuth 配置表"""
    __tablename__ = "oauth_configs"

    id = Column(String(36), primary_key=True, index=True, comment="配置 ID")
    provider = Column(String(50), nullable=False, comment="OAuth 提供商")
    status = Column(String(50), nullable=False, default="pending", comment="集成状态")

    # OAuth 凭证
    client_id = Column(String(500), nullable=False, comment="客户端 ID")
    client_secret = Column(String(500), nullable=False, comment="客户端密钥")

    # 端点配置
    authorize_url = Column(String(500), comment="授权 URL")
    token_url = Column(String(500), comment="令牌 URL")
    userinfo_url = Column(String(500), comment="用户信息 URL")
    redirect_uri = Column(String(500), nullable=False, comment="重定向 URI")

    # 权限范围
    scopes = Column(JSON, nullable=False, default=list, comment="权限范围列表")

    # 用户映射配置
    user_mapping = Column(JSON, nullable=False, default=dict, comment="用户字段映射")

    # 自动注册配置
    auto_register = Column(Boolean, nullable=False, default=True, comment="自动注册")
    default_role = Column(String(50), nullable=False, default="member", comment="默认角色")

    # 统计
    total_logins = Column(Integer, nullable=False, default=0, comment="总登录数")
    total_registrations = Column(Integer, nullable=False, default=0, comment="总注册数")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    last_used_at = Column(DateTime(timezone=True), comment="最后使用时间")


class DBOAuthToken(BaseModel):
    """OAuth 令牌表"""
    __tablename__ = "oauth_tokens"

    id = Column(String(36), primary_key=True, index=True, comment="令牌 ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")
    provider = Column(String(50), nullable=False, comment="OAuth 提供商")
    access_token = Column(Text, nullable=False, comment="访问令牌")
    refresh_token = Column(Text, comment="刷新令牌")
    token_type = Column(String(50), nullable=False, default="Bearer", comment="令牌类型")
    expires_in = Column(Integer, nullable=False, comment="过期时间（秒）")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="过期时间")
    scopes = Column(JSON, nullable=False, default=list, comment="权限范围")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    refreshed_at = Column(DateTime(timezone=True), comment="刷新时间")


class DBSSOConfig(BaseModel):
    """SSO 配置表"""
    __tablename__ = "sso_configs"

    id = Column(String(36), primary_key=True, index=True, comment="配置 ID")
    name = Column(String(200), nullable=False, comment="配置名称")
    protocol = Column(String(50), nullable=False, comment="SSO 协议")
    status = Column(String(50), nullable=False, default="pending", comment="集成状态")

    # SAML 2.0 配置
    idp_entity_id = Column(String(500), comment="IdP 实体 ID")
    idp_sso_url = Column(String(500), comment="IdP SSO URL")
    idp_metadata_url = Column(String(500), comment="IdP 元数据 URL")
    sp_entity_id = Column(String(500), comment="SP 实体 ID")
    assertion_consumer_service_url = Column(String(500), comment="ACS URL")

    # OIDC 配置
    oidc_issuer = Column(String(500), comment="OIDC 颁发者")
    oidc_client_id = Column(String(500), comment="OIDC 客户端 ID")
    oidc_client_secret = Column(String(500), comment="OIDC 客户端密钥")
    oidc_redirect_uri = Column(String(500), comment="OIDC 重定向 URI")

    # LDAP 配置
    ldap_host = Column(String(200), comment="LDAP 主机")
    ldap_port = Column(Integer, comment="LDAP 端口")
    ldap_bind_dn = Column(String(500), comment="LDAP 绑定 DN")
    ldap_bind_password = Column(String(500), comment="LDAP 绑定密码")
    ldap_base_dn = Column(String(500), comment="LDAP 基础 DN")
    ldap_user_filter = Column(String(500), comment="LDAP 用户过滤器")

    # 用户属性映射
    attribute_mapping = Column(JSON, nullable=False, default=dict, comment="属性映射")

    # 同步配置
    auto_sync_users = Column(Boolean, nullable=False, default=False, comment="自动同步用户")
    sync_schedule = Column(String(100), comment="同步计划（Cron 表达式）")

    # 统计
    total_logins = Column(Integer, nullable=False, default=0, comment="总登录数")
    total_users_synced = Column(Integer, nullable=False, default=0, comment="总同步用户数")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    last_sync_at = Column(DateTime(timezone=True), comment="最后同步时间")


class DBSSOSession(BaseModel):
    """SSO 会话表"""
    __tablename__ = "sso_sessions"

    id = Column(String(36), primary_key=True, index=True, comment="会话 ID")
    sso_config_id = Column(String(36), nullable=False, index=True, comment="SSO 配置 ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")
    session_id = Column(String(100), nullable=False, unique=True, comment="会话 ID")
    assertion_id = Column(String(200), comment="SAML Assertion ID")
    name_id = Column(String(500), comment="SAML NameID")
    attributes = Column(JSON, nullable=False, default=dict, comment="属性")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="过期时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    last_activity_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="最后活动时间")


class DBShareConfig(BaseModel):
    """社交分享配置表"""
    __tablename__ = "share_configs"

    id = Column(String(36), primary_key=True, index=True, comment="配置 ID")
    platform = Column(String(50), nullable=False, comment="分享平台")
    status = Column(String(50), nullable=False, default="pending", comment="集成状态")

    # 平台凭证
    app_id = Column(String(200), comment="应用 ID")
    app_secret = Column(String(500), comment="应用密钥")

    # 分享卡片配置
    default_title = Column(String(500), nullable=False, default="Human-AI-Community", comment="默认标题")
    default_description = Column(Text, nullable=False, default="人类与 AI 共享身份的社区平台", comment="默认描述")
    default_image = Column(String(500), comment="默认图片 URL")

    # URL 配置
    base_url = Column(String(500), nullable=False, default="https://community.example.com", comment="基础 URL")
    url_template = Column(String(200), nullable=False, default="/posts/{id}", comment="URL 模板")

    # 统计
    total_shares = Column(Integer, nullable=False, default=0, comment="总分享数")
    total_clicks = Column(Integer, nullable=False, default=0, comment="总点击数")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class DBShareRecord(BaseModel):
    """社交分享记录表"""
    __tablename__ = "share_records"

    id = Column(String(36), primary_key=True, index=True, comment="记录 ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")
    platform = Column(String(50), nullable=False, comment="分享平台")
    content_type = Column(String(50), nullable=False, comment="内容类型")
    content_id = Column(String(36), nullable=False, index=True, comment="内容 ID")
    content_title = Column(String(500), nullable=False, comment="内容标题")
    share_url = Column(String(500), nullable=False, comment="分享 URL")
    share_text = Column(Text, comment="分享文本")
    share_image = Column(String(500), comment="分享图片")
    share_token = Column(String(100), comment="分享追踪令牌")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class DBCrossPlatformIdentity(BaseModel):
    """跨平台身份映射表"""
    __tablename__ = "cross_platform_identities"

    id = Column(String(36), primary_key=True, index=True, comment="映射 ID")
    local_user_id = Column(String(36), nullable=False, index=True, comment="本地用户 ID")
    local_user_type = Column(String(50), nullable=False, default="member", comment="本地用户类型")

    # 外部平台身份
    external_platform = Column(String(50), nullable=False, comment="外部平台")
    external_user_id = Column(String(200), nullable=False, index=True, comment="外部用户 ID")
    external_username = Column(String(200), comment="外部用户名")
    external_metadata = Column(JSON, nullable=False, default=dict, comment="外部元数据")

    # 身份验证
    access_token = Column(Text, comment="访问令牌")
    refresh_token = Column(Text, comment="刷新令牌")
    token_expires_at = Column(DateTime(timezone=True), comment="令牌过期时间")

    # 同步状态
    is_linked = Column(Boolean, nullable=False, default=True, comment="是否已绑定")
    linked_at = Column(DateTime(timezone=True), server_default=func.now(), comment="绑定时间")
    last_synced_at = Column(DateTime(timezone=True), comment="最后同步时间")

    # 信誉携带
    reputation_synced = Column(Boolean, nullable=False, default=False, comment="信誉是否已同步")
    reputation_score = Column(Float, comment="信誉分数")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
