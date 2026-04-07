"""
任务 API — AI 因能力缺口雇佣真人；真人接单、交付、AI 验收。
"""
from __future__ import annotations

from datetime import datetime
import os
import sys
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.task import (
    InteractionType,
    Task,
    TaskAcceptBody,
    TaskAppealBody,
    TaskCancelBody,
    TaskCompleteBody,
    TaskCreate,
    TaskManualReviewBody,
    TaskPriority,
    TaskStatus,
    TaskSubmitBody,
)
from services.anti_cheat_service import anti_cheat_service
from services.callback_service import notify_task_completed_by_id
from services.task_service import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/search", response_model=List[Task])
async def search_tasks(
    skill: Optional[str] = None,
    min_reward: float = 0,
    max_reward: Optional[float] = None,
    interaction_type: Optional[InteractionType] = None,
    location: Optional[str] = None,
    priority: Optional[TaskPriority] = None,
    keyword: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    """真人侧：浏览可接任务（须为已发布），支持多维度筛选与排序。

    - sort_by 可选值: created_at, reward, priority, deadline
    - sort_order 可选值: asc, desc
    """
    allowed_sort_by = {"created_at", "reward", "priority", "deadline"}
    allowed_sort_order = {"asc", "desc"}
    sort_by_normalized = sort_by.lower().strip()
    sort_order_normalized = sort_order.lower().strip()
    if sort_by_normalized not in allowed_sort_by:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by: {sort_by}")
    if sort_order_normalized not in allowed_sort_order:
        raise HTTPException(
            status_code=400, detail=f"Invalid sort_order: {sort_order}"
        )
    if min_reward < 0:
        raise HTTPException(status_code=400, detail="Invalid min_reward: must be >= 0")
    if max_reward is not None and max_reward < min_reward:
        raise HTTPException(
            status_code=400, detail="Invalid max_reward: must be >= min_reward"
        )
    return task_service.search_tasks(
        skill=skill,
        min_reward=min_reward,
        max_reward=max_reward,
        interaction_type=interaction_type,
        location=location,
        priority=priority,
        keyword=keyword,
        sort_by=sort_by_normalized,
        sort_order=sort_order_normalized,
    )


@router.get("", response_model=List[Task])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    interaction_type: Optional[InteractionType] = None,
):
    """列表：可按状态、交互类型筛选（含运营/AI 侧查询）。"""
    return task_service.list_tasks(
        status=status,
        interaction_type=interaction_type,
    )


@router.post("", response_model=Task)
async def create_task(task_data: TaskCreate):
    """AI / Agent 发布任务（默认因能力缺口立即进入可接单状态）。"""
    return task_service.create_task(task_data)


@router.post("/{task_id}/publish")
async def publish_task(task_id: str):
    """将仍为 pending 的任务发布到市场。"""
    if not task_service.publish_task(task_id):
        raise HTTPException(
            status_code=400,
            detail="Task not found or not in pending status",
        )
    return {"message": "published", "task_id": task_id}


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """任务详情。"""
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/accept")
async def accept_task(task_id: str, body: TaskAcceptBody):
    """真人接单。"""
    if not task_service.accept_task(task_id, body.worker_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot accept: task missing, not published, or already taken",
        )
    return {"message": "Task accepted", "task_id": task_id, "worker_id": body.worker_id}


@router.post("/{task_id}/submit")
async def submit_work(task_id: str, body: TaskSubmitBody):
    """提交交付物（进入待 AI 验收）。"""
    # 反作弊检测
    # 1. 检查提交频率
    freq_ok, freq_reason = anti_cheat_service.check_submission_frequency(body.worker_id)
    if not freq_ok:
        raise HTTPException(
            status_code=429,
            detail=f"Submission rejected: {freq_reason}",
        )

    # 2. 检查重复交付
    dup_ok, dup_reason = anti_cheat_service.check_duplicate_delivery(
        task_id, body.content, body.attachments, body.worker_id
    )
    if not dup_ok:
        raise HTTPException(
            status_code=400,
            detail=f"Submission rejected: {dup_reason}",
        )

    # 3. 提交到任务服务
    ok = task_service.submit_work(
        task_id,
        body.worker_id,
        body.content,
        body.attachments,
    )
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Submit failed: wrong worker, or task not in progress",
        )

    # 记录提交到反作弊系统
    task = task_service.get_task(task_id)
    if task:
        content_hash = anti_cheat_service.record_submission(
            task_id, body.worker_id, body.content, body.attachments
        )
        # 更新任务的反作弊相关字段
        task.delivery_content_hash = content_hash
        task.submission_count += 1
        task.last_submitted_at = task.submitted_at
        # 反作弊字段写入完成后更新更新时间，便于审计/排查
        task.updated_at = datetime.now()

    return {"message": "Work submitted", "task_id": task_id}


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    body: TaskCompleteBody,
    background_tasks: BackgroundTasks,
):
    """AI 雇主验收。验收通过且配置了 callback_url 时，异步 POST `task.completed` 事件。"""
    task = task_service.get_task(task_id)
    if not task or task.ai_employer_id != body.ai_employer_id:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.REVIEW:
        raise HTTPException(
            status_code=400,
            detail="Task is not awaiting review",
        )
    task_service.complete_task(task_id, body.approved)
    task = task_service.get_task(task_id)
    if body.approved and task and task.callback_url:
        background_tasks.add_task(notify_task_completed_by_id, task_id)
    return {
        "message": "Task review done",
        "approved": body.approved,
        "task_id": task_id,
        "delivery_content": task.delivery_content if task else None,
        "delivery_attachments": task.delivery_attachments if task else [],
    }


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, body: TaskCancelBody):
    """取消任务。可由AI雇主或平台操作，已完成的任务不可取消。"""
    if not task_service.cancel_task(task_id, body.operator_id, body.reason):
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel: task not found, already completed/cancelled, or no permission",
        )
    return {"message": "Task cancelled", "task_id": task_id, "reason": body.reason}


