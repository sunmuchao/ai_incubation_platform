"""
P8 阶段 API 路由 - 企业数据分析与绩效管理

路由列表:
1. /api/enterprise/dashboard - 企业数据看板
2. /api/performance - 绩效管理
3. /api/departments - 组织架构
4. /api/webhooks - Webhook 集成
5. /api/exports - 数据导出
"""

from fastapi import APIRouter, HTTPException, Header, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.p8_models import (
    EnterpriseDashboard, PerformanceReview, KPIMetric, PerformanceLevel,
    Department, DepartmentLevel, WebhookSubscription, WebhookEventType, WebhookStatus,
    ExportReport, ExportRequest, ReportType, ReportFormat,
    DashboardResponse, PerformanceReviewRequest, PerformanceReviewResponse,
    DepartmentRequest, DepartmentResponse, WebhookRequest, WebhookResponse, ExportResponse
)
from services.p8_services import (
    dashboard_service, performance_service, department_service,
    webhook_service, export_service
)

router = APIRouter(prefix="/api", tags=["P8 - 企业数据分析与绩效管理"])


# ==================== 企业数据看板路由 ====================

@router.get("/enterprise/dashboard", summary="获取企业数据看板")
async def get_enterprise_dashboard(
    tenant_id: str = Query(..., description="租户 ID"),
    user_id: str = Query(..., description="用户 ID"),
    period: str = Query("month", description="时间范围：today, week, month, quarter, year")
) -> DashboardResponse:
    """
    获取企业数据看板，包含：
    - 核心指标（员工数、订单数、收入、成本等）
    - 趋势数据
    - 图表数据
    - Top 员工排行榜
    - 警告/提醒
    """
    try:
        dashboard = dashboard_service.get_dashboard(tenant_id, user_id, period)
        return DashboardResponse(
            success=True,
            dashboard=dashboard,
            message="看板数据获取成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enterprise/metrics", summary="获取核心指标")
async def get_core_metrics(
    tenant_id: str = Query(..., description="租户 ID"),
    period: str = Query("month", description="时间范围")
) -> Dict[str, Any]:
    """获取核心指标数据"""
    dashboard = dashboard_service.get_dashboard(tenant_id, "system", period)
    return {
        "success": True,
        "metrics": dashboard.metrics.dict()
    }


@router.get("/enterprise/trends", summary="获取趋势数据")
async def get_trend_data(
    tenant_id: str = Query(..., description="租户 ID"),
    period: str = Query("month", description="时间范围"),
    metrics: List[str] = Query(["revenue", "orders"], description="需要获取的指标")
) -> Dict[str, Any]:
    """获取指定指标的趋势数据"""
    dashboard = dashboard_service.get_dashboard(tenant_id, "system", period)
    trends = {k: v for k, v in dashboard.trends.items() if k in metrics}
    return {
        "success": True,
        "trends": {k: [t.dict() for t in v] for k, v in trends.items()}
    }


@router.get("/enterprise/top-employees", summary="获取 Top 员工")
async def get_top_employees(
    tenant_id: str = Query(..., description="租户 ID"),
    period: str = Query("month", description="时间范围"),
    limit: int = Query(10, description="返回数量限制")
) -> Dict[str, Any]:
    """获取表现最好的员工排行榜"""
    dashboard = dashboard_service.get_dashboard(tenant_id, "system", period)
    return {
        "success": True,
        "top_employees": dashboard.top_employees[:limit]
    }


# ==================== 绩效管理路由 ====================

@router.post("/performance/reviews", summary="创建绩效评估", response_model=PerformanceReviewResponse)
async def create_performance_review(
    request: PerformanceReviewRequest
) -> PerformanceReviewResponse:
    """
    创建员工绩效评估

    - **employee_id**: 员工 ID
    - **review_period**: 评估周期（如 2024-Q1, 2024-01）
    - **kpi_metrics**: KPI 指标列表
    - **comments**: 评语
    """
    try:
        # 将请求数据转换为 KPIMetric 对象
        kpi_metrics = [
            KPIMetric(
                metric_id=m["metric_id"],
                metric_name=m["metric_name"],
                target_value=m["target_value"],
                actual_value=m["actual_value"],
                weight=m.get("weight", 1.0),
                score=m.get("score", 0.0),
                trend=m.get("trend", "stable")
            )
            for m in request.kpi_metrics
        ]

        review = performance_service.create_review(
            employee_id=request.employee_id,
            employee_name="",  # 需要从数据库获取
            reviewer_id="current_user",  # 从认证信息获取
            tenant_id="default",  # 从认证信息获取
            review_period=request.review_period,
            kpi_metrics=kpi_metrics,
            comments=request.comments
        )

        return PerformanceReviewResponse(
            success=True,
            review=review,
            message="绩效评估创建成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/reviews/{review_id}", summary="获取绩效评估")
