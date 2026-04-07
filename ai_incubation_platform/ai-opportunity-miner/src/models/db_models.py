"""
SQLAlchemy 数据库模型
映射商机、趋势、用户、订阅等实体到数据库表
"""
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, Text, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import json
import enum

from config.database import Base


class SubscriptionTier(enum.Enum):
    """订阅等级枚举"""
    FREE = "free"  # 免费版
    PRO = "pro"    # 专业版
    ENTERPRISE = "enterprise"  # 企业版


class QuotaType(enum.Enum):
    """配额类型枚举"""
    DAILY = "daily"      # 每日配额
    MONTHLY = "monthly"  # 每月配额
    ONE_TIME = "one_time"  # 一次性配额


class BillingMode(enum.Enum):
    """计费模式枚举"""
    SUBSCRIPTION = "subscription"  # 订阅制
    PAY_AS_YOU_GO = "pay_as_you_go"  # 按量计费
    PREPAID = "prepaid"  # 预付费套餐包


class TenantType(enum.Enum):
    """租户类型枚举"""
    INDIVIDUAL = "individual"  # 个人租户
    TEAM = "team"  # 团队租户
    ENTERPRISE = "enterprise"  # 企业租户


class UserDB(Base):
    """用户数据库模型"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # 个人信息
    full_name = Column(String(200), nullable=True)
    company_name = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)

    # 账户状态
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)

    # 订阅信息
    subscription_tier = Column(String(20), default="free")
    subscription_started_at = Column(DateTime, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # 关联
    audit_logs = relationship("AuditLogDB", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecordDB", back_populates="user", cascade="all, delete-orphan")
    contributions = relationship("UserContributionDB", foreign_keys="UserContributionDB.user_id", back_populates="contributor", cascade="all, delete-orphan")
    reviews = relationship("UserContributionDB", foreign_keys="UserContributionDB.reviewed_by", back_populates="reviewer", cascade="all, delete-orphan")
    points_account = relationship("UserPointsDB", back_populates="user", uselist=False, cascade="all, delete-orphan")
    comments = relationship("CommunityCommentDB", back_populates="author", cascade="all, delete-orphan")
    api_keys = relationship("APIKeyDB", back_populates="owner", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """转换为字典（不包含敏感信息）"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "company_name": self.company_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "subscription_tier": self.subscription_tier,
            "subscription_started_at": self.subscription_started_at.isoformat() if self.subscription_started_at else None,
            "subscription_expires_at": self.subscription_expires_at.isoformat() if self.subscription_expires_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AuditLogDB(Base):
    """审计日志数据库模型"""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 操作信息
    action = Column(String(100), nullable=False)  # 操作类型
    resource_type = Column(String(50), nullable=True)  # 资源类型
    resource_id = Column(String(36), nullable=True)  # 资源 ID

    # 操作详情
    request_method = Column(String(10), nullable=True)  # HTTP 方法
    request_path = Column(String(500), nullable=True)  # 请求路径
    request_body = Column(JSON, nullable=True)  # 请求体
    response_status = Column(Integer, nullable=True)  # 响应状态码

    # 审计信息
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)

    # 关联
    user = relationship("UserDB", back_populates="audit_logs")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "request_body": self.request_body,
            "response_status": self.response_status,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


class UsageRecordDB(Base):
    """使用记录数据库模型（用于用量统计和计费）"""
    __tablename__ = "usage_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 使用信息
    feature = Column(String(100), nullable=False)  # 使用的功能
    count = Column(Integer, default=1)  # 使用次数
    unit = Column(String(50), default="times")  # 单位

    # 用量详情
    details = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    date = Column(String(10), nullable=False, index=True)  # 日期 YYYY-MM-DD

    # 关联
    user = relationship("UserDB", back_populates="usage_records")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "feature": self.feature,
            "count": self.count,
            "unit": self.unit,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
            "date": self.date,
        }


# ==================== 原有的模型 ====================


