"""
用户组管理 API 路由

提供用户组管理接口：
- 用户组 CRUD
- 组成员管理
- 组权限查看
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.user_group_service import user_group_service, UserGroupType
from services.channel_enhancement_service import ChannelRole
from services.permission_service import permission_service

router = APIRouter(prefix="/api/user-groups", tags=["user-groups"])


# ==================== 请求/响应模型 ====================

class UserGroupCreate(BaseModel):
    """创建用户组请求"""
    name: str = Field(..., description="用户组名称")
    description: str = Field(default="", description="用户组描述")
    group_type: str = Field(default="custom", description="用户组类型：system, custom, auto")
    permissions: Optional[List[str]] = Field(default=None, description="权限列表")


class UserGroupUpdate(BaseModel):
    """更新用户组请求"""
    name: Optional[str] = Field(None, description="用户组名称")
    description: Optional[str] = Field(None, description="用户组描述")
    permissions: Optional[List[str]] = Field(None, description="权限列表")


class UserGroupResponse(BaseModel):
    """用户组响应"""
    id: str
    name: str
    group_type: str
    description: str
    permissions: List[str]
    member_count: int
    created_at: str
    updated_at: str
    is_active: bool


class AddMemberRequest(BaseModel):
    """添加成员请求"""
    user_id: str = Field(..., description="用户 ID")


# ==================== 用户组 CRUD ====================

@router.post("")
async def create_user_group(
    group: UserGroupCreate,
    operator_id: str = Query(..., description="操作人 ID")
):
    """创建用户组"""
    try:
        group_type = UserGroupType(group.group_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid group_type: {group.group_type}")

    try:
        new_group = user_group_service.create_group(
            name=group.name,
            description=group.description,
            group_type=group_type,
            permissions=group.permissions,
            creator_id=operator_id
        )
        return {
            "success": True,
            "group": new_group.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_user_groups(
    group_type: Optional[str] = Query(None),
    include_inactive: bool = False
):
    """获取用户组列表"""
    try:
        gt = UserGroupType(group_type) if group_type else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid group_type: {group_type}")

    groups = user_group_service.list_groups(
        group_type=gt,
        include_inactive=include_inactive
    )

    return {
        "groups": [g.to_dict() for g in groups],
        "total": len(groups)
    }


@router.get("/{group_id}")
async def get_user_group(group_id: str):
    """获取用户组详情"""
    group = user_group_service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    return {"group": group.to_dict()}


@router.get("/name/{name}")
async def get_user_group_by_name(name: str):
    """通过名称获取用户组"""
    group = user_group_service.get_group_by_name(name)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    return {"group": group.to_dict()}


@router.put("/{group_id}")
async def update_user_group(group_id: str, group: UserGroupUpdate, operator_id: str = Query(...)):
    """更新用户组"""
    result = user_group_service.update_group(
        group_id=group_id,
        name=group.name,
        description=group.description,
        permissions=group.permissions
    )

    if not result:
        raise HTTPException(status_code=404, detail="User group not found")

    try:
        return {
            "success": True,
            "group": result.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{group_id}")
async def delete_user_group(group_id: str, operator_id: str = Query(...)):
    """删除用户组"""
    try:
        success = user_group_service.delete_group(group_id)
        if not success:
            raise HTTPException(status_code=404, detail="User group not found")
        return {"success": True, "group_id": group_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 组成员管理 ====================

@router.post("/{group_id}/members")
async def add_member_to_group(group_id: str, request: AddMemberRequest):
    """添加用户到用户组"""
    group = user_group_service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    success = user_group_service.add_member_to_group(group_id, request.user_id)
    if not success:
        raise HTTPException(status_code=400, detail="User is already a member")

    return {
        "success": True,
        "group_id": group_id,
        "user_id": request.user_id
    }


@router.delete("/{group_id}/members/{user_id}")
async def remove_member_from_group(group_id: str, user_id: str):
    """从用户组移除用户"""
    group = user_group_service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    success = user_group_service.remove_member_from_group(group_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User is not a member")

    return {
        "success": True,
        "group_id": group_id,
        "user_id": user_id
    }


@router.get("/{group_id}/members")
async def get_group_members(
    group_id: str,
    limit: int = Query(default=100, ge=1, le=500)
):
    """获取组成员列表"""
    group = user_group_service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    members = user_group_service.get_group_members(group_id, limit)

    return {
        "group_id": group_id,
        "members": members,
        "total": len(members)
    }


@router.get("/users/{user_id}/groups")
async def get_user_groups(user_id: str):
    """获取用户所属的所有用户组"""
    groups = user_group_service.get_user_groups(user_id)

    return {
        "user_id": user_id,
        "groups": [g.to_dict() for g in groups],
        "total": len(groups)
    }


@router.get("/users/{user_id}/permissions")
async def get_user_permissions_from_groups(user_id: str):
    """获取用户从用户组继承的权限"""
    permissions = user_group_service.get_user_permissions_from_groups(user_id)

    return {
        "user_id": user_id,
        "permissions": permissions,
        "count": len(permissions)
    }


# ==================== 频道用户组关联 ====================

@router.get("/{group_id}/channels")
async def get_group_channels(group_id: str):
    """获取用户组关联的频道"""
    from services.channel_enhancement_service import channel_enhancement_service

    # 获取所有频道并检查关联
    from services.channel_service import channel_service
    from db.manager import db_manager

    async with db_manager._session_factory() as session:
        channels = await channel_service.list_channels(session, limit=200)

    linked_channels = []
    for channel in channels:
        channel_groups = channel_enhancement_service.get_channel_user_groups(channel.id)
        if group_id in channel_groups:
            linked_channels.append({
                "channel_id": channel.id,
                "channel_name": channel.name,
                "channel_slug": channel.slug
            })

    return {
        "group_id": group_id,
        "linked_channels": linked_channels,
        "total": len(linked_channels)
    }


# ==================== 统计和导出 ====================

@router.get("/stats")
async def get_user_group_stats():
    """获取用户组统计"""
    stats = user_group_service.get_group_stats()
    return stats


@router.get("/export")
async def export_user_groups(operator_id: str = Query(...)):
    """导出用户组配置"""
    config = user_group_service.export_group_config()
    config["exported_by"] = operator_id
    return config


@router.post("/import")
async def import_user_groups(
    config: Dict[str, Any] = Body(...),
    operator_id: str = Query(...)
):
    """导入用户组配置"""
    result = user_group_service.import_group_config(config, operator_id)
    return result


# ==================== 可用角色列表 ====================

@router.get("/roles/available")
async def get_available_channel_roles():
    """获取可用的频道角色列表"""
    from services.channel_enhancement_service import ChannelRole, CHANNEL_ROLE_PERMISSIONS

    return {
        "roles": [
            {
                "role": role.value,
                "default_permissions": CHANNEL_ROLE_PERMISSIONS.get(role, []),
                "description": CHANNEL_ROLE_DESCRIPTIONS.get(role, "")
            }
            for role in ChannelRole
        ]
    }


# 角色描述
CHANNEL_ROLE_DESCRIPTIONS = {
    ChannelRole.OWNER: "频道所有者，拥有所有权限",
    ChannelRole.ADMIN: "频道管理员，拥有管理权限",
    ChannelRole.MODERATOR: "频道版主，可以管理内容和成员",
    ChannelRole.VIP: "贵宾用户，享有特殊权限",
    ChannelRole.CONTRIBUTOR: "活跃贡献者，可以发布更多内容",
    ChannelRole.MEMBER: "普通成员",
    ChannelRole.GUEST: "访客，仅可查看内容"
}
