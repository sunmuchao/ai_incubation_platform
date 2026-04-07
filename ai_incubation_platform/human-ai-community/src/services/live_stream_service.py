"""
直播服务层
支持直播管理、聊天/弹幕、礼物打赏等功能
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import secrets

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.activity_models import (
    DBLiveStream, LiveChatMessage, DBActivity,
    LiveStreamStatusEnum, ActivityStatusEnum
)
from db.economy_models import DBWalletTransaction, TransactionTypeEnum, TransactionStatusEnum
from services.notification_service import notification_service
from core.logging_config import get_logger

logger = get_logger(__name__)


class LiveStreamService:
    """直播服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 直播管理 ====================

    async def create_live_stream(
        self,
        activity_id: str,
        is_chat_enabled: bool = True,
        is_gift_enabled: bool = True,
        is_record_enabled: bool = True,
    ) -> Tuple[bool, Optional[DBLiveStream], str]:
        """创建直播"""
        # 检查活动是否存在
        result = await self.db.execute(
            select(DBActivity).where(DBActivity.id == activity_id)
        )
        activity = result.scalar_one_or_none()
        if not activity:
            return False, None, "活动不存在"

        # 检查是否已存在直播
        existing = await self.get_live_stream_by_activity(activity_id)
        if existing:
            return False, existing, "该活动已创建直播"

        stream_id = str(uuid.uuid4())
        stream_key = self._generate_stream_key()

        live_stream = DBLiveStream(
            id=stream_id,
            activity_id=activity_id,
            stream_key=stream_key,
            is_chat_enabled=is_chat_enabled,
            is_gift_enabled=is_gift_enabled,
            is_record_enabled=is_record_enabled,
            status=LiveStreamStatusEnum.SCHEDULED,
        )

        self.db.add(live_stream)
        await self.db.commit()
        await self.db.refresh(live_stream)

        logger.info(f"直播已创建：{stream_id}, 活动：{activity_id}")
        return True, live_stream, "直播创建成功"

    def _generate_stream_key(self) -> str:
        """生成推流密钥"""
        return f"sk_{secrets.token_urlsafe(32)}"

    async def get_live_stream(self, stream_id: str) -> Optional[DBLiveStream]:
        """获取直播详情"""
        result = await self.db.execute(
            select(DBLiveStream).where(DBLiveStream.id == stream_id)
        )
        return result.scalar_one_or_none()

    async def get_live_stream_by_activity(self, activity_id: str) -> Optional[DBLiveStream]:
        """根据活动 ID 获取直播"""
        result = await self.db.execute(
            select(DBLiveStream).where(DBLiveStream.activity_id == activity_id)
        )
        return result.scalar_one_or_none()

    async def start_live_stream(self, stream_id: str) -> Tuple[bool, Optional[DBLiveStream], str]:
        """开始直播"""
        live_stream = await self.get_live_stream(stream_id)
        if not live_stream:
            return False, None, "直播不存在"

        if live_stream.status == LiveStreamStatusEnum.LIVE:
            return False, None, "直播已在进行中"

        live_stream.status = LiveStreamStatusEnum.LIVE
        live_stream.started_at = datetime.now()

        # 更新关联活动状态
        activity = await self.db.get(DBActivity, live_stream.activity_id)
        if activity:
            activity.status = ActivityStatusEnum.IN_PROGRESS

        await self.db.commit()
        await self.db.refresh(live_stream)

        logger.info(f"直播已开始：{stream_id}")
        return True, live_stream, "直播已开始"

    async def end_live_stream(self, stream_id: str) -> Tuple[bool, Optional[DBLiveStream], str]:
        """结束直播"""
        live_stream = await self.get_live_stream(stream_id)
        if not live_stream:
            return False, None, "直播不存在"

        if live_stream.status != LiveStreamStatusEnum.LIVE:
            return False, None, "直播未在进行中"

        live_stream.status = LiveStreamStatusEnum.ENDED
        live_stream.ended_at = datetime.now()

        # 计算录制时长
        if live_stream.started_at:
            duration = (live_stream.ended_at - live_stream.started_at).total_seconds()
            live_stream.recording_duration = int(duration)

        # 更新关联活动状态
        activity = await self.db.get(DBActivity, live_stream.activity_id)
        if activity:
            activity.status = ActivityStatusEnum.COMPLETED

        await self.db.commit()
        await self.db.refresh(live_stream)

        logger.info(f"直播已结束：{stream_id}")
        return True, live_stream, "直播已结束"

    async def update_viewer_count(self, stream_id: str, count: int) -> bool:
        """更新观看人数"""
        live_stream = await self.get_live_stream(stream_id)
        if not live_stream:
            return False

        live_stream.viewer_count = count
        if count > live_stream.peak_viewer_count:
            live_stream.peak_viewer_count = count

        await self.db.commit()
        return True

    async def increment_total_views(self, stream_id: str) -> bool:
        """增加累计观看次数"""
        live_stream = await self.get_live_stream(stream_id)
        if not live_stream:
            return False

        live_stream.total_views += 1
        await self.db.commit()
        return True

    async def increment_like_count(self, stream_id: str) -> bool:
        """增加点赞数"""
        live_stream = await self.get_live_stream(stream_id)
        if not live_stream:
            return False

        live_stream.like_count += 1
        await self.db.commit()
        return True

    async def add_gift_value(self, stream_id: str, value: int) -> bool:
        """增加礼物总价值"""
        live_stream = await self.get_live_stream(stream_id)
        if not live_stream:
            return False

        live_stream.gift_value += value
        await self.db.commit()
        return True

    async def set_recording_url(self, stream_id: str, recording_url: str) -> bool:
        """设置录制视频 URL"""
        live_stream = await self.get_live_stream(stream_id)
        if not live_stream:
            return False

        live_stream.recording_url = recording_url
        live_stream.status = LiveStreamStatusEnum.RECORDED
        await self.db.commit()

        logger.info(f"直播录制 URL 已设置：{stream_id}")
        return True

    async def get_live_streams(
        self,
        status: Optional[LiveStreamStatusEnum] = None,
        limit: int = 50,
    ) -> List[DBLiveStream]:
        """获取直播列表"""
        query = select(DBLiveStream)

        if status:
            query = query.where(DBLiveStream.status == status)

        query = query.order_by(desc(DBLiveStream.created_at))
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())


