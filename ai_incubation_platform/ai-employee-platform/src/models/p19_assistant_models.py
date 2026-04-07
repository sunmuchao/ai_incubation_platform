"""
P19 AI 助手增强 - 数据模型层
版本：v19.0.0
主题：AI 助手增强 (智能工作助手、日程管理、会议摘要、工作简报)
"""
import sqlite3
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field, asdict


# ==================== 枚举定义 ====================

class TaskPriority(str, Enum):
    """任务优先级"""
    CRITICAL = "critical"  # 紧急重要
    HIGH = "high"  # 高优先级
    MEDIUM = "medium"  # 中优先级
    LOW = "low"  # 低优先级


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"  # 待处理
    IN_PROGRESS = "in_progress"  # 进行中
    BLOCKED = "blocked"  # 已阻塞
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class AssistantType(str, Enum):
    """助手类型"""
    TASK_ASSISTANT = "task_assistant"  # 任务助手
    SCHEDULE_ASSISTANT = "schedule_assistant"  # 日程助手
    MEETING_ASSISTANT = "meeting_assistant"  # 会议助手
    REPORT_ASSISTANT = "report_assistant"  # 报告助手


class RecommendationType(str, Enum):
    """推荐类型"""
    TASK_PRIORITY = "task_priority"  # 任务优先级推荐
    AI_EMPLOYEE = "ai_employee"  # AI 员工推荐
    WORKFLOW_OPTIMIZATION = "workflow_optimization"  # 工作流优化
    SCHEDULE_OPTIMIZATION = "schedule_optimization"  # 日程优化


class MeetingType(str, Enum):
    """会议类型"""
    STANDUP = "standup"  # 站会
    PLANNING = "planning"  # 规划会
    REVIEW = "review"  # 评审会
    RETROSPECTIVE = "retrospective"  # 回顾会
    ONE_ON_ONE = "one_on_one"  # 1 对 1
    TEAM_MEETING = "team_meeting"  # 团队会议
    CLIENT_MEETING = "client_meeting"  # 客户会议
    OTHER = "other"  # 其他


class MeetingStatus(str, Enum):
    """会议状态"""
    SCHEDULED = "scheduled"  # 已安排
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class ReportType(str, Enum):
    """报告类型"""
    DAILY = "daily"  # 日报
    WEEKLY = "weekly"  # 周报
    MONTHLY = "monthly"  # 月报
    PROJECT = "project"  # 项目报告
    CUSTOM = "custom"  # 自定义


class ReportStatus(str, Enum):
    """报告状态"""
    DRAFT = "draft"  # 草稿
    GENERATING = "generating"  # 生成中
    COMPLETED = "completed"  # 已完成
    SENT = "sent"  # 已发送


class ScheduleConflictType(str, Enum):
    """日程冲突类型"""
    TIME_OVERLAP = "time_overlap"  # 时间重叠
    DOUBLE_BOOKING = "double_booking"  # 重复预订
    AVAILABILITY_MISMATCH = "availability_mismatch"  # 可用性不匹配
    PRIORITY_CONFLICT = "priority_conflict"  # 优先级冲突


class ConflictResolutionStrategy(str, Enum):
    """冲突解决策略"""
    AUTO_RESCHEDULE = "auto_reschedule"  # 自动重新安排
    NOTIFY_USERS = "notify_users"  # 通知用户
    ESCALATE_TO_MANAGER = "escalate_to_manager"  # 上报主管
    IGNORE = "ignore"  # 忽略


# ==================== 数据模型类 ====================

