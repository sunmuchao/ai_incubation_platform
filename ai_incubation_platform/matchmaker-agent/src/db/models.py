"""
SQLAlchemy 数据模型定义

P3 新增:
- 对话历史持久化
- 浏览行为追踪
- 动态用户画像
- 关系进展记录
- 活动地点收藏
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Table, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base


# ============= 基础用户与匹配模型 =============

class UserDB(Base):
    """用户数据库模型"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False, index=True)
    gender = Column(String(20), nullable=False, index=True)
    location = Column(String(200), nullable=False, index=True)
    interests = Column(Text, default="")  # JSON 字符串存储
    values = Column(Text, default="")  # JSON 字符串存储
    bio = Column(Text, default="")
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 偏好设置
    preferred_age_min = Column(Integer, default=18)
    preferred_age_max = Column(Integer, default=60)
    preferred_location = Column(String(200), nullable=True)
    preferred_gender = Column(String(20), nullable=True)


class MatchHistoryDB(Base):
    """匹配历史记录 - P3 增强版"""
    __tablename__ = "match_history"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), nullable=False, index=True)
    user_id_2 = Column(String(36), nullable=False, index=True)
    compatibility_score = Column(Float, nullable=False)
    status = Column(String(20), default="pending")  # pending, accepted, rejected, expired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # P3 新增：匹配原因快照
    match_reasoning = Column(Text, default="")
    common_interests = Column(Text, default="")  # JSON 字符串
    score_breakdown = Column(Text, default="")  # JSON 字符串

    # P3 新增：关系进展追踪
    interaction_count = Column(Integer, default=0)  # 互动次数
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)
    relationship_stage = Column(String(20), default="matched")  # matched, chatting, dated, in_relationship


# ============= P3 新增：对话与行为追踪模型 =============

