"""
P17 远程工作支持 - 数据模型层
版本：v17.0.0
日期：2026-04-05
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import sqlite3
import uuid
import json


# ==================== 枚举定义 ====================

class PresenceStatus(str, Enum):
    """在线状态"""
    AVAILABLE = "available"  # 可用
    BUSY = "busy"  # 忙碌
    IN_MEETING = "in_meeting"  # 会议中
    ON_BREAK = "on_break"  # 休息中
    OFFLINE = "offline"  # 离线
    DO_NOT_DISTURB = "do_not_disturb"  # 请勿打扰
    REMOTE_WORKING = "remote_working"  # 远程工作中


class WorkMode(str, Enum):
    """工作模式"""
    OFFICE = "office"  # 办公室
    REMOTE = "remote"  # 远程
    HYBRID = "hybrid"  # 混合
    TRAVELING = "traveling"  # 出差


class MeetingType(str, Enum):
    """会议类型"""
    STANDUP = "standup"  # 站会
    TEAM_MEETING = "team_meeting"  # 团队会议
    ONE_ON_ONE = "one_on_one"  # 1 对 1 会议
    CLIENT_CALL = "client_call"  # 客户电话
    TRAINING = "training"  # 培训
    SOCIAL = "social"  # 社交
    BRAINSTORMING = "brainstorming"  # 头脑风暴


class ActivityType(str, Enum):
    """活动类型"""
    CODING = "coding"  # 编码
    MEETING = "meeting"  # 会议
    EMAIL = "email"  # 邮件
    DOCUMENTATION = "documentation"  # 文档
    REVIEW = "review"  # 评审
    PLANNING = "planning"  # 计划
    BREAK = "break"  # 休息
    LEARNING = "learning"  # 学习
    COMMUNICATING = "communicating"  # 沟通
    WORKING = "working"  # 一般工作


class TeamEventType(str, Enum):
    """团队活动类型"""
    VIRTUAL_HAPPY_HOUR = "virtual_happy_hour"  # 虚拟欢乐时光
    TEAM_BUILDING = "team_building"  # 团建
    SHOW_AND_TELL = "show_and_tell"  # 展示与分享
    CELEBRATION = "celebration"  # 庆祝活动
    WELLNESS_CHECK = "wellness_check"  # 健康检查
    COFFEE_CHAT = "coffee_chat"  # 咖啡聊天
    GAME_NIGHT = "game_night"  # 游戏之夜


class NotificationPreference(str, Enum):
    """通知偏好"""
    IMMEDIATE = "immediate"  # 立即
    DIGEST_HOURLY = "digest_hourly"  # 每小时汇总
    DIGEST_DAILY = "digest_daily"  # 每日汇总
    QUIET_HOURS = "quiet_hours"  # 安静时段


# ==================== 数据模型 ====================

@dataclass
class RemoteWorkSession:
    """远程工作会话"""
    employee_id: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_mode: str = WorkMode.REMOTE.value
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None  # 工作地点描述
    internet_quality: Optional[str] = None  # 网络质量 (excellent/good/fair/poor)
    setup_quality: Optional[str] = None  # 工作环境质量
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "session_id": self.session_id,
            "work_mode": self.work_mode,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "location": self.location,
            "internet_quality": self.internet_quality,
            "setup_quality": self.setup_quality,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RemoteWorkSession":
        return cls(
            employee_id=data["employee_id"],
            session_id=data.get("session_id", str(uuid.uuid4())),
            work_mode=data.get("work_mode", WorkMode.REMOTE.value),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            location=data.get("location"),
            internet_quality=data.get("internet_quality"),
            setup_quality=data.get("setup_quality"),
            notes=data.get("notes"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


@dataclass
class PresenceStatus:
    """在线状态记录"""
    employee_id: str
    status_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    presence_status: str = PresenceStatus.AVAILABLE.value
    work_mode: str = WorkMode.OFFICE.value
    status_message: Optional[str] = None  # 状态消息
    until_time: Optional[datetime] = None  # 状态持续时间
    location_timezone: Optional[str] = None  # 所在时区
    last_heartbeat: Optional[datetime] = None  # 最后心跳时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "status_id": self.status_id,
            "presence_status": self.presence_status,
            "work_mode": self.work_mode,
            "status_message": self.status_message,
            "until_time": self.until_time.isoformat() if self.until_time else None,
            "location_timezone": self.location_timezone,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PresenceStatus":
        return cls(
            employee_id=data["employee_id"],
            status_id=data.get("status_id", str(uuid.uuid4())),
            presence_status=data.get("presence_status", PresenceStatus.AVAILABLE.value),
            work_mode=data.get("work_mode", WorkMode.OFFICE.value),
            status_message=data.get("status_message"),
            until_time=datetime.fromisoformat(data["until_time"]) if data.get("until_time") else None,
            location_timezone=data.get("location_timezone"),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]) if data.get("last_heartbeat") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


@dataclass
class VirtualWorkspace:
    """虚拟工作空间"""
    workspace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    owner_id: str = ""  # 创建者 ID
    workspace_type: str = "office"  # office/meeting_room/lounge/focus_room
    capacity: int = 10  # 最大容量
    current_occupants: List[str] = field(default_factory=list)  # 当前占用者 ID 列表
    is_private: bool = False  # 是否私密空间
    amenities: List[str] = field(default_factory=list)  # 设施 (whiteboard/screen/recording/etc)
    background_image: Optional[str] = None
    background_sound: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "workspace_type": self.workspace_type,
            "capacity": self.capacity,
            "current_occupants": self.current_occupants,
            "is_private": self.is_private,
            "amenities": self.amenities,
            "background_image": self.background_image,
            "background_sound": self.background_sound,
            "settings": self.settings,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VirtualWorkspace":
        return cls(
            workspace_id=data.get("workspace_id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description"),
            owner_id=data.get("owner_id", ""),
            workspace_type=data.get("workspace_type", "office"),
            capacity=data.get("capacity", 10),
            current_occupants=data.get("current_occupants", []),
            is_private=data.get("is_private", False),
            amenities=data.get("amenities", []),
            background_image=data.get("background_image"),
            background_sound=data.get("background_sound"),
            settings=data.get("settings", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


@dataclass
class WorkActivity:
    """工作活动记录"""
    employee_id: str
    activity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    activity_type: str = ActivityType.CODING.value
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_minutes: int = 0  # 自动计算
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    description: Optional[str] = None
    is_focus_time: bool = False  # 是否专注时间
    interruption_count: int = 0  # 被打断次数
    self_reported_productivity: Optional[int] = None  # 自我报告生产力 (1-10)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "activity_id": self.activity_id,
            "activity_type": self.activity_type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "description": self.description,
            "is_focus_time": self.is_focus_time,
            "interruption_count": self.interruption_count,
            "self_reported_productivity": self.self_reported_productivity,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkActivity":
        return cls(
            employee_id=data["employee_id"],
            activity_id=data.get("activity_id", str(uuid.uuid4())),
            activity_type=data.get("activity_type", ActivityType.CODING.value),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else datetime.now(),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            duration_minutes=data.get("duration_minutes", 0),
            project_id=data.get("project_id"),
            task_id=data.get("task_id"),
            description=data.get("description"),
            is_focus_time=data.get("is_focus_time", False),
            interruption_count=data.get("interruption_count", 0),
            self_reported_productivity=data.get("self_reported_productivity"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )


@dataclass
class TeamEvent:
    """团队活动/虚拟团建"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: Optional[str] = None
    event_type: str = TeamEventType.VIRTUAL_HAPPY_HOUR.value
    organizer_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_minutes: int = 60
    virtual_workspace_id: Optional[str] = None
    meeting_link: Optional[str] = None
    participants: List[str] = field(default_factory=list)  # 参与者 ID
    rsvp_status: Dict[str, str] = field(default_factory=dict)  # {employee_id: "going"/"not_going"/"maybe"}
    photos: List[str] = field(default_factory=list)  # 活动照片 URL 列表
    notes: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # weekly/biweekly/monthly
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type,
            "organizer_id": self.organizer_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "virtual_workspace_id": self.virtual_workspace_id,
            "meeting_link": self.meeting_link,
            "participants": self.participants,
            "rsvp_status": self.rsvp_status,
            "photos": self.photos,
            "notes": self.notes,
            "is_recurring": self.is_recurring,
            "recurrence_pattern": self.recurrence_pattern,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamEvent":
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description"),
            event_type=data.get("event_type", TeamEventType.VIRTUAL_HAPPY_HOUR.value),
            organizer_id=data.get("organizer_id", ""),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else datetime.now(),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            duration_minutes=data.get("duration_minutes", 60),
            virtual_workspace_id=data.get("virtual_workspace_id"),
            meeting_link=data.get("meeting_link"),
            participants=data.get("participants", []),
            rsvp_status=data.get("rsvp_status", {}),
            photos=data.get("photos", []),
            notes=data.get("notes"),
            is_recurring=data.get("is_recurring", False),
            recurrence_pattern=data.get("recurrence_pattern"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


@dataclass
class TimezoneCoordination:
    """时区协调记录"""
    coordination_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    team_id: str = ""
    members: List[Dict[str, Any]] = field(default_factory=list)  # [{employee_id, timezone, working_hours}]
    overlap_windows: List[Dict[str, Any]] = field(default_factory=list)  # 重叠时间窗口
    preferred_meeting_times: List[Dict[str, Any]] = field(default_factory=list)  # 推荐会议时间
    async_handoff_times: List[Dict[str, Any]] = field(default_factory=list)  # 异步交接时间
    holiday_calendars: Dict[str, List[str]] = field(default_factory=dict)  # {country: [holidays]}
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coordination_id": self.coordination_id,
            "team_id": self.team_id,
            "members": self.members,
            "overlap_windows": self.overlap_windows,
            "preferred_meeting_times": self.preferred_meeting_times,
            "async_handoff_times": self.async_handoff_times,
            "holiday_calendars": self.holiday_calendars,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimezoneCoordination":
        return cls(
            coordination_id=data.get("coordination_id", str(uuid.uuid4())),
            team_id=data.get("team_id", ""),
            members=data.get("members", []),
            overlap_windows=data.get("overlap_windows", []),
            preferred_meeting_times=data.get("preferred_meeting_times", []),
            async_handoff_times=data.get("async_handoff_times", []),
            holiday_calendars=data.get("holiday_calendars", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


@dataclass
class RemoteWorkMetrics:
    """远程工作指标"""
    metrics_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str = ""
    date: str = ""  # YYYY-MM-DD
    total_work_minutes: int = 0
    focus_time_minutes: int = 0
    meeting_minutes: int = 0
    break_minutes: int = 0
    communication_minutes: int = 0
    productivity_score: Optional[float] = None  # 0-100
    work_mode: str = WorkMode.REMOTE.value
    location: Optional[str] = None
    internet_issues_count: int = 0
    self_reported_wellbeing: Optional[int] = None  # 1-10
    manager_notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics_id": self.metrics_id,
            "employee_id": self.employee_id,
            "date": self.date,
            "total_work_minutes": self.total_work_minutes,
            "focus_time_minutes": self.focus_time_minutes,
            "meeting_minutes": self.meeting_minutes,
            "break_minutes": self.break_minutes,
            "communication_minutes": self.communication_minutes,
            "productivity_score": self.productivity_score,
            "work_mode": self.work_mode,
            "location": self.location,
            "internet_issues_count": self.internet_issues_count,
            "self_reported_wellbeing": self.self_reported_wellbeing,
            "manager_notes": self.manager_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RemoteWorkMetrics":
        return cls(
            metrics_id=data.get("metrics_id", str(uuid.uuid4())),
            employee_id=data.get("employee_id", ""),
            date=data.get("date", ""),
            total_work_minutes=data.get("total_work_minutes", 0),
            focus_time_minutes=data.get("focus_time_minutes", 0),
            meeting_minutes=data.get("meeting_minutes", 0),
            break_minutes=data.get("break_minutes", 0),
            communication_minutes=data.get("communication_minutes", 0),
            productivity_score=data.get("productivity_score"),
            work_mode=data.get("work_mode", WorkMode.REMOTE.value),
            location=data.get("location"),
            internet_issues_count=data.get("internet_issues_count", 0),
            self_reported_wellbeing=data.get("self_reported_wellbeing"),
            manager_notes=data.get("manager_notes"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


@dataclass
class VirtualWaterCooler:
    """虚拟茶水间聊天"""
    chat_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: Optional[str] = None
    initiator_id: str = ""
    participants: List[str] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)  # [{sender_id, content, timestamp}]
    is_active: bool = True
    workspace_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chat_id": self.chat_id,
            "topic": self.topic,
            "initiator_id": self.initiator_id,
            "participants": self.participants,
            "messages": self.messages,
            "is_active": self.is_active,
            "workspace_id": self.workspace_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VirtualWaterCooler":
        return cls(
            chat_id=data.get("chat_id", str(uuid.uuid4())),
            topic=data.get("topic"),
            initiator_id=data.get("initiator_id", ""),
            participants=data.get("participants", []),
            messages=data.get("messages", []),
            is_active=data.get("is_active", True),
            workspace_id=data.get("workspace_id"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else datetime.now(),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )


@dataclass
class RemoteWorkPolicy:
    """远程工作政策"""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str = ""
    name: str = ""
    description: Optional[str] = None
    remote_days_required: int = 0  # 每周最少远程天数
    office_days_required: int = 0  # 每周最少办公室天数
    core_hours_start: Optional[str] = None  # 核心工作时间开始 (如 "10:00")
    core_hours_end: Optional[str] = None  # 核心工作时间结束 (如 "16:00")
    allowed_countries: List[str] = field(default_factory=list)  # 允许远程的国家
    timezone_restrictions: List[str] = field(default_factory=list)  # 时区限制
    equipment_allowance: Optional[float] = None  # 设备补贴
    internet_allowance: Optional[float] = None  # 网络补贴
    check_in_required: bool = True  # 是否需要签到
    meeting_requirements: Dict[str, Any] = field(default_factory=dict)  # 会议要求
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "organization_id": self.organization_id,
            "name": self.name,
            "description": self.description,
            "remote_days_required": self.remote_days_required,
            "office_days_required": self.office_days_required,
            "core_hours_start": self.core_hours_start,
            "core_hours_end": self.core_hours_end,
            "allowed_countries": self.allowed_countries,
            "timezone_restrictions": self.timezone_restrictions,
            "equipment_allowance": self.equipment_allowance,
            "internet_allowance": self.internet_allowance,
            "check_in_required": self.check_in_required,
            "meeting_requirements": self.meeting_requirements,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RemoteWorkPolicy":
        return cls(
            policy_id=data.get("policy_id", str(uuid.uuid4())),
            organization_id=data.get("organization_id", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            remote_days_required=data.get("remote_days_required", 0),
            office_days_required=data.get("office_days_required", 0),
            core_hours_start=data.get("core_hours_start"),
            core_hours_end=data.get("core_hours_end"),
            allowed_countries=data.get("allowed_countries", []),
            timezone_restrictions=data.get("timezone_restrictions", []),
            equipment_allowance=data.get("equipment_allowance"),
            internet_allowance=data.get("internet_allowance"),
            check_in_required=data.get("check_in_required", True),
            meeting_requirements=data.get("meeting_requirements", {}),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


# ==================== 数据库持久化层 ====================

class RemoteWorkDB:
    """远程工作数据库持久化层"""

    def __init__(self, db_path: str = "test.db"):
        self.db_path = db_path
        self.conn = None
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（单例模式）"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def _init_tables(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 远程工作会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p17_remote_work_sessions (
                session_id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                work_mode TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                internet_quality TEXT,
                setup_quality TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 在线状态表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p17_presence_status (
                status_id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL UNIQUE,
                presence_status TEXT NOT NULL,
                work_mode TEXT NOT NULL,
                status_message TEXT,
                until_time TEXT,
                location_timezone TEXT,
                last_heartbeat TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 虚拟工作空间表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p17_virtual_workspaces (
                workspace_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                owner_id TEXT NOT NULL,
                workspace_type TEXT NOT NULL,
                capacity INTEGER DEFAULT 10,
                current_occupants TEXT DEFAULT '[]',
                is_private INTEGER DEFAULT 0,
                amenities TEXT DEFAULT '[]',
                background_image TEXT,
                background_sound TEXT,
                settings TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 工作活动表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p17_work_activities (
                activity_id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_minutes INTEGER DEFAULT 0,
                project_id TEXT,
                task_id TEXT,
                description TEXT,
                is_focus_time INTEGER DEFAULT 0,
                interruption_count INTEGER DEFAULT 0,
                self_reported_productivity INTEGER,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)

        # 团队活动表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p17_team_events (
                event_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                event_type TEXT NOT NULL,
                organizer_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_minutes INTEGER DEFAULT 60,
                virtual_workspace_id TEXT,
                meeting_link TEXT,
                participants TEXT DEFAULT '[]',
                rsvp_status TEXT DEFAULT '{}',
                photos TEXT DEFAULT '[]',
                notes TEXT,
                is_recurring INTEGER DEFAULT 0,
                recurrence_pattern TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 时区协调表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p17_timezone_coordinations (
                coordination_id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                members TEXT DEFAULT '[]',
                overlap_windows TEXT DEFAULT '[]',
                preferred_meeting_times TEXT DEFAULT '[]',
                async_handoff_times TEXT DEFAULT '[]',
                holiday_calendars TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 远程工作指标表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p17_remote_work_metrics (
                metrics_id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                date TEXT NOT NULL,
                total_work_minutes INTEGER DEFAULT 0,
                focus_time_minutes INTEGER DEFAULT 0,
                meeting_minutes INTEGER DEFAULT 0,
                break_minutes INTEGER DEFAULT 0,
                communication_minutes INTEGER DEFAULT 0,
                productivity_score REAL,
                work_mode TEXT NOT NULL,
                location TEXT,
                internet_issues_count INTEGER DEFAULT 0,
                self_reported_wellbeing INTEGER,
                manager_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(employee_id, date)
            )
        """)

        # 虚拟茶水间聊天表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p17_virtual_water_cooler (
                chat_id TEXT PRIMARY KEY,
                topic TEXT,
                initiator_id TEXT NOT NULL,
                participants TEXT DEFAULT '[]',
                messages TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 1,
                workspace_id TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 远程工作政策表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p17_remote_work_policies (
                policy_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                remote_days_required INTEGER DEFAULT 0,
                office_days_required INTEGER DEFAULT 0,
                core_hours_start TEXT,
                core_hours_end TEXT,
                allowed_countries TEXT DEFAULT '[]',
                timezone_restrictions TEXT DEFAULT '[]',
                equipment_allowance REAL,
                internet_allowance REAL,
                check_in_required INTEGER DEFAULT 1,
                meeting_requirements TEXT DEFAULT '{}',
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p17_sessions_employee ON p17_remote_work_sessions(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p17_presence_employee ON p17_presence_status(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p17_activities_employee ON p17_work_activities(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p17_activities_date ON p17_work_activities(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p17_events_organizer ON p17_team_events(organizer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p17_metrics_employee_date ON p17_remote_work_metrics(employee_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p17_policies_org ON p17_remote_work_policies(organization_id)")

        conn.commit()

    # ==================== RemoteWorkSession CRUD ====================

    def create_session(self, session: RemoteWorkSession) -> RemoteWorkSession:
        """创建远程工作会话"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO p17_remote_work_sessions
            (session_id, employee_id, work_mode, start_time, end_time, location, internet_quality, setup_quality, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.employee_id,
            session.work_mode,
            session.start_time.isoformat() if session.start_time else None,
            session.end_time.isoformat() if session.end_time else None,
            session.location,
            session.internet_quality,
            session.setup_quality,
            session.notes,
            session.created_at.isoformat(),
            session.updated_at.isoformat()
        ))
        conn.commit()
        return session

    def get_session(self, session_id: str) -> Optional[RemoteWorkSession]:
        """获取远程工作会话"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_remote_work_sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return RemoteWorkSession(
                session_id=row["session_id"],
                employee_id=row["employee_id"],
                work_mode=row["work_mode"],
                start_time=datetime.fromisoformat(row["start_time"]) if row["start_time"] else None,
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                location=row["location"],
                internet_quality=row["internet_quality"],
                setup_quality=row["setup_quality"],
                notes=row["notes"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
        return None

    def update_session(self, session: RemoteWorkSession) -> RemoteWorkSession:
        """更新远程工作会话"""
        session.updated_at = datetime.now()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE p17_remote_work_sessions
            SET end_time=?, location=?, internet_quality=?, setup_quality=?, notes=?, updated_at=?
            WHERE session_id=?
        """, (
            session.end_time.isoformat() if session.end_time else None,
            session.location,
            session.internet_quality,
            session.setup_quality,
            session.notes,
            session.updated_at.isoformat(),
            session.session_id
        ))
        conn.commit()
        return session

    def list_sessions(self, employee_id: str, limit: int = 100) -> List[RemoteWorkSession]:
        """列出员工的远程工作会话"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM p17_remote_work_sessions
            WHERE employee_id=?
            ORDER BY created_at DESC
            LIMIT ?
        """, (employee_id, limit))
        rows = cursor.fetchall()
        return [
            RemoteWorkSession(
                session_id=row["session_id"],
                employee_id=row["employee_id"],
                work_mode=row["work_mode"],
                start_time=datetime.fromisoformat(row["start_time"]) if row["start_time"] else None,
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                location=row["location"],
                internet_quality=row["internet_quality"],
                setup_quality=row["setup_quality"],
                notes=row["notes"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
            for row in rows
        ]

    # ==================== PresenceStatus CRUD ====================

    def set_presence(self, presence: PresenceStatus) -> PresenceStatus:
        """设置在线状态（Upsert）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO p17_presence_status
            (status_id, employee_id, presence_status, work_mode, status_message, until_time, location_timezone, last_heartbeat, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            presence.status_id,
            presence.employee_id,
            presence.presence_status,
            presence.work_mode,
            presence.status_message,
            presence.until_time.isoformat() if presence.until_time else None,
            presence.location_timezone,
            presence.last_heartbeat.isoformat() if presence.last_heartbeat else None,
            presence.created_at.isoformat(),
            presence.updated_at.isoformat()
        ))
        conn.commit()
        return presence

    def get_presence(self, employee_id: str) -> Optional[PresenceStatus]:
        """获取员工在线状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_presence_status WHERE employee_id = ?", (employee_id,))
        row = cursor.fetchone()
        if row:
            return PresenceStatus(
                status_id=row["status_id"],
                employee_id=row["employee_id"],
                presence_status=row["presence_status"],
                work_mode=row["work_mode"],
                status_message=row["status_message"],
                until_time=datetime.fromisoformat(row["until_time"]) if row["until_time"] else None,
                location_timezone=row["location_timezone"],
                last_heartbeat=datetime.fromisoformat(row["last_heartbeat"]) if row["last_heartbeat"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
        return None

    def list_all_presence(self) -> List[PresenceStatus]:
        """列出所有员工的在线状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_presence_status")
        rows = cursor.fetchall()
        return [
            PresenceStatus(
                status_id=row["status_id"],
                employee_id=row["employee_id"],
                presence_status=row["presence_status"],
                work_mode=row["work_mode"],
                status_message=row["status_message"],
                until_time=datetime.fromisoformat(row["until_time"]) if row["until_time"] else None,
                location_timezone=row["location_timezone"],
                last_heartbeat=datetime.fromisoformat(row["last_heartbeat"]) if row["last_heartbeat"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
            for row in rows
        ]

    # ==================== VirtualWorkspace CRUD ====================

    def create_workspace(self, workspace: VirtualWorkspace) -> VirtualWorkspace:
        """创建虚拟工作空间"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO p17_virtual_workspaces
            (workspace_id, name, description, owner_id, workspace_type, capacity, current_occupants, is_private, amenities, background_image, background_sound, settings, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workspace.workspace_id,
            workspace.name,
            workspace.description,
            workspace.owner_id,
            workspace.workspace_type,
            workspace.capacity,
            json.dumps(workspace.current_occupants),
            1 if workspace.is_private else 0,
            json.dumps(workspace.amenities),
            workspace.background_image,
            workspace.background_sound,
            json.dumps(workspace.settings),
            workspace.created_at.isoformat(),
            workspace.updated_at.isoformat()
        ))
        conn.commit()
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[VirtualWorkspace]:
        """获取虚拟工作空间"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_virtual_workspaces WHERE workspace_id = ?", (workspace_id,))
        row = cursor.fetchone()
        if row:
            return VirtualWorkspace(
                workspace_id=row["workspace_id"],
                name=row["name"],
                description=row["description"],
                owner_id=row["owner_id"],
                workspace_type=row["workspace_type"],
                capacity=row["capacity"],
                current_occupants=json.loads(row["current_occupants"]),
                is_private=bool(row["is_private"]),
                amenities=json.loads(row["amenities"]),
                background_image=row["background_image"],
                background_sound=row["background_sound"],
                settings=json.loads(row["settings"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
        return None

    def update_workspace(self, workspace: VirtualWorkspace) -> VirtualWorkspace:
        """更新虚拟工作空间"""
        workspace.updated_at = datetime.now()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE p17_virtual_workspaces
            SET name=?, description=?, workspace_type=?, capacity=?, current_occupants=?, is_private=?, amenities=?, background_image=?, background_sound=?, settings=?, updated_at=?
            WHERE workspace_id=?
        """, (
            workspace.name,
            workspace.description,
            workspace.workspace_type,
            workspace.capacity,
            json.dumps(workspace.current_occupants),
            1 if workspace.is_private else 0,
            json.dumps(workspace.amenities),
            workspace.background_image,
            workspace.background_sound,
            json.dumps(workspace.settings),
            workspace.updated_at.isoformat(),
            workspace.workspace_id
        ))
        conn.commit()
        return workspace

    def delete_workspace(self, workspace_id: str) -> bool:
        """删除虚拟工作空间"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM p17_virtual_workspaces WHERE workspace_id = ?", (workspace_id,))
        conn.commit()
        return cursor.rowcount > 0

    def list_workspaces(self, owner_id: Optional[str] = None, workspace_type: Optional[str] = None) -> List[VirtualWorkspace]:
        """列出虚拟工作空间"""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM p17_virtual_workspaces WHERE 1=1"
        params = []
        if owner_id:
            query += " AND owner_id=?"
            params.append(owner_id)
        if workspace_type:
            query += " AND workspace_type=?"
            params.append(workspace_type)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            VirtualWorkspace(
                workspace_id=row["workspace_id"],
                name=row["name"],
                description=row["description"],
                owner_id=row["owner_id"],
                workspace_type=row["workspace_type"],
                capacity=row["capacity"],
                current_occupants=json.loads(row["current_occupants"]),
                is_private=bool(row["is_private"]),
                amenities=json.loads(row["amenities"]),
                background_image=row["background_image"],
                background_sound=row["background_sound"],
                settings=json.loads(row["settings"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
            for row in rows
        ]

    # ==================== WorkActivity CRUD ====================

    def create_activity(self, activity: WorkActivity) -> WorkActivity:
        """创建工作活动记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO p17_work_activities
            (activity_id, employee_id, activity_type, start_time, end_time, duration_minutes, project_id, task_id, description, is_focus_time, interruption_count, self_reported_productivity, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            activity.activity_id,
            activity.employee_id,
            activity.activity_type,
            activity.start_time.isoformat(),
            activity.end_time.isoformat() if activity.end_time else None,
            activity.duration_minutes,
            activity.project_id,
            activity.task_id,
            activity.description,
            1 if activity.is_focus_time else 0,
            activity.interruption_count,
            activity.self_reported_productivity,
            json.dumps(activity.metadata),
            activity.created_at.isoformat()
        ))
        conn.commit()
        return activity

    def get_activity(self, activity_id: str) -> Optional[WorkActivity]:
        """获取工作活动"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_work_activities WHERE activity_id = ?", (activity_id,))
        row = cursor.fetchone()
        if row:
            return WorkActivity(
                activity_id=row["activity_id"],
                employee_id=row["employee_id"],
                activity_type=row["activity_type"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                duration_minutes=row["duration_minutes"],
                project_id=row["project_id"],
                task_id=row["task_id"],
                description=row["description"],
                is_focus_time=bool(row["is_focus_time"]),
                interruption_count=row["interruption_count"],
                self_reported_productivity=row["self_reported_productivity"],
                metadata=json.loads(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"])
            )
        return None

    def list_activities(self, employee_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[WorkActivity]:
        """列出工作活动"""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM p17_work_activities WHERE employee_id=?"
        params = [employee_id]
        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND start_time <= ?"
            params.append(end_date.isoformat())
        query += " ORDER BY start_time DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            WorkActivity(
                activity_id=row["activity_id"],
                employee_id=row["employee_id"],
                activity_type=row["activity_type"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                duration_minutes=row["duration_minutes"],
                project_id=row["project_id"],
                task_id=row["task_id"],
                description=row["description"],
                is_focus_time=bool(row["is_focus_time"]),
                interruption_count=row["interruption_count"],
                self_reported_productivity=row["self_reported_productivity"],
                metadata=json.loads(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"])
            )
            for row in rows
        ]

    # ==================== TeamEvent CRUD ====================

    def create_event(self, event: TeamEvent) -> TeamEvent:
        """创建团队活动"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO p17_team_events
            (event_id, title, description, event_type, organizer_id, start_time, end_time, duration_minutes, virtual_workspace_id, meeting_link, participants, rsvp_status, photos, notes, is_recurring, recurrence_pattern, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.title,
            event.description,
            event.event_type,
            event.organizer_id,
            event.start_time.isoformat(),
            event.end_time.isoformat() if event.end_time else None,
            event.duration_minutes,
            event.virtual_workspace_id,
            event.meeting_link,
            json.dumps(event.participants),
            json.dumps(event.rsvp_status),
            json.dumps(event.photos),
            event.notes,
            1 if event.is_recurring else 0,
            event.recurrence_pattern,
            event.created_at.isoformat(),
            event.updated_at.isoformat()
        ))
        conn.commit()
        return event

    def get_event(self, event_id: str) -> Optional[TeamEvent]:
        """获取团队活动"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_team_events WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        if row:
            return TeamEvent(
                event_id=row["event_id"],
                title=row["title"],
                description=row["description"],
                event_type=row["event_type"],
                organizer_id=row["organizer_id"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                duration_minutes=row["duration_minutes"],
                virtual_workspace_id=row["virtual_workspace_id"],
                meeting_link=row["meeting_link"],
                participants=json.loads(row["participants"]),
                rsvp_status=json.loads(row["rsvp_status"]),
                photos=json.loads(row["photos"]),
                notes=row["notes"],
                is_recurring=bool(row["is_recurring"]),
                recurrence_pattern=row["recurrence_pattern"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
        return None

    def update_event(self, event: TeamEvent) -> TeamEvent:
        """更新团队活动"""
        event.updated_at = datetime.now()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE p17_team_events
            SET title=?, description=?, event_type=?, start_time=?, end_time=?, duration_minutes=?, virtual_workspace_id=?, meeting_link=?, participants=?, rsvp_status=?, photos=?, notes=?, is_recurring=?, recurrence_pattern=?, updated_at=?
            WHERE event_id=?
        """, (
            event.title,
            event.description,
            event.event_type,
            event.start_time.isoformat(),
            event.end_time.isoformat() if event.end_time else None,
            event.duration_minutes,
            event.virtual_workspace_id,
            event.meeting_link,
            json.dumps(event.participants),
            json.dumps(event.rsvp_status),
            json.dumps(event.photos),
            event.notes,
            1 if event.is_recurring else 0,
            event.recurrence_pattern,
            event.updated_at.isoformat(),
            event.event_id
        ))
        conn.commit()
        return event

    def list_events(self, organizer_id: Optional[str] = None, upcoming_only: bool = False) -> List[TeamEvent]:
        """列出团队活动"""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM p17_team_events WHERE 1=1"
        params = []
        if organizer_id:
            query += " AND organizer_id=?"
            params.append(organizer_id)
        if upcoming_only:
            query += " AND start_time >= datetime('now')"
        query += " ORDER BY start_time ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            TeamEvent(
                event_id=row["event_id"],
                title=row["title"],
                description=row["description"],
                event_type=row["event_type"],
                organizer_id=row["organizer_id"],
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                duration_minutes=row["duration_minutes"],
                virtual_workspace_id=row["virtual_workspace_id"],
                meeting_link=row["meeting_link"],
                participants=json.loads(row["participants"]),
                rsvp_status=json.loads(row["rsvp_status"]),
                photos=json.loads(row["photos"]),
                notes=row["notes"],
                is_recurring=bool(row["is_recurring"]),
                recurrence_pattern=row["recurrence_pattern"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
            for row in rows
        ]

    # ==================== TimezoneCoordination CRUD ====================

    def create_coordination(self, coordination: TimezoneCoordination) -> TimezoneCoordination:
        """创建时区协调记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO p17_timezone_coordinations
            (coordination_id, team_id, members, overlap_windows, preferred_meeting_times, async_handoff_times, holiday_calendars, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            coordination.coordination_id,
            coordination.team_id,
            json.dumps(coordination.members),
            json.dumps(coordination.overlap_windows),
            json.dumps(coordination.preferred_meeting_times),
            json.dumps(coordination.async_handoff_times),
            json.dumps(coordination.holiday_calendars),
            coordination.created_at.isoformat(),
            coordination.updated_at.isoformat()
        ))
        conn.commit()
        return coordination

    def get_coordination(self, team_id: str) -> Optional[TimezoneCoordination]:
        """获取时区协调记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_timezone_coordinations WHERE team_id = ?", (team_id,))
        row = cursor.fetchone()
        if row:
            return TimezoneCoordination(
                coordination_id=row["coordination_id"],
                team_id=row["team_id"],
                members=json.loads(row["members"]),
                overlap_windows=json.loads(row["overlap_windows"]),
                preferred_meeting_times=json.loads(row["preferred_meeting_times"]),
                async_handoff_times=json.loads(row["async_handoff_times"]),
                holiday_calendars=json.loads(row["holiday_calendars"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
        return None

    def update_coordination(self, coordination: TimezoneCoordination) -> TimezoneCoordination:
        """更新时区协调记录"""
        coordination.updated_at = datetime.now()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE p17_timezone_coordinations
            SET members=?, overlap_windows=?, preferred_meeting_times=?, async_handoff_times=?, holiday_calendars=?, updated_at=?
            WHERE team_id=?
        """, (
            json.dumps(coordination.members),
            json.dumps(coordination.overlap_windows),
            json.dumps(coordination.preferred_meeting_times),
            json.dumps(coordination.async_handoff_times),
            json.dumps(coordination.holiday_calendars),
            coordination.updated_at.isoformat(),
            coordination.team_id
        ))
        conn.commit()
        return coordination

    # ==================== RemoteWorkMetrics CRUD ====================

    def create_or_update_metrics(self, metrics: RemoteWorkMetrics) -> RemoteWorkMetrics:
        """创建或更新远程工作指标（Upsert）"""
        metrics.updated_at = datetime.now()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO p17_remote_work_metrics
            (metrics_id, employee_id, date, total_work_minutes, focus_time_minutes, meeting_minutes, break_minutes, communication_minutes, productivity_score, work_mode, location, internet_issues_count, self_reported_wellbeing, manager_notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.metrics_id,
            metrics.employee_id,
            metrics.date,
            metrics.total_work_minutes,
            metrics.focus_time_minutes,
            metrics.meeting_minutes,
            metrics.break_minutes,
            metrics.communication_minutes,
            metrics.productivity_score,
            metrics.work_mode,
            metrics.location,
            metrics.internet_issues_count,
            metrics.self_reported_wellbeing,
            metrics.manager_notes,
            metrics.created_at.isoformat(),
            metrics.updated_at.isoformat()
        ))
        conn.commit()
        return metrics

    def get_metrics(self, employee_id: str, date: str) -> Optional[RemoteWorkMetrics]:
        """获取远程工作指标"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_remote_work_metrics WHERE employee_id=? AND date=?", (employee_id, date))
        row = cursor.fetchone()
        if row:
            return RemoteWorkMetrics(
                metrics_id=row["metrics_id"],
                employee_id=row["employee_id"],
                date=row["date"],
                total_work_minutes=row["total_work_minutes"],
                focus_time_minutes=row["focus_time_minutes"],
                meeting_minutes=row["meeting_minutes"],
                break_minutes=row["break_minutes"],
                communication_minutes=row["communication_minutes"],
                productivity_score=row["productivity_score"],
                work_mode=row["work_mode"],
                location=row["location"],
                internet_issues_count=row["internet_issues_count"],
                self_reported_wellbeing=row["self_reported_wellbeing"],
                manager_notes=row["manager_notes"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
        return None

    def list_metrics(self, employee_id: str, start_date: str, end_date: str) -> List[RemoteWorkMetrics]:
        """列出远程工作指标"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM p17_remote_work_metrics
            WHERE employee_id=? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (employee_id, start_date, end_date))
        rows = cursor.fetchall()
        return [
            RemoteWorkMetrics(
                metrics_id=row["metrics_id"],
                employee_id=row["employee_id"],
                date=row["date"],
                total_work_minutes=row["total_work_minutes"],
                focus_time_minutes=row["focus_time_minutes"],
                meeting_minutes=row["meeting_minutes"],
                break_minutes=row["break_minutes"],
                communication_minutes=row["communication_minutes"],
                productivity_score=row["productivity_score"],
                work_mode=row["work_mode"],
                location=row["location"],
                internet_issues_count=row["internet_issues_count"],
                self_reported_wellbeing=row["self_reported_wellbeing"],
                manager_notes=row["manager_notes"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
            for row in rows
        ]

    # ==================== VirtualWaterCooler CRUD ====================

    def create_water_cooler(self, cooler: VirtualWaterCooler) -> VirtualWaterCooler:
        """创建虚拟茶水间聊天"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO p17_virtual_water_cooler
            (chat_id, topic, initiator_id, participants, messages, is_active, workspace_id, started_at, ended_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cooler.chat_id,
            cooler.topic,
            cooler.initiator_id,
            json.dumps(cooler.participants),
            json.dumps(cooler.messages),
            1 if cooler.is_active else 0,
            cooler.workspace_id,
            cooler.started_at.isoformat(),
            cooler.ended_at.isoformat() if cooler.ended_at else None,
            cooler.created_at.isoformat()
        ))
        conn.commit()
        return cooler

    def get_water_cooler(self, chat_id: str) -> Optional[VirtualWaterCooler]:
        """获取虚拟茶水间聊天"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_virtual_water_cooler WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        if row:
            return VirtualWaterCooler(
                chat_id=row["chat_id"],
                topic=row["topic"],
                initiator_id=row["initiator_id"],
                participants=json.loads(row["participants"]),
                messages=json.loads(row["messages"]),
                is_active=bool(row["is_active"]),
                workspace_id=row["workspace_id"],
                started_at=datetime.fromisoformat(row["started_at"]),
                ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"])
            )
        return None

    def update_water_cooler(self, cooler: VirtualWaterCooler) -> VirtualWaterCooler:
        """更新虚拟茶水间聊天"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE p17_virtual_water_cooler
            SET topic=?, participants=?, messages=?, is_active=?, workspace_id=?, ended_at=?
            WHERE chat_id=?
        """, (
            cooler.topic,
            json.dumps(cooler.participants),
            json.dumps(cooler.messages),
            1 if cooler.is_active else 0,
            cooler.workspace_id,
            cooler.ended_at.isoformat() if cooler.ended_at else None,
            cooler.chat_id
        ))
        conn.commit()
        return cooler

    def list_active_water_coolers(self) -> List[VirtualWaterCooler]:
        """列出活跃的茶水间聊天"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_virtual_water_cooler WHERE is_active=1 ORDER BY started_at DESC")
        rows = cursor.fetchall()
        return [
            VirtualWaterCooler(
                chat_id=row["chat_id"],
                topic=row["topic"],
                initiator_id=row["initiator_id"],
                participants=json.loads(row["participants"]),
                messages=json.loads(row["messages"]),
                is_active=bool(row["is_active"]),
                workspace_id=row["workspace_id"],
                started_at=datetime.fromisoformat(row["started_at"]),
                ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"])
            )
            for row in rows
        ]

    # ==================== RemoteWorkPolicy CRUD ====================

    def create_policy(self, policy: RemoteWorkPolicy) -> RemoteWorkPolicy:
        """创建远程工作政策"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO p17_remote_work_policies
            (policy_id, organization_id, name, description, remote_days_required, office_days_required, core_hours_start, core_hours_end, allowed_countries, timezone_restrictions, equipment_allowance, internet_allowance, check_in_required, meeting_requirements, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            policy.policy_id,
            policy.organization_id,
            policy.name,
            policy.description,
            policy.remote_days_required,
            policy.office_days_required,
            policy.core_hours_start,
            policy.core_hours_end,
            json.dumps(policy.allowed_countries),
            json.dumps(policy.timezone_restrictions),
            policy.equipment_allowance,
            policy.internet_allowance,
            1 if policy.check_in_required else 0,
            json.dumps(policy.meeting_requirements),
            1 if policy.is_active else 0,
            policy.created_at.isoformat(),
            policy.updated_at.isoformat()
        ))
        conn.commit()
        return policy

    def get_policy(self, policy_id: str) -> Optional[RemoteWorkPolicy]:
        """获取远程工作政策"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM p17_remote_work_policies WHERE policy_id = ?", (policy_id,))
        row = cursor.fetchone()
        if row:
            return RemoteWorkPolicy(
                policy_id=row["policy_id"],
                organization_id=row["organization_id"],
                name=row["name"],
                description=row["description"],
                remote_days_required=row["remote_days_required"],
                office_days_required=row["office_days_required"],
                core_hours_start=row["core_hours_start"],
                core_hours_end=row["core_hours_end"],
                allowed_countries=json.loads(row["allowed_countries"]),
                timezone_restrictions=json.loads(row["timezone_restrictions"]),
                equipment_allowance=row["equipment_allowance"],
                internet_allowance=row["internet_allowance"],
                check_in_required=bool(row["check_in_required"]),
                meeting_requirements=json.loads(row["meeting_requirements"]),
                is_active=bool(row["is_active"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
        return None

    def list_policies(self, organization_id: str) -> List[RemoteWorkPolicy]:
        """列出远程工作政策"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM p17_remote_work_policies
            WHERE organization_id=?
            ORDER BY created_at DESC
        """, (organization_id,))
        rows = cursor.fetchall()
        return [
            RemoteWorkPolicy(
                policy_id=row["policy_id"],
                organization_id=row["organization_id"],
                name=row["name"],
                description=row["description"],
                remote_days_required=row["remote_days_required"],
                office_days_required=row["office_days_required"],
                core_hours_start=row["core_hours_start"],
                core_hours_end=row["core_hours_end"],
                allowed_countries=json.loads(row["allowed_countries"]),
                timezone_restrictions=json.loads(row["timezone_restrictions"]),
                equipment_allowance=row["equipment_allowance"],
                internet_allowance=row["internet_allowance"],
                check_in_required=bool(row["check_in_required"]),
                meeting_requirements=json.loads(row["meeting_requirements"]),
                is_active=bool(row["is_active"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )
            for row in rows
        ]

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
