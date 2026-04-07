"""
P11: AI 员工市场增强 API 路由
版本：v11.0.0
功能：排行榜、精选推荐、技能趋势、个性化推荐
"""
from fastapi import APIRouter, Query, Body, Request
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.p11_models import (
    RankingCategory, RankingPeriod, RecommendationType,
    RankingQueryRequest, FeaturedEmployeeCreateRequest,
    MarketSearchRequest, MarketStatsResponse
)
from services.market_enhanced_service import market_enhanced_service

router = APIRouter(prefix="/api/marketplace-enhanced", tags=["marketplace-enhanced"])


# ==================== 排行榜功能 ====================

@router.get("/rankings", response_model=dict)
async def get_rankings(
    category: RankingCategory = Query(RankingCategory.OVERALL, description="排行榜分类"),
    period: RankingPeriod = Query(RankingPeriod.WEEKLY, description="排行榜周期"),
    skill_tag: Optional[str] = Query(None, description="技能标签（按技能分类时使用）"),
    industry: Optional[str] = Query(None, description="行业（按行业分类时使用）"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制")
):
    """
    获取 AI 员工排行榜

    - **category**: 排行榜分类（overall/by_skill/by_industry/newcomer/fastest_growing）
    - **period**: 排行榜周期（daily/weekly/monthly/all_time）
    - **skill_tag**: 技能标签，当 category=by_skill 时使用
    - **industry**: 行业，当 category=by_industry 时使用
    - **limit**: 返回前 N 名

    返回示例：
    ```json
    {
      "category": "overall",
      "period": "weekly",
      "rankings": [
        {
          "rank": 1,
          "employee_id": "emp_001",
          "name": "数据分析助手",
          "score": 98.5,
          "rating": 4.9,
          "total_jobs": 120,
          "hourly_rate": 50.0,
          "skills": ["数据分析", "Python", "Pandas"],
          "change": "+2"
        }
      ],
      "total_employees": 500,
      "calculated_at": "2026-04-05T10:00:00",
      "expires_at": "2026-04-12T10:00:00"
    }
    ```
    """
    result = market_enhanced_service.get_ranking(
        category=category,
        period=period,
        skill_tag=skill_tag,
        industry=industry,
        limit=limit
    )
    return result.dict() if result else {"error": "Failed to get ranking"}


@router.post("/rankings/calculate", response_model=dict)
async def calculate_rankings(
    category: RankingCategory = Query(RankingCategory.OVERALL),
    period: RankingPeriod = Query(RankingPeriod.WEEKLY),
    skill_tag: Optional[str] = Query(None),
    industry: Optional[str] = Query(None)
):
    """
    强制重新计算排行榜

    用于后台管理或定时任务触发排行榜更新
    """
    ranking = market_enhanced_service.calculate_ranking(
        category=category,
        period=period,
        skill_tag=skill_tag,
        industry=industry
    )
    return {
        "status": "success",
        "ranking": {
            "category": ranking.category.value,
            "period": ranking.period.value,
            "total_employees": ranking.total_employees,
            "calculated_at": ranking.calculated_at.isoformat(),
            "expires_at": ranking.expires_at.isoformat()
        }
    }


# ==================== 精选推荐功能 ====================

@router.get("/featured", response_model=dict)
async def get_featured_employees(
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    featured_type: Optional[str] = Query(None, description="精选类型过滤")
):
    """
    获取精选 AI 员工列表

    - **limit**: 返回数量限制
    - **featured_type**: 精选类型（editor_pick/top_rated/best_value/trending）

    返回示例：
    ```json
    {
      "featured_employees": [
        {
          "id": "feat_001",
          "employee": {
            "id": "emp_001",
            "name": "数据分析助手",
            "avatar": "https://example.com/avatar.png",
            "rating": 4.9,
            "hourly_rate": 50.0
          },
          "reason": "编辑精选：本周最佳数据分析 AI",
          "featured_type": "editor_pick",
          "badge": "Editor's Choice",
          "click_count": 150,
          "conversion_count": 25
        }
      ],
      "total_count": 5
    }
    ```
    """
    results = market_enhanced_service.get_featured_employees(
        limit=limit,
        featured_type=featured_type
    )
    return {
        "featured_employees": results,
        "total_count": len(results)
    }


@router.post("/featured", response_model=dict)
async def create_featured_employee(request: FeaturedEmployeeCreateRequest):
    """
    创建精选员工（管理员功能）

    - **employee_id**: AI 员工 ID
    - **reason**: 推荐理由
    - **featured_type**: 精选类型
    - **priority**: 优先级（数字越大越靠前）
    - **duration_days**: 展示天数
    """
    featured = market_enhanced_service.create_featured_employee(
        employee_id=request.employee_id,
        reason=request.reason,
        featured_type=request.featured_type,
        priority=request.priority,
        highlight_title=request.highlight_title,
        highlight_description=request.highlight_description,
        badge=request.badge,
        duration_days=request.duration_days
    )
    return {
        "status": "success",
        "featured": {
            "id": featured.id,
            "employee_id": featured.employee_id,
            "start_at": featured.start_at.isoformat(),
            "end_at": featured.end_at.isoformat()
        }
    }


@router.post("/featured/{featured_id}/track/click")
async def track_featured_click(featured_id: str):
    """追踪精选员工点击"""
    market_enhanced_service.track_featured_click(featured_id)
    return {"status": "success", "message": "Click tracked"}


@router.post("/featured/{featured_id}/track/conversion")
async def track_featured_conversion(featured_id: str):
    """追踪精选员工转化"""
    market_enhanced_service.track_featured_conversion(featured_id)
    return {"status": "success", "message": "Conversion tracked"}


# ==================== 技能趋势功能 ====================

@router.get("/trending-skills", response_model=dict)
async def get_trending_skills(
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    trend_direction: Optional[str] = Query(None, description="趋势方向（up/down/stable）")
):
    """
    获取热门技能趋势

    - **limit**: 返回数量限制
    - **trend_direction**: 趋势方向过滤

    返回示例：
    ```json
    {
      "skills": [
        {
          "skill_name": "数据分析",
          "trend_score": 95.5,
          "growth_rate": "25.3%",
          "demand_index": 45.0,
          "supply_index": 120,
          "avg_hourly_rate": 55.0,
          "trend_direction": "up",
          "rank_change": 1
        }
      ],
      "period": "7d",
      "total_count": 10
    }
    ```
    """
    skills = market_enhanced_service.get_trending_skills(
        limit=limit,
        trend_direction=trend_direction
    )
    return {
        "skills": skills,
        "period": "7d",
        "total_count": len(skills)
    }


@router.get("/stats", response_model=dict)
async def get_market_stats(force_refresh: bool = Query(False, description="强制刷新缓存")):
    """
    获取市场统计数据

    返回市场整体统计信息，包括：
    - 员工总数和活跃数
    - 技能类别数量
    - 平均/中位数时薪
    - 热门分类
    -  trending 技能
    - 新增员工数
    """
    stats = market_enhanced_service.get_market_stats(force_refresh=force_refresh)
    return stats.dict()


# ==================== 个性化推荐功能 ====================

@router.get("/recommendations", response_model=dict)
async def get_personalized_recommendations(
    user_id: str = Query(..., description="用户 ID"),
    limit: int = Query(10, ge=1, le=50, description="返回数量限制")
):
    """
    获取个性化推荐

    基于用户历史行为（浏览、搜索、雇佣）生成个性化 AI 员工推荐

    - **user_id**: 用户 ID
    - **limit**: 返回数量限制

    返回示例：
    ```json
    {
      "user_id": "user_001",
      "recommendation_type": "personalized",
      "recommendations": [
        {
          "employee_id": "emp_001",
          "score": 0.95,
          "reason": "与你关注的 数据分析、Python 技能匹配"
        }
      ],
      "algorithm": "content_based",
      "generated_at": "2026-04-05T10:00:00",
      "expires_at": "2026-04-05T11:00:00"
    }
    ```
    """
    recommendation = market_enhanced_service.get_personalized_recommendations(
        user_id=user_id,
        limit=limit
    )
    return {
        "user_id": recommendation.user_id,
        "recommendation_type": recommendation.recommendation_type.value,
        "recommendations": recommendation.recommendations,
        "algorithm": recommendation.algorithm,
        "generated_at": recommendation.generated_at.isoformat(),
        "expires_at": recommendation.expires_at.isoformat()
    }


@router.post("/behavior/track")
async def track_user_behavior(
    user_id: str = Query(..., description="用户 ID"),
    tenant_id: str = Query(..., description="租户 ID"),
    behavior_type: str = Query(..., description="行为类型（view/search/hire/favorite）"),
    target_type: str = Query(..., description="目标类型（employee/skill/category）"),
    target_id: str = Query(..., description="目标 ID"),
    context: Optional[dict] = Body(None, description="行为上下文"),
    result: Optional[str] = Body(None, description="行为结果")
):
    """
    追踪用户行为

    用于个性化推荐算法的数据采集

    - **user_id**: 用户 ID
    - **tenant_id**: 租户 ID
    - **behavior_type**: 行为类型（view/search/hire/favorite）
    - **target_type**: 目标类型（employee/skill/category）
    - **target_id**: 目标 ID
    - **context**: 行为上下文（可选）
    - **result**: 行为结果（converted/ignored/bookmarked）
    """
    market_enhanced_service.record_user_behavior(
        user_id=user_id,
        tenant_id=tenant_id,
        behavior_type=behavior_type,
        target_type=target_type,
        target_id=target_id,
        context=context or {},
        result=result
    )
    return {"status": "success", "message": "Behavior tracked"}


# ==================== 高级搜索功能 ====================

@router.post("/search", response_model=dict)
async def advanced_search(
    request: MarketSearchRequest
):
    """
    高级搜索 AI 员工

    支持多维度筛选和排序：
    - 关键词搜索
    - 技能筛选
    - 分类筛选
    - 评分范围
    - 价格范围
    - 多种排序方式

    请求示例：
    ```json
    {
      "query": "数据分析",
      "skills": ["Python", "Pandas"],
      "min_rating": 4.0,
      "max_hourly_rate": 100.0,
      "sort_by": "rating",
      "sort_order": "desc",
      "limit": 20
    }
    ```
    """
    from services.employee_service import employee_service
    from models.employee import EmployeeStatus

    # 获取所有可用员工
    employees = employee_service.list_employees(EmployeeStatus.AVAILABLE)
    results = []

    for emp in employees:
        # 关键词匹配
        if request.query:
            query_lower = request.query.lower()
            match = (
                query_lower in emp.name.lower() or
                query_lower in emp.description.lower() or
                any(query_lower in skill.lower() for skill in emp.skills.keys())
            )
            if not match:
                continue

        # 技能筛选
        if request.skills:
            emp_skills_lower = [s.lower() for s in emp.skills.keys()]
            if not any(skill.lower() in emp_skills_lower for skill in request.skills):
                continue

        # 评分筛选
        if emp.rating < request.min_rating:
            continue

        # 价格筛选
        if request.max_hourly_rate and emp.hourly_rate > request.max_hourly_rate:
            continue
        if request.min_hourly_rate and emp.hourly_rate < request.min_hourly_rate:
            continue

        results.append(emp)

    # 排序
    if request.sort_by == "rating":
        results.sort(key=lambda e: e.rating, reverse=(request.sort_order == "desc"))
    elif request.sort_by == "earnings":
        results.sort(key=lambda e: e.total_earnings, reverse=(request.sort_order == "desc"))
    elif request.sort_by == "jobs":
        results.sort(key=lambda e: e.total_jobs, reverse=(request.sort_order == "desc"))
    elif request.sort_by == "price":
        results.sort(key=lambda e: e.hourly_rate, reverse=(request.sort_order == "desc"))
    elif request.sort_by == "newest":
        results.sort(key=lambda e: e.created_at, reverse=(request.sort_order == "desc"))

    # 分页
    total = len(results)
    start = request.offset
    end = min(request.offset + request.limit, total)
    paginated = results[start:end]

    # 转换为字典
    result_list = []
    for emp in paginated:
        result_list.append({
            "id": emp.id,
            "name": emp.name,
            "avatar": emp.avatar,
            "description": emp.description,
            "skills": list(emp.skills.keys()),
            "hourly_rate": emp.hourly_rate,
            "rating": emp.rating,
            "total_jobs": emp.total_jobs,
            "total_earnings": emp.total_earnings,
            "status": emp.status.value
        })

    return {
        "results": result_list,
        "total": total,
        "limit": request.limit,
        "offset": request.offset,
        "has_more": end < total
    }