async def get_performance_review(review_id: str) -> Dict[str, Any]:
    """获取指定的绩效评估"""
    review = performance_service.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="绩效评估不存在")

    return {
        "success": True,
        "review": review.dict()
    }


@router.get("/performance/employees/{employee_id}/history", summary="获取员工绩效历史")
async def get_employee_performance_history(employee_id: str) -> Dict[str, Any]:
    """获取员工的绩效历史记录和趋势分析"""
    history = performance_service.get_employee_history(employee_id)
    return {
        "success": True,
        "history": history.dict()
    }


@router.get("/performance/kpi-definitions", summary="获取 KPI 定义")
async def get_kpi_definitions() -> Dict[str, Any]:
    """获取默认的 KPI 指标定义"""
    definitions = performance_service.get_default_kpi_definitions()
    return {
        "success": True,
        "definitions": definitions
    }


# ==================== 组织架构路由 ====================

@router.post("/departments", summary="创建部门", response_model=DepartmentResponse)
async def create_department(request: DepartmentRequest) -> DepartmentResponse:
    """
    创建企业部门

    - **name**: 部门名称
    - **parent_id**: 父部门 ID（可选，为空则为顶级部门）
    - **level**: 部门层级
    - **manager_id**: 部门经理 ID（可选）
    - **description**: 部门描述
    - **budget**: 部门预算（可选）
    """
    try:
        department = department_service.create_department(
            tenant_id="default",  # 从认证信息获取
            name=request.name,
            parent_id=request.parent_id,
            level=request.level,
            manager_id=request.manager_id,
            description=request.description,
            budget=request.budget
        )

        return DepartmentResponse(
            success=True,
            department=department,
            message="部门创建成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/departments", summary="获取部门列表")
async def get_departments(
    tenant_id: str = Query(..., description="租户 ID")
) -> Dict[str, Any]:
    """获取租户的所有部门列表"""
    departments = department_service.get_tenant_departments(tenant_id)
    return {
        "success": True,
        "departments": [d.dict() for d in departments]
    }


@router.get("/departments/tree", summary="获取部门树形结构")
async def get_department_tree(
    tenant_id: str = Query(..., description="租户 ID")
) -> Dict[str, Any]:
    """获取企业组织架构图（树形结构）"""
    org_chart = department_service.get_department_tree(tenant_id)
    return {
        "success": True,
        "organization_chart": org_chart.dict()
    }


@router.get("/departments/{dept_id}", summary="获取部门详情")
async def get_department(dept_id: str) -> Dict[str, Any]:
    """获取指定部门的详细信息"""
    department = department_service.get_department(dept_id)
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")

    return {
        "success": True,
        "department": department.dict()
    }


@router.put("/departments/{dept_id}", summary="更新部门")
async def update_department(
    dept_id: str,
    request: DepartmentRequest
) -> Dict[str, Any]:
    """更新部门信息"""
    department = department_service.update_department(
        dept_id,
        name=request.name,
        parent_id=request.parent_id,
        level=request.level,
        manager_id=request.manager_id,
        description=request.description,
        budget=request.budget
    )

    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")

    return {
        "success": True,
        "department": department.dict()
    }


@router.delete("/departments/{dept_id}", summary="删除部门")
async def delete_department(dept_id: str) -> Dict[str, Any]:
    """删除部门"""
    success = department_service.delete_department(dept_id)
    if not success:
        raise HTTPException(status_code=404, detail="部门不存在")

    return {
        "success": True,
        "message": "部门删除成功"
    }


# ==================== Webhook 集成路由 ====================

@router.post("/webhooks", summary="创建 Webhook 订阅", response_model=WebhookResponse)
async def create_webhook(request: WebhookRequest) -> WebhookResponse:
    """
    创建 Webhook 订阅

    - **name**: 订阅名称
    - **url**: Webhook 接收地址
    - **events**: 订阅的事件类型列表
    """
    try:
        subscription = webhook_service.create_subscription(
            tenant_id="default",  # 从认证信息获取
            created_by="current_user",  # 从认证信息获取
            name=request.name,
            url=request.url,
            events=request.events
        )

        return WebhookResponse(
            success=True,
            subscription=subscription,
            message=f"Webhook 创建成功，密钥：{subscription.secret}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks", summary="获取 Webhook 列表")
async def get_webhooks(
    tenant_id: str = Query(..., description="租户 ID")
) -> Dict[str, Any]:
    """获取租户的所有 Webhook 订阅"""
    subscriptions = webhook_service.get_tenant_subscriptions(tenant_id)
    return {
        "success": True,
        "subscriptions": [
            {
                **s.dict(),
                "secret": "***"  # 隐藏密钥
            }
            for s in subscriptions
        ]
    }


