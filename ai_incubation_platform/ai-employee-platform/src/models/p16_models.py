"""
P16 职业发展规划 - 数据模型层
版本：v16.0.0
主题：职业发展规划 (Career Development Planning)
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import sqlite3
import json
from pathlib import Path


# ============================================================================
# 枚举类型定义
# ============================================================================

class SkillLevel(Enum):
    """技能等级"""
    BEGINNER = "beginner"  # 初学者
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"  # 高级
    EXPERT = "expert"  # 专家
    MASTER = "master"  # 大师


class SkillCategory(Enum):
    """技能类别"""
    TECHNICAL = "technical"  # 技术技能
    SOFT_SKILL = "soft_skill"  # 软技能
    DOMAIN = "domain"  # 领域知识
    CERTIFICATION = "certification"  # 认证资质
    LEADERSHIP = "leadership"  # 领导力


class CareerPathType(Enum):
    """职业路径类型"""
    INDIVIDUAL_CONTRIBUTOR = "individual_contributor"  # 个人贡献者
    MANAGEMENT = "management"  # 管理路线
    TECHNICAL_EXPERT = "technical_expert"  # 技术专家


class MentorshipStatus(Enum):
    """导师关系状态"""
    PENDING = "pending"  # 待确认
    ACTIVE = "active"  # 进行中
    COMPLETED = "completed"  # 已完成
    PAUSED = "paused"  # 已暂停
    TERMINATED = "terminated"  # 已终止


class DevelopmentPlanStatus(Enum):
    """发展计划状态"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 进行中
    ON_HOLD = "on_hold"  # 暂停
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"  # 已归档


class GoalType(Enum):
    """目标类型"""
    SKILL_ACQUISITION = "skill_acquisition"  # 技能学习
    CERTIFICATION = "certification"  # 认证获取
    PROJECT_COMPLETION = "project_completion"  # 项目完成
    PROMOTION = "promotion"  # 晋升
    ROLE_TRANSITION = "role_transition"  # 角色转换


class GoalStatus(Enum):
    """目标状态"""
    NOT_STARTED = "not_started"  # 未开始
    IN_PROGRESS = "in_progress"  # 进行中
    BLOCKED = "blocked"  # 受阻
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class DependencyType(Enum):
    """依赖关系类型"""
    PREREQUISITE = "prerequisite"  # 先决条件
    COREQUISITE = "corequisite"  # 共修条件
    RECOMMENDED = "recommended"  # 推荐前置


class PromotionReadiness(Enum):
    """晋升准备度"""
    NOT_READY = "not_ready"  # 未准备好
    DEVELOPING = "developing"  # 发展中
    READY = "ready"  # 已准备好
    EXCEEDED = "exceeded"  # 超越要求


# ============================================================================
# 技能图谱模型
# ============================================================================

