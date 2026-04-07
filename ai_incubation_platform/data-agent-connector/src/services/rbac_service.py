"""
RBAC 权限服务

实现基于角色的访问控制，支持：
- 角色管理（CRUD）
- 用户 - 角色绑定
- 权限校验
- 数据脱敏
"""
import asyncio
import fnmatch
import re
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from contextlib import asynccontextmanager

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker, Session

from models.rbac import (
    RoleModel, UserModel, UserRoleModel,
    DataSourcePermissionModel, ColumnMaskModel, PermissionAuditModel,
    OperationType, ResourceType
)
from config.database import db_manager
from utils.logger import logger
from config.settings import settings


class PermissionChecker:
    """权限校验器"""

    def __init__(self):
        self._builtin_roles_initialized = False

    def _parse_permission(self, permission: str) -> Tuple[str, str, Optional[str]]:
        """
        解析权限字符串

        格式：
        - "*:*" - 所有权限
        - "system:admin" - 系统管理员权限
        - "datasource:*:select" - 所有数据源的 SELECT 权限
        - "datasource:mydb:select" - mydb 数据源的 SELECT 权限
        - "datasource:mydb:table:users:select" - mydb 数据源 users 表的 SELECT 权限

        返回：(resource_type, resource_pattern, operation)
        """
        parts = permission.split(":")
        if len(parts) == 2:
            # system:admin 或 datasource:*
            return parts[0], parts[1], None
        elif len(parts) == 3:
            # datasource:*:select
            return parts[0], parts[1], parts[2]
        elif len(parts) >= 4:
            # datasource:mydb:table:users:select
            return parts[0], ":".join(parts[1:-1]), parts[-1]
        else:
            return "", "", None

    def _match_permission(self, permission: str, required_resource: str, required_operation: str) -> bool:
        """
        检查权限是否匹配

        支持通配符匹配：* 匹配任意字符

        权限格式: "resource_type:resource_pattern:operation"
        例如："datasource:mydb:select" 匹配资源 "datasource:mydb" 和操作 "SELECT"
        """
        res_type, res_pattern, op = self._parse_permission(permission)

        # 检查操作权限
        if op and op != "*" and op.upper() != required_operation.upper():
            return False

        # 检查资源权限
        if res_pattern == "*":
            return True

        # 构造完整的资源标识进行匹配
        # permission 格式：datasource:mydb -> 匹配 required_resource: datasource:mydb
        # 首先构造权限中的完整资源标识
        perm_resource = f"{res_type}:{res_pattern}"

        # 使用 fnmatch 进行通配符匹配
        return fnmatch.fnmatch(required_resource, perm_resource)

    def has_permission(self, permissions: List[str], resource: str, operation: str) -> bool:
        """
        检查是否拥有指定权限

        Args:
            permissions: 权限列表
            resource: 资源标识 (如 "datasource:mydb" 或 "datasource:mydb:table:users")
            operation: 操作类型 (如 "SELECT", "INSERT", "VIEW")

        Returns:
            bool: 是否拥有权限
        """
        for perm in permissions:
            # 通配符权限
            if perm == "*:*":
                return True

            if self._match_permission(perm, resource, operation):
                return True

        return False


