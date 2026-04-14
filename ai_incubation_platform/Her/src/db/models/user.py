"""
SQLAlchemy 数据模型 - 用户核心表

UserDB: 用户核心信息表（125 个字段）
"""
from db.models.base import *

class UserDB(Base):
    """用户数据库模型"""
    __tablename__ = "users"

    # ===== 基础字段 =====
    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)  # 用户名（登录标识）
    name = Column(String(100), nullable=False, index=True)  # 显示名称/昵称
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False, index=True)
    gender = Column(String(20), nullable=False, index=True)
    location = Column(String(200), nullable=False, index=True)
    interests = Column(Text, default="")
    values = Column(Text, default="")
    bio = Column(Text, default="")
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ===== 注册对话收集的用户画像字段 =====
    relationship_goal = Column(String(50), nullable=True, index=True)
    personality = Column(Text, nullable=True)
    ideal_type = Column(Text, nullable=True)
    lifestyle = Column(Text, nullable=True)
    deal_breakers = Column(Text, nullable=True)

    # ===== QuickStart 可选字段 =====
    education = Column(String(50), nullable=True, index=True)
    occupation = Column(String(50), nullable=True, index=True)
    income = Column(String(50), nullable=True, index=True)

    # ===== QuickStart 扩展字段 =====
    height = Column(Integer, nullable=True)
    has_car = Column(Boolean, nullable=True)
    housing = Column(String(20), nullable=True)

    # ===== 一票否决维度 =====
    want_children = Column(String(20), nullable=True, index=True)
    spending_style = Column(String(20), nullable=True, index=True)

    # ===== 核心价值观维度 =====
    family_importance = Column(Float, nullable=True)
    work_life_balance = Column(String(20), nullable=True)

    # ===== 迁移能力维度 =====
    migration_willingness = Column(Float, nullable=True)
    accept_remote = Column(String(20), nullable=True, index=True)

    # ===== 生活方式维度 =====
    sleep_type = Column(String(20), nullable=True)

    # ===== 偏好设置 =====
    preferred_age_min = Column(Integer, default=18)
    preferred_age_max = Column(Integer, default=60)
    preferred_location = Column(String(200), nullable=True)
    preferred_gender = Column(String(20), nullable=True)
    sexual_orientation = Column(String(20), default="heterosexual")

    # ===== 违规计数 =====
    violation_count = Column(Integer, default=0, index=True)
    ban_reason = Column(Text, nullable=True)
    is_permanently_banned = Column(Boolean, default=False)

    # ===== 手机号登录 =====
    phone = Column(String(20), unique=True, nullable=True, index=True)
    phone_verified = Column(Boolean, default=False)
    phone_verification_code = Column(String(6), nullable=True)
    phone_verification_expires_at = Column(DateTime(timezone=True), nullable=True)

    # ===== 微信登录 =====
    wechat_openid = Column(String(64), unique=True, nullable=True, index=True)
    wechat_unionid = Column(String(64), unique=True, nullable=True, index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # ===== 动态画像 =====
    self_profile_json = Column(Text, default="{}")
    desire_profile_json = Column(Text, default="{}")
    profile_confidence = Column(Float, default=0.3)
    profile_completeness = Column(Float, default=0.0)
    profile_updated_at = Column(DateTime(timezone=True), nullable=True)

__all__ = ["UserDB"]