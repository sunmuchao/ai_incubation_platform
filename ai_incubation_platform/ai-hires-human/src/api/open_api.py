"""
开放 API 路由 - 支持第三方开发者集成。
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_session
from services.api_key_service import APIKeyService, DeveloperService, APIUsageService, hash_api_key
from models.api_key import APIKeyDB

router = APIRouter(prefix="/api/open", tags=["open-api"])


# ==================== Pydantic 模型 ====================

class APIKeyCreateRequest(BaseModel):
    """创建 API 密钥请求。"""
    name: str = Field(..., description="密钥名称")
    description: Optional[str] = Field(None, description="密钥描述")
    scopes: Optional[List[str]] = Field(default=["tasks:read", "tasks:write", "workers:read"], description="权限范围")
    rate_limit: int = Field(default=1000, description="每分钟请求数限制")
    rate_limit_daily: int = Field(default=10000, description="每日请求数限制")
    expires_in_days: Optional[int] = Field(None, description="过期天数")


class APIKeyResponse(BaseModel):
    """API 密钥响应。"""
    key_id: str
    key_prefix: str
    name: str
    description: Optional[str]
    owner_type: str
    scopes: List[str]
    rate_limit: int
    rate_limit_daily: int
    is_active: bool
    is_revoked: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """API 密钥创建响应。"""
    key_id: str
    key_prefix: str
    full_key: str  # 仅在创建时返回
    name: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    warning: str = "请安全保存此密钥，它只会显示这一次！"


class DeveloperProfileRequest(BaseModel):
    """开发者档案更新请求。"""
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    developer_type: Optional[str] = None
    applications: Optional[List[dict]] = None


class DeveloperProfileResponse(BaseModel):
    """开发者档案响应。"""
    developer_id: str
    name: str
    email: str
    company: Optional[str]
    website: Optional[str]
    developer_type: str
    is_verified: bool
    applications: List[dict]
    total_api_calls: int
    total_tasks_created: int
    created_at: datetime

    class Config:
        from_attributes = True


class UsageStatsResponse(BaseModel):
    """使用统计响应。"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_latency_ms: float
    period_start: datetime
    period_end: datetime


# ==================== 认证依赖 ====================

async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
) -> APIKeyDB:
    """验证 API 密钥。"""
    if not x_api_key and not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide via X-API-Key header or Authorization: Bearer <token>",
        )

    # 从 Authorization 头中提取
    if not x_api_key and authorization:
        if authorization.startswith("Bearer "):
            x_api_key = authorization[7:]

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format",
        )

    # 获取数据库会话
    db_session = await anext(get_db_session())

    # 哈希密钥并查找
    key_hash = hash_api_key(x_api_key)
    api_key_service = APIKeyService(db_session)
    api_key = await api_key_service.get_api_key_by_hash(key_hash)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if not api_key.is_active or api_key.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has been revoked or is inactive",
        )

    if api_key.expires_at and datetime.now() > api_key.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # 检查速率限制
    rate_check = await api_key_service.check_rate_limit(api_key.key_id)
    if not rate_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_check["reason"],
        )

    # 更新使用计数
    await api_key_service.increment_usage(api_key.key_id)
    await api_key_service.update_last_used(api_key.key_id)

    return api_key


# ==================== API 密钥管理 ====================

