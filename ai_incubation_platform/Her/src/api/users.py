"""
用户 API 路由 - 数据库版本

Identity 优化：
- 支持双令牌（access_token + refresh_token）
- 添加刷新令牌端点
- 集成缓存层
- 集成限流保护
"""
from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import List, Optional
import json

from models.user import User, UserCreate, UserProfile, UserUpdate, Gender, RelationshipGoal, SexualOrientation
from db.database import get_db
from db.repositories import UserRepository
from auth.jwt import (
    get_password_hash,
    create_token_pair,
    decode_refresh_token,
    TokenResponse,
    RefreshTokenRequest,
    UserCredentials,
    get_current_user,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from matching.matcher import MatchmakerAlgorithm
from utils.logger import logger
from config import settings
from cache import cache_manager
from middleware.rate_limiter import rate_limiter, rate_limit_login

# 创建全局匹配器实例
matchmaker = MatchmakerAlgorithm()

router = APIRouter(prefix="/api/users", tags=["users"])


def get_user_service(db=Depends(get_db)):
    """获取用户服务依赖注入"""
    return UserRepository(db)


@router.post("/register", response_model=User)
async def register_user(
    user_data: UserCreate,
    request: Request,
    service=Depends(get_user_service)
):
    """注册新用户

    安全特性：
    - 限流保护：防止批量注册攻击
    - 邮箱唯一性检查
    - 密码哈希存储（SHA-256 + bcrypt 双重哈希）
    """
    # 注册限流保护
    await rate_limit_login(request)

    logger.info(f"New user registration attempt: {user_data.email}")

    # 检查邮箱是否已存在
    existing = service.get_by_email(user_data.email)
    if existing:
        logger.warning(f"Registration failed: email already exists: {user_data.email}")
        raise HTTPException(status_code=400, detail="Email already registered")

    user_dict = user_data.model_dump()
    user_dict["id"] = str(__import__('uuid').uuid4())

    # 生成 password_hash，避免数据库落明文 password
    # 生产环境强制要求显式 password；测试/开发环境允许缺省并使用默认测试密码。
    default_test_password = "testpassword123"
    password = user_data.password if getattr(user_data, "password", None) else None
    if not password:
        if settings.environment == "production":
            raise HTTPException(status_code=422, detail="password is required")
        password = default_test_password

    # 检测前端是否已经对密码进行了 SHA-256 哈希
    # SHA-256 哈希格式：64 个十六进制字符
    is_sha256_hash = len(password) == 64 and all(c in '0123456789abcdef' for c in password.lower())

    if is_sha256_hash:
        # 前端已哈希：对 SHA-256 哈希再进行 bcrypt 存储
        user_dict["password_hash"] = get_password_hash(password)
    else:
        # 原始密码：进行 bcrypt 哈希（向后兼容）
        user_dict["password_hash"] = get_password_hash(password)

    user_dict.pop("password", None)

    db_user = service.create(user_dict)
    logger.info(f"User created successfully: {db_user.id}")

    # 注册到匹配系统
    matchmaker.register_user(_from_db(db_user).model_dump())
    logger.info(f"User registered to matching system: {db_user.id}")

    return _from_db(db_user)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserCredentials,
    request: Request,
    service=Depends(get_user_service)
):
    """用户登录（返回 access_token + refresh_token）

    支持多种登录方式：邮箱、用户名、手机号

    安全特性：
    - 限流保护：同一客户端 10 次突发，1 次/秒补充
    - 密码错误日志记录
    """
    # Identity: 登录限流保护 - 防止暴力破解
    await rate_limit_login(request)

    logger.info(f"Login attempt START: username={credentials.username}")
    logger.info(f"Login credentials: username={credentials.username}, password_length={len(credentials.password)}")

    # 尝试多种登录方式：邮箱、用户名、手机号
    user = None

    # 1. 先尝试邮箱登录
    if '@' in credentials.username:
        logger.info(f"Login: Trying email lookup for: {credentials.username}")
        user = service.get_by_email(credentials.username)
        if user:
            logger.info(f"Login found user by email: {credentials.username}, user_id={user.id}, password_hash_exists={bool(user.password_hash)}")
        else:
            logger.warning(f"Login: No user found with email: {credentials.username}")

    # 2. 如果没有找到，尝试用户名登录
    if not user:
        logger.info(f"Login: Trying username lookup for: {credentials.username}")
        user = service.get_by_username(credentials.username)
        if user:
            logger.info(f"Login found user by username: {credentials.username}, user_id={user.id}")

    # 3. 如果还是没有找到，尝试手机号登录
    if not user and credentials.username.startswith('1'):
        logger.info(f"Login: Trying phone lookup for: {credentials.username}")
        user = service.get_by_phone(credentials.username)
        if user:
            logger.info(f"Login found user by phone: {credentials.username}, user_id={user.id}")

    logger.info(f"Login: Final user lookup result: {'FOUND' if user else 'NOT_FOUND'}")

    if not user or not user.password_hash:
        logger.warning(f"Login failed: user not found or no password_hash for: {credentials.username}")
        logger.warning(f"Login failed details: user={user}, password_hash_exists={bool(user.password_hash) if user else 'N/A'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # 调试密码验证
    logger.info(f"Login: Verifying password for user: {user.id}")
    password_valid = verify_password(credentials.password, user.password_hash)
    logger.info(f"Login: Password verification result: {password_valid}")

    if not password_valid:
        logger.warning(f"Login failed: invalid password for user: {user.id}")
        logger.warning(f"Login failed: stored password_hash prefix: {user.password_hash[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # 生成令牌对
    access_token, refresh_token = create_token_pair(user.id)
    logger.info(f"Login successful for user: {user.id}")

    # AI Native: 触发用户登录事件，取消激活推送计划
    try:
        from agent.autonomous.event_listener import emit_event
        emit_event(
            event_type="user_login",
            event_data={
                "user_id": user.id,
                "login_method": "credentials",
            },
            event_source=user.id
        )
        logger.info(f"Login event 'user_login' emitted for user {user.id}")
    except Exception as e:
        logger.warning(f"Failed to emit user_login event: {e}")

    # 存储用户信息到 localStorage 供前端使用
    user_info = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "location": user.location,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
    }
    # 将用户信息添加到响应头部（前端可通过响应获取）
    from fastapi.responses import JSONResponse
    return JSONResponse(
        content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_expires_in": REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            "user": user_info
        }
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, service=Depends(get_user_service)):
    """
    刷新令牌

    使用 refresh_token 获取新的 access_token 和 refresh_token
    旧的 refresh_token 会被作废（轮换机制）
    """
    logger.info("Token refresh request received")

    # 检查 token 是否已被撤销
    if is_token_revoked(request.refresh_token):
        logger.warning("Token refresh failed: token has been revoked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    # 验证 refresh_token
    user_id = decode_refresh_token(request.refresh_token)
    if not user_id:
        logger.warning("Token refresh failed: invalid or expired refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # 检查用户是否仍存在且活跃
    db_user = service.get_by_id(user_id)
    if not db_user or not db_user.is_active:
        logger.warning(f"Token refresh failed: user not found or inactive: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # 生成新的令牌对（轮换机制）
    access_token, new_refresh_token = create_token_pair(user_id)

    # 撤销旧的 refresh token（轮换机制）
    revoke_refresh_token(request.refresh_token)

    logger.info(f"Token refreshed for user: {user_id}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )


@router.get("/", response_model=List[User])
async def list_users(service=Depends(get_user_service)):
    """获取所有用户列表"""
    db_users = service.list_all()
    return [_from_db(u) for u in db_users]


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, service=Depends(get_user_service)):
    """获取用户详情"""
    # 先从缓存读取
    cached_profile = cache_manager.get_profile(user_id)
    if cached_profile:
        logger.debug(f"User cache hit: {user_id}")
        return User(**cached_profile)

    # 缓存未命中，从数据库读取
    db_user = service.get_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    user = _from_db(db_user)

    # 写入缓存
    cache_manager.set_profile(user_id, user.model_dump())

    return user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user_id: str = Depends(get_current_user),
    service=Depends(get_user_service)
):
    """更新用户信息"""
    db_user = service.get_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 权限检查
    if db_user.id != current_user_id:
        raise HTTPException(status_code=403, detail="Not allowed to update this user")

    update_data = user_data.model_dump(exclude_unset=True)
    updated_user = service.update(user_id, update_data)

    # 更新匹配系统
    matchmaker.unregister_user(user_id)
    matchmaker.register_user(_from_db(updated_user).model_dump())

    # 清除缓存
    cache_manager.invalidate_profile(user_id)
    cache_manager.invalidate_match_result(user_id)

    return _from_db(updated_user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user_id: str = Depends(get_current_user),
    service=Depends(get_user_service)
):
    """删除用户"""
    db_user = service.get_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 权限检查
    if db_user.id != current_user_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this user")

    # 从匹配系统注销
    matchmaker.unregister_user(user_id)
    service.delete(user_id)

    # 清除所有缓存
    cache_manager.invalidate_profile(user_id)
    cache_manager.invalidate_match_result(user_id)

    return {"message": "User deleted"}


@router.get("/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(user_id: str, service=Depends(get_user_service)):
    """获取用户完整画像"""
    db_user = service.get_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    user = _from_db(db_user)

    # 生成性格评分
    personality_scores = {
        'openness': user.values.get('openness', 0.5),
        'conscientiousness': user.values.get('conscientiousness', 0.5),
        'extraversion': user.values.get('extraversion', 0.5),
        'agreeableness': user.values.get('agreeableness', 0.5),
        'neuroticism': user.values.get('neuroticism', 0.5),
    }

    # 兼容性画像
    compatibility_profile = {
        'communication': 0.8,
        'lifestyle': 0.7,
        'long_term_goals': 0.9,
    }

    return UserProfile(
        user_id=user_id,
        personality_scores=personality_scores,
        compatibility_profile=compatibility_profile,
        deal_breakers=['smoking', 'debt']  # 示例
    )


# ========== 密码重置相关模型 ==========

from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import secrets


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    token: str
    new_password: str  # 前端已 SHA-256 哈希


class PasswordResetResponse(BaseModel):
    """密码重置响应"""
    success: bool
    message: str


# ========== 密码重置端点 ==========

# 临时存储重置 token（生产环境应使用 Redis）
_password_reset_tokens = {}  # {token: {"email": str, "expires_at": datetime}}


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    http_request: Request,
    service=Depends(get_user_service)
):
    """
    忘记密码 - 发送重置邮件

    安全特性：
    - 限流保护
    - 不泄露用户是否存在信息
    - Token 1 小时有效
    """
    # 限流保护
    await rate_limit_login(http_request)

    # 查找用户
    user = service.get_by_email(request.email)

    # 安全考虑：无论用户是否存在，都返回相同响应，避免枚举攻击
    if not user:
        logger.info(f"Password reset requested for non-existent email: {request.email}")
        return PasswordResetResponse(
            success=True,
            message="如果该邮箱已注册，重置邮件将在几分钟内送达"
        )

    # 生成重置 token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    # 存储 token（生产环境应使用 Redis）
    _password_reset_tokens[reset_token] = {
        "email": request.email,
        "user_id": user.id,
        "expires_at": expires_at
    }

    # 邮件发送需要配置 SMTP 服务（当前开发环境打印到日志）
    # 生产环境应集成邮件服务（如阿里云邮件推送）
    # 目前开发环境：打印 token 到日志
    logger.info(f"Password reset token for {request.email}: {reset_token}")

    # 开发环境：返回 token（生产环境应移除）
    if settings.environment == "development":
        logger.info(f"[DEV] Reset link: /reset-password?token={reset_token}")

    return PasswordResetResponse(
        success=True,
        message="如果该邮箱已注册，重置邮件将在几分钟内送达"
    )


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    request: ResetPasswordRequest,
    http_request: Request,
    service=Depends(get_user_service)
):
    """
    重置密码 - 使用 token 设置新密码

    安全特性：
    - Token 一次性使用
    - Token 过期机制
    - 密码强度验证
    """
    # 限流保护
    await rate_limit_login(http_request)

    # 验证 token
    token_data = _password_reset_tokens.get(request.token)

    if not token_data:
        logger.warning(f"Invalid reset token used: {request.token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置链接无效或已过期"
        )

    # 检查是否过期
    if datetime.utcnow() > token_data["expires_at"]:
        del _password_reset_tokens[request.token]
        logger.warning(f"Expired reset token used: {request.token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置链接已过期，请重新申请"
        )

    # 获取用户
    user = service.get_by_id(token_data["user_id"])
    if not user:
        del _password_reset_tokens[request.token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户不存在"
        )

    # 验证密码强度（SHA-256 哈希后应为 64 位十六进制）
    new_password = request.new_password
    is_sha256_hash = len(new_password) == 64 and all(c in '0123456789abcdef' for c in new_password.lower())

    if not is_sha256_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码格式错误"
        )

    # 更新密码
    user.password_hash = get_password_hash(new_password)
    service.db.commit()

    # 删除已使用的 token
    del _password_reset_tokens[request.token]

    logger.info(f"Password reset successful for user: {user.id}")

    return PasswordResetResponse(
        success=True,
        message="密码重置成功，请使用新密码登录"
    )


