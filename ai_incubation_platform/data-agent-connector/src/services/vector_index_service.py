"""
向量索引服务

实现：
1. 文本和 Schema 的向量嵌入
2. 向量索引的创建和管理
3. 向量相似度搜索
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import db_manager
from config.vector_settings import vector_settings
from core.embedding_engine import embedding_engine
from core.retrieval_engine import retrieval_engine
from models.vector_index import VectorIndexModel, VectorCollectionModel, VectorSearchHistoryModel, VectorSchemaInfoModel
from utils.logger import logger


class VectorIndexService:
    """向量索引服务"""

    def __init__(self):
        self._initialized = False

    async def initialize(self):
        """初始化服务"""
        await embedding_engine.initialize()
        await retrieval_engine.initialize()
        self._initialized = True
        logger.info("Vector index service initialized")

    async def close(self):
        """关闭服务"""
        await embedding_engine.close()
        await retrieval_engine.close()
        self._initialized = False

    def _compute_content_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()

    # ==================== 嵌入生成 ====================

    async def embed_text(self, text: str) -> List[float]:
        """
        生成文本向量

        Args:
            text: 输入文本

        Returns:
            向量嵌入列表
        """
        if not self._initialized:
            logger.warning("Vector index service not initialized")
            return [0.0] * vector_settings.embedding_dimension

        return await embedding_engine.embed_text(text)

    async def embed_queries(self, queries: List[str]) -> List[List[float]]:
        """批量生成查询向量"""
        if not self._initialized:
            return [[0.0] * vector_settings.embedding_dimension] * len(queries)

        return await embedding_engine.embed_batch(queries)

    # ==================== 索引创建 ====================

    async def index_document(
        self,
        collection: str,
        content: str,
        metadata: Dict[str, Any] = None,
        datasource: str = None,
        table_name: str = None,
        created_by: str = None
    ) -> str:
        """
        索引文档

        Args:
            collection: 集合名称
            content: 文档内容
            metadata: 元数据
            datasource: 数据源名称
            table_name: 表名
            created_by: 创建者

        Returns:
            索引 ID
        """
        if not self._initialized:
            logger.warning("Vector index service not initialized")
            return None

        # 生成 ID 和哈希
        content_hash = self._compute_content_hash(content)
        doc_id = f"{collection}_{content_hash[:16]}"

        # 生成嵌入
        embedding = await embedding_engine.embed_text(content)

        # 添加到 ChromaDB
        await retrieval_engine.add_document(
            collection=collection,
            id=doc_id,
            embedding=embedding,
            content=content,
            metadata=metadata or {}
        )

        # 持久化到数据库
        async with db_manager.get_async_session() as session:
            # 检查是否已存在
            existing = await session.execute(
                select(VectorIndexModel).where(VectorIndexModel.content_hash == content_hash)
            )
            if existing.scalar_one_or_none():
                logger.debug(f"Document already indexed: {doc_id}")
                return doc_id

            # 创建新记录
            index = VectorIndexModel(
                id=doc_id,
                collection=collection,
                content=content,
                content_hash=content_hash,
                metadata_json=metadata,
                datasource=datasource,
                table_name=table_name,
                index_type="content",
                created_by=created_by
            )
            session.add(index)
            await session.flush()

            # 更新集合统计
            await self._update_collection_stats(collection, session)

        logger.info(f"Indexed document: {doc_id}")
        return doc_id

    async def index_table_schema(
        self,
        datasource: str,
        table_name: str,
        schema_info: Dict[str, Any],
        created_by: str = None
    ) -> str:
        """
        索引表 Schema 信息

        Args:
            datasource: 数据源名称
            table_name: 表名
            schema_info: Schema 信息，包含 columns, description 等
            created_by: 创建者

        Returns:
            索引 ID
        """
        if not self._initialized:
            return None

        collection = "schema_tables"

        # 构建 Schema 描述文本
        description = schema_info.get("description", "")
        columns = schema_info.get("columns", [])

        # 构建用于嵌入的文本
        schema_text = f"""
