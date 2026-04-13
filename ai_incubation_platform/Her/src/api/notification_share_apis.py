"""
Notification-002: 推送通知系统 API
Notification-003: 分享机制 API

通知系统端点:
- GET /api/notifications - 获取通知列表
- GET /api/notifications/unread-count - 获取未读通知数
- POST /api/notifications/{id}/read - 标记为已读
- POST /api/notifications/read-all - 标记全部为已读
- DELETE /api/notifications/{id} - 删除通知
- POST /api/notifications/push-token - 注册推送令牌
- DELETE /api/notifications/push-token - 注销推送令牌
- GET /api/notifications/preferences - 获取通知偏好
- PUT /api/notifications/preferences - 更新通知偏好

分享机制端点:
- POST /api/share/invite-code - 创建邀请码
- GET /api/share/invite-codes - 获取我的邀请码
- POST /api/share/invite-code/validate - 验证邀请码
- POST /api/share/invite-code/use - 使用邀请码
- POST /api/share/record - 创建分享记录
- GET /api/share/stats - 获取分享统计
- GET /api/share/invite-stats - 获取邀请统计
- GET /api/share/posters - 获取海报模板列表
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.notification_service import NotificationService, ShareService


# ============= Router 定义 =============

router_notifications = APIRouter(prefix="/api/notifications", tags=["Notification-通知系统"])
router_share = APIRouter(prefix="/api/share", tags=["Notification-分享机制"])


# ============= 请求/响应模型 =============

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    notification_type: str
    title: str
    content: str
    is_read: bool
    is_deleted: bool
    related_user_id: Optional[str]
    related_type: Optional[str]
    related_id: Optional[str]
    priority: str
    push_sent: bool
    created_at: datetime


class UnreadCountResponse(BaseModel):
    count: int


class CreatePushTokenRequest(BaseModel):
    platform: str = Field(..., description="推送平台：ios, android, web, wechat")
    token: str = Field(..., description="推送令牌")
    device_id: Optional[str] = None
    device_model: Optional[str] = None
    app_version: Optional[str] = None


class NotificationPreferencesResponse(BaseModel):
    enable_match_notification: bool
    enable_message_notification: bool
    enable_system_notification: bool
    enable_promotion_notification: bool


class UpdateNotificationPreferencesRequest(BaseModel):
    enable_match_notification: Optional[bool] = None
    enable_message_notification: Optional[bool] = None
    enable_system_notification: Optional[bool] = None
    enable_promotion_notification: Optional[bool] = None


class CreateInviteCodeRequest(BaseModel):
    code_type: str = Field(default="standard", description="邀请码类型：standard, vip, event, partner")
    max_uses: int = Field(default=10, description="最大使用次数")
    reward_type: str = Field(default="credits", description="奖励类型：credits, membership, coupon")
    reward_amount: int = Field(default=10, description="奖励数量")
    expires_days: Optional[int] = Field(default=None, description="有效期天数")


class InviteCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    code_type: str
    max_uses: int
    used_count: int
    reward_type: str
    reward_amount: int
    reward_description: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime


class ValidateInviteCodeRequest(BaseModel):
    code: str


class ValidateInviteCodeResponse(BaseModel):
    valid: bool
    code: Optional[str]
    reward_description: Optional[str]


class UseInviteCodeRequest(BaseModel):
    code: str


class CreateShareRecordRequest(BaseModel):
    share_type: str = Field(..., description="分享类型")
    channel: str = Field(..., description="分享渠道")
    share_url: str = Field(..., description="分享链接")
    content_type: Optional[str] = None
    content_id: Optional[str] = None
    share_title: Optional[str] = None
    share_description: Optional[str] = None
    share_image_url: Optional[str] = None


class ShareRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    share_type: str
    channel: str
    share_url: str
    view_count: int
    click_count: int
    convert_count: int
    created_at: datetime


class ShareStatsResponse(BaseModel):
    total_records: int
    total_views: int
    total_clicks: int
    total_converts: int
    channel_stats: Dict[str, Dict[str, int]]


class InviteStatsResponse(BaseModel):
    total_codes: int
    total_invites: int
    total_rewards: int
    invite_codes: List[Dict[str, Any]]


class SharePosterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    poster_key: str
    poster_name: str
    poster_type: str
    background_url: Optional[str]
    is_default: bool
    use_count: int


# ============= 通知系统 API =============

@router_notifications.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户未读通知数量"""
    service = NotificationService(db)
    count = service.get_unread_count(current_user_id)
    return {"count": count}