@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建新的 API 密钥。

    需要使用现有的 API 密钥进行认证。
    """
    # 验证是否有创建密钥的权限
    if "api_keys:write" not in api_key.scopes and api_key.owner_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create API keys",
        )

    api_key_service = APIKeyService(db)

    # 创建新密钥
    new_key = await api_key_service.create_api_key(
        owner_id=api_key.owner_id,
        name=request.name,
        description=request.description,
        scopes=request.scopes,
        rate_limit=request.rate_limit,
        rate_limit_daily=request.rate_limit_daily,
        expires_in_days=request.expires_in_days,
    )

    return APIKeyCreateResponse(
        key_id=new_key.key_id,
        key_prefix=new_key.key_prefix,
        full_key=getattr(new_key, "_plain_key", ""),
        name=new_key.name,
        scopes=new_key.scopes,
        created_at=new_key.created_at,
        expires_at=new_key.expires_at,
        warning="请安全保存此密钥，它只会显示这一次！",
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """列出当前用户的所有 API 密钥。"""
    api_key_service = APIKeyService(db)
    keys = await api_key_service.list_api_keys(api_key.owner_id)
    return keys


@router.get("/api-keys/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """获取指定 API 密钥的详情。"""
    api_key_service = APIKeyService(db)
    key = await api_key_service.get_api_key_by_id(key_id)

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    # 验证所有权
    if key.owner_id != api_key.owner_id and api_key.owner_type != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return key


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    reason: str = "User requested",
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """吊销 API 密钥。"""
    api_key_service = APIKeyService(db)
    key = await api_key_service.get_api_key_by_id(key_id)

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    # 验证所有权
    if key.owner_id != api_key.owner_id and api_key.owner_type != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    success = await api_key_service.revoke_api_key(key_id, reason)
    return {"message": "API key revoked successfully", "key_id": key_id}


# ==================== 开发者档案 ====================

@router.get("/developer/profile", response_model=DeveloperProfileResponse)
async def get_developer_profile(
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """获取开发者档案。"""
    developer_service = DeveloperService(db)
    profile = await developer_service.get_developer(api_key.owner_id)

    if not profile:
        # 自动创建档案
        profile = await developer_service.get_or_create_developer(
            developer_id=api_key.owner_id,
            name="Unknown Developer",
            email="",
        )

    return profile


@router.put("/developer/profile", response_model=DeveloperProfileResponse)
async def update_developer_profile(
    request: DeveloperProfileRequest,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """更新开发者档案。"""
    developer_service = DeveloperService(db)
    update_data = request.model_dump(exclude_none=True)
    profile = await developer_service.update_developer(api_key.owner_id, **update_data)
    return profile


# ==================== 使用统计 ====================

@router.get("/usage/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    days: int = Query(default=7, ge=1, le=90, description="查询天数"),
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """获取 API 使用统计。"""
    api_key_service = APIUsageService(db)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    stats = await api_key_service.get_usage_stats(
        api_key_id=api_key.key_id,
        start_date=start_date,
        end_date=end_date,
    )

    return UsageStatsResponse(
        **stats,
        period_start=start_date,
        period_end=end_date,
    )


# ==================== 平台统计（公开） ====================

@router.get("/platform/stats")
async def get_platform_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取平台整体统计数据（公开接口，无需认证）。

    返回平台整体的任务、工人、交易额等统计信息。
    """
    from sqlalchemy import func
    from models.db_models import TaskDB, WorkerProfileDB, PaymentTransactionDB

    # 任务统计
    task_result = await db.execute(
        select(
            func.count(TaskDB.id),
            func.sum(TaskDB.reward_amount).filter(TaskDB.status == "completed"),
        )
    )
    total_tasks, total_reward_paid = task_result.first()

    # 工人统计
    worker_result = await db.execute(select(func.count(WorkerProfileDB.worker_id)))
    total_workers = worker_result.scalar()

    # 交易统计
    payment_result = await db.execute(
        select(func.count(PaymentTransactionDB.id)).where(PaymentTransactionDB.status == "completed")
    )
    total_transactions = payment_result.scalar()

    return {
        "total_tasks": total_tasks or 0,
        "total_workers": total_workers or 0,
        "total_reward_paid": total_reward_paid or 0.0,
        "total_transactions": total_transactions or 0,
        "currency": "CNY",
    }


# ==================== 中间件：API 使用日志 ====================

from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware


class APIUsageLoggingMiddleware(BaseHTTPMiddleware):
    """API 使用日志中间件。"""

    async def dispatch(self, request: Request, call_next):
        # 记录开始时间
        start_time = time.time()

        # 处理请求
        response = await call_next(request)

        # 计算耗时
        latency_ms = int((time.time() - start_time) * 1000)

        # 仅记录 /api/open 开头的请求
        if request.url.path.startswith("/api/open"):
            # 尝试获取 API 密钥
            x_api_key = request.headers.get("x-api-key")
            authorization = request.headers.get("authorization")

            api_key_id = "unknown"
            if x_api_key:
                api_key_id = hash_api_key(x_api_key)[:16]  # 仅记录前缀
            elif authorization and authorization.startswith("Bearer "):
                api_key_id = hash_api_key(authorization[7:])[:16]

            # 异步记录日志（不阻塞响应）
            try:
                db_session = await anext(get_db_session())
                usage_service = APIUsageService(db_session)

                # 获取响应体大小
                response_size = 0
                async for chunk in response.body_iterator:
                    response_size += len(chunk)

                await usage_service.log_request(
                    api_key_id=api_key_id,
                    endpoint=str(request.url.path),
                    method=request.method,
                    response_status=response.status_code,
                    response_size=response_size,
                    latency_ms=latency_ms,
                    client_ip=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
            except Exception as e:
                # 日志记录失败不影响主流程
                pass

        return response
