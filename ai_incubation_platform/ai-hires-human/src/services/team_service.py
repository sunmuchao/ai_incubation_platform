"""
团队权限系统 - 服务层。

提供组织管理、成员管理、角色权限管理等核心功能。
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.team import (
    OrganizationDB, TeamMemberDB, RoleDB, PermissionDB,
    TeamInvitationDB, OrganizationAuditLogDB, SYSTEM_ROLES
)


class TeamService:
    """团队服务。"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ==================== 组织管理 ====================

    async def create_organization(
        self,
        org_name: str,
        created_by: str,
        org_type: str = "enterprise",
        description: Optional[str] = None,
        contact_email: Optional[str] = None,
    ) -> OrganizationDB:
        """创建组织。"""
        org_id = str(uuid.uuid4())
        org = OrganizationDB(
            org_id=org_id,
            org_name=org_name,
            org_type=org_type,
            description=description,
            contact_email=contact_email,
            created_by=created_by,
        )
        self.db.add(org)

        # 创建者自动成为组织管理员
        admin_role = await self._get_or_create_system_role("org_admin")
        member = TeamMemberDB(
            member_id=str(uuid.uuid4()),
            org_id=org_id,
            user_id=created_by,
            role_id=admin_role.role_id,
            status="active",
        )
        self.db.add(member)

        # 记录审计日志
        await self._log_action(
            org_id=org_id,
            action="ORGANIZATION_CREATED",
            resource_type="organization",
            resource_id=org_id,
            actor_user_id=created_by,
            actor_role="org_admin",
            action_details={"org_name": org_name},
        )

        return org

    async def get_organization(self, org_id: str) -> Optional[OrganizationDB]:
        """获取组织详情。"""
        query = select(OrganizationDB).where(OrganizationDB.org_id == org_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_organizations(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[OrganizationDB]:
        """获取用户加入的所有组织。"""
        query = (
            select(OrganizationDB)
            .join(TeamMemberDB, OrganizationDB.org_id == TeamMemberDB.org_id)
            .where(TeamMemberDB.user_id == user_id)
            .where(TeamMemberDB.status == "active")
        )
        if status:
            query = query.where(OrganizationDB.status == status)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_organization(
        self,
        org_id: str,
        updates: Dict[str, Any],
        actor_user_id: str
    ) -> Optional[OrganizationDB]:
        """更新组织信息。"""
        org = await self.get_organization(org_id)
        if not org:
            return None

        for key, value in updates.items():
            if hasattr(org, key) and key not in ["org_id", "created_at", "updated_at"]:
                setattr(org, key, value)

        await self._log_action(
            org_id=org_id,
            action="ORGANIZATION_UPDATED",
            resource_type="organization",
            resource_id=org_id,
            actor_user_id=actor_user_id,
            action_details={"updates": updates},
        )

        return org

    async def delete_organization(
        self,
        org_id: str,
        actor_user_id: str
    ) -> bool:
        """删除组织（软删除）。"""
        org = await self.get_organization(org_id)
        if not org:
            return False

        org.status = "deleted"

        await self._log_action(
            org_id=org_id,
            action="ORGANIZATION_DELETED",
            resource_type="organization",
            resource_id=org_id,
            actor_user_id=actor_user_id,
        )

        return True

    # ==================== 成员管理 ====================

    async def add_member(
        self,
        org_id: str,
        user_id: str,
        role_id: str,
        invited_by: str
    ) -> TeamMemberDB:
        """添加组织成员。"""
        # 检查是否已存在
        existing = await self.get_member(org_id, user_id)
        if existing:
            raise ValueError(f"User {user_id} is already a member of organization {org_id}")

        member = TeamMemberDB(
            member_id=str(uuid.uuid4()),
            org_id=org_id,
            user_id=user_id,
            role_id=role_id,
            status="active",
            invited_by=invited_by,
            invited_at=datetime.now(),
        )
        self.db.add(member)

        await self._log_action(
            org_id=org_id,
            action="MEMBER_ADDED",
            resource_type="team_member",
            resource_id=member.member_id,
            actor_user_id=invited_by,
            action_details={"user_id": user_id, "role_id": role_id},
        )

        return member

    async def get_member(
        self,
        org_id: str,
        user_id: str
    ) -> Optional[TeamMemberDB]:
        """获取成员信息。"""
        query = select(TeamMemberDB).where(
            and_(
                TeamMemberDB.org_id == org_id,
                TeamMemberDB.user_id == user_id,
                TeamMemberDB.status == "active",
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_member_by_id(self, member_id: str) -> Optional[TeamMemberDB]:
        """通过成员 ID 获取成员信息。"""
        query = select(TeamMemberDB).where(TeamMemberDB.member_id == member_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_members(self, org_id: str) -> List[Dict[str, Any]]:
        """获取组织所有成员列表（含角色信息）。"""
        query = (
            select(TeamMemberDB, RoleDB.role_name_zh, RoleDB.permissions)
            .join(RoleDB, TeamMemberDB.role_id == RoleDB.role_id)
            .where(TeamMemberDB.org_id == org_id)
            .where(TeamMemberDB.status == "active")
        )
        result = await self.db.execute(query)

        members = []
        for row in result.fetchall():
            member = row[0]
            members.append({
                "member_id": member.member_id,
                "user_id": member.user_id,
                "role_id": member.role_id,
                "role_name": row[1],
                "permissions": row[2],
                "status": member.status,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            })
        return members

    async def update_member_role(
        self,
        org_id: str,
        user_id: str,
        new_role_id: str,
        actor_user_id: str
    ) -> bool:
        """更新成员角色。"""
        member = await self.get_member(org_id, user_id)
        if not member:
            return False

        old_role_id = member.role_id
        member.role_id = new_role_id

        await self._log_action(
            org_id=org_id,
            action="MEMBER_ROLE_UPDATED",
            resource_type="team_member",
            resource_id=member.member_id,
            actor_user_id=actor_user_id,
            action_details={
                "user_id": user_id,
                "old_role_id": old_role_id,
                "new_role_id": new_role_id,
            },
        )

        return True

    async def remove_member(
        self,
        org_id: str,
        user_id: str,
        actor_user_id: str
    ) -> bool:
        """移除组织成员（软删除）。"""
        member = await self.get_member(org_id, user_id)
        if not member:
            return False

        member.status = "removed"

        await self._log_action(
            org_id=org_id,
            action="MEMBER_REMOVED",
            resource_type="team_member",
            resource_id=member.member_id,
            actor_user_id=actor_user_id,
            action_details={"user_id": user_id},
        )

        return True

    # ==================== 邀请管理 ====================

    async def create_invitation(
        self,
        org_id: str,
        invitee_email: str,
        invitee_name: Optional[str],
        role_id: str,
        invited_by: str
    ) -> TeamInvitationDB:
        """创建团队邀请。"""
        invitation_id = str(uuid.uuid4())
        invitation = TeamInvitationDB(
            invitation_id=invitation_id,
            org_id=org_id,
            invitee_email=invitee_email,
            invitee_name=invitee_name,
            role_id=role_id,
            invited_by=invited_by,
            expires_at=datetime.now() + timedelta(days=7),  # 7 天有效期
        )
        self.db.add(invitation)

        return invitation

    async def get_invitation(self, invitation_id: str) -> Optional[TeamInvitationDB]:
        """获取邀请详情。"""
        query = select(TeamInvitationDB).where(
            TeamInvitationDB.invitation_id == invitation_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def accept_invitation(
        self,
        invitation_id: str,
        user_id: str
    ) -> bool:
        """接受邀请。"""
        invitation = await self.get_invitation(invitation_id)
        if not invitation:
            return False

        if invitation.status != "pending":
            raise ValueError("Invitation is no longer pending")

        if datetime.now() > invitation.expires_at:
            invitation.status = "expired"
            raise ValueError("Invitation has expired")

        # 创建成员记录
        await self.add_member(
            org_id=invitation.org_id,
            user_id=user_id,
            role_id=invitation.role_id,
            invited_by=invitation.invited_by,
        )

        invitation.status = "accepted"
        invitation.accepted_at = datetime.now()

        return True

    async def list_invitations(self, org_id: str) -> List[TeamInvitationDB]:
        """获取组织的邀请列表。"""
        query = select(TeamInvitationDB).where(
            TeamInvitationDB.org_id == org_id
        ).order_by(TeamInvitationDB.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== 角色权限管理 ====================

    async def get_role(self, role_id: str) -> Optional[RoleDB]:
        """获取角色详情。"""
        query = select(RoleDB).where(RoleDB.role_id == role_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_roles(
        self,
        org_id: Optional[str] = None,
        include_system: bool = True
    ) -> List[RoleDB]:
        """获取角色列表。"""
        query = select(RoleDB)
        if include_system:
            if org_id:
                query = query.where(
                    (RoleDB.org_id == org_id) | (RoleDB.org_id.is_(None))
                )
        else:
            query = query.where(RoleDB.org_id == org_id)

        query = query.order_by(RoleDB.role_type.desc(), RoleDB.role_name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_role(
        self,
        org_id: str,
        role_name: str,
        role_name_zh: str,
        permissions: List[str],
        created_by: str,
        description: Optional[str] = None
    ) -> RoleDB:
        """创建自定义角色。"""
        role_id = str(uuid.uuid4())
        role = RoleDB(
            role_id=role_id,
            role_name=role_name,
            role_name_zh=role_name_zh,
            role_type="custom",
            org_id=org_id,
            description=description,
            permissions=permissions,
            created_by=created_by,
        )
        self.db.add(role)

        return role

    async def update_role(
        self,
        role_id: str,
        updates: Dict[str, Any]
    ) -> Optional[RoleDB]:
        """更新角色信息。"""
        role = await self.get_role(role_id)
        if not role:
            return None

        if not role.is_deletable:
            raise ValueError("Cannot modify system role")

        for key, value in updates.items():
            if hasattr(role, key) and key not in ["role_id", "role_type", "org_id"]:
                setattr(role, key, value)

        return role

    async def delete_role(self, role_id: str) -> bool:
        """删除角色。"""
        role = await self.get_role(role_id)
        if not role:
            return False

        if not role.is_deletable:
            raise ValueError("Cannot delete system role")

        # 检查是否有成员使用该角色
        member_query = select(TeamMemberDB).where(
            TeamMemberDB.role_id == role_id
        ).limit(1)
        result = await self.db.execute(member_query)
        if result.scalar_one_or_none():
            raise ValueError("Cannot delete role that is in use")

        self.db.delete(role)
        return True

    async def check_permission(
        self,
        org_id: str,
        user_id: str,
        permission: str
    ) -> bool:
        """检查用户是否有指定权限。"""
        member = await self.get_member(org_id, user_id)
        if not member:
            return False

        role = await self.get_role(member.role_id)
        if not role:
            return False

        return permission in role.permissions

    async def get_user_permissions(
        self,
        org_id: str,
        user_id: str
    ) -> List[str]:
        """获取用户在组织内的所有权限。"""
        member = await self.get_member(org_id, user_id)
        if not member:
            return []

        role = await self.get_role(member.role_id)
        if not role:
            return []

        return role.permissions

    async def get_user_roles(
        self,
        org_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """获取用户在组织内的角色信息。"""
        member = await self.get_member(org_id, user_id)
        if not member:
            return {"is_member": False}

        role = await self.get_role(member.role_id)
        return {
            "is_member": True,
            "member_id": member.member_id,
            "role_id": role.role_id if role else None,
            "role_name": role.role_name if role else None,
            "role_name_zh": role.role_name_zh if role else None,
            "permissions": role.permissions if role else [],
        }

    # ==================== 审计日志 ====================

    async def _log_action(
        self,
        org_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        actor_user_id: str,
        actor_role: Optional[str] = None,
        action_details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """记录审计日志（内部方法）。"""
        log = OrganizationAuditLogDB(
            log_id=str(uuid.uuid4()),
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action_details=action_details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)

    async def list_audit_logs(
        self,
        org_id: str,
        limit: int = 100,
        action: Optional[str] = None
    ) -> List[OrganizationAuditLogDB]:
        """获取审计日志列表。"""
        query = select(OrganizationAuditLogDB).where(
            OrganizationAuditLogDB.org_id == org_id
        ).order_by(OrganizationAuditLogDB.created_at.desc()).limit(limit)

        if action:
            query = query.where(OrganizationAuditLogDB.action == action)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== 工具方法 ====================

    async def _get_or_create_system_role(self, role_key: str) -> RoleDB:
        """获取或创建系统角色。"""
        # 先查询是否已存在
        query = select(RoleDB).where(RoleDB.role_name == role_key)
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # 创建系统角色
        role_info = SYSTEM_ROLES.get(role_key)
        if not role_info:
            raise ValueError(f"Unknown system role: {role_key}")

        role_id = str(uuid.uuid4())
        role = RoleDB(
            role_id=role_id,
            role_name=role_info["role_name"],
            role_name_zh=role_info["role_name_zh"],
            role_type="system",
            org_id=None,
            description=role_info["description"],
            permissions=role_info["permissions"],
            is_deletable=False,
        )
        self.db.add(role)
        return role

    async def initialize_system_roles(self):
        """初始化所有系统角色。"""
        for role_key in SYSTEM_ROLES.keys():
            await self._get_or_create_system_role(role_key)
