"""
限流模块
实现请求限流和并发控制，防止系统过载
"""
from typing import Optional
import asyncio
from collections import deque
from datetime import datetime, timedelta
from config.settings import settings
from utils.logger import logger


class RateLimiter:
    """限流器"""

    def __init__(self):
        self._enabled = settings.rate_limit.enabled
        self._max_requests_per_minute = settings.rate_limit.max_requests_per_minute
        self._max_concurrent = settings.rate_limit.max_concurrent_queries
        self._burst_limit = settings.rate_limit.burst_limit

        # 请求时间窗口
        self._request_times: deque = deque()
        # 当前并发数
        self._current_concurrent = 0
        # 锁
        self._lock = asyncio.Lock()
        # 并发信号量
        self._semaphore = asyncio.Semaphore(self._max_concurrent)

    async def acquire(self) -> bool:
        """
        获取限流许可
        返回 True 表示允许请求，False 表示被限流
        """
        if not self._enabled:
            return True

        async with self._lock:
            now = datetime.utcnow()
            one_minute_ago = now - timedelta(minutes=1)

            # 移除窗口外的请求记录
            while self._request_times and self._request_times[0] < one_minute_ago:
                self._request_times.popleft()

            # 检查是否超过速率限制
            if len(self._request_times) >= self._max_requests_per_minute:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "requests_in_window": len(self._request_times),
                        "limit": self._max_requests_per_minute
                    }
                )
                return False

            # 检查突发限制
            if len(self._request_times) >= self._burst_limit:
                logger.warning(
                    "Burst limit exceeded",
                    extra={
                        "requests_in_window": len(self._request_times),
                        "burst_limit": self._burst_limit
                    }
                )
                return False

            # 添加当前请求时间
            self._request_times.append(now)

        # 获取并发许可
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=5.0)
            async with self._lock:
                self._current_concurrent += 1
            return True
        except asyncio.TimeoutError:
            logger.warning("Concurrent query limit exceeded")
            return False

    async def release(self) -> None:
        """释放限流许可"""
        if not self._enabled:
            return

        async with self._lock:
            self._current_concurrent -= 1
        self._semaphore.release()

    @property
    def current_concurrent(self) -> int:
        """获取当前并发数"""
        return self._current_concurrent

    @property
    def requests_in_window(self) -> int:
        """获取当前窗口内的请求数"""
        return len(self._request_times)


# 全局限流器实例
rate_limiter = RateLimiter()
