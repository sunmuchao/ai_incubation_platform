"""
视频片段 API

参考 Tinder 的视频片段功能：
- 用户录制短视频自我介绍
- 视频作为匹配资料的一部分
- AI 分析视频内容
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from db.database import get_db
from services.video_clip_service import VideoClipService, get_video_clip_service
from utils.logger import logger

router = APIRouter(prefix="/api/video-clips", tags=["Video Clips"])


class VideoUploadRequest(BaseModel):
    """视频上传请求"""
    video_duration: float
    video_description: Optional[str] = None


class VideoResponse(BaseModel):
    """视频响应"""
    video_id: str
    user_id: str
    video_url: str
    video_thumbnail: Optional[str] = None
    video_duration: float
    video_description: Optional[str] = None
    is_primary: bool
    view_count: int
    created_at: str


class VideoIntroSuggestion(BaseModel):
    """视频介绍建议"""
    style: str
    outline: str
    filming_tips: str
    expected_effect: str


@router.post("/upload")
async def upload_video(
    user_id: str,
    video: UploadFile = File(...),
    video_duration: float = Query(..., ge=1, le=30),
    video_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    上传视频片段

    支持的视频格式：mp4, mov, webm, avi
    最大时长：30秒
    最大文件大小：50MB
    """
    try:
        # 检查文件格式
        file_ext = video.filename.split('.')[-1].lower()
        allowed_formats = ["mp4", "mov", "webm", "avi"]
        if file_ext not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的视频格式，允许: {allowed_formats}"
            )

        # 保存文件（临时）
        import os
        import uuid
        temp_dir = "/tmp/video_clips"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = f"{temp_dir}/{uuid.uuid4()}.{file_ext}"

        with open(file_path, "wb") as f:
            content = await video.read()
            f.write(content)

        # 上传处理
        service = get_video_clip_service(db)
        result = await service.upload_video(
            user_id=user_id,
            video_file_path=file_path,
            video_duration=video_duration,
            video_description=video_description
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=List[VideoResponse])
async def get_user_videos(
    user_id: str,
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    获取用户的视频片段列表
    """
    try:
        service = get_video_clip_service(db)
        videos = service.get_user_videos(user_id, limit)
        return videos
    except Exception as e:
        logger.error(f"Failed to get user videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/primary/{user_id}", response_model=Optional[VideoResponse])
async def get_primary_video(user_id: str, db: Session = Depends(get_db)):
    """
    获取用户的主要视频
    """
    try:
        service = get_video_clip_service(db)
        video = service.get_primary_video(user_id)
        return video
    except Exception as e:
        logger.error(f"Failed to get primary video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set-primary")
async def set_primary_video(
    user_id: str,
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    设置主要视频
    """
    try:
        service = get_video_clip_service(db)
        success = service.set_primary_video(user_id, video_id)
        if success:
            return {"success": True, "message": "主要视频已设置"}
        else:
            return {"success": False, "message": "视频不存在"}
    except Exception as e:
        logger.error(f"Failed to set primary video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{video_id}")
async def delete_video(
    user_id: str,
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    删除视频
    """
    try:
        service = get_video_clip_service(db)
        success = service.delete_video(user_id, video_id)
        if success:
            return {"success": True, "message": "视频已删除"}
        else:
            return {"success": False, "message": "视频不存在"}
    except Exception as e:
        logger.error(f"Failed to delete video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/view/{video_id}")
async def increment_view_count(video_id: str, db: Session = Depends(get_db)):
    """
    增加视频观看次数
    """
    try:
        service = get_video_clip_service(db)
        count = service.increment_view_count(video_id)
        return {"view_count": count}
    except Exception as e:
        logger.error(f"Failed to increment view count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intro-suggestions/{user_id}", response_model=List[VideoIntroSuggestion])
async def get_intro_suggestions(user_id: str, db: Session = Depends(get_db)):
    """
    AI 生成视频介绍建议

    帮助用户录制更好的自我介绍视频
    """
    try:
        # 获取用户资料
        from db.models import UserDB
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        user_profile = {
            "age": user.age,
            "interests": user.interests,
            "bio": user.bio,
            "goal": user.goal
        }

        service = get_video_clip_service(db)
        suggestions = await service.generate_video_intro_suggestions(user_profile)
        return suggestions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get intro suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_video_config():
    """
    获取视频配置信息
    """
    return {
        "max_duration": 30,  # 最大时长（秒）
        "max_size": 50,  # 最大文件大小（MB）
        "allowed_formats": ["mp4", "mov", "webm", "avi"],
        "recommended_duration": 15,  # 推荐时长
        "tips": [
            "选择光线充足的环境",
            "保持微笑，自然表达",
            "介绍你的兴趣爱好",
            "时长建议 15-30 秒",
            "避免背景噪音"
        ]
    }