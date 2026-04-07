"""
API Key 管理 API

提供 API Key 的创建、管理、使用统计等功能
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.api_key import (
    APIKeyCreate, APIKeyUpdate, APIKeyStatus, APIKeyTier, APIKeyType
)
from services.api_key_service import api_key_service
from middleware.api_auth import verify_api_key, APIAuthMiddleware
from models.member import CommunityMember

router = APIRouter(prefix="/api/api-keys", tags=["API Keys"])


# ==================== API Key CRUD ====================

@router.post("")
async def create_api_key(
    request: APIKeyCreate,
    current_user: CommunityMember = Depends(verify_api_key)
):
    """
    创建新的 API Key

    需要认证权限
    """
    try:
        api_key = await api_key_service.create_api_key(
            request=request,
            owner_id=current_user.id,
            owner_type="member"
        )
        return {
            "success": True,
            "api_key": api_key.to_dict(hide_key=False)  # 创建时显示完整密钥
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_api_keys(
    status: Optional[APIKeyStatus] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """
    获取 API Key 列表

    返回当前用户的所有 API Key
    """
    api_keys = await api_key_service.list_api_keys(
        owner_id=current_user.id,
        status=status,
        limit=limit
    )
    return {
        "total": len(api_keys),
        "api_keys": [key.to_dict(hide_key=True) for key in api_keys]
    }


@router.get("/{api_key_id}")
async def get_api_key(
    api_key_id: str,
    current_user: CommunityMember = Depends(verify_api_key)
):
    """
    获取 API Key 详情
    """
    api_key = await api_key_service.get_api_key(api_key_id)

    if not api_key:
        raise HTTPException(status_code=404, detail="API Key not found")

    # 检查权限：只能查看自己的 API Key
    if api_key.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return api_key.to_dict(hide_key=True)


@router.put("/{api_key_id}")
async def update_api_key(
    api_key_id: str,
    request: APIKeyUpdate,
    current_user: CommunityMember = Depends(verify_api_key)
):
    """
    更新 API Key 配置
    """
    # 先获取 API Key 检查权限
    existing_key = await api_key_service.get_api_key(api_key_id)
    if not existing_key:
        raise HTTPException(status_code=404, detail="API Key not found")

    if existing_key.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    updated_key = await api_key_service.update_api_key(api_key_id, request)

    return {
        "success": True,
        "api_key": updated_key.to_dict(hide_key=True)
    }


@router.delete("/{api_key_id}")
async def revoke_api_key(
    api_key_id: str,
    current_user: CommunityMember = Depends(verify_api_key)
):
    """
    撤销 API Key

    撤销后的 API Key 将无法再使用
    """
    # 先获取 API Key 检查权限
    existing_key = await api_key_service.get_api_key(api_key_id)
    if not existing_key:
        raise HTTPException(status_code=404, detail="API Key not found")

    if existing_key.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    success = await api_key_service.revoke_api_key(api_key_id)

    return {
        "success": success,
        "revoked_api_key_id": api_key_id
    }


# ==================== 使用统计 ====================

@router.get("/{api_key_id}/usage")
async def get_api_key_usage(
    api_key_id: str,
    days: int = Query(default=7, ge=1, le=90),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """
    获取 API Key 使用统计
    """
    # 检查权限
    existing_key = await api_key_service.get_api_key(api_key_id)
    if not existing_key:
        raise HTTPException(status_code=404, detail="API Key not found")

    if existing_key.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    stats = await api_key_service.get_usage_stats(api_key_id, days)

    return {
        "api_key_id": api_key_id,
        "period_days": days,
        "stats": stats
    }


@router.get("/{api_key_id}/logs")
async def get_api_key_logs(
    api_key_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """
    获取 API Key 请求日志
    """
    from db.manager import db_manager
    from repositories.api_key_repository import APIRequestLogRepository

    # 检查权限
    existing_key = await api_key_service.get_api_key(api_key_id)
    if not existing_key:
        raise HTTPException(status_code=404, detail="API Key not found")

    if existing_key.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    async for db in db_manager.get_session():
        repo = APIRequestLogRepository(db)
        logs = await repo.get_logs_by_key(api_key_id, limit, offset)

        return {
            "api_key_id": api_key_id,
            "total": limit,  # 实际总数需要单独查询
            "offset": offset,
            "logs": [
                {
                    "id": log.id,
                    "request_id": log.request_id,
                    "method": log.method,
                    "path": log.path,
                    "endpoint": log.endpoint,
                    "status_code": log.status_code,
                    "response_time_ms": log.response_time_ms,
                    "ip_address": log.ip_address,
                    "is_rate_limited": log.is_rate_limited,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ]
        }


# ==================== 管理员功能 ====================

@router.get("/admin/all")
async def list_all_api_keys(
    status: Optional[APIKeyStatus] = Query(default=None),
    tier: Optional[APIKeyTier] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """
    获取所有 API Key（管理员专用）

    需要 admin 权限
    """
    # 检查管理员权限
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    api_keys = await api_key_service.list_api_keys(
        status=status,
        limit=limit
    )

    # 按等级过滤
    if tier:
        api_keys = [key for key in api_keys if key.tier == tier]

    return {
        "total": len(api_keys),
        "api_keys": [key.to_dict(hide_key=False) for key in api_keys]
    }


@router.post("/admin/{api_key_id}/revoke")
async def admin_revoke_api_key(
    api_key_id: str,
    reason: str = Body(..., embed=True),
    current_user: CommunityMember = Depends(verify_api_key)
):
    """
    管理员撤销 API Key

    需要 admin 权限
    """
    # 检查管理员权限
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    api_key = await api_key_service.get_api_key(api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key not found")

    success = await api_key_service.revoke_api_key(api_key_id)

    # 记录撤销原因（可以添加到审计日志）
    logger_info = {
        "api_key_id": api_key_id,
        "owner_id": api_key.owner_id,
        "reason": reason,
        "operator_id": current_user.id,
    }

    return {
        "success": success,
        "revoked_api_key_id": api_key_id,
        "info": logger_info
    }


# ==================== 等级和配额 ====================

@router.get("/tiers")
async def get_api_tiers():
    """
    获取 API Key 等级和配额信息
    """
    from services.api_key_service import TIER_LIMITS

    tiers = {}
    for tier, limits in TIER_LIMITS.items():
        tiers[tier.value] = {
            "rate_limit": limits["rate_limit"],
            "daily_limit": limits["daily_limit"],
            "scopes": limits["scopes"],
            "description": _get_tier_description(tier),
        }

    return {"tiers": tiers}


def _get_tier_description(tier: APIKeyTier) -> str:
    """获取等级描述"""
    descriptions = {
        APIKeyTier.FREE: "免费版 - 适合个人开发者和小型项目",
        APIKeyTier.BASIC: "基础版 - 适合中小规模应用",
        APIKeyTier.PRO: "专业版 - 适合商业应用和高流量场景",
        APIKeyTier.ENTERPRISE: "企业版 -  unlimited 配额和专属支持",
    }
    return descriptions.get(tier, "")
