"""
SocialTribe 圈子融合数据库模型

核心理念：生活圈的介绍人
恋爱是两个圈子的碰撞，不仅要人合，还要生活方式合。

包含以下模块：
1. 部落匹配 - 生活方式标签、圈子融合算法
2. 数字小家 - 私密空间、共同目标、打卡监督
3. 见家长模拟 - 虚拟角色、社交场景模拟
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum
from sqlalchemy.orm import relationship
import enum

from db.database import Base


# ==================== 部落匹配模块 ====================

class LifestyleTag(str, enum.Enum):
    """生活方式标签"""
    OUTDOOR = "outdoor"  # 户外爱好者
    HOMEBODY = "homebody"  # 宅家派
    FITNESS = "fitness"  # 健身达人
    FOODIE = "foodie"  # 美食家
    TRAVELER = "traveler"  # 旅行家
    ARTIST = "artist"  # 文艺青年
    GAMER = "gamer"  # 游戏玩家
    READER = "reader"  # 阅读爱好者
    PARTY = "party"  # 派对动物
    VOLUNTEER = "volunteer"  # 志愿者


class TribeType(str, enum.Enum):
    """部落类型"""
    CAMPING = "camping"  # 露营狂魔
    SCRIPT_GAMES = "script_games"  # 剧本杀达人
    MARATHON = "marathon"  # 马拉松爱好者
    COOKING = "cooking"  # 厨艺达人
    PHOTOGRAPHY = "photography"  # 摄影爱好者
    MUSIC = "music"  # 音乐爱好者
    MOVIE = "movie"  # 电影爱好者
    TECH = "tech"  # 科技爱好者


class LifestyleTribeDB(Base):
    """生活方式部落"""
    __tablename__ = "lifestyle_tribes"

    id = Column(String, primary_key=True)

    # 部落信息
    tribe_name = Column(String, nullable=False)
    tribe_type = Column(String, nullable=False)
    description = Column(Text)

    # 标签
    lifestyle_tags = Column(JSON)  # [outdoor, fitness]

    # 活动列表
    regular_activities = Column(JSON)  # 定期举办的活动

    # 成员统计
    member_count = Column(Integer, default=0)
    active_member_count = Column(Integer, default=0)

    # 部落特色
    tribe_features = Column(JSON)

    # 创建者
    founder_id = Column(String, ForeignKey("users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)


class UserTribeMembershipDB(Base):
    """用户部落成员关系"""
    __tablename__ = "user_tribe_memberships"

    id = Column(String, primary_key=True)

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tribe_id = Column(String, ForeignKey("lifestyle_tribes.id"), nullable=False)

    # 成员角色
    role = Column(String, default="member")  # member, moderator, admin

    # 参与程度
    participation_level = Column(String)  # casual, active, core

    # 加入时间
    joined_at = Column(DateTime, default=datetime.utcnow)

    # 贡献度
    contribution_score = Column(Integer, default=0)

    # 参与活动次数
    activities_participated = Column(Integer, default=0)


class TribeCompatibilityDB(Base):
    """部落兼容性评估"""
    __tablename__ = "tribe_compatibility"

    id = Column(String, primary_key=True)

    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 共同部落
    common_tribes = Column(JSON)  # 共同加入的部落

    # 兼容标签
    compatible_tags = Column(JSON)  # 兼容的生活方式标签

    # 冲突标签
    conflicting_tags = Column(JSON)  # 可能冲突的标签

    # 兼容性评分
    compatibility_score = Column(Float, default=0.0)

    # 融合建议
    fusion_suggestions = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 数字小家模块 ====================

class DigitalHomeType(str, enum.Enum):
    """数字小家类型"""
    COUPLE = "couple"  # 情侣空间
    ENGAGED = "engaged"  # 订婚空间
    MARRIED = "married"  # 已婚空间


class CoupleDigitalHomeDB(Base):
    """情侣数字小家"""
    __tablename__ = "couple_digital_homes"

    id = Column(String, primary_key=True)

    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 小家信息
    home_name = Column(String, nullable=False)
    home_type = Column(String, default=DigitalHomeType.COUPLE.value)

    # 主题
    theme = Column(String)  # 温馨、简约、浪漫等

    # 背景
    background_image_url = Column(String)

    # 纪念日
    anniversary_date = Column(DateTime)

    # 共同空间配置
    shared_space_config = Column(JSON)
    # {photo_wall, calendar, todo_list, memory_box}

    # 隐私设置
    is_private = Column(Boolean, default=True)

    # 最后活跃时间
    last_active_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CoupleGoalDB(Base):
    """共同目标"""
    __tablename__ = "couple_goals"

    id = Column(String, primary_key=True)

    # 关联的数字小家 ID
    home_id = Column(String, ForeignKey("couple_digital_homes.id"))

    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 目标信息
    goal_title = Column(String, nullable=False)
    goal_description = Column(Text)

    # 目标类型
    goal_type = Column(String)
    # fitness, saving, travel, learning, health

    # 目标设定
    target_value = Column(Float)  # 目标值（如金额、次数）
    current_value = Column(Float, default=0)  # 当前进度
    unit = Column(String)  # 单位

    # 时间设定
    start_date = Column(DateTime)
    target_date = Column(DateTime)

    # 目标状态
    status = Column(String, default="active")  # active, completed, paused

    # 提醒设置
    reminder_frequency = Column(String)  # daily, weekly, monthly
    reminder_enabled = Column(Boolean, default=True)

    # 奖励设定
    reward_description = Column(Text)  # 达成后的奖励

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class CoupleCheckinDB(Base):
    """情侣打卡记录"""
    __tablename__ = "couple_checkins"

    id = Column(String, primary_key=True)

    goal_id = Column(String, ForeignKey("couple_goals.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 打卡内容
    checkin_content = Column(Text)
    checkin_value = Column(Float, default=1)  # 本次打卡的贡献值

    # 证明
    proof_photo_urls = Column(JSON)
    proof_note = Column(Text)

    # 打卡日期
    checkin_date = Column(DateTime, default=datetime.utcnow)

    # 连续打卡
    streak_count = Column(Integer, default=1)

    # 同伴确认
    partner_acknowledged = Column(Boolean, default=False)
    partner_note = Column(Text)


# ==================== 见家长模拟模块 ====================

class VirtualRoleType(str, enum.Enum):
    """虚拟角色类型"""
    PARENT = "parent"  # 家长
    SIBLING = "sibling"  # 兄弟姐妹
    RELATIVE = "relative"  # 亲戚
    FRIEND = "friend"  # 朋友


class VirtualRoleDB(Base):
    """虚拟角色"""
    __tablename__ = "virtual_roles"

    id = Column(String, primary_key=True)

    # 创建者
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 角色信息
    role_name = Column(String, nullable=False)
    role_type = Column(String, default=VirtualRoleType.PARENT.value)

    # 角色特征
    personality = Column(String)  # 严厉、温和、开明
    interests = Column(JSON)  # 兴趣爱好
    values = Column(JSON)  # 价值观

    # 对话风格
    conversation_style = Column(JSON)

    # 常见问题
    typical_questions = Column(JSON)

    # 难度等级
    difficulty_level = Column(Integer, default=3)  # 1-5

    created_at = Column(DateTime, default=datetime.utcnow)


class FamilyMeetingSimulationDB(Base):
    """见家长模拟记录"""
    __tablename__ = "family_meeting_simulations"

    id = Column(String, primary_key=True)

    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 使用的虚拟角色
    role_id = Column(String, ForeignKey("virtual_roles.id"))

    # 场景设置
    scenario = Column(String, nullable=False)
    # first_meet, formal_dinner, casual_visit

    # 模拟状态
    status = Column(String, default="ongoing")  # ongoing, completed

    # 对话历史
    conversation_history = Column(JSON)

    # 模拟时长
    duration_minutes = Column(Integer)

    # 表现评估
    performance_scores = Column(JSON)
    # {communication, respect, confidence, appropriateness}

    # AI 反馈
    ai_feedback = Column(Text)

    # 改进建议
    improvement_suggestions = Column(JSON)

    # 用户自评
    self_rating = Column(Integer)

    is_completed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


# 创建全局服务实例（在 social_tribe_service.py 中实现）
