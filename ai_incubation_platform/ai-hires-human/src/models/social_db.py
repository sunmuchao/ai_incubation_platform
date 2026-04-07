"""
社交网络数据库 ORM 模型 - v1.19 社交网络增强

支持好友动态（朋友圈）、社区圈子（兴趣小组）、内容分享、社交图谱、隐私设置
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ==================== 社交帖子表 ====================

class SocialPostDB(Base):
    """社交帖子表"""
    __tablename__ = "social_posts"

    post_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 作者信息
    author_id: Mapped[str] = mapped_column(String(255), index=True)
    author_type: Mapped[str] = mapped_column(String(50), default="user")  # user, employer, worker, ai_agent
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 内容
    content: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(50), default="text")  # text, image, video, link, mixed
    media_urls: Mapped[Dict] = mapped_column(JSON, default=list)  # 图片/视频 URL 列表
    link_preview: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)  # 链接预览信息

    # 可见性
    visibility: Mapped[str] = mapped_column(String(50), default="public")  # public, friends, circle, private, employers, workers
    allowed_circles: Mapped[Dict] = mapped_column(JSON, default=list)  # 可见的圈子 ID 列表

    # 状态
    status: Mapped[str] = mapped_column(String(50), default="published")  # published, draft, deleted, under_review
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    # 统计
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    # 标签
    tags: Mapped[Dict] = mapped_column(JSON, default=list)
    circle_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("social_circles.circle_id"), nullable=True, index=True)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 索引
    __table_args__ = (
        Index('idx_posts_author_status', 'author_id', 'status'),
        Index('idx_posts_visibility_created', 'visibility', 'created_at'),
        Index('idx_posts_circle_created', 'circle_id', 'created_at'),
    )


# ==================== 评论表 ====================

class SocialCommentDB(Base):
    """社交评论表"""
    __tablename__ = "social_comments"

    comment_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("social_posts.post_id"), index=True)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("social_comments.comment_id"), nullable=True, index=True)

    # 作者信息
    author_id: Mapped[str] = mapped_column(String(255), index=True)
    author_type: Mapped[str] = mapped_column(String(50), default="user")
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 内容
    content: Mapped[str] = mapped_column(Text)

    # 统计
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)

    # 状态
    status: Mapped[str] = mapped_column(String(50), default="published")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index('idx_comments_post_created', 'post_id', 'created_at'),
    )


# ==================== 互动表 ====================

class PostInteractionDB(Base):
    """帖子互动表"""
    __tablename__ = "post_interactions"

    interaction_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("social_posts.post_id"), index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    user_type: Mapped[str] = mapped_column(String(50), default="user")

    interaction_type: Mapped[str] = mapped_column(String(50), default="like")  # like, love, laugh, wow, sad, angry

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)

    # 唯一约束：同一用户对同一帖子只能有一种互动
    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='uq_post_user_interaction'),
        Index('idx_interactions_post_type', 'post_id', 'interaction_type'),
    )


class BookmarkDB(Base):
    """收藏表"""
    __tablename__ = "bookmarks"

    bookmark_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    user_id: Mapped[str] = mapped_column(String(255), index=True)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("social_posts.post_id"), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)

    # 唯一约束：同一用户不能收藏同一帖子两次
    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='uq_user_post_bookmark'),
    )


class ShareDB(Base):
    """分享表"""
    __tablename__ = "shares"

    share_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    user_id: Mapped[str] = mapped_column(String(255), index=True)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("social_posts.post_id"), index=True)

    share_type: Mapped[str] = mapped_column(String(50), default="repost")  # repost, external
    share_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 转发时的附加内容
    external_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 外部链接

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


# ==================== 社交关系表 ====================

class SocialRelationshipDB(Base):
    """社交关系表"""
    __tablename__ = "social_relationships"

    relationship_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    user_id: Mapped[str] = mapped_column(String(255), index=True)  # 发起方
    target_id: Mapped[str] = mapped_column(String(255), index=True)  # 目标方

    relationship_type: Mapped[str] = mapped_column(String(50), default="friend")  # friend, following, blocked, collaborated
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, pending, rejected

    # 双向关系标记
    is_mutual: Mapped[bool] = mapped_column(Boolean, default=False)

    # 协作关系特有
    collaboration_count: Mapped[int] = mapped_column(Integer, default=0)
    total_transaction_amount: Mapped[float] = mapped_column(Float, default=0.0)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index('idx_relationships_user_target', 'user_id', 'target_id'),
        Index('idx_relationships_type_status', 'relationship_type', 'status'),
    )


class FriendRequestDB(Base):
    """好友请求表"""
    __tablename__ = "friend_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    sender_id: Mapped[str] = mapped_column(String(255), index=True)
    receiver_id: Mapped[str] = mapped_column(String(255), index=True)

    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, accepted, rejected

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 唯一约束：同一对用户只能有一个待处理请求
    __table_args__ = (
        Index('idx_friend_requests_status', 'receiver_id', 'status'),
    )


# ==================== 圈子表 ====================

class SocialCircleDB(Base):
    """社交圈子表"""
    __tablename__ = "social_circles"

    circle_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 基本信息
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 类型
    circle_type: Mapped[str] = mapped_column(String(50), default="interest")  # skill, industry, region, interest, task
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # 创建者
    creator_id: Mapped[str] = mapped_column(String(255), index=True)
    creator_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 访问控制
    join_type: Mapped[str] = mapped_column(String(50), default="open")  # open, approval, invite_only
    visibility: Mapped[str] = mapped_column(String(50), default="public")

    # 规则
    rules: Mapped[Dict] = mapped_column(JSON, default=list)

    # 统计
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    post_count: Mapped[int] = mapped_column(Integer, default=0)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class CircleMemberDB(Base):
    """圈子成员表"""
    __tablename__ = "circle_members"

    membership_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    circle_id: Mapped[str] = mapped_column(String(36), ForeignKey("social_circles.circle_id"), index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(String(50), default="member")  # member, moderator, admin
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, muted, banned

    # 加入方式
    join_method: Mapped[str] = mapped_column(String(50), default="apply")  # apply, invite

    # 时间
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 唯一约束：同一用户在同一圈子只能有一个成员记录
    __table_args__ = (
        UniqueConstraint('circle_id', 'user_id', name='uq_circle_user_member'),
        Index('idx_members_user_circle', 'user_id', 'circle_id'),
    )


class CircleJoinRequestDB(Base):
    """加入圈子申请表"""
    __tablename__ = "circle_join_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    circle_id: Mapped[str] = mapped_column(String(36), ForeignKey("social_circles.circle_id"), index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)

    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, approved, rejected

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 唯一约束：同一用户对同一圈子只能有一个待处理请求
    __table_args__ = (
        Index('idx_circle_requests_status', 'circle_id', 'user_id', 'status'),
    )


# ==================== 隐私设置表 ====================

class PrivacySettingsDB(Base):
    """隐私设置表"""
    __tablename__ = "privacy_settings"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # 动态可见性
    who_can_see_posts: Mapped[str] = mapped_column(String(50), default="friends")
    who_can_comment: Mapped[str] = mapped_column(String(50), default="friends")
    who_can_message: Mapped[str] = mapped_column(String(50), default="friends")

    # 个人信息
    show_real_name: Mapped[bool] = mapped_column(Boolean, default=False)
    show_location: Mapped[bool] = mapped_column(Boolean, default=False)
    show_contact_info: Mapped[bool] = mapped_column(Boolean, default=False)
    show_activity_status: Mapped[bool] = mapped_column(Boolean, default=True)

    # 社交关系
    allow_friend_requests: Mapped[bool] = mapped_column(Boolean, default=True)
    hide_friend_list: Mapped[bool] = mapped_column(Boolean, default=True)
    hide_circle_memberships: Mapped[bool] = mapped_column(Boolean, default=False)

    # 搜索与发现
    appear_in_search: Mapped[bool] = mapped_column(Boolean, default=True)
    show_in_recommendations: Mapped[bool] = mapped_column(Boolean, default=True)

    # 通知
    notify_on_like: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_comment: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_follow: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_circle_invite: Mapped[bool] = mapped_column(Boolean, default=True)

    # 黑名单
    blocked_users: Mapped[Dict] = mapped_column(JSON, default=list)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


# ==================== 通知表 ====================

class SocialNotificationDB(Base):
    """社交通知表"""
    __tablename__ = "social_notifications"

    notification_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    recipient_id: Mapped[str] = mapped_column(String(255), index=True)

    notification_type: Mapped[str] = mapped_column(String(50))  # like, comment, reply, follow, friend_request, circle_invite, etc.
    sender_id: Mapped[str] = mapped_column(String(255), index=True)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关联内容
    post_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    comment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    circle_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 内容预览
    preview_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 状态
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)


# ==================== 社交图谱表 ====================

class SocialGraphConnectionDB(Base):
    """社交图谱连接表"""
    __tablename__ = "social_graph_connections"

    connection_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    user_id: Mapped[str] = mapped_column(String(255), index=True)
    connected_user_id: Mapped[str] = mapped_column(String(255), index=True)

    connection_type: Mapped[str] = mapped_column(String(50))  # friend, follower, following, collaborated
    connection_strength: Mapped[float] = mapped_column(Float, default=0.0)  # 连接强度 (0-1)

    # 共同点
    common_circles: Mapped[Dict] = mapped_column(JSON, default=list)
    common_interests: Mapped[Dict] = mapped_column(JSON, default=list)
    collaboration_count: Mapped[int] = mapped_column(Integer, default=0)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index('idx_graph_user_connected', 'user_id', 'connected_user_id'),
        Index('idx_graph_type_strength', 'connection_type', 'connection_strength'),
    )
