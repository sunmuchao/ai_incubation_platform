"""
社交网络 API 路由 - v1.19 社交网络增强

提供好友动态、社区圈子、内容分享、社交图谱、隐私设置等 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from services.social_service import (
    get_social_post_service,
    get_social_relationship_service,
    get_social_circle_service,
    get_privacy_settings_service,
    get_social_notification_service
)

router = APIRouter(prefix="/api/social", tags=["social-network"])


# ==================== 依赖注入 ====================

async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user_id(x_user_id: str = Header(..., description="用户 ID")) -> str:
    """获取当前用户 ID（从请求头）"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未授权")
    return x_user_id


# ==================== 社交帖子 API ====================

@router.post("/posts")
async def create_post(
    content: str = Body(..., description="帖子内容"),
    content_type: str = Body("text", description="内容类型：text, image, video, link, mixed"),
    media_urls: List[str] = Body(default_factory=list, description="媒体 URL 列表"),
    visibility: str = Body("public", description="可见性：public, friends, circle, private, employers, workers"),
    tags: List[str] = Body(default_factory=list, description="标签列表"),
    circle_id: Optional[str] = Body(None, description="圈子 ID（当 visibility=circle 时）"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    创建社交帖子

    - **content**: 帖子内容
    - **content_type**: 内容类型（text/image/video/link/mixed）
    - **media_urls**: 图片/视频 URL 列表
    - **visibility**: 可见性（public/friends/circle/private/employers/workers）
    - **tags**: 标签列表
    - **circle_id**: 圈子 ID（当可见性为 circle 时必填）
    """
    service = get_social_post_service(db)

    # 获取用户信息（实际项目中应从用户服务获取）
    user_info = {"name": f"User_{user_id[:8]}", "type": "user", "avatar": None}

    try:
        post = await service.create_post(
            author_id=user_id,
            author_type=user_info["type"],
            author_name=user_info["name"],
            content=content,
            content_type=content_type,
            media_urls=media_urls,
            visibility=visibility,
            tags=tags,
            circle_id=circle_id
        )

        return {
            "success": True,
            "post": {
                "post_id": post.post_id,
                "author_id": post.author_id,
                "author_name": post.author_name,
                "content": post.content,
                "content_type": post.content_type,
                "visibility": post.visibility,
                "tags": post.tags,
                "circle_id": post.circle_id,
                "like_count": post.like_count,
                "comment_count": post.comment_count,
                "share_count": post.share_count,
                "created_at": post.created_at.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/posts/{post_id}")
async def get_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取帖子详情

    - **post_id**: 帖子 ID
    """
    service = get_social_post_service(db)

    post = await service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 检查可见性
    if post.visibility == "private" and post.author_id != user_id:
        raise HTTPException(status_code=403, detail="无权查看此帖子")

    return {
        "success": True,
        "post": {
            "post_id": post.post_id,
            "author_id": post.author_id,
            "author_name": post.author_name,
            "author_avatar": post.author_avatar,
            "content": post.content,
            "content_type": post.content_type,
            "media_urls": post.media_urls,
            "visibility": post.visibility,
            "tags": post.tags,
            "like_count": post.like_count,
            "comment_count": post.comment_count,
            "share_count": post.share_count,
            "view_count": post.view_count,
            "is_pinned": post.is_pinned,
            "created_at": post.created_at.isoformat()
        }
    }


@router.get("/feed")
async def get_feed(
    feed_type: str = Query("home", description="Feed 类型：home, circle, profile"),
    circle_id: Optional[str] = Query(None, description="圈子 ID（当 feed_type=circle 时）"),
    profile_user_id: Optional[str] = Query(None, description="用户 ID（当 feed_type=profile 时）"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取 Feed（首页动态）

    - **feed_type**: Feed 类型（home/circle/profile）
    - **circle_id**: 圈子 ID（当 feed_type=circle 时）
    - **profile_user_id**: 用户 ID（当 feed_type=profile 时）
    - **skip**: 跳过数量
    - **limit**: 返回数量
    """
    service = get_social_post_service(db)

    if feed_type == "home":
        posts, total = await service.get_user_feed(user_id, skip=skip, limit=limit)
    elif feed_type == "circle":
        if not circle_id:
            raise HTTPException(status_code=400, detail="circle_id 必填")
        posts, total = await service.get_circle_feed(circle_id, user_id, skip=skip, limit=limit)
    elif feed_type == "profile":
        if not profile_user_id:
            raise HTTPException(status_code=400, detail="profile_user_id 必填")
        posts, total = await service.get_user_posts(profile_user_id, viewer_id=user_id, skip=skip, limit=limit)
    else:
        raise HTTPException(status_code=400, detail="无效的 feed_type")

    return {
        "success": True,
        "posts": [
            {
                "post_id": p.post_id,
                "author_id": p.author_id,
                "author_name": p.author_name,
                "author_avatar": p.author_avatar,
                "content": p.content,
                "content_type": p.content_type,
                "media_urls": p.media_urls,
                "visibility": p.visibility,
                "tags": p.tags,
                "like_count": p.like_count,
                "comment_count": p.comment_count,
                "share_count": p.share_count,
                "created_at": p.created_at.isoformat()
            }
            for p in posts
        ],
        "total": total,
        "has_more": total > skip + limit
    }


@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """点赞帖子"""
    service = get_social_post_service(db)

    success = await service.like_post(post_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="点赞失败（可能已点赞）")

    return {"success": True, "message": "点赞成功"}


@router.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """取消点赞"""
    service = get_social_post_service(db)

    success = await service.unlike_post(post_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="取消点赞失败（可能未点赞）")

    return {"success": True, "message": "取消点赞成功"}


@router.post("/posts/{post_id}/comments")
async def add_comment(
    post_id: str,
    content: str = Body(..., description="评论内容"),
    parent_comment_id: Optional[str] = Body(None, description="回复的评论 ID"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """添加评论"""
    service = get_social_post_service(db)

    user_info = {"name": f"User_{user_id[:8]}", "type": "user"}

    comment = await service.add_comment(
        post_id=post_id,
        author_id=user_id,
        author_type=user_info["type"],
        author_name=user_info["name"],
        content=content,
        parent_comment_id=parent_comment_id
    )

    return {
        "success": True,
        "comment": {
            "comment_id": comment.comment_id,
            "post_id": comment.post_id,
            "author_id": comment.author_id,
            "author_name": comment.author_name,
            "content": comment.content,
            "like_count": comment.like_count,
            "created_at": comment.created_at.isoformat()
        }
    }


@router.get("/posts/{post_id}/comments")
async def get_comments(
    post_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取帖子评论"""
    service = get_social_post_service(db)

    comments = await service.get_post_comments(post_id, skip=skip, limit=limit)

    return {
        "success": True,
        "comments": [
            {
                "comment_id": c.comment_id,
                "author_id": c.author_id,
                "author_name": c.author_name,
                "content": c.content,
                "like_count": c.like_count,
                "reply_count": c.reply_count,
                "created_at": c.created_at.isoformat()
            }
            for c in comments
        ],
        "total": len(comments)
    }


@router.post("/posts/{post_id}/bookmark")
async def bookmark_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """收藏帖子"""
    service = get_social_post_service(db)

    success = await service.bookmark_post(post_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="收藏失败（可能已收藏）")

    return {"success": True, "message": "收藏成功"}


@router.post("/posts/{post_id}/share")
async def share_post(
    post_id: str,
    share_type: str = Body("repost", description="分享类型：repost, external"),
    share_content: Optional[str] = Body(None, description="转发时的附加内容"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """分享帖子"""
    service = get_social_post_service(db)

    share = await service.share_post(
        post_id=post_id,
        user_id=user_id,
        share_type=share_type,
        share_content=share_content
    )

    return {
        "success": True,
        "share": {
            "share_id": share.share_id,
            "post_id": share.post_id,
            "share_type": share.share_type,
            "created_at": share.created_at.isoformat()
        }
    }


# ==================== 社交关系 API ====================

@router.post("/friends/request")
async def send_friend_request(
    receiver_id: str = Body(..., description="接收方用户 ID"),
    message: Optional[str] = Body(None, description="好友申请消息"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """发送好友请求"""
    service = get_social_relationship_service(db)

    try:
        request = await service.send_friend_request(
            sender_id=user_id,
            receiver_id=receiver_id,
            message=message
        )

        return {
            "success": True,
            "request": {
                "request_id": request.request_id,
                "sender_id": request.sender_id,
                "receiver_id": request.receiver_id,
                "status": request.status,
                "created_at": request.created_at.isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/friends/request/{request_id}/respond")
async def respond_friend_request(
    request_id: str,
    accept: bool = Body(..., description="是否接受"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """响应好友请求"""
    service = get_social_relationship_service(db)

    success = await service.respond_friend_request(
        request_id=request_id,
        user_id=user_id,
        accept=accept
    )

    if not success:
        raise HTTPException(status_code=400, detail="响应失败")

    return {"success": True, "message": "接受好友请求" if accept else "拒绝好友请求"}


@router.get("/friends/requests")
async def get_friend_requests(
    status: str = Query("pending", description="请求状态：pending, accepted, rejected"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取好友请求列表"""
    service = get_social_relationship_service(db)

    requests = await service.get_friend_requests(user_id, status)

    return {
        "success": True,
        "requests": [
            {
                "request_id": r.request_id,
                "sender_id": r.sender_id,
                "message": r.message,
                "status": r.status,
                "created_at": r.created_at.isoformat()
            }
            for r in requests
        ],
        "total": len(requests)
    }


@router.get("/friends")
async def get_friends(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取好友列表"""
    service = get_social_relationship_service(db)

    friends, total = await service.get_friends(user_id, skip=skip, limit=limit)

    return {
        "success": True,
        "friends": [
            {
                "friend_id": f.target_id if f.user_id == user_id else f.user_id,
                "relationship_type": f.relationship_type,
                "is_mutual": f.is_mutual,
                "collaboration_count": f.collaboration_count
            }
            for f in friends
        ],
        "total": total,
        "has_more": total > skip + limit
    }


@router.delete("/friends/{friend_id}")
async def remove_friend(
    friend_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """删除好友"""
    service = get_social_relationship_service(db)

    success = await service.remove_friend(user_id, friend_id)
    if not success:
        raise HTTPException(status_code=400, detail="删除失败")

    return {"success": True, "message": "好友已删除"}


@router.post("/block/{target_id}")
async def block_user(
    target_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """拉黑用户"""
    relationship_service = get_social_relationship_service(db)

    relationship = await relationship_service.block_user(user_id, target_id)

    return {
        "success": True,
        "relationship": {
            "relationship_id": relationship.relationship_id,
            "target_id": relationship.target_id,
            "relationship_type": relationship.relationship_type
        }
    }


@router.get("/mutual-friends/{target_id}")
async def get_mutual_friends(
    target_id: str,
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取共同好友"""
    service = get_social_relationship_service(db)

    mutual_friend_ids = await service.get_mutual_friends(user_id, target_id, limit=limit)

    return {
        "success": True,
        "mutual_friends": [
            {"friend_id": fid}
            for fid in mutual_friend_ids
        ],
        "total": len(mutual_friend_ids)
    }


# ==================== 圈子 API ====================

@router.post("/circles")
async def create_circle(
    name: str = Body(..., description="圈子名称"),
    description: Optional[str] = Body(None, description="圈子描述"),
    circle_type: str = Body("interest", description="圈子类型：skill, industry, region, interest, task"),
    category: Optional[str] = Body(None, description="分类"),
    join_type: str = Body("open", description="加入方式：open, approval, invite_only"),
    visibility: str = Body("public", description="可见性：public, circle_members"),
    rules: List[str] = Body(default_factory=list, description="圈子规则"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """创建圈子"""
    service = get_social_circle_service(db)

    user_name = f"User_{user_id[:8]}"

    circle = await service.create_circle(
        creator_id=user_id,
        creator_name=user_name,
        name=name,
        description=description,
        circle_type=circle_type,
        category=category,
        join_type=join_type,
        visibility=visibility,
        rules=rules
    )

    return {
        "success": True,
        "circle": {
            "circle_id": circle.circle_id,
            "name": circle.name,
            "description": circle.description,
            "circle_type": circle.circle_type,
            "category": circle.category,
            "creator_id": circle.creator_id,
            "member_count": circle.member_count,
            "created_at": circle.created_at.isoformat()
        }
    }


@router.get("/circles/{circle_id}")
async def get_circle(
    circle_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取圈子详情"""
    service = get_social_circle_service(db)

    circle = await service.get_circle(circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="圈子不存在")

    return {
        "success": True,
        "circle": {
            "circle_id": circle.circle_id,
            "name": circle.name,
            "description": circle.description,
            "circle_type": circle.circle_type,
            "category": circle.category,
            "creator_id": circle.creator_id,
            "creator_name": circle.creator_name,
            "join_type": circle.join_type,
            "visibility": circle.visibility,
            "rules": circle.rules,
            "member_count": circle.member_count,
            "post_count": circle.post_count,
            "is_official": circle.is_official,
            "created_at": circle.created_at.isoformat()
        }
    }


@router.post("/circles/{circle_id}/join")
async def join_circle(
    circle_id: str,
    message: Optional[str] = Body(None, description="申请消息（当 join_type=approval 时）"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """加入圈子"""
    service = get_social_circle_service(db)

    user_name = f"User_{user_id[:8]}"

    try:
        result = await service.join_circle(
            circle_id=circle_id,
            user_id=user_id,
            user_name=user_name,
            message=message
        )

        if result:
            return {
                "success": True,
                "message": "加入圈子成功",
                "membership": {
                    "membership_id": result.membership_id,
                    "circle_id": result.circle_id,
                    "role": result.role,
                    "joined_at": result.joined_at.isoformat()
                }
            }
        else:
            return {
                "success": True,
                "message": "已提交加入申请，等待管理员审批"
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/circles/{circle_id}/leave")
async def leave_circle(
    circle_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """退出圈子"""
    service = get_social_circle_service(db)

    try:
        success = await service.leave_circle(circle_id, user_id)
        if not success:
            raise HTTPException(status_code=400, detail="退出失败")

        return {"success": True, "message": "退出圈子成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/circles")
async def get_user_circles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取用户加入的圈子"""
    service = get_social_circle_service(db)

    circles, total = await service.get_user_circles(user_id, skip=skip, limit=limit)

    return {
        "success": True,
        "circles": [
            {
                "circle_id": c.circle_id,
                "name": c.name,
                "description": c.description,
                "circle_type": c.circle_type,
                "category": c.category,
                "member_count": c.member_count,
                "post_count": c.post_count,
                "created_at": c.created_at.isoformat()
            }
            for c in circles
        ],
        "total": total,
        "has_more": total > skip + limit
    }


@router.get("/circles/{circle_id}/members")
async def get_circle_members(
    circle_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取圈子成员列表"""
    service = get_social_circle_service(db)

    members, total = await service.get_circle_members(circle_id, skip=skip, limit=limit)

    return {
        "success": True,
        "members": [
            {
                "membership_id": m.membership_id,
                "user_id": m.user_id,
                "user_name": m.user_name,
                "role": m.role,
                "joined_at": m.joined_at.isoformat()
            }
            for m in members
        ],
        "total": total,
        "has_more": total > skip + limit
    }


@router.post("/circle-requests/{request_id}/approve")
async def approve_join_request(
    request_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """批准加入圈子申请"""
    service = get_social_circle_service(db)

    try:
        success = await service.approve_join_request(request_id, user_id)
        if not success:
            raise HTTPException(status_code=400, detail="审批失败")

        return {"success": True, "message": "已批准加入申请"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/circle-requests/{request_id}/reject")
async def reject_join_request(
    request_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """拒绝加入圈子申请"""
    service = get_social_circle_service(db)

    try:
        success = await service.reject_join_request(request_id, user_id)
        if not success:
            raise HTTPException(status_code=400, detail="审批失败")

        return {"success": True, "message": "已拒绝加入申请"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==================== 隐私设置 API ====================

@router.get("/privacy/settings")
async def get_privacy_settings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取隐私设置"""
    service = get_privacy_settings_service(db)

    settings = await service.get_settings(user_id)

    if not settings:
        # 返回默认设置
        settings_data = {
            "who_can_see_posts": "friends",
            "who_can_comment": "friends",
            "who_can_message": "friends",
            "show_real_name": False,
            "show_location": False,
            "show_contact_info": False,
            "show_activity_status": True,
            "allow_friend_requests": True,
            "hide_friend_list": True,
            "appear_in_search": True,
            "show_in_recommendations": True,
            "notify_on_like": True,
            "notify_on_comment": True,
            "notify_on_follow": True,
            "notify_on_circle_invite": True,
            "blocked_users": []
        }
    else:
        settings_data = {
            "who_can_see_posts": settings.who_can_see_posts,
            "who_can_comment": settings.who_can_comment,
            "who_can_message": settings.who_can_message,
            "show_real_name": settings.show_real_name,
            "show_location": settings.show_location,
            "show_contact_info": settings.show_contact_info,
            "show_activity_status": settings.show_activity_status,
            "allow_friend_requests": settings.allow_friend_requests,
            "hide_friend_list": settings.hide_friend_list,
            "appear_in_search": settings.appear_in_search,
            "show_in_recommendations": settings.show_in_recommendations,
            "notify_on_like": settings.notify_on_like,
            "notify_on_comment": settings.notify_on_comment,
            "notify_on_follow": settings.notify_on_follow,
            "notify_on_circle_invite": settings.notify_on_circle_invite,
            "blocked_users": settings.blocked_users
        }

    return {
        "success": True,
        "settings": settings_data
    }


@router.put("/privacy/settings")
async def update_privacy_settings(
    settings: Dict[str, Any],
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """更新隐私设置"""
    service = get_privacy_settings_service(db)

    updated_settings = await service.update_settings(user_id, settings)

    return {
        "success": True,
        "settings": {
            "who_can_see_posts": updated_settings.who_can_see_posts,
            "who_can_comment": updated_settings.who_can_comment,
            "who_can_message": updated_settings.who_can_message,
            "show_real_name": updated_settings.show_real_name,
            "show_location": updated_settings.show_location,
            "show_contact_info": updated_settings.show_contact_info,
            "show_activity_status": updated_settings.show_activity_status,
            "allow_friend_requests": updated_settings.allow_friend_requests,
            "hide_friend_list": updated_settings.hide_friend_list,
            "appear_in_search": updated_settings.appear_in_search,
            "show_in_recommendations": updated_settings.show_in_recommendations,
            "notify_on_like": updated_settings.notify_on_like,
            "notify_on_comment": updated_settings.notify_on_comment,
            "notify_on_follow": updated_settings.notify_on_follow,
            "notify_on_circle_invite": updated_settings.notify_on_circle_invite,
            "blocked_users": updated_settings.blocked_users
        }
    }


@router.post("/privacy/block/{target_id}")
async def block_user_privacy(
    target_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """拉黑用户（隐私设置）"""
    service = get_privacy_settings_service(db)

    settings = await service.block_user(user_id, target_id)

    return {
        "success": True,
        "blocked_users": settings.blocked_users
    }


@router.delete("/privacy/unblock/{target_id}")
async def unblock_user_privacy(
    target_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """取消拉黑用户"""
    service = get_privacy_settings_service(db)

    settings = await service.unblock_user(user_id, target_id)

    return {
        "success": True,
        "blocked_users": settings.blocked_users
    }


# ==================== 通知 API ====================

@router.get("/notifications")
async def get_notifications(
    unread_only: bool = Query(False, description="是否仅获取未读通知"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取通知列表"""
    service = get_social_notification_service(db)

    notifications, total = await service.get_notifications(
        user_id, skip=skip, limit=limit, unread_only=unread_only
    )

    return {
        "success": True,
        "notifications": [
            {
                "notification_id": n.notification_id,
                "notification_type": n.notification_type,
                "sender_id": n.sender_id,
                "sender_name": n.sender_name,
                "post_id": n.post_id,
                "preview_content": n.preview_content,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            }
            for n in notifications
        ],
        "total": total,
        "has_more": total > skip + limit
    }


@router.post("/notifications/mark-read")
async def mark_notifications_as_read(
    notification_ids: List[str] = Body(..., description="通知 ID 列表"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """标记通知为已读"""
    service = get_social_notification_service(db)

    count = await service.mark_as_read(user_id, notification_ids)

    return {
        "success": True,
        "marked_count": count
    }


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_as_read(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """标记所有通知为已读"""
    service = get_social_notification_service(db)

    count = await service.mark_all_as_read(user_id)

    return {
        "success": True,
        "marked_count": count
    }


# ==================== 统计 API ====================

@router.get("/stats/overview")
async def get_social_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取社交统计概览"""
    from sqlalchemy import select, func
    from models.social_db import SocialPostDB, SocialRelationshipDB, CircleMemberDB, SocialNotificationDB

    # 获取帖子数
    post_result = await db.execute(
        select(func.count()).select_from(SocialPostDB).where(
            SocialPostDB.author_id == user_id,
            SocialPostDB.status == "published"
        )
    )
    post_count = post_result.scalar()

    # 获取好友数
    friend_result = await db.execute(
        select(func.count()).select_from(SocialRelationshipDB).where(
            SocialRelationshipDB.user_id == user_id,
            SocialRelationshipDB.relationship_type == "friend",
            SocialRelationshipDB.is_mutual == True
        )
    )
    friend_count = friend_result.scalar()

    # 获取圈子数
    circle_result = await db.execute(
        select(func.count()).select_from(CircleMemberDB).where(
            CircleMemberDB.user_id == user_id,
            CircleMemberDB.status == "active"
        )
    )
    circle_count = circle_result.scalar()

    # 获取未读通知数
    notification_result = await db.execute(
        select(func.count()).select_from(SocialNotificationDB).where(
            SocialNotificationDB.recipient_id == user_id,
            SocialNotificationDB.is_read == False
        )
    )
    unread_notification_count = notification_result.scalar()

    return {
        "success": True,
        "stats": {
            "post_count": post_count,
            "friend_count": friend_count,
            "circle_count": circle_count,
            "unread_notification_count": unread_notification_count
        }
    }
