"""
向量索引持久化模型

实现向量索引的数据库存储，支持：
- 向量索引元数据持久化
- 集合管理
- 索引导航
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, Index, Integer, JSON, Float, Text
from models.lineage_db import Base
import uuid

# Base imported from lineage_db


class VectorIndexModel(Base):
    """向量索引模型"""
    __tablename__ = "vector_indexes"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    collection = Column(String(128), nullable=False, index=True)
    content = Column(Text, nullable=False)  # 原始内容
    content_hash = Column(String(64), nullable=True, index=True)  # 内容哈希，用于去重

    # 元数据
    metadata_json = Column(JSON, nullable=True, default=dict)

    # 索引信息
    datasource = Column(String(128), nullable=True, index=True)
    table_name = Column(String(128), nullable=True, index=True)
    column_name = Column(String(128), nullable=True)
    index_type = Column(String(32), nullable=False, default="content")  # content, schema, query_history

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_vector_collection_type', 'collection', 'index_type'),
        Index('idx_vector_datasource_table', 'datasource', 'table_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "collection": self.collection,
            "content": self.content[:500] if self.content else None,  # 截断内容
            "content_hash": self.content_hash,
            "metadata": self.metadata_json or {},
            "datasource": self.datasource,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "index_type": self.index_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }


class VectorCollectionModel(Base):
    """向量集合模型"""
    __tablename__ = "vector_collections"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(128), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # 集合配置
    dimension = Column(Integer, default=1536, nullable=False)
    distance_metric = Column(String(32), default="cosine", nullable=False)  # cosine, l2, ip

    # 统计信息
    total_vectors = Column(Integer, default=0, nullable=False)
    total_size_bytes = Column(Integer, default=0, nullable=False)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "dimension": self.dimension,
            "distance_metric": self.distance_metric,
            "total_vectors": self.total_vectors,
            "total_size_bytes": self.total_size_bytes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }


class VectorSearchHistoryModel(Base):
    """向量搜索历史模型"""
    __tablename__ = "vector_search_history"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    query_text = Column(Text, nullable=False)
    query_embedding_hash = Column(String(64), nullable=True, index=True)

    # 搜索参数
    collection = Column(String(128), nullable=False, index=True)
    search_filters = Column(JSON, nullable=True, default=dict)
    limit = Column(Integer, default=10, nullable=False)

    # 搜索结果
    result_count = Column(Integer, default=0, nullable=False)
    result_ids = Column(JSON, nullable=True, default=list)
    avg_similarity = Column(Float, nullable=True)

    # 用户信息
    user_id = Column(String(128), nullable=True, index=True)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    execution_time_ms = Column(Integer, nullable=True)

    __table_args__ = (
        Index('idx_search_history_collection_time', 'collection', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query_text": self.query_text[:500] if self.query_text else None,
            "collection": self.collection,
            "search_filters": self.search_filters or {},
            "limit": self.limit,
            "result_count": self.result_count,
            "result_ids": self.result_ids or [],
            "avg_similarity": self.avg_similarity,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "execution_time_ms": self.execution_time_ms
        }


class VectorSchemaInfoModel(Base):
    """向量 Schema 信息模型 - 用于存储表和字段的向量描述"""
    __tablename__ = "vector_schema_info"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    datasource = Column(String(128), nullable=False, index=True)
    table_name = Column(String(128), nullable=False, index=True)
    column_name = Column(String(128), nullable=True)

    # Schema 描述
    schema_description = Column(Text, nullable=False)
    sample_values = Column(JSON, nullable=True, default=list)
    data_type = Column(String(64), nullable=True)
    is_nullable = Column(Boolean, default=True)

    # 向量嵌入
    description_embedding_hash = Column(String(64), nullable=True, index=True)

    # 统计信息
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_schema_datasource_table_column', 'datasource', 'table_name', 'column_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "datasource": self.datasource,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "schema_description": self.schema_description,
            "sample_values": self.sample_values or [],
            "data_type": self.data_type,
            "is_nullable": self.is_nullable,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
