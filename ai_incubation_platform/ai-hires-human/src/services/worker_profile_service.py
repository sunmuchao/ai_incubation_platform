"""
工人能力画像服务。
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from models.worker_profile import (
    WorkerProfile,
    WorkerProfileCreate,
    WorkerProfileUpdate,
    WorkerStats,
)
from models.task import TaskStatus


class WorkerProfileService:
    """
    工人能力画像服务（内存存储实现）。
    提供工人画像的 CRUD、搜索、统计等功能。
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, WorkerProfile] = {}
        # 模拟任务数据用于统计
        self._task_history: Dict[str, List[Dict]] = {}  # worker_id -> [task_history]

    def reset_state(self) -> None:
        """重置内存状态（用于测试）。"""
        self._profiles.clear()
        self._task_history.clear()

    def create_profile(self, data: WorkerProfileCreate) -> WorkerProfile:
        """创建工人画像。"""
        now = datetime.now()
        profile = WorkerProfile(
            worker_id=data.worker_id,
            name=data.name,
            avatar=data.avatar,
            phone=data.phone,
            email=data.email,
            location=data.location,
            skills=data.skills,
            level=data.level,
            tags=data.tags,
            external_profile_id=data.external_profile_id,
            created_at=now,
            updated_at=now,
        )
        self._profiles[data.worker_id] = profile
        return profile

    def get_profile(self, worker_id: str) -> Optional[WorkerProfile]:
        """获取工人画像。"""
        return self._profiles.get(worker_id)

    def update_profile(self, worker_id: str, data: WorkerProfileUpdate) -> Optional[WorkerProfile]:
        """更新工人画像。"""
        profile = self._profiles.get(worker_id)
        if not profile:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(profile, field) and value is not None:
                setattr(profile, field, value)

        profile.updated_at = datetime.now()
        return profile

    def delete_profile(self, worker_id: str) -> bool:
        """删除工人画像。"""
        if worker_id in self._profiles:
            del self._profiles[worker_id]
            return True
        return False

    def search_profiles(
        self,
        skills: Optional[List[str]] = None,
        location: Optional[str] = None,
        min_level: int = 0,
        min_rating: float = 0.0,
        min_success_rate: float = 0.0,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkerProfile]:
        """
        搜索工人画像。
        支持技能、地点、等级、评分、成功率等筛选条件。
        """
        results = []
        for profile in self._profiles.values():
            # 技能匹配
            if skills:
                profile_skills_lower = {k.lower(): v.lower() for k, v in profile.skills.items()}
                profile_tags_lower = [t.lower() for t in profile.tags]
                skill_match = False
                for skill in skills:
                    skill_lower = skill.lower()
                    if skill_lower in profile_skills_lower or skill_lower in profile_tags_lower:
                        skill_match = True
                        break
                if not skill_match:
                    continue

            # 地点匹配（模糊）
            if location and profile.location:
                if location.lower() not in profile.location.lower():
                    continue

            # 等级筛选
            if min_level > 0 and profile.level < min_level:
                continue

            # 评分筛选
            if min_rating > 0 and profile.average_rating < min_rating:
                continue

            # 成功率筛选
            if min_success_rate > 0 and profile.success_rate < min_success_rate:
                continue

            results.append(profile)

        # 排序：综合评分、完成任务数、等级
        results.sort(key=lambda p: (p.average_rating, p.completed_tasks, p.level), reverse=True)

        # 分页
        return results[skip:skip + limit]

    def list_profiles(self, skip: int = 0, limit: int = 100) -> List[WorkerProfile]:
        """列出所有工人画像。"""
        profiles = list(self._profiles.values())
        profiles.sort(key=lambda p: p.created_at or datetime.min, reverse=True)
        return profiles[skip:skip + limit]

    def list_all_workers(self) -> List[WorkerProfile]:
        """列出所有工人画像（不限数量）。"""
        return list(self._profiles.values())

    def record_task_completion(
        self,
        worker_id: str,
        task_id: str,
        reward: float,
        rating: Optional[float] = None,
        success: bool = True,
    ) -> Optional[WorkerProfile]:
        """
        记录任务完成，更新工人画像统计。
        """
        profile = self._profiles.get(worker_id)
        if not profile:
            return None

        # 更新完成任务数
        profile.completed_tasks += 1

        # 更新总收入
        profile.total_earnings += reward

        # 更新平均评分
        if rating is not None:
            old_total = profile.average_rating * (profile.completed_tasks - 1)
            profile.average_rating = (old_total + rating) / profile.completed_tasks

        # 更新成功率
        total_tasks = len(self._task_history.get(worker_id, [])) + 1
        success_count = sum(1 for h in self._task_history.get(worker_id, []) if h.get('success', True))
        success_count += 1 if success else 0
        profile.success_rate = success_count / total_tasks if total_tasks > 0 else 1.0

        # 更新等级（简单规则：每完成 10 个任务升 1 级）
        profile.level = 1 + profile.completed_tasks // 10

        # 记录历史
        if worker_id not in self._task_history:
            self._task_history[worker_id] = []
        self._task_history[worker_id].append({
            'task_id': task_id,
            'reward': reward,
            'rating': rating,
            'success': success,
            'completed_at': datetime.now().isoformat(),
        })

        profile.updated_at = datetime.now()
        return profile

    def get_worker_stats(self, worker_id: str) -> WorkerStats:
        """
        获取工人统计数据。
        """
        profile = self._profiles.get(worker_id)
        history = self._task_history.get(worker_id, [])

        # 计算统计数据
        completed = len([h for h in history if h.get('success', True)])
        total = len(history)
        success_count = sum(1 for h in history if h.get('success', True))

        # 最近任务
        recent = sorted(history, key=lambda x: x.get('completed_at', ''), reverse=True)[:5]

        return WorkerStats(
            worker_id=worker_id,
            total_tasks=total,
            completed_tasks=completed,
            in_progress_tasks=0,  # 需要从任务服务获取实时数据
            success_rate=success_count / total if total > 0 else 0.0,
            average_rating=profile.average_rating if profile else 0.0,
            total_earnings=profile.total_earnings if profile else 0.0,
            recent_tasks=recent,
        )

    def sync_from_external(self, worker_id: str, external_data: Dict) -> WorkerProfile:
        """
        从外部系统同步工人画像数据。
        """
        profile = self._profiles.get(worker_id)
        if not profile:
            # 创建新画像
            profile_data = WorkerProfileCreate(
                worker_id=worker_id,
                name=external_data.get('name'),
                avatar=external_data.get('avatar'),
                location=external_data.get('location'),
                skills=external_data.get('skills', {}),
                tags=external_data.get('tags', []),
                external_profile_id=external_data.get('external_profile_id'),
            )
            profile = self.create_profile(profile_data)
        else:
            # 更新现有画像
            update_data = WorkerProfileUpdate()
            if 'name' in external_data:
                update_data.name = external_data['name']
            if 'avatar' in external_data:
                update_data.avatar = external_data['avatar']
            if 'location' in external_data:
                update_data.location = external_data['location']
            if 'skills' in external_data:
                update_data.skills = external_data['skills']
            if 'tags' in external_data:
                update_data.tags = external_data['tags']
            if 'external_profile_id' in external_data:
                update_data.external_profile_id = external_data['external_profile_id']
            profile = self.update_profile(worker_id, update_data)

        return profile


worker_profile_service = WorkerProfileService()
