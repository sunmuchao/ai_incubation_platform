"""
Internal callback sink for local testing.

This endpoint is only meant to make `callback_url` behavior testable in the
end-to-end demo without relying on external network access.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from services.anti_cheat_service import anti_cheat_service
from services.callback_service import (
    notify_task_completed_by_id,
    reset_callback_delivery_state,
    resend_callback,
    get_callback_status,
    get_dead_letter_queue,
)
from services.callback_retry_service import callback_retry_service
from services.task_service import task_service

router = APIRouter(prefix="/api/internal/callback-sink", tags=["internal-callback-sink"])

# In-memory store: single-process demo/test usage.
_CALLBACK_EVENTS: List[Dict[str, Any]] = []
_CALLBACK_EVENTS_BY_TASK_ID: Dict[str, Dict[str, Any]] = {}

# Flaky endpoint: fail exactly once per task_id, then succeed.
_FLAKY_FAILED_ONCE: Dict[str, bool] = {}
_FLAKY_LOCK = asyncio.Lock()


@router.post("/reset")
async def reset_callback_sink() -> Dict[str, Any]:
    _CALLBACK_EVENTS.clear()
    _CALLBACK_EVENTS_BY_TASK_ID.clear()
    _FLAKY_FAILED_ONCE.clear()
    # Also reset callback delivery idempotency state so repeated end-to-end
    # test runs remain deterministic.
    reset_callback_delivery_state()
    anti_cheat_service.reset_state()
    task_service.reset_state()
    return {"ok": True}


@router.post("/task-completed")
async def task_completed_sink(payload: Dict[str, Any]) -> Dict[str, Any]:
    task_id = payload.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="Invalid payload: missing task_id")

    _CALLBACK_EVENTS.append(payload)
    _CALLBACK_EVENTS_BY_TASK_ID[str(task_id)] = payload
    return {"ok": True}


@router.post("/task-completed-flaky")
async def task_completed_flaky_sink(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fail once per task_id, then record the event.

    Used to test callback retry correctness under concurrency.
    """
    task_id = payload.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="Invalid payload: missing task_id")

    async with _FLAKY_LOCK:
        if not _FLAKY_FAILED_ONCE.get(str(task_id), False):
            _FLAKY_FAILED_ONCE[str(task_id)] = True
            raise HTTPException(status_code=500, detail="Simulated flaky failure")

    _CALLBACK_EVENTS.append(payload)
    _CALLBACK_EVENTS_BY_TASK_ID[str(task_id)] = payload
    return {"ok": True}


@router.get("/events/{task_id}")
async def get_event(task_id: str) -> Dict[str, Any]:
    payload = _CALLBACK_EVENTS_BY_TASK_ID.get(task_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Event not found")
    return payload


@router.get("/events")
async def list_events() -> List[Dict[str, Any]]:
    return _CALLBACK_EVENTS


@router.post("/force-complete/{task_id}")
async def force_complete_task(task_id: str) -> Dict[str, Any]:
    """Mark task as COMPLETED without triggering any background callback.

    This is intended for deterministic testing of callback behavior.
    """
    ok = task_service.complete_task(task_id, approved=True)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot force complete")
    return {"ok": True}


@router.post("/resend/{task_id}")
async def resend_task_completed(task_id: str) -> Dict[str, Any]:
    """Manually trigger `notify_task_completed_by_id`."""
    await notify_task_completed_by_id(task_id)
    return {"ok": True}


@router.get("/status/{task_id}")
async def get_callback_status_endpoint(task_id: str) -> Optional[Dict[str, Any]]:
    """获取回调状态（包含重试次数、错误信息等）。"""
    status = get_callback_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Callback status not found")
    return status


@router.get("/dead-letter-queue")
async def get_dead_letter_queue_endpoint(limit: int = 100) -> List[Dict[str, Any]]:
    """获取死信队列列表（回调失败超过最大重试次数的任务）。"""
    return get_dead_letter_queue(limit)


@router.post("/retry-from-dead-letter/{task_id}")
async def retry_from_dead_letter(task_id: str) -> Dict[str, Any]:
    """从死信队列中恢复并重新尝试回调。"""
    record = await resend_callback(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Callback record not found")
    return {"ok": True, "task_id": task_id}


@router.post("/start-retry-scheduler")
async def start_retry_scheduler() -> Dict[str, Any]:
    """启动回调重试调度器（通常在应用启动时自动启动）。"""
    await callback_retry_service.start()
    return {"ok": True, "message": "Retry scheduler started"}


@router.post("/stop-retry-scheduler")
async def stop_retry_scheduler() -> Dict[str, Any]:
    """停止回调重试调度器。"""
    await callback_retry_service.stop()
    return {"ok": True, "message": "Retry scheduler stopped"}

