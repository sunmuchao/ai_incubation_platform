"""
社区活动系统 - 实体模型
用于 API 请求/响应的数据验证
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 枚举类型 ====================

class ActivityType(str, Enum):
    """活动类型"""
    ONLINE = "online"
    OFFLINE = "offline"
    LIVE = "live"
    AMA = "ama"
    VOTE = "vote"
    MEETUP = "meetup"
    WORKSHOP = "workshop"
    WEBINAR = "webinar"


class ActivityStatus(str, Enum):
    """活动状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ActivityRole(str, Enum):
    """活动角色"""
    ORGANIZER = "organizer"
    CO_HOST = "co_host"
    SPEAKER = "speaker"
    ATTENDEE = "attendee"
    VOLUNTEER = "volunteer"


class RegistrationStatus(str, Enum):
    """报名状态"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    WAITLIST = "waitlist"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    ATTENDED = "attended"


class InteractionType(str, Enum):
    """互动类型"""
    COMMENT = "comment"
    QUESTION = "question"
    VOTE = "vote"
    REACTION = "reaction"
    CHAT = "chat"
    GIFT = "gift"
    SHARE = "share"


class VoteType(str, Enum):
    """投票类型"""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    RANKING = "ranking"


class VoteStatus(str, Enum):
    """投票状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    ENDED = "ended"


class LiveStreamStatus(str, Enum):
    """直播状态"""
    SCHEDULED = "scheduled"
    TESTING = "testing"
    LIVE = "live"
    ENDED = "ended"
    RECORDED = "recorded"


# ==================== 活动相关模型 ====================

class CreateActivityRequest(BaseModel):
    """创建活动请求"""
    title: str = Field(..., min_length=1, max_length=200, description="活动标题")
    description: str = Field(..., description="活动描述")
    content: Optional[str] = Field(None, description="活动详细内容")
    activity_type: ActivityType = Field(..., description="活动类型")
    start_time: datetime = Field(..., description="活动开始时间")
    end_time: datetime = Field(..., description="活动结束时间")
    location_type: str = Field(default="online", description="地点类型")
    location_address: Optional[str] = Field(None, description="线下地址")
    location_online_url: Optional[str] = Field(None, description="线上链接")
    max_participants: Optional[int] = Field(None, description="最大参与人数")
    tags: Optional[List[str]] = Field(default=[], description="活动标签")
    cover_image_url: Optional[str] = Field(None, description="封面图片 URL")


class UpdateActivityRequest(BaseModel):
    """更新活动请求"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    content: Optional[str] = None
    status: Optional[ActivityStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    location_type: Optional[str] = None
    location_address: Optional[str] = None
    location_online_url: Optional[str] = None
    max_participants: Optional[int] = None
    tags: Optional[List[str]] = None
    cover_image_url: Optional[str] = None
    allow_comments: Optional[bool] = None
    allow_chat: Optional[bool] = None
    allow_questions: Optional[bool] = None


class ActivityResponse(BaseModel):
    """活动响应"""
    id: str
    title: str
    description: str
    content: Optional[str]
    activity_type: str
    status: str
    organizer_id: str
    co_organizers: List[str]
    start_time: datetime
    end_time: datetime
    registration_start: Optional[datetime]
    registration_end: Optional[datetime]
    location_type: str
    location_address: Optional[str]
    location_online_url: Optional[str]
    max_participants: Optional[int]
    current_participants: int
    tags: List[str]
    cover_image_url: Optional[str]
    view_count: int
    registration_count: int
    attendance_count: int
    allow_comments: bool
    allow_chat: bool
    allow_questions: bool
    created_at: datetime
    updated_at: Optional[datetime]


class ActivityListItem(BaseModel):
    """活动列表项"""
    id: str
    title: str
    description: str
    activity_type: str
    status: str
    start_time: datetime
    end_time: datetime
    location_type: str
    current_participants: int
    max_participants: Optional[int]
    cover_image_url: Optional[str]
    view_count: int
    registration_count: int


# ==================== 报名相关模型 ====================

class RegisterActivityRequest(BaseModel):
    """报名活动请求"""
    role: ActivityRole = Field(default=ActivityRole.ATTENDEE, description="活动角色")
    registration_note: Optional[str] = Field(None, description="报名备注")


class RegistrationResponse(BaseModel):
    """报名响应"""
    id: str
    activity_id: str
    user_id: str
    role: str
    status: str
    registration_note: Optional[str]
    approval_note: Optional[str]
    checked_in: bool
    check_in_time: Optional[datetime]
    interaction_count: int
    questions_asked: int
    created_at: datetime


# ==================== 议程相关模型 ====================

class CreateSessionRequest(BaseModel):
    """创建议程请求"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    speakers: Optional[List[str]] = Field(default=[])
    session_type: str = Field(default="presentation")
    order_index: int = Field(default=0)