class BusinessOpportunityDB(Base):
    """商机数据库模型"""
    __tablename__ = "business_opportunities"

    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=False)
    opportunity_type = Column(String(50), nullable=False)  # market, product, partnership, investment
    status = Column(String(20), nullable=False, index=True, default="new")  # new, validated, expired

    # 置信度和价值评估
    confidence_score = Column(Float, nullable=False, default=0.0)
    potential_value = Column(Float, nullable=False, default=0.0)
    potential_value_currency = Column(String(10), default="CNY")

    # 来源信息
    source_type = Column(String(50), nullable=False)
    source_name = Column(String(200), nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_publish_date = Column(DateTime, nullable=True)

    # 风险评估
    risk_labels = Column(JSON, nullable=True)  # 存储为 JSON 数组
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_description = Column(Text, nullable=True)

    # 验证信息
    validation_steps = Column(JSON, nullable=True)  # 存储为 JSON 数组
    validation_status = Column(String(20), default="pending")
    validation_notes = Column(Text, nullable=True)

    # 实体和标签
    related_entities = Column(JSON, nullable=True)  # 存储为 JSON 数组
    tags = Column(JSON, nullable=True)  # 存储为 JSON 数组

    # 额外数据（用于存储 LLM 分析结果等）
    extra = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.opportunity_type,
            "status": self.status,
            "confidence_score": self.confidence_score,
            "potential_value": self.potential_value,
            "potential_value_currency": self.potential_value_currency,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "source_publish_date": self.source_publish_date.isoformat() if self.source_publish_date else None,
            "risk_labels": self.risk_labels or [],
            "risk_score": self.risk_score,
            "risk_description": self.risk_description,
            "validation_steps": self.validation_steps or [],
            "validation_status": self.validation_status,
            "validation_notes": self.validation_notes,
            "related_entities": self.related_entities or [],
            "tags": self.tags or [],
            "extra": self.extra,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BusinessOpportunityDB":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            title=data.get("title"),
            description=data.get("description"),
            opportunity_type=data.get("type"),
            status=data.get("status", "new"),
            confidence_score=data.get("confidence_score", 0.0),
            potential_value=data.get("potential_value", 0.0),
            potential_value_currency=data.get("potential_value_currency", "CNY"),
            source_type=data.get("source_type", "ai_analysis"),
            source_name=data.get("source_name"),
            source_url=data.get("source_url"),
            source_publish_date=data.get("source_publish_date"),
            risk_labels=data.get("risk_labels", []),
            risk_score=data.get("risk_score", 0.0),
            risk_description=data.get("risk_description"),
            validation_steps=data.get("validation_steps", []),
            validation_status=data.get("validation_status", "pending"),
            validation_notes=data.get("validation_notes"),
            related_entities=data.get("related_entities", []),
            tags=data.get("tags", []),
            extra=data.get("extra", {}),
        )


class MarketTrendDB(Base):
    """市场趋势数据库模型"""
    __tablename__ = "market_trends"

    id = Column(String(36), primary_key=True, index=True)
    keyword = Column(String(100), nullable=False, index=True)
    trend_score = Column(Float, nullable=False)
    growth_rate = Column(Float, nullable=False)
    related_keywords = Column(JSON, nullable=True)  # 存储为 JSON 数组
    data_points = Column(JSON, nullable=True)  # 存储为 JSON 数组
    extra = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "keyword": self.keyword,
            "trend_score": self.trend_score,
            "growth_rate": self.growth_rate,
            "related_keywords": self.related_keywords or [],
            "data_points": self.data_points or [],
            "extra": self.extra,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MarketTrendDB":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            keyword=data.get("keyword"),
            trend_score=data.get("trend_score"),
            growth_rate=data.get("growth_rate"),
            related_keywords=data.get("related_keywords", []),
            data_points=data.get("data_points", []),
            extra=data.get("extra", {}),
        )


# ==================== P7 平台化功能模型 ====================


