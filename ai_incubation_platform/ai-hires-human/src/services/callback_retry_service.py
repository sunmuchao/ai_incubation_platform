"""
回调重试服务。

提供带指数退避的回调重试机制和死信队列功能。
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
import os

import httpx

from models.task import Task, TaskStatus
from services.task_service import task_service

logger = logging.getLogger(__name__)


class CallbackStatus(str, Enum):
    """回调状态。"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"  # 死信


@dataclass
class CallbackRecord:
    """回调记录。"""
    task_id: str
    callback_url: str
    payload: Dict[str, Any]
    status: CallbackStatus = CallbackStatus.PENDING
    retry_count: int = 0
    max_retries: int = 5
    next_retry_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_error: Optional[str] = None
    succeeded_at: Optional[datetime] = None

    def should_retry(self) -> bool:
        """判断是否应该重试。"""
        if self.status in (CallbackStatus.SUCCESS, CallbackStatus.DEAD_LETTER):
            return False
        if self.retry_count >= self.max_retries:
            return False
        if self.next_retry_at and datetime.now() < self.next_retry_at:
            return False
        return True

    def get_retry_delay(self) -> float:
        """
        计算下次重试的延迟时间（指数退避）。

        使用公式：delay = base_delay * (2 ^ retry_count) + jitter
        base_delay = 5 秒
        jitter = 随机 0-2 秒，避免多个请求同时到达
        """
        import random
        base_delay = 5.0  # 基础延迟 5 秒
        delay = base_delay * (2 ** self.retry_count)
        jitter = random.uniform(0, 2.0)  # 添加 0-2 秒随机抖动
        return min(delay + jitter, 300.0)  # 最大延迟不超过 5 分钟


