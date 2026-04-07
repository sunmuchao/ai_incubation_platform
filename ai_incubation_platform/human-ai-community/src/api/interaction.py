"""
互动 API 路由 - 点赞、收藏、关注等功能
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.member import ContentType, MemberType
from services.interaction_service import interaction_service
from db.manager import db_manager
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api", tags=["interaction"])


# ==================== 请求/响应模型 ====================
class ToggleLikeRequest(BaseModel):
    """切换点赞请求"""
    user_id: str
    content_id: str
    content_type: str  # "post" or "comment"


class ToggleBookmarkRequest(BaseModel):
    """切换收藏请求"""
    user_id: str
    content_id: str
    content_type: str  # "post" or "comment"
    folder: Optional[str] = "default"
    note: Optional[str] = None


class ToggleFollowRequest(BaseModel):
    """切换关注请求"""
    follower_id: str
    following_id: str


class LikeStatusResponse(BaseModel):
    """点赞状态响应"""
    is_liked: bool
    like_count: int


class FollowStatsResponse(BaseModel):
    """关注统计响应"""
    following_count: int
    followers_count: int


# ==================== 点赞功能 ====================
@router.post("/likes/toggle")
async def toggle_like(request: ToggleLikeRequest):
    """切换点赞状态（点赞/取消点赞）"""
    try:
        content_type = ContentType(request.content_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid content_type")

    async with db_manager._session_factory() as session:
        result = await interaction_service.toggle_like(
            session,
            request.user_id,
            request.content_id,
            content_type
        )
        return result


@router.get("/likes/status")
async def get_like_status(
    user_id: str = Query(...),
    content_id: str = Query(...),
    content_type: str = Query(...)
):
    """获取点赞状态"""
    try:
        content_type = ContentType(content_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid content_type")

    async with db_manager._session_factory() as session:
        result = await interaction_service.get_like_status(
            session,
            user_id,
            content_id,
            content_type
        )
        return result


@router.get("/likes")
async def get_user_likes(
    user_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=100)
):
    """获取用户的点赞列表"""
    async with db_manager._session_factory() as session:
        likes = await interaction_service.get_user_likes(session, user_id, limit)
        return [
            {
                "id": like.id,
                "content_id": like.content_id,
                "content_type": like.content_type.value,
                "created_at": like.created_at.isoformat()
            }
            for like in likes
        ]


# ==================== 收藏功能 ====================
@router.post("/bookmarks/toggle")
async def toggle_bookmark(request: ToggleBookmarkRequest):
    """切换收藏状态（收藏/取消收藏）"""
    try:
        content_type = ContentType(request.content_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid content_type")

    async with db_manager._session_factory() as session:
        result = await interaction_service.toggle_bookmark(
            session,
            request.user_id,
            request.content_id,
            content_type,
            request.folder,
            request.note
        )
        return result


@router.get("/bookmarks/status")
async def get_bookmark_status(
    user_id: str = Query(...),
    content_id: str = Query(...),
    content_type: str = Query(...)
):
    """获取收藏状态"""
    try:
        content_type = ContentType(content_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid content_type")

    async with db_manager._session_factory() as session:
        is_bookmarked = await interaction_service.get_bookmark_status(
            session,
            user_id,
            content_id,
            content_type
        )
        return {"is_bookmarked": is_bookmarked}


@router.get("/bookmarks")
async def get_user_bookmarks(
    user_id: str = Query(...),
    folder: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=100)
):
    """获取用户的收藏列表"""
    async with db_manager._session_factory() as session:
        bookmarks = await interaction_service.get_user_bookmarks(
            session,
            user_id,
            folder,
            limit
        )
        return [
            {
                "id": bookmark.id,
                "content_id": bookmark.content_id,
                "content_type": bookmark.content_type.value,
                "folder": bookmark.folder,
                "note": bookmark.note,
                "created_at": bookmark.created_at.isoformat()
            }
            for bookmark in bookmarks
        ]


@router.get("/bookmarks/folders")
async def get_user_folders(user_id: str = Query(...)):
    """获取用户的所有收藏夹名称"""
    async with db_manager._session_factory() as session:
        folders = await interaction_service.get_user_folders(session, user_id)
        return {"folders": folders}


# ==================== 关注功能 ====================
@router.post("/follows/toggle")
async def toggle_follow(request: ToggleFollowRequest):
    """切换关注状态（关注/取消关注）"""
    async with db_manager._session_factory() as session:
        result = await interaction_service.toggle_follow(
            session,
            request.follower_id,
            request.following_id
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result


@router.get("/follows/status")
async def get_follow_status(
    follower_id: str = Query(...),
    following_id: str = Query(...)
):
    """获取关注状态"""
    async with db_manager._session_factory() as session:
        is_following = await interaction_service.get_follow_status(
            session,
            follower_id,
            following_id
        )
        return {"is_following": is_following}


@router.get("/follows/following")
async def get_following_list(
    user_id: str = Query(...),
    limit: int = Query(default=100, ge=1, le=200)
):
    """获取用户关注的列表"""
    async with db_manager._session_factory() as session:
        follows = await interaction_service.get_following_list(session, user_id, limit)
        return [
            {
                "id": follow.id,
                "following_id": follow.following_id,
                "created_at": follow.created_at.isoformat()
            }
            for follow in follows
        ]


@router.get("/follows/followers")
async def get_followers_list(
    user_id: str = Query(...),
    limit: int = Query(default=100, ge=1, le=200)
):
    """获取用户的粉丝列表"""
    async with db_manager._session_factory() as session:
        follows = await interaction_service.get_followers_list(session, user_id, limit)
        return [
            {
                "id": follow.id,
                "follower_id": follow.follower_id,
                "created_at": follow.created_at.isoformat()
            }
            for follow in follows
        ]


@router.get("/follows/stats")
async def get_follow_stats(user_id: str = Query(...)):
    """获取用户的关注统计"""
    async with db_manager._session_factory() as session:
        stats = await interaction_service.get_follow_stats(session, user_id)
        return stats
