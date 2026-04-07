"""
血缘持久化服务

实现血缘关系的 CRUD 操作、历史版本追溯和查询优化
"""
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import uuid
import json

from models.lineage_db import (
    LineageNodeModel,
    LineageEdgeModel,
    LineageQueryHistoryModel,
    LineageSnapshotModel
)
from config.database import db_manager
from utils.logger import logger


class LineagePersistenceService:
    """血缘持久化服务"""

    def __init__(self):
        self._db_manager = db_manager

    async def _get_session(self) -> AsyncSession:
        """获取数据库会话"""
        async with self._db_manager.get_async_session() as session:
            yield session

    # ============ 节点操作 ============

    async def create_node(
        self,
        node_id: str,
        name: str,
        node_type: str,
        datasource: str,
        schema_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建血缘节点"""
        async for session in self._get_session():
            try:
                # 检查节点是否已存在
                result = await session.execute(
                    select(LineageNodeModel).where(
                        LineageNodeModel.id == node_id,
                        LineageNodeModel.is_current == True
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    return {
                        "success": False,
                        "message": f"节点已存在：{node_id}",
                        "node": existing.to_dict()
                    }

                # 创建新节点
                node = LineageNodeModel(
                    id=node_id,
                    name=name,
                    node_type=node_type,
                    datasource=datasource,
                    schema_name=schema_name,
                    metadata_json=metadata or {},
                    created_by=created_by,
                    version=1,
                    is_current=True
                )
                session.add(node)
                await session.flush()  # 获取生成的 ID

                logger.info(f"创建血缘节点：{node_id}")

                return {
                    "success": True,
                    "message": f"节点创建成功：{node_id}",
                    "node": node.to_dict()
                }

            except Exception as e:
                logger.error(f"创建血缘节点失败：{e}")
                return {
                    "success": False,
                    "message": f"创建失败：{str(e)}"
                }

    async def get_node(self, node_id: str, include_history: bool = False) -> Dict[str, Any]:
        """获取节点信息"""
        async for session in self._get_session():
            try:
                if include_history:
                    # 获取所有版本
                    result = await session.execute(
                        select(LineageNodeModel)
                        .where(LineageNodeModel.id == node_id)
                        .order_by(LineageNodeModel.version.desc())
                    )
                    nodes = result.scalars().all()
                    return {
                        "success": True,
                        "current": nodes[0].to_dict() if nodes else None,
                        "history": [n.to_dict() for n in nodes[1:]] if len(nodes) > 1 else []
                    }
                else:
                    # 只获取当前版本
                    result = await session.execute(
                        select(LineageNodeModel).where(
                            LineageNodeModel.id == node_id,
                            LineageNodeModel.is_current == True
                        )
                    )
                    node = result.scalar_one_or_none()

                    if node:
                        return {
                            "success": True,
                            "node": node.to_dict()
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"节点不存在：{node_id}"
                        }

            except Exception as e:
                logger.error(f"获取节点失败：{e}")
                return {
                    "success": False,
                    "message": f"获取失败：{str(e)}"
                }

    async def update_node(
        self,
        node_id: str,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新节点（保留历史版本）"""
        async for session in self._get_session():
            try:
                # 获取当前版本
                result = await session.execute(
                    select(LineageNodeModel).where(
                        LineageNodeModel.id == node_id,
                        LineageNodeModel.is_current == True
                    )
                )
                current = result.scalar_one_or_none()

                if not current:
                    return {
                        "success": False,
                        "message": f"节点不存在：{node_id}"
                    }

                # 将当前版本标记为非当前
                current.is_current = False
                current.updated_at = datetime.utcnow()

                # 创建新版本
                new_version = LineageNodeModel(
                    id=current.id,
                    name=updates.get("name", current.name),
                    node_type=current.node_type,
                    datasource=current.datasource,
                    schema_name=updates.get("schema_name", current.schema_name),
                    metadata_json=updates.get("metadata", current.metadata_json),
                    created_by=current.created_by,
                    updated_by=updated_by,
                    version=current.version + 1,
                    is_current=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_version)

                logger.info(f"更新血缘节点：{node_id}, 新版本：{new_version.version}")

                return {
                    "success": True,
                    "message": f"节点更新成功：{node_id}",
                    "node": new_version.to_dict()
                }

            except Exception as e:
                logger.error(f"更新节点失败：{e}")
                return {
                    "success": False,
                    "message": f"更新失败：{str(e)}"
                }

    async def delete_node(self, node_id: str) -> Dict[str, Any]:
        """删除节点（软删除，标记为非当前）"""
        async for session in self._get_session():
            try:
                result = await session.execute(
                    update(LineageNodeModel)
                    .where(
                        LineageNodeModel.id == node_id,
                        LineageNodeModel.is_current == True
                    )
                    .values(is_current=False, updated_at=datetime.utcnow())
                )

                if result.rowcount > 0:
                    logger.info(f"删除血缘节点：{node_id}")
                    return {
                        "success": True,
                        "message": f"节点已删除：{node_id}"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"节点不存在：{node_id}"
                    }

            except Exception as e:
                logger.error(f"删除节点失败：{e}")
                return {
                    "success": False,
                    "message": f"删除失败：{str(e)}"
                }

    async def list_nodes(
        self,
        datasource: Optional[str] = None,
        node_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """查询节点列表"""
        async for session in self._get_session():
            try:
                query = select(LineageNodeModel).where(LineageNodeModel.is_current == True)

                if datasource:
                    query = query.where(LineageNodeModel.datasource == datasource)
                if node_type:
                    query = query.where(LineageNodeModel.node_type == node_type)
                if search:
                    query = query.where(LineageNodeModel.name.ilike(f"%{search}%"))

                # 获取总数
                count_query = select(func.count()).select_from(query.subquery())
                total = await session.execute(count_query)
                total_count = total.scalar()

                # 获取数据
                query = query.order_by(LineageNodeModel.name).limit(limit).offset(offset)
                result = await session.execute(query)
                nodes = result.scalars().all()

                return {
                    "success": True,
                    "nodes": [n.to_dict() for n in nodes],
                    "total": total_count,
                    "limit": limit,
                    "offset": offset
                }

            except Exception as e:
                logger.error(f"查询节点列表失败：{e}")
                return {
                    "success": False,
                    "message": f"查询失败：{str(e)}"
                }

    # ============ 边操作 ============

    async def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        operation: str,
        query_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建血缘边"""
        async for session in self._get_session():
            try:
                # 验证源节点和目标节点存在
                for node_id in [source_id, target_id]:
                    result = await session.execute(
                        select(LineageNodeModel).where(
                            LineageNodeModel.id == node_id,
                            LineageNodeModel.is_current == True
                        )
                    )
                    if not result.scalar_one_or_none():
                        return {
                            "success": False,
                            "message": f"节点不存在：{node_id}"
                        }

                # 生成边 ID
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                edge_id = f"edge:{source_id}:{target_id}:{operation}:{timestamp}"

                # 创建边
                edge = LineageEdgeModel(
                    id=edge_id,
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=edge_type,
                    operation=operation,
                    query_hash=query_hash,
                    metadata_json=metadata or {},
                    created_by=created_by,
                    version=1,
                    is_current=True
                )
                session.add(edge)
                await session.flush()

                logger.info(f"创建血缘边：{source_id} -> {target_id}")

                return {
                    "success": True,
                    "message": "边创建成功",
                    "edge": edge.to_dict()
                }

            except Exception as e:
                logger.error(f"创建血缘边失败：{e}")
                return {
                    "success": False,
                    "message": f"创建失败：{str(e)}"
                }

    async def get_edges(
        self,
        node_id: Optional[str] = None,
        datasource: Optional[str] = None,
        direction: str = "both"  # upstream, downstream, both
    ) -> Dict[str, Any]:
        """获取节点的边（上游/下游）"""
        async for session in self._get_session():
            try:
                edges = []

                if direction in ["upstream", "both"] and node_id:
                    # 获取上游边（指向该节点的边）
                    result = await session.execute(
                        select(LineageEdgeModel).where(
                            LineageEdgeModel.target_id == node_id,
                            LineageEdgeModel.is_current == True
                        )
                    )
                    edges.extend(result.scalars().all())

                if direction in ["downstream", "both"] and node_id:
                    # 获取下游边（从该节点出发的边）
                    result = await session.execute(
                        select(LineageEdgeModel).where(
                            LineageEdgeModel.source_id == node_id,
                            LineageEdgeModel.is_current == True
                        )
                    )
                    edges.extend(result.scalars().all())

                return {
                    "success": True,
                    "edges": [e.to_dict() for e in edges],
                    "count": len(edges)
                }

            except Exception as e:
                logger.error(f"获取边失败：{e}")
                return {
                    "success": False,
                    "message": f"获取失败：{str(e)}"
                }

    # ============ 查询历史操作 ============

    async def record_query_history(
        self,
        datasource: str,
        query_sql: str,
        query_hash: str,
        operation_type: str,
        source_tables: List[str],
        target_tables: List[str],
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        nodes_created: int = 0,
        edges_created: int = 0
    ) -> Dict[str, Any]:
        """记录查询历史"""
        async for session in self._get_session():
            try:
                history = LineageQueryHistoryModel(
                    id=uuid.uuid4().hex,
                    datasource=datasource,
                    query_sql=query_sql,
                    query_hash=query_hash,
                    operation_type=operation_type,
                    source_tables=source_tables,
                    target_tables=target_tables,
                    user_id=user_id,
                    user_name=user_name,
                    execution_time_ms=execution_time_ms,
                    status=status,
                    error_message=error_message,
                    nodes_created=nodes_created,
                    edges_created=edges_created
                )
                session.add(history)
                await session.flush()

                return {
                    "success": True,
                    "history_id": history.id
                }

            except Exception as e:
                logger.error(f"记录查询历史失败：{e}")
                return {
                    "success": False,
                    "message": f"记录失败：{str(e)}"
                }

    async def get_query_history(
        self,
        datasource: Optional[str] = None,
        user_id: Optional[str] = None,
        query_hash: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """查询历史记录"""
        async for session in self._get_session():
            try:
                query = select(LineageQueryHistoryModel).order_by(
                    LineageQueryHistoryModel.executed_at.desc()
                ).limit(limit)

                if datasource:
                    query = query.where(LineageQueryHistoryModel.datasource == datasource)
                if user_id:
                    query = query.where(LineageQueryHistoryModel.user_id == user_id)
                if query_hash:
                    query = query.where(LineageQueryHistoryModel.query_hash == query_hash)
                if start_time:
                    query = query.where(LineageQueryHistoryModel.executed_at >= start_time)
                if end_time:
                    query = query.where(LineageQueryHistoryModel.executed_at <= end_time)

                result = await session.execute(query)
                histories = result.scalars().all()

                return {
                    "success": True,
                    "histories": [h.to_dict() for h in histories],
                    "count": len(histories)
                }

            except Exception as e:
                logger.error(f"查询历史记录失败：{e}")
                return {
                    "success": False,
                    "message": f"查询失败：{str(e)}"
                }

    # ============ 快照操作 ============

    async def create_snapshot(
        self,
        snapshot_name: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建血缘快照"""
        async for session in self._get_session():
            try:
                # 获取所有当前节点和边
                nodes_result = await session.execute(
                    select(LineageNodeModel).where(LineageNodeModel.is_current == True)
                )
                nodes = nodes_result.scalars().all()

                edges_result = await session.execute(
                    select(LineageEdgeModel).where(LineageEdgeModel.is_current == True)
                )
                edges = edges_result.scalars().all()

                # 获取数据源列表
                datasources = list(set(n.datasource for n in nodes))

                # 创建快照
                snapshot = LineageSnapshotModel(
                    snapshot_name=snapshot_name,
                    description=description,
                    nodes_snapshot=[n.to_dict() for n in nodes],
                    edges_snapshot=[e.to_dict() for e in edges],
                    total_nodes=len(nodes),
                    total_edges=len(edges),
                    datasources=datasources,
                    created_by=created_by
                )
                session.add(snapshot)
                await session.flush()

                logger.info(f"创建血缘快照：{snapshot_name}, 节点：{len(nodes)}, 边：{len(edges)}")

                return {
                    "success": True,
                    "message": f"快照创建成功：{snapshot_name}",
                    "snapshot": snapshot.to_dict()
                }

            except Exception as e:
                logger.error(f"创建快照失败：{e}")
                return {
                    "success": False,
                    "message": f"创建失败：{str(e)}"
                }

    async def get_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """获取快照详情"""
        async for session in self._get_session():
            try:
                result = await session.execute(
                    select(LineageSnapshotModel).where(LineageSnapshotModel.id == snapshot_id)
                )
                snapshot = result.scalar_one_or_none()

                if snapshot:
                    return {
                        "success": True,
                        "snapshot": snapshot.to_dict()
                    }
                else:
                    return {
                        "success": False,
                        "message": f"快照不存在：{snapshot_id}"
                    }

            except Exception as e:
                logger.error(f"获取快照失败：{e}")
                return {
                    "success": False,
                    "message": f"获取失败：{str(e)}"
                }

    async def list_snapshots(self, limit: int = 50) -> Dict[str, Any]:
        """获取快照列表"""
        async for session in self._get_session():
            try:
                result = await session.execute(
                    select(LineageSnapshotModel)
                    .order_by(LineageSnapshotModel.created_at.desc())
                    .limit(limit)
                )
                snapshots = result.scalars().all()

                return {
                    "success": True,
                    "snapshots": [s.to_dict() for s in snapshots],
                    "count": len(snapshots)
                }

            except Exception as e:
                logger.error(f"获取快照列表失败：{e}")
                return {
                    "success": False,
                    "message": f"获取失败：{str(e)}"
                }

    # ============ 统计操作 ============

    async def get_statistics(self) -> Dict[str, Any]:
        """获取血缘统计信息"""
        async for session in self._get_session():
            try:
                # 节点统计
                nodes_count = await session.execute(
                    select(func.count()).where(
                        LineageNodeModel.is_current == True
                    )
                )
                total_nodes = nodes_count.scalar()

                # 边统计
                edges_count = await session.execute(
                    select(func.count()).where(
                        LineageEdgeModel.is_current == True
                    )
                )
                total_edges = edges_count.scalar()

                # 数据源统计
                datasources_result = await session.execute(
                    select(LineageNodeModel.datasource, func.count(LineageNodeModel.id))
                    .where(LineageNodeModel.is_current == True)
                    .group_by(LineageNodeModel.datasource)
                )
                datasources = {row[0]: row[1] for row in datasources_result.all()}

                # 节点类型统计
                types_result = await session.execute(
                    select(LineageNodeModel.node_type, func.count(LineageNodeModel.id))
                    .where(LineageNodeModel.is_current == True)
                    .group_by(LineageNodeModel.node_type)
                )
                node_types = {row[0]: row[1] for row in types_result.all()}

                # 查询历史统计
                history_count = await session.execute(select(func.count(LineageQueryHistoryModel.id)))
                total_queries = history_count.scalar()

                return {
                    "success": True,
                    "statistics": {
                        "total_nodes": total_nodes,
                        "total_edges": total_edges,
                        "total_queries": total_queries,
                        "datasources": datasources,
                        "node_types": node_types
                    }
                }

            except Exception as e:
                logger.error(f"获取统计信息失败：{e}")
                return {
                    "success": False,
                    "message": f"获取失败：{str(e)}"
                }

    async def cleanup_old_data(self, retention_days: int = 90) -> Dict[str, Any]:
        """清理过期数据"""
        async for session in self._get_session():
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

                # 清理过期的查询历史
                result = await session.execute(
                    delete(LineageQueryHistoryModel)
                    .where(LineageQueryHistoryModel.executed_at < cutoff_date)
                )
                deleted_history = result.rowcount

                logger.info(f"清理过期数据：删除 {deleted_history} 条查询历史")

                return {
                    "success": True,
                    "deleted_history": deleted_history,
                    "cutoff_date": cutoff_date.isoformat()
                }

            except Exception as e:
                logger.error(f"清理过期数据失败：{e}")
                return {
                    "success": False,
                    "message": f"清理失败：{str(e)}"
                }


# 全局服务实例
lineage_persistence_service = LineagePersistenceService()
