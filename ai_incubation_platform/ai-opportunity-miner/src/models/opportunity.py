"""
商机模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum


class OpportunityType(str, Enum):
    MARKET = "market"
    PRODUCT = "product"
    PARTNERSHIP = "partnership"
    INVESTMENT = "investment"


class OpportunityStatus(str, Enum):
    NEW = "new"
    VALIDATED = "validated"
    EXPIRED = "expired"


class RiskLabel(str, Enum):
    """风险标签"""
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    REGULATORY = "regulatory"
    COMPETITIVE = "competitive"
    TECHNOLOGICAL = "technological"
    MARKET = "market"


class SourceType(str, Enum):
    """数据来源类型"""
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    PATENT = "patent"
    RECRUITMENT = "recruitment"
    INDUSTRY_REPORT = "industry_report"
    GOVERNMENT_DATA = "government_data"
    INTERNAL_DATA = "internal_data"
    AI_ANALYSIS = "ai_analysis"
    USER_CONTRIBUTION = "user_contribution"  # P7 用户贡献数据


class BusinessOpportunity(BaseModel):
    """商机模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    type: OpportunityType
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)  # AI 置信度 0-1
    potential_value: float = Field(0.0, ge=0.0)  # 潜在价值（估算）
    potential_value_currency: str = "CNY"  # 货币单位

    # 来源信息
    source_type: SourceType = SourceType.AI_ANALYSIS
    source_name: str = ""  # 具体来源名称，如网站名、报告名称
    source_url: str = ""  # 来源链接
    source_publish_date: Optional[datetime] = None  # 来源发布时间

    # 风险标签
    risk_labels: List[RiskLabel] = Field(default_factory=list)
    risk_score: float = Field(0.0, ge=0.0, le=1.0)  # 风险评分 0-1，越高风险越大
    risk_description: str = ""  # 风险详细描述

    # 验证信息
    validation_steps: List[str] = Field(default_factory=list)  # 建议的验证步骤
    validation_status: str = "pending"  # 验证状态: pending, in_progress, completed, failed
    validation_notes: str = ""  # 验证备注

    # 实体关联
    related_entities: List[Dict[str, str]] = Field(default_factory=list)  # 相关实体，如公司、产品、人物等

    tags: List[str] = Field(default_factory=list)
    status: OpportunityStatus = OpportunityStatus.NEW
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MarketTrend(BaseModel):
    """市场趋势模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    keyword: str
    trend_score: float  # 趋势分数 0-1
    growth_rate: float  # 增长率
    related_keywords: List[str] = Field(default_factory=list)
    data_points: List[Dict] = Field(default_factory=list)
    # 预留给 LLM 深度分析的额外结构化结果（用于 P1 趋势/竞品管线）
    extra: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
