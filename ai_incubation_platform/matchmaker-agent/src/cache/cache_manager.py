"""
缓存管理模块

基于 Redis 实现多层缓存策略，用于：
- 用户画像缓存
- 匹配结果缓存
- 会话状态管理
- 通用缓存项
"""
import json
import hashlib
from typing import Optional, Any, Dict, List
from datetime import timedelta
from config import settings
from utils.logger import logger

try:
    import redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore
    RedisError = Exception  # type: ignore
    RedisConnectionError = Exception  # type: ignore
    REDIS_AVAILABLE = False


class CacheManager:
    """
    缓存管理器单例类

    提供多层缓存策略：
    1. L1: 内存缓存（最快，容量小）
    2. L2: Redis 缓存（较快，容量大，可共享）
    3. L3: 数据库（最慢，持久化）
    """

    _instance: Optional["CacheManager"] = None

    # 缓存键前缀
    KEY_PREFIX = "matchmaker:"
    PROFILE_KEY = f"{KEY_PREFIX}profile:"
    MATCH_RESULT_KEY = f"{KEY_PREFIX}match:"
    MUTUAL_MATCH_KEY = f"{KEY_PREFIX}mutual:"
    SESSION_KEY = f"{KEY_PREFIX}session:"
    GENERIC_KEY = f"{KEY_PREFIX}generic:"

    # 默认过期时间
    PROFILE_TTL = timedelta(minutes=30)
    MATCH_RESULT_TTL = timedelta(minutes=10)
    SESSION_TTL = timedelta(hours=24)
    GENERIC_TTL = timedelta(hours=1)

    def __new__(cls) -> "CacheManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._redis_client = None
            cls._instance._memory_cache: Dict[str, Any] = {}
            cls._instance._cache_hits = 0
            cls._instance._cache_misses = 0
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CacheManager":
        """获取单例实例"""
        return cls()

    def __init__(self):
        if self._initialized:
            return
        self._init_redis()
        self._initialized = True
        logger.info(f"CacheManager initialized, redis_available={REDIS_AVAILABLE}")

    def _init_redis(self) -> None:
        """初始化 Redis 连接"""
        if not REDIS_AVAILABLE or not settings.redis_url:
            logger.info("Redis not configured, using memory cache only")
            return

        try:
            self._redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self._redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, falling back to memory cache")
            self._redis_client = None

    def _serialize(self, value: Any) -> str:
        """序列化值为 JSON 字符串"""
        return json.dumps(value, default=str, ensure_ascii=False)

    def _deserialize(self, value: str) -> Any:
        """反序列化 JSON 字符串"""
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def _make_key(self, prefix: str, *parts: str) -> str:
        """生成缓存键"""
        if not parts:
            return prefix
        key_suffix = ":".join(str(p) for p in parts)
        return f"{prefix}{key_suffix}"

    def _make_hash_key(self, prefix: str, data: Dict) -> str:
        """生成基于数据哈希的缓存键（用于匹配结果等）"""
        hash_input = json.dumps(data, sort_keys=True, default=str)
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return f"{prefix}{hash_value}"

    # ========== 用户画像缓存 ==========

    def get_profile(self, user_id: str) -> Optional[Dict]:
        """获取用户画像缓存"""
        key = self._make_key(self.PROFILE_KEY, user_id)

        # 先查内存缓存
        if key in self._memory_cache:
            self._cache_hits += 1
            logger.debug(f"Profile cache hit (memory): {user_id}")
            return self._memory_cache[key]

        # 再查 Redis
        if self._redis_client:
            try:
                value = self._redis_client.get(key)
                if value:
                    self._cache_hits += 1
                    logger.debug(f"Profile cache hit (redis): {user_id}")
                    profile = self._deserialize(value)
                    # 回写到内存缓存
                    self._memory_cache[key] = profile
                    return profile
            except RedisError as e:
                logger.warning(f"Redis get profile failed: {e}")

        self._cache_misses += 1
        logger.debug(f"Profile cache miss: {user_id}")
        return None

    def set_profile(self, user_id: str, profile: Dict) -> bool:
        """设置用户画像缓存"""
        key = self._make_key(self.PROFILE_KEY, user_id)

        # 内存缓存
        self._memory_cache[key] = profile

        # Redis 缓存
        if self._redis_client:
            try:
                ttl_seconds = int(self.PROFILE_TTL.total_seconds())
                self._redis_client.setex(key, ttl_seconds, self._serialize(profile))
                logger.debug(f"Profile cached: {user_id}")
                return True
            except RedisError as e:
                logger.warning(f"Redis set profile failed: {e}")
        return True

    def invalidate_profile(self, user_id: str) -> bool:
        """失效用户画像缓存"""
        key = self._make_key(self.PROFILE_KEY, user_id)

        # 清除内存缓存
        self._memory_cache.pop(key, None)

        # 清除 Redis 缓存
        if self._redis_client:
            try:
                self._redis_client.delete(key)
                logger.debug(f"Profile cache invalidated: {user_id}")
                return True
            except RedisError as e:
                logger.warning(f"Redis delete profile failed: {e}")
        return True

    # ========== 匹配结果缓存 ==========

    def get_match_result(self, user_id: str, limit: int = 10) -> Optional[List[Dict]]:
        """获取匹配结果缓存"""
        key = self._make_key(self.MATCH_RESULT_KEY, user_id, str(limit))

        # 先查内存缓存
        if key in self._memory_cache:
            self._cache_hits += 1
            logger.debug(f"Match result cache hit (memory): {user_id}")
            return self._memory_cache[key]

        # 再查 Redis
        if self._redis_client:
            try:
                value = self._redis_client.get(key)
                if value:
                    self._cache_hits += 1
                    logger.debug(f"Match result cache hit (redis): {user_id}")
                    result = self._deserialize(value)
                    # 回写到内存缓存
                    self._memory_cache[key] = result
                    return result
            except RedisError as e:
                logger.warning(f"Redis get match result failed: {e}")

        self._cache_misses += 1
        logger.debug(f"Match result cache miss: {user_id}")
        return None

    def set_match_result(self, user_id: str, matches: List[Dict], limit: int = 10) -> bool:
        """设置匹配结果缓存"""
        key = self._make_key(self.MATCH_RESULT_KEY, user_id, str(limit))

        # 内存缓存
        self._memory_cache[key] = matches

        # Redis 缓存
        if self._redis_client:
            try:
                ttl_seconds = int(self.MATCH_RESULT_TTL.total_seconds())
                self._redis_client.setex(key, ttl_seconds, self._serialize(matches))
                logger.debug(f"Match result cached: {user_id}, count={len(matches)}")
                return True
            except RedisError as e:
                logger.warning(f"Redis set match result failed: {e}")
        return True

    def invalidate_match_result(self, user_id: str) -> bool:
        """失效用户匹配结果缓存（清除所有 limit 配置）"""
        pattern = self._make_key(self.MATCH_RESULT_KEY, user_id, "*")

        # 清除内存缓存（遍历匹配）
        keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(f"{self.MATCH_RESULT_KEY}{user_id}:")]
        for key in keys_to_delete:
            del self._memory_cache[key]

        # 清除 Redis 缓存
        if self._redis_client:
            try:
                keys = self._redis_client.keys(pattern)
                if keys:
                    self._redis_client.delete(*keys)
                    logger.debug(f"Match result cache invalidated: {user_id}")
                return True
            except RedisError as e:
                logger.warning(f"Redis delete match result failed: {e}")
        return True

    # ========== 双向匹配缓存 ==========

    def get_mutual_match(self, user_id: str) -> Optional[List[Dict]]:
        """获取双向匹配缓存"""
        key = self._make_key(self.MUTUAL_MATCH_KEY, user_id)

        if key in self._memory_cache:
            self._cache_hits += 1
            logger.debug(f"Mutual match cache hit (memory): {user_id}")
            return self._memory_cache[key]

        if self._redis_client:
            try:
                value = self._redis_client.get(key)
                if value:
                    self._cache_hits += 1
                    logger.debug(f"Mutual match cache hit (redis): {user_id}")
                    result = self._deserialize(value)
                    self._memory_cache[key] = result
                    return result
            except RedisError as e:
                logger.warning(f"Redis get mutual match failed: {e}")

        self._cache_misses += 1
        return None

    def set_mutual_match(self, user_id: str, matches: List[Dict]) -> bool:
        """设置双向匹配缓存"""
        key = self._make_key(self.MUTUAL_MATCH_KEY, user_id)

        self._memory_cache[key] = matches

        if self._redis_client:
            try:
                ttl_seconds = int(self.MATCH_RESULT_TTL.total_seconds())
                self._redis_client.setex(key, ttl_seconds, self._serialize(matches))
                logger.debug(f"Mutual match cached: {user_id}, count={len(matches)}")
                return True
            except RedisError as e:
                logger.warning(f"Redis set mutual match failed: {e}")
        return True

    # ========== 会话缓存 ==========

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话数据"""
        key = self._make_key(self.SESSION_KEY, session_id)

        if self._redis_client:
            try:
                value = self._redis_client.get(key)
                if value:
                    self._cache_hits += 1
                    return self._deserialize(value)
            except RedisError as e:
                logger.warning(f"Redis get session failed: {e}")

        self._cache_misses += 1
        return None

    def set_session(self, session_id: str, data: Dict) -> bool:
        """设置会话数据"""
        key = self._make_key(self.SESSION_KEY, session_id)

        if self._redis_client:
            try:
                ttl_seconds = int(self.SESSION_TTL.total_seconds())
                self._redis_client.setex(key, ttl_seconds, self._serialize(data))
                return True
            except RedisError as e:
                logger.warning(f"Redis set session failed: {e}")
        return False

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        key = self._make_key(self.SESSION_KEY, session_id)

        self._memory_cache.pop(key, None)

        if self._redis_client:
            try:
                self._redis_client.delete(key)
                return True
            except RedisError as e:
                logger.warning(f"Redis delete session failed: {e}")
        return True

    # ========== 通用缓存方法 (v1.23 新增) ==========

    def get_cache_item(self, key: str) -> Optional[Any]:
        """获取通用缓存项"""
        full_key = key if key.startswith(self.KEY_PREFIX) else f"{self.GENERIC_KEY}{key}"

        # 先查内存缓存
        if full_key in self._memory_cache:
            self._cache_hits += 1
            logger.debug(f"Generic cache hit (memory): {key}")
            return self._memory_cache[full_key]

        # 再查 Redis
        if self._redis_client:
            try:
                value = self._redis_client.get(full_key)
                if value:
                    self._cache_hits += 1
                    logger.debug(f"Generic cache hit (redis): {key}")
                    result = self._deserialize(value)
                    self._memory_cache[full_key] = result
                    return result
            except RedisError as e:
                logger.warning(f"Redis get generic cache failed: {e}")

        self._cache_misses += 1
        logger.debug(f"Generic cache miss: {key}")
        return None

    def set_cache_item(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None
    ) -> bool:
        """设置通用缓存项"""
        full_key = key if key.startswith(self.KEY_PREFIX) else f"{self.GENERIC_KEY}{key}"
        default_ttl = ttl or self.GENERIC_TTL

        # 内存缓存
        self._memory_cache[full_key] = value

        # Redis 缓存
        if self._redis_client:
            try:
                ttl_seconds = int(default_ttl.total_seconds())
                self._redis_client.setex(full_key, ttl_seconds, self._serialize(value))
                logger.debug(f"Generic cache set: {key}, ttl={ttl_seconds}s")
                return True
            except RedisError as e:
                logger.warning(f"Redis set generic cache failed: {e}")
        return True

    def invalidate_cache_item(self, key: str) -> bool:
        """失效通用缓存项"""
        full_key = key if key.startswith(self.KEY_PREFIX) else f"{self.GENERIC_KEY}{key}"

        # 清除内存缓存
        self._memory_cache.pop(full_key, None)

        # 清除 Redis 缓存
        if self._redis_client:
            try:
                self._redis_client.delete(full_key)
                logger.debug(f"Generic cache invalidated: {key}")
                return True
            except RedisError as e:
                logger.warning(f"Redis delete generic cache failed: {e}")
        return True

    # ========== 工具方法 ==========

    def clear_memory_cache(self) -> None:
        """清空内存缓存（用于测试）"""
        self._memory_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Memory cache cleared")

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        stats = {
            "memory_cache_size": len(self._memory_cache),
            "redis_connected": self._redis_client is not None,
            "redis_available": REDIS_AVAILABLE and settings.redis_url is not None,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0
        }

        if self._memory_cache:
            stats["memory_cache_keys_sample"] = list(self._memory_cache.keys())[:20]

        if self._redis_client:
            try:
                info = self._redis_client.info("memory")
                stats["redis_used_memory"] = info.get("used_memory_human", "unknown")
                stats["redis_keys"] = self._redis_client.dbsize()
            except RedisError:
                stats["redis_used_memory"] = "unknown"
                stats["redis_keys"] = "unknown"

        return stats

    def health_check(self) -> bool:
        """健康检查"""
        if self._redis_client:
            try:
                self._redis_client.ping()
                return True
            except RedisError:
                return False
        # 无 Redis 配置时也认为健康（降级到内存缓存）
        return True


# 全局缓存实例
cache_manager: CacheManager = CacheManager.get_instance()
