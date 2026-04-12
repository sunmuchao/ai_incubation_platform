"""
LLM 语义缓存 API

Values 功能接口：
- 查看缓存统计
- 手动清除缓存
- 测试缓存命中
"""
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from typing import Dict, List, Optional
from pydantic import BaseModel
from utils.logger import logger
from auth.jwt import get_current_user
from cache.semantic_cache import semantic_cache

router = APIRouter(prefix="/api/llm/cache", tags=["llm-cache"])


# ============= 请求/响应模型 =============

class CacheStatsResponse(BaseModel):
    """缓存统计响应"""
    success: bool
    data: Dict
    message: Optional[str] = None


class CacheTestRequest(BaseModel):
    """缓存测试请求"""
    query: str
    context: Optional[Dict] = None


class CacheTestResponse(BaseModel):
    """缓存测试响应"""
    success: bool
    data: Dict
    message: str


class CacheClearRequest(BaseModel):
    """缓存清除请求"""
    pattern: Optional[str] = None


class CacheClearResponse(BaseModel):
    """缓存清除响应"""
    success: bool
    cleared_count: int
    message: str


# ============= API 端点 =============

@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(current_user: dict = Depends(get_current_user)):
    """
    获取语义缓存统计

    返回缓存的使用情况、命中率等指标
    """
    try:
        stats = semantic_cache.get_stats()
        return CacheStatsResponse(
            success=True,
            data=stats,
            message=f"当前缓存条目：{stats['total_entries']}/{stats['max_size']}"
        )
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=CacheTestResponse)
async def test_cache(
    request: CacheTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    测试缓存命中

    用于调试和验证缓存效果
    """
    try:
        import asyncio

        # 尝试命中缓存
        cached = asyncio.get_event_loop().run_until_complete(
            semantic_cache.get(request.query, request.context)
        )

        if cached is not None:
            return CacheTestResponse(
                success=True,
                data=cached,
                message="缓存命中"
            )
        else:
            return CacheTestResponse(
                success=True,
                data={},
                message="缓存未命中"
            )
    except Exception as e:
        logger.error(f"Failed to test cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear", response_model=CacheClearResponse)
async def clear_cache(
    request: CacheClearRequest = None,
    current_user: dict = Depends(get_current_user)
):
    """
    清除语义缓存

    可选 pattern 参数用于模糊匹配清除特定缓存
    """
    try:
        # 简化实现：清除所有缓存
        # 生产环境应实现 pattern 匹配
        semantic_cache.clear()
        return CacheClearResponse(
            success=True,
            cleared_count=0,  # 简化实现，不统计具体数量
            message="缓存已清空"
        )
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_cache_config(current_user: dict = Depends(get_current_user)):
    """
    获取缓存配置
    """
    return {
        "success": True,
        "data": {
            "max_size": semantic_cache.max_size,
            "similarity_threshold": semantic_cache.similarity_threshold,
            "default_ttl": semantic_cache.default_ttl
        }
    }


@router.post("/config")
async def update_cache_config(
    similarity_threshold: float = Body(default=0.95, ge=0, le=1),
    ttl: int = Body(default=3600, ge=60),
    current_user: dict = Depends(get_current_user)
):
    """
    更新缓存配置

    Args:
        similarity_threshold: 相似度阈值 (0-1)
        ttl: 默认过期时间 (秒)
    """
    try:
        semantic_cache.similarity_threshold = similarity_threshold
        semantic_cache.default_ttl = ttl

        logger.info(
            f"Cache config updated: threshold={similarity_threshold}, ttl={ttl}"
        )

        return {
            "success": True,
            "data": {
                "similarity_threshold": similarity_threshold,
                "default_ttl": ttl
            },
            "message": "缓存配置已更新"
        }
    except Exception as e:
        logger.error(f"Failed to update cache config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
