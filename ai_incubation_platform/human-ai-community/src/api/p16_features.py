"""
社区活动系统 API 路由
支持线上活动（AMA/直播/投票）、线下聚会、活动管理（报名/签到/回顾）、直播系统等功能
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from db.manager import db_manager

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.p16_entities import (
    CreateActivityRequest, UpdateActivityRequest, ActivityResponse, ActivityListItem,
    RegisterActivityRequest, RegistrationResponse,
    CreateSessionRequest, SessionResponse,
    CreateInteractionRequest, InteractionResponse,
    CreateLiveStreamRequest, LiveStreamResponse, ChatMessageRequest, ChatMessageResponse,
    CreateVoteRequest, AddVoteOptionRequest, CastVoteRequest,
    VoteResponse, VoteResultsResponse, VoteOptionResponse,
    CreateRecapRequest, RecapResponse,
    SuccessResponse, ErrorResponse,
    ActivityType, ActivityStatus, ActivityRole, RegistrationStatus,
    InteractionType, VoteType, LiveStreamStatus
)
from services.activity_service import get_activity_service, ActivityService
from services.live_stream_service import get_live_stream_service, get_live_chat_service, LiveStreamService, LiveChatService
from services.vote_service import get_vote_service, VoteService
from db.activity_models import (
    ActivityTypeEnum, ActivityStatusEnum, ActivityRoleEnum, RegistrationStatusEnum,
    ActivityInteractionTypeEnum, LiveStreamStatusEnum, VoteTypeEnum
)

router = APIRouter(prefix="/api/p16", tags=["community-activities"])


# ==================== 活动管理 API ====================

@router.post("/activities", response_model=Dict[str, Any])
async def create_activity(request: CreateActivityRequest):
    """
    创建活动

    支持线上活动、线下活动、直播、AMA、投票等多种活动类型
    """
    async with db_manager.get_session() as db:
        service = get_activity_service(db)

        # 转换枚举类型
        activity_type = ActivityTypeEnum(request.activity_type.value)

        try:
            activity = await service.create_activity(
                organizer_id="demo_user_001",  # TODO: 从认证上下文获取
                title=request.title,
                description=request.description,
                activity_type=activity_type,
                start_time=request.start_time,
                end_time=request.end_time,
                content=request.content,
                location_type=request.location_type,
                location_address=request.location_address,
                location_online_url=request.location_online_url,
                max_participants=request.max_participants,
                tags=request.tags,
                cover_image_url=request.cover_image_url,
            )

            return {
                "success": True,
                "message": "活动创建成功",
                "data": {
                    "activity_id": activity.id,
                    "title": activity.title,
                    "status": activity.status.value,
                }
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/activities/{activity_id}", response_model=Dict[str, Any])
async def get_activity(activity_id: str):
    """获取活动详情"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        activity = await service.get_activity(activity_id)

        if not activity:
            raise HTTPException(status_code=404, detail="活动不存在")

        return {
            "success": True,
            "data": {
                "id": activity.id,
                "title": activity.title,
                "description": activity.description,
                "content": activity.content,
                "activity_type": activity.activity_type.value,
                "status": activity.status.value,
                "organizer_id": activity.organizer_id,
                "co_organizers": activity.co_organizers,
                "start_time": activity.start_time.isoformat(),
                "end_time": activity.end_time.isoformat(),
                "registration_start": activity.registration_start.isoformat() if activity.registration_start else None,
                "registration_end": activity.registration_end.isoformat() if activity.registration_end else None,
                "location_type": activity.location_type,
                "location_address": activity.location_address,
                "location_online_url": activity.location_online_url,
                "max_participants": activity.max_participants,
                "current_participants": activity.current_participants,
                "tags": activity.tags,
                "cover_image_url": activity.cover_image_url,
                "view_count": activity.view_count,
                "registration_count": activity.registration_count,
                "attendance_count": activity.attendance_count,
                "allow_comments": activity.allow_comments,
                "allow_chat": activity.allow_chat,
                "allow_questions": activity.allow_questions,
                "created_at": activity.created_at.isoformat(),
            }
        }


