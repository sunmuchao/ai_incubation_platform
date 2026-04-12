"""
视频片段数据库模型

参考 Tinder 的视频片段功能
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from db.database import Base


class VideoClipDB(Base):
    """视频片段"""
    __tablename__ = "video_clips"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 视频信息
    video_url = Column(Text, nullable=False)  # 视频 URL
    video_thumbnail = Column(Text, nullable=True)  # 视频缩略图 URL
    video_duration = Column(Float, nullable=False)  # 视频时长（秒）
    video_description = Column(Text, nullable=True)  # 视频描述
    video_format = Column(String(10), default="mp4")  # 视频格式

    # AI 分析结果
    video_analysis = Column(JSON, nullable=True)  # 视频内容分析

    # 状态
    is_primary = Column(Boolean, default=False)  # 是否为主要视频
    is_deleted = Column(Boolean, default=False)  # 是否已删除

    # 统计
    view_count = Column(Integer, default=0)  # 观看次数

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<VideoClipDB(id={self.id}, user_id={self.user_id}, duration={self.video_duration})>"