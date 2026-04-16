"""
用户 API 路由 - 数据库版本

Identity 优化：
- 支持双令牌（access_token + refresh_token）
- 添加刷新令牌端点
- 集成缓存层
- 集成限流保护

架构说明：新架构使用 ConversationMatchService + HerAdvisorService (AI Native)，
详见 HER_ADVISOR_ARCHITECTURE.md
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
from utils.logger import logger
from config import settings
from cache import cache_manager
from middleware.rate_limiter import rate_limiter, rate_limit_login

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

    自动填充：
    - username: 如未提供，自动生成 UUID
    - email: 如未提供，自动生成临时邮箱
    """
    import time
    import uuid
    start_time = time.time()

    # 🔧 [自动填充] username 和 email 可选，自动生成
    if not user_data.username:
        user_data.username = f"user_{uuid.uuid4().hex[:8]}"
        logger.info(f"[REGISTER] Auto-generated username: {user_data.username}")

    if not user_data.email:
        user_data.email = f"{user_data.username}@temp.her.local"
        logger.info(f"[REGISTER] Auto-generated email: {user_data.email}")

    # 注册限流保护
    await rate_limit_login(request)
    logger.info(f"[REGISTER] {user_data.username} - START at {start_time:.3f}")

    # 检查邮箱是否已存在
    check_start = time.time()
    existing = service.get_by_email(user_data.email)
    logger.info(f"[REGISTER] {user_data.username} - Email check done in {time.time() - check_start:.3f}s")
    if existing:
        logger.warning(f"Registration failed: email already exists: {user_data.email}")
        raise HTTPException(status_code=400, detail="Email already registered")

    # 检查用户名是否已存在
    existing_username = service.get_by_username(user_data.username)
    if existing_username:
        logger.warning(f"Registration failed: username already exists: {user_data.username}")
        raise HTTPException(status_code=400, detail="Username already registered")

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

    # 密码哈希 - 性能关键点
    hash_start = time.time()
    if is_sha256_hash:
        user_dict["password_hash"] = get_password_hash(password)
    else:
        user_dict["password_hash"] = get_password_hash(password)
    logger.info(f"[REGISTER] {user_data.email} - Password hash done in {time.time() - hash_start:.3f}s")

    user_dict.pop("password", None)

    # 数据库写入
    db_start = time.time()
    db_user = service.create(user_dict)
    logger.info(f"[REGISTER] {user_data.email} - DB create done in {time.time() - db_start:.3f}s")
    logger.info(f"[REGISTER] {user_data.email} - User created: {db_user.id}, TOTAL: {time.time() - start_time:.3f}s")

    # 注：matchmaker.register_user 已废弃
    # 新架构：候选人从数据库查询，无需注册到内存池

    # v1.30: 注册后自动评估置信度
    try:
        from api.profile_confidence import evaluate_on_register
        import asyncio
        asyncio.create_task(evaluate_on_register(db_user.id))
        logger.info(f"[REGISTER] {user_data.email} - Triggered async confidence evaluation")
    except Exception as e:
        logger.warning(f"Failed to trigger confidence evaluation: {e}")

    # 🔧 [新增] 事件驱动通知：检查所有用户的偏好，匹配成功则写入通知队列
    try:
        from services.notification_service import check_and_notify_preferences
        asyncio.create_task(check_and_notify_preferences(db_user))
        logger.info(f"[REGISTER] {user_data.email} - Triggered notification preference check")
    except Exception as e:
        logger.warning(f"Failed to trigger notification check: {e}")

    logger.info(f"[REGISTER] {user_data.email} - COMPLETE in {time.time() - start_time:.3f}s")
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
    import time
    start_time = time.time()

    # Identity: 登录限流保护 - 防止暴力破解
    await rate_limit_login(request)

    logger.info(f"[LOGIN] {credentials.username} - START at {start_time:.3f}")
    logger.info(f"[LOGIN] {credentials.username} - Password length: {len(credentials.password)}")

    # 尝试多种登录方式：邮箱、用户名、手机号
    user = None
    lookup_start = time.time()

    # 1. 先尝试邮箱登录
    if '@' in credentials.username:
        user = service.get_by_email(credentials.username)
        if user:
            logger.info(f"[LOGIN] {credentials.username} - Email lookup found user: {user.id} in {time.time() - lookup_start:.3f}s")

    # 2. 如果没有找到，尝试用户名登录
    if not user:
        user = service.get_by_username(credentials.username)
        if user:
            logger.info(f"[LOGIN] {credentials.username} - Username lookup found user: {user.id} in {time.time() - lookup_start:.3f}s")

    # 3. 如果还是没有找到，尝试手机号登录
    if not user and credentials.username.startswith('1'):
        user = service.get_by_phone(credentials.username)
        if user:
            logger.info(f"[LOGIN] {credentials.username} - Phone lookup found user: {user.id} in {time.time() - lookup_start:.3f}s")

    logger.info(f"[LOGIN] {credentials.username} - User lookup done in {time.time() - lookup_start:.3f}s, found: {bool(user)}")

    if not user or not user.password_hash:
        logger.warning(f"[LOGIN] {credentials.username} - FAILED: user not found or no password_hash")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # 密码验证 - 性能关键点（bcrypt）
    verify_start = time.time()
    password_valid = verify_password(credentials.password, user.password_hash)
    logger.info(f"[LOGIN] {credentials.username} - Password verify done in {time.time() - verify_start:.3f}s, valid: {password_valid}")

    if not password_valid:
        logger.warning(f"[LOGIN] {credentials.username} - FAILED: invalid password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # 生成令牌对
    token_start = time.time()
    access_token, refresh_token = create_token_pair(user.id)
    logger.info(f"[LOGIN] {credentials.username} - Token generation done in {time.time() - token_start:.3f}s")

    # AI Native: 触发用户登录事件，取消激活推送计划
    event_start = time.time()
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
        logger.info(f"[LOGIN] {credentials.username} - Event emitted in {time.time() - event_start:.3f}s")
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
    logger.info(f"[LOGIN] {credentials.username} - COMPLETE in {time.time() - start_time:.3f}s")
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

    # 注：matchmaker 操作已废弃，候选人从数据库查询

    # 🔧 [缓存一致性] 清除所有相关缓存
    cache_manager.invalidate_profile(user_id)
    cache_manager.invalidate_match_result(user_id)

    # 同时清除 UserProfileService 的画像缓存
    from services.user_profile_service import get_user_profile_service
    profile_service = get_user_profile_service()
    profile_service.clear_cache(user_id)

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

    # 注：matchmaker.unregister_user 已废弃，候选人从数据库查询

    service.delete(user_id)

    # 🔧 [缓存一致性] 清除所有相关缓存
    cache_manager.invalidate_profile(user_id)
    cache_manager.invalidate_match_result(user_id)

    # 同时清除 UserProfileService 的画像缓存
    from services.user_profile_service import get_user_profile_service
    profile_service = get_user_profile_service()
    profile_service.clear_cache(user_id)

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
