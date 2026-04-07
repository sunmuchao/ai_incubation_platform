"""
RBAC 权限管理 API

提供角色管理、用户角色绑定、权限校验等接口
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header, Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.rbac_service import rbac_service, init_rbac
from utils.logger import logger

router = APIRouter(prefix="/api/rbac", tags=["RBAC 权限管理"])


# ==================== 请求/响应模型 ====================

class CreateRoleRequest(BaseModel):
    """创建角色请求"""
    name: str = Field(..., description="角色名称")
    description: str = Field(None, description="角色描述")
    permissions: List[str] = Field(default_factory=list, description="权限列表")


class UpdateRoleRequest(BaseModel):
    """更新角色请求"""
    description: str = Field(None, description="角色描述")
    permissions: List[str] = Field(None, description="权限列表")


class AssignRoleRequest(BaseModel):
    """分配角色请求"""
    user_id: str = Field(..., description="用户 ID")
    role_name: str = Field(..., description="角色名称")


class CheckPermissionRequest(BaseModel):
    """权限校验请求"""
    user_id: str = Field(..., description="用户 ID")
    resource: str = Field(..., description="资源标识")
    operation: str = Field(..., description="操作类型")


class MaskDataRequest(BaseModel):
    """数据脱敏请求"""
    user_id: str = Field(..., description="用户 ID")
    datasource_name: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    columns: List[str] = Field(..., description="列名列表")
    rows: List[Dict[str, Any]] = Field(..., description="数据行")


# ==================== 角色管理 API ====================

@router.post("/roles")
async def create_role(request: CreateRoleRequest, x_user_id: str = Header(None)) -> Dict[str, Any]:
    """创建角色"""
    result = await rbac_service.create_role(
        name=request.name,
        description=request.description,
        permissions=request.permissions,
        created_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))

    return result


@router.get("/roles")
async def list_roles() -> Dict[str, Any]:
    """获取所有角色"""
    roles = await rbac_service.list_roles()
    return {"roles": roles}


@router.get("/roles/{role_name}")
async def get_role(role_name: str) -> Dict[str, Any]:
    """获取角色详情"""
    role = await rbac_service.get_role(role_name)
    if not role:
        raise HTTPException(status_code=404, detail=f"角色 '{role_name}' 不存在")
    return {"role": role}


@router.put("/roles/{role_name}")
async def update_role(role_name: str, request: UpdateRoleRequest,
                      x_user_id: str = Header(None)) -> Dict[str, Any]:
    """更新角色"""
    result = await rbac_service.update_role(
        role_name=role_name,
        description=request.description,
        permissions=request.permissions,
        updated_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))

    return result


@router.delete("/roles/{role_name}")
async def delete_role(role_name: str, x_user_id: str = Header(None)) -> Dict[str, Any]:
    """删除角色"""
    result = await rbac_service.delete_role(
        role_name=role_name,
        deleted_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))

    return result


# ==================== 用户 - 角色管理 API ====================

@router.post("/users/{user_id}/roles")
async def assign_role(user_id: str, request: AssignRoleRequest,
                      x_user_id: str = Header(None)) -> Dict[str, Any]:
    """给用户分配角色"""
    result = await rbac_service.assign_role_to_user(
        user_id=user_id,
        role_name=request.role_name,
        assigned_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "分配失败"))

    return result


@router.delete("/users/{user_id}/roles/{role_name}")
async def revoke_role(user_id: str, role_name: str,
                      x_user_id: str = Header(None)) -> Dict[str, Any]:
    """撤销用户角色"""
    result = await rbac_service.revoke_role_from_user(
        user_id=user_id,
        role_name=role_name,
        revoked_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "撤销失败"))

    return result


@router.get("/users/{user_id}/roles")
async def get_user_roles(user_id: str) -> Dict[str, Any]:
    """获取用户的所有角色"""
    roles = await rbac_service.get_user_roles(user_id)
    return {"roles": roles}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: str) -> Dict[str, Any]:
    """获取用户的所有权限"""
    permissions = await rbac_service.get_user_permissions(user_id)
    return {"permissions": list(permissions)}


# ==================== 权限校验 API ====================

@router.post("/check")
async def check_permission(request: CheckPermissionRequest) -> Dict[str, Any]:
    """检查权限"""
    has_perm, reason = await rbac_service.check_permission(
        user_id=request.user_id,
        resource=request.resource,
        operation=request.operation
    )

    return {
        "has_permission": has_perm,
        "reason": reason
    }


@router.post("/check/datasource")
async def check_datasource_access(request: CheckPermissionRequest) -> Dict[str, Any]:
    """检查数据源访问权限"""
    has_perm, reason = await rbac_service.check_datasource_access(
        user_id=request.user_id,
        datasource_name=request.resource,
        operation=request.operation
    )

    return {
        "has_permission": has_perm,
        "reason": reason
    }


# ==================== 数据脱敏 API ====================

@router.post("/mask")
async def mask_data(request: MaskDataRequest) -> Dict[str, Any]:
    """对数据应用脱敏规则"""
    masked_rows = await rbac_service.mask_query_result(
        user_id=request.user_id,
        datasource_name=request.datasource_name,
        table_name=request.table_name,
        columns=request.columns,
        rows=request.rows
    )

    return {
        "masked_rows": masked_rows
    }


@router.get("/masks/{datasource_name}/{table_name}")
async def get_column_masks(user_id: str = Query(...),
                           datasource_name: str = Path(...),
                           table_name: str = Path(...)) -> Dict[str, Any]:
    """获取列脱敏规则"""
    masks = await rbac_service.get_column_masks(user_id, datasource_name, table_name)
    return {"masks": masks}


# ==================== 审计日志 API ====================

@router.get("/audits")
async def list_permission_audits(
    user_id: Optional[str] = Query(None, description="用户 ID"),
    action: Optional[str] = Query(None, description="操作类型"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> Dict[str, Any]:
    """查询权限审计日志"""
    audits = await rbac_service.list_permission_audits(
        user_id=user_id,
        action=action,
        limit=limit,
        offset=offset
    )
    return {"audits": audits}


# ==================== 系统初始化 ====================

@router.on_event("startup")
async def startup():
    """服务启动时初始化 RBAC"""
    await init_rbac()