@dataclass
class Skill:
    """技能定义"""
    name: str
    description: str
    category: SkillCategory
    parent_skill_id: Optional[str] = None  # 父技能 ID（用于技能树）
    tags: Optional[List[str]] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parent_skill_id": self.parent_skill_id,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            category=SkillCategory(data["category"]),
            parent_skill_id=data.get("parent_skill_id"),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class SkillDependency:
    """技能依赖关系"""
    from_skill_id: str  # 前置技能
    to_skill_id: str  # 目标技能
    dependency_type: DependencyType
    strength: float = 1.0  # 依赖强度 0-1
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_skill_id": self.from_skill_id,
            "to_skill_id": self.to_skill_id,
            "dependency_type": self.dependency_type.value,
            "strength": self.strength,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillDependency":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            from_skill_id=data["from_skill_id"],
            to_skill_id=data["to_skill_id"],
            dependency_type=DependencyType(data["dependency_type"]),
            strength=data.get("strength", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


@dataclass
class EmployeeSkill:
    """员工技能记录"""
    employee_id: str
    skill_id: str
    level: SkillLevel
    years_of_experience: float  # 从业年限
    self_assessed: bool  # 是否自评
    verified: bool = False  # 是否已验证
    evidence: Optional[str] = None  # 证明材料/项目链接
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "skill_id": self.skill_id,
            "level": self.level.value,
            "years_of_experience": self.years_of_experience,
            "self_assessed": self.self_assessed,
            "verified": self.verified,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmployeeSkill":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            skill_id=data["skill_id"],
            level=SkillLevel(data["level"]),
            years_of_experience=data.get("years_of_experience", 0),
            self_assessed=data.get("self_assessed", True),
            verified=data.get("verified", False),
            evidence=data.get("evidence"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class SkillGrowth:
    """技能成长记录"""
    employee_id: str
    skill_id: str
    from_level: SkillLevel
    to_level: SkillLevel
    growth_type: str  # training/project/self_study
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recorded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "skill_id": self.skill_id,
            "from_level": self.from_level.value,
            "to_level": self.to_level.value,
            "growth_type": self.growth_type,
            "recorded_at": self.recorded_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillGrowth":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            skill_id=data["skill_id"],
            from_level=SkillLevel(data["from_level"]),
            to_level=SkillLevel(data["to_level"]),
            growth_type=data["growth_type"],
            recorded_at=datetime.fromisoformat(data["recorded_at"]) if "recorded_at" in data else datetime.now(),
        )


# ============================================================================
# 职业路径模型
# ============================================================================

@dataclass
class CareerRole:
    """职业角色定义"""
    name: str
    description: str
    level: int  # 职级 1-10
    path_type: CareerPathType
    required_skills: Dict[str, int]  # skill_id -> minimum_level (1-5)
    recommended_skills: Optional[List[str]] = None
    salary_range_min: Optional[int] = None
    salary_range_max: Optional[int] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "path_type": self.path_type.value,
            "required_skills": self.required_skills,
            "recommended_skills": self.recommended_skills or [],
            "salary_range_min": self.salary_range_min,
            "salary_range_max": self.salary_range_max,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CareerRole":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            level=data["level"],
            path_type=CareerPathType(data["path_type"]),
            required_skills=data.get("required_skills", {}),
            recommended_skills=data.get("recommended_skills", []),
            salary_range_min=data.get("salary_range_min"),
            salary_range_max=data.get("salary_range_max"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class RoleTransition:
    """角色转换路径"""
    from_role_id: str
    to_role_id: str
    typical_duration_months: int
    transition_difficulty: str  # easy/medium/hard
    key_skills_to_develop: Optional[List[str]] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_role_id": self.from_role_id,
            "to_role_id": self.to_role_id,
            "typical_duration_months": self.typical_duration_months,
            "transition_difficulty": self.transition_difficulty,
            "key_skills_to_develop": self.key_skills_to_develop or [],
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoleTransition":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            from_role_id=data["from_role_id"],
            to_role_id=data["to_role_id"],
            typical_duration_months=data["typical_duration_months"],
            transition_difficulty=data["transition_difficulty"],
            key_skills_to_develop=data.get("key_skills_to_develop", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


@dataclass
class CareerPathRecommendation:
    """职业路径推荐"""
    employee_id: str
    recommended_role_id: str
    current_role_id: Optional[str] = None
    match_score: float = 0.0
    reasoning: Optional[str] = None
    skill_gaps: Optional[Dict[str, int]] = None  # skill_id -> gap_level
    estimated_timeline_months: Optional[int] = None
    confidence: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "recommended_role_id": self.recommended_role_id,
            "current_role_id": self.current_role_id,
            "match_score": self.match_score,
            "reasoning": self.reasoning,
            "skill_gaps": self.skill_gaps or {},
            "estimated_timeline_months": self.estimated_timeline_months,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CareerPathRecommendation":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            recommended_role_id=data["recommended_role_id"],
            current_role_id=data.get("current_role_id"),
            match_score=data.get("match_score", 0.0),
            reasoning=data.get("reasoning"),
            skill_gaps=data.get("skill_gaps", {}),
            estimated_timeline_months=data.get("estimated_timeline_months"),
            confidence=data.get("confidence", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


# ============================================================================
# 发展计划模型
# ============================================================================

@dataclass
class DevelopmentPlan:
    """员工发展计划"""
    employee_id: str
    plan_name: str
    status: DevelopmentPlanStatus
    target_role_id: Optional[str] = None
    start_date: Optional[date] = None
    target_completion_date: Optional[date] = None
    manager_id: Optional[str] = None
    mentor_id: Optional[str] = None
    notes: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "plan_name": self.plan_name,
            "status": self.status.value,
            "target_role_id": self.target_role_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "target_completion_date": self.target_completion_date.isoformat() if self.target_completion_date else None,
            "manager_id": self.manager_id,
            "mentor_id": self.mentor_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevelopmentPlan":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            plan_name=data["plan_name"],
            status=DevelopmentPlanStatus(data["status"]),
            target_role_id=data.get("target_role_id"),
            start_date=date.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            target_completion_date=date.fromisoformat(data["target_completion_date"]) if data.get("target_completion_date") else None,
            manager_id=data.get("manager_id"),
            mentor_id=data.get("mentor_id"),
            notes=data.get("notes"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class DevelopmentGoal:
    """发展目标"""
    plan_id: str
    goal_type: GoalType
    title: str
    description: str
    status: GoalStatus
    skill_id: Optional[str] = None
    target_level: Optional[SkillLevel] = None
    priority: int = 1  # 1-5, 1 最高
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "goal_type": self.goal_type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "skill_id": self.skill_id,
            "target_level": self.target_level.value if self.target_level else None,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress_percent": self.progress_percent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevelopmentGoal":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            plan_id=data["plan_id"],
            goal_type=GoalType(data["goal_type"]),
            title=data["title"],
            description=data.get("description", ""),
            status=GoalStatus(data["status"]),
            skill_id=data.get("skill_id"),
            target_level=SkillLevel(data["target_level"]) if data.get("target_level") else None,
            priority=data.get("priority", 1),
            due_date=date.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            progress_percent=data.get("progress_percent", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class DevelopmentActivity:
    """发展活动记录"""
    goal_id: str
    activity_type: str  # training/project/reading/mentorship/certification
    title: str
    description: str
    hours_spent: float = 0.0
    completed: bool = False
    evidence_url: Optional[str] = None
    feedback: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "activity_type": self.activity_type,
            "title": self.title,
            "description": self.description,
            "hours_spent": self.hours_spent,
            "completed": self.completed,
            "evidence_url": self.evidence_url,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevelopmentActivity":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            goal_id=data["goal_id"],
            activity_type=data["activity_type"],
            title=data["title"],
            description=data.get("description", ""),
            hours_spent=data.get("hours_spent", 0.0),
            completed=data.get("completed", False),
            evidence_url=data.get("evidence_url"),
            feedback=data.get("feedback"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )


# ============================================================================
# 导师匹配模型
# ============================================================================

@dataclass
class MentorProfile:
    """导师档案"""
    employee_id: str
    areas_of_expertise: List[str]  # skill_ids
    mentoring_capacity: int = 3  # 最多指导人数
    current_mentees: int = 0
    availability: str = "available"  # available/limited/unavailable
    mentoring_style: Optional[str] = None  # hands_on/guiding/autonomous
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "areas_of_expertise": self.areas_of_expertise,
            "mentoring_capacity": self.mentoring_capacity,
            "current_mentees": self.current_mentees,
            "availability": self.availability,
            "mentoring_style": self.mentoring_style,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MentorProfile":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            areas_of_expertise=data.get("areas_of_expertise", []),
            mentoring_capacity=data.get("mentoring_capacity", 3),
            current_mentees=data.get("current_mentees", 0),
            availability=data.get("availability", "available"),
            mentoring_style=data.get("mentoring_style"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class MenteeProfile:
    """学员档案"""
    employee_id: str
    development_goals: Optional[List[str]] = None  # goal_ids
    preferred_mentor_style: Optional[str] = None
    availability: str = "active"  # active/paused/completed
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "development_goals": self.development_goals or [],
            "preferred_mentor_style": self.preferred_mentor_style,
            "availability": self.availability,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MenteeProfile":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            development_goals=data.get("development_goals", []),
            preferred_mentor_style=data.get("preferred_mentor_style"),
            availability=data.get("availability", "active"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class MentorshipMatch:
    """导师匹配记录"""
    mentor_id: str
    mentee_id: str
    match_score: float
    match_reason: str
    status: MentorshipStatus
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    goals: Optional[List[str]] = None  # 匹配的目标 skill_ids
    meeting_frequency: str = "biweekly"  # weekly/biweekly/monthly
    notes: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mentor_id": self.mentor_id,
            "mentee_id": self.mentee_id,
            "match_score": self.match_score,
            "match_reason": self.match_reason,
            "status": self.status.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "goals": self.goals or [],
            "meeting_frequency": self.meeting_frequency,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MentorshipMatch":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            mentor_id=data["mentor_id"],
            mentee_id=data["mentee_id"],
            match_score=data.get("match_score", 0.0),
            match_reason=data.get("match_reason", ""),
            status=MentorshipStatus(data["status"]),
            start_date=date.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            end_date=date.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            goals=data.get("goals", []),
            meeting_frequency=data.get("meeting_frequency", "biweekly"),
            notes=data.get("notes"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class MentorshipSession:
    """导师会话记录"""
    match_id: str
    session_date: datetime
    duration_minutes: int
    topics_discussed: Optional[List[str]] = None
    notes: Optional[str] = None
    action_items: Optional[List[str]] = None
    next_session_date: Optional[date] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "match_id": self.match_id,
            "session_date": self.session_date.isoformat(),
            "duration_minutes": self.duration_minutes,
            "topics_discussed": self.topics_discussed or [],
            "notes": self.notes,
            "action_items": self.action_items or [],
            "next_session_date": self.next_session_date.isoformat() if self.next_session_date else None,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MentorshipSession":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            match_id=data["match_id"],
            session_date=datetime.fromisoformat(data["session_date"]) if isinstance(data["session_date"], str) else data["session_date"],
            duration_minutes=data["duration_minutes"],
            topics_discussed=data.get("topics_discussed", []),
            notes=data.get("notes"),
            action_items=data.get("action_items", []),
            next_session_date=date.fromisoformat(data["next_session_date"]) if data.get("next_session_date") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


# ============================================================================
# 晋升规划模型
# ============================================================================

@dataclass
class PromotionReadinessAssessment:
    """晋升准备度评估"""
    employee_id: str
    target_role_id: str
    current_role_id: Optional[str] = None
    overall_readiness: PromotionReadiness = PromotionReadiness.NOT_READY
    readiness_score: float = 0.0  # 0-100
    skill_gaps: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # skill_id -> {current, required, gap}
    experience_gaps: Optional[List[str]] = None
    strengths: Optional[List[str]] = None
    development_recommendations: Optional[List[str]] = None
    estimated_timeline_months: Optional[int] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "target_role_id": self.target_role_id,
            "current_role_id": self.current_role_id,
            "overall_readiness": self.overall_readiness.value,
            "readiness_score": self.readiness_score,
            "skill_gaps": self.skill_gaps,
            "experience_gaps": self.experience_gaps or [],
            "strengths": self.strengths or [],
            "development_recommendations": self.development_recommendations or [],
            "estimated_timeline_months": self.estimated_timeline_months,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromotionReadinessAssessment":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            target_role_id=data["target_role_id"],
            current_role_id=data.get("current_role_id"),
            overall_readiness=PromotionReadiness(data["overall_readiness"]),
            readiness_score=data.get("readiness_score", 0.0),
            skill_gaps=data.get("skill_gaps", {}),
            experience_gaps=data.get("experience_gaps", []),
            strengths=data.get("strengths", []),
            development_recommendations=data.get("development_recommendations", []),
            estimated_timeline_months=data.get("estimated_timeline_months"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class PromotionHistory:
    """晋升历史记录"""
    employee_id: str
    from_role_id: Optional[str] = None
    to_role_id: str = ""
    promotion_date: date = None
    promotion_type: str = "promotion"  # promotion/transfer/role_expansion
    decision_maker_id: Optional[str] = None
    notes: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "from_role_id": self.from_role_id,
            "to_role_id": self.to_role_id,
            "promotion_date": (self.promotion_date or date.today()).isoformat(),
            "promotion_type": self.promotion_type,
            "decision_maker_id": self.decision_maker_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromotionHistory":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            from_role_id=data.get("from_role_id"),
            to_role_id=data["to_role_id"],
            promotion_date=date.fromisoformat(data["promotion_date"]) if data.get("promotion_date") else date.today(),
            promotion_type=data.get("promotion_type", "promotion"),
            decision_maker_id=data.get("decision_maker_id"),
            notes=data.get("notes"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


# ============================================================================
# 数据库持久化层
# ============================================================================

class CareerDevelopmentDB:
    """职业发展数据库操作类"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "test.db"
        self.db_path = str(db_path)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 技能图谱表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                parent_skill_id TEXT,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_dependencies (
                id TEXT PRIMARY KEY,
                from_skill_id TEXT NOT NULL,
                to_skill_id TEXT NOT NULL,
                dependency_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (from_skill_id) REFERENCES skills(id),
                FOREIGN KEY (to_skill_id) REFERENCES skills(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_skills (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                level TEXT NOT NULL,
                years_of_experience REAL DEFAULT 0,
                self_assessed INTEGER DEFAULT 1,
                verified INTEGER DEFAULT 0,
                evidence TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_growth (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                from_level TEXT NOT NULL,
                to_level TEXT NOT NULL,
                growth_type TEXT,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)

        # 职业路径表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS career_roles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                level INTEGER NOT NULL,
                path_type TEXT NOT NULL,
                required_skills TEXT DEFAULT '{}',
                recommended_skills TEXT DEFAULT '[]',
                salary_range_min INTEGER,
                salary_range_max INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_transitions (
                id TEXT PRIMARY KEY,
                from_role_id TEXT NOT NULL,
                to_role_id TEXT NOT NULL,
                typical_duration_months INTEGER,
                transition_difficulty TEXT,
                key_skills_to_develop TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (from_role_id) REFERENCES career_roles(id),
                FOREIGN KEY (to_role_id) REFERENCES career_roles(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS career_path_recommendations (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                recommended_role_id TEXT NOT NULL,
                current_role_id TEXT,
                match_score REAL DEFAULT 0.0,
                reasoning TEXT,
                skill_gaps TEXT DEFAULT '{}',
                estimated_timeline_months INTEGER,
                confidence REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (recommended_role_id) REFERENCES career_roles(id)
            )
        """)

        # 发展计划表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS development_plans (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                status TEXT NOT NULL,
                target_role_id TEXT,
                start_date TEXT,
                target_completion_date TEXT,
                manager_id TEXT,
                mentor_id TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (target_role_id) REFERENCES career_roles(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS development_goals (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                goal_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                skill_id TEXT,
                target_level TEXT,
                priority INTEGER DEFAULT 1,
                due_date TEXT,
                completed_at TEXT,
                progress_percent REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (plan_id) REFERENCES development_plans(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS development_activities (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                hours_spent REAL DEFAULT 0.0,
                completed INTEGER DEFAULT 0,
                evidence_url TEXT,
                feedback TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (goal_id) REFERENCES development_goals(id)
            )
        """)

        # 导师匹配表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mentor_profiles (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                areas_of_expertise TEXT DEFAULT '[]',
                mentoring_capacity INTEGER DEFAULT 3,
                current_mentees INTEGER DEFAULT 0,
                availability TEXT DEFAULT 'available',
                mentoring_style TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mentee_profiles (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                development_goals TEXT DEFAULT '[]',
                preferred_mentor_style TEXT,
                availability TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mentorship_matches (
                id TEXT PRIMARY KEY,
                mentor_id TEXT NOT NULL,
                mentee_id TEXT NOT NULL,
                match_score REAL DEFAULT 0.0,
                match_reason TEXT,
                status TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                goals TEXT DEFAULT '[]',
                meeting_frequency TEXT DEFAULT 'biweekly',
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (mentor_id) REFERENCES mentor_profiles(id),
                FOREIGN KEY (mentee_id) REFERENCES mentee_profiles(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mentorship_sessions (
                id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                session_date TEXT NOT NULL,
                duration_minutes INTEGER,
                topics_discussed TEXT DEFAULT '[]',
                notes TEXT,
                action_items TEXT DEFAULT '[]',
                next_session_date TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (match_id) REFERENCES mentorship_matches(id)
            )
        """)

        # 晋升规划表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promotion_readiness_assessments (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                target_role_id TEXT NOT NULL,
                current_role_id TEXT,
                overall_readiness TEXT NOT NULL,
                readiness_score REAL DEFAULT 0.0,
                skill_gaps TEXT DEFAULT '{}',
                experience_gaps TEXT DEFAULT '[]',
                strengths TEXT DEFAULT '[]',
                development_recommendations TEXT DEFAULT '[]',
                estimated_timeline_months INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (target_role_id) REFERENCES career_roles(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promotion_history (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                from_role_id TEXT,
                to_role_id TEXT NOT NULL,
                promotion_date TEXT NOT NULL,
                promotion_type TEXT DEFAULT 'promotion',
                decision_maker_id TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (to_role_id) REFERENCES career_roles(id)
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employee_skills_employee ON employee_skills(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employee_skills_skill ON employee_skills(skill_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_development_plans_employee ON development_plans(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_development_goals_plan ON development_goals(plan_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mentorship_matches_mentor ON mentorship_matches(mentor_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mentorship_matches_mentee ON mentorship_matches(mentee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_career_path_recommendations_employee ON career_path_recommendations(employee_id)")

        conn.commit()
        conn.close()

    # ========================================================================
    # 通用 CRUD 操作
    # ========================================================================

    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """插入记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 处理列表和字典类型，转换为 JSON 字符串
        processed_data = {}
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                processed_data[key] = json.dumps(value)
            elif isinstance(value, bool):
                processed_data[key] = 1 if value else 0
            else:
                processed_data[key] = value

        columns = list(processed_data.keys())
        placeholders = [":" + col for col in columns]
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

        cursor.execute(sql, processed_data)
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()

        return str(record_id) if record_id else data.get("id", "")

    def get(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """获取单条记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None

        # 解析 JSON 字符串
        result = dict(row)
        json_fields = ['tags', 'required_skills', 'recommended_skills', 'skill_gaps',
                       'areas_of_expertise', 'development_goals', 'topics_discussed',
                       'action_items', 'experience_gaps', 'strengths', 'dimensions',
                       'risk_factors', 'recommendations', 'stress_sources', 'physical_symptoms',
                       'key_skills_to_develop', 'goals', 'required_skills', 'dimensions']
        for field in json_fields:
            if field in result and result[field]:
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return result

    def update(self, table: str, record_id: str, data: Dict[str, Any]) -> bool:
        """更新记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 处理列表和字典类型，转换为 JSON 字符串
        processed_data = {}
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                processed_data[key] = json.dumps(value)
            elif isinstance(value, bool):
                processed_data[key] = 1 if value else 0
            else:
                processed_data[key] = value

        # 检查表是否有 updated_at 列
        has_updated_at = table not in ['development_activities', 'skill_growth', 'mentorship_sessions', 'promotion_history']

        set_clause = ", ".join([f"{col} = ?" for col in processed_data.keys()])
        if has_updated_at:
            sql = f"UPDATE {table} SET {set_clause}, updated_at = datetime('now') WHERE id = ?"
        else:
            sql = f"UPDATE {table} SET {set_clause} WHERE id = ?"

        params = list(processed_data.values()) + [record_id]
        cursor.execute(sql, params)
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()

        return success

    def delete(self, table: str, record_id: str) -> bool:
        """删除记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    def list(self, table: str, filters: Optional[Dict[str, Any]] = None,
             order_by: str = "created_at DESC", limit: int = 100) -> List[Dict[str, Any]]:
        """列出记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        where_clause = ""
        params = []
        if filters:
            conditions = []
            for col, val in filters.items():
                conditions.append(f"{col} = ?")
                params.append(val)
            where_clause = " WHERE " + " AND ".join(conditions)

        sql = f"SELECT * FROM {table}{where_clause} ORDER BY {order_by} LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        # 解析 JSON 字符串
        json_fields = ['tags', 'required_skills', 'recommended_skills', 'skill_gaps',
                       'areas_of_expertise', 'development_goals', 'topics_discussed',
                       'action_items', 'experience_gaps', 'strengths', 'dimensions',
                       'risk_factors', 'recommendations', 'stress_sources', 'physical_symptoms',
                       'key_skills_to_develop', 'goals']
        result = []
        for row in rows:
            row_dict = dict(row)
            for field in json_fields:
                if field in row_dict and row_dict[field]:
                    try:
                        row_dict[field] = json.loads(row_dict[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            result.append(row_dict)

        return result

    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行自定义查询"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
