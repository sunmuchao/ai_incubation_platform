"""
P15 阶段：内容推荐系统增强 - 数据模型

v1.15 新增模型：
- 阅读历史追踪
- 内容标签系统
- 推荐多样性配置
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, JSON, DateTime, func, Index
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.base import BaseModel


class DBReadingHistory(BaseModel):
    """用户阅读历史表"""
    __tablename__ = "reading_history"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="阅读记录 ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")
    content_id = Column(String(36), nullable=False, index=True, comment="内容 ID（帖子或评论）")
    content_type = Column(String(50), nullable=False, default="post", comment="内容类型：post/comment")

    # 阅读行为
    read_duration_seconds = Column(Integer, default=0, comment="阅读时长（秒）")
    read_percentage = Column(Float, default=0.0, comment="阅读进度百分比 (0-100)")
    is_complete = Column(Boolean, default=False, comment="是否完整阅读")

    # 来源追踪
    source = Column(String(50), default="feed", comment="来源：feed/search/recommendation/direct")
    recommendation_id = Column(String(36), comment="推荐记录 ID（如果是通过推荐进入）")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="阅读时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 索引
    __table_args__ = (
        Index('idx_reading_history_user_content', 'user_id', 'content_id', 'content_type'),
        Index('idx_reading_history_user_created', 'user_id', 'created_at'),
    )


class DBContentTag(BaseModel):
    """内容标签表"""
    __tablename__ = "content_tags"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="标签 ID")
    name = Column(String(50), nullable=False, unique=True, index=True, comment="标签名称")
    description = Column(Text, comment="标签描述")
    category = Column(String(50), comment="标签分类")

    # 统计
    usage_count = Column(Integer, default=0, comment="使用次数")
    post_count = Column(Integer, default=0, comment="关联帖子数")

    # 标签权重（用于推荐）
    weight = Column(Float, default=1.0, comment="标签权重")

    # 父子标签关系（用于标签层级）
    parent_id = Column(String(36), ForeignKey("content_tags.id"), comment="父标签 ID")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 关系
    parent = relationship("DBContentTag", remote_side=[id], back_populates="children")
    children = relationship("DBContentTag", back_populates="parent")


class DBPostTag(BaseModel):
    """帖子 - 标签关联表"""
    __tablename__ = "post_tags"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="关联 ID")
    post_id = Column(String(36), ForeignKey("posts.id"), nullable=False, index=True, comment="帖子 ID")
    tag_id = Column(String(36), ForeignKey("content_tags.id"), nullable=False, index=True, comment="标签 ID")

    # 标签来源
    source = Column(String(50), default="manual", comment="来源：manual/auto/ai")
    confidence = Column(Float, default=1.0, comment="置信度（自动标签）")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 索引
    __table_args__ = (
        Index('idx_post_tags_post_tag', 'post_id', 'tag_id', unique=True),
    )

    # 关系
    post = relationship("DBPost", back_populates="post_tags")
    tag = relationship("DBContentTag", back_populates="post_tags")


class DBUserInterest(BaseModel):
    """用户兴趣画像表"""
    __tablename__ = "user_interests"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="兴趣记录 ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")

    # 兴趣类型
    interest_type = Column(String(50), nullable=False, comment="兴趣类型：tag/channel/category/author")
    interest_id = Column(String(36), nullable=False, comment="兴趣对象 ID（标签 ID/频道 ID 等）")
    interest_value = Column(String(100), comment="兴趣值（用于存储名称等）")

    # 兴趣强度
    score = Column(Float, default=0.0, comment="兴趣分数")

    # 兴趣来源
    source = Column(String(50), default="behavior", comment="来源：behavior/explicit/ai_inferred")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    last_interaction_at = Column(DateTime(timezone=True), comment="最后互动时间")

    # 索引
    __table_args__ = (
        Index('idx_user_interests_user_type', 'user_id', 'interest_type'),
        Index('idx_user_interests_user_score', 'user_id', 'score'),
    )


class DBRecommendationLog(BaseModel):
    """推荐日志表（用于追溯和优化）"""
    __tablename__ = "recommendation_logs"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="日志 ID")
    recommendation_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4()), comment="推荐批次 ID")

    # 用户和场景
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")
    scene = Column(String(50), default="feed", comment="推荐场景：feed/home/search/detail")

    # 推荐内容
    recommended_content = Column(JSON, nullable=False, default=list, comment="推荐内容列表 [{id, type, score, reason}]")

    # 算法信息
    algorithm_version = Column(String(50), default="v1.15", comment="算法版本")
    algorithm_params = Column(JSON, default=dict, comment="算法参数")

    # 多样性信息
    diversity_metrics = Column(JSON, default=dict, comment="多样性指标 {channel_diversity, author_diversity, ai_human_ratio}")

    # 用户反馈（后续更新）
    click_positions = Column(JSON, default=list, comment="点击位置列表")
    dwell_time = Column(JSON, default=dict, comment="停留时间 {content_id: seconds}")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="推荐时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 索引
    __table_args__ = (
        Index('idx_recommendation_logs_user_created', 'user_id', 'created_at'),
    )


class DBRecommendationConfig(BaseModel):
    """推荐系统配置表"""
    __tablename__ = "recommendation_configs"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()), comment="配置 ID")
    config_key = Column(String(50), nullable=False, unique=True, index=True, comment="配置键")
    config_value = Column(JSON, nullable=False, comment="配置值")
    description = Column(Text, comment="配置描述")

    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


# 添加 post_tags 关系到 DBPost
from sqlalchemy.orm import relationship

# 延迟导入以避免循环引用
def setup_post_tags_relationship():
    """设置帖子 - 标签关系"""
    from db.models import DBPost
    if not hasattr(DBPost, 'post_tags'):
        DBPost.post_tags = relationship("DBPostTag", back_populates="post")
