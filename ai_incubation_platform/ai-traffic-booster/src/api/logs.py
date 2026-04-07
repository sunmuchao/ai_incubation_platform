"""
日志 API - P0 日志持久化

提供日志查询、统计和分析的 HTTP 接口
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from services.log_service import LogService, get_log_service
from db.postgresql_models import SystemLogModel


router = APIRouter(prefix="/logs", tags=["Logs"])


# ==================== Schema 定义 ====================

class LogQueryParams(BaseModel):
    """日志查询参数"""
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    level: Optional[str] = Field(None, description="日志级别")
    logger_name: Optional[str] = Field(None, description="日志器名称")
    trace_id: Optional[str] = Field(None, description="追踪 ID")
    request_id: Optional[str] = Field(None, description="请求 ID")
    search_keyword: Optional[str] = Field(None, description="搜索关键词")
    offset: int = Field(0, ge=0, description="偏移量")
    limit: int = Field(100, ge=1, le=1000, description="限制数量")


class LogStatsResponse(BaseModel):
    """日志统计响应"""
    total_count: int
    by_level: Dict[str, int]
    by_module: Dict[str, int]
    error_rate: float
    avg_duration_ms: float


class LogEntryResponse(BaseModel):
    """日志条目响应"""
    id: int
    level: str
    message: str
    logger_name: Optional[str]
    trace_id: Optional[str]
    module: Optional[str]
    function: Optional[str]
    line_number: Optional[int]
    extra_data: Optional[Dict[str, Any]]
    request_id: Optional[str]
    exception_type: Optional[str]
    exception_message: Optional[str]
    duration_ms: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== API 端点 ====================

@router.get("", response_model=List[LogEntryResponse])
async def list_logs(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    level: Optional[str] = Query(None, description="日志级别"),
    logger_name: Optional[str] = Query(None, description="日志器名称"),
    trace_id: Optional[str] = Query(None, description="追踪 ID"),
    request_id: Optional[str] = Query(None, description="请求 ID"),
    search_keyword: Optional[str] = Query(None, description="搜索关键词"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    log_service: LogService = Depends(get_log_service),
):
    """
    查询日志

    - **start_time**: 开始时间 (ISO 8601 格式)
    - **end_time**: 结束时间 (ISO 8601 格式)
    - **level**: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - **trace_id**: 追踪 ID，用于查询完整调用链
    - **search_keyword**: 关键词搜索
    """
    logs = log_service.get_logs(
        start_time=start_time,
        end_time=end_time,
        level=level,
        logger_name=logger_name,
        trace_id=trace_id,
        request_id=request_id,
        search_keyword=search_keyword,
        offset=offset,
        limit=limit,
    )
    return logs


@router.get("/trace/{trace_id}", response_model=List[LogEntryResponse])
async def get_trace_logs(
    trace_id: str,
    limit: int = Query(1000, ge=1, le=5000, description="限制数量"),
    log_service: LogService = Depends(get_log_service),
):
    """
    获取指定追踪 ID 的完整日志链

    用于调试和排查问题，可追溯完整请求链路
    """
    logs = log_service.get_trace_logs(trace_id)
    return logs[:limit]


@router.get("/errors", response_model=List[LogEntryResponse])
async def get_error_logs(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(50, ge=1, le=500, description="限制数量"),
    log_service: LogService = Depends(get_log_service),
):
    """
    获取错误日志

    默认返回最近 24 小时的错误日志
    """
    logs = log_service.get_error_logs(
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    return logs


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    group_by: str = Query("level", description="分组维度"),
    log_service: LogService = Depends(get_log_service),
):
    """
    获取日志统计

    返回日志数量、级别分布、模块分布、错误率等统计信息
    """
    stats = log_service.get_log_stats(
        start_time=start_time,
        end_time=end_time,
        group_by=group_by,
    )
    return stats


@router.get("/request/{request_id}", response_model=List[LogEntryResponse])
async def get_request_logs(
    request_id: str,
    limit: int = Query(1000, ge=1, le=5000, description="限制数量"),
    log_service: LogService = Depends(get_log_service),
):
    """
    获取指定请求 ID 的日志

    用于排查特定请求的问题
    """
    logs = log_service.get_logs(request_id=request_id, limit=limit)
    return logs


@router.delete("/cleanup", response_model=Dict[str, int])
async def cleanup_old_logs(
    retention_days: int = Query(30, ge=1, le=365, description="保留天数"),
    log_service: LogService = Depends(get_log_service),
):
    """
    清理过期日志

    删除指定天数之前的日志记录
    """
    deleted_count = log_service.cleanup_old_logs(retention_days=retention_days)
    return {"deleted_count": deleted_count}


# ==================== 分析端点 ====================

@router.get("/analysis/error-trends")
async def get_error_trends(
    days: int = Query(7, ge=1, le=30, description="天数"),
    log_service: LogService = Depends(get_log_service),
):
    """
    获取错误趋势分析

    返回每天错误数量的时间序列数据
    """
    from datetime import timedelta
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    logs = log_service.get_logs(
        start_time=start_time,
        end_time=end_time,
        level="ERROR",
        limit=10000,
    )

    # 按天聚合
    trends = {}
    for log in logs:
        date_key = log.created_at.strftime("%Y-%m-%d")
        trends[date_key] = trends.get(date_key, 0) + 1

    # 转换为时间序列
    result = []
    current = start_time
    while current <= end_time:
        date_key = current.strftime("%Y-%m-%d")
        result.append({
            "date": date_key,
            "error_count": trends.get(date_key, 0),
        })
        current += timedelta(days=1)

    return {"trends": result, "total_errors": sum(t["error_count"] for t in result)}


@router.get("/analysis/slow-operations")
async def get_slow_operations(
    threshold_ms: float = Query(1000, ge=100, description="耗时阈值 (毫秒)"),
    limit: int = Query(50, ge=1, le=500, description="限制数量"),
    log_service: LogService = Depends(get_log_service),
):
    """
    获取慢操作分析

    返回耗时超过阈值的操作列表
    """
    from datetime import timedelta
    start_time = datetime.utcnow() - timedelta(hours=24)

    logs = log_service.get_logs(
        start_time=start_time,
        limit=1000,
    )

    # 过滤慢操作
    slow_ops = [
        {
            "module": log.module,
            "function": log.function,
            "message": log.message,
            "duration_ms": log.duration_ms,
            "trace_id": log.trace_id,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
        if log.duration_ms and log.duration_ms > threshold_ms
    ]

    # 按耗时排序
    slow_ops.sort(key=lambda x: x["duration_ms"], reverse=True)

    return {"slow_operations": slow_ops[:limit], "threshold_ms": threshold_ms}