@router_notifications.get("", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    notification_type: Optional[str] = Query(default=None),
    unread_only: bool = Query(default=False),
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户通知列表"""
    service = NotificationService(db)
    notifications = service.get_notifications(
        user_id=current_user_id,
        limit=limit,
        offset=offset,
        notification_type=notification_type,
        unread_only=unread_only
    )
    return notifications


@router_notifications.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记通知为已读"""
    service = NotificationService(db)
    success = service.mark_as_read(notification_id, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}


@router_notifications.post("/read-all")
async def mark_all_as_read(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记所有通知为已读"""
    service = NotificationService(db)
    count = service.mark_all_as_read(current_user_id)
    return {"message": f"{count} notifications marked as read"}


@router_notifications.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除通知"""
    service = NotificationService(db)
    success = service.delete_notification(notification_id, current_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}


@router_notifications.post("/push-token")
async def register_push_token(
    request: CreatePushTokenRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """注册推送令牌"""
    service = NotificationService(db)
    push_token = service.register_push_token(
        user_id=current_user_id,
        platform=request.platform,
        token=request.token,
        device_id=request.device_id,
        device_model=request.device_model,
        app_version=request.app_version
    )
    return {"message": "Push token registered", "id": push_token.id}


@router_notifications.delete("/push-token")
async def unregister_push_token(
    token: str = Query(...),
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """注销推送令牌"""
    service = NotificationService(db)
    success = service.unregister_push_token(current_user_id, token)
    if not success:
        raise HTTPException(status_code=404, detail="Push token not found")
    return {"message": "Push token unregistered"}


@router_notifications.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户通知偏好"""
    service = NotificationService(db)
    preferences = service.get_notification_preferences(current_user_id)
    return preferences


@router_notifications.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    request: UpdateNotificationPreferencesRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户通知偏好"""
    service = NotificationService(db)
    success = service.update_notification_preferences(
        user_id=current_user_id,
        enable_match=request.enable_match_notification,
        enable_message=request.enable_message_notification,
        enable_system=request.enable_system_notification,
        enable_promotion=request.enable_promotion_notification
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update preferences")
    return service.get_notification_preferences(current_user_id)


# ============= 分享机制 API =============

@router_share.post("/invite-code", response_model=InviteCodeResponse)
async def create_invite_code(
    request: CreateInviteCodeRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建邀请码"""
    service = ShareService(db)
    invite_code = service.create_invite_code(
        user_id=current_user_id,
        code_type=request.code_type,
        max_uses=request.max_uses,
        reward_type=request.reward_type,
        reward_amount=request.reward_amount,
        expires_days=request.expires_days
    )
    return invite_code


@router_share.get("/invite-codes", response_model=List[InviteCodeResponse])
async def get_invite_codes(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的邀请码列表"""
    service = ShareService(db)
    invite_codes = service.get_user_invite_codes(current_user_id)
    return invite_codes


@router_share.post("/invite-code/validate", response_model=ValidateInviteCodeResponse)
async def validate_invite_code(
    request: ValidateInviteCodeRequest,
    db: Session = Depends(get_db)
):
    """验证邀请码是否有效"""
    service = ShareService(db)
    invite_code = service.validate_invite_code(request.code)

    if not invite_code:
        return {"valid": False, "code": None, "reward_description": None}

    return {
        "valid": True,
        "code": invite_code.code,
        "reward_description": invite_code.reward_description
    }


@router_share.post("/invite-code/use")
async def use_invite_code(
    request: UseInviteCodeRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """使用邀请码"""
    service = ShareService(db)

    # 不能使用自己的邀请码
    invite_code = service.validate_invite_code(request.code)
    if not invite_code:
        raise HTTPException(status_code=400, detail="Invalid or expired invite code")

    if invite_code.inviter_user_id == current_user_id:
        raise HTTPException(status_code=400, detail="Cannot use your own invite code")

    # 查询当前用户邮箱
    from db.models import UserDB
    user = db.query(UserDB).filter(UserDB.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reward = service.use_invite_code(
        code=request.code,
        invited_user_id=current_user_id,
        invited_user_email=user.email
    )

    if not reward:
        raise HTTPException(status_code=400, detail="Failed to use invite code")

    return {
        "message": "Invite code used successfully",
        "reward_type": reward.reward_type,
        "reward_amount": reward.reward_amount
    }


@router_share.post("/record", response_model=ShareRecordResponse)
async def create_share_record(
    request: CreateShareRecordRequest,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建分享记录"""
    service = ShareService(db)
    share_record = service.create_share_record(
        user_id=current_user_id,
        share_type=request.share_type,
        channel=request.channel,
        share_url=request.share_url,
        content_type=request.content_type,
        content_id=request.content_id,
        share_title=request.share_title,
        share_description=request.share_description,
        share_image_url=request.share_image_url
    )
    return share_record


@router_share.get("/stats", response_model=ShareStatsResponse)
async def get_share_stats(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户分享统计"""
    service = ShareService(db)
    stats = service.get_share_stats(current_user_id)
    return stats


@router_share.get("/invite-stats", response_model=InviteStatsResponse)
async def get_invite_stats(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户邀请统计"""
    service = ShareService(db)
    stats = service.get_invite_stats(current_user_id)
    return stats


@router_share.get("/posters", response_model=List[SharePosterResponse])
async def get_share_posters(
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取分享海报模板列表"""
    from models.notification_models import SharePosterDB
    from sqlalchemy import and_

    posters = db.query(SharePosterDB).filter(
        and_(
            SharePosterDB.is_active == True,
            SharePosterDB.is_default == True
        )
    ).all()

    return posters
