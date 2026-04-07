"""
审核规则 Repository
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.base import BaseRepository
from db.models import DBReviewRule


class ReviewRuleRepository(BaseRepository[DBReviewRule]):
    """审核规则 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBReviewRule, db)

    async def list_enabled_rules(self) -> List[DBReviewRule]:
        """获取所有启用的审核规则"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.enabled == True)
        )
        return list(result.scalars().all())

    async def list_all_rules(self) -> List[DBReviewRule]:
        """获取所有审核规则（含启用/禁用）"""
        result = await self.db.execute(select(self.model))
        return list(result.scalars().all())

    async def set_rule_enabled(self, rule_id: str, enabled: bool) -> Optional[DBReviewRule]:
        """设置规则启用/禁用状态"""
        rule = await self.get(rule_id)
        if rule:
            rule.enabled = enabled
            from datetime import datetime
            rule.updated_at = datetime.now()
            await self.db.flush()
            await self.db.refresh(rule)
        return rule

    async def list_by_type(self, rule_type: str) -> List[DBReviewRule]:
        """根据规则类型获取规则列表"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.rule_type == rule_type)
        )
        return list(result.scalars().all())
