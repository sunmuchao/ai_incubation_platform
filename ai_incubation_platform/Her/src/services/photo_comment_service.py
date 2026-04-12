"""
照片评论服务

参考 Hinge 的照片评论功能：
- 用户可以对对方照片发表评论
- 评论作为破冰话题，更容易开始对话
- AI 可生成评论提示，帮助用户表达
- 评论可以获得对方的回复
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from utils.logger import logger
from services.base_service import BaseService


class PhotoCommentService(BaseService):
    """照片评论服务"""

    # 评论类型
    COMMENT_TYPES = [
        "observation",   # 观察 - 发现照片中的有趣细节
        "question",      # 询问 - 提出问题引发讨论
        "compliment",    # 赞美 - 对照片的正面评价
        "shared_interest",  # 共同兴趣 - 发现共同点
        "story",         # 故事 - 分享相关经历
        "ai_suggested",  # AI 建议 - AI 生成的评论
    ]

    def __init__(self, db: Session):
        super().__init__(db)
        self.db = db

    async def create_comment(
        self,
        user_id: str,
        photo_id: str,
        photo_owner_id: str,
        comment_content: str,
        comment_type: str = "observation",
        position_x: Optional[float] = None,  # 评论位置（照片上的坐标）
        position_y: Optional[float] = None,
        is_ai_generated: bool = False
    ) -> Dict[str, Any]:
        """
        创建照片评论

        Args:
            user_id: 评论者 ID
            photo_id: 照片 ID
            photo_owner_id: 照片主人 ID
            comment_content: 评论内容
            comment_type: 评论类型
            position_x: 照片上的 X 坐标（可选）
            position_y: 照片上的 Y 坐标（可选）
            is_ai_generated: 是否为 AI 生成的评论

        Returns:
            评论详情
        """
        from models.photo_comment import PhotoCommentDB

        comment_id = str(uuid.uuid4())

        # 创建评论记录
        comment = PhotoCommentDB(
            id=comment_id,
            user_id=user_id,
            photo_id=photo_id,
            photo_owner_id=photo_owner_id,
            comment_content=comment_content,
            comment_type=comment_type,
            position_x=position_x,
            position_y=position_y,
            is_ai_generated=is_ai_generated,
            created_at=datetime.now()
        )
        self.db.add(comment)
        self.db.commit()

        logger.info(f"Photo comment created: {comment_id} by user {user_id} on photo {photo_id}")

        return {
            "comment_id": comment_id,
            "photo_id": photo_id,
            "user_id": user_id,
            "photo_owner_id": photo_owner_id,
            "comment_content": comment_content,
            "comment_type": comment_type,
            "position_x": position_x,
            "position_y": position_y,
            "is_ai_generated": is_ai_generated,
            "created_at": datetime.now().isoformat()
        }

    async def generate_comment_suggestions(
        self,
        photo_id: str,
        photo_description: str,
        user_id: str,
        photo_owner_profile: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        AI 生成评论建议

        帮助用户找到合适的照片评论切入点

        Args:
            photo_id: 照片 ID
            photo_description: 照片描述（AI 分析结果）
            user_id: 当前用户 ID
            photo_owner_profile: 照片主人的资料

        Returns:
            评论建议列表
        """
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        # 构建上下文
        context = f"照片描述：{photo_description}\n"
        if photo_owner_profile:
            context += f"照片主人兴趣：{photo_owner_profile.get('interests', [])}\n"
            context += f"照片主人简介：{photo_owner_profile.get('bio', '')}\n"

        prompt = f"""请为这张照片生成 3-5 个合适的评论建议，作为破冰话题：

{context}

要求：
1. 评论要自然、真诚，不要太正式
2. 评论要能引发对话，不要只是赞美
3. 每个评论要标注类型：observation/question/compliment/shared_interest
4. 给出每个评论的预期效果

回复格式：
[
  {
    "comment_type": "observation",
    "comment_content": "评论内容",
    "expected_effect": "预期效果",
    "confidence": 0.85
  },
  ...
]"""

        try:
            result = await llm_service.generate(prompt)
            import json
            suggestions = json.loads(result)

            # 添加标记
            for s in suggestions:
                s["photo_id"] = photo_id
                s["is_ai_generated"] = True

            return suggestions
        except Exception as e:
            logger.error(f"Failed to generate comment suggestions: {e}")
            # 返回默认建议
            return [
                {
                    "comment_type": "question",
                    "comment_content": "这张照片是在哪里拍的？看起来很棒！",
                    "expected_effect": "引发地点讨论",
                    "confidence": 0.7,
                    "photo_id": photo_id,
                    "is_ai_generated": True
                },
                {
                    "comment_type": "observation",
                    "comment_content": "照片里的风景真美，你也喜欢户外吗？",
                    "expected_effect": "发现共同兴趣",
                    "confidence": 0.7,
                    "photo_id": photo_id,
                    "is_ai_generated": True
                }
            ]

    def get_photo_comments(
        self,
        photo_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取照片的所有评论

        Args:
            photo_id: 照片 ID
            limit: 返回数量限制

        Returns:
            评论列表
        """
        from models.photo_comment import PhotoCommentDB
        from db.models import UserDB

        comments = self.db.query(PhotoCommentDB).filter(
            PhotoCommentDB.photo_id == photo_id
        ).order_by(desc(PhotoCommentDB.created_at)).limit(limit).all()

        # 补充用户信息
        result = []
        for comment in comments:
            user = self.db.query(UserDB).filter(UserDB.id == comment.user_id).first()
            result.append({
                "comment_id": comment.id,
                "photo_id": comment.photo_id,
                "user_id": comment.user_id,
                "user_name": user.name if user else "用户",
                "user_avatar": user.avatar_url if user else None,
                "comment_content": comment.comment_content,
                "comment_type": comment.comment_type,
                "position_x": comment.position_x,
                "position_y": comment.position_y,
                "is_ai_generated": comment.is_ai_generated,
                "replies_count": 0,  # 评论回复功能待后续迭代，当前返回 0
                "created_at": comment.created_at.isoformat()
            })

        return result

    def get_user_photo_comments(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户收到的照片评论

        查看别人对自己照片的评论

        Args:
            user_id: 用户 ID（照片主人）
            limit: 返回数量限制

        Returns:
            评论列表
        """
        from models.photo_comment import PhotoCommentDB
        from db.models import UserDB

        comments = self.db.query(PhotoCommentDB).filter(
            PhotoCommentDB.photo_owner_id == user_id
        ).order_by(desc(PhotoCommentDB.created_at)).limit(limit).all()

        result = []
        for comment in comments:
            user = self.db.query(UserDB).filter(UserDB.id == comment.user_id).first()
            result.append({
                "comment_id": comment.id,
                "photo_id": comment.photo_id,
                "user_id": comment.user_id,
                "user_name": user.name if user else "用户",
                "user_avatar": user.avatar_url if user else None,
                "comment_content": comment.comment_content,
                "comment_type": comment.comment_type,
                "is_ai_generated": comment.is_ai_generated,
                "is_read": comment.is_read,
                "created_at": comment.created_at.isoformat()
            })

        return result

    def mark_comment_read(self, comment_id: str) -> bool:
        """标记评论已读"""
        from models.photo_comment import PhotoCommentDB

        comment = self.db.query(PhotoCommentDB).filter(
            PhotoCommentDB.id == comment_id
        ).first()

        if comment:
            comment.is_read = True
            self.db.commit()
            return True

        return False

    def get_unread_comments_count(self, user_id: str) -> int:
        """获取未读评论数量"""
        from models.photo_comment import PhotoCommentDB

        count = self.db.query(PhotoCommentDB).filter(
            PhotoCommentDB.photo_owner_id == user_id,
            PhotoCommentDB.is_read == False
        ).count()

        return count

    async def reply_to_comment(
        self,
        comment_id: str,
        user_id: str,
        reply_content: str
    ) -> Dict[str, Any]:
        """
        回复照片评论

        Args:
            comment_id: 原评论 ID
            user_id: 回复者 ID（照片主人）
            reply_content: 回复内容

        Returns:
            回复详情
        """
        from models.photo_comment import PhotoCommentReplyDB

        reply_id = str(uuid.uuid4())

        reply = PhotoCommentReplyDB(
            id=reply_id,
            comment_id=comment_id,
            user_id=user_id,
            reply_content=reply_content,
            created_at=datetime.now()
        )
        self.db.add(reply)
        self.db.commit()

        return {
            "reply_id": reply_id,
            "comment_id": comment_id,
            "user_id": user_id,
            "reply_content": reply_content,
            "created_at": datetime.now().isoformat()
        }


# 服务工厂函数
def get_photo_comment_service(db: Session) -> PhotoCommentService:
    """获取照片评论服务实例"""
    return PhotoCommentService(db)