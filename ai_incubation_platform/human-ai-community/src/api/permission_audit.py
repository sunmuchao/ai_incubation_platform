"""
权限审计 API 路由

提供权限审计日志接口：
- 审计日志查询
- 审计日志导出
- 审计统计
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.permission_audit_service import permission_audit_service, AuditEventType

router = APIRouter(prefix="/api/audit", tags=["audit"])


# ==================== 请求模型 ====================

class AuditLogQuery(BaseModel):
    """审计日志查询请求"""
    actor_id: Optional[str] = Field(None, description="操作人 ID")
    resource_type: Optional[str] = Field(None, description="资源类型")
    resource_id: Optional[str] = Field(None, description="资源 ID")
    event_type: Optional[str] = Field(None, description="事件类型")
    start_time: Optional[str] = Field(None, description="开始时间 ISO8601")
    end_time: Optional[str] = Field(None, description="结束时间 ISO8601")
    limit: int = Field(default=100, ge=1, le=500)


class AuditLogStats(BaseModel):
    """审计统计查询"""
    start_time: Optional[str] = Field(None, description="开始时间 ISO8601")
    end_time: Optional[str] = Field(None, description="结束时间 ISO8601")


# ==================== 审计日志查询 ====================

@router.get("/logs")
async def get_audit_logs(
    actor_id: Optional[str] = Query(None, description="操作人 ID"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    resource_id: Optional[str] = Query(None, description="资源 ID"),
    event_type: Optional[str] = Query(None, description="事件类型"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO8601"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO8601"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """
    获取审计日志

    支持按操作人、资源、事件类型、时间范围过滤
    """
    # 解析时间
    start_dt = None
    end_dt = None

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    # 根据条件查询日志
    if actor_id:
        logs = permission_audit_service.get_logs_by_actor(
            actor_id=actor_id,
            limit=limit,
            start_time=start_dt,
            end_time=end_dt
        )
    elif resource_type and resource_id:
        logs = permission_audit_service.get_logs_by_resource(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
            start_time=start_dt,
            end_time=end_dt
        )
    elif event_type:
        try:
            et = AuditEventType(event_type)
            logs = permission_audit_service.get_logs_by_event_type(
                event_type=et,
                limit=limit,
                start_time=start_dt,
                end_time=end_dt
            )
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid event_type: {event_type}")
    else:
        logs = permission_audit_service.get_recent_logs(
            limit=limit,
            start_time=start_dt,
            end_time=end_dt
        )

    return {
        "logs": logs,
        "total": len(logs),
        "filters": {
            "actor_id": actor_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "event_type": event_type,
            "start_time": start_time,
            "end_time": end_time
        }
    }


@router.get("/logs/user/{user_id}")
async def get_user_audit_logs(
    user_id: str,
    start_time: Optional[str] = Query(None, description="开始时间 ISO8601"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO8601"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """获取指定用户的操作日志"""
    start_dt = None
    end_dt = None

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    logs = permission_audit_service.get_logs_by_actor(
        actor_id=user_id,
        limit=limit,
        start_time=start_dt,
        end_time=end_dt
    )

    return {
        "user_id": user_id,
        "logs": logs,
        "total": len(logs)
    }


@router.get("/logs/resource/{resource_type}/{resource_id}")
async def get_resource_audit_logs(
    resource_type: str,
    resource_id: str,
    start_time: Optional[str] = Query(None, description="开始时间 ISO8601"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO8601"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """获取指定资源的操作日志"""
    start_dt = None
    end_dt = None

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    logs = permission_audit_service.get_logs_by_resource(
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
        start_time=start_dt,
        end_time=end_dt
    )

    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "logs": logs,
        "total": len(logs)
    }


@router.get("/logs/recent")
async def get_recent_audit_logs(
    hours: int = Query(default=24, ge=1, le=720, description="最近 N 小时"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """获取最近的审计日志"""
    start_dt = datetime.now() - timedelta(hours=hours)

    logs = permission_audit_service.get_recent_logs(
        limit=limit,
        start_time=start_dt
    )

    return {
        "logs": logs,
        "total": len(logs),
        "time_range_hours": hours
    }


# ==================== 审计统计 ====================

@router.get("/stats")
async def get_audit_stats(
    start_time: Optional[str] = Query(None, description="开始时间 ISO8601"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO8601")
):
    """获取审计统计"""
    start_dt = None
    end_dt = None

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    stats = permission_audit_service.get_audit_stats(
        start_time=start_dt,
        end_time=end_dt
    )

    return stats


@router.get("/stats/summary")
async def get_audit_stats_summary(
    days: int = Query(default=7, ge=1, le=90, description="最近 N 天")
):
    """获取审计统计摘要"""
    start_dt = datetime.now() - timedelta(days=days)

    stats = permission_audit_service.get_audit_stats(start_time=start_dt)

    # 计算每日趋势
    daily_stats = []
    for i in range(days):
        day_start = start_dt + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_stats = permission_audit_service.get_audit_stats(
            start_time=day_start,
            end_time=day_end
        )
        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "total_logs": day_stats["total_logs"],
            "event_counts": day_stats["event_counts"]
        })

    return {
        "summary": stats,
        "daily_trend": daily_stats,
        "days": days
    }


# ==================== 审计日志导出 ====================

@router.get("/export")
async def export_audit_logs(
    format: str = Query(default="json", description="导出格式：json, csv"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO8601"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO8601"),
    operator_id: str = Query(..., description="操作人 ID")
):
    """导出审计日志"""
    start_dt = None
    end_dt = None

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Format must be json or csv")

    try:
        content = permission_audit_service.export_logs(
            format=format,
            start_time=start_dt,
            end_time=end_dt
        )

        return {
            "exported_by": operator_id,
            "exported_at": datetime.now().isoformat(),
            "format": format,
            "record_count": len(content) if format == "json" else len(content.split("\n")) - 1,
            "content": content
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 事件类型列表 ====================

@router.get("/event-types")
async def get_audit_event_types():
    """获取所有审计事件类型"""
    return {
        "event_types": [
            {
                "value": et.value,
                "name": et.value.replace("_", " ").title()
            }
            for et in AuditEventType
        ]
    }


# ==================== 管理功能 ====================

@router.post("/logs/prune")
async def prune_audit_logs(
    days_old: int = Query(default=90, ge=1, description="保留最近 N 天的日志"),
    operator_id: str = Query(...)
):
    """
    清理过期审计日志

    注意：这是演示实现，实际生产环境需要持久化存储
    """
    # 由于当前审计日志存储在内存中，重启后会丢失
    # 此接口仅返回成功响应
    cutoff_date = datetime.now() - timedelta(days=days_old)

    return {
        "success": True,
        "message": f"Audit logs older than {days_old} days would be pruned",
        "cutoff_date": cutoff_date.isoformat(),
        "operator_id": operator_id
    }
