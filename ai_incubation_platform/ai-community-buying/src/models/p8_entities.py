"""
P8 阶段 - 智能风控/信用体系数据库实体模型

包含:
1. 信用体系 (Credit System)
2. 风控规则引擎 (Risk Rule Engine)
3. 黑名单管理 (Blacklist Management)
4. 订单风控 (Order Risk Assessment)
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum, Boolean, Index, Float, Numeric, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
import enum

from config.database import Base


# ====================  Enums  ====================

class CreditLevel(enum.Enum):
    """信用等级"""
    EXCELLENT = "excellent"    # 优秀 (750-850)
    VERY_GOOD = "very_good"    # 很好 (700-749)
    GOOD = "good"              # 好 (650-699)
    FAIR = "fair"              # 一般 (600-649)
    POOR = "poor"              # 差 (300-599)


class RiskLevel(enum.Enum):
    """风险等级"""
    LOW = "low"            # 低风险
    MEDIUM = "medium"      # 中风险
    HIGH = "high"          # 高风险
    CRITICAL = "critical"  # 严重风险


class BlacklistType(enum.Enum):
    """黑名单类型"""
    USER = "user"        # 用户黑名单
    DEVICE = "device"    # 设备黑名单
    ADDRESS = "address"  # 地址黑名单
    PHONE = "phone"      # 手机号黑名单


class RiskRuleType(enum.Enum):
    """风控规则类型"""
    ORDER = "order"          # 订单风控规则
    USER = "user"            # 用户风控规则
    COUPON = "coupon"        # 优惠券风控规则
    CASHBACK = "cashback"    # 返现风控规则
    BARGAIN = "bargain"      # 砍价风控规则


class RiskRuleAction(enum.Enum):
    """风控规则动作"""
    ALLOW = "allow"              # 允许
    REVIEW = "review"            # 人工审核
    REJECT = "reject"            # 拒绝
    LIMIT = "limit"              # 限制 (限额/限量)
    NOTIFY = "notify"            # 通知


class OrderRiskDecision(enum.Enum):
    """订单风险决策"""
    APPROVE = "approve"      # 通过
    REVIEW = "review"        # 审核
    REJECT = "reject"        # 拒绝
    CANCEL = "cancel"        # 取消


# ====================  信用体系  ====================

class CreditScoreEntity(Base):
    """用户信用分实体"""
    __tablename__ = "credit_scores"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, unique=True, index=True)  # 用户 ID

    # 信用分
    credit_score = Column(Integer, nullable=False, default=500)  # 信用分 (300-850)
    credit_level = Column(Enum(CreditLevel), nullable=False, default=CreditLevel.FAIR)  # 信用等级

    # 信用因子快照 (JSON 格式存储各因子得分)
    factor_scores = Column(Text)  # {"order_completion_rate": 80, "fulfillment_score": 90, ...}

    # 有效期
    valid_from = Column(DateTime, default=datetime.now)
    valid_until = Column(DateTime)  # 过期时间，NULL 表示长期有效

    # 元数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    calculated_by = Column(String(64))  # 计算者 (系统/人工)

    __table_args__ = (
        Index('idx_credit_scores_user_level', 'user_id', 'credit_level'),
    )


class CreditScoreHistoryEntity(Base):
    """信用分历史实体 - 记录信用分变化"""
    __tablename__ = "credit_score_history"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)  # 用户 ID

    # 变化前后
    old_score = Column(Integer, nullable=False)
    new_score = Column(Integer, nullable=False)
    score_change = Column(Integer, nullable=False)  # 变化值 (正/负)

    # 变化原因
    change_reason = Column(String(256), nullable=False)  # 变化原因描述
    change_type = Column(String(32), nullable=False)  # 变化类型：ORDER_COMPLETE/GOOD_REVIEW/COMPLAINT/FRAUD etc.

    # 关联信息
    related_order_id = Column(String(64))  # 关联订单 ID
    related_event_id = Column(String(64))  # 关联事件 ID

    # 元数据
    created_at = Column(DateTime, default=datetime.now, index=True)
    created_by = Column(String(64))  # 创建者 (系统/人工)

    __table_args__ = (
        Index('idx_credit_history_user_time', 'user_id', 'created_at'),
    )


class CreditFactorEntity(Base):
    """信用因子配置实体 - 定义信用分的计算因子"""
    __tablename__ = "credit_factors"

    id = Column(String(64), primary_key=True)
    factor_code = Column(String(64), nullable=False, unique=True)  # 因子代码
    factor_name = Column(String(128), nullable=False)  # 因子名称

    # 计算配置
    weight = Column(DECIMAL(5, 4), nullable=False, default=0.1)  # 权重 (0-1)
    calculation_method = Column(String(32), nullable=False)  # 计算方法：ratio/average/count/sum
    min_value = Column(Integer, default=0)  # 最小值
    max_value = Column(Integer, default=100)  # 最大值

    # 描述
    description = Column(Text)
    formula = Column(String(512))  # 计算公式描述

    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ====================  风控规则引擎  ====================

class RiskRuleEntity(Base):
    """风控规则定义实体"""
    __tablename__ = "risk_rules"

    id = Column(String(64), primary_key=True)
    rule_code = Column(String(64), nullable=False, unique=True)  # 规则代码
    rule_name = Column(String(128), nullable=False)  # 规则名称
    rule_type = Column(Enum(RiskRuleType), nullable=False)  # 规则类型

    # 规则配置
    rule_category = Column(String(32))  # 规则分类：FREQUENCY/AMOUNT/BEHAVIOR/DEVICE etc.

    # 条件配置 (JSON 格式)
    # 示例：{"field": "order_amount", "operator": ">", "threshold": 1000}
    # 支持的操作符：>, <, =, >=, <=, in, contains, matches
    conditions = Column(Text, nullable=False)

    # 动作配置
    action = Column(Enum(RiskRuleAction), nullable=False, default=RiskRuleAction.REVIEW)  # 执行动作
    action_params = Column(Text)  # 动作参数 (JSON 格式)

    # 风险评分
    risk_score = Column(Integer, default=0)  # 命中该规则增加的风险分

    # 优先级和状态
    priority = Column(Integer, default=100)  # 优先级 (数字越小优先级越高)
    is_active = Column(Boolean, default=True)  # 是否启用

    # 描述
    description = Column(Text)
    examples = Column(Text)  # 示例 (JSON 格式)

    # 统计信息
    hit_count = Column(Integer, default=0)  # 命中次数
    last_hit_at = Column(DateTime)  # 最后命中时间

    # 元数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String(64))  # 创建者

    __table_args__ = (
        Index('idx_risk_rules_type_priority', 'rule_type', 'priority'),
    )


class RiskEventEntity(Base):
    """风险事件记录实体"""
    __tablename__ = "risk_events"

    id = Column(String(64), primary_key=True)
    event_type = Column(String(64), nullable=False)  # 事件类型：FRAUD/SUSPICIOUS/ABNORMAL etc.

    # 关联对象
    user_id = Column(String(64), index=True)  # 用户 ID
    order_id = Column(String(64), index=True)  # 订单 ID
    related_id = Column(String(64))  # 其他关联 ID (优惠券/活动 etc.)

    # 风险评估
    risk_level = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.LOW)  # 风险等级
    risk_score = Column(Integer, default=0)  # 风险评分

    # 命中的规则
    hit_rules = Column(Text)  # 命中的规则列表 (JSON 格式)
    rule_hit_count = Column(Integer, default=0)  # 命中规则数量

    # 证据
    evidence = Column(Text)  # 证据数据 (JSON 格式)
    description = Column(Text)  # 事件描述

    # 处理
    status = Column(String(32), default="pending")  # pending/processing/resolved/ignored
    handled_by = Column(String(64))  # 处理人
    handled_at = Column(DateTime)  # 处理时间
    handle_result = Column(Text)  # 处理结果

    # 元数据
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_risk_events_user_level', 'user_id', 'risk_level'),
        Index('idx_risk_events_status', 'status'),
    )


class BlacklistEntity(Base):
    """黑名单记录实体"""
    __tablename__ = "blacklists"

    id = Column(String(64), primary_key=True)

    # 目标信息
    target_type = Column(Enum(BlacklistType), nullable=False)  # 目标类型
    target_value = Column(String(256), nullable=False, index=True)  # 目标值 (user_id/device_id/address/phone)

    # 黑名单类型
    blacklist_type = Column(String(32), nullable=False)  # PERMANENT/TEMPORARY/SPECIFIC
    reason_code = Column(String(64))  # 原因代码
    reason = Column(Text, nullable=False)  # 原因描述

    # 有效期
    expire_at = Column(DateTime)  # 过期时间 (NULL 表示永久)
    is_active = Column(Boolean, default=True)  # 是否生效

    # 证据
    evidence = Column(Text)  # 证据 (JSON 格式)
    related_event_id = Column(String(64))  # 关联风险事件 ID

    # 元数据
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String(64))  # 创建者

    __table_args__ = (
        Index('idx_blacklist_type_value', 'target_type', 'target_value'),
    )


# ====================  订单风控  ====================

class OrderRiskAssessmentEntity(Base):
    """订单风险评估实体"""
    __tablename__ = "order_risk_assessments"

    id = Column(String(64), primary_key=True)
    order_id = Column(String(64), nullable=False, unique=True, index=True)  # 订单 ID
    user_id = Column(String(64), nullable=False, index=True)  # 用户 ID

    # 风险评估结果
    risk_score = Column(Integer, nullable=False, default=0)  # 风险评分 (0-100)
    risk_level = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.LOW)  # 风险等级

    # 风险因子详情 (JSON 格式)
    # 示例：{"credit_risk": 20, "amount_risk": 30, "behavior_risk": 10, "blacklist_risk": 0}
    risk_factors = Column(Text)

    # 命中的规则
    hit_rules = Column(Text)  # 命中的风控规则列表 (JSON 格式)

    # 决策
    decision = Column(Enum(OrderRiskDecision), nullable=False, default=OrderRiskDecision.APPROVE)  # 决策结果
    decision_reason = Column(String(256))  # 决策原因

    # 评估上下文
    assessment_context = Column(Text)  # 评估时的上下文数据 (JSON 格式)

    # 元数据
    created_at = Column(DateTime, default=datetime.now, index=True)
    assessed_by = Column(String(64))  # 评估者 (系统/人工)

    __table_args__ = (
        Index('idx_order_risk_level', 'risk_level'),
        Index('idx_order_risk_decision', 'decision'),
    )