class LiveChatService:
    """直播聊天服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_chat_message(
        self,
        stream_id: str,
        user_id: str,
        content: str,
        message_type: str = "text",
        gift_info: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[LiveChatMessage], str]:
        """发送聊天消息"""
        # 检查直播是否存在
        result = await self.db.execute(
            select(DBLiveStream).where(DBLiveStream.id == stream_id)
        )
        live_stream = result.scalar_one_or_none()
        if not live_stream:
            return False, None, "直播不存在"

        # 检查直播状态
        if live_stream.status not in [LiveStreamStatusEnum.LIVE, LiveStreamStatusEnum.RECORDED]:
            return False, None, "直播未在进行中"

        # 检查聊天是否启用
        if not live_stream.is_chat_enabled:
            return False, None, "该直播已禁用聊天"

        message = LiveChatMessage(
            id=str(uuid.uuid4()),
            stream_id=stream_id,
            user_id=user_id,
            content=content,
            message_type=message_type,
            gift_info=gift_info if gift_info else None,
        )

        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        return True, message, "消息发送成功"

    async def get_chat_messages(
        self,
        stream_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LiveChatMessage]:
        """获取聊天消息列表"""
        query = select(LiveChatMessage).where(
            LiveChatMessage.stream_id == stream_id,
            LiveChatMessage.is_hidden == False
        )
        query = query.order_by(LiveChatMessage.created_at)
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def hide_message(self, message_id: str) -> bool:
        """隐藏消息"""
        result = await self.db.execute(
            select(LiveChatMessage).where(LiveChatMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            return False

        message.is_hidden = True
        await self.db.commit()
        return True

    async def get_recent_messages(self, stream_id: str, limit: int = 50) -> List[LiveChatMessage]:
        """获取最近聊天消息"""
        return await self.get_chat_messages(stream_id, limit=limit)


def get_live_stream_service(db: AsyncSession) -> LiveStreamService:
    """获取直播服务实例"""
    return LiveStreamService(db)


def get_live_chat_service(db: AsyncSession) -> LiveChatService:
    """获取直播聊天服务实例"""
    return LiveChatService(db)
