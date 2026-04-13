"""
约会提醒服务

提醒用户的约会安排：
- 创建约会计划
- 约会前提醒
- 约会准备建议
- 约会后反馈收集
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from utils.logger import logger
from services.base_service import BaseService


class DateReminderService(BaseService):
    """约会提醒服务"""

    # 提醒时间配置
    REMINDER_TIMINGS = {
        "one_day_before": 24,  # 提前 24 小时
        "three_hours_before": 3,  # 提前 3 小时
        "one_hour_before": 1,  # 提前 1 小时
    }

    def __init__(self, db: Session):
        super().__init__(db)
        self.db = db

    def create_date_plan(
        self,
        user_id: str,
        partner_id: str,
        date_time: datetime,
        location: str,
        activity: str,
        notes: Optional[str] = None,
        reminder_settings: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建约会计划

        Args:
            user_id: 用户 ID
            partner_id: 对方 ID
            date_time: 约会时间
            location: 约会地点
            activity: 约会活动
            notes: 备注（可选）
            reminder_settings: 提醒设置（可选）

        Returns:
            约会计划详情
        """
        from models.date_reminder import DateReminderPlanDB

        plan_id = str(uuid.uuid4())

        # 默认提醒设置
        default_reminders = {
            "one_day_before": True,
            "three_hours_before": True,
            "one_hour_before": True,
        }
        reminders = reminder_settings or default_reminders

        plan = DateReminderPlanDB(
            id=plan_id,
            user_id=user_id,
            partner_id=partner_id,
            date_time=date_time,
            location=location,
            activity=activity,
            notes=notes,
            reminder_settings=reminders,
            status="scheduled",
            created_at=datetime.now()
        )
        self.db.add(plan)
        self.db.commit()

        logger.info(f"Date plan created: {plan_id}")

        return {
            "plan_id": plan_id,
            "user_id": user_id,
            "partner_id": partner_id,
            "date_time": date_time.isoformat(),
            "location": location,
            "activity": activity,
            "notes": notes,
            "reminder_settings": reminders,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }

    def get_upcoming_dates(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取即将到来的约会

        Args:
            user_id: 用户 ID
            limit: 返回数量限制

        Returns:
            约会列表
        """
        from models.date_reminder import DateReminderPlanDB

        now = datetime.now()

        dates = self.db.query(DateReminderPlanDB).filter(
            DateReminderPlanDB.user_id == user_id,
            DateReminderPlanDB.date_time > now,
            DateReminderPlanDB.status != "cancelled"
        ).order_by(DateReminderPlanDB.date_time).limit(limit).all()

        return [
            {
                "plan_id": d.id,
                "partner_id": d.partner_id,
                "date_time": d.date_time.isoformat(),
                "location": d.location,
                "activity": d.activity,
                "notes": d.notes,
                "status": d.status,
                "time_until": self._calculate_time_until(d.date_time)
            }
            for d in dates
        ]

    def _calculate_time_until(self, date_time: datetime) -> Dict[str, int]:
        """计算距离约会的时间"""
        now = datetime.now()
        delta = date_time - now

        return {
            "days": delta.days,
            "hours": delta.seconds // 3600,
            "minutes": (delta.seconds % 3600) // 60,
            "total_seconds": delta.total_seconds()
        }

    def get_pending_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取待发送的提醒

        用于定时任务检查需要发送的提醒

        Args:
            user_id: 用户 ID

        Returns:
            待提醒列表
        """
        from models.date_reminder import DateReminderPlanDB

        now = datetime.now()

        # 查询所有即将到来的约会
        upcoming = self.db.query(DateReminderPlanDB).filter(
            DateReminderPlanDB.user_id == user_id,
            DateReminderPlanDB.date_time > now,
            DateReminderPlanDB.date_time <= now + timedelta(hours=24),
            DateReminderPlanDB.status == "scheduled"
        ).all()

        reminders = []
        for date in upcoming:
            time_until = date.date_time - now

            # 检查是否需要发送提醒
            reminder_settings = date.reminder_settings or {}

            # 24 小时前提醒
            if reminder_settings.get("one_day_before"):
                if timedelta(hours=23) <= time_until <= timedelta(hours=25):
                    if not date.one_day_reminder_sent:
                        reminders.append({
                            "plan_id": date.id,
                            "reminder_type": "one_day_before",
                            "date_time": date.date_time.isoformat(),
                            "location": date.location,
                            "activity": date.activity
                        })

            # 3 小时前提醒
            if reminder_settings.get("three_hours_before"):
                if timedelta(hours=2.5) <= time_until <= timedelta(hours=3.5):
                    if not date.three_hours_reminder_sent:
                        reminders.append({
                            "plan_id": date.id,
                            "reminder_type": "three_hours_before",
                            "date_time": date.date_time.isoformat(),
                            "location": date.location,
                            "activity": date.activity
                        })

            # 1 小时前提醒
            if reminder_settings.get("one_hour_before"):
                if timedelta(minutes=50) <= time_until <= timedelta(hours=1.5):
                    if not date.one_hour_reminder_sent:
                        reminders.append({
                            "plan_id": date.id,
                            "reminder_type": "one_hour_before",
                            "date_time": date.date_time.isoformat(),
                            "location": date.location,
                            "activity": date.activity
                        })

        return reminders

    def mark_reminder_sent(self, plan_id: str, reminder_type: str) -> bool:
        """标记提醒已发送"""
        from models.date_reminder import DateReminderPlanDB

        plan = self.db.query(DateReminderPlanDB).filter(DateReminderPlanDB.id == plan_id).first()
        if not plan:
            return False

        if reminder_type == "one_day_before":
            plan.one_day_reminder_sent = True
        elif reminder_type == "three_hours_before":
            plan.three_hours_reminder_sent = True
        elif reminder_type == "one_hour_before":
            plan.one_hour_reminder_sent = True

        self.db.commit()
        return True

    async def generate_date_preparation_suggestions(
        self,
        date_plan: Dict[str, Any],
        user_profile: Dict[str, Any],
        partner_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI 生成约会准备建议

        Args:
            date_plan: 约会计划
            user_profile: 用户资料
            partner_profile: 对方资料

        Returns:
            准备建议
        """
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        prompt = f"""请为这个约会生成准备建议：

约会信息：
- 时间：{date_plan.get('date_time')}
- 地点：{date_plan.get('location')}
- 活动：{date_plan.get('activity')}
- 备注：{date_plan.get('notes', '无')}

用户资料：
- 兴趣：{user_profile.get('interests', [])}
- 简介：{user_profile.get('bio', '')}

对方资料：
- 兴趣：{partner_profile.get('interests', [])}
- 简介：{partner_profile.get('bio', '')}

请给出：
1. 穿着建议（根据地点和活动）
2. 话题准备（可以聊什么）
3. 礼物建议（是否需要准备礼物）
4. 注意事项（特别提醒）
5. 应急方案（如果出现问题）

回复格式：
{
  "dress_suggestion": "穿着建议",
  "conversation_topics": ["话题1", "话题2", ...],
  "gift_suggestion": "礼物建议（或不需要）",
  "special_notes": ["注意事项"],
  "backup_plan": "应急方案",
  "confidence": 0.85
}"""

        try:
            result = await llm_service.generate(prompt)
            import json
            suggestions = json.loads(result)
            return suggestions
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return {
                "dress_suggestion": "根据活动选择合适的穿着",
                "conversation_topics": ["了解对方兴趣", "分享有趣经历"],
                "confidence": 0.5
            }

    def update_date_status(self, plan_id: str, status: str) -> bool:
        """
        更新约会状态

        Args:
            plan_id: 约会 ID
            status: 新状态（scheduled/completed/cancelled/postponed）

        Returns:
            是否成功
        """
        from models.date_reminder import DateReminderPlanDB

        plan = self.db.query(DateReminderPlanDB).filter(DateReminderPlanDB.id == plan_id).first()
        if not plan:
            return False

        plan.status = status
        if status == "completed":
            plan.completed_at = datetime.now()
        elif status == "cancelled":
            plan.cancelled_at = datetime.now()

        self.db.commit()
        return True

    def record_date_feedback(
        self,
        plan_id: str,
        user_id: str,
        rating: int,  # 1-5
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        记录约会反馈

        Args:
            plan_id: 约会 ID
            user_id: 用户 ID
            rating: 评分
            feedback: 反馈内容

        Returns:
            反馈记录
        """
        from models.date_reminder import DateFeedbackDB

        feedback_id = str(uuid.uuid4())

        feedback_record = DateFeedbackDB(
            id=feedback_id,
            plan_id=plan_id,
            user_id=user_id,
            rating=rating,
            feedback=feedback,
            created_at=datetime.now()
        )
        self.db.add(feedback_record)
        self.db.commit()

        return {
            "feedback_id": feedback_id,
            "plan_id": plan_id,
            "rating": rating,
            "feedback": feedback
        }


# 服务工厂函数
def get_date_reminder_service(db: Session) -> DateReminderService:
    """获取约会提醒服务实例"""
    return DateReminderService(db)