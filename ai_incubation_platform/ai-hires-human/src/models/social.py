"""
社交网络数据模型 - v1.19 社交网络增强

支持好友动态（朋友圈）、社区圈子（兴趣小组）、内容分享（照片/视频/状态）、
社交图谱（共同好友/兴趣匹配）、隐私设置
"""
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


# ==================== 枚举类型 ====================

class ContentType(str, Enum):
    """内容类型"""
    TEXT = "text"  # 纯文本
    IMAGE = "image"  # 图片
    VIDEO = "video"  # 视频
    LINK = "link"  # 链接
    MIXED = "mixed"  # 混合内容


class PostVisibility(str, Enum):
    """帖子可见性"""
    PUBLIC = "public"  # 公开（所有人可见）
    FRIENDS = "friends"  # 仅好友可见
    CIRCLE = "circle"  # 仅圈子成员可见
    PRIVATE = "private"  # 仅自己可见
    EMPLOYERS = "employers"  # 仅雇主可见
    WORKERS = "workers"  # 仅工人可见


class CircleType(str, Enum):
    """圈子类型"""
    SKILL = "skill"  # 技能交流圈
    INDUSTRY = "industry"  # 行业圈
    REGION = "region"  # 地域圈
    INTEREST = "interest"  # 兴趣圈
    TASK = "task"  # 任务协作圈


class CircleRole(str, Enum):
    """圈子成员角色"""
    MEMBER = "member"  # 普通成员
    MODERATOR = "moderator"  # 管理员
    ADMIN = "admin"  # 圈主


class RelationshipType(str, Enum):
    """关系类型"""
    FRIEND = "friend"  # 好友
    FOLLOWING = "following"  # 关注
    BLOCKED = "blocked"  # 拉黑
    COLLABORATED = "collaborated"  # 协作过（雇主 - 工人）


class PostStatus(str, Enum):
    """帖子状态"""
    PUBLISHED = "published"  # 已发布
    DRAFT = "draft"  # 草稿
    DELETED = "deleted"  # 已删除
    UNDER_REVIEW = "under_review"  # 审核中


# ==================== 社交帖子模型 ====================

class SocialPost(BaseModel):
    """社交帖子模型"""
    post_id: str = Field(default_factory=lambda: "")
    author_id: str
    author_type: str = "user"  # user, employer, worker, ai_agent
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None

    # 内容
    content: str  # 文本内容
    content_type: ContentType = ContentType.TEXT
    media_urls: List[str] = Field(default_factory=list)  # 图片/视频 URL 列表
    link_preview: Optional[Dict] = None  # 链接预览信息

    # 可见性
    visibility: PostVisibility = PostVisibility.PUBLIC
    allowed_circles: List[str] = Field(default_factory=list)  # 可见的圈子 ID 列表（当 visibility=circle 时）

    # 状态
    status: PostStatus = PostStatus.PUBLISHED
    is_pinned: bool = False  # 是否置顶
    is_locked: bool = False  # 是否锁定（不允许评论/互动）

    # 统计
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    view_count: int = 0

    # 标签
    tags: List[str] = Field(default_factory=list)  # 话题标签
    circle_id: Optional[str] = None  # 所属圈子 ID

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    published_at: Optional[datetime] = None


class SocialPostCreate(BaseModel):
    """创建社交帖子请求"""
    content: str
    content_type: ContentType = ContentType.TEXT
    media_urls: List[str] = Field(default_factory=list)
    link_preview: Optional[Dict] = None
    visibility: PostVisibility = PostVisibility.PUBLIC
    allowed_circles: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    circle_id: Optional[str] = None


class SocialPostUpdate(BaseModel):
    """更新社交帖子请求"""
    content: Optional[str] = None
    visibility: Optional[PostVisibility] = None
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None


# ==================== 评论模型 ====================

class SocialComment(BaseModel):
    """社交评论模型"""
    comment_id: str = Field(default_factory=lambda: "")
    post_id: str
    parent_comment_id: Optional[str] = None  # 回复的评论 ID，顶层评论为 None

    author_id: str
    author_type: str = "user"
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None

    content: str  # 评论内容

    # 统计
    like_count: int = 0
    reply_count: int = 0

    # 状态
    status: PostStatus = PostStatus.PUBLISHED
    is_deleted: bool = False

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SocialCommentCreate(BaseModel):
    """创建社交评论请求"""
    post_id: str
    content: str
    parent_comment_id: Optional[str] = None


# ==================== 互动模型 ====================