@router.put("/activities/{activity_id}", response_model=Dict[str, Any])
async def update_activity(activity_id: str, request: UpdateActivityRequest):
    """更新活动"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)

        update_data = request.model_dump(exclude_unset=True)

        # 转换枚举类型
        if "status" in update_data and update_data["status"]:
            update_data["status"] = ActivityStatusEnum(update_data["status"])

        activity = await service.update_activity(activity_id, **update_data)

        if not activity:
            raise HTTPException(status_code=404, detail="活动不存在")

        return {
            "success": True,
            "message": "活动更新成功",
            "data": {"activity_id": activity.id}
        }


@router.delete("/activities/{activity_id}", response_model=Dict[str, Any])
async def delete_activity(activity_id: str):
    """删除活动"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        success = await service.delete_activity(activity_id)

        if not success:
            raise HTTPException(status_code=404, detail="活动不存在")

        return {"success": True, "message": "活动删除成功"}


@router.get("/activities", response_model=Dict[str, Any])
async def list_activities(
    status: Optional[str] = Query(None, description="活动状态"),
    activity_type: Optional[str] = Query(None, description="活动类型"),
    organizer_id: Optional[str] = Query(None, description="组织者 ID"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """获取活动列表"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)

        status_enum = ActivityStatusEnum(status) if status else None
        type_enum = ActivityTypeEnum(activity_type) if activity_type else None

        activities = await service.list_activities(
            status=status_enum,
            activity_type=type_enum,
            organizer_id=organizer_id,
            limit=limit,
            offset=offset,
        )

        return {
            "success": True,
            "total": len(activities),
            "activities": [
                {
                    "id": a.id,
                    "title": a.title,
                    "description": a.description,
                    "activity_type": a.activity_type.value,
                    "status": a.status.value,
                    "start_time": a.start_time.isoformat(),
                    "end_time": a.end_time.isoformat(),
                    "location_type": a.location_type,
                    "current_participants": a.current_participants,
                    "max_participants": a.max_participants,
                    "cover_image_url": a.cover_image_url,
                    "view_count": a.view_count,
                    "registration_count": a.registration_count,
                }
                for a in activities
            ]
        }


@router.get("/activities/upcoming", response_model=Dict[str, Any])
async def get_upcoming_activities(limit: int = Query(default=20, ge=1, le=50)):
    """获取即将开始的活动"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        activities = await service.get_upcoming_activities(limit=limit)

        return {
            "success": True,
            "total": len(activities),
            "activities": [
                {
                    "id": a.id,
                    "title": a.title,
                    "start_time": a.start_time.isoformat(),
                    "location_type": a.location_type,
                }
                for a in activities
            ]
        }


@router.get("/activities/live", response_model=Dict[str, Any])
async def get_live_activities():
    """获取进行中的活动"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        activities = await service.get_live_activities()

        return {
            "success": True,
            "total": len(activities),
            "activities": [
                {
                    "id": a.id,
                    "title": a.title,
                    "start_time": a.start_time.isoformat(),
                    "end_time": a.end_time.isoformat(),
                    "viewer_count": a.view_count,
                }
                for a in activities
            ]
        }


@router.post("/activities/{activity_id}/view", response_model=Dict[str, Any])
async def increment_activity_view(activity_id: str):
    """增加活动浏览次数"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        success = await service.increment_view_count(activity_id)

        if not success:
            raise HTTPException(status_code=404, detail="活动不存在")

        return {"success": True, "message": "浏览次数已更新"}


# ==================== 活动报名 API ====================

@router.post("/activities/{activity_id}/register", response_model=Dict[str, Any])
async def register_activity(activity_id: str, request: RegisterActivityRequest):
    """报名参加活动"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)

        role = ActivityRoleEnum(request.role.value) if request.role else ActivityRoleEnum.ATTENDEE

        success, registration, message = await service.register_activity(
            activity_id=activity_id,
            user_id="demo_user_001",  # TODO: 从认证上下文获取
            role=role,
            registration_note=request.registration_note,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": message,
            "data": {
                "registration_id": registration.id,
                "status": registration.status.value,
            }
        }


@router.delete("/activities/{activity_id}/register", response_model=Dict[str, Any])
async def cancel_registration(activity_id: str):
    """取消活动报名"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        success, message = await service.cancel_registration(
            activity_id=activity_id,
            user_id="demo_user_001",
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "message": message}


@router.post("/activities/{activity_id}/checkin", response_model=Dict[str, Any])
async def check_in(activity_id: str):
    """活动签到"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        success, message = await service.check_in(
            activity_id=activity_id,
            user_id="demo_user_001",
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "message": message}


@router.get("/activities/{activity_id}/registrations", response_model=Dict[str, Any])
async def get_registrations(
    activity_id: str,
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
):
    """获取活动报名列表"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)

        status_enum = RegistrationStatusEnum(status) if status else None
        role_enum = ActivityRoleEnum(role) if role else None

        registrations = await service.get_registrations(
            activity_id=activity_id,
            status=status_enum,
            role=role_enum,
            limit=limit,
        )

        return {
            "success": True,
            "total": len(registrations),
            "registrations": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "role": r.role.value,
                    "status": r.status.value,
                    "checked_in": r.checked_in,
                    "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
                    "created_at": r.created_at.isoformat(),
                }
                for r in registrations
            ]
        }


