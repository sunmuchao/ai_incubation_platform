"""
P6 - 商机评分与推荐 API

新增 API 端点：
1. 商机质量评分
2. 智能推荐
3. 政策数据查询
4. 供应链数据查询
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/p6", tags=["P6 - 商机评分与推荐"])

# 导入服务层
from services.opportunity_scorer import opportunity_scorer, ml_score_model, OpportunityScore
from services.recommendation_engine import recommendation_engine, UserPreference, RecommendationType
from crawler.policy_supply_chain import policy_crawler, supply_chain_crawler, health_monitor
from crawler.policy_supply_chain import PolicyType, PolicyLevel


# ==================== 请求/响应模型 ====================

class ScoringRequest(BaseModel):
    """评分请求"""
    opportunity_id: str
    source_type: str = "AI_ANALYSIS"
    confidence_score: float = 0.5
    potential_value: float = 0
    risk_factors: Dict[str, float] = {}
    opportunity_window_days: Optional[int] = None
    technical_feasibility: float = 0.5
    strategic_alignment: float = 0.5


class ScoringResponse(BaseModel):
    """评分响应"""
    opportunity_id: str
    overall_score: float
    grade: str
    confidence_score: float
    risk_score: float
    value_score: float
    urgency_score: float
    feasibility_score: float
    strategic_fit_score: float
    recommendations: List[str]


class RecommendationRequest(BaseModel):
    """推荐请求"""
    user_id: str
    preferred_industries: List[str] = []
    preferred_keywords: List[str] = []
    preferred_opportunity_types: List[str] = []
    min_confidence: float = 0.5
    min_value: float = 0
    risk_tolerance: float = 0.5
    limit: int = 10
    enable_strategies: List[str] = ["content_based", "collaborative", "trend_driven"]


class RecommendationResponse(BaseModel):
    """推荐响应"""
    recommendations: List[Dict[str, Any]]
    total: int
    user_id: str


class PolicySearchRequest(BaseModel):
    """政策搜索请求"""
    keywords: List[str] = []
    industry: Optional[str] = None
    policy_type: Optional[str] = None
    level: Optional[str] = None
    region: Optional[str] = None
    limit: int = 20


class SupplyChainRequest(BaseModel):
    """供应链查询请求"""
    company_name: str
    depth: int = 2


# ==================== 商机评分 API ====================

@router.post("/score/opportunity", response_model=ScoringResponse)
async def score_opportunity(request: ScoringRequest):
    """
    对商机进行多维度质量评分

    评分维度包括：
    - 置信度：基于数据源可靠性和 AI 置信度
    - 风险：多维度风险评估
    - 价值：潜在商业价值
    - 紧迫性：机会窗口紧迫程度
    - 可行性：技术/资源/时间可行性
    - 战略匹配：与公司战略的对齐度
    """
    # 构建评分数据
    scoring_data = {
        "id": request.opportunity_id,
        "source_type": request.source_type,
        "confidence_score": request.confidence_score,
        "potential_value": request.potential_value,
        "risk_factors": request.risk_factors,
        "opportunity_window_days": request.opportunity_window_days,
        "technical_feasibility": request.technical_feasibility,
        "strategic_alignment": request.strategic_alignment,
        # 默认值
        "data_completeness": 0.7,
        "cross_validation_count": 1,
        "value_confidence": 0.6,
        "competitive_pressure": 0.5,
        "market_readiness": 0.6,
        "internal_readiness": 0.5,
        "resource_availability": 0.5,
        "core_competency_match": 0.6,
    }

    # 计算评分
    score = opportunity_scorer.score_opportunity(scoring_data)

    return ScoringResponse(
        opportunity_id=score.opportunity_id,
        overall_score=score.overall_score,
        grade=score.grade,
        confidence_score=score.confidence_score,
        risk_score=score.risk_score,
        value_score=score.value_score,
        urgency_score=score.urgency_score,
        feasibility_score=score.feasibility_score,
        strategic_fit_score=score.strategic_fit_score,
        recommendations=score.recommendations
    )


@router.get("/score/{opportunity_id}")
async def get_opportunity_score(opportunity_id: str):
    """获取商机评分（从服务层获取商机数据后评分）"""
    # TODO: 从机会服务获取商机数据
    # 这里使用模拟数据演示
    mock_opportunity = {
        "id": opportunity_id,
        "source_type": "AI_ANALYSIS",
        "confidence_score": 0.75,
        "potential_value": 5000000,
        "risk_factors": {"regulatory": 0.3, "competitive": 0.5, "technological": 0.2},
        "opportunity_window_days": 60,
        "technical_feasibility": 0.7,
        "strategic_alignment": 0.8,
    }

    score = opportunity_scorer.score_opportunity(mock_opportunity)

    return {
        "opportunity_id": score.opportunity_id,
        "overall_score": score.overall_score,
        "grade": score.grade,
        "dimension_scores": {
            "confidence": score.confidence_score,
            "risk": score.risk_score,
            "value": score.value_score,
            "urgency": score.urgency_score,
            "feasibility": score.feasibility_score,
            "strategic_fit": score.strategic_fit_score,
        },
        "score_breakdown": score.score_breakdown,
        "scoring_factors": score.scoring_factors,
        "recommendations": score.recommendations,
    }


@router.post("/ml/predict-success")
async def predict_success_probability(
    opportunity_data: Dict[str, Any] = Body(...)
):
    """
    使用 ML 模型预测商机成功概率
    """
    probability = ml_score_model.predict_success_probability(opportunity_data)
    explanations = ml_score_model.explain_prediction(opportunity_data)

    return {
        "success_probability": round(probability, 4),
        "probability_percentage": f"{probability * 100:.1f}%",
        "explanations": explanations,
    }


# ==================== 智能推荐 API ====================

@router.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    获取智能推荐商机列表

    支持多种推荐策略：
    - content_based: 基于内容的推荐（匹配用户偏好）
    - collaborative: 协同过滤（相似用户喜欢的）
    - trend_driven: 趋势驱动（上升领域的商机）
    - knowledge_graph: 知识图谱（关联发现）
    """
    # 创建用户偏好
    user_pref = recommendation_engine.update_user_preference(
        user_id=request.user_id,
        preferences={
            "preferred_industries": request.preferred_industries,
            "preferred_keywords": request.preferred_keywords,
            "preferred_opportunity_types": request.preferred_opportunity_types,
            "min_confidence": request.min_confidence,
            "min_value": request.min_value,
            "risk_tolerance": request.risk_tolerance,
        }
    )

    # 解析启用的策略
    enable_strategies = []
    for s in request.enable_strategies:
        try:
            enable_strategies.append(RecommendationType(s))
        except ValueError:
            pass

    # TODO: 从机会服务获取商机池
    # 这里使用模拟数据
    mock_opportunities = [
        {
            "id": "opp_001",
            "title": "AI 医疗影像分析",
            "type": "market",
            "industry": "人工智能",
            "tags": ["AI", "医疗", "影像分析"],
            "confidence_score": 0.85,
            "potential_value": 10000000,
            "related_entities": [{"name": "腾讯医疗", "type": "company"}],
        },
        {
            "id": "opp_002",
            "title": "新能源汽车充电桩运营",
            "type": "investment",
            "industry": "新能源",
            "tags": ["新能源", "充电桩", "运营"],
            "confidence_score": 0.78,
            "potential_value": 5000000,
            "related_entities": [{"name": "特斯拉", "type": "company"}],
        },
        {
            "id": "opp_003",
            "title": "智能制造解决方案",
            "type": "product",
            "industry": "智能制造",
            "tags": ["智能制造", "工业 4.0", "解决方案"],
            "confidence_score": 0.72,
            "potential_value": 8000000,
            "related_entities": [{"name": "华为", "type": "company"}],
        },
    ]

    # 更新趋势数据（模拟）
    for opp in mock_opportunities:
        for tag in opp.get("tags", []):
            recommendation_engine.trend_recommender.update_trend(
                tag, 0.5 + np.random.random() * 0.5, datetime.now()
            )

    # 生成推荐
    recommendations = recommendation_engine.recommend(
        user_preference=user_pref,
        opportunities=mock_opportunities,
        limit=request.limit,
        enable_strategies=enable_strategies
    )

    return RecommendationResponse(
        recommendations=[rec.to_dict() for rec in recommendations],
        total=len(recommendations),
        user_id=request.user_id
    )