# ========== Token 撤销机制（Values） ==========

# 已撤销的 refresh token（生产环境应使用 Redis）
_revoked_tokens = set()


def revoke_refresh_token(token: str) -> None:
    """撤销 refresh token"""
    _revoked_tokens.add(token)


def is_token_revoked(token: str) -> bool:
    """检查 token 是否已被撤销"""
    return token in _revoked_tokens


@router.post("/logout")
async def logout(
    request: RefreshTokenRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    登出 - 撤销 refresh token

    安全特性：
    - 撤销 refresh token，防止被滥用
    - 前端应同时清除本地存储的 token
    """
    if request.refresh_token:
        revoke_refresh_token(request.refresh_token)
        logger.info(f"User logged out, token revoked: {current_user_id}")

    return {"success": True, "message": "登出成功"}


def _from_db(db_user) -> User:
    """将数据库模型转换为 Pydantic 模型"""
    interests = []
    if db_user.interests:
        try:
            interests = json.loads(db_user.interests)
        except json.JSONDecodeError:
            interests = db_user.interests.split(",") if db_user.interests else []

    values = {}
    if db_user.values:
        try:
            values = json.loads(db_user.values)
        except json.JSONDecodeError:
            pass

    return User(
        id=db_user.id,
        name=db_user.name,
        email=db_user.email,
        age=db_user.age,
        gender=Gender(db_user.gender),
        location=db_user.location,
        avatar=db_user.avatar_url,
        bio=db_user.bio,
        preferred_age_min=db_user.preferred_age_min,
        preferred_age_max=db_user.preferred_age_max,
        preferred_gender=Gender(db_user.preferred_gender) if db_user.preferred_gender else None,
        interests=interests,
        values=values,
        goal=RelationshipGoal.SERIOUS,  # 简化处理
        sexual_orientation=SexualOrientation(getattr(db_user, 'sexual_orientation', 'heterosexual')) if hasattr(db_user, 'sexual_orientation') and db_user.sexual_orientation else SexualOrientation.HETEROSEXUAL
    )
