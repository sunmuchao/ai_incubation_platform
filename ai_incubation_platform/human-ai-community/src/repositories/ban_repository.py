"""
封禁记录 Repository
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBBanRecord
from models.member import BanStatus


class BanRepository(BaseRepository[DBBanRecord]):
    """封禁记录 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBBanRecord, db)

    async def list_by_user(self, user_id: str) -> List[DBBanRecord]:
        """获取用户的封禁记录"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(desc(self.model.created_at))
        )
        return list(result.scalars().all())

    async def get_active_bans(self, user_id: str) -> List[DBBanRecord]:
        """获取用户当前生效的封禁记录"""
        now = datetime.now()
        result = await self.db.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.status == BanStatus.ACTIVE)
            .where(
                (self.model.expire_time.is_(None)) | (self.model.expire_time > now)
            )
            .order_by(desc(self.model.created_at))
        )
        return list(result.scalars().all())

    async def is_user_banned(
        self, user_id: str, ban_type: str = "all"
    ) -> bool:
        """检查用户是否被封禁"""
        now = datetime.now()
        query = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.status == BanStatus.ACTIVE)
            .where(
                (self.model.expire_time.is_(None)) | (self.model.expire_time > now)
            )
        )
        if ban_type != "all":
            query = query.where(
                (self.model.ban_type == ban_type) | (self.model.ban_type == "all")
            )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def lift_ban(self, ban_id: str) -> Optional[DBBanRecord]:
        """解除封禁"""
        ban = await self.get(ban_id)
        if ban:
            ban.status = BanStatus.LIFTED
            ban.lifted_at = datetime.now()
            await self.db.flush()
            await self.db.refresh(ban)
        return ban
