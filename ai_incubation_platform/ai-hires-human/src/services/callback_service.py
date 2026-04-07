"""
验收通过后的异步 HTTP 回调 — 供上游 Agent / 网关接收结构化结果。
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import httpx

from models.task import Task, TaskStatus
from services.task_service import task_service
from services.callback_retry_service import callback_retry_service, CallbackRecord

logger = logging.getLogger(__name__)

CALLBACK_SECRET = os.getenv("AI_HIRES_HUMAN_CALLBACK_SECRET", "").strip()

# In-memory delivery state for callback idempotency.
# Keyed by task_id.
_DELIVERY_SUCCEEDED: Dict[str, bool] = {}  # task_id -> succeeded
_DELIVERY_INFLIGHT: Dict[str, asyncio.Future] = {}  # task_id -> completion future
_DELIVERY_LOCK = asyncio.Lock()


def reset_callback_delivery_state() -> None:
    """Reset idempotency state for local tests/demos."""
    _DELIVERY_SUCCEEDED.clear()
    for fut in _DELIVERY_INFLIGHT.values():
        if fut and not fut.done():
            fut.set_result(False)
    _DELIVERY_INFLIGHT.clear()
    # Also reset the retry service
    callback_retry_service.reset_state()


def build_completed_payload(task: Task) -> Dict[str, Any]:
    it = task.interaction_type
    if hasattr(it, "value"):
        it = it.value
    return {
        "event": "task.completed",
        "task_id": task.id,
        "ai_employer_id": task.ai_employer_id,
        "approved": True,
        "interaction_type": it,
        "title": task.title,
        "capability_gap": task.capability_gap,
        "delivery_content": task.delivery_content,
        "delivery_attachments": task.delivery_attachments,
        "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
        "worker_id": task.worker_id,
    }


async def notify_task_completed_by_id(task_id: str) -> None:
    """
    若任务已验收通过且配置了 callback_url，则通过重试服务发送回调。

    使用回调重试服务，提供以下能力：
    1. 并发安全的幂等性保证
    2. 指数退避自动重试（最多 5 次）
    3. 死信队列管理
    """
    task = task_service.get_task(task_id)
    if not task or not task.callback_url:
        return
    if task.status != TaskStatus.COMPLETED:
        return

    # 使用回调重试服务发送
    payload = build_completed_payload(task)
    url = str(task.callback_url).strip()

    try:
        await callback_retry_service.enqueue_callback(
            task_id=task_id,
            callback_url=url,
            payload=payload,
        )
    except Exception as exc:
        logger.error("callback enqueue failed task_id=%s url=%s: %s", task_id, url, exc)


async def resend_callback(task_id: str) -> Optional[CallbackRecord]:
    """
    手动重发回调（用于死信队列恢复）。

    Args:
        task_id: 任务 ID

    Returns:
        回调记录，如不存在则返回 None
    """
    return await callback_retry_service.resend_callback(task_id)


def get_callback_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    获取回调状态。

    Args:
        task_id: 任务 ID

    Returns:
        回调状态字典，如不存在则返回 None
    """
    return callback_retry_service.get_callback_status(task_id)


def get_dead_letter_queue(limit: int = 100) -> list:
    """
    获取死信队列列表。

    Args:
        limit: 返回数量限制

    Returns:
        死信队列记录列表
    """
    return callback_retry_service.get_dead_letter_queue(limit)
