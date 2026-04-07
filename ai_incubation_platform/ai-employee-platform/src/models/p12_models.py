"""
P12 高级匹配算法增强 - 数据模型

包含：
- 向量嵌入模型（用于语义匹配）
- 文化适配档案
- 匹配解释报告
- 历史表现增强模型
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


# ==================== 枚举类型 ====================

class CommunicationStyle(str, Enum):
    """沟通风格"""
    FREQUENT = "frequent"  # 频繁沟通
    MODERATE = "moderate"  # 适度沟通
    MINIMAL = "minimal"  # 最少沟通


class FeedbackStyle(str, Enum):
    """反馈风格"""
    DIRECT = "direct"  # 直接
    DIPLOMATIC = "diplomatic"  # 委婉


class WorkSchedulePreference(str, Enum):
    """工作时间偏好"""
    TRADITIONAL = "traditional"  # 朝九晚五
    FLEXIBLE = "flexible"  # 弹性工作
    NIGHT = "night"  # 夜猫子


class DecisionStyle(str, Enum):
    """决策风格"""
    DATA_DRIVEN = "data_driven"  # 数据驱动
    INTUITIVE = "intuitive"  # 直觉驱动


class CollaborationStyle(str, Enum):
    """协作风格"""
    INDEPENDENT = "independent"  # 独立工作
    COLLABORATIVE = "collaborative"  # 团队协作


class VectorModelVersion(str, Enum):
    """向量模型版本"""
    SENTENCE_TRANSFORMER_V1 = "sentence-transformer-v1.0"
    OPENAI_EMBEDDING_V3 = "openai-embedding-v3"
    CUSTOM_FINETUNED_V1 = "custom-finetuned-v1"


class PricingStrategy(str, Enum):
    """定价策略"""
    UNDERPRICED = "underpriced"  # 低价
    FAIR = "fair"  # 公平
    PREMIUM = "premium"  # 溢价
    OVERPRICED = "overpriced"  # 过高


class TrendDirection(str, Enum):
    """趋势方向"""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class ConfidenceLevel(str, Enum):
    """置信度级别"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ==================== 向量嵌入模型 ====================

class EmployeeVector(BaseModel):
    """员工技能向量"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    skill_vector: List[float]  # 嵌入向量（维度取决于使用的模型）
    vector_model_version: str = "sentence-transformer-v1.0"
    skill_tags: List[str] = Field(default_factory=list)  # 技能标签
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        table_name = "p12_employee_vectors"


class JobVector(BaseModel):
    """职位需求向量"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    job_vector: List[float]  # 嵌入向量
    vector_model_version: str = "sentence-transformer-v1.0"
    requirements_text: str = ""  # 原始需求文本
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        table_name = "p12_job_vectors"


class VectorSimilarityCache(BaseModel):
    """向量相似度缓存"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    job_id: str
    similarity_score: float  # 余弦相似度 0-1
    computed_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime  # 过期时间

    class Config:
        table_name = "p12_vector_cache"


# ==================== 文化适配档案 ====================


class CulturalFitProfile(BaseModel):
    """文化适配档案"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # 员工或雇主 ID
    user_type: str = "employee"  # employee 或 employer

    # 沟通风格
    communication_style: CommunicationStyle = CommunicationStyle.MODERATE
    communication_notes: str = ""

    # 反馈风格
    feedback_style: FeedbackStyle = FeedbackStyle.DIRECT
    feedback_notes: str = ""

    # 工作时间偏好
    work_schedule_preference: WorkSchedulePreference = WorkSchedulePreference.FLEXIBLE
    timezone: str = "UTC"
    working_hours_start: int = 9  # 开始时间（小时）
    working_hours_end: int = 18  # 结束时间（小时）

    # 决策风格
    decision_style: DecisionStyle = DecisionStyle.DATA_DRIVEN
    decision_notes: str = ""

    # 协作风格
    collaboration_style: CollaborationStyle = CollaborationStyle.COLLABORATIVE
    collaboration_notes: str = ""

    # 其他偏好
    meeting_preference: str = "video"  # video/voice/chat
    documentation_preference: str = "detailed"  # detailed/minimal

    # 评估分数（通过行为分析得出）
    responsiveness_score: float = 0.8  # 响应性 0-1
    flexibility_score: float = 0.8  # 灵活性 0-1
    proactiveness_score: float = 0.8  # 主动性 0-1

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        table_name = "p12_cultural_fit_profiles"


