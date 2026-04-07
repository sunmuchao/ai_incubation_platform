"""
实时数据仪表板 - API 接口。

提供实时数据仪表板的各类指标查询接口。
"""
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ==================== 响应模型 ====================

class OverviewResponse(BaseModel):
    """总览数据响应。"""
    time_range: str
    start_time: Optional[str]
    end_time: str
    generated_at: str

    # 任务指标
    total_tasks: int = 0
    tasks_by_status: Dict[str, int] = Field(default_factory=dict)
    task_completion_rate: float = 0.0
    avg_completion_time_hours: float = 0.0

    # 工人指标
    active_workers: int = 0
    total_workers: int = 0
    avg_tasks_per_worker: float = 0.0
    avg_worker_rating: float = 0.0

    # 质量指标
    approval_rate: float = 0.0
    dispute_rate: float = 0.0
    cheating_rate: float = 0.0
    pending_manual_review: int = 0

    # 财务指标
    total_gmv: float = 0.0
    platform_fees: float = 0.0
    pending_settlement: float = 0.0
    total_wallet_balance: float = 0.0


class TrendDataPoint(BaseModel):
    """趋势数据点。"""
    date: str
    created: Optional[int] = None
    completed: Optional[int] = None
    active_workers: Optional[int] = None
    gmv: Optional[float] = None


class TrendResponse(BaseModel):
    """趋势数据响应。"""
    trend_type: str
    days: int
    data: list[TrendDataPoint]


class TaskAnalysisResponse(BaseModel):
    """任务分析数据响应。"""
    total_tasks: int
    tasks_by_status: Dict[str, int]
    tasks_by_interaction_type: Dict[str, int]
    tasks_by_priority: Dict[str, int]
    avg_completion_time_hours: float
    task_completion_rate: float
    top_reward_tasks: list[Dict[str, Any]]


class WorkerAnalysisResponse(BaseModel):
    """工人分析数据响应。"""
    total_workers: int
    active_workers: int
    workers_by_level: Dict[int, int]
    avg_worker_rating: float
    avg_success_rate: float
    top_workers: list[Dict[str, Any]]


class QualityAnalysisResponse(BaseModel):
    """质量分析数据响应。"""
    approval_rate: float
    dispute_rate: float
    cheating_rate: float
    pending_manual_review: int
    rejection_reasons: Dict[str, int]
    quality_trend: str  # improving/stable/declining


class FinancialAnalysisResponse(BaseModel):
    """财务分析数据响应。"""
    total_gmv: float
    platform_fees: float
    pending_settlement: float
    total_wallet_balance: float
    gmv_trend: str  # increasing/stable/decreasing
    avg_task_reward: float


# ==================== API 接口 ====================

