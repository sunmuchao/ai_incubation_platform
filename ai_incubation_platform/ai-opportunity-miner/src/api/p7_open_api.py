"""
P7 - 开放 API 平台

功能：
1. API Key 管理（创建、删除、列表）
2. API 访问鉴权
3. 使用统计
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from config.database import get_db
from services.p7_api_key_service import get_api_key_service, APIKeyService


router = APIRouter(prefix="/api/p7/open-api", tags=["P7-开放 API 平台"])


# ==================== 依赖注入 ====================

def get_current_user_id(x_user_id: str = Header(..., description="用户 ID")) -> str:
    """获取当前用户 ID（从请求头）"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未授权")
    return x_user_id


# ==================== API Key 管理 ====================

@router.post("/api-keys", summary="创建 API Key")
def create_api_key(
    name: str = Body(..., description="API Key 名称"),
    description: str = Body(None, description="描述"),
    scopes: List[str] = Body(None, description="权限范围列表"),
    rate_limit_per_minute: int = Body(None, description="每分钟速率限制"),
    rate_limit_per_day: int = Body(None, description="每天速率限制"),
    expires_in_days: int = Body(None, description="过期天数"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    创建 API Key

    **权限范围**:
    - read:opportunities - 读取商机
    - write:opportunities - 写入商机
    - read:trends - 读取趋势
    - read:companies - 读取企业数据
    - read:investment - 读取投资数据
    - read:equity - 读取股权数据
    - ml:predict - ML 预测
    - export:report - 导出报告

    **注意**: 只有专业版和企业版用户可以创建 API Key
    """
    service = get_api_key_service(db)
    try:
        api_key = service.create_api_key(
            user_id=user_id,
            name=name,
            description=description,
            scopes=scopes,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_day=rate_limit_per_day,
            expires_in_days=expires_in_days,
        )
        result = api_key.to_dict()
        # 如果是新创建的，返回完整 key（只显示一次）
        if hasattr(api_key, '_raw_key'):
            result["key"] = api_key._raw_key
            result["warning"] = "完整密钥只显示一次，请妥善保存"

        return {
            "success": True,
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api-keys", summary="获取我的 API Key 列表")
def list_api_keys(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取当前用户的所有 API Key"""
    service = get_api_key_service(db)
    api_keys = service.list_api_keys(user_id)
    return {
        "success": True,
        "data": [key.to_dict() for key in api_keys],
        "total": len(api_keys),
    }


@router.get("/api-keys/{api_key_id}", summary="获取 API Key 详情")
def get_api_key(
    api_key_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取指定 API Key 的详情"""
    service = get_api_key_service(db)
    api_key = service.get_api_key(api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key 不存在")

    if api_key.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此 API Key")

    return {
        "success": True,
        "data": api_key.to_dict(),
    }


@router.put("/api-keys/{api_key_id}", summary="更新 API Key")
def update_api_key(
    api_key_id: str,
    name: str = Body(None, description="API Key 名称"),
    description: str = Body(None, description="描述"),
    scopes: List[str] = Body(None, description="权限范围列表"),
    rate_limit_per_minute: int = Body(None, description="每分钟速率限制"),
    rate_limit_per_day: int = Body(None, description="每天速率限制"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """更新 API Key 配置"""
    service = get_api_key_service(db)
    try:
        api_key = service.update_api_key(
            api_key_id=api_key_id,
            user_id=user_id,
            name=name,
            description=description,
            scopes=scopes,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_day=rate_limit_per_day,
        )
        return {
            "success": True,
            "data": api_key.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api-keys/{api_key_id}", summary="撤销 API Key")
def revoke_api_key(
    api_key_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """撤销/删除 API Key"""
    service = get_api_key_service(db)
    try:
        service.revoke_api_key(api_key_id=api_key_id, user_id=user_id)
        return {
            "success": True,
            "message": "API Key 已撤销",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 使用统计 ====================

@router.get("/api-keys/{api_key_id}/usage", summary="获取 API 使用统计")
def get_api_key_usage(
    api_key_id: str,
    start_date: str = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期 (YYYY-MM-DD)"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """获取指定 API Key 的使用统计"""
    service = get_api_key_service(db)
    api_key = service.get_api_key(api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key 不存在")

    if api_key.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此 API Key")

    stats = service.get_usage_stats(
        api_key_id=api_key_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "success": True,
        "data": stats,
    }


# ==================== API 文档 ====================

@router.get("/docs", summary="获取 API 文档")
def get_api_docs():
    """获取开放 API 的文档"""
    return {
        "success": True,
        "data": {
            "title": "AI Opportunity Miner - Open API",
            "version": "1.0.0",
            "base_url": "/api",
            "authentication": {
                "type": "API Key",
                "header": "X-API-Key",
                "example": "X-API-Key: your_api_key_here",
            },
            "endpoints": [
                {
                    "path": "/api/opportunities",
                    "method": "GET",
                    "scope": "read:opportunities",
                    "description": "获取商机列表",
                },
                {
                    "path": "/api/opportunities/{id}",
                    "method": "GET",
                    "scope": "read:opportunities",
                    "description": "获取商机详情",
                },
                {
                    "path": "/api/trends",
                    "method": "GET",
                    "scope": "read:trends",
                    "description": "获取趋势列表",
                },
                {
                    "path": "/api/intelligence/events",
                    "method": "GET",
                    "scope": "read:opportunities",
                    "description": "获取商业情报事件",
                },
                {
                    "path": "/api/investment/list",
                    "method": "GET",
                    "scope": "read:investment",
                    "description": "获取投资关系列表",
                },
                {
                    "path": "/api/equity/ownership/{company_id}",
                    "method": "GET",
                    "scope": "read:equity",
                    "description": "获取股权穿透图",
                },
                {
                    "path": "/api/ml/forecast/industry/{industry}",
                    "method": "GET",
                    "scope": "ml:predict",
                    "description": "行业趋势预测",
                },
            ],
            "rate_limits": {
                "professional": {
                    "per_minute": 60,
                    "per_day": 1000,
                },
                "enterprise": {
                    "per_minute": 300,
                    "per_day": 10000,
                },
            },
            "error_codes": {
                "400": "请求参数错误",
                "401": "未授权（API Key 无效或缺失）",
                "403": "权限不足",
                "404": "资源不存在",
                "429": "请求频率超限",
                "500": "服务器内部错误",
            },
        },
    }
