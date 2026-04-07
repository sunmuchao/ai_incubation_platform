"""
血缘关系持久化模型

实现血缘关系的数据库存储，支持：
- 血缘关系持久化存储
- 血缘历史版本追溯
- 血缘查询优化
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Text, Boolean, Index, Integer, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


class LineageNodeModel(Base):
    """血缘节点模型"""
    __tablename__ = "lineage_nodes"

    id = Column(String(128), primary_key=True)
    name = Column(String(256), nullable=False, index=True)
    node_type = Column(String(64), nullable=False, index=True)  # table, column, view, api, etc.
    datasource = Column(String(128), nullable=False, index=True)
    schema_name = Column(String(128), nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    # 版本控制
    version = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False, index=True)

    # 关系
    outgoing_edges = relationship("LineageEdgeModel", foreign_keys="LineageEdgeModel.source_id", back_populates="source_node")
    incoming_edges = relationship("LineageEdgeModel", foreign_keys="LineageEdgeModel.target_id", back_populates="target_node")

    __table_args__ = (
        UniqueConstraint('datasource', 'node_type', 'name', 'is_current', name='uq_node_datasource_type_name'),
        Index('idx_node_type_current', 'node_type', 'is_current'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type,
            "datasource": self.datasource,
            "schema_name": self.schema_name,
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "is_current": self.is_current
        }


class LineageEdgeModel(Base):
    """血缘边模型"""
    __tablename__ = "lineage_edges"

    id = Column(String(128), primary_key=True)
    source_id = Column(String(128), ForeignKey("lineage_nodes.id"), nullable=False, index=True)
    target_id = Column(String(128), ForeignKey("lineage_nodes.id"), nullable=False, index=True)
    edge_type = Column(String(64), nullable=False, index=True)  # transform, write, read, depends_on
    operation = Column(String(64), nullable=False)  # SELECT, INSERT, UPDATE, DELETE, JOIN
    query_hash = Column(String(64), nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True, default=dict)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String(128), nullable=True)

    # 版本控制
    version = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False, index=True)

    # 关系
    source_node = relationship("LineageNodeModel", foreign_keys=[source_id], back_populates="outgoing_edges")
    target_node = relationship("LineageNodeModel", foreign_keys=[target_id], back_populates="incoming_edges")

    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', 'edge_type', 'query_hash', 'is_current', name='uq_edge_source_target_type'),
        Index('idx_edge_source_current', 'source_id', 'is_current'),
        Index('idx_edge_target_current', 'target_id', 'is_current'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type,
            "operation": self.operation,
            "query_hash": self.query_hash,
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "version": self.version,
            "is_current": self.is_current
        }


class LineageQueryHistoryModel(Base):
    """查询历史记录模型"""
    __tablename__ = "lineage_query_history"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    datasource = Column(String(128), nullable=False, index=True)
    query_sql = Column(Text, nullable=False)
    query_hash = Column(String(64), nullable=False, index=True)
    operation_type = Column(String(32), nullable=False, index=True)

    # 关联的表
    source_tables = Column(JSON, nullable=True, default=list)
    target_tables = Column(JSON, nullable=True, default=list)

    # 用户信息
    user_id = Column(String(128), nullable=True, index=True)
    user_name = Column(String(256), nullable=True)

    # 执行信息
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    execution_time_ms = Column(Integer, nullable=True)
    status = Column(String(32), default="success", nullable=False)
    error_message = Column(Text, nullable=True)

    # 血缘追踪结果
    nodes_created = Column(Integer, default=0, nullable=False)
    edges_created = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index('idx_history_datasource_time', 'datasource', 'executed_at'),
        Index('idx_history_user_time', 'user_id', 'executed_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "query_sql": self.query_sql[:500] if self.query_sql else None,
            "query_hash": self.query_hash,
            "operation_type": self.operation_type,
            "source_tables": self.source_tables or [],
            "target_tables": self.target_tables or [],
            "user_id": self.user_id,
            "user_name": self.user_name,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "status": self.status,
            "error_message": self.error_message,
            "nodes_created": self.nodes_created,
            "edges_created": self.edges_created
        }


class LineageSnapshotModel(Base):
    """血缘快照模型 - 用于历史版本追溯"""
    __tablename__ = "lineage_snapshots"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    snapshot_name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)

    # 快照内容 - 存储完整的血缘图
    nodes_snapshot = Column(JSON, nullable=False, default=list)
    edges_snapshot = Column(JSON, nullable=False, default=list)

    # 统计信息
    total_nodes = Column(Integer, default=0, nullable=False)
    total_edges = Column(Integer, default=0, nullable=False)
    datasources = Column(JSON, nullable=True, default=list)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_snapshot_created', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "snapshot_name": self.snapshot_name,
            "description": self.description,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "datasources": self.datasources or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }
