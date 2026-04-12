"""
用户行为日志收集服务

收集用户在应用中的各种行为，用于 AI 分析和推荐

架构说明：
- UserBehaviorEventDB 和 UserBehaviorDailyStatsDB 模型已迁移到 models/behavior_log.py
- 本服务仅负责业务逻辑，不定义数据模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from db.database import get_db
from utils.logger import logger
from services.base_service import BaseService
from models.behavior_log import UserBehaviorEventDB, UserBehaviorDailyStatsDB
import json


class BehaviorLogService(BaseService):
    """行为日志服务"""

    def __init__(self, db: Session):
        super().__init__(db)

    def log_event(
        self,
        user_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        记录用户行为事件

        Args:
            user_id: 用户 ID
            event_type: 事件类型
            event_data: 事件数据
            session_id: 会话 ID
            device_id: 设备 ID
            ip_address: IP 地址

        Returns:
            事件 ID
        """
        event_id = f"ube-{user_id}-{datetime.now().timestamp()}"

        event = UserBehaviorEventDB(
            id=event_id,
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
            session_id=session_id,
            device_id=device_id,
            ip_address=ip_address
        )

        self.db.add(event)
        self.db.commit()

        # 异步更新日统计
        self._update_daily_stats(user_id, event_type, event_data)

        logger.debug(f"BehaviorLog: Logged {event_type} for user={user_id}")
        return event_id

    def _update_daily_stats(
        self,
        user_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ):
        """更新日统计数据"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stats_id = f"ubd-{user_id}-{today.strftime('%Y%m%d')}"

        # 获取或创建日统计记录
        stats = self.db.query(UserBehaviorDailyStatsDB).filter(
            UserBehaviorDailyStatsDB.user_id == user_id,
            UserBehaviorDailyStatsDB.stat_date == today
        ).first()

        if not stats:
            stats = UserBehaviorDailyStatsDB(
                id=stats_id,
                user_id=user_id,
                stat_date=today,
                swipe_count=0,
                like_count=0,
                pass_count=0,
                message_count=0,
                profile_view_count=0,
                match_count=0,
                active_minutes=0,
                first_active_time=datetime.now(),
                last_active_time=datetime.now()
            )
            self.db.add(stats)

        # 更新统计
        if event_type == "swipe":
            stats.swipe_count += 1
            action = event_data.get("action") if event_data else None
            if action == "like":
                stats.like_count += 1
            elif action == "pass":
                stats.pass_count += 1

        elif event_type == "message":
            stats.message_count += 1

        elif event_type == "profile_view":
            stats.profile_view_count += 1

        elif event_type == "match":
            stats.match_count += 1

        # 更新最后活跃时间
        stats.last_active_time = datetime.now()

        self.db.commit()

    def get_user_behavior_history(
        self,
        user_id: str,
        days: int = 7,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户行为历史

        Args:
            user_id: 用户 ID
            days: 查询天数
            event_type: 事件类型过滤

        Returns:
            行为事件列表
        """
        start_date = datetime.now() - timedelta(days=days)

        query = self.db.query(UserBehaviorEventDB).filter(
            UserBehaviorEventDB.user_id == user_id,
            UserBehaviorEventDB.created_at >= start_date
        )

        if event_type:
            query = query.filter(UserBehaviorEventDB.event_type == event_type)

        events = query.order_by(UserBehaviorEventDB.created_at.desc()).all()

        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_data": e.event_data,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in events
        ]

    def get_user_daily_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取用户日统计数据

        Args:
            user_id: 用户 ID
            days: 查询天数

        Returns:
            日统计列表
        """
        start_date = datetime.now() - timedelta(days=days)

        stats = self.db.query(UserBehaviorDailyStatsDB).filter(
            UserBehaviorDailyStatsDB.user_id == user_id,
            UserBehaviorDailyStatsDB.stat_date >= start_date
        ).order_by(UserBehaviorDailyStatsDB.stat_date.desc()).all()

        return [
            {
                "stat_date": s.stat_date.isoformat() if s.stat_date else None,
                "swipe_count": s.swipe_count,
                "like_count": s.like_count,
                "pass_count": s.pass_count,
                "message_count": s.message_count,
                "profile_view_count": s.profile_view_count,
                "match_count": s.match_count,
                "active_minutes": s.active_minutes,
                "first_active_time": s.first_active_time.isoformat() if s.first_active_time else None,
                "last_active_time": s.last_active_time.isoformat() if s.last_active_time else None
            }
            for s in stats
        ]

    def get_active_hours(self, user_id: str, days: int = 7) -> List[int]:
        """
        获取用户活跃时间段

        Args:
            user_id: 用户 ID
            days: 查询天数

        Returns:
            活跃小时列表（0-23）
        """
        start_date = datetime.now() - timedelta(days=days)

        events = self.db.query(
            func.extract("hour", UserBehaviorEventDB.created_at).label("hour")
        ).filter(
            UserBehaviorEventDB.user_id == user_id,
            UserBehaviorEventDB.created_at >= start_date
        ).all()

        active_hours = list(set([int(e.hour) for e in events]))
        return sorted(active_hours)

    def get_message_stats(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        获取用户消息统计

        Args:
            user_id: 用户 ID
            days: 查询天数

        Returns:
            消息统计数据
        """
        start_date = datetime.now() - timedelta(days=days)

        events = self.db.query(UserBehaviorEventDB).filter(
            UserBehaviorEventDB.user_id == user_id,
            UserBehaviorEventDB.event_type == "message",
            UserBehaviorEventDB.created_at >= start_date
        ).all()

        if not events:
            return {
                "total_messages": 0,
                "avg_message_length": 0,
                "active_conversations": 0,
                "avg_response_time_minutes": 0
            }

        total_messages = len(events)
        total_length = sum(
            e.event_data.get("message_length", 0)
            for e in events
            if e.event_data
        )
        avg_length = total_length / total_messages if total_messages > 0 else 0

        # 统计活跃对话数
        conversation_ids = set(
            e.event_data.get("conversation_id")
            for e in events
            if e.event_data and e.event_data.get("conversation_id")
        )

        # 计算平均响应时间
        response_times = [
            e.event_data.get("response_time_seconds", 0)
            for e in events
            if e.event_data
        ]
        avg_response = sum(response_times) / len(response_times) if response_times else 0

        return {
            "total_messages": total_messages,
            "avg_message_length": round(avg_length, 1),
            "active_conversations": len(conversation_ids),
            "avg_response_time_minutes": round(avg_response / 60, 1)
        }


# 便捷函数
def get_behavior_log_service(db: Session) -> BehaviorLogService:
    """获取行为日志服务实例"""
    return BehaviorLogService(db)


# 事件类型常量
class EventTypes:
    """行为事件类型常量"""
    SWIPE = "swipe"
    MESSAGE = "message"
    PROFILE_VIEW = "profile_view"
    MATCH = "match"
    LOGIN = "login"
    LOGOUT = "logout"
    PROFILE_UPDATE = "profile_update"
    SEARCH = "search"
    FILTER_CHANGE = "filter_change"
    NOTIFICATION_CLICK = "notification_click"
