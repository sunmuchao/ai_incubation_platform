"""
企业级功能 API

包含：
- 列级权限管理
- 行级策略管理
- 租户配额管理
- 租户使用统计
- 增强审计日志
- 合规报告
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header, Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime

from services.enterprise_service import enterprise_service
from utils.logger import logger

router = APIRouter(prefix="/api/enterprise", tags=["企业级功能"])


# ==================== 请求/响应模型 ====================

class ColumnPermissionRequest(BaseModel):
    """列权限请求"""
    role_name: str = Field(..., description="角色名称")
    datasource_name: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    column_name: str = Field(..., description="列名")
    access_type: str = Field("deny", description="访问类型：allow/deny")


class RowLevelPolicyRequest(BaseModel):
    """行级策略请求"""
    role_name: str = Field(..., description="角色名称")
    datasource_name: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    filter_condition: str = Field(..., description="过滤条件 (SQL WHERE 子句，不含 WHERE 关键字)")
    description: str = Field(None, description="策略描述")
    priority: int = Field(0, description="优先级")


class TenantQuotaRequest(BaseModel):
    """租户配额请求"""
    daily_query_limit: int = Field(None, description="每日查询次数限制")
    monthly_query_limit: int = Field(None, description="每月查询次数限制")
    max_concurrent_queries: int = Field(None, description="最大并发查询数")
    max_storage_gb: float = Field(None, description="最大存储空间 (GB)")
    max_datasources: int = Field(None, description="最大数据源数量")
    reset_day: int = Field(None, description="月度配额重置日 (1-28)")


class ComplianceReportRequest(BaseModel):
    """合规报告请求"""
    report_type: str = Field(..., description="报告类型：soc2/gdpr/hipaa/custom")
    start_date: date = Field(..., description="报告开始日期")
    end_date: date = Field(..., description="报告结束日期")


# ==================== 列级权限 API ====================

@router.post("/column-permissions")
async def create_column_permission(
    request: ColumnPermissionRequest,
    x_user_id: str = Header(None, description="用户 ID")
) -> Dict[str, Any]:
    """创建列级权限"""
    result = await enterprise_service.create_column_permission(
        role_name=request.role_name,
        datasource_name=request.datasource_name,
        table_name=request.table_name,
        column_name=request.column_name,
        access_type=request.access_type,
        created_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))

    return result


@router.get("/column-permissions")
async def list_column_permissions(
    role_name: Optional[str] = Query(None, description="角色名称"),
    datasource_name: Optional[str] = Query(None, description="数据源名称"),
    table_name: Optional[str] = Query(None, description="表名")
) -> Dict[str, Any]:
    """获取列权限列表"""
    permissions = await enterprise_service.get_column_permissions(
        role_name=role_name,
        datasource_name=datasource_name,
        table_name=table_name
    )
    return {"permissions": permissions}


@router.delete("/column-permissions/{permission_id}")
async def delete_column_permission(
    permission_id: str = Path(..., description="权限 ID")
) -> Dict[str, Any]:
    """删除列权限"""
    result = await enterprise_service.delete_column_permission(permission_id)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "权限不存在"))

    return result


@router.get("/users/{user_id}/column-permissions/{datasource_name}/{table_name}")
async def get_user_column_permissions(
    user_id: str = Path(..., description="用户 ID"),
    datasource_name: str = Path(..., description="数据源名称"),
    table_name: str = Path(..., description="表名")
) -> Dict[str, Any]:
    """获取用户对指定表的列权限"""
    permissions = await enterprise_service.get_user_column_permissions(
        user_id=user_id,
        datasource_name=datasource_name,
        table_name=table_name
    )
    return {"permissions": permissions}


# ==================== 行级策略 API ====================

@router.post("/row-policies")
async def create_row_level_policy(
    request: RowLevelPolicyRequest,
    x_user_id: str = Header(None, description="用户 ID")
) -> Dict[str, Any]:
    """创建行级策略"""
    result = await enterprise_service.create_row_level_policy(
        role_name=request.role_name,
        datasource_name=request.datasource_name,
        table_name=request.table_name,
        filter_condition=request.filter_condition,
        description=request.description,
        priority=request.priority,
        created_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))

    return result


@router.get("/row-policies")
async def list_row_level_policies(
    role_name: Optional[str] = Query(None, description="角色名称"),
    datasource_name: Optional[str] = Query(None, description="数据源名称"),
    table_name: Optional[str] = Query(None, description="表名"),
    active_only: bool = Query(True, description="是否仅获取活跃策略")
) -> Dict[str, Any]:
    """获取行级策略列表"""
    policies = await enterprise_service.get_row_level_policies(
        role_name=role_name,
        datasource_name=datasource_name,
        table_name=table_name,
        active_only=active_only
    )
    return {"policies": policies}


@router.put("/row-policies/{policy_id}")
async def update_row_level_policy(
    policy_id: str = Path(..., description="策略 ID"),
    filter_condition: Optional[str] = Body(None, description="过滤条件"),
    description: Optional[str] = Body(None, description="策略描述"),
    priority: Optional[int] = Body(None, description="优先级"),
    is_active: Optional[bool] = Body(None, description="是否活跃")
) -> Dict[str, Any]:
    """更新行级策略"""
    result = await enterprise_service.update_row_level_policy(
        policy_id=policy_id,
        filter_condition=filter_condition,
        description=description,
        priority=priority,
        is_active=is_active
    )

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "策略不存在"))

    return result


@router.delete("/row-policies/{policy_id}")
async def delete_row_level_policy(
    policy_id: str = Path(..., description="策略 ID")
) -> Dict[str, Any]:
    """删除行级策略"""
    result = await enterprise_service.delete_row_level_policy(policy_id)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "策略不存在"))

    return result


@router.get("/users/{user_id}/row-policies/{datasource_name}/{table_name}")
async def get_user_row_level_policies(
    user_id: str = Path(..., description="用户 ID"),
    datasource_name: str = Path(..., description="数据源名称"),
    table_name: str = Path(..., description="表名")
) -> Dict[str, Any]:
    """获取用户对指定表的行级策略"""
    policies = await enterprise_service.get_user_row_level_policies(
        user_id=user_id,
        datasource_name=datasource_name,
        table_name=table_name
    )
    return {"policies": policies}


@router.get("/users/{user_id}/row-filters/{datasource_name}/{table_name}")
async def get_user_row_filter(
    user_id: str = Path(..., description="用户 ID"),
    datasource_name: str = Path(..., description="数据源名称"),
    table_name: str = Path(..., description="表名")
) -> Dict[str, Any]:
    """获取用户的行级过滤条件"""
    filter_condition = await enterprise_service.build_row_level_filter(
        user_id=user_id,
        datasource_name=datasource_name,
        table_name=table_name
    )
    return {"filter_condition": filter_condition}


# ==================== 租户配额 API ====================

@router.put("/tenants/{tenant_code}/quota")
async def set_tenant_quota(
    tenant_code: str = Path(..., description="租户编码"),
    request: TenantQuotaRequest = None,
    x_user_id: str = Header(None, description="用户 ID")
) -> Dict[str, Any]:
    """设置租户配额"""
    result = await enterprise_service.set_tenant_quota(
        tenant_code=tenant_code,
        daily_query_limit=request.daily_query_limit if request else None,
        monthly_query_limit=request.monthly_query_limit if request else None,
        max_concurrent_queries=request.max_concurrent_queries if request else None,
        max_storage_gb=request.max_storage_gb if request else None,
        max_datasources=request.max_datasources if request else None,
        reset_day=request.reset_day if request else None,
        created_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "设置失败"))

    return result


@router.get("/tenants/{tenant_code}/quota")
async def get_tenant_quota(
    tenant_code: str = Path(..., description="租户编码")
) -> Dict[str, Any]:
    """获取租户配额"""
    quota = await enterprise_service.get_tenant_quota(tenant_code)
    if not quota:
        raise HTTPException(status_code=404, detail="租户配额不存在")
    return {"quota": quota}


@router.post("/tenants/{tenant_code}/quota/check")
async def check_quota_limit(
    tenant_code: str = Path(..., description="租户编码"),
    query_count: int = Body(1, description="查询次数"),
    concurrent_count: int = Body(None, description="并发数")
) -> Dict[str, Any]:
    """检查配额限制"""
    allowed, reason = await enterprise_service.check_quota_limit(
        tenant_code=tenant_code,
        query_count=query_count,
        concurrent_count=concurrent_count
    )
    return {"allowed": allowed, "reason": reason}


# ==================== 租户使用统计 API ====================

@router.post("/tenants/{tenant_code}/usage")
async def record_tenant_usage(
    tenant_code: str = Path(..., description="租户编码"),
    query_count: int = Body(1, description="查询次数"),
    failed_query_count: int = Body(0, description="失败查询次数"),
    query_duration_ms: float = Body(0, description="查询耗时 (ms)"),
    storage_used_gb: float = Body(0, description="存储空间 (GB)"),
    concurrent_count: int = Body(0, description="并发数"),
    active_datasources: int = Body(0, description="活跃数据源数"),
    active_users: int = Body(0, description="活跃用户数")
) -> Dict[str, Any]:
    """记录租户使用统计"""
    result = await enterprise_service.record_tenant_usage(
        tenant_code=tenant_code,
        query_count=query_count,
        failed_query_count=failed_query_count,
        query_duration_ms=query_duration_ms,
        storage_used_gb=storage_used_gb,
        concurrent_count=concurrent_count,
        active_datasources=active_datasources,
        active_users=active_users
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "记录失败"))

    return result


@router.get("/tenants/{tenant_code}/usage")
async def get_tenant_usage(
    tenant_code: str = Path(..., description="租户编码"),
    stat_date: Optional[date] = Query(None, description="统计日期")
) -> Dict[str, Any]:
    """获取租户使用统计"""
    usage = await enterprise_service.get_tenant_usage(tenant_code, stat_date)
    if not usage:
        raise HTTPException(status_code=404, detail="未找到使用统计")
    return {"usage": usage}


@router.get("/tenants/{tenant_code}/usage-range")
async def get_tenant_usage_range(
    tenant_code: str = Path(..., description="租户编码"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期")
) -> Dict[str, Any]:
    """获取租户使用统计范围"""
    usages = await enterprise_service.get_tenant_usage_range(
        tenant_code=tenant_code,
        start_date=start_date,
        end_date=end_date
    )
    return {"usages": usages}


# ==================== 增强审计日志 API ====================

@router.get("/audit-logs")
async def list_audit_logs(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    tenant_id: Optional[str] = Query(None, description="租户 ID"),
    action: Optional[str] = Query(None, description="操作类型"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    resource_id: Optional[str] = Query(None, description="资源 ID"),
    is_anomaly: Optional[bool] = Query(None, description="是否异常"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> Dict[str, Any]:
    """获取审计日志"""
    logs = await enterprise_service.get_audit_logs(
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        is_anomaly=is_anomaly,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    return {"logs": logs}


@router.get("/audit-statistics")
async def get_audit_statistics(
    tenant_id: Optional[str] = Query(None, description="租户 ID"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间")
) -> Dict[str, Any]:
    """获取审计统计"""
    stats = await enterprise_service.get_audit_statistics(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date
    )
    return {"statistics": stats}


@router.post("/audit-logs")
async def create_audit_log(
    trace_id: str = Body(..., description="链路追踪 ID"),
    user_id: str = Body(..., description="用户 ID"),
    action: str = Body(..., description="操作类型"),
    resource_type: str = Body(..., description="资源类型"),
    resource_id: Optional[str] = Body(None, description="资源 ID"),
    tenant_id: Optional[str] = Body(None, description="租户 ID"),
    request_method: Optional[str] = Body(None, description="请求方法"),
    request_path: Optional[str] = Body(None, description="请求路径"),
    request_body: Optional[Dict] = Body(None, description="请求体"),
    response_status: Optional[int] = Body(None, description="响应状态码"),
    response_body: Optional[Dict] = Body(None, description="响应体"),
    before_state: Optional[Dict] = Body(None, description="操作前状态"),
    after_state: Optional[Dict] = Body(None, description="操作后状态"),
    duration_ms: Optional[int] = Body(None, description="耗时 (ms)"),
    risk_score: Optional[float] = Body(0.0, description="风险评分"),
    is_anomaly: Optional[bool] = Body(False, description="是否异常")
) -> Dict[str, Any]:
    """创建审计日志"""
    result = await enterprise_service.log_audit(
        trace_id=trace_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=tenant_id,
        request_method=request_method,
        request_path=request_path,
        request_body=request_body,
        response_status=response_status,
        response_body=response_body,
        before_state=before_state,
        after_state=after_state,
        duration_ms=duration_ms,
        risk_score=risk_score,
        is_anomaly=is_anomaly
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))

    return result


# ==================== 合规报告 API ====================

@router.post("/compliance-reports")
async def generate_compliance_report(
    tenant_code: str = Path(..., description="租户编码"),
    request: ComplianceReportRequest = None,
    x_user_id: str = Header(None, description="用户 ID")
) -> Dict[str, Any]:
    """生成合规报告"""
    result = await enterprise_service.generate_compliance_report(
        tenant_code=tenant_code,
        report_type=request.report_type,
        start_date=request.start_date,
        end_date=request.end_date,
        created_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "生成失败"))

    return result


@router.get("/compliance-reports/{report_id}")
async def get_compliance_report(
    report_id: str = Path(..., description="报告 ID")
) -> Dict[str, Any]:
    """获取合规报告"""
    report = await enterprise_service.get_compliance_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"report": report}


@router.get("/tenants/{tenant_code}/compliance-reports")
async def list_compliance_reports(
    tenant_code: str = Path(..., description="租户编码"),
    report_type: Optional[str] = Query(None, description="报告类型"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> Dict[str, Any]:
    """获取合规报告列表"""
    reports = await enterprise_service.list_compliance_reports(
        tenant_code=tenant_code,
        report_type=report_type,
        limit=limit,
        offset=offset
    )
    return {"reports": reports}
