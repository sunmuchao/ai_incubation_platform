"""
P17 远程工作支持 - 服务层
版本：v17.0.0
日期：2026-04-05
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import random
from models.p17_models import (
    RemoteWorkSession, WorkMode, PresenceStatus as PresenceStatusEnum,
    VirtualWorkspace, WorkActivity, ActivityType, TeamEvent, TeamEventType,
    TimezoneCoordination, RemoteWorkMetrics, VirtualWaterCooler, RemoteWorkPolicy,
    RemoteWorkDB
)


# ==================== 远程工作会话服务 ====================

class RemoteWorkSessionService:
    """远程工作会话服务"""

    def __init__(self, db: RemoteWorkDB):
        self.db = db

    def start_session(self, employee_id: str, work_mode: str = WorkMode.REMOTE.value,
                      location: Optional[str] = None) -> RemoteWorkSession:
        """开始远程工作会话"""
        session = RemoteWorkSession(
            employee_id=employee_id,
            work_mode=work_mode,
            start_time=datetime.now(),
            location=location
        )
        return self.db.create_session(session)

    def end_session(self, session_id: str, notes: Optional[str] = None) -> Optional[RemoteWorkSession]:
        """结束远程工作会话"""
        session = self.db.get_session(session_id)
        if session:
            session.end_time = datetime.now()
            session.notes = notes
            # 计算持续时间并记录活动
            duration = session.end_time - session.start_time
            duration_minutes = int(duration.total_seconds() / 60)

            # 创建对应的活动记录
            activity = WorkActivity(
                employee_id=session.employee_id,
                activity_type=ActivityType.WORKING.value if session.work_mode == WorkMode.REMOTE.value else ActivityType.CODING,
                start_time=session.start_time,
                end_time=session.end_time,
                duration_minutes=duration_minutes,
                description=f"Remote work session: {session.location or 'Remote'}"
            )
            self.db.create_activity(activity)

            return self.db.update_session(session)
        return None

    def get_session(self, session_id: str) -> Optional[RemoteWorkSession]:
        """获取会话详情"""
        return self.db.get_session(session_id)

    def list_sessions(self, employee_id: str, limit: int = 100) -> List[RemoteWorkSession]:
        """列出员工的会话历史"""
        return self.db.list_sessions(employee_id, limit)

    def get_active_session(self, employee_id: str) -> Optional[RemoteWorkSession]:
        """获取员工当前活跃的会话"""
        sessions = self.db.list_sessions(employee_id, limit=1)
        if sessions and sessions[0].end_time is None:
            return sessions[0]
        return None


# ==================== 在线状态服务 ====================

class PresenceService:
    """在线状态服务"""

    def __init__(self, db: RemoteWorkDB):
        self.db = db

    def set_status(self, employee_id: str, status: str, work_mode: str = WorkMode.OFFICE.value,
                   status_message: Optional[str] = None,
                   until_minutes: Optional[int] = None,
                   timezone: Optional[str] = None) -> PresenceStatusEnum:
        """设置在线状态"""
        until_time = None
        if until_minutes:
            until_time = datetime.now() + timedelta(minutes=until_minutes)

        presence = PresenceStatusEnum(
            employee_id=employee_id,
            presence_status=status,
            work_mode=work_mode,
            status_message=status_message,
            until_time=until_time,
            location_timezone=timezone,
            last_heartbeat=datetime.now()
        )
        return self.db.set_presence(presence)

    def update_heartbeat(self, employee_id: str) -> Optional[PresenceStatusEnum]:
        """更新心跳"""
        presence = self.db.get_presence(employee_id)
        if presence:
            presence.last_heartbeat = datetime.now()
            presence.updated_at = datetime.now()
            return self.db.set_presence(presence)
        return None

    def get_status(self, employee_id: str) -> Optional[PresenceStatusEnum]:
        """获取员工在线状态"""
        return self.db.get_presence(employee_id)

    def get_all_status(self) -> List[PresenceStatusEnum]:
        """获取所有员工在线状态"""
        return self.db.list_all_presence()

    def get_available_employees(self) -> List[PresenceStatusEnum]:
        """获取可用状态的员工列表"""
        all_status = self.db.list_all_presence()
        return [s for s in all_status if s.presence_status == PresenceStatusEnum.AVAILABLE.value]

    def cleanup_expired_statuses(self) -> int:
        """清理过期的状态"""
        all_status = self.db.list_all_presence()
        count = 0
        now = datetime.now()
        for status in all_status:
            if status.until_time and status.until_time < now:
                # 过期了，恢复为可用状态
                status.presence_status = PresenceStatusEnum.AVAILABLE.value
                status.until_time = None
                status.updated_at = now
                self.db.set_presence(status)
                count += 1
        return count


# ==================== 虚拟工作空间服务 ====================

class VirtualWorkspaceService:
    """虚拟工作空间服务"""

    def __init__(self, db: RemoteWorkDB):
        self.db = db

    def create_workspace(self, name: str, owner_id: str,
                         workspace_type: str = "office",
                         capacity: int = 10,
                         description: Optional[str] = None,
                         is_private: bool = False,
                         amenities: Optional[List[str]] = None) -> VirtualWorkspace:
        """创建虚拟工作空间"""
        workspace = VirtualWorkspace(
            name=name,
            owner_id=owner_id,
            workspace_type=workspace_type,
            capacity=capacity,
            description=description,
            is_private=is_private,
            amenities=amenities or []
        )
        return self.db.create_workspace(workspace)

    def join_workspace(self, workspace_id: str, employee_id: str) -> Optional[VirtualWorkspace]:
        """加入虚拟工作空间"""
        workspace = self.db.get_workspace(workspace_id)
        if workspace:
            if len(workspace.current_occupants) >= workspace.capacity:
                raise ValueError("Workspace is at capacity")
            if employee_id not in workspace.current_occupants:
                workspace.current_occupants.append(employee_id)
                # 更新员工状态为在该空间
                presence_service = PresenceService(self.db)
                presence_service.set_status(
                    employee_id=employee_id,
                    status=PresenceStatusEnum.BUSY.value,
                    status_message=f"In {workspace.name}"
                )
            return self.db.update_workspace(workspace)
        return None

    def leave_workspace(self, workspace_id: str, employee_id: str) -> Optional[VirtualWorkspace]:
        """离开虚拟工作空间"""
        workspace = self.db.get_workspace(workspace_id)
        if workspace:
            if employee_id in workspace.current_occupants:
                workspace.current_occupants.remove(employee_id)
            return self.db.update_workspace(workspace)
        return None

    def get_workspace(self, workspace_id: str) -> Optional[VirtualWorkspace]:
        """获取虚拟工作空间"""
        return self.db.get_workspace(workspace_id)

    def list_workspaces(self, owner_id: Optional[str] = None,
                        workspace_type: Optional[str] = None) -> List[VirtualWorkspace]:
        """列出虚拟工作空间"""
        return self.db.list_workspaces(owner_id, workspace_type)

    def delete_workspace(self, workspace_id: str) -> bool:
        """删除虚拟工作空间"""
        return self.db.delete_workspace(workspace_id)


# ==================== 工作活动服务 ====================

class WorkActivityService:
    """工作活动服务"""

    def __init__(self, db: RemoteWorkDB):
        self.db = db

    def start_activity(self, employee_id: str, activity_type: str,
                       project_id: Optional[str] = None,
                       task_id: Optional[str] = None,
                       description: Optional[str] = None,
                       is_focus_time: bool = False) -> WorkActivity:
        """开始工作活动"""
        activity = WorkActivity(
            employee_id=employee_id,
            activity_type=activity_type,
            start_time=datetime.now(),
            project_id=project_id,
            task_id=task_id,
            description=description,
            is_focus_time=is_focus_time
        )
        return self.db.create_activity(activity)

    def end_activity(self, activity_id: str,
                     self_reported_productivity: Optional[int] = None) -> Optional[WorkActivity]:
        """结束工作活动"""
        activity = self.db.get_activity(activity_id)
        if activity:
            activity.end_time = datetime.now()
            duration = activity.end_time - activity.start_time
            activity.duration_minutes = int(duration.total_seconds() / 60)
            activity.self_reported_productivity = self_reported_productivity
            return self.db.create_activity(activity)  # Upsert
        return None

    def log_activity(self, employee_id: str, activity_type: str,
                     start_time: datetime, end_time: datetime,
                     duration_minutes: int,
                     project_id: Optional[str] = None,
                     description: Optional[str] = None,
                     is_focus_time: bool = False) -> WorkActivity:
        """记录已完成的活动"""
        activity = WorkActivity(
            employee_id=employee_id,
            activity_type=activity_type,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            project_id=project_id,
            description=description,
            is_focus_time=is_focus_time
        )
        return self.db.create_activity(activity)

    def get_activity(self, activity_id: str) -> Optional[WorkActivity]:
        """获取活动详情"""
        return self.db.get_activity(activity_id)

    def list_activities(self, employee_id: str,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> List[WorkActivity]:
        """列出活动记录"""
        return self.db.list_activities(employee_id, start_date, end_date)

    def calculate_daily_metrics(self, employee_id: str, date: str) -> RemoteWorkMetrics:
        """计算员工的每日工作指标"""
        start_dt = datetime.strptime(date, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=1)

        activities = self.db.list_activities(employee_id, start_dt, end_dt)

        total_minutes = 0
        focus_minutes = 0
        meeting_minutes = 0
        break_minutes = 0
        communication_minutes = 0

        for activity in activities:
            total_minutes += activity.duration_minutes
            if activity.is_focus_time:
                focus_minutes += activity.duration_minutes
            if activity.activity_type == ActivityType.MEETING.value:
                meeting_minutes += activity.duration_minutes
            elif activity.activity_type == ActivityType.BREAK.value:
                break_minutes += activity.duration_minutes
            elif activity.activity_type == ActivityType.COMMUNICATING.value:
                communication_minutes += activity.duration_minutes

        # 计算生产力分数 (简单算法)
        productivity_score = None
        if total_minutes > 0:
            focus_ratio = focus_minutes / total_minutes if total_minutes > 0 else 0
            # 生产力分数 = 专注时间占比 * 40 + 工作效率 * 60
            efficiency = min(1.0, total_minutes / 480)  # 8 小时为满分
            productivity_score = round(focus_ratio * 40 + efficiency * 60, 2)

        metrics = RemoteWorkMetrics(
            employee_id=employee_id,
            date=date,
            total_work_minutes=total_minutes,
            focus_time_minutes=focus_minutes,
            meeting_minutes=meeting_minutes,
            break_minutes=break_minutes,
            communication_minutes=communication_minutes,
            productivity_score=productivity_score,
            work_mode=WorkMode.REMOTE.value
        )
        return self.db.create_or_update_metrics(metrics)


# ==================== 团队活动服务 ====================

class TeamEventService:
    """团队活动服务"""

    def __init__(self, db: RemoteWorkDB):
        self.db = db

    def create_event(self, title: str, organizer_id: str,
                     event_type: str = TeamEventType.VIRTUAL_HAPPY_HOUR.value,
                     start_time: Optional[datetime] = None,
                     duration_minutes: int = 60,
                     description: Optional[str] = None,
                     virtual_workspace_id: Optional[str] = None,
                     meeting_link: Optional[str] = None,
                     is_recurring: bool = False,
                     recurrence_pattern: Optional[str] = None) -> TeamEvent:
        """创建团队活动"""
        event = TeamEvent(
            title=title,
            organizer_id=organizer_id,
            event_type=event_type,
            start_time=start_time or datetime.now(),
            duration_minutes=duration_minutes,
            description=description,
            virtual_workspace_id=virtual_workspace_id,
            meeting_link=meeting_link,
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern
        )
        return self.db.create_event(event)

    def rsvp(self, event_id: str, employee_id: str,
             status: str = "going") -> Optional[TeamEvent]:
        """回复活动邀请"""
        event = self.db.get_event(event_id)
        if event:
            event.rsvp_status[employee_id] = status
            if employee_id not in event.participants:
                event.participants.append(employee_id)
            return self.db.update_event(event)
        return None

    def add_participant(self, event_id: str, employee_id: str) -> Optional[TeamEvent]:
        """添加参与者"""
        event = self.db.get_event(event_id)
        if event:
            if employee_id not in event.participants:
                event.participants.append(employee_id)
            return self.db.update_event(event)
        return None

    def add_photo(self, event_id: str, photo_url: str) -> Optional[TeamEvent]:
        """添加活动照片"""
        event = self.db.get_event(event_id)
        if event:
            event.photos.append(photo_url)
            return self.db.update_event(event)
        return None

    def get_event(self, event_id: str) -> Optional[TeamEvent]:
        """获取活动详情"""
        return self.db.get_event(event_id)

    def list_events(self, organizer_id: Optional[str] = None,
                    upcoming_only: bool = False) -> List[TeamEvent]:
        """列出活动"""
        return self.db.list_events(organizer_id, upcoming_only)

    def get_rsvp_stats(self, event_id: str) -> Dict[str, int]:
        """获取活动回复统计"""
        event = self.db.get_event(event_id)
        if event:
            stats = {"going": 0, "not_going": 0, "maybe": 0}
            for status in event.rsvp_status.values():
                if status in stats:
                    stats[status] += 1
            return stats
        return {}


# ==================== 时区协调服务 ====================

class TimezoneCoordinationService:
    """时区协调服务"""

    # 常见时区偏移（小时）
    TIMEZONE_OFFSETS = {
        "UTC": 0,
        "America/New_York": -5,
        "America/Los_Angeles": -8,
        "America/Chicago": -6,
        "Europe/London": 0,
        "Europe/Paris": 1,
        "Europe/Berlin": 1,
        "Asia/Shanghai": 8,
        "Asia/Tokyo": 9,
        "Asia/Singapore": 8,
        "Australia/Sydney": 11,
    }

    def __init__(self, db: RemoteWorkDB):
        self.db = db

    def create_coordination(self, team_id: str,
                            members: List[Dict[str, Any]]) -> TimezoneCoordination:
        """创建时区协调记录"""
        coordination = TimezoneCoordination(
            team_id=team_id,
            members=members
        )
        # 自动计算重叠时间窗口
        coordination.overlap_windows = self._calculate_overlap_windows(members)
        # 推荐会议时间
        coordination.preferred_meeting_times = self._recommend_meeting_times(members)
        # 计算异步交接时间
        coordination.async_handoff_times = self._calculate_handoff_times(members)
        return self.db.create_coordination(coordination)

    def _calculate_overlap_windows(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """计算重叠工作时间窗口"""
        if not members:
            return []

        # 假设标准工作时间是 9:00-18:00
        working_hours_start = 9
        working_hours_end = 18

        # 找到所有时区的最小和最大偏移
        offsets = []
        for member in members:
            tz = member.get("timezone", "UTC")
            offset = self.TIMEZONE_OFFSETS.get(tz, 0)
            offsets.append(offset)

        min_offset = min(offsets)
        max_offset = max(offsets)

        # 计算 UTC 时间下的重叠窗口
        # 最早时区的工作时间结束 vs 最晚时区的工作时间开始
        overlap_start_utc = working_hours_end - min_offset
        overlap_end_utc = working_hours_start - max_offset

        if overlap_start_utc > overlap_end_utc:
            return []  # 没有重叠时间

        return [{
            "start_utc": f"{overlap_start_utc:02d}:00",
            "end_utc": f"{overlap_end_utc:02d}:00",
            "duration_hours": overlap_end_utc - overlap_start_utc,
            "participants": [m.get("employee_id") for m in members]
        }]

    def _recommend_meeting_times(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """推荐会议时间"""
        overlap_windows = self._calculate_overlap_windows(members)
        if not overlap_windows:
            # 如果没有重叠时间，推荐在边界时间
            return self._recommend_boundary_times(members)

        recommendations = []
        for window in overlap_windows:
            start_hour = int(window["start_utc"].split(":")[0])
            recommendations.append({
                "utc_time": f"{start_hour:02d}:00",
                "description": "Best overlap time for all team members",
                "local_times": self._convert_to_local_times(start_hour, members)
            })

        return recommendations

    def _recommend_boundary_times(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """推荐边界时间（当没有重叠时）"""
        recommendations = []
        # 推荐两个时间：一个适合早期时区，一个适合晚期时区
        recommendations.append({
            "utc_time": "14:00",
            "description": "Compromise time - morning for Americas, evening for Asia",
            "local_times": self._convert_to_local_times(14, members)
        })
        recommendations.append({
            "utc_time": "08:00",
            "description": "Compromise time - morning for Europe/Asia, evening for Americas",
            "local_times": self._convert_to_local_times(8, members)
        })
        return recommendations

    def _convert_to_local_times(self, utc_hour: int, members: List[Dict[str, Any]]) -> Dict[str, str]:
        """将 UTC 时间转换为各成员的本地时间"""
        local_times = {}
        for member in members:
            tz = member.get("timezone", "UTC")
            offset = self.TIMEZONE_OFFSETS.get(tz, 0)
            local_hour = (utc_hour + offset) % 24
            local_times[member.get("employee_id", "unknown")] = f"{local_hour:02d}:00 ({tz})"
        return local_times

    def _calculate_handoff_times(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """计算异步交接时间"""
        handoffs = []
        sorted_members = sorted(
            members,
            key=lambda m: self.TIMEZONE_OFFSETS.get(m.get("timezone", "UTC"), 0)
        )

        for i in range(len(sorted_members) - 1):
            current = sorted_members[i]
            next_member = sorted_members[i + 1]

            current_offset = self.TIMEZONE_OFFSETS.get(current.get("timezone", "UTC"), 0)
            next_offset = self.TIMEZONE_OFFSETS.get(next_member.get("timezone", "UTC"), 0)

            # 计算交接时间（当前时区下班时间 = 下一个时区的上班时间）
            handoff_utc = 18 - current_offset  # 当前时区 18:00 对应的 UTC 时间

            handoffs.append({
                "from_employee": current.get("employee_id"),
                "to_employee": next_member.get("employee_id"),
                "utc_time": f"{handoff_utc:02d}:00",
                "from_local": f"18:00 ({current.get('timezone', 'UTC')})",
                "to_local": self._format_local_time(handoff_utc, next_member.get("timezone", "UTC"))
            })

        return handoffs

    def _format_local_time(self, utc_hour: int, timezone: str) -> str:
        """格式化本地时间"""
        offset = self.TIMEZONE_OFFSETS.get(timezone, 0)
        local_hour = (utc_hour + offset) % 24
        return f"{local_hour:02d}:00 ({timezone})"

    def get_coordination(self, team_id: str) -> Optional[TimezoneCoordination]:
        """获取时区协调记录"""
        return self.db.get_coordination(team_id)

    def update_coordination(self, coordination: TimezoneCoordination) -> TimezoneCoordination:
        """更新时区协调记录"""
        return self.db.update_coordination(coordination)


# ==================== 虚拟茶水间服务 ====================

class VirtualWaterCoolerService:
    """虚拟茶水间服务"""

    def __init__(self, db: RemoteWorkDB):
        self.db = db

    def start_chat(self, initiator_id: str, topic: Optional[str] = None,
                   workspace_id: Optional[str] = None) -> VirtualWaterCooler:
        """发起茶水间聊天"""
        cooler = VirtualWaterCooler(
            topic=topic,
            initiator_id=initiator_id,
            participants=[initiator_id],
            workspace_id=workspace_id
        )
        return self.db.create_water_cooler(cooler)

    def join_chat(self, chat_id: str, employee_id: str) -> Optional[VirtualWaterCooler]:
        """加入茶水间聊天"""
        cooler = self.db.get_water_cooler(chat_id)
        if cooler:
            if employee_id not in cooler.participants:
                cooler.participants.append(employee_id)
            return self.db.update_water_cooler(cooler)
        return None

    def add_message(self, chat_id: str, sender_id: str,
                    content: str) -> Optional[VirtualWaterCooler]:
        """添加消息"""
        cooler = self.db.get_water_cooler(chat_id)
        if cooler:
            cooler.messages.append({
                "sender_id": sender_id,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            return self.db.update_water_cooler(cooler)
        return None

    def end_chat(self, chat_id: str) -> Optional[VirtualWaterCooler]:
        """结束茶水间聊天"""
        cooler = self.db.get_water_cooler(chat_id)
        if cooler:
            cooler.is_active = False
            cooler.ended_at = datetime.now()
            return self.db.update_water_cooler(cooler)
        return None

    def get_chat(self, chat_id: str) -> Optional[VirtualWaterCooler]:
        """获取茶水间聊天"""
        return self.db.get_water_cooler(chat_id)

    def list_active_chats(self) -> List[VirtualWaterCooler]:
        """列出活跃的茶水间聊天"""
        return self.db.list_active_water_coolers()


# ==================== 远程工作政策服务 ====================

class RemoteWorkPolicyService:
    """远程工作政策服务"""

    def __init__(self, db: RemoteWorkDB):
        self.db = db

    def create_policy(self, organization_id: str, name: str,
                      description: Optional[str] = None,
                      remote_days_required: int = 0,
                      office_days_required: int = 0,
                      core_hours_start: Optional[str] = None,
                      core_hours_end: Optional[str] = None,
                      allowed_countries: Optional[List[str]] = None,
                      equipment_allowance: Optional[float] = None,
                      internet_allowance: Optional[float] = None) -> RemoteWorkPolicy:
        """创建远程工作政策"""
        policy = RemoteWorkPolicy(
            organization_id=organization_id,
            name=name,
            description=description,
            remote_days_required=remote_days_required,
            office_days_required=office_days_required,
            core_hours_start=core_hours_start,
            core_hours_end=core_hours_end,
            allowed_countries=allowed_countries or [],
            equipment_allowance=equipment_allowance,
            internet_allowance=internet_allowance
        )
        return self.db.create_policy(policy)

    def get_policy(self, policy_id: str) -> Optional[RemoteWorkPolicy]:
        """获取远程工作政策"""
        return self.db.get_policy(policy_id)

    def list_policies(self, organization_id: str) -> List[RemoteWorkPolicy]:
        """列出组织的远程工作政策"""
        return self.db.list_policies(organization_id)

    def check_compliance(self, employee_id: str, policy: RemoteWorkPolicy,
                         week_start: datetime) -> Dict[str, Any]:
        """检查员工是否符合政策要求"""
        # 获取该周的会话记录
        session_service = RemoteWorkSessionService(self.db)
        sessions = session_service.list_sessions(employee_id, limit=100)

        # 统计远程和办公室天数
        remote_days = set()
        office_days = set()

        for session in sessions:
            if session.start_time and session.start_time >= week_start:
                date_str = session.start_time.strftime("%Y-%m-%d")
                if session.work_mode == WorkMode.REMOTE.value:
                    remote_days.add(date_str)
                elif session.work_mode == WorkMode.OFFICE.value:
                    office_days.add(date_str)

        compliance = {
            "employee_id": employee_id,
            "week_start": week_start.strftime("%Y-%m-%d"),
            "remote_days": len(remote_days),
            "office_days": len(office_days),
            "remote_required": policy.remote_days_required,
            "office_required": policy.office_days_required,
            "remote_compliant": len(remote_days) >= policy.remote_days_required if policy.remote_days_required > 0 else True,
            "office_compliant": len(office_days) >= policy.office_days_required if policy.office_days_required > 0 else True,
            "overall_compliant": True
        }

        compliance["overall_compliant"] = compliance["remote_compliant"] and compliance["office_compliant"]

        return compliance


# ==================== 远程工作指标服务 ====================

class RemoteWorkMetricsService:
    """远程工作指标服务"""

    def __init__(self, db: RemoteWorkDB):
        self.db = db

    def get_daily_metrics(self, employee_id: str, date: str) -> Optional[RemoteWorkMetrics]:
        """获取每日指标"""
        return self.db.get_metrics(employee_id, date)

    def get_weekly_metrics(self, employee_id: str, week_start: datetime) -> Dict[str, Any]:
        """获取每周指标汇总"""
        start_date = week_start.strftime("%Y-%m-%d")
        end_date = (week_start + timedelta(days=6)).strftime("%Y-%m-%d")

        metrics_list = self.db.list_metrics(employee_id, start_date, end_date)

        if not metrics_list:
            return {
                "employee_id": employee_id,
                "week_start": start_date,
                "total_work_minutes": 0,
                "avg_daily_minutes": 0,
                "total_focus_minutes": 0,
                "total_meeting_minutes": 0,
                "avg_productivity_score": None,
                "days_worked": 0
            }

        total_work = sum(m.total_work_minutes for m in metrics_list)
        total_focus = sum(m.focus_time_minutes for m in metrics_list)
        total_meeting = sum(m.meeting_minutes for m in metrics_list)
        productivity_scores = [m.productivity_score for m in metrics_list if m.productivity_score is not None]
        avg_productivity = sum(productivity_scores) / len(productivity_scores) if productivity_scores else None

        return {
            "employee_id": employee_id,
            "week_start": start_date,
            "total_work_minutes": total_work,
            "avg_daily_minutes": total_work // len(metrics_list) if metrics_list else 0,
            "total_focus_minutes": total_focus,
            "total_meeting_minutes": total_meeting,
            "avg_productivity_score": round(avg_productivity, 2) if avg_productivity else None,
            "days_worked": len(metrics_list)
        }

    def get_team_metrics(self, employee_ids: List[str], date: str) -> List[Dict[str, Any]]:
        """获取团队指标"""
        team_metrics = []
        for emp_id in employee_ids:
            metrics = self.db.get_metrics(emp_id, date)
            if metrics:
                team_metrics.append(metrics.to_dict())
        return team_metrics


# ==================== 统一外观服务 ====================

class RemoteWorkService:
    """远程工作统一外观服务"""

    def __init__(self, db_path: str = "test.db"):
        self.db = RemoteWorkDB(db_path)
        self.session_service = RemoteWorkSessionService(self.db)
        self.presence_service = PresenceService(self.db)
        self.workspace_service = VirtualWorkspaceService(self.db)
        self.activity_service = WorkActivityService(self.db)
        self.event_service = TeamEventService(self.db)
        self.timezone_service = TimezoneCoordinationService(self.db)
        self.water_cooler_service = VirtualWaterCoolerService(self.db)
        self.policy_service = RemoteWorkPolicyService(self.db)
        self.metrics_service = RemoteWorkMetricsService(self.db)

    def get_dashboard(self, employee_id: str) -> Dict[str, Any]:
        """获取远程工作仪表盘"""
        # 获取当前状态
        presence = self.presence_service.get_status(employee_id)

        # 获取今日指标
        today = datetime.now().strftime("%Y-%m-%d")
        metrics = self.metrics_service.get_daily_metrics(employee_id, today)

        # 获取活跃会话
        active_session = self.session_service.get_active_session(employee_id)

        # 获取即将开始的活动
        upcoming_events = self.event_service.list_events(upcoming_only=True)[:3]

        # 获取活跃的茶水间聊天
        active_chats = self.water_cooler_service.list_active_chats()[:3]

        return {
            "employee_id": employee_id,
            "presence": presence.to_dict() if presence else None,
            "today_metrics": metrics.to_dict() if metrics else None,
            "active_session": active_session.to_dict() if active_session else None,
            "upcoming_events": [e.to_dict() for e in upcoming_events],
            "active_water_coolers": [c.to_dict() for c in active_chats]
        }

    def close(self):
        """关闭数据库连接"""
        self.db.close()
