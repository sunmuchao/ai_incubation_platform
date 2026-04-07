"""
频道增强服务

提供频道管理增强功能：
- 频道角色细分
- 频道用户组
- 频道访问策略
- 频道 moderation 队列
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import uuid

from services.channel_service import channel_service
from services.user_group_service import user_group_service, UserGroup
from services.access_control_service import access_control_service, AccessDecision


class ChannelRole(str, Enum):
    """频道角色（扩展）"""
    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"
    VIP = "vip"  # 贵宾
    CONTRIBUTOR = "contributor"  # 贡献者
    MEMBER = "member"
    GUEST = "guest"  # 访客（受限）


# 扩展角色权限映射
CHANNEL_ROLE_PERMISSIONS = {
    ChannelRole.OWNER: ["all"],
    ChannelRole.ADMIN: ["manage_channel", "manage_members", "manage_posts", "manage_comments", "manage_roles", "view_analytics"],
    ChannelRole.MODERATOR: ["manage_posts", "manage_comments", "pin_post", "feature_post", "warn_user", "remove_content"],
    ChannelRole.VIP: ["create_post", "create_comment", "view_channel", "use_ai_tools", "create_events"],
    ChannelRole.CONTRIBUTOR: ["create_post", "create_comment", "view_channel", "edit_own_post_extended"],
    ChannelRole.MEMBER: ["create_post", "create_comment", "view_channel"],
    ChannelRole.GUEST: ["view_channel"],
}


class ChannelModerationQueue:
    """频道审核队列"""

    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self._pending_items: List[Dict[str, Any]] = []
        self._processed_items: List[Dict[str, Any]] = []

    def add_item(
        self,
        item_id: str,
        item_type: str,
        author_id: str,
        content: str,
        reason: str = "",
        priority: float = 0.5
    ) -> Dict[str, Any]:
        """添加审核项目"""
        item = {
            "id": str(uuid.uuid4()),
            "item_id": item_id,
            "item_type": item_type,  # post, comment
            "author_id": author_id,
            "content": content,
            "reason": reason,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now(),
            "processed_at": None,
            "processor_id": None,
            "decision": None,
            "notes": ""
        }
        self._pending_items.append(item)
        return item

    def get_pending_items(
        self,
        limit: int = 50,
        min_priority: float = 0.0
    ) -> List[Dict[str, Any]]:
        """获取待审核项目"""
        pending = [
            item for item in self._pending_items
            if item["priority"] >= min_priority
        ]
        # 按优先级排序
        pending = sorted(pending, key=lambda x: x["priority"], reverse=True)
        return pending[:limit]

    def process_item(
        self,
        item_id: str,
        processor_id: str,
        decision: str,  # approved, rejected
        notes: str = ""
    ) -> Optional[Dict[str, Any]]:
        """处理审核项目"""
        for i, item in enumerate(self._pending_items):
            if item["id"] == item_id:
                item["status"] = "processed"
                item["processed_at"] = datetime.now()
                item["processor_id"] = processor_id
                item["decision"] = decision
                item["notes"] = notes

                # 移到已处理列表
                self._processed_items.append(item)
                self._pending_items.pop(i)
                return item

        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        return {
            "channel_id": self.channel_id,
            "pending_count": len(self._pending_items),
            "processed_count": len(self._processed_items),
            "pending_by_type": self._count_by_type(self._pending_items),
            "processed_by_decision": self._count_by_decision(self._processed_items)
        }

    def _count_by_type(self, items: List[Dict]) -> Dict[str, int]:
        """按类型统计"""
        counts = {}
        for item in items:
            item_type = item["item_type"]
            counts[item_type] = counts.get(item_type, 0) + 1
        return counts

    def _count_by_decision(self, items: List[Dict]) -> Dict[str, int]:
        """按决策统计"""
        counts = {}
        for item in items:
            decision = item["decision"]
            counts[decision] = counts.get(decision, 0) + 1
        return counts


class ChannelEnhancementService:
    """频道增强服务"""

    def __init__(self):
        self._channel_queues: Dict[str, ChannelModerationQueue] = {}
        self._channel_user_groups: Dict[str, Set[str]] = {}  # channel_id -> group_ids
        self._channel_role_overrides: Dict[str, Dict[str, List[str]]] = {}  # channel_id -> {role -> permissions}

    def get_moderation_queue(self, channel_id: str) -> ChannelModerationQueue:
        """获取频道审核队列"""
        if channel_id not in self._channel_queues:
            self._channel_queues[channel_id] = ChannelModerationQueue(channel_id)
        return self._channel_queues[channel_id]

    def add_to_moderation_queue(
        self,
        channel_id: str,
        item_id: str,
        item_type: str,
        author_id: str,
        content: str,
        reason: str = "",
        priority: float = 0.5
    ) -> Dict[str, Any]:
        """添加项目到审核队列"""
        queue = self.get_moderation_queue(channel_id)
        return queue.add_item(
            item_id=item_id,
            item_type=item_type,
            author_id=author_id,
            content=content,
            reason=reason,
            priority=priority
        )

    def process_moderation_queue_item(
        self,
        channel_id: str,
        item_id: str,
        processor_id: str,
        decision: str,
        notes: str = ""
    ) -> Optional[Dict[str, Any]]:
        """处理审核队列项目"""
        queue = self.get_moderation_queue(channel_id)
        return queue.process_item(
            item_id=item_id,
            processor_id=processor_id,
            decision=decision,
            notes=notes
        )

    def get_moderation_queue_stats(self, channel_id: str) -> Dict[str, Any]:
        """获取审核队列统计"""
        queue = self.get_moderation_queue(channel_id)
        return queue.get_stats()

    def get_all_channel_queues_stats(self) -> Dict[str, Any]:
        """获取所有频道审核队列统计"""
        return {
            channel_id: queue.get_stats()
            for channel_id, queue in self._channel_queues.items()
        }

    # ==================== 频道用户组管理 ====================

    def set_channel_user_groups(
        self,
        channel_id: str,
        group_ids: List[str]
    ) -> Dict[str, Any]:
        """设置频道关联的用户组"""
        self._channel_user_groups[channel_id] = set(group_ids)
        return {
            "channel_id": channel_id,
            "group_ids": group_ids
        }

    def get_channel_user_groups(self, channel_id: str) -> List[str]:
        """获取频道关联的用户组"""
        return list(self._channel_user_groups.get(channel_id, set()))

    def add_channel_user_group(self, channel_id: str, group_id: str) -> bool:
        """添加频道关联用户组"""
        if channel_id not in self._channel_user_groups:
            self._channel_user_groups[channel_id] = set()
        self._channel_user_groups[channel_id].add(group_id)
        return True

    def remove_channel_user_group(self, channel_id: str, group_id: str) -> bool:
        """移除频道关联用户组"""
        if channel_id in self._channel_user_groups:
            self._channel_user_groups[channel_id].discard(group_id)
            return True
        return False

    def check_user_channel_access_via_groups(
        self,
        channel_id: str,
        user_id: str
    ) -> bool:
        """检查用户是否通过用户组访问频道"""
        channel_groups = self._channel_user_groups.get(channel_id, set())
        if not channel_groups:
            return False

        user_groups = user_group_service.get_user_groups(user_id)
        user_group_ids = {g.id for g in user_groups}

        # 检查是否有交集
        return bool(channel_groups & user_group_ids)

    # ==================== 频道角色权限覆盖 ====================

    def set_channel_role_permissions(
        self,
        channel_id: str,
        role: str,
        permissions: List[str]
    ) -> Dict[str, Any]:
        """设置频道特定角色权限（覆盖默认）"""
        if channel_id not in self._channel_role_overrides:
            self._channel_role_overrides[channel_id] = {}

        valid_roles = [r.value for r in ChannelRole]
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")

        self._channel_role_overrides[channel_id][role] = permissions

        return {
            "channel_id": channel_id,
            "role": role,
            "permissions": permissions
        }

    def get_channel_role_permissions(self, channel_id: str, role: str) -> List[str]:
        """获取频道角色权限（考虑覆盖）"""
        # 首先检查频道特定覆盖
        channel_overrides = self._channel_role_overrides.get(channel_id, {})
        if role in channel_overrides:
            return channel_overrides[role]

        # 返回默认权限
        try:
            channel_role = ChannelRole(role)
            return CHANNEL_ROLE_PERMISSIONS.get(channel_role, [])
        except ValueError:
            return []

    def get_channel_member_effective_permissions(
        self,
        channel_id: str,
        member_role: str
    ) -> List[str]:
        """获取频道成员的有效权限"""
        return self.get_channel_role_permissions(channel_id, member_role)

    # ==================== 频道访问增强 ====================

    def check_enhanced_channel_access(
        self,
        channel_id: str,
        user_id: str,
        user_type: str,
        user_role: str,
        channel_access_level: str,
        is_channel_member: bool,
        channel_member_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        增强的频道访问检查

        考虑：
        - 频道访问级别
        - 频道成员角色
        - 用户组关联
        """
        # 超级管理员 always allowed
        from services.permission_service import permission_service
        if permission_service.is_super_user(user_id):
            return {"allowed": True, "reason": "Superuser access"}

        # 检查频道角色权限
        if channel_member_role:
            role_perms = self.get_channel_role_permissions(channel_id, channel_member_role)
            if "all" in role_perms or "view_channel" in role_perms:
                return {"allowed": True, "reason": f"Channel {channel_member_role} access"}

        # 检查用户组访问
        if self.check_user_channel_access_via_groups(channel_id, user_id):
            return {"allowed": True, "reason": "User group access"}

        # 基础访问级别检查
        decision, details = access_control_service.check_channel_access(
            user_id=user_id,
            user_type=user_type,
            user_role=user_role,
            channel_id=channel_id,
            channel_access_level=channel_access_level,
            is_channel_member=is_channel_member
        )

        return {
            "allowed": decision == AccessDecision.ALLOW,
            "reason": details.get("reason", ""),
            "required": details.get("required")
        }

    # ==================== 频道统计增强 ====================

    def get_channel_enhanced_stats(self, channel_id: str) -> Dict[str, Any]:
        """获取频道增强统计"""
        from sqlalchemy import select, func
        from db.channel_models import DBChannelMember, DBChannelPost

        queue_stats = self.get_moderation_queue_stats(channel_id)
        channel_groups = self.get_channel_user_groups(channel_id)

        return {
            "channel_id": channel_id,
            "moderation_queue": queue_stats,
            "linked_user_groups": channel_groups,
            "has_custom_role_permissions": channel_id in self._channel_role_overrides
        }

    def get_channel_role_distribution(
        self,
        channel_id: str,
        members: List[Any]
    ) -> Dict[str, Any]:
        """获取频道角色分布"""
        distribution = {}
        for member in members:
            role = getattr(member, 'role', 'member')
            distribution[role] = distribution.get(role, 0) + 1

        return {
            "channel_id": channel_id,
            "total_members": len(members),
            "by_role": distribution
        }

    # ==================== 频道角色管理 ====================

    def get_available_channel_roles(self) -> List[Dict[str, Any]]:
        """获取可用的频道角色列表"""
        return [
            {
                "role": role.value,
                "default_permissions": CHANNEL_ROLE_PERMISSIONS.get(role, []),
                "description": self._get_role_description(role)
            }
            for role in ChannelRole
        ]

    def _get_role_description(self, role: ChannelRole) -> str:
        """获取角色描述"""
        descriptions = {
            ChannelRole.OWNER: "频道所有者，拥有所有权限",
            ChannelRole.ADMIN: "频道管理员，拥有管理权限",
            ChannelRole.MODERATOR: "频道版主，可以管理内容和成员",
            ChannelRole.VIP: "贵宾用户，享有特殊权限",
            ChannelRole.CONTRIBUTOR: "活跃贡献者，可以发布更多内容",
            ChannelRole.MEMBER: "普通成员",
            ChannelRole.GUEST: "访客，仅可查看内容"
        }
        return descriptions.get(role, "")

    def export_channel_config(self, channel_id: str) -> Dict[str, Any]:
        """导出频道配置"""
        return {
            "channel_id": channel_id,
            "user_groups": self.get_channel_user_groups(channel_id),
            "role_overrides": self._channel_role_overrides.get(channel_id, {}),
            "exported_at": datetime.now().isoformat()
        }

    def import_channel_config(
        self,
        channel_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """导入频道配置"""
        result = {"imported": [], "skipped": []}

        # 导入用户组关联
        if "user_groups" in config:
            self.set_channel_user_groups(channel_id, config["user_groups"])
            result["imported"].append("user_groups")

        # 导入角色权限覆盖
        if "role_overrides" in config:
            for role, permissions in config["role_overrides"].items():
                try:
                    self.set_channel_role_permissions(channel_id, role, permissions)
                    result["imported"].append(f"role_override:{role}")
                except ValueError as e:
                    result["skipped"].append(f"role_override:{role}: {str(e)}")

        result["imported_at"] = datetime.now().isoformat()
        return result


# 全局服务实例
channel_enhancement_service = ChannelEnhancementService()