class UserContributionDB(Base):
    """用户贡献数据模型 - P7 用户贡献数据机制"""
    __tablename__ = "user_contributions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 贡献内容
    contribution_type = Column(String(50), nullable=False)  # opportunity, data_source, verification, correction
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    content = Column(JSON, nullable=True)  # 结构化内容

    # 来源信息
    source_url = Column(String(1000), nullable=True)
    source_evidence = Column(JSON, nullable=True)  # 证据材料

    # 审核状态
    status = Column(String(20), nullable=False, default="pending")  # pending, approved, rejected
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)  # 审核人
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)  # 审核意见

    # 质量评分
    quality_score = Column(Float, nullable=True)  # 0-100
    community_votes = Column(Integer, default=0)  # 社区投票数

    # 采纳状态
    is_adopted = Column(Boolean, default=False)  # 是否被采纳到系统
    adopted_opportunity_id = Column(String(36), nullable=True)  # 关联的商机 ID

    # 奖励积分
    points_awarded = Column(Integer, default=0)  # 奖励积分

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # 关联
    contributor = relationship("UserDB", foreign_keys=[user_id], back_populates="contributions")
    reviewer = relationship("UserDB", foreign_keys=[reviewed_by], back_populates="reviews")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "contribution_type": self.contribution_type,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "source_url": self.source_url,
            "source_evidence": self.source_evidence,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "quality_score": self.quality_score,
            "community_votes": self.community_votes,
            "is_adopted": self.is_adopted,
            "adopted_opportunity_id": self.adopted_opportunity_id,
            "points_awarded": self.points_awarded,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class UserPointsDB(Base):
    """用户积分模型 - P7 用户信誉系统"""
    __tablename__ = "user_points"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 积分信息
    total_points = Column(Integer, default=0)  # 总积分
    available_points = Column(Integer, default=0)  # 可用积分
    spent_points = Column(Integer, default=0)  # 已消耗积分

    # 信誉等级
    reputation_level = Column(String(20), default="bronze")  # bronze, silver, gold, platinum, diamond
    reputation_score = Column(Float, default=0.0)  # 信誉分数 0-100

    # 贡献统计
    contributions_count = Column(Integer, default=0)  # 贡献次数
    approved_contributions_count = Column(Integer, default=0)  # 通过审核的贡献
    adopted_contributions_count = Column(Integer, default=0)  # 被采纳的贡献

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # 关联
    user = relationship("UserDB", back_populates="points_account")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "total_points": self.total_points,
            "available_points": self.available_points,
            "spent_points": self.spent_points,
            "reputation_level": self.reputation_level,
            "reputation_score": self.reputation_score,
            "contributions_count": self.contributions_count,
            "approved_contributions_count": self.approved_contributions_count,
            "adopted_contributions_count": self.adopted_contributions_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PointsTransactionDB(Base):
    """积分交易记录模型"""
    __tablename__ = "points_transactions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 交易类型
    transaction_type = Column(String(20), nullable=False)  # earn, spend, refund, adjust
    action = Column(String(50), nullable=False)  # contribution_approved, contribution_adopted, redeem_reward, etc.

    # 交易金额
    points_change = Column(Integer, nullable=False)  # 正数为收入，负数为支出
    balance_after = Column(Integer, nullable=False)  # 交易后余额

    # 关联信息
    related_contribution_id = Column(String(36), nullable=True)
    description = Column(String(500), nullable=True)
    extra_data = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "transaction_type": self.transaction_type,
            "action": self.action,
            "points_change": self.points_change,
            "balance_after": self.balance_after,
            "related_contribution_id": self.related_contribution_id,
            "description": self.description,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat(),
        }


