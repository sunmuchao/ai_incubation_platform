"""
内容审核 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBContentReview
from models.member import ContentType, ReviewStatus


class ReviewRepository(BaseRepository[DBContentReview]):
    """内容审核 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBContentReview, db)

    async def get_latest_review(
        self, content_type: ContentType, content_id: str
    ) -> Optional[DBContentReview]:
        """获取指定内容的最新审核记录"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.content_type == content_type)
            .where(self.model.content_id == content_id)
            .order_by(desc(self.model.submit_time))
        )
        return result.scalar_one_or_none()

    async def get_pending_reviews(self, limit: int = 100) -> List[DBContentReview]:
        """获取待审核内容列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.status == ReviewStatus.PENDING)
            .order_by(self.model.submit_time)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_review_queue(
        self, limit_pending: int = 50, limit_flagged: int = 50
    ) -> dict:
        """获取人工审核队列（pending/flagged 分组）"""
        pending_result = await self.db.execute(
            select(self.model)
            .where(self.model.status == ReviewStatus.PENDING)
            .order_by(self.model.submit_time)
            .limit(limit_pending)
        )
        flagged_result = await self.db.execute(
            select(self.model)
            .where(self.model.status == ReviewStatus.FLAGGED)
            .order_by(self.model.submit_time)
            .limit(limit_flagged)
        )

        return {
            "pending": list(pending_result.scalars().all()),
            "flagged": list(flagged_result.scalars().all()),
        }

    async def count_by_status(self, status: ReviewStatus) -> int:
        """统计某状态的审核记录数"""
        result = await self.db.execute(
            select(func.count()).select_from(self.model).where(self.model.status == status)
        )
        return result.scalar()

    async def list_by_author(self, author_id: str, limit: int = 100) -> List[DBContentReview]:
        """根据作者 ID 获取审核记录列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.author_id == author_id)
            .order_by(desc(self.model.submit_time))
            .limit(limit)
        )
        return list(result.scalars().all())