@router.get("/overview", response_model=OverviewResponse, summary="获取总览数据")
async def get_dashboard_overview(
    time_range: str = Query(
        default="realtime",
        description="时间范围：realtime/hourly/daily/weekly/monthly/all"
    ),
    organization_id: Optional[str] = Query(
        default=None,
        description="组织 ID（用于团队权限过滤）"
    ),
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取仪表板总览数据。

    包含任务、工人、质量、财务四大类核心指标。
    """
    # 验证时间范围参数
    valid_ranges = ["realtime", "hourly", "daily", "weekly", "monthly", "all"]
    if time_range not in valid_ranges:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time_range. Must be one of: {valid_ranges}"
        )

    service = DashboardService(db)
    metrics = await service.get_overview_metrics(time_range, organization_id)

    return OverviewResponse(**metrics)


@router.get("/tasks", response_model=TaskAnalysisResponse, summary="获取任务分析数据")
async def get_task_analysis(
    time_range: str = Query(default="daily"),
    organization_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取任务分析数据。

    包含任务状态分布、交互类型分布、优先级分布等详细分析。
    """
    service = DashboardService(db)

    # 获取基础指标
    overview = await service.get_overview_metrics(time_range, organization_id)

    # 获取任务趋势
    trend = await service.get_task_trend(days=7, organization_id=organization_id)

    # 查询高报酬任务（示例）
    from models.db_models import TaskDB
    from sqlalchemy import select, desc

    top_reward_query = select(TaskDB).where(
        TaskDB.status == 'published'
    ).order_by(desc(TaskDB.reward_amount)).limit(5)

    result = await db.execute(top_reward_query)
    top_tasks = [
        {
            "id": task.id,
            "title": task.title,
            "reward_amount": task.reward_amount,
        }
        for task in result.scalars().all()
    ]

    return TaskAnalysisResponse(
        total_tasks=overview.get("total_tasks", 0),
        tasks_by_status=overview.get("tasks_by_status", {}),
        tasks_by_interaction_type={},  # TODO: 实现详细分析
        tasks_by_priority={},  # TODO: 实现详细分析
        avg_completion_time_hours=overview.get("avg_completion_time_hours", 0.0),
        task_completion_rate=overview.get("task_completion_rate", 0.0),
        top_reward_tasks=top_tasks,
    )


@router.get("/workers", response_model=WorkerAnalysisResponse, summary="获取工人分析数据")
async def get_worker_analysis(
    time_range: str = Query(default="daily"),
    organization_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取工人分析数据。

    包含工人等级分布、活跃度、绩效等详细分析。
    """
    from models.db_models import WorkerProfileDB, WorkerSubmissionDB
    from sqlalchemy import select, func, desc

    # 总工人数
    total_query = select(func.count(WorkerProfileDB.worker_id))
    result = await db.execute(total_query)
    total_workers = result.scalar() or 0

    # 活跃工人数（最近 7 天有提交）
    from datetime import timedelta
    seven_days_ago = datetime.now() - timedelta(days=7)
    active_query = select(
        func.count(func.distinct(WorkerSubmissionDB.worker_id))
    ).where(
        WorkerSubmissionDB.submitted_at >= seven_days_ago
    )
    result = await db.execute(active_query)
    active_workers = result.scalar() or 0

    # 工人等级分布
    level_query = select(
        WorkerProfileDB.level,
        func.count(WorkerProfileDB.worker_id).label('count')
    ).group_by(WorkerProfileDB.level)
    result = await db.execute(level_query)
    workers_by_level = {row.level: row.count for row in result.fetchall()}

    # 平均评分
    rating_query = select(func.avg(WorkerProfileDB.average_rating))
    result = await db.execute(rating_query)
    avg_rating = result.scalar() or 0.0

    # 平均成功率
    success_query = select(func.avg(WorkerProfileDB.success_rate))
    result = await db.execute(success_query)
    avg_success = result.scalar() or 0.0

    # 顶级工人
    top_query = select(WorkerProfileDB).order_by(
        desc(WorkerProfileDB.average_rating),
        desc(WorkerProfileDB.completed_tasks)
    ).limit(5)
    result = await db.execute(top_query)
    top_workers_list = [
        {
            "worker_id": w.worker_id,
            "name": w.name,
            "completed_tasks": w.completed_tasks,
            "average_rating": w.average_rating,
            "success_rate": w.success_rate,
        }
        for w in result.scalars().all()
    ]

    return WorkerAnalysisResponse(
        total_workers=total_workers,
        active_workers=active_workers,
        workers_by_level=workers_by_level,
        avg_worker_rating=round(avg_rating, 2),
        avg_success_rate=round(avg_success, 2),
        top_workers=top_workers_list,
    )


@router.get("/quality", response_model=QualityAnalysisResponse, summary="获取质量分析数据")
async def get_quality_analysis(
    time_range: str = Query(default="daily"),
    organization_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取质量分析数据。

    包含验收通过率、争议率、作弊检测率等质量指标。
    """
    service = DashboardService(db)
    overview = await service.get_overview_metrics(time_range, organization_id)

    # TODO: 实现拒绝原因分析
    rejection_reasons = {}

    # 计算质量趋势（简化版）
    quality_trend = "stable"
    approval_rate = overview.get("approval_rate", 0.0)
    if approval_rate >= 90:
        quality_trend = "improving"
    elif approval_rate < 70:
        quality_trend = "declining"

    return QualityAnalysisResponse(
        approval_rate=overview.get("approval_rate", 0.0),
        dispute_rate=overview.get("dispute_rate", 0.0),
        cheating_rate=overview.get("cheating_rate", 0.0),
        pending_manual_review=overview.get("pending_manual_review", 0),
        rejection_reasons=rejection_reasons,
        quality_trend=quality_trend,
    )


@router.get("/financial", response_model=FinancialAnalysisResponse, summary="获取财务分析数据")
async def get_financial_analysis(
    time_range: str = Query(default="daily"),
    organization_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取财务分析数据。

    包含 GMV、平台收入、待结算金额等财务指标。
    """
    from models.db_models import TaskDB, PaymentTransactionDB
    from sqlalchemy import select, func

    service = DashboardService(db)
    overview = await service.get_overview_metrics(time_range, organization_id)

    # 获取财务趋势
    trend = await service.get_financial_trend(days=7, organization_id=organization_id)

    # 计算 GMV 趋势
    gmv_trend = "stable"
    if len(trend["data"]) >= 2:
        recent_gmv = [d["gmv"] for d in trend["data"][-3:]]
        if all(recent_gmv[i] <= recent_gmv[i+1] for i in range(len(recent_gmv)-1)):
            gmv_trend = "increasing"
        elif all(recent_gmv[i] >= recent_gmv[i+1] for i in range(len(recent_gmv)-1)):
            gmv_trend = "decreasing"

    # 平均任务报酬
    avg_reward_query = select(func.avg(TaskDB.reward_amount))
    result = await db.execute(avg_reward_query)
    avg_reward = result.scalar() or 0.0

    return FinancialAnalysisResponse(
        total_gmv=overview.get("total_gmv", 0.0),
        platform_fees=overview.get("platform_fees", 0.0),
        pending_settlement=overview.get("pending_settlement", 0.0),
        total_wallet_balance=overview.get("total_wallet_balance", 0.0),
        gmv_trend=gmv_trend,
        avg_task_reward=round(avg_reward, 2),
    )


@router.get("/trend/tasks", response_model=TrendResponse, summary="获取任务趋势")
async def get_task_trend(
    days: int = Query(default=7, ge=1, le=30, description="天数范围 (1-30)"),
    organization_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session)
):
    """获取任务趋势数据（最近 N 天）。"""
    service = DashboardService(db)
    trend = await service.get_task_trend(days, organization_id)
    return TrendResponse(**trend)


@router.get("/trend/workers", response_model=TrendResponse, summary="获取工人活跃趋势")
async def get_worker_trend(
    days: int = Query(default=7, ge=1, le=30, description="天数范围 (1-30)"),
    organization_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session)
):
    """获取工人活跃趋势数据。"""
    service = DashboardService(db)
    trend = await service.get_worker_trend(days, organization_id)
    return TrendResponse(**trend)


@router.get("/trend/financial", response_model=TrendResponse, summary="获取财务趋势")
async def get_financial_trend(
    days: int = Query(default=7, ge=1, le=30, description="天数范围 (1-30)"),
    organization_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session)
):
    """获取财务趋势数据。"""
    service = DashboardService(db)
    trend = await service.get_financial_trend(days, organization_id)
    return TrendResponse(**trend)


@router.get("/metrics", summary="获取所有可用指标列表")
async def get_available_metrics():
    """获取仪表板支持的所有指标定义。"""
    return {
        "task_metrics": {
            "total_tasks": {"name": "任务总数", "unit": "个", "category": "task"},
            "task_completion_rate": {"name": "任务完成率", "unit": "%", "category": "task"},
            "avg_completion_time_hours": {"name": "平均完成时间", "unit": "小时", "category": "task"},
        },
        "worker_metrics": {
            "active_workers": {"name": "活跃工人数", "unit": "人", "category": "worker"},
            "total_workers": {"name": "总工人数", "unit": "人", "category": "worker"},
            "avg_worker_rating": {"name": "工人平均评分", "unit": "分", "category": "worker"},
        },
        "quality_metrics": {
            "approval_rate": {"name": "验收通过率", "unit": "%", "category": "quality"},
            "dispute_rate": {"name": "争议率", "unit": "%", "category": "quality"},
            "cheating_rate": {"name": "作弊检测率", "unit": "%", "category": "quality"},
        },
        "financial_metrics": {
            "total_gmv": {"name": "交易总额", "unit": "元", "category": "financial"},
            "platform_fees": {"name": "平台服务费", "unit": "元", "category": "financial"},
            "pending_settlement": {"name": "待结算金额", "unit": "元", "category": "financial"},
        },
    }
