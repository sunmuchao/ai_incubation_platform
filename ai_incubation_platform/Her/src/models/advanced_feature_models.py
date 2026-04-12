"""
Advanced 数据模型

EmotionWeather: AI 预沟通
Advanced: 真实匹配（消费水平与地理轨迹）
Future: 防渣黑名单（行为信用分）
Advanced: 动态关系教练
Advanced: 产品悖论破解（情境感知、用户确权、隐私透明）
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base


# ==================== EmotionWeather: AI 预沟通模型 ====================

class AIChatSession(Base):
    """
    AI 预沟通会话
    当新匹配产生时，双方 AI Agent 进行自动对聊
    """
    __tablename__ = "p18_ai_chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(String, nullable=False, index=True)  # 用户 A ID
    user_b_id = Column(String, nullable=False, index=True)  # 用户 B ID
    session_status = Column(String, default="pending")  # pending, chatting, completed, cancelled

    # 对话配置
    conversation_rounds = Column(Integer, default=50)  # 目标对话轮数
    completed_rounds = Column(Integer, default=0)  # 已完成轮数

    # 关键发现
    three_views_match_score = Column(Float, default=0.0)  # 三观匹配度 (0-1)
    settlement_plan_match = Column(Boolean, default=False)  # 定居计划是否一致
    pet_attitude_match = Column(Boolean, default=False)  # 宠物态度是否一致
    career_compatibility = Column(String)  # 职业兼容性：high/medium/low

    # 对话记录 (JSON 格式存储)
    conversation_log = Column(JSON, default=list)  # [{"round": 1, "user_a_agent": "...", "user_b_agent": "..."}]

    # 提取的关键信息
    key_findings = Column(JSON, default=dict)  # {定居计划，生育观念，宠物态度， etc.}

    # 推荐结果
    overall_match_score = Column(Float, default=0.0)  # 综合匹配度 (0-1)
    recommendation = Column(String)  # "建议开启人工对话" / "匹配度较低"
    recommendation_reason = Column(Text)  # 推荐理由详细说明

    # 时间戳
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_user_pair', 'user_a_id', 'user_b_id'),
    )


class AIChatSessionResult(Base):
    """
    AI 预沟通结果报告
    """
    __tablename__ = "p18_chat_session_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("p18_ai_chat_sessions.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)  # 查看报告的用户 ID

    # 报告内容
    report_content = Column(JSON, default=dict)  # 完整的匹配报告
    match_highlights = Column(JSON, default=list)  # 匹配亮点列表

    # 用户反馈
    user_feedback = Column(String)  # interested, not_interested, need_more_time
    user_action = Column(String)  # start_chat, pass, maybe

    # 是否已读
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_session_user', 'session_id', 'user_id'),
    )


# ==================== Advanced: 真实匹配模型 ====================

class ConsumptionProfile(Base):
    """
    用户消费画像
    基于授权后的账单特征分析（非明细）
    """
    __tablename__ = "p19_consumption_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)

    # 消费层级
    consumption_level = Column(String)  # "经济型", "性价比", "轻奢", "高端", "奢华"
    consumption_frequency = Column(String)  # "低频", "中频", "高频"

    # 消费类别偏好 (JSON)
    preferred_categories = Column(JSON, default=list)  # ["精品咖啡", "书店", "艺术展览", etc.]

    # 消费特征
    average_transaction = Column(String)  # "0-100 元", "100-300 元", "300-500 元", "500+ 元"
    monthly_spending_trend = Column(String)  # "稳定", "增长", "下降"

    # 账单特征分析结果（非明细）
    bill_characteristics = Column(JSON, default=dict)  # {商户类型分布，时间段分布，etc.}

    # 授权状态
    is_authorized = Column(Boolean, default=False)
    authorized_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeoTrajectory(Base):
    """
    用户地理轨迹画像
    """
    __tablename__ = "p19_geo_trajectories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)

    # 常驻区域
    home_district = Column(String)  # 朝阳区
    work_district = Column(String)  # 海淀区

    # 常去区域列表 (JSON)
    frequent_areas = Column(JSON, default=list)
    # [{"name": "三里屯", "type": "商圈", "visit_count": 25, "last_visit": "2026-04-01"}]

    # 商圈偏好
    preferred商圈_types = Column(JSON, default=list)  # ["购物中心", "文艺街区", "科技园区"]

    # 生活质感评估
    lifestyle_quality_score = Column(Float, default=5.0)  # 1-10 分
    lifestyle_tags = Column(JSON, default=list)  # ["文艺", "小资", "品质生活", "极简"]

    # 活动范围半径 (km)
    activity_radius_km = Column(Float, default=10.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthenticMatchResult(Base):
    """
    真实匹配结果（基于消费和地理）
    """
    __tablename__ = "p19_authentic_match_results"

    id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(String, nullable=False, index=True)
    user_b_id = Column(String, nullable=False, index=True)

    # 匹配维度得分
    consumption_match_score = Column(Float, default=0.0)  # 消费观匹配度
    lifestyle_match_score = Column(Float, default=0.0)  # 生活方式匹配度
    aesthetic_match_score = Column(Float, default=0.0)  # 审美匹配度
    geo_compatibility_score = Column(Float, default=0.0)  # 地理兼容性

    # 综合得分
    overall_match_score = Column(Float, default=0.0)

    # 匹配合集
    match_highlights = Column(JSON, default=list)  # ["都常去三里屯", "都喜欢精品咖啡", etc.]

    # 风险提示
    potential_gaps = Column(JSON, default=list)  # ["消费层级差异较大", "活动区域较少重叠"]

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_match_pair', 'user_a_id', 'user_b_id', unique=True),
    )


# ==================== Future: 防渣黑名单模型 ====================

class BehaviorCredit(Base):
    """
    用户行为信用分
    """
    __tablename__ = "p20_behavior_credits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)

    # 信用分 (0-100)
    credit_score = Column(Integer, default=80)

    # 信用等级
    credit_level = Column(String, default="正常")  # "高信用", "正常", "关注", "高风险"

    # 评分因素 (JSON)
    scoring_factors = Column(JSON, default=dict)
    # {
    #   "identity_verified": true,
    #   "photo_authenticity": 0.95,
    #   "date_feedback_score": 4.8,
    #   "interaction_quality": 0.92,
    #   "response_rate": 0.85,
    #   "complaint_count": 0
    # }

    # 动态更新记录
    score_changes = Column(JSON, default=list)  # [{date, change, reason}]

    # 标记列表
    flags = Column(JSON, default=list)  # [{"type": "late", "count": 2}, {"type": "cold_violence", "count": 0}]

    # 高风险预警触发次数
    high_risk_warnings = Column(Integer, default=0)

    # 封禁状态
    is_banned = Column(Boolean, default=False)
    banned_at = Column(DateTime)
    ban_reason = Column(Text)
    ban_device_id = Column(String)  # 封禁设备号

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DateFeedback(Base):
    """
    约会后反馈
    """
    __tablename__ = "p20_date_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    date_id = Column(String, nullable=False, index=True)  # 约会 ID

    # 反馈者 ID（匿名处理）
    reporter_id = Column(String, nullable=False, index=True)
    target_user_id = Column(String, nullable=False, index=True)  # 被反馈的用户

    # 反馈内容
    feedback_items = Column(JSON, default=dict)
    # {
    #   "offensive_behavior": false,
    #   "photo_authentic": true,
    #   "late_arrival": false,
    #   "cold_violence": false,
    #   "financial_solicitation": false,
    #   "respectful": true,
    #   "good_communication": true
    # }

    # 总体评分 (1-5)
    overall_rating = Column(Integer, default=5)

    # 文字评论（可选，匿名）
    comments = Column(Text)

    # 反馈类型
    feedback_type = Column(String)  # "positive", "neutral", "negative"

    # 是否已处理
    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_target_user', 'target_user_id', 'feedback_type'),
    )


class RiskFlag(Base):
    """
    风险标记（多人反馈时触发）
    """
    __tablename__ = "p20_risk_flags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)

    # 风险类型
    risk_type = Column(String, nullable=False)  # "杀猪盘", "言语骚扰", "诱导理财", "照片造假", etc.

    # 反馈次数
    report_count = Column(Integer, default=1)

    # 风险等级
    risk_level = Column(String)  # "low", "medium", "high", "critical"

    # 详情
    details = Column(JSON, default=list)  # 反馈详情列表

    # 处理状态
    status = Column(String, default="pending")  # pending, investigating, resolved, banned
    handled_by = Column(String)  # 处理人 ID
    handled_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Advanced: 动态关系教练模型 ====================

class RelationshipHealth(Base):
    """
    关系健康度监测
    """
    __tablename__ = "p21_relationship_health"

    id = Column(Integer, primary_key=True, index=True)
    couple_id = Column(String, nullable=False, unique=True, index=True)  # 情侣 ID
    user_a_id = Column(String, nullable=False)
    user_b_id = Column(String, nullable=False)

    # 沟通频率监测
    current_daily_messages = Column(Integer, default=0)  # 当前日均消息数
    previous_daily_messages = Column(Integer, default=0)  # 之前日均消息数
    communication_trend = Column(Float, default=1.0)  # 趋势比率 (当前/之前)
    communication_status = Column(String)  # "健康", "需要关注", "危险"

    # 关键词分析
    positive_keywords_count = Column(Integer, default=0)
    negative_keywords_count = Column(Integer, default=0)
    neutral_keywords_count = Column(Integer, default=0)
    keyword_trend = Column(String)  # "积极", "中性", "冷淡"

    # AI 介入记录
    ai_interventions = Column(JSON, default=list)
    # [{date, message, topic_suggestions, user_response}]

    # 关系状态
    relationship_stage = Column(String)  # "初识", "暧昧", "交往中", "稳定期", "倦怠期"

    # 健康度评分 (0-100)
    health_score = Column(Integer, default=80)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GiftManager(Base):
    """
    送礼与纪念日管家
    """
    __tablename__ = "p21_gift_managers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)

    # 对方信息
    partner_id = Column(String, nullable=False)
    partner_name = Column(String)

    # 对方喜好画像 (JSON)
    partner_preferences = Column(JSON, default=dict)
    # {favorite_colors, favorite_brands, hobbies, style}

    # 重要日期
    upcoming_events = Column(JSON, default=list)
    # [{"event": "生日", "date": "2026-04-20", "days_remaining": 12, "gift_ideas": []}]

    # 礼物历史
    gift_history = Column(JSON, default=list)
    # [{"date", "gift", "price", "rating"}]

    # 自动下单配置
    auto_order_enabled = Column(Boolean, default=False)
    budget_range = Column(String)  # "0-200 元", "200-500 元", "500+ 元"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Advanced: 产品悖论破解模型 ====================

class DynamicProfile(Base):
    """
    动态用户画像（情境感知）
    """
    __tablename__ = "p22_dynamic_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)

    # 基础画像（来自注册对话）
    base_profile = Column(JSON, default=dict)
    # {values, personality, interests}

    # 实时状态
    real_time_state = Column(JSON, default=dict)
    # {
    #   "mood": "渴望倾听",  # 渴望倾听/只想看颜/寻找共同爱好
    #   "energy_level": "高/中/低",
    #   "social_appetite": "深层社交/浅层社交",
    #   "last_updated": timestamp
    # }

    # 行为信号
    behavior_signals = Column(JSON, default=dict)
    # {
    #   "swipe_speed_trend": "加快/稳定/减慢",
    #   "profile_view_duration": "延长/缩短",
    #   "message_response_rate": 0.85,
    #   "anxiety_indicator": "高/中/低"
    # }

    # 动态权重（情境感知调整后的）
    adjusted_weights = Column(JSON, default=dict)
    # {values: 0.25, personality: 0.15, appearance: 0.35, communication: 0.25}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PreferenceDial(Base):
    """
    用户偏好拨盘（用户确权）
    """
    __tablename__ = "p22_preference_dials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)

    # 用户可调节的权重
    is_user_adjustable = Column(Boolean, default=True)

    # 当前设置 (0-100)
    values_weight = Column(Integer, default=30)
    personality_weight = Column(Integer, default=20)
    appearance_weight = Column(Integer, default=35)
    communication_weight = Column(Integer, default=15)

    # AI 建议的调整
    ai_suggested_adjustment = Column(JSON, default=dict)
    # {"reason": "检测到您最近更关注外表吸引力", "suggested_appearance_weight": 40}

    # 调整历史
    adjustment_history = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PrivacySetting(Base):
    """
    隐私权限设置（信任透明）
    """
    __tablename__ = "p22_privacy_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)

    # 数据访问级别
    data_access_level = Column(String, default="standard")
    # minimal: 仅分析文字
    # standard: 分析文字 + 行为
    # full: 分析文字 + 行为 + 语音 + 位置

    # 允许的分析类型
    allowed_analysis = Column(JSON, default=list)  # ["text", "behavior"]

    # 禁止的分析类型
    blocked_analysis = Column(JSON, default=list)  # ["voice", "location", "biometric"]

    # 审计日志可见性
    audit_log_visible = Column(Boolean, default=True)

    # 申诉功能可用性
    appeal_available = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIAuditLog(Base):
    """
    AI 干预审计日志（可解释 AI）
    """
    __tablename__ = "p22_ai_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)

    # 干预类型
    intervention_type = Column(String, nullable=False)
    # recommendation, warning, suggestion, analysis

    # 干预内容
    intervention_content = Column(JSON, default=dict)

    # AI 判断依据
    ai_reasoning = Column(Text)

    # 置信度
    confidence_score = Column(Float, default=0.0)

    # 用户反馈
    user_feedback = Column(String)  # helpful, not_helpful, false_positive
    user_correction = Column(Text)  # 用户纠正内容

    # 是否用于模型优化
    used_for_training = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class OfflineConversionFunnel(Base):
    """
    线下转化漏斗追踪
    """
    __tablename__ = "p22_offline_conversion_funnels"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String, nullable=False, index=True)
    user_a_id = Column(String, nullable=False)
    user_b_id = Column(String, nullable=False)

    # 转化阶段
    current_stage = Column(String, default="online_chat")
    # online_chat -> contact_exchanged -> date_planned -> date_completed

    # 各阶段时间戳
    online_chat_started_at = Column(DateTime)
    contact_exchanged_at = Column(DateTime)
    date_planned_at = Column(DateTime)
    date_completed_at = Column(DateTime)

    # AI 辅助记录
    ai_assistance_records = Column(JSON, default=list)
    # [{stage, action, result}]

    # 破冰任务完成情况
    icebreaker_tasks = Column(JSON, default=list)
    # [{task_id, task_name, completed, completed_at}]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CoupleMode(Base):
    """
    情侣模式（数字家园）
    """
    __tablename__ = "p22_couple_modes"

    id = Column(Integer, primary_key=True, index=True)
    couple_id = Column(String, nullable=False, unique=True, index=True)
    user_a_id = Column(String, nullable=False)
    user_b_id = Column(String, nullable=False)

    # 模式状态
    is_active = Column(Boolean, default=False)

    # 界面主题
    theme = Column(String, default="default")  # default, romantic, minimal

    # 共享空间配置
    shared_space_config = Column(JSON, default=dict)
    # {photo_wall, shared_calendar, goal_board}

    # 毕业状态
    is_graduated = Column(Boolean, default=False)
    graduated_at = Column(DateTime)
    graduation_album = Column(JSON, default=dict)  # 毕业纪念册

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
