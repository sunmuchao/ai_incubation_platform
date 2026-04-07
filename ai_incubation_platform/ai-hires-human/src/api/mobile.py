"""
P11 移动端优化 - API 层。

提供移动端优化的 HTTP 接口，包括：
- 响应式数据格式
- 离线模式支持
- 推送通知
- 移动端任务管理
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_session
from models.db_models import (
    TaskDB,
    WorkerProfileDB,
    WorkerSubmissionDB,
    EmployerProfileDB,
)

router = APIRouter(prefix="/api/mobile", tags=["mobile"])


# ==================== 响应模型 ====================

class MobileTaskItem(BaseModel):
    """移动端任务项（精简版）。"""
    id: int
    title: str
    description: str
    reward_amount: float
    interaction_type: str
    status: str
    created_at: str
    deadline: Optional[str] = None
    # 移动端特有字段
    distance: Optional[float] = None  # 距离（米）
    estimated_duration: Optional[int] = None  # 预估时长（分钟）
    is_urgent: bool = False


class MobileTaskListResponse(BaseModel):
    """移动端任务列表响应。"""
    tasks: List[MobileTaskItem]
    total: int
    has_more: bool
    cursor: Optional[str] = None


class MobileTaskDetailResponse(BaseModel):
    """移动端任务详情响应。"""
    task: MobileTaskItem
    acceptance_criteria: str
    employer_info: Optional[Dict[str, Any]] = None
    worker_info: Optional[Dict[str, Any]] = None
    submission: Optional[Dict[str, Any]] = None


class MobileWorkerProfileResponse(BaseModel):
    """移动端工人资料响应。"""
    worker_id: int
    name: str
    level: int
    level_name: str
    completed_tasks: int
    success_rate: float
    average_rating: float
    total_earnings: float
    available_balance: float
    # 移动端特有字段
    today_earnings: float = 0.0
    week_earnings: float = 0.0
    active_tasks: int = 0
    badges: List[Dict[str, Any]] = Field(default_factory=list)


class MobileNotificationItem(BaseModel):
    """移动端通知项。"""
    id: int
    type: str
    title: str
    message: str
    created_at: str
    is_read: bool = False
    action_url: Optional[str] = None
    priority: str = "normal"  # low/normal/high


class MobileNotificationListResponse(BaseModel):
    """移动端通知列表响应。"""
    notifications: List[MobileNotificationItem]
    unread_count: int
    has_more: bool


class MobileDashboardResponse(BaseModel):
    """移动端仪表板响应。"""
    # 工人视图
    active_tasks: int = 0
    pending_submissions: int = 0
    available_balance: float = 0.0
    today_earnings: float = 0.0
    recommended_tasks: List[MobileTaskItem] = Field(default_factory=list)

    # 雇主视图
    published_tasks: int = 0
    pending_review: int = 0
    total_spent: float = 0.0

    # 通用
    notifications_unread: int = 0
    system_announcements: List[Dict[str, Any]] = Field(default_factory=list)


class OfflineDataResponse(BaseModel):
    """离线数据响应。"""
    sync_timestamp: str
    tasks: List[MobileTaskItem] = Field(default_factory=list)
    worker_profile: Optional[MobileWorkerProfileResponse] = None
    notifications: List[MobileNotificationItem] = Field(default_factory=list)
    # 增量更新标识
    has_updates: bool = False


# ==================== 移动端任务列表 ====================

@router.get("/tasks", response_model=MobileTaskListResponse, summary="移动端任务列表")
async def get_mobile_tasks(
    status: Optional[str] = Query(default=None, description="任务状态筛选"),
    interaction_type: Optional[str] = Query(default=None, description="交互类型筛选"),
    limit: int = Query(default=20, ge=1, le=50, description="每页数量"),
    cursor: Optional[str] = Query(default=None, description="游标"),
    lat: Optional[float] = Query(default=None, description="纬度（用于距离计算）"),
    lng: Optional[float] = Query(default=None, description="经度（用于距离计算）"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取移动端任务列表（精简版，适合手机屏幕展示）。

    支持：
    - 分页加载（游标分页）
    - 位置筛选（附近任务）
    - 状态筛选
    - 交互类型筛选
    """
    # 构建查询
    query = select(TaskDB).where(TaskDB.status == "published")

    if status:
        query = query.where(TaskDB.status == status)
    if interaction_type:
        query = query.where(TaskDB.interaction_type == interaction_type)

    # 按创建时间倒序
    query = query.order_by(desc(TaskDB.created_at)).limit(limit + 1)

    if cursor:
        try:
            cursor_date = datetime.fromisoformat(cursor)
            query = query.where(TaskDB.created_at < cursor_date)
        except ValueError:
            pass

    result = await db.execute(query)
    tasks = result.scalars().all()

    has_more = len(tasks) > limit
    if has_more:
        tasks = tasks[:limit]

    # 转换为移动端格式
    task_items = []
    for task in tasks:
        is_urgent = False
        if task.deadline:
            remaining = (task.deadline - datetime.now()).total_seconds()
            is_urgent = remaining < 3600  # 1 小时内截止

        task_items.append(
            MobileTaskItem(
                id=task.id,
                title=task.title[:50] + "..." if len(task.title) > 50 else task.title,
                description=task.description[:100] + "..." if len(task.description) > 100 else task.description,
                reward_amount=task.reward_amount,
                interaction_type=task.interaction_type,
                status=task.status,
                created_at=task.created_at.isoformat() if task.created_at else None,
                deadline=task.deadline.isoformat() if task.deadline else None,
                is_urgent=is_urgent,
                estimated_duration=30,  # TODO: 基于历史数据估算
            )
        )

    next_cursor = tasks[-1].created_at.isoformat() if tasks and has_more else None

    return MobileTaskListResponse(
        tasks=task_items,
        total=len(task_items),
        has_more=has_more,
        cursor=next_cursor,
    )


