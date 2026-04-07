"""
团队权限系统 - API 接口。

提供组织管理、成员管理、角色权限管理等 API。
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from services.team_service import TeamService

router = APIRouter(prefix="/api/team", tags=["team"])


# ==================== 请求/响应模型 ====================

class OrganizationCreateRequest(BaseModel):
    """创建组织请求。"""
    org_name: str = Field(..., min_length=1, max_length=200, description="组织名称")
    org_type: str = Field(default="enterprise", description="组织类型")
    description: Optional[str] = Field(default=None, max_length=2000)
    contact_email: Optional[EmailStr] = Field(default=None)


class OrganizationResponse(BaseModel):
    """组织响应。"""
    org_id: str
    org_name: str
    org_type: str
    description: Optional[str]
    contact_email: Optional[str]
    status: str
    is_verified: bool
    max_members: int
    created_at: str
    member_count: Optional[int] = None


class MemberResponse(BaseModel):
    """成员响应。"""
    member_id: str
    user_id: str
    role_id: str
    role_name: str
    role_name_zh: str
    permissions: List[str]
    status: str
    joined_at: str


class RoleResponse(BaseModel):
    """角色响应。"""
    role_id: str
    role_name: str
    role_name_zh: str
    role_type: str
    description: Optional[str]
    permissions: List[str]
    is_enabled: bool
    is_deletable: bool


class InvitationCreateRequest(BaseModel):
    """创建邀请请求。"""
    invitee_email: EmailStr
    invitee_name: Optional[str] = None
    role_id: str


class InvitationResponse(BaseModel):
    """邀请响应。"""
    invitation_id: str
    invitee_email: str
    invitee_name: Optional[str]
    role_id: str
    role_name: str
    status: str
    invited_by: str
    invited_at: str
    expires_at: str


class PermissionCheckResponse(BaseModel):
    """权限检查响应。"""
    has_permission: bool
    permission: str
    org_id: str
    user_id: str


class UserRoleResponse(BaseModel):
    """用户角色响应。"""
    is_member: bool
    member_id: Optional[str] = None
    role_id: Optional[str] = None
    role_name: Optional[str] = None
    role_name_zh: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class AuditLogResponse(BaseModel):
    """审计日志响应。"""
    log_id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    actor_user_id: str
    actor_role: Optional[str]
    action_details: Dict[str, Any]
    created_at: str


# ==================== 组织管理 API ====================

@router.post("/organizations", response_model=OrganizationResponse, summary="创建组织")
async def create_organization(
    request: OrganizationCreateRequest,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    创建新的组织。

    创建者自动成为组织管理员。
    """
    service = TeamService(db)

    org = await service.create_organization(
        org_name=request.org_name,
        org_type=request.org_type,
        description=request.description,
        contact_email=request.contact_email,
        created_by=current_user_id,
    )

    return OrganizationResponse(
        org_id=org.org_id,
        org_name=org.org_name,
        org_type=org.org_type,
        description=org.description,
        contact_email=org.contact_email,
        status=org.status,
        is_verified=org.is_verified,
        max_members=org.max_members,
        created_at=org.created_at.isoformat(),
    )


@router.get("/organizations", response_model=List[OrganizationResponse], summary="获取我的组织列表")
async def list_organizations(
    current_user_id: str = Query(..., description="当前用户 ID"),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session)
):
    """获取当前用户加入的所有组织。"""
    service = TeamService(db)
    orgs = await service.list_organizations(current_user_id, status)

    return [
        OrganizationResponse(
            org_id=org.org_id,
            org_name=org.org_name,
            org_type=org.org_type,
            description=org.description,
            contact_email=org.contact_email,
            status=org.status,
            is_verified=org.is_verified,
            max_members=org.max_members,
            created_at=org.created_at.isoformat(),
        )
        for org in orgs
    ]