class RBACService:
    """RBAC 服务"""

    def __init__(self):
        self.permission_checker = PermissionChecker()
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: int = 60  # 缓存 TTL（秒）
        self._cache_time: Dict[str, float] = {}

    def _get_sync_session(self) -> Session:
        """获取同步数据库 Session"""
        return db_manager.get_sync_session()

    async def initialize_builtin_roles(self) -> None:
        """初始化内置角色"""
        session = self._get_sync_session()
        try:
            builtin_roles = RoleModel.get_builtin_roles()
            for role_data in builtin_roles:
                stmt = select(RoleModel).where(RoleModel.name == role_data["name"])
                existing = session.scalar(stmt)

                if not existing:
                    role = RoleModel(
                        id=role_data.get("id", None) or f"builtin_{role_data['name']}",
                        name=role_data["name"],
                        description=role_data["description"],
                        is_system_role=role_data["is_system_role"],
                        permissions_json=role_data["permissions_json"]
                    )
                    session.add(role)
                    logger.info(f"Created builtin role: {role_data['name']}")

            session.commit()
            self._builtin_roles_initialized = True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to initialize builtin roles: {e}")
        finally:
            session.close()

    # ==================== 角色管理 ====================

    async def create_role(self, name: str, description: str = None,
                          permissions: List[str] = None, created_by: str = None) -> Dict[str, Any]:
        """创建角色"""
        session = self._get_sync_session()
        try:
            # 检查角色是否已存在
            stmt = select(RoleModel).where(RoleModel.name == name)
            existing = session.scalar(stmt)
            if existing:
                return {"success": False, "error": f"角色 '{name}' 已存在"}

            role = RoleModel(
                name=name,
                description=description,
                permissions_json=permissions or [],
                created_by=created_by
            )
            session.add(role)
            session.commit()
            session.refresh(role)

            await self._audit_permission_action(
                action="CREATE_ROLE",
                resource_type="role",
                resource_id=role.id,
                details={"name": name, "permissions": permissions},
                result="success",
                created_by=created_by
            )

            return {"success": True, "role": role.to_dict()}
        except Exception as e:
            session.rollback()
            await self._audit_permission_action(
                action="CREATE_ROLE",
                resource_type="role",
                resource_id=name,
                details={"error": str(e)},
                result="failed",
                created_by=created_by
            )
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_role(self, role_name: str) -> Optional[Dict[str, Any]]:
        """获取角色信息"""
        session = self._get_sync_session()
        try:
            stmt = select(RoleModel).where(RoleModel.name == role_name)
            role = session.scalar(stmt)
            return role.to_dict() if role else None
        finally:
            session.close()

    async def list_roles(self) -> List[Dict[str, Any]]:
        """获取所有角色"""
        session = self._get_sync_session()
        try:
            stmt = select(RoleModel).order_by(RoleModel.name)
            roles = session.scalars(stmt).all()
            return [role.to_dict() for role in roles]
        finally:
            session.close()

    async def update_role(self, role_name: str, permissions: List[str] = None,
                          description: str = None, updated_by: str = None) -> Dict[str, Any]:
        """更新角色"""
        session = self._get_sync_session()
        try:
            stmt = select(RoleModel).where(RoleModel.name == role_name)
            role = session.scalar(stmt)

            if not role:
                return {"success": False, "error": f"角色 '{role_name}' 不存在"}

            if role.is_system_role and updated_by:
                # 系统内置角色只能由管理员更新
                pass  # 可以在这里添加额外的权限检查

            if permissions is not None:
                role.permissions_json = permissions
            if description is not None:
                role.description = description

            session.commit()
            session.refresh(role)

            await self._audit_permission_action(
                action="UPDATE_ROLE",
                resource_type="role",
                resource_id=role.id,
                details={"name": role_name, "permissions": permissions},
                result="success",
                created_by=updated_by
            )

            return {"success": True, "role": role.to_dict()}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def delete_role(self, role_name: str, deleted_by: str = None) -> Dict[str, Any]:
        """删除角色"""
        session = self._get_sync_session()
        try:
            stmt = select(RoleModel).where(RoleModel.name == role_name)
            role = session.scalar(stmt)

            if not role:
                return {"success": False, "error": f"角色 '{role_name}' 不存在"}

            if role.is_system_role:
                return {"success": False, "error": "系统内置角色不可删除"}

            # 检查是否有用户绑定此角色
            user_role_stmt = select(UserRoleModel).where(UserRoleModel.role_id == role.id)
            user_roles = session.scalars(user_role_stmt).all()
            if user_roles:
                return {"success": False, "error": f"有 {len(user_roles)} 个用户绑定了此角色"}

            session.delete(role)
            session.commit()

            await self._audit_permission_action(
                action="DELETE_ROLE",
                resource_type="role",
                resource_id=role.id,
                details={"name": role_name},
                result="success",
                created_by=deleted_by
            )

            return {"success": True, "message": f"角色 '{role_name}' 已删除"}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    # ==================== 用户 - 角色管理 ====================

    async def get_or_create_user(self, user_id: str, username: str = None,
                                  email: str = None) -> UserModel:
        """获取或创建用户"""
        session = self._get_sync_session()
        try:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            user = session.scalar(stmt)

            if not user:
                user = UserModel(
                    user_id=user_id,
                    username=username,
                    email=email
                )
                session.add(user)
                session.commit()
                session.refresh(user)

            return user
        finally:
            session.close()

    async def assign_role_to_user(self, user_id: str, role_name: str,
                                   assigned_by: str = None) -> Dict[str, Any]:
        """给用户分配角色"""
        session = self._get_sync_session()
        try:
            # 获取用户
            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user = session.scalar(user_stmt)
            if not user:
                user = UserModel(user_id=user_id)
                session.add(user)
                session.flush()

            # 获取角色
            role_stmt = select(RoleModel).where(RoleModel.name == role_name)
            role = session.scalar(role_stmt)
            if not role:
                return {"success": False, "error": f"角色 '{role_name}' 不存在"}

            # 检查是否已绑定
            existing_stmt = select(UserRoleModel).where(
                UserRoleModel.user_id == user.id,
                UserRoleModel.role_id == role.id
            )
            existing = session.scalar(existing_stmt)
            if existing:
                return {"success": False, "error": "用户已拥有此角色"}

            user_role = UserRoleModel(
                user_id=user.id,
                role_id=role.id,
                created_by=assigned_by
            )
            session.add(user_role)
            session.commit()

            await self._audit_permission_action(
                action="ASSIGN_ROLE",
                resource_type="user_role",
                resource_id=user_role.id,
                details={"user_id": user_id, "role_name": role_name},
                result="success",
                created_by=assigned_by
            )

            return {"success": True, "message": f"用户 '{user_id}' 已分配角色 '{role_name}'"}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def revoke_role_from_user(self, user_id: str, role_name: str,
                                     revoked_by: str = None) -> Dict[str, Any]:
        """撤销用户角色"""
        session = self._get_sync_session()
        try:
            # 获取用户
            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user = session.scalar(user_stmt)
            if not user:
                return {"success": False, "error": f"用户 '{user_id}' 不存在"}

            # 获取角色
            role_stmt = select(RoleModel).where(RoleModel.name == role_name)
            role = session.scalar(role_stmt)
            if not role:
                return {"success": False, "error": f"角色 '{role_name}' 不存在"}

            # 删除绑定
            delete_stmt = delete(UserRoleModel).where(
                UserRoleModel.user_id == user.id,
                UserRoleModel.role_id == role.id
            )
            session.execute(delete_stmt)
            session.commit()

            await self._audit_permission_action(
                action="REVOKE_ROLE",
                resource_type="user_role",
                resource_id=f"{user.id}:{role.id}",
                details={"user_id": user_id, "role_name": role_name},
                result="success",
                created_by=revoked_by
            )

            return {"success": True, "message": f"用户 '{user_id}' 的角色 '{role_name}' 已撤销"}
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    async def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有角色"""
        session = self._get_sync_session()
        try:
            # 获取用户
            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user = session.scalar(user_stmt)
            if not user:
                return []

            # 获取用户的角色绑定
            user_role_stmt = select(UserRoleModel).where(UserRoleModel.user_id == user.id)
            user_roles = session.scalars(user_role_stmt).all()

            roles = []
            for ur in user_roles:
                role_stmt = select(RoleModel).where(RoleModel.id == ur.role_id)
                role = session.scalar(role_stmt)
                if role:
                    roles.append(role.to_dict())

            return roles
        finally:
            session.close()

    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户的所有权限"""
        roles = await self.get_user_roles(user_id)
        permissions = set()
        for role in roles:
            permissions.update(role.get("permissions", []))
        return permissions

    # ==================== 权限校验 ====================

    async def check_permission(self, user_id: str, resource: str,
                                operation: str) -> Tuple[bool, Optional[str]]:
        """
        检查用户是否有指定权限

        Args:
            user_id: 用户 ID
            resource: 资源标识 (如 "datasource:mydb" 或 "datasource:mydb:table:users")
            operation: 操作类型 (如 "SELECT", "INSERT")

        Returns:
            (has_permission, reason): 是否有权限及原因
        """
        # 获取用户权限
        permissions = await self.get_user_permissions(user_id)

        # 检查是否有通配符权限
        if "*:*" in permissions:
            return True, None

        # 检查具体权限
        if self.permission_checker.has_permission(list(permissions), resource, operation):
            return True, None

        return False, f"用户 '{user_id}' 没有 '{operation}' 权限访问 '{resource}'"

    async def check_datasource_access(self, user_id: str, datasource_name: str,
                                       operation: str = "SELECT") -> Tuple[bool, Optional[str]]:
        """检查数据源访问权限"""
        resource = f"datasource:{datasource_name}"
        return await self.check_permission(user_id, resource, operation)

    async def check_table_access(self, user_id: str, datasource_name: str,
                                  table_name: str, operation: str = "SELECT") -> Tuple[bool, Optional[str]]:
        """检查表访问权限"""
        resource = f"datasource:{datasource_name}:table:{table_name}"
        return await self.check_permission(user_id, resource, operation)

    # ==================== 数据脱敏 ====================

    async def get_column_masks(self, user_id: str, datasource_name: str,
                                table_name: str) -> Dict[str, Dict[str, Any]]:
        """
        获取用户查看表时的列脱敏规则

        Returns:
            Dict[column_name, {mask_type, mask_params}]
        """
        session = self._get_sync_session()
        try:
            # 获取用户角色
            user_stmt = select(UserModel).where(UserModel.user_id == user_id)
            user = session.scalar(user_stmt)
            if not user:
                return {}

            user_role_stmt = select(UserRoleModel).where(UserRoleModel.user_id == user.id)
            user_roles = session.scalars(user_role_stmt).all()

            role_ids = [ur.role_id for ur in user_roles]
            if not role_ids:
                return {}

            # 获取脱敏规则
            mask_stmt = select(ColumnMaskModel).where(
                ColumnMaskModel.role_id.in_(role_ids),
                ColumnMaskModel.datasource_name == datasource_name,
                ColumnMaskModel.table_name == table_name
            )
            masks = session.scalars(mask_stmt).all()

            return {
                mask.column_name: {
                    "mask_type": mask.mask_type,
                    "mask_params": mask.mask_params or {}
                }
                for mask in masks
            }
        finally:
            session.close()

    def apply_mask(self, value: Any, mask_type: str, mask_params: Dict[str, Any] = None) -> Any:
        """
        应用脱敏规则

        Args:
            value: 原始值
            mask_type: 脱敏类型 (none, mask, hash, redact, custom)
            mask_params: 脱敏参数

        Returns:
            脱敏后的值
        """
        if value is None:
            return None

        mask_params = mask_params or {}

        if mask_type == "none":
            return value

        elif mask_type == "redact":
            return "***"

        elif mask_type == "hash":
            return hashlib.sha256(str(value).encode()).hexdigest()[:16]

        elif mask_type == "mask":
            # 部分掩码
            str_value = str(value)
            if len(str_value) <= 4:
                return "*" * len(str_value)

            # 默认保留前 3 位和后 4 位
            keep_prefix = mask_params.get("keep_prefix", 3)
            keep_suffix = mask_params.get("keep_suffix", 4)

            if len(str_value) <= keep_prefix + keep_suffix:
                return str_value

            masked = str_value[:keep_prefix] + "*" * (len(str_value) - keep_prefix - keep_suffix) + str_value[-keep_suffix:]
            return masked

        elif mask_type == "custom":
            # 自定义脱敏函数
            custom_func = mask_params.get("function")
            if custom_func and callable(custom_func):
                return custom_func(value)
            return value

        return value

    async def mask_query_result(self, user_id: str, datasource_name: str,
                                 table_name: str, columns: List[str],
                                 rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对查询结果应用脱敏规则

        Args:
            user_id: 用户 ID
            datasource_name: 数据源名称
            table_name: 表名
            columns: 列名列表
            rows: 查询结果行

        Returns:
            脱敏后的结果
        """
        masks = await self.get_column_masks(user_id, datasource_name, table_name)

        if not masks:
            return rows

        masked_rows = []
        for row in rows:
            masked_row = {}
            for col, value in row.items():
                if col in masks:
                    mask_info = masks[col]
                    masked_row[col] = self.apply_mask(value, mask_info["mask_type"], mask_info["mask_params"])
                else:
                    masked_row[col] = value
            masked_rows.append(masked_row)

        return masked_rows

    # ==================== 审计日志 ====================

    async def _audit_permission_action(self, action: str, resource_type: str,
                                        resource_id: str, details: Dict = None,
                                        result: str = "success", reason: str = None,
                                        created_by: str = None) -> None:
        """记录权限操作审计日志"""
        session = self._get_sync_session()
        try:
            audit = PermissionAuditModel(
                user_id=created_by or "system",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                result=result,
                reason=reason,
                created_by=created_by
            )
            session.add(audit)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to audit permission action: {e}")
        finally:
            session.close()

    async def list_permission_audits(self, user_id: str = None, action: str = None,
                                      limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """查询权限审计日志"""
        session = self._get_sync_session()
        try:
            stmt = select(PermissionAuditModel).order_by(PermissionAuditModel.created_at.desc())

            if user_id:
                stmt = stmt.where(PermissionAuditModel.user_id == user_id)
            if action:
                stmt = stmt.where(PermissionAuditModel.action == action)

            stmt = stmt.offset(offset).limit(limit)
            audits = session.scalars(stmt).all()

            return [audit.to_dict() for audit in audits]
        finally:
            session.close()


# 全局服务实例
rbac_service = RBACService()


async def init_rbac():
    """初始化 RBAC 服务"""
    await rbac_service.initialize_builtin_roles()
    logger.info("RBAC service initialized")
