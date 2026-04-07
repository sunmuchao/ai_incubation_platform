"""
权限管理 API 路由

提供细粒度权限管理接口：
- 权限点列表
- 角色权限管理
- 用户权限检查
- 权限授予/撤销
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.member import MemberRole, MemberType
from services.permission_service import permission_service, Permission

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


# ==================== 请求模型 ====================

class UpdateRolePermissionsRequest(BaseModel):
    """更新角色权限请求"""
    add_permissions: Optional[List[str]] = Field(default=None, description="要添加的权限列表")
    remove_permissions: Optional[List[str]] = Field(default=None, description="要移除的权限列表")


class GrantPermissionRequest(BaseModel):
    """授予用户权限请求"""
    permission: str = Field(..., description="权限点")


class CheckPermissionRequest(BaseModel):
    """检查权限请求"""
    user_id: str = Field(..., description="用户 ID")
    member_type: str = Field(..., description="成员类型")
    role: str = Field(..., description="角色")
    permission: str = Field(..., description="权限点")


class PermissionInfo(BaseModel):
    """权限信息"""
    value: str
    name: str
    group: str


# ==================== 权限点查询 ====================

@router.get("/list")
async def list_permissions():
    """
    获取所有权限点列表

    返回系统中定义的所有权限点及其分组信息
    """
    all_permissions = permission_service.get_all_permissions()
    groups = permission_service.get_permission_groups()

    # 构建权限到分组的映射
    permission_to_group = {}
    for group_name, perms in groups.items():
        for perm in perms:
            permission_to_group[perm.value] = group_name

    return {
        "total": len(all_permissions),
        "permissions": [
            {
                "value": p.value,
                "name": p.value.replace("_", " ").title(),
                "group": permission_to_group.get(p.value, "other")
            }
            for p in all_permissions
        ],
        "groups": list(groups.keys())
    }


@router.get("/groups")
async def get_permission_groups():
    """获取权限分组"""
    groups = permission_service.get_permission_groups()
    return {
        group_name: [p.value for p in perms]
        for group_name, perms in groups.items()
    }


@router.get("/group/{group_name}")
async def get_permissions_by_group(group_name: str):
    """获取指定分组的权限"""
    perms = permission_service.get_permissions_by_group(group_name)
    if not perms:
        raise HTTPException(status_code=404, detail=f"Unknown group: {group_name}")

    return {
        "group": group_name,
        "permissions": [p.value for p in perms],
        "count": len(perms)
    }


# ==================== 角色权限管理 ====================

@router.get("/roles/{role}")
async def get_role_permissions(role: str):
    """
    获取角色权限

    返回指定角色的所有权限点
    """
    try:
        member_role = MemberRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    permissions = permission_service.get_role_permissions(member_role)

    return {
        "role": role,
        "permissions": [p.value for p in permissions],
        "count": len(permissions)
    }


@router.post("/roles/{role}/update")
async def update_role_permissions(
    role: str,
    request: UpdateRolePermissionsRequest,
    operator_id: str = Query(..., description="操作人 ID")
):
    """
    更新角色权限

    可以添加或移除角色的权限点
    """
    try:
        member_role = MemberRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    # 转换权限字符串为枚举
    add_perms = []
    if request.add_permissions:
        for p_str in request.add_permissions:
            try:
                add_perms.append(Permission(p_str))
            except ValueError:
                pass  # 忽略无效权限

    remove_perms = []
    if request.remove_permissions:
        for p_str in request.remove_permissions:
            try:
                remove_perms.append(Permission(p_str))
            except ValueError:
                pass  # 忽略无效权限

    # 更新权限
    updated_perms = permission_service.update_role_permissions(
        role=member_role,
        add_permissions=add_perms if add_perms else None,
        remove_permissions=remove_perms if remove_perms else None
    )

    # 记录审计日志（这里简化处理）
    return {
        "success": True,
        "role": role,
        "updated_permissions": [p.value for p in updated_perms],
        "count": len(updated_perms),
        "operator_id": operator_id
    }


@router.get("/roles/export")
async def export_role_config(operator_id: str = Query(...)):
    """导出角色权限配置"""
    config = permission_service.export_role_config()
    return {
        "exported_by": operator_id,
        "exported_at": datetime.now().isoformat(),
        "config": config
    }


@router.post("/roles/import")
async def import_role_config(
    config: Dict[str, List[str]] = Body(...),
    operator_id: str = Query(...)
):
    """导入角色权限配置"""
    permission_service.import_role_config(config)
    return {
        "success": True,
        "imported_by": operator_id,
        "imported_at": datetime.now().isoformat()
    }


# ==================== 用户权限 ====================

@router.get("/user/{user_id}")
async def get_user_permissions(user_id: str, role: str = Query(default="member")):
    """
    获取用户权限

    返回用户的实际权限（包括角色权限和特殊覆盖）
    """
    try:
        member_role = MemberRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    permissions = permission_service.get_user_permissions(user_id, member_role)

    return {
        "user_id": user_id,
        "role": role,
        "permissions": [p.value for p in permissions],
        "count": len(permissions)
    }


@router.post("/check")
async def check_permission(request: CheckPermissionRequest):
    """
    检查用户是否有指定权限

    用于在 API 接口中进行权限校验
    """
    try:
        member_type = MemberType(request.member_type)
        role = MemberRole(request.role)
        permission = Permission(request.permission)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")

    has_permission = permission_service.has_permission(
        user_id=request.user_id,
        member_type=member_type,
        role=role,
        permission=permission
    )

    return {
        "user_id": request.user_id,
        "permission": request.permission,
        "has_permission": has_permission
    }


@router.post("/check-batch")
async def check_permissions_batch(
    user_id: str = Body(...),
    member_type: str = Body(...),
    role: str = Body(...),
    permissions: List[str] = Body(...)
):
    """批量检查用户权限"""
    try:
        mt = MemberType(member_type)
        rl = MemberRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid member_type or role")

    results = {}
    for perm_str in permissions:
        try:
            perm = Permission(perm_str)
            results[perm_str] = permission_service.has_permission(user_id, mt, rl, perm)
        except ValueError:
            results[perm_str] = False

    return {
        "user_id": user_id,
        "results": results
    }


# ==================== 权限授予/撤销 ====================

@router.post("/grant")
async def grant_permission(
    user_id: str = Query(...),
    permission: str = Query(...),
    operator_id: str = Query(...)
):
    """授予用户特殊权限"""
    try:
        perm = Permission(permission)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid permission: {permission}")

    permission_service.grant_permission(user_id, perm)

    return {
        "success": True,
        "user_id": user_id,
        "granted_permission": permission,
        "operator_id": operator_id
    }


@router.post("/revoke")
async def revoke_permission(
    user_id: str = Query(...),
    permission: str = Query(...),
    operator_id: str = Query(...)
):
    """撤销用户特殊权限"""
    try:
        perm = Permission(permission)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid permission: {permission}")

    permission_service.revoke_permission(user_id, perm)

    return {
        "success": True,
        "user_id": user_id,
        "revoked_permission": permission,
        "operator_id": operator_id
    }


@router.post("/deny")
async def deny_permission(
    user_id: str = Query(...),
    permission: str = Query(...),
    operator_id: str = Query(...)
):
    """禁止用户的某个权限"""
    try:
        perm = Permission(permission)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid permission: {permission}")

    permission_service.deny_permission(user_id, perm)

    return {
        "success": True,
        "user_id": user_id,
        "denied_permission": permission,
        "operator_id": operator_id
    }


# ==================== 管理功能 ====================

@router.get("/superuser/check")
async def check_superuser(user_id: str = Query(...)):
    """检查用户是否是超级管理员"""
    is_super = permission_service.is_super_user(user_id)
    return {
        "user_id": user_id,
        "is_superuser": is_super
    }


@router.get("/stats")
async def get_permission_stats():
    """获取权限系统统计"""
    all_perms = permission_service.get_all_permissions()
    groups = permission_service.get_permission_groups()

    return {
        "total_permissions": len(all_perms),
        "total_groups": len(groups),
        "permissions_by_group": {
            group: len(perms) for group, perms in groups.items()
        },
        "role_count": len(MemberRole)
    }


# 导入 datetime
from datetime import datetime