class CallbackRetryService:
    """
    回调重试服务。

    功能：
    1. 带指数退避的自动重试
    2. 并发安全（使用 asyncio.Lock）
    3. 死信队列管理
    4. 手动重发支持
    """

    def __init__(self) -> None:
        # 回调记录存储：task_id -> CallbackRecord
        self._records: Dict[str, CallbackRecord] = {}
        # 死信队列：task_id -> CallbackRecord
        self._dead_letter_queue: Dict[str, CallbackRecord] = {}
        # 并发控制锁
        self._lock = asyncio.Lock()
        # HTTP 客户端（单例，复用连接）
        self._client: Optional[httpx.AsyncClient] = None
        # 回调密钥（从环境变量读取）
        self._callback_secret = os.getenv("AI_HIRES_HUMAN_CALLBACK_SECRET", "").strip()
        # 重试任务调度器
        self._retry_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """启动重试调度器。"""
        if self._running:
            return
        self._running = True
        self._retry_task = asyncio.create_task(self._retry_scheduler())
        logger.info("Callback retry scheduler started")

    async def stop(self) -> None:
        """停止重试调度器。"""
        self._running = False
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()
        logger.info("Callback retry scheduler stopped")

    async def _retry_scheduler(self) -> None:
        """定期扫描并处理待重试的回调。"""
        while self._running:
            try:
                await self._process_pending_retries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Retry scheduler error: %s", e)
            await asyncio.sleep(1.0)  # 每秒检查一次

    async def _process_pending_retries(self) -> None:
        """处理所有待重试的回调。"""
        async with self._lock:
            now = datetime.now()
            pending = [
                record for record in self._records.values()
                if record.should_retry() and
                   (record.next_retry_at is None or record.next_retry_at <= now)
            ]

        for record in pending:
            await self._execute_callback(record)

    async def _execute_callback(self, record: CallbackRecord) -> None:
        """执行单次回调调用。"""
        async with self._lock:
            if record.status not in (CallbackStatus.PENDING, CallbackStatus.IN_PROGRESS):
                return
            record.status = CallbackStatus.IN_PROGRESS
            record.retry_count += 1
            record.updated_at = datetime.now()
            callback_url = record.callback_url
            payload = record.payload

        headers = {}
        if self._callback_secret:
            headers["X-Callback-Secret"] = self._callback_secret

        try:
            client = await self._get_client()
            async with client:
                resp = await client.post(callback_url, json=payload, headers=headers, timeout=30.0)
                resp.raise_for_status()

            # 回调成功
            async with self._lock:
                record.status = CallbackStatus.SUCCESS
                record.succeeded_at = datetime.now()
                record.updated_at = datetime.now()

            logger.info(
                "callback succeeded: task_id=%s url=%s retry_count=%d",
                record.task_id, callback_url, record.retry_count - 1
            )

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)}"

            async with self._lock:
                record.last_error = error_msg
                record.updated_at = datetime.now()

                # 判断是否还有重试机会
                if record.retry_count >= record.max_retries:
                    record.status = CallbackStatus.DEAD_LETTER
                    self._dead_letter_queue[record.task_id] = record
                    logger.warning(
                        "callback moved to dead letter queue: task_id=%s url=%s error=%s",
                        record.task_id, callback_url, error_msg
                    )
                else:
                    # 计算下次重试时间
                    delay = record.get_retry_delay()
                    record.next_retry_at = datetime.now() + timedelta(seconds=delay)
                    record.status = CallbackStatus.PENDING
                    logger.warning(
                        "callback failed, will retry in %.1f seconds: task_id=%s url=%s error=%s",
                        delay, record.task_id, callback_url, error_msg
                    )

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端单例。"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def enqueue_callback(
        self,
        task_id: str,
        callback_url: str,
        payload: Dict[str, Any],
    ) -> CallbackRecord:
        """
        将回调加入队列。

        Args:
            task_id: 任务 ID
            callback_url: 回调 URL
            payload: 回调负载

        Returns:
            回调记录
        """
        async with self._lock:
            # 检查是否已存在（幂等性）
            existing = self._records.get(task_id)
            if existing and existing.status == CallbackStatus.SUCCESS:
                logger.info("callback already succeeded, skipping: task_id=%s", task_id)
                return existing

            record = CallbackRecord(
                task_id=task_id,
                callback_url=callback_url,
                payload=payload,
            )
            self._records[task_id] = record

        # 立即尝试发送一次
        await self._execute_callback(record)
        return record

    async def resend_callback(self, task_id: str) -> Optional[CallbackRecord]:
        """
        手动重发回调（用于死信队列恢复）。

        Args:
            task_id: 任务 ID

        Returns:
            回调记录，如不存在则返回 None
        """
        async with self._lock:
            record = self._records.get(task_id)
            if not record:
                return None

            # 重置状态
            record.status = CallbackStatus.PENDING
            record.retry_count = 0
            record.next_retry_at = None
            record.last_error = None
            record.updated_at = datetime.now()

            # 从死信队列移除
            if task_id in self._dead_letter_queue:
                del self._dead_letter_queue[task_id]

        logger.info("callback manual resend triggered: task_id=%s", task_id)
        await self._execute_callback(record)
        return record

    def get_callback_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取回调状态。

        Args:
            task_id: 任务 ID

        Returns:
            回调状态字典，如不存在则返回 None
        """
        record = self._records.get(task_id)
        if not record:
            return None

        return {
            "task_id": record.task_id,
            "callback_url": record.callback_url,
            "status": record.status.value,
            "retry_count": record.retry_count,
            "max_retries": record.max_retries,
            "last_error": record.last_error,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "succeeded_at": record.succeeded_at.isoformat() if record.succeeded_at else None,
            "next_retry_at": record.next_retry_at.isoformat() if record.next_retry_at else None,
        }

    def get_dead_letter_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取死信队列列表。

        Args:
            limit: 返回数量限制

        Returns:
            死信队列记录列表
        """
        records = list(self._dead_letter_queue.values())
        records.sort(key=lambda r: r.updated_at, reverse=True)

        return [
            {
                "task_id": r.task_id,
                "callback_url": r.callback_url,
                "retry_count": r.retry_count,
                "last_error": r.last_error,
                "failed_at": r.updated_at.isoformat(),
            }
            for r in records[:limit]
        ]

    def reset_state(self) -> None:
        """重置状态（用于测试）。"""
        self._records.clear()
        self._dead_letter_queue.clear()


# 全局回调重试服务实例
callback_retry_service = CallbackRetryService()
