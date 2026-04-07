"""
语义搜索服务

实现：
1. 表语义搜索
2. 列语义搜索
3. 查询历史搜索
4. 混合搜索（向量 + 关键字）
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re

from sqlalchemy import select, desc, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import db_manager
from config.vector_settings import vector_settings
from services.vector_index_service import vector_index_service
from models.vector_index import VectorIndexModel, VectorSchemaInfoModel, VectorSearchHistoryModel
from utils.logger import logger


class SemanticSearchService:
    """语义搜索服务"""

    def __init__(self):
        self._initialized = False

    async def initialize(self):
        """初始化服务"""
        await vector_index_service.initialize()
        self._initialized = True
        logger.info("Semantic search service initialized")

    async def close(self):
        """关闭服务"""
        await vector_index_service.close()
        self._initialized = False

    # ==================== 表搜索 ====================

    async def search_tables(
        self,
        query: str,
        datasource: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索相关表

        Args:
            query: 查询文本
            datasource: 数据源过滤
            limit: 返回数量

        Returns:
            表列表
        """
        if not self._initialized:
            return []

        # 使用向量搜索
        filters = {}
        if datasource:
            filters["datasource"] = datasource

        results = await vector_index_service.search_similar(
            collection="schema_tables",
            query=query,
            limit=limit,
            filters=filters
        )

        # 格式化结果
        tables = []
        for result in results:
            metadata = result.get("metadata", {})
            tables.append({
                "id": result["id"],
                "datasource": metadata.get("datasource"),
                "table_name": metadata.get("table_name"),
                "description": metadata.get("description", ""),
                "similarity": result.get("similarity", 0),
                "content": result.get("content", "")
            })

        # 如果没有向量搜索结果，尝试关键字搜索
        if not tables:
            tables = await self._keyword_search_tables(query, datasource, limit)

        logger.info(f"Semantic search tables: {query} -> {len(tables)} results")
        return tables

    async def _keyword_search_tables(
        self,
        query: str,
        datasource: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """关键字搜索表（降级方案）"""
        async with db_manager.get_async_session() as session:
            # 构建查询条件
            conditions = [VectorIndexModel.index_type == "schema"]
            if datasource:
                conditions.append(VectorIndexModel.datasource == datasource)

            # 使用 LIKE 进行模糊匹配
            query_lower = f"%{query.lower()}%"
            conditions.append(
                (VectorIndexModel.content.ilike(query_lower)) |
                (VectorIndexModel.table_name.ilike(query_lower))
            )

            result = await session.execute(
                select(VectorIndexModel)
                .where(and_(*conditions))
                .limit(limit)
            )
            indexes = result.scalars().all()

            return [
                {
                    "id": idx.id,
                    "datasource": idx.datasource,
                    "table_name": idx.table_name,
                    "description": idx.metadata_json.get("description", "") if idx.metadata_json else "",
                    "similarity": 0.5,  # 关键字搜索的默认相似度
                    "content": idx.content
                }
                for idx in indexes
            ]

    # ==================== 列搜索 ====================

    async def search_columns(
        self,
        query: str,
        table_name: Optional[str] = None,
        datasource: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索相关列

        Args:
            query: 查询文本
            table_name: 表名过滤
            datasource: 数据源过滤
            limit: 返回数量

        Returns:
            列列表
        """
        if not self._initialized:
            return []

        # 使用向量搜索
        filters = {}
        if table_name:
            filters["table_name"] = table_name
        if datasource:
            filters["datasource"] = datasource

        results = await vector_index_service.search_similar(
            collection="schema_columns",
            query=query,
            limit=limit,
            filters=filters
        )

        # 格式化结果
        columns = []
        for result in results:
            metadata = result.get("metadata", {})
            columns.append({
                "id": result["id"],
                "datasource": metadata.get("datasource"),
                "table_name": metadata.get("table_name"),
                "column_name": metadata.get("column_name"),
                "description": metadata.get("description", ""),
                "similarity": result.get("similarity", 0),
                "content": result.get("content", "")
            })

        # 如果没有向量搜索结果，尝试关键字搜索
        if not columns:
            columns = await self._keyword_search_columns(query, table_name, datasource, limit)

        logger.info(f"Semantic search columns: {query} -> {len(columns)} results")
        return columns

    async def _keyword_search_columns(
        self,
        query: str,
        table_name: Optional[str] = None,
        datasource: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """关键字搜索列（降级方案）"""
        async with db_manager.get_async_session() as session:
            # 从 Schema 信息中搜索
            query_lower = f"%{query.lower()}%"

            conditions = []
            if datasource:
                conditions.append(VectorSchemaInfoModel.datasource == datasource)
            if table_name:
                conditions.append(VectorSchemaInfoModel.table_name == table_name)

            # 搜索列名或描述
            conditions.append(
                (VectorSchemaInfoModel.column_name.ilike(query_lower)) |
                (VectorSchemaInfoModel.schema_description.ilike(query_lower))
            )

            result = await session.execute(
                select(VectorSchemaInfoModel)
                .where(and_(*conditions))
                .limit(limit)
            )
            schemas = result.scalars().all()

            return [
                {
                    "id": schema.id,
                    "datasource": schema.datasource,
                    "table_name": schema.table_name,
                    "column_name": schema.column_name,
                    "description": schema.schema_description[:200] if schema.schema_description else "",
                    "similarity": 0.5,
                    "content": f"{schema.table_name}.{schema.column_name}"
                }
                for schema in schemas
            ]

    # ==================== 查询历史搜索 ====================

    async def search_query_history(
        self,
        query: str,
        limit: int = 10,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索历史查询

        Args:
            query: 查询文本
            limit: 返回数量
            user_id: 用户 ID 过滤

        Returns:
            历史查询列表
        """
        if not self._initialized:
            return []

        # 使用向量搜索
        filters = {}
        if user_id:
            filters["user_id"] = user_id

        results = await vector_index_service.search_similar(
            collection="query_history",
            query=query,
            limit=limit,
            filters=filters
        )

        # 格式化结果
        history = []
        for result in results:
            metadata = result.get("metadata", {})
            history.append({
                "id": result["id"],
                "query": metadata.get("query", result.get("content", "")),
                "result_summary": metadata.get("result_summary", ""),
                "datasource": metadata.get("datasource"),
                "tables_involved": metadata.get("tables_involved", []),
                "similarity": result.get("similarity", 0),
                "executed_at": metadata.get("executed_at")
            })

        logger.info(f"Semantic search query history: {query} -> {len(history)} results")
        return history

    # ==================== 混合搜索 ====================

    async def hybrid_search(
        self,
        query: str,
        collections: Optional[List[str]] = None,
        filters: Dict[str, Any] = None,
        limit: int = 10,
        use_ai_rerank: bool = True
    ) -> List[Dict[str, Any]]:
        """
        混合搜索（跨多个集合）

        Args:
            query: 查询文本
            collections: 集合列表，默认为所有
            filters: 过滤条件
            limit: 返回数量
            use_ai_rerank: 是否使用 AI 重排序

        Returns:
            搜索结果
        """
        if not self._initialized:
            return []

        # 默认搜索所有集合
        if collections is None:
            collections = ["schema_tables", "schema_columns", "query_history"]

        # 并行搜索所有集合
        tasks = []
        for collection in collections:
            task = vector_index_service.search_similar(
                collection=collection,
                query=query,
                limit=limit * 2,  # 每个集合多取一些用于重排序
                filters=filters
            )
            tasks.append(task)

        results_lists = await asyncio.gather(*tasks)

        # 合并结果
        all_results = []
        for results in results_lists:
            all_results.extend(results)

        # 去重（基于 ID）
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result["id"] not in seen_ids:
                seen_ids.add(result["id"])
                unique_results.append(result)

        # 按相似度排序
        sorted_results = sorted(
            unique_results,
            key=lambda x: x.get("similarity", 0),
            reverse=True
        )

        # AI 重排序（可选）
        if use_ai_rerank and len(sorted_results) > limit:
            sorted_results = await self._ai_rerank(query, sorted_results, limit)

        logger.info(f"Hybrid search: {query} -> {len(sorted_results)} results")
        return sorted_results[:limit]

    async def _ai_rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """使用 AI 重排序结果"""
        # TODO: 集成 DeerFlow 进行 AI 重排序
        # 目前简单按相似度排序
        return results[:top_k]

    # ==================== 搜索建议 ====================

    async def get_search_suggestions(
        self,
        partial_query: str,
        limit: int = 5
    ) -> List[str]:
        """获取搜索建议"""
        if not self._initialized:
            return []

        async with db_manager.get_async_session() as session:
            # 从搜索历史中获取建议
            result = await session.execute(
                select(VectorSearchHistoryModel.query_text)
                .where(VectorSearchHistoryModel.query_text.ilike(f"%{partial_query}%"))
                .group_by(VectorSearchHistoryModel.query_text)
                .order_by(desc(func.count()))
                .limit(limit)
            )
            suggestions = result.scalars().all()

        return list(suggestions)

    async def record_search(
        self,
        query: str,
        collection: str,
        results: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ):
        """记录搜索行为"""
        async with db_manager.get_async_session() as session:
            history = VectorSearchHistoryModel(
                query_text=query,
                collection=collection,
                result_count=len(results),
                result_ids=[r["id"] for r in results],
                avg_similarity=sum(r.get("similarity", 0) for r in results) / len(results) if results else 0,
                user_id=user_id,
                execution_time_ms=0
            )
            session.add(history)


# 全局语义搜索服务实例
semantic_search_service = SemanticSearchService()
