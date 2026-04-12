"""
照片管理 API

P4 新增:
- 照片上传
- 照片审核
- 照片展示
- 照片验证机制
"""
import uuid
import os
import base64
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.photo_service import PhotoService
from utils.logger import logger

# 静态文件目录
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'static')
os.makedirs(STATIC_DIR, exist_ok=True)


router = APIRouter(prefix="/api/photos", tags=["照片管理"])


# ============= 常量配置 ====================
MAX_FILE_SIZE = 10 * 1024 * 1024  # 最大文件大小 10MB
MIN_FILE_SIZE = 100  # 最小文件大小 100 字节（拒绝空文件）
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "webp"]


def validate_file_upload(file: UploadFile, content: bytes) -> tuple[bool, str]:
    """
    验证上传文件

    Args:
        file: 上传的文件对象
        content: 文件内容

    Returns:
        (是否有效, 错误消息)

    Raises:
        HTTPException: 文件无效时抛出
    """
    # 1. 验证空文件
    if len(content) < MIN_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件太小或为空文件，请上传有效图片"
        )

    # 2. 验证文件大小上限
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制 {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    # 3. 验证文件类型
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}，仅支持 JPG/PNG/GIF/WEBP"
        )

    # 4. 验证文件扩展名
    if file.filename:
        ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件扩展名: {ext}"
            )

    # 5. 验证文件名安全（防止路径遍历攻击）
    if file.filename:
        safe_filename = file.filename.replace("/", "").replace("\\", "").replace("..", "")
        if safe_filename != file.filename:
            logger.warning(f"文件名包含危险字符，已清理: {file.filename} -> {safe_filename}")
            file.filename = safe_filename

    return True, ""


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


@router.post("/upload-file", summary="上传照片文件")
async def upload_photo_file(
    file: UploadFile = File(..., description="照片文件"),
    photo_type: str = Form(default="chat", description="照片类型"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    上传照片文件（用于聊天图片等场景）

    - **file**: 照片文件 (支持 jpg/png/gif/webp)
    - **photo_type**: 照片类型 (chat/profile/avatar/verification/lifestyle)
    """
    # 读取文件内容
    content = await file.read()

    # 使用统一的验证函数进行完整校验
    validate_file_upload(file, content)

    # 生成唯一文件名
    file_ext = file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'jpg'
    unique_filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{file_ext}"
    file_path = os.path.join(STATIC_DIR, unique_filename)

    # 保存文件
    try:
        with open(file_path, 'wb') as f:
            f.write(content)
        logger.info(f"Photo file saved: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save photo file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件保存失败"
        )

    # 生成 URL
    photo_url = f"/static/{unique_filename}"

    # 如果是 profile 类型，保存到照片服务
    if photo_type in ["profile", "avatar", "lifestyle"]:
        service = PhotoService(db)
        try:
            photo = service.upload_photo(
                user_id=current_user.id,
                photo_url=photo_url,
                photo_type=photo_type
            )
            return {
                "id": photo.id,
                "photo_url": photo_url,
                "photo_type": photo_type
            }
        except ValueError as e:
            # 清理文件
            os.remove(file_path)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # chat 类型直接返回 URL
    return {
        "id": uuid.uuid4().hex,
        "photo_url": photo_url,
        "photo_type": photo_type
    }


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