# ==================== 活动议程 API ====================

@router.post("/activities/{activity_id}/sessions", response_model=Dict[str, Any])
async def create_session(activity_id: str, request: CreateSessionRequest):
    """创建活动议程"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)

        session = await service.create_session(
            activity_id=activity_id,
            title=request.title,
            description=request.description,
            start_time=request.start_time,
            end_time=request.end_time,
            speakers=request.speakers,
            session_type=request.session_type,
            order_index=request.order_index,
        )

        return {
            "success": True,
            "message": "议程创建成功",
            "data": {"session_id": session.id}
        }


@router.get("/activities/{activity_id}/sessions", response_model=Dict[str, Any])
async def get_sessions(activity_id: str):
    """获取活动议程列表"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        sessions = await service.get_sessions(activity_id)

        return {
            "success": True,
            "total": len(sessions),
            "sessions": [
                {
                    "id": s.id,
                    "title": s.title,
                    "description": s.description,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat(),
                    "speakers": s.speakers,
                    "session_type": s.session_type,
                    "order_index": s.order_index,
                }
                for s in sessions
            ]
        }


# ==================== 活动互动 API ====================

@router.post("/activities/{activity_id}/interactions", response_model=Dict[str, Any])
async def create_interaction(activity_id: str, request: CreateInteractionRequest):
    """创建活动互动"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)

        interaction_type = ActivityInteractionTypeEnum(request.interaction_type.value)

        try:
            interaction = await service.create_interaction(
                activity_id=activity_id,
                user_id="demo_user_001",
                interaction_type=interaction_type,
                content=request.content,
                parent_id=request.parent_id,
                target_id=request.target_id,
                session_id=request.session_id,
            )

            return {
                "success": True,
                "message": "互动创建成功",
                "data": {"interaction_id": interaction.id}
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/activities/{activity_id}/interactions", response_model=Dict[str, Any])
async def get_interactions(
    activity_id: str,
    interaction_type: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
):
    """获取活动互动列表"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)

        type_enum = ActivityInteractionTypeEnum(interaction_type) if interaction_type else None

        interactions = await service.get_interactions(
            activity_id=activity_id,
            interaction_type=type_enum,
            session_id=session_id,
            limit=limit,
        )

        return {
            "success": True,
            "total": len(interactions),
            "interactions": [
                {
                    "id": i.id,
                    "user_id": i.user_id,
                    "interaction_type": i.interaction_type.value,
                    "content": i.content,
                    "is_pinned": i.is_pinned,
                    "is_answered": i.is_answered,
                    "like_count": i.like_count,
                    "reply_count": i.reply_count,
                    "created_at": i.created_at.isoformat(),
                }
                for i in interactions
            ]
        }


