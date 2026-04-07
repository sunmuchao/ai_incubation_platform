"""
用户认证 API 路由

提供用户注册、登录、认证等功能
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal, Base, engine
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ==================== 数据库模型 ====================

class User(Base):
    """用户账号表"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="worker")  # worker or employer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 请求/响应模型 ====================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=6)
    role: str = "worker"  # worker or employer


class AuthResponse(BaseModel):
    """认证响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: dict


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    email: str
    role: str


# ==================== 工具函数 ====================

def hash_password(password: str) -> str:
    """简单的密码哈希（生产环境应使用 bcrypt）"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return hash_password(password) == password_hash


def create_token(user_id: str, username: str, role: str) -> str:
    """创建简单的 JWT token（生产环境应使用 PyJWT）"""
    import base64
    import json
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session


# ==================== API 端点 ====================

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    用户注册
    
    - **username**: 用户名（3-50 个字符）
    - **email**: 邮箱地址
    - **password**: 密码（至少 6 个字符）
    - **role**: 角色（worker 或 employer）
    """
    async with AsyncSessionLocal() as session:
        # 检查用户名是否已存在
        result = await session.execute(
            sa.select(User).where(User.username == request.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 检查邮箱是否已存在
        result = await session.execute(
            sa.select(User).where(User.email == request.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被注册")
        
        # 创建新用户
        user = User(
            username=request.username,
            email=request.email,
            password_hash=hash_password(request.password),
            role=request.role
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # 生成 token
        access_token = create_token(user.id, user.username, user.role)
        refresh_token = create_token(user.id, user.username, user.role)  # 简化处理
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    用户登录
    
    - **username**: 用户名或邮箱
    - **password**: 密码
    """
    async with AsyncSessionLocal() as session:
        # 查找用户（支持用户名或邮箱登录）
        result = await session.execute(
            sa.select(User).where(
                (User.username == request.username) | (User.email == request.username)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账号已被禁用")
        
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 生成 token
        access_token = create_token(user.id, user.username, user.role)
        refresh_token = create_token(user.id, user.username, user.role)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }


@router.get("/me", response_model=UserResponse)
async def get_current_user(x_authorization: Optional[str] = Header(None)):
    """获取当前用户信息"""
    if not x_authorization:
        raise HTTPException(status_code=401, detail="未授权")
    
    # 简化处理，实际需要解析 JWT token
    async with AsyncSessionLocal() as session:
        # 这里简化处理，实际应该从 token 中解析用户 ID
        raise HTTPException(status_code=501, detail="此功能尚未实现")


@router.post("/logout")
async def logout():
    """用户登出"""
    return {"message": "登出成功"}
