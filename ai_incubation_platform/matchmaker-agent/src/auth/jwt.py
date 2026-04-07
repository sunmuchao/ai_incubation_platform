"""
JWT 认证模块

支持 access_token 和 refresh_token 双令牌机制：
- access_token: 短期有效（默认 60 分钟），用于 API 认证
- refresh_token: 长期有效（默认 7 天），用于刷新 access_token
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends
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

# HTTP Bearer 认证
security = HTTPBearer()


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
    """验证密码"""
    if not plain_password or not hashed_password:
        return False
    # bcrypt 限制：输入密码最多 72 bytes（超过需手动截断）
    pw_bytes = plain_password.encode("utf-8")[:72]
    try:
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
    使用方式：user_id = Depends(get_current_user)
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
