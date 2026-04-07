"""
v1.7 AI 驱动增强 - 商机评分算法升级与趋势预测可视化
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/api/v1.7", tags=["v1.7 ML 增强"])

# ==================== 请求/响应模型 ====================

class EnhancedScoreRequest(BaseModel):
    """增强商机评分请求"""
    opportunity_id: str
    factors: Optional[List[str]] = Field(default=None, description="评分因子列表")
    include_explanation: bool = Field(default=True, description="是否包含解释")

class EnhancedScoreResponse(BaseModel):
    """增强商机评分响应"""
    opportunity_id: str
    total_score: float
    score_level: str  # S/A/B/C/D
    factor_scores: Dict[str, float]
    explanation: Dict[str, str]
    confidence: float
    risk_factors: List[str]
    recommended_actions: List[str]

class TrendPredictionRequest(BaseModel):
    """趋势预测请求"""
    industry: str
    horizon_days: int = Field(default=90, ge=7, le=365)
    include_confidence: bool = Field(default=True)

class TrendPredictionPoint(BaseModel):
    """趋势预测点"""
    date: str
    predicted_value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    confidence: Optional[float] = None

class TrendPredictionResponse(BaseModel):
    """趋势预测响应"""
    industry: str
    prediction_horizon_days: int
    current_value: float
    predicted_end_value: float
    predicted_growth_rate: float
    trend_direction: str  # upward/downward/stable
    prediction_points: List[TrendPredictionPoint]
    key_drivers: List[str]
    risk_factors: List[str]

class OpportunityComparisonRequest(BaseModel):
    """商机对比请求"""
    opportunity_ids: List[str] = Field(..., min_items=2, max_items=5)
    comparison_factors: Optional[List[str]] = None

class OpportunityComparisonResponse(BaseModel):
    """商机对比响应"""
    opportunities: List[Dict[str, Any]]
    comparison_matrix: Dict[str, Dict[str, float]]
    ranking: List[Dict[str, Any]]
    insights: List[str]

class MLInsight(BaseModel):
    """ML 洞察"""
    insight_type: str
    title: str
    description: str
    confidence: float
    data_points: int
    actionability: str  # high/medium/low

class MLInsightsResponse(BaseModel):
    """ML 洞察列表响应"""
    insights: List[MLInsight]
    generated_at: str
    model_version: str

# ==================== 模拟数据 ====================

def _generate_enhanced_score(opportunity_id: str, include_explanation: bool = True) -> EnhancedScoreResponse:
    """生成增强商机评分"""
    # 10 因子评分模型
    factors = {
        "market_size": random.uniform(60, 95),
        "growth_rate": random.uniform(50, 98),
        "competition_intensity": random.uniform(40, 90),
        "technology_maturity": random.uniform(55, 92),
        "policy_support": random.uniform(45, 88),
        "capital_hotness": random.uniform(50, 95),
        "team_strength": random.uniform(55, 90),
        "business_model": random.uniform(50, 88),
        "barrier_to_entry": random.uniform(45, 85),
        "exit_potential": random.uniform(50, 92),
    }

    # 计算加权总分
    weights = {
        "market_size": 0.15,
        "growth_rate": 0.15,
        "competition_intensity": 0.10,
        "technology_maturity": 0.10,
        "policy_support": 0.10,
        "capital_hotness": 0.12,
        "team_strength": 0.10,
        "business_model": 0.08,
        "barrier_to_entry": 0.05,
        "exit_potential": 0.05,
    }

    total_score = sum(factors[k] * weights[k] for k in factors)

    # 确定等级
    if total_score >= 90:
        score_level = "S"
    elif total_score >= 80:
        score_level = "A"
    elif total_score >= 70:
        score_level = "B"
    elif total_score >= 60:
        score_level = "C"
    else:
        score_level = "D"

    explanation = {}
    if include_explanation:
        top_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:3]
        for factor, score in top_factors:
            if score >= 85:
                explanation[factor] = f"{factor} 表现优异 (得分：{score:.1f})，是该商机的主要优势"
            elif score >= 70:
                explanation[factor] = f"{factor} 表现良好 (得分：{score:.1f})，具有竞争力"
            else:
                explanation[factor] = f"{factor} 表现一般 (得分：{score:.1f})，有提升空间"

    # 风险因素
    risk_factors = []
    if factors["competition_intensity"] < 60:
        risk_factors.append("竞争激烈")
    if factors["technology_maturity"] < 65:
        risk_factors.append("技术成熟度低")
    if factors["policy_support"] < 60:
        risk_factors.append("政策支持不足")
    if factors["barrier_to_entry"] < 55:
        risk_factors.append("进入壁垒低")

    # 推荐行动
    recommended_actions = []
    if total_score >= 80:
        recommended_actions.append("建议优先推进尽职调查")
    if factors["market_size"] >= 85:
        recommended_actions.append("市场规模大，建议快速抢占市场份额")
    if factors["competition_intensity"] < 60:
        recommended_actions.append("竞争激烈，建议差异化定位")
    if not recommended_actions:
        recommended_actions.append("建议持续观察，等待更佳时机")

    return EnhancedScoreResponse(
        opportunity_id=opportunity_id,
        total_score=round(total_score, 2),
        score_level=score_level,
        factor_scores={k: round(v, 2) for k, v in factors.items()},
        explanation=explanation,
        confidence=random.uniform(0.75, 0.95),
        risk_factors=risk_factors,
        recommended_actions=recommended_actions,
    )

def _generate_trend_prediction(industry: str, horizon_days: int) -> TrendPredictionResponse:
    """生成趋势预测"""
    # 当前值（模拟）
    current_value = random.uniform(100, 1000)

    # 预测增长率
    growth_rate = random.uniform(-0.1, 0.3)
    predicted_end_value = current_value * (1 + growth_rate)

    # 趋势方向
    if growth_rate > 0.1:
        trend_direction = "upward"
    elif growth_rate < -0.05:
        trend_direction = "downward"
    else:
        trend_direction = "stable"

    # 生成预测点
    prediction_points = []
    for i in range(horizon_days // 7 + 1):
        days = i * 7
        if days > horizon_days:
            break
        progress = days / horizon_days
        predicted_value = current_value * (1 + growth_rate * progress)
        # 添加置信区间
        uncertainty = random.uniform(0.05, 0.15) * progress
        lower_bound = predicted_value * (1 - uncertainty)
        upper_bound = predicted_value * (1 + uncertainty)
        confidence = 0.95 - (uncertainty * 2)

        prediction_points.append(TrendPredictionPoint(
            date=(datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"),
            predicted_value=round(predicted_value, 2),
            lower_bound=round(lower_bound, 2),
            upper_bound=round(upper_bound, 2),
            confidence=round(confidence, 3),
        ))

    # 关键驱动因素
    key_drivers = [
        f"{industry}技术创新加速",
        "资本市场关注度提升",
        "政策支持力度加大",
        "市场需求持续增长",
        "产业链协同发展",
    ][:random.randint(3, 5)]

    # 风险因素
    risk_factors = [
        "宏观经济不确定性",
        "行业竞争加剧",
        "技术路线变更风险",
        "监管政策变化",
    ][:random.randint(2, 3)]

    return TrendPredictionResponse(
        industry=industry,
        prediction_horizon_days=horizon_days,
        current_value=round(current_value, 2),
        predicted_end_value=round(predicted_end_value, 2),
        predicted_growth_rate=round(growth_rate * 100, 2),
        trend_direction=trend_direction,
        prediction_points=prediction_points,
        key_drivers=key_drivers,
        risk_factors=risk_factors,
    )

def _generate_ml_insights() -> MLInsightsResponse:
    """生成 ML 洞察"""
    insights = [
        MLInsight(
            insight_type="trend_detection",
            title="新能源储能行业热度上升",
            description="过去 30 天内，储能相关投资事件增长 45%，媒体提及率增长 62%",
            confidence=0.89,
            data_points=156,
            actionability="high",
        ),
        MLInsight(
            insight_type="anomaly_detection",
            title="AI 芯片领域投资异常活跃",
            description="本周 AI 芯片领域投资事件达到过去 6 个月平均值的 2.3 倍",
            confidence=0.92,
            data_points=89,
            actionability="high",
        ),
        MLInsight(
            insight_type="correlation",
            title="政策发布与行业投资呈正相关",
            description="过去 6 个月数据显示，政策发布后 2 周内行业投资平均增长 28%",
            confidence=0.76,
            data_points=234,
            actionability="medium",
        ),
        MLInsight(
            insight_type="prediction",
            title="下季度生物医药预计升温",
            description="基于历史模式和当前信号，预测下季度生物医药领域投资将增长 15-25%",
            confidence=0.68,
            data_points=312,
            actionability="medium",
        ),
    ]

    return MLInsightsResponse(
        insights=insights[:random.randint(2, len(insights))],
        generated_at=datetime.now().isoformat(),
        model_version="v1.7.0",
    )

# ==================== API 端点 ====================

@router.post("/ml/enhanced-score", response_model=EnhancedScoreResponse, summary="增强商机评分")
async def enhanced_opportunity_score(request: EnhancedScoreRequest):
    """
    对商机进行增强评分（10 因子模型）

    评分因子：
    - market_size: 市场规模
    - growth_rate: 增长率
    - competition_intensity: 竞争强度
    - technology_maturity: 技术成熟度
    - policy_support: 政策支持
    - capital_hotness: 资本热度
    - team_strength: 团队实力
    - business_model: 商业模式
    - barrier_to_entry: 进入壁垒
    - exit_potential: 退出潜力
    """
    return _generate_enhanced_score(
        request.opportunity_id,
        include_explanation=request.include_explanation,
    )

@router.post("/ml/trend-prediction", response_model=TrendPredictionResponse, summary="趋势预测")
async def trend_prediction(request: TrendPredictionRequest):
    """
    预测行业趋势

    返回：
    - 当前值与预测值
    - 增长率预测
    - 趋势方向（上升/下降/稳定）
    - 置信区间
    - 关键驱动因素
    - 风险因素
    """
    return _generate_trend_prediction(
        request.industry,
        request.horizon_days,
    )

@router.post("/ml/compare-opportunities", response_model=OpportunityComparisonResponse, summary="商机对比")
async def compare_opportunities(request: OpportunityComparisonRequest):
    """
    对比多个商机

    返回：
    - 各商机的详细评分
    - 对比矩阵
    - 排名
    - 洞察建议
    """
    opportunities = []
    for opp_id in request.opportunity_ids:
        score_data = _generate_enhanced_score(opp_id)
        opportunities.append({
            "opportunity_id": opp_id,
            "total_score": score_data.total_score,
            "score_level": score_data.score_level,
            "top_factors": dict(sorted(score_data.factor_scores.items(), key=lambda x: x[1], reverse=True)[:3]),
            "risk_factors": score_data.risk_factors,
        })

    # 生成对比矩阵
    comparison_matrix = {}
    for opp in opportunities:
        comparison_matrix[opp["opportunity_id"]] = opp["top_factors"]

    # 生成排名
    ranking = sorted(opportunities, key=lambda x: x["total_score"], reverse=True)
    for i, opp in enumerate(ranking):
        opp["rank"] = i + 1

    # 生成洞察
    insights = []
    if len(ranking) >= 2:
        best = ranking[0]
        worst = ranking[-1]
        insights.append(f"{best['opportunity_id']} 综合得分最高 ({best['total_score']})")
        insights.append(f"最高分与最低分差距：{best['total_score'] - worst['total_score']:.1f}")
        insights.append("建议优先关注排名靠前的商机")

    return OpportunityComparisonResponse(
        opportunities=opportunities,
        comparison_matrix=comparison_matrix,
        ranking=ranking,
        insights=insights,
    )

@router.get("/ml/insights", response_model=MLInsightsResponse, summary="ML 洞察")
async def get_ml_insights():
    """
    获取 ML 驱动的洞察

    包括：
    - 趋势检测
    - 异常检测
    - 相关性分析
    - 预测性洞察
    """
    return _generate_ml_insights()

@router.get("/ml/hot-industries", response_model=List[Dict[str, Any]], summary="热门行业")
async def get_hot_industries(limit: int = 10):
    """获取当前热门行业"""
    industries = [
        {"name": "新能源储能", "hot_score": 95.2, "growth_rate": 45.3, "trend": "upward"},
        {"name": "AI 芯片", "hot_score": 92.8, "growth_rate": 38.7, "trend": "upward"},
        {"name": "生物医药", "hot_score": 88.5, "growth_rate": 25.4, "trend": "upward"},
        {"name": "智能制造", "hot_score": 85.3, "growth_rate": 22.1, "trend": "upward"},
        {"name": "企业服务 SaaS", "hot_score": 82.1, "growth_rate": 18.9, "trend": "stable"},
        {"name": "消费电子", "hot_score": 78.9, "growth_rate": 15.2, "trend": "stable"},
        {"name": "农业科技", "hot_score": 75.6, "growth_rate": 28.3, "trend": "upward"},
        {"name": "金融科技", "hot_score": 72.4, "growth_rate": 12.5, "trend": "downward"},
        {"name": "教育培训", "hot_score": 68.2, "growth_rate": -5.3, "trend": "downward"},
        {"name": "房地产科技", "hot_score": 65.1, "growth_rate": -8.7, "trend": "downward"},
    ]
    return sorted(industries, key=lambda x: x["hot_score"], reverse=True)[:limit]
