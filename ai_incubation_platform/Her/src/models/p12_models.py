"""
P12 行为实验室数据库模型

包含以下模块：
1. 时机感知破冰 - 共同经历检测、尴尬沉默识别、情境话题生成
2. 情感调解 - 吵架预警、爱之语翻译、关系气象报告
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from db.database import Base


# ==================== 时机感知破冰模块 ====================

class SharedExperienceDB(Base):
    """共同经历记录"""
    __tablename__ = "shared_experiences"

    id = Column(String, primary_key=True)
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 经历类型
    experience_type = Column(String, nullable=False)  # conversation, activity, location, event
    # 经历描述
    description = Column(Text)
    # 时间窗口
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    # 地点（可选）
    location = Column(String)
    # 相关数据（如对话 ID、活动 ID 等）
    reference_data = Column(JSON)
    # 情感评分
    sentiment_score = Column(Float, default=0.0)
    # 是否被标记为重要
    is_significant = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class SilenceEventDB(Base):
    """沉默/冷场事件记录"""
    __tablename__ = "silence_events"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 沉默持续时间（秒）
    duration_seconds = Column(Integer, nullable=False)
    # 沉默前的最后一条消息时间
    last_message_time = Column(DateTime, nullable=False)
    # 沉默类型
    silence_type = Column(String)  # awkward, comfortable, waiting_response
    # 上下文摘要
    context_summary = Column(Text)
    # AI 生成的破冰建议
    icebreaker_suggestions = Column(JSON)
    # 是否已处理
    is_resolved = Column(Boolean, default=False)
    # 解决方式
    resolution_method = Column(String)  # ai_suggestion, natural_resume, user_action

    created_at = Column(DateTime, default=datetime.utcnow)


class IcebreakerTopicDB(Base):
    """情境话题库"""
    __tablename__ = "icebreaker_topics"

    id = Column(String, primary_key=True)

    # 话题分类
    category = Column(String, nullable=False)  # shared_experience, current_event, interest_based, seasonal
    # 话题内容
    topic_text = Column(Text, nullable=False)
    # 适用场景标签
    applicable_scenarios = Column(JSON)  # ["first_date", "long_silence", "morning_greeting"]
    # 关联的共同经历类型
    required_experience_type = Column(String)
    # 话题深度等级（1-5）
    depth_level = Column(Integer, default=1)
    # 使用次数统计
    usage_count = Column(Integer, default=0)
    # 成功率（用户接受并继续对话的比例）
    success_rate = Column(Float, default=0.0)
    # 平均回应长度
    avg_response_length = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeneratedIcebreakerDB(Base):
    """AI 生成的破冰话题实例"""
    __tablename__ = "generated_icebreakers"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)

    # 生成的话题
    topic_text = Column(Text, nullable=False)
    # 话题来源
    source_topic_id = Column(String, ForeignKey("icebreaker_topics.id"))
    # 生成依据（共同经历 ID 列表）
    based_on_experience_ids = Column(JSON)
    # 推荐理由
    recommendation_reason = Column(Text)
    # 推荐时机
    recommended_at = Column(DateTime, default=datetime.utcnow)
    # 是否被使用
    is_used = Column(Boolean, default=False)
    # 使用后的效果评分
    effectiveness_score = Column(Float)
    # 对方的回应摘要
    response_summary = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 情感调解模块 ====================

class EmotionWarningDB(Base):
    """情感预警记录（吵架预警）"""
    __tablename__ = "emotion_warnings"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 预警级别
    warning_level = Column(String, nullable=False)  # low, medium, high, critical
    # 触发原因
    trigger_reason = Column(String, nullable=False)
    # 检测到的情绪
    detected_emotions = Column(JSON)
    # 情绪强度（0-1）
    emotion_intensity = Column(Float, default=0.0)
    # 升级风险评分（0-100）
    escalation_risk_score = Column(Float, default=0.0)
    # AI 建议的冷静锦囊
    calming_suggestions = Column(JSON)
    # 是否已读
    is_acknowledged = Column(Boolean, default=False)
    # 是否已解决
    is_resolved = Column(Boolean, default=False)
    # 解决后的关系状态改善
    relationship_improvement = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)


class LoveLanguageTranslationDB(Base):
    """爱之语翻译记录"""
    __tablename__ = "love_language_translations"

    id = Column(String, primary_key=True)

    # 用户 ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    # 目标用户 ID（接收方）
    target_user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 原始表达
    original_expression = Column(Text, nullable=False)
    # 原始表达的情感分析
    original_sentiment = Column(JSON)
    # AI 解读的真实意图
    true_intention = Column(Text, nullable=False)
    # 建议的回应方式
    suggested_response = Column(Text)
    # 回应方式说明
    response_explanation = Column(Text)
    # 双方爱之语类型
    user_love_language = Column(String)  # words, gifts, acts, time, touch
    target_love_language = Column(String)
    # 翻译置信度
    confidence_score = Column(Float, default=0.0)
    # 用户反馈（是否认同 AI 解读）
    user_feedback = Column(String)  # accurate, partially_accurate, inaccurate

    created_at = Column(DateTime, default=datetime.utcnow)


class RelationshipWeatherReportDB(Base):
    """关系气象报告"""
    __tablename__ = "relationship_weather_reports"

    id = Column(String, primary_key=True)
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 报告周期
    report_period = Column(String, nullable=False)  # daily, weekly, monthly
    # 报告日期
    report_date = Column(DateTime, nullable=False)

    # 情感温度（0-100）
    emotional_temperature = Column(Float, nullable=False)
    # 关系天气描述
    weather_description = Column(String, nullable=False)  # sunny, cloudy, rainy, stormy, partly_cloudy
    # 本周亮点
    highlights = Column(JSON)
    # 需要关注的领域
    areas_of_concern = Column(JSON)
    # 冲突热点图数据
    conflict_heatmap = Column(JSON)
    # 情感温度曲线数据
    temperature_curve = Column(JSON)
    # AI 总结和建议
    ai_summary = Column(Text)
    # 行动建议
    action_suggestions = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)


class CalmingKitDB(Base):
    """冷静锦囊库"""
    __tablename__ = "calming_kits"

    id = Column(String, primary_key=True)

    # 锦囊类型
    kit_type = Column(String, nullable=False)  # breathing, reframing, timeout, empathy, appreciation
    # 适用场景
    applicable_scenarios = Column(JSON)
    # 锦囊内容
    content = Column(Text, nullable=False)
    # 预期效果
    expected_effect = Column(String)
    # 使用指南
    usage_guide = Column(Text)
    # 使用次数
    usage_count = Column(Integer, default=0)
    # 有效性评分（用户反馈）
    effectiveness_rating = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
