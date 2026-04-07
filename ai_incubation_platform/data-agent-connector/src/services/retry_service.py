"""
错误自动重试服务

实现可配置的重试机制，减少人工干预
支持指数退避、死信队列、重试策略配置
"""
import asyncio
import time
import random
from typing import Any, Callable, Dict, List, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import sqlite3
from datetime import datetime, timedelta

from utils.logger import logger


class RetryStrategy(Enum):
    """重试策略类型"""
    FIXED = "fixed"  # 固定间隔
    LINEAR = "linear"  # 线性退避
    EXPONENTIAL = "exponential"  # 指数退避
    EXPONENTIAL_JITTER = "exponential_jitter"  # 指数退避 + 抖动


class ErrorType(Enum):
    """错误类型分类"""
    TRANSIENT = "transient"  # 临时错误，可重试
    PERMANENT = "permanent"  # 永久错误，不可重试
    UNKNOWN = "unknown"  # 未知错误


# 可重试的异常类型
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    sqlite3.OperationalError,
)

# 不可重试的异常类型
NON_RETRYABLE_EXCEPTIONS = (
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)

# 错误关键字匹配（用于判断是否可重试）
RETRYABLE_ERROR_KEYWORDS = [
    "connection",
    "timeout",
    "temporarily",
    "retry",
    "lock",
    "busy",
    "deadlock",
    "unavailable",
    "rate limit",
]

NON_RETRYABLE_ERROR_KEYWORDS = [
    "invalid",
    "not found",
    "permission",
    "unauthorized",
    "forbidden",
    "syntax error",
    "constraint",
]


@dataclass
class RetryConfig:
    """重试配置"""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    max_retries: int = 3
    base_delay: float = 1.0  # 基础延迟（秒）
    max_delay: float = 60.0  # 最大延迟（秒）
    jitter: float = 0.1  # 抖动系数（0-1）

    # 错误分类配置
    retryable_exceptions: tuple = RETRYABLE_EXCEPTIONS
    non_retryable_exceptions: tuple = NON_RETRYABLE_EXCEPTIONS

    # 回调函数
    on_retry: Optional[Callable] = None  # 重试时回调
    on_failure: Optional[Callable] = None  # 失败时回调


@dataclass
class RetryContext:
    """重试上下文"""
    func_name: str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    attempt: int = 0
    last_error: Optional[Exception] = None
    start_time: float = field(default_factory=time.time)
    total_delay: float = 0.0


@dataclass
class DeadLetterEntry:
    """死信队列条目"""
    func_name: str
    args: tuple
    kwargs: dict
    error_type: str
    error_message: str
    retry_count: int
    total_time: float
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "func_name": self.func_name,
            "args": str(self.args),
            "kwargs": str(self.kwargs),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "total_time": self.total_time,
            "created_at": self.created_at.isoformat(),
        }


