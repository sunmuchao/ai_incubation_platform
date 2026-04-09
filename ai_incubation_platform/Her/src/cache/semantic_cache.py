"""
LLM 语义缓存层

P1 功能：基于语义相似度的缓存机制，降低 LLM 调用成本和延迟

工作原理：
1. 将查询转换为向量
2. 检索相似查询（阈值>0.95）
3. 检查缓存是否过期
4. 命中则返回缓存响应，未命中则调用 LLM 并写入缓存

缓存策略：
- TTL: 1 小时
- 相似度阈值：0.95
- 最大缓存数：10000
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib
import json
import numpy as np
from collections import OrderedDict
from utils.logger import logger


class SemanticCacheEntry:
    """语义缓存条目"""

    def __init__(
        self,
        query: str,
        response: Dict,
        query_vector: Optional[np.ndarray] = None,
        ttl_seconds: int = 3600
    ):
        self.query = query
        self.response = response
        self.query_vector = query_vector
        self.created_at = datetime.now()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)

    def hit(self):
        """记录一次访问"""
        self.access_count += 1


class SemanticCache:
    """
    语义缓存管理器

    使用向量相似度进行缓存匹配，支持：
    - 语义相似度检索
    - TTL 过期
    - LRU 淘汰策略
    """

    def __init__(
        self,
        max_size: int = 10000,
        similarity_threshold: float = 0.95,
        default_ttl: int = 3600
    ):
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl

        # 缓存存储：key -> entry
        self._cache: OrderedDict[str, SemanticCacheEntry] = OrderedDict()

        # 向量存储：key -> vector
        self._vectors: Dict[str, np.ndarray] = {}

        logger.info(
            f"SemanticCache initialized: max_size={max_size}, "
            f"threshold={similarity_threshold}, ttl={default_ttl}s"
        )

    def _compute_query_vector(self, query: str) -> np.ndarray:
        """
        计算查询向量

        简化实现：使用 TF-IDF 或词嵌入
        生产环境应使用 sentence-transformers 等模型
        """
        # 简化实现：使用词袋模型 + 哈希
        # 实际应使用：from sentence_transformers import SentenceTransformer
        # model = SentenceTransformer('all-MiniLM-L6-v2')
        # vector = model.encode(query)

        # 使用哈希生成固定长度的伪向量（演示用）
        vector_size = 384  # 模拟 sentence-transformers 的输出维度
        seed = int(hashlib.md5(query.encode('utf-8')).hexdigest(), 16) % (2**32)
        np.random.seed(seed)
        vector = np.random.randn(vector_size)
        # 归一化
        vector = vector / np.linalg.norm(vector)
        return vector

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """计算余弦相似度"""
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    def _generate_cache_key(self, query: str, context: Optional[Dict] = None) -> str:
        """生成缓存键"""
        key_data = f"{query}:{json.dumps(context or {}, sort_keys=True)}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()

    async def get(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        获取缓存响应

        Args:
            query: 查询字符串
            context: 上下文信息（可选）

        Returns:
            缓存的响应，如果未命中则返回 None
        """
        # 计算查询向量
        query_vector = self._compute_query_vector(query)

        # 搜索相似缓存
        best_match = None
        best_similarity = 0.0

        for key, entry in self._cache.items():
            if entry.is_expired():
                # 过期条目，删除
                self._remove_entry(key)
                continue

            # 计算相似度
            if key in self._vectors:
                similarity = self._cosine_similarity(query_vector, self._vectors[key])
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = (key, entry)

        if best_match and best_similarity >= self.similarity_threshold:
            key, entry = best_match
            entry.hit()

            # 移到 OrderedDict 末尾（LRU）
            self._cache.move_to_end(key)

            logger.info(
                f"Semantic cache HIT: query='{query[:50]}...', "
                f"similarity={best_similarity:.3f}"
            )

            return entry.response

        logger.info(f"Semantic cache MISS: query='{query[:50]}...'")
        return None

    async def set(
        self,
        query: str,
        response: Dict,
        context: Optional[Dict] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        设置缓存

        Args:
            query: 查询字符串
            response: 响应数据
            context: 上下文信息
            ttl: 过期时间（秒）
        """
        key = self._generate_cache_key(query, context)

        # 检查是否已存在
        if key in self._cache:
            logger.debug(f"Updating existing cache entry: {key}")

        # 计算向量
        query_vector = self._compute_query_vector(query)

        # 创建缓存条目
        entry = SemanticCacheEntry(
            query=query,
            response=response,
            query_vector=query_vector,
            ttl_seconds=ttl or self.default_ttl
        )

        # 检查容量
        if len(self._cache) >= self.max_size:
            # LRU 淘汰：删除最久未使用的条目
            self._evict_lru()

        # 存储
        self._cache[key] = entry
        self._vectors[key] = query_vector

        logger.debug(f"Semantic cache SET: key={key[:16]}...")

    def _remove_entry(self, key: str):
        """删除缓存条目"""
        if key in self._cache:
            del self._cache[key]
        if key in self._vectors:
            del self._vectors[key]

    def _evict_lru(self):
        """淘汰最久未使用的条目（LRU）"""
        if self._cache:
            # OrderedDict 的第一个元素是最久未使用的
            oldest_key = next(iter(self._cache))
            self._remove_entry(oldest_key)
            logger.debug(f"Evicted LRU entry: {oldest_key[:16]}...")

    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total_entries = len(self._cache)
        total_accesses = sum(e.access_count for e in self._cache.values())
        expired_entries = sum(1 for e in self._cache.values() if e.is_expired())

        return {
            "total_entries": total_entries,
            "total_accesses": total_accesses,
            "expired_entries": expired_entries,
            "max_size": self.max_size,
            "utilization": total_entries / self.max_size if self.max_size > 0 else 0,
            "similarity_threshold": self.similarity_threshold,
            "default_ttl": self.default_ttl
        }

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._vectors.clear()
        logger.info("Semantic cache cleared")


# 装饰器：带语义缓存的异步函数
def semantic_cache_decorator(
    cache: SemanticCache,
    query_extractor: callable = None,
    context_extractor: callable = None,
    ttl: Optional[int] = None
):
    """
    语义缓存装饰器

    用法:
        @semantic_cache_decorator(cache=my_cache)
        async def my_llm_function(query: str, **kwargs):
            return await call_llm(query, **kwargs)

    Args:
        cache: 语义缓存实例
        query_extractor: 从函数参数提取查询字符串的函数
        context_extractor: 从函数参数提取上下文的函数
        ttl: 缓存过期时间
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 提取查询和上下文
            if query_extractor:
                query = query_extractor(*args, **kwargs)
            else:
                # 默认：第一个参数作为查询
                query = args[0] if args else kwargs.get('query', '')

            if context_extractor:
                context = context_extractor(*args, **kwargs)
            else:
                context = kwargs

            # 尝试命中缓存
            cached = await cache.get(query, context)
            if cached is not None:
                return cached

            # 调用原函数
            result = await func(*args, **kwargs)

            # 写入缓存
            await cache.set(query, result, context, ttl)

            return result
        return wrapper
    return decorator


# 全局单例实例
semantic_cache = SemanticCache(
    max_size=10000,
    similarity_threshold=0.95,
    default_ttl=3600
)
