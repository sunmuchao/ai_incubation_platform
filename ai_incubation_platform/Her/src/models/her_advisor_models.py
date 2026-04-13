"""
Her 顾问系统数据模型

双向动态画像 + 认知偏差分析 + 匹配建议

核心设计：
- SelfProfile: 这个用户是什么样的（别人匹配你时使用）
- DesireProfile: 这个用户想要什么（给你推荐对象时使用）
- CognitiveBiasAnalysis: 认知偏差分析结果（LLM自主判断）
- MatchAdvice: Her 专业匹配建议

架构说明（v2.0）：
- 单一数据源：画像数据存储在 UserDB，无需 UserProfileDB
- UserDB.self_profile_json 存储动态画像
- UserDB.desire_profile_json 存储偏好画像
- 基础信息（age, gender, location 等）直接从 UserDB 字段读取
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base


class UserProfileDB(Base):
    """
    [DEPRECATED] 用户完整画像 - 已合并到 UserDB

    新架构使用 UserDB 存储：
    - UserDB.self_profile_json: 动态画像
    - UserDB.desire_profile_json: 偏好画像

    此表仅用于历史数据迁移，请勿在新代码中使用
    """
    __tablename__ = "user_profiles"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False, index=True)

    self_profile_json = Column(Text, nullable=False, default="{}")
    desire_profile_json = Column(Text, nullable=False, default="{}")

    self_profile_confidence = Column(Float, default=0.0)
    desire_profile_confidence = Column(Float, default=0.0)
    self_profile_completeness = Column(Float, default=0.0)
    desire_profile_completeness = Column(Float, default=0.0)

    profile_version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_behavior_analysis_at = Column(DateTime(timezone=True), nullable=True)
    last_conversation_analysis_at = Column(DateTime(timezone=True), nullable=True)


class ProfileUpdateHistoryDB(Base):
    """
    [DEPRECATED] 画像更新历史记录

    新架构不再单独记录更新历史，此表保留用于历史数据迁移
    """
    __tablename__ = "profile_update_history"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    profile_type = Column(String(20), nullable=False, index=True)
    dimension = Column(String(50), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=False)
    update_source = Column(String(50), nullable=False, index=True)
    # 来源类型：
    # - behavior_event: 行为事件触发
    # - conversation_analysis: 对话分析推断
    # - match_feedback: 匹配反馈学习
    # - received_feedback: 收到的别人反馈
    # - manual_update: 用户手动更新
    # - her_inference: Her 自主推断

    # ===== 关联事件 =====
    related_event_id = Column(String(36), nullable=True)

    # ===== 置信度 =====
    update_confidence = Column(Float, default=1.0)

    # ===== 时间戳 =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CognitiveBiasAnalysisDB(Base):
    """认知偏差分析记录 - Her 自主判断结果"""
    __tablename__ = "cognitive_bias_analyses"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # ===== 分析结果 =====
    has_bias = Column(Boolean, default=False, index=True)
    bias_type = Column(String(100), nullable=True)
    # 常见偏差类型：
    # - double_dominant: 双强势偏差
    # - double_introvert: 双内向偏差
    # - attachment_mismatch: 依恋错配
    # - need_mismatch: 需求错配
    # - control_vs_independent: 控制-独立冲突

    bias_description = Column(Text, nullable=True)
    # Her 的心理学解释

    # ===== Her 建议 =====
    actual_suitable_type = Column(Text, nullable=True)
    # 用户实际适合的类型描述

    potential_risks = Column(Text, nullable=True)
    # JSON 数组：如果坚持当前偏好可能遇到的问题

    adjustment_suggestion = Column(Text, nullable=True)
    # Her 的调整建议

    # ===== 分析置信度 =====
    confidence = Column(Float, default=0.0)

    # ===== LLM 信息 =====
    llm_model = Column(String(100), nullable=True)
    llm_tokens_used = Column(Integer, nullable=True)

    # ===== 时间戳 =====
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    profile_snapshot = Column(Text, nullable=True)
    # 分析时的画像快照（用于对比）

    # ===== 是否有效 =====
    is_valid = Column(Boolean, default=True)
    # 用户画像更新后，此分析可能过期


class MatchAdviceDB(Base):
    """匹配建议记录 - Her 专业判断"""
    __tablename__ = "match_advices"

    id = Column(String(36), primary_key=True)

    # ===== 匹配双方 =====
    user_id_a = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    user_id_b = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # ===== 意向匹配状态 =====
    intent_match_status = Column(String(50), nullable=False)
    # 状态类型：
    # - bidirectional_match: 双向意向匹配
    # - unidirectional_match: 单向意向匹配
    # - no_intent_match: 意向不匹配

    # ===== 认知偏差关联 =====
    user_a_bias_id = Column(String(36), nullable=True)
    user_b_bias_id = Column(String(36), nullable=True)

    # ===== 适配度分析 =====
    compatibility_score = Column(Float, default=0.0)
    compatibility_analysis_json = Column(Text, nullable=True)
    # JSON 结构：
    # {
    #     "value_alignment": {},
    #     "communication_compatibility": {},
    #     "emotional_compatibility": {},
    #     "power_dynamic_match": {},
    # }

    # ===== Her 建议类型 =====
    advice_type = Column(String(50), nullable=False, index=True)
    # 建议类型：
    # - strongly_recommend: 强烈推荐
    # - recommend_with_caution: 谨慎推荐
    # - not_recommended: 不推荐
    # - suggest_adjustment: 建议调整期待
    # - potential_but_needs_work: 有潜力但需要努力

    # ===== Her 建议内容 =====
    advice_content = Column(Text, nullable=False)
    # Her 的专业建议文本

    reasoning = Column(Text, nullable=True)
    # Her 的分析推理过程

    suggestions_for_a = Column(Text, nullable=True)
    # JSON 数组：给用户A的建议

    suggestions_for_b = Column(Text, nullable=True)
    # JSON 数组：给用户B的建议

    potential_issues = Column(Text, nullable=True)
    # JSON 数组：潜在问题列表

    # ===== 时间戳 =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserBehaviorEventDB(Base):
    """用户行为事件（增强版）- 用于画像更新"""
    __tablename__ = "user_behavior_events_v2"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # ===== 事件类型 =====
    event_type = Column(String(50), nullable=False, index=True)
    # 事件类型扩展：
    #
    # SelfProfile 相关事件：
    # - message_sent: 发送消息
    # - response_time: 响应时间
    # - emoji_usage: 表情使用
    # - topic_initiation: 主动发起话题
    # - conflict_handling: 冲突处理方式
    # - received_feedback: 收到的反馈
    # - received_like: 收到的喜欢
    #
    # DesireProfile 相关事件：
    # - search_query: 搜索查询
    # - profile_view: 查看某人资料
    # - swipe_like: 滑动喜欢
    # - swipe_pass: 滑动跳过
    # - match_like: 喜欢匹配
    # - match_dislike: 不喜欢匹配
    # - match_skip: 跳过匹配
    # - conversation_topic: 对话话题偏好

    # ===== 事件目标 =====
    target_user_id = Column(String(36), nullable=True, index=True)

    # ===== 事件详情 =====
    event_data = Column(JSON, nullable=True)
    # 结构化事件数据，不同事件类型有不同结构

    # ===== 事件置信度 =====
    event_confidence = Column(Float, default=1.0)
    # 此事件对画像推断的置信度

    # ===== 是否已处理 =====
    is_processed = Column(Boolean, default=False, index=True)
    # 是否已用于画像更新

    # ===== 时间戳 =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class ConversationPreferenceInferenceDB(Base):
    """对话偏好推断记录"""
    __tablename__ = "conversation_preference_inferences"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # ===== 推断来源 =====
    conversation_id = Column(String(36), nullable=True, index=True)
    message_snippet = Column(Text, nullable=True)
    # 原始消息片段（脱敏）

    # ===== 推断结果 =====
    stated_preference = Column(Text, nullable=True)
    # 用户自称想要的类型

    inferred_preference = Column(Text, nullable=True)
    # Her 从对话推断的实际偏好

    preference_dimensions = Column(Text, nullable=True)
    # JSON 结构：推断的各维度偏好
    # {
    #     "personality_type": "温和型",
    #     "emotional_needs": "需要被理解",
    #     "communication_style": "直接表达",
    #     "lifestyle": "户外活动",
    # }

    # ===== 置信度 =====
    inference_confidence = Column(Float, default=0.0)

    # ===== LLM 信息 =====
    llm_model = Column(String(100), nullable=True)

    # ===== 是否已应用 =====
    is_applied = Column(Boolean, default=False)

    # ===== 时间戳 =====
    inferred_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)


class HerKnowledgeCaseDB(Base):
    """Her 知识库案例 - 典型匹配案例"""
    __tablename__ = "her_knowledge_cases"

    id = Column(String(36), primary_key=True)

    # ===== 案例类型 =====
    case_type = Column(String(50), nullable=False, index=True)
    # success_case: 成功案例
    # warning_case: 警示案例
    # typical_pattern: 典型模式

    # ===== 案例标签 =====
    tags = Column(Text, nullable=True)
    # JSON 数组：["双强势", "冲突", "需要妥协"]

    # ===== 案例描述 =====
    case_description = Column(Text, nullable=False)
    # 案例情境描述

    # ===== Her 分析 =====
    her_analysis = Column(Text, nullable=False)
    # Her 的专业分析

    # ===== Her 建议 =====
    her_suggestion = Column(Text, nullable=False)
    # Her 的建议

    # ===== 关键洞察 =====
    key_insights = Column(Text, nullable=True)
    # JSON 数组：关键洞察点

    # ===== 使用统计 =====
    usage_count = Column(Integer, default=0)
    effectiveness_score = Column(Float, default=0.0)

    # ===== 时间戳 =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)