@router.get("/tasks/{task_id}", response_model=MobileTaskDetailResponse, summary="移动端任务详情")
async def get_mobile_task_detail(
    task_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    """获取任务详情（移动端优化版）。"""
    task_query = select(TaskDB).where(TaskDB.id == task_id)
    result = await db.execute(task_query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 获取雇主信息（脱敏）
    employer_info = None
    if task.employer_id:
        employer_query = select(EmployerProfileDB).where(
            EmployerProfileDB.employer_id == task.employer_id
        )
        result = await db.execute(employer_query)
        employer = result.scalar_one_or_none()
        if employer:
            employer_info = {
                "name": employer.name[:10] + "***" if employer.name else "匿名雇主",
                "rating": employer.average_rating,
                "completion_rate": employer.task_completion_rate,
            }

    # 获取工人信息（如果有）
    worker_info = None
    if task.accepted_by_worker_id:
        worker_query = select(WorkerProfileDB).where(
            WorkerProfileDB.worker_id == task.accepted_by_worker_id
        )
        result = await db.execute(worker_query)
        worker = result.scalar_one_or_none()
        if worker:
            worker_info = {
                "name": worker.name[:10] + "***" if worker.name else "匿名工人",
                "level": worker.level,
                "success_rate": worker.success_rate,
            }

    return MobileTaskDetailResponse(
        task=MobileTaskItem(
            id=task.id,
            title=task.title,
            description=task.description,
            reward_amount=task.reward_amount,
            interaction_type=task.interaction_type,
            status=task.status,
            created_at=task.created_at.isoformat() if task.created_at else None,
            deadline=task.deadline.isoformat() if task.deadline else None,
        ),
        acceptance_criteria=task.acceptance_criteria or "",
        employer_info=employer_info,
        worker_info=worker_info,
    )


# ==================== 移动端工人资料 ====================

@router.get("/worker/profile", response_model=MobileWorkerProfileResponse, summary="移动端工人资料")
async def get_mobile_worker_profile(
    worker_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    """获取工人资料（移动端优化版）。"""
    worker_query = select(WorkerProfileDB).where(
        WorkerProfileDB.worker_id == worker_id
    )
    result = await db.execute(worker_query)
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # 计算今日收入
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = select(
        func.sum(TaskDB.reward_amount)
    ).where(
        TaskDB.accepted_by_worker_id == worker_id,
        TaskDB.status == "completed",
        TaskDB.completed_at >= today_start
    )
    result = await db.execute(today_query)
    today_earnings = float(result.scalar() or 0)

    # 计算本周收入
    week_start = today_start - timedelta(days=7)
    week_query = select(
        func.sum(TaskDB.reward_amount)
    ).where(
        TaskDB.accepted_by_worker_id == worker_id,
        TaskDB.status == "completed",
        TaskDB.completed_at >= week_start
    )
    result = await db.execute(week_query)
    week_earnings = float(result.scalar() or 0)

    # 计算活跃任务数
    active_query = select(
        func.count(TaskDB.id)
    ).where(
        TaskDB.accepted_by_worker_id == worker_id,
        TaskDB.status.in_(["accepted", "in_progress", "submitted"])
    )
    result = await db.execute(active_query)
    active_tasks = result.scalar() or 0

    # 获取徽章（简化版）
    badges = []
    if worker.completed_tasks >= 100:
        badges.append({"name": "百日百单", "icon": "🏆", "description": "完成 100 个任务"})
    if worker.success_rate >= 0.95:
        badges.append({"name": "质量保证", "icon": "✅", "description": "成功率 95% 以上"})
    if worker.average_rating >= 4.8:
        badges.append({"name": "明星工人", "icon": "⭐", "description": "平均评分 4.8 以上"})

    # 等级名称映射
    level_names = {
        1: "青铜", 2: "白银", 3: "黄金", 4: "钻石", 5: "王者"
    }

    return MobileWorkerProfileResponse(
        worker_id=worker.worker_id,
        name=worker.name,
        level=worker.level,
        level_name=level_names.get(worker.level, "青铜"),
        completed_tasks=worker.completed_tasks or 0,
        success_rate=worker.success_rate or 0,
        average_rating=worker.average_rating or 0,
        total_earnings=worker.total_earnings or 0,
        available_balance=worker.available_balance or 0,
        today_earnings=today_earnings,
        week_earnings=week_earnings,
        active_tasks=active_tasks,
        badges=badges,
    )


# ==================== 移动端仪表板 ====================

@router.get("/dashboard", response_model=MobileDashboardResponse, summary="移动端仪表板")
async def get_mobile_dashboard(
    user_type: str = Query(default="worker", description="用户类型：worker/employer"),
    user_id: int = Query(default=0, description="用户 ID"),
    db: AsyncSession = Depends(get_db_session),
):
    """获取移动端仪表板数据（快速概览）。"""
    dashboard = MobileDashboardResponse()

    if user_type == "worker":
        # 工人视图
        if user_id:
            # 活跃任务数
            active_query = select(
                func.count(TaskDB.id)
            ).where(
                TaskDB.accepted_by_worker_id == user_id,
                TaskDB.status.in_(["accepted", "in_progress", "submitted"])
            )
            result = await db.execute(active_query)
            dashboard.active_tasks = result.scalar() or 0

            # 待提交任务数
            pending_query = select(
                func.count(TaskDB.id)
            ).where(
                TaskDB.accepted_by_worker_id == user_id,
                TaskDB.status.in_(["accepted", "in_progress"])
            )
            result = await db.execute(pending_query)
            dashboard.pending_submissions = result.scalar() or 0

            # 推荐任务（最近的 5 个已发布任务）
            recommended_query = select(TaskDB).where(
                TaskDB.status == "published"
            ).order_by(desc(TaskDB.created_at)).limit(5)
            result = await db.execute(recommended_query)
            dashboard.recommended_tasks = [
                MobileTaskItem(
                    id=t.id,
                    title=t.title[:30],
                    description=t.description[:50],
                    reward_amount=t.reward_amount,
                    interaction_type=t.interaction_type,
                    status=t.status,
                    created_at=t.created_at.isoformat() if t.created_at else None,
                )
                for t in result.scalars().all()
            ]

    elif user_type == "employer":
        # 雇主视图
        if user_id:
            # 已发布任务数
            published_query = select(
                func.count(TaskDB.id)
            ).where(
                TaskDB.employer_id == user_id,
                TaskDB.status.in_(["published", "in_progress", "submitted"])
            )
            result = await db.execute(published_query)
            dashboard.published_tasks = result.scalar() or 0

            # 待审核任务数
            pending_query = select(
                func.count(TaskDB.id)
            ).where(
                TaskDB.employer_id == user_id,
                TaskDB.status == "submitted"
            )
            result = await db.execute(pending_query)
            dashboard.pending_review = result.scalar() or 0

    # 未读通知数（简化）
    dashboard.notifications_unread = 0

    # 系统公告
    dashboard.system_announcements = [
        {
            "id": 1,
            "title": "平台更新通知",
            "content": "新增 P11 移动端优化功能",
            "priority": "normal",
            "created_at": datetime.now().isoformat()
        }
    ]

    return dashboard


# ==================== 离线模式支持 ====================

@router.get("/offline/sync", response_model=OfflineDataResponse, summary="离线数据同步")
async def get_offline_data(
    user_type: str = Query(default="worker", description="用户类型"),
    user_id: int = Query(default=0, description="用户 ID"),
    last_sync: Optional[str] = Query(default=None, description="上次同步时间"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取离线数据（用于离线模式）。

    返回用户需要的核心数据，支持离线浏览和操作。
    """
    now = datetime.now()

    # 获取任务数据
    tasks_query = select(TaskDB).where(
        or_(
            TaskDB.status == "published",
            TaskDB.accepted_by_worker_id == user_id
        )
    ).order_by(desc(TaskDB.created_at)).limit(50)

    result = await db.execute(tasks_query)
    tasks = result.scalars().all()

    task_items = [
        MobileTaskItem(
            id=t.id,
            title=t.title[:50],
            description=t.description[:100],
            reward_amount=t.reward_amount,
            interaction_type=t.interaction_type,
            status=t.status,
            created_at=t.created_at.isoformat() if t.created_at else None,
        )
        for t in tasks
    ]

    # 获取通知数据（简化）
    notifications = []

    # 判断是否有更新
    has_updates = True
    if last_sync:
        try:
            last_sync_dt = datetime.fromisoformat(last_sync)
            # 检查是否有新数据
            has_updates = any(
                t.created_at and t.created_at > last_sync_dt
                for t in tasks
            )
        except ValueError:
            pass

    return OfflineDataResponse(
        sync_timestamp=now.isoformat(),
        tasks=task_items,
        notifications=notifications,
        has_updates=has_updates,
    )


# ==================== 移动端配置 ====================

@router.get("/config", summary="移动端配置")
async def get_mobile_config():
    """获取移动端配置信息。"""
    return {
        "app_version": "1.0.0",
        "min_supported_version": "0.9.0",
        "features": {
            "offline_mode": True,
            "push_notifications": True,
            "location_services": True,
            "camera_upload": True,
            "biometric_auth": False,
        },
        "ui_config": {
            "theme": "auto",  # auto/light/dark
            "language": "zh-CN",
            "date_format": "YYYY-MM-DD",
            "time_format": "HH:mm",
        },
        "api_config": {
            "timeout_seconds": 30,
            "retry_count": 3,
            "cache_ttl_seconds": 300,
        },
    }


# ==================== 快速操作 ====================

@router.post("/tasks/{task_id}/quick-accept", summary="快速接单")
async def quick_accept_task(
    task_id: int,
    worker_id: int = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
):
    """快速接单（移动端优化）。"""
    # 获取任务
    task_query = select(TaskDB).where(TaskDB.id == task_id)
    result = await db.execute(task_query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "published":
        raise HTTPException(status_code=400, detail="Task is not available")

    # 更新任务状态
    task.status = "accepted"
    task.accepted_by_worker_id = worker_id
    task.accepted_at = datetime.now()

    await db.commit()

    return {
        "success": True,
        "message": "接单成功",
        "task_id": task_id,
    }


@router.post("/tasks/{task_id}/quick-submit", summary="快速提交")
async def quick_submit_task(
    task_id: int,
    worker_id: int = Body(..., embed=True),
    result_data: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db_session),
):
    """快速提交任务（移动端优化）。"""
    # 获取任务
    task_query = select(TaskDB).where(TaskDB.id == task_id)
    result = await db.execute(task_query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.accepted_by_worker_id != worker_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if task.status not in ["accepted", "in_progress"]:
        raise HTTPException(status_code=400, detail="Task is not in progress")

    # 更新任务状态
    task.status = "submitted"
    task.result_data = result_data
    task.submitted_at = datetime.now()

    await db.commit()

    return {
        "success": True,
        "message": "提交成功，等待雇主验收",
        "task_id": task_id,
    }