@router.post("/interactions/{interaction_id}/answer", response_model=Dict[str, Any])
async def answer_question(interaction_id: str):
    """标记问题为已回答"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        interaction = await service.answer_question(interaction_id)

        if not interaction:
            raise HTTPException(status_code=404, detail="互动不存在")

        return {"success": True, "message": "问题已标记为已回答"}


@router.post("/interactions/{interaction_id}/pin", response_model=Dict[str, Any])
async def pin_interaction(interaction_id: str, pinned: bool = True):
    """置顶/取消置顶互动"""
    async with db_manager.get_session() as db:
        service = get_activity_service(db)
        interaction = await service.pin_interaction(interaction_id, pinned)

        if not interaction:
            raise HTTPException(status_code=404, detail="互动不存在")

        return {"success": True, "message": "操作成功"}


# ==================== 直播 API ====================

@router.post("/live-streams", response_model=Dict[str, Any])
async def create_live_stream(request: CreateLiveStreamRequest):
    """创建直播"""
    # TODO: 需要传入 activity_id
    async with db_manager.get_session() as db:
        service = get_live_stream_service(db)

        success, stream, message = await service.create_live_stream(
            activity_id="demo_activity_001",  # TODO: 从请求获取
            is_chat_enabled=request.is_chat_enabled,
            is_gift_enabled=request.is_gift_enabled,
            is_record_enabled=request.is_record_enabled,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": message,
            "data": {
                "stream_id": stream.id,
                "stream_key": stream.stream_key,
                "status": stream.status.value,
            }
        }


@router.get("/live-streams/{stream_id}", response_model=Dict[str, Any])
async def get_live_stream(stream_id: str):
    """获取直播详情"""
    async with db_manager.get_session() as db:
        service = get_live_stream_service(db)
        stream = await service.get_live_stream(stream_id)

        if not stream:
            raise HTTPException(status_code=404, detail="直播不存在")

        return {
            "success": True,
            "data": {
                "id": stream.id,
                "activity_id": stream.activity_id,
                "status": stream.status.value,
                "viewer_count": stream.viewer_count,
                "peak_viewer_count": stream.peak_viewer_count,
                "total_views": stream.total_views,
                "like_count": stream.like_count,
                "gift_value": stream.gift_value,
                "is_chat_enabled": stream.is_chat_enabled,
                "is_gift_enabled": stream.is_gift_enabled,
                "recording_url": stream.recording_url,
                "started_at": stream.started_at.isoformat() if stream.started_at else None,
                "ended_at": stream.ended_at.isoformat() if stream.ended_at else None,
            }
        }


@router.post("/live-streams/{stream_id}/start", response_model=Dict[str, Any])
async def start_live_stream(stream_id: str):
    """开始直播"""
    async with db_manager.get_session() as db:
        service = get_live_stream_service(db)
        success, stream, message = await service.start_live_stream(stream_id)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "message": message}


@router.post("/live-streams/{stream_id}/end", response_model=Dict[str, Any])
async def end_live_stream(stream_id: str):
    """结束直播"""
    async with db_manager.get_session() as db:
        service = get_live_stream_service(db)
        success, stream, message = await service.end_live_stream(stream_id)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "message": message}


@router.post("/live-streams/{stream_id}/like", response_model=Dict[str, Any])
async def like_live_stream(stream_id: str):
    """直播点赞"""
    async with db_manager.get_session() as db:
        service = get_live_stream_service(db)
        success = await service.increment_like_count(stream_id)

        if not success:
            raise HTTPException(status_code=404, detail="直播不存在")

        return {"success": True, "message": "点赞成功"}


# ==================== 直播聊天 API ====================

@router.post("/live-streams/{stream_id}/chat", response_model=Dict[str, Any])
async def send_chat_message(stream_id: str, request: ChatMessageRequest):
    """发送直播聊天消息"""
    async with db_manager.get_session() as db:
        service = get_live_chat_service(db)

        success, message, result = await service.send_chat_message(
            stream_id=stream_id,
            user_id="demo_user_001",
            content=request.content,
            message_type=request.message_type,
            gift_info=request.gift_info,
        )

        if not success:
            raise HTTPException(status_code=400, detail=result)

        return {
            "success": True,
            "message": result,
            "data": {"message_id": message.id}
        }


@router.get("/live-streams/{stream_id}/chat", response_model=Dict[str, Any])
async def get_chat_messages(
    stream_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """获取直播聊天消息"""
    async with db_manager.get_session() as db:
        service = get_live_chat_service(db)
        messages = await service.get_chat_messages(stream_id, limit=limit, offset=offset)

        return {
            "success": True,
            "total": len(messages),
            "messages": [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "content": m.content,
                    "message_type": m.message_type,
                    "gift_info": m.gift_info,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ]
        }


# ==================== 投票 API ====================

@router.post("/votes", response_model=Dict[str, Any])
async def create_vote(request: CreateVoteRequest):
    """创建投票"""
    async with db_manager.get_session() as db:
        service = get_vote_service(db)

        vote_type = VoteTypeEnum(request.vote_type.value)

        success, vote, message = await service.create_vote(
            activity_id="demo_activity_001",  # TODO: 从请求获取
            title=request.title,
            description=request.description,
            vote_type=vote_type,
            start_time=request.start_time,
            end_time=request.end_time,
            min_choices=request.min_choices,
            max_choices=request.max_choices,
            is_anonymous=request.is_anonymous,
            show_results_before_vote=request.show_results_before_vote,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": message,
            "data": {"vote_id": vote.id}
        }


@router.get("/votes/{vote_id}", response_model=Dict[str, Any])
async def get_vote(vote_id: str):
    """获取投票详情"""
    async with db_manager.get_session() as db:
        service = get_vote_service(db)
        vote = await service.get_vote(vote_id)

        if not vote:
            raise HTTPException(status_code=404, detail="投票不存在")

        options = await service.get_vote_options(vote_id)

        return {
            "success": True,
            "data": {
                "id": vote.id,
                "activity_id": vote.activity_id,
                "title": vote.title,
                "description": vote.description,
                "vote_type": vote.vote_type.value,
                "status": vote.status.value,
                "min_choices": vote.min_choices,
                "max_choices": vote.max_choices,
                "is_anonymous": vote.is_anonymous,
                "start_time": vote.start_time.isoformat(),
                "end_time": vote.end_time.isoformat(),
                "total_voters": vote.total_voters,
                "total_votes": vote.total_votes,
                "options": [
                    {
                        "id": opt.id,
                        "title": opt.title,
                        "description": opt.description,
                        "vote_count": opt.vote_count,
                        "vote_percentage": opt.vote_percentage,
                    }
                    for opt in options
                ],
            }
        }


@router.get("/votes/{vote_id}/results", response_model=Dict[str, Any])
async def get_vote_results(vote_id: str):
    """获取投票结果"""
    async with db_manager.get_session() as db:
        service = get_vote_service(db)
        results = await service.get_vote_results(vote_id)

        if not results:
            raise HTTPException(status_code=404, detail="投票不存在")

        return {"success": True, "data": results}


@router.post("/votes/{vote_id}/cast", response_model=Dict[str, Any])
async def cast_vote(vote_id: str, request: CastVoteRequest):
    """投票"""
    async with db_manager.get_session() as db:
        service = get_vote_service(db)

        success, record, message = await service.cast_vote(
            vote_id=vote_id,
            user_id="demo_user_001",
            selected_options=request.selected_options,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "message": message}


@router.post("/votes/{vote_id}/end", response_model=Dict[str, Any])
async def end_vote(vote_id: str):
    """手动结束投票"""
    async with db_manager.get_session() as db:
        service = get_vote_service(db)
        success, vote, message = await service.end_vote(vote_id)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "message": message}


@router.post("/votes/{vote_id}/options", response_model=Dict[str, Any])
async def add_vote_option(vote_id: str, request: AddVoteOptionRequest):
    """添加投票选项"""
    async with db_manager.get_session() as db:
        service = get_vote_service(db)

        success, option, message = await service.add_vote_option(
            vote_id=vote_id,
            title=request.title,
            description=request.description,
            image_url=request.image_url,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": message,
            "data": {"option_id": option.id}
        }
