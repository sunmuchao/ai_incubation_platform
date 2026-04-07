"""
细粒度权限服务

提供 Discord 风格的权限管理系统：
- 权限点定义
- 角色权限映射
- 用户权限检查
- 权限继承与覆盖
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum

from models.member import MemberType, MemberRole, CommunityMember


class Permission(str, Enum):
    """权限点定义"""
    # 内容相关权限
    CREATE_POST = "create_post"
    VIEW_POST = "view_post"
    EDIT_OWN_POST = "edit_own_post"
    DELETE_OWN_POST = "delete_own_post"
    EDIT_ANY_POST = "edit_any_post"
    DELETE_ANY_POST = "delete_any_post"
    PIN_POST = "pin_post"  # 置顶帖子

    CREATE_COMMENT = "create_comment"
    VIEW_COMMENT = "view_comment"
    EDIT_OWN_COMMENT = "edit_own_comment"
    DELETE_OWN_COMMENT = "delete_own_comment"
    EDIT_ANY_COMMENT = "edit_any_comment"
    DELETE_ANY_COMMENT = "delete_any_comment"

    # 审核相关权限
    REPORT_CONTENT = "report_content"
    VIEW_REPORTS = "view_reports"
    PROCESS_REPORT = "process_report"
    REVIEW_CONTENT = "review_content"

    # 治理相关权限
    BAN_USER = "ban_user"
    LIFT_BAN = "lift_ban"
    WARN_USER = "warn_user"
    REMOVE_CONTENT = "remove_content"

    # 管理相关权限
    MANAGE_ROLES = "manage_roles"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_WEBHOOKS = "manage_webhooks"
    MANAGE_ANNOTATIONS = "manage_annotations"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    EXPORT_DATA = "export_data"

    # AI 相关权限
    USE_AI_AGENT = "use_ai_agent"
    CONFIGURE_AI_AGENT = "configure_ai_agent"

    # 系统权限
    SUPERUSER = "superuser"  # 拥有所有权限


# 角色权限映射（默认配置）
ROLE_PERMISSIONS: Dict[MemberRole, Set[Permission]] = {
    MemberRole.MEMBER: {
        Permission.CREATE_POST,
        Permission.VIEW_POST,
        Permission.EDIT_OWN_POST,
        Permission.DELETE_OWN_POST,
        Permission.CREATE_COMMENT,
        Permission.VIEW_COMMENT,
        Permission.EDIT_OWN_COMMENT,
        Permission.DELETE_OWN_COMMENT,
        Permission.REPORT_CONTENT,
        Permission.USE_AI_AGENT,
    },
    MemberRole.MODERATOR: {
        Permission.CREATE_POST,
        Permission.VIEW_POST,
        Permission.EDIT_OWN_POST,
        Permission.DELETE_OWN_POST,
        Permission.EDIT_ANY_POST,
        Permission.DELETE_ANY_POST,
        Permission.PIN_POST,
        Permission.CREATE_COMMENT,
        Permission.VIEW_COMMENT,
        Permission.EDIT_OWN_COMMENT,
        Permission.DELETE_OWN_COMMENT,
        Permission.EDIT_ANY_COMMENT,
        Permission.DELETE_ANY_COMMENT,
        Permission.REPORT_CONTENT,
        Permission.VIEW_REPORTS,
        Permission.PROCESS_REPORT,
        Permission.REVIEW_CONTENT,
        Permission.WARN_USER,
        Permission.REMOVE_CONTENT,
        Permission.VIEW_AUDIT_LOGS,
        Permission.USE_AI_AGENT,
        Permission.MANAGE_ANNOTATIONS,
    },
    MemberRole.ADMIN: {
        Permission.CREATE_POST,
        Permission.VIEW_POST,
        Permission.EDIT_OWN_POST,
        Permission.DELETE_OWN_POST,
        Permission.EDIT_ANY_POST,
        Permission.DELETE_ANY_POST,
        Permission.PIN_POST,
        Permission.CREATE_COMMENT,
        Permission.VIEW_COMMENT,
        Permission.EDIT_OWN_COMMENT,
        Permission.DELETE_OWN_COMMENT,
        Permission.EDIT_ANY_COMMENT,
        Permission.DELETE_ANY_COMMENT,
        Permission.REPORT_CONTENT,
        Permission.VIEW_REPORTS,
        Permission.PROCESS_REPORT,
        Permission.REVIEW_CONTENT,
        Permission.BAN_USER,
        Permission.LIFT_BAN,
        Permission.WARN_USER,
        Permission.REMOVE_CONTENT,
        Permission.MANAGE_ROLES,
        Permission.MANAGE_MEMBERS,
        Permission.MANAGE_WEBHOOKS,
        Permission.MANAGE_ANNOTATIONS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.EXPORT_DATA,
        Permission.USE_AI_AGENT,
        Permission.CONFIGURE_AI_AGENT,
    },
}

# 权限分组（用于 UI 展示和批量检查）
PERMISSION_GROUPS: Dict[str, List[Permission]] = {
    "content_create": [
        Permission.CREATE_POST,
        Permission.CREATE_COMMENT,
    ],
    "content_edit": [
        Permission.EDIT_OWN_POST,
        Permission.EDIT_OWN_COMMENT,
        Permission.EDIT_ANY_POST,
        Permission.EDIT_ANY_COMMENT,
    ],
    "content_delete": [
        Permission.DELETE_OWN_POST,
        Permission.DELETE_OWN_COMMENT,
        Permission.DELETE_ANY_POST,
        Permission.DELETE_ANY_COMMENT,
    ],
    "moderation": [
        Permission.REPORT_CONTENT,
        Permission.VIEW_REPORTS,
        Permission.PROCESS_REPORT,
        Permission.REVIEW_CONTENT,
        Permission.WARN_USER,
        Permission.REMOVE_CONTENT,
    ],
    "governance": [
        Permission.BAN_USER,
        Permission.LIFT_BAN,
        Permission.MANAGE_ROLES,
        Permission.MANAGE_MEMBERS,
    ],
    "admin": [
        Permission.MANAGE_WEBHOOKS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.EXPORT_DATA,
        Permission.CONFIGURE_AI_AGENT,
    ],
}


class PermissionService:
    """权限服务"""

    def __init__(self):
        self._role_permissions: Dict[MemberRole, Set[Permission]] = ROLE_PERMISSIONS.copy()
        self._user_override_permissions: Dict[str, Set[Permission]] = {}  # 用户特殊权限覆盖
        self._user_denied_permissions: Dict[str, Set[Permission]] = {}  # 用户被禁止的权限

    def get_role_permissions(self, role: MemberRole) -> Set[Permission]:
        """获取角色的默认权限"""
        return self._role_permissions.get(role, set())

    def update_role_permissions(
        self,
        role: MemberRole,
        add_permissions: List[Permission] = None,
        remove_permissions: List[Permission] = None
    ) -> Set[Permission]:
        """更新角色权限"""
        current = self._role_permissions.get(role, set()).copy()

        if add_permissions:
            current.update(add_permissions)
        if remove_permissions:
            current.difference_update(remove_permissions)

        self._role_permissions[role] = current
        return current

    def get_user_permissions(self, user_id: str, role: MemberRole) -> Set[Permission]:
        """获取用户的实际权限（考虑特殊覆盖）"""
        # 基础权限来自角色
        permissions = self._role_permissions.get(role, set()).copy()

        # 添加特殊授权
        if user_id in self._user_override_permissions:
            permissions.update(self._user_override_permissions[user_id])

        # 移除被禁止的权限
        if user_id in self._user_denied_permissions:
            permissions.difference_update(self._user_denied_permissions[user_id])

        return permissions

    def grant_permission(self, user_id: str, permission: Permission) -> None:
        """给用户授予特殊权限（覆盖角色默认）"""
        if user_id not in self._user_override_permissions:
            self._user_override_permissions[user_id] = set()
        self._user_override_permissions[user_id].add(permission)

    def revoke_permission(self, user_id: str, permission: Permission) -> None:
        """撤销用户的特殊权限"""
        if user_id in self._user_override_permissions:
            self._user_override_permissions[user_id].discard(permission)

    def deny_permission(self, user_id: str, permission: Permission) -> None:
        """禁止用户的某个权限（即使角色有该权限）"""
        if user_id not in self._user_denied_permissions:
            self._user_denied_permissions[user_id] = set()
        self._user_denied_permissions[user_id].add(permission)

    def has_permission(
        self,
        user_id: str,
        member_type: MemberType,
        role: MemberRole,
        permission: Permission
    ) -> bool:
        """检查用户是否有指定权限"""
        # AI 成员特殊处理
        if member_type == MemberType.AI:
            # AI 默认只能使用 AI Agent 相关权限
            ai_permissions = {Permission.USE_AI_AGENT, Permission.CONFIGURE_AI_AGENT}
            return permission in ai_permissions

        # 检查是否被明确禁止
        if user_id in self._user_denied_permissions:
            if permission in self._user_denied_permissions[user_id]:
                return False

        # 检查是否有特殊授权
        if user_id in self._user_override_permissions:
            if permission in self._user_override_permissions[user_id]:
                return True

        # 检查角色默认权限
        return permission in self._role_permissions.get(role, set())

    def has_any_permission(
        self,
        user_id: str,
        member_type: MemberType,
        role: MemberRole,
        permissions: List[Permission]
    ) -> bool:
        """检查用户是否有任意一个指定权限"""
        for permission in permissions:
            if self.has_permission(user_id, member_type, role, permission):
                return True
        return False

    def has_all_permissions(
        self,
        user_id: str,
        member_type: MemberType,
        role: MemberRole,
        permissions: List[Permission]
    ) -> bool:
        """检查用户是否有所有指定权限"""
        for permission in permissions:
            if not self.has_permission(user_id, member_type, role, permission):
                return False
        return True

    def get_permission_groups(self) -> Dict[str, List[Permission]]:
        """获取权限分组"""
        return PERMISSION_GROUPS.copy()

    def get_permissions_by_group(self, group_name: str) -> List[Permission]:
        """获取指定分组的权限"""
        return PERMISSION_GROUPS.get(group_name, [])

    def is_super_user(self, user_id: str) -> bool:
        """检查用户是否是超级管理员"""
        # 检查是否有 superuser 权限
        return self.has_permission(user_id, MemberType.HUMAN, MemberRole.ADMIN, Permission.SUPERUSER)

    def get_all_permissions(self) -> List[Permission]:
        """获取所有权限点列表"""
        return list(Permission)

    def export_role_config(self) -> Dict[str, Any]:
        """导出角色权限配置（用于备份或迁移）"""
        return {
            role.value: [p.value for p in permissions]
            for role, permissions in self._role_permissions.items()
        }

    def import_role_config(self, config: Dict[str, List[str]]) -> None:
        """导入角色权限配置"""
        for role_value, perm_values in config.items():
            try:
                role = MemberRole(role_value)
                permissions = {Permission(p) for p in perm_values}
                self._role_permissions[role] = permissions
            except (ValueError, KeyError) as e:
                # 忽略无效的配置
                continue


# 全局服务实例
permission_service = PermissionService()