表名：{datasource}.{table_name}
描述：{description}
列信息：
{json.dumps(columns, ensure_ascii=False, indent=2)}
""".strip()

        content_hash = self._compute_content_hash(schema_text)
        doc_id = f"schema_{datasource}_{table_name}_{content_hash[:8]}"

        # 生成嵌入
        embedding = await embedding_engine.embed_text(schema_text)

        # 添加到 ChromaDB
        metadata = {
            "datasource": datasource,
            "table_name": table_name,
            "schema_type": "table",
            **schema_info.get("metadata", {})
        }

        await retrieval_engine.add_document(
            collection=collection,
            id=doc_id,
            embedding=embedding,
            content=schema_text,
            metadata=metadata
        )

        # 索引每个列的描述
        for col in columns:
            col_name = col.get("name", "")
            col_desc = col.get("description", "")
            if col_desc:
                col_text = f"表：{table_name}\n列：{col_name}\n描述：{col_desc}"
                col_id = f"schema_{datasource}_{table_name}_{col_name}"
                col_embedding = await embedding_engine.embed_text(col_text)

                await retrieval_engine.add_document(
                    collection="schema_columns",
                    id=col_id,
                    embedding=col_embedding,
                    content=col_text,
                    metadata={
                        "datasource": datasource,
                        "table_name": table_name,
                        "column_name": col_name,
                        "schema_type": "column"
                    }
                )

        # 持久化到数据库
        async with db_manager.get_async_session() as session:
            # 保存 Schema 信息
            schema_record = VectorSchemaInfoModel(
                datasource=datasource,
                table_name=table_name,
                schema_description=json.dumps(schema_info, ensure_ascii=False),
                sample_values=schema_info.get("sample_values", []),
                data_type="table",
                is_nullable=False
            )
            session.add(schema_record)

            # 保存索引记录
            index = VectorIndexModel(
                id=doc_id,
                collection=collection,
                content=schema_text,
                content_hash=content_hash,
                metadata_json=schema_info,
                datasource=datasource,
                table_name=table_name,
                index_type="schema",
                created_by=created_by
            )
            session.add(index)

        logger.info(f"Indexed schema: {datasource}.{table_name}")
        return doc_id

    async def index_query_history(
        self,
        query: str,
        result_summary: str = "",
        metadata: Dict[str, Any] = None,
        user_id: str = None
    ) -> str:
        """
        索引查询历史

        Args:
            query: SQL 查询或自然语言查询
            result_summary: 结果摘要
            metadata: 元数据
            user_id: 用户 ID

        Returns:
            索引 ID
        """
        if not self._initialized:
            return None

        collection = "query_history"

        # 构建索引内容
        content = f"""查询：{query}
结果摘要：{result_summary}
""".strip()

        content_hash = self._compute_content_hash(content)
        doc_id = f"query_{content_hash[:16]}"

        # 生成嵌入
        embedding = await embedding_engine.embed_text(content)

        # 添加到 ChromaDB
        await retrieval_engine.add_document(
            collection=collection,
            id=doc_id,
            embedding=embedding,
            content=content,
            metadata=metadata or {}
        )

        # 记录搜索历史
        async with db_manager.get_async_session() as session:
            history = VectorSearchHistoryModel(
                query_text=query,
                query_embedding_hash=content_hash,
                collection=collection,
                search_filters=metadata,
                limit=1,
                result_count=1,
                user_id=user_id
            )
            session.add(history)

        return doc_id

    # ==================== 索引删除 ====================

    async def delete_index(self, collection: str, id: str) -> bool:
        """删除索引"""
        if not self._initialized:
            return False

        # 从 ChromaDB 删除
        success = await retrieval_engine.delete_document(collection, id)

        # 从数据库删除
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(VectorIndexModel).where(
                    and_(
                        VectorIndexModel.collection == collection,
                        VectorIndexModel.id == id
                    )
                )
            )
            index = result.scalar_one_or_none()
            if index:
                await session.delete(index)

        logger.info(f"Deleted index: {collection}/{id}")
        return success

    # ==================== 集合管理 ====================

    async def list_collections(self) -> List[Dict[str, Any]]:
        """列出所有集合"""
        if not self._initialized:
            return []

        # 从 ChromaDB 获取
        chroma_collections = await retrieval_engine.list_collections()

        # 从数据库获取统计
        async with db_manager.get_async_session() as session:
            result = await session.execute(select(VectorCollectionModel))
            db_collections = result.scalars().all()

        # 合并信息
        collections = []
        for name in chroma_collections:
            stats = await retrieval_engine.get_collection_stats(name)
            collections.append({
                "name": name,
                **stats
            })

        return collections

    async def _update_collection_stats(self, collection: str, session: AsyncSession):
        """更新集合统计信息"""
        result = await session.execute(
            select(VectorIndexModel).where(VectorIndexModel.collection == collection)
        )
        indexes = result.scalars().all()

        # 更新或创建集合记录
        coll_record = await session.execute(
            select(VectorCollectionModel).where(VectorCollectionModel.name == collection)
        )
        coll = coll_record.scalar_one_or_none()

        if not coll:
            coll = VectorCollectionModel(name=collection)

        coll.total_vectors = len(indexes)
        session.add(coll)

    # ==================== 搜索 ====================

    async def search_similar(
        self,
        collection: str,
        query: str,
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档

        Args:
            collection: 集合名称
            query: 查询文本
            limit: 返回数量
            filters: 过滤条件

        Returns:
            相似文档列表
        """
        if not self._initialized:
            return []

        # 生成查询向量
        query_embedding = await embedding_engine.embed_text(query)

        # 搜索
        results = await retrieval_engine.search_similar(
            collection=collection,
            query_embedding=query_embedding,
            limit=limit,
            filters=filters
        )

        # 记录搜索历史
        async with db_manager.get_async_session() as session:
            history = VectorSearchHistoryModel(
                query_text=query,
                query_embedding_hash=self._compute_content_hash(query),
                collection=collection,
                search_filters=filters,
                limit=limit,
                result_count=len(results),
                execution_time_ms=0  # TODO: 记录耗时
            )
            session.add(history)

        return results

    async def get_embedding_cache_stats(self) -> Dict[str, Any]:
        """获取嵌入缓存统计"""
        return embedding_engine.get_cache_stats()

    async def clear_embedding_cache(self):
        """清除嵌入缓存"""
        await embedding_engine.clear_cache()


# 全局向量索引服务实例
vector_index_service = VectorIndexService()
