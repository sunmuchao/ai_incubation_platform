"""
认证依赖和中间件
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from config.database import get_db
from services.service_manager import ServiceManager, get_service_manager
from config.logging_config import get_logger

logger = get_logger(__name__)

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    获取当前认证用户
    用于需要认证的 API 接口
    """
    if not credentials:
        return None

    token = credentials.credentials
    service_manager = get_service_manager(db)
    payload = service_manager.users.verify_token(token)

    if not payload:
        return None

    return payload


async def require_auth(
    user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    要求用户认证
    用于必须认证的 API 接口
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_id(
    user: Dict[str, Any] = Depends(require_auth)
) -> str:
    """
    获取当前用户 ID
    用于需要用户身份的业务逻辑
    """
    return user.get("user_id")


async def get_current_tenant_id(
    user: Dict[str, Any] = Depends(require_auth)
) -> str:
    """
    获取当前租户 ID
    用于多租户隔离
    """
    return user.get("tenant_id")
