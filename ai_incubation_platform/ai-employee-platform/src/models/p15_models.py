"""
P15 员工福祉管理 - 数据模型层
版本：v15.0.0
主题：员工福祉管理 (Employee Wellness Management)
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

class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AssessmentType(Enum):
    """评估类型"""
    MENTAL_HEALTH = "mental_health"
    STRESS = "stress"
    BURNOUT = "burnout"
    SATISFACTION = "satisfaction"
    ENGAGEMENT = "engagement"
    WORK_LIFE_BALANCE = "work_life_balance"


class SurveyType(Enum):
    """调查类型"""
    SATISFACTION = "satisfaction"
    ENGAGEMENT = "engagement"
    PULSE = "pulse"
    EXIT = "exit"
    ONBOARDING = "onboarding"


class QuestionType(Enum):
    """问题类型"""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    LIKERT_SCALE = "likert_scale"
    TEXT = "text"
    RATING = "rating"


class LeaveType(Enum):
    """假期类型"""
    ANNUAL = "annual"
    SICK = "sick"
    PERSONAL = "personal"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    BEREAVEMENT = "bereavement"
    UNPAID = "unpaid"
    REMOTE = "remote"


class LeaveStatus(Enum):
    """假期申请状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class BenefitType(Enum):
    """福利类型"""
    INSURANCE = "insurance"
    PENSION = "pension"
    SUBSIDY = "subsidy"
    BONUS = "bonus"
    STOCK_OPTION = "stock_option"
    WELLNESS = "wellness"
    EDUCATION = "education"


class InterventionType(Enum):
    """干预措施类型"""
    COUNSELING = "counseling"
    WORKLOAD_ADJUSTMENT = "workload_adjustment"
    SALARY_ADJUSTMENT = "salary_adjustment"
    ROLE_CHANGE = "role_change"
    MENTORSHIP = "mentorship"
    TRAINING = "training"
    TIME_OFF = "time_off"
    FLEXIBLE_HOURS = "flexible_hours"


class InterventionStatus(Enum):
    """干预措施状态"""
    PROPOSED = "proposed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FOLLOW_UP = "follow_up"


class AlertType(Enum):
    """预警类型"""
    OVERTIME = "overtime"
    BURNOUT_RISK = "burnout_risk"
    HIGH_TURNOVER_RISK = "high_turnover_risk"
    LOW_SATISFACTION = "low_satisfaction"
    WORK_LIFE_IMBALANCE = "work_life_imbalance"
    MENTAL_HEALTH = "mental_health"


