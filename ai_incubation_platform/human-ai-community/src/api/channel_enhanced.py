"""
频道增强 API 路由

提供频道管理增强接口：
- 频道角色细分
- 频道用户组关联
- 频道审核队列
- 频道权限覆盖
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.channel_enhancement_service import channel_enhancement_service, ChannelRole, CHANNEL_ROLE_PERMISSIONS
from services.channel_service import channel_service
from db.manager import db_manager

router = APIRouter(prefix="/api/channels", tags=["channels-enhanced"])


# ==================== 请求模型 ====================

class ChannelRolePermissionUpdate(BaseModel):
    """更新频道角色权限请求"""
    permissions: List[str] = Field(..., description="权限列表")


class ChannelUserGroupLink(BaseModel):
    """频道用户组关联请求"""
    group_ids: List[str] = Field(..., description="用户组 ID 列表")


class ModerationQueueItem(BaseModel):
    """审核队列项目请求"""
    item_id: str = Field(..., description="项目 ID")
    item_type: str = Field(..., description="项目类型：post, comment")
    author_id: str = Field(..., description="作者 ID")
    content: str = Field(..., description="内容")
    reason: str = Field(default="", description="审核原因")
    priority: float = Field(default=0.5, ge=0, le=1, description="优先级")


class ProcessModerationItem(BaseModel):
    """处理审核项目请求"""
    decision: str = Field(..., description="决策：approved, rejected")
    notes: str = Field(default="", description="处理备注")


# ==================== 频道角色管理 ====================

@router.get("/{channel_id}/roles")
async def get_channel_roles(channel_id: str):
    """获取频道可用角色列表"""
    roles = channel_enhancement_service.get_available_channel_roles()
    return {"roles": roles}


@router.get("/{channel_id}/roles/permissions")
async def get_channel_role_permissions(channel_id: str, role: Optional[str] = Query(None)):
    """获取频道角色权限（考虑覆盖）"""
    if role:
        permissions = channel_enhancement_service.get_channel_role_permissions(channel_id, role)
        return {
            "channel_id": channel_id,
            "role": role,
            "permissions": permissions,
            "is_custom": channel_id in channel_enhancement_service._channel_role_overrides and
                         role in channel_enhancement_service._channel_role_overrides[channel_id]
        }
    else:
        all_permissions = {}
        for channel_role in ChannelRole:
            all_permissions[channel_role.value] = channel_enhancement_service.get_channel_role_permissions(
                channel_id, channel_role.value
            )
        return {
            "channel_id": channel_id,
            "permissions": all_permissions
        }


@router.put("/{channel_id}/roles/{role}/permissions")
async def update_channel_role_permissions(
    channel_id: str,
    role: str,
    request: ChannelRolePermissionUpdate,
    operator_id: str = Query(..., description="操作人 ID")
):
    """设置频道特定角色权限（覆盖默认）"""
    try:
        result = channel_enhancement_service.set_channel_role_permissions(
            channel_id=channel_id,
            role=role,
            permissions=request.permissions
        )
        return {
            "success": True,
            "channel_id": channel_id,
            "role": role,
            "permissions": result["permissions"],
            "operator_id": operator_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{channel_id}/members/{member_id}/permissions")
async def get_member_channel_permissions(
    channel_id: str,
    member_id: str,
    member_role: str = Query(..., description="成员角色")
):
    """获取频道成员的有效权限"""
    permissions = channel_enhancement_service.get_channel_member_effective_permissions(
        channel_id=channel_id,
        member_role=member_role
    )
    return {
        "channel_id": channel_id,
        "member_id": member_id,
        "member_role": member_role,
        "permissions": permissions
    }


# ==================== 频道用户组关联 ====================

@router.get("/{channel_id}/user-groups")
async def get_channel_user_groups(channel_id: str):
    """获取频道关联的用户组"""
    groups = channel_enhancement_service.get_channel_user_groups(channel_id)

    # 获取用户组详情
    from services.user_group_service import user_group_service
    group_details = []
    for group_id in groups:
        group = user_group_service.get_group(group_id)
        if group:
            group_details.append(group.to_dict())

    return {
        "channel_id": channel_id,
        "linked_groups": group_details,
        "total": len(group_details)
    }


@router.put("/{channel_id}/user-groups")
async def set_channel_user_groups(
    channel_id: str,
    request: ChannelUserGroupLink,
    operator_id: str = Query(...)
):
    """设置频道关联的用户组"""
    result = channel_enhancement_service.set_channel_user_groups(
        channel_id=channel_id,
        group_ids=request.group_ids
    )
    return {
        "success": True,
        "channel_id": channel_id,
        "group_ids": result["group_ids"],
        "operator_id": operator_id
    }


@router.post("/{channel_id}/user-groups/{group_id}")
async def add_channel_user_group(
    channel_id: str,
    group_id: str,
    operator_id: str = Query(...)
):
    """添加频道关联用户组"""
    # 验证用户组是否存在
    from services.user_group_service import user_group_service
    group = user_group_service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    success = channel_enhancement_service.add_channel_user_group(channel_id, group_id)
    return {
        "success": True,
        "channel_id": channel_id,
        "group_id": group_id
    }


@router.delete("/{channel_id}/user-groups/{group_id}")
async def remove_channel_user_group(
    channel_id: str,
    group_id: str
):
    """移除频道关联用户组"""
    success = channel_enhancement_service.remove_channel_user_group(channel_id, group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Group not linked to channel")

    return {
        "success": True,
        "channel_id": channel_id,
        "group_id": group_id
    }


@router.post("/{channel_id}/access/check")
async def check_channel_access(
    channel_id: str,
    user_id: str = Query(..., description="用户 ID"),
    user_type: str = Query(..., description="用户类型"),
    user_role: str = Query(..., description="用户角色")
):
    """检查用户频道访问权限"""
    # 获取频道信息
    async with db_manager._session_factory() as session:
        channel = await channel_service.get_channel(session, channel_id)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # 检查用户是否是频道成员
    async with db_manager._session_factory() as session:
        member = await channel_service.get_channel_member(session, channel_id, user_id)

    result = channel_enhancement_service.check_enhanced_channel_access(
        channel_id=channel_id,
        user_id=user_id,
        user_type=user_type,
        user_role=user_role,
        channel_access_level=channel.access_level,
        is_channel_member=member is not None,
        channel_member_role=member.role if member else None
    )

    if result["allowed"]:
        return result
    else:
        raise HTTPException(status_code=403, detail=result.get("reason", "Access denied"))


# ==================== 频道审核队列 ====================

@router.get("/{channel_id}/moderation-queue")
async def get_channel_moderation_queue(
    channel_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    min_priority: float = Query(default=0.0, ge=0, le=1)
):
    """获取频道审核队列"""
    items = channel_enhancement_service.get_moderation_queue(channel_id).get_pending_items(
        limit=limit,
        min_priority=min_priority
    )

    return {
        "channel_id": channel_id,
        "items": items,
        "total": len(items)
    }


@router.post("/{channel_id}/moderation-queue")
async def add_to_moderation_queue(
    channel_id: str,
    request: ModerationQueueItem,
    operator_id: str = Query(...)
):
    """添加项目到审核队列"""
    item = channel_enhancement_service.add_to_moderation_queue(
        channel_id=channel_id,
        item_id=request.item_id,
        item_type=request.item_type,
        author_id=request.author_id,
        content=request.content,
        reason=request.reason,
        priority=request.priority
    )

    return {
        "success": True,
        "item": item,
        "operator_id": operator_id
    }


@router.post("/{channel_id}/moderation-queue/{item_id}/process")
async def process_moderation_queue_item(
    channel_id: str,
    item_id: str,
    request: ProcessModerationItem,
    processor_id: str = Query(..., description="处理人 ID")
):
    """处理审核队列项目"""
    item = channel_enhancement_service.process_moderation_queue_item(
        channel_id=channel_id,
        item_id=item_id,
        processor_id=processor_id,
        decision=request.decision,
        notes=request.notes
    )

    if not item:
        raise HTTPException(status_code=404, detail="Moderation item not found")

    return {
        "success": True,
        "item": item
    }


@router.get("/{channel_id}/moderation-queue/stats")
async def get_moderation_queue_stats(channel_id: str):
    """获取审核队列统计"""
    stats = channel_enhancement_service.get_moderation_queue_stats(channel_id)
    return stats


@router.get("/moderation-queue/all-stats")
async def get_all_channel_moderation_stats():
    """获取所有频道审核队列统计"""
    stats = channel_enhancement_service.get_all_channel_queues_stats()
    return {
        "channels": stats,
        "total_channels": len(stats)
    }


# ==================== 频道统计增强 ====================

@router.get("/{channel_id}/enhanced-stats")
async def get_channel_enhanced_stats(channel_id: str):
    """获取频道增强统计"""
    stats = channel_enhancement_service.get_channel_enhanced_stats(channel_id)
    return stats


@router.get("/{channel_id}/role-distribution")
async def get_channel_role_distribution(
    channel_id: str,
    limit: int = Query(default=200, ge=1, le=500)
):
    """获取频道角色分布"""
    # 获取频道成员
    async with db_manager._session_factory() as session:
        members = await channel_service.list_channel_members(session, channel_id, limit=limit)

    distribution = channel_enhancement_service.get_channel_role_distribution(
        channel_id=channel_id,
        members=members
    )

    return distribution


# ==================== 频道配置导出/导入 ====================

@router.get("/{channel_id}/export")
async def export_channel_config(
    channel_id: str,
    operator_id: str = Query(...)
):
    """导出频道配置"""
    config = channel_enhancement_service.export_channel_config(channel_id)
    config["exported_by"] = operator_id
    return config


@router.post("/{channel_id}/import")
async def import_channel_config(
    channel_id: str,
    config: Dict[str, Any] = Body(...),
    operator_id: str = Query(...)
):
    """导入频道配置"""
    result = channel_enhancement_service.import_channel_config(channel_id, config)
    result["operator_id"] = operator_id
    return result