@dataclass
class AssistantProfile:
    """AI 助手档案"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    assistant_type: str = AssistantType.TASK_ASSISTANT.value
    name: str = "工作助手"
    description: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AssistantProfile':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskRecommendation:
    """任务推荐"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    recommendation_type: str = RecommendationType.TASK_PRIORITY.value
    task_id: Optional[int] = None
    employee_id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    reason: Optional[str] = None
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_accepted: Optional[bool] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskRecommendation':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkSuggestion:
    """工作建议"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    suggestion_type: str = "workflow_optimization"
    title: str = ""
    description: Optional[str] = None
    expected_impact: Optional[str] = None
    effort_level: str = "medium"  # low, medium, high
    priority: str = TaskPriority.MEDIUM.value
    status: str = "pending"  # pending, accepted, rejected, implemented
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkSuggestion':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SmartSchedule:
    """智能日程"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    start_time: str = ""
    end_time: str = ""
    location: Optional[str] = None
    attendees: List[int] = field(default_factory=list)
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, monthly
    recurrence_end: Optional[str] = None
    priority: str = TaskPriority.MEDIUM.value
    status: str = "confirmed"  # tentative, confirmed, cancelled
    timezone: str = "UTC"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SmartSchedule':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScheduleConflict:
    """日程冲突"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    conflict_type: str = ScheduleConflictType.TIME_OVERLAP.value
    schedule_id_1: int = 0
    schedule_id_2: int = 0
    description: Optional[str] = None
    severity: str = "high"  # low, medium, high
    resolution_strategy: Optional[str] = None
    resolution_notes: Optional[str] = None
    is_resolved: bool = False
    resolved_at: Optional[str] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleConflict':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Meeting:
    """会议记录"""
    id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    meeting_type: str = MeetingType.TEAM_MEETING.value
    organizer_id: Optional[int] = None
    start_time: str = ""
    end_time: str = ""
    location: Optional[str] = None
    attendees: List[int] = field(default_factory=list)
    status: str = MeetingStatus.SCHEDULED.value
    agenda: Optional[str] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Meeting':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MeetingSummary:
    """会议摘要"""
    id: Optional[int] = None
    meeting_id: int = 0
    summary_text: str = ""
    key_decisions: List[str] = field(default_factory=list)
    action_items: List[Dict[str, Any]] = field(default_factory=list)
    follow_up_items: List[str] = field(default_factory=list)
    sentiment: Optional[str] = None  # positive, neutral, negative
    generated_by: str = "ai"
    quality_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MeetingSummary':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MeetingActionItem:
    """会议行动项"""
    id: Optional[int] = None
    meeting_id: int = 0
    summary_id: Optional[int] = None
    title: str = ""
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    due_date: Optional[str] = None
    priority: str = TaskPriority.MEDIUM.value
    status: str = "pending"  # pending, in_progress, completed, cancelled
    completion_notes: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MeetingActionItem':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkReport:
    """工作报告"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    report_type: str = ReportType.DAILY.value
    title: Optional[str] = None
    period_start: str = ""
    period_end: str = ""
    content: Optional[str] = None
    tasks_completed: List[int] = field(default_factory=list)
    time_spent_hours: float = 0.0
    achievements: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    status: str = ReportStatus.DRAFT.value
    sent_to: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkReport':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReportTemplate:
    """报告模板"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    report_type: str = ReportType.DAILY.value
    template_content: str = ""
    sections: List[str] = field(default_factory=list)
    is_default: bool = False
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportTemplate':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReportGeneration:
    """报告生成记录"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    template_id: Optional[int] = None
    report_type: str = ReportType.DAILY.value
    generation_status: str = "pending"  # pending, generating, completed, failed
    error_message: Optional[str] = None
    generated_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportGeneration':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==================== 数据库操作类 ====================

