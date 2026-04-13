"""
SQLAlchemy 数据模型 - 视频约会领域

包含：视频通话、视频约会记录、游戏会话等
"""
from db.models.base import *

class VideoCallDB(Base):
    """视频通话记录"""
    __tablename__ = "video_calls"

    id = Column(String(36), primary_key=True, index=True)

    caller_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String(20), default="pending")

    room_id = Column(String(100), nullable=False, unique=True, index=True)
    sdp_offer = Column(Text, nullable=True)
    sdp_answer = Column(Text, nullable=True)
    ice_candidates = Column(Text, default="")

    duration_seconds = Column(Integer, default=0)
    quality_score = Column(Float, nullable=True)
    connection_type = Column(String(20), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)


class VideoDateDB(Base):
    """视频约会记录"""
    __tablename__ = "video_dates"

    id = Column(String(36), primary_key=True, index=True)

    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String(20), default="scheduled")

    scheduled_time = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, default=30)
    theme = Column(String(100), nullable=True)

    room_id = Column(String(100), nullable=True, unique=True)
    background = Column(String(50), default="default")
    filter_applied = Column(String(50), nullable=True)

    actual_start_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)

    rating_user1 = Column(Integer, nullable=True)
    rating_user2 = Column(Integer, nullable=True)
    review_user1 = Column(Text, nullable=True)
    review_user2 = Column(Text, nullable=True)

    games_played = Column(Text, default="")
    icebreakers_used = Column(Text, default="")

    has_report = Column(Boolean, default=False)
    report_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VideoDateReportDB(Base):
    """视频约会举报记录"""
    __tablename__ = "video_date_reports"

    id = Column(String(36), primary_key=True, index=True)
    date_id = Column(String(36), ForeignKey("video_dates.id"), nullable=False, index=True)

    reporter_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    reported_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    reason = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(String(20), default="pending")
    resolution = Column(Text, nullable=True)

    evidence_urls = Column(Text, default="")

    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IcebreakerQuestionDB(Base):
    """破冰问题库"""
    __tablename__ = "icebreaker_questions"

    id = Column(String(36), primary_key=True, index=True)

    question = Column(Text, nullable=False)

    category = Column(String(20), default="casual")
    depth_level = Column(Integer, default=1)

    suitable_scenarios = Column(Text, default="")

    usage_count = Column(Integer, default=0)
    positive_feedback_rate = Column(Float, default=0.5)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class GameSessionDB(Base):
    """游戏会话记录"""
    __tablename__ = "game_sessions"

    id = Column(String(36), primary_key=True, index=True)
    date_id = Column(String(36), ForeignKey("video_dates.id"), nullable=True, index=True)

    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    game_type = Column(String(50), nullable=False)

    status = Column(String(20), default="pending")

    game_data = Column(JSON, nullable=True)

    winner_id = Column(String(36), nullable=True)
    score_user1 = Column(Integer, nullable=True)
    score_user2 = Column(Integer, nullable=True)
    result_summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class VirtualBackgroundDB(Base):
    """虚拟背景配置"""
    __tablename__ = "virtual_backgrounds"

    id = Column(String(36), primary_key=True, index=True)

    name = Column(String(100), nullable=False)
    category = Column(String(50), default="scene")

    thumbnail_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)

    is_free = Column(Boolean, default=True)
    required_tier = Column(String(20), default="free")

    usage_count = Column(Integer, default=0)
    popularity_score = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

__all__ = [
    "VideoCallDB", "VideoDateDB", "VideoDateReportDB",
    "IcebreakerQuestionDB", "GameSessionDB", "VirtualBackgroundDB"
]