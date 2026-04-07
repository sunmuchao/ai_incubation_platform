"""
薪酬管理数据模型。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class SalaryRange(BaseModel):
    """薪资范围。"""
    min_salary: float
    max_salary: float
    median_salary: float
    percentile_25: float
    percentile_75: float
    currency: str = "CNY"
    period: str = "monthly"  # hourly, daily, monthly, yearly


class ExperienceLevel(str, Enum):
    """经验级别。"""
    ENTRY = "entry"  # 0-2 年
    JUNIOR = "junior"  # 2-5 年
    MID = "mid"  # 5-10 年
    SENIOR = "senior"  # 10-15 年
    EXPERT = "expert"  # 15+ 年


class WorkMode(str, Enum):
    """工作模式。"""
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"


class IndustryType(str, Enum):
    """行业类型。"""
    TECH = "tech"  # 互联网/科技
    FINANCE = "finance"  # 金融
    HEALTHCARE = "healthcare"  # 医疗
    EDUCATION = "education"  # 教育
    RETAIL = "retail"  # 零售
    MANUFACTURING = "manufacturing"  # 制造
    MEDIA = "media"  # 媒体
    OTHER = "other"


class BenefitType(str, Enum):
    """福利类型。"""
    INSURANCE = "insurance"  # 保险
    STOCK = "stock"  # 股票/期权
    ALLOWANCE = "allowance"  # 补贴
    PAID_LEAVE = "paid_leave"  # 带薪休假
    TRAINING = "training"  # 培训
    WELLNESS = "wellness"  # 健康福利
    RETIREMENT = "retirement"  # 退休金


class TransparencyLevel(str, Enum):
    """薪酬透明度级别。"""
    PUBLIC = "public"  # 完全公开
    LIMITED = "limited"  # 部分公开（仅对投标人）
    PRIVATE = "private"  # 保密


# ===== 薪酬调查模型 =====

class CompensationSurvey(BaseModel):
    """薪酬调查记录。"""
    survey_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 调查维度
    skill: str  # 技能名称
    industry: Optional[IndustryType] = None  # 行业
    location: Optional[str] = None  # 地区
    experience_level: Optional[ExperienceLevel] = None  # 经验级别
    work_mode: Optional[WorkMode] = None  # 工作模式

    # 薪酬数据
    salary_range: SalaryRange
    sample_size: int = 0  # 样本数量
    data_freshness: datetime = Field(default_factory=datetime.now)  # 数据新鲜度

    # 趋势分析
    yoy_growth: Optional[float] = None  # 同比增长率
    mom_growth: Optional[float] = None  # 环比增长率

    created_at: datetime = Field(default_factory=datetime.now)


class SalaryBenchmark(BaseModel):
    """薪资基准数据。"""
    benchmark_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 基准维度
    job_title: str  # 职位名称
    skill: str  # 核心技能
    industry: IndustryType
    location: str  # 城市
    experience_level: ExperienceLevel
    work_mode: WorkMode

    # 基准数据
    salary_range: SalaryRange
    confidence_score: float = 0.0  # 置信度分数（0-1）
    sample_count: int = 0

    # 更新时间
    updated_at: datetime = Field(default_factory=datetime.now)


# ===== 薪资谈判模型 =====

class NegotiationPosition(str, Enum):
    """谈判立场。"""
    EMPLOYER = "employer"  # 雇主视角
    WORKER = "worker"  # 工人视角


class NegotiationAdvice(BaseModel):
    """薪资谈判建议。"""
    advice_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 谈判上下文
    position: NegotiationPosition
    job_title: str
    worker_id: Optional[str] = None
    employer_id: Optional[str] = None

    # 市场基准
    market_range: SalaryRange
    worker_current_salary: Optional[float] = None
    worker_expected_salary: Optional[float] = None

    # 谈判建议
    suggested_offer: float  # 建议报价
    negotiation_range: tuple  # (最低可接受，最高可接受)
    walk_away_price: Optional[float] = None  # walk away 价格

    # 谈判策略
    strategies: List[str] = []  # 谈判策略建议
    leverage_points: List[str] = []  # 议价点
    talking_points: List[str] = []  # 谈判话术

    # 工人优势分析（工人视角）
    worker_strengths: List[str] = []
    unique_value_props: List[str] = []

    created_at: datetime = Field(default_factory=datetime.now)


# ===== 调薪建议模型 =====

class AdjustmentReason(str, Enum):
    """调薪原因。"""
    PERFORMANCE = "performance"  # 绩效优秀
    MARKET = "market"  # 市场变化
    PROMOTION = "promotion"  # 晋升
    TENURE = "tenure"  # 年资
    RETENTION = "retention"  # 留任
    INFLATION = "inflation"  # 通胀调整


class SalaryAdjustment(BaseModel):
    """调薪建议记录。"""
    adjustment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 调薪对象
    worker_id: str
    current_salary: float
    currency: str = "CNY"

    # 调薪原因
    reason: AdjustmentReason
    reason_details: Optional[str] = None

    # 调薪建议
    suggested_new_salary: float
    increase_amount: float
    increase_percentage: float

    # 调薪依据
    performance_score: Optional[float] = None  # 绩效分数
    market_percentile: Optional[float] = None  # 市场百分位
    peer_comparison: Optional[Dict] = None  # 同级对比

    # 生效日期
    effective_date: Optional[datetime] = None

    # 审批状态
    status: str = "draft"  # draft, pending, approved, rejected

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ===== 福利管理模型 =====

class InsurancePlan(BaseModel):
    """保险计划。"""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_name: str
    insurance_type: str  # health, dental, vision, life, disability
    coverage_amount: float  # 保额
    monthly_premium: float  # 月保费
    employer_contribution_rate: float = 1.0  # 雇主承担比例（0-1）
    deductible: float = 0.0  # 自付额
    co_pay_rate: float = 0.0  # 共付比例


class StockOption(BaseModel):
    """股票期权。"""
    grant_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    shares: int  # 期权股数
    strike_price: float  # 行权价
    current_price: float  # 当前股价
    grant_date: datetime  # 授予日期
    vesting_start: datetime  # 归属开始日期
    vesting_duration_years: int = 4  # 归属期限（年）
    cliff_months: int = 12  # 悬崖期（月）
    exercise_window_years: int = 10  # 行权窗口（年）

    @property
    def vested_percentage(self) -> float:
        """计算已归属比例（简化版）。"""
        from datetime import datetime
        now = datetime.now()
        if now < self.vesting_start:
            return 0.0
        if now >= self.vesting_start:
            months_since_grant = (now - self.vesting_start).days / 30
            if months_since_grant < self.cliff_months:
                return 0.0
            return min(1.0, months_since_grant / (self.vesting_duration_years * 12))
        return 0.0

    @property
    def intrinsic_value(self) -> float:
        """计算内在价值。"""
        return max(0, self.current_price - self.strike_price) * self.shares


class Allowance(BaseModel):
    """补贴。"""
    allowance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    allowance_type: str  # transportation, meal, communication, housing, remote_work
    amount: float
    frequency: str = "monthly"  # one_time, monthly, yearly
    conditions: Optional[str] = None  # 发放条件


class BenefitsPackage(BaseModel):
    """福利包。"""
    package_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    package_name: str

    # 福利组成
    insurance_plans: List[InsurancePlan] = []
    stock_options: List[StockOption] = []
    allowances: List[Allowance] = []
    paid_leave_days: int = 0  # 带薪休假天数
    training_budget: float = 0.0  # 培训预算
    wellness_budget: float = 0.0  # 健康预算

    # 总价值
    @property
    def total_annual_value(self) -> float:
        """计算年度总福利价值。"""
        insurance_value = sum(
            plan.monthly_premium * plan.employer_contribution_rate * 12
            for plan in self.insurance_plans
        )
        stock_value = sum(
            opt.intrinsic_value / self.vesting_duration_years
            for opt in self.stock_options
            if hasattr(self, 'vesting_duration_years')
        )
        allowance_value = sum(
            allowance.amount * (12 if allowance.frequency == "monthly" else 1)
            for allowance in self.allowances
        )
        return insurance_value + stock_value + allowance_value + self.training_budget + self.wellness_budget

    created_at: datetime = Field(default_factory=datetime.now)


# ===== 薪酬透明度模型 =====

class CompensationTransparency(BaseModel):
    """薪酬透明度设置。"""
    transparency_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 关联对象
    task_id: Optional[str] = None
    employer_id: Optional[str] = None

    # 透明度级别
    level: TransparencyLevel = TransparencyLevel.PRIVATE

    # 公开内容
    show_salary_range: bool = False
    show_benefits: bool = False
    show_negotiable: bool = True

    # 公开范围（如果 level 是 limited）
    visible_to_bidders: bool = False
    visible_after_acceptance: bool = False

    # 薪酬公平性标记
    equity_verified: bool = False  # 是否通过公平性验证
    last_equity_audit: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ===== 薪酬公平性分析模型 =====

class EquityAnalysis(BaseModel):
    """薪酬公平性分析报告。"""
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 分析范围
    employer_id: Optional[str] = None
    department: Optional[str] = None
    job_family: Optional[str] = None

    # 分析周期
    start_date: datetime
    end_date: datetime

    # 公平性指标
    gender_pay_gap: Optional[float] = None  # 性别薪酬差距（百分比）
    ethnicity_pay_gap: Optional[float] = None  # 种族薪酬差距
    age_pay_gap: Optional[float] = None  # 年龄薪酬差距

    # 同工同酬分析
    equal_pay_violations: List[Dict] = []  #  violations 列表

    # 总体公平性评分
    equity_score: float = 0.0  # 0-100

    # 改进建议
    recommendations: List[str] = []

    created_at: datetime = Field(default_factory=datetime.now)


# ===== API 请求/响应模型 =====

class SalaryBenchmarkRequest(BaseModel):
    """薪资基准查询请求。"""
    job_title: Optional[str] = None
    skill: str
    industry: Optional[IndustryType] = None
    location: Optional[str] = None
    experience_level: Optional[ExperienceLevel] = None
    work_mode: Optional[WorkMode] = None


class SalarySurveyRequest(BaseModel):
    """薪酬调查请求。"""
    skills: List[str] = []
    industries: List[IndustryType] = []
    locations: List[str] = []
    experience_levels: List[ExperienceLevel] = []


class NegotiationAdviceRequest(BaseModel):
    """谈判建议请求。"""
    position: NegotiationPosition
    job_title: str
    worker_id: Optional[str] = None
    employer_id: Optional[str] = None
    skills: List[str] = []
    experience_years: Optional[int] = None
    current_salary: Optional[float] = None
    expected_salary: Optional[float] = None
    location: Optional[str] = None


class RaiseRecommendationRequest(BaseModel):
    """调薪建议请求。"""
    worker_id: str
    current_salary: float
    reasons: List[AdjustmentReason] = [AdjustmentReason.PERFORMANCE, AdjustmentReason.MARKET]


class BenefitsPackageRequest(BaseModel):
    """福利包请求。"""
    package_name: str
    budget: Optional[float] = None
    employee_count: Optional[int] = None
    preferences: Dict = {}


class EquityAnalysisRequest(BaseModel):
    """公平性分析请求。"""
    employer_id: Optional[str] = None
    include_gender: bool = True
    include_ethnicity: bool = True
    include_age: bool = False
    job_family: Optional[str] = None
