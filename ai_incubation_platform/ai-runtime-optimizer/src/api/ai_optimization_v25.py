"""
AI 优化建议 API v2.5
性能瓶颈分析、资源优化建议、成本优化接口
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/optimization/v2.5", tags=["Optimization v2.5"])

# ============================================================================
# 数据模型
# ============================================================================

class AnalyzeRequest(BaseModel):
    """分析请求"""
    service_name: str = Field(..., description="服务名称")
    metrics: Dict[str, Any] = Field(..., description="指标数据")


class RecommendationFilterRequest(BaseModel):
    """建议过滤请求"""
    service_name: Optional[str] = Field(None, description="服务名称")
    category: Optional[str] = Field(None, description="优化类别")
    priority: Optional[str] = Field(None, description="优先级")
    limit: int = Field(default=50, ge=1, le=200, description="返回数量限制")


class BottleneckFilterRequest(BaseModel):
    """瓶颈过滤请求"""
    service_name: Optional[str] = Field(None, description="服务名称")
    severity: Optional[str] = Field(None, description="严重程度")


# ============================================================================
# 综合分析
# ============================================================================

@router.post("/analyze", summary="综合分析")
async def comprehensive_analyze(request: AnalyzeRequest):
    """
    综合分析服务性能

    分析内容包括：
    - 性能瓶颈检测
    - 优化建议生成
    - 成本分析

    请求示例：
    ```json
    {
        "service_name": "payment-service",
        "metrics": {
            "cpu_percent": 85,
            "memory_percent": 72,
            "latency_p99_ms": 450,
            "error_rate": 0.5,
            "cache_hit_rate": 65
        }
    }
    ```
    """
    from core.ai_optimization import get_optimization_engine

    engine = get_optimization_engine()

    results = engine.analyze(
        service_name=request.service_name,
        metrics=request.metrics
    )

    return results


@router.get("/analyze/{service_name}", summary="服务分析")
async def analyze_service(
    service_name: str,
    cpu_percent: float = Query(..., description="CPU 使用率"),
    memory_percent: float = Query(..., description="内存使用率"),
    latency_p99_ms: float = Query(default=0, description="P99 延迟"),
    error_rate: float = Query(default=0, description="错误率"),
    cache_hit_rate: float = Query(default=100, description="缓存命中率")
):
    """
    快速分析服务性能

    通过查询参数传递指标数据进行分析。
    """
    from core.ai_optimization import get_optimization_engine

    engine = get_optimization_engine()

    metrics = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "latency_p99_ms": latency_p99_ms,
        "error_rate": error_rate,
        "cache_hit_rate": cache_hit_rate
    }

    results = engine.analyze(service_name=service_name, metrics=metrics)

    return results


# ============================================================================
# 性能瓶颈
# ============================================================================

@router.get("/bottlenecks", summary="瓶颈列表")
async def get_bottlenecks(
    service_name: Optional[str] = Query(None, description="服务名称"),
    severity: Optional[str] = Query(None, description="严重程度", enum=["critical", "high", "medium", "low"])
):
    """
    获取性能瓶颈列表

    支持按服务和严重程度过滤。
    """
    from core.ai_optimization import get_optimization_engine

    engine = get_optimization_engine()

    bottlenecks = engine._bottleneck_analyzer.get_bottlenecks(
        service_name=service_name,
        severity=severity
    )

    return {
        "total": len(bottlenecks),
        "bottlenecks": [b.to_dict() for b in bottlenecks]
    }


@router.get("/bottlenecks/{bottleneck_id}", summary="瓶颈详情")
async def get_bottleneck(bottleneck_id: str):
    """
    获取瓶颈详情
    """
    from core.ai_optimization import get_optimization_engine

    engine = get_optimization_engine()

    bottleneck = engine._bottleneck_analyzer._bottlenecks.get(bottleneck_id)

    if not bottleneck:
        raise HTTPException(status_code=404, detail=f"Bottleneck {bottleneck_id} not found")

    return bottleneck.to_dict()


# ============================================================================
# 优化建议
# ============================================================================

@router.get("/recommendations", summary="优化建议列表")
async def get_recommendations(
    service_name: Optional[str] = Query(None, description="服务名称"),
    category: Optional[str] = Query(None, description="优化类别", enum=["performance", "resource", "cost", "reliability"]),
    priority: Optional[str] = Query(None, description="优先级", enum=["critical", "high", "medium", "low"]),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制")
):
    """
    获取优化建议列表

    支持按服务、类别、优先级过滤。
    """
    from core.ai_optimization import get_optimization_engine, OptimizationCategory, OptimizationPriority

    engine = get_optimization_engine()

    # 转换枚举
    cat_enum = None
    if category:
        try:
            cat_enum = OptimizationCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    pri_enum = None
    if priority:
        try:
            pri_enum = OptimizationPriority(priority)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")

    recs = engine.get_recommendations(
        service_name=service_name,
        category=cat_enum,
        priority=pri_enum,
        limit=limit
    )

    return {
        "total": len(recs),
        "recommendations": [r.to_dict() for r in recs]
    }


@router.get("/recommendations/{rec_id}", summary="建议详情")
async def get_recommendation(rec_id: str):
    """
    获取优化建议详情
    """
    from core.ai_optimization import get_optimization_engine

    engine = get_optimization_engine()

    rec = engine._recommendations.get(rec_id)

    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")

    return rec.to_dict()


# ============================================================================
# 成本分析
# ============================================================================

@router.get("/cost-analysis/{service_name}", summary="成本分析")
async def get_cost_analysis(service_name: str):
    """
    获取服务的成本分析报告

    包括当前成本估算、优化后成本、节省潜力等。
    """
    from core.ai_optimization import get_optimization_engine

    engine = get_optimization_engine()

    # 获取服务最近的分析结果
    analysis = engine._cost_analyses.get(service_name)

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"No cost analysis found for service: {service_name}. Please run analyze first."
        )

    return analysis.to_dict()


# ============================================================================
# 快速诊断
# ============================================================================

@router.get("/quick-diagnosis/{service_name}", summary="快速诊断")
async def quick_diagnosis(service_name: str):
    """
    快速诊断服务健康状况

    返回关键问题和最优先的优化建议。
    """
    from core.ai_optimization import get_optimization_engine

    engine = get_optimization_engine()

    # 获取关键瓶颈
    critical_bottlenecks = engine._bottleneck_analyzer.get_bottlenecks(
        service_name=service_name,
        severity="critical"
    )

    # 获取高优先级建议
    high_priority_recs = engine.get_recommendations(
        service_name=service_name,
        priority=None,  # 获取所有，然后在结果中排序
        limit=10
    )

    # 计算健康评分
    health_score = 100
    for b in critical_bottlenecks:
        health_score -= 20
    health_score = max(0, health_score)

    return {
        "service_name": service_name,
        "health_score": health_score,
        "health_status": "critical" if health_score < 50 else ("warning" if health_score < 80 else "healthy"),
        "critical_issues": len(critical_bottlenecks),
        "critical_bottlenecks": [b.to_dict() for b in critical_bottlenecks],
        "top_recommendations": [r.to_dict() for r in high_priority_recs[:5]]
    }


# ============================================================================
# 优化追踪
# ============================================================================

@router.post("/recommendations/{rec_id}/implement", summary="标记建议已实施")
async def mark_recommendation_implemented(
    rec_id: str,
    result: Dict[str, Any] = Body(..., description="实施结果")
):
    """
    标记优化建议已实施，并记录结果

    用于追踪优化效果和持续学习。
    """
    from core.ai_optimization import get_optimization_engine

    engine = get_optimization_engine()

    rec = engine._recommendations.get(rec_id)

    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")

    # 更新建议状态
    rec.evidence.append(f"Implemented at {datetime.utcnow().isoformat()}")
    rec.evidence.append(f"Result: {result}")

    return {
        "status": "ok",
        "message": "Recommendation marked as implemented",
        "recommendation": rec.to_dict()
    }


# ============================================================================
# 仪表板数据
# ============================================================================

@router.get("/dashboard/overview", summary="优化概览")
async def get_optimization_overview():
    """
    获取优化概览数据

    用于前端仪表板展示。
    """
    from core.ai_optimization import get_optimization_engine

    engine = get_optimization_engine()

    # 获取所有瓶颈
    all_bottlenecks = engine._bottleneck_analyzer.get_bottlenecks()

    # 获取所有建议
    all_recommendations = engine.get_recommendations(limit=200)

    # 统计
    critical_count = len([b for b in all_bottlenecks if b.severity == "critical"])
    high_count = len([b for b in all_bottlenecks if b.severity == "high"])

    # 按类别统计建议
    category_stats = {}
    for rec in all_recommendations:
        cat = rec.category.value
        category_stats[cat] = category_stats.get(cat, 0) + 1

    # 预估节省
    total_savings = sum(
        engine._cost_analyses[s].savings_potential
        for s in engine._cost_analyses
    )

    return {
        "summary": {
            "total_bottlenecks": len(all_bottlenecks),
            "critical_bottlenecks": critical_count,
            "high_priority_bottlenecks": high_count,
            "total_recommendations": len(all_recommendations),
            "estimated_monthly_savings": round(total_savings, 2)
        },
        "category_breakdown": category_stats,
        "recent_bottlenecks": [b.to_dict() for b in all_bottlenecks[:10]],
        "recent_recommendations": [r.to_dict() for r in all_recommendations[:10]]
    }
