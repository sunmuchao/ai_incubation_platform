"""
团队权限中间件。

提供基于组织的权限校验功能，确保用户只能访问其有权限的组织和数据。
"""
from functools import wraps
from typing import List, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionDenied(Exception):
    """权限不足异常。"""
    pass


async def check_org_permission(
    db: AsyncSession,
    org_id: str,
    user_id: str,
    required_permission: str
) -> bool:
    """
    检查用户在指定组织是否有特定权限。

    Args:
        db: 数据库会话
        org_id: 组织 ID
        user_id: 用户 ID
        required_permission: 所需权限

    Returns:
        是否有权限

    Raises:
        PermissionDenied: 权限不足
    """
    from services.team_service import TeamService

    service = TeamService(db)

    # 获取用户权限
    permissions = await service.get_user_permissions(org_id, user_id)

    if required_permission not in permissions:
        raise PermissionDenied(
            f"User {user_id} does not have permission {required_permission} in organization {org_id}"
        )

    return True


async def check_org_membership(
    db: AsyncSession,
    org_id: str,
    user_id: str
) -> bool:
    """
    检查用户是否是组织成员。

    Args:
        db: 数据库会话
        org_id: 组织 ID
        user_id: 用户 ID

    Returns:
        是否是成员

    Raises:
        PermissionDenied: 不是组织成员
    """
    from services.team_service import TeamService

    service = TeamService(db)
    member_info = await service.get_user_roles(org_id, user_id)

    if not member_info["is_member"]:
        raise PermissionDenied(
            f"User {user_id} is not a member of organization {org_id}"
        )

    return True


def require_permission(required_permission: str, org_id_param: str = "org_id"):
    """
    权限检查装饰器。

    用法:
        @router.get("/organizations/{org_id}/tasks")
        @require_permission("task:read", org_id_param="org_id")
        async def list_tasks(org_id: str, current_user_id: str, db: AsyncSession):
            ...

    Args:
        required_permission: 所需权限
        org_id_param: 组织 ID 参数名
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取参数
            request = kwargs.get("request")
            if not request:
                # 尝试从 kwargs 获取
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # 获取组织 ID 和用户 ID
            org_id = kwargs.get(org_id_param)
            if not org_id and request:
                org_id = request.path_params.get(org_id_param)
            if not org_id:
                org_id = request.query_params.get("org_id") if request else None

            # 从查询参数获取用户 ID（实际应该从认证系统获取）
            user_id = kwargs.get("current_user_id")
            if not user_id and request:
                user_id = request.query_params.get("current_user_id")

            db = kwargs.get("db")

            if not all([org_id, user_id, db]):
                raise HTTPException(
                    status_code=400,
                    detail="Missing required parameters for permission check"
                )

            try:
                await check_org_permission(db, org_id, user_id, required_permission)
            except PermissionDenied as e:
                raise HTTPException(
                    status_code=403,
                    detail=str(e),
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_membership(org_id_param: str = "org_id"):
    """
    组织成员检查装饰器。

    用法:
        @router.get("/organizations/{org_id}")
        @require_membership(org_id_param="org_id")
        async def get_organization(org_id: str, current_user_id: str, db: AsyncSession):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            org_id = kwargs.get(org_id_param)
            if not org_id and request:
                org_id = request.path_params.get(org_id_param)
            if not org_id:
                org_id = request.query_params.get("org_id") if request else None

            user_id = kwargs.get("current_user_id")
            if not user_id and request:
                user_id = request.query_params.get("current_user_id")

            db = kwargs.get("db")

            if not all([org_id, user_id, db]):
                raise HTTPException(
                    status_code=400,
                    detail="Missing required parameters for membership check"
                )

            try:
                await check_org_membership(db, org_id, user_id)
            except PermissionDenied as e:
                raise HTTPException(
                    status_code=403,
                    detail=str(e),
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ==================== 权限常量 ====================

class Permissions:
    """权限常量定义。"""

    # 任务权限
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_APPROVE = "task:approve"
    TASK_REJECT = "task:reject"

    # 工人权限
    WORKER_READ = "worker:read"
    WORKER_MANAGE = "worker:manage"

    # 财务权限
    FINANCIAL_READ = "financial:read"
    FINANCIAL_MANAGE = "financial:manage"

    # 团队权限
    TEAM_READ = "team:read"
    TEAM_MANAGE = "team:manage"

    # 设置权限
    SETTINGS_READ = "settings:read"
    SETTINGS_MANAGE = "settings:manage"

    # 报表权限
    REPORT_READ = "report:read"
    REPORT_EXPORT = "report:export"


# ==================== 权限映射 ====================

# API 路径到所需权限的映射
API_PERMISSION_MAP = {
    # 任务相关
    "POST:/api/tasks": Permissions.TASK_CREATE,
    "GET:/api/tasks": Permissions.TASK_READ,
    "PUT:/api/tasks": Permissions.TASK_UPDATE,
    "DELETE:/api/tasks": Permissions.TASK_DELETE,

    # 报表相关
    "GET:/api/reports": Permissions.REPORT_READ,
    "GET:/api/reports/export": Permissions.REPORT_EXPORT,
}


def get_required_permission(method: str, path: str) -> Optional[str]:
    """
    根据 API 方法获取所需权限。

    Args:
        method: HTTP 方法
        path: API 路径

    Returns:
        所需权限，如果没有映射则返回 None
    """
    key = f"{method}:{path}"
    return API_PERMISSION_MAP.get(key)
