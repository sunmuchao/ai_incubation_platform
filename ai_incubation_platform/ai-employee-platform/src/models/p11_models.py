"""
P11: AI 员工市场增强模型
版本：v11.0.0
功能：排行榜、精选推荐、技能趋势、个性化推荐
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid


class RankingCategory(str, Enum):
    """排行榜分类"""
    OVERALL = "overall"  # 综合排行榜
    BY_SKILL = "by_skill"  # 按技能分类
    BY_INDUSTRY = "by_industry"  # 按行业分类
    NEWCOMER = "newcomer"  # 新人榜
    FASTEST_GROWING = "fastest_growing"  # 增长最快榜


class RankingPeriod(str, Enum):
    """排行榜周期"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL_TIME = "all_time"


class RecommendationType(str, Enum):
    """推荐类型"""
    PERSONALIZED = "personalized"  # 个性化推荐
    TRENDING = "trending"  # 热门趋势
    NEW_ARRIVAL = "new_arrival"  # 新上架
    SIMILAR = "similar"  # 相似推荐
    PREMIUM = "premium"  # 精选推荐


class MarketRanking(BaseModel):
    """市场排行榜模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: RankingCategory  # 排行榜分类
    period: RankingPeriod  # 周期
    skill_tag: Optional[str] = None  # 技能标签（当 category=BY_SKILL 时）
    industry: Optional[str] = None  # 行业（当 category=BY_INDUSTRY 时）

    # 排名数据
    rankings: List[Dict[str, Any]] = Field(default_factory=list)
    # 格式：[{"rank": 1, "employee_id": "xxx", "score": 98.5, "change": "+2"}, ...]

    # 计算时间
    calculated_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime  # 过期时间
    is_active: bool = True

    # 元数据
    total_employees: int = 0  # 参与排名的员工总数
    algorithm_version: str = "v11.0.0"  # 排名算法版本


class FeaturedEmployee(BaseModel):
    """精选 AI 员工模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    reason: str  # 推荐理由
    featured_type: str  # 精选类型：editor_pick, top_rated, best_value, trending
    priority: int = 0  # 优先级，数字越大越靠前

    # 展示信息
    highlight_title: Optional[str] = None  # 高亮标题
    highlight_description: Optional[str] = None  # 高亮描述
    badge: Optional[str] = None  # 徽章标识

    # 时间控制
    start_at: datetime
    end_at: datetime

    # 状态
    is_active: bool = True
    click_count: int = 0  # 点击次数
    conversion_count: int = 0  # 转化次数

    created_by: str  # 创建者 ID（运营人员）
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SkillTrend(BaseModel):
    """技能趋势模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_name: str
    category: str

    # 趋势数据
    trend_score: float  # 趋势得分 (0-100)
    growth_rate: float  # 增长率 (%)
    demand_index: float  # 需求指数
    supply_index: float  # 供给指数

    # 统计数据
    search_count: int = 0  # 搜索次数
    hire_count: int = 0  # 雇佣次数
    avg_hourly_rate: float = 0.0  # 平均时薪

    # 趋势方向
    trend_direction: str  # "up", "down", "stable"
    rank_change: int = 0  # 排名变化

    # 时间周期
    period_start: datetime
    period_end: datetime

    calculated_at: datetime = Field(default_factory=datetime.now)


class MarketInsight(BaseModel):
    """市场洞察模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    insight_type: str  # "hot_skills", "emerging_categories", "price_trends"

    # 洞察内容
    title: str
    description: str
    data_points: List[Dict[str, Any]] = Field(default_factory=list)

    # 可视化数据
    chart_type: Optional[str] = None  # "line", "bar", "pie"
    chart_data: Optional[Dict[str, Any]] = None

    # 时间
    period: str  # "7d", "30d", "90d"
    generated_at: datetime = Field(default_factory=datetime.now)


class UserBehavior(BaseModel):
    """用户行为记录模型（用于个性化推荐）"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    tenant_id: str

    # 行为类型
    behavior_type: str  # "view", "search", "hire", "favorite"
    target_type: str  # "employee", "skill", "category"
    target_id: str  # 目标 ID

    # 行为上下文
    context: Dict[str, Any] = Field(default_factory=dict)
    # 例如：{"search_query": "数据分析", "filters": {"min_rating": 4.0}}

    # 行为结果
    result: Optional[str] = None  # "converted", "ignored", "bookmarked"

    timestamp: datetime = Field(default_factory=datetime.now)


class PersonalizedRecommendation(BaseModel):
    """个性化推荐结果"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    recommendation_type: RecommendationType

    # 推荐列表
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    # 格式：[{"employee_id": "xxx", "score": 0.95, "reason": "与你雇佣过的 AI 员工技能相似"}, ...]

    # 推荐算法
    algorithm: str  # "collaborative_filtering", "content_based", "hybrid"
    factors: Dict[str, float] = Field(default_factory=dict)
    # 例如：{"skill_match": 0.4, "price_preference": 0.2, "rating": 0.2, "past_hires": 0.2}

    generated_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime


# 请求模型
class RankingQueryRequest(BaseModel):
    """排行榜查询请求"""
    category: RankingCategory = RankingCategory.OVERALL
    period: RankingPeriod = RankingPeriod.WEEKLY
    skill_tag: Optional[str] = None
    industry: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)


class FeaturedEmployeeCreateRequest(BaseModel):
    """创建精选员工请求"""
    employee_id: str
    reason: str
    featured_type: str
    priority: int = 0
    highlight_title: Optional[str] = None
    highlight_description: Optional[str] = None
    badge: Optional[str] = None
    duration_days: int = 7


class MarketSearchRequest(BaseModel):
    """市场搜索请求（增强版）"""
    query: Optional[str] = None
    skills: Optional[List[str]] = Field(default_factory=list)
    categories: Optional[List[str]] = Field(default_factory=list)
    min_rating: float = Field(default=0, ge=0, le=5)
    max_hourly_rate: Optional[float] = None
    min_hourly_rate: Optional[float] = None
    available_only: bool = True
    sort_by: str = Field(default="rating", pattern="^(rating|earnings|jobs|price|newest)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MarketStatsResponse(BaseModel):
    """市场统计响应"""
    total_employees: int
    active_employees: int
    total_categories: int
    total_skills: int
    avg_hourly_rate: float
    median_hourly_rate: float
    top_categories: List[Dict[str, Any]]
    trending_skills: List[str]
    new_employees_today: int
    new_employees_week: int


# 响应模型
class RankingResponse(BaseModel):
    """排行榜响应"""
    category: str
    period: str
    skill_tag: Optional[str] = None
    industry: Optional[str] = None
    rankings: List[Dict[str, Any]]
    total_employees: int
    calculated_at: datetime
    expires_at: datetime
    algorithm_version: str


class FeaturedListResponse(BaseModel):
    """精选列表响应"""
    featured_employees: List[Dict[str, Any]]
    total_count: int
    has_more: bool = False


class TrendingSkillsResponse(BaseModel):
    """热门技能响应"""
    skills: List[Dict[str, Any]]
    period: str
    total_count: int


class PersonalizedRecommendationResponse(BaseModel):
    """个性化推荐响应"""
    user_id: str
    recommendation_type: str
    recommendations: List[Dict[str, Any]]
    algorithm: str
    generated_at: datetime
    expires_at: datetime
