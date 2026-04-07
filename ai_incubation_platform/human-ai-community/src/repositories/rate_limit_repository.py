"""
速率限制配置 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBRateLimitConfig


class RateLimitRepository(BaseRepository[DBRateLimitConfig]):
    """速率限制配置 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBRateLimitConfig, db)

    async def get_by_resource(self, resource: str) -> List[DBRateLimitConfig]:
        """根据资源类型获取速率限制配置"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.resource == resource)
            .where(self.model.enabled == True)
        )
        return list(result.scalars().all())

    async def get_latest_by_resource(
        self, resource: str
    ) -> Optional[DBRateLimitConfig]:
        """根据资源类型获取最新的速率限制配置"""
        configs = await self.get_by_resource(resource)
        if configs:
            # 返回最新添加的配置
            return max(configs, key=lambda c: c.created_at)
        return None
