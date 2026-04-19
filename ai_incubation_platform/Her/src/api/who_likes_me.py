"""
Who Likes Me API

参考 Tinder Gold 功能：
- 显示喜欢你的人列表
- 会员可查看完整信息并直接匹配
- 非会员只能看模糊预览
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from db.database import get_db
from services.who_likes_me_service import WhoLikesMeService, get_who_likes_me_service
from services.membership_service import MembershipService
from models.membership import MembershipTier
from utils.logger import logger

router = APIRouter(prefix="/api/who-likes-me", tags=["Who Likes Me"])


class LikeUserResponse(BaseModel):
    """喜欢我的用户响应"""
    user_id: str
    name: str
    avatar: Optional[str] = None
    avatar_blurred: Optional[str] = None  # 模糊头像 URL
    liked_at: str
    compatibility_score: Optional[float] = None  # 会员可见
    is_blurred: bool
    blur_level: Optional[str] = None


class WhoLikesMeResponse(BaseModel):
    """Who Likes Me 响应"""
    total_count: int
    has_more: bool
    is_member: bool
    likes: List[LikeUserResponse]
    free_preview_count: int


class LikeBackRequest(BaseModel):
    """回喜欢请求"""
    target_user_id: str


class LikeBackResponse(BaseModel):
    """回喜欢响应"""
    success: bool
    message: str
    matched: bool
    match_id: Optional[str] = None


@router.get("/{user_id}", response_model=WhoLikesMeResponse)
async def get_who_likes_me(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("time", regex="^(time|compatibility)$"),
    db: Session = Depends(get_db)
):
    """
    获取喜欢我的用户列表

    会员可查看完整信息，非会员只能看模糊预览
    """
    try:
        # 检查会员状态
        membership_service = MembershipService(db)
        membership = membership_service.get_user_membership(user_id)
        is_member = membership.is_active() and membership.tier != MembershipTier.FREE

        # 获取喜欢列表
        service = get_who_likes_me_service(db)
        result = service.get_likes_received(
            user_id=user_id,
            is_member=is_member,
            limit=limit,
            offset=offset,
            sort_by=sort_by
        )

        logger.info(f"User {user_id} (member: {is_member}) viewed {len(result['likes'])} likes")
        return result
    except Exception as e:
        logger.error(f"Failed to get who likes me for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count/{user_id}")
async def get_likes_count(user_id: str, db: Session = Depends(get_db)):
    """
    获取喜欢我的用户数量

    用于显示徽章数量
    """
    try:
        service = get_who_likes_me_service(db)
        count = service.get_likes_count(user_id)
        return {"count": count}
    except Exception as e:
        logger.error(f"Failed to get likes count for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/like-back", response_model=LikeBackResponse)
async def like_back(
    user_id: str,
    request: LikeBackRequest,
    db: Session = Depends(get_db)
):
    """
    回喜欢（喜欢喜欢我的人）

    会员功能：直接匹配
    """
    try:
        # 检查会员状态
        membership_service = MembershipService(db)
        membership = membership_service.get_user_membership(user_id)
        is_member = membership.is_active() and membership.tier != MembershipTier.FREE

        if not is_member:
            return {
                "success": False,
                "message": "此功能需要会员订阅",
                "matched": False
            }

        service = get_who_likes_me_service(db)
        result = service.like_back(user_id, request.target_user_id)

        return result
    except Exception as e:
        logger.error(f"Failed to like back: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/new-count/{user_id}")
async def get_new_likes_count(
    user_id: str,
    since: str = Query(..., description="ISO格式时间字符串"),
    db: Session = Depends(get_db)
):
    """
    获取指定时间以来的新喜欢数量

    用于推送通知
    """
    try:
        from datetime import datetime

        since_time = datetime.fromisoformat(since)
        service = get_who_likes_me_service(db)
        count = service.get_new_likes_count_since(user_id, since_time)

        return {"new_count": count}
    except Exception as e:
        logger.error(f"Failed to get new likes count: {e}")
        raise HTTPException(status_code=500, detail=str(e))