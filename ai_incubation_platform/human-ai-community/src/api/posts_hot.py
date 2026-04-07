"""
内容热度算法 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.heat_service import HeatService, get_heat_service
from db.manager import db_manager
from models.member import MemberType

router = APIRouter(prefix="/api/posts", tags=["posts"])


class HotPostResponse(BaseModel):
    """热门帖子响应"""
    post_id: str
    author_id: str
    author_type: str
    title: str
    content: str
    tags: list
    created_at: str
    heat_score: float
    like_count: int
    comment_count: int


class QualityContentResponse(BaseModel):
    """优质内容响应"""
    post_id: str
    heat_score: float
    quality_score: float
    is_quality: bool
    is_hot: bool
    like_count: int
    bookmark_count: int
    comment_count: int


@router.get("")
async def list_posts(
    sort: str = Query(default="hot", description="排序方式：hot(热门)/new(最新)/top(最多互动)"),
    time_range: str = Query(default="24h", description="时间范围：24h/7d/30d/all"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量"),
    author_type: Optional[str] = Query(None, description="作者类型：human/ai")
):
    """
    获取帖子列表

    支持按热度、时间、互动数排序，可按时间范围和作者类型筛选。
    """
    async with db_manager.get_session() as db:
        heat_service = get_heat_service(db)

        # 解析作者类型
        parsed_author_type = None
        if author_type:
            try:
                parsed_author_type = MemberType(author_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的 author_type")

        if sort == "hot":
            # 按热度排序
            results = await heat_service.get_hot_posts(
                time_range=time_range,
                limit=limit,
                author_type=parsed_author_type
            )
            posts_data = [
                {
                    "post_id": item["post"].id,
                    "author_id": item["post"].author_id,
                    "author_type": item["post"].author_type.value,
                    "title": item["post"].title,
                    "content": item["post"].content,
                    "tags": item["post"].tags,
                    "created_at": item["post"].created_at.isoformat(),
                    "heat_score": round(item["heat_score"], 2),
                }
                for item in results
            ]
        elif sort == "new":
            # 按时间排序（使用 community_service）
            from services.community_service import community_service
            posts = community_service.list_posts(limit=limit, author_type=parsed_author_type)
            posts_data = [
                {
                    "post_id": p.id,
                    "author_id": p.author_id,
                    "author_type": p.author_type.value,
                    "title": p.title,
                    "content": p.content,
                    "tags": p.tags,
                    "created_at": p.created_at.isoformat(),
                }
                for p in posts
            ]
        else:
            # 默认按热度排序
            results = await heat_service.get_hot_posts(
                time_range=time_range,
                limit=limit,
                author_type=parsed_author_type
            )
            posts_data = [
                {
                    "post_id": item["post"].id,
                    "author_id": item["post"].author_id,
                    "author_type": item["post"].author_type.value,
                    "title": item["post"].title,
                    "content": item["post"].content,
                    "tags": item["post"].tags,
                    "created_at": item["post"].created_at.isoformat(),
                    "heat_score": round(item["heat_score"], 2),
                }
                for item in results
            ]

        return {
            "total": len(posts_data),
            "sort": sort,
            "time_range": time_range,
            "posts": posts_data
        }


@router.get("/trending")
async def get_trending_posts(
    limit: int = Query(default=20, ge=1, le=50, description="返回数量")
):
    """
    获取实时上升帖子

    基于最近 2 小时内的互动增长率，发现正在快速传播的内容。
    """
    async with db_manager.get_session() as db:
        heat_service = get_heat_service(db)
        try:
            results = await heat_service.get_trending_posts(limit=limit)
            return {
                "total": len(results),
                "trending_posts": [
                    {
                        "post_id": item["post"].id,
                        "title": item["post"].title,
                        "trend_score": round(item["trend_score"], 2),
                    }
                    for item in results
                ]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/{post_id}/quality")
async def get_post_quality_analysis(post_id: str):
    """
    获取帖子质量分析

    分析内容是否为优质内容，并提供详细的质量评分。
    """
    async with db_manager.get_session() as db:
        heat_service = get_heat_service(db)
        try:
            analysis = await heat_service.identify_quality_content(post_id)
            if not analysis:
                raise HTTPException(status_code=404, detail="帖子不存在")
            return analysis
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot")
async def get_hot_posts(
    time_range: str = Query(default="24h", description="时间范围：24h/7d/30d/all"),
    limit: int = Query(default=20, ge=1, le=50, description="返回数量")
):
    """
    获取热门帖子

    按热度分数排序，支持时间范围筛选。
    """
    async with db_manager.get_session() as db:
        heat_service = get_heat_service(db)
        try:
            results = await heat_service.get_hot_posts(time_range=time_range, limit=limit)
            return {
                "total": len(results),
                "time_range": time_range,
                "hot_posts": [
                    {
                        "post_id": item["post"].id,
                        "title": item["post"].title,
                        "heat_score": round(item["heat_score"], 2),
                        "created_at": item["post"].created_at.isoformat(),
                    }
                    for item in results
                ]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