class CommunityVoteDB(Base):
    """社区投票模型 - P7 社区驱动功能"""
    __tablename__ = "community_votes"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 投票目标
    target_type = Column(String(50), nullable=False)  # contribution, opportunity, comment
    target_id = Column(String(36), nullable=False, index=True)

    # 投票类型
    vote_type = Column(String(10), nullable=False)  # upvote, downvote
    weight = Column(Float, default=1.0)  # 投票权重（基于用户信誉）

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "vote_type": self.vote_type,
            "weight": self.weight,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class CommunityCommentDB(Base):
    """社区评论模型 - P7 社区驱动功能"""
    __tablename__ = "community_comments"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("community_comments.id"), nullable=True)  # 回复评论

    # 评论内容
    target_type = Column(String(50), nullable=False)  # opportunity, contribution
    target_id = Column(String(36), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # 评论状态
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # 关联
    author = relationship("UserDB", back_populates="comments")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "parent_id": self.parent_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "content": self.content,
            "is_edited": self.is_edited,
            "is_deleted": self.is_deleted,
            "upvotes": self.upvotes,
            "downvotes": self.downvotes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class APIKeyDB(Base):
    """API 密钥模型 - P7 开放 API 平台"""
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 密钥信息
    key = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)  # 密钥名称
    description = Column(Text, nullable=True)

    # 权限范围
    scopes = Column(JSON, nullable=True)  # ["read:opportunities", "write:opportunities", "read:trends"]

    # 使用限制
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=1000)

    # 状态
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    expires_at = Column(DateTime, nullable=True)  # 过期时间，None 表示永不过期

    # 关联
    owner = relationship("UserDB", back_populates="api_keys")

    def to_dict(self) -> dict:
        """转换为字典（不暴露完整密钥）"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "key_prefix": self.key[:8] + "..." if self.key else None,
            "name": self.name,
            "description": self.description,
            "scopes": self.scopes or [],
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_per_day": self.rate_limit_per_day,
            "is_active": self.is_active,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class APIUsageLogDB(Base):
    """API 使用日志模型 - P7 开放 API 平台"""
    __tablename__ = "api_usage_logs"

    id = Column(String(36), primary_key=True, index=True)
    api_key_id = Column(String(36), ForeignKey("api_keys.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 请求信息
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    request_params = Column(JSON, nullable=True)

    # 响应信息
    response_status = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)  # 响应时间（毫秒）

    # 使用量
    tokens_used = Column(Integer, default=0)  # 如果有 token 计费

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "api_key_id": self.api_key_id,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "request_params": self.request_params,
            "response_status": self.response_status,
            "response_time_ms": self.response_time_ms,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat(),
        }


# ==================== P6 商用就绪 - 支付与订单模型 ====================


class OrderStatus(enum.Enum):
    """订单状态枚举"""
    PENDING = "pending"       # 待支付
    PAID = "paid"            # 已支付
    CANCELLED = "cancelled"   # 已取消
    REFUNDED = "refunded"    # 已退款
    EXPIRED = "expired"      # 已过期


class RefundStatus(enum.Enum):
    """退款状态枚举"""
    PENDING = "pending"      # 待处理
    APPROVED = "approved"    # 已批准
    REJECTED = "rejected"    # 已拒绝
    COMPLETED = "completed"  # 已完成


class InvoiceStatus(enum.Enum):
    """发票状态枚举"""
    PENDING = "pending"      # 待开具
    ISSUED = "issued"        # 已开具
    DELIVERED = "delivered"  # 已送达
    CANCELLED = "cancelled"  # 已取消


class OrderDB(Base):
    """订单数据库模型 - P6 订单管理"""
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    order_no = Column(String(64), nullable=False, unique=True, index=True)  # 订单号

    # 产品信息
    product_type = Column(String(50), nullable=False)  # subscription-订阅，topup-充值
    subscription_tier = Column(String(20), nullable=True)  # free/pro/enterprise
    billing_cycle = Column(String(20), default="monthly")  # monthly-月付，yearly-年付

    # 金额信息
    amount = Column(Float, nullable=False)  # 原价
    discount_amount = Column(Float, default=0)  # 优惠金额
    paid_amount = Column(Float, nullable=True)  # 实付金额
    currency = Column(String(10), default="CNY")

    # 订单状态
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, index=True)

    # 支付信息
    payment_method = Column(String(50), nullable=True)  # alipay, wechat, stripe
    payment_time = Column(DateTime, nullable=True)
    transaction_id = Column(String(128), nullable=True)  # 第三方支付流水号

    # 退款信息
    refund_status = Column(SQLEnum(RefundStatus), nullable=True)
    refund_time = Column(DateTime, nullable=True)
    refund_amount = Column(Float, nullable=True)
    refund_reason = Column(Text, nullable=True)

    # 发票信息
    invoice_required = Column(Boolean, default=False)
    invoice_title = Column(String(200), nullable=True)  # 发票抬头
    invoice_tax_id = Column(String(50), nullable=True)  # 税号

    # 备注
    notes = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    paid_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # 订单过期时间

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "order_no": self.order_no,
            "product_type": self.product_type,
            "subscription_tier": self.subscription_tier,
            "billing_cycle": self.billing_cycle,
            "amount": self.amount,
            "discount_amount": self.discount_amount,
            "paid_amount": self.paid_amount,
            "currency": self.currency,
            "status": self.status.value if self.status else None,
            "payment_method": self.payment_method,
            "payment_time": self.payment_time.isoformat() if self.payment_time else None,
            "transaction_id": self.transaction_id,
            "refund_status": self.refund_status.value if self.refund_status else None,
            "refund_time": self.refund_time.isoformat() if self.refund_time else None,
            "refund_amount": self.refund_amount,
            "refund_reason": self.refund_reason,
            "invoice_required": self.invoice_required,
            "invoice_title": self.invoice_title,
            "invoice_tax_id": self.invoice_tax_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class PaymentRecordDB(Base):
    """支付记录数据库模型 - P6 支付管理"""
    __tablename__ = "payment_records"

    id = Column(String(36), primary_key=True, index=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 支付信息
    payment_method = Column(String(50), nullable=False)  # alipay, wechat, stripe, mock
    transaction_id = Column(String(128), nullable=True, unique=True)  # 第三方支付流水号

    # 金额信息
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="CNY")

    # 支付状态
    status = Column(String(20), default="pending")  # pending, success, failed, refunded

    # 回调数据
    callback_data = Column(JSON, nullable=True)  # 第三方支付回调原始数据

    # 失败原因
    failed_reason = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    paid_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "callback_data": self.callback_data,
            "failed_reason": self.failed_reason,
            "created_at": self.created_at.isoformat(),
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


class InvoiceDB(Base):
    """发票数据库模型 - P6 发票管理"""
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True, index=True)  # 关联订单

    # 发票信息
    invoice_no = Column(String(64), nullable=False, unique=True, index=True)  # 发票号码
    invoice_type = Column(String(20), nullable=False)  # electronic-电子发票，paper-纸质发票
    invoice_title = Column(String(200), nullable=False)  # 发票抬头
    tax_id = Column(String(50), nullable=False)  # 税号

    # 金额
    amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0)  # 税额
    total_amount = Column(Float, nullable=False)  # 价税合计

    # 收件信息（纸质发票）
    receiver_name = Column(String(100), nullable=True)
    receiver_phone = Column(String(50), nullable=True)
    receiver_address = Column(String(500), nullable=True)

    # 电子发票接收邮箱
    receiver_email = Column(String(255), nullable=True)

    # 发票状态
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING, index=True)

    # 发票文件
    invoice_url = Column(String(1000), nullable=True)  # 电子文件 URL
    delivery_status = Column(String(20), default="pending")  # pending, sent, delivered, failed

    # 备注
    notes = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    issued_at = Column(DateTime, nullable=True)  # 开具时间
    delivered_at = Column(DateTime, nullable=True)  # 送达时间

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "invoice_no": self.invoice_no,
            "invoice_type": self.invoice_type,
            "invoice_title": self.invoice_title,
            "tax_id": self.tax_id,
            "amount": self.amount,
            "tax_amount": self.tax_amount,
            "total_amount": self.total_amount,
            "receiver_name": self.receiver_name,
            "receiver_phone": self.receiver_phone,
            "receiver_address": self.receiver_address,
            "receiver_email": self.receiver_email,
            "status": self.status.value if self.status else None,
            "invoice_url": self.invoice_url,
            "delivery_status": self.delivery_status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
        }


class TrialRecordDB(Base):
    """试用记录数据库模型 - P6 试用管理"""
    __tablename__ = "trial_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 试用信息
    trial_tier = Column(String(20), nullable=False)  # pro/enterprise
    trial_start = Column(DateTime, nullable=False)
    trial_end = Column(DateTime, nullable=False)

    # 试用状态
    status = Column(String(20), default="active", index=True)  # active, expired, converted, cancelled

    # 转化信息
    converted_at = Column(DateTime, nullable=True)
    converted_tier = Column(String(20), nullable=True)  # 转化后的订阅等级

    # 取消信息
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "trial_tier": self.trial_tier,
            "trial_start": self.trial_start.isoformat(),
            "trial_end": self.trial_end.isoformat(),
            "status": self.status,
            "converted_at": self.converted_at.isoformat() if self.converted_at else None,
            "converted_tier": self.converted_tier,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancel_reason": self.cancel_reason,
            "created_at": self.created_at.isoformat(),
        }


class CompanyInvoiceInfoDB(Base):
    """企业发票信息数据库模型 - P6 发票管理"""
    __tablename__ = "company_invoice_info"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 企业信息
    company_name = Column(String(200), nullable=False)  # 公司名称
    tax_id = Column(String(50), nullable=False)  # 纳税人识别号
    company_address = Column(String(500), nullable=True)  # 公司地址
    company_phone = Column(String(50), nullable=True)  # 公司电话

    # 开户行信息
    bank_name = Column(String(200), nullable=True)  # 开户行名称
    bank_account = Column(String(50), nullable=True)  # 银行账号

    # 发票接收信息
    receiver_email = Column(String(255), nullable=True)  # 电子发票接收邮箱
    receiver_address = Column(String(500), nullable=True)  # 纸质发票收件地址
    receiver_phone = Column(String(50), nullable=True)  # 收件人电话

    # 发票类型偏好
    invoice_type_preference = Column(String(20), default="electronic")  # electronic/paper

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "tax_id": self.tax_id,
            "company_address": self.company_address,
            "company_phone": self.company_phone,
            "bank_name": self.bank_name,
            "bank_account": self.bank_account,
            "receiver_email": self.receiver_email,
            "receiver_address": self.receiver_address,
            "receiver_phone": self.receiver_phone,
            "invoice_type_preference": self.invoice_type_preference,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ==================== v1.6 商用增强 - 配额与计费模型 ====================


class TenantDB(Base):
    """租户数据库模型 - v1.6 多租户隔离增强"""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # 租户名称
    type = Column(SQLEnum(TenantType), default=TenantType.INDIVIDUAL)  # 租户类型

    # 租户配置
    max_users = Column(Integer, default=1)  # 最大用户数
    max_storage_gb = Column(Float, default=10)  # 最大存储空间 (GB)
    custom_domain = Column(String(255), nullable=True)  # 自定义域名
    custom_branding = Column(JSON, nullable=True)  # 自定义品牌配置 (logo, colors, etc.)

    # SSO 配置（企业版）
    sso_enabled = Column(Boolean, default=False)
    sso_provider = Column(String(50), nullable=True)  # okta, azure_ad, google_workspace
    sso_config = Column(JSON, nullable=True)  # SSO 配置详情

    # 状态
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value if self.type else None,
            "max_users": self.max_users,
            "max_storage_gb": self.max_storage_gb,
            "custom_domain": self.custom_domain,
            "custom_branding": self.custom_branding,
            "sso_enabled": self.sso_enabled,
            "sso_provider": self.sso_provider,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TenantUserDB(Base):
    """租户用户关联模型 - v1.6 多租户隔离"""
    __tablename__ = "tenant_users"

    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 用户角色
    role = Column(String(50), default="member")  # owner, admin, member, viewer

    # 权限配置
    permissions = Column(JSON, nullable=True)  # 自定义权限列表

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "role": self.role,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat(),
        }


class QuotaConfigDB(Base):
    """配额配置模型 - v1.6 精细化配额管理"""
    __tablename__ = "quota_configs"

    id = Column(String(36), primary_key=True, index=True)
    subscription_tier = Column(String(20), nullable=False, index=True)  # free/pro/enterprise

    # 配额维度
    feature_name = Column(String(100), nullable=False)  # 功能名称 (e.g., "daily_searches", "monthly_reports")
    quota_type = Column(SQLEnum(QuotaType), default=QuotaType.DAILY)
    limit_value = Column(Integer, nullable=False)  # 限制值 (-1 表示无限制)
    unit = Column(String(50), default="times")  # 单位

    # 超额处理策略
    overage_policy = Column(String(20), default="block")  # block-阻止，charge-按量计费，notify-仅通知
    overage_price = Column(Float, nullable=True)  # 超额单价（元/次）

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "subscription_tier": self.subscription_tier,
            "feature_name": self.feature_name,
            "quota_type": self.quota_type.value if self.quota_type else None,
            "limit_value": self.limit_value,
            "unit": self.unit,
            "overage_policy": self.overage_policy,
            "overage_price": self.overage_price,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class QuotaUsageDB(Base):
    """配额使用记录模型 - v1.6 配额使用追踪"""
    __tablename__ = "quota_usage"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

    # 使用详情
    feature_name = Column(String(100), nullable=False)
    quota_type = Column(SQLEnum(QuotaType), default=QuotaType.DAILY)
    used_count = Column(Integer, default=0)
    period_start = Column(DateTime, nullable=False)  # 周期开始
    period_end = Column(DateTime, nullable=False)  # 周期结束

    # 超额使用
    overage_count = Column(Integer, default=0)  # 超额使用次数
    overage_charge = Column(Float, default=0)  # 超额费用

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "feature_name": self.feature_name,
            "quota_type": self.quota_type.value if self.quota_type else None,
            "used_count": self.used_count,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "overage_count": self.overage_count,
            "overage_charge": self.overage_charge,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BillingAccountDB(Base):
    """计费账户模型 - v1.6 按量计费支持"""
    __tablename__ = "billing_accounts"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

    # 计费模式
    billing_mode = Column(SQLEnum(BillingMode), default=BillingMode.SUBSCRIPTION)

    # 账户余额（预付费/按量计费）
    balance = Column(Float, default=0)  # 账户余额
    credit_limit = Column(Float, default=0)  # 信用额度（后付费）

    # 充值信息
    total_recharged = Column(Float, default=0)  # 累计充值
    total_consumed = Column(Float, default=0)  # 累计消费

    # 自动充值配置
    auto_recharge_enabled = Column(Boolean, default=False)
    auto_recharge_threshold = Column(Float, default=10)  # 余额低于此值时自动充值
    auto_recharge_amount = Column(Float, default=100)  # 自动充值金额

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "billing_mode": self.billing_mode.value if self.billing_mode else None,
            "balance": self.balance,
            "credit_limit": self.credit_limit,
            "total_recharged": self.total_recharged,
            "total_consumed": self.total_consumed,
            "auto_recharge_enabled": self.auto_recharge_enabled,
            "auto_recharge_threshold": self.auto_recharge_threshold,
            "auto_recharge_amount": self.auto_recharge_amount,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BillingItemDB(Base):
    """计费项目模型 - v1.6 按量计费项目"""
    __tablename__ = "billing_items"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

    # 计费项目
    item_name = Column(String(100), nullable=False)  # 项目名称
    item_type = Column(String(50), nullable=False)  # api_call, storage, compute, export

    # 计费详情
    quantity = Column(Float, nullable=False)  # 使用数量
    unit_price = Column(Float, nullable=False)  # 单价
    total_amount = Column(Float, nullable=False)  # 总金额

    # 关联信息
    related_order_id = Column(String(36), nullable=True)  # 关联订单
    related_resource_id = Column(String(36), nullable=True)  # 关联资源 ID

    # 计费周期
    billing_period_start = Column(DateTime, nullable=True)
    billing_period_end = Column(DateTime, nullable=True)

    # 状态
    status = Column(String(20), default="pending")  # pending, billed, paid

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "item_name": self.item_name,
            "item_type": self.item_type,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_amount": self.total_amount,
            "related_order_id": self.related_order_id,
            "related_resource_id": self.related_resource_id,
            "billing_period_start": self.billing_period_start.isoformat() if self.billing_period_start else None,
            "billing_period_end": self.billing_period_end.isoformat() if self.billing_period_end else None,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


class RechargeRecordDB(Base):
    """充值记录模型 - v1.6 预付费充值"""
    __tablename__ = "recharge_records"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)  # 关联订单

    # 充值信息
    amount = Column(Float, nullable=False)
    bonus_amount = Column(Float, default=0)  # 赠送金额
    total_amount = Column(Float, nullable=False)  # 实际到账金额

    # 支付信息
    payment_method = Column(String(50), nullable=True)
    transaction_id = Column(String(128), nullable=True)

    # 状态
    status = Column(String(20), default="pending")  # pending, success, failed, refunded

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "bonus_amount": self.bonus_amount,
            "total_amount": self.total_amount,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class PackageDB(Base):
    """套餐包模型 - v1.6 预付费套餐包"""
    __tablename__ = "packages"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 套餐包名称
    code = Column(String(50), nullable=False, unique=True)  # 套餐包代码

    # 套餐包内容
    credits = Column(Integer, default=0)  # API 调用次数
    storage_gb = Column(Float, default=0)  # 存储空间 (GB)
    export_count = Column(Integer, default=0)  # 导出次数
    valid_days = Column(Integer, default=365)  # 有效期（天）

    # 价格
    original_price = Column(Float, nullable=False)  # 原价
    current_price = Column(Float, nullable=False)  # 现价

    # 状态
    is_active = Column(Boolean, default=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "credits": self.credits,
            "storage_gb": self.storage_gb,
            "export_count": self.export_count,
            "valid_days": self.valid_days,
            "original_price": self.original_price,
            "current_price": self.current_price,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class UserPackageDB(Base):
    """用户套餐包模型 - v1.6 用户购买的套餐包"""
    __tablename__ = "user_packages"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    package_id = Column(String(36), ForeignKey("packages.id"), nullable=False)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)

    # 关联
    package = relationship("PackageDB", backref="user_packages")

    # 套餐包内容
    credits_total = Column(Integer, default=0)
    credits_used = Column(Integer, default=0)
    storage_gb_total = Column(Float, default=0)
    storage_gb_used = Column(Float, default=0)
    export_count_total = Column(Integer, default=0)
    export_count_used = Column(Integer, default=0)

    # 有效期
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # 状态
    status = Column(String(20), default="active")  # active, expired, exhausted

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "package_id": self.package_id,
            "order_id": self.order_id,
            "credits_total": self.credits_total,
            "credits_used": self.credits_used,
            "credits_remaining": self.credits_total - self.credits_used,
            "storage_gb_total": self.storage_gb_total,
            "storage_gb_used": self.storage_gb_used,
            "storage_gb_remaining": self.storage_gb_total - self.storage_gb_used,
            "export_count_total": self.export_count_total,
            "export_count_used": self.export_count_used,
            "export_count_remaining": self.export_count_total - self.export_count_used,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
