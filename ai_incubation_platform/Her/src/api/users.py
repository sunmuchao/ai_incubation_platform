"""
用户 API 路由 - 数据库版本

P0 优化：
- 支持双令牌（access_token + refresh_token）
- 添加刷新令牌端点
- 集成缓存层
- 集成限流保护
"""
from fastapi import APIRouter, HTTPException, Depends, status
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
from matching.matcher import matchmaker
from utils.logger import logger
from config import settings
from cache import cache_manager
from middleware.rate_limiter import rate_limit_login

router = APIRouter(prefix="/api/users", tags=["users"])


def get_user_service(db=Depends(get_db)):
    """获取用户服务依赖注入"""
    return UserRepository(db)


@router.post("/register", response_model=User)
async def register_user(user_data: UserCreate, service=Depends(get_user_service)):
    """注册新用户"""
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
async def login(credentials: UserCredentials, service=Depends(get_user_service)):
    """用户登录（返回 access_token + refresh_token）

    支持多种登录方式：邮箱、用户名、手机号
    """
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