@router.get("/recommend/{user_id}/history")
async def get_recommendation_history(user_id: str):
    """获取用户的推荐历史"""
    stats = recommendation_engine.get_recommendation_stats(user_id)
    return stats


@router.post("/recommend/interaction")
async def record_interaction(
    user_id: str = Query(...),
    opportunity_id: str = Query(...),
    interaction_type: str = Query("view", description="交互类型：view/click/save/share")
):
    """记录用户对推荐商机的交互"""
    recommendation_engine.add_user_interaction(user_id, opportunity_id, interaction_type)
    return {"message": "交互记录成功"}


# ==================== 政策数据 API ====================

@router.get("/policy/search")
async def search_policies(
    industry: Optional[str] = Query(None, description="行业"),
    policy_type: Optional[str] = Query(None, description="政策类型"),
    level: Optional[str] = Query(None, description="政策级别"),
    region: Optional[str] = Query(None, description="地区"),
    limit: int = Query(20, ge=1, le=100)
):
    """搜索政策数据"""
    # 转换参数
    p_type = None
    if policy_type:
        try:
            p_type = PolicyType(policy_type)
        except ValueError:
            pass

    p_level = None
    if level:
        try:
            p_level = PolicyLevel(level)
        except ValueError:
            pass

    policies = policy_crawler.fetch_policies(
        industry=industry,
        policy_type=p_type,
        level=p_level,
        region=region,
        limit=limit
    )

    return {
        "policies": [p.to_dict() for p in policies],
        "count": len(policies),
    }


