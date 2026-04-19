"""
Your Turn 提醒服务

参考 Hinge 的 Your Turn 机制：
- 当对方发消息后未回复，显示 "Your Turn" 提醒
- 提醒用户回复，避免对话中断
- 记录提醒历史，避免重复提醒
- 会员可自定义提醒频率

架构说明：
- YourTurnReminderDB 模型已迁移到 models/your_turn.py
- 本服务仅负责业务逻辑，不定义数据模型
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from utils.logger import logger
from services.base_service import BaseService
from models.your_turn import YourTurnReminderDB


class YourTurnReminderService(BaseService):
    """Your Turn 提醒服务"""

    # 提醒配置
    REMINDER_DELAY_HOURS = 24  # 首次提醒延迟（24小时未回复）
    REMINDER_INTERVAL_HOURS = 48  # 提醒间隔（48小时）
    MAX_REMINDERS = 3  # 最大提醒次数
    REMINDER_EXPIRE_DAYS = 7  # 提醒过期天数

    def __init__(self, db: Session):
        super().__init__(db)

    def get_pending_reminders(self, user_id: str) -> List[dict]:
        """
        获取用户待处理的 Your Turn 提醒

        返回需要回复的对话列表
        """
        # 查询对方发了消息但用户未回复的对话
        # 且超过 REMINDER_DELAY_HOURS 小时

        # 简化实现：查询最近对方发消息但用户未回复的对话
        from db.models import ChatConversationDB, ChatMessageDB

        # 获取用户所有对话
        conversations = self.db.query(ChatConversationDB).filter(
            or_(
                ChatConversationDB.user_id_1 == user_id,
                ChatConversationDB.user_id_2 == user_id
            )
        ).all()

        reminders = []
        now = datetime.now()

        for conv in conversations:
            # 确定对方 ID
            partner_id = conv.user_id_2 if conv.user_id_1 == user_id else conv.user_id_1

            # 查询最后一条消息
            last_message = self.db.query(ChatMessageDB).filter(
                ChatMessageDB.conversation_id == conv.id
            ).order_by(ChatMessageDB.created_at.desc()).first()

            if not last_message:
                continue

            # 判断是否需要提醒
            # 1. 最后一条消息是对方发的
            # 2. 用户未回复
            # 3. 超过 24 小时

            if last_message.sender_id == partner_id:
                # 对方发的消息，检查用户是否回复
                time_since_message = now - last_message.created_at

                if time_since_message >= timedelta(hours=self.REMINDER_DELAY_HOURS):
                    # 检查是否在消息后有用户的回复
                    user_reply = self.db.query(ChatMessageDB).filter(
                        ChatMessageDB.conversation_id == conv.id,
                        ChatMessageDB.sender_id == user_id,
                        ChatMessageDB.created_at > last_message.created_at
                    ).first()

                    if not user_reply:
                        # 需要提醒
                        reminders.append({
                            "conversation_id": conv.id,
                            "partner_id": partner_id,
                            "last_message_content": last_message.content[:100] if last_message.content else "",
                            "last_message_time": last_message.created_at.isoformat(),
                            "hours_waiting": int(time_since_message.total_seconds() / 3600),
                            "is_your_turn": True,
                        })

        return reminders

    def should_show_reminder(self, user_id: str, conversation_id: str) -> Tuple[bool, Optional[dict]]:
        """
        判断是否应该显示 Your Turn 提醒

        Returns:
            (是否显示, 提醒详情)
        """
        reminders = self.get_pending_reminders(user_id)

        for reminder in reminders:
            if reminder["conversation_id"] == conversation_id:
                return True, reminder

        return False, None

    def mark_reminder_shown(self, user_id: str, conversation_id: str) -> bool:
        """标记提醒已显示"""
        # 记录提醒显示历史（避免重复提醒）

        # 检查是否已有记录
        existing = self.db.query(YourTurnReminderDB).filter(
            YourTurnReminderDB.user_id == user_id,
            YourTurnReminderDB.conversation_id == conversation_id
        ).first()

        if existing:
            existing.shown_count += 1
            existing.last_shown_at = datetime.now()
            self.db.commit()
            return True

        # 创建新记录
        reminder = YourTurnReminderDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            conversation_id=conversation_id,
            shown_count=1,
            last_shown_at=datetime.now(),
        )
        self.db.add(reminder)
        self.db.commit()

        return True

    def get_reminder_stats(self, user_id: str) -> dict:
        """获取用户提醒统计"""
        pending = self.get_pending_reminders(user_id)

        return {
            "pending_count": len(pending),
            "total_waiting_hours": sum(r["hours_waiting"] for r in pending),
            "oldest_waiting_hours": max(r["hours_waiting"] for r in pending) if pending else 0,
        }

    def dismiss_reminder(self, user_id: str, conversation_id: str) -> bool:
        """用户主动忽略提醒"""

        reminder = self.db.query(YourTurnReminderDB).filter(
            YourTurnReminderDB.user_id == user_id,
            YourTurnReminderDB.conversation_id == conversation_id
        ).first()

        if reminder:
            reminder.dismissed = True
            reminder.dismissed_at = datetime.now()
            self.db.commit()
            return True

        return False


# 服务工厂函数
def get_your_turn_service(db: Session) -> YourTurnReminderService:
    """获取 Your Turn 服务实例"""
    return YourTurnReminderService(db)