@router.post("/{task_id}/manual-review/start")
async def start_manual_review(task_id: str, reviewer_id: str):
    """将任务从REVIEW状态转入人工复核（兜底流程触发）。"""
    if not task_service.start_manual_review(task_id, reviewer_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot start manual review: task not found or not in review status",
        )
    return {"message": "Manual review started", "task_id": task_id, "reviewer_id": reviewer_id}


@router.post("/{task_id}/manual-review")
async def manual_review_task(task_id: str, body: TaskManualReviewBody, background_tasks: BackgroundTasks):
    """人工复核任务。"""
    if not task_service.manual_review_task(
        task_id,
        body.reviewer_id,
        body.approved,
        body.reason,
        body.override_ai_decision
    ):
        raise HTTPException(
            status_code=400,
            detail="Manual review failed: task not found or not in manual review status",
        )
    task = task_service.get_task(task_id)
    if body.approved and task and task.callback_url:
        background_tasks.add_task(notify_task_completed_by_id, task_id)
    return {
        "message": "Manual review completed",
        "approved": body.approved,
        "task_id": task_id,
        "reason": body.reason,
        "delivery_content": task.delivery_content if task else None,
        "delivery_attachments": task.delivery_attachments if task else [],
    }


@router.post("/{task_id}/appeal")
async def appeal_task(task_id: str, body: TaskAppealBody):
    """对已完成的任务提出申诉，进入争议仲裁状态（仅可申诉一次）。"""
    if not task_service.appeal_task(task_id, body.appealer_id, body.appeal_reason, body.evidence):
        raise HTTPException(
            status_code=400,
            detail="Appeal failed: task not found, not completed, or already appealed",
        )
    return {"message": "Appeal submitted", "task_id": task_id, "appeal_reason": body.appeal_reason}


@router.post("/{task_id}/resolve-dispute")
async def resolve_dispute(task_id: str, reviewer_id: str, approved: bool, reason: str, background_tasks: BackgroundTasks):
    """平台仲裁争议，为最终结果。"""
    if not task_service.resolve_dispute(task_id, reviewer_id, approved, reason):
        raise HTTPException(
            status_code=400,
            detail="Cannot resolve dispute: task not found or not in dispute status",
        )
    task = task_service.get_task(task_id)
    if approved and task and task.callback_url:
        background_tasks.add_task(notify_task_completed_by_id, task_id)
    return {
        "message": "Dispute resolved",
        "approved": approved,
        "task_id": task_id,
        "reason": reason,
    }


@router.get("/workers/{worker_id}/risk-score")
async def get_worker_risk_score(worker_id: str):
    """获取工人的风险分数（0-1，越高风险越大）。"""
    risk_score = anti_cheat_service.get_worker_risk_score(worker_id)
    return {
        "worker_id": worker_id,
        "risk_score": risk_score,
        "risk_level": "low" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "high"
    }


@router.post("/{task_id}/mark-cheating")
async def mark_task_cheating(task_id: str, reviewer_id: str, reason: str):
    """标记任务为作弊（平台管理员操作）。"""
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    anti_cheat_service.mark_cheating(task, reason)
    # 记录管理员/复核人，便于后续审计与排查
    task.reviewer_id = reviewer_id
    return {
        "message": "Task marked as cheating",
        "task_id": task_id,
        "reason": reason
    }
