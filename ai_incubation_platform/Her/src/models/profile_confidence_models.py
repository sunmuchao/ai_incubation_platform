"""
用户基础信息置信度评估模型

核心功能：
- 多维置信度评估（身份验证、交叉验证、行为一致性、社交背书）
- 交叉验证异常标记
- 置信度更新历史追踪
- 验证建议生成

设计理念：
- 非二元验证（通过/未通过），而是概率性置信度评估
- 轻量级验证，无需用户配合，后台自动计算
- 渐进式置信度提升，随时间和行为积累

置信度计算公式：
overall_confidence = base_score (0.3)
  + identity_verified × 0.25
  + cross_validation_score × 0.20
  + behavior_consistency × 0.15
  + social_endorsement × 0.10
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import json


class ConfidenceLevel(str, Enum):
    """置信度等级"""
    LOW = "low"         # 0.0 - 0.4: 需谨慎
    MEDIUM = "medium"   # 0.4 - 0.6: 普通用户
    HIGH = "high"       # 0.6 - 0.8: 较可信
    VERY_HIGH = "very_high"  # 0.8 - 1.0: 极可信


class ValidationFlagType(str, Enum):
    """交叉验证异常类型"""
    AGE_EDUCATION_MISMATCH = "age_education_mismatch"       # 年龄与学历不匹配
    OCCUPATION_INCOME_MISMATCH = "occupation_income_mismatch"  # 职业与收入不匹配
    LOCATION_ACTIVITY_MISMATCH = "location_activity_mismatch"  # 地理与活跃时间不匹配
    INTEREST_BEHAVIOR_MISMATCH = "interest_behavior_mismatch"  # 兴趣与行为不一致
    PROFILE_PHOTO_MISMATCH = "profile_photo_mismatch"       # 画像与照片风格不一致
    AGE_SELF_DECLARED_MISMATCH = "age_self_declared_mismatch"  # 自报年龄与推断年龄不一致


class ProfileConfidenceDetailDB(Base):
    """用户画像置信度详情"""
    __tablename__ = "profile_confidence_details"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # ========== 总置信度 ==========
    overall_confidence = Column(Float, default=0.3, nullable=False)
    confidence_level = Column(String(20), default="medium")  # low, medium, high, very_high

    # ========== 各维度置信度 ==========
    # 身份验证置信度 (0-1)
    # 来源：实名认证、人脸核身、手机验证
    identity_confidence = Column(Float, default=0.0)

    # 交叉验证置信度 (0-1)
    # 来源：年龄-学历、职业-收入、地理-活跃时间等逻辑校验
    cross_validation_confidence = Column(Float, default=0.0)

    # 行为一致性置信度 (0-1)
    # 来源：声称兴趣 vs 实际浏览、声称性格 vs 聊天风格
    behavior_consistency = Column(Float, default=0.0)

    # 社交背书置信度 (0-1)
    # 来源：邀请码、朋友推荐、好评率
    social_endorsement = Column(Float, default=0.0)

    # 时间积累置信度 (0-1)
    # 来源：注册时长、活跃天数、信息完善进度
    time_accumulation = Column(Float, default=0.0)

    # ========== 交叉验证详情 ==========
    # 交叉验证异常标记 (JSON)
    # 示例: {"age_education_mismatch": {"severity": "high", "detail": "25岁但声称10年前毕业"}}
    cross_validation_flags = Column(Text, default="{}")

    # 交叉验证通过的项
    cross_validation_passed = Column(Text, default="[]")

    # 交叉验证分数明细
    cross_validation_score_breakdown = Column(Text, default="{}")

    # ========== 行为一致性详情 ==========
    # 兴趣一致性分析
    # 示例: {"claimed_interests": ["旅行", "摄影"], "actual_browse_categories": ["旅行", "美食"], "match_rate": 0.67}
    interest_consistency_detail = Column(Text, default="{}")

    # 性格一致性分析
    # 示例: {"claimed_personality": "introvert", "chat_style_analysis": "introvert", "match": true}
    personality_consistency_detail = Column(Text, default="{}")

    # ========== 社交背书详情 ==========
    # 邀请来源
    invite_source_type = Column(String(50), nullable=True)  # direct, invite_code, referral
    inviter_id = Column(String(36), nullable=True)  # 邀请人 ID

    # 好评率
    positive_feedback_rate = Column(Float, default=0.5)

    # ========== 时间积累详情 ==========
    # 注册天数
    account_age_days = Column(Integer, default=0)

    # 活跃天数
    active_days = Column(Integer, default=0)

    # 信息完善进度 (0-100%)
    profile_completeness_pct = Column(Float, default=0.0)

    # ========== 置信度更新历史 ==========
    # 最近一次评估时间
    last_evaluated_at = Column(DateTime(timezone=True), nullable=True)

    # 评估版本
    evaluation_version = Column(String(20), default="v1.0")

    # 置信度变化历史
    # 示例: [{"at": "2024-01-01", "confidence": 0.3, "reason": "初始注册"}, ...]
    confidence_history = Column(Text, default="[]")

    # ========== 验证建议 ==========
    # 建议完成的验证项
    # 示例: [{"type": "identity", "priority": "high", "score_impact": "+0.25"}, ...]
    recommended_verifications = Column(Text, default="[]")

    # 已完成的验证项
    completed_verifications = Column(Text, default="[]")

    # ========== 元数据 ==========
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联用户
    user = relationship("UserDB", backref="confidence_detail")


class CrossValidationRuleDB(Base):
    """交叉验证规则配置"""
    __tablename__ = "cross_validation_rules"

    id = Column(String(36), primary_key=True, index=True)

    # 规则标识
    rule_key = Column(String(100), nullable=False, unique=True, index=True)
    # 规则列表:
    # - age_education_match: 年龄与学历毕业年份匹配
    # - occupation_income_match: 职业与收入匹配
    # - location_activity_match: 地理位置与活跃时间匹配
    # - interest_browse_match: 兴趣与浏览行为匹配

    # 规则名称
    rule_name = Column(String(200), nullable=False)

    # 规则描述
    rule_description = Column(Text, nullable=True)

    # 规则类型
    rule_type = Column(String(50), nullable=False)
    # logic_check: 逻辑校验（年龄-学历）
    # statistical_check: 统计校验（职业-收入分布）
    # behavior_check: 行为校验（兴趣-浏览）

    # 规则权重 (用于置信度计算)
    rule_weight = Column(Float, default=1.0)

    # 规则配置 (JSON)
    # 示例: {"min_age": 18, "max_age": 60, "education_years": {"bachelor": 4, "master": 2}}
    rule_config = Column(Text, default="{}")

    # 异常阈值
    anomaly_threshold = Column(Float, default=0.7)

    # 异常严重等级
    anomaly_severity_levels = Column(Text, default="{}")
    # 示例: {"low": 0.3, "medium": 0.5, "high": 0.7}

    # 规则状态
    is_active = Column(Boolean, default=True)

    # 规则版本
    version = Column(String(20), default="v1.0")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ConfidenceEvaluationLogDB(Base):
    """置信度评估日志"""
    __tablename__ = "confidence_evaluation_logs"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 评估触发来源
    trigger_source = Column(String(50), nullable=False)
    # register: 注册时评估
    # profile_update: 画像更新时评估
    # periodic: 定期评估
    # manual: 手动触发评估
    # behavior_change: 行为变化触发

    # 评估前置信度
    confidence_before = Column(Float, nullable=True)

    # 评估后置信度
    confidence_after = Column(Float, nullable=False)

    # 置信度变化
    confidence_change = Column(Float, nullable=True)

    # 各维度变化明细
    dimension_changes = Column(Text, default="{}")

    # 评估详情
    evaluation_details = Column(Text, default="{}")

    # 评估耗时 (毫秒)
    evaluation_time_ms = Column(Integer, nullable=True)

    # 时间戳
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())


class VerificationSuggestionDB(Base):
    """验证建议缓存"""
    __tablename__ = "verification_suggestions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 建议类型
    suggestion_type = Column(String(50), nullable=False, index=True)
    # identity_verify: 完成实名认证
    # education_verify: 完成学历认证
    # occupation_verify: 完成职业认证
    # income_verify: 完成收入认证
    # photo_verify: 完成照片验证
    # profile_complete: 完善个人资料
    # behavior_confirm: 通过行为确认兴趣

    # 建议优先级
    priority = Column(String(20), default="medium")  # high, medium, low

    # 预估置信度提升
    estimated_confidence_boost = Column(Float, default=0.0)

    # 建议原因
    reason = Column(Text, nullable=True)

    # 建议状态
    status = Column(String(20), default="pending")  # pending, completed, dismissed

    # 用户反馈
    user_feedback = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


# ============================================
# 模型导出
# ============================================

__all__ = [
    'ConfidenceLevel',
    'ValidationFlagType',
    'ProfileConfidenceDetailDB',
    'CrossValidationRuleDB',
    'ConfidenceEvaluationLogDB',
    'VerificationSuggestionDB',
]