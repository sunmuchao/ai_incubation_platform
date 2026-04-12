"""
Milestone 数据模型定义

关系里程碑追踪增强、约会建议引擎、双人互动游戏
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Table, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base
import enum


# ============= Milestone-001: 关系里程碑追踪增强模型 =============

class RelationshipMilestoneDB(Base):
    """关系里程碑记录 - 增强版"""
    __tablename__ = "relationship_milestones"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 里程碑类型
    milestone_type = Column(String(50), nullable=False, index=True)
    # 类型列表:
    # - first_match: 首次匹配
    # - first_message: 第一条消息
    # - first_like: 第一次点赞
    # - deep_conversation: 深度对话
    # - contact_exchange: 交换联系方式
    # - first_date_proposal: 首次约会提议
    # - first_date_completed: 完成第一次约会
    # - anniversary_1month: 一月纪念日
    # - anniversary_3month: 三月纪念日
    # - anniversary_6month: 六月纪念日
    # - anniversary_1year: 一周年纪念日
    # - relationship_exclusive: 确定排他性关系
    # - meet_parents: 见家长
    # - engagement: 订婚
    # - marriage: 结婚

    # 里程碑详情
    title = Column(String(200), nullable=False)  # 里程碑标题
    description = Column(Text, nullable=False)  # 详细描述
    milestone_date = Column(DateTime(timezone=True), nullable=False)  # 里程碑发生时间

    # 庆祝建议
    celebration_suggested = Column(Boolean, default=False)  # 是否建议庆祝
    celebration_type = Column(String(50), nullable=True)  # 庆祝类型：gift, card, activity, none
    celebration_description = Column(Text, nullable=True)  # 庆祝建议描述

    # AI 分析
    ai_analysis = Column(Text, default="")  # JSON 字符串，AI 对关系的分析
    relationship_stage_at_milestone = Column(String(20), nullable=True)  # 里程碑时的关系阶段

    # 用户反馈
    user_rating = Column(Integer, nullable=True)  # 用户评分 1-5
    user_note = Column(Text, nullable=True)  # 用户备注
    is_private = Column(Boolean, default=False)  # 是否私密里程碑

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RelationshipStageHistoryDB(Base):
    """关系阶段变更历史"""
    __tablename__ = "relationship_stage_history"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 阶段信息
    from_stage = Column(String(20), nullable=True)  # 变更前的阶段
    to_stage = Column(String(20), nullable=False)  # 变更后的阶段
    stage_label = Column(String(50), nullable=False)  # 阶段标签（中文）

    # 变更原因
    change_reason = Column(String(100), nullable=True)  # 变更原因
    trigger_event = Column(String(50), nullable=True)  # 触发事件

    # AI 分析
    ai_comment = Column(Text, nullable=True)  # AI 评论
    next_stage_suggestions = Column(Text, default="")  # JSON 字符串，下一阶段建议

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RelationshipInsightDB(Base):
    """关系洞察 - AI 生成的关系分析"""
    __tablename__ = "relationship_insights"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 洞察类型
    insight_type = Column(String(50), nullable=False)
    # 类型列表:
    # - communication_pattern: 沟通模式分析
    # - compatibility_highlight: 兼容性亮点
    # - growth_area: 成长领域
    # - risk_alert: 风险提醒
    # - celebration_opportunity: 庆祝机会
    # - activity_suggestion: 活动建议

    # 洞察内容
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.5)  # AI 置信度 0-1

    # 行动建议
    action_suggestion = Column(Text, nullable=True)  # 行动建议
    priority = Column(String(20), default="normal")  # low, normal, high, urgent

    # 状态
    is_read_user1 = Column(Boolean, default=False)
    is_read_user2 = Column(Boolean, default=False)
    is_actioned = Column(Boolean, default=False)  # 用户是否采纳建议

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 过期时间


# ============= Milestone-002: 约会建议引擎模型 =============

class DateSuggestionDB(Base):
    """约会建议"""
    __tablename__ = "date_suggestions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 约会对象（可选，用于双人约会建议）
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # 约会类型
    date_type = Column(String(50), nullable=False)
    # 类型列表:
    # - coffee: 咖啡约会
    # - meal: 用餐约会
    # - movie: 电影约会
    # - outdoor: 户外活动
    # - culture: 文化艺术
    # - sports: 运动健身
    # - entertainment: 娱乐活动
    # - creative: 创意体验
    # - travel: 短途旅行

    # 地点信息
    venue_name = Column(String(200), nullable=False)
    venue_type = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # 推荐详情
    recommendation_reason = Column(Text, nullable=False)  # 推荐理由
    estimated_cost = Column(Float, nullable=True)  # 预估费用
    estimated_duration = Column(Integer, nullable=True)  # 预估时长（分钟）
    best_time_suggestion = Column(String(100), nullable=True)  # 最佳时间建议

    # 兼容性分析
    compatibility_analysis = Column(Text, default="")  # JSON 字符串，与双方的兴趣匹配分析
    match_score = Column(Float, default=0.0)  # 匹配置信度 0-1

    # 状态
    status = Column(String(20), default="pending")  # pending, accepted, rejected, expired, completed
    suggested_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)

    # 用户反馈
    user_rating = Column(Integer, nullable=True)  # 1-5
    user_feedback = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DateVenueDB(Base):
    """约会地点数据库"""
    __tablename__ = "date_venues"

    id = Column(String(36), primary_key=True, index=True)

    # 地点信息
    venue_name = Column(String(200), nullable=False, index=True)
    venue_type = Column(String(50), nullable=False, index=True)
    category = Column(String(50), nullable=True)  # 一级分类：餐饮、娱乐、文化、户外等

    # 位置信息
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # 评分和信息
    rating = Column(Float, default=0.0)  # 评分 1-5
    review_count = Column(Integer, default=0)
    price_level = Column(Integer, default=2)  # 1-4（便宜到贵）

    # 特色标签
    tags = Column(Text, default="")  # JSON 字符串
    suitable_for = Column(Text, default="")  # JSON 字符串，适合的场景

    # 营业时间
    opening_hours = Column(Text, default="")  # JSON 字符串
    is_popular = Column(Boolean, default=False)  # 是否热门地点

    # 来源
    source = Column(String(50), default="manual")  # manual, api, user_contribution

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= Milestone-004: 双人互动游戏模型 =============

class CoupleGameDB(Base):
    """双人互动游戏"""
    __tablename__ = "couple_games"

    id = Column(String(36), primary_key=True, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 游戏信息
    game_type = Column(String(50), nullable=False)
    # 游戏类型列表:
    # - qna_mutual: 互相问答
    # - values_quiz: 价值观测试
    # - preference_match: 偏好匹配
    # - personality_quiz: 性格测试
    # - trivia_couple: 情侣知识问答
    # - future_planning: 未来规划游戏
    # - memory_lane: 回忆之旅

    # 游戏状态
    status = Column(String(20), default="pending")  # pending, in_progress, completed, abandoned
    current_round = Column(Integer, default=0)  # 当前轮次
    total_rounds = Column(Integer, default=10)  # 总轮次

    # 游戏配置
    game_config = Column(JSON, nullable=True)  # 游戏配置
    difficulty = Column(String(20), default="normal")  # easy, normal, hard

    # 结果
    result_user1 = Column(Integer, nullable=True)  # 用户 1 得分/结果
    result_user2 = Column(Integer, nullable=True)  # 用户 2 得分/结果
    compatibility_insight = Column(Text, nullable=True)  # 兼容性洞察

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class CoupleGameRoundDB(Base):
    """双人游戏轮次"""
    __tablename__ = "couple_game_rounds"

    id = Column(String(36), primary_key=True, index=True)
    game_id = Column(String(36), ForeignKey("couple_games.id"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)

    # 问题/挑战
    question = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=True)  # 问题类型

    # 用户回答
    answer_user1 = Column(Text, nullable=True)
    answer_user2 = Column(Text, nullable=True)

    # 匹配结果
    is_match = Column(Boolean, nullable=True)  # 是否匹配
    match_percentage = Column(Float, nullable=True)  # 匹配百分比

    # 洞察
    insight = Column(Text, nullable=True)  # AI 生成的洞察

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GameResultInsightDB(Base):
    """游戏结果洞察"""
    __tablename__ = "game_result_insights"

    id = Column(String(36), primary_key=True, index=True)
    game_id = Column(String(36), ForeignKey("couple_games.id"), nullable=False, index=True)
    user_id_1 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 洞察内容
    insight_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    # 兼容性分析
    compatibility_areas = Column(Text, default="")  # JSON 字符串
    strength_areas = Column(Text, default="")  # JSON 字符串
    growth_areas = Column(Text, default="")  # JSON 字符串

    # 建议
    suggestions = Column(Text, default="")  # JSON 字符串

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
