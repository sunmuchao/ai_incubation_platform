"""
API 限流中间件

基于令牌桶算法实现 API 限流，防止暴力破解和 DDoS 攻击。
"""
import time
from collections import defaultdict
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from config import settings
from utils.logger import logger


class TokenBucket:
    """
    令牌桶限流器

    每个用户/IP 有一个桶，以固定速率生成令牌，请求消耗令牌。
    桶满时令牌不再生成，桶空时请求被拒绝。
    """

    def __init__(self, capacity: int = 100, refill_rate: float = 10.0):
        """
        Args:
            capacity: 桶容量（最大令牌数）
            refill_rate: 令牌生成速率（个/秒）
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets: Dict[str, Tuple[float, float]] = {}  # key -> (tokens, last_update)
        self._locks: Dict[str, bool] = {}  # 简易锁标记

    def _get_bucket(self, key: str) -> Tuple[float, float]:
        """获取或创建桶"""
        if key not in self._buckets:
            self._buckets[key] = (float(self.capacity), time.time())
        return self._buckets[key]

    def consume(self, key: str, tokens: int = 1) -> Tuple[bool, float]:
        """
        消费令牌

        Args:
            key: 桶标识（用户 ID 或 IP）
            tokens: 消费令牌数量

        Returns:
            (是否成功，等待时间秒数)
        """
        # 先获取桶，再获取当前时间，避免 time_passed 为负数
        bucket_tokens, last_update = self._get_bucket(key)
        current_time = time.time()

        # 计算新增令牌数
        time_passed = current_time - last_update
        new_tokens = time_passed * self.refill_rate
        bucket_tokens = min(self.capacity, bucket_tokens + new_tokens)

        if bucket_tokens >= tokens:
            # 有足够令牌，消费
            bucket_tokens -= tokens
            self._buckets[key] = (bucket_tokens, current_time)
            return True, 0.0
        else:
            # 令牌不足，计算需要等待的时间
            tokens_needed = tokens - bucket_tokens
            wait_time = tokens_needed / self.refill_rate
            # 更新桶状态（即使失败也更新，避免重复计算）
            self._buckets[key] = (bucket_tokens, current_time)
            return False, wait_time

    def get_remaining(self, key: str) -> int:
        """获取剩余令牌数"""
        # 先获取桶，再获取当前时间
        bucket_tokens, last_update = self._get_bucket(key)
        current_time = time.time()

        # 计算新增令牌数
        time_passed = current_time - last_update
        new_tokens = time_passed * self.refill_rate
        bucket_tokens = min(self.capacity, bucket_tokens + new_tokens)

        return int(bucket_tokens)


class RateLimiter:
    """
    API 限流器

    支持基于用户 ID 和 IP 的限流策略。
    """

    def __init__(
        self,
        # 登录限流：更严格
        login_capacity: int = 10,
        login_refill_rate: float = 1.0,
        # 普通 API 限流
        api_capacity: int = 100,
        api_refill_rate: float = 10.0,
        # 匹配查询限流
        match_capacity: int = 50,
        match_refill_rate: float = 5.0,
    ):
        self._login_bucket = TokenBucket(login_capacity, login_refill_rate)
        self._api_bucket = TokenBucket(api_capacity, api_refill_rate)
        self._match_bucket = TokenBucket(match_capacity, match_refill_rate)

        # 限流统计
        self._stats = defaultdict(int)

    def _get_client_key(self, request: Request) -> str:
        """获取客户端标识（用户 ID 或 IP）"""
        # 优先使用用户 ID
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return f"user:{user_id}"

        # 退而使用 IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"

    async def check_login_limit(self, request: Request) -> None:
        """检查登录接口限流"""
        key = self._get_client_key(request)
        allowed, wait_time = self._login_bucket.consume(key)

        if not allowed:
            self._stats["login_limited"] += 1
            logger.warning(
                f"Login rate limited: {key}, wait_time={wait_time:.1f}s"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too many login attempts",
                    "retry_after": int(wait_time) + 1,
                    "message": "请稍后再试，频繁登录可能触发账号保护"
                },
                headers={"Retry-After": str(int(wait_time) + 1)}
            )

    async def check_match_limit(self, request: Request) -> None:
        """检查匹配接口限流"""
        key = self._get_client_key(request)
        allowed, wait_time = self._match_bucket.consume(key)

        if not allowed:
            self._stats["match_limited"] += 1
            logger.warning(
                f"Match query rate limited: {key}, wait_time={wait_time:.1f}s"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too many match queries",
                    "retry_after": int(wait_time) + 1,
                },
                headers={"Retry-After": str(int(wait_time) + 1)}
            )

    async def check_api_limit(self, request: Request) -> None:
        """检查普通 API 限流"""
        key = self._get_client_key(request)
        allowed, wait_time = self._api_bucket.consume(key)

        if not allowed:
            self._stats["api_limited"] += 1
            logger.warning(f"API rate limited: {key}, wait_time={wait_time:.1f}s")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too many requests",
                    "retry_after": int(wait_time) + 1,
                },
                headers={"Retry-After": str(int(wait_time) + 1)}
            )

    def get_remaining(self, request: Request, bucket_type: str = "api") -> int:
        """获取剩余请求数"""
        key = self._get_client_key(request)
        if bucket_type == "login":
            return self._login_bucket.get_remaining(key)
        elif bucket_type == "match":
            return self._match_bucket.get_remaining(key)
        else:
            return self._api_bucket.get_remaining(key)

    def get_stats(self) -> Dict:
        """获取限流统计"""
        return dict(self._stats)


# 全局限流器实例
# 配置说明：
# - 登录：10 次突发，1 次/秒补充（10 秒内最多 10 次登录尝试）
# - 匹配：50 次突发，5 次/秒补充（10 秒内最多 50 次匹配查询）
# - 普通 API：100 次突发，10 次/秒补充
rate_limiter = RateLimiter(
    login_capacity=10,
    login_refill_rate=1.0,
    api_capacity=100,
    api_refill_rate=10.0,
    match_capacity=50,
    match_refill_rate=5.0,
)


# ========== FastAPI 中间件和依赖 ==========

from fastapi import Depends


async def rate_limit_login(request: Request):
    """登录接口限流依赖"""
    await rate_limiter.check_login_limit(request)


async def rate_limit_match(request: Request):
    """匹配接口限流依赖"""
    await rate_limiter.check_match_limit(request)


async def rate_limit_api(request: Request):
    """普通 API 限流依赖"""
    await rate_limiter.check_api_limit(request)


# 可选：全局中间件方式（对所有请求限流）
class RateLimitMiddleware:
    """
    全局限流中间件

    用法：app.add_middleware(RateLimitMiddleware)
    """

    def __init__(self, app, excluded_paths: Optional[list] = None):
        self.app = app
        self.excluded_paths = excluded_paths or ["/health", "/docs", "/openapi.json"]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        # 跳过排除的路径
        if any(path.startswith(p) for p in self.excluded_paths):
            await self.app(scope, receive, send)
            return

        # 检查限流
        try:
            await rate_limiter.check_api_limit(request)
        except HTTPException as exc:
            response = JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
                headers=exc.headers,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
