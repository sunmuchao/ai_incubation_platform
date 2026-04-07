"""
管理后台 API 路由

提供管理后台所需的功能：
- 仪表盘数据统计
- 用户管理
- 内容管理
- 审核管理
- 治理统计
- 系统配置
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import db_manager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from db.models import DBPost, DBComment, DBCommunityMember, DBReport, DBBanRecord, DBAuditLog, DBLike, DBBookmark
from db.channel_models import DBChannel, DBChannelMember
from models.member import ReportStatus, ContentType, MemberRole
from services.ai_moderator_service import get_ai_moderator_service
from services.presence_service import get_presence_service
from services.level_service import get_level_service, LEVEL_PRIVILEGES


router = APIRouter(prefix="/api/admin", tags=["admin"])


# ==================== 请求/响应模型 ====================

class DashboardStatsResponse(BaseModel):
    """仪表盘统计响应"""
    total_users: int
    total_posts: int
    total_comments: int
    total_channels: int
    online_users: int
    pending_reports: int
    today_new_users: int
    today_posts: int
    ai_content_ratio: float


class UserStatsResponse(BaseModel):
    """用户统计响应"""
    total_users: int
    active_users_24h: int
    active_users_7d: int
    new_users_today: int
    banned_users: int


class ContentStatsResponse(BaseModel):
    """内容统计响应"""
    total_posts: int
    total_comments: int
    today_posts: int
    today_comments: int
    avg_posts_per_day: float


class GovernanceStatsResponse(BaseModel):
    """治理统计响应"""
    total_reports: int
    pending_reports: int
    resolved_reports: int
    auto_resolved_ratio: float
    total_bans: int
    active_bans: int


class UserSearchRequest(BaseModel):
    """用户搜索请求"""
    keyword: Optional[str] = Field(None, description="关键词")
    role: Optional[str] = Field(None, description="角色筛选")
    is_banned: Optional[bool] = Field(None, description="是否封禁")
    limit: int = Field(default=50, ge=1, le=200)


class ContentSearchRequest(BaseModel):
    """内容搜索请求"""
    keyword: Optional[str] = Field(None, description="关键词")
    author_id: Optional[str] = Field(None, description="作者 ID")
    channel_id: Optional[str] = Field(None, description="频道 ID")
    is_deleted: bool = Field(default=False, description="是否删除")
    limit: int = Field(default=50, ge=1, le=200)


class BanUserRequest(BaseModel):
    """封禁用户请求"""
    user_id: str = Field(..., description="用户 ID")
    reason: str = Field(..., description="封禁原因")
    ban_type: str = Field(default="all", description="封禁类型：all, post, comment")
    duration_hours: Optional[int] = Field(None, description="封禁时长（小时），None 为永久")


class AdminActionRequest(BaseModel):
    """管理员操作请求"""
    action: str = Field(..., description="操作类型")
    target_id: str = Field(..., description="目标 ID")
    reason: str = Field(..., description="操作原因")


# ==================== 仪表盘 ====================

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """
    获取仪表盘统计数据

    返回核心业务指标概览
    """
    async with db_manager._session_factory() as session:
        # 用户统计
        result = await session.execute(select(func.count(DBCommunityMember.id)))
        total_users = result.scalar() or 0

        # 今日新增用户
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(DBCommunityMember.id))
            .where(DBCommunityMember.created_at >= today_start)
        )
        today_new_users = result.scalar() or 0

        # 帖子统计
        result = await session.execute(select(func.count(DBPost.id)))
        total_posts = result.scalar() or 0

        result = await session.execute(
            select(func.count(DBPost.id))
            .where(DBPost.created_at >= today_start)
        )
        today_posts = result.scalar() or 0

        # 评论统计
        result = await session.execute(select(func.count(DBComment.id)))
        total_comments = result.scalar() or 0

        # 频道统计
        result = await session.execute(select(func.count(DBChannel.id)))
        total_channels = result.scalar() or 0

        # 在线用户
        presence_service = get_presence_service()
        online_users = presence_service.get_user_count()

        # 待处理举报
        result = await session.execute(
            select(func.count(DBReport.id))
            .where(DBReport.status == ReportStatus.PENDING.value)
        )
        pending_reports = result.scalar() or 0

        # AI 内容占比
        result = await session.execute(
            select(func.count(DBCommunityMember.id))
            .where(DBCommunityMember.member_type == "ai")
        )
        ai_members = result.scalar() or 0
        ai_content_ratio = round(ai_members / total_users * 100, 2) if total_users > 0 else 0

        return {
            "stats": {
                "total_users": total_users,
                "total_posts": total_posts,
                "total_comments": total_comments,
                "total_channels": total_channels,
                "online_users": online_users,
                "pending_reports": pending_reports,
                "today_new_users": today_new_users,
                "today_posts": today_posts,
                "ai_content_ratio": ai_content_ratio,
            }
        }


@router.get("/dashboard/user-stats")
async def get_user_stats():
    """获取用户统计数据"""
    async with db_manager._session_factory() as session:
        # 总用户数
        result = await session.execute(select(func.count(DBCommunityMember.id)))
        total_users = result.scalar() or 0

        # 今日新增
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(DBCommunityMember.id))
            .where(DBCommunityMember.created_at >= today_start)
        )
        new_users_today = result.scalar() or 0

        # 24 小时活跃用户（有发帖或评论）
        day_ago = datetime.now() - timedelta(days=1)
        result = await session.execute(
            select(func.distinct(DBPost.author_id))
            .where(DBPost.created_at >= day_ago)
        )
        active_posters = set(result.scalars().all())

        result = await session.execute(
            select(func.distinct(DBComment.author_id))
            .where(DBComment.created_at >= day_ago)
        )
        active_commenters = set(result.scalars().all())
        active_users_24h = len(active_posters | active_commenters)

        # 7 天活跃用户
        week_ago = datetime.now() - timedelta(days=7)
        result = await session.execute(
            select(func.distinct(DBPost.author_id))
            .where(DBPost.created_at >= week_ago)
        )
        active_posters_7d = set(result.scalars().all())

        result = await session.execute(
            select(func.distinct(DBComment.author_id))
            .where(DBComment.created_at >= week_ago)
        )
        active_commenters_7d = set(result.scalars().all())
        active_users_7d = len(active_posters_7d | active_commenters_7d)

        # 封禁用户数
        result = await session.execute(
            select(func.count(DBBanRecord.id))
            .where(DBBanRecord.is_active == True)
        )
        banned_users = result.scalar() or 0

        return {
            "stats": {
                "total_users": total_users,
                "active_users_24h": active_users_24h,
                "active_users_7d": active_users_7d,
                "new_users_today": new_users_today,
                "banned_users": banned_users,
            }
        }


@router.get("/dashboard/content-stats")
async def get_content_stats():
    """获取内容统计数据"""
    async with db_manager._session_factory() as session:
        # 总帖子数
        result = await session.execute(select(func.count(DBPost.id)))
        total_posts = result.scalar() or 0

        # 总评论数
        result = await session.execute(select(func.count(DBComment.id)))
        total_comments = result.scalar() or 0

        # 今日帖子
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(DBPost.id))
            .where(DBPost.created_at >= today_start)
        )
        today_posts = result.scalar() or 0

        # 今日评论
        result = await session.execute(
            select(func.count(DBComment.id))
            .where(DBComment.created_at >= today_start)
        )
        today_comments = result.scalar() or 0

        # 日均帖子数（过去 7 天）
        week_ago = datetime.now() - timedelta(days=7)
        result = await session.execute(
            select(func.count(DBPost.id))
            .where(DBPost.created_at >= week_ago)
        )
        week_posts = result.scalar() or 0
        avg_posts_per_day = round(week_posts / 7, 2)

        return {
            "stats": {
                "total_posts": total_posts,
                "total_comments": total_comments,
                "today_posts": today_posts,
                "today_comments": today_comments,
                "avg_posts_per_day": avg_posts_per_day,
            }
        }


@router.get("/dashboard/governance-stats")
async def get_governance_stats():
    """获取治理统计数据"""
    async with db_manager._session_factory() as session:
        # 总举报数
        result = await session.execute(select(func.count(DBReport.id)))
        total_reports = result.scalar() or 0

        # 待处理举报
        result = await session.execute(
            select(func.count(DBReport.id))
            .where(DBReport.status == ReportStatus.PENDING.value)
        )
        pending_reports = result.scalar() or 0

        # 已解决举报
        result = await session.execute(
            select(func.count(DBReport.id))
            .where(DBReport.status == ReportStatus.RESOLVED.value)
        )
        resolved_reports = result.scalar() or 0

        # AI 自动解决比例
        result = await session.execute(
            select(func.count(DBAuditLog.id))
            .where(DBAuditLog.operator_id == "ai_moderator")
        )
        auto_resolved = result.scalar() or 0
        auto_resolved_ratio = round(auto_resolved / total_reports * 100, 2) if total_reports > 0 else 0

        # 封禁统计
        result = await session.execute(select(func.count(DBBanRecord.id)))
        total_bans = result.scalar() or 0

        result = await session.execute(
            select(func.count(DBBanRecord.id))
            .where(DBBanRecord.is_active == True)
        )
        active_bans = result.scalar() or 0

        return {
            "stats": {
                "total_reports": total_reports,
                "pending_reports": pending_reports,
                "resolved_reports": resolved_reports,
                "auto_resolved_ratio": auto_resolved_ratio,
                "total_bans": total_bans,
                "active_bans": active_bans,
            }
        }


# ==================== 用户管理 ====================

@router.get("/users")
async def list_users(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    role: Optional[str] = Query(None, description="角色筛选"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    """获取用户列表"""
    async with db_manager._session_factory() as session:
        query = select(DBCommunityMember)

        if keyword:
            query = query.where(DBCommunityMember.name.like(f"%{keyword}%"))

        if role:
            query = query.where(DBCommunityMember.role == role)

        query = query.order_by(desc(DBCommunityMember.created_at))
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        members = result.scalars().all()

        # 获取总数
        count_query = select(func.count(DBCommunityMember.id))
        if keyword:
            count_query = count_query.where(DBCommunityMember.name.like(f"%{keyword}%"))
        if role:
            count_query = count_query.where(DBCommunityMember.role == role)

        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        return {
            "users": [
                {
                    "id": m.id,
                    "name": m.name,
                    "role": m.role,
                    "member_type": m.member_type.value,
                    "level": m.level,
                    "experience_points": m.experience_points,
                    "post_count": m.post_count,
                    "created_at": m.created_at.isoformat(),
                }
                for m in members
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    """获取用户详情"""
    async with db_manager._session_factory() as session:
        result = await session.execute(
            select(DBCommunityMember).where(DBCommunityMember.id == user_id)
        )
        member = result.scalar_one_or_none()

        if not member:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 获取用户等级信息
        level_service = get_level_service(session)
        level_info = await level_service.get_user_level(user_id)

        # 获取在线状态
        presence_service = get_presence_service()
        presence = presence_service.get_presence(user_id)

        return {
            "user": {
                "id": member.id,
                "name": member.name,
                "role": member.role,
                "member_type": member.member_type.value,
                "level": level_info,
                "post_count": member.post_count,
                "comment_count": member.comment_count,
                "like_count": member.like_count,
                "created_at": member.created_at.isoformat(),
                "online_status": presence.to_dict() if presence else None,
            }
        }


@router.post("/users/{user_id}/ban")
async def ban_user(user_id: str, request: BanUserRequest):
    """封禁用户"""
    # TODO: 实现封禁逻辑
    return {
        "success": True,
        "message": f"用户 {user_id} 已被封禁",
        "ban_type": request.ban_type,
        "reason": request.reason,
    }


@router.post("/users/{user_id}/unban")
async def unban_user(user_id: str):
    """解封用户"""
    # TODO: 实现解封逻辑
    return {
        "success": True,
        "message": f"用户 {user_id} 已被解封",
    }


# ==================== 内容管理 ====================

@router.get("/posts")
async def list_posts(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    author_id: Optional[str] = Query(None, description="作者 ID"),
    channel_id: Optional[str] = Query(None, description="频道 ID"),
    is_deleted: bool = Query(default=False, description="是否删除"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    """获取帖子列表"""
    async with db_manager._session_factory() as session:
        query = select(DBPost).where(DBPost.is_deleted == is_deleted)

        if keyword:
            query = query.where(DBPost.title.like(f"%{keyword}%"))

        if author_id:
            query = query.where(DBPost.author_id == author_id)

        if channel_id:
            query = query.where(DBPost.channel_id == channel_id)

        query = query.order_by(desc(DBPost.created_at))
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        posts = result.scalars().all()

        return {
            "posts": [
                {
                    "id": p.id,
                    "title": p.title,
                    "author_id": p.author_id,
                    "channel_id": p.channel_id,
                    "like_count": p.like_count,
                    "comment_count": p.comment_count,
                    "view_count": p.view_count,
                    "is_deleted": p.is_deleted,
                    "created_at": p.created_at.isoformat(),
                }
                for p in posts
            ],
            "total": len(posts),
        }


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, reason: str = Query(..., description="删除原因")):
    """删除帖子"""
    async with db_manager._session_factory() as session:
        result = await session.execute(select(DBPost).where(DBPost.id == post_id))
        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")

        post.is_deleted = True
        post.deleted_at = datetime.now()
        post.deleted_reason = reason
        await session.commit()

        return {
            "success": True,
            "message": "帖子已删除",
        }


# ==================== 审核管理 ====================

@router.get("/reports")
async def list_reports(
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    """获取举报列表"""
    async with db_manager._session_factory() as session:
        query = select(DBReport)

        if status:
            query = query.where(DBReport.status == status)

        query = query.order_by(desc(DBReport.created_at))
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        reports = result.scalars().all()

        return {
            "reports": [
                {
                    "id": r.id,
                    "report_type": r.report_type,
                    "reported_content_id": r.reported_content_id,
                    "reported_content_type": r.reported_content_type,
                    "reporter_id": r.reporter_id,
                    "status": r.status,
                    "handler_id": r.handler_id,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reports
            ],
            "total": len(reports),
        }


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """获取举报详情"""
    async with db_manager._session_factory() as session:
        result = await session.execute(select(DBReport).where(DBReport.id == report_id))
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="举报不存在")

        return {
            "report": {
                "id": report.id,
                "report_type": report.report_type,
                "reported_content_id": report.reported_content_id,
                "reported_content_type": report.reported_content_type,
                "reporter_id": report.reporter_id,
                "reason": report.reason,
                "status": report.status,
                "handler_id": report.handler_id,
                "handler_note": report.handler_note,
                "created_at": report.created_at.isoformat(),
                "processed_at": report.processed_at.isoformat() if report.processed_at else None,
            }
        }


# ==================== 审计日志 ====================

@router.get("/audit-logs")
async def list_audit_logs(
    operator_id: Optional[str] = Query(None, description="操作人 ID"),
    operation_type: Optional[str] = Query(None, description="操作类型"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    """获取审计日志列表"""
    async with db_manager._session_factory() as session:
        query = select(DBAuditLog)

        if operator_id:
            query = query.where(DBAuditLog.operator_id == operator_id)

        if operation_type:
            query = query.where(DBAuditLog.operation_type == operation_type)

        query = query.order_by(desc(DBAuditLog.created_at))
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        logs = result.scalars().all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "operator_id": log.operator_id,
                    "operation_type": log.operation_type,
                    "target_id": log.target_id,
                    "target_type": log.target_type,
                    "details": log.details,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            "total": len(logs),
        }


# ==================== AI 版主管理 ====================

@router.post("/ai-moderator/process")
async def ai_moderator_process(
    batch_size: int = Query(default=50, ge=1, le=200)
):
    """AI 版主批量处理举报"""
    async with db_manager._session_factory() as session:
        service = get_ai_moderator_service(session)
        result = await service.auto_process_reports(batch_size=batch_size)
        return {
            "success": True,
            "result": result,
        }


@router.get("/ai-moderator/stats")
async def get_ai_moderator_stats():
    """获取 AI 版主统计"""
    async with db_manager._session_factory() as session:
        service = get_ai_moderator_service(session)
        stats = await service.get_auto_moderation_stats()
        return {
            "success": True,
            "stats": stats,
        }


# ==================== 在线状态 ====================

@router.get("/presence/online-users")
async def get_online_users():
    """获取在线用户列表"""
    presence_service = get_presence_service()
    online_users = presence_service.get_online_users()
    return {
        "online_users": online_users,
        "count": len(online_users),
    }


@router.get("/presence/stats")
async def get_presence_stats():
    """获取在线状态统计"""
    presence_service = get_presence_service()
    stats = await presence_service.get_presence_stats()
    return {
        "success": True,
        "stats": stats,
    }
