"""
AI Agent 调用记录 Repository
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBAgentCallRecord


class AgentCallRepository(BaseRepository[DBAgentCallRecord]):
    """AI Agent 调用记录 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBAgentCallRecord, db)

    async def list_by_agent(
        self, agent_name: str, limit: int = 50
    ) -> List[DBAgentCallRecord]:
        """根据 Agent 名称获取调用记录"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.agent_name == agent_name)
            .order_by(desc(self.model.call_time))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_action(
        self, action: str, limit: int = 50
    ) -> List[DBAgentCallRecord]:
        """根据动作类型获取调用记录"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.action == action)
            .order_by(desc(self.model.call_time))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> List[DBAgentCallRecord]:
        """根据时间范围获取调用记录"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.call_time >= start_time)
            .where(self.model.call_time <= end_time)
            .order_by(desc(self.model.call_time))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 50) -> List[DBAgentCallRecord]:
        """获取最近的调用记录"""
        result = await self.db.execute(
            select(self.model)
            .order_by(desc(self.model.call_time))
            .limit(limit)
        )
        return list(result.scalars().all())
