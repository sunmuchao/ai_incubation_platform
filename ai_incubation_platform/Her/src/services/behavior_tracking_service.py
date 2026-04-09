"""
行为追踪服务 - P3

用于记录和分析用户在系统内的行为：
- 浏览行为（查看资料页）
- 搜索行为（筛选条件变化）
- 互动行为（点赞、跳过、发消息）
- 对话行为（话题偏好、互动节奏）

基于行为数据动态更新用户画像，实现「越用越懂你」的匹配体验。
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json
from sqlalchemy.orm import Session
from utils.db_session_manager import db_session, db_session_readonly
from db.database import SessionLocal
from db.models import BehaviorEventDB, UserProfileUpdateDB, ConversationDB
from utils.logger import logger


class BehaviorTrackingService:
    """行为追踪服务"""

    # 行为类型常量
    EVENT_PROFILE_VIEW = "profile_view"
    EVENT_SEARCH = "search"
    EVENT_LIKE = "like"
    EVENT_PASS = "pass"
    EVENT_MESSAGE_OPEN = "message_open"
    EVENT_MESSAGE_SEND = "message_send"
    EVENT_RECOMMENDATION_CLICK = "recommendation_click"
    EVENT_RECOMMENDATION_DISMISS = "recommendation_dismiss"

    def __init__(self) -> None:
        self._event_buffer: Dict[str, List[dict]] = defaultdict(list)
        self._buffer_size_limit: int = 100  # 缓冲区大小限制
        self._buffer_time_limit: timedelta = timedelta(minutes=5)  # 缓冲区时间限制

    def record_event(
        self,
        user_id: str,
        event_type: str,
        target_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录用户行为事件

        Args:
            user_id: 用户 ID
            event_type: 事件类型
            target_id: 目标用户 ID（如被查看的资料）
            event_data: 事件详情数据

        Returns:
            事件 ID
        """
        event_id = str(__import__('uuid').uuid4())

        # 构建事件记录
        event = {
            "id": event_id,
            "user_id": user_id,
            "event_type": event_type,
            "target_id": target_id,
            "event_data": event_data or {},
            "created_at": datetime.now()
        }

        # 加入缓冲区
        self._event_buffer[user_id].append(event)

        # 检查是否需要刷新到数据库
        if len(self._event_buffer[user_id]) >= self._buffer_size_limit:
            self.flush_events(user_id)

        logger.debug(f"Recorded behavior event: {event_type} for user {user_id}")
        return event_id

    def flush_events(self, user_id: str) -> int:
        """
        将缓冲区的事件刷新到数据库

        Args:
            user_id: 用户 ID

        Returns:
            刷新的事件数量
        """
        events = self._event_buffer.pop(user_id, [])
        if not events:
            return 0

        with db_session() as db:
            for event in events:
                db_event = BehaviorEventDB(
                    id=event["id"],
                    user_id=event["user_id"],
                    event_type=event["event_type"],
                    target_id=event["target_id"],
                    event_data=event["event_data"],
                    created_at=event["created_at"]
                )
                db.add(db_event)

            # auto-commits
            logger.info(f"Flushed {len(events)} behavior events for user {user_id}")
            return len(events)

    def get_user_behavior_summary(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取用户行为摘要

        Args:
            user_id: 用户 ID
            days: 统计天数

        Returns:
            行为摘要字典
        """
        with db_session_readonly() as db:
            since = datetime.now() - timedelta(days=days)

            # 查询行为事件
            events = db.query(BehaviorEventDB).filter(
                BehaviorEventDB.user_id == user_id,
                BehaviorEventDB.created_at >= since
            ).all()

            if not events:
                return self._empty_summary()

            # 统计各类型事件数量
            event_counts = defaultdict(int)
            target_views = defaultdict(int)  # 被查看的目标用户计数
            hourly_activity = defaultdict(int)  # 每小时活跃度

            for event in events:
                event_counts[event.event_type] += 1

                if event.event_type == self.EVENT_PROFILE_VIEW and event.target_id:
                    target_views[event.target_id] += 1

                hour = event.created_at.hour
                hourly_activity[hour] += 1

            # 计算活跃时段
            peak_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:3]

            # 计算最常查看的用户
            top_viewed = sorted(target_views.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                "total_events": len(events),
                "event_counts": dict(event_counts),
                "unique_profiles_viewed": len(target_views),
                "peak_activity_hours": [h[0] for h in peak_hours],
                "top_viewed_profiles": [{"user_id": u[0], "views": u[1]} for u in top_viewed],
                "average_daily_events": len(events) / days if days > 0 else 0
            }

    def analyze_preference_shift(
        self,
        user_id: str,
        days: int = 14
    ) -> Dict[str, Any]:
        """
        分析用户偏好变化趋势

        Args:
            user_id: 用户 ID
            days: 分析天数

        Returns:
            偏好变化分析结果
        """
        with db_session_readonly() as db:
            since = datetime.now() - timedelta(days=days)

            # 获取用户行为
            events = db.query(BehaviorEventDB).filter(
                BehaviorEventDB.user_id == user_id,
                BehaviorEventDB.created_at >= since
            ).all()

            if not events:
                return {"trend": "insufficient_data", "changes": []}

            # 分析年龄偏好变化
            age_preferences = self._analyze_age_preference_shift(events, db)

            # 分析地点偏好变化
            location_preferences = self._analyze_location_preference_shift(events, db)

            # 分析类型偏好变化（通过 like/pass 行为）
            type_preferences = self._analyze_type_preference_shift(events, db)

            changes = []
            if age_preferences.get("shift"):
                changes.append({
                    "type": "age_preference",
                    "description": f"年龄偏好从 {age_preferences['from']} 岁转向 {age_preferences['to']} 岁",
                    "confidence": age_preferences.get("confidence", 0.5)
                })

            if location_preferences.get("shift"):
                changes.append({
                    "type": "location_preference",
                    "description": f"地点偏好变化：{location_preferences['description']}",
                    "confidence": location_preferences.get("confidence", 0.5)
                })

            if type_preferences.get("shift"):
                changes.append({
                    "type": "type_preference",
                    "description": type_preferences["description"],
                    "confidence": type_preferences.get("confidence", 0.5)
                })

            return {
                "trend": "preference_shift_detected" if changes else "stable",
                "changes": changes,
                "analysis_period_days": days
            }

    def _analyze_age_preference_shift(self, events: List[BehaviorEventDB], db: Session) -> Dict[str, Any]:
        """分析年龄偏好变化"""
        from db.models import UserDB

        liked_user_ids = [
            e.target_id for e in events
            if e.event_type == self.EVENT_LIKE and e.target_id
        ]

        if not liked_user_ids:
            return {"shift": False}

        liked_users = db.query(UserDB).filter(UserDB.id.in_(liked_user_ids)).all()
        if not liked_users:
            return {"shift": False}

        ages = [u.age for u in liked_users]
        avg_age = sum(ages) / len(ages)

        return {
            "shift": True,
            "to": int(avg_age),
            "from": "unknown",  # 需要历史数据对比
            "confidence": min(0.9, len(ages) / 20)  # 样本越多置信度越高
        }

    def _analyze_location_preference_shift(self, events: List[BehaviorEventDB], db: Session) -> Dict[str, Any]:
        """分析地点偏好变化"""
        # 简化实现
        return {"shift": False, "description": ""}

    def _analyze_type_preference_shift(self, events: List[BehaviorEventDB], db: Session) -> Dict[str, Any]:
        """分析类型偏好变化"""
        # 简化实现：分析 like/pass 比例变化
        likes = [e for e in events if e.event_type == self.EVENT_LIKE]
        passes = [e for e in events if e.event_type == self.EVENT_PASS]

        if not likes and not passes:
            return {"shift": False}

        like_rate = len(likes) / (len(likes) + len(passes)) if (len(likes) + len(passes)) > 0 else 0

        return {
            "shift": like_rate < 0.3 or like_rate > 0.7,
            "description": f"选择倾向：{'更挑剔' if like_rate < 0.3 else '更开放' if like_rate > 0.7 else '平衡'} (通过率 {like_rate:.1%})",
            "confidence": min(0.9, (len(likes) + len(passes)) / 30)
        }

    def _empty_summary(self) -> Dict[str, Any]:
        """返回空的行为摘要"""
        return {
            "total_events": 0,
            "event_counts": {},
            "unique_profiles_viewed": 0,
            "peak_activity_hours": [],
            "top_viewed_profiles": [],
            "average_daily_events": 0
        }

    def flush_all(self) -> int:
        """刷新所有缓冲区的事件"""
        total = 0
        for user_id in list(self._event_buffer.keys()):
            total += self.flush_events(user_id)
        return total


# 全局服务实例
behavior_service = BehaviorTrackingService()
