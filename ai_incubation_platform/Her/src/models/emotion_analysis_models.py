"""
Emotion 感官洞察数据模型定义

包含：
1. AI 视频面诊（情感翻译官）- 微表情捕捉、语音情感分析、情感报告生成
2. 物理安全守护神 - 位置安全监测、语音异常检测、分级响应机制
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base
import enum


# ============= Emotion-001: AI 视频面诊/情感分析模型 =============

class EmotionAnalysisDB(Base):
    """情感分析记录 - AI 视频面诊核心数据"""
    __tablename__ = "emotion_analyses"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 会话信息
    session_id = Column(String(36), nullable=False, index=True)
    session_type = Column(String(50), nullable=False)  # video_interview, date_review, check_in

    # 分析类型
    analysis_type = Column(String(50), nullable=False)
    # 类型列表:
    # - micro_expression: 微表情分析
    # - voice_emotion: 语音情感分析
    # - combined_analysis: 综合分析

    # 微表情数据
    micro_expressions = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "detected_emotions": [
    #         {"emotion": "happiness", "confidence": 0.85, "duration_ms": 320},
    #         {"emotion": "nervousness", "confidence": 0.72, "duration_ms": 150}
    #     ],
    #     "facial_action_units": [1, 2, 12, 25],  # FACS 编码
    #     "dominant_emotion": "happiness",
    #     "emotional_intensity": 0.78,
    #     "authenticity_score": 0.92  # 真实性评分
    # }

    # 语音情感数据
    voice_emotions = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "detected_emotions": [
    #         {"emotion": "excitement", "confidence": 0.88},
    #         {"emotion": "confidence", "confidence": 0.65}
    #     ],
    #     "voice_features": {
    #         "pitch_avg": 220.5,
    #         "pitch_variance": 45.2,
    #         "speech_rate": 4.2,  # 字/秒
    #         "pause_frequency": 0.15,  # 停顿频率
    #         "volume_variance": 12.3
    #     },
    #     "dominant_emotion": "excitement",
    #     "emotional_stability": 0.75
    # }

    # 综合分析结果
    combined_emotion = Column(String(50), nullable=True)  # 主导情感
    emotion_confidence = Column(Float, default=0.0)  # 置信度 0-1
    emotional_state_summary = Column(Text, nullable=True)  # 情感状态总结（自然语言）

    # 真实性检测
    authenticity_score = Column(Float, default=0.5)  # 真实性评分 0-1
    inconsistency_flags = Column(JSON, nullable=True)  # 不一致标记
    # 格式：
    # [
    #     {"type": "voice_face_mismatch", "description": "语音和面部表情不一致", "severity": "low"}
    # ]

    # AI 洞察
    ai_insights = Column(Text, nullable=True)  # JSON 字符串，AI 生成的洞察
    emotional_intelligence_tips = Column(Text, nullable=True)  # 情商建议

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed_at = Column(DateTime(timezone=True), nullable=True)


class EmotionReportDB(Base):
    """情感报告 - 生成的情感分析报告"""
    __tablename__ = "emotion_reports"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)

    # 报告类型
    report_type = Column(String(50), nullable=False)
    # 类型列表:
    # - session_summary: 会话总结
    # - emotional_pattern: 情感模式分析
    # - compatibility_indicator: 兼容性指标
    # - growth_suggestion: 成长建议

    # 报告内容
    title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=False)  # 报告摘要
    detailed_analysis = Column(Text, nullable=True)  # 详细分析（JSON 字符串）
    # 格式：
    # {
    #     "emotional_patterns": [...],
    #     "strengths": [...],
    #     "areas_for_improvement": [...],
    #     "recommendations": [...]
    # }

    # 情感指标
    emotional_metrics = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "overall_positivity": 0.75,
    #     "emotional_stability": 0.68,
    #     "authenticity": 0.92,
    #     "engagement_level": 0.85,
    #     "comfort_level": 0.70
    # }

    # 可视化数据
    visualization_data = Column(JSON, nullable=True)  # 用于前端可视化的数据

    # 行动建议
    action_items = Column(Text, nullable=True)  # JSON 字符串，行动建议列表

    # 状态
    is_private = Column(Boolean, default=True)  # 是否私密报告
    shared_with = Column(String(36), nullable=True)  # 可选：分享给谁（约会对象）

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)


class EmotionalTrendDB(Base):
    """情感趋势 - 用户情感变化趋势"""
    __tablename__ = "emotional_trends"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 时间周期
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # 趋势数据
    trend_data = Column(JSON, nullable=False)
    # 格式：
    # {
    #     "daily_emotions": [
    #         {"date": "2024-01-01", "dominant_emotion": "happy", "intensity": 0.8},
    #         ...
    #     ],
    #     "emotion_distribution": {
    #         "happiness": 0.35,
    #         "excitement": 0.25,
    #         "nervousness": 0.20,
    #         "sadness": 0.10,
    #         "anger": 0.05,
    #         "fear": 0.05
    #     },
    #     "trend_direction": "improving",  # improving, stable, declining
    #     "notable_changes": [...]
    # }

    # 模式识别
    identified_patterns = Column(JSON, nullable=True)
    # 格式：
    # [
    #     {"pattern": "weekday_blues", "confidence": 0.75, "description": "工作日情绪较低"},
    #     {"pattern": "date_excitement", "confidence": 0.90, "description": "约会前后情绪高涨"}
    # ]

    # AI 洞察
    ai_summary = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============= Emotion-002: 物理安全守护神模型 =============

class SafetyCheckDB(Base):
    """安全检查记录 - 位置/语音安全监测"""
    __tablename__ = "safety_checks"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 会话/约会信息
    session_id = Column(String(36), nullable=True, index=True)
    session_type = Column(String(50), nullable=True)  # date, meetup, video_call
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # 检查类型
    check_type = Column(String(50), nullable=False)
    # 类型列表:
    # - location_safety: 位置安全检查
    # - voice_anomaly: 语音异常检测
    # - scheduled_checkin: 定时签到
    # - emergency_check: 紧急检查

    # 位置数据
    location_data = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "latitude": 39.9042,
    #     "longitude": 116.4074,
    #     "accuracy_meters": 10,
    #     "address": "北京市朝阳区 xxx",
    #     "venue_type": "restaurant",
    #     "is_public_place": true,
    #     "safety_score": 0.85,
    #     "nearby_safe_zones": ["police_station", "hospital"],
    #     "time_at_location_minutes": 45
    # }

    # 语音数据
    voice_data = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "anomaly_detected": false,
    #     "stress_level": 0.3,
    #     "distress_keywords": [],
    #     "background_noise_level": "normal",
    #     "voice_analysis": {
    #         "pitch_elevated": false,
    #         "speech_pattern": "normal",
    #         "interruption_detected": false
    #     }
    # }

    # 风险评估
    risk_level = Column(String(20), default="low")  # low, medium, high, critical
    risk_score = Column(Float, default=0.0)  # 风险评分 0-1
    risk_factors = Column(JSON, nullable=True)
    # 格式：
    # [
    #     {"factor": "isolated_location", "severity": "medium", "description": "位置偏僻"},
    #     {"factor": "voice_stress", "severity": "low", "description": "语音压力升高"}
    # ]

    # 检查结果
    check_status = Column(String(20), default="completed")  # pending, completed, alert_triggered, failed
    check_result = Column(Text, nullable=True)  # 检查结果总结

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    checked_at = Column(DateTime(timezone=True), nullable=True)


class SafetyAlertDB(Base):
    """安全警报 - 分级响应机制"""
    __tablename__ = "safety_alerts"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 关联记录
    safety_check_id = Column(String(36), ForeignKey("safety_checks.id"), nullable=True)
    session_id = Column(String(36), nullable=True)

    # 警报级别
    alert_level = Column(String(20), nullable=False)
    # 级别列表:
    # - info: 信息提示
    # - warning: 警告
    # - urgent: 紧急
    # - critical: 严重

    # 警报内容
    alert_type = Column(String(50), nullable=False)
    # 类型列表:
    # - location_deviation: 位置偏离
    # - voice_distress: 语音求救
    # - missed_checkin: 错过签到
    # - high_risk_detected: 高风险检测
    # - emergency_button: 紧急按钮

    alert_title = Column(String(200), nullable=False)
    alert_message = Column(Text, nullable=False)

    # 风险详情
    risk_details = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "triggered_factors": [...],
    #     "current_location": {...},
    #     "last_voice_analysis": {...},
    #     "time_since_last_contact_minutes": 30
    # }

    # 响应状态
    response_status = Column(String(20), default="pending")  # pending, acknowledged, in_progress, resolved, false_alarm
    response_actions = Column(JSON, nullable=True)
    # 格式：
    # [
    #     {"action": "notify_emergency_contact", "timestamp": "...", "status": "completed"},
    #     {"action": "alert_platform_moderator", "timestamp": "...", "status": "completed"},
    #     {"action": "contact_local_authorities", "timestamp": "...", "status": "pending"}
    # ]

    # 紧急联系人
    emergency_contact_notified = Column(Boolean, default=False)
    emergency_contact_response = Column(Text, nullable=True)

    # 解决信息
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(36), nullable=True)  # user_id of resolver
    resolution_notes = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)


class SafetyPlanDB(Base):
    """安全计划 - 用户预设的安全配置"""
    __tablename__ = "safety_plans"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 紧急联系人
    emergency_contacts = Column(JSON, nullable=True)
    # 格式：
    # [
    #     {
    #         "name": "张三",
    #         "relationship": "friend",
    #         "phone": "138****1234",
    #         "priority": 1,
    #         "notify_on_alert_levels": ["urgent", "critical"]
    #     }
    # ]

    # 安全偏好
    safety_preferences = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "auto_check_in_interval_minutes": 30,
    #     "missed_checkin_alert_after_minutes": 10,
    #     "location_tracking_enabled": true,
    #     "voice_monitoring_enabled": true,
    #     "alert_threshold": "medium",  # low, medium, high
    #     "auto_notify_emergency_contact": true,
    #     "share_location_with_date": true,
    #     "safe_word": "暗号词汇"
    # }

    # 医疗信息
    medical_info = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "blood_type": "A",
    #     "allergies": ["penicillin"],
    #     "medical_conditions": ["asthma"],
    #     "emergency_medication": "inhaler"
    # }

    # 信任区域
    safe_zones = Column(JSON, nullable=True)
    # 格式：
    # [
    #     {"name": "家", "latitude": 39.9042, "longitude": 116.4074, "radius_meters": 100},
    #     {"name": "公司", "latitude": 39.9052, "longitude": 116.4084, "radius_meters": 200}
    # ]

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DateSafetySessionDB(Base):
    """约会安全会话 - 单次约会的安全追踪"""
    __tablename__ = "date_safety_sessions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # 约会信息
    date_id = Column(String(36), nullable=True)  # 关联约会 ID
    date_type = Column(String(50), nullable=True)  # online, in_person

    # 会话状态
    session_status = Column(String(20), default="scheduled")  # scheduled, active, completed, aborted

    # 时间信息
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)

    # 位置追踪
    location_sharing_enabled = Column(Boolean, default=False)
    location_updates = Column(JSON, nullable=True)
    # 格式：
    # [
    #     {"timestamp": "...", "latitude": 39.9042, "longitude": 116.4074, "accuracy": 10}
    # ]

    # 签到记录
    checkins = Column(JSON, nullable=True)
    # 格式：
    # [
    #     {"timestamp": "...", "status": "ok", "note": "一切正常"},
    #     {"timestamp": "...", "status": "concern", "note": "感觉不太舒服"}
    # ]

    # 安全状态
    current_risk_level = Column(String(20), default="low")
    alerts_triggered = Column(Integer, default=0)

    # 事后反馈
    post_date_feedback = Column(Text, nullable=True)
    safety_rating = Column(Integer, nullable=True)  # 1-5
    would_recommend_venue = Column(Boolean, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============= Emotion-003: 感官洞察综合分析模型 =============

class SensoryInsightDB(Base):
    """感官洞察 - 综合分析结果"""
    __tablename__ = "sensory_insights"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    partner_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # 会话信息
    session_id = Column(String(36), nullable=False, index=True)
    session_type = Column(String(50), nullable=False)  # video_interview, date, review

    # 洞察类型
    insight_type = Column(String(50), nullable=False)
    # 类型列表:
    # - emotional_compatibility: 情感兼容性
    # - communication_style: 沟通风格
    # - stress_response: 压力反应
    # - authenticity_assessment: 真实性评估
    # - attraction_indicators: 吸引力指标

    # 分析结果
    insight_data = Column(JSON, nullable=False)
    # 格式根据类型而定

    # 置信度
    confidence_score = Column(Float, default=0.5)

    # 建议
    recommendations = Column(Text, nullable=True)  # JSON 字符串

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MicroExpressionPatternDB(Base):
    """微表情模式 - 用户微表情习惯分析"""
    __tablename__ = "micro_expression_patterns"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 基础情绪表达
    base_emotions = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "happiness_threshold": 0.6,  # 触发 happiness 标签的阈值
    #     "typical_expressions": ["genuine_smile", "eye_contact"],
    #     "suppression_tendency": 0.3,  # 抑制情绪表达的倾向
    #     "leakage_rate": 0.15  # 情绪泄露率
    # }

    # 情境反应模式
    contextual_patterns = Column(JSON, nullable=True)
    # 格式：
    # [
    #     {
    #         "context": "compliment_received",
    #         "typical_reaction": "genuine_smile_with_blush",
    #         "confidence": 0.85
    #     }
    # ]

    # 真实性指标
    authenticity_metrics = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "congruence_score": 0.92,  # 表里一致性
    #     "spontaneity_score": 0.88,  # 自发性
    #     "consistency_score": 0.95  # 跨情境一致性
    # }

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VoicePatternDB(Base):
    """语音模式 - 用户语音特征分析"""
    __tablename__ = "voice_patterns"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 基础语音特征
    voice_profile = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "pitch_range": {"min": 150, "max": 300, "avg": 220},
    #     "speech_rate_avg": 4.2,
    #     "articulation_clarity": 0.85,
    #     "voice_quality": "warm",
    #     "typical_volume": "moderate"
    # }

    # 情感语音模式
    emotional_voice_patterns = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "when_nervous": {"pitch_increase": 15, "speech_rate_increase": 20},
    #     "when_excited": {"pitch_increase": 25, "volume_increase": 30},
    #     "when_sad": {"pitch_decrease": 10, "speech_rate_decrease": 15}
    # }

    # 压力指标
    stress_indicators = Column(JSON, nullable=True)
    # 格式：
    # {
    #     "baseline_stress_level": 0.3,
    #     "stress_threshold": 0.6,
    #     "recovery_time_avg_minutes": 15
    # }

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
