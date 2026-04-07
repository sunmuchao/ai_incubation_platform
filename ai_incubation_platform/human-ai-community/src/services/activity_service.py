"""
社区活动服务层
支持线上活动（AMA/直播/投票）、线下聚会、活动管理（报名/签到/回顾）、直播系统等功能
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import uuid
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.activity_models import (
    DBActivity, DBActivityRegistration, DBActivitySession, DBActivityInteraction,
    DBLiveStream, LiveChatMessage, DBVote, DBVoteOption, DBVoteRecord,
    DBActivityRecap, DBActivityRecommendation,
    ActivityTypeEnum, ActivityStatusEnum, ActivityRoleEnum, RegistrationStatusEnum,
    ActivityInteractionTypeEnum, LiveStreamStatusEnum, VoteTypeEnum, VoteStatusEnum
)
from db.models import DBCommunityMember
from services.notification_service import notification_service, NotificationType
from core.logging_config import get_logger

logger = get_logger(__name__)


class ActivityService:
    """社区活动服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 活动管理 ====================

    async def create_activity(
        self,
        organizer_id: str,
        title: str,
        description: str,
        activity_type: ActivityTypeEnum,
        start_time: datetime,
        end_time: datetime,
        content: Optional[str] = None,
        location_type: str = "online",
        location_address: Optional[str] = None,
        location_online_url: Optional[str] = None,
        max_participants: Optional[int] = None,
        tags: Optional[List[str]] = None,
        cover_image_url: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        co_organizers: Optional[List[str]] = None,
    ) -> DBActivity:
        """创建活动"""
        activity_id = str(uuid.uuid4())

        # 根据时间自动设置状态
        now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
        if start_time > now:
            status = ActivityStatusEnum.DRAFT
        else:
            status = ActivityStatusEnum.IN_PROGRESS

        activity = DBActivity(
            id=activity_id,
            organizer_id=organizer_id,
            title=title,
            description=description,
            content=content,
            activity_type=activity_type,
            status=status,
            start_time=start_time,
            end_time=end_time,
            location_type=location_type,
            location_address=location_address,
            location_online_url=location_online_url,
            max_participants=max_participants,
            tags=tags or [],
            cover_image_url=cover_image_url,
            extra_data=extra_data or {},
            co_organizers=co_organizers or [],
        )

        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)

        logger.info(f"活动已创建：{activity_id}, 标题：{title}, 组织者：{organizer_id}")
        return activity

    async def get_activity(self, activity_id: str) -> Optional[DBActivity]:
        """获取活动详情"""
        result = await self.db.execute(
            select(DBActivity).where(DBActivity.id == activity_id)
        )
        return result.scalar_one_or_none()

    async def update_activity(
        self,
        activity_id: str,
        **kwargs
    ) -> Optional[DBActivity]:
        """更新活动"""
        activity = await self.get_activity(activity_id)
        if not activity:
            return None

        # 过滤不允许直接更新的字段
        allowed_fields = [
            "title", "description", "content", "status", "start_time", "end_time",
            "registration_start", "registration_end", "location_type", "location_address",
            "location_online_url", "max_participants", "tags", "cover_image_url",
            "allow_comments", "allow_chat", "allow_questions", "extra_data", "co_organizers"
        ]

        for field in allowed_fields:
            if field in kwargs:
                setattr(activity, field, kwargs[field])

        await self.db.commit()
        await self.db.refresh(activity)

        logger.info(f"活动已更新：{activity_id}")
        return activity

    async def delete_activity(self, activity_id: str) -> bool:
        """删除活动"""
        activity = await self.get_activity(activity_id)
        if not activity:
            return False

        await self.db.delete(activity)
        await self.db.commit()

        logger.info(f"活动已删除：{activity_id}")
        return True

    async def list_activities(
        self,
        status: Optional[ActivityStatusEnum] = None,
        activity_type: Optional[ActivityTypeEnum] = None,
        organizer_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DBActivity]:
        """获取活动列表"""
        query = select(DBActivity)

        if status:
            query = query.where(DBActivity.status == status)
        if activity_type:
            query = query.where(DBActivity.activity_type == activity_type)
        if organizer_id:
            query = query.where(DBActivity.organizer_id == organizer_id)

        query = query.order_by(desc(DBActivity.created_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_upcoming_activities(self, limit: int = 20) -> List[DBActivity]:
        """获取即将开始的活动"""
        now = datetime.now()
        result = await self.db.execute(
            select(DBActivity)
            .where(DBActivity.start_time > now)
            .where(DBActivity.status != ActivityStatusEnum.CANCELLED)
            .order_by(DBActivity.start_time)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_live_activities(self) -> List[DBActivity]:
        """获取进行中的活动"""
        now = datetime.now()
        result = await self.db.execute(
            select(DBActivity)
            .where(DBActivity.status == ActivityStatusEnum.IN_PROGRESS)
            .where(DBActivity.start_time <= now)
            .where(DBActivity.end_time > now)
            .order_by(desc(DBActivity.view_count))
        )
        return list(result.scalars().all())

    async def increment_view_count(self, activity_id: str) -> bool:
        """增加活动浏览次数"""
        activity = await self.get_activity(activity_id)
        if not activity:
            return False

        activity.view_count += 1
        await self.db.commit()
        return True

    # ==================== 活动报名管理 ====================

    async def register_activity(
        self,
        activity_id: str,
        user_id: str,
        role: ActivityRoleEnum = ActivityRoleEnum.ATTENDEE,
        registration_note: Optional[str] = None,
    ) -> Tuple[bool, Optional[DBActivityRegistration], str]:
        """报名参加活动"""
        activity = await self.get_activity(activity_id)
        if not activity:
            return False, None, "活动不存在"

        # 检查活动状态
        if activity.status in [ActivityStatusEnum.CANCELLED, ActivityStatusEnum.ARCHIVED]:
            return False, None, "活动已取消或归档"

        if activity.status == ActivityStatusEnum.REGISTRATION_CLOSED:
            return False, None, "活动报名已截止"

        # 检查是否已报名
        existing = await self.get_registration(activity_id, user_id)
        if existing:
            return False, None, "您已报名该活动"

        # 检查人数限制
        if activity.max_participants and activity.current_participants >= activity.max_participants:
            # 加入候补
            status = RegistrationStatusEnum.WAITLIST
        else:
            status = RegistrationStatusEnum.CONFIRMED

        registration = DBActivityRegistration(
            id=str(uuid.uuid4()),
            activity_id=activity_id,
            user_id=user_id,
            role=role,
            status=status,
            registration_note=registration_note,
        )

        self.db.add(registration)

        if status == RegistrationStatusEnum.CONFIRMED:
            activity.current_participants += 1
            activity.registration_count += 1

        await self.db.commit()
        await self.db.refresh(registration)

        # 发送通知
        await notification_service.send_notification(
            recipient_id=user_id,
            title="报名成功",
            content=f"您已成功报名参加活动：{activity.title}",
            notification_type="activity_registration",
            related_content_id=activity_id,
        )

        logger.info(f"用户 {user_id} 已报名活动 {activity_id}")
        return True, registration, "报名成功"

    async def get_registration(self, activity_id: str, user_id: str) -> Optional[DBActivityRegistration]:
        """获取报名记录"""
        result = await self.db.execute(
            select(DBActivityRegistration)
            .where(DBActivityRegistration.activity_id == activity_id)
            .where(DBActivityRegistration.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def cancel_registration(self, activity_id: str, user_id: str) -> Tuple[bool, str]:
        """取消报名"""
        registration = await self.get_registration(activity_id, user_id)
        if not registration:
            return False, "未找到报名记录"

        if registration.status in [RegistrationStatusEnum.CANCELLED, RegistrationStatusEnum.NO_SHOW]:
            return False, "报名已取消或已过期"

        activity = await self.get_activity(activity_id)

        # 如果是确认状态，减少计数
        if registration.status == RegistrationStatusEnum.CONFIRMED:
            activity.current_participants = max(0, activity.current_participants - 1)

        registration.status = RegistrationStatusEnum.CANCELLED
        await self.db.commit()

        logger.info(f"用户 {user_id} 已取消报名活动 {activity_id}")
        return True, "取消成功"

    async def confirm_registration(self, registration_id: str) -> Optional[DBActivityRegistration]:
        """确认报名（从候补转为确认）"""
        result = await self.db.execute(
            select(DBActivityRegistration).where(DBActivityRegistration.id == registration_id)
        )
        registration = result.scalar_one_or_none()
        if not registration:
            return None

        if registration.status == RegistrationStatusEnum.WAITLIST:
            registration.status = RegistrationStatusEnum.CONFIRMED
            await self.db.commit()
            await self.db.refresh(registration)

        return registration

    async def check_in(self, activity_id: str, user_id: str) -> Tuple[bool, str]:
        """活动签到"""
        registration = await self.get_registration(activity_id, user_id)
        if not registration:
            return False, "未找到报名记录"

        if registration.checked_in:
            return False, "您已签到"

        registration.checked_in = True
        registration.check_in_time = datetime.now()
        registration.status = RegistrationStatusEnum.ATTENDED

        # 更新活动出席人数
        activity = await self.get_activity(activity_id)
        if activity:
            activity.attendance_count += 1

        await self.db.commit()

        logger.info(f"用户 {user_id} 已在活动 {activity_id} 签到")
        return True, "签到成功"

    async def get_registrations(
        self,
        activity_id: str,
        status: Optional[RegistrationStatusEnum] = None,
        role: Optional[ActivityRoleEnum] = None,
        limit: int = 100,
    ) -> List[DBActivityRegistration]:
        """获取活动报名列表"""
        query = select(DBActivityRegistration).where(DBActivityRegistration.activity_id == activity_id)

        if status:
            query = query.where(DBActivityRegistration.status == status)
        if role:
            query = query.where(DBActivityRegistration.role == role)

        query = query.order_by(DBActivityRegistration.created_at)
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== 活动议程管理 ====================

    async def create_session(
        self,
        activity_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        speakers: Optional[List[str]] = None,
        session_type: str = "presentation",
        order_index: int = 0,
    ) -> DBActivitySession:
        """创建活动场次/议程"""
        session = DBActivitySession(
            id=str(uuid.uuid4()),
            activity_id=activity_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            speakers=speakers or [],
            session_type=session_type,
            order_index=order_index,
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def get_sessions(self, activity_id: str) -> List[DBActivitySession]:
        """获取活动场次列表"""
        result = await self.db.execute(
            select(DBActivitySession)
            .where(DBActivitySession.activity_id == activity_id)
            .order_by(DBActivitySession.order_index)
        )
        return list(result.scalars().all())

    async def update_session(
        self,
        session_id: str,
        **kwargs
    ) -> Optional[DBActivitySession]:
        """更新场次"""
        result = await self.db.execute(
            select(DBActivitySession).where(DBActivitySession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return None

        allowed_fields = ["title", "description", "start_time", "end_time", "speakers", "session_type", "order_index"]
        for field in allowed_fields:
            if field in kwargs:
                setattr(session, field, kwargs[field])

        await self.db.commit()
        await self.db.refresh(session)
        return session

    # ==================== 活动互动管理 ====================

    async def create_interaction(
        self,
        activity_id: str,
        user_id: str,
        interaction_type: ActivityInteractionTypeEnum,
        content: Optional[str] = None,
        parent_id: Optional[str] = None,
        target_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> DBActivityInteraction:
        """创建活动互动"""
        activity = await self.get_activity(activity_id)
        if not activity:
            raise ValueError("活动不存在")

        # 检查互动权限
        if interaction_type == ActivityInteractionTypeEnum.COMMENT and not activity.allow_comments:
            raise ValueError("该活动不允许评论")
        if interaction_type == ActivityInteractionTypeEnum.QUESTION and not activity.allow_questions:
            raise ValueError("该活动不允许提问")
        if interaction_type == ActivityInteractionTypeEnum.CHAT and not activity.allow_chat:
            raise ValueError("该活动不允许聊天")

        interaction = DBActivityInteraction(
            id=str(uuid.uuid4()),
            activity_id=activity_id,
            user_id=user_id,
            interaction_type=interaction_type,
            content=content,
            parent_id=parent_id,
            target_id=target_id,
            session_id=session_id,
        )

        self.db.add(interaction)

        # 更新用户互动计数
        registration = await self.get_registration(activity_id, user_id)
        if registration:
            registration.interaction_count += 1
            if interaction_type == ActivityInteractionTypeEnum.QUESTION:
                registration.questions_asked += 1

        await self.db.commit()
        await self.db.refresh(interaction)

        return interaction

    async def get_interactions(
        self,
        activity_id: str,
        interaction_type: Optional[ActivityInteractionTypeEnum] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DBActivityInteraction]:
        """获取活动互动列表"""
        query = select(DBActivityInteraction).where(DBActivityInteraction.activity_id == activity_id)

        if interaction_type:
            query = query.where(DBActivityInteraction.interaction_type == interaction_type)
        if session_id:
            query = query.where(DBActivityInteraction.session_id == session_id)

        # 只显示已审核且未隐藏的内容
        query = query.where(DBActivityInteraction.is_approved == True)
        query = query.where(DBActivityInteraction.is_hidden == False)

        query = query.order_by(DBActivityInteraction.created_at)
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def answer_question(self, interaction_id: str) -> Optional[DBActivityInteraction]:
        """标记问题为已回答"""
        result = await self.db.execute(
            select(DBActivityInteraction).where(DBActivityInteraction.id == interaction_id)
        )
        interaction = result.scalar_one_or_none()
        if not interaction:
            return None

        if interaction.interaction_type != ActivityInteractionTypeEnum.QUESTION:
            raise ValueError("这不是一个提问")

        interaction.is_answered = True
        await self.db.commit()
        await self.db.refresh(interaction)

        return interaction

    async def pin_interaction(self, interaction_id: str, pinned: bool = True) -> Optional[DBActivityInteraction]:
        """置顶/取消置顶互动"""
        result = await self.db.execute(
            select(DBActivityInteraction).where(DBActivityInteraction.id == interaction_id)
        )
        interaction = result.scalar_one_or_none()
        if not interaction:
            return None

        interaction.is_pinned = pinned
        await self.db.commit()
        await self.db.refresh(interaction)

        return interaction


def get_activity_service(db: AsyncSession) -> ActivityService:
    """获取活动服务实例"""
    return ActivityService(db)
