"""
嵌入引擎

实现文本向量化功能，支持：
- 远程 API 嵌入 (Anthropic, OpenAI)
- 本地模型嵌入 (sentence-transformers)
- 嵌入缓存
"""
import hashlib
import asyncio
from typing import List, Optional, Dict, Any
from functools import lru_cache
import aiohttp
from datetime import datetime

from config.vector_settings import vector_settings
from utils.logger import logger


class EmbeddingEngine:
    """嵌入引擎"""

    def __init__(self):
        self._cache: Dict[str, List[float]] = {}
        self._cache_stats = {"hits": 0, "misses": 0}
        self._session: Optional[aiohttp.ClientSession] = None
        self._local_model = None

    async def initialize(self):
        """初始化嵌入引擎"""
        if vector_settings.use_remote_embedding:
            self._session = aiohttp.ClientSession()
            logger.info("Initialized remote embedding engine")
        elif vector_settings.use_local_embedding:
            await self._load_local_model()
            logger.info("Initialized local embedding engine")
        else:
            logger.warning("No embedding engine configured")

    async def close(self):
        """关闭嵌入引擎"""
        if self._session:
            await self._session.close()
        if self._local_model:
            del self._local_model
            self._local_model = None

    async def _load_local_model(self):
        """加载本地嵌入模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(vector_settings.local_embedding_model)
            logger.info(f"Loaded local embedding model: {vector_settings.local_embedding_model}")
        except ImportError:
            logger.warning("sentence-transformers not installed, falling back to remote API")
            vector_settings.use_remote_embedding = True
            await self.initialize()

    def _compute_content_hash(self, text: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(text.encode()).hexdigest()

    async def embed_text(self, text: str) -> List[float]:
        """
        生成文本向量

        Args:
            text: 输入文本

        Returns:
            向量嵌入列表
        """
        if not text or not text.strip():
            return [0.0] * vector_settings.embedding_dimension

        # 检查缓存
        if vector_settings.enable_embedding_cache:
            content_hash = self._compute_content_hash(text)
            if content_hash in self._cache:
                self._cache_stats["hits"] += 1
                logger.debug(f"Embedding cache hit for: {text[:50]}...")
                return self._cache[content_hash]
            self._cache_stats["misses"] += 1

        # 生成嵌入
        if vector_settings.use_remote_embedding and self._session:
            embedding = await self._embed_remote(text)
        elif self._local_model:
            embedding = await self._embed_local(text)
        else:
            # 降级：返回零向量
            logger.warning("No embedding engine available, returning zero vector")
            embedding = [0.0] * vector_settings.embedding_dimension

        # 缓存结果
        if vector_settings.enable_embedding_cache:
            if len(self._cache) >= vector_settings.embedding_cache_size:
                # 清除一半缓存
                keys_to_remove = list(self._cache.keys())[:len(self._cache) // 2]
                for key in keys_to_remove:
                    del self._cache[key]
            self._cache[content_hash] = embedding

        return embedding

    async def _embed_remote(self, text: str) -> List[float]:
        """使用远程 API 生成嵌入"""
        try:
            # 支持 OpenAI 兼容的 API
            url = vector_settings.remote_embedding_url or "https://api.openai.com/v1/embeddings"
            api_key = vector_settings.remote_embedding_api_key or ""

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            payload = {
                "input": text,
                "model": vector_settings.embedding_model
            }

            async with self._session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Embedding API error: {response.status} - {error_text}")
                    raise ValueError(f"Embedding API error: {response.status}")

                result = await response.json()
                embedding = result["data"][0]["embedding"]

                # 确保维度正确
                if len(embedding) != vector_settings.embedding_dimension:
                    logger.warning(f"Embedding dimension mismatch: expected {vector_settings.embedding_dimension}, got {len(embedding)}")

                return embedding

        except Exception as e:
            logger.error(f"Remote embedding failed: {e}")
            # 降级到本地模型
            if self._local_model:
                return await self._embed_local(text)
            raise

    async def _embed_local(self, text: str) -> List[float]:
        """使用本地模型生成嵌入"""
        try:
            import numpy as np
            from concurrent.futures import ThreadPoolExecutor

            def _embed():
                embedding = self._local_model.encode([text], convert_to_numpy=True)
                return embedding[0].tolist()

            # 在线程池中运行以避免阻塞
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                embedding = await loop.run_in_executor(executor, _embed)

            return embedding

        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成嵌入

        Args:
            texts: 文本列表

        Returns:
            嵌入列表
        """
        if not texts:
            return []

        # 分批处理
        batch_size = vector_settings.embedding_batch_size
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            tasks = [self.embed_text(text) for text in batch]
            batch_embeddings = await asyncio.gather(*tasks)
            results.extend(batch_embeddings)

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = self._cache_stats["hits"] / total if total > 0 else 0
        return {
            "cache_size": len(self._cache),
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "hit_rate": round(hit_rate, 4)
        }

    async def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        self._cache_stats = {"hits": 0, "misses": 0}
        logger.info("Embedding cache cleared")


# 全局嵌入引擎实例
embedding_engine = EmbeddingEngine()
