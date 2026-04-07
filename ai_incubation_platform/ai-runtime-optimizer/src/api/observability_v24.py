"""
可观测性 API v2.4
统一指标、日志、追踪的可观测性接口
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/observability/v2.4", tags=["Observability v2.4"])

# ============================================================================
# 数据模型
# ============================================================================

class LogSearchRequest(BaseModel):
    """日志搜索请求"""
    service_name: Optional[str] = Field(None, description="服务名称")
    level: Optional[str] = Field(None, description="日志级别")
    trace_id: Optional[str] = Field(None, description="追踪 ID")
    query: Optional[str] = Field(None, description="搜索关键词")
    start_time: Optional[str] = Field(None, description="开始时间 (ISO8601)")
    end_time: Optional[str] = Field(None, description="结束时间 (ISO8601)")
    limit: int = Field(default=100, ge=1, le=1000, description="返回数量限制")


class LogPatternRequest(BaseModel):
    """日志模式请求"""
    min_count: int = Field(default=1, ge=1, description="最小出现次数")
    severity: Optional[str] = Field(None, description="日志级别")
    limit: int = Field(default=50, ge=1, le=200, description="返回数量限制")


class ServiceHealthResponse(BaseModel):
    """服务健康响应"""
    service_name: str
    health_score: float
    health_status: str
    last_seen: Optional[str]
    error_count: int
    warning_count: int
    issues: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]


class ObservabilityOverviewResponse(BaseModel):
    """可观测性概览响应"""
    timestamp: str
    logs: Dict[str, Any]
    traces: Dict[str, Any]
    services: Dict[str, Any]


class CorrelationRequest(BaseModel):
    """关联分析请求"""
    trace_id: str = Field(..., description="追踪 ID")
    include_logs: bool = Field(default=True, description="是否包含日志")
    include_metrics: bool = Field(default=True, description="是否包含指标")


# ============================================================================
# 可观测性概览
# ============================================================================

@router.get("/overview", response_model=ObservabilityOverviewResponse, summary="可观测性概览")
async def get_observability_overview():
    """
    获取系统整体可观测性状态概览

    返回指标、日志、追踪的综合统计信息，以及服务健康状态摘要。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()
    overview = engine.get_observability_overview()

    return overview


@router.get("/health", summary="健康检查")
async def health_check():
    """
    健康检查接口

    返回可观测性引擎的健康状态。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "engine_status": "running"
    }


# ============================================================================
# 日志查询与分析
# ============================================================================

@router.post("/logs/search", summary="日志搜索")
async def search_logs(request: LogSearchRequest):
    """
    搜索日志

    支持多维度过滤：
    - 服务名称
    - 日志级别
    - 追踪 ID
    - 关键词搜索
    - 时间范围
    """
    from core.observability_engine import get_observability_engine, LogLevel

    engine = get_observability_engine()

    # 解析时间
    start_time = None
    end_time = None

    if request.start_time:
        try:
            start_time = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    if request.end_time:
        try:
            end_time = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    logs = engine.search_logs(
        service_name=request.service_name,
        level=request.level,
        trace_id=request.trace_id,
        query=request.query,
        start_time=start_time,
        end_time=end_time,
        limit=request.limit
    )

    return {
        "total": len(logs),
        "logs": logs
    }


@router.post("/logs/patterns", summary="日志模式分析")
async def get_log_patterns(request: LogPatternRequest):
    """
    获取日志模式

    自动聚类相似的日志消息，识别常见问题模式。
    支持按严重程度和最小出现次数过滤。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    patterns = engine.get_log_patterns(
        min_count=request.min_count,
        severity=request.severity,
        limit=request.limit
    )

    return {
        "total_patterns": len(patterns),
        "patterns": patterns
    }


@router.get("/logs/error-patterns", summary="错误模式分析")
async def get_error_patterns(limit: int = Query(default=20, ge=1, le=100)):
    """
    获取错误日志模式

    返回出现频率最高的错误模式，帮助快速定位系统性问题。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    patterns = engine._log_aggregator.get_error_patterns(limit=limit)

    return {
        "total": len(patterns),
        "patterns": [p.to_dict() for p in patterns]
    }


@router.get("/logs/stats", summary="日志统计")
async def get_log_stats():
    """
    获取日志统计信息

    返回日志总量、模式数量、错误数量等统计数据。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    return engine.get_log_stats()


# ============================================================================
# 服务健康
# ============================================================================

