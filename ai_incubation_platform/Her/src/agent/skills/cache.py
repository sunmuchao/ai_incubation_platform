"""
Skill 缓存机制

为高频调用的 Skill 提供缓存支持，降低重复计算，提升响应速度。
"""
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json
from utils.logger import logger


class SkillCacheConfig:
    """Skill 缓存配置"""

    # 默认缓存时间（秒）
    DEFAULT_TTL = 300  # 5 分钟

    # 高频 Skill 缓存配置
    SKILL_CACHE_CONFIG = {
        # Skill 名称：TTL（秒）
        "risk_control": 600,  # 10 分钟 - 风控数据变化较慢
        "share_growth": 300,  # 5 分钟
        "conversation_matchmaker": 120,  # 2 分钟 - 匹配推荐更新频繁
        "activity_director": 600,  # 10 分钟 - 地点推荐相对稳定
        "date_coach": 300,  # 5 分钟
        "date_assistant": 300,  # 5 分钟
        "relationship_curator": 600,  # 10 分钟 - 关系数据变化慢
        "performance_coach": 300,  # 5 分钟
        "emotion_translator": 60,  # 1 分钟 - 情感实时变化
        "safety_guardian": 30,  # 30 秒 - 安全数据需要实时
        "silence_breaker": 30,  # 30 秒 - 沉默检测需要实时
        "emotion_mediator": 60,  # 1 分钟 - 情感调解需要实时
        "love_language_translator": 120,  # 2 分钟
        "relationship_prophet": 300,  # 5 分钟
    }

    # 缓存键前缀
    CACHE_KEY_PREFIX = "skill_cache:"

    # 最大缓存条目数（防止内存溢出）
    MAX_CACHE_ENTRIES = 1000


class SkillCacheManager:
    """Skill 缓存管理器"""

    def __init__(self):
        # 内存缓存存储
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    def _generate_cache_key(self, skill_name: str, params: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 序列化参数并生成哈希
        param_str = json.dumps(params, sort_keys=True, default=str)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"{SkillCacheConfig.CACHE_KEY_PREFIX}{skill_name}:{param_hash}"

    def _get_ttl(self, skill_name: str) -> int:
        """获取 Skill 的 TTL"""
        return SkillCacheConfig.SKILL_CACHE_CONFIG.get(
            skill_name, SkillCacheConfig.DEFAULT_TTL
        )

    def get(self, skill_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        cache_key = self._generate_cache_key(skill_name, params)

        if cache_key not in self._cache:
            self._cache_stats["misses"] += 1
            return None

        cached = self._cache[cache_key]
        expires_at = cached.get("expires_at")

        # 检查是否过期
        if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
            # 过期，删除
            del self._cache[cache_key]
            self._cache_stats["evictions"] += 1
            self._cache_stats["misses"] += 1
            return None

        self._cache_stats["hits"] += 1
        logger.debug(f"SkillCache: HIT for {skill_name}, key={cache_key[:50]}...")
        return cached["data"]

    def set(self, skill_name: str, params: Dict[str, Any], data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """设置缓存"""
        if ttl is None:
            ttl = self._get_ttl(skill_name)

        cache_key = self._generate_cache_key(skill_name, params)
        expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

        # 检查是否需要清理旧缓存
        if len(self._cache) >= SkillCacheConfig.MAX_CACHE_ENTRIES:
            self._evict_oldest()

        self._cache[cache_key] = {
            "data": data,
            "expires_at": expires_at,
            "created_at": datetime.now().isoformat(),
            "skill_name": skill_name
        }

        logger.debug(f"SkillCache: SET for {skill_name}, TTL={ttl}s, key={cache_key[:50]}...")

    def invalidate(self, skill_name: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        使缓存失效

        Args:
            skill_name: Skill 名称
            params: 如果提供，只删除特定参数的缓存；否则删除该 Skill 的所有缓存

        Returns:
            删除的缓存条目数
        """
        if params:
            cache_key = self._generate_cache_key(skill_name, params)
            if cache_key in self._cache:
                del self._cache[cache_key]
                return 1
            return 0

        # 删除该 Skill 的所有缓存
        keys_to_delete = [
            k for k in self._cache.keys()
            if k.startswith(f"{SkillCacheConfig.CACHE_KEY_PREFIX}{skill_name}:")
        ]
        for key in keys_to_delete:
            del self._cache[key]

        logger.info(f"SkillCache: Invalidated {len(keys_to_delete)} entries for {skill_name}")
        return len(keys_to_delete)

    def _evict_oldest(self) -> None:
        """清理最旧的缓存条目"""
        if not self._cache:
            return

        # 找到最旧的条目
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].get("created_at", "")
        )
        del self._cache[oldest_key]
        self._cache_stats["evictions"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (
            self._cache_stats["hits"] / total_requests
            if total_requests > 0 else 0
        )

        return {
            "total_entries": len(self._cache),
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "evictions": self._cache_stats["evictions"],
            "hit_rate": round(hit_rate, 2)
        }

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        logger.info("SkillCache: Cleared all entries")


# 全局缓存管理器实例
_cache_manager: Optional[SkillCacheManager] = None


def get_cache_manager() -> SkillCacheManager:
    """获取缓存管理器单例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = SkillCacheManager()
    return _cache_manager


def cache_skill_result(skill_name: str):
    """
    Skill 结果缓存装饰器

    用法:
        @cache_skill_result("risk_control")
        async def execute(self, user_id: str, service_type: str, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取缓存管理器
            cache = get_cache_manager()

            # 提取用于生成缓存键的参数
            # 假设第一个参数是 self，跳过
            cache_params = {}
            for key, value in kwargs.items():
                # 只缓存可序列化的参数
                if key not in ["context", "kwargs"]:
                    try:
                        json.dumps(value, default=str)
                        cache_params[key] = value
                    except (TypeError, ValueError):
                        pass

            # 尝试从缓存获取
            cached_result = cache.get(skill_name, cache_params)
            if cached_result is not None:
                logger.info(f"SkillCache: Returning cached result for {skill_name}")
                return cached_result

            # 执行原函数
            result = await func(*args, **kwargs)

            # 只有成功的结果才缓存
            if result.get("success", False):
                cache.set(skill_name, cache_params, result)

            return result
        return wrapper

    return decorator


# 缓存刷新装饰器（用于使特定缓存失效）
def invalidate_skill_cache(skill_name: str, params_key: Optional[str] = None):
    """
    缓存失效装饰器

    用于在数据更新时使相关缓存失效

    用法:
        @invalidate_skill_cache("risk_control")
        def update_data(self, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 先执行原函数
            result = await func(*args, **kwargs)

            # 使缓存失效
            cache = get_cache_manager()
            if params_key and params_key in kwargs:
                cache.invalidate(skill_name, kwargs[params_key])
            else:
                cache.invalidate(skill_name)

            return result
        return wrapper

    return decorator


# 缓存 API 端点
def register_cache_routes(router):
    """注册缓存管理 API 路由"""
    from fastapi import Depends
    from auth.jwt import get_current_user

    @router.get("/cache/stats")
    async def get_cache_stats(current_user: dict = Depends(get_current_user)):
        """获取缓存统计"""
        cache = get_cache_manager()
        return {
            "success": True,
            "stats": cache.get_stats()
        }

    @router.post("/cache/invalidate/{skill_name}")
    async def invalidate_skill(
        skill_name: str,
        current_user: dict = Depends(get_current_user)
    ):
        """使 Skill 缓存失效"""
        cache = get_cache_manager()
        count = cache.invalidate(skill_name)
        return {
            "success": True,
            "invalidated_count": count
        }

    @router.post("/cache/clear")
    async def clear_cache(current_user: dict = Depends(get_current_user)):
        """清空所有缓存（管理员操作）"""
        # 这里应该添加权限检查
        cache = get_cache_manager()
        cache.clear()
        return {
            "success": True,
            "message": "Cache cleared"
        }


# 导出
__all__ = [
    "SkillCacheConfig",
    "SkillCacheManager",
    "get_cache_manager",
    "cache_skill_result",
    "invalidate_skill_cache",
]
