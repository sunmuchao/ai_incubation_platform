"""
照片管理 API

P4 新增:
- 照片上传
- 照片审核
- 照片展示
- 照片验证机制
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.photo_service import PhotoService


router = APIRouter(prefix="/api/photos", tags=["照片管理"])


# ============= Pydantic 模型 =============

class PhotoResponse(BaseModel):
    """照片响应模型"""
    id: str
    user_id: str
    photo_url: str
    photo_type: str
    display_order: int
    moderation_status: str
    moderation_reason: Optional[str] = None
    ai_tags: str = ""
    ai_quality_score: Optional[float] = None
    is_verified: bool = False
    like_count: int = 0
    view_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


class PhotoUploadRequest(BaseModel):
    """照片上传请求"""
    photo_url: str = Field(..., description="照片 URL")
    photo_type: str = Field(default="profile", description="照片类型")
    ai_tags: Optional[List[str]] = Field(default=None, description="AI 分析标签")
    ai_quality_score: Optional[float] = Field(default=None, description="AI 质量评分")


class PhotoOrderUpdateRequest(BaseModel):
    """照片排序更新请求"""
    photo_ids: List[str] = Field(..., description="按新顺序排列的照片 ID 列表")


class ModeratePhotoRequest(BaseModel):
    """审核照片请求"""
    status: str = Field(..., description="审核状态：approved/rejected")
    reason: Optional[str] = Field(default=None, description="审核原因")


class VerifyPhotoRequest(BaseModel):
    """验证照片请求"""
    pose: str = Field(..., description="验证姿势")
    is_match: bool = Field(..., description="是否匹配")


# ============= API 端点 =============

@router.post("/upload", response_model=PhotoResponse, summary="上传照片")
async def upload_photo(
    request: PhotoUploadRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    上传照片

    - **photo_url**: 照片 URL (已上传到 OSS/CDN 后的地址)
    - **photo_type**: 照片类型 (profile/avatar/verification/lifestyle)
    - **ai_tags**: AI 分析标签 (可选)
    - **ai_quality_score**: AI 质量评分 (可选)
    """
    service = PhotoService(db)

    try:
        photo = service.upload_photo(
            user_id=current_user.id,
            photo_url=request.photo_url,
            photo_type=request.photo_type,
            ai_tags=request.ai_tags,
            ai_quality_score=request.ai_quality_score
        )
        return photo
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/my", response_model=List[PhotoResponse], summary="获取我的照片列表")
async def get_my_photos(
    approved_only: bool = Query(default=False, description="是否只返回已审核通过的照片"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取当前用户的照片列表"""
    service = PhotoService(db)
    photos = service.get_user_photos(current_user.id, approved_only=approved_only)
    return photos


@router.get("/{photo_id}", response_model=PhotoResponse, summary="获取照片详情")
async def get_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取指定照片的详情"""
    service = PhotoService(db)
    photo = service.get_photo(photo_id)

    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在")

    # 权限检查：只能查看自己的照片或已审核通过的公共照片
    if photo.user_id != current_user.id and photo.moderation_status != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此照片")

    return photo


@router.get("/user/{user_id}", response_model=List[PhotoResponse], summary="获取用户照片列表")
async def get_user_photos(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取指定用户的已审核通过照片列表"""
    service = PhotoService(db)
    photos = service.get_user_photos(user_id, approved_only=True)
    return photos


@router.put("/order", summary="更新照片排序")
async def update_photo_order(
    request: PhotoOrderUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """更新用户照片的显示顺序"""
    service = PhotoService(db)
    success = service.update_photo_order(current_user.id, request.photo_ids)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新失败")

    return {"message": "排序更新成功"}


@router.delete("/{photo_id}", summary="删除照片")
async def delete_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """删除照片"""
    service = PhotoService(db)
    success = service.delete_photo(photo_id, current_user.id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="删除失败")

    return {"message": "照片已删除"}


@router.post("/{photo_id}/moderate", response_model=PhotoResponse, summary="审核照片")
async def moderate_photo(
    photo_id: str,
    request: ModeratePhotoRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    审核照片 (仅管理员可用)

    - **status**: 审核状态 (approved/rejected)
    - **reason**: 审核原因
    """
    from utils.admin_check import require_admin
    require_admin(current_user)  # 管理员权限检查

    service = PhotoService(db)

    photo = service.moderate_photo(
        photo_id=photo_id,
        moderator_id=current_user.id,
        status=request.status,
        reason=request.reason
    )

    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在")

    return photo


@router.post("/{photo_id}/verify", response_model=PhotoResponse, summary="验证照片姿势")
async def verify_photo(
    photo_id: str,
    request: VerifyPhotoRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    验证照片姿势 (真人验证)

    - **pose**: 验证姿势 (如 "raised_hand", "thumbs_up")
    - **is_match**: 是否匹配
    """
    service = PhotoService(db)

    photo = service.verify_photo_pose(
        photo_id=photo_id,
        user_id=current_user.id,
        pose=request.pose,
        is_match=request.is_match
    )

    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在")

    return photo


@router.post("/{photo_id}/like", summary="点赞照片")
async def like_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """点赞照片"""
    service = PhotoService(db)
    success = service.increment_like_count(photo_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在")

    return {"message": "点赞成功"}


@router.post("/{photo_id}/view", summary="增加照片查看次数")
async def view_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """增加照片查看次数"""
    service = PhotoService(db)
    success = service.increment_view_count(photo_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在")

    return {"message": "查看次数已更新"}


@router.get("/stats/verified-count", summary="获取已验证照片数量")
async def get_verified_count(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取当前用户的已验证照片数量"""
    service = PhotoService(db)
    count = service.get_verified_photos_count(current_user.id)
    return {"verified_count": count}


@router.get("/stats/avatar-url", summary="获取头像 URL")
async def get_avatar_url(
    user_id: Optional[str] = Query(default=None, description="用户 ID，不传则为当前用户"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取用户头像 URL"""
    service = PhotoService(db)
    target_user_id = user_id or current_user.id
    avatar_url = service.get_avatar_url(target_user_id)
    return {"avatar_url": avatar_url}


@router.post("/ai-moderate/{photo_id}", response_model=PhotoResponse, summary="AI 自动审核照片")
async def ai_moderate_photo(
    photo_id: str,
    is_safe: bool = Form(..., description="是否安全"),
    ai_tags: Optional[str] = Form(default=None, description="AI 分析标签 JSON 字符串"),
    quality_score: Optional[float] = Form(default=None, description="质量评分"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    AI 自动审核照片

    - **is_safe**: 是否安全
    - **ai_tags**: AI 分析标签 (JSON 字符串)
    - **quality_score**: 质量评分
    """
    import json
    service = PhotoService(db)

    tags = json.loads(ai_tags) if ai_tags else None

    photo = service.ai_moderate_photo(
        photo_id=photo_id,
        is_safe=is_safe,
        ai_tags=tags,
        quality_score=quality_score
    )

    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在")

    return photo
