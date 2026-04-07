"""
RBAC 权限模型

实现细粒度的基于角色的访问控制，支持：
- 系统级权限（角色管理、用户管理）
- 数据源级权限（访问特定数据源）
- 表级权限（访问特定表）
- 列级权限（字段脱敏）
- 操作级权限（SELECT、INSERT、UPDATE、DELETE）
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, Index, Integer, JSON, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
import uuid
from enum import Enum

from models.lineage_db import Base


class ResourceType(Enum):
    """资源类型"""
    SYSTEM = "system"
    DATASOURCE = "datasource"
    TABLE = "table"
    COLUMN = "column"


class OperationType(Enum):
    """操作类型"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"
    ADMIN = "ADMIN"
    VIEW = "VIEW"
    EDIT = "EDIT"
    MANAGE = "MANAGE"


class RoleModel(Base):
    """角色模型"""
    __tablename__ = "rbac_roles"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)  # 系统内置角色不可删除

    # 角色权限（JSON 存储）
    # 格式：{"system": ["admin", "view"], "datasource:*": ["select", "view"], "datasource:mydb": ["select"], ...}
    permissions_json = Column(JSON, nullable=True, default=list)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    # 关系
    users = relationship("UserRoleModel", back_populates="role")

    __table_args__ = (
        Index('idx_role_name', 'name', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_system_role": self.is_system_role,
            "permissions": self.permissions_json or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }

    @classmethod
    def get_builtin_roles(cls) -> List[Dict]:
        """获取内置角色定义"""
        return [
            {
                "name": "admin",
                "description": "系统管理员，拥有所有权限",
                "is_system_role": True,
                "permissions_json": ["*:*"]  # 通配符表示所有权限
            },
            {
                "name": "editor",
                "description": "编辑者，拥有读写权限",
                "is_system_role": True,
                "permissions_json": [
                    "datasource:*:select",
                    "datasource:*:insert",
                    "datasource:*:update",
                    "datasource:*:delete"
                ]
            },
            {
                "name": "analyst",
                "description": "分析师，拥有只读 + 分析权限",
                "is_system_role": True,
                "permissions_json": [
                    "datasource:*:select",
                    "system:view"
                ]
            },
            {
                "name": "viewer",
                "description": "查看者，仅拥有查看权限",
                "is_system_role": True,
                "permissions_json": [
                    "datasource:*:select"
                ]
            }
        ]


class UserModel(Base):
    """用户模型"""
    __tablename__ = "rbac_users"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id = Column(String(128), unique=True, nullable=False, index=True)  # 外部用户 ID
    username = Column(String(128), nullable=True)
    email = Column(String(256), nullable=True)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    roles = relationship("UserRoleModel", back_populates="user")

    __table_args__ = (
        Index('idx_user_user_id', 'user_id', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": [ur.role.name for ur in self.roles] if self.roles else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UserRoleModel(Base):
    """用户 - 角色绑定模型"""
    __tablename__ = "rbac_user_roles"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id = Column(String(64), ForeignKey("rbac_users.id"), nullable=False)
    role_id = Column(String(64), ForeignKey("rbac_roles.id"), nullable=False)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    # 关系
    user = relationship("UserModel", back_populates="roles")
    role = relationship("RoleModel", back_populates="users")

    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
        Index('idx_user_role_user', 'user_id'),
        Index('idx_user_role_role', 'role_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


class DataSourcePermissionModel(Base):
    """数据源权限模型"""
    __tablename__ = "rbac_datasource_permissions"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    role_id = Column(String(64), ForeignKey("rbac_roles.id"), nullable=False)
    datasource_name = Column(String(128), nullable=False, index=True)

    # 允许的操作
    allowed_operations = Column(JSON, nullable=True, default=list)  # ["SELECT", "INSERT", ...]

    # 表级权限（白名单/黑名单）
    # 格式：{"tables_allow": ["table1", "table2"], "tables_deny": ["sensitive_table"]}
    table_scope = Column(JSON, nullable=True, default=dict)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint('role_id', 'datasource_name', name='uq_role_datasource'),
        Index('idx_ds_perm_role', 'role_id'),
        Index('idx_ds_perm_datasource', 'datasource_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role_id": self.role_id,
            "datasource_name": self.datasource_name,
            "allowed_operations": self.allowed_operations or [],
            "table_scope": self.table_scope or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


class ColumnMaskModel(Base):
    """列脱敏规则模型"""
    __tablename__ = "rbac_column_masks"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    role_id = Column(String(64), ForeignKey("rbac_roles.id"), nullable=False)
    datasource_name = Column(String(128), nullable=False)
    table_name = Column(String(128), nullable=False)
    column_name = Column(String(128), nullable=False)

    # 脱敏类型
    # none: 不脱敏
    # mask: 部分掩码 (如 138****1234)
    # hash: 哈希处理
    # redact: 完全隐藏（返回 null 或 ***）
    # custom: 自定义函数
    mask_type = Column(String(32), default="redact", nullable=False)

    # 脱敏参数（用于自定义脱敏）
    mask_params = Column(JSON, nullable=True, default=dict)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint('role_id', 'datasource_name', 'table_name', 'column_name', name='uq_mask_unique'),
        Index('idx_mask_role', 'role_id'),
        Index('idx_mask_datasource_table', 'datasource_name', 'table_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role_id": self.role_id,
            "datasource_name": self.datasource_name,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "mask_type": self.mask_type,
            "mask_params": self.mask_params or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


class PermissionAuditModel(Base):
    """权限审计日志模型"""
    __tablename__ = "rbac_permission_audit"

    id = Column(String(64), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id = Column(String(128), nullable=False, index=True)
    action = Column(String(64), nullable=False)  # CREATE_ROLE, ASSIGN_ROLE, REVOKE_PERMISSION, etc.
    resource_type = Column(String(32), nullable=False)  # role, user, permission, datasource
    resource_id = Column(String(128), nullable=True)
    details = Column(JSON, nullable=True)
    result = Column(String(32), nullable=False)  # success, failed
    reason = Column(Text, nullable=True)

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String(128), nullable=True)
    ip_address = Column(String(64), nullable=True)

    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'created_at'),
        Index('idx_audit_action', 'action'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "result": self.result,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "ip_address": self.ip_address
        }
