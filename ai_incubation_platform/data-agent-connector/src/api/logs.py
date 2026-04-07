"""
日志与审计 API

提供日志查询、导出、分析和审计功能
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.log_storage_service import log_storage_service
from services.log_cleanup_service import log_cleanup_service
from services.log_analytics_service import log_analytics_service
from models.audit_log import AuditLogEntry, QueryLogEntry, AccessLogEntry
from utils.logger import logger

router = APIRouter(prefix="/api/logs", tags=["日志与审计"])


# ==================== 请求/响应模型 ====================

class LogQueryRequest(BaseModel):
    """日志查询请求"""
    tenant_id: Optional[str] = Field(default=None, description="租户 ID")
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    start_date: Optional[str] = Field(default=None, description="开始时间 ISO8601")
    end_date: Optional[str] = Field(default=None, description="结束时间 ISO8601")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=50, ge=1, le=200, description="每页数量")


class AuditLogQueryRequest(LogQueryRequest):
    """审计日志查询请求"""
    action_type: Optional[str] = Field(default=None, description="操作类型")
    resource_type: Optional[str] = Field(default=None, description="资源类型")
    resource_id: Optional[str] = Field(default=None, description="资源 ID")


class QueryLogQueryRequest(LogQueryRequest):
    """查询日志查询请求"""
    datasource: Optional[str] = Field(default=None, description="数据源")
    connector_name: Optional[str] = Field(default=None, description="连接器名称")
    status: Optional[str] = Field(default=None, description="状态")


class AccessLogQueryRequest(LogQueryRequest):
    """访问日志查询请求"""
    granted: Optional[bool] = Field(default=None, description="是否允许")


class LogExportRequest(BaseModel):
    """日志导出请求"""
    log_type: str = Field(..., description="日志类型：audit, query, access")
    time_range_start: str = Field(..., description="开始时间 ISO8601")
    time_range_end: str = Field(..., description="结束时间 ISO8601")
    format: str = Field(default="json", description="导出格式：json, csv")
    destination: Optional[str] = Field(default=None, description="导出目的地")


class RetentionPolicyRequest(BaseModel):
    """保留策略请求"""
    log_type: str = Field(..., description="日志类型")
    retention_days: int = Field(..., ge=1, le=730, description="保留天数")
    storage_backend: str = Field(default="database", description="存储后端")
    export_enabled: bool = Field(default=False, description="是否启用导出")
    export_destination: Optional[str] = Field(default=None, description="导出目的地")


class UserActivityRequest(BaseModel):
    """用户活动分析请求"""
    user_id: str = Field(..., description="用户 ID")
    hours: int = Field(default=24, ge=1, le=720, description="时间范围（小时）")


class AnomalyDetectionRequest(BaseModel):
    """异常检测请求"""
    hours: int = Field(default=24, ge=1, le=168, description="时间范围（小时）")


class ComplianceReportRequest(BaseModel):
    """合规报告请求"""
    report_type: str = Field(..., description="报告类型：access_review, permission_audit, data_access")
    days: int = Field(default=30, ge=1, le=365, description="时间范围（天）")


# ==================== 审计日志 API ====================

@router.get("/audit", summary="查询审计日志")
async def query_audit_logs(
    tenant_id: Optional[str] = Query(default=None, description="租户 ID"),
    user_id: Optional[str] = Query(default=None, description="用户 ID"),
    action_type: Optional[str] = Query(default=None, description="操作类型"),
    resource_type: Optional[str] = Query(default=None, description="资源类型"),
    resource_id: Optional[str] = Query(default=None, description="资源 ID"),
    start_date: Optional[str] = Query(default=None, description="开始时间 ISO8601"),
    end_date: Optional[str] = Query(default=None, description="结束时间 ISO8601"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=50, ge=1, le=200, description="每页数量")
):
    """
    查询审计日志

    支持多条件过滤和分页
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        logs, total = await log_storage_service.query_audit_logs(
            tenant_id=tenant_id,
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            start_date=start_dt,
            end_date=end_dt,
            page=page,
            page_size=page_size
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "logs": [log.to_dict() for log in logs]
        }
    except Exception as e:
        logger.error(f"Failed to query audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/{log_id}", summary="获取审计日志详情")
async def get_audit_log(log_id: str):
    """获取审计日志详情"""
    logs, _ = await log_storage_service.query_audit_logs(
        page=1,
        page_size=1
    )
    # 简单实现，实际应该根据 ID 查询
    raise HTTPException(status_code=501, detail="Not implemented")


# ==================== 查询日志 API ====================

