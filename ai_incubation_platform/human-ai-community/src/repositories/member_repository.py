"""
成员 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBCommunityMember
from models.member import MemberType, MemberRole


class MemberRepository(BaseRepository[DBCommunityMember]):
    """成员 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBCommunityMember, db)

    async def get_by_email(self, email: str) -> Optional[DBCommunityMember]:
        """根据邮箱获取成员"""
        return await self.get_by_field("email", email)

    async def get_ai_members(self) -> List[DBCommunityMember]:
        """获取所有 AI 成员"""
        result = await self.db.execute(
            select(self.model).where(self.model.member_type == MemberType.AI)
        )
        return list(result.scalars().all())

    async def get_human_members(self) -> List[DBCommunityMember]:
        """获取所有人类成员"""
        result = await self.db.execute(
            select(self.model).where(self.model.member_type == MemberType.HUMAN)
        )
        return list(result.scalars().all())

    async def get_by_role(self, role: MemberRole) -> List[DBCommunityMember]:
        """根据角色获取成员"""
        result = await self.db.execute(
            select(self.model).where(self.model.role == role)
        )
        return list(result.scalars().all())

    async def increment_post_count(self, member_id: str) -> Optional[DBCommunityMember]:
        """增加成员发帖数"""
        member = await self.get(member_id)
        if member:
            member.post_count += 1
            await self.db.flush()
            await self.db.refresh(member)
        return member
