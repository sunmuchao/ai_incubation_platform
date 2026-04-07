"""
事件写入优化服务 - P0 数据持久化增强

功能:
1. 批量写入优化
2. 异步写入队列
3. 写入失败重试
4. 写入性能监控
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
from collections import deque
import threading
import time
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from .postgresql_models import EventModel, EventTypeEnum, DeviceTypeEnum
from .postgresql_config import db_manager

logger = logging.getLogger(__name__)


class EventWriteRequest:
    """事件写入请求"""
    def __init__(
        self,
        event_id: str,
        event_type: str,
        event_name: str,
        timestamp: datetime,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        session_id: str = None,
        anonymous_id: Optional[str] = None,
        page_url: str = None,
        page_title: Optional[str] = None,
        referrer: Optional[str] = None,
        device_type: Optional[str] = None,
        os: Optional[str] = None,
        os_version: Optional[str] = None,
        browser: Optional[str] = None,
        browser_version: Optional[str] = None,
        country: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        ip_address: Optional[str] = None,
        properties: Optional[Dict] = None,
        value: Optional[float] = None,
        currency: Optional[str] = None,
    ):
        self.event_id = event_id
        self.event_type = event_type
        self.event_name = event_name
        self.timestamp = timestamp
        self.user_id = user_id
        self.device_id = device_id
        self.session_id = session_id
        self.anonymous_id = anonymous_id
        self.page_url = page_url
        self.page_title = page_title
        self.referrer = referrer
        self.device_type = device_type
        self.os = os
        self.os_version = os_version
        self.browser = browser
        self.browser_version = browser_version
        self.country = country
        self.region = region
        self.city = city
        self.ip_address = ip_address
        self.properties = properties
        self.value = value
        self.currency = currency
        self.created_at = datetime.utcnow()


class EventWriterStats:
    """写入统计"""
    def __init__(self):
        self.total_received = 0
        self.total_written = 0
        self.total_failed = 0
        self.total_retried = 0
        self.last_write_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.avg_batch_size = 0.0
        self.avg_write_latency_ms = 0.0
        self._latency_samples = deque(maxlen=100)
        self._batch_samples = deque(maxlen=100)

    def record_write(self, batch_size: int, latency_ms: float):
        """记录写入成功"""
        self.total_written += batch_size
        self.last_write_time = datetime.utcnow()
        self._latency_samples.append(latency_ms)
        self._batch_samples.append(batch_size)
        self.avg_write_latency_ms = sum(self._latency_samples) / len(self._latency_samples)
        self.avg_batch_size = sum(self._batch_samples) / len(self._batch_samples)

    def record_failure(self):
        """记录写入失败"""
        self.total_failed += 1

    def record_retry(self):
        """记录重试"""
        self.total_retried += 1

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "total_received": self.total_received,
            "total_written": self.total_written,
            "total_failed": self.total_failed,
            "total_retried": self.total_retried,
            "last_write_time": self.last_write_time.isoformat() if self.last_write_time else None,
            "last_error": self.last_error,
            "avg_batch_size": round(self.avg_batch_size, 2),
            "avg_write_latency_ms": round(self.avg_write_latency_ms, 2),
        }


class EventWriter:
    """
    事件写入器

    功能:
    - 批量写入优化 (减少数据库往返)
    - 异步写入队列 (非阻塞)
    - 失败重试机制
    - 写入性能监控
    """

    def __init__(
        self,
        batch_size: int = 100,
        flush_interval_seconds: float = 5.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        queue_max_size: int = 10000,
        use_async: bool = True,
    ):
        """
        初始化事件写入器

        Args:
            batch_size: 批量写入大小
            flush_interval_seconds: 强制刷新间隔 (秒)
            max_retries: 最大重试次数
            retry_delay_seconds: 重试延迟 (秒)
            queue_max_size: 队列最大大小
            use_async: 是否使用异步写入
        """
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.use_async = use_async

        # 写入队列
        self._queue: deque = deque(maxlen=queue_max_size)
        self._queue_lock = threading.Lock()

        # 统计
        self.stats = EventWriteStats()

        # 异步写入线程
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_flush_time = time.time()

        # 启动异步写入线程
        if use_async:
            self._start_worker()
            logger.info(f"EventWriter started with batch_size={batch_size}, flush_interval={flush_interval_seconds}s")

    def _start_worker(self):
        """启动后台工作线程"""
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self):
        """后台工作循环"""
        while not self._stop_event.is_set():
            try:
                # 定期检查是否需要刷新
                current_time = time.time()
                if current_time - self._last_flush_time >= self.flush_interval_seconds:
                    self._flush_batch()
                    self._last_flush_time = current_time

                # 短暂休眠
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                self.stats.record_failure()

    def write(self, event: EventWriteRequest) -> bool:
        """
        写入单个事件

        Args:
            event: 事件写入请求

        Returns:
            是否成功 (异步模式下总是返回 True)
        """
        self.stats.total_received += 1

        with self._queue_lock:
            self._queue.append(event)

        # 如果队列达到批量大小，立即刷新
        if len(self._queue) >= self.batch_size:
            if self.use_async:
                # 异步模式下，工作线程会处理
                pass
            else:
                self._flush_batch()

        return True

    def write_batch(self, events: List[EventWriteRequest]) -> Dict[str, int]:
        """
        批量写入事件

        Args:
            events: 事件列表

        Returns:
            写入结果统计
        """
        total = len(events)
        self.stats.total_received += total

        with self._queue_lock:
            for event in events:
                self._queue.append(event)

        # 立即刷新
        if not self.use_async:
            self._flush_batch()

        return {"total": total, "queued": total}

    def _flush_batch(self):
        """刷新队列中的事件到数据库"""
        # 获取一批事件
        batch = []
        with self._queue_lock:
            while len(batch) < self.batch_size and self._queue:
                batch.append(self._queue.popleft())

        if not batch:
            return

        # 写入数据库
        start_time = time.time()
        success = False

        for retry in range(self.max_retries):
            try:
                self._write_to_db(batch)
                latency_ms = (time.time() - start_time) * 1000
                self.stats.record_write(len(batch), latency_ms)
                success = True
                break
            except OperationalError as e:
                logger.warning(f"Database operational error (retry {retry + 1}/{self.max_retries}): {e}")
                self.stats.record_retry()
                time.sleep(self.retry_delay_seconds * (retry + 1))
            except SQLAlchemyError as e:
                logger.error(f"Database error: {e}")
                self.stats.last_error = str(e)
                self.stats.record_failure()
                # 对于非 OperationalError，不重试
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                self.stats.last_error = str(e)
                self.stats.record_failure()
                break

        if not success:
            # 将失败的事件重新放回队列 (如果队列未满)
            with self._queue_lock:
                for event in reversed(batch):
                    if len(self._queue) < self._queue.maxlen:
                        self._queue.appendleft(event)

    def _write_to_db(self, batch: List[EventWriteRequest]):
        """
        将批量事件写入数据库

        使用 bulk_insert_mappings 提高性能
        """
        with db_manager.session_scope() as session:
            # 转换为字典列表
            mappings = []
            for event in batch:
                mapping = {
                    "event_id": event.event_id,
                    "event_type": EventTypeEnum(event.event_type) if event.event_type else EventTypeEnum.CUSTOM,
                    "event_name": event.event_name,
                    "timestamp": event.timestamp,
                    "user_id": event.user_id,
                    "device_id": event.device_id,
                    "session_id": event.session_id,
                    "anonymous_id": event.anonymous_id,
                    "page_url": event.page_url,
                    "page_title": event.page_title,
                    "referrer": event.referrer,
                    "device_type": DeviceTypeEnum(event.device_type) if event.device_type else None,
                    "os": event.os,
                    "os_version": event.os_version,
                    "browser": event.browser,
                    "browser_version": event.browser_version,
                    "country": event.country,
                    "region": event.region,
                    "city": event.city,
                    "ip_address": event.ip_address,
                    "properties": event.properties,
                    "value": event.value,
                    "currency": event.currency,
                    "created_at": event.created_at,
                    "processed": False,
                }
                mappings.append(mapping)

            # 批量插入
            session.bulk_insert_mappings(EventModel, mappings)
            session.commit()

    def flush(self):
        """强制刷新所有待写入事件"""
        self._flush_batch()

    def stop(self):
        """停止写入器"""
        logger.info("Stopping EventWriter...")
        self._stop_event.set()

        # 刷新剩余事件
        self.flush()

        # 等待工作线程结束
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)

        logger.info("EventWriter stopped")

    def get_stats(self) -> Dict[str, Any]:
        """获取写入统计"""
        return {
            "queue_size": len(self._queue),
            "stats": self.stats.to_dict(),
            "config": {
                "batch_size": self.batch_size,
                "flush_interval_seconds": self.flush_interval_seconds,
                "max_retries": self.max_retries,
                "use_async": self.use_async,
            }
        }


# ==================== 全局实例 ====================

# 全局事件写入器实例
event_writer: Optional[EventWriter] = None


def get_event_writer() -> Optional[EventWriter]:
    """获取事件写入器实例"""
    return event_writer


def init_event_writer(**kwargs) -> EventWriter:
    """
    初始化全局事件写入器

    Args:
        **kwargs: 配置参数

    Returns:
        事件写入器实例
    """
    global event_writer
    event_writer = EventWriter(**kwargs)
    return event_writer


def shutdown_event_writer():
    """关闭全局事件写入器"""
    global event_writer
    if event_writer:
        event_writer.stop()
        event_writer = None
