"""
弹性模式实现

包含：
- 重试机制（指数退避）
- 超时控制
- 熔断器模式
- 降级策略
"""
import asyncio
import logging
from typing import Optional, Callable, Any, Dict, List
from datetime import datetime, timedelta
from functools import wraps
import time

logger = logging.getLogger(__name__)


class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        retryable_exceptions: Optional[List[type]] = None
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions or [Exception]

    def get_delay(self, attempt: int) -> float:
        """计算延迟时间（指数退避）"""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


class CircuitBreakerState:
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态（测试恢复）


class CircuitBreaker:
    """
    熔断器实现

    状态转换:
    CLOSED -> OPEN: 失败次数达到阈值
    OPEN -> HALF_OPEN: 恢复超时后
    HALF_OPEN -> CLOSED: 成功调用
    HALF_OPEN -> OPEN: 失败调用
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0

    @property
    def state(self) -> str:
        """获取当前状态"""
        if self._state == CircuitBreakerState.OPEN:
            # 检查是否可以进入半开状态
            if self._last_failure_time:
                elapsed = datetime.now() - self._last_failure_time
                if elapsed.total_seconds() >= self.recovery_timeout:
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(f"熔断器进入半开状态")
        return self._state

    def record_success(self):
        """记录成功调用"""
        self._failure_count = 0
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._close()
        elif self._state == CircuitBreakerState.CLOSED:
            self._failure_count = 0

    def record_failure(self):
        """记录失败调用"""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == CircuitBreakerState.HALF_OPEN:
            self._open()
        elif self._state == CircuitBreakerState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._open()

    def _open(self):
        """打开熔断器"""
        self._state = CircuitBreakerState.OPEN
        logger.warning(f"熔断器打开，失败次数：{self._failure_count}")

    def _close(self):
        """关闭熔断器"""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.info("熔断器关闭")

    def allow_request(self) -> bool:
        """检查是否允许请求"""
        current_state = self.state  # 触发状态检查

        if self._state == CircuitBreakerState.CLOSED:
            return True
        elif self._state == CircuitBreakerState.OPEN:
            return False
        else:  # HALF_OPEN
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取熔断器统计"""
        return {
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "half_open_calls": self._half_open_calls
        }


class TimeoutError(Exception):
    """超时异常"""
    pass


class FallbackError(Exception):
    """降级失败异常"""
    pass


async def with_retry(
    func: Callable,
    config: Optional[RetryConfig] = None,
    context: Optional[Dict[str, Any]] = None
) -> Any:
    """
    带重试执行函数

    Args:
        func: 要执行的异步函数
        config: 重试配置
        context: 日志上下文（用于追踪）

    Returns:
        函数执行结果
    """
    config = config or RetryConfig()
    context = context or {}
    trace_id = context.get("trace_id", "unknown")

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            logger.info(
                f"[重试] trace_id={trace_id}, 尝试 {attempt + 1}/{config.max_attempts}",
                extra={"trace_id": trace_id}
            )
            return await func()
        except tuple(config.retryable_exceptions) as e:
            last_exception = e
            logger.warning(
                f"[重试] trace_id={trace_id}, 尝试 {attempt + 1} 失败：{str(e)}",
                extra={"trace_id": trace_id}
            )

            if attempt < config.max_attempts - 1:
                delay = config.get_delay(attempt)
                logger.info(
                    f"[重试] trace_id={trace_id}, {delay:.2f}秒后重试",
                    extra={"trace_id": trace_id}
                )
                await asyncio.sleep(delay)

    logger.error(
        f"[重试] trace_id={trace_id}, 所有重试失败：{str(last_exception)}",
        extra={"trace_id": trace_id}
    )
    raise last_exception


