"""
频道/版块系统数据模型
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, JSON, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel


class ChannelCategoryType(str, Enum):
    """频道分类类型"""
    GENERAL = "general"  # 综合讨论
    TECHNOLOGY = "technology"  # 技术讨论
    LIFE = "life"  # 生活分享
    ENTERTAINMENT = "entertainment"  # 娱乐
    STUDY = "study"  # 学习
    WORK = "work"  # 工作
    OTHER = "other"  # 其他


class ChannelAccessLevel(str, Enum):
    """频道访问权限级别"""
    PUBLIC = "public"  # 所有人可访问
    MEMBER_ONLY = "member_only"  # 仅社区成员可访问
    PRIVATE = "private"  # 仅邀请可访问


class DBChannelCategory(BaseModel):
    """频道分类表（一级分类）"""
    __tablename__ = "channel_categories"

    id = Column(String(36), primary_key=True, index=True, comment="分类 ID")
    name = Column(String(100), nullable=False, unique=True, comment="分类名称")
    description = Column(Text, comment="分类描述")
    category_type = Column(String(50), default=ChannelCategoryType.OTHER.value, comment="分类类型")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    icon = Column(String(100), comment="图标")
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 关系
    channels = relationship("DBChannel", back_populates="category", cascade="all, delete-orphan")


class DBChannel(BaseModel):
    """频道表（二级分类）"""
    __tablename__ = "channels"

    id = Column(String(36), primary_key=True, index=True, comment="频道 ID")
    category_id = Column(String(36), ForeignKey("channel_categories.id"), nullable=False, comment="所属分类 ID")
    name = Column(String(100), nullable=False, comment="频道名称")
    slug = Column(String(100), unique=True, index=True, comment="频道标识符（URL 友好）")
    description = Column(Text, comment="频道描述")
    access_level = Column(String(50), default=ChannelAccessLevel.PUBLIC.value, comment="访问权限级别")
    icon = Column(String(100), comment="频道图标")
    banner = Column(String(500), comment="频道横幅")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    rules = Column(JSON, default=list, comment="频道规则列表")
    settings = Column(JSON, default=dict, comment="频道配置")

    # 统计字段
    member_count = Column(Integer, default=0, comment="成员数")
    post_count = Column(Integer, default=0, comment="帖子数")
    last_activity_at = Column(DateTime(timezone=True), comment="最后活跃时间")

    # 管理
    owner_id = Column(String(36), comment="频道创建者/所有者 ID")
    is_official = Column(Boolean, default=False, comment="是否官方频道")
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 关系
    category = relationship("DBChannelCategory", back_populates="channels")
    members = relationship("DBChannelMember", back_populates="channel", cascade="all, delete-orphan")
    # 注意：帖子和频道是多对多关系，通过 DBChannelPost 关联表管理，不直接建立 relationship


class DBChannelMember(BaseModel):
    """频道成员表"""
    __tablename__ = "channel_members"

    id = Column(String(36), primary_key=True, index=True, comment="记录 ID")
    channel_id = Column(String(36), ForeignKey("channels.id"), nullable=False, comment="频道 ID")
    member_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, comment="成员 ID")
    role = Column(String(50), default="member", comment="成员角色：owner/admin/moderator/member")
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), comment="加入时间")
    is_active = Column(Boolean, default=True, comment="是否活跃")
    settings = Column(JSON, default=dict, comment="个人频道设置")

    # 关系
    channel = relationship("DBChannel", back_populates="members")
    member = relationship("DBCommunityMember")

    __table_args__ = (
        UniqueConstraint('channel_id', 'member_id', name='uq_channel_member'),
    )


class DBChannelPermission(BaseModel):
    """频道权限表"""
    __tablename__ = "channel_permissions"

    id = Column(String(36), primary_key=True, index=True, comment="权限 ID")
    channel_id = Column(String(36), ForeignKey("channels.id"), nullable=False, comment="频道 ID")
    role = Column(String(50), nullable=False, comment="角色类型")
    permissions = Column(JSON, nullable=False, default=list, comment="权限列表")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 关系
    channel = relationship("DBChannel")

    __table_args__ = (
        UniqueConstraint('channel_id', 'role', name='uq_channel_role'),
    )


class DBChannelPost(BaseModel):
    """频道帖子表（扩展原有 Post 模型）"""
    __tablename__ = "channel_posts"

    id = Column(String(36), primary_key=True, index=True, comment="频道帖子 ID")
    channel_id = Column(String(36), ForeignKey("channels.id"), nullable=False, comment="频道 ID")
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False, comment="关联的帖子 ID")
    is_pinned = Column(Boolean, default=False, comment="是否置顶")
    is_featured = Column(Boolean, default=False, comment="是否精华")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 关系
    channel = relationship("DBChannel")

    __table_args__ = (
        UniqueConstraint('channel_id', 'post_id', name='uq_channel_post'),
    )


# 更新 DBPost 添加 channel 关系
def patch_db_post():
    """补丁：为 DBPost 添加 channel 字段"""
    from db.models import DBPost
    from sqlalchemy.orm import relationship

    # 添加 channel 关系（如果不存在）
    if not hasattr(DBPost, 'channel'):
        DBPost.channel_id = Column(String(36), ForeignKey("channels.id"), nullable=True, comment="频道 ID")
        DBPost.channel = relationship("DBChannel", back_populates="posts")
