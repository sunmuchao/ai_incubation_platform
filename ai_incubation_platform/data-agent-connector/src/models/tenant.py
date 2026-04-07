"""
多租户模型

实现多租户架构支持：
- 租户管理（CRUD）
- 租户隔离
- 租户配置
- 租户配额管理
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, Index, Integer, JSON, Text
from models.lineage_db import Base
import uuid

# Base imported from lineage_db


class TenantModel(Base):
    """租户模型"""
    __tablename__ = "tenants"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_code = Column(String(64), unique=True, nullable=False, index=True)  # 租户编码
    tenant_name = Column(String(256), nullable=False)  # 租户名称
    description = Column(Text, nullable=True)  # 租户描述

    # 租户状态
    # active: 正常
    # suspended: 暂停
    # inactive: 停用
    status = Column(String(32), default="active", nullable=False)

    # 租户配置（JSON 存储）
    # 格式：{
    #     "default_datasources": ["ds1", "ds2"],  # 默认数据源
    #     "allowed_connectors": ["mysql", "postgresql"],  # 允许的连接器类型
    #     "max_connections": 20,  # 最大连接数
    #     "max_queries_per_minute": 100,  # 每分钟最大查询数
    #     "max_query_rows": 50000,  # 单次查询最大行数
    #     "enable_ai_features": true,  # 是否启用 AI 功能
    #     "timezone": "Asia/Shanghai",  # 时区
    #     "locale": "zh-CN"  # 语言
    # }
    config_json = Column(JSON, nullable=True, default=dict)

    # 配额限制
    # 格式：{
    #     "max_datasources": 10,  # 最大数据源数量
    #     "max_users": 100,  # 最大用户数
    #     "max_queries_per_day": 100000,  # 每日最大查询数
    #     "max_storage_mb": 1024,  # 最大存储空间 (MB)
    #     "max_api_calls_per_day": 50000  # 每日最大 API 调用数
    # }
    quota_json = Column(JSON, nullable=True, default=dict)

    # 联系信息
    contact_name = Column(String(128), nullable=True)
    contact_email = Column(String(256), nullable=True)
    contact_phone = Column(String(64), nullable=True)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    # 索引
    __table_args__ = (
        Index('idx_tenant_code', 'tenant_code', unique=True),
        Index('idx_tenant_status', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_code": self.tenant_code,
            "tenant_name": self.tenant_name,
            "description": self.description,
            "status": self.status,
            "config": self.config_json or {},
            "quota": self.quota_json or {},
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }

    @classmethod
    def get_builtin_tenants(cls) -> List[Dict]:
        """获取内置租户定义（用于初始化）"""
        return [
            {
                "tenant_code": "default",
                "tenant_name": "默认租户",
                "description": "系统默认租户，用于单租户场景",
                "status": "active",
                "config_json": {
                    "default_datasources": [],
                    "allowed_connectors": ["mysql", "postgresql", "sqlite", "mongodb"],
                    "max_connections": 20,
                    "max_queries_per_minute": 100,
                    "max_query_rows": 50000,
                    "enable_ai_features": True,
                    "timezone": "Asia/Shanghai",
                    "locale": "zh-CN"
                },
                "quota_json": {
                    "max_datasources": 20,
                    "max_users": 100,
                    "max_queries_per_day": 100000,
                    "max_storage_mb": 2048,
                    "max_api_calls_per_day": 100000
                },
                "contact_name": "System Admin",
                "contact_email": "admin@example.com"
            }
        ]


class TenantMemberModel(Base):
    """租户成员模型"""
    __tablename__ = "tenant_members"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id = Column(String(64), nullable=False, index=True)  # 租户 ID
    user_id = Column(String(128), nullable=False, index=True)  # 用户 ID

    # 成员角色
    # owner: 租户所有者
    # admin: 租户管理员
    # member: 普通成员
    # viewer: 只读成员
    role = Column(String(32), default="member", nullable=False)

    # 成员状态
    status = Column(String(32), default="active", nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_tenant_member_unique', 'tenant_id', 'user_id', unique=True),
        Index('idx_tenant_member_role', 'tenant_id', 'role'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


class TenantDatasourceModel(Base):
    """租户数据源模型"""
    __tablename__ = "tenant_datasources"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id = Column(String(64), nullable=False, index=True)  # 租户 ID
    datasource_name = Column(String(128), nullable=False)  # 数据源名称

    # 数据源配置（引用 connectors 中的配置）
    connector_type = Column(String(64), nullable=False)  # 连接器类型
    config_json = Column(JSON, nullable=True, default=dict)

    # 访问控制
    is_public = Column(Boolean, default=False, nullable=False)  # 是否租户内公开
    allowed_users = Column(JSON, nullable=True, default=list)  # 允许的用户 ID 列表

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index('idx_tenant_ds_unique', 'tenant_id', 'datasource_name', unique=True),
        Index('idx_tenant_ds_connector', 'tenant_id', 'connector_type'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "datasource_name": self.datasource_name,
            "connector_type": self.connector_type,
            "config_summary": self._get_config_summary(),
            "is_public": self.is_public,
            "allowed_users": self.allowed_users or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }

    def _get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要（隐藏敏感信息）"""
        if not self.config_json:
            return {}
        summary = {}
        sensitive_keys = ["password", "secret", "token", "key", "credential"]
        for k, v in self.config_json.items():
            if any(s in k.lower() for s in sensitive_keys):
                summary[k] = "***"
            else:
                summary[k] = v
        return summary


class TenantQuotaUsageModel(Base):
    """租户配额使用模型"""
    __tablename__ = "tenant_quota_usage"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id = Column(String(64), nullable=False, index=True)  # 租户 ID

    # 日期（按天统计）
    usage_date = Column(String(10), nullable=False, index=True)  # 格式：YYYY-MM-DD

    # 使用量
    queries_count = Column(Integer, default=0, nullable=False)  # 查询次数
    api_calls_count = Column(Integer, default=0, nullable=False)  # API 调用次数
    storage_used_mb = Column(Integer, default=0, nullable=False)  # 存储空间 (MB)
    datasources_count = Column(Integer, default=0, nullable=False)  # 数据源数量
    users_count = Column(Integer, default=0, nullable=False)  # 用户数量

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_quota_usage_unique', 'tenant_id', 'usage_date', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "usage_date": self.usage_date,
            "queries_count": self.queries_count,
            "api_calls_count": self.api_calls_count,
            "storage_used_mb": self.storage_used_mb,
            "datasources_count": self.datasources_count,
            "users_count": self.users_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
