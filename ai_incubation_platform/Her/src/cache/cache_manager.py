"""
缓存管理模块

基于 Redis 实现多层缓存策略，用于：
- 用户画像缓存
- 匹配结果缓存
- 会话状态管理
- 通用缓存项

性能优化（v1.30.0）：
- 内存缓存 LRU 淘汰机制（防止无限增长）
- 线程安全锁（防止并发竞争）
- 结构化失效索引（提升失效效率）
"""
import json
import hashlib
import threading
from collections import OrderedDict
from typing import Optional, Any, Dict, List, Set
from datetime import timedelta, datetime
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
    1. L1: 内存缓存（最快，容量小，带 LRU）
    2. L2: Redis 缓存（较快，容量大，可共享）
    3. L3: 数据库（最慢，持久化）

    性能优化（v1.30.0）：
    - 内存缓存使用 OrderedDict 实现 LRU 淘汰
    - 线程安全锁保护并发操作
    - 结构化失效索引（用户 -> 缓存键映射）
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

    # 性能优化：内存缓存配置
    MEMORY_CACHE_MAX_SIZE = 1000  # 最大条目数

    def __new__(cls) -> "CacheManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._redis_client = None
            # 性能优化：使用 OrderedDict 实现 LRU
            cls._instance._memory_cache: OrderedDict = OrderedDict()
            cls._instance._cache_hits = 0
            cls._instance._cache_misses = 0
            # 性能优化：线程安全锁
            cls._instance._lock = threading.RLock()
            # 性能优化：用户 -> 缓存键索引（加速失效）
            cls._instance._user_key_index: Dict[str, Set[str]] = {}
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

    def _evict_if_needed(self) -> None:
        """LRU 淘汰：超过容量时删除最旧的条目"""
        with self._lock:
            while len(self._memory_cache) > self.MEMORY_CACHE_MAX_SIZE:
                # OrderedDict 的 popitem(last=False) 删除最旧的条目
                oldest_key, _ = self._memory_cache.popitem(last=False)
                # 同时清理用户索引
                self._remove_from_user_index(oldest_key)
                logger.debug(f"[Cache] LRU evicted: {oldest_key}")

    def _add_to_user_index(self, user_id: str, cache_key: str) -> None:
        """将缓存键添加到用户索引"""
        with self._lock:
            if user_id not in self._user_key_index:
                self._user_key_index[user_id] = set()
            self._user_key_index[user_id].add(cache_key)

    def _remove_from_user_index(self, cache_key: str) -> None:
        """从用户索引中移除缓存键"""
        with self._lock:
            for user_id, keys in self._user_key_index.items():
                keys.discard(cache_key)
            # 清理空的用户索引
            empty_users = [u for u, keys in self._user_key_index.items() if not keys]
            for u in empty_users:
                del self._user_key_index[u]

    def _get_user_keys(self, user_id: str) -> Set[str]:
        """获取用户的所有缓存键"""
        with self._lock:
            return self._user_key_index.get(user_id, set()).copy()

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

        # 性能优化：线程安全 + LRU 顺序维护
        with self._lock:
            if key in self._memory_cache:
                self._cache_hits += 1
                # LRU: 访问时移动到末尾（最近使用）
                self._memory_cache.move_to_end(key)
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
                    with self._lock:
                        self._memory_cache[key] = profile
                        self._memory_cache.move_to_end(key)
                        self._add_to_user_index(user_id, key)
                        self._evict_if_needed()
                    return profile
            except RedisError as e:
                logger.warning(f"Redis get profile failed: {e}")

        self._cache_misses += 1
        logger.debug(f"Profile cache miss: {user_id}")
        return None

    def set_profile(self, user_id: str, profile: Dict) -> bool:
        """设置用户画像缓存"""
        key = self._make_key(self.PROFILE_KEY, user_id)

        # 性能优化：线程安全 + LRU 淘汰
        with self._lock:
            self._memory_cache[key] = profile
            self._memory_cache.move_to_end(key)  # 新条目放到末尾
            self._add_to_user_index(user_id, key)
            self._evict_if_needed()

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

        # 性能优化：线程安全
        with self._lock:
            self._memory_cache.pop(key, None)
            self._user_key_index.pop(user_id, None)

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

        # 性能优化：线程安全 + LRU
        with self._lock:
            if key in self._memory_cache:
                self._cache_hits += 1
                self._memory_cache.move_to_end(key)
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
                    with self._lock:
                        self._memory_cache[key] = result
                        self._memory_cache.move_to_end(key)
                        self._add_to_user_index(user_id, key)
                        self._evict_if_needed()
                    return result
            except RedisError as e:
                logger.warning(f"Redis get match result failed: {e}")

        self._cache_misses += 1
        logger.debug(f"Match result cache miss: {user_id}")
        return None

    def set_match_result(self, user_id: str, matches: List[Dict], limit: int = 10) -> bool:
        """设置匹配结果缓存"""
        key = self._make_key(self.MATCH_RESULT_KEY, user_id, str(limit))

        # 性能优化：线程安全 + LRU
        with self._lock:
            self._memory_cache[key] = matches
            self._memory_cache.move_to_end(key)
            self._add_to_user_index(user_id, key)
            self._evict_if_needed()

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
        """失效用户匹配结果缓存（使用用户索引加速）"""
        # 性能优化：使用用户索引获取所有相关键，O(1) 复杂度
        user_keys = self._get_user_keys(user_id)

        # 筛选出匹配结果相关的键
        match_keys_to_delete = [
            k for k in user_keys
            if k.startswith(f"{self.MATCH_RESULT_KEY}{user_id}:")
        ]

        # 清除内存缓存
        with self._lock:
            for key in match_keys_to_delete:
                self._memory_cache.pop(key, None)
            # 清理用户索引
            self._user_key_index.pop(user_id, None)

        # 清除 Redis 缓存
        if self._redis_client:
            try:
                if match_keys_to_delete:
                    self._redis_client.delete(*match_keys_to_delete)
                    logger.debug(f"Match result cache invalidated: {user_id}, keys={len(match_keys_to_delete)}")
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

    # ========== 用户数据变更时的主动缓存失效（Future 增强） ==========

    def invalidate_user_all_cache(self, user_id: str, reason: str = "unknown") -> Dict[str, bool]:
        """
        用户数据变更时，主动失效所有相关缓存

        Args:
            user_id: 用户 ID
            reason: 失效原因 (profile_update, matching_preference_change, membership_change, etc.)

        Returns:
            失效结果统计
        """
        results = {
            "profile": self.invalidate_profile(user_id),
            "match_result": self.invalidate_match_result(user_id),
            "mutual_match": self.invalidate_mutual_match(user_id),
        }

        # 记录日志
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"User cache invalidated: user_id={user_id}, reason={reason}, success={success_count}/{len(results)}")

        return results

    def invalidate_on_profile_update(self, user_id: str) -> Dict[str, bool]:
        """用户资料更新时的缓存失效"""
        return self.invalidate_user_all_cache(user_id, reason="profile_update")

    def invalidate_on_membership_change(self, user_id: str) -> Dict[str, bool]:
        """会员状态变更时的缓存失效"""
        return self.invalidate_user_all_cache(user_id, reason="membership_change")

    def invalidate_on_preference_change(self, user_id: str) -> Dict[str, bool]:
        """匹配偏好变更时的缓存失效"""
        return self.invalidate_user_all_cache(user_id, reason="preference_change")


# 全局缓存实例
cache_manager: CacheManager = CacheManager.get_instance()
