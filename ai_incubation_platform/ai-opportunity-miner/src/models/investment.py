"""
投资关系链和股权穿透模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class InvestmentRound(str, Enum):
    """投资轮次"""
    ANGEL = "angel"  # 天使轮
    PRE_A = "pre_a"  # Pre-A 轮
    A = "a"  # A 轮
    B = "b"  # B 轮
    C = "c"  # C 轮
    D = "d"  # D 轮
    E = "e"  # E 轮
    F = "f"  # F 轮
    D_PLUS = "d_plus"  # D 轮及以上
    STRATEGIC = "strategic"  # 战略投资
    PE = "pe"  # PE 投资
    IPO = "ipo"  # IPO
    M_A = "m_a"  # 并购


class InvestorType(str, Enum):
    """投资机构类型"""
    VC = "vc"  # 风险投资
    PE = "pe"  # 私募股权
    ANGEL = "angel"  # 天使投资人
    CORPORATE = "corporate"  # 企业战投
    GOVERNMENT = "government"  # 政府基金
    FAMILY_OFFICE = "family_office"  # 家族办公室
    SOVEREIGN_WEALTH = "sovereign_wealth"  # 主权财富基金


class ShareholderType(str, Enum):
    """股东类型"""
    INDIVIDUAL = "individual"  # 自然人
    CORPORATE = "corporate"  # 企业法人
    INVESTMENT_FIRM = "investment_firm"  # 投资机构
    GOVERNMENT = "government"  # 政府/事业单位
    OTHER = "other"  # 其他


class InvestmentChain(BaseModel):
    """投资关系链模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 投资方信息
    investor_id: str
    investor_name: str
    investor_type: InvestorType = InvestorType.VC

    # 被投资方信息
    investee_id: str
    investee_name: str
    investee_industry: str = ""

    # 投资详情
    round: InvestmentRound
    amount: Optional[float] = None  # 投资金额
    amount_currency: str = "CNY"
    investment_date: Optional[datetime] = None
    announced_date: Optional[datetime] = None

    # 股权信息
    equity_ratio: Optional[float] = None  # 持股比例 (%)
    board_seat: bool = False  # 是否获得董事会席位

    # 投资状态
    status: str = "completed"  # completed, announced, rumored, failed

    # 来源信息
    source: str = ""  # 信息来源
    source_url: str = ""

    # 备注
    description: str = ""
    tags: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ShareholderNode(BaseModel):
    """股东节点模型（用于股权穿透图）"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 股东信息
    name: str
    type: ShareholderType = ShareholderType.INDIVIDUAL

    # 持股信息
    direct_ratio: float = 0.0  # 直接持股比例 (%)
    indirect_ratio: float = 0.0  # 间接持股比例 (%)
    total_ratio: float = 0.0  # 总持股比例 (%)

    # 控制权信息
    voting_ratio: Optional[float] = None  # 表决权比例 (%)
    is_actual_controller: bool = False  # 是否为实际控制人
    is_beneficial_owner: bool = False  # 是否为最终受益人

    # 层级信息
    level: int = 0  # 在股权穿透图中的层级
    parent_id: Optional[str] = None  # 父节点 ID

    # 详细信息
    company_id: Optional[str] = None  # 如果是公司股东，关联公司 ID
    identity_masked: Optional[str] = None  # 如果是自然人，掩码后的身份信息

    # 其他信息
    registered_capital: Optional[str] = None  # 注册资本（如果是公司）
    legal_representative: Optional[str] = None  # 法人代表（如果是公司）

    children: List["ShareholderNode"] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class EquityOwnership(BaseModel):
    """股权穿透结果模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 目标公司
    company_id: str
    company_name: str

    # 股权穿透图
    ownership_tree: Optional[ShareholderNode] = None

    # 最终受益人列表
    beneficial_owners: List[Dict] = Field(default_factory=list)
    # 格式：{"name": str, "total_ratio": float, "paths": [str]}

    # 实际控制人
    actual_controllers: List[Dict] = Field(default_factory=list)
    # 格式：{"name": str, "voting_ratio": float, "type": str}

    # 股权穿透图可视化数据
    visualization_data: Dict[str, Any] = Field(default_factory=dict)

    # 控制链分析
    control_chain_analysis: Dict[str, Any] = Field(default_factory=dict)
    # 包含：最长控制链、控制权层级数等

    # 风险识别
    risk_indicators: List[Dict] = Field(default_factory=list)
    # 格式：{"type": str, "description": str, "level": str}

    created_at: datetime = Field(default_factory=datetime.now)


class InvestmentNetwork(BaseModel):
    """投资网络图谱模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 网络节点
    nodes: List[Dict] = Field(default_factory=list)
    # 格式：{"id": str, "name": str, "type": str, "size": float, "category": str}

    # 网络边
    edges: List[Dict] = Field(default_factory=list)
    # 格式：{"source": str, "target": str, "type": str, "value": float, "label": str}

    # 网络统计
    network_stats: Dict[str, Any] = Field(default_factory=dict)
    # 包含：节点数、边数、密度、中心性等

    # 子群分析
    communities: List[Dict] = Field(default_factory=list)

    # 关键节点分析
    key_players: List[Dict] = Field(default_factory=list)
    # 格式：{"id": str, "name": str, "centrality": float, "role": str}

    created_at: datetime = Field(default_factory=datetime.now)


class InvestmentTrend(BaseModel):
    """投资趋势分析模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 分析维度
    dimension: str  # industry, region, round, etc.
    dimension_value: str

    # 时间范围
    start_date: datetime
    end_date: datetime

    # 趋势数据
    trend_data: List[Dict] = Field(default_factory=list)
    # 格式：{"period": str, "count": int, "amount": float}

    # 统计指标
    total_investments: int = 0
    total_amount: float = 0.0
    avg_investment: float = 0.0

    # 热门排行
    top_investors: List[Dict] = Field(default_factory=list)
    top_investees: List[Dict] = Field(default_factory=list)

    # 趋势判断
    trend_direction: str = "stable"  # up, down, stable
    growth_rate: float = 0.0

    # 预测
    forecast: Optional[Dict] = None

    created_at: datetime = Field(default_factory=datetime.now)
