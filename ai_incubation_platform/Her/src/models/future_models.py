"""
AI 约会助手数据模型 (原 Future 模块) - v1.20+

注意：文件名 "future_models" 是历史命名，实际为正在使用的 AI 约会助手核心模型。

包含功能：
- 智能聊天助手（回复建议/话题推荐） → ChatAssistantSuggestionDB
- 约会策划引擎（地点/时间/活动） → DatePlanDB（注意：与 date_reminder.py 的 DateReminderPlanDB 不同表）
- 约会地点数据库 → DateVenueDB (内部重命名为 DateVenueP20DB 避免冲突)
- 关系咨询服务（情感问题解答） → RelationshipConsultationDB
- 情感分析服务（聊天记录分析） → ChatEmotionTrendDB
- 恋爱日记（关系记录） → LoveDiaryEntryDB, LoveDiaryMemoryDB
- 关系时间线 → RelationshipTimelineDB
- 行为信用 → BehaviorCreditDB, BehaviorCreditEventDB

表名说明：
- DatePlanDB → date_plans (AI 约会策划)
- DateReminderPlanDB → date_reminder_plans (约会提醒，见 date_reminder.py)
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from db.database import Base


# ============= Future-001: 智能聊天助手模型 =============

class ChatAssistantSuggestionDB(Base):
    """聊天助手建议记录"""
    __tablename__ = "chat_assistant_suggestions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(String(36), nullable=True, index=True)  # 相关会话 ID
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)  # 聊天对象
    message_id = Column(String(36), nullable=True)  # 原始消息 ID

    # 建议类型
    suggestion_type = Column(String(50), nullable=False)
    # 类型列表:
    # - reply_suggestion: 回复建议
    # - topic_recommendation: 话题推荐
    # - compliment: 赞美话术
    # - emoji_suggestion: 表情符号建议
    # - mood_response: 情绪化回复
    # - follow_up_question: 后续问题
    # - active_listening: 积极倾听回应

    # 建议内容
    suggested_text = Column(Text, nullable=False)
    alternative_suggestions = Column(Text, default="")  # JSON 字符串，备选建议列表

    # 上下文分析
    received_message = Column(Text, nullable=True)  # 对方发来的消息
    sender_mood = Column(String(30), nullable=True)  # 发送者情绪
    conversation_context = Column(Text, nullable=True)  # 会话上下文摘要

    # AI 分析
    tone = Column(String(30), nullable=True)  # 建议语气：casual, sincere, humorous, romantic
    reasoning = Column(Text, nullable=True)  # 推荐理由
    confidence_score = Column(Float, default=0.5)  # 置信度 0-1
    emotional_intelligence_score = Column(Float, default=0.5)  # 情商评分

    # 状态
    status = Column(String(20), default="pending")  # pending, used, ignored, modified
    used_at = Column(DateTime(timezone=True), nullable=True)
    modified_text = Column(Text, nullable=True)  # 用户修改后的文本

    # 用户反馈
    user_rating = Column(Integer, nullable=True)  # 1-5
    feedback = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= Future-002: 约会策划引擎模型 =============

class DatePlanDB(Base):
    """约会计划记录"""
    __tablename__ = "date_plans"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)  # 约会对象

    # 计划类型
    plan_type = Column(String(50), nullable=False)
    # 类型列表:
    # - first_date: 首次约会
    # - anniversary: 纪念日庆祝
    # - weekend_date: 周末约会
    # - special_occasion: 特殊场合
    # - long_distance: 异地恋约会
    # - group_date: 群体约会
    # - virtual_date: 线上约会

    # 计划内容
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # 时间和地点
    proposed_date = Column(DateTime(timezone=True), nullable=True)  # 建议日期
    proposed_time = Column(String(50), nullable=True)  # 建议时间（上午/下午/晚上）
    duration_hours = Column(Float, nullable=True)  # 预计时长（小时）
    location = Column(String(200), nullable=True)  # 地点区域

    # 预算
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    estimated_total = Column(Float, nullable=True)

    # 活动安排
    activities = Column(Text, default="")  # JSON 字符串，活动安排列表
    venue_ids = Column(Text, default="")  # JSON 字符串，推荐地点 ID 列表

    # AI 分析
    reasoning = Column(Text, nullable=True)  # 推荐理由
    compatibility_analysis = Column(Text, default="")  # JSON 字符串，与双方兴趣的匹配分析
    weather_consideration = Column(String(200), nullable=True)  # 天气考虑

    # 状态
    status = Column(String(20), default="draft")  # draft, proposed, accepted, rejected, completed, cancelled
    proposed_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 反馈
    user_rating = Column(Integer, nullable=True)
    partner_rating = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DateVenueDB(Base):
    """约会地点数据库（扩展版）"""
    __tablename__ = "date_venues_p20"

    id = Column(String(36), primary_key=True, index=True)

    # 地点信息
    venue_name = Column(String(200), nullable=False, index=True)
    venue_type = Column(String(50), nullable=False, index=True)
    # 类型列表:
    # - cafe: 咖啡厅
    # - restaurant: 餐厅
    # - bar: 酒吧
    # - park: 公园
    # - museum: 博物馆
    # - cinema: 电影院
    # - theater: 剧院
    # - outdoor: 户外场所
    # - activity: 活动场所
    # - workshop: 工作室/手作体验
    # - exhibition: 展览

    category = Column(String(50), nullable=True)  # 一级分类
    subcategory = Column(String(50), nullable=True)  # 二级分类

    # 位置信息
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # 评分和信息
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    price_level = Column(Integer, default=2)  # 1-4

    # 适合的场景
    suitable_occasions = Column(Text, default="")  # JSON 字符串
    suitable_for_first_date = Column(Boolean, default=False)
    suitable_for_anniversary = Column(Boolean, default=False)
    suitable_for_group = Column(Boolean, default=False)

    # 氛围标签
    ambiance_tags = Column(Text, default="")  # JSON 字符串，如：romantic, quiet, lively, cozy
    noise_level = Column(String(20), nullable=True)  # quiet, moderate, lively

    # 设施
    facilities = Column(Text, default="")  # JSON 字符串，如：parking, wifi, private_room
    accessibility = Column(Text, default="")  # JSON 字符串，无障碍设施

    # 营业时间
    opening_hours = Column(Text, default="")  # JSON 字符串
    best_visit_time = Column(String(100), nullable=True)  # 最佳访问时间

    # 用户评价摘要
    review_summary = Column(Text, nullable=True)
    pros = Column(Text, default="")  # JSON 字符串
    cons = Column(Text, default="")  # JSON 字符串

    # 预订信息
    reservation_required = Column(Boolean, default=False)
    reservation_link = Column(String(500), nullable=True)

    # 图片来源
    image_urls = Column(Text, default="")  # JSON 字符串

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)


# ============= Future-003: 关系咨询服务模型 =============

class RelationshipConsultationDB(Base):
    """关系咨询记录"""
    __tablename__ = "relationship_consultations"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 咨询类型
    consult_type = Column(String(50), nullable=False)
    # 类型列表:
    # - relationship_confusion: 关系困惑
    # - conflict_resolution: 冲突解决
    # - communication_issue: 沟通问题
    # - commitment_discussion: 承诺讨论
    # - breakup_recovery: 分手恢复
    # - long_distance_challenge: 异地恋挑战
    # - family_integration: 见家长问题
    # - future_planning: 未来规划

    # 咨询内容
    question = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # 背景信息

    # AI 回复
    ai_response = Column(Text, nullable=False)
    key_points = Column(Text, default="")  # JSON 字符串，关键要点
    action_steps = Column(Text, default="")  # JSON 字符串，行动步骤
    additional_resources = Column(Text, default="")  # JSON 字符串，额外资源

    # 心理学依据
    psychological_basis = Column(Text, nullable=True)  # 心理学依据
    related_theories = Column(Text, default="")  # JSON 字符串，相关理论

    # 状态
    status = Column(String(20), default="completed")  # completed, archived
    is_helpful = Column(Boolean, nullable=True)  # 用户反馈是否有用

    # 跟进
    follow_up_required = Column(Boolean, default=False)
    follow_up_at = Column(DateTime(timezone=True), nullable=True)
    follow_up_notes = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RelationshipFAQDB(Base):
    """关系咨询常见问题库"""
    __tablename__ = "relationship_faqs"

    id = Column(String(36), primary_key=True, index=True)

    # 问题分类
    category = Column(String(50), nullable=False, index=True)
    # 分类列表:
    # - early_stage: 早期阶段
    # - dating: 约会中
    # - relationship: 恋爱中
    # - conflict: 冲突处理
    # - communication: 沟通
    # - intimacy: 亲密关系
    # - long_distance: 异地恋
    # - breakup: 分手

    # 问题和答案
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    keywords = Column(Text, default="")  # JSON 字符串，关键词列表

    # 答案详情
    detailed_explanation = Column(Text, nullable=True)
    examples = Column(Text, default="")  # JSON 字符串，示例
    dos_and_donts = Column(Text, default="")  # JSON 字符串

    # 元数据
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)


# ============================================
# Future 模型注册到统一模型中心
# ============================================
# 注意：EmotionAnalysisDB 已在 emotion_analysis_models 中定义，此处不重复定义
# Future 的情感分析专注于聊天会话分析，与 Emotion 的视频面诊不同
# 如需使用情感趋势模型，请使用 ChatEmotionTrendDB（Future 专用）


class ChatEmotionTrendDB(Base):
    """聊天情感趋势记录 (Future 专用 - 专注于聊天会话分析)

    与 Emotion 的 EmotionalTrendDB 区别:
    - Emotion: 基于视频面诊/语音的情感趋势
    - Future: 基于聊天文本的情感趋势
    """
    __tablename__ = "chat_emotion_trends"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 趋势周期
    period = Column(String(20), nullable=False)  # daily, weekly, monthly
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # 趋势数据
    avg_sentiment = Column(Float, default=0.0)
    sentiment_trend = Column(String(20), nullable=True)  # improving, stable, declining
    daily_sentiments = Column(Text, default="")  # JSON 字符串，每日情感得分

    # 关键事件
    key_events = Column(Text, default="")  # JSON 字符串，影响情感的关键事件
    peak_positive_date = Column(DateTime(timezone=True), nullable=True)
    peak_negative_date = Column(DateTime(timezone=True), nullable=True)

    # 关系热力
    relationship_heat = Column(Float, default=0.0)  # 0-100，关系热度
    communication_frequency = Column(Float, default=0.0)  # 日均沟通次数

    # AI 洞察
    trend_analysis = Column(Text, nullable=True)
    predictions = Column(Text, default="")  # JSON 字符串，趋势预测

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============= Future-005: 恋爱日记服务模型 =============

class LoveDiaryEntryDB(Base):
    """恋爱日记条目"""
    __tablename__ = "love_diary_entries"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 日记类型
    entry_type = Column(String(50), nullable=False)
    # 类型列表:
    # - auto_generated: AI 自动生成
    # - manual_entry: 手动记录
    # - milestone: 里程碑事件
    # - photo_memory: 照片回忆
    # - voice_note: 语音记录
    # - date_record: 约会记录
    # - mood_log: 心情记录

    # 日记内容
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(String(500), nullable=True)  # 摘要

    # 情感
    mood = Column(String(30), nullable=True)  # happy, sad, excited, nervous, etc.
    emotion_tags = Column(Text, default="")  # JSON 字符串

    # 关联
    related_event_id = Column(String(36), nullable=True)  # 关联事件 ID
    related_event_type = Column(String(50), nullable=True)  # date, milestone, conversation

    # 媒体
    photo_urls = Column(Text, default="")  # JSON 字符串
    voice_note_url = Column(String(500), nullable=True)
    location_name = Column(String(200), nullable=True)
    location_coords = Column(String(50), nullable=True)  # lat,lng

    # 隐私
    is_private = Column(Boolean, default=False)
    is_shared_with_partner = Column(Boolean, default=False)
    shared_at = Column(DateTime(timezone=True), nullable=True)

    # AI 增强
    ai_enhanced = Column(Boolean, default=False)
    ai_polish_content = Column(Text, nullable=True)  # AI 润色后的内容
    ai_suggested_title = Column(String(200), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    entry_date = Column(DateTime(timezone=True), nullable=True)  # 日记记录的日期


class LoveDiaryMemoryDB(Base):
    """恋爱日记回忆"""
    __tablename__ = "love_diary_memories"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 回忆类型
    memory_type = Column(String(50), nullable=False)
    # 类型列表:
    # - first_time: 第一次
    # - special_moment: 特别时刻
    # - funny_moment: 有趣时刻
    # - touching_moment: 感动时刻
    # - challenge_overcome: 共同克服的挑战

    # 回忆内容
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    memory_date = Column(DateTime(timezone=True), nullable=False)

    # 关联日记
    related_entry_ids = Column(Text, default="")  # JSON 字符串

    # 媒体
    photo_urls = Column(Text, default="")  # JSON 字符串

    # 情感
    emotion = Column(String(30), nullable=True)
    significance_score = Column(Float, default=0.5)  # 重要性评分 0-1

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RelationshipTimelineDB(Base):
    """关系时间线事件"""
    __tablename__ = "relationship_timelines"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 事件类型
    event_type = Column(String(50), nullable=False)
    # 类型列表:
    # - first_match: 首次匹配
    # - first_message: 首次对话
    # - first_date: 首次约会
    # - relationship_start: 开始恋爱
    # - first_trip: 首次旅行
    # - meet_family: 见家长
    # - engagement: 订婚
    # - marriage: 结婚
    # - custom: 自定义事件

    # 事件信息
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_date = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(200), nullable=True)

    # 媒体
    photo_urls = Column(Text, default="")  # JSON 字符串

    # 来源
    source = Column(String(50), default="manual")  # manual, auto_detected, imported
    source_entity_type = Column(String(50), nullable=True)  # 来源实体类型
    source_entity_id = Column(String(36), nullable=True)  # 来源实体 ID

    # 重要性
    importance_level = Column(Integer, default=1)  # 1-5
    is_milestone = Column(Boolean, default=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= Future-006: AI 行为信用分系统 =============

class BehaviorCreditDB(Base):
    """用户行为信用记录"""
    __tablename__ = "behavior_credits"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 信用分数
    credit_score = Column(Integer, default=100, nullable=False)  # 0-100
    credit_level = Column(String(10), default="B")  # S/A/B/C/D

    # 分数明细
    base_score = Column(Integer, default=100)  # 基础分
    positive_score = Column(Integer, default=0)  # 正面行为加分
    negative_score = Column(Integer, default=0)  # 负面行为扣分

    # 行为统计
    total_positive_events = Column(Integer, default=0)
    total_negative_events = Column(Integer, default=0)

    # 信用等级历史
    level_history = Column(Text, default="")  # JSON 字符串，等级变化历史

    # 限制状态
    restrictions = Column(Text, default="")  # JSON 字符串，当前限制列表
    # 限制类型：no_chat_initiate, no_contact_exchange, reduced_recommendations

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_calculated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BehaviorCreditEventDB(Base):
    """行为信用事件记录"""
    __tablename__ = "behavior_credit_events"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 事件类型
    event_type = Column(String(50), nullable=False)
    # 负面事件:
    # - harassment_reported: 被举报骚扰 (-50)
    # - fake_info_detected: 虚假信息 (-30)
    # - aggressive_language: 攻击性语言 (-20)
    # - photo_rejected: 照片审核不通过 (-10)
    # - ghosting_after_contact: 交换联系方式后消失 (-5)
    # - spam_behavior: 骚扰行为 (-15)
    # - inappropriate_content: 不当内容 (-25)
    # 正面事件:
    # - complete_profile: 完善资料 (+10)
    # - verified_badge: 获得认证标识 (+20)
    # - positive_feedback: 获得好评 (+15)
    # - active_response: 及时回复 (+5)
    # - successful_date: 成功约会 (+25)
    # - helpful_behavior: 帮助他人 (+10)

    # 分数变化
    score_change = Column(Integer, nullable=False)  # 正数为加分，负数为扣分
    score_before = Column(Integer, nullable=False)
    score_after = Column(Integer, nullable=False)

    # 事件详情
    description = Column(Text, nullable=False)
    evidence = Column(Text, default="")  # JSON 字符串，证据信息
    source = Column(String(50), nullable=False)  # 来源：system, user_report, ai_detection, manual_review

    # 关联实体
    related_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)  # 相关用户（如举报人）
    related_message_id = Column(String(36), nullable=True)  # 相关消息 ID
    related_report_id = Column(String(36), nullable=True)  # 相关举报 ID

    # 处理状态
    status = Column(String(20), default="processed")  # pending, processed, appealed, overturned
    processed_by = Column(String(50), nullable=True)  # ai, manual_reviewer
    reviewer_id = Column(String(36), nullable=True)  # 审核员 ID

    # 申诉
    appeal_reason = Column(Text, nullable=True)
    appeal_result = Column(String(20), nullable=True)  # approved, rejected, pending
    appeal_processed_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
