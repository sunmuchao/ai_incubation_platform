"""
人脸认证 API 路由

参考 Tinder Blue Star 认证徽章：
- 人脸照片认证
- 活体检测
- 认证徽章发放
- 认证状态查询
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from models.face_verification import (
    FaceVerificationMethod,
    FaceVerificationStatus,
    VerificationBadgeType,
    FaceVerificationRequest,
    FaceVerificationResponse,
    UserVerificationStatus,
    VERIFICATION_BADGE_CONFIG,
)
from services.face_verification_service import get_face_verification_service, FaceVerificationService
from auth.jwt import get_current_user
from db.database import get_db
from utils.logger import logger

router = APIRouter(prefix="/api/face-verification", tags=["face-verification"])


# ==================== 请求/响应模型 ====================

class StartVerificationRequest(BaseModel):
    """开始认证请求"""
    method: str = "id_card_compare"  # id_card_compare, self_photo, video_liveness


class VerificationStatusResponse(BaseModel):
    """认证状态响应"""
    user_id: str
    face_verified: bool
    face_verification_id: Optional[str]
    face_verification_date: Optional[str]
    id_verified: bool
    education_verified: bool
    occupation_verified: bool
    current_badge: Optional[str]
    badge_display_name: Optional[str]
    badge_display_icon: Optional[str]
    badge_display_color: Optional[str]
    trust_score: int


class SubmitPhotoRequest(BaseModel):
    """提交照片请求"""
    photo_base64: str
    method: str = "id_card_compare"
    video_base64: Optional[str] = None
    gesture_sequence: Optional[list] = None


class BadgeInfoResponse(BaseModel):
    """徽章信息响应"""
    badge_type: str
    icon: str
    color: str
    name: str
    description: str
    requirements: list


class VerificationRecordResponse(BaseModel):
    """认证记录响应"""
    id: str
    user_id: str
    method: str
    status: str
    similarity_score: Optional[float]
    liveness_score: Optional[float]
    is_passed: bool
    failure_reason: Optional[str]
    retry_count: int
    submitted_at: Optional[str]
    completed_at: Optional[str]


# ==================== API 端点 ====================

@router.get("/status", response_model=VerificationStatusResponse)
async def get_verification_status(current_user: str = Depends(get_current_user)):
    """
    获取用户认证状态

    返回人脸认证、身份认证、徽章等完整状态信息
    """
    user_id = current_user
    db = next(get_db())
    service = get_face_verification_service(db)

    status = service.get_user_verification_status(user_id)

    return VerificationStatusResponse(
        user_id=status.user_id,
        face_verified=status.face_verified,
        face_verification_id=status.face_verification_id,
        face_verification_date=status.face_verification_date.isoformat() if status.face_verification_date else None,
        id_verified=status.id_verified,
        education_verified=status.education_verified,
        occupation_verified=status.occupation_verified,
        current_badge=status.current_badge.value if status.current_badge else None,
        badge_display_name=status.badge_display_name,
        badge_display_icon=status.badge_display_icon,
        badge_display_color=status.badge_display_color,
        trust_score=status.trust_score,
    )


@router.post("/start", response_model=FaceVerificationResponse)
async def start_verification(
    request: StartVerificationRequest,
    current_user: str = Depends(get_current_user)
):
    """
    开始人脸认证流程

    Args:
        method: 认证方式（id_card_compare/self_photo/video_liveness）

    Returns:
        认证流程状态
    """
    user_id = current_user
    logger.info(f"Starting face verification: user={user_id}, method={request.method}")

    db = next(get_db())
    service = get_face_verification_service(db)

    try:
        method = FaceVerificationMethod(request.method)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的认证方式")

    result = service.start_verification(user_id, method)

    return result


@router.post("/submit", response_model=FaceVerificationResponse)
async def submit_verification(
    request: SubmitPhotoRequest,
    current_user: str = Depends(get_current_user)
):
    """
    提交人脸照片进行认证

    Args:
        photo_base64: 人脸照片（Base64 编码）
        method: 认证方式
        video_base64: 活体检测视频（可选）
        gesture_sequence: 动作序列（可选）

    Returns:
        认证结果
    """
    user_id = current_user
    logger.info(f"Submitting face verification: user={user_id}")

    # 验证照片数据
    if not request.photo_base64:
        raise HTTPException(status_code=400, detail="请提供人脸照片")

    # 验证 Base64 格式
    try:
        # 检查是否是有效的 Base64
        import base64
        base64.b64decode(request.photo_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="照片格式无效，请使用 Base64 编码")

    db = next(get_db())
    service = get_face_verification_service(db)

    try:
        method = FaceVerificationMethod(request.method)
    except ValueError:
        method = FaceVerificationMethod.ID_CARD_COMPARE

    verification_request = FaceVerificationRequest(
        method=method,
        photo_base64=request.photo_base64,
        video_base64=request.video_base64,
        gesture_sequence=request.gesture_sequence,
    )

    result = service.submit_verification(user_id, verification_request)

    return result


@router.post("/retry", response_model=FaceVerificationResponse)
async def retry_verification(current_user: str = Depends(get_current_user)):
    """
    重试人脸认证

    Returns:
        重试状态
    """
    user_id = current_user

    db = next(get_db())
    service = get_face_verification_service(db)

    result = service.retry_verification(user_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return result


@router.get("/record", response_model=VerificationRecordResponse)
async def get_verification_record(current_user: str = Depends(get_current_user)):
    """
    获取用户认证记录

    Returns:
        认证记录详情
    """
    user_id = current_user

    db = next(get_db())
    service = get_face_verification_service(db)

    record = service.get_verification_record(user_id)

    if not record:
        raise HTTPException(status_code=404, detail="未找到认证记录")

    return VerificationRecordResponse(
        id=record.id,
        user_id=record.user_id,
        method=record.method,
        status=record.status,
        similarity_score=record.similarity_score,
        liveness_score=record.liveness_score,
        is_passed=record.is_passed,
        failure_reason=record.failure_reason,
        retry_count=record.retry_count,
        submitted_at=record.submitted_at.isoformat() if record.submitted_at else None,
        completed_at=record.completed_at.isoformat() if record.completed_at else None,
    )


@router.get("/badges")
async def get_all_badges():
    """
    获取所有徽章类型说明

    Returns:
        徽章类型列表及说明
    """
    badges = []
    for badge_type, config in VERIFICATION_BADGE_CONFIG.items():
        badges.append(BadgeInfoResponse(
            badge_type=badge_type.value,
            icon=config["icon"],
            color=config["color"],
            name=config["name"],
            description=config["description"],
            requirements=config["requirements"],
        ))

    return {
        "success": True,
        "badges": badges,
        "total": len(badges),
    }


@router.get("/badge/{badge_type}")
async def get_badge_info(badge_type: str):
    """
    获取单个徽章信息

    Args:
        badge_type: 徽章类型

    Returns:
        徽章详情
    """
    try:
        badge = VerificationBadgeType(badge_type)
    except ValueError:
        raise HTTPException(status_code=404, detail="徽章类型不存在")

    config = VERIFICATION_BADGE_CONFIG.get(badge)
    if not config:
        raise HTTPException(status_code=404, detail="徽章信息不存在")

    return BadgeInfoResponse(
        badge_type=badge.value,
        icon=config["icon"],
        color=config["color"],
        name=config["name"],
        description=config["description"],
        requirements=config["requirements"],
    )


@router.get("/check/{user_id}")
async def check_user_verified(user_id: str):
    """
    检查用户是否已认证（公开接口）

    Args:
        user_id: 用户 ID

    Returns:
        是否已认证
    """
    db = next(get_db())
    service = get_face_verification_service(db)

    is_verified = service.check_user_verified(user_id)

    return {
        "user_id": user_id,
        "verified": is_verified,
    }


@router.get("/user/{user_id}/badge")
async def get_user_badge(user_id: str):
    """
    获取用户认证徽章（公开接口）

    Args:
        user_id: 用户 ID

    Returns:
        用户徽章信息
    """
    db = next(get_db())
    service = get_face_verification_service(db)

    status = service.get_user_verification_status(user_id)

    if not status.current_badge:
        return {
            "user_id": user_id,
            "verified": False,
            "badge": None,
        }

    badge_info = service.get_badge_display_info(status.current_badge)

    return {
        "user_id": user_id,
        "verified": True,
        "badge": {
            "type": status.current_badge.value,
            "icon": badge_info["icon"],
            "color": badge_info["color"],
            "name": badge_info["name"],
        },
        "trust_score": status.trust_score,
    }


@router.get("/methods")
async def get_verification_methods():
    """
    获取所有认证方式说明

    Returns:
        认证方式列表
    """
    return {
        "success": True,
        "methods": [
            {
                "type": "id_card_compare",
                "name": "身份证比对",
                "description": "自拍照片与身份证照片进行比对",
                "difficulty": "简单",
                "estimated_time": "1-2 分钟",
            },
            {
                "type": "self_photo",
                "name": "自拍认证",
                "description": "仅自拍照片认证",
                "difficulty": "简单",
                "estimated_time": "1 分钟",
            },
            {
                "type": "video_liveness",
                "name": "视频活体检测",
                "description": "录制短视频进行活体检测",
                "difficulty": "中等",
                "estimated_time": "2-3 分钟",
            },
            {
                "type": "ai_gesture",
                "name": "AI 动作检测",
                "description": "按提示完成眨眼、张嘴等动作",
                "difficulty": "中等",
                "estimated_time": "2-3 分钟",
            },
        ],
    }