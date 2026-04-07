"""
用户组管理服务

提供跨频道的用户组功能：
- 用户组创建与管理
- 组成员资格
- 组权限继承
- 预设用户组
"""
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum
import uuid
import hashlib


class UserGroupType(str, Enum):
    """用户组类型"""
    SYSTEM = "system"  # 系统预设组（不可删除）
    CUSTOM = "custom"  # 自定义组
    AUTO = "auto"  # 自动组（基于条件自动加入）


class UserGroup:
    """用户组"""

    def __init__(
        self,
        name: str,
        group_type: UserGroupType = UserGroupType.CUSTOM,
        description: str = "",
        permissions: List[str] = None,
        auto_join_conditions: Dict[str, Any] = None
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.group_type = group_type
        self.description = description
        self.permissions = permissions or []
        self.auto_join_conditions = auto_join_conditions or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.is_active = True

        # 成员
        self.member_ids: Set[str] = set()

    def add_member(self, user_id: str) -> bool:
        """添加成员"""
        if user_id in self.member_ids:
            return False
        self.member_ids.add(user_id)
        self.updated_at = datetime.now()
        return True

    def remove_member(self, user_id: str) -> bool:
        """移除成员"""
        if user_id not in self.member_ids:
            return False
        self.member_ids.discard(user_id)
        self.updated_at = datetime.now()
        return True

    def has_member(self, user_id: str) -> bool:
        """检查是否是成员"""
        return user_id in self.member_ids

    def add_permissions(self, permissions: List[str]) -> None:
        """添加权限"""
        for perm in permissions:
            if perm not in self.permissions:
                self.permissions.append(perm)
        self.updated_at = datetime.now()

    def remove_permissions(self, permissions: List[str]) -> None:
        """移除权限"""
        self.permissions = [p for p in self.permissions if p not in permissions]
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "group_type": self.group_type.value,
            "description": self.description,
            "permissions": self.permissions,
            "member_count": len(self.member_ids),
            "auto_join_conditions": self.auto_join_conditions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active
        }


