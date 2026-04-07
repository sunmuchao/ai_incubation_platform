"""
LlamaIndex ChromaVectorStore 实现
使用 LlamaIndex 框架包装 ChromaDB，提供更强大的检索和索引能力
"""
from typing import Any, Dict, List, Optional, Union
import uuid
from pathlib import Path

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode, Document, BaseNode
from llama_index.vector_stores.chroma import ChromaVectorStore as LlamaChromaVectorStore
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core import Settings

# 本地导入
from ..base import BaseVectorStore, CodeChunk


class LlamaIndexVectorStore(BaseVectorStore):
    """
    LlamaIndex 向量存储实现
    特点：
    - 基于 LlamaIndex 框架，提供更强大的检索能力
    - 使用 ChromaDB 作为底层存储
    - 支持高级检索策略（Hybrid Search, Fusion 等）
    - 与 LlamaIndex 生态系统无缝集成
    - 支持多种文档变换器和节点解析器
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.persist_directory = self.config.get('persist_directory', './data/chroma')
        self.collection_name = self.config.get('collection_name', 'code_index')

        # LlamaIndex 核心组件
        self.vector_store = None  # LlamaChromaVectorStore
        self.storage_context = None
        self.index = None
        self.retriever = None

        # 内部集合映射（兼容原有接口）
        self.collections = {}

    def connect(self, config: Dict[str, Any]) -> None:
        """连接到 LlamaIndex + Chroma 实例"""
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        # 创建底层 Chroma 客户端
        chroma_client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=self.config.get('allow_reset', False)
            )
        )

        # 创建 LlamaIndex ChromaVectorStore
        self.vector_store = LlamaChromaVectorStore(
            chroma_collection=chroma_client.get_or_create_collection(self.collection_name)
        )

        # 创建存储上下文
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )

        # 创建索引（如果已有数据则加载）
        try:
            self.index = VectorStoreIndex.from_vector_store(
                self.vector_store,
                storage_context=self.storage_context
            )
        except Exception:
            # 空索引
            self.index = VectorStoreIndex(
                nodes=[],
                storage_context=self.storage_context
            )

    def create_collection(self, collection_name: str, dimension: int) -> None:
        """创建集合"""
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        chroma_client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        collection = chroma_client.get_or_create_collection(collection_name)
        self.collections[collection_name] = collection

        # 更新 vector store 和 index
        self.vector_store = LlamaChromaVectorStore(chroma_collection=collection)
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context
        )

    def _get_collection(self, collection_name: str):
        """获取集合实例"""
        if collection_name not in self.collections:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self.collections[collection_name] = chroma_client.get_collection(collection_name)
        return self.collections[collection_name]

    def upsert_chunks(self, collection_name: str, chunks: List[CodeChunk]) -> int:
        """插入或更新代码块 - 使用 LlamaIndex 节点"""
        collection = self._get_collection(collection_name)

        # 转换为 LlamaIndex 节点
        nodes = []
        for chunk in chunks:
            if not chunk.embedding:
                continue

            # 创建 TextNode
            node = TextNode(
                id_=chunk.chunk_id,
                text=chunk.content,
                embedding=chunk.embedding,
                metadata={
                    "file_path": chunk.file_path,
                    "language": chunk.language,
                    "chunk_type": chunk.chunk_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "symbols": ",".join(chunk.symbols) if chunk.symbols else "",
                    **chunk.metadata
                }
            )
            nodes.append(node)

        if not nodes:
            return 0

        # 使用 LlamaIndex 插入
        self.index.insert_nodes(nodes)
        return len(nodes)

    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[CodeChunk]:
        """语义搜索代码块 - 使用 LlamaIndex Retriever"""
        # 切换到指定集合
        collection = self._get_collection(collection_name)
        self.vector_store = LlamaChromaVectorStore(chroma_collection=collection)
        self.index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context
        )

        # 创建检索器
        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=top_k,
        )

        # 创建带 embedding 的查询节点
        query_node = TextNode(
            text="",  # 不需要 text，因为我们已经有 embedding
            embedding=query_embedding
        )

        # 执行检索
        try:
            nodes_with_scores = retriever.retrieve(query_node)
        except Exception:
            # 回退到直接查询 Chroma
            return self._fallback_search(collection_name, query_embedding, top_k, filters)

        # 转换为 CodeChunk 列表
        chunks = []
        for node_with_score in nodes_with_scores:
            node = node_with_score.node
            metadata = node.metadata or {}
            symbols = metadata.get('symbols', '')
            if symbols:
                symbols = symbols.split(',')

            chunk = CodeChunk(
                file_path=metadata.get('file_path', ''),
                language=metadata.get('language', ''),
                content=node.text,
                start_line=int(metadata.get('start_line', 0)),
                end_line=int(metadata.get('end_line', 0)),
                chunk_type=metadata.get('chunk_type', 'code'),
                symbols=symbols if symbols else [],
                metadata={
                    **metadata,
                    'similarity': node_with_score.score if node_with_score.score else 0.0
                },
                embedding=None
            )
            chunks.append(chunk)

        return chunks

    def _fallback_search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[CodeChunk]:
        """回退到直接 Chroma 查询"""
        collection = self._get_collection(collection_name)

        # 转换过滤条件
        where_filter = self._build_chroma_filter(filters) if filters else None

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["metadatas", "documents", "distances"]
        )

        chunks = []
        for i in range(len(results['ids'][0])):
            chunk_id = results['ids'][0][i]
            metadata = results['metadatas'][0][i]
            content = results['documents'][0][i]
            distance = results['distances'][0][i]

            symbols = metadata.pop('symbols', '').split(',') if metadata.get('symbols') else []

            chunk = CodeChunk(
                file_path=metadata.pop('file_path', ''),
                language=metadata.pop('language', ''),
                content=content,
                start_line=int(metadata.pop('start_line', 0)),
                end_line=int(metadata.pop('end_line', 0)),
                chunk_type=metadata.pop('chunk_type', 'code'),
                symbols=symbols,
                metadata=metadata,
                embedding=None
            )
            chunk.chunk_id = chunk_id
            similarity = max(0.0, min(1.0, 1 - float(distance)))
            chunk.metadata['similarity'] = similarity
            chunks.append(chunk)

        return chunks

    def delete_by_file(self, collection_name: str, file_path: str) -> int:
        """删除指定文件的所有块"""
        collection = self._get_collection(collection_name)

        # 先查询该文件的所有块
        results = collection.get(
            where={"file_path": file_path},
        )

        if not results['ids']:
            return 0

        # 批量删除
        collection.delete(ids=results['ids'])
        return len(results['ids'])

    def _build_chroma_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """构建 Chroma 支持的过滤条件"""
        chroma_filter = {}

        for key, value in filters.items():
            if isinstance(value, dict):
                op = list(value.keys())[0]
                val = value[op]
                if op == '$eq':
                    chroma_filter[key] = val
                elif op == '$ne':
                    chroma_filter[key] = {"$ne": val}
                elif op == '$gt':
                    chroma_filter[key] = {"$gt": val}
                elif op == '$gte':
                    chroma_filter[key] = {"$gte": val}
                elif op == '$lt':
                    chroma_filter[key] = {"$lt": val}
                elif op == '$lte':
                    chroma_filter[key] = {"$lte": val}
                elif op == '$in':
                    chroma_filter[key] = {"$in": val}
                elif op == '$nin':
                    chroma_filter[key] = {"$nin": val}
                elif op == '$contains':
                    chroma_filter[key] = {"$contains": val}
            else:
                chroma_filter[key] = value

        return chroma_filter

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """获取集合统计信息"""
        collection = self._get_collection(collection_name)
        count = collection.count()
        return {
            "total_chunks": count,
            "collection_name": collection_name
        }

    def list_collections(self) -> List[str]:
        """列出所有集合"""
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        chroma_client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        return [col.name for col in chroma_client.list_collections()]

    # ========== LlamaIndex 高级方法 ==========

    def get_retriever(
        self,
        similarity_top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> VectorIndexRetriever:
        """获取 LlamaIndex 检索器"""
        return VectorIndexRetriever(
            index=self.index,
            similarity_top_k=similarity_top_k,
        )

    def as_query_engine(self, **kwargs):
        """转换为 LlamaIndex 查询引擎"""
        return self.index.as_query_engine(**kwargs)
