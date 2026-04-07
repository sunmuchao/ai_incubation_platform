"""
降级模式实现

提供 DeerFlow 不可用时的降级策略和本地执行能力
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)


class FallbackMode(Enum):
    """降级模式"""
    DISABLED = "disabled"  # 不启用降级，直接失败
    LOCAL_ONLY = "local_only"  # 仅本地执行
    HYBRID = "hybrid"  # 混合模式，优先 DeerFlow，失败时降级
    CACHED = "cached"  # 使用缓存结果


class FallbackStrategy(Enum):
    """降级策略"""
    FAIL_FAST = "fail_fast"  # 快速失败
    RETRY_THEN_FALLBACK = "retry_then_fallback"  # 重试后降级
    ALWAYS_FALLBACK = "always_fallback"  # 始终降级
    CONDITIONAL = "conditional"  # 条件降级


@dataclass
class FallbackConfig:
    """降级配置"""
    mode: FallbackMode = FallbackMode.HYBRID
    strategy: FallbackStrategy = FallbackStrategy.RETRY_THEN_FALLBACK
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_ttl: int = 3600  # 缓存过期时间（秒）
    condition_check: Optional[Callable[[], bool]] = None
    local_handlers: Dict[str, Callable] = field(default_factory=dict)


@dataclass
class FallbackResult:
    """降级执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    is_fallback: bool = False
    fallback_mode: Optional[FallbackMode] = None
    execution_time_ms: float = 0.0
    cache_hit: bool = False