class PostInteraction(BaseModel):
    """帖子互动记录"""
    interaction_id: str = Field(default_factory=lambda: "")
    post_id: str
    user_id: str
    user_type: str = "user"

    interaction_type: str = "like"  # like, love, laugh, wow, sad, angry
    created_at: datetime = Field(default_factory=datetime.now)


class Bookmark(BaseModel):
    """收藏记录"""
    bookmark_id: str = Field(default_factory=lambda: "")
    user_id: str
    post_id: str
    created_at: datetime = Field(default_factory=datetime.now)


class Share(BaseModel):
    """分享记录"""
    share_id: str = Field(default_factory=lambda: "")
    user_id: str
    post_id: str
    share_type: str = "repost"  # repost, external
    share_content: Optional[str] = None  # 转发时的附加内容
    external_url: Optional[str] = None  # 外部链接（当 share_type=external 时）
    created_at: datetime = Field(default_factory=datetime.now)


# ==================== 社交关系模型 ====================

class SocialRelationship(BaseModel):
    """社交关系模型"""
    relationship_id: str = Field(default_factory=lambda: "")

    user_id: str  # 发起方
    target_id: str  # 目标方

    relationship_type: RelationshipType
    status: str = "active"  # active, pending, rejected

    # 双向关系标记（用于好友关系）
    is_mutual: bool = False  # 是否互为好友

    # 协作关系特有
    collaboration_count: int = 0  # 协作次数
    total_transaction_amount: float = 0.0  # 总交易金额

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class FriendRequest(BaseModel):
    """好友请求"""
    request_id: str = Field(default_factory=lambda: "")
    sender_id: str
    receiver_id: str
    message: Optional[str] = None  # 好友申请消息
    status: str = "pending"  # pending, accepted, rejected
    created_at: datetime = Field(default_factory=datetime.now)
    responded_at: Optional[datetime] = None


# ==================== 圈子模型 ====================

class SocialCircle(BaseModel):
    """社交圈子模型"""
    circle_id: str = Field(default_factory=lambda: "")

    # 基本信息
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    cover_image: Optional[str] = None

    # 类型
    circle_type: CircleType
    category: Optional[str] = None  # 分类（如技能圈的技能名称）

    # 创建者
    creator_id: str
    creator_name: Optional[str] = None

    # 访问控制
    join_type: str = "open"  # open, approval, invite_only
    visibility: PostVisibility = PostVisibility.PUBLIC

    # 规则
    rules: List[str] = Field(default_factory=list)  # 圈子规则

    # 统计
    member_count: int = 0
    post_count: int = 0

    # 状态
    is_active: bool = True
    is_official: bool = False  # 是否官方圈子

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SocialCircleCreate(BaseModel):
    """创建社交圈子请求"""
    name: str
    description: Optional[str] = None
    circle_type: CircleType
    category: Optional[str] = None
    join_type: str = "open"
    visibility: PostVisibility = PostVisibility.PUBLIC
    rules: List[str] = Field(default_factory=list)


class CircleMember(BaseModel):
    """圈子成员模型"""
    membership_id: str = Field(default_factory=lambda: "")
    circle_id: str
    user_id: str
    user_name: Optional[str] = None

    role: CircleRole = CircleRole.MEMBER
    status: str = "active"  # active, muted, banned

    # 加入方式
    join_method: str = "apply"  # apply, invite

    # 时间
    joined_at: datetime = Field(default_factory=datetime.now)
    last_active_at: Optional[datetime] = None


class CircleJoinRequest(BaseModel):
    """加入圈子申请"""
    request_id: str = Field(default_factory=lambda: "")
    circle_id: str
    user_id: str
    message: Optional[str] = None  # 申请消息
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime = Field(default_factory=datetime.now)
    responded_at: Optional[datetime] = None


# ==================== 社交图谱模型 ====================

class SocialGraphConnection(BaseModel):
    """社交图谱连接"""
    user_id: str
    connected_user_id: str
    connection_type: str  # friend, follower, following, collaborated
    connection_strength: float = 0.0  # 连接强度 (0-1)
    common_circles: List[str] = Field(default_factory=list)  # 共同圈子
    common_interests: List[str] = Field(default_factory=list)  # 共同兴趣
    collaboration_count: int = 0  # 协作次数


class MutualFriend(BaseModel):
    """共同好友"""
    friend_id: str
    friend_name: str
    friend_avatar: Optional[str] = None
    mutual_friend_count: int = 0  # 与目标用户的共同好友数量


# ==================== 隐私设置模型 ====================

