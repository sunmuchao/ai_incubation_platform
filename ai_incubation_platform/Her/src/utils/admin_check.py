"""
管理员权限检查工具

提供统一的 admin 权限验证函数。
"""
from fastapi import HTTPException, status
from typing import TYPE_CHECKING
from config import settings

if TYPE_CHECKING:
    from db.models import UserDB


def is_admin_user(current_user: "UserDB") -> bool:
    """
    检查当前用户是否为管理员

    判定规则：
    1. 用户 email 在 ADMIN_EMAILS 配置列表中
    2. 或者用户 id 为特定的 admin id（预留）

    Args:
        current_user: 当前登录用户

    Returns:
        bool: 是否为管理员
    """
    if not current_user:
        return False

    # 检查 email 是否在管理员列表中
    return current_user.email in settings.admin_emails


def require_admin(current_user: "UserDB") -> None:
    """
    要求当前用户必须是管理员，否则抛出异常

    Args:
        current_user: 当前登录用户

    Raises:
        HTTPException: 403 Forbidden 如果用户不是管理员
    """
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限才能执行此操作"
        )
