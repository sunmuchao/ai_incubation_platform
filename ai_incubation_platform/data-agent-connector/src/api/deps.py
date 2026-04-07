"""
API 依赖项
提供公共依赖注入，如API密钥验证、用户信息获取等
"""
from fastapi import Header, HTTPException, status
from typing import Optional
from config.settings import settings
from utils.logger import request_id_var, user_id_var, generate_request_id


async def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    x_request_id: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> None:
    """验证API密钥并设置上下文"""
    # 设置请求ID
    request_id = x_request_id or generate_request_id()
    request_id_var.set(request_id)

    # 设置用户ID
    if x_user_id:
        user_id_var.set(x_user_id)

    # 如果配置了API密钥则进行验证
    if settings.security.api_key and x_api_key != settings.security.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )


async def get_user_role(x_user_role: Optional[str] = Header(None)) -> str:
    """获取用户角色，默认返回只读角色"""
    if not x_user_role or x_user_role not in settings.security.allow_roles:
        return settings.security.default_role
    return x_user_role