@router.post("/policy/search/keywords")
async def search_policies_by_keywords(request: PolicySearchRequest):
    """通过关键词搜索政策"""
    if request.keywords:
        policies = policy_crawler.search_policies(
            keywords=request.keywords,
            limit=request.limit
        )
    else:
        policies = policy_crawler.fetch_policies(
            industry=request.industry,
            level=PolicyLevel(request.level) if request.level else None,
            region=request.region,
            limit=request.limit
        )

    return {
        "policies": [p.to_dict() for p in policies],
        "count": len(policies),
    }


@router.get("/policy/types")
async def get_policy_types():
    """获取支持的政策类型"""
    return {
        "types": [{"value": t.value, "label": t.name} for t in PolicyType],
        "levels": [{"value": l.value, "label": l.name} for l in PolicyLevel],
    }


# ==================== 供应链数据 API ====================

@router.get("/supply-chain/{company_name}")
async def get_supply_chain(
    company_name: str,
    depth: int = Query(2, ge=1, le=5)
):
    """获取公司供应链图谱"""
    graph = supply_chain_crawler.get_supply_chain(company_name, depth)
    return graph


@router.post("/supply-chain/alternatives")
async def find_alternative_suppliers(
    request: SupplyChainRequest
):
    """寻找替代供应商"""
    # TODO: 添加产品和地区参数
    alternatives = supply_chain_crawler.find_alternative_suppliers(
        current_supplier=request.company_name,
        product="通用"  # 简化处理
    )
    return {
        "alternatives": [a.to_dict() for a in alternatives],
        "count": len(alternatives),
    }


# ==================== 数据源健康监控 API ====================

@router.get("/health/sources")
async def get_all_health_status():
    """获取所有数据源健康状态"""
    return health_monitor.get_all_health_status()


@router.get("/health/sources/{data_source}")
async def get_data_source_health(data_source: str):
    """获取指定数据源健康状态"""
    return health_monitor.get_health_status(data_source)


@router.get("/health/alerts")
async def get_health_alerts():
    """获取数据源健康告警"""
    alerts = health_monitor.check_alerts()
    return {
        "alerts": alerts,
        "count": len(alerts),
    }


@router.post("/health/record")
async def record_health_data(
    data_source: str = Query(...),
    success: bool = Query(...),
    latency: float = Query(...),
    error_message: Optional[str] = Query(None)
):
    """记录数据源调用健康数据（用于监控）"""
    health_monitor.record_call(data_source, success, latency, error_message)
    return {"message": "记录成功"}
