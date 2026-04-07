"""
用户反馈服务中心层 - v1.22 用户体验优化

提供用户反馈功能的核心业务逻辑
"""
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import logging
import json

from sqlalchemy import select, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.ux_feedback import UserFeedbackDB, FeedbackCategoryDB

logger = logging.getLogger(__name__)


# ==================== 反馈服务 ====================

class FeedbackService:
    """用户反馈服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_feedback(
        self,
        user_id: str,
        feedback_type: str,
        title: str,
        description: str,
        category: Optional[str] = None,
        screenshots: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        contact_info: Optional[str] = None
    ) -> UserFeedbackDB:
        """创建用户反馈"""
        # 验证反馈类型
        valid_types = ['bug', 'feature', 'complaint', 'compliment', 'other']
        if feedback_type not in valid_types:
            raise ValueError(f"无效的反馈类型：{feedback_type}，必须是 {valid_types}")

        # 处理截图和附件
        screenshots_json = json.dumps(screenshots) if screenshots else None
        attachments_json = json.dumps(attachments) if attachments else None

        feedback = UserFeedbackDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            feedback_type=feedback_type,
            category=category,
            title=title,
            description=description,
            screenshots=screenshots_json,
            attachments=attachments_json,
            contact_info=contact_info,
        )

        self.db.add(feedback)
        await self.db.flush()

        logger.info(f"用户 {user_id} 创建了反馈：{feedback_type} - {title}")

        return feedback

    async def get_user_feedback(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[UserFeedbackDB]:
        """获取用户反馈列表"""
        query = select(UserFeedbackDB).where(UserFeedbackDB.user_id == user_id)

        if status_filter:
            query = query.where(UserFeedbackDB.status == status_filter)

        if type_filter:
            query = query.where(UserFeedbackDB.feedback_type == type_filter)

        query = query.order_by(desc(UserFeedbackDB.created_at)).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_feedback_details(self, feedback_id: str) -> Optional[UserFeedbackDB]:
        """获取反馈详情"""
        result = await self.db.execute(
            select(UserFeedbackDB).where(UserFeedbackDB.id == feedback_id)
        )
        return result.scalar_one_or_none()

    async def update_feedback(
        self,
        feedback_id: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        screenshots: Optional[List[str]] = None,
        contact_info: Optional[str] = None
    ) -> UserFeedbackDB:
        """更新反馈（用户补充信息）"""
        feedback = await self.get_feedback_details(feedback_id)

        if not feedback:
            raise ValueError(f"反馈不存在：{feedback_id}")

        if feedback.user_id != user_id:
            raise ValueError(f"无权修改此反馈")

        if title:
            feedback.title = title
        if description:
            feedback.description = description
        if screenshots is not None:
            feedback.screenshots = json.dumps(screenshots)
        if contact_info is not None:
            feedback.contact_info = contact_info

        feedback.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"用户 {user_id} 更新了反馈 {feedback_id}")

        return feedback

    async def update_feedback_status(
        self,
        feedback_id: str,
        status: str,
        response: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
        internal_notes: Optional[str] = None
    ) -> UserFeedbackDB:
        """更新反馈状态（管理员操作）"""
        valid_statuses = ['pending', 'investigated', 'resolved', 'rejected']
        if status not in valid_statuses:
            raise ValueError(f"无效的状态：{status}，必须是 {valid_statuses}")

        feedback = await self.get_feedback_details(feedback_id)

        if not feedback:
            raise ValueError(f"反馈不存在：{feedback_id}")

        feedback.status = status

        if priority:
            feedback.priority = priority
        if assigned_to:
            feedback.assigned_to = assigned_to
        if internal_notes:
            feedback.internal_notes = internal_notes
        if response:
            feedback.response = response
            feedback.responded_at = datetime.utcnow()

        if status == 'resolved':
            feedback.resolved_at = datetime.utcnow()

        feedback.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"反馈 {feedback_id} 状态更新为：{status}")

        return feedback

    async def get_feedback_categories(self) -> List[FeedbackCategoryDB]:
        """获取反馈分类列表"""
        result = await self.db.execute(
            select(FeedbackCategoryDB)
            .where(FeedbackCategoryDB.is_active == True)
            .order_by(FeedbackCategoryDB.sort_order)
        )
        return list(result.scalars().all())

    async def get_feedback_stats(self) -> Dict:
        """获取反馈统计信息"""
        # 按类型统计
        type_result = await self.db.execute(
            select(
                UserFeedbackDB.feedback_type,
                func.count(UserFeedbackDB.id)
            )
            .group_by(UserFeedbackDB.feedback_type)
        )
        type_stats = dict(type_result.all())

        # 按状态统计
        status_result = await self.db.execute(
            select(
                UserFeedbackDB.status,
                func.count(UserFeedbackDB.id)
            )
            .group_by(UserFeedbackDB.status)
        )
        status_stats = dict(status_result.all())

        # 总数
        total_result = await self.db.execute(
            select(func.count(UserFeedbackDB.id))
        )
        total = total_result.scalar_one()

        # 待处理数量
        pending_result = await self.db.execute(
            select(func.count(UserFeedbackDB.id)).where(UserFeedbackDB.status == 'pending')
        )
        pending = pending_result.scalar_one()

        return {
            "total": total,
            "pending": pending,
            "by_type": type_stats,
            "by_status": status_stats,
        }

    async def submit_satisfaction_rating(
        self,
        feedback_id: str,
        user_id: str,
        rating: int,
        comment: Optional[str] = None
    ) -> UserFeedbackDB:
        """提交满意度评分"""
        feedback = await self.get_feedback_details(feedback_id)

        if not feedback:
            raise ValueError(f"反馈不存在：{feedback_id}")

        if feedback.user_id != user_id:
            raise ValueError(f"无权评价此反馈")

        if feedback.status != 'resolved':
            raise ValueError(f"反馈尚未解决，无法评价")

        if not 1 <= rating <= 5:
            raise ValueError(f"评分必须在 1-5 之间")

        feedback.satisfaction_rating = rating
        feedback.satisfaction_comment = comment
        feedback.updated_at = datetime.utcnow()

        await self.db.flush()

        logger.info(f"用户 {user_id} 对反馈 {feedback_id} 评分：{rating}")

        return feedback


# ==================== 依赖注入 ====================

def get_feedback_service(db: AsyncSession) -> FeedbackService:
    """获取反馈服务实例"""
    return FeedbackService(db)