class PrivacySettings(BaseModel):
    """隐私设置模型"""
    user_id: str

    # 动态可见性
    who_can_see_posts: str = "friends"  # everyone, friends, self
    who_can_comment: str = "friends"  # everyone, friends, self
    who_can_message: str = "friends"  # everyone, friends, nobody

    # 个人信息
    show_real_name: bool = False  # 是否显示真实姓名
    show_location: bool = False  # 是否显示位置
    show_contact_info: bool = False  # 是否显示联系方式
    show_activity_status: bool = True  # 是否显示在线状态

    # 社交关系
    allow_friend_requests: bool = True  # 允许好友申请
    hide_friend_list: bool = True  # 隐藏好友列表
    hide_circle_memberships: bool = False  # 隐藏圈子成员身份

    # 搜索与发现
    appear_in_search: bool = True  # 在搜索结果中出现
    show_in_recommendations: bool = True  # 在推荐中出现

    # 通知
    notify_on_like: bool = True  # 点赞通知
    notify_on_comment: bool = True  # 评论通知
    notify_on_follow: bool = True  # 关注通知
    notify_on_circle_invite: bool = True  # 圈子邀请通知

    # 黑名单
    blocked_users: List[str] = Field(default_factory=list)

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PrivacySettingsUpdate(BaseModel):
    """隐私设置更新请求"""
    who_can_see_posts: Optional[str] = None
    who_can_comment: Optional[str] = None
    who_can_message: Optional[str] = None
    show_real_name: Optional[bool] = None
    show_location: Optional[bool] = None
    show_contact_info: Optional[bool] = None
    show_activity_status: Optional[bool] = None
    allow_friend_requests: Optional[bool] = None
    hide_friend_list: Optional[bool] = None
    appear_in_search: Optional[bool] = None
    show_in_recommendations: Optional[bool] = None


# ==================== Feed/时间线模型 ====================

class FeedPost(BaseModel):
    """Feed 中的帖子"""
    post: SocialPost
    author_info: Optional[Dict] = None
    is_liked: bool = False  # 当前用户是否已点赞
    is_bookmarked: bool = False  # 当前用户是否已收藏
    user_interaction: Optional[str] = None  # 当前用户的互动类型


class FeedRequest(BaseModel):
    """Feed 请求"""
    user_id: str
    feed_type: str = "home"  # home, circle, profile
    circle_id: Optional[str] = None  # 圈子 ID（当 feed_type=circle 时）
    profile_user_id: Optional[str] = None  # 用户 ID（当 feed_type=profile 时）
    skip: int = 0
    limit: int = 20


class FeedResponse(BaseModel):
    """Feed 响应"""
    posts: List[FeedPost]
    total: int
    has_more: bool


# ==================== 通知模型 ====================

class SocialNotificationType(str, Enum):
    """社交通知类型"""
    LIKE = "like"  # 点赞
    COMMENT = "comment"  # 评论
    REPLY = "reply"  # 回复
    FOLLOW = "follow"  # 关注
    FRIEND_REQUEST = "friend_request"  # 好友申请
    CIRCLE_INVITE = "circle_invite"  # 圈子邀请
    CIRCLE_JOIN_APPROVED = "circle_join_approved"  # 加入圈子批准
    MENTION = "mention"  # 提及
    SHARE = "share"  # 分享


class SocialNotification(BaseModel):
    """社交通知"""
    notification_id: str = Field(default_factory=lambda: "")
    recipient_id: str

    notification_type: SocialNotificationType
    sender_id: str
    sender_name: Optional[str] = None
    sender_avatar: Optional[str] = None

    # 关联内容
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    circle_id: Optional[str] = None

    # 内容预览
    preview_content: Optional[str] = None

    # 状态
    is_read: bool = False

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)


# ==================== 响应模型 ====================

class PostListResponse(BaseModel):
    """帖子列表响应"""
    posts: List[SocialPost]
    total: int
    has_more: bool


class CircleListResponse(BaseModel):
    """圈子列表响应"""
    circles: List[SocialCircle]
    total: int
    has_more: bool


class RelationshipListResponse(BaseModel):
    """关系列表响应"""
    relationships: List[SocialRelationship]
    total: int


class FriendListResponse(BaseModel):
    """好友列表响应"""
    friends: List[Dict]  # 包含用户信息和关系状态
    total: int
    has_more: bool


class MutualConnectionResponse(BaseModel):
    """共同连接响应"""
    mutual_friends: List[MutualFriend]
    mutual_circles: List[SocialCircle]
    total_mutual_friends: int
    total_mutual_circles: int
