"""
社区活动系统 - 数据库模型
支持线上活动（AMA/直播/投票）、线下聚会、活动管理（报名/签到/回顾）、直播系统等功能
"""
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, DateTime, func, Enum as SQLAlchemyEnum, Boolean, Float, Text, JSON
from sqlalchemy.orm import relationship, declarative_base
from .base import BaseModel
from enum import Enum


# ==================== 活动基础模型 ====================

class ActivityTypeEnum(str, Enum):
    """活动类型枚举"""
    ONLINE = "online"  # 线上活动
    OFFLINE = "offline"  # 线下活动
    LIVE = "live"  # 直播活动
    AMA = "ama"  # AMA 问答
    VOTE = "vote"  # 投票活动
    MEETUP = "meetup"  # 线下聚会
    WORKSHOP = "workshop"  # 工作坊
    WEBINAR = "webinar"  # 网络研讨会


class ActivityStatusEnum(str, Enum):
    """活动状态枚举"""
    DRAFT = "draft"  # 草稿
    PUBLISHED = "published"  # 已发布
    REGISTRATION_OPEN = "registration_open"  # 报名中
    REGISTRATION_CLOSED = "registration_closed"  # 报名截止
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    ARCHIVED = "archived"  # 已归档


class ActivityRoleEnum(str, Enum):
    """活动角色枚举"""
    ORGANIZER = "organizer"  # 组织者
    CO_HOST = "co_host"  # 协办者
    SPEAKER = "speaker"  # 嘉宾/讲师
    ATTENDEE = "attendee"  # 参与者
    VOLUNTEER = "volunteer"  # 志愿者