class SessionResponse(BaseModel):
    """议程响应"""
    id: str
    activity_id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    speakers: List[str]
    session_type: str
    order_index: int
    created_at: datetime


# ==================== 互动相关模型 ====================

class CreateInteractionRequest(BaseModel):
    """创建互动请求"""
    interaction_type: InteractionType = Field(...)
    content: Optional[str] = Field(None, description="互动内容")
    parent_id: Optional[str] = Field(None, description="父互动 ID")
    target_id: Optional[str] = Field(None, description="目标 ID")
    session_id: Optional[str] = Field(None, description="场次 ID")


class InteractionResponse(BaseModel):
    """互动响应"""
    id: str
    activity_id: str
    user_id: str
    interaction_type: str
    content: Optional[str]
    parent_id: Optional[str]
    target_id: Optional[str]
    session_id: Optional[str]
    is_approved: bool
    is_hidden: bool
    is_pinned: bool
    is_answered: bool
    like_count: int
    reply_count: int
    created_at: datetime


# ==================== 直播相关模型 ====================

class CreateLiveStreamRequest(BaseModel):
    """创建直播请求"""
    is_chat_enabled: bool = Field(default=True)
    is_gift_enabled: bool = Field(default=True)
    is_record_enabled: bool = Field(default=True)


class LiveStreamResponse(BaseModel):
    """直播响应"""
    id: str
    activity_id: str
    status: str
    stream_key: Optional[str]  # 仅对组织者显示
    stream_url: Optional[str]
    playback_url: Optional[str]
    viewer_count: int
    peak_viewer_count: int
    total_views: int
    like_count: int
    gift_value: int
    is_chat_enabled: bool
    is_gift_enabled: bool
    is_record_enabled: bool
    recording_url: Optional[str]
    recording_duration: Optional[int]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class ChatMessageRequest(BaseModel):
    """聊天消息请求"""
    content: str = Field(..., min_length=1, max_length=1000)
    message_type: str = Field(default="text")
    gift_info: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    """聊天消息响应"""
    id: str
    stream_id: str
    user_id: str
    content: str
    message_type: str
    gift_info: Optional[Dict[str, Any]]
    created_at: datetime


# ==================== 投票相关模型 ====================

class CreateVoteRequest(BaseModel):
    """创建投票请求"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    vote_type: VoteType = Field(...)
    start_time: datetime
    end_time: datetime
    min_choices: int = Field(default=1)
    max_choices: int = Field(default=1)
    is_anonymous: bool = Field(default=False)
    show_results_before_vote: bool = Field(default=False)


class AddVoteOptionRequest(BaseModel):
    """添加投票选项请求"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None


class CastVoteRequest(BaseModel):
    """投票请求"""
    selected_options: List[str] = Field(..., min_length=1)


class VoteOptionResponse(BaseModel):
    """投票选项响应"""
    id: str
    vote_id: str
    title: str
    description: Optional[str]
    image_url: Optional[str]
    order_index: int
    vote_count: int
    vote_percentage: float
    created_at: datetime


class VoteResponse(BaseModel):
    """投票响应"""
    id: str
    activity_id: str
    title: str
    description: Optional[str]
    vote_type: str
    status: str
    min_choices: int
    max_choices: int
    is_anonymous: bool
    show_results_before_vote: bool
    start_time: datetime
    end_time: datetime
    total_voters: int
    total_votes: int
    created_at: datetime
    updated_at: Optional[datetime]
    options: Optional[List[VoteOptionResponse]] = None


class VoteResultsResponse(BaseModel):
    """投票结果响应"""
    vote_id: str
    title: str
    vote_type: str
    status: str
    total_voters: int
    total_votes: int
    is_anonymous: bool
    options: List[Dict[str, Any]]


# ==================== 活动回顾相关模型 ====================

class CreateRecapRequest(BaseModel):
    """创建活动回顾请求"""
    title: str = Field(..., min_length=1, max_length=200)
    summary: Optional[str] = None
    content: Optional[str] = None
    key_metrics: Optional[Dict[str, Any]] = None
    photos: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    is_published: bool = Field(default=False)


class RecapResponse(BaseModel):
    """活动回顾响应"""
    id: str
    activity_id: str
    title: str
    summary: Optional[str]
    content: Optional[str]
    key_metrics: Optional[Dict[str, Any]]
    photos: List[str]
    videos: List[str]
    feedback_summary: Optional[Dict[str, Any]]
    nps_score: Optional[float]
    satisfaction_score: Optional[float]
    is_published: bool
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


# ==================== 通用响应模型 ====================

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error_code: str = "error"
    message: str
