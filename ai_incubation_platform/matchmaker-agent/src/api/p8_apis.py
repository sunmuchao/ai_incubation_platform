"""
P8 企业数据看板与绩效管理 - API 路由

包含路由：
- /api/dashboard - 企业数据看板
- /api/performance - 绩效管理
- /api/departments - 组织架构
- /api/operators - 运营角色管理
- /api/exports - 数据导出
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.database import get_db
from services.p8_services import (
    EnterpriseDashboardService,
    PerformanceService,
    DepartmentService,
    OperatorService,
    ExportService
)


# ============= 企业数据看板路由 =============

router_dashboard = APIRouter(prefix="/api/dashboard", tags=["P8-企业数据看板"])


@router_dashboard.get("/overview")
async def get_dashboard_overview(
    days: int = Query(default=7, ge=1, le=90, description="天数范围"),
    db: Session = Depends(get_db)
):
    """
    获取企业数据看板概览

    返回核心指标：
    - 用户数据：总数、活跃数、新增数
    - 匹配数据：总匹配数、成功率
    - 收入数据：总收入、订单数
    - 安全数据：举报数、处理率
    - 活跃度数据：滑动数、消息数
    """
    service = EnterpriseDashboardService(db)
    return service.get_dashboard_overview(days=days)


@router_dashboard.get("/metrics")
async def get_dashboard_metrics(
    db: Session = Depends(get_db)
):
    """
    获取核心指标详情

    返回各类型指标的详细信息
    """
    service = EnterpriseDashboardService(db)
    return {
        "user_metrics": service._get_user_stats(datetime.now() - timedelta(days=7)),
        "match_metrics": service._get_match_stats(datetime.now() - timedelta(days=7)),
        "revenue_metrics": service._get_revenue_stats(datetime.now() - timedelta(days=7)),
        "safety_metrics": service._get_safety_stats(datetime.now() - timedelta(days=7)),
        "engagement_metrics": service._get_engagement_stats(datetime.now() - timedelta(days=7))
    }


@router_dashboard.get("/trends/{trend_type}")
async def get_trend_data(
    trend_type: str,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    获取趋势数据

    支持的趋势类型：
    - user_growth_trend: 用户增长趋势
    - matching_success_trend: 匹配成功趋势
    - revenue_trend: 收入趋势
    """
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")

    service = EnterpriseDashboardService(db)
    return service.get_trend_data(trend_type, start, end)