class DBActivity(BaseModel):
    """活动主表"""
    __tablename__ = "activities"

    id = Column(String(36), primary_key=True, index=True, comment="活动 ID")
    title = Column(String(200), nullable=False, comment="活动标题")
    description = Column(Text, comment="活动描述")
    content = Column(Text, comment="活动详细内容（富文本/Markdown）")

    # 活动类型
    activity_type = Column(SQLAlchemyEnum(ActivityTypeEnum), nullable=False, comment="活动类型")
    status = Column(SQLAlchemyEnum(ActivityStatusEnum), nullable=False, default=ActivityStatusEnum.DRAFT, comment="活动状态")

    # 组织者信息
    organizer_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="组织者 ID")
    co_organizers = Column(JSON, default=list, comment="协办者 ID 列表")

    # 时间信息
    start_time = Column(DateTime(timezone=True), nullable=False, comment="活动开始时间")
    end_time = Column(DateTime(timezone=True), nullable=False, comment="活动结束时间")
    registration_start = Column(DateTime(timezone=True), comment="报名开始时间")
    registration_end = Column(DateTime(timezone=True), comment="报名截止时间")

    # 地点信息
    location_type = Column(String(20), nullable=False, default="online", comment="地点类型：online/offline/hybrid")
    location_address = Column(String(500), comment="线下地址")
    location_online_url = Column(String(500), comment="线上链接")
    location_online_platform = Column(String(100), comment="线上平台名称")

    # 人数限制
    max_participants = Column(Integer, comment="最大参与人数")
    current_participants = Column(Integer, nullable=False, default=0, comment="当前参与人数")
    max_speakers = Column(Integer, comment="最大嘉宾数")

    # 活动标签
    tags = Column(JSON, default=list, comment="活动标签列表")
    cover_image_url = Column(String(500), comment="封面图片 URL")

    # 统计信息
    view_count = Column(Integer, nullable=False, default=0, comment="浏览次数")
    registration_count = Column(Integer, nullable=False, default=0, comment="报名人数")
    attendance_count = Column(Integer, nullable=False, default=0, comment="实际出席人数")

    # 互动设置
    allow_comments = Column(Boolean, nullable=False, default=True, comment="是否允许评论")
    allow_chat = Column(Boolean, nullable=False, default=True, comment="是否允许聊天")
    allow_questions = Column(Boolean, nullable=False, default=True, comment="是否允许提问")

    # 元数据
    extra_data = Column(JSON, default=dict, comment="扩展数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 关系
    organizer = relationship("DBCommunityMember", foreign_keys=[organizer_id], back_populates="organized_activities", viewonly=True)
    registrations = relationship("DBActivityRegistration", back_populates="activity", cascade="all, delete-orphan")
    sessions = relationship("DBActivitySession", back_populates="activity", cascade="all, delete-orphan")
    interactions = relationship("DBActivityInteraction", back_populates="activity", cascade="all, delete-orphan")


# ==================== 活动报名 ====================

class RegistrationStatusEnum(str, Enum):
    """报名状态枚举"""
    PENDING = "pending"  # 待确认
    CONFIRMED = "confirmed"  # 已确认
    WAITLIST = "waitlist"  # 候补
    CANCELLED = "cancelled"  # 已取消
    NO_SHOW = "no_show"  # 未出席
    ATTENDED = "attended"  # 已出席


class DBActivityRegistration(BaseModel):
    """活动报名表"""
    __tablename__ = "activity_registrations"

    id = Column(String(36), primary_key=True, index=True, comment="报名记录 ID")
    activity_id = Column(String(36), ForeignKey("activities.id"), nullable=False, index=True, comment="活动 ID")
    user_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="用户 ID")

    # 报名角色
    role = Column(SQLAlchemyEnum(ActivityRoleEnum), nullable=False, default=ActivityRoleEnum.ATTENDEE, comment="活动角色")

    # 报名状态
    status = Column(SQLAlchemyEnum(RegistrationStatusEnum), nullable=False, default=RegistrationStatusEnum.PENDING, comment="报名状态")

    # 报名信息
    registration_note = Column(String(500), comment="报名备注")
    approval_note = Column(String(500), comment="审批备注")

    # 签到信息
    checked_in = Column(Boolean, nullable=False, default=False, comment="是否已签到")
    check_in_time = Column(DateTime(timezone=True), comment="签到时间")
    check_out_time = Column(DateTime(timezone=True), comment="签退时间")

    # 互动统计
    interaction_count = Column(Integer, nullable=False, default=0, comment="互动次数")
    questions_asked = Column(Integer, nullable=False, default=0, comment="提问次数")

    # 元数据
    extra_data = Column(JSON, default=dict, comment="扩展数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 关系
    activity = relationship("DBActivity", back_populates="registrations", viewonly=True)
    user = relationship("DBCommunityMember", back_populates="activity_registrations", viewonly=True)


# ==================== 活动场次/议程 ====================

class DBActivitySession(BaseModel):
    """活动场次/议程表"""
    __tablename__ = "activity_sessions"

    id = Column(String(36), primary_key=True, index=True, comment="场次 ID")
    activity_id = Column(String(36), ForeignKey("activities.id"), nullable=False, index=True, comment="活动 ID")

    # 场次信息
    title = Column(String(200), nullable=False, comment="场次标题")
    description = Column(Text, comment="场次描述")

    # 时间
    start_time = Column(DateTime(timezone=True), nullable=False, comment="开始时间")
    end_time = Column(DateTime(timezone=True), nullable=False, comment="结束时间")

    # 嘉宾/讲师
    speakers = Column(JSON, default=list, comment="嘉宾/讲师 ID 列表")

    # 场次类型
    session_type = Column(String(50), default="presentation", comment="场次类型：presentation/panel/workshop/qanda")

    # 顺序
    order_index = Column(Integer, nullable=False, default=0, comment="显示顺序")

    # 元数据
    extra_data = Column(JSON, default=dict, comment="扩展数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 关系
    activity = relationship("DBActivity", back_populates="sessions")


# ==================== 活动互动 ====================

class ActivityInteractionTypeEnum(str, Enum):
    """活动互动类型枚举"""
    COMMENT = "comment"  # 评论
    QUESTION = "question"  # 提问
    VOTE = "vote"  # 投票
    REACTION = "reaction"  # 表情反应
    CHAT = "chat"  # 聊天消息
    GIFT = "gift"  # 礼物/打赏
    SHARE = "share"  # 分享


class DBActivityInteraction(BaseModel):
    """活动互动表"""
    __tablename__ = "activity_interactions"

    id = Column(String(36), primary_key=True, index=True, comment="互动记录 ID")
    activity_id = Column(String(36), ForeignKey("activities.id"), nullable=False, index=True, comment="活动 ID")
    user_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="用户 ID")

    # 互动类型
    interaction_type = Column(SQLAlchemyEnum(ActivityInteractionTypeEnum), nullable=False, comment="互动类型")

    # 互动内容
    content = Column(Text, comment="互动内容")

    # 关联信息
    parent_id = Column(String(36), comment="父互动 ID（用于回复）")
    target_id = Column(String(36), comment="目标 ID（如被回答的问题 ID）")
    session_id = Column(String(36), comment="所属场次 ID")

    # 互动状态
    is_approved = Column(Boolean, nullable=False, default=True, comment="是否已审核")
    is_hidden = Column(Boolean, nullable=False, default=False, comment="是否隐藏")
    is_pinned = Column(Boolean, nullable=False, default=False, comment="是否置顶")
    is_answered = Column(Boolean, nullable=False, default=False, comment="是否已回答（针对提问）")

    # 互动统计
    like_count = Column(Integer, nullable=False, default=0, comment="点赞数")
    reply_count = Column(Integer, nullable=False, default=0, comment="回复数")

    # 元数据
    extra_data = Column(JSON, default=dict, comment="扩展数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 关系
    activity = relationship("DBActivity", back_populates="interactions", viewonly=True)
    user = relationship("DBCommunityMember", back_populates="activity_interactions", viewonly=True)


# ==================== 直播相关模型 ====================

class LiveStreamStatusEnum(str, Enum):
    """直播状态枚举"""
    SCHEDULED = "scheduled"  # 已安排
    TESTING = "testing"  # 测试中
    LIVE = "live"  # 直播中
    ENDED = "ended"  # 已结束
    RECORDED = "recorded"  # 已录制


class DBLiveStream(BaseModel):
    """直播信息表"""
    __tablename__ = "live_streams"

    id = Column(String(36), primary_key=True, index=True, comment="直播 ID")
    activity_id = Column(String(36), ForeignKey("activities.id"), nullable=False, unique=True, index=True, comment="关联活动 ID")

    # 直播状态
    status = Column(SQLAlchemyEnum(LiveStreamStatusEnum), nullable=False, default=LiveStreamStatusEnum.SCHEDULED, comment="直播状态")

    # 直播配置
    stream_key = Column(String(100), unique=True, index=True, comment="推流密钥")
    stream_url = Column(String(500), comment="推流地址")
    playback_url = Column(String(500), comment="播放地址")

    # 直播统计
    viewer_count = Column(Integer, nullable=False, default=0, comment="当前观看人数")
    peak_viewer_count = Column(Integer, nullable=False, default=0, comment="峰值观看人数")
    total_views = Column(Integer, nullable=False, default=0, comment="累计观看次数")
    like_count = Column(Integer, nullable=False, default=0, comment="点赞数")
    gift_value = Column(BigInteger, nullable=False, default=0, comment="礼物总价值（分）")

    # 直播设置
    is_chat_enabled = Column(Boolean, nullable=False, default=True, comment="是否启用聊天")
    is_gift_enabled = Column(Boolean, nullable=False, default=True, comment="是否启用礼物")
    is_record_enabled = Column(Boolean, nullable=False, default=True, comment="是否录制")

    # 录制信息
    recording_url = Column(String(500), comment="录制视频 URL")
    recording_duration = Column(Integer, comment="录制时长（秒）")

    # 元数据
    extra_data = Column(JSON, default=dict, comment="扩展数据")
    started_at = Column(DateTime(timezone=True), comment="开始直播时间")
    ended_at = Column(DateTime(timezone=True), comment="结束直播时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


# ==================== 直播聊天/弹幕 ====================

class LiveChatMessage(BaseModel):
    """直播聊天消息表"""
    __tablename__ = "live_chat_messages"

    id = Column(String(36), primary_key=True, index=True, comment="消息 ID")
    stream_id = Column(String(36), ForeignKey("live_streams.id"), nullable=False, index=True, comment="直播 ID")
    user_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="用户 ID")

    # 消息内容
    content = Column(Text, nullable=False, comment="消息内容")
    message_type = Column(String(20), default="text", comment="消息类型：text/gift/system")

    # 消息状态
    is_moderated = Column(Boolean, nullable=False, default=False, comment="是否已审核")
    is_hidden = Column(Boolean, nullable=False, default=False, comment="是否隐藏")

    # 礼物信息（如果是礼物消息）
    gift_info = Column(JSON, comment="礼物信息")

    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


# ==================== 投票活动模型 ====================

class VoteTypeEnum(str, Enum):
    """投票类型枚举"""
    SINGLE_CHOICE = "single_choice"  # 单选
    MULTIPLE_CHOICE = "multiple_choice"  # 多选
    RANKING = "ranking"  # 排序


class VoteStatusEnum(str, Enum):
    """投票状态枚举"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 进行中
    ENDED = "ended"  # 已结束


class DBVote(BaseModel):
    """投票主表"""
    __tablename__ = "activity_votes"

    id = Column(String(36), primary_key=True, index=True, comment="投票 ID")
    activity_id = Column(String(36), ForeignKey("activities.id"), nullable=False, index=True, comment="关联活动 ID")

    # 投票信息
    title = Column(String(200), nullable=False, comment="投票标题")
    description = Column(Text, comment="投票描述")

    # 投票类型
    vote_type = Column(SQLAlchemyEnum(VoteTypeEnum), nullable=False, comment="投票类型")
    status = Column(SQLAlchemyEnum(VoteStatusEnum), nullable=False, default=VoteStatusEnum.DRAFT, comment="投票状态")

    # 投票规则
    min_choices = Column(Integer, nullable=False, default=1, comment="最少选择数")
    max_choices = Column(Integer, nullable=False, default=1, comment="最多选择数")
    is_anonymous = Column(Boolean, nullable=False, default=False, comment="是否匿名投票")
    show_results_before_vote = Column(Boolean, nullable=False, default=False, comment="投票前是否显示结果")

    # 时间控制
    start_time = Column(DateTime(timezone=True), nullable=False, comment="开始时间")
    end_time = Column(DateTime(timezone=True), nullable=False, comment="结束时间")

    # 统计
    total_voters = Column(Integer, nullable=False, default=0, comment="参与人数")
    total_votes = Column(Integer, nullable=False, default=0, comment="总票数")

    # 元数据
    extra_data = Column(JSON, default=dict, comment="扩展数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class DBVoteOption(BaseModel):
    """投票选项表"""
    __tablename__ = "activity_vote_options"

    id = Column(String(36), primary_key=True, index=True, comment="选项 ID")
    vote_id = Column(String(36), ForeignKey("activity_votes.id"), nullable=False, index=True, comment="投票 ID")

    # 选项信息
    title = Column(String(200), nullable=False, comment="选项标题")
    description = Column(String(500), comment="选项描述")
    image_url = Column(String(500), comment="选项图片 URL")

    # 顺序
    order_index = Column(Integer, nullable=False, default=0, comment="显示顺序")

    # 统计
    vote_count = Column(Integer, nullable=False, default=0, comment="得票数")
    vote_percentage = Column(Float, nullable=False, default=0.0, comment="得票百分比")

    # 元数据
    extra_data = Column(JSON, default=dict, comment="扩展数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class DBVoteRecord(BaseModel):
    """投票记录表"""
    __tablename__ = "activity_vote_records"

    id = Column(String(36), primary_key=True, index=True, comment="投票记录 ID")
    vote_id = Column(String(36), ForeignKey("activity_votes.id"), nullable=False, index=True, comment="投票 ID")
    user_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="用户 ID")

    # 选择的选项
    selected_options = Column(JSON, nullable=False, default=list, comment="选择的选项 ID 列表")

    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="投票时间")

    __table_args__ = (
        __import__('sqlalchemy').UniqueConstraint('vote_id', 'user_id', name='uq_vote_user'),
    )


# ==================== 活动回顾/总结 ====================

class DBActivityRecap(BaseModel):
    """活动回顾表"""
    __tablename__ = "activity_recaps"

    id = Column(String(36), primary_key=True, index=True, comment="回顾 ID")
    activity_id = Column(String(36), ForeignKey("activities.id"), nullable=False, unique=True, index=True, comment="活动 ID")

    # 回顾内容
    title = Column(String(200), nullable=False, comment="回顾标题")
    summary = Column(Text, comment="活动总结")
    content = Column(Text, comment="回顾详细内容")

    # 统计数据
    key_metrics = Column(JSON, default=dict, comment="关键指标")

    # 媒体资源
    photos = Column(JSON, default=list, comment="照片列表")
    videos = Column(JSON, default=list, comment="视频列表")
    recordings = Column(JSON, default=list, comment="录制视频列表")

    # 反馈收集
    feedback_summary = Column(JSON, comment="反馈汇总")
    nps_score = Column(Float, comment="净推荐值")
    satisfaction_score = Column(Float, comment="满意度评分")

    # 元数据
    author_id = Column(String(36), comment="作者 ID")
    is_published = Column(Boolean, nullable=False, default=False, comment="是否发布")
    published_at = Column(DateTime(timezone=True), comment="发布时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


# ==================== 活动推荐 ====================

class DBActivityRecommendation(BaseModel):
    """活动推荐表"""
    __tablename__ = "activity_recommendations"

    id = Column(String(36), primary_key=True, index=True, comment="推荐 ID")
    user_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="用户 ID")
    activity_id = Column(String(36), ForeignKey("activities.id"), nullable=False, index=True, comment="活动 ID")

    # 推荐信息
    recommendation_score = Column(Float, nullable=False, default=0.0, comment="推荐分数")
    recommendation_reason = Column(String(200), comment="推荐理由")

    # 推荐来源
    source = Column(String(50), default="algorithm", comment="推荐来源：algorithm/manual/similar_users")

    # 用户反馈
    is_clicked = Column(Boolean, nullable=False, default=False, comment="是否点击")
    is_registered = Column(Boolean, nullable=False, default=False, comment="是否报名")
    feedback_type = Column(String(20), comment="反馈类型：like/dislike/ignore")

    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    clicked_at = Column(DateTime(timezone=True), comment="点击时间")


# ==================== 更新 DBCommunityMember 添加活动相关关系 ====================
# 注意：这些关系将在 models.py 中添加到 DBCommunityMember 类