class AlertSeverity(Enum):
    """预警严重程度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CounselingType(Enum):
    """心理咨询类型"""
    STRESS_MANAGEMENT = "stress_management"
    CAREER_GUIDANCE = "career_guidance"
    WORK_LIFE_BALANCE = "work_life_balance"
    MENTAL_HEALTH = "mental_health"
    CRISIS_INTERVENTION = "crisis_intervention"


class CounselingStatus(Enum):
    """心理咨询状态"""
    REQUESTED = "requested"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# ============================================================================
# 心理健康支持模型
# ============================================================================

@dataclass
class MentalHealthAssessment:
    """心理健康评估记录"""
    employee_id: str
    assessment_type: AssessmentType
    overall_score: float  # 0-100
    dimensions: Dict[str, float]  # 各维度分数
    risk_factors: List[str]  # 风险因素列表
    recommendations: List[str]  # 建议列表
    assessor_id: Optional[str] = None
    notes: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "assessment_type": self.assessment_type.value,
            "overall_score": self.overall_score,
            "dimensions": self.dimensions,
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations,
            "assessor_id": self.assessor_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MentalHealthAssessment":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            assessment_type=AssessmentType(data["assessment_type"]),
            overall_score=data["overall_score"],
            dimensions=data.get("dimensions", {}),
            risk_factors=data.get("risk_factors", []),
            recommendations=data.get("recommendations", []),
            assessor_id=data.get("assessor_id"),
            notes=data.get("notes"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class StressLevel:
    """压力水平追踪记录"""
    employee_id: str
    stress_score: float  # 0-100, 越高压力越大
    stress_sources: List[str]  # 压力来源
    physical_symptoms: List[str]  # 身体症状
    emotional_state: str  # 情绪状态
    sleep_quality: Optional[float] = None  # 睡眠质量 0-100
    energy_level: Optional[float] = None  # 精力水平 0-100
    measurement_method: Optional[str] = None  # 测量方法 (self_report/sensor/assessment)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recorded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "stress_score": self.stress_score,
            "stress_sources": self.stress_sources,
            "physical_symptoms": self.physical_symptoms,
            "emotional_state": self.emotional_state,
            "sleep_quality": self.sleep_quality,
            "energy_level": self.energy_level,
            "measurement_method": self.measurement_method,
            "recorded_at": self.recorded_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StressLevel":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            stress_score=data["stress_score"],
            stress_sources=data.get("stress_sources", []),
            physical_symptoms=data.get("physical_symptoms", []),
            emotional_state=data.get("emotional_state", "unknown"),
            sleep_quality=data.get("sleep_quality"),
            energy_level=data.get("energy_level"),
            measurement_method=data.get("measurement_method"),
            recorded_at=datetime.fromisoformat(data["recorded_at"]) if "recorded_at" in data else datetime.now(),
        )


@dataclass
class CounselingSession:
    """心理咨询会话记录"""
    employee_id: str
    counselor_id: str
    counseling_type: CounselingType
    session_date: datetime
    duration_minutes: int
    status: CounselingStatus
    notes: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None
    session_number: int = 1  # 第几次咨询
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "counselor_id": self.counselor_id,
            "counseling_type": self.counseling_type.value,
            "session_date": self.session_date.isoformat(),
            "duration_minutes": self.duration_minutes,
            "status": self.status.value,
            "notes": self.notes,
            "follow_up_required": self.follow_up_required,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "session_number": self.session_number,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CounselingSession":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            counselor_id=data["counselor_id"],
            counseling_type=CounselingType(data["counseling_type"]),
            session_date=datetime.fromisoformat(data["session_date"]) if isinstance(data["session_date"], str) else data["session_date"],
            duration_minutes=data["duration_minutes"],
            status=CounselingStatus(data["status"]),
            notes=data.get("notes"),
            follow_up_required=data.get("follow_up_required", False),
            follow_up_date=datetime.fromisoformat(data["follow_up_date"]) if data.get("follow_up_date") else None,
            session_number=data.get("session_number", 1),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class WellnessResource:
    """健康资源库"""
    title: str
    description: str
    resource_type: str  # article/video/podcast/tool/hotline
    category: str  # stress_management/mental_health/work_life_balance/etc.
    url: Optional[str] = None
    content: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    author: Optional[str] = None
    duration_minutes: Optional[int] = None  # 预计阅读/观看时长
    is_featured: bool = False
    view_count: int = 0
    helpful_count: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "resource_type": self.resource_type,
            "category": self.category,
            "url": self.url,
            "content": self.content,
            "tags": self.tags,
            "author": self.author,
            "duration_minutes": self.duration_minutes,
            "is_featured": self.is_featured,
            "view_count": self.view_count,
            "helpful_count": self.helpful_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WellnessResource":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data["title"],
            description=data["description"],
            resource_type=data["resource_type"],
            category=data["category"],
            url=data.get("url"),
            content=data.get("content"),
            tags=data.get("tags", []),
            author=data.get("author"),
            duration_minutes=data.get("duration_minutes"),
            is_featured=data.get("is_featured", False),
            view_count=data.get("view_count", 0),
            helpful_count=data.get("helpful_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


# ============================================================================
# 工作生活平衡模型
# ============================================================================

@dataclass
class WorkHourLog:
    """工时记录"""
    employee_id: str
    work_date: date
    start_time: datetime
    end_time: datetime
    break_minutes: int = 0
    work_type: str = "office"  # office/remote/overtime/weekend
    project_id: Optional[str] = None
    task_description: Optional[str] = None
    is_overtime: bool = False
    approved: bool = False
    approver_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def total_minutes(self) -> int:
        """计算总工作分钟数"""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60) - self.break_minutes

    @property
    def total_hours(self) -> float:
        """计算总工作小时数"""
        return self.total_minutes / 60.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "work_date": self.work_date.isoformat(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "break_minutes": self.break_minutes,
            "work_type": self.work_type,
            "project_id": self.project_id,
            "task_description": self.task_description,
            "is_overtime": self.is_overtime,
            "approved": self.approved,
            "approver_id": self.approver_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkHourLog":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            work_date=date.fromisoformat(data["work_date"]) if isinstance(data["work_date"], str) else data["work_date"],
            start_time=datetime.fromisoformat(data["start_time"]) if isinstance(data["start_time"], str) else data["start_time"],
            end_time=datetime.fromisoformat(data["end_time"]) if isinstance(data["end_time"], str) else data["end_time"],
            break_minutes=data.get("break_minutes", 0),
            work_type=data.get("work_type", "office"),
            project_id=data.get("project_id"),
            task_description=data.get("task_description"),
            is_overtime=data.get("is_overtime", False),
            approved=data.get("approved", False),
            approver_id=data.get("approver_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class OvertimeRecord:
    """加班记录"""
    employee_id: str
    overtime_date: date
    start_time: datetime
    end_time: datetime
    reason: str
    approved: bool = False
    approver_id: Optional[str] = None
    approval_date: Optional[datetime] = None
    compensation_type: str = "time_off"  # time_off/payment
    compensation_hours: Optional[float] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def overtime_hours(self) -> float:
        """计算加班小时数"""
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "overtime_date": self.overtime_date.isoformat(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "reason": self.reason,
            "approved": self.approved,
            "approver_id": self.approver_id,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "compensation_type": self.compensation_type,
            "compensation_hours": self.compensation_hours,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OvertimeRecord":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            overtime_date=date.fromisoformat(data["overtime_date"]) if isinstance(data["overtime_date"], str) else data["overtime_date"],
            start_time=datetime.fromisoformat(data["start_time"]) if isinstance(data["start_time"], str) else data["start_time"],
            end_time=datetime.fromisoformat(data["end_time"]) if isinstance(data["end_time"], str) else data["end_time"],
            reason=data["reason"],
            approved=data.get("approved", False),
            approver_id=data.get("approver_id"),
            approval_date=datetime.fromisoformat(data["approval_date"]) if data.get("approval_date") else None,
            compensation_type=data.get("compensation_type", "time_off"),
            compensation_hours=data.get("compensation_hours"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class WorkLifeBalanceMetrics:
    """工作生活平衡指标"""
    employee_id: str
    balance_score: float  # 0-100
    work_hours_score: float  # 工时得分
    rest_compliance_score: float  # 休息合规得分
    vacation_utilization_score: float  # 假期使用得分
    overtime_ratio: float  # 加班比例 0-1
    weekend_work_days: int  # 周末工作天数
    average_daily_hours: float  # 平均每日工时
    consecutive_work_days: int  # 连续工作天数
    last_vacation_date: Optional[date] = None
    risk_level: RiskLevel = RiskLevel.LOW
    recommendations: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    calculated_at: datetime = field(default_factory=datetime.now)
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "balance_score": self.balance_score,
            "work_hours_score": self.work_hours_score,
            "rest_compliance_score": self.rest_compliance_score,
            "vacation_utilization_score": self.vacation_utilization_score,
            "overtime_ratio": self.overtime_ratio,
            "weekend_work_days": self.weekend_work_days,
            "average_daily_hours": self.average_daily_hours,
            "consecutive_work_days": self.consecutive_work_days,
            "last_vacation_date": self.last_vacation_date.isoformat() if self.last_vacation_date else None,
            "risk_level": self.risk_level.value,
            "recommendations": self.recommendations,
            "calculated_at": self.calculated_at.isoformat(),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkLifeBalanceMetrics":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            balance_score=data["balance_score"],
            work_hours_score=data["work_hours_score"],
            rest_compliance_score=data["rest_compliance_score"],
            vacation_utilization_score=data["vacation_utilization_score"],
            overtime_ratio=data["overtime_ratio"],
            weekend_work_days=data["weekend_work_days"],
            average_daily_hours=data["average_daily_hours"],
            consecutive_work_days=data["consecutive_work_days"],
            last_vacation_date=date.fromisoformat(data["last_vacation_date"]) if data.get("last_vacation_date") else None,
            risk_level=RiskLevel(data["risk_level"]),
            recommendations=data.get("recommendations", []),
            calculated_at=datetime.fromisoformat(data["calculated_at"]) if "calculated_at" in data else datetime.now(),
            period_start=date.fromisoformat(data["period_start"]) if data.get("period_start") else None,
            period_end=date.fromisoformat(data["period_end"]) if data.get("period_end") else None,
        )


# ============================================================================
# 福利管理模型
# ============================================================================

@dataclass
class BenefitPlan:
    """福利计划"""
    name: str
    description: str
    benefit_type: BenefitType
    coverage_type: str  # all/dept/role/level
    coverage_criteria: Dict[str, Any] = field(default_factory=dict)
    provider: Optional[str] = None
    coverage_amount: Optional[float] = None  # 保额/金额
    employee_contribution: float = 0.0  # 员工缴纳比例
    employer_contribution: float = 1.0  # 雇主缴纳比例
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    is_active: bool = True
    enrollment_count: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "benefit_type": self.benefit_type.value,
            "coverage_type": self.coverage_type,
            "coverage_criteria": self.coverage_criteria,
            "provider": self.provider,
            "coverage_amount": self.coverage_amount,
            "employee_contribution": self.employee_contribution,
            "employer_contribution": self.employer_contribution,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "is_active": self.is_active,
            "enrollment_count": self.enrollment_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenefitPlan":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data["description"],
            benefit_type=BenefitType(data["benefit_type"]),
            coverage_type=data.get("coverage_type", "all"),
            coverage_criteria=data.get("coverage_criteria", {}),
            provider=data.get("provider"),
            coverage_amount=data.get("coverage_amount"),
            employee_contribution=data.get("employee_contribution", 0.0),
            employer_contribution=data.get("employer_contribution", 1.0),
            effective_date=date.fromisoformat(data["effective_date"]) if data.get("effective_date") else None,
            expiration_date=date.fromisoformat(data["expiration_date"]) if data.get("expiration_date") else None,
            is_active=data.get("is_active", True),
            enrollment_count=data.get("enrollment_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class EmployeeBenefitEnrollment:
    """员工福利注册"""
    employee_id: str
    plan_id: str
    enrollment_date: date
    status: str  # enrolled/active/inactive/terminated
    beneficiary_name: Optional[str] = None
    beneficiary_relationship: Optional[str] = None
    coverage_start_date: Optional[date] = None
    coverage_end_date: Optional[date] = None
    monthly_premium: Optional[float] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "plan_id": self.plan_id,
            "enrollment_date": self.enrollment_date.isoformat(),
            "status": self.status,
            "beneficiary_name": self.beneficiary_name,
            "beneficiary_relationship": self.beneficiary_relationship,
            "coverage_start_date": self.coverage_start_date.isoformat() if self.coverage_start_date else None,
            "coverage_end_date": self.coverage_end_date.isoformat() if self.coverage_end_date else None,
            "monthly_premium": self.monthly_premium,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmployeeBenefitEnrollment":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            plan_id=data["plan_id"],
            enrollment_date=date.fromisoformat(data["enrollment_date"]) if isinstance(data["enrollment_date"], str) else data["enrollment_date"],
            status=data.get("status", "enrolled"),
            beneficiary_name=data.get("beneficiary_name"),
            beneficiary_relationship=data.get("beneficiary_relationship"),
            coverage_start_date=date.fromisoformat(data["coverage_start_date"]) if data.get("coverage_start_date") else None,
            coverage_end_date=date.fromisoformat(data["coverage_end_date"]) if data.get("coverage_end_date") else None,
            monthly_premium=data.get("monthly_premium"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class LeaveBalance:
    """假期余额"""
    employee_id: str
    leave_type: LeaveType
    total_days: float  # 总天数
    used_days: float  # 已使用天数
    remaining_days: float  # 剩余天数
    accrued_days: float  # 累计天数
    carryover_days: float = 0.0  # 结转天数
    expiration_date: Optional[date] = None
    accrual_rate: Optional[float] = None  # 累计速率（天/月）
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    year: int = field(default_factory=lambda: datetime.now().year)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "leave_type": self.leave_type.value,
            "total_days": self.total_days,
            "used_days": self.used_days,
            "remaining_days": self.remaining_days,
            "accrued_days": self.accrued_days,
            "carryover_days": self.carryover_days,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "accrual_rate": self.accrual_rate,
            "year": self.year,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeaveBalance":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            leave_type=LeaveType(data["leave_type"]),
            total_days=data["total_days"],
            used_days=data["used_days"],
            remaining_days=data["remaining_days"],
            accrued_days=data["accrued_days"],
            carryover_days=data.get("carryover_days", 0.0),
            expiration_date=date.fromisoformat(data["expiration_date"]) if data.get("expiration_date") else None,
            accrual_rate=data.get("accrual_rate"),
            year=data.get("year", datetime.now().year),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class LeaveRequest:
    """假期申请"""
    employee_id: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus = LeaveStatus.PENDING
    approver_id: Optional[str] = None
    approval_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    handover_notes: Optional[str] = None
    contact_during_leave: Optional[str] = None
    total_days: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.total_days == 0.0:
            delta = self.end_date - self.start_date
            self.total_days = delta.days + 1  # 包含首尾两天

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "leave_type": self.leave_type.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_days": self.total_days,
            "reason": self.reason,
            "status": self.status.value,
            "approver_id": self.approver_id,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "rejection_reason": self.rejection_reason,
            "handover_notes": self.handover_notes,
            "contact_during_leave": self.contact_during_leave,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeaveRequest":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            leave_type=LeaveType(data["leave_type"]),
            start_date=date.fromisoformat(data["start_date"]) if isinstance(data["start_date"], str) else data["start_date"],
            end_date=date.fromisoformat(data["end_date"]) if isinstance(data["end_date"], str) else data["end_date"],
            reason=data["reason"],
            status=LeaveStatus(data["status"]),
            approver_id=data.get("approver_id"),
            approval_date=datetime.fromisoformat(data["approval_date"]) if data.get("approval_date") else None,
            rejection_reason=data.get("rejection_reason"),
            handover_notes=data.get("handover_notes"),
            contact_during_leave=data.get("contact_during_leave"),
            total_days=data.get("total_days", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class SubsidyRecord:
    """补贴记录"""
    employee_id: str
    subsidy_type: str  # meal/transport/communication/housing/etc.
    amount: float
    period_start: date
    period_end: date
    currency: str = "CNY"
    status: str = "pending"  # pending/approved/paid/rejected
    description: Optional[str] = None
    payment_date: Optional[date] = None
    approver_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "subsidy_type": self.subsidy_type,
            "amount": self.amount,
            "currency": self.currency,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "status": self.status,
            "description": self.description,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "approver_id": self.approver_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubsidyRecord":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            subsidy_type=data["subsidy_type"],
            amount=data["amount"],
            currency=data.get("currency", "CNY"),
            period_start=date.fromisoformat(data["period_start"]) if isinstance(data["period_start"], str) else data["period_start"],
            period_end=date.fromisoformat(data["period_end"]) if isinstance(data["period_end"], str) else data["period_end"],
            status=data.get("status", "pending"),
            description=data.get("description"),
            payment_date=date.fromisoformat(data["payment_date"]) if data.get("payment_date") else None,
            approver_id=data.get("approver_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


# ============================================================================
# 员工满意度调查模型
# ============================================================================

@dataclass
class SatisfactionSurvey:
    """满意度调查问卷"""
    title: str
    description: str
    survey_type: SurveyType
    is_anonymous: bool = True
    is_active: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_audience: str = "all"  # all/dept/role/custom
    target_criteria: Dict[str, Any] = field(default_factory=dict)
    reminder_enabled: bool = True
    reminder_frequency_days: int = 3
    max_reminders: int = 3
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "survey_type": self.survey_type.value,
            "is_anonymous": self.is_anonymous,
            "is_active": self.is_active,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "target_audience": self.target_audience,
            "target_criteria": self.target_criteria,
            "reminder_enabled": self.reminder_enabled,
            "reminder_frequency_days": self.reminder_frequency_days,
            "max_reminders": self.max_reminders,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SatisfactionSurvey":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data["title"],
            description=data["description"],
            survey_type=SurveyType(data["survey_type"]),
            is_anonymous=data.get("is_anonymous", True),
            is_active=data.get("is_active", False),
            start_date=datetime.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            end_date=datetime.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            target_audience=data.get("target_audience", "all"),
            target_criteria=data.get("target_criteria", {}),
            reminder_enabled=data.get("reminder_enabled", True),
            reminder_frequency_days=data.get("reminder_frequency_days", 3),
            max_reminders=data.get("max_reminders", 3),
            created_by=data.get("created_by"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class SurveyQuestion:
    """调查问题"""
    survey_id: str
    question_text: str
    question_type: QuestionType
    order: int
    is_required: bool = True
    options: Optional[List[str]] = None  # 选择题选项
    min_value: Optional[float] = None  # 评分最小值
    max_value: Optional[float] = None  # 评分最大值
    min_label: Optional[str] = None  # 最小值标签
    max_label: Optional[str] = None  # 最大值标签
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "survey_id": self.survey_id,
            "question_text": self.question_text,
            "question_type": self.question_type.value,
            "orders": self.order,
            "is_required": self.is_required,
            "options": self.options,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "min_label": self.min_label,
            "max_label": self.max_label,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurveyQuestion":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            survey_id=data["survey_id"],
            question_text=data["question_text"],
            question_type=QuestionType(data["question_type"]),
            order=data["orders"],
            is_required=data.get("is_required", True),
            options=data.get("options"),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            min_label=data.get("min_label"),
            max_label=data.get("max_label"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


@dataclass
class SurveyResponse:
    """调查回复"""
    survey_id: str
    employee_id: Optional[str] = None  # 匿名调查可能没有员工 ID
    responses: Dict[str, Any] = field(default_factory=dict)  # question_id -> answer
    overall_score: Optional[float] = None  # 总体评分
    comments: Optional[str] = None
    completion_time_seconds: Optional[int] = None
    device_type: Optional[str] = None  # mobile/desktop
    ip_hash: Optional[str] = None  # 用于防作弊（不存储原始 IP）
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    submitted_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "survey_id": self.survey_id,
            "employee_id": self.employee_id,
            "responses": self.responses,
            "overall_score": self.overall_score,
            "comments": self.comments,
            "completion_time_seconds": self.completion_time_seconds,
            "device_type": self.device_type,
            "ip_hash": self.ip_hash,
            "submitted_at": self.submitted_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurveyResponse":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            survey_id=data["survey_id"],
            employee_id=data.get("employee_id"),
            responses=data.get("responses", {}),
            overall_score=data.get("overall_score"),
            comments=data.get("comments"),
            completion_time_seconds=data.get("completion_time_seconds"),
            device_type=data.get("device_type"),
            ip_hash=data.get("ip_hash"),
            submitted_at=datetime.fromisoformat(data["submitted_at"]) if "submitted_at" in data else datetime.now(),
        )


@dataclass
class PulseSurvey:
    """脉冲调查（快速调查）"""
    title: str
    question: str
    question_type: QuestionType = QuestionType.LIKERT_SCALE
    target_audience: str = "all"
    is_active: bool = True
    expires_at: Optional[datetime] = None
    response_count: int = 0
    average_score: Optional[float] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "question": self.question,
            "question_type": self.question_type.value,
            "target_audience": self.target_audience,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "response_count": self.response_count,
            "average_score": self.average_score,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PulseSurvey":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data["title"],
            question=data["question"],
            question_type=QuestionType(data["question_type"]),
            target_audience=data.get("target_audience", "all"),
            is_active=data.get("is_active", True),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            response_count=data.get("response_count", 0),
            average_score=data.get("average_score"),
            created_by=data.get("created_by"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


@dataclass
class SatisfactionTrend:
    """满意度趋势"""
    period: str  # daily/weekly/monthly/quarterly
    period_start: date
    period_end: date
    overall_score: float
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    response_rate: float = 0.0  # 回复率
    total_responses: int = 0
    trend_direction: str = "stable"  # improving/declining/stable
    change_percentage: float = 0.0
    key_insights: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "period": self.period,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "response_rate": self.response_rate,
            "total_responses": self.total_responses,
            "trend_direction": self.trend_direction,
            "change_percentage": self.change_percentage,
            "key_insights": self.key_insights,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SatisfactionTrend":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            period=data["period"],
            period_start=date.fromisoformat(data["period_start"]) if isinstance(data["period_start"], str) else data["period_start"],
            period_end=date.fromisoformat(data["period_end"]) if isinstance(data["period_end"], str) else data["period_end"],
            overall_score=data["overall_score"],
            dimension_scores=data.get("dimension_scores", {}),
            response_rate=data.get("response_rate", 0.0),
            total_responses=data.get("total_responses", 0),
            trend_direction=data.get("trend_direction", "stable"),
            change_percentage=data.get("change_percentage", 0.0),
            key_insights=data.get("key_insights", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


# ============================================================================
# 离职风险预测模型
# ============================================================================

@dataclass
class TurnoverRiskPrediction:
    """离职风险预测"""
    employee_id: str
    risk_score: float  # 0-1, 越高风险越大
    risk_level: RiskLevel
    prediction_factors: Dict[str, float] = field(default_factory=dict)  # 各因素得分
    contributing_factors: List[str] = field(default_factory=list)  # 主要贡献因素
    protective_factors: List[str] = field(default_factory=list)  # 保护因素
    recommended_actions: List[str] = field(default_factory=list)  # 推荐行动
    model_version: str = "v1.0"
    confidence_score: float = 0.0  # 预测置信度
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prediction_date: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None  # 预测过期时间

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "prediction_factors": self.prediction_factors,
            "contributing_factors": self.contributing_factors,
            "protective_factors": self.protective_factors,
            "recommended_actions": self.recommended_actions,
            "model_version": self.model_version,
            "confidence_score": self.confidence_score,
            "prediction_date": self.prediction_date.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TurnoverRiskPrediction":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            risk_score=data["risk_score"],
            risk_level=RiskLevel(data["risk_level"]),
            prediction_factors=data.get("prediction_factors", {}),
            contributing_factors=data.get("contributing_factors", []),
            protective_factors=data.get("protective_factors", []),
            recommended_actions=data.get("recommended_actions", []),
            model_version=data.get("model_version", "v1.0"),
            confidence_score=data.get("confidence_score", 0.0),
            prediction_date=datetime.fromisoformat(data["prediction_date"]) if "prediction_date" in data else datetime.now(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


@dataclass
class EngagementScore:
    """敬业度分数"""
    employee_id: str
    overall_score: float  # 0-100
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    # 维度包括：work_engagement, team_engagement, company_engagement, growth_engagement
    behavioral_indicators: Dict[str, float] = field(default_factory=dict)
    # 行为指标：meeting_attendance, collaboration_frequency, initiative_score
    survey_score: Optional[float] = None  # 调查得分
    manager_assessment: Optional[float] = None  # 管理者评估
    peer_assessment: Optional[float] = None  # 同事评估
    trend: str = "stable"  # improving/declining/stable
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    calculated_at: datetime = field(default_factory=datetime.now)
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "behavioral_indicators": self.behavioral_indicators,
            "survey_score": self.survey_score,
            "manager_assessment": self.manager_assessment,
            "peer_assessment": self.peer_assessment,
            "trend": self.trend,
            "calculated_at": self.calculated_at.isoformat(),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EngagementScore":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            overall_score=data["overall_score"],
            dimension_scores=data.get("dimension_scores", {}),
            behavioral_indicators=data.get("behavioral_indicators", {}),
            survey_score=data.get("survey_score"),
            manager_assessment=data.get("manager_assessment"),
            peer_assessment=data.get("peer_assessment"),
            trend=data.get("trend", "stable"),
            calculated_at=datetime.fromisoformat(data["calculated_at"]) if "calculated_at" in data else datetime.now(),
            period_start=date.fromisoformat(data["period_start"]) if data.get("period_start") else None,
            period_end=date.fromisoformat(data["period_end"]) if data.get("period_end") else None,
        )


@dataclass
class RetentionIntervention:
    """留任干预措施"""
    employee_id: str
    intervention_type: InterventionType
    description: str
    priority: str = "medium"  # low/medium/high/urgent
    status: InterventionStatus = InterventionStatus.PROPOSED
    proposed_by: Optional[str] = None
    assigned_to: Optional[str] = None
    start_date: Optional[date] = None
    target_completion_date: Optional[date] = None
    actual_completion_date: Optional[date] = None
    expected_impact: Optional[str] = None
    actual_impact: Optional[str] = None
    cost_estimate: Optional[float] = None
    notes: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[date] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "intervention_type": self.intervention_type.value,
            "description": self.description,
            "priority": self.priority,
            "status": self.status.value,
            "proposed_by": self.proposed_by,
            "assigned_to": self.assigned_to,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "target_completion_date": self.target_completion_date.isoformat() if self.target_completion_date else None,
            "actual_completion_date": self.actual_completion_date.isoformat() if self.actual_completion_date else None,
            "expected_impact": self.expected_impact,
            "actual_impact": self.actual_impact,
            "cost_estimate": self.cost_estimate,
            "notes": self.notes,
            "follow_up_required": self.follow_up_required,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetentionIntervention":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            intervention_type=InterventionType(data["intervention_type"]),
            description=data["description"],
            priority=data.get("priority", "medium"),
            status=InterventionStatus(data["status"]),
            proposed_by=data.get("proposed_by"),
            assigned_to=data.get("assigned_to"),
            start_date=date.fromisoformat(data["start_date"]) if data.get("start_date") else None,
            target_completion_date=date.fromisoformat(data["target_completion_date"]) if data.get("target_completion_date") else None,
            actual_completion_date=date.fromisoformat(data["actual_completion_date"]) if data.get("actual_completion_date") else None,
            expected_impact=data.get("expected_impact"),
            actual_impact=data.get("actual_impact"),
            cost_estimate=data.get("cost_estimate"),
            notes=data.get("notes"),
            follow_up_required=data.get("follow_up_required", False),
            follow_up_date=date.fromisoformat(data["follow_up_date"]) if data.get("follow_up_date") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )


@dataclass
class RiskFactor:
    """风险因素（用于离职风险预测的明细）"""
    employee_id: str
    factor_name: str
    factor_category: str  # workload/compensation/growth/culture/management
    factor_value: float  # 因素得分
    factor_weight: float  # 因素权重
    contribution_to_risk: float  # 对风险的贡献度
    trend: str = "stable"  # improving/worsening/stable
    benchmark_value: Optional[float] = None  # 基准值（公司平均）
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assessed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "factor_name": self.factor_name,
            "factor_category": self.factor_category,
            "factor_value": self.factor_value,
            "factor_weight": self.factor_weight,
            "contribution_to_risk": self.contribution_to_risk,
            "trend": self.trend,
            "benchmark_value": self.benchmark_value,
            "assessed_at": self.assessed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskFactor":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data["employee_id"],
            factor_name=data["factor_name"],
            factor_category=data["factor_category"],
            factor_value=data["factor_value"],
            factor_weight=data["factor_weight"],
            contribution_to_risk=data["contribution_to_risk"],
            trend=data.get("trend", "stable"),
            benchmark_value=data.get("benchmark_value"),
            assessed_at=datetime.fromisoformat(data["assessed_at"]) if "assessed_at" in data else datetime.now(),
        )


# ============================================================================
# 预警系统模型
# ============================================================================

@dataclass
class WellnessAlert:
    """健康预警"""
    employee_id: Optional[str] = None  # 可能没有具体员工（如团队预警）
    team_id: Optional[str] = None
    alert_type: AlertType = None  # type: ignore
    severity: AlertSeverity = None  # type: ignore
    title: str = ""
    description: str = ""
    trigger_value: Optional[float] = None  # 触发值
    threshold_value: Optional[float] = None  # 阈值
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    related_entity_id: Optional[str] = None  # 相关实体 ID（如加班记录 ID）
    auto_generated: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    triggered_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "team_id": self.team_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "trigger_value": self.trigger_value,
            "threshold_value": self.threshold_value,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "is_resolved": self.is_resolved,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
            "related_entity_id": self.related_entity_id,
            "auto_generated": self.auto_generated,
            "triggered_at": self.triggered_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WellnessAlert":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            employee_id=data.get("employee_id"),
            team_id=data.get("team_id"),
            alert_type=AlertType(data["alert_type"]),
            severity=AlertSeverity(data["severity"]),
            title=data["title"],
            description=data["description"],
            trigger_value=data.get("trigger_value"),
            threshold_value=data.get("threshold_value"),
            is_acknowledged=data.get("is_acknowledged", False),
            acknowledged_by=data.get("acknowledged_by"),
            acknowledged_at=datetime.fromisoformat(data["acknowledged_at"]) if data.get("acknowledged_at") else None,
            is_resolved=data.get("is_resolved", False),
            resolved_by=data.get("resolved_by"),
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
            resolution_notes=data.get("resolution_notes"),
            related_entity_id=data.get("related_entity_id"),
            auto_generated=data.get("auto_generated", True),
            triggered_at=datetime.fromisoformat(data["triggered_at"]) if "triggered_at" in data else datetime.now(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


# ============================================================================
# 数据库持久化层
# ============================================================================

class WellnessDB:
    """员工福祉数据库管理类"""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（单例模式，确保内存数据库正常工作）"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_tables(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 心理健康评估表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mental_health_assessments (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                assessment_type TEXT NOT NULL,
                overall_score REAL NOT NULL,
                dimensions TEXT,
                risk_factors TEXT,
                recommendations TEXT,
                assessor_id TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 压力水平记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stress_levels (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                stress_score REAL NOT NULL,
                stress_sources TEXT,
                physical_symptoms TEXT,
                emotional_state TEXT,
                sleep_quality REAL,
                energy_level REAL,
                measurement_method TEXT,
                recorded_at TEXT NOT NULL
            )
        """)

        # 心理咨询会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counseling_sessions (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                counselor_id TEXT NOT NULL,
                counseling_type TEXT NOT NULL,
                session_date TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                follow_up_required INTEGER DEFAULT 0,
                follow_up_date TEXT,
                session_number INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 健康资源表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wellness_resources (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                category TEXT NOT NULL,
                url TEXT,
                content TEXT,
                tags TEXT,
                author TEXT,
                duration_minutes INTEGER,
                is_featured INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                helpful_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 工时记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_hour_logs (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                work_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                break_minutes INTEGER DEFAULT 0,
                work_type TEXT DEFAULT 'office',
                project_id TEXT,
                task_description TEXT,
                is_overtime INTEGER DEFAULT 0,
                approved INTEGER DEFAULT 0,
                approver_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 加班记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS overtime_records (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                overtime_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                reason TEXT NOT NULL,
                approved INTEGER DEFAULT 0,
                approver_id TEXT,
                approval_date TEXT,
                compensation_type TEXT DEFAULT 'time_off',
                compensation_hours REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 工作生活平衡指标表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_life_balance_metrics (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                balance_score REAL NOT NULL,
                work_hours_score REAL NOT NULL,
                rest_compliance_score REAL NOT NULL,
                vacation_utilization_score REAL NOT NULL,
                overtime_ratio REAL NOT NULL,
                weekend_work_days INTEGER NOT NULL,
                average_daily_hours REAL NOT NULL,
                consecutive_work_days INTEGER NOT NULL,
                last_vacation_date TEXT,
                risk_level TEXT NOT NULL,
                recommendations TEXT,
                calculated_at TEXT NOT NULL,
                period_start TEXT,
                period_end TEXT
            )
        """)

        # 福利计划表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benefit_plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                benefit_type TEXT NOT NULL,
                coverage_type TEXT NOT NULL,
                coverage_criteria TEXT,
                provider TEXT,
                coverage_amount REAL,
                employee_contribution REAL DEFAULT 0,
                employer_contribution REAL DEFAULT 1,
                effective_date TEXT,
                expiration_date TEXT,
                is_active INTEGER DEFAULT 1,
                enrollment_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 员工福利注册表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_benefit_enrollments (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                enrollment_date TEXT NOT NULL,
                status TEXT NOT NULL,
                beneficiary_name TEXT,
                beneficiary_relationship TEXT,
                coverage_start_date TEXT,
                coverage_end_date TEXT,
                monthly_premium REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 假期余额表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leave_balances (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                leave_type TEXT NOT NULL,
                total_days REAL NOT NULL,
                used_days REAL NOT NULL,
                remaining_days REAL NOT NULL,
                accrued_days REAL NOT NULL,
                carryover_days REAL DEFAULT 0,
                expiration_date TEXT,
                accrual_rate REAL,
                year INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 假期申请表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leave_requests (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                leave_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                total_days REAL NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                approver_id TEXT,
                approval_date TEXT,
                rejection_reason TEXT,
                handover_notes TEXT,
                contact_during_leave TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 补贴记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subsidy_records (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                subsidy_type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'CNY',
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                description TEXT,
                payment_date TEXT,
                approver_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 满意度调查问卷表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS satisfaction_surveys (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                survey_type TEXT NOT NULL,
                is_anonymous INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 0,
                start_date TEXT,
                end_date TEXT,
                target_audience TEXT DEFAULT 'all',
                target_criteria TEXT,
                reminder_enabled INTEGER DEFAULT 1,
                reminder_frequency_days INTEGER DEFAULT 3,
                max_reminders INTEGER DEFAULT 3,
                created_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 调查问题表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS survey_questions (
                id TEXT PRIMARY KEY,
                survey_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                orders INTEGER NOT NULL,
                is_required INTEGER DEFAULT 1,
                options TEXT,
                min_value REAL,
                max_value REAL,
                min_label TEXT,
                max_label TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 调查回复表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS survey_responses (
                id TEXT PRIMARY KEY,
                survey_id TEXT NOT NULL,
                employee_id TEXT,
                responses TEXT NOT NULL,
                overall_score REAL,
                comments TEXT,
                completion_time_seconds INTEGER,
                device_type TEXT,
                ip_hash TEXT,
                submitted_at TEXT NOT NULL
            )
        """)

        # 脉冲调查表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pulse_surveys (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                question TEXT NOT NULL,
                question_type TEXT NOT NULL,
                target_audience TEXT DEFAULT 'all',
                is_active INTEGER DEFAULT 1,
                expires_at TEXT,
                response_count INTEGER DEFAULT 0,
                average_score REAL,
                created_by TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 满意度趋势表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS satisfaction_trends (
                id TEXT PRIMARY KEY,
                period TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                overall_score REAL NOT NULL,
                dimension_scores TEXT,
                response_rate REAL DEFAULT 0,
                total_responses INTEGER DEFAULT 0,
                trend_direction TEXT DEFAULT 'stable',
                change_percentage REAL DEFAULT 0,
                key_insights TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 离职风险预测表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS turnover_risk_predictions (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                prediction_factors TEXT,
                contributing_factors TEXT,
                protective_factors TEXT,
                recommended_actions TEXT,
                model_version TEXT DEFAULT 'v1.0',
                confidence_score REAL DEFAULT 0,
                prediction_date TEXT NOT NULL,
                expires_at TEXT
            )
        """)

        # 敬业度分数表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engagement_scores (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                overall_score REAL NOT NULL,
                dimension_scores TEXT,
                behavioral_indicators TEXT,
                survey_score REAL,
                manager_assessment REAL,
                peer_assessment REAL,
                trend TEXT DEFAULT 'stable',
                calculated_at TEXT NOT NULL,
                period_start TEXT,
                period_end TEXT
            )
        """)

        # 留任干预措施表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS retention_interventions (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                intervention_type TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                status TEXT NOT NULL,
                proposed_by TEXT,
                assigned_to TEXT,
                start_date TEXT,
                target_completion_date TEXT,
                actual_completion_date TEXT,
                expected_impact TEXT,
                actual_impact TEXT,
                cost_estimate REAL,
                notes TEXT,
                follow_up_required INTEGER DEFAULT 0,
                follow_up_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 风险因素表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_factors (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                factor_name TEXT NOT NULL,
                factor_category TEXT NOT NULL,
                factor_value REAL NOT NULL,
                factor_weight REAL NOT NULL,
                contribution_to_risk REAL NOT NULL,
                trend TEXT DEFAULT 'stable',
                benchmark_value REAL,
                assessed_at TEXT NOT NULL
            )
        """)

        # 预警表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wellness_alerts (
                id TEXT PRIMARY KEY,
                employee_id TEXT,
                team_id TEXT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                trigger_value REAL,
                threshold_value REAL,
                is_acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                is_resolved INTEGER DEFAULT 0,
                resolved_by TEXT,
                resolved_at TEXT,
                resolution_notes TEXT,
                related_entity_id TEXT,
                auto_generated INTEGER DEFAULT 1,
                triggered_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mha_employee ON mental_health_assessments(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sl_employee ON stress_levels(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wl_employee ON work_hour_logs(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ot_employee ON overtime_records(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lb_employee ON leave_balances(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lr_employee ON leave_requests(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sr_survey ON survey_responses(survey_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trp_employee ON turnover_risk_predictions(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_es_employee ON engagement_scores(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ri_employee ON retention_interventions(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_employee ON wellness_alerts(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_type ON wellness_alerts(alert_type)")

        conn.commit()

    # 通用 CRUD 方法
    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """插入记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 将字典和列表转换为 JSON 字符串
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                data[key] = json.dumps(value)
            elif isinstance(value, Enum):
                data[key] = value.value

        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

        cursor.execute(sql, data)
        conn.commit()
        return data.get("id")

    def update(self, table: str, id: str, data: Dict[str, Any]) -> bool:
        """更新记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 将字典和列表转换为 JSON 字符串
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                data[key] = json.dumps(value)
            elif isinstance(value, Enum):
                data[key] = value.value

        set_clauses = [f"{col} = :{col}" for col in data.keys()]
        sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = :id"

        data["id"] = id
        cursor.execute(sql, data)
        conn.commit()
        affected = cursor.rowcount
        return affected > 0

    def get(self, table: str, id: str) -> Optional[Dict[str, Any]]:
        """获取单条记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (id,))
        row = cursor.fetchone()

        return dict(row) if row else None

    def list(self, table: str, filters: Optional[Dict[str, Any]] = None,
             order_by: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """列出记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        sql = f"SELECT * FROM {table}"
        params = []

        if filters:
            where_clauses = []
            for key, value in filters.items():
                where_clauses.append(f"{key} = ?")
                params.append(value)
            sql += f" WHERE {' AND '.join(where_clauses)}"

        if order_by:
            sql += f" ORDER BY {order_by}"

        if limit:
            sql += f" LIMIT {limit}"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def delete(self, table: str, id: str) -> bool:
        """删除记录"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (id,))
        conn.commit()
        affected = cursor.rowcount
        return affected > 0


# ============================================================================
# 内存模型注册表
# ============================================================================

# 用于将模型类注册到数据库
MODEL_REGISTRY = {
    "mental_health_assessments": MentalHealthAssessment,
    "stress_levels": StressLevel,
    "counseling_sessions": CounselingSession,
    "wellness_resources": WellnessResource,
    "work_hour_logs": WorkHourLog,
    "overtime_records": OvertimeRecord,
    "work_life_balance_metrics": WorkLifeBalanceMetrics,
    "benefit_plans": BenefitPlan,
    "employee_benefit_enrollments": EmployeeBenefitEnrollment,
    "leave_balances": LeaveBalance,
    "leave_requests": LeaveRequest,
    "subsidy_records": SubsidyRecord,
    "satisfaction_surveys": SatisfactionSurvey,
    "survey_questions": SurveyQuestion,
    "survey_responses": SurveyResponse,
    "pulse_surveys": PulseSurvey,
    "satisfaction_trends": SatisfactionTrend,
    "turnover_risk_predictions": TurnoverRiskPrediction,
    "engagement_scores": EngagementScore,
    "retention_interventions": RetentionIntervention,
    "risk_factors": RiskFactor,
    "wellness_alerts": WellnessAlert,
}
