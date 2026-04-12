"""
EmotionWeather 数据模型定义 - v1.18 关系进阶功能

关系进阶功能包括：
- 关系状态管理增强（暧昧/恋爱/订婚/结婚）
- AI 约会建议引擎
- 恋爱指导服务（聊天建议/礼物推荐）
- 关系健康度分析
- 关系进阶 API 端点
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Table, JSON, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base
import enum


# ============= EmotionWeather-001: 关系状态管理增强模型 =============

class RelationshipStateDB(Base):
    """关系状态记录 - 增强版"""
    __tablename__ = "relationship_states"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 关系状态
    state = Column(String(30), nullable=False, default="matched")
    # 状态列表:
    # - matched: 已匹配
    # - chatting: 聊天中
    # -暧昧：ambiguity (互有好感但未明确)
    # - dating: 约会中
    # - exclusive: 确定排他性关系
    # - in_relationship: 恋爱中
    # - engaged: 已订婚
    # - married: 已结婚
    # - separated: 已分居
    # - broken_up: 已分手

    # 状态详情
    state_label = Column(String(50), nullable=True)  # 中文标签
    state_description = Column(Text, nullable=True)  # 状态描述

    # 状态变更
    previous_state = Column(String(30), nullable=True)
    state_changed_at = Column(DateTime(timezone=True), nullable=True)
    state_change_reason = Column(String(200), nullable=True)

    # AI 分析
    ai_confidence = Column(Float, default=0.5)  # AI 对当前状态判断的置信度 0-1
    ai_analysis = Column(Text, default="")  # JSON 字符串，AI 分析详情

    # 双方确认状态
    confirmed_by_user1 = Column(Boolean, default=False)
    confirmed_by_user2 = Column(Boolean, default=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 唯一约束
    __table_args__ = (
        UniqueConstraint('user_id_1', 'user_id_2', name='uq_relationship_pair'),
    )


class RelationshipStateTransitionDB(Base):
    """关系状态变更历史"""
    __tablename__ = "relationship_state_transitions"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 状态变更
    from_state = Column(String(30), nullable=True)
    to_state = Column(String(30), nullable=False)
    to_state_label = Column(String(50), nullable=True)

    # 变更原因
    transition_type = Column(String(50), nullable=False)  # manual, ai_detected, mutual_agreement
    transition_reason = Column(String(200), nullable=True)
    trigger_event = Column(String(100), nullable=True)  # 触发事件，如 first_date, confession 等

    # AI 分析
    ai_comment = Column(Text, nullable=True)  # AI 对状态变更的评论
    next_stage_suggestions = Column(Text, default="")  # JSON 字符串，下一阶段建议

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============= EmotionWeather-002: AI 约会建议引擎模型 =============

class DatingAdviceDB(Base):
    """AI 生成的约会建议"""
    __tablename__ = "dating_advice"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)  # 约会对象

    # 建议类型
    advice_type = Column(String(50), nullable=False)
    # 类型列表:
    # - first_date: 首次约会建议
    # - anniversary: 纪念日庆祝建议
    # - routine: 日常约会建议
    # - special: 特殊场合建议
    # - long_distance: 异地恋约会建议
    # - group_date: 群体约会建议

    # 建议内容
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # 推荐详情
    activity_type = Column(String(50), nullable=True)  # 活动类型
    venue_suggestions = Column(Text, default="")  # JSON 字符串，推荐地点列表
    estimated_cost = Column(Float, nullable=True)  # 预估费用
    estimated_duration = Column(Integer, nullable=True)  # 预估时长（分钟）
    best_timing = Column(String(100), nullable=True)  # 最佳时间建议

    # AI 分析
    reasoning = Column(Text, nullable=True)  # 推荐理由
    compatibility_analysis = Column(Text, default="")  # JSON 字符串，与双方兴趣的匹配分析
    confidence_score = Column(Float, default=0.5)  # 置信度 0-1

    # 状态
    status = Column(String(20), default="pending")  # pending, accepted, rejected, expired, completed
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 用户反馈
    user_rating = Column(Integer, nullable=True)  # 1-5
    user_feedback = Column(Text, nullable=True)
    actual_cost = Column(Float, nullable=True)  # 实际花费
    actual_duration = Column(Integer, nullable=True)  # 实际时长

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 建议过期时间


class DatingVenueDB(Base):
    """约会地点数据库 - 增强版"""
    __tablename__ = "dating_venues"

    id = Column(String(36), primary_key=True, index=True)

    # 地点信息
    venue_name = Column(String(200), nullable=False, index=True)
    venue_type = Column(String(50), nullable=False, index=True)
    # 类型列表：
    # - cafe: 咖啡厅
    # - restaurant: 餐厅
    # - bar: 酒吧
    # - park: 公园
    # - museum: 博物馆
    # - cinema: 电影院
    # - theater: 剧院
    # - outdoor: 户外场所
    # - activity: 活动场所

    category = Column(String(50), nullable=True)  # 一级分类：餐饮、娱乐、文化、户外等

    # 位置信息
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # 评分和信息
    rating = Column(Float, default=0.0)  # 评分 1-5
    review_count = Column(Integer, default=0)
    price_level = Column(Integer, default=2)  # 1-4（便宜到贵）

    # 特色标签
    tags = Column(Text, default="")  # JSON 字符串
    suitable_for = Column(Text, default="")  # JSON 字符串，适合的场景
    ambiance_tags = Column(Text, default="")  # JSON 字符串，氛围标签（浪漫、安静、热闹等）

    # 营业时间
    opening_hours = Column(Text, default="")  # JSON 字符串
    is_popular = Column(Boolean, default=False)  # 是否热门地点
    reservation_required = Column(Boolean, default=False)  # 是否需要预约

    # 用户评价摘要
    user_review_summary = Column(Text, nullable=True)  # 用户评价摘要
    pros = Column(Text, default="")  # JSON 字符串，优点
    cons = Column(Text, default="")  # JSON 字符串，缺点

    # 来源
    source = Column(String(50), default="manual")  # manual, api, user_contribution
    source_id = Column(String(100), nullable=True)  # 来源平台 ID

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)


# ============= EmotionWeather-003: 恋爱指导服务模型 =============

class LoveGuidanceDB(Base):
    """恋爱指导记录"""
    __tablename__ = "love_guidance"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)  # 相关对象

    # 指导类型
    guidance_type = Column(String(50), nullable=False)
    # 类型列表:
    # - chat_advice: 聊天建议
    # - gift_recommendation: 礼物推荐
    # - conflict_resolution: 冲突解决
    # - relationship_improvement: 关系改善
    # - breakup_recovery: 分手 recovery
    # - proposal_planning: 求婚策划
    # - long_distance_tips: 异地恋建议

    # 指导内容
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    # 详情
    scenario = Column(String(200), nullable=True)  # 适用场景
    step_by_step_guide = Column(Text, default="")  # JSON 字符串，分步指南
    dos_and_donts = Column(Text, default="")  # JSON 字符串，应该做和不应该做的事

    # AI 分析
    reasoning = Column(Text, nullable=True)  # 建议依据
    confidence_score = Column(Float, default=0.5)  # 置信度
    related_resources = Column(Text, default="")  # JSON 字符串，相关资源链接

    # 状态
    status = Column(String(20), default="active")  # active, archived
    is_read = Column(Boolean, default=False)
    is_actioned = Column(Boolean, default=False)  # 用户是否采纳建议

    # 用户反馈
    user_rating = Column(Integer, nullable=True)  # 1-5
    user_feedback = Column(Text, nullable=True)
    outcome_description = Column(Text, nullable=True)  # 实施后的结果描述

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)


class ChatSuggestionDB(Base):
    """聊天建议记录"""
    __tablename__ = "chat_suggestions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(String(36), nullable=True, index=True)  # 相关会话 ID
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 建议类型
    suggestion_type = Column(String(50), nullable=False)
    # 类型列表:
    # - opener: 开场白
    # - topic: 话题建议
    # - response: 回复建议
    # - follow_up: 后续话题
    # - compliment: 赞美话术
    # - comfort: 安慰话术
    # - date_invitation: 约会邀请话术
    # - confession: 表白话术

    # 建议内容
    suggested_text = Column(Text, nullable=False)
    alternative_texts = Column(Text, default="")  # JSON 字符串，备选话术

    # 上下文
    context = Column(String(200), nullable=True)  # 建议的上下文
    trigger_event = Column(String(100), nullable=True)  # 触发事件

    # AI 分析
    reasoning = Column(Text, nullable=True)  # 推荐理由
    tone = Column(String(30), nullable=True)  # 语气：casual, sincere, humorous, romantic 等
    confidence_score = Column(Float, default=0.5)

    # 状态
    status = Column(String(20), default="pending")  # pending, used, ignored
    used_at = Column(DateTime(timezone=True), nullable=True)

    # 用户反馈
    user_rating = Column(Integer, nullable=True)
    modified_text = Column(Text, nullable=True)  # 用户修改后的文本

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class GiftRecommendationDB(Base):
    """礼物推荐记录"""
    __tablename__ = "gift_recommendations"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    recipient_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)  # 收礼人

    # 推荐类型
    occasion = Column(String(50), nullable=False)
    # 场合列表:
    # - birthday: 生日
    # - anniversary: 纪念日
    # - valentines: 情人节
    # - christmas: 圣诞节
    # - just_because: 日常惊喜
    # - apology: 道歉
    # - congratulations: 恭喜
    # - first_date: 首次约会礼物

    # 礼物信息
    gift_name = Column(String(200), nullable=False)
    gift_description = Column(Text, nullable=False)
    gift_category = Column(String(50), nullable=True)  # 礼物类别

    # 价格和购买
    price_range_min = Column(Float, nullable=True)
    price_range_max = Column(Float, nullable=True)
    purchase_links = Column(Text, default="")  # JSON 字符串，购买链接列表
    availability = Column(String(50), default="in_stock")  # in_stock, out_of_stock, custom_made

    # AI 分析
    reasoning = Column(Text, nullable=True)  # 推荐理由
    recipient_match_analysis = Column(Text, default="")  # JSON 字符串，与收礼人兴趣的匹配分析
    confidence_score = Column(Float, default=0.5)
    personalization_tips = Column(Text, default="")  # JSON 字符串，个性化建议

    # 状态
    status = Column(String(20), default="pending")  # pending, purchased, gifted, rejected
    purchased_at = Column(DateTime(timezone=True), nullable=True)
    gifted_at = Column(DateTime(timezone=True), nullable=True)

    # 反馈
    recipient_reaction = Column(String(50), nullable=True)  # 收礼人反应
    user_rating = Column(Integer, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= EmotionWeather-004: 关系健康度分析模型 =============

class RelationshipHealthDB(Base):
    """关系健康度评估记录"""
    __tablename__ = "relationship_health"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 评估维度得分
    communication_score = Column(Float, default=0.0)  # 沟通质量 0-10
    trust_score = Column(Float, default=0.0)  # 信任度 0-10
    intimacy_score = Column(Float, default=0.0)  # 亲密度 0-10
    commitment_score = Column(Float, default=0.0)  # 承诺度 0-10
    compatibility_score = Column(Float, default=0.0)  # 兼容性 0-10

    # 综合得分
    overall_score = Column(Float, default=0.0)  # 综合得分 0-100
    health_level = Column(String(20), default="unknown")  # excellent, good, fair, needs_attention, critical

    # AI 分析
    strengths = Column(Text, default="")  # JSON 字符串，关系优势
    growth_areas = Column(Text, default="")  # JSON 字符串，需要改进的领域
    ai_insights = Column(Text, nullable=True)  # AI 洞察

    # 建议
    suggestions = Column(Text, default="")  # JSON 字符串，改进建议
    recommended_actions = Column(Text, default="")  # JSON 字符串，推荐行动

    # 趋势
    trend = Column(String(20), nullable=True)  # improving, stable, declining
    previous_score = Column(Float, nullable=True)  # 上次评估得分

    # 评估来源
    assessment_source = Column(String(50), default="ai")  # ai, self_assessment, combined

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    assessment_date = Column(DateTime(timezone=True), nullable=True)  # 评估日期


class RelationshipCheckInDB(Base):
    """关系签到记录 - 用户自我评估"""
    __tablename__ = "relationship_checkins"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 签到内容
    mood = Column(String(30), nullable=True)  # 当前心情
    satisfaction_level = Column(Integer, nullable=True)  # 满意度 1-10
    concern_areas = Column(Text, default="")  # JSON 字符串，关注的问题领域

    # 开放式问题
    what_is_going_well = Column(Text, nullable=True)  # 什么进展顺利
    what_needs_improvement = Column(Text, nullable=True)  # 什么需要改进
    how_feeling_connected = Column(Text, nullable=True)  # 如何感受连接

    # AI 反馈
    ai_response = Column(Text, nullable=True)  # AI 生成的反馈
    suggested_actions = Column(Text, default="")  # JSON 字符串，建议行动

    # 隐私设置
    is_shared_with_partner = Column(Boolean, default=False)  # 是否与伴侣分享

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    checkin_date = Column(DateTime(timezone=True), nullable=True)


# ============= EmotionWeather-005: 关系里程碑增强模型 =============

class RelationshipAnniversaryDB(Base):
    """关系纪念日记录"""
    __tablename__ = "relationship_anniversaries"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 纪念日类型
    anniversary_type = Column(String(50), nullable=False)
    # 类型列表:
    # - first_match: 首次匹配纪念日
    # - first_date: 首次约会纪念日
    # - relationship_start: 恋爱纪念日
    # - engagement: 订婚纪念日
    # - marriage: 结婚纪念日
    # - custom: 自定义纪念日

    # 纪念日信息
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    anniversary_date = Column(DateTime(timezone=True), nullable=False)  # 纪念日日期

    #  recurring
    is_recurring = Column(Boolean, default=True)  # 是否每年重复
    recurrence_pattern = Column(String(20), nullable=True)  # yearly, monthly

    # 庆祝历史
    celebration_history = Column(Text, default="")  # JSON 字符串，历史庆祝记录

    # 提醒设置
    reminder_enabled = Column(Boolean, default=True)
    reminder_days_before = Column(Integer, default=7)  # 提前几天提醒

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RelationshipGoalDB(Base):
    """关系目标记录"""
    __tablename__ = "relationship_goals"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 目标信息
    goal_type = Column(String(50), nullable=False)
    # 类型列表:
    # - communication: 沟通目标
    # - quality_time: 相处时间目标
    # - personal_growth: 个人成长目标
    # - relationship_milestone: 关系里程碑目标
    # - financial: 财务目标
    # - future_planning: 未来规划目标

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 目标状态
    status = Column(String(20), default="active")  # active, completed, abandoned
    priority = Column(String(20), default="medium")  # low, medium, high

    # 进度追踪
    target_date = Column(DateTime(timezone=True), nullable=True)
    progress_percentage = Column(Integer, default=0)  # 进度 0-100

    # 步骤
    steps = Column(Text, default="")  # JSON 字符串，目标步骤
    completed_steps = Column(Text, default="")  # JSON 字符串，已完成步骤

    # AI 支持
    ai_suggestions = Column(Text, default="")  # JSON 字符串，AI 建议
    motivation_message = Column(Text, nullable=True)  # AI 生成的激励消息

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


# ============= EmotionWeather-006: 关系分析增强模型 =============

class RelationshipPatternDB(Base):
    """关系模式分析记录"""
    __tablename__ = "relationship_patterns"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 模式类型
    pattern_type = Column(String(50), nullable=False)
    # 类型列表:
    # - communication_pattern: 沟通模式
    # - conflict_pattern: 冲突模式
    # - intimacy_pattern: 亲密模式
    # - activity_pattern: 活动模式

    # 模式描述
    pattern_name = Column(String(100), nullable=False)
    pattern_description = Column(Text, nullable=False)

    # 模式分析
    pattern_data = Column(JSON, nullable=True)  # 模式数据
    frequency = Column(String(50), nullable=True)  # 出现频率
    impact = Column(String(20), nullable=True)  # positive, neutral, negative

    # AI 洞察
    ai_insight = Column(Text, nullable=True)
    improvement_suggestions = Column(Text, default="")  # JSON 字符串，改进建议

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    detected_at = Column(DateTime(timezone=True), nullable=True)


# ============= EmotionWeather-007: 关系通知模型 =============

class RelationshipNotificationDB(Base):
    """关系相关通知"""
    __tablename__ = "relationship_notifications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 通知类型
    notification_type = Column(String(50), nullable=False)
    # 类型列表:
    # - milestone_achieved: 里程碑达成
    # - anniversary_reminder: 纪念日提醒
    # - advice_available: 新建议可用
    # - health_check_reminder: 健康检查提醒
    # - goal_progress: 目标进展
    # - pattern_detected: 模式识别

    # 通知内容
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # 关联数据
    related_entity_type = Column(String(50), nullable=True)  # 关联实体类型
    related_entity_id = Column(String(36), nullable=True)  # 关联实体 ID

    # 状态
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    action_taken = Column(Boolean, default=False)  # 用户是否采取行动

    # 优先级
    priority = Column(String(20), default="normal")  # low, normal, high, urgent

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
