"""
通知偏好设置服务中心层 - v1.22 用户体验优化

提供通知偏好设置功能的核心业务逻辑
"""
from datetime import datetime, time
from typing import Dict, List, Optional
import uuid
import logging

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.ux_notifications import UserNotificationPreferencesDB, UserNotificationDB

logger = logging.getLogger(__name__)


# ==================== 通知偏好服务 ====================

class NotificationPreferenceService:
    """用户通知偏好设置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_preferences(self, user_id: str) -> Optional[UserNotificationPreferencesDB]:
        """获取用户通知偏好设置"""
        result = await self.db.execute(
            select(UserNotificationPreferencesDB).where(UserNotificationPreferencesDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_preferences(self, user_id: str) -> UserNotificationPreferencesDB:
        """获取用户通知偏好设置，如果不存在则创建默认设置"""
        preferences = await self.get_user_preferences(user_id)

        if not preferences:
            preferences = UserNotificationPreferencesDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
            )
            self.db.add(preferences)
            await self.db.flush()

        return preferences

    async def update_preferences(self, user_id: str, preferences_data: Dict) -> UserNotificationPreferencesDB:
        """更新用户通知偏好设置"""
        preferences = await self.get_or_create_preferences(user_id)

        # 更新推送通知设置
        if 'push_notifications' in preferences_data:
            push = preferences_data['push_notifications']
            if 'task' in push:
                preferences.push_task_notifications = push['task']
            if 'message' in push:
                preferences.push_message_notifications = push['message']
            if 'payment' in push:
                preferences.push_payment_notifications = push['payment']
            if 'system' in push:
                preferences.push_system_notifications = push['system']
            if 'marketing' in push:
                preferences.push_marketing_notifications = push['marketing']

        # 更新邮件通知设置
        if 'email_notifications' in preferences_data:
            email = preferences_data['email_notifications']
            if 'task' in email:
                preferences.email_task_notifications = email['task']
            if 'message' in email:
                preferences.email_message_notifications = email['message']
            if 'payment' in email:
                preferences.email_payment_notifications = email['payment']
            if 'system' in email:
                preferences.email_system_notifications = email['system']
            if 'marketing' in email:
                preferences.email_marketing_notifications = email['marketing']

        # 更新短信通知设置
        if 'sms_notifications' in preferences_data:
            sms = preferences_data['sms_notifications']
            if 'payment' in sms:
                preferences.sms_payment_notifications = sms['payment']
            if 'urgent' in sms:
                preferences.sms_urgent_notifications = sms['urgent']
            if 'marketing' in sms:
                preferences.sms_marketing_notifications = sms['marketing']

        # 更新免打扰设置
        if 'do_not_disturb' in preferences_data:
            dnd = preferences_data['do_not_disturb']
            if 'enabled' in dnd:
                preferences.dnd_enabled = dnd['enabled']
            if 'start_time' in dnd and self._is_valid_time(dnd['start_time']):
                preferences.dnd_start_time = dnd['start_time']
            if 'end_time' in dnd and self._is_valid_time(dnd['end_time']):
                preferences.dnd_end_time = dnd['end_time']

        # 更新通知摘要设置
        if 'digest' in preferences_data:
            digest = preferences_data['digest']
            if 'enabled' in digest:
                preferences.digest_enabled = digest['enabled']
            if 'frequency' in digest and digest['frequency'] in ['hourly', 'daily', 'weekly']:
                preferences.digest_frequency = digest['frequency']

        preferences.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"用户 {user_id} 更新了通知偏好设置")

        return preferences

    def _is_valid_time(self, time_str: str) -> bool:
        """验证时间字符串格式是否有效 (HH:MM:SS)"""
        try:
            parts = time_str.split(':')
            if len(parts) != 3:
                return False
            hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
            return 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59
        except (ValueError, AttributeError):
            return False

    def _parse_time(self, time_str: str) -> time:
        """将时间字符串转换为 time 对象"""
        parts = time_str.split(':')
        return time(hour=int(parts[0]), minute=int(parts[1]), second=int(parts[2]))

    async def is_in_dnd_period(self, user_id: str) -> bool:
        """检查当前是否在用户的免打扰时段内"""
        preferences = await self.get_user_preferences(user_id)

        if not preferences or not preferences.dnd_enabled:
            return False

        now = datetime.now().time()
        start_time = self._parse_time(preferences.dnd_start_time)
        end_time = self._parse_time(preferences.dnd_end_time)

        # 处理跨天的情况（如 22:00 - 08:00）
        if start_time <= end_time:
            # 不跨天
            return start_time <= now <= end_time
        else:
            # 跨天（如 22:00 - 次日 08:00）
            return now >= start_time or now <= end_time

    async def should_send_notification(
        self,
        user_id: str,
        notification_type: str,
        channel: str
    ) -> bool:
        """判断是否应该发送通知"""
        preferences = await self.get_user_preferences(user_id)

        if not preferences:
            return True  # 没有偏好设置时默认发送

        # 检查是否在免打扰时段
        if channel == 'push' and await self.is_in_dnd_period(user_id):
            logger.info(f"用户 {user_id} 当前在免打扰时段，跳过推送通知")
            return False

        # 根据通知类型和渠道检查偏好
        if channel == 'push':
            if notification_type == 'task':
                return preferences.push_task_notifications
            elif notification_type == 'message':
                return preferences.push_message_notifications
            elif notification_type == 'payment':
                return preferences.push_payment_notifications
            elif notification_type == 'system':
                return preferences.push_system_notifications
            elif notification_type == 'marketing':
                return preferences.push_marketing_notifications

        elif channel == 'email':
            if notification_type == 'task':
                return preferences.email_task_notifications
            elif notification_type == 'message':
                return preferences.email_message_notifications
            elif notification_type == 'payment':
                return preferences.email_payment_notifications
            elif notification_type == 'system':
                return preferences.email_system_notifications
            elif notification_type == 'marketing':
                return preferences.email_marketing_notifications

        elif channel == 'sms':
            if notification_type == 'payment':
                return preferences.sms_payment_notifications
            elif notification_type == 'urgent':
                return preferences.sms_urgent_notifications
            elif notification_type == 'marketing':
                return preferences.sms_marketing_notifications

        return True  # 默认发送

    async def get_notification_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        notification_type: Optional[str] = None,
        is_read: Optional[bool] = None
    ) -> List[UserNotificationDB]:
        """获取用户通知历史"""
        query = select(UserNotificationDB).where(UserNotificationDB.user_id == user_id)

        if notification_type:
            query = query.where(UserNotificationDB.notification_type == notification_type)

        if is_read is not None:
            query = query.where(UserNotificationDB.is_read == is_read)

        query = query.order_by(desc(UserNotificationDB.created_at)).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_notifications_as_read(
        self,
        user_id: str,
        notification_ids: List[str]
    ) -> int:
        """标记通知为已读"""
        from sqlalchemy import update

        query = (
            update(UserNotificationDB)
            .where(UserNotificationDB.id.in_(notification_ids))
            .where(UserNotificationDB.user_id == user_id)
            .values(is_read=True, read_at=datetime.utcnow())
        )

        result = await self.db.execute(query)
        await self.db.commit()

        logger.info(f"用户 {user_id} 标记了 {result.rowcount} 条通知为已读")

        return result.rowcount

    async def mark_all_as_read(self, user_id: str) -> int:
        """标记所有通知为已读"""
        from sqlalchemy import update

        query = (
            update(UserNotificationDB)
            .where(UserNotificationDB.user_id == user_id)
            .where(UserNotificationDB.is_read == False)
            .values(is_read=True, read_at=datetime.utcnow())
        )

        result = await self.db.execute(query)
        await self.db.commit()

        logger.info(f"用户 {user_id} 标记了所有通知为已读")

        return result.rowcount

    async def delete_notification(self, user_id: str, notification_id: str) -> bool:
        """删除通知"""
        result = await self.db.execute(
            select(UserNotificationDB).where(
                UserNotificationDB.id == notification_id,
                UserNotificationDB.user_id == user_id
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            return False

        await self.db.delete(notification)
        await self.db.commit()

        logger.info(f"用户 {user_id} 删除了通知 {notification_id}")

        return True

    async def get_unread_count(self, user_id: str) -> int:
        """获取未读通知数量"""
        result = await self.db.execute(
            select(func.count()).where(
                UserNotificationDB.user_id == user_id,
                UserNotificationDB.is_read == False
            )
        )
        return result.scalar_one()


# ==================== 依赖注入 ====================

def get_notification_preference_service(db: AsyncSession) -> NotificationPreferenceService:
    """获取通知偏好服务实例"""
    return NotificationPreferenceService(db)
