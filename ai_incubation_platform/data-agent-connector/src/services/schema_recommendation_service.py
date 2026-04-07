"""
智能 Schema 推荐服务

实现：
1. 查询模式分析
2. 索引推荐
3. 分区推荐
4. 规范化推荐
5. 冗余检测
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import db_manager
from models.schema_recommendation import RecommendationModel, QueryPatternModel, IndexUsageModel
from models.vector_index import VectorSchemaInfoModel
from utils.logger import logger


class SchemaRecommendationService:
    """Schema 推荐服务"""

    def __init__(self):
        self._initialized = False

    async def initialize(self):
        """初始化服务"""
        self._initialized = True
        logger.info("Schema recommendation service initialized")

    async def close(self):
        """关闭服务"""
        self._initialized = False

    # ==================== 查询模式分析 ====================

    async def analyze_query_patterns(
        self,
        datasource: str,
        table_name: str,
        time_range: timedelta = timedelta(days=7)
    ) -> Dict[str, Any]:
        """
        分析查询模式

        Args:
            datasource: 数据源
            table_name: 表名
            time_range: 时间范围

        Returns:
            查询模式分析结果
        """
        async with db_manager.get_async_session() as session:
            # 获取查询历史（从血缘或审计日志）
            # 这里简化实现，实际应该从审计日志中分析

            # 获取已有的模式记录
            result = await session.execute(
                select(QueryPatternModel)
                .where(
                    and_(
                        QueryPatternModel.datasource == datasource,
                        QueryPatternModel.table_name == table_name,
                        QueryPatternModel.last_seen_at >= datetime.utcnow() - time_range
                    )
                )
                .order_by(desc(QueryPatternModel.frequency))
            )
            patterns = result.scalars().all()

            # 按类型分组
            patterns_by_type = defaultdict(list)
            for pattern in patterns:
                patterns_by_type[pattern.pattern_type].append(pattern.to_dict())

            return {
                "datasource": datasource,
                "table_name": table_name,
                "time_range_days": time_range.days,
                "total_patterns": len(patterns),
                "patterns_by_type": dict(patterns_by_type),
                "summary": {
                    "frequent_columns": len(patterns_by_type.get("frequent_column", [])),
                    "join_patterns": len(patterns_by_type.get("join_pattern", [])),
                    "filter_patterns": len(patterns_by_type.get("filter_pattern", [])),
                    "order_patterns": len(patterns_by_type.get("order_pattern", []))
                }
            }

    # ==================== 索引推荐 ====================

    async def recommend_indexes(
        self,
        datasource: str,
        table_name: str
    ) -> List[Dict[str, Any]]:
        """
        推荐索引

        Args:
            datasource: 数据源
            table_name: 表名

        Returns:
            索引推荐列表
        """
        recommendations = []

        try:
            # 分析查询模式，找出频繁用于过滤和连接的列
            patterns = await self.analyze_query_patterns(datasource, table_name)

            # 获取表结构信息
            async with db_manager.get_async_session() as session:
                result = await session.execute(
                    select(VectorSchemaInfoModel)
                    .where(
                        and_(
                            VectorSchemaInfoModel.datasource == datasource,
                            VectorSchemaInfoModel.table_name == table_name
                        )
                    )
                )
                schema_info = result.scalars().first()

            if schema_info:
                columns = schema_info.schema_description or {}

                # 基于查询模式推荐索引
                filter_patterns = patterns.get("patterns_by_type", {}).get("filter_pattern", [])
                for pattern in filter_patterns[:5]:  # 最多推荐 5 个
                    pattern_data = pattern.get("pattern_data", {})
                    column = pattern_data.get("column")
                    frequency = pattern.get("frequency", 0)

                    if column:
                        recommendations.append({
                            "type": "index",
                            "title": f"为 {column} 列添加索引",
                            "description": f"该列在查询中频繁用于过滤（{frequency} 次）",
                            "suggested_sql": f"CREATE INDEX idx_{table_name}_{column} ON {table_name}({column})",
                            "impact_score": min(1.0, frequency / 100),
                            "effort_level": "low",
                            "priority": "high" if frequency > 50 else "medium"
                        })

        except Exception as e:
            logger.error(f"Index recommendation failed: {e}")

        return recommendations

    # ==================== 分区推荐 ====================

    async def recommend_partitioning(
        self,
        datasource: str,
        table_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        推荐分区策略

        Args:
            datasource: 数据源
            table_name: 表名

        Returns:
            分区推荐
        """
        try:
            # 获取表信息
            async with db_manager.get_async_session() as session:
                result = await session.execute(
                    select(VectorSchemaInfoModel)
                    .where(
                        and_(
                            VectorSchemaInfoModel.datasource == datasource,
                            VectorSchemaInfoModel.table_name == table_name
                        )
                    )
                )
                schema_info = result.scalars().first()

            if schema_info:
                # 检查是否有时间字段
                schema_desc = schema_info.schema_description or "{}"
                import json
                columns = json.loads(schema_desc).get("columns", []) if isinstance(schema_desc, str) else []

                time_columns = [
                    col for col in columns
                    if any(kw in col.get("name", "").lower() for kw in ["date", "time", "created", "updated"])
                ]

                if time_columns:
                    time_column = time_columns[0]["name"]
                    return {
                        "type": "partition",
                        "title": f"按 {time_column} 列进行分区",
                        "description": f"检测到时间列 {time_column}，建议按时间分区以提升查询性能",
                        "suggested_sql": f"ALTER TABLE {table_name} PARTITION BY RANGE ({time_column})",
                        "impact_score": 0.8,
                        "effort_level": "high",
                        "priority": "medium"
                    }

        except Exception as e:
            logger.error(f"Partition recommendation failed: {e}")

        return None

    # ==================== 冗余检测 ====================

    async def detect_redundancy(
        self,
        datasource: str,
        table_name: str
    ) -> List[Dict[str, Any]]:
        """
        检测冗余

        Args:
            datasource: 数据源
            table_name: 表名

        Returns:
            冗余发现列表
        """
        findings = []

        try:
            async with db_manager.get_async_session() as session:
                result = await session.execute(
                    select(VectorSchemaInfoModel)
                    .where(
                        and_(
                            VectorSchemaInfoModel.datasource == datasource,
                            VectorSchemaInfoModel.table_name == table_name
                        )
                    )
                )
                schema_info = result.scalars().first()

            if schema_info:
                import json
                schema_desc = schema_info.schema_description or "{}"
                columns = json.loads(schema_desc).get("columns", []) if isinstance(schema_desc, str) else []

                # 检测相似列名
                column_names = [col.get("name", "").lower() for col in columns]

                # 简单相似度检测（基于名称相似度）
                for i, col1 in enumerate(column_names):
                    for col2 in column_names[i+1:]:
                        # 检测常见冗余模式
                        if self._is_similar_column(col1, col2):
                            findings.append({
                                "type": "redundancy",
                                "title": f"检测到冗余列：{col1} 和 {col2}",
                                "description": "这两列可能存储相同或相似的数据",
                                "columns": [col1, col2],
                                "impact_score": 0.6,
                                "effort_level": "medium",
                                "priority": "low"
                            })

        except Exception as e:
            logger.error(f"Redundancy detection failed: {e}")

        return findings

    def _is_similar_column(self, col1: str, col2: str) -> bool:
        """检测列名是否相似"""
        # 常见冗余模式
        similar_pairs = [
            ("name", "title"),
            ("desc", "description"),
            ("amt", "amount"),
            ("qty", "quantity"),
            ("cnt", "count"),
            ("num", "number"),
            ("id", "code"),
            ("type", "category"),
        ]

        for prefix1, prefix2 in similar_pairs:
            if (col1.startswith(prefix1) and col2.startswith(prefix2)) or \
               (col1.startswith(prefix2) and col2.startswith(prefix1)):
                return True

        # 检测完全相同的前缀
        if col1[:-1] == col2[:-1] and len(col1) == len(col2):
            return True

        return False

    # ==================== 获取所有推荐 ====================

    async def get_all_recommendations(
        self,
        datasource: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取所有推荐"""
        async with db_manager.get_async_session() as session:
            conditions = []
            if datasource:
                conditions.append(RecommendationModel.datasource == datasource)
            if status:
                conditions.append(RecommendationModel.status == status)

            query = select(RecommendationModel)
            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(desc(RecommendationModel.created_at)).limit(limit)

            result = await session.execute(query)
            recommendations = result.scalars().all()

            return [rec.to_dict() for rec in recommendations]

    # ==================== 创建推荐 ====================

    async def create_recommendation(
        self,
        datasource: str,
        table_name: str,
        recommendation_type: str,
        title: str,
        description: str,
        suggested_sql: str = None,
        column_name: str = None,
        rationale: str = None,
        priority: str = "medium"
    ) -> str:
        """创建推荐"""
        async with db_manager.get_async_session() as session:
            rec = RecommendationModel(
                datasource=datasource,
                table_name=table_name,
                column_name=column_name,
                recommendation_type=recommendation_type,
                title=title,
                description=description,
                suggested_sql=suggested_sql,
                rationale=rationale,
                priority=priority
            )
            session.add(rec)
            await session.flush()
            return rec.id

    # ==================== 应用推荐 ====================

    async def apply_recommendation(
        self,
        recommendation_id: str,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """应用推荐"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(RecommendationModel).where(RecommendationModel.id == recommendation_id)
            )
            rec = result.scalar_one_or_none()

            if not rec:
                return {"error": "Recommendation not found"}

            if dry_run:
                return {
                    "dry_run": True,
                    "recommendation": rec.to_dict(),
                    "sql": rec.suggested_sql,
                    "message": "Dry run mode - no changes applied"
                }

            # 标记为已应用
            rec.status = "applied"
            rec.applied_at = datetime.utcnow()
            session.add(rec)

            return {
                "success": True,
                "recommendation_id": recommendation_id,
                "status": "applied",
                "sql": rec.suggested_sql
            }

    # ==================== 拒绝推荐 ====================

    async def reject_recommendation(
        self,
        recommendation_id: str,
        reason: str
    ) -> bool:
        """拒绝推荐"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(RecommendationModel).where(RecommendationModel.id == recommendation_id)
            )
            rec = result.scalar_one_or_none()

            if not rec:
                return False

            rec.status = "rejected"
            rec.rejected_reason = reason
            session.add(rec)
            return True


# 全局 Schema 推荐服务实例
schema_recommendation_service = SchemaRecommendationService()
