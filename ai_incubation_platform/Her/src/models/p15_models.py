"""
P15 虚实结合数据库模型

核心理念：全自动关系管家
把繁琐留给 AI，把心动留给自己。

包含以下模块：
1. 自主约会策划 - 地理中点计算、偏好匹配、自主预订
2. 情感纪念册 - 甜蜜语录汇总、共同足迹整理、多媒体生成
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum
from sqlalchemy.orm import relationship
import enum

from db.database import Base


# ==================== 自主约会策划模块 ====================

class DatePlanStatus(str, enum.Enum):
    """约会计划状态"""
    DRAFT = "draft"  # 草稿
    PLANNING = "planning"  # 规划中
    CONFIRMED = "confirmed"  # 已确认
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class VenueCategory(str, enum.Enum):
    """场所类别"""
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    PARK = "park"
    CINEMA = "cinema"
    MUSEUM = "museum"
    CONCERT_HALL = "concert_hall"
    SPORTS_VENUE = "sports_venue"


class AutonomousDatePlanDB(Base):
    """自主约会计划"""
    __tablename__ = "autonomous_date_plans"

    id = Column(String, primary_key=True)

    # 用户信息
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 计划信息
    plan_name = Column(String, nullable=False)
    plan_description = Column(Text)

    # 地理中点
    midpoint_latitude = Column(Float)
    midpoint_longitude = Column(Float)
    midpoint_address = Column(String)

    # 场所信息
    venue_id = Column(String)
    venue_name = Column(String)
    venue_category = Column(String)
    venue_address = Column(String)

    # 偏好匹配
    preference_match_score = Column(Float)  # 偏好匹配度 0-1
    budget_match_score = Column(Float)  # 预算匹配度 0-1

    # 约会时间
    planned_date_time = Column(DateTime)
    duration_hours = Column(Float)

    # 预订信息
    reservation_required = Column(Boolean, default=False)
    reservation_status = Column(String)  # none, pending, confirmed
    reservation_reference = Column(String)

    # 计划状态
    status = Column(String, default=DatePlanStatus.DRAFT.value)

    # AI 推荐理由
    ai_recommendation_reason = Column(Text)

    # 活动安排
    activity_schedule = Column(JSON)
    # [{time, activity, description}]

    # 交通建议
    transportation_suggestions = Column(JSON)
    # {user_a: {...}, user_b: {...}}

    # 预算估算
    estimated_budget = Column(Float)
    actual_budget = Column(Float)

    # 用户反馈
    user_a_confirmation = Column(Boolean)
    user_b_confirmation = Column(Boolean)
    post_date_rating = Column(Integer)  # 1-5

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)


class DateReservationDB(Base):
    """约会预订记录"""
    __tablename__ = "date_reservations"

    id = Column(String, primary_key=True)

    # 关联的计划 ID
    plan_id = Column(String, ForeignKey("autonomous_date_plans.id"))

    # 用户 ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 场所信息
    venue_name = Column(String, nullable=False)
    venue_contact = Column(JSON)  # {phone, email, website}

    # 预订详情
    reservation_date = Column(DateTime, nullable=False)
    party_size = Column(Integer, default=2)
    special_requests = Column(Text)

    # 预订状态
    status = Column(String, default="pending")  # pending, confirmed, cancelled

    # 第三方预订信息
    third_party_platform = Column(String)  # open_table, diyin, etc.
    third_party_reference = Column(String)

    # 确认信息
    confirmation_code = Column(String)
    confirmation_received_at = Column(DateTime)

    # 提醒设置
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 情感纪念册模块 ====================

class AlbumType(str, enum.Enum):
    """纪念册类型"""
    MOMENT = "moment"  # 瞬间
    MONTHLY = "monthly"  # 月度
    MILESTONE = "milestone"  # 里程碑
    TRIP = "trip"  # 旅行
    CUSTOM = "custom"  # 自定义


class RelationshipAlbumDB(Base):
    """情感纪念册"""
    __tablename__ = "relationship_albums"

    id = Column(String, primary_key=True)

    # 用户信息
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 纪念册信息
    title = Column(String, nullable=False)
    description = Column(Text)
    album_type = Column(String, default=AlbumType.MOMENT.value)

    # 封面
    cover_image_url = Column(String)

    # 时间范围
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # 内容项 ID 列表
    content_item_ids = Column(JSON, default=list)

    # 统计信息
    total_moments = Column(Integer, default=0)
    total_photos = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)

    # AI 生成的总结
    ai_summary = Column(Text)

    # 隐私设置
    is_private = Column(Boolean, default=True)

    # 情感温度（纪念册整体的情感评分）
    emotional_temperature = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SweetMomentDB(Base):
    """甜蜜瞬间记录"""
    __tablename__ = "sweet_moments"

    id = Column(String, primary_key=True)

    # 关联用户
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 关联的纪念册 ID
    album_id = Column(String, ForeignKey("relationship_albums.id"))

    # 来源类型
    source_type = Column(String, nullable=False)  # chat_message, date_activity, photo, voice

    # 来源 ID
    source_id = Column(String)

    # 时刻内容
    content = Column(Text, nullable=False)
    # 对话内容、照片描述等

    # 情感分析
    sentiment_score = Column(Float)  # -1 到 1
    emotion_tags = Column(JSON)  # ["love", "happiness", "gratitude"]

    # 时间信息
    moment_date = Column(DateTime, nullable=False)

    # 地理位置（可选）
    location = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # 媒体附件
    media_urls = Column(JSON)  # 照片、语音等

    # AI 提取的关键词
    ai_keywords = Column(JSON)

    # 用户标记
    is_favorite = Column(Boolean, default=False)
    user_note = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


class CoupleFootprintDB(Base):
    """共同足迹记录"""
    __tablename__ = "couple_footprints"

    id = Column(String, primary_key=True)

    # 关联用户
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 足迹类型
    footprint_type = Column(String, nullable=False)
    # first_meet, first_date, first_kiss, trip, anniversary, etc.

    # 足迹名称
    title = Column(String, nullable=False)

    # 描述
    description = Column(Text)

    # 日期
    footprint_date = Column(DateTime, nullable=False)

    # 地点
    location_name = Column(String)
    location_address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

    # 相关照片
    photo_urls = Column(JSON)

    # 相关瞬间 ID 列表
    moment_ids = Column(JSON, default=list)

    # 重要性评分
    significance_score = Column(Float, default=0.5)

    # 用户评分
    user_rating = Column(Integer)  # 1-5

    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 多媒体生成模块 ====================

class MediaGenerationType(str, enum.Enum):
    """媒体生成类型"""
    COLLAGE = "collage"  # 拼贴图
    VIDEO = "video"  # 视频
    SLIDESHOW = "slideshow"  # 幻灯片
    CARD = "card"  # 卡片
    POSTER = "poster"  # 海报


class GeneratedMediaDB(Base):
    """生成的多媒体内容"""
    __tablename__ = "generated_media"

    id = Column(String, primary_key=True)

    # 关联用户
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 关联的纪念册 ID
    album_id = Column(String, ForeignKey("relationship_albums.id"))

    # 媒体类型
    media_type = Column(String, nullable=False)

    # 生成类型
    generation_type = Column(String, default=MediaGenerationType.COLLAGE.value)

    # 媒体 URL
    media_url = Column(String, nullable=False)

    # 缩略图 URL
    thumbnail_url = Column(String)

    # 使用的素材 ID 列表
    source_material_ids = Column(JSON)

    # 生成参数
    generation_params = Column(JSON)
    # {template, music, transition, duration}

    # AI 生成的描述
    ai_description = Column(Text)

    # 文件大小
    file_size_bytes = Column(Integer)

    # 时长（秒，针对视频/音频）
    duration_seconds = Column(Float)

    # 用户反馈
    user_rating = Column(Integer)  # 1-5
    is_shared = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
