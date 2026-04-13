"""
JWT 认证模块

支持 access_token 和 refresh_token 双令牌机制：
- access_token: 短期有效（默认 60 分钟），用于 API 认证
- refresh_token: 长期有效（默认 7 天），用于刷新 access_token
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings
from utils.logger import logger
import bcrypt as bcrypt_lib
import secrets

# 配置
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = getattr(settings, 'jwt_refresh_expire_days', 7)

# HTTP Bearer 认证（可选）
security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """Token 载荷"""
    user_id: str
    exp: datetime
    token_type: str = "access"  # access 或 refresh


class UserCredentials(BaseModel):
    """用户登录凭证"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应（双令牌）"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码

    支持两种场景：
    1. plain_password 是原始密码 - 使用 bcrypt 验证
    2. plain_password 是 SHA-256 哈希（前端已哈希）- 使用 bcrypt 验证 SHA-256 哈希

    安全增强：
    - 前端对密码进行 SHA-256 哈希（确定性哈希）
    - 后端对 SHA-256 哈希再进行 bcrypt 存储
    - 传输过程中密码不以明文形式存在
    """
    if not plain_password or not hashed_password:
        return False

    # 检测前端是否已经对密码进行了 SHA-256 哈希
    # SHA-256 哈希格式：64 个十六进制字符
    is_sha256_hash = len(plain_password) == 64 and all(c in '0123456789abcdef' for c in plain_password.lower())

    if is_sha256_hash:
        # 前端已哈希：直接使用 bcrypt 验证 SHA-256 哈希
        # 数据库存储的是 bcrypt(SHA-256(原始密码))
        try:
            pw_bytes = plain_password.encode("utf-8")[:72]
            return bcrypt_lib.checkpw(pw_bytes, hashed_password.encode("utf-8"))
        except Exception:
            return False
    else:
        # 原始密码：标准 bcrypt 验证（向后兼容）
        try:
            pw_bytes = plain_password.encode("utf-8")[:72]
            return bcrypt_lib.checkpw(pw_bytes, hashed_password.encode("utf-8"))
        except Exception:
            return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    if password is None:
        raise ValueError("password must not be None")
    pw_bytes = password.encode("utf-8")[:72]
    hashed = bcrypt_lib.hashpw(pw_bytes, bcrypt_lib.gensalt())
    return hashed.decode("utf-8")


def _create_token(user_id: str, token_type: str, expires_delta: timedelta) -> str:
    """创建令牌（内部方法）"""
    expire = datetime.utcnow() + expires_delta

    to_encode = {
        "user_id": user_id,
        "exp": expire,
        "token_type": token_type,
        "jti": secrets.token_hex(16)  # 唯一标识，支持令牌撤销
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Created {token_type} token for user: {user_id}, expires at: {expire}")
    return encoded_jwt


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问 Token"""
    if expires_delta:
        expire = expires_delta
    else:
        expire = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(user_id, "access", expire)


def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """创建刷新 Token"""
    if expires_delta:
        expire = expires_delta
    else:
        expire = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(user_id, "refresh", expire)


def create_token_pair(user_id: str) -> Tuple[str, str]:
    """创建令牌对（access + refresh）"""
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return access_token, refresh_token


def decode_access_token(token: str) -> Optional[str]:
    """解码访问 Token，返回 user_id"""
    return _decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> Optional[str]:
    """解码刷新 Token，返回 user_id"""
    return _decode_token(token, expected_type="refresh")


def _decode_token(token: str, expected_type: str = "access") -> Optional[str]:
    """解码 Token（内部方法）"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        token_type: str = payload.get("token_type", "access")

        if user_id is None:
            logger.warning("Token decoded but user_id is missing")
            return None

        if token_type != expected_type:
            logger.warning(f"Token type mismatch: expected {expected_type}, got {token_type}")
            return None

        logger.debug(f"{expected_type} token decoded successfully for user: {user_id}")
        return user_id
    except JWTError as e:
        # 避免在日志中泄露 token 内容/解析细节
        logger.warning(f"Failed to decode {expected_type} token")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    获取当前用户 ID（依赖注入）
    使用方式：user_id: str = Depends(get_current_user)

    返回 user_id 字符串，端点可基于此进行数据库查询
    """
    token = credentials.credentials
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    获取当前用户 ID（可选）- 开发环境允许匿名访问

    使用方式：current_user = Depends(get_current_user_optional)

    支持三种认证方式：
    1. Bearer Token（生产/开发环境）
    2. X-Dev-User-Id Header（开发环境调试用）
    3. 返回匿名用户（开发环境，无认证）
    """
    from config import settings

    logger.info(f"[get_current_user_optional] credentials: {credentials is not None}")
    if credentials:
        logger.info(f"[get_current_user_optional] token (first 50 chars): {credentials.credentials[:50] if credentials.credentials else 'None'}")

    # 1. 尝试从 Bearer Token 获取用户
    try:
        if credentials and credentials.credentials:
            token = credentials.credentials
            user_id = decode_access_token(token)
            logger.info(f"[get_current_user_optional] token decoded to user_id: {user_id}")
            if user_id:
                return {"user_id": user_id, "is_anonymous": False}
    except Exception as e:
        logger.warning(f"[get_current_user_optional] Token decode failed: {e}")

    # 2. 开发环境：尝试从 X-Dev-User-Id Header 获取用户
    if settings.environment == "development":
        dev_user_id = request.headers.get("X-Dev-User-Id")
        if dev_user_id:
            logger.info(f"[get_current_user_optional] using X-Dev-User-Id: {dev_user_id}")
            return {"user_id": dev_user_id, "is_anonymous": True}

        logger.info("[get_current_user_optional] returning anonymous user for dev environment")
        return {"user_id": "user-anonymous-dev", "is_anonymous": True}

    # 生产环境：必须认证
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def authenticate_user(username: str, password: str, stored_hash: str) -> Optional[str]:
    """
    认证用户
    返回 user_id 如果认证成功
    """
    if not verify_password(password, stored_hash):
        logger.warning(f"Failed authentication attempt for username: {username}")
        return None
    logger.info(f"User authenticated successfully: {username}")
    # 这里使用 username 作为 user_id（简化处理）
    return username


async def get_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    获取管理员用户 ID（依赖注入）

    使用方式：admin_user_id: str = Depends(get_admin_user)

    验证流程：
    1. 解析 Bearer Token 获取 user_id
    2. 查询数据库获取用户信息
    3. 检查用户是否是管理员

    Returns:
        str: 管理员用户的 user_id

    Raises:
        HTTPException: 401 如果 token 无效
        HTTPException: 403 如果用户不是管理员
    """
    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 查询数据库获取用户信息
    from utils.db_session_manager import db_session
    from db.models import UserDB

    with db_session() as db:
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查是否是管理员
        from utils.admin_check import is_admin_user
        if not is_admin_user(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限才能执行此操作"
            )

    return user_id
