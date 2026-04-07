"""
新手引导服务中心层 - v1.22 用户体验优化

提供新手引导流程的核心业务逻辑
"""
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import logging
import json

from sqlalchemy import select, desc, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.ux_onboarding import (
    UserOnboardingProgressDB,
    OnboardingStepDefinitionDB,
    UserBehaviorNudgeDB
)

logger = logging.getLogger(__name__)


# ==================== 新手引导服务 ====================

class OnboardingService:
    """用户新手引导服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # 核心步骤定义
    CORE_STEPS = [
        'step_profile_complete',
        'step_verification_complete',
        'step_first_task_published',
        'step_first_task_accepted',
        'step_first_task_completed',
        'step_payment_setup_complete',
        'step_capability_graph_complete',
    ]

    EXTENDED_STEPS = [
        'step_team_created',
        'step_api_integration',
        'step_social_connection',
    ]

    async def get_onboarding_progress(self, user_id: str) -> Optional[UserOnboardingProgressDB]:
        """获取用户新手引导进度"""
        result = await self.db.execute(
            select(UserOnboardingProgressDB).where(UserOnboardingProgressDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_progress(self, user_id: str) -> UserOnboardingProgressDB:
        """获取或创建新手引导进度记录"""
        progress = await self.get_onboarding_progress(user_id)

        if not progress:
            progress = UserOnboardingProgressDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                onboarding_status='not_started',
            )
            self.db.add(progress)
            await self.db.flush()

        return progress

    async def start_onboarding(self, user_id: str) -> UserOnboardingProgressDB:
        """开始新手引导"""
        progress = await self.get_or_create_progress(user_id)

        progress.onboarding_status = 'in_progress'
        progress.started_at = datetime.utcnow()
        progress.overall_progress = 0.00

        await self.db.flush()

        logger.info(f"用户 {user_id} 开始新手引导")

        return progress

    async def update_step_progress(
        self,
        user_id: str,
        step_name: str,
        completed: bool
    ) -> UserOnboardingProgressDB:
        """更新引导步骤进度"""
        progress = await self.get_or_create_progress(user_id)

        # 动态设置属性
        step_attr = f"step_{step_name}" if not step_name.startswith('step_') else step_name

        if hasattr(progress, step_attr):
            setattr(progress, step_attr, completed)

            # 如果刚完成步骤，更新时间
            if completed and progress.started_at is None:
                progress.started_at = datetime.utcnow()
                progress.onboarding_status = 'in_progress'

            # 重新计算整体进度
            progress.overall_progress = await self._calculate_overall_progress(progress)

            # 检查是否所有核心步骤都已完成
            if await self._all_core_steps_complete(progress):
                progress.onboarding_status = 'completed'
                progress.completed_at = datetime.utcnow()

            progress.updated_at = datetime.utcnow()
            await self.db.flush()

            logger.info(f"用户 {user_id} 更新步骤 {step_name} 为 {'完成' if completed else '未完成'}")
        else:
            logger.warning(f"未知步骤：{step_name}")

        return progress

    async def _calculate_overall_progress(self, progress: UserOnboardingProgressDB) -> float:
        """计算整体进度百分比"""
        total_steps = len(self.CORE_STEPS)
        completed_steps = 0

        for step in self.CORE_STEPS:
            if hasattr(progress, step) and getattr(progress, step):
                completed_steps += 1

        return round((completed_steps / total_steps) * 100, 2)

    async def _all_core_steps_complete(self, progress: UserOnboardingProgressDB) -> bool:
        """检查所有核心步骤是否都已完成"""
        for step in self.CORE_STEPS:
            if not hasattr(progress, step) or not getattr(progress, step):
                return False
        return True

    async def complete_onboarding(self, user_id: str) -> UserOnboardingProgressDB:
        """完成新手引导"""
        progress = await self.get_or_create_progress(user_id)

        progress.onboarding_status = 'completed'
        progress.completed_at = datetime.utcnow()
        progress.overall_progress = 100.00

        await self.db.flush()

        logger.info(f"用户 {user_id} 完成了新手引导")

        return progress

    async def skip_onboarding(self, user_id: str) -> UserOnboardingProgressDB:
        """跳过新手引导"""
        progress = await self.get_or_create_progress(user_id)

        progress.onboarding_status = 'skipped'
        progress.skipped_at = datetime.utcnow()

        await self.db.flush()

        logger.info(f"用户 {user_id} 跳过了新手引导")

        return progress

    async def get_onboarding_checklist(self, user_id: str) -> Dict:
        """获取新手任务清单"""
        progress = await self.get_or_create_progress(user_id)

        # 获取步骤定义
        result = await self.db.execute(
            select(OnboardingStepDefinitionDB)
            .where(OnboardingStepDefinitionDB.is_active == True)
            .order_by(OnboardingStepDefinitionDB.sort_order)
        )
        step_definitions = list(result.scalars().all())

        # 构建清单
        checklist = []
        for step_def in step_definitions:
            step_key = step_def.step_key
            step_attr = f"step_{step_key}" if not step_key.startswith('step_') else step_key

            is_complete = hasattr(progress, step_attr) and getattr(progress, step_attr)

            checklist.append({
                "step_key": step_key,
                "display_name": step_def.display_name,
                "description": step_def.description,
                "step_type": step_def.step_type,
                "is_complete": is_complete,
                "is_required": step_def.is_required,
                "guide_content": step_def.guide_content,
                "tutorial_url": step_def.tutorial_url,
                "video_url": step_def.video_url,
                "reward": {
                    "points": step_def.reward_points,
                    "badge": step_def.reward_badge,
                } if step_def.reward_points or step_def.reward_badge else None,
            })

        return {
            "overall_progress": float(progress.overall_progress) if progress.overall_progress else 0.0,
            "status": progress.onboarding_status,
            "checklist": checklist,
        }

    async def get_step_tips(self, user_id: str, step_key: str) -> Optional[Dict]:
        """获取特定步骤的提示信息"""
        result = await self.db.execute(
            select(OnboardingStepDefinitionDB).where(
                OnboardingStepDefinitionDB.step_key == step_key,
                OnboardingStepDefinitionDB.is_active == True
            )
        )
        step_def = result.scalar_one_or_none()

        if not step_def:
            return None

        return {
            "step_key": step_def.step_key,
            "title": step_def.title,
            "guide_content": step_def.guide_content,
            "tutorial_url": step_def.tutorial_url,
            "video_url": step_def.video_url,
        }


# ==================== 用户引导服务 ====================

class NudgeService:
    """用户行为引导服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_nudges(self, user_id: str) -> List[UserBehaviorNudgeDB]:
        """获取当前活跃的用户引导"""
        now = datetime.utcnow()

        result = await self.db.execute(
            select(UserBehaviorNudgeDB)
            .where(UserBehaviorNudgeDB.user_id == user_id)
            .where(UserBehaviorNudgeDB.is_dismissed == False)
            .where(UserBehaviorNudgeDB.is_completed == False)
            .where(
                or_(
                    UserBehaviorNudgeDB.expires_at.is_(None),
                    UserBehaviorNudgeDB.expires_at > now
                )
            )
            .order_by(desc(UserBehaviorNudgeDB.priority), desc(UserBehaviorNudgeDB.created_at))
        )

        return list(result.scalars().all())

    async def should_show_nudge(
        self,
        user_id: str,
        nudge_type: str,
        context: Optional[Dict] = None
    ) -> bool:
        """判断是否应该展示引导"""
        # 检查是否有未过期的同类型引导
        now = datetime.utcnow()

        result = await self.db.execute(
            select(UserBehaviorNudgeDB)
            .where(UserBehaviorNudgeDB.user_id == user_id)
            .where(UserBehaviorNudgeDB.nudge_type == nudge_type)
            .where(UserBehaviorNudgeDB.is_dismissed == False)
            .where(UserBehaviorNudgeDB.is_completed == False)
            .where(
                or_(
                    UserBehaviorNudgeDB.expires_at.is_(None),
                    UserBehaviorNudgeDB.expires_at > now
                )
            )
        )

        existing_nudge = result.scalar_one_or_none()

        if existing_nudge:
            # 如果已有未完成的引导，检查展示次数
            return existing_nudge.display_count < existing_nudge.max_display_count

        return True

    async def create_nudge(
        self,
        user_id: str,
        nudge_type: str,
        nudge_title: str,
        nudge_content: str,
        action_url: Optional[str] = None,
        action_button_text: str = '知道了',
        max_display_count: int = 3,
        expires_hours: Optional[int] = None,
        context: Optional[Dict] = None,
        priority: int = 0
    ) -> UserBehaviorNudgeDB:
        """创建用户引导"""
        now = datetime.utcnow()

        expires_at = None
        if expires_hours:
            from datetime import timedelta
            expires_at = now + timedelta(hours=expires_hours)

        nudge = UserBehaviorNudgeDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            nudge_type=nudge_type,
            nudge_title=nudge_title,
            nudge_content=nudge_content,
            nudge_context=json.dumps(context) if context else None,
            action_url=action_url,
            action_button_text=action_button_text,
            display_count=0,
            max_display_count=max_display_count,
            is_dismissed=False,
            is_completed=False,
            expires_at=expires_at,
            priority=priority,
        )

        self.db.add(nudge)
        await self.db.flush()

        logger.info(f"为用户 {user_id} 创建引导：{nudge_type}")

        return nudge

    async def dismiss_nudge(self, nudge_id: str) -> bool:
        """关闭引导"""
        result = await self.db.execute(
            select(UserBehaviorNudgeDB).where(UserBehaviorNudgeDB.id == nudge_id)
        )
        nudge = result.scalar_one_or_none()

        if not nudge:
            return False

        nudge.is_dismissed = True
        nudge.dismissed_at = datetime.utcnow()
        nudge.updated_at = datetime.utcnow()

        await self.db.flush()

        logger.info(f"引导 {nudge_id} 被用户关闭")

        return True

    async def complete_nudge(self, nudge_id: str) -> bool:
        """完成引导"""
        result = await self.db.execute(
            select(UserBehaviorNudgeDB).where(UserBehaviorNudgeDB.id == nudge_id)
        )
        nudge = result.scalar_one_or_none()

        if not nudge:
            return False

        nudge.is_completed = True
        nudge.completed_at = datetime.utcnow()
        nudge.updated_at = datetime.utcnow()

        await self.db.flush()

        logger.info(f"引导 {nudge_id} 被用户完成")

        return True

    async def increment_nudge_display_count(self, nudge_id: str) -> int:
        """增加引导展示次数"""
        result = await self.db.execute(
            select(UserBehaviorNudgeDB).where(UserBehaviorNudgeDB.id == nudge_id)
        )
        nudge = result.scalar_one_or_none()

        if not nudge:
            return 0

        nudge.display_count += 1
        nudge.updated_at = datetime.utcnow()

        await self.db.flush()

        return nudge.display_count

    async def get_contextual_nudges(
        self,
        user_id: str,
        context_key: str,
        context_value: str
    ) -> List[UserBehaviorNudgeDB]:
        """获取上下文相关的引导"""
        now = datetime.utcnow()

        result = await self.db.execute(
            select(UserBehaviorNudgeDB)
            .where(UserBehaviorNudgeDB.user_id == user_id)
            .where(UserBehaviorNudgeDB.is_dismissed == False)
            .where(UserBehaviorNudgeDB.is_completed == False)
            .where(
                or_(
                    UserBehaviorNudgeDB.expires_at.is_(None),
                    UserBehaviorNudgeDB.expires_at > now
                )
            )
        )

        nudges = list(result.scalars().all())

        # 过滤出与上下文匹配的引导
        matching_nudges = []
        for nudge in nudges:
            if nudge.nudge_context:
                try:
                    nudge_context = json.loads(nudge.nudge_context)
                    if nudge_context.get(context_key) == context_value:
                        matching_nudges.append(nudge)
                except json.JSONDecodeError:
                    pass

        return matching_nudges


# ==================== 依赖注入 ====================

def get_onboarding_service(db: AsyncSession) -> OnboardingService:
    """获取新手引导服务实例"""
    return OnboardingService(db)


def get_nudge_service(db: AsyncSession) -> NudgeService:
    """获取用户引导服务实例"""
    return NudgeService(db)
