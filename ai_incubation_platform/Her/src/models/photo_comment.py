"""
照片评论数据库模型

参考 Hinge 的照片评论功能
"""
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from db.database import Base


class PhotoCommentDB(Base):
    """照片评论"""
    __tablename__ = "photo_comments"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)  # 评论者
    photo_id = Column(String(36), nullable=False, index=True)  # 照片 ID
    photo_owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)  # 照片主人

    # 评论内容
    comment_content = Column(Text, nullable=False)
    comment_type = Column(String(20), nullable=False)  # observation/question/compliment/shared_interest/story/ai_suggested

    # 评论位置（照片上的坐标，可选）
    position_x = Column(Float, nullable=True)  # 0-1 范围
    position_y = Column(Float, nullable=True)  # 0-1 范围

    # 状态
    is_ai_generated = Column(Boolean, default=False)  # 是否 AI 生成
    is_read = Column(Boolean, default=False)  # 是否已读

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PhotoCommentDB(id={self.id}, type={self.comment_type})>"


class PhotoCommentReplyDB(Base):
    """照片评论回复"""
    __tablename__ = "photo_comment_replies"

    id = Column(String(36), primary_key=True, index=True)
    comment_id = Column(String(36), ForeignKey("photo_comments.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 回复内容
    reply_content = Column(Text, nullable=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PhotoCommentReplyDB(id={self.id}, comment_id={self.comment_id})>"