class UserGroupService:
    """用户组服务"""

    def __init__(self):
        self._groups: Dict[str, UserGroup] = {}
        self._user_groups: Dict[str, Set[str]] = {}  # user_id -> group_ids
        self._name_index: Dict[str, str] = {}  # name -> group_id

        # 初始化系统预设组
        self._init_system_groups()

    def _init_system_groups(self) -> None:
        """初始化系统预设组"""
        system_groups = [
            UserGroup(
                name="verified_users",
                group_type=UserGroupType.SYSTEM,
                description="已认证用户",
                permissions=["post_without_review", "higher_rate_limit"]
            ),
            UserGroup(
                name="new_members",
                group_type=UserGroupType.AUTO,
                description="新成员（加入少于 7 天）",
                auto_join_conditions={"join_days_less_than": 7},
                permissions=[]
            ),
            UserGroup(
                name="content_creators",
                group_type=UserGroupType.CUSTOM,
                description="内容创作者（发帖数>10）",
                auto_join_conditions={"post_count_greater_than": 10},
                permissions=["use_advanced_ai_tools", "create_polls"]
            ),
            UserGroup(
                name="trusted_members",
                group_type=UserGroupType.CUSTOM,
                description="可信成员（高信誉分数）",
                permissions=["edit_own_post_extended", "create_events"]
            ),
            UserGroup(
                name="beta_testers",
                group_type=UserGroupType.CUSTOM,
                description="Beta 测试员",
                permissions=["access_beta_features", "report_bugs"]
            )
        ]

        for group in system_groups:
            self._groups[group.id] = group
            self._name_index[group.name] = group.id

    def create_group(
        self,
        name: str,
        description: str = "",
        group_type: UserGroupType = UserGroupType.CUSTOM,
        permissions: List[str] = None,
        creator_id: Optional[str] = None
    ) -> UserGroup:
        """创建用户组"""
        # 检查名称是否已存在
        if name.lower() in self._name_index:
            raise ValueError(f"Group name '{name}' already exists")

        group = UserGroup(
            name=name,
            group_type=group_type,
            description=description,
            permissions=permissions or []
        )
        self._groups[group.id] = group
        self._name_index[name.lower()] = group.id

        return group

    def get_group(self, group_id: str) -> Optional[UserGroup]:
        """获取用户组"""
        return self._groups.get(group_id)

    def get_group_by_name(self, name: str) -> Optional[UserGroup]:
        """通过名称获取用户组"""
        group_id = self._name_index.get(name.lower())
        if group_id:
            return self._groups.get(group_id)
        return None

    def list_groups(
        self,
        group_type: Optional[UserGroupType] = None,
        include_inactive: bool = False
    ) -> List[UserGroup]:
        """获取用户组列表"""
        groups = list(self._groups.values())

        if group_type:
            groups = [g for g in groups if g.group_type == group_type]

        if not include_inactive:
            groups = [g for g in groups if g.is_active]

        return sorted(groups, key=lambda g: g.name)

    def update_group(
        self,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None
    ) -> Optional[UserGroup]:
        """更新用户组"""
        group = self._groups.get(group_id)
        if not group:
            return None

        # 系统组不能修改名称
        if group.group_type == UserGroupType.SYSTEM and name and name != group.name:
            raise ValueError("Cannot rename system groups")

        if name:
            # 更新名称索引
            if group.name.lower() in self._name_index:
                del self._name_index[group.name.lower()]
            self._name_index[name.lower()] = group_id
            group.name = name

        if description is not None:
            group.description = description

        if permissions is not None:
            group.permissions = permissions

        group.updated_at = datetime.now()
        return group

    def delete_group(self, group_id: str) -> bool:
        """删除用户组"""
        group = self._groups.get(group_id)
        if not group:
            return False

        # 系统组不能删除
        if group.group_type == UserGroupType.SYSTEM:
            raise ValueError("Cannot delete system groups")

        # 从所有成员中移除
        for user_id in list(group.member_ids):
            self._user_groups.get(user_id, set()).discard(group_id)

        # 删除索引
        if group.name.lower() in self._name_index:
            del self._name_index[group.name.lower()]

        del self._groups[group_id]
        return True

    def add_member_to_group(self, group_id: str, user_id: str) -> bool:
        """添加用户到用户组"""
        group = self._groups.get(group_id)
        if not group:
            return False

        if not group.add_member(user_id):
            return False  # 已经是成员

        # 更新用户索引
        if user_id not in self._user_groups:
            self._user_groups[user_id] = set()
        self._user_groups[user_id].add(group_id)

        return True

    def remove_member_from_group(self, group_id: str, user_id: str) -> bool:
        """从用户组移除用户"""
        group = self._groups.get(group_id)
        if not group:
            return False

        if not group.remove_member(user_id):
            return False

        # 更新用户索引
        if user_id in self._user_groups:
            self._user_groups[user_id].discard(group_id)

        return True

    def get_user_groups(self, user_id: str) -> List[UserGroup]:
        """获取用户所属的所有用户组"""
        group_ids = self._user_groups.get(user_id, set())
        groups = [self._groups[gid] for gid in group_ids if gid in self._groups]
        return groups

    def get_user_permissions_from_groups(self, user_id: str) -> List[str]:
        """获取用户从用户组继承的所有权限"""
        groups = self.get_user_groups(user_id)
        permissions = set()
        for group in groups:
            permissions.update(group.permissions)
        return list(permissions)

    def get_group_members(
        self,
        group_id: str,
        limit: int = 100
    ) -> List[str]:
        """获取组成员列表"""
        group = self._groups.get(group_id)
        if not group:
            return []
        return list(group.member_ids)[:limit]

    def auto_assign_groups(self, user_id: str, user_profile: Dict[str, Any]) -> List[str]:
        """
        根据条件自动分配用户组

        Args:
            user_id: 用户 ID
            user_profile: 用户档案（包含 join_date, post_count 等）

        Returns:
            自动加入的用户组 ID 列表
        """
        assigned_groups = []

        for group in self._groups.values():
            if not group.auto_join_conditions:
                continue

            if group.has_member(user_id):
                continue  # 已经是成员

            # 检查是否满足条件
            should_join = True
            conditions = group.auto_join_conditions

            if "join_days_less_than" in conditions:
                join_date = user_profile.get("join_date")
                if join_date:
                    join_days = (datetime.now() - join_date).days
                    if join_days >= conditions["join_days_less_than"]:
                        should_join = False

            if "post_count_greater_than" in conditions:
                post_count = user_profile.get("post_count", 0)
                if post_count <= conditions["post_count_greater_than"]:
                    should_join = False

            if should_join:
                self.add_member_to_group(group_id, user_id)
                assigned_groups.append(group_id)

        return assigned_groups

    def get_group_stats(self) -> Dict[str, Any]:
        """获取用户组统计"""
        groups = list(self._groups.values())

        return {
            "total_groups": len(groups),
            "system_groups": len([g for g in groups if g.group_type == UserGroupType.SYSTEM]),
            "custom_groups": len([g for g in groups if g.group_type == UserGroupType.CUSTOM]),
            "auto_groups": len([g for g in groups if g.group_type == UserGroupType.AUTO]),
            "total_memberships": sum(len(g.member_ids) for g in groups),
            "groups": [
                {
                    "id": g.id,
                    "name": g.name,
                    "member_count": len(g.member_ids),
                    "group_type": g.group_type.value
                }
                for g in groups
            ]
        }

    def export_group_config(self) -> Dict[str, Any]:
        """导出用户组配置"""
        return {
            "groups": [
                {
                    "name": g.name,
                    "group_type": g.group_type.value,
                    "description": g.description,
                    "permissions": g.permissions,
                    "auto_join_conditions": g.auto_join_conditions
                }
                for g in self._groups.values()
                if g.group_type != UserGroupType.SYSTEM
            ],
            "exported_at": datetime.now().isoformat()
        }

    def import_group_config(self, config: Dict[str, Any], operator_id: str) -> Dict[str, Any]:
        """导入用户组配置"""
        imported = []
        skipped = []

        for group_config in config.get("groups", []):
            try:
                # 检查是否已存在
                existing = self.get_group_by_name(group_config["name"])
                if existing:
                    skipped.append(group_config["name"])
                    continue

                group_type = UserGroupType(group_config.get("group_type", "custom"))
                self.create_group(
                    name=group_config["name"],
                    description=group_config.get("description", ""),
                    group_type=group_type,
                    permissions=group_config.get("permissions", []),
                    creator_id=operator_id
                )
                imported.append(group_config["name"])
            except Exception as e:
                skipped.append(f"{group_config.get('name', 'unknown')}: {str(e)}")

        return {
            "imported": imported,
            "skipped": skipped,
            "imported_at": datetime.now().isoformat()
        }


# 全局服务实例
user_group_service = UserGroupService()
