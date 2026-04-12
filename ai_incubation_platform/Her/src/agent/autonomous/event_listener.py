"""
事件监听器

监听关键业务事件，触发心跳或更新状态。
支持的事件：
- match_created：匹配成功 → 立即触发破冰心跳
- message_sent：消息发送 → 更新活跃状态，取消停滞推送
- user_login：用户登录 → 更新活跃状态，取消激活推送
- date_scheduled：约会安排 → 设置约会提醒
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from utils.logger import logger
from db.database import get_db
from db.autonomous_models import TriggerEventDB, UserPushPreferencesDB
from db.models import UserDB, MatchHistoryDB


class EventListener:
    """
    事件监听器

    监听并处理关键业务事件
    """

    # 支持的事件类型
    SUPPORTED_EVENTS = [
        "match_created",
        "message_sent",
        "user_login",
        "date_scheduled",
        "date_completed",
        "profile_updated",
        "relationship_stage_changed"
    ]

    # 事件优先级
    EVENT_PRIORITY = {
        "match_created": "high",
        "date_scheduled": "high",
        "message_sent": "medium",
        "user_login": "medium",
        "date_completed": "medium",
        "profile_updated": "low",
        "relationship_stage_changed": "low"
    }

    # 事件触发的规则
    EVENT_TRIGGER_RULES = {
        "match_created": "check_new_matches",
        "date_scheduled": "check_pending_dates",
        "message_sent": None,  # 不触发心跳，只更新状态
        "user_login": None,
    }

    def __init__(self):
        self.scheduler = None
        self._init_scheduler()

    def _init_scheduler(self):
        """
        初始化调度器引用
        """
        try:
            from agent.autonomous.scheduler import get_scheduler
            self.scheduler = get_scheduler()
            logger.info("EventListener: Scheduler initialized")
        except Exception as e:
            logger.warning(f"EventListener: Scheduler not initialized: {e}")
            self.scheduler = None

    def handle_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        event_source: str = None
    ) -> Dict[str, Any]:
        """
        处理事件

        Args:
            event_type: 事件类型
            event_data: 事件数据
            event_source: 事件来源（用户ID等）

        Returns:
            处理结果
        """
        if event_type not in self.SUPPORTED_EVENTS:
            logger.warning(f"EventListener: Unsupported event type: {event_type}")
            return {"success": False, "error": "unsupported_event_type"}

        event_id = str(uuid.uuid4())
        priority = self.EVENT_PRIORITY.get(event_type, "medium")

        logger.info(f"🔔 [EVENT:{event_id}] Received event type={event_type}, priority={priority}")

        result = {
            "event_id": event_id,
            "event_type": event_type,
            "priority": priority,
            "processed": False
        }

        try:
            # 记录事件
            self._record_event(event_id, event_type, event_data, event_source)

            # 处理事件
            if event_type == "match_created":
                self._handle_match_created(event_id, event_data)

            elif event_type == "message_sent":
                self._handle_message_sent(event_id, event_data)

            elif event_type == "user_login":
                self._handle_user_login(event_id, event_data)

            elif event_type == "date_scheduled":
                self._handle_date_scheduled(event_id, event_data)

            elif event_type == "date_completed":
                self._handle_date_completed(event_id, event_data)

            elif event_type == "relationship_stage_changed":
                self._handle_relationship_stage_changed(event_id, event_data)

            result["processed"] = True

        except Exception as e:
            logger.error(f"🔔 [EVENT:{event_id}] Failed to process: {e}")
            result["error"] = str(e)

        return result

    def _record_event(
        self,
        event_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        event_source: str
    ):
        """
        记录事件到数据库
        """
        try:
            db = next(get_db())

            event_record = TriggerEventDB(
                id=event_id,
                event_type=event_type,
                event_source=event_source,
                event_data=event_data,
                processed=False
            )
            db.add(event_record)
            db.commit()

        except Exception as e:
            logger.warning(f"Failed to record event: {e}")

    def _handle_match_created(self, event_id: str, event_data: Dict[str, Any]):
        """
        处理匹配成功事件

        立即触发破冰心跳
        """
        user_id_1 = event_data.get("user_id_1")
        user_id_2 = event_data.get("user_id_2")
        match_id = event_data.get("match_id")

        logger.info(f"🔔 [EVENT:{event_id}] Match created: {match_id}, users={user_id_1},{user_id_2}")

        # 更新匹配记录（如果需要）
        try:
            db = next(get_db())

            match = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()
            if match:
                # 确保关系阶段正确
                match.relationship_stage = "matched"
                match.icebreaker_pushed = False  # 新增字段，标记未推送
                db.commit()

        except Exception as e:
            logger.warning(f"Failed to update match record: {e}")

        # 立即触发心跳（针对两个用户）
        trigger_rule = self.EVENT_TRIGGER_RULES.get("match_created")

        if self.scheduler and trigger_rule:
            # 为用户1触发
            self.scheduler.trigger_immediate(
                rule_name=trigger_rule,
                user_id=user_id_1
            )

            # 为用户2触发
            self.scheduler.trigger_immediate(
                rule_name=trigger_rule,
                user_id=user_id_2
            )

        logger.info(f"🔔 [EVENT:{event_id}] Triggered immediate heartbeat for match")

    def _handle_message_sent(self, event_id: str, event_data: Dict[str, Any]):
        """
        处理消息发送事件

        更新对话活跃状态，取消停滞推送计划
        """
        sender_id = event_data.get("sender_id")
        receiver_id = event_data.get("receiver_id")
        match_id = event_data.get("match_id")

        logger.info(f"🔔 [EVENT:{event_id}] Message sent: from={sender_id} to={receiver_id}")

        # 更新匹配记录的活跃状态
        try:
            db = next(get_db())

            match = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()
            if match:
                # 更新最后交互时间
                match.last_interaction_at = datetime.now()
                match.interaction_count += 1

                # 如果还在 matched 阶段，升级到 chatting
                if match.relationship_stage == "matched":
                    match.relationship_stage = "chatting"

                db.commit()

        except Exception as e:
            logger.warning(f"Failed to update match activity: {e}")

        # 更新用户活跃状态
        try:
            db = next(get_db())

            sender = db.query(UserDB).filter(UserDB.id == sender_id).first()
            if sender:
                sender.last_login = datetime.now()

            receiver = db.query(UserDB).filter(UserDB.id == receiver_id).first()
            if receiver:
                receiver.last_login = datetime.now()

            db.commit()

        except Exception as e:
            logger.warning(f"Failed to update user activity: {e}")

    def _handle_user_login(self, event_id: str, event_data: Dict[str, Any]):
        """
        处理用户登录事件

        更新活跃状态，取消激活推送计划
        """
        user_id = event_data.get("user_id")

        logger.info(f"🔔 [EVENT:{event_id}] User login: {user_id}")

        # 更新用户活跃状态
        try:
            db = next(get_db())

            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if user:
                user.last_login = datetime.now()
                db.commit()

        except Exception as e:
            logger.warning(f"Failed to update user login time: {e}")

    def _handle_date_scheduled(self, event_id: str, event_data: Dict[str, Any]):
        """
        处理约会安排事件

        设置约会提醒
        """
        user_id_1 = event_data.get("user_id_1")
        user_id_2 = event_data.get("user_id_2")
        date_id = event_data.get("date_id")
        scheduled_time = event_data.get("scheduled_time")

        logger.info(f"🔔 [EVENT:{event_id}] Date scheduled: {date_id}, time={scheduled_time}")

        # 记录约会安排（如果需要）
        # 注意：约会相关数据可能在 autonomous_dating_models.py 中

        # 触发约会准备心跳（提前24小时）
        # 这里可以设置一个定时任务，或者依赖心跳规则 check_pending_dates

    def _handle_date_completed(self, event_id: str, event_data: Dict[str, Any]):
        """
        处理约会完成事件

        更新关系阶段，触发约会反馈
        """
        user_id_1 = event_data.get("user_id_1")
        user_id_2 = event_data.get("user_id_2")
        match_id = event_data.get("match_id")

        logger.info(f"🔔 [EVENT:{event_id}] Date completed: match={match_id}")

        # 更新匹配记录的关系阶段
        try:
            db = next(get_db())

            match = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()
            if match:
                match.relationship_stage = "dated"
                db.commit()

        except Exception as e:
            logger.warning(f"Failed to update match stage after date: {e}")

    def _handle_relationship_stage_changed(self, event_id: str, event_data: Dict[str, Any]):
        """
        处理关系阶段变更事件

        更新关系进展，可能触发里程碑推送
        """
        match_id = event_data.get("match_id")
        old_stage = event_data.get("old_stage")
        new_stage = event_data.get("new_stage")

        logger.info(f"🔔 [EVENT:{event_id}] Relationship stage changed: {match_id}, {old_stage} -> {new_stage}")

        # 更新匹配记录
        try:
            db = next(get_db())

            match = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()
            if match:
                match.relationship_stage = new_stage
                db.commit()

        except Exception as e:
            logger.warning(f"Failed to update relationship stage: {e}")

        # 如果是里程碑阶段（如 in_relationship），可能触发庆祝推送
        if new_stage == "in_relationship":
            logger.info(f"🔔 [EVENT:{event_id}] Relationship milestone! May trigger celebration push")


# ============= 全局事件监听器 =============

_global_listener: Optional[EventListener] = None


def get_listener() -> EventListener:
    """
    获取全局事件监听器
    """
    if _global_listener is None:
        _global_listener = EventListener()
    return _global_listener


def emit_event(
    event_type: str,
    event_data: Dict[str, Any],
    event_source: str = None
) -> Dict[str, Any]:
    """
    发送事件（便捷函数）
    """
    listener = get_listener()
    return listener.handle_event(event_type, event_data, event_source)


# ============= 导出 =============

__all__ = [
    "EventListener",
    "get_listener",
    "emit_event",
]