class ConversationDB(Base):
    """对话历史记录"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), nullable=False, index=True)
    user_id_2 = Column(String(36), nullable=False, index=True)

    # 对话内容 (脱敏后)
    message_content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, image, emoji, system

    # 元数据
    sender_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # P3 新增：对话分析标签
    topic_tags = Column(Text, default="")  # JSON 字符串，如 ["旅行", "美食", "电影"]
    sentiment_score = Column(Float, nullable=True)  # 情感得分 -1.0 到 1.0
    is_sensitive = Column(Boolean, default=False)  # 是否敏感内容
    safety_flags = Column(Text, default="")  # JSON 字符串，安全标记


class BehaviorEventDB(Base):
    """用户行为事件记录"""
    __tablename__ = "behavior_events"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    # 行为类型
    event_type = Column(String(50), nullable=False, index=True)  # profile_view, search, like, pass, message_open
    target_id = Column(String(36), nullable=True, index=True)  # 被查看/操作的用户 ID

    # 行为详情
    event_data = Column(JSON, nullable=True)  # 结构化事件数据

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserProfileUpdateDB(Base):
    """动态用户画像更新记录"""
    __tablename__ = "user_profile_updates"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    # 更新类型
    update_type = Column(String(50), nullable=False)  # interest_add, interest_remove, behavior_pattern, conversation_insight

    # 更新内容
    old_value = Column(Text, nullable=True)  # JSON 字符串
    new_value = Column(Text, nullable=False)  # JSON 字符串

    # 更新来源
    source = Column(String(50), nullable=False)  # conversation_analysis, behavior_analysis, manual

    # 置信度 (0-1)
    confidence = Column(Float, default=1.0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied = Column(Boolean, default=False)  # 是否已应用到用户画像


class RelationshipProgressDB(Base):
    """关系进展记录"""
    __tablename__ = "relationship_progress"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), nullable=False, index=True)
    user_id_2 = Column(String(36), nullable=False, index=True)

    # 进展类型
    progress_type = Column(String(50), nullable=False)  # first_message, first_date, relationship_milestone
    description = Column(Text, nullable=False)

    # 进展评分 (1-10)
    progress_score = Column(Integer, default=5)

    # 相关数据
    related_data = Column(JSON, nullable=True)  # 如约会地点、里程碑类型等

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SavedLocationDB(Base):
    """收藏的地点/活动推荐"""
    __tablename__ = "saved_locations"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    # 地点信息
    location_name = Column(String(200), nullable=False)
    location_type = Column(String(50), nullable=False)  # cafe, restaurant, park, activity, event
    address = Column(String(500), nullable=True)

    # 地理位置 (用于地图 API)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # 推荐理由
    reason = Column(Text, nullable=True)
    tags = Column(Text, default="")  # JSON 字符串

    # 评分
    rating = Column(Float, nullable=True)  # 1-5
    price_level = Column(Integer, nullable=True)  # 1-4

    # 来源
    source = Column(String(50), default="manual")  # manual, map_api, recommendation

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


# ============= P4 新增：照片管理模型 =============

class PhotoDB(Base):
    """用户照片管理"""
    __tablename__ = "photos"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 照片信息
    photo_url = Column(String(500), nullable=False)
    photo_type = Column(String(20), default="profile")  # profile, avatar, verification, lifestyle
    display_order = Column(Integer, default=0)  # 显示顺序，0 为封面

    # 审核状态
    moderation_status = Column(String(20), default="pending")  # pending, approved, rejected
    moderation_reason = Column(Text, nullable=True)  # 审核不通过原因
    moderated_at = Column(DateTime(timezone=True), nullable=True)
    moderated_by = Column(String(36), nullable=True)  # 审核员 ID 或 "ai"

    # AI 分析标签
    ai_tags = Column(Text, default="")  # JSON 字符串，如 ["微笑", "户外", "运动"]
    ai_quality_score = Column(Float, nullable=True)  # AI 质量评分 0-1

    # 验证标记
    is_verified = Column(Boolean, default=False)  # 是否通过真人验证
    verification_pose = Column(String(50), nullable=True)  # 验证姿势要求

    # 互动统计
    like_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)


# ============= P4 新增：实名认证模型 =============

class IdentityVerificationDB(Base):
    """用户实名认证信息"""
    __tablename__ = "identity_verifications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 身份信息
    real_name = Column(String(100), nullable=False)
    id_number = Column(String(18), nullable=False)  # 身份证号 (加密存储)
    id_number_hash = Column(String(64), nullable=False, index=True)  # 身份证号哈希 (用于去重)

    # 认证状态
    verification_status = Column(String(20), default="pending")  # pending, verified, rejected, expired
    rejection_reason = Column(Text, nullable=True)

    # OCR 识别结果
    ocr_data = Column(Text, default="")  # JSON 字符串，OCR 识别结果
    id_front_url = Column(String(500), nullable=True)  # 身份证正面照片
    id_back_url = Column(String(500), nullable=True)  # 身份证反面照片

    # 人脸核身
    face_verify_url = Column(String(500), nullable=True)  # 人脸核身照片
    face_similarity_score = Column(Float, nullable=True)  # 人脸相似度

    # 认证类型
    verification_type = Column(String(20), default="basic")  # basic(身份证), advanced(身份证 + 人脸)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 认证标识
    verification_badge = Column(String(20), nullable=True)  # verified, premium, vip


# ============= P6 新增：信任标识体系模型 =============

class VerificationBadgeDB(Base):
    """用户信任徽章/认证标识"""
    __tablename__ = "verification_badges"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 徽章类型
    badge_type = Column(String(50), nullable=False, index=True)
    # 徽章类型列表:
    # - identity_verified: 实名认证 (基础)
    # - face_verified: 人脸核身认证
    # - photo_verified: 照片验证 (姿势验证)
    # - education_verified: 学历认证
    # - career_verified: 职业认证
    # - income_verified: 收入认证
    # - phone_verified: 手机认证
    # - email_verified: 邮箱认证
    # - social_verified: 社交账号认证
    # - premium_member: 付费会员
    # - vip_member: VIP 会员
    # - active_user: 活跃用户
    # - early_adopter: 早期用户

    # 徽章状态
    status = Column(String(20), default="active")  # active, suspended, expired

    # 认证详情
    verification_data = Column(Text, default="")  # JSON 字符串，认证详情

    # 有效期
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 显示顺序 (0 为最重要，优先展示)
    display_order = Column(Integer, default=10)

    # 图标和描述
    icon_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EducationVerificationDB(Base):
    """学历认证信息"""
    __tablename__ = "education_verifications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 学校信息
    school_name = Column(String(200), nullable=False)
    school_type = Column(String(50), nullable=True)  # 985, 211, 双一流，海外名校等
    degree = Column(String(50), nullable=True)  # 学士，硕士，博士
    major = Column(String(100), nullable=True)  # 专业
    graduation_year = Column(Integer, nullable=True)  # 毕业年份

    # 认证状态
    verification_status = Column(String(20), default="pending")  # pending, verified, rejected
    verification_method = Column(String(50), default="manual")  # manual, api, document

    # 证明材料
    certificate_url = Column(String(500), nullable=True)  # 学历证书照片
    student_id_url = Column(String(500), nullable=True)  # 学生证照片

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)


class CareerVerificationDB(Base):
    """职业认证信息"""
    __tablename__ = "career_verifications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 职业信息
    company_name = Column(String(200), nullable=True)  # 公司名称
    company_type = Column(String(50), nullable=True)  # 国企，外企，互联网，金融等
    position = Column(String(100), nullable=True)  # 职位
    industry = Column(String(100), nullable=True)  # 行业

    # 认证状态
    verification_status = Column(String(20), default="pending")  # pending, verified, rejected
    verification_method = Column(String(50), default="manual")  # manual, api, document

    # 证明材料
    work_email = Column(String(255), nullable=True)  # 工作邮箱验证
    work_certificate_url = Column(String(500), nullable=True)  # 工作证明照片

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)


# ============= P4 新增：实时聊天模型 =============

class ChatMessageDB(Base):
    """实时聊天消息"""
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), nullable=False, index=True)  # 会话 ID

    # 聊天双方
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 消息内容
    message_type = Column(String(20), default="text")  # text, image, emoji, voice, system
    content = Column(Text, nullable=False)  # 消息内容或 URL

    # 消息状态
    status = Column(String(20), default="sent")  # sent, delivered, read, recalled
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # 元数据
    message_metadata = Column(JSON, nullable=True)  # 扩展数据，如图片尺寸、语音时长等

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChatConversationDB(Base):
    """聊天会话"""
    __tablename__ = "chat_conversations"

    id = Column(String(36), primary_key=True, index=True)

    # 聊天双方
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 会话状态
    status = Column(String(20), default="active")  # active, archived, blocked
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    last_message_preview = Column(Text, nullable=True)  # 最后一条消息预览

    # 未读计数
    unread_count_user1 = Column(Integer, default=0)
    unread_count_user2 = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= 会员订阅模型 =============

class UserMembershipDB(Base):
    """用户会员状态"""
    __tablename__ = "user_memberships"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 会员等级
    tier = Column(String(20), default="free")  # free, standard, premium

    # 会员状态
    status = Column(String(20), default="inactive")  # inactive, active, expired, cancelled

    # 有效期
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # 自动续费
    auto_renew = Column(Boolean, default=False)

    # 支付信息
    payment_method = Column(String(20), nullable=True)  # wechat, alipay, apple_pay
    subscription_id = Column(String(100), nullable=True)  # 第三方订阅 ID

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MembershipOrderDB(Base):
    """会员订单"""
    __tablename__ = "membership_orders"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 会员信息
    tier = Column(String(20), nullable=False)  # standard, premium
    duration_months = Column(Integer, nullable=False)

    # 金额
    amount = Column(Float, nullable=False)  # 实付金额
    original_amount = Column(Float, nullable=False)  # 原价
    discount_code = Column(String(50), nullable=True)  # 折扣码

    # 订单状态
    status = Column(String(20), default="pending")  # pending, paid, failed, refunded

    # 支付信息
    payment_method = Column(String(20), nullable=True)
    payment_time = Column(DateTime(timezone=True), nullable=True)
    transaction_id = Column(String(100), nullable=True)  # 第三方交易 ID

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MemberFeatureUsageDB(Base):
    """会员功能使用记录"""
    __tablename__ = "member_feature_usage"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 功能类型
    feature = Column(String(50), nullable=False)  # super_like, rewind, boost

    # 使用次数
    usage_count = Column(Integer, default=1)
    usage_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============= P5 新增：滑动交互模型 =============

class SwipeActionDB(Base):
    """用户滑动动作记录"""
    __tablename__ = "swipe_actions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 滑动动作
    action = Column(String(20), nullable=False)  # like, pass, super_like

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============= P6 新增：关系类型标签模型 =============

class UserRelationshipPreferenceDB(Base):
    """用户关系类型偏好"""
    __tablename__ = "user_relationship_preferences"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 关系类型标签 (多选)
    relationship_types = Column(Text, default="")  # JSON 字符串

    # 关系状态
    current_status = Column(String(50), nullable=True)  # single, in_relationship, married, divorced, widowed

    # 对关系的期待
    expectation_description = Column(Text, nullable=True)  # 用户自定义描述

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= P6 新增：视频通话模型 =============

class VideoCallDB(Base):
    """视频通话记录"""
    __tablename__ = "video_calls"

    id = Column(String(36), primary_key=True, index=True)

    # 通话双方
    caller_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 通话状态
    status = Column(String(20), default="pending")  # pending, accepted, rejected, missed, ended

    # WebRTC 信令信息
    room_id = Column(String(100), nullable=False, unique=True, index=True)  # 通话房间 ID
    sdp_offer = Column(Text, nullable=True)  # SDP Offer
    sdp_answer = Column(Text, nullable=True)  # SDP Answer
    ice_candidates = Column(Text, default="")  # JSON 字符串，ICE Candidate 列表

    # 通话质量
    duration_seconds = Column(Integer, default=0)  # 通话时长 (秒)
    quality_score = Column(Float, nullable=True)  # 通话质量评分 1-5
    connection_type = Column(String(20), nullable=True)  # p2p, relay

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)


# ============= P6 新增：AI 陪伴助手模型 =============

class AICompanionSessionDB(Base):
    """AI 陪伴会话记录"""
    __tablename__ = "ai_companion_sessions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 会话类型
    session_type = Column(String(50), default="chat")
    companion_persona = Column(String(50), default="gentle_advisor")

    # 会话内容摘要 (脱敏)
    session_summary = Column(Text, nullable=True)
    key_insights = Column(Text, default="")  # JSON 字符串

    # 情感分析
    user_mood = Column(String(50), nullable=True)
    sentiment_score = Column(Float, nullable=True)

    # 会话时长
    duration_minutes = Column(Integer, default=0)
    message_count = Column(Integer, default=0)

    # 用户反馈
    user_rating = Column(Integer, nullable=True)  # 1-5
    user_feedback = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)


class AICompanionMessageDB(Base):
    """AI 陪伴消息记录"""
    __tablename__ = "ai_companion_messages"

    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("ai_companion_sessions.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 消息内容
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)

    # 情感分析
    emotion = Column(String(50), nullable=True)
    sentiment = Column(Float, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============= P6 新增：行为学习推荐模型 =============

class UserBehaviorFeatureDB(Base):
    """用户行为特征向量 - 用于推荐系统"""
    __tablename__ = "user_behavior_features"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 行为特征向量 (JSON 存储)
    feature_vector = Column(Text, default="")  # JSON 字符串

    # 协同过滤特征
    similar_users = Column(Text, default="")  # JSON 字符串，相似用户 ID 列表
    user_cluster = Column(String(50), nullable=True)  # 用户聚类标签

    # 偏好权重
    preference_weights = Column(Text, default="")  # JSON 字符串

    # 模型版本
    model_version = Column(String(50), default="v1")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_trained_at = Column(DateTime(timezone=True), nullable=True)


class MatchInteractionDB(Base):
    """匹配交互反馈 - 用于学习"""
    __tablename__ = "match_interactions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 交互类型
    interaction_type = Column(String(50), nullable=False)  # viewed, liked, passed, messaged, replied, blocked

    # 交互详情
    dwell_time_seconds = Column(Integer, default=0)  # 浏览时长

    # 反馈信号 (用于训练)
    positive_signal = Column(Boolean, default=True)  # 是否为正向反馈
    signal_strength = Column(Float, default=1.0)  # 信号强度 0-1

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============= P1 新增 (v1.3): 视频约会功能模型 =============

class VideoDateDB(Base):
    """视频约会记录 - v1.3 视频约会功能"""
    __tablename__ = "video_dates"

    id = Column(String(36), primary_key=True, index=True)

    # 约会双方
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 约会状态
    status = Column(String(20), default="scheduled")  # scheduled, waiting, in_progress, completed, cancelled, no_show

    # 预约信息
    scheduled_time = Column(DateTime(timezone=True), nullable=False, index=True)  # 预约开始时间
    duration_minutes = Column(Integer, default=30)  # 预计时长（分钟）
    theme = Column(String(100), nullable=True)  # 约会主题，如"初次见面"、"深度了解"

    # 房间配置
    room_id = Column(String(100), nullable=True, unique=True)  # 视频房间 ID
    background = Column(String(50), default="default")  # 虚拟背景
    filter_applied = Column(String(50), nullable=True)  # 应用的滤镜

    # 实际时间
    actual_start_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)

    # 约会评分
    rating_user1 = Column(Integer, nullable=True)  # 1-5
    rating_user2 = Column(Integer, nullable=True)
    review_user1 = Column(Text, nullable=True)
    review_user2 = Column(Text, nullable=True)

    # 游戏互动记录
    games_played = Column(Text, default="")  # JSON 字符串，记录玩过的游戏
    icebreakers_used = Column(Text, default="")  # JSON 字符串，记录使用的破冰问题

    # 举报标记
    has_report = Column(Boolean, default=False)
    report_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VideoDateReportDB(Base):
    """视频约会举报记录"""
    __tablename__ = "video_date_reports"

    id = Column(String(36), primary_key=True, index=True)
    date_id = Column(String(36), ForeignKey("video_dates.id"), nullable=False, index=True)

    # 举报人
    reporter_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    reported_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 举报原因
    reason = Column(String(50), nullable=False)  # inappropriate_behavior, harassment, spam, fake_profile, other
    description = Column(Text, nullable=False)

    # 举报状态
    status = Column(String(20), default="pending")  # pending, under_review, resolved, dismissed
    resolution = Column(Text, nullable=True)  # 处理结果说明

    # 证据
    evidence_urls = Column(Text, default="")  # JSON 字符串，截图等证据

    # 处理信息
    reviewed_by = Column(String(36), nullable=True)  # 审核员 ID
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IcebreakerQuestionDB(Base):
    """破冰问题库"""
    __tablename__ = "icebreaker_questions"

    id = Column(String(36), primary_key=True, index=True)

    # 问题内容
    question = Column(Text, nullable=False)

    # 问题分类
    category = Column(String(20), default="casual")  # casual, deep, fun, values
    # casual: 轻松话题（爱好、美食、旅行）
    # deep: 深入话题（人生观、价值观）
    # fun: 趣味话题（假设性问题）
    # values: 价值观话题（婚姻观、家庭观）

    # 难度/深度等级 (1-5)
    depth_level = Column(Integer, default=1)  # 1=浅层，5=深层

    # 适用场景
    suitable_scenarios = Column(Text, default="")  # JSON 字符串，如 ["first_date", "long_relationship"]

    # 使用统计
    usage_count = Column(Integer, default=0)
    positive_feedback_rate = Column(Float, default=0.5)  # 好评率 0-1

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class GameSessionDB(Base):
    """游戏会话记录"""
    __tablename__ = "game_sessions"

    id = Column(String(36), primary_key=True, index=True)
    date_id = Column(String(36), ForeignKey("video_dates.id"), nullable=True, index=True)

    # 参与用户
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 游戏类型
    game_type = Column(String(50), nullable=False)  # compatibility_quiz, draw_guess, truth_or_dare, memory_match
    # compatibility_quiz: 默契问答
    # draw_guess: 你画我猜
    # truth_or_dare: 真心话大冒险
    # memory_match: 记忆配对

    # 游戏状态
    status = Column(String(20), default="pending")  # pending, in_progress, completed, cancelled

    # 游戏数据
    game_data = Column(JSON, nullable=True)  # 游戏具体数据（题目、答案等）

    # 游戏结果
    winner_id = Column(String(36), nullable=True)  # 获胜者 ID，平局为 null
    score_user1 = Column(Integer, nullable=True)
    score_user2 = Column(Integer, nullable=True)
    result_summary = Column(Text, nullable=True)  # 游戏结果总结

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class VirtualBackgroundDB(Base):
    """虚拟背景配置"""
    __tablename__ = "virtual_backgrounds"

    id = Column(String(36), primary_key=True, index=True)

    # 背景信息
    name = Column(String(100), nullable=False)
    category = Column(String(50), default="scene")  # scene, abstract, color, custom
    # scene: 场景（咖啡厅、海滩、书房等）
    # abstract: 抽象图案
    # color: 纯色背景
    # custom: 用户自定义

    # 背景资源
    thumbnail_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)  # 静态图片
    video_url = Column(String(500), nullable=True)  # 动态背景（可选）

    # 可用性
    is_free = Column(Boolean, default=True)
    required_tier = Column(String(20), default="free")  # free, standard, premium

    # 使用统计
    usage_count = Column(Integer, default=0)
    popularity_score = Column(Float, default=0.0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class UserBlockDB(Base):
    """用户黑名单"""
    __tablename__ = "user_blocks"

    id = Column(String(36), primary_key=True, index=True)
    blocker_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    blocked_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 拉黑原因
    reason = Column(String(50), nullable=True)  # harassment, inappropriate_behavior, spam, other

    # 拉黑范围
    block_scope = Column(Text, default="")  # JSON 字符串，如 ["chat", "video_date", "matching"]

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 过期时间，null 为永久

    # 唯一约束：同一用户不能重复拉黑
    __table_args__ = (
        # 防止重复拉黑同一用户
        {"sqlite_autoincrement": True}
    )