@router.get("/organizations/{org_id}", response_model=OrganizationResponse, summary="获取组织详情")
async def get_organization(
    org_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """获取指定组织的详细信息。"""
    service = TeamService(db)

    # 检查权限
    member_info = await service.get_user_roles(org_id, current_user_id)
    if not member_info["is_member"]:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this organization"
        )

    org = await service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # 获取成员数量
    members = await service.list_members(org_id)

    return OrganizationResponse(
        org_id=org.org_id,
        org_name=org.org_name,
        org_type=org.org_type,
        description=org.description,
        contact_email=org.contact_email,
        status=org.status,
        is_verified=org.is_verified,
        max_members=org.max_members,
        created_at=org.created_at.isoformat(),
        member_count=len(members),
    )


@router.put("/organizations/{org_id}", response_model=OrganizationResponse, summary="更新组织")
async def update_organization(
    org_id: str,
    updates: Dict[str, Any],
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """更新组织信息。"""
    service = TeamService(db)

    # 检查管理员权限
    member_info = await service.get_user_roles(org_id, current_user_id)
    if "org_admin" not in (member_info.get("role_name", "")):
        raise HTTPException(
            status_code=403,
            detail="Only organization admin can update organization"
        )

    org = await service.update_organization(org_id, updates, current_user_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrganizationResponse(
        org_id=org.org_id,
        org_name=org.org_name,
        org_type=org.org_type,
        description=org.description,
        contact_email=org.contact_email,
        status=org.status,
        is_verified=org.is_verified,
        max_members=org.max_members,
        created_at=org.created_at.isoformat(),
    )


@router.delete("/organizations/{org_id}", summary="删除组织")
async def delete_organization(
    org_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """删除组织（软删除）。"""
    service = TeamService(db)

    # 检查管理员权限
    member_info = await service.get_user_roles(org_id, current_user_id)
    if "org_admin" not in (member_info.get("role_name", "")):
        raise HTTPException(
            status_code=403,
            detail="Only organization admin can delete organization"
        )

    success = await service.delete_organization(org_id, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {"message": "Organization deleted successfully"}


# ==================== 成员管理 API ====================

@router.get("/organizations/{org_id}/members", response_model=List[MemberResponse], summary="获取成员列表")
async def list_members(
    org_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """获取组织的所有成员列表。"""
    service = TeamService(db)

    # 检查权限
    member_info = await service.get_user_roles(org_id, current_user_id)
    if not member_info["is_member"]:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this organization"
        )

    members = await service.list_members(org_id)
    return [MemberResponse(**m) for m in members]


@router.post("/organizations/{org_id}/members", response_model=MemberResponse, summary="添加成员")
async def add_member(
    org_id: str,
    user_id: str = Query(..., description="要添加的用户 ID"),
    role_id: str = Query(..., description="角色 ID"),
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """添加组织成员。"""
    service = TeamService(db)

    # 检查权限
    actor_info = await service.get_user_roles(org_id, current_user_id)
    if "org_admin" not in (actor_info.get("role_name", "")):
        raise HTTPException(
            status_code=403,
            detail="Only organization admin can add members"
        )

    try:
        member = await service.add_member(org_id, user_id, role_id, current_user_id)
        role = await service.get_role(member.role_id)
        return MemberResponse(
            member_id=member.member_id,
            user_id=member.user_id,
            role_id=member.role_id,
            role_name=role.role_name if role else "",
            role_name_zh=role.role_name_zh if role else "",
            permissions=role.permissions if role else [],
            status=member.status,
            joined_at=member.joined_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/organizations/{org_id}/members/{user_id}", summary="移除成员")
async def remove_member(
    org_id: str,
    user_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """移除组织成员。"""
    service = TeamService(db)

    # 检查权限
    actor_info = await service.get_user_roles(org_id, current_user_id)
    if "org_admin" not in (actor_info.get("role_name", "")):
        raise HTTPException(
            status_code=403,
            detail="Only organization admin can remove members"
        )

    success = await service.remove_member(org_id, user_id, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")

    return {"message": "Member removed successfully"}


@router.put("/organizations/{org_id}/members/{user_id}/role", summary="更新成员角色")
async def update_member_role(
    org_id: str,
    user_id: str,
    role_id: str = Query(..., description="新角色 ID"),
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """更新成员角色。"""
    service = TeamService(db)

    # 检查权限
    actor_info = await service.get_user_roles(org_id, current_user_id)
    if "org_admin" not in (actor_info.get("role_name", "")):
        raise HTTPException(
            status_code=403,
            detail="Only organization admin can update member roles"
        )

    success = await service.update_member_role(org_id, user_id, role_id, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")

    return {"message": "Member role updated successfully"}


# ==================== 邀请管理 API ====================

@router.post("/organizations/{org_id}/invitations", response_model=InvitationResponse, summary="创建邀请")
async def create_invitation(
    org_id: str,
    request: InvitationCreateRequest,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """创建团队邀请。"""
    service = TeamService(db)

    # 检查权限
    actor_info = await service.get_user_roles(org_id, current_user_id)
    if "org_admin" not in (actor_info.get("role_name", "")):
        raise HTTPException(
            status_code=403,
            detail="Only organization admin can send invitations"
        )

    invitation = await service.create_invitation(
        org_id=org_id,
        invitee_email=request.invitee_email,
        invitee_name=request.invitee_name,
        role_id=request.role_id,
        invited_by=current_user_id,
    )

    role = await service.get_role(invitation.role_id)
    return InvitationResponse(
        invitation_id=invitation.invitation_id,
        invitee_email=invitation.invitee_email,
        invitee_name=invitation.invitee_name,
        role_id=invitation.role_id,
        role_name=role.role_name if role else "",
        status=invitation.status,
        invited_by=invitation.invited_by,
        invited_at=invitation.invited_at.isoformat(),
        expires_at=invitation.expires_at.isoformat(),
    )


@router.get("/organizations/{org_id}/invitations", response_model=List[InvitationResponse], summary="获取邀请列表")
async def list_invitations(
    org_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """获取组织的邀请列表。"""
    service = TeamService(db)

    # 检查权限
    member_info = await service.get_user_roles(org_id, current_user_id)
    if not member_info["is_member"]:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this organization"
        )

    invitations = await service.list_invitations(org_id)
    result = []
    for inv in invitations:
        role = await service.get_role(inv.role_id)
        result.append(
            InvitationResponse(
                invitation_id=inv.invitation_id,
                invitee_email=inv.invitee_email,
                invitee_name=inv.invitee_name,
                role_id=inv.role_id,
                role_name=role.role_name if role else "",
                status=inv.status,
                invited_by=inv.invited_by,
                invited_at=inv.invited_at.isoformat(),
                expires_at=inv.expires_at.isoformat(),
            )
        )
    return result


@router.post("/invitations/{invitation_id}/accept", summary="接受邀请")
async def accept_invitation(
    invitation_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """接受团队邀请。"""
    service = TeamService(db)

    try:
        success = await service.accept_invitation(invitation_id, current_user_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to accept invitation")
        return {"message": "Invitation accepted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 角色权限 API ====================

@router.get("/roles", response_model=List[RoleResponse], summary="获取角色列表")
async def list_roles(
    org_id: Optional[str] = Query(default=None, description="组织 ID"),
    include_system: bool = Query(default=True, description="是否包含系统角色"),
    db: AsyncSession = Depends(get_db_session)
):
    """获取所有可用角色。"""
    service = TeamService(db)
    roles = await service.list_roles(org_id, include_system)

    return [
        RoleResponse(
            role_id=role.role_id,
            role_name=role.role_name,
            role_name_zh=role.role_name_zh,
            role_type=role.role_type,
            description=role.description,
            permissions=role.permissions,
            is_enabled=role.is_enabled,
            is_deletable=role.is_deletable,
        )
        for role in roles
    ]


@router.get("/organizations/{org_id}/roles", response_model=List[RoleResponse], summary="获取组织角色列表")
async def list_org_roles(
    org_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """获取组织的角色列表（包含系统角色和自定义角色）。"""
    service = TeamService(db)

    # 检查权限
    member_info = await service.get_user_roles(org_id, current_user_id)
    if not member_info["is_member"]:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this organization"
        )

    roles = await service.list_roles(org_id, include_system=True)
    return [
        RoleResponse(
            role_id=role.role_id,
            role_name=role.role_name,
            role_name_zh=role.role_name_zh,
            role_type=role.role_type,
            description=role.description,
            permissions=role.permissions,
            is_enabled=role.is_enabled,
            is_deletable=role.is_deletable,
        )
        for role in roles
    ]


@router.post("/organizations/{org_id}/roles", response_model=RoleResponse, summary="创建自定义角色")
async def create_role(
    org_id: str,
    role_name: str = Query(..., description="角色英文名"),
    role_name_zh: str = Query(..., description="角色中文名"),
    permissions: List[str] = Query(..., description="权限列表"),
    description: Optional[str] = Query(default=None),
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """创建自定义角色。"""
    service = TeamService(db)

    # 检查权限
    actor_info = await service.get_user_roles(org_id, current_user_id)
    if "org_admin" not in (actor_info.get("role_name", "")):
        raise HTTPException(
            status_code=403,
            detail="Only organization admin can create roles"
        )

    role = await service.create_role(
        org_id=org_id,
        role_name=role_name,
        role_name_zh=role_name_zh,
        permissions=permissions,
        description=description,
        created_by=current_user_id,
    )

    return RoleResponse(
        role_id=role.role_id,
        role_name=role.role_name,
        role_name_zh=role.role_name_zh,
        role_type=role.role_type,
        description=role.description,
        permissions=role.permissions,
        is_enabled=role.is_enabled,
        is_deletable=role.is_deletable,
    )


@router.get("/organizations/{org_id}/permissions", summary="检查权限")
async def check_permission(
    org_id: str,
    permission: str = Query(..., description="权限标识"),
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """检查当前用户是否有指定权限。"""
    service = TeamService(db)
    has_permission = await service.check_permission(org_id, current_user_id, permission)

    return PermissionCheckResponse(
        has_permission=has_permission,
        permission=permission,
        org_id=org_id,
        user_id=current_user_id,
    )


@router.get("/organizations/{org_id}/my-permissions", response_model=UserRoleResponse, summary="获取我的权限")
async def get_my_permissions(
    org_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """获取当前用户在组织内的所有权限。"""
    service = TeamService(db)
    user_roles = await service.get_user_roles(org_id, current_user_id)
    return UserRoleResponse(**user_roles)


# ==================== 审计日志 API ====================

@router.get("/organizations/{org_id}/audit-logs", response_model=List[AuditLogResponse], summary="获取审计日志")
async def list_audit_logs(
    org_id: str,
    current_user_id: str = Query(..., description="当前用户 ID"),
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db_session)
):
    """获取组织的审计日志列表。"""
    service = TeamService(db)

    # 检查权限
    actor_info = await service.get_user_roles(org_id, current_user_id)
    if "org_admin" not in (actor_info.get("role_name", "")):
        raise HTTPException(
            status_code=403,
            detail="Only organization admin can view audit logs"
        )

    logs = await service.list_audit_logs(org_id, limit, action)
    return [
        AuditLogResponse(
            log_id=log.log_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            actor_user_id=log.actor_user_id,
            actor_role=log.actor_role,
            action_details=log.action_details,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]


# ==================== 系统初始化 ====================

@router.post("/init-system-roles", summary="初始化系统角色")
async def init_system_roles(
    db: AsyncSession = Depends(get_db_session)
):
    """初始化系统预定义角色。"""
    service = TeamService(db)
    await service.initialize_system_roles()
    return {"message": "System roles initialized successfully"}
