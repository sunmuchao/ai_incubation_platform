"""
检索引擎 - LlamaIndex 版本

实现：
- 基于 LlamaIndex 的向量检索
- 使用 ChromaDB 作为底层向量存储
- 支持混合搜索（向量 + 关键字）
- 结果重排序
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
import numpy as np

from config.vector_settings import vector_settings
from utils.logger import logger

# 类型检查时的占位类型
if TYPE_CHECKING:
    try:
        import chromadb
    except ImportError:
        pass

    # LlamaIndex 类型占位符
    class VectorIndexRetriever:
        """Placeholder type for VectorIndexRetriever"""
        pass

    class VectorStoreIndex:
        """Placeholder type for VectorStoreIndex"""
        pass
else:
    VectorIndexRetriever = object
    VectorStoreIndex = object

try:
    # LlamaIndex imports
    from llama_index.core import VectorStoreIndex, StorageContext, Settings as LlamaSettings
    from llama_index.core.schema import TextNode
    from llama_index.vector_stores.chroma import ChromaVectorStore as LlamaChromaVectorStore
    from llama_index.core.retrievers import VectorIndexRetriever as LlamaVectorIndexRetriever
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    LlamaVectorIndexRetriever = None
    logger.warning("LlamaIndex not installed, using fallback retrieval")

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not installed, vector search will be limited")


class RetrievalEngine:
    """检索引擎 - 基于 LlamaIndex"""

    def __init__(self):
        self._client = None
        self._collections: Dict[str, Any] = {}  # 存储 LlamaIndex 索引
        self._vector_stores: Dict[str, Any] = {}  # 存储 VectorStore
        self._initialized = False

    async def initialize(self):
        """初始化检索引擎"""
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available, using in-memory retrieval")
            self._initialized = False
            return

        if not LLAMAINDEX_AVAILABLE:
            logger.warning("LlamaIndex not available, using basic retrieval")
            self._initialized = False
            return

        try:
            # 初始化 ChromaDB 客户端
            self._client = chromadb.PersistentClient(
                path=vector_settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False
                )
            )
            self._initialized = True
            logger.info(f"Initialized ChromaDB at {vector_settings.chroma_persist_directory}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._initialized = False

    async def close(self):
        """关闭检索引擎"""
        if self._client:
            # LlamaIndex 不需要显式持久化，ChromaDB 会自动保存
            logger.info("Retrieval engine closed")

    def _get_or_create_collection(self, name: str, dimension: int = 1536) -> Tuple[Any, Any]:
        """获取或创建集合，返回 (chroma_collection, llama_index)"""
        if name not in self._collections:
            try:
                # 获取或创建 Chroma collection
                chroma_collection = self._client.get_or_create_collection(
                    name=name,
                    metadata={"description": f"Collection for {name}"}
                )

                # 创建 LlamaIndex ChromaVectorStore
                vector_store = LlamaChromaVectorStore(chroma_collection=chroma_collection)

                # 创建存储上下文
                storage_context = StorageContext.from_defaults(vector_store=vector_store)

                # 创建或加载索引
                try:
                    index = VectorStoreIndex.from_vector_store(
                        vector_store,
                        storage_context=storage_context
                    )
                except Exception:
                    # 空索引
                    index = VectorStoreIndex(nodes=[], storage_context=storage_context)

                self._collections[name] = index
                self._vector_stores[name] = vector_store

                logger.info(f"Created collection: {name}")
            except Exception as e:
                logger.error(f"Failed to create collection {name}: {e}")
                raise
        return self._client.get_collection(name), self._collections[name]

    async def add_document(
        self,
        collection: str,
        id: str,
        embedding: List[float],
        content: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        添加文档到集合 - 使用 LlamaIndex 节点

        Args:
            collection: 集合名称
            id: 文档 ID
            embedding: 向量嵌入
            content: 原始内容
            metadata: 元数据

        Returns:
            是否成功
        """
        if not self._initialized:
            logger.warning("Retrieval engine not initialized")
            return False

        try:
            _, index = self._get_or_create_collection(collection)

            # 创建 LlamaIndex TextNode
            node = TextNode(
                id_=id,
                text=content,
                embedding=embedding,
                metadata=metadata or {}
            )

            # 插入节点
            index.insert_node(node)
            return True
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False

    async def add_documents_batch(
        self,
        collection: str,
        documents: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        批量添加文档

        Args:
            collection: 集合名称
            documents: 文档列表，每项包含 id, embedding, content, metadata

        Returns:
            (成功数，失败数)
        """
        if not self._initialized:
            return 0, len(documents)

        try:
            _, index = self._get_or_create_collection(collection)

            # 创建节点列表
            nodes = []
            for doc in documents:
                node = TextNode(
                    id_=doc["id"],
                    text=doc["content"],
                    embedding=doc["embedding"],
                    metadata=doc.get("metadata", {})
                )
                nodes.append(node)

            # 批量插入
            index.insert_nodes(nodes)
            return len(documents), 0
        except Exception as e:
            logger.error(f"Batch add failed: {e}")
            return 0, len(documents)

    async def search_similar(
        self,
        collection: str,
        query_embedding: List[float],
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档 - 使用 LlamaIndex Retriever

        Args:
            collection: 集合名称
            query_embedding: 查询向量
            limit: 返回数量
            filters: 过滤条件

        Returns:
            相似文档列表
        """
        if not self._initialized:
            logger.warning("Retrieval engine not initialized")
            return []

        if not LLAMAINDEX_AVAILABLE:
            logger.warning("LlamaIndex not available, using fallback search")
            return self._fallback_search(collection, query_embedding, limit, filters)

        try:
            chroma_collection, index = self._get_or_create_collection(collection)

            # 创建检索器
            retriever = LlamaVectorIndexRetriever(
                index=index,
                similarity_top_k=limit,
            )

            # 创建查询节点（只有 embedding，没有 text）
            query_node = TextNode(
                text="",
                embedding=query_embedding
            )

            # 执行检索
            nodes_with_scores = retriever.retrieve(query_node)

            # 格式化结果
            results = []
            for node_with_score in nodes_with_scores:
                node = node_with_score.node
                item = {
                    "id": node.id_,
                    "content": node.text,
                    "metadata": node.metadata or {},
                    "similarity": node_with_score.score if node_with_score.score else 0.0
                }
                results.append(item)

            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # 回退到直接 Chroma 查询
            return self._fallback_search(collection, query_embedding, limit, filters)

    def _fallback_search(
        self,
        collection: str,
        query_embedding: List[float],
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """回退到直接 Chroma 查询"""
        try:
            chroma_collection = self._client.get_collection(collection)

            # 构建 where 条件
            where = self._build_where_clause(filters) if filters else None

            results = chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            return self._format_chroma_results(results)
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []

    def _build_where_clause(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """构建 where 子句"""
        if not filters:
            return None

        conditions = []
        for key, value in filters.items():
            if isinstance(value, dict):
                for op, val in value.items():
                    conditions.append({key: {op: val}})
            else:
                conditions.append({key: value})

        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _format_chroma_results(self, results: dict) -> List[Dict[str, Any]]:
        """格式化 Chroma 搜索结果"""
        if not results or not results.get("ids"):
            return []

        formatted = []
        for i, id in enumerate(results["ids"][0]):
            item = {
                "id": id,
                "content": results["documents"][0][i] if results.get("documents") else None,
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else None,
                "similarity": 1 - (results["distances"][0][i] / 2) if results.get("distances") else 1.0
            }
            formatted.append(item)

        return formatted

    def _format_results(self, results: dict) -> List[Dict[str, Any]]:
        """格式化搜索结果（兼容旧接口）"""
        return self._format_chroma_results(results)

    async def delete_document(self, collection: str, id: str) -> bool:
        """删除文档"""
        if not self._initialized:
            return False

        try:
            chroma_collection = self._client.get_collection(collection)
            chroma_collection.delete(ids=[id])
            return True
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    async def list_collections(self) -> List[str]:
        """列出所有集合"""
        if not self._initialized:
            return []

        try:
            return [coll.name for coll in self._client.list_collections()]
        except Exception as e:
            logger.error(f"List collections failed: {e}")
            return []

    async def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        """获取集合统计信息"""
        if not self._initialized:
            return {}

        try:
            chroma_collection = self._client.get_collection(collection)
            count = chroma_collection.count()
            return {
                "name": collection,
                "count": count,
                "metadata": getattr(chroma_collection, "metadata", {})
            }
        except Exception as e:
            logger.error(f"Get stats failed: {e}")
            return {}

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算余弦相似度"""
        v1 = np.array(embedding1)
        v2 = np.array(embedding2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    async def rerank_results(
        self,
        results: List[Dict[str, Any]],
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """重排序结果"""
        # 添加相似度分数
        for result in results:
            if "similarity" not in result:
                result["similarity"] = self.compute_similarity(
                    query_embedding,
                    result.get("embedding", [0] * len(query_embedding))
                )

        # 按相似度排序
        sorted_results = sorted(results, key=lambda x: x.get("similarity", 0), reverse=True)
        return sorted_results[:top_k]

    # ========== LlamaIndex 高级方法 ==========

    def get_retriever(self, collection: str, similarity_top_k: int = 10) -> Any:
        """获取 LlamaIndex 检索器"""
        if collection not in self._collections:
            raise ValueError(f"Collection {collection} not found")
        if not LLAMAINDEX_AVAILABLE:
            raise RuntimeError("LlamaIndex not available")
        return LlamaVectorIndexRetriever(
            index=self._collections[collection],
            similarity_top_k=similarity_top_k,
        )

    def as_query_engine(self, collection: str, **kwargs):
        """转换为 LlamaIndex 查询引擎"""
        if collection not in self._collections:
            raise ValueError(f"Collection {collection} not found")
        return self._collections[collection].as_query_engine(**kwargs)


# 全局检索引擎实例
retrieval_engine = RetrievalEngine()
