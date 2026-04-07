"""
内容访问控制服务

提供基于权限的内容访问控制：
- 频道访问检查
- 内容访问检查
- 权限要求配置
- 访问策略管理
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
import uuid

from services.permission_service import permission_service, Permission
from services.permission_audit_service import permission_audit_service, AuditEventType


class AccessDecision(str, Enum):
    """访问决策"""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"  # 需要审核
    REQUIRE_PAYMENT = "require_payment"  # 需要付费


class AccessRequirement:
    """访问要求"""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        required_permissions: List[str] = None,
        required_roles: List[str] = None,
        required_groups: List[str] = None,
        minimum_reputation: float = None,
        custom_condition: str = None
    ):
        self.id = str(uuid.uuid4())
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.required_permissions = required_permissions or []
        self.required_roles = required_roles or []
        self.required_groups = required_groups or []
        self.minimum_reputation = minimum_reputation
        self.custom_condition = custom_condition
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "required_permissions": self.required_permissions,
            "required_roles": self.required_roles,
            "required_groups": self.required_groups,
            "minimum_reputation": self.minimum_reputation,
            "custom_condition": self.custom_condition
        }


class AccessControlService:
    """访问控制服务"""

    def __init__(self):
        self._requirements: Dict[str, AccessRequirement] = {}  # resource_key -> requirement
        self._resource_requirements: Dict[str, List[AccessRequirement]] = {}  # resource_type -> requirements

        # 默认权限要求映射
        self._default_permission_map = {
            ("channel", "view"): ["view_channel"],
            ("channel", "post"): ["create_post"],
            ("channel", "comment"): ["create_comment"],
            ("post", "view"): ["view_post"],
            ("post", "edit"): ["edit_own_post"],
            ("post", "delete"): ["delete_own_post"],
            ("comment", "view"): ["view_comment"],
            ("comment", "edit"): ["edit_own_comment"],
            ("comment", "delete"): ["delete_own_comment"],
        }

    def _get_resource_key(self, resource_type: str, resource_id: str) -> str:
        """生成资源键"""
        return f"{resource_type}:{resource_id}"

    def set_resource_permissions(
        self,
        resource_type: str,
        resource_id: str,
        required_permissions: List[str]
    ) -> AccessRequirement:
        """设置资源的权限要求"""
        key = self._get_resource_key(resource_type, resource_id)

        requirement = AccessRequirement(
            resource_type=resource_type,
            resource_id=resource_id,
            required_permissions=required_permissions
        )

        self._requirements[key] = requirement

        # 更新资源类型索引
        if resource_type not in self._resource_requirements:
            self._resource_requirements[resource_type] = []
        self._resource_requirements[resource_type].append(requirement)

        return requirement

    def get_resource_permissions(
        self,
        resource_type: str,
        resource_id: str
    ) -> Optional[AccessRequirement]:
        """获取资源的权限要求"""
        key = self._get_resource_key(resource_type, resource_id)
        return self._requirements.get(key)

    def check_access(
        self,
        user_id: str,
        user_type: str,
        user_role: str,
        resource_type: str,
        resource_id: str,
        action: str = "view",
        user_groups: List[str] = None,
        user_reputation: float = None,
        ip_address: Optional[str] = None
    ) -> Tuple[AccessDecision, Dict[str, Any]]:
        """
        检查用户是否有权限访问资源

        Returns:
            (决策，详情)
        """
        from services.user_group_service import user_group_service

        # 获取资源权限要求
        key = self._get_resource_key(resource_type, resource_id)
        requirement = self._requirements.get(key)

        # 如果没有特定要求，使用默认映射
        if not requirement:
            default_perms = self._default_permission_map.get((resource_type, action))
            if default_perms:
                requirement = AccessRequirement(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    required_permissions=default_perms
                )

        if not requirement:
            # 没有要求，允许访问
            return AccessDecision.ALLOW, {"reason": "No access requirements"}

        # 检查权限
        denied_reasons = []
        missing_permissions = []

        for perm in requirement.required_permissions:
            try:
                has_perm = permission_service.has_permission(
                    user_id=user_id,
                    member_type=user_type,
                    role=user_role,
                    permission=Permission(perm)
                )
                if not has_perm:
                    missing_permissions.append(perm)
            except ValueError:
                missing_permissions.append(perm)

        if missing_permissions:
            denied_reasons.append(f"Missing permissions: {', '.join(missing_permissions)}")

        # 检查角色要求
        if requirement.required_roles:
            if user_role not in requirement.required_roles:
                denied_reasons.append(f"Required roles: {', '.join(requirement.required_roles)}")

        # 检查组要求
        if requirement.required_groups:
            user_groups = user_groups or []
            if not any(g in user_groups for g in requirement.required_groups):
                denied_reasons.append(f"Required groups: {', '.join(requirement.required_groups)}")

        # 检查信誉分数
        if requirement.minimum_reputation and user_reputation:
            if user_reputation < requirement.minimum_reputation:
                denied_reasons.append(f"Minimum reputation required: {requirement.minimum_reputation}")

        # 做出决策
        if denied_reasons:
            # 记录访问拒绝日志
            permission_audit_service.log_content_access_denied(
                user_id=user_id,
                content_type=resource_type,
                content_id=resource_id,
                required_permission=", ".join(requirement.required_permissions),
                user_role=user_role,
                ip_address=ip_address
            )

            return AccessDecision.DENY, {
                "reason": "Access denied",
                "details": denied_reasons,
                "missing_permissions": missing_permissions
            }

        return AccessDecision.ALLOW, {"reason": "Access granted"}

    def check_channel_access(
        self,
        user_id: str,
        user_type: str,
        user_role: str,
        channel_id: str,
        channel_access_level: str,
        is_channel_member: bool,
        user_groups: List[str] = None
    ) -> Tuple[AccessDecision, Dict[str, Any]]:
        """
        检查频道访问权限

        基于频道访问级别：
        - public: 所有人可访问
        - member_only: 仅社区成员可访问
        - private: 仅邀请可访问
        """
        # 公共频道，所有人都可以访问
        if channel_access_level == "public":
            return AccessDecision.ALLOW, {"reason": "Public channel"}

        # 检查是否是超级管理员
        if permission_service.is_super_user(user_id):
            return AccessDecision.ALLOW, {"reason": "Superuser access"}

        # 成员限定频道
        if channel_access_level == "member_only":
            if user_type == "human" and is_channel_member:
                return AccessDecision.ALLOW, {"reason": "Channel member"}
            # 检查是否在社区用户组中
            if user_groups:
                return AccessDecision.ALLOW, {"reason": "Community member group"}
            return AccessDecision.DENY, {
                "reason": "Member only channel",
                "required": "Join the community or channel"
            }

        # 私有频道
        if channel_access_level == "private":
            if is_channel_member:
                return AccessDecision.ALLOW, {"reason": "Invited member"}
            return AccessDecision.DENY, {
                "reason": "Private channel",
                "required": "Invitation required"
            }

        return AccessDecision.DENY, {"reason": "Unknown access level"}

    def check_post_permission(
        self,
        user_id: str,
        user_type: str,
        user_role: str,
        post_id: str,
        action: str,
        post_author_id: str,
        channel_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[AccessDecision, Dict[str, Any]]:
        """
        检查帖子操作权限

        Args:
            action: view, edit, delete, pin, feature
        """
        # 查看权限
        if action == "view":
            decision, details = self.check_access(
                user_id=user_id,
                user_type=user_type,
                user_role=user_role,
                resource_type="post",
                resource_id=post_id,
                action="view",
                ip_address=ip_address
            )
            return decision, details

        # 编辑权限：作者本人或有 edit_any_post 权限
        if action == "edit":
            if user_id == post_author_id:
                decision, details = self.check_access(
                    user_id=user_id,
                    user_type=user_type,
                    user_role=user_role,
                    resource_type="post",
                    resource_id=post_id,
                    action="edit",
                    ip_address=ip_address
                )
                return decision, details
            else:
                # 检查是否有编辑他人帖子的权限
                has_perm = permission_service.has_permission(
                    user_id=user_id,
                    member_type=user_type,
                    role=user_role,
                    permission=Permission.EDIT_ANY_POST
                )
                if has_perm:
                    return AccessDecision.ALLOW, {"reason": "Has EDIT_ANY_POST permission"}
                return AccessDecision.DENY, {"reason": "Not the author and no EDIT_ANY_POST permission"}

        # 删除权限：作者本人或有 delete_any_post 权限
        if action == "delete":
            if user_id == post_author_id:
                decision, details = self.check_access(
                    user_id=user_id,
                    user_type=user_type,
                    user_role=user_role,
                    resource_type="post",
                    resource_id=post_id,
                    action="delete",
                    ip_address=ip_address
                )
                return decision, details
            else:
                has_perm = permission_service.has_permission(
                    user_id=user_id,
                    member_type=user_type,
                    role=user_role,
                    permission=Permission.DELETE_ANY_POST
                )
                if has_perm:
                    return AccessDecision.ALLOW, {"reason": "Has DELETE_ANY_POST permission"}
                return AccessDecision.DENY, {"reason": "Not the author and no DELETE_ANY_POST permission"}

        # 置顶/加精权限
        if action in ["pin", "feature"]:
            required_perm = Permission.PIN_POST if action == "pin" else Permission.FEATURE_POST
            # 注意：需要在 permission_service 中添加 FEATURE_POST
            has_perm = permission_service.has_permission(
                user_id=user_id,
                member_type=user_type,
                role=user_role,
                permission=required_perm
            )
            if has_perm:
                return AccessDecision.ALLOW, {"reason": f"Has {required_perm.value} permission"}
            return AccessDecision.DENY, {"reason": f"Missing {required_perm.value} permission"}

        return AccessDecision.DENY, {"reason": f"Unknown action: {action}"}

    def get_user_accessible_resources(
        self,
        user_id: str,
        user_type: str,
        user_role: str,
        resource_type: str,
        user_groups: List[str] = None
    ) -> List[str]:
        """获取用户可访问的资源列表"""
        accessible = []

        requirements = self._resource_requirements.get(resource_type, [])
        for req in requirements:
            decision, _ = self.check_access(
                user_id=user_id,
                user_type=user_type,
                user_role=user_role,
                resource_type=resource_type,
                resource_id=req.resource_id,
                user_groups=user_groups
            )
            if decision == AccessDecision.ALLOW:
                accessible.append(req.resource_id)

        return accessible

    def create_access_policy(
        self,
        resource_type: str,
        resource_id: str,
        policy_config: Dict[str, Any]
    ) -> AccessRequirement:
        """创建访问策略"""
        requirement = AccessRequirement(
            resource_type=resource_type,
            resource_id=resource_id,
            required_permissions=policy_config.get("required_permissions", []),
            required_roles=policy_config.get("required_roles", []),
            required_groups=policy_config.get("required_groups", []),
            minimum_reputation=policy_config.get("minimum_reputation"),
            custom_condition=policy_config.get("custom_condition")
        )

        key = self._get_resource_key(resource_type, resource_id)
        self._requirements[key] = requirement

        return requirement

    def get_access_policy_stats(self) -> Dict[str, Any]:
        """获取访问策略统计"""
        return {
            "total_policies": len(self._requirements),
            "by_resource_type": {
                rt: len(reqs)
                for rt, reqs in self._resource_requirements.items()
            }
        }


# 全局服务实例
access_control_service = AccessControlService()
