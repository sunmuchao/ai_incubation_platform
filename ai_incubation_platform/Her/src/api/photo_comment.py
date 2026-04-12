"""
照片评论 API

参考 Hinge 的照片评论功能：
- 用户可以对照片发表评论
- AI 生成评论建议
- 评论作为破冰话题
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from db.database import get_db
from services.photo_comment_service import PhotoCommentService, get_photo_comment_service
from utils.logger import logger

router = APIRouter(prefix="/api/photo-comments", tags=["Photo Comments"])


class CreateCommentRequest(BaseModel):
    """创建评论请求"""
    photo_id: str
    photo_owner_id: str
    comment_content: str
    comment_type: str = "observation"  # observation/question/compliment/shared_interest/story
    position_x: Optional[float] = None
    position_y: Optional[float] = None


class CommentResponse(BaseModel):
    """评论响应"""
    comment_id: str
    photo_id: str
    user_id: str
    user_name: str
    user_avatar: Optional[str] = None
    comment_content: str
    comment_type: str
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    is_ai_generated: bool
    replies_count: int
    created_at: str


class CommentSuggestion(BaseModel):
    """评论建议"""
    comment_type: str
    comment_content: str
    expected_effect: str
    confidence: float
    photo_id: str
    is_ai_generated: bool


class ReplyRequest(BaseModel):
    """回复请求"""
    comment_id: str
    reply_content: str


@router.post("/create", response_model=Dict[str, Any])
async def create_comment(
    user_id: str,
    request: CreateCommentRequest,
    db: Session = Depends(get_db)
):
    """
    创建照片评论

    用户对照片发表评论，作为破冰话题
    """
    try:
        service = get_photo_comment_service(db)
        result = await service.create_comment(
            user_id=user_id,
            photo_id=request.photo_id,
            photo_owner_id=request.photo_owner_id,
            comment_content=request.comment_content,
            comment_type=request.comment_type,
            position_x=request.position_x,
            position_y=request.position_y
        )

        logger.info(f"Photo comment created: {result['comment_id']}")
        return result
    except Exception as e:
        logger.error(f"Failed to create photo comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/{photo_id}", response_model=List[CommentSuggestion])
async def get_comment_suggestions(
    photo_id: str,
    user_id: str,
    photo_description: str = Query(..., description="照片 AI 分析描述"),
    db: Session = Depends(get_db)
):
    """
    AI 生成评论建议

    帮助用户找到合适的照片评论切入点
    """
    try:
        service = get_photo_comment_service(db)
        suggestions = await service.generate_comment_suggestions(
            photo_id=photo_id,
            photo_description=photo_description,
            user_id=user_id
        )

        return suggestions
    except Exception as e:
        logger.error(f"Failed to generate comment suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/photo/{photo_id}", response_model=List[CommentResponse])
async def get_photo_comments(
    photo_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    获取照片的所有评论
    """
    try:
        service = get_photo_comment_service(db)
        comments = service.get_photo_comments(photo_id, limit)
        return comments
    except Exception as e:
        logger.error(f"Failed to get photo comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/received/{user_id}", response_model=List[CommentResponse])
async def get_received_comments(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    获取用户收到的照片评论

    查看别人对自己照片的评论
    """
    try:
        service = get_photo_comment_service(db)
        comments = service.get_user_photo_comments(user_id, limit)
        return comments
    except Exception as e:
        logger.error(f"Failed to get received comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reply")
async def reply_to_comment(
    user_id: str,
    request: ReplyRequest,
    db: Session = Depends(get_db)
):
    """
    回复照片评论
    """
    try:
        service = get_photo_comment_service(db)
        result = await service.reply_to_comment(
            comment_id=request.comment_id,
            user_id=user_id,
            reply_content=request.reply_content
        )
        return result
    except Exception as e:
        logger.error(f"Failed to reply to comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read/{comment_id}")
async def mark_comment_read(comment_id: str, db: Session = Depends(get_db)):
    """
    标记评论已读
    """
    try:
        service = get_photo_comment_service(db)
        success = service.mark_comment_read(comment_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to mark comment read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unread-count/{user_id}")
async def get_unread_comments_count(user_id: str, db: Session = Depends(get_db)):
    """
    获取未读评论数量
    """
    try:
        service = get_photo_comment_service(db)
        count = service.get_unread_comments_count(user_id)
        return {"unread_count": count}
    except Exception as e:
        logger.error(f"Failed to get unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_comment_types():
    """
    获取评论类型列表
    """
    return {
        "types": [
            {
                "name": "observation",
                "description": "观察 - 发现照片中的有趣细节",
                "icon": "🔍",
                "example": "照片里的那只猫看起来好可爱！"
            },
            {
                "name": "question",
                "description": "询问 - 提出问题引发讨论",
                "icon": "❓",
                "example": "这是在哪里拍的？风景真美！"
            },
            {
                "name": "compliment",
                "description": "赞美 - 对照片的正面评价",
                "icon": "👍",
                "example": "这张照片拍得太棒了！"
            },
            {
                "name": "shared_interest",
                "description": "共同兴趣 - 发现共同点",
                "icon": "💡",
                "example": "你也喜欢徒步吗？看起来我们兴趣相似！"
            },
            {
                "name": "story",
                "description": "故事 - 分享相关经历",
                "icon": "📖",
                "example": "看到这张照片想起了我也去过那里..."
            }
        ]
    }