class CulturalFitMatch(BaseModel):
    """文化适配匹配结果"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    employer_id: str
    overall_fit_score: float  # 总体适配度 0-100

    # 各维度适配度
    communication_fit: float  # 沟通风格适配
    feedback_fit: float  # 反馈风格适配
    schedule_fit: float  # 时间适配
    decision_fit: float  # 决策风格适配
    collaboration_fit: float  # 协作风格适配

    # 适配详情
    strengths: List[str] = Field(default_factory=list)  # 适配优势
    potential_conflicts: List[str] = Field(default_factory=list)  # 潜在冲突
    suggestions: List[str] = Field(default_factory=list)  # 建议

    computed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        table_name = "p12_cultural_fit_matches"


# ==================== 历史表现增强模型 ====================

class PerformanceMetric(BaseModel):
    """单项表现指标"""
    metric_name: str
    value: float  # 指标值
    weight: float  # 权重
    time_decay_factor: float = 1.0  # 时间衰减因子
    weighted_score: float = 0.0  # 加权后分数


class ProjectComplexity(BaseModel):
    """项目复杂度"""
    project_id: str
    complexity_score: float  # 1-5 分
    complexity_factors: Dict[str, float] = Field(default_factory=dict)
    # 因素：technical_difficulty, scope_size, team_size, deadline_pressure


class PerformanceTrend(BaseModel):
    """表现趋势"""
    employee_id: str
    period_days: int  # 统计周期

    # 各时期分数
    recent_score: float  # 最近 period_days 天
    previous_score: float  # 上一个 period_days 天
    trend_direction: str  # "improving", "stable", "declining"
    trend_percentage: float  # 变化百分比

    # 趋势分析
    trend_analysis: str = ""

    computed_at: datetime = Field(default_factory=datetime.now)


class WeightedPerformanceScore(BaseModel):
    """加权表现分数"""
    employee_id: str
    overall_score: float  # 总体加权分数 0-100

    # 基础分数
    rating_score: float  # 评分分数
    completion_rate_score: float  # 完成率分数
    rehire_rate_score: float  # 复雇率分数
    on_time_delivery_score: float  # 准时交付分数

    # 调整因子
    time_decay_multiplier: float = 1.0  # 时间衰减乘数
    complexity_bonus: float = 1.0  # 复杂度奖励
    client_type_weight: float = 1.0  # 客户类型权重

    # 趋势
    trend: PerformanceTrend = None

    # 计算详情
    breakdown: Dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime = Field(default_factory=datetime.now)


# ==================== 薪资分析模型 ====================

class SalaryBenchmark(BaseModel):
    """薪资基准"""
    skill_category: str
    experience_level: str  # beginner/intermediate/advanced/expert

    # 市场薪资分布
    percentile_10: float  # 第 10 百分位
    percentile_25: float  # 第 25 百分位
    percentile_50: float  # 中位数
    percentile_75: float  # 第 75 百分位
    percentile_90: float  # 第 90 百分位

    # 统计样本
    sample_size: int
    currency: str = "USD"
    period: str = "hourly"  # hourly/monthly/yearly

    region: str = "global"  # 地区
    updated_at: datetime = Field(default_factory=datetime.now)


class EmployeeSalaryAnalysis(BaseModel):
    """员工薪资分析"""
    employee_id: str
    current_rate: float  # 当前时薪
    currency: str = "USD"

    # 市场定位
    market_percentile: float  # 市场分位数 0-100
    vs_median: float  # 相对于中位数的百分比
    pricing_strategy: str  # "underpriced", "fair", "premium", "overpriced"

    # 性价比评分
    value_score: float  # 性价比 0-100（考虑技能和表现）

    # 建议
    suggested_rate_min: float  # 建议最低薪资
    suggested_rate_max: float  # 建议最高薪资
    pricing_suggestions: List[str] = Field(default_factory=list)

    analyzed_at: datetime = Field(default_factory=datetime.now)


# ==================== 匹配解释报告 ====================

class MatchScoreBreakdown(BaseModel):
    """匹配分数分解"""
    skill_match: float  # 技能匹配度
    performance_match: float  # 表现匹配度
    cultural_fit: float  # 文化适配度
    price_fit: float  # 价格匹配度
    availability_match: float  # 可用性匹配度
    vector_similarity: float  # 向量相似度（v12 新增）
    weighted_score: float  # 加权后总分


class MatchStrength(BaseModel):
    """匹配优势"""
    category: str  # 类别
    description: str  # 描述
    impact_score: float  # 影响力 0-10
    evidence: str = ""  # 证据


class MatchRisk(BaseModel):
    """匹配风险"""
    category: str
    description: str
    severity: str  # "low", "medium", "high"
    mitigation: str = ""  # 缓解建议
    probability: float = 0.0  # 发生概率 0-1


class MatchExplanation(BaseModel):
    """匹配解释报告"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str
    employee_id: str
    job_id: str

    # 总体评分
    overall_score: float  # 0-100
    confidence_level: str  # "high", "medium", "low"
    confidence_score: float  # 置信度分数 0-1

    # 分数分解
    score_breakdown: MatchScoreBreakdown

    # 优势与风险
    strengths: List[MatchStrength] = Field(default_factory=list)
    risks: List[MatchRisk] = Field(default_factory=list)

    # 建议
    suggestions: List[str] = Field(default_factory=list)
    alternative_employees: List[str] = Field(default_factory=list)  # 替代员工 ID
    alternative_jobs: List[str] = Field(default_factory=list)  # 替代职位 ID

    # 可解释性详情
    explanation_text: str = ""  # 自然语言解释
    key_factors: List[str] = Field(default_factory=list)  # 关键因素

    generated_at: datetime = Field(default_factory=datetime.now)
    model_version: str = "v12.0.0"

    class Config:
        table_name = "p12_match_explanations"


# ==================== 内存存储类（用于测试和演示） ====================

class P12InMemoryStorage:
    """P12 数据内存存储"""

    def __init__(self):
        self.employee_vectors: Dict[str, EmployeeVector] = {}
        self.job_vectors: Dict[str, JobVector] = {}
        self.vector_cache: Dict[str, VectorSimilarityCache] = {}
        self.cultural_profiles: Dict[str, CulturalFitProfile] = {}
        self.cultural_matches: Dict[str, CulturalFitMatch] = {}
        self.performance_metrics: Dict[str, WeightedPerformanceScore] = {}
        self.salary_analyses: Dict[str, EmployeeSalaryAnalysis] = {}
        self.match_explanations: Dict[str, MatchExplanation] = {}

    def save_employee_vector(self, vector: EmployeeVector):
        """保存员工向量"""
        self.employee_vectors[vector.employee_id] = vector

    def get_employee_vector(self, employee_id: str) -> Optional[EmployeeVector]:
        """获取员工向量"""
        return self.employee_vectors.get(employee_id)

    def save_job_vector(self, vector: JobVector):
        """保存职位向量"""
        self.job_vectors[vector.job_id] = vector

    def get_job_vector(self, job_id: str) -> Optional[JobVector]:
        """获取职位向量"""
        return self.job_vectors.get(job_id)

    def save_cultural_profile(self, profile: CulturalFitProfile):
        """保存文化档案"""
        self.cultural_profiles[profile.user_id] = profile

    def get_cultural_profile(self, user_id: str) -> Optional[CulturalFitProfile]:
        """获取文化档案"""
        return self.cultural_profiles.get(user_id)

    def save_match_explanation(self, explanation: MatchExplanation):
        """保存匹配解释"""
        self.match_explanations[explanation.id] = explanation

    def get_match_explanation(self, match_id: str) -> Optional[MatchExplanation]:
        """获取匹配解释"""
        return self.match_explanations.get(match_id)


# 全局存储实例
p12_storage = P12InMemoryStorage()