@router_dashboard.post("/reports")
async def generate_report(
    report_type: str = Query(..., description="报告类型"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """生成数据报告"""
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")

    service = EnterpriseDashboardService(db)
    return service.generate_report(report_type, start, end)


@router_dashboard.get("/reports")
async def get_reports(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取报告列表"""
    service = EnterpriseDashboardService(db)
    return service.get_reports(limit=limit)


@router_dashboard.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """获取报告详情"""
    from models.p8_models import DashboardReportDB
    report = db.query(DashboardReportDB).filter(
        DashboardReportDB.id == report_id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    return {
        "id": report.id,
        "title": report.title,
        "report_type": report.report_type,
        "report_data": report.report_data,
        "created_at": report.created_at.isoformat()
    }


# ============= 绩效管理路由 =============

router_performance = APIRouter(prefix="/api/performance", tags=["P8-绩效管理"])


@router_performance.get("/kpi-definitions")
async def get_kpi_definitions(db: Session = Depends(get_db)):
    """获取 KPI 指标定义列表"""
    service = PerformanceService(db)
    return service.get_kpi_definitions()


@router_performance.put("/kpi/{metric_name}")
async def update_kpi_value(
    metric_name: str,
    value: float,
    db: Session = Depends(get_db)
):
    """更新 KPI 当前值"""
    service = PerformanceService(db)
    try:
        return service.update_kpi_value(metric_name, value)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router_performance.post("/reviews")
async def create_performance_review(
    user_id: str,
    review_type: str,
    period_type: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """创建绩效评估"""
    service = PerformanceService(db)
    period_end = datetime.now()
    period_start = period_end - timedelta(days=days)

    return service.create_performance_review(
        user_id=user_id,
        review_type=review_type,
        period_start=period_start,
        period_end=period_end,
        period_type=period_type
    )


@router_performance.get("/reviews/{user_id}")
async def get_performance_history(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取用户绩效历史"""
    service = PerformanceService(db)
    return service.get_performance_history(user_id, limit)


@router_performance.get("/users/{user_id}/summary")
async def get_performance_summary(
    user_id: str,
    db: Session = Depends(get_db)
):
    """获取用户绩效摘要"""
    service = PerformanceService(db)
    return service.get_performance_summary(user_id)


# ============= 组织架构路由 =============

router_departments = APIRouter(prefix="/api/departments", tags=["P8-组织架构"])


@router_departments.post("")
async def create_department(
    name: str,
    code: str,
    level: int,
    parent_id: Optional[str] = None,
    description: Optional[str] = None,
    manager_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """创建部门"""
    service = DepartmentService(db)
    try:
        return service.create_department(
            name=name,
            code=code,
            level=level,
            parent_id=parent_id,
            description=description,
            manager_id=manager_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_departments.get("")
async def get_departments(
    is_active: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    """获取部门列表"""
    service = DepartmentService(db)
    return service.get_departments(is_active)


@router_departments.get("/tree")
async def get_department_tree(db: Session = Depends(get_db)):
    """获取组织架构树"""
    service = DepartmentService(db)
    return service.get_department_tree()


@router_departments.get("/{dept_id}")
async def get_department(
    dept_id: str,
    db: Session = Depends(get_db)
):
    """获取部门详情"""
    service = DepartmentService(db)
    dept = service.get_department(dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")
    return dept


@router_departments.put("/{dept_id}")
async def update_department(
    dept_id: str,
    name: Optional[str] = None,
    code: Optional[str] = None,
    level: Optional[int] = None,
    parent_id: Optional[str] = None,
    description: Optional[str] = None,
    manager_id: Optional[str] = None,
    sort_order: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """更新部门"""
    service = DepartmentService(db)
    kwargs = {k: v for k, v in {
        "name": name, "code": code, "level": level,
        "parent_id": parent_id, "description": description,
        "manager_id": manager_id, "sort_order": sort_order
    }.items() if v is not None}

    result = service.update_department(dept_id, **kwargs)
    if not result:
        raise HTTPException(status_code=404, detail="部门不存在")
    return result


@router_departments.delete("/{dept_id}")
async def delete_department(
    dept_id: str,
    db: Session = Depends(get_db)
):
    """删除部门 (软删除)"""
    service = DepartmentService(db)
    if not service.delete_department(dept_id):
        raise HTTPException(status_code=404, detail="部门不存在")
    return {"message": "部门已删除"}


# ============= 运营角色管理路由 =============

router_operators = APIRouter(prefix="/api/operators", tags=["P8-运营角色"])


@router_operators.post("/roles")
async def create_role(
    role_name: str,
    description: str,
    permissions: List[str],
    db: Session = Depends(get_db)
):
    """创建角色"""
    service = OperatorService(db)
    return service.create_role(role_name, description, permissions)


@router_operators.get("/roles")
async def get_roles(
    is_active: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    """获取角色列表"""
    service = OperatorService(db)
    return service.get_roles(is_active)


@router_operators.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: str,
    role_id: str,
    department_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """给用户分配角色"""
    service = OperatorService(db)
    return service.assign_role_to_user(user_id, role_id, department_id)


@router_operators.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: str,
    db: Session = Depends(get_db)
):
    """获取用户的角色"""
    service = OperatorService(db)
    return service.get_user_roles(user_id)


@router_operators.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    db: Session = Depends(get_db)
):
    """获取用户权限列表"""
    service = OperatorService(db)
    return {"permissions": service.get_user_permissions(user_id)}


@router_operators.post("/logs")
async def log_operator_action(
    operator_id: str,
    action_type: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    action_details: Optional[Dict] = None,
    result: str = "success",
    ip_address: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """记录运营操作日志"""
    service = OperatorService(db)
    return service.log_operator_action(
        operator_id=operator_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        action_details=action_details,
        result=result,
        ip_address=ip_address
    )


@router_operators.get("/logs")
async def get_action_logs(
    operator_id: Optional[str] = None,
    action_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取操作日志"""
    service = OperatorService(db)
    return service.get_action_logs(operator_id, action_type, limit)


# ============= 数据导出路由 =============

router_exports = APIRouter(prefix="/api/exports", tags=["P8-数据导出"])


@router_exports.post("")
async def create_export_task(
    export_type: str,
    export_format: str,
    export_params: Optional[Dict] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """创建导出任务"""
    # 获取请求者 ID (实际应从认证信息中获取)
    requested_by = "system"  # TODO: 从 JWT token 中获取

    service = ExportService(db)
    return service.create_export_task(
        requested_by=requested_by,
        export_type=export_type,
        export_format=export_format,
        export_params=export_params
    )


@router_exports.get("/{task_id}")
async def get_export_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取导出任务状态"""
    service = ExportService(db)
    task = service.get_export_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router_exports.get("")
async def get_export_history(
    requested_by: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """获取导出历史"""
    # 实际应从认证信息中获取 requested_by
    if not requested_by:
        requested_by = "system"  # TODO: 从 JWT token 中获取

    service = ExportService(db)
    return service.get_export_history(requested_by, limit)


@router_exports.post("/{task_id}/complete")
async def complete_export_task(
    task_id: str,
    file_url: str,
    file_size: int,
    db: Session = Depends(get_db)
):
    """标记导出任务完成"""
    service = ExportService(db)
    if not service.complete_export_task(task_id, file_url, file_size):
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"message": "任务已完成"}


@router_exports.post("/{task_id}/fail")
async def fail_export_task(
    task_id: str,
    error_message: str,
    db: Session = Depends(get_db)
):
    """标记导出任务失败"""
    service = ExportService(db)
    if not service.fail_export_task(task_id, error_message):
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"message": "任务已标记为失败"}


# 导出路由器供 main.py 使用
__all__ = [
    "router_dashboard",
    "router_performance",
    "router_departments",
    "router_operators",
    "router_exports"
]