class DeadLetterQueue:
    """死信队列"""

    def __init__(self, db_path: str = "./data/dead_letter.db", max_size: int = 1000):
        self.db_path = db_path
        self.max_size = max_size
        self._entries: List[DeadLetterEntry] = []
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dead_letter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                func_name TEXT NOT NULL,
                args TEXT,
                kwargs TEXT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                retry_count INTEGER NOT NULL,
                total_time REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dead_letter_created_at
            ON dead_letter(created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dead_letter_error_type
            ON dead_letter(error_type)
        """)
        conn.commit()
        conn.close()

    def add(self, entry: DeadLetterEntry) -> bool:
        """添加条目到死信队列"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO dead_letter
                (func_name, args, kwargs, error_type, error_message, retry_count, total_time, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.func_name,
                str(entry.args),
                str(entry.kwargs),
                entry.error_type,
                entry.error_message,
                entry.retry_count,
                entry.total_time,
                entry.created_at.isoformat()
            ))
            conn.commit()
            conn.close()

            self._entries.append(entry)

            # 清理超出大小的条目
            if len(self._entries) > self.max_size:
                self._entries = self._entries[-self.max_size:]

            logger.info(f"Added entry to dead letter queue: {entry.func_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add to dead letter queue: {e}")
            return False

    def get_entries(self, limit: int = 100,
                    error_type: Optional[str] = None,
                    since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """获取死信队列条目"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM dead_letter WHERE 1=1"
            params = []

            if error_type:
                query += " AND error_type = ?"
                params.append(error_type)

            if since:
                query += " AND created_at >= ?"
                params.append(since.isoformat())

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "id": row[0],
                    "func_name": row[1],
                    "args": row[2],
                    "kwargs": row[3],
                    "error_type": row[4],
                    "error_message": row[5],
                    "retry_count": row[6],
                    "total_time": row[7],
                    "created_at": row[8],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get dead letter entries: {e}")
            return []

    def delete(self, entry_id: int) -> bool:
        """删除死信队列条目"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dead_letter WHERE id = ?", (entry_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to delete dead letter entry: {e}")
            return False

    def clear(self, older_than: Optional[datetime] = None) -> int:
        """清理死信队列"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if older_than:
                cursor.execute(
                    "DELETE FROM dead_letter WHERE created_at < ?",
                    (older_than.isoformat(),)
                )
            else:
                cursor.execute("DELETE FROM dead_letter")

            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            logger.error(f"Failed to clear dead letter queue: {e}")
            return 0

    def count(self) -> int:
        """获取死信队列条目数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dead_letter")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Failed to count dead letter entries: {e}")
            return 0


class RetryService:
    """重试服务"""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.dead_letter_queue = DeadLetterQueue()
        self._stats = defaultdict(lambda: {"success": 0, "failure": 0, "retries": 0})

    def classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型"""
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()

        # 检查是否是不可重试的错误
        if isinstance(error, self.config.non_retryable_exceptions):
            return ErrorType.PERMANENT

        # 检查是否是非重试关键字
        for keyword in NON_RETRYABLE_ERROR_KEYWORDS:
            if keyword in error_msg or keyword in error_type:
                return ErrorType.PERMANENT

        # 检查是否是可重试的错误
        if isinstance(error, self.config.retryable_exceptions):
            return ErrorType.TRANSIENT

        # 检查是否是重试关键字
        for keyword in RETRYABLE_ERROR_KEYWORDS:
            if keyword in error_msg or keyword in error_type:
                return ErrorType.TRANSIENT

        return ErrorType.UNKNOWN

    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * attempt
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            delay = self.config.base_delay * (2 ** (attempt - 1))
            # 添加抖动避免惊群效应
            jitter_range = delay * self.config.jitter
            delay += random.uniform(-jitter_range, jitter_range)
        else:
            delay = self.config.base_delay

        # 限制最大延迟
        return min(delay, self.config.max_delay)

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Any:
        """
        执行函数并自动重试

        Args:
            func: 要执行的异步函数
            *args: 函数参数
            config: 可选的重试配置覆盖
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 重试耗尽后仍然失败的异常
        """
        cfg = config or self.config
        ctx = RetryContext(
            func_name=func.__name__,
            args=args,
            kwargs=kwargs
        )

        last_exception = None

        for attempt in range(cfg.max_retries + 1):
            ctx.attempt = attempt + 1

            try:
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # 成功，更新统计
                self._stats[func.__name__]["success"] += 1

                # 如果是重试后成功，记录日志
                if attempt > 0:
                    logger.info(
                        f"Function {func.__name__} succeeded after {attempt} retries",
                        extra={
                            "func_name": func.__name__,
                            "attempts": attempt + 1,
                            "total_time": time.time() - ctx.start_time
                        }
                    )

                return result

            except Exception as e:
                last_exception = e
                ctx.last_error = e

                # 分类错误
                error_type = self.classify_error(e)

                # 永久错误，立即失败
                if error_type == ErrorType.PERMANENT:
                    logger.error(
                        f"Function {func.__name__} failed with permanent error",
                        extra={
                            "func_name": func.__name__,
                            "error_type": error_type.value,
                            "error": str(e)
                        }
                    )
                    self._stats[func.__name__]["failure"] += 1

                    if cfg.on_failure:
                        await self._call_callback(cfg.on_failure, ctx, e)

                    raise

                # 重试耗尽，加入死信队列
                if attempt >= cfg.max_retries:
                    total_time = time.time() - ctx.start_time

                    logger.error(
                        f"Function {func.__name__} failed after {cfg.max_retries + 1} attempts",
                        extra={
                            "func_name": func.__name__,
                            "attempts": cfg.max_retries + 1,
                            "error": str(e),
                            "total_time": total_time
                        }
                    )

                    # 加入死信队列
                    entry = DeadLetterEntry(
                        func_name=func.__name__,
                        args=args,
                        kwargs=kwargs,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        retry_count=cfg.max_retries,
                        total_time=total_time
                    )
                    self.dead_letter_queue.add(entry)

                    self._stats[func.__name__]["failure"] += 1

                    if cfg.on_failure:
                        await self._call_callback(cfg.on_failure, ctx, e)

                    raise

                # 计算延迟并重试
                delay = self.calculate_delay(attempt + 1)
                ctx.total_delay += delay

                logger.warning(
                    f"Function {func.__name__} failed (attempt {attempt + 1}/{cfg.max_retries + 1}), "
                    f"retrying in {delay:.2f}s",
                    extra={
                        "func_name": func.__name__,
                        "attempt": attempt + 1,
                        "max_attempts": cfg.max_retries + 1,
                        "delay": delay,
                        "error": str(e)
                    }
                )

                self._stats[func.__name__]["retries"] += 1

                if cfg.on_retry:
                    await self._call_callback(cfg.on_retry, ctx, e)

                await asyncio.sleep(delay)

        # 不应该到达这里
        raise last_exception

    async def _call_callback(self, callback: Callable, ctx: RetryContext, error: Exception):
        """调用回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(ctx, error)
            else:
                callback(ctx, error)
        except Exception as e:
            logger.error(f"Callback failed: {e}")

    def get_stats(self, func_name: Optional[str] = None) -> Dict[str, Any]:
        """获取重试统计"""
        if func_name:
            return dict(self._stats.get(func_name, {"success": 0, "failure": 0, "retries": 0}))
        return {k: dict(v) for k, v in self._stats.items()}

    def reset_stats(self, func_name: Optional[str] = None):
        """重置统计"""
        if func_name:
            self._stats[func_name] = {"success": 0, "failure": 0, "retries": 0}
        else:
            self._stats.clear()


# 全局重试服务实例
retry_service = RetryService(
    RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        jitter=0.1
    )
)


# 装饰器模式
def with_retry(config: Optional[RetryConfig] = None):
    """
    重试装饰器

    使用示例:
        @with_retry()
        async def my_function():
            pass

        @with_retry(RetryConfig(max_retries=5))
        async def another_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            return await retry_service.execute_with_retry(
                func, *args, config=config, **kwargs
            )
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
