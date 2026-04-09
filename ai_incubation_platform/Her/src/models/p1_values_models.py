"""
P1: 价值观演化追踪模型

从"静态标签匹配"转向"动态共鸣演算法"的核心组件。

功能包括：
- 用户声明的价值观存储
- 从行为推断的价值观
- 价值观偏移计算
- 价值观偏移通知
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from db.database import Base
from typing import Optional, Dict, Any
from datetime import datetime
import json


# ============= P1: 价值观演化追踪模型 =============

class DeclaredValuesDB(Base):
    """用户声明的价值观"""
    __tablename__ = "declared_values"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 价值观维度 (JSON 存储)
    # 包括：
    # - 家庭观念：traditional (传统), balanced (平衡), liberal (开放)
    # - 事业观念：career_focused (事业优先), family_focused (家庭优先), balanced (平衡)
    # - 消费观念：frugal (节俭), moderate (适度), generous (享受)
    # - 社交观念：introverted (内向), extroverted (外向), ambivert (中间)
    # - 生活节奏：slow (慢节奏), balanced (平衡), fast (快节奏)
    # - 风险偏好：risk_averse (风险规避), moderate (适度), risk_seeking (风险偏好)
    values_data = Column(Text, nullable=False)  # JSON 字符串

    # 价值观来源
    source = Column(String(50), default="questionnaire")
    # questionnaire (问卷), interview (访谈), ai_inferred (AI 推断)

    # 置信度 (0-1)
    confidence_score = Column(Float, default=0.5)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_assessed_at = Column(DateTime(timezone=True), nullable=True)


class InferredValuesDB(Base):
    """从行为推断的价值观"""
    __tablename__ = "inferred_values"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 推断的价值观维度 (JSON 存储)
    # 格式与 DeclaredValuesDB.values_data 相同
    values_data = Column(Text, nullable=False)

    # 推断依据
    # 包括：
    # - 浏览行为：浏览的用户类型、筛选条件
    # - 互动行为：聊天频率、话题偏好
    # - 约会行为：约会地点偏好、活动类型
    # - 消费行为：礼物偏好、消费水平
    behavior_evidence = Column(Text, default="")  # JSON 字符串

    # 推断置信度 (0-1)
    confidence_score = Column(Float, default=0.5)

    # 分析周期
    analysis_start_date = Column(DateTime(timezone=True), nullable=False)
    analysis_end_date = Column(DateTime(timezone=True), nullable=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ValuesDriftDB(Base):
    """价值观偏移记录"""
    __tablename__ = "values_drift"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 偏移维度
    # 如："career_focus", "consumption", "social_preference"
    drift_dimension = Column(String(50), nullable=False, index=True)

    # 原始值 (声明的价值观)
    original_value = Column(String(100), nullable=False)

    # 当前值 (推断的价值观)
    current_value = Column(String(100), nullable=False)

    # 偏移分数 (0-1, 0 表示无偏移，1 表示完全偏移)
    drift_score = Column(Float, nullable=False)

    # 偏移方向
    # positive (积极变化), negative (消极变化), neutral (中性变化)
    drift_direction = Column(String(20), default="neutral")

    # 偏移严重程度
    # slight (轻微), moderate (中等), significant (显著), severe (严重)
    drift_severity = Column(String(20), default="slight")

    # 偏移描述
    drift_description = Column(Text, nullable=True)

    # 建议操作
    # none (无需操作), notify_user (通知用户), adjust_recommendation (调整推荐), review (人工审核)
    suggested_action = Column(String(30), default="none")

    # 是否已处理
    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processed_by = Column(String(36), nullable=True)  # 处理者 ID (user 或 admin)

    # 时间戳
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 索引
    __table_args__ = (
        UniqueConstraint('user_id', 'drift_dimension', name='uniq_user_drift_dimension'),
    )


class ValuesEvolutionHistoryDB(Base):
    """价值观演化历史"""
    __tablename__ = "values_evolution_history"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 演化类型
    # values_updated (价值观更新), drift_detected (偏移检测), behavior_adjusted (行为调整)
    evolution_type = Column(String(30), nullable=False)

    # 演化前状态
    before_state = Column(Text, nullable=False)  # JSON 字符串

    # 演化后状态
    after_state = Column(Text, nullable=False)  # JSON 字符串

    # 演化原因
    # 如："用户主动更新", "AI 检测到行为变化", "定期评估"
    evolution_reason = Column(String(200), nullable=True)

    # 演化详情
    evolution_details = Column(Text, default="")  # JSON 字符串

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MatchingWeightAdjustmentDB(Base):
    """匹配权重调整记录"""
    __tablename__ = "matching_weight_adjustments"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 调整原因
    # values_drift (价值观偏移), behavior_change (行为变化), user_request (用户请求)
    adjustment_reason = Column(String(30), nullable=False)

    # 调整前的权重配置
    previous_weights = Column(Text, nullable=False)  # JSON 字符串

    # 调整后的权重配置
    new_weights = Column(Text, nullable=False)  # JSON 字符串

    # 调整详情
    # 包括哪些维度被调整，调整幅度等
    adjustment_details = Column(Text, default="")  # JSON 字符串

    # 是否生效
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    effective_until = Column(DateTime(timezone=True), nullable=True)

    # 索引
    __table_args__ = (
        UniqueConstraint('user_id', 'adjustment_reason', name='uniq_user_adjustment_reason'),
    )


# ============================================
# 常量定义
# ============================================

# 价值观维度列表
VALUES_DIMENSIONS = [
    "family_view",        # 家庭观念
    "career_view",        # 事业观念
    "consumption_view",   # 消费观念
    "social_view",        # 社交观念
    "life_pace",          # 生活节奏
    "risk_preference",    # 风险偏好
]

# 各维度的可选值
VALUES_OPTIONS = {
    "family_view": ["traditional", "balanced", "liberal"],
    "career_view": ["career_focused", "family_focused", "balanced"],
    "consumption_view": ["frugal", "moderate", "generous"],
    "social_view": ["introverted", "extroverted", "ambivert"],
    "life_pace": ["slow", "balanced", "fast"],
    "risk_preference": ["risk_averse", "moderate", "risk_seeking"],
}

# 偏移严重程度阈值
DRIFT_SEVERITY_THRESHOLDS = {
    "slight": (0.0, 0.3),      # 0.0-0.3: 轻微
    "moderate": (0.3, 0.5),    # 0.3-0.5: 中等
    "significant": (0.5, 0.7), # 0.5-0.7: 显著
    "severe": (0.7, 1.0),      # 0.7-1.0: 严重
}

# 偏移方向判定
DRIFT_DIRECTION_RULES = {
    # 从 X 到 Y 的方向判定
    ("frugal", "generous"): "negative",  # 从节俭到享受：消极 (可能过度消费)
    ("generous", "frugal"): "positive",  # 从享受到节俭：积极 (更理性)
    ("career_focused", "balanced"): "positive",  # 更平衡
    ("risk_averse", "moderate"): "positive",  # 更平衡
}

# 建议操作规则
SUGGESTED_ACTION_RULES = {
    "slight": "none",              # 轻微：无需操作
    "moderate": "notify_user",     # 中等：通知用户
    "significant": "adjust_recommendation",  # 显著：调整推荐
    "severe": "review",            # 严重：人工审核
}


# ============================================
# 模型导出
# ============================================

__all__ = [
    'DeclaredValuesDB',
    'InferredValuesDB',
    'ValuesDriftDB',
    'ValuesEvolutionHistoryDB',
    'MatchingWeightAdjustmentDB',
    'VALUES_DIMENSIONS',
    'VALUES_OPTIONS',
    'DRIFT_SEVERITY_THRESHOLDS',
    'DRIFT_DIRECTION_RULES',
    'SUGGESTED_ACTION_RULES',
]