@router.get("/webhooks/{sub_id}", summary="获取 Webhook 详情")
async def get_webhook(sub_id: str) -> Dict[str, Any]:
    """获取指定的 Webhook 订阅详情"""
    subscription = webhook_service.get_subscription(sub_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Webhook 订阅不存在")

    return {
        "success": True,
        "subscription": {
            **subscription.dict(),
            "secret": "***"  # 隐藏密钥
        }
    }


@router.put("/webhooks/{sub_id}", summary="更新 Webhook")
async def update_webhook(
    sub_id: str,
    name: Optional[str] = None,
    url: Optional[str] = None,
    events: Optional[List[WebhookEventType]] = None,
    status: Optional[WebhookStatus] = None
) -> Dict[str, Any]:
    """更新 Webhook 订阅"""
    subscription = webhook_service.update_subscription(
        sub_id,
        name=name,
        url=url,
        events=events,
        status=status
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="Webhook 订阅不存在")

    return {
        "success": True,
        "subscription": subscription.dict()
    }


@router.delete("/webhooks/{sub_id}", summary="删除 Webhook")
async def delete_webhook(sub_id: str) -> Dict[str, Any]:
    """删除 Webhook 订阅"""
    success = webhook_service.delete_subscription(sub_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook 订阅不存在")

    return {
        "success": True,
        "message": "Webhook 删除成功"
    }


@router.post("/webhooks/{sub_id}/test", summary="测试 Webhook")
async def test_webhook(sub_id: str) -> Dict[str, Any]:
    """发送测试事件到 Webhook"""
    subscription = webhook_service.get_subscription(sub_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Webhook 订阅不存在")

    # 发送测试事件
    deliveries = webhook_service.trigger_webhook(
        tenant_id=subscription.tenant_id,
        event_type=WebhookEventType.ORDER_CREATED,
        data={"test": True, "message": "这是一条测试消息"}
    )

    return {
        "success": True,
        "message": "测试事件已发送",
        "delivery_status": deliveries[0].status if deliveries else "unknown"
    }


@router.get("/webhooks/{sub_id}/deliveries", summary="获取投递历史")
async def get_webhook_deliveries(
    sub_id: str,
    limit: int = Query(50, description="返回数量限制")
) -> Dict[str, Any]:
    """获取 Webhook 投递历史记录"""
    deliveries = webhook_service.get_delivery_history(sub_id, limit)
    return {
        "success": True,
        "deliveries": [d.dict() for d in deliveries]
    }


# ==================== 数据导出路由 ====================

@router.post("/exports", summary="创建导出任务", response_model=ExportResponse)
async def create_export(request: ExportRequest) -> ExportResponse:
    """
    创建数据导出任务

    - **report_type**: 报告类型（performance, analytics, financial, usage）
    - **format**: 导出格式（pdf, excel, csv, json）
    - **period**: 时间范围
    - **filters**: 筛选条件
    - **include_charts**: 是否包含图表
    - **include_raw_data**: 是否包含原始数据
    """
    try:
        report = export_service.create_export(
            tenant_id="default",  # 从认证信息获取
            requested_by="current_user",  # 从认证信息获取
            request=request
        )

        return ExportResponse(
            success=True,
            report=report,
            message="导出任务已创建，处理完成后将通过通知告知"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exports/{report_id}", summary="获取导出报告状态")
async def get_export_report(report_id: str) -> Dict[str, Any]:
    """获取导出报告的状态和下载链接"""
    report = export_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="导出报告不存在")

    return {
        "success": True,
        "report": report.dict()
    }


@router.get("/exports", summary="获取导出历史")
async def get_export_history(
    tenant_id: str = Query(..., description="租户 ID")
) -> Dict[str, Any]:
    """获取租户的导出历史记录"""
    reports = export_service.get_tenant_reports(tenant_id)
    return {
        "success": True,
        "reports": [r.dict() for r in reports]
    }


@router.get("/exports/{report_id}/download", summary="下载导出文件")
async def download_export(report_id: str):
    """下载导出的文件"""
    report = export_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="导出报告不存在")

    if report.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"导出尚未完成，当前状态：{report.status}"
        )

    # TODO: 实际实现文件下载
    return {
        "success": True,
        "file_url": report.file_url,
        "file_size": report.file_size
    }


# ==================== 系统信息 ====================

@router.get("/p8/info", summary="P8 服务信息")
async def get_p8_info() -> Dict[str, Any]:
    """获取 P8 服务信息和功能列表"""
    return {
        "version": "v1.0",
        "features": [
            "企业数据看板",
            "绩效管理",
            "组织架构",
            "Webhook 集成",
            "数据导出"
        ],
        "endpoints": {
            "dashboard": "/api/enterprise/dashboard",
            "performance": "/api/performance/reviews",
            "departments": "/api/departments",
            "webhooks": "/api/webhooks",
            "exports": "/api/exports"
        }
    }
