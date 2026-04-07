"""
评论 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBComment
from models.member import MemberType


class CommentRepository(BaseRepository[DBComment]):
    """评论 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBComment, db)

    async def list_by_post(self, post_id: str) -> List[DBComment]:
        """获取帖子的所有评论"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.post_id == post_id)
            .order_by(self.model.created_at)
        )
        return list(result.scalars().all())

    async def list_by_post_and_author_type(
        self, post_id: str, author_type: MemberType
    ) -> List[DBComment]:
        """根据帖子 ID 和作者类型获取评论"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.post_id == post_id)
            .where(self.model.author_type == author_type)
            .order_by(self.model.created_at)
        )
        return list(result.scalars().all())

    async def list_replies(self, parent_id: str) -> List[DBComment]:
        """获取评论的回复"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.parent_id == parent_id)
            .order_by(self.model.created_at)
        )
        return list(result.scalars().all())

    async def list_by_author(self, author_id: str, limit: int = 50) -> List[DBComment]:
        """根据作者 ID 获取评论列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.author_id == author_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_visible_comments(
        self, post_id: str, visible_content_ids: set
    ) -> List[DBComment]:
        """获取可见的评论列表"""
        if not visible_content_ids:
            return []
        result = await self.db.execute(
            select(self.model)
            .where(self.model.post_id == post_id)
            .where(self.model.id.in_(visible_content_ids))
            .order_by(self.model.created_at)
        )
        return list(result.scalars().all())

    async def get_all_comments_for_review_check(self) -> List[DBComment]:
        """获取所有评论（用于审核检查，内部使用）"""
        result = await self.db.execute(select(self.model))
        return list(result.scalars().all())