@router.get("/query", summary="查询查询日志")
async def query_query_logs(
    datasource: Optional[str] = Query(default=None, description="数据源"),
    connector_name: Optional[str] = Query(default=None, description="连接器名称"),
    status: Optional[str] = Query(default=None, description="状态"),
    start_date: Optional[str] = Query(default=None, description="开始时间 ISO8601"),
    end_date: Optional[str] = Query(default=None, description="结束时间 ISO8601"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=50, ge=1, le=200, description="每页数量")
):
    """
    查询查询日志

    记录所有 SQL 查询的执行情况
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        logs, total = await log_storage_service.query_query_logs(
            datasource=datasource,
            connector_name=connector_name,
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            page=page,
            page_size=page_size
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "logs": [log.to_dict() for log in logs]
        }
    except Exception as e:
        logger.error(f"Failed to query query logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 访问日志 API ====================

@router.get("/access", summary="查询访问日志")
async def query_access_logs(
    tenant_id: Optional[str] = Query(default=None, description="租户 ID"),
    user_id: Optional[str] = Query(default=None, description="用户 ID"),
    granted: Optional[bool] = Query(default=None, description="是否允许"),
    start_date: Optional[str] = Query(default=None, description="开始时间 ISO8601"),
    end_date: Optional[str] = Query(default=None, description="结束时间 ISO8601"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=50, ge=1, le=200, description="每页数量")
):
    """
    查询访问日志

    记录所有权限检查的结果
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        logs, total = await log_storage_service.query_access_logs(
            tenant_id=tenant_id,
            user_id=user_id,
            granted=granted,
            start_date=start_dt,
            end_date=end_dt,
            page=page,
            page_size=page_size
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "logs": [log.to_dict() for log in logs]
        }
    except Exception as e:
        logger.error(f"Failed to query access logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 日志导出 API ====================

@router.post("/export", summary="导出日志")
async def export_logs(request: LogExportRequest):
    """
    导出日志到指定位置

    支持 JSON 和 CSV 格式
    """
    # 简化实现，实际应该创建异步导出任务
    try:
        export_id = f"export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        return {
            "export_id": export_id,
            "status": "completed",
            "message": "Export feature is under development",
            "log_type": request.log_type,
            "time_range": {
                "start": request.time_range_start,
                "end": request.time_range_end
            }
        }
    except Exception as e:
        logger.error(f"Failed to export logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 保留策略 API ====================

@router.get("/retention", summary="获取保留策略")
async def get_retention_policies():
    """获取所有日志保留策略"""
    try:
        policies = await log_storage_service.get_retention_policies()
        return {
            "policies": [p.to_dict() for p in policies]
        }
    except Exception as e:
        logger.error(f"Failed to get retention policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retention", summary="更新保留策略")
async def update_retention_policy(request: RetentionPolicyRequest):
    """更新日志保留策略"""
    try:
        from models.audit_log import LogRetentionPolicy
        policy = LogRetentionPolicy(
            log_type=request.log_type,
            retention_days=request.retention_days,
            storage_backend=request.storage_backend,
            export_enabled=request.export_enabled,
            export_destination=request.export_destination
        )
        await log_storage_service.update_retention_policy(policy)
        return {"status": "success", "policy": policy.to_dict()}
    except Exception as e:
        logger.error(f"Failed to update retention policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", summary="手动触发清理")
async def trigger_cleanup():
    """手动触发日志清理任务"""
    try:
        result = await log_cleanup_service.apply_retention_policies()
        return {
            "status": "success",
            "result": result.to_dict()
        }
    except Exception as e:
        logger.error(f"Failed to cleanup logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cleanup/stats", summary="获取清理统计")
async def get_cleanup_statistics():
    """获取日志清理统计信息"""
    try:
        stats = await log_cleanup_service.get_cleanup_statistics()
        return {"statistics": stats}
    except Exception as e:
        logger.error(f"Failed to get cleanup statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 日志分析 API ====================

@router.get("/analyze/activity", summary="用户活动分析")
async def analyze_user_activity(
    user_id: str = Query(..., description="用户 ID"),
    hours: int = Query(default=24, ge=1, le=720, description="时间范围（小时）")
):
    """分析用户活动"""
    try:
        report = await log_analytics_service.analyze_user_activity(
            user_id=user_id,
            hours=hours
        )
        return {"report": report.to_dict()}
    except Exception as e:
        logger.error(f"Failed to analyze user activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/anomalies", summary="异常检测")
async def detect_anomalies(
    hours: int = Query(default=24, ge=1, le=168, description="时间范围（小时）")
):
    """检测异常日志模式"""
    try:
        anomalies = await log_analytics_service.detect_anomalies(hours=hours)
        return {
            "anomalies": [a.to_dict() for a in anomalies],
            "total": len(anomalies)
        }
    except Exception as e:
        logger.error(f"Failed to detect anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/compliance", summary="合规报告")
async def generate_compliance_report(
    report_type: str = Query(..., description="报告类型"),
    days: int = Query(default=30, ge=1, le=365, description="时间范围（天）"),
    tenant_id: str = Query(..., description="租户 ID")
):
    """生成合规报告"""
    try:
        report = await log_analytics_service.generate_compliance_report(
            report_type=report_type,
            tenant_id=tenant_id,
            days=days
        )
        return {"report": report.to_dict()}
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-trail/{resource_type}/{resource_id}", summary="资源审计轨迹")
async def get_audit_trail(
    resource_type: str,
    resource_id: str,
    tenant_id: Optional[str] = Query(default=None, description="租户 ID"),
    hours: int = Query(default=168, ge=1, le=720, description="时间范围（小时）")
):
    """获取资源的审计轨迹"""
    try:
        logs = await log_analytics_service.get_audit_trail(
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            hours=hours
        )
        return {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "total_events": len(logs),
            "logs": [log.to_dict() for log in logs]
        }
    except Exception as e:
        logger.error(f"Failed to get audit trail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", summary="日志统计")
async def get_log_statistics(
    hours: int = Query(default=24, ge=1, le=168, description="时间范围（小时）")
):
    """获取日志统计信息"""
    try:
        stats = await log_analytics_service.get_log_statistics(hours=hours)
        return {"statistics": stats}
    except Exception as e:
        logger.error(f"Failed to get log statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 健康检查 ====================

@router.get("/health", summary="健康检查")
async def health_check():
    """日志服务健康检查"""
    return {
        "status": "healthy",
        "service": "log-storage",
        "timestamp": datetime.utcnow().isoformat()
    }