async def with_timeout(
    func: Callable,
    timeout: float,
    context: Optional[Dict[str, Any]] = None
) -> Any:
    """
    带超时执行函数

    Args:
        func: 要执行的异步函数
        timeout: 超时时间（秒）
        context: 日志上下文

    Returns:
        函数执行结果
    """
    context = context or {}
    trace_id = context.get("trace_id", "unknown")

    try:
        logger.debug(
            f"[超时] trace_id={trace_id}, 设置超时 {timeout}秒",
            extra={"trace_id": trace_id}
        )
        return await asyncio.wait_for(func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(
            f"[超时] trace_id={trace_id}, 执行超时 {timeout}秒",
            extra={"trace_id": trace_id}
        )
        raise TimeoutError(f"执行超时，限制为{timeout}秒")


async def with_circuit_breaker(
    func: Callable,
    breaker: CircuitBreaker,
    fallback: Optional[Callable] = None,
    context: Optional[Dict[str, Any]] = None
) -> Any:
    """
    带熔断器执行函数

    Args:
        func: 要执行的异步函数
        breaker: 熔断器实例
        fallback: 降级函数（可选）
        context: 日志上下文

    Returns:
        函数执行结果
    """
    context = context or {}
    trace_id = context.get("trace_id", "unknown")

    if not breaker.allow_request():
        logger.warning(
            f"[熔断器] trace_id={trace_id}, 熔断器打开，拒绝请求",
            extra={"trace_id": trace_id}
        )

        if fallback:
            logger.info(
                f"[熔断器] trace_id={trace_id}, 执行降级函数",
                extra={"trace_id": trace_id}
            )
            try:
                return await fallback()
            except Exception as e:
                logger.error(
                    f"[熔断器] trace_id={trace_id}, 降级失败：{str(e)}",
                    extra={"trace_id": trace_id}
                )
                raise FallbackError(f"熔断器打开且降级失败：{str(e)}")

        raise FallbackError("熔断器打开，请求被拒绝")

    try:
        result = await func()
        breaker.record_success()
        return result
    except Exception as e:
        breaker.record_failure()
        logger.error(
            f"[熔断器] trace_id={trace_id}, 执行失败：{str(e)}",
            extra={"trace_id": trace_id}
        )

        if fallback:
            logger.info(
                f"[熔断器] trace_id={trace_id}, 执行降级函数",
                extra={"trace_id": trace_id}
            )
            try:
                return await fallback()
            except Exception as fallback_error:
                logger.error(
                    f"[熔断器] trace_id={trace_id}, 降级失败：{str(fallback_error)}",
                    extra={"trace_id": trace_id}
                )

        raise


class ResiliencePolicy:
    """
    弹性策略组合

    将重试、超时、熔断器组合使用
    """

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        timeout: float = 30.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
        fallback: Optional[Callable] = None
    ):
        self.retry_config = retry_config or RetryConfig()
        self.timeout = timeout
        self.circuit_breaker = circuit_breaker
        self.fallback = fallback

    async def execute(
        self,
        func: Callable,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        执行函数（应用所有策略）

        执行顺序：熔断器 -> 重试 -> 超时
        """
        context = context or {}
        trace_id = context.get("trace_id", "unknown")

        logger.info(
            f"[弹性策略] trace_id={trace_id}, 开始执行",
            extra={"trace_id": trace_id}
        )

        start_time = time.time()

        async def execute_with_retry_and_timeout():
            async def inner():
                return await with_timeout(func, self.timeout, context)
            return await with_retry(inner, self.retry_config, context)

        try:
            if self.circuit_breaker:
                result = await with_circuit_breaker(
                    execute_with_retry_and_timeout,
                    self.circuit_breaker,
                    self.fallback,
                    context
                )
            else:
                result = await execute_with_retry_and_timeout()

            elapsed = time.time() - start_time
            logger.info(
                f"[弹性策略] trace_id={trace_id}, 执行成功，耗时 {elapsed:.2f}秒",
                extra={"trace_id": trace_id}
            )
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"[弹性策略] trace_id={trace_id}, 执行失败，耗时 {elapsed:.2f}秒：{str(e)}",
                extra={"trace_id": trace_id}
            )
            raise

    def get_stats(self) -> Dict[str, Any]:
        """获取策略统计"""
        stats = {
            "timeout": self.timeout,
            "retry_config": {
                "max_attempts": self.retry_config.max_attempts,
                "initial_delay": self.retry_config.initial_delay,
                "max_delay": self.retry_config.max_delay
            }
        }
        if self.circuit_breaker:
            stats["circuit_breaker"] = self.circuit_breaker.get_stats()
        return stats


class FallbackStrategy:
    """降级策略"""

    @staticmethod
    def return_default(default_value: Any) -> Callable:
        """返回默认值"""
        async def fallback():
            logger.info(f"[降级] 返回默认值：{default_value}")
            return default_value
        return fallback

    @staticmethod
    def return_cached(cache_key: str, cache: Dict[str, Any]) -> Callable:
        """返回缓存值"""
        async def fallback():
            if cache_key in cache:
                logger.info(f"[降级] 返回缓存值：{cache_key}")
                return cache[cache_key]
            raise FallbackError(f"缓存未命中：{cache_key}")
        return fallback

    @staticmethod
    def partial_result(partial_func: Callable) -> Callable:
        """返回部分结果"""
        async def fallback():
            logger.info("[降级] 返回部分结果")
            return await partial_func()
        return fallback
