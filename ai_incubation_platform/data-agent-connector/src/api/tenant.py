"""
多租户 API

提供租户管理、成员管理、数据源管理等接口
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header, Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.tenant_service import tenant_service, init_tenant
from utils.logger import logger

router = APIRouter(prefix="/api/tenant", tags=["多租户管理"])


# ==================== 请求/响应模型 ====================

class CreateTenantRequest(BaseModel):
    """创建租户请求"""
    tenant_code: str = Field(..., description="租户编码")
    tenant_name: str = Field(..., description="租户名称")
    description: str = Field(None, description="租户描述")
    config: Dict[str, Any] = Field(default_factory=dict, description="租户配置")
    quota: Dict[str, Any] = Field(default_factory=dict, description="租户配额")


class UpdateTenantRequest(BaseModel):
    """更新租户请求"""
    tenant_name: str = Field(None, description="租户名称")
    description: str = Field(None, description="租户描述")
    config: Dict[str, Any] = Field(None, description="租户配置")
    quota: Dict[str, Any] = Field(None, description="租户配额")
    status: str = Field(None, description="租户状态")


class AddMemberRequest(BaseModel):
    """添加成员请求"""
    user_id: str = Field(..., description="用户 ID")
    role: str = Field("member", description="成员角色：owner, admin, member, viewer")


class AddDatasourceRequest(BaseModel):
    """添加数据源请求"""
    datasource_name: str = Field(..., description="数据源名称")
    connector_type: str = Field(..., description="连接器类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="数据源配置")
    is_public: bool = Field(False, description="是否租户内公开")
    allowed_users: List[str] = Field(default_factory=list, description="允许的用户 ID 列表")


# ==================== 租户管理 API ====================

@router.post("")
async def create_tenant(request: CreateTenantRequest,
                        x_user_id: str = Header(None)) -> Dict[str, Any]:
    """创建租户"""
    result = await tenant_service.create_tenant(
        tenant_code=request.tenant_code,
        tenant_name=request.tenant_name,
        description=request.description,
        config=request.config,
        quota=request.quota,
        created_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))

    return result


@router.get("")
async def list_tenants(status: Optional[str] = Query(None, description="租户状态"),
                       limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
                       offset: int = Query(0, ge=0, description="偏移量")) -> Dict[str, Any]:
    """获取租户列表"""
    tenants = await tenant_service.list_tenants(
        status=status,
        limit=limit,
        offset=offset
    )
    return {"tenants": tenants}


@router.get("/{tenant_code}")
async def get_tenant(tenant_code: str) -> Dict[str, Any]:
    """获取租户详情"""
    tenant = await tenant_service.get_tenant(tenant_code)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"租户 '{tenant_code}' 不存在")
    return {"tenant": tenant}


@router.put("/{tenant_code}")
async def update_tenant(tenant_code: str, request: UpdateTenantRequest,
                        x_user_id: str = Header(None)) -> Dict[str, Any]:
    """更新租户"""
    result = await tenant_service.update_tenant(
        tenant_code=tenant_code,
        tenant_name=request.tenant_name,
        description=request.description,
        config=request.config,
        quota=request.quota,
        status=request.status,
        updated_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))

    return result


@router.delete("/{tenant_code}")
async def delete_tenant(tenant_code: str,
                        x_user_id: str = Header(None)) -> Dict[str, Any]:
    """删除租户（软删除）"""
    result = await tenant_service.delete_tenant(
        tenant_code=tenant_code,
        deleted_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))

    return result


# ==================== 租户成员管理 API ====================

@router.post("/{tenant_code}/members")
async def add_tenant_member(tenant_code: str, request: AddMemberRequest,
                            x_user_id: str = Header(None)) -> Dict[str, Any]:
    """添加租户成员"""
    # 检查租户是否存在
    tenant = await tenant_service.get_tenant(tenant_code)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"租户 '{tenant_code}' 不存在")

    result = await tenant_service.add_tenant_member(
        tenant_code=tenant_code,
        user_id=request.user_id,
        role=request.role,
        created_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "添加失败"))

    return result


@router.delete("/{tenant_code}/members/{user_id}")
async def remove_tenant_member(tenant_code: str, user_id: str) -> Dict[str, Any]:
    """移除租户成员"""
    result = await tenant_service.remove_tenant_member(
        tenant_code=tenant_code,
        user_id=user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "移除失败"))

    return result


@router.get("/{tenant_code}/members")
async def get_tenant_members(tenant_code: str) -> Dict[str, Any]:
    """获取租户成员列表"""
    members = await tenant_service.get_tenant_members(tenant_code)
    return {"members": members}


@router.get("/{tenant_code}/members/{user_id}/role")
async def get_member_role(tenant_code: str, user_id: str) -> Dict[str, Any]:
    """获取用户在租户中的角色"""
    role = await tenant_service.check_tenant_member_role(tenant_code, user_id)
    if role is None:
        raise HTTPException(status_code=404, detail=f"用户 '{user_id}' 不属于租户 '{tenant_code}'")
    return {"role": role}


# ==================== 租户数据源管理 API ====================

@router.post("/{tenant_code}/datasources")
async def add_tenant_datasource(tenant_code: str, request: AddDatasourceRequest,
                                x_user_id: str = Header(None)) -> Dict[str, Any]:
    """添加租户数据源"""
    # 检查租户是否存在
    tenant = await tenant_service.get_tenant(tenant_code)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"租户 '{tenant_code}' 不存在")

    result = await tenant_service.add_tenant_datasource(
        tenant_code=tenant_code,
        datasource_name=request.datasource_name,
        connector_type=request.connector_type,
        config=request.config,
        is_public=request.is_public,
        allowed_users=request.allowed_users,
        created_by=x_user_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "添加失败"))

    return result


@router.delete("/{tenant_code}/datasources/{datasource_name}")
async def remove_tenant_datasource(tenant_code: str,
                                   datasource_name: str) -> Dict[str, Any]:
    """移除租户数据源"""
    result = await tenant_service.remove_tenant_datasource(
        tenant_code=tenant_code,
        datasource_name=datasource_name
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "移除失败"))

    return result


@router.get("/{tenant_code}/datasources")
async def get_tenant_datasources(tenant_code: str,
                                 user_id: Optional[str] = Query(None, description="用户 ID（用于权限过滤）")) -> Dict[str, Any]:
    """获取租户数据源列表"""
    datasources = await tenant_service.get_tenant_datasources(
        tenant_code=tenant_code,
        user_id=user_id
    )
    return {"datasources": datasources}


@router.get("/{tenant_code}/datasources/{datasource_name}")
async def get_tenant_datasource(tenant_code: str,
                                datasource_name: str) -> Dict[str, Any]:
    """获取租户数据源详情"""
    datasource = await tenant_service.get_tenant_datasource(
        tenant_code=tenant_code,
        datasource_name=datasource_name
    )
    if not datasource:
        raise HTTPException(status_code=404, detail=f"数据源 '{datasource_name}' 不存在")
    return {"datasource": datasource}


# ==================== 租户配额管理 API ====================

@router.get("/{tenant_code}/quota")
async def get_tenant_quota(tenant_code: str,
                           days: int = Query(7, ge=1, le=30, description="查询天数")) -> Dict[str, Any]:
    """获取租户配额使用情况"""
    usage = await tenant_service.get_quota_usage(
        tenant_code=tenant_code,
        days=days
    )

    # 获取租户配额限制
    tenant = await tenant_service.get_tenant(tenant_code)
    quota = tenant.get("quota", {}) if tenant else {}

    return {
        "quota_limit": quota,
        "usage_history": usage
    }


# ==================== 用户租户关系 API ====================

@router.get("/my-tenants")
async def get_my_tenants(x_user_id: str = Header(..., description="用户 ID")) -> Dict[str, Any]:
    """获取当前用户所属的所有租户"""
    tenants = await tenant_service.get_user_tenants(x_user_id)
    return {"tenants": tenants}


@router.get("/resolve")
async def resolve_tenant(x_user_id: str = Header(..., description="用户 ID"),
                         x_tenant_code: Optional[str] = Header(None, description="指定的租户编码")) -> Dict[str, Any]:
    """解析当前用户激活的租户"""
    tenant_code = await tenant_service.get_tenant_for_user(x_user_id, x_tenant_code)
    if not tenant_code:
        raise HTTPException(status_code=400, detail="用户不属于任何租户")
    return {"tenant_code": tenant_code}


# ==================== 系统初始化 ====================

@router.on_event("startup")
async def startup():
    """服务启动时初始化多租户"""
    await init_tenant()
