"""
P13 情感调解增强数据库模型

P13 在 P12 基础上增强：
1. 预警分级响应机制
2. 爱之语画像系统
3. 关系趋势预测

包含以下模块：
1. 爱之语画像 - 用户爱之语偏好学习
2. 关系趋势 - 关系发展趋势预测
3. 预警响应 - 分级响应策略
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum
from sqlalchemy.orm import relationship
import enum

from db.database import Base


# ==================== 爱之语画像模块 ====================

class LoveLanguageType(str, enum.Enum):
    """五种爱之语类型"""
    WORDS = "words"  # 肯定的言辞
    TIME = "time"  # 精心时刻
    GIFTS = "gifts"  # 接受礼物
    ACTS = "acts"  # 服务的行动
    TOUCH = "touch"  # 身体的接触


class UserLoveLanguageProfileDB(Base):
    """用户爱之语画像"""
    __tablename__ = "user_love_language_profiles"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    # 主要爱之语类型（得分最高的）
    primary_love_language = Column(String, default=LoveLanguageType.WORDS.value)
    # 次要爱之语类型
    secondary_love_language = Column(String)

    # 各维度得分 (0-100)
    words_score = Column(Integer, default=0)
    time_score = Column(Integer, default=0)
    gifts_score = Column(Integer, default=0)
    acts_score = Column(Integer, default=0)
    touch_score = Column(Integer, default=0)

    # 总测试次数
    assessment_count = Column(Integer, default=0)

    # 爱之语表达偏好（如何表达爱）
    expression_preferences = Column(JSON, default=list)
    # 爱之语接收偏好（希望如何被爱）
    reception_preferences = Column(JSON, default=list)

    # 历史翻译记录 ID 列表（用于学习）
    translation_history_ids = Column(JSON, default=list)

    # 置信度（基于数据量）
    confidence_score = Column(Float, default=0.0)

    # 最后更新时间
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 关系趋势预测模块 ====================

class RelationshipTrendPredictionDB(Base):
    """关系趋势预测记录"""
    __tablename__ = "relationship_trend_predictions"

    id = Column(String, primary_key=True)
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 预测基准日期
    prediction_base_date = Column(DateTime, nullable=False)
    # 预测周期
    prediction_period = Column(String, nullable=False)  # 7d, 14d, 30d

    # 当前情感温度
    current_temperature = Column(Float, nullable=False)
    # 预测情感温度
    predicted_temperature = Column(Float)
    # 温度变化趋势
    temperature_trend = Column(String)  # rising, stable, declining

    # 关系发展阶段
    current_stage = Column(String)  # matched, chatting, dating, in_relationship
    predicted_stage = Column(String)
    stage_change_probability = Column(Float, default=0.0)

    # 风险指标
    risk_indicators = Column(JSON)  # 可能导致关系恶化的因素
    opportunity_indicators = Column(JSON)  # 可能促进关系发展的因素

    # 关键事件预测
    predicted_milestones = Column(JSON)  # 可能达到的里程碑

    # 建议行动
    recommended_actions = Column(JSON)

    # 预测准确性（事后评估）
    prediction_accuracy = Column(Float)
    actual_outcome = Column(JSON)  # 实际结果

    # 预测模型版本
    model_version = Column(String, default="v1.0")

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # 预测过期时间


# ==================== 预警分级响应模块 ====================

class WarningResponseType(str, enum.Enum):
    """预警响应类型"""
    PRIVATE_SUGGESTION = "private_suggestion"  # 私下建议
    COOLING_TECHNIQUE = "cooling_technique"  # 冷静技巧
    COMMUNICATION_GUIDE = "communication_guide"  # 沟通指导
    PROFESSIONAL_HELP = "professional_help"  # 专业帮助
    EMERGENCY_INTERVENTION = "emergency_intervention"  # 紧急干预


class WarningResponseStrategyDB(Base):
    """预警响应策略库"""
    __tablename__ = "warning_response_strategies"

    id = Column(String, primary_key=True)

    # 适用的预警级别
    warning_level = Column(String, nullable=False)  # low, medium, high, critical

    # 响应类型
    response_type = Column(String, nullable=False)

    # 触发条件
    trigger_conditions = Column(JSON)  # 在什么情况下使用此策略

    # 响应内容模板
    response_template = Column(Text, nullable=False)

    # 预期效果
    expected_effect = Column(String)

    # 使用指南
    usage_guide = Column(Text)

    # 使用次数统计
    usage_count = Column(Integer, default=0)

    # 有效性评分
    effectiveness_rating = Column(Float, default=0.0)

    # 适用场景标签
    applicable_scenarios = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WarningResponseRecordDB(Base):
    """预警响应记录"""
    __tablename__ = "warning_response_records"

    id = Column(String, primary_key=True)

    # 关联的预警 ID
    warning_id = Column(String, ForeignKey("emotion_warnings.id"), nullable=False)

    # 使用的策略 ID
    strategy_id = Column(String, ForeignKey("warning_response_strategies.id"))

    # 响应类型
    response_type = Column(String, nullable=False)

    # 实际发送的内容
    response_content = Column(Text, nullable=False)

    # 接收者 ID
    recipient_user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 接收方式
    delivery_method = Column(String)  # push_notification, in_app_message, email

    # 是否已读
    is_acknowledged = Column(Boolean, default=False)

    # 用户反馈
    user_feedback = Column(String)  # helpful, neutral, unhelpful

    # 响应后的情绪变化
    emotion_change = Column(Float)  # 情绪改善/恶化程度

    # 关系改善程度
    relationship_improvement = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== 情感调解增强统计模块 ====================

class EmotionMediationStatsDB(Base):
    """情感调解统计数据"""
    __tablename__ = "emotion_mediation_stats"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 统计周期
    stat_period = Column(String, nullable=False)  # daily, weekly, monthly

    # 统计日期
    stat_date = Column(DateTime, nullable=False)

    # 预警次数统计
    warning_count = Column(Integer, default=0)
    warning_by_level = Column(JSON)  # {low: 5, medium: 3, high: 1, critical: 0}

    # 翻译次数统计
    translation_count = Column(Integer, default=0)
    translation_accuracy_rate = Column(Float, default=0.0)  # 翻译准确率

    # 气象报告次数
    weather_report_count = Column(Integer, default=0)

    # 平均情感温度
    avg_emotional_temperature = Column(Float, default=50.0)

    # 情感温度变化
    temperature_change = Column(Float, default=0.0)

    # 响应策略使用统计
    response_strategy_usage = Column(JSON)

    # 用户满意度
    user_satisfaction = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
