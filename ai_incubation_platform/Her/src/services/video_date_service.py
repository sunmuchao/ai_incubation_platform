"""
v1.3 视频约会服务

提供视频约会管理、预约、提醒等功能。

Future 增强:
- 继承 BaseService 统一数据库会话管理
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import uuid

from db.models import VideoDateDB, UserDB, VideoDateReportDB, UserBlockDB, GameSessionDB
from services.base_service import BaseService


class VideoDateService(BaseService[VideoDateDB]):
    """视频约会服务"""

    def __init__(self, db: Optional[Session] = None):
        """
        初始化视频约会服务

        Args:
            db: 数据库会话（可选，支持依赖注入）
        """
        super().__init__(db, VideoDateDB)
        self.active_dates = {}  # 内存存储活跃约会 {room_id: date_info}

    def schedule_date(
        self,
        user_id_1: str,
        user_id_2: str,
        scheduled_time: datetime,
        duration_minutes: int = 30,
        theme: str = "初次见面",
        background: str = "default"
    ) -> Dict[str, Any]:
        """
        预约视频约会

        Returns:
            {
                "date_id": str,
                "room_id": str,
                "status": "scheduled",
                "scheduled_time": str,
            }
        """
        # 验证用户
        user1 = self.db.query(UserDB).filter(UserDB.id == user_id_1).first()
        user2 = self.db.query(UserDB).filter(UserDB.id == user_id_2).first()

        if not user1 or not user2:
            raise ValueError("用户不存在")

        # 检查是否已存在未完成的约会
        existing = self.db.query(VideoDateDB).filter(
            or_(
                (VideoDateDB.user_id_1 == user_id_1) & (VideoDateDB.user_id_2 == user_id_2),
                (VideoDateDB.user_id_1 == user_id_2) & (VideoDateDB.user_id_2 == user_id_1),
            ),
            VideoDateDB.status.in_(["scheduled", "waiting", "in_progress"])
        ).first()

        if existing:
            raise ValueError(f"已有未完成的约会，状态：{existing.status}")

        # 检查是否被拉黑
        block = self.db.query(UserBlockDB).filter(
            ((UserBlockDB.blocker_id == user_id_1) & (UserBlockDB.blocked_user_id == user_id_2)) |
            ((UserBlockDB.blocker_id == user_id_2) & (UserBlockDB.blocked_user_id == user_id_1))
        ).first()

        if block:
            raise ValueError("用户已被拉黑，无法预约")

        # 生成房间 ID
        room_id = f"date_{uuid.uuid4().hex[:12]}"

        # 创建约会记录
        date = VideoDateDB(
            id=str(uuid.uuid4()),
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            status="scheduled",
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            theme=theme,
            background=background,
            room_id=room_id,
        )

        self.db.add(date)
        self.db.commit()
        self.db.refresh(date)

        # 存储到活跃约会
        self.active_dates[room_id] = {
            "date_id": date.id,
            "user_id_1": user_id_1,
            "user_id_2": user_id_2,
            "status": "scheduled",
            "scheduled_time": scheduled_time.isoformat(),
        }

        return {
            "date_id": date.id,
            "room_id": room_id,
            "status": "scheduled",
            "scheduled_time": scheduled_time.isoformat(),
            "duration_minutes": duration_minutes,
            "theme": theme,
            "background": background,
        }

    def start_date(self, date_id: str, user_id: str) -> Dict[str, Any]:
        """开始视频约会"""
        date = self.db.query(VideoDateDB).filter(VideoDateDB.id == date_id).first()

        if not date:
            raise ValueError("约会不存在")

        if date.user_id_1 != user_id and date.user_id_2 != user_id:
            raise ValueError("无权开始此约会")

        if date.status not in ["scheduled", "waiting"]:
            raise ValueError(f"约会状态不允许开始：{date.status}")

        # 检查是否到预约时间
        now = datetime.utcnow()
        if now < date.scheduled_time - timedelta(minutes=5):
            raise ValueError("还未到预约时间（可提前 5 分钟开始）")

        date.status = "in_progress"
        date.actual_start_time = now

        self.db.commit()

        # 更新活跃约会状态
        if date.room_id in self.active_dates:
            self.active_dates[date.room_id]["status"] = "in_progress"
            self.active_dates[date.room_id]["actual_start_time"] = now.isoformat()

        return {
            "date_id": date.id,
            "room_id": date.room_id,
            "status": "in_progress",
            "actual_start_time": now.isoformat(),
        }

    def complete_date(
        self,
        date_id: str,
        user_id: str,
        rating: Optional[int] = None,
        review: Optional[str] = None
    ) -> bool:
        """完成视频约会"""
        date = self.db.query(VideoDateDB).filter(VideoDateDB.id == date_id).first()

        if not date:
            raise ValueError("约会不存在")

        if date.user_id_1 != user_id and date.user_id_2 != user_id:
            raise ValueError("无权结束此约会")

        date.actual_end_time = datetime.utcnow()
        if date.actual_start_time:
            date.actual_duration_minutes = int(
                (date.actual_end_time - date.actual_start_time).total_seconds() / 60
            )

        # 记录评分
        if rating:
            if user_id == date.user_id_1:
                date.rating_user1 = rating
                date.review_user1 = review
            else:
                date.rating_user2 = rating
                date.review_user2 = review

        # 如果双方都已完成，更新状态
        if date.rating_user1 is not None and date.rating_user2 is not None:
            date.status = "completed"
        else:
            date.status = "waiting"  # 等待另一方评分

        self.db.commit()

        # 从活跃约会移除
        if date.room_id in self.active_dates:
            del self.active_dates[date.room_id]

        return True

    def cancel_date(self, date_id: str, user_id: str, reason: str = "") -> bool:
        """取消视频约会"""
        date = self.db.query(VideoDateDB).filter(VideoDateDB.id == date_id).first()

        if not date:
            raise ValueError("约会不存在")

        if date.user_id_1 != user_id and date.user_id_2 != user_id:
            raise ValueError("无权取消此约会")

        if date.status not in ["scheduled", "waiting"]:
            raise ValueError(f"约会状态不允许取消：{date.status}")

        date.status = "cancelled"

        self.db.commit()

        # 从活跃约会移除
        if date.room_id in self.active_dates:
            del self.active_dates[date.room_id]

        return True

    def get_date_info(self, date_id: str) -> Optional[Dict[str, Any]]:
        """获取约会信息"""
        date = self.db.query(VideoDateDB).filter(VideoDateDB.id == date_id).first()

        if not date:
            return None

        return {
            "date_id": date.id,
            "user_id_1": date.user_id_1,
            "user_id_2": date.user_id_2,
            "status": date.status,
            "scheduled_time": date.scheduled_time.isoformat() if date.scheduled_time else None,
            "duration_minutes": date.duration_minutes,
            "theme": date.theme,
            "room_id": date.room_id,
            "background": date.background,
            "actual_start_time": date.actual_start_time.isoformat() if date.actual_start_time else None,
            "actual_end_time": date.actual_end_time.isoformat() if date.actual_end_time else None,
            "actual_duration_minutes": date.actual_duration_minutes,
            "rating_user1": date.rating_user1,
            "rating_user2": date.rating_user2,
            "review_user1": date.review_user1,
            "review_user2": date.review_user2,
            "created_at": date.created_at.isoformat(),
        }

    def get_user_date_list(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户约会列表"""
        query = self.db.query(VideoDateDB).filter(
            or_(
                VideoDateDB.user_id_1 == user_id,
                VideoDateDB.user_id_2 == user_id
            )
        )

        if status:
            query = query.filter(VideoDateDB.status == status)

        dates = query.order_by(VideoDateDB.scheduled_time.desc()).limit(limit).offset(offset).all()

        return [
            {
                "date_id": d.id,
                "partner_id": d.user_id_2 if d.user_id_1 == user_id else d.user_id_1,
                "status": d.status,
                "scheduled_time": d.scheduled_time.isoformat() if d.scheduled_time else None,
                "duration_minutes": d.duration_minutes,
                "theme": d.theme,
                "room_id": d.room_id,
                "rating": d.rating_user1 if d.user_id_1 == user_id else d.rating_user2,
                "created_at": d.created_at.isoformat(),
            }
            for d in dates
        ]

    def get_upcoming_reminders(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取即将到期的约会提醒"""
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)

        dates = self.db.query(VideoDateDB).filter(
            or_(
                VideoDateDB.user_id_1 == user_id,
                VideoDateDB.user_id_2 == user_id
            ),
            VideoDateDB.status.in_(["scheduled", "waiting"]),
            VideoDateDB.scheduled_time <= cutoff,
            VideoDateDB.scheduled_time >= now
        ).order_by(VideoDateDB.scheduled_time).all()

        return [
            {
                "date_id": d.id,
                "partner_id": d.user_id_2 if d.user_id_1 == user_id else d.user_id_1,
                "scheduled_time": d.scheduled_time.isoformat(),
                "theme": d.theme,
                "room_id": d.room_id,
                "minutes_until_start": int((d.scheduled_time - now).total_seconds() / 60),
            }
            for d in dates
        ]

    def record_game(self, date_id: str, game_type: str, game_data: Dict[str, Any]) -> str:
        """记录约会中玩的游戏"""
        date = self.db.query(VideoDateDB).filter(VideoDateDB.id == date_id).first()
        if not date:
            raise ValueError("约会不存在")

        # 创建游戏记录
        game = GameSessionDB(
            id=str(uuid.uuid4()),
            date_id=date_id,
            user_id_1=date.user_id_1,
            user_id_2=date.user_id_2,
            game_type=game_type,
            status="pending",
            game_data=json.dumps(game_data) if game_data else None,
        )

        self.db.add(game)
        self.db.commit()
        self.db.refresh(game)

        return game.id

    def cleanup_no_show_dates(self, max_delay_minutes: int = 30) -> int:
        """清理未赴约的约会（超过预约时间 30 分钟未开始）"""
        cutoff = datetime.utcnow() - timedelta(minutes=max_delay_minutes)

        no_show_dates = self.db.query(VideoDateDB).filter(
            VideoDateDB.status.in_(["scheduled", "waiting"]),
            VideoDateDB.scheduled_time < cutoff
        ).all()

        count = 0
        for date in no_show_dates:
            date.status = "no_show"
            count += 1

        self.db.commit()
        return count
