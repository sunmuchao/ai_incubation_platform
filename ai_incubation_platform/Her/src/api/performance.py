"""
性能优化 API 模块

v1.23 新增功能：
- 性能监控仪表板
- 慢查询日志查询
- 性能优化建议
- 缓存管理

v1.31 新增功能：
- LLM 成本监控
- LLM 调用统计
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime, timedelta
from services.performance_service import perf_service, SlowQueryLogger, PerformanceMonitor
from cache import cache_manager
from utils.llm_cost_tracker import get_llm_cost_tracker

router = APIRouter(prefix="/api/performance", tags=["性能优化"])


@router.get("/dashboard")
async def get_performance_dashboard():
    """
    获取性能仪表板数据

    返回：
    - 系统运行时长
    - 缓存统计
    - API 性能指标
    - 慢查询统计
    - 慢端点排行
    """
    return perf_service.get_performance_dashboard()


@router.get("/slow-queries")
async def get_slow_queries(
    limit: int = Query(default=100, ge=1, le=1000, description="返回记录数"),
    hours: int = Query(default=24, ge=1, le=168, description="查询最近 N 小时")
):
    """
    获取慢查询日志

    Args:
        limit: 返回记录数
        hours: 查询最近 N 小时的数据
    """
    since = datetime.now() - timedelta(hours=hours)
    queries = perf_service.slow_query_logger.get_slow_queries(limit=limit, since=since)

    return {
        "total": len(queries),
        "since": since.isoformat(),
        "queries": [
            {
                "query_name": q.query_name,
                "execution_time_ms": round(q.execution_time, 2),
                "timestamp": q.timestamp.isoformat(),
                "params": q.params,
                "result_count": q.result_count
            }
            for q in queries
        ],
        "stats": perf_service.slow_query_logger.get_stats()
    }


@router.get("/api-stats")
async def get_api_stats(
    endpoint: Optional[str] = Query(default=None, description="指定端点"),
    hours: int = Query(default=1, ge=1, le=168, description="查询最近 N 小时")
):
    """
    获取 API 性能统计

    Args:
        endpoint: 指定端点路径
        hours: 查询最近 N 小时的数据
    """
    since = datetime.now() - timedelta(hours=hours)
    stats = perf_service.performance_monitor.get_api_stats(endpoint=endpoint, since=since)

    return {
        "endpoint": endpoint or "all",
        "period_hours": hours,
        "since": since.isoformat(),
        "stats": stats
    }


@router.get("/slow-endpoints")
async def get_slow_endpoints(
    limit: int = Query(default=10, ge=1, le=50, description="返回记录数")
):
    """
    获取最慢的 API 端点排行
    """
    endpoints = perf_service.performance_monitor.get_slow_endpoints(limit=limit)
    return {
        "limit": limit,
        "endpoints": endpoints
    }


@router.get("/optimization-suggestions")
async def get_optimization_suggestions():
    """
    获取性能优化建议

    基于当前系统性能分析，提供优化建议
    """
    suggestions = perf_service.get_optimization_suggestions()
    return {
        "total": len(suggestions),
        "suggestions": suggestions
    }


@router.get("/cache/stats")
async def get_cache_stats():
    """
    获取缓存统计信息
    """
    return cache_manager.get_instance().get_cache_stats()


@router.post("/cache/warm/{name}")
async def warm_cache(name: str):
    """
    手动触发缓存预热

    Args:
        name: 预热任务名称
    """
    success = perf_service.cache_warmer.warm_now(name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cache warm task not found: {name}"
        )
    return {"message": f"Cache warmed successfully: {name}"}


@router.delete("/cache/clear")
async def clear_cache():
    """
    清空缓存

    注意：此操作会清空所有缓存数据，生产环境慎用
    """
    cache_manager.get_instance().clear_memory_cache()
    return {"message": "Cache cleared successfully"}


@router.get("/uptime")
async def get_uptime():
    """
    获取系统运行时长
    """
    uptime = perf_service.performance_monitor.get_uptime()
    return {
        "uptime_seconds": uptime.total_seconds(),
        "uptime_human": str(uptime),
        "start_time": (datetime.now() - uptime).isoformat()
    }


@router.get("/health")
async def health_check():
    """
    性能健康检查

    检查各项性能指标是否正常
    """
    issues = []

    # 检查缓存
    cache_stats = cache_manager.get_instance().get_cache_stats()
    if not cache_stats.get("redis_available", False):
        issues.append("Redis cache not available (using memory cache)")

    # 检查慢查询
    slow_stats = perf_service.slow_query_logger.get_stats()
    if slow_stats.get("total_slow_queries", 0) > 100:
        issues.append(f"High number of slow queries: {slow_stats['total_slow_queries']}")

    # 检查 API 错误率
    api_stats = perf_service.performance_monitor.get_api_stats()
    if api_stats.get("error_rate", 0) > 0.05:
        issues.append(f"High API error rate: {api_stats['error_rate']:.2%}")

    status_level = "healthy" if not issues else "degraded"

    return {
        "status": status_level,
        "issues": issues,
        "cache": cache_stats,
        "slow_queries_count": slow_stats.get("total_slow_queries", 0),
        "api_error_rate": api_stats.get("error_rate", 0)
    }


# ==================== LLM 成本监控 API ====================

@router.get("/llm/stats")
async def get_llm_stats():
    """
    获取 LLM 成本统计

    返回：
    - 总调用次数
    - 总 token 消耗
    - 总成本（元）
    - 缓存命中率
    - 错误率
    - 平均响应时间
    """
    tracker = get_llm_cost_tracker()
    return tracker.get_stats()


@router.get("/llm/cost-by-endpoint")
async def get_llm_cost_by_endpoint():
    """
    按场景统计 LLM 成本

    返回各场景（matching, bias_analysis, precommunication 等）的成本明细
    """
    tracker = get_llm_cost_tracker()
    return tracker.get_cost_by_endpoint()


@router.get("/llm/recent-calls")
async def get_llm_recent_calls(
    limit: int = Query(default=100, ge=1, le=500, description="返回记录数")
):
    """
    获取最近的 LLM 调用记录

    Args:
        limit: 返回记录数
    """
    tracker = get_llm_cost_tracker()
    return {
        "total": limit,
        "records": tracker.get_recent_records(limit=limit)
    }


@router.post("/llm/reset-stats")
async def reset_llm_stats():
    """
    重置 LLM 统计数据

    注意：此操作会清空所有统计数据，用于测试或定期清理
    """
    tracker = get_llm_cost_tracker()
    tracker.clear_records()
    return {"message": "LLM cost stats reset successfully"}