class AssistantDB:
    """AI 助手数据库操作"""

    def __init__(self, db_path: str = "test.db"):
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """初始化数据表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # AssistantProfile 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_assistant_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                assistant_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                preferences TEXT DEFAULT '{}',
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # TaskRecommendation 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_task_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                recommendation_type TEXT NOT NULL,
                task_id INTEGER,
                employee_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                reason TEXT,
                confidence_score REAL DEFAULT 0.0,
                metadata TEXT DEFAULT '{}',
                is_accepted BOOLEAN,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # WorkSuggestion 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_work_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                suggestion_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                expected_impact TEXT,
                effort_level TEXT DEFAULT 'medium',
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # SmartSchedule 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_smart_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT,
                attendees TEXT DEFAULT '[]',
                is_recurring BOOLEAN DEFAULT 0,
                recurrence_pattern TEXT,
                recurrence_end TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'confirmed',
                timezone TEXT DEFAULT 'UTC',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ScheduleConflict 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_schedule_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                conflict_type TEXT NOT NULL,
                schedule_id_1 INTEGER NOT NULL,
                schedule_id_2 INTEGER NOT NULL,
                description TEXT,
                severity TEXT DEFAULT 'high',
                resolution_strategy TEXT,
                resolution_notes TEXT,
                is_resolved BOOLEAN DEFAULT 0,
                resolved_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Meeting 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                meeting_type TEXT NOT NULL,
                organizer_id INTEGER,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT,
                attendees TEXT DEFAULT '[]',
                status TEXT DEFAULT 'scheduled',
                agenda TEXT,
                recording_url TEXT,
                transcript TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (organizer_id) REFERENCES users(id)
            )
        """)

        # MeetingSummary 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_meeting_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                summary_text TEXT NOT NULL,
                key_decisions TEXT DEFAULT '[]',
                action_items TEXT DEFAULT '[]',
                follow_up_items TEXT DEFAULT '[]',
                sentiment TEXT,
                generated_by TEXT DEFAULT 'ai',
                quality_score REAL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES p19_meetings(id)
            )
        """)

        # MeetingActionItem 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_meeting_action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                summary_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                assignee_id INTEGER,
                due_date TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                completion_notes TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES p19_meetings(id),
                FOREIGN KEY (summary_id) REFERENCES p19_meeting_summaries(id)
            )
        """)

        # WorkReport 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_work_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                report_type TEXT NOT NULL,
                title TEXT,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                content TEXT,
                tasks_completed TEXT DEFAULT '[]',
                time_spent_hours REAL DEFAULT 0.0,
                achievements TEXT DEFAULT '[]',
                blockers TEXT DEFAULT '[]',
                next_steps TEXT DEFAULT '[]',
                status TEXT DEFAULT 'draft',
                sent_to TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                generated_at TEXT,
                sent_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ReportTemplate 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_report_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                report_type TEXT NOT NULL,
                template_content TEXT NOT NULL,
                sections TEXT DEFAULT '[]',
                is_default BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ReportGeneration 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS p19_report_generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                template_id INTEGER,
                report_type TEXT NOT NULL,
                generation_status TEXT DEFAULT 'pending',
                error_message TEXT,
                generated_content TEXT,
                metadata TEXT DEFAULT '{}',
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (template_id) REFERENCES p19_report_templates(id)
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p19_assistant_user ON p19_assistant_profiles(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p19_task_rec_user ON p19_task_recommendations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p19_schedule_user ON p19_smart_schedules(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p19_schedule_time ON p19_smart_schedules(start_time, end_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p19_meeting_time ON p19_meetings(start_time, end_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p19_report_user ON p19_work_reports(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_p19_report_type ON p19_work_reports(report_type, period_start, period_end)")

        conn.commit()
        conn.close()

    # ==================== AssistantProfile CRUD ====================

    def create_assistant(self, assistant: AssistantProfile) -> AssistantProfile:
        """创建助手档案"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO p19_assistant_profiles
            (user_id, assistant_type, name, description, preferences, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assistant.user_id,
            assistant.assistant_type,
            assistant.name,
            assistant.description,
            json.dumps(assistant.preferences),
            assistant.is_active,
            assistant.created_at,
            assistant.updated_at
        ))

        assistant.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return assistant

    def get_assistant(self, assistant_id: int) -> Optional[AssistantProfile]:
        """获取助手档案"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM p19_assistant_profiles WHERE id = ?", (assistant_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_assistant(row)
        return None

    def get_user_assistants(self, user_id: int) -> List[AssistantProfile]:
        """获取用户的助手列表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM p19_assistant_profiles WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_assistant(row) for row in rows]

    def update_assistant(self, assistant: AssistantProfile) -> AssistantProfile:
        """更新助手档案"""
        assistant.updated_at = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE p19_assistant_profiles
            SET name=?, description=?, preferences=?, is_active=?, updated_at=?
            WHERE id=?
        """, (
            assistant.name,
            assistant.description,
            json.dumps(assistant.preferences),
            assistant.is_active,
            assistant.updated_at,
            assistant.id
        ))

        conn.commit()
        conn.close()
        return assistant

    def delete_assistant(self, assistant_id: int) -> bool:
        """删除助手档案"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM p19_assistant_profiles WHERE id = ?", (assistant_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def _row_to_assistant(self, row: sqlite3.Row) -> AssistantProfile:
        """将数据库行转换为 AssistantProfile 对象"""
        return AssistantProfile(
            id=row['id'],
            user_id=row['user_id'],
            assistant_type=row['assistant_type'],
            name=row['name'],
            description=row['description'],
            preferences=json.loads(row['preferences']),
            is_active=bool(row['is_active']),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    # ==================== TaskRecommendation CRUD ====================

    def create_recommendation(self, recommendation: TaskRecommendation) -> TaskRecommendation:
        """创建任务推荐"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO p19_task_recommendations
            (user_id, recommendation_type, task_id, employee_id, title, description, reason, confidence_score, metadata, is_accepted, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recommendation.user_id,
            recommendation.recommendation_type,
            recommendation.task_id,
            recommendation.employee_id,
            recommendation.title,
            recommendation.description,
            recommendation.reason,
            recommendation.confidence_score,
            json.dumps(recommendation.metadata),
            recommendation.is_accepted,
            recommendation.created_at
        ))

        recommendation.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return recommendation

    def get_recommendations(self, user_id: int, limit: int = 50) -> List[TaskRecommendation]:
        """获取用户的任务推荐"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM p19_task_recommendations
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_recommendation(row) for row in rows]

    def accept_recommendation(self, recommendation_id: int) -> bool:
        """接受推荐"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE p19_task_recommendations
            SET is_accepted = 1
            WHERE id = ?
        """, (recommendation_id,))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def _row_to_recommendation(self, row: sqlite3.Row) -> TaskRecommendation:
        """将数据库行转换为 TaskRecommendation 对象"""
        return TaskRecommendation(
            id=row['id'],
            user_id=row['user_id'],
            recommendation_type=row['recommendation_type'],
            task_id=row['task_id'],
            employee_id=row['employee_id'],
            title=row['title'],
            description=row['description'],
            reason=row['reason'],
            confidence_score=row['confidence_score'],
            metadata=json.loads(row['metadata']),
            is_accepted=row['is_accepted'],
            created_at=row['created_at']
        )

    # ==================== SmartSchedule CRUD ====================

    def create_schedule(self, schedule: SmartSchedule) -> SmartSchedule:
        """创建日程"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO p19_smart_schedules
            (user_id, title, description, start_time, end_time, location, attendees, is_recurring,
             recurrence_pattern, recurrence_end, priority, status, timezone, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule.user_id,
            schedule.title,
            schedule.description,
            schedule.start_time,
            schedule.end_time,
            schedule.location,
            json.dumps(schedule.attendees),
            schedule.is_recurring,
            schedule.recurrence_pattern,
            schedule.recurrence_end,
            schedule.priority,
            schedule.status,
            schedule.timezone,
            json.dumps(schedule.metadata),
            schedule.created_at,
            schedule.updated_at
        ))

        schedule.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return schedule

    def get_schedule(self, schedule_id: int) -> Optional[SmartSchedule]:
        """获取日程"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM p19_smart_schedules WHERE id = ?", (schedule_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_schedule(row)
        return None

    def get_user_schedules(self, user_id: int, start_date: str = None, end_date: str = None) -> List[SmartSchedule]:
        """获取用户日程"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if start_date and end_date:
            cursor.execute("""
                SELECT * FROM p19_smart_schedules
                WHERE user_id = ? AND start_time >= ? AND end_time <= ?
                ORDER BY start_time
            """, (user_id, start_date, end_date))
        else:
            cursor.execute("""
                SELECT * FROM p19_smart_schedules
                WHERE user_id = ?
                ORDER BY start_time
            """, (user_id,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_schedule(row) for row in rows]

    def update_schedule(self, schedule: SmartSchedule) -> SmartSchedule:
        """更新日程"""
        schedule.updated_at = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE p19_smart_schedules
            SET title=?, description=?, start_time=?, end_time=?, location=?, attendees=?,
                is_recurring=?, recurrence_pattern=?, recurrence_end=?, priority=?,
                status=?, timezone=?, metadata=?, updated_at=?
            WHERE id=?
        """, (
            schedule.title,
            schedule.description,
            schedule.start_time,
            schedule.end_time,
            schedule.location,
            json.dumps(schedule.attendees),
            schedule.is_recurring,
            schedule.recurrence_pattern,
            schedule.recurrence_end,
            schedule.priority,
            schedule.status,
            schedule.timezone,
            json.dumps(schedule.metadata),
            schedule.updated_at,
            schedule.id
        ))

        conn.commit()
        conn.close()
        return schedule

    def delete_schedule(self, schedule_id: int) -> bool:
        """删除日程"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM p19_smart_schedules WHERE id = ?", (schedule_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def _row_to_schedule(self, row: sqlite3.Row) -> SmartSchedule:
        """将数据库行转换为 SmartSchedule 对象"""
        return SmartSchedule(
            id=row['id'],
            user_id=row['user_id'],
            title=row['title'],
            description=row['description'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            location=row['location'],
            attendees=json.loads(row['attendees']),
            is_recurring=bool(row['is_recurring']),
            recurrence_pattern=row['recurrence_pattern'],
            recurrence_end=row['recurrence_end'],
            priority=row['priority'],
            status=row['status'],
            timezone=row['timezone'],
            metadata=json.loads(row['metadata']),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    # ==================== Meeting CRUD ====================

    def create_meeting(self, meeting: Meeting) -> Meeting:
        """创建会议"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO p19_meetings
            (title, description, meeting_type, organizer_id, start_time, end_time, location,
             attendees, status, agenda, recording_url, transcript, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            meeting.title,
            meeting.description,
            meeting.meeting_type,
            meeting.organizer_id,
            meeting.start_time,
            meeting.end_time,
            meeting.location,
            json.dumps(meeting.attendees),
            meeting.status,
            meeting.agenda,
            meeting.recording_url,
            meeting.transcript,
            json.dumps(meeting.metadata),
            meeting.created_at,
            meeting.updated_at
        ))

        meeting.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return meeting

    def get_meeting(self, meeting_id: int) -> Optional[Meeting]:
        """获取会议"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM p19_meetings WHERE id = ?", (meeting_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_meeting(row)
        return None

    def get_user_meetings(self, user_id: int, status: str = None) -> List[Meeting]:
        """获取用户会议"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT * FROM p19_meetings
                WHERE organizer_id = ? OR attendees LIKE ?
                AND status = ?
                ORDER BY start_time DESC
            """, (user_id, f'%{user_id}%', status))
        else:
            cursor.execute("""
                SELECT * FROM p19_meetings
                WHERE organizer_id = ? OR attendees LIKE ?
                ORDER BY start_time DESC
            """, (user_id, f'%{user_id}%'))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_meeting(row) for row in rows]

    def update_meeting(self, meeting: Meeting) -> Meeting:
        """更新会议"""
        meeting.updated_at = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE p19_meetings
            SET title=?, description=?, meeting_type=?, start_time=?, end_time=?, location=?,
                attendees=?, status=?, agenda=?, recording_url=?, transcript=?, metadata=?, updated_at=?
            WHERE id=?
        """, (
            meeting.title,
            meeting.description,
            meeting.meeting_type,
            meeting.start_time,
            meeting.end_time,
            meeting.location,
            json.dumps(meeting.attendees),
            meeting.status,
            meeting.agenda,
            meeting.recording_url,
            meeting.transcript,
            json.dumps(meeting.metadata),
            meeting.updated_at,
            meeting.id
        ))

        conn.commit()
        conn.close()
        return meeting

    def delete_meeting(self, meeting_id: int) -> bool:
        """删除会议"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM p19_meetings WHERE id = ?", (meeting_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def _row_to_meeting(self, row: sqlite3.Row) -> Meeting:
        """将数据库行转换为 Meeting 对象"""
        return Meeting(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            meeting_type=row['meeting_type'],
            organizer_id=row['organizer_id'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            location=row['location'],
            attendees=json.loads(row['attendees']),
            status=row['status'],
            agenda=row['agenda'],
            recording_url=row['recording_url'],
            transcript=row['transcript'],
            metadata=json.loads(row['metadata']),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    # ==================== WorkReport CRUD ====================

    def create_report(self, report: WorkReport) -> WorkReport:
        """创建工作报告"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO p19_work_reports
            (user_id, report_type, title, period_start, period_end, content, tasks_completed,
             time_spent_hours, achievements, blockers, next_steps, status, sent_to,
             metadata, generated_at, sent_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report.user_id,
            report.report_type,
            report.title,
            report.period_start,
            report.period_end,
            report.content,
            json.dumps(report.tasks_completed),
            report.time_spent_hours,
            json.dumps(report.achievements),
            json.dumps(report.blockers),
            json.dumps(report.next_steps),
            report.status,
            json.dumps(report.sent_to),
            json.dumps(report.metadata),
            report.generated_at,
            report.sent_at,
            report.created_at,
            report.updated_at
        ))

        report.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return report

    def get_report(self, report_id: int) -> Optional[WorkReport]:
        """获取报告"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM p19_work_reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_report(row)
        return None

    def get_user_reports(self, user_id: int, report_type: str = None, limit: int = 50) -> List[WorkReport]:
        """获取用户报告"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if report_type:
            cursor.execute("""
                SELECT * FROM p19_work_reports
                WHERE user_id = ? AND report_type = ?
                ORDER BY period_end DESC
                LIMIT ?
            """, (user_id, report_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM p19_work_reports
                WHERE user_id = ?
                ORDER BY period_end DESC
                LIMIT ?
            """, (user_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_report(row) for row in rows]

    def update_report(self, report: WorkReport) -> WorkReport:
        """更新报告"""
        report.updated_at = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE p19_work_reports
            SET title=?, content=?, tasks_completed=?, time_spent_hours=?, achievements=?,
                blockers=?, next_steps=?, status=?, sent_to=?, metadata=?,
                generated_at=?, sent_at=?, updated_at=?
            WHERE id=?
        """, (
            report.title,
            report.content,
            json.dumps(report.tasks_completed),
            report.time_spent_hours,
            json.dumps(report.achievements),
            json.dumps(report.blockers),
            json.dumps(report.next_steps),
            report.status,
            json.dumps(report.sent_to),
            json.dumps(report.metadata),
            report.generated_at,
            report.sent_at,
            report.updated_at,
            report.id
        ))

        conn.commit()
        conn.close()
        return report

    def delete_report(self, report_id: int) -> bool:
        """删除报告"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM p19_work_reports WHERE id = ?", (report_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def _row_to_report(self, row: sqlite3.Row) -> WorkReport:
        """将数据库行转换为 WorkReport 对象"""
        return WorkReport(
            id=row['id'],
            user_id=row['user_id'],
            report_type=row['report_type'],
            title=row['title'],
            period_start=row['period_start'],
            period_end=row['period_end'],
            content=row['content'],
            tasks_completed=json.loads(row['tasks_completed']),
            time_spent_hours=row['time_spent_hours'],
            achievements=json.loads(row['achievements']),
            blockers=json.loads(row['blockers']),
            next_steps=json.loads(row['next_steps']),
            status=row['status'],
            sent_to=json.loads(row['sent_to']),
            metadata=json.loads(row['metadata']),
            generated_at=row['generated_at'],
            sent_at=row['sent_at'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    # ==================== ReportTemplate CRUD ====================

    def create_template(self, template: ReportTemplate) -> ReportTemplate:
        """创建报告模板"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO p19_report_templates
            (user_id, name, description, report_type, template_content, sections, is_default, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template.user_id,
            template.name,
            template.description,
            template.report_type,
            template.template_content,
            json.dumps(template.sections),
            template.is_default,
            template.is_active,
            template.created_at,
            template.updated_at
        ))

        template.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return template

    def get_template(self, template_id: int) -> Optional[ReportTemplate]:
        """获取模板"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM p19_report_templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_template(row)
        return None

    def get_user_templates(self, user_id: int) -> List[ReportTemplate]:
        """获取用户模板"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM p19_report_templates
            WHERE user_id = ?
            ORDER BY is_default DESC, name
        """, (user_id,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_template(row) for row in rows]

    def update_template(self, template: ReportTemplate) -> ReportTemplate:
        """更新模板"""
        template.updated_at = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE p19_report_templates
            SET name=?, description=?, report_type=?, template_content=?, sections=?,
                is_default=?, is_active=?, updated_at=?
            WHERE id=?
        """, (
            template.name,
            template.description,
            template.report_type,
            template.template_content,
            json.dumps(template.sections),
            template.is_default,
            template.is_active,
            template.updated_at,
            template.id
        ))

        conn.commit()
        conn.close()
        return template

    def delete_template(self, template_id: int) -> bool:
        """删除模板"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM p19_report_templates WHERE id = ?", (template_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return deleted

    def _row_to_template(self, row: sqlite3.Row) -> ReportTemplate:
        """将数据库行转换为 ReportTemplate 对象"""
        return ReportTemplate(
            id=row['id'],
            user_id=row['user_id'],
            name=row['name'],
            description=row['description'],
            report_type=row['report_type'],
            template_content=row['template_content'],
            sections=json.loads(row['sections']),
            is_default=bool(row['is_default']),
            is_active=bool(row['is_active']),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


# ==================== 单例模式 ====================

_db_instance = None

def get_assistant_db(db_path: str = "test.db") -> AssistantDB:
    """获取数据库单例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = AssistantDB(db_path)
    return _db_instance