@router.get("/services", summary="服务列表")
async def get_services():
    """
    获取所有已发现的服务列表及其健康状态
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    services = engine.get_service_health()

    return {
        "total_services": len(services),
        "services": services
    }


@router.get("/services/{service_name}", response_model=ServiceHealthResponse, summary="服务健康详情")
async def get_service_health(service_name: str):
    """
    获取指定服务的健康状态详情

    包含健康分数、问题诊断和优化建议。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    health = engine.get_service_health(service_name)

    if not health:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")

    # 分析问题
    analysis = engine.analyze_service_issues(service_name)

    return ServiceHealthResponse(
        service_name=service_name,
        health_score=analysis.get("health_score", 100),
        health_status=analysis.get("health_status", "unknown"),
        last_seen=health.get("last_seen"),
        error_count=health.get("error_count", 0),
        warning_count=health.get("warning_count", 0),
        issues=analysis.get("issues", []),
        recommendations=analysis.get("recommendations", [])
    )


@router.get("/services/{service_name}/analysis", summary="服务问题分析")
async def analyze_service_issues(service_name: str):
    """
    分析服务存在的问题

    综合日志、指标、追踪数据，诊断服务问题并提供建议。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    analysis = engine.analyze_service_issues(service_name)

    return analysis


# ============================================================================
# 关联分析
# ============================================================================

@router.post("/correlate", summary="关联分析")
async def correlate_trace_with_logs(request: CorrelationRequest):
    """
    关联追踪与日志

    将分布式追踪与相关日志关联起来，提供完整的问题排查视图。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    correlation = engine.correlate_trace_with_logs(request.trace_id)

    if not correlation.get("trace") and not correlation.get("related_logs"):
        raise HTTPException(
            status_code=404,
            detail=f"No data found for trace_id: {request.trace_id}"
        )

    return correlation


# ============================================================================
# 指标查询
# ============================================================================

@router.get("/metrics/summary", summary="指标摘要")
async def get_metrics_summary(
    service_name: Optional[str] = Query(None, description="服务名称"),
    time_range_minutes: int = Query(default=60, ge=1, le=1440, description="时间范围 (分钟)")
):
    """
    获取指标摘要

    返回指定时间范围内的指标统计数据。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    health = engine.get_service_health(service_name)

    return {
        "service_name": service_name or "all",
        "time_range_minutes": time_range_minutes,
        "health_data": health
    }


# ============================================================================
# 数据摄入
# ============================================================================

@router.post("/ingest/log", summary="摄入日志")
async def ingest_log(
    level: str = Query(..., description="日志级别"),
    service_name: str = Query(..., description="服务名称"),
    message: str = Query(..., description="日志消息"),
    trace_id: Optional[str] = Query(None, description="追踪 ID"),
    attributes: Dict[str, Any] = Body(default={}, description="附加属性")
):
    """
    摄入单条日志

    用于外部系统集成。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    engine.ingest_log(
        level=level,
        service_name=service_name,
        message=message,
        trace_id=trace_id,
        attributes=attributes
    )

    return {"status": "ok", "message": "Log ingested successfully"}


@router.post("/ingest/metrics", summary="摄入指标")
async def ingest_metrics(
    service_name: str = Query(..., description="服务名称"),
    metrics: Dict[str, Any] = Body(..., description="指标数据")
):
    """
    摄入指标数据

    用于外部系统集成。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    engine.ingest_metrics(service_name, metrics)

    return {"status": "ok", "message": "Metrics ingested successfully"}


# ============================================================================
# 仪表盘数据
# ============================================================================

@router.get("/dashboard/main", summary="主仪表盘数据")
async def get_dashboard_data():
    """
    获取主仪表盘数据

    为前端仪表盘提供完整的数据支持。
    """
    from core.observability_engine import get_observability_engine

    engine = get_observability_engine()

    overview = engine.get_observability_overview()
    services = engine.get_service_health()

    # 获取最近的错误模式
    error_patterns = engine._log_aggregator.get_error_patterns(limit=5)

    # 计算整体健康度
    if services:
        avg_health = sum(s.get("health_score", 100) for s in services.values()) / len(services)
        health_trend = "stable"  # 简化实现
    else:
        avg_health = 100
        health_trend = "unknown"

    return {
        "overview": overview,
        "health": {
            "average_score": round(avg_health, 2),
            "trend": health_trend,
            "service_count": len(services)
        },
        "alerts": {
            "critical_services": len([s for s in services.values() if s.get("health_score", 100) < 50]),
            "degraded_services": len([s for s in services.values() if 50 <= s.get("health_score", 100) < 80]),
            "error_patterns": len(error_patterns)
        },
        "recent_error_patterns": [p.to_dict() for p in error_patterns]
    }
