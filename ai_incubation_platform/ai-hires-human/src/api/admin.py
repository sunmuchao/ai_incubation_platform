"""
运营后台 API - 提供平台运营所需的只读数据接口。
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional, Any

from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.task import Task, TaskStatus, TaskPriority, InteractionType
from models.payment import PaymentTransaction
from services.admin_service import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=dict)
async def get_platform_stats():
    """
    获取平台整体统计数据。

    返回内容包括:
    - task_stats: 任务统计（总数、按状态/交互类型/优先级分布）
    - payment_stats: 支付统计（总流水、总服务费）
    - user_stats: 用户统计（工人数、雇主数、钱包数）
    - time_stats: 时间统计（今日/本周新增和完成任务数）
    """
    return admin_service.get_platform_stats()


@router.get("/tasks", response_model=List[Task])
async def get_admin_task_list(
    status: Optional[TaskStatus] = None,
    interaction_type: Optional[InteractionType] = None,
    priority: Optional[TaskPriority] = None,
    keyword: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """
    获取任务列表（管理视角）。

    支持按状态、交互类型、优先级、关键词筛选。
    """
    return admin_service.get_task_list(
        status=status,
        interaction_type=interaction_type,
        priority=priority,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )


@router.get("/tasks/{task_id}", response_model=Task)
async def get_admin_task_detail(task_id: str):
    """获取任务详情（管理视角）。"""
    task = admin_service.get_task_detail(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/users", response_model=List[dict])
async def get_admin_user_list(
    user_type: str = "all",  # all, worker, employer
    skip: int = 0,
    limit: int = 100,
):
    """
    获取用户列表。

    - user_type: all（全部）, worker（工人）, employer（雇主）
    """
    if user_type not in ("all", "worker", "employer"):
        raise HTTPException(
            status_code=400,
            detail="Invalid user_type. Must be one of: all, worker, employer"
        )
    return admin_service.get_user_list(user_type=user_type, skip=skip, limit=limit)


@router.get("/users/{user_id}")
async def get_admin_user_detail(user_id: str):
    """获取用户详情（包含任务历史、钱包余额等）。"""
    # 获取用户参与的任务
    tasks = admin_service.get_task_list(skip=0, limit=1000)
    user_tasks = [
        t for t in tasks
        if t.worker_id == user_id or t.ai_employer_id == user_id
    ]

    # 获取钱包余额
    wallet = payment_service.get_wallet_balance(user_id)

    # 获取交易记录
    txs = payment_service.list_user_transactions(user_id, limit=50)

    return {
        "user_id": user_id,
        "wallet": wallet,
        "task_count": len(user_tasks),
        "as_worker": len([t for t in user_tasks if t.worker_id == user_id]),
        "as_employer": len([t for t in user_tasks if t.ai_employer_id == user_id]),
        "recent_transactions": txs[:10],
    }


@router.get("/transactions", response_model=List[dict])
async def get_admin_transaction_list(
    transaction_type: Optional[str] = None,
    user_id: Optional[str] = None,
    task_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """
    获取交易记录列表。

    支持按交易类型、用户、任务筛选。
    """
    return admin_service.get_transaction_list(
        transaction_type=transaction_type,
        user_id=user_id,
        task_id=task_id,
        skip=skip,
        limit=limit,
    )


@router.get("/transactions/{transaction_id}", response_model=dict)
async def get_admin_transaction_detail(transaction_id: str):
    """获取交易详情。"""
    tx = payment_service.get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.get("/cheating-reports", response_model=List[dict])
async def get_cheating_reports():
    """获取作弊报告列表。"""
    return admin_service.get_cheating_reports()


@router.get("/dashboard")
async def get_admin_dashboard():
    """
    获取管理仪表板数据（概览）。

    返回用于仪表板展示的关键指标。
    """
    stats = admin_service.get_platform_stats()
    cheating_reports = admin_service.get_cheating_reports()

    return {
        "overview": {
            "total_tasks": stats['task_stats']['total'],
            "active_workers": stats['user_stats']['total_workers'],
            "active_employers": stats['user_stats']['total_employers'],
            "total_volume": stats['payment_stats']['total_volume'],
        },
        "task_breakdown": stats['task_stats']['by_status'],
        "recent_activity": stats['time_stats'],
        "alerts": {
            "cheating_cases": len(cheating_reports),
        },
    }
