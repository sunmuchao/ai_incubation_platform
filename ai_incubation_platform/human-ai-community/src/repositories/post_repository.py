"""
帖子 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBPost
from models.member import MemberType


class PostRepository(BaseRepository[DBPost]):
    """帖子 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBPost, db)

    async def list_by_author(self, author_id: str, limit: int = 50) -> List[DBPost]:
        """根据作者 ID 获取帖子列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.author_id == author_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_author_type(self, author_type: MemberType, limit: int = 50) -> List[DBPost]:
        """根据作者类型获取帖子列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.author_type == author_type)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 50) -> List[DBPost]:
        """获取最新的帖子列表"""
        result = await self.db.execute(
            select(self.model)
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_visible_posts(self, visible_content_ids: set, limit: int = 50) -> List[DBPost]:
        """获取可见的帖子列表（通过审核的内容）"""
        if not visible_content_ids:
            return []
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id.in_(visible_content_ids))
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_posts_for_review_check(self) -> List[DBPost]:
        """获取所有帖子（用于审核检查，内部使用）"""
        result = await self.db.execute(select(self.model))
        return list(result.scalars().all())