class FallbackModeManager:
    """
    降级模式管理器

    功能:
    - 降级模式切换
    - 本地执行处理器
    - 缓存管理
    - 健康检查
    """

    def __init__(self, config: Optional[FallbackConfig] = None):
        """
        初始化降级模式

        Args:
            config: 降级配置
        """
        self.config = config or FallbackConfig()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._is_deerflow_available = True
        self._health_check_interval = 60  # 秒
        self._last_health_check = 0.0

    @property
    def mode(self) -> FallbackMode:
        """获取当前降级模式"""
        return self.config.mode

    @mode.setter
    def mode(self, value: FallbackMode) -> None:
        """设置降级模式"""
        self.config.mode = value
        logger.info(f"Fallback mode set to: {value}")

    @property
    def is_degraded(self) -> bool:
        """检查是否处于降级状态"""
        return not self._is_deerflow_available or self.config.mode == FallbackMode.LOCAL_ONLY

    def set_deerflow_availability(self, available: bool) -> None:
        """设置 DeerFlow 可用性"""
        self._is_deerflow_available = available
        logger.info(f"DeerFlow availability: {available}")

    def should_fallback(self) -> bool:
        """判断是否应该降级"""
        if self.config.mode == FallbackMode.DISABLED:
            return False

        if self.config.mode == FallbackMode.LOCAL_ONLY:
            return True

        if self.config.mode == FallbackMode.CACHED:
            return True

        if not self._is_deerflow_available:
            return True

        # 条件降级
        if self.config.strategy == FallbackStrategy.CONDITIONAL:
            if self.config.condition_check:
                return not self.config.condition_check()

        return False

    async def execute(
        self,
        primary_func: Callable,
        fallback_func: Optional[Callable] = None,
        cache_key: Optional[str] = None,
        *args,
        **kwargs
    ) -> FallbackResult:
        """
        执行带降级的函数

        Args:
            primary_func: 主函数（DeerFlow）
            fallback_func: 降级函数（本地执行）
            cache_key: 缓存键
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            FallbackResult: 执行结果
        """
        start_time = time.time()

        # 检查缓存
        if cache_key and self.config.mode == FallbackMode.CACHED:
            cached = self._get_cache(cache_key)
            if cached is not None:
                return FallbackResult(
                    success=True,
                    data=cached,
                    is_fallback=True,
                    fallback_mode=FallbackMode.CACHED,
                    cache_hit=True,
                    execution_time_ms=(time.time() - start_time) * 1000
                )

        # 判断是否直接降级
        if self.should_fallback():
            return await self._execute_fallback(
                fallback_func or self._create_default_fallback(primary_func),
                cache_key,
                start_time,
                *args,
                **kwargs
            )

        # 尝试执行主函数
        return await self._execute_with_fallback(
            primary_func,
            fallback_func,
            cache_key,
            *args,
            **kwargs,
            start_time=start_time
        )

    async def _execute_with_fallback(
        self,
        primary_func: Callable,
        fallback_func: Optional[Callable],
        cache_key: Optional[str],
        start_time: float,
        *args,
        **kwargs
    ) -> FallbackResult:
        """执行带 fallback 的主函数"""
        attempts = 0
        last_error = None

        while attempts <= self.config.max_retries:
            try:
                if asyncio.iscoroutinefunction(primary_func):
                    result = await primary_func(*args, **kwargs)
                else:
                    result = primary_func(*args, **kwargs)

                # 缓存结果
                if cache_key:
                    self._set_cache(cache_key, result)

                return FallbackResult(
                    success=True,
                    data=result,
                    is_fallback=False,
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            except Exception as e:
                last_error = e
                logger.warning(f"Primary execution failed (attempt {attempts + 1}): {e}")
                attempts += 1

                if attempts <= self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * attempts)

        # 所有重试失败，执行降级
        logger.warning("All primary attempts failed, falling back")
        return await self._execute_fallback(
            fallback_func or self._create_default_fallback(primary_func),
            cache_key,
            start_time,
            *args,
            **kwargs,
        )

    async def _execute_fallback(
        self,
        fallback_func: Callable,
        cache_key: Optional[str],
        start_time: float,
        error: Optional[Exception] = None,
        *args,
        **kwargs
    ) -> FallbackResult:
        """执行降级函数"""
        try:
            if asyncio.iscoroutinefunction(fallback_func):
                result = await fallback_func(*args, **kwargs)
            else:
                result = fallback_func(*args, **kwargs)

            # 缓存结果
            if cache_key:
                self._set_cache(cache_key, result)

            return FallbackResult(
                success=True,
                data=result,
                is_fallback=True,
                fallback_mode=self.config.mode,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.error(f"Fallback execution failed: {e}")
            return FallbackResult(
                success=False,
                error=str(e),
                is_fallback=True,
                fallback_mode=self.config.mode,
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def _create_default_fallback(self, primary_func: Callable) -> Callable:
        """创建默认降级函数"""
        async def default_fallback(*args, **kwargs):
            logger.warning("Using default fallback, returning None")
            return {"status": "fallback_executed", "warning": "No fallback handler available"}
        return default_fallback

    def _get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.config.cache_ttl:
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        """设置缓存"""
        self._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
        logger.debug(f"Cached result for key: {key}")

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("Cache cleared")

    def register_local_handler(self, name: str, handler: Callable) -> None:
        """注册本地处理器"""
        self.config.local_handlers[name] = handler
        logger.info(f"Registered local handler: {name}")

    def get_local_handler(self, name: str) -> Optional[Callable]:
        """获取本地处理器"""
        return self.config.local_handlers.get(name)

    async def health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        self._last_health_check = time.time()

        status = {
            "is_degraded": self.is_degraded,
            "fallback_mode": self.config.mode.value,
            "deerflow_available": self._is_deerflow_available,
            "cache_size": len(self._cache),
            "registered_handlers": len(self.config.local_handlers),
            "last_health_check": self._last_health_check
        }
        return status

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "mode": self.config.mode.value,
            "strategy": self.config.strategy.value,
            "is_degraded": self.is_degraded,
            "deerflow_available": self._is_deerflow_available,
            "max_retries": self.config.max_retries,
            "cache_ttl": self.config.cache_ttl,
            "cache_entries": len(self._cache)
        }


class FallbackStrategy:
    """
    降级策略实现

    提供不同的降级策略选择
    """

    def __init__(self, fallback_mode: FallbackMode):
        self.fallback_mode = fallback_mode

    def should_retry(self, attempt: int, max_retries: int) -> bool:
        """判断是否应该重试"""
        return attempt < max_retries

    def get_delay(self, attempt: int, base_delay: float) -> float:
        """计算重试延迟（指数退避）"""
        import random
        jitter = random.uniform(0, base_delay * 0.1)
        return base_delay * (2 ** attempt) + jitter

    def select_fallback_handler(
        self,
        name: str,
        available_handlers: Dict[str, Callable]
    ) -> Optional[Callable]:
        """选择降级处理器"""
        # 优先查找同名处理器
        if name in available_handlers:
            return available_handlers[name]

        # 查找默认处理器
        if "default" in available_handlers:
            return available_handlers["default"]

        return None


# 便捷函数
async def execute_with_fallback(
    primary: Callable,
    fallback: Optional[Callable] = None,
    mode: FallbackMode = FallbackMode.HYBRID,
    max_retries: int = 3,
    cache_key: Optional[str] = None,
    *args,
    **kwargs
) -> FallbackResult:
    """
    便捷函数：带降级执行

    Args:
        primary: 主函数
        fallback: 降级函数
        mode: 降级模式
        max_retries: 最大重试次数
        cache_key: 缓存键
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        FallbackResult: 执行结果
    """
    config = FallbackConfig(
        mode=mode,
        max_retries=max_retries
    )
    fallback_mode = FallbackModeManager(config)
    return await fallback_mode.execute(
        primary,
        fallback,
        cache_key,
        *args,
        **kwargs
    )
