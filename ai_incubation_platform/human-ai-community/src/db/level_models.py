"""
用户等级系统 - 数据库模型
"""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, func, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, declarative_base
from .base import BaseModel
from enum import Enum


class ExperienceSourceType(str, Enum):
    """经验值来源类型"""
    POST = "post"              # 发帖
    COMMENT = "comment"        # 评论
    LIKE_RECEIVED = "like_received"    # 被点赞
    BOOKMARK_RECEIVED = "bookmark_received"  # 被收藏
    DAILY_CHECKIN = "daily_checkin"  # 每日签到
    QUALITY_CONTENT = "quality_content"  # 优质内容加精
    FIRST_POST = "first_post"  # 首次发帖
    FIRST_COMMENT = "first_comment"  # 首次评论


class DBExperienceLog(BaseModel):
    """经验值流水记录表"""
    __tablename__ = "experience_logs"

    id = Column(String(36), primary_key=True, index=True, comment="记录 ID")
    user_id = Column(String(36), ForeignKey("community_members.id"), nullable=False, index=True, comment="用户 ID")
    source_type = Column(SQLAlchemyEnum(ExperienceSourceType), nullable=False, comment="经验来源类型")
    points = Column(Integer, nullable=False, comment="获得经验值")
    description = Column(String(200), comment="描述")
    related_content_id = Column(String(36), comment="关联内容 ID（帖子/评论 ID）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 关系 - 使用字符串引用，延迟绑定
    user = relationship("DBCommunityMember", back_populates="experience_logs", foreign_keys=[user_id])


class DBLevelPrivilege(BaseModel):
    """等级特权配置表"""
    __tablename__ = "level_privileges"

    id = Column(String(36), primary_key=True, index=True, comment="记录 ID")
    level = Column(Integer, nullable=False, index=True, comment="等级")
    privilege_type = Column(String(50), nullable=False, comment="特权类型")
    privilege_value = Column(String(200), comment="特权值")
    description = Column(String(200), comment="特权描述")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
