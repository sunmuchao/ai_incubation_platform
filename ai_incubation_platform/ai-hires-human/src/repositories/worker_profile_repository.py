"""
工人画像Repository，封装工人能力画像相关的数据库操作。
"""
from typing import List, Optional, Dict

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import WorkerProfileDB
from repositories.base_repository import BaseRepository


class WorkerProfileRepository(BaseRepository[WorkerProfileDB]):
    """工人能力画像数据库操作类。"""

    def __init__(self, db: AsyncSession):
        super().__init__(WorkerProfileDB, db)

    async def get_by_worker_id(self, worker_id: str) -> Optional[WorkerProfileDB]:
        """根据工人ID获取画像。"""
        result = await self.db.execute(select(self.model).where(self.model.worker_id == worker_id))
        return result.scalar_one_or_none()

    async def search_by_skills(
        self,
        skills: List[str],
        location: Optional[str] = None,
        min_level: int = 0,
        min_rating: float = 0.0,
        skip: int = 0,
        limit: int = 100
    ) -> List[WorkerProfileDB]:
        """
        按技能搜索工人。
        """
        query = select(self.model)

        # 技能匹配
        if skills:
            conditions = []
            for skill in skills:
                skill_lower = skill.lower()
                conditions.append(
                    or_(
                        func.jsonb_exists(self.model.skills, skill_lower),
                        func.jsonb_each_text(self.model.skills).value.ilike(f"%{skill_lower}%"),
                        func.array_to_string(self.model.tags, ' ').ilike(f"%{skill_lower}%")
                    )
                )
            query = query.where(or_(*conditions))

        # 地点筛选
        if location:
            query = query.where(self.model.location.ilike(f"%{location}%"))

        # 等级筛选
        if min_level > 0:
            query = query.where(self.model.level >= min_level)

        # 评分筛选
        if min_rating > 0:
            query = query.where(self.model.average_rating >= min_rating)

        # 排序：按评分、完成任务数、等级综合排序
        query = query.order_by(
            self.model.average_rating.desc(),
            self.model.completed_tasks.desc(),
            self.model.level.desc()
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_task_statistics(
        self,
        worker_id: str,
        task_completed: bool = True,
        rating: Optional[float] = None,
        earnings: float = 0.0
    ) -> Optional[WorkerProfileDB]:
        """更新工人任务统计数据。"""
        profile = await self.get_by_worker_id(worker_id)
        if not profile:
            # 如果不存在则创建默认画像
            profile = WorkerProfileDB(
                worker_id=worker_id,
                completed_tasks=1 if task_completed else 0,
                success_rate=1.0 if task_completed else 0.0,
                average_rating=rating or 5.0,
                total_earnings=earnings
            )
            self.db.add(profile)
        else:
            profile.completed_tasks += 1 if task_completed else 0
            # 更新成功率
            total_tasks = profile.completed_tasks + (0 if task_completed else 1)
            profile.success_rate = profile.completed_tasks / max(total_tasks, 1)
            # 更新平均评分
            if rating is not None:
                profile.average_rating = (
                    (profile.average_rating * (profile.completed_tasks - 1) + rating)
                    / profile.completed_tasks
                )
            # 更新总收入
            profile.total_earnings += earnings

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def sync_external_profile(self, worker_id: str, external_data: Dict) -> WorkerProfileDB:
        """同步外部系统的工人画像数据。"""
        profile = await self.get_by_worker_id(worker_id)
        if not profile:
            profile = WorkerProfileDB(worker_id=worker_id)
            self.db.add(profile)

        # 更新字段
        if "name" in external_data:
            profile.name = external_data["name"]
        if "avatar" in external_data:
            profile.avatar = external_data["avatar"]
        if "phone" in external_data:
            profile.phone = external_data["phone"]
        if "email" in external_data:
            profile.email = external_data["email"]
        if "location" in external_data:
            profile.location = external_data["location"]
        if "skills" in external_data:
            profile.skills = external_data["skills"]
        if "level" in external_data:
            profile.level = external_data["level"]
        if "tags" in external_data:
            profile.tags = external_data["tags"]
        if "external_profile_id" in external_data:
            profile.external_profile_id = external_data["external_profile_id"]
        if "metadata" in external_data:
            profile.metadata.update(external_data["metadata"])

        await self.db.commit()
        await self.db.refresh(profile)
        return profile
