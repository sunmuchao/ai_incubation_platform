"""
P15 员工福祉管理 - API 路由层
版本：v15.0.0
主题：员工福祉管理 (Employee Wellness Management)
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import sqlite3

from models.p15_models import (
    RiskLevel, AssessmentType, SurveyType, QuestionType, LeaveType, LeaveStatus,
    BenefitType, InterventionType, InterventionStatus, AlertType, AlertSeverity,
    CounselingType, CounselingStatus,
    MentalHealthAssessment, StressLevel, CounselingSession, WellnessResource,
    WorkHourLog, OvertimeRecord, WorkLifeBalanceMetrics,
    BenefitPlan, EmployeeBenefitEnrollment, LeaveBalance, LeaveRequest, SubsidyRecord,
    SatisfactionSurvey, SurveyQuestion, SurveyResponse, PulseSurvey, SatisfactionTrend,
    TurnoverRiskPrediction, EngagementScore, RetentionIntervention, RiskFactor,
    WellnessAlert,
    WellnessDB,
)
from services.p15_wellness_services import (
    WellnessService, MentalHealthService, WorkLifeBalanceService,
    BenefitsService, SurveyService, TurnoverPredictionService, EngagementService,
)


# ============================================================================
# Pydantic 请求/响应模型
# ============================================================================

class MentalHealthAssessmentCreate(BaseModel):
    employee_id: str
    assessment_type: str
    overall_score: float = Field(ge=0, le=100)
    dimensions: Dict[str, float] = {}
    risk_factors: List[str] = []
    recommendations: List[str] = []
    assessor_id: Optional[str] = None
    notes: Optional[str] = None


class StressLevelCreate(BaseModel):
    employee_id: str
    stress_score: float = Field(ge=0, le=100)
    stress_sources: List[str] = []
    emotional_state: str
    physical_symptoms: List[str] = []
    sleep_quality: Optional[float] = Field(None, ge=0, le=100)
    energy_level: Optional[float] = Field(None, ge=0, le=100)
    measurement_method: Optional[str] = None


class CounselingSessionCreate(BaseModel):
    employee_id: str
    counselor_id: str
    counseling_type: str
    session_date: datetime
    duration_minutes: int = 60


class CounselingSessionComplete(BaseModel):
    notes: str
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None


class WellnessResourceCreate(BaseModel):
    title: str
    description: str
    resource_type: str
    category: str
    url: Optional[str] = None
    content: Optional[str] = None
    tags: List[str] = []


class WorkHourLogCreate(BaseModel):
    employee_id: str
    work_date: date
    start_time: datetime
    end_time: datetime
    break_minutes: int = 0
    work_type: str = "office"
    project_id: Optional[str] = None
    task_description: Optional[str] = None


class OvertimeRecordCreate(BaseModel):
    employee_id: str
    overtime_date: date
    start_time: datetime
    end_time: datetime
    reason: str
    compensation_type: str = "time_off"


class OvertimeApprove(BaseModel):
    approver_id: str
    compensation_hours: Optional[float] = None


class BenefitPlanCreate(BaseModel):
    name: str
    description: str
    benefit_type: str
    coverage_type: str = "all"
    coverage_criteria: Dict[str, Any] = {}
    provider: Optional[str] = None
    coverage_amount: Optional[float] = None
    employee_contribution: float = 0.0
    employer_contribution: float = 1.0
    effective_date: Optional[date] = None


class EmployeeBenefitEnroll(BaseModel):
    employee_id: str
    plan_id: str
    beneficiary_name: Optional[str] = None
    beneficiary_relationship: Optional[str] = None
    coverage_start_date: Optional[date] = None


class LeaveRequestCreate(BaseModel):
    employee_id: str
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    handover_notes: Optional[str] = None
    contact_during_leave: Optional[str] = None


class LeaveApprove(BaseModel):
    approver_id: str


class LeaveReject(BaseModel):
    approver_id: str
    rejection_reason: str


class SubsidyRecordCreate(BaseModel):
    employee_id: str
    subsidy_type: str
    amount: float
    period_start: date
    period_end: date
    description: Optional[str] = None


class SatisfactionSurveyCreate(BaseModel):
    title: str
    description: str
    survey_type: str
    is_anonymous: bool = True
    target_audience: str = "all"
    target_criteria: Dict[str, Any] = {}
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SurveyQuestionCreate(BaseModel):
    survey_id: str
    question_text: str
    question_type: str
    order: int
    is_required: bool = True
    options: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_label: Optional[str] = None
    max_label: Optional[str] = None


class SurveyResponseCreate(BaseModel):
    survey_id: str
    employee_id: Optional[str] = None
    responses: Dict[str, Any] = {}
    overall_score: Optional[float] = None
    comments: Optional[str] = None
    completion_time_seconds: Optional[int] = None
    device_type: Optional[str] = None


class PulseSurveyCreate(BaseModel):
    title: str
    question: str
    question_type: str = "likert_scale"
    target_audience: str = "all"
    expires_hours: int = 24


class PulseResponseCreate(BaseModel):
    survey_id: str
    score: float
    employee_id: Optional[str] = None
    comments: Optional[str] = None


class TurnoverPredictionCreate(BaseModel):
    employee_id: str
    work_hour_trend: float = 0.5
    satisfaction_score: float = 0.5
    performance_trend: float = 0.5
    overtime_frequency: float = 0.5
    leave_utilization: float = 0.5
    engagement_score: float = 0.5
    career_growth: float = 0.5


class RetentionInterventionCreate(BaseModel):
    employee_id: str
    intervention_type: str
    description: str
    priority: str = "medium"
    proposed_by: Optional[str] = None
    assigned_to: Optional[str] = None
    expected_impact: Optional[str] = None
    cost_estimate: Optional[float] = None


class EngagementScoreCreate(BaseModel):
    employee_id: str
    dimension_scores: Dict[str, float] = {}
    behavioral_indicators: Dict[str, float] = {}
    survey_score: Optional[float] = None
    manager_assessment: Optional[float] = None
    peer_assessment: Optional[float] = None


# ============================================================================
# API 路由器
# ============================================================================

router = APIRouter(prefix="/api/wellness", tags=["Wellness"])

# 全局服务实例（实际使用时应该通过依赖注入）
_wellness_service: Optional[WellnessService] = None


def get_wellness_service() -> WellnessService:
    global _wellness_service
    if _wellness_service is None:
        _wellness_service = WellnessService(":memory:")
    return _wellness_service


# ============================================================================
# 心理健康支持 API
# ============================================================================

@router.post("/mental-health/assessments", response_model=Dict[str, Any])
def create_mental_health_assessment(assessment: MentalHealthAssessmentCreate):
    """创建心理健康评估"""
    service = get_wellness_service().mental_health

    try:
        assessment_type = AssessmentType(assessment.assessment_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid assessment type: {assessment.assessment_type}")

    result = service.create_assessment(
        employee_id=assessment.employee_id,
        assessment_type=assessment_type,
        overall_score=assessment.overall_score,
        dimensions=assessment.dimensions,
        risk_factors=assessment.risk_factors,
        recommendations=assessment.recommendations,
        assessor_id=assessment.assessor_id,
        notes=assessment.notes,
    )
    return result.to_dict()


@router.get("/mental-health/assessments/{assessment_id}", response_model=Dict[str, Any])
def get_mental_health_assessment(assessment_id: str):
    """获取心理健康评估详情"""
    service = get_wellness_service().mental_health
    result = service.get_assessment(assessment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return result.to_dict()


@router.get("/mental-health/employees/{employee_id}/assessments", response_model=List[Dict[str, Any]])
def list_mental_health_assessments(employee_id: str, limit: int = Query(100, le=1000)):
    """列出员工的心理健康评估记录"""
    service = get_wellness_service().mental_health
    results = service.list_assessments(employee_id=employee_id, limit=limit)
    return [r.to_dict() for r in results]


@router.post("/mental-health/stress-levels", response_model=Dict[str, Any])
def record_stress_level(stress: StressLevelCreate):
    """记录压力水平"""
    service = get_wellness_service().mental_health
    result = service.record_stress_level(
        employee_id=stress.employee_id,
        stress_score=stress.stress_score,
        stress_sources=stress.stress_sources,
        emotional_state=stress.emotional_state,
        physical_symptoms=stress.physical_symptoms,
        sleep_quality=stress.sleep_quality,
        energy_level=stress.energy_level,
        measurement_method=stress.measurement_method,
    )
    return result.to_dict()


@router.get("/mental-health/employees/{employee_id}/stress-history", response_model=List[Dict[str, Any]])
def get_stress_history(employee_id: str, days: int = Query(30, ge=1, le=365)):
    """获取员工压力历史记录"""
    service = get_wellness_service().mental_health
    results = service.get_stress_history(employee_id, days=days)
    return [r.to_dict() for r in results]


@router.post("/mental-health/counseling/sessions", response_model=Dict[str, Any])
def schedule_counseling_session(session: CounselingSessionCreate):
    """预约心理咨询"""
    service = get_wellness_service().mental_health

    try:
        counseling_type = CounselingType(session.counseling_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid counseling type: {session.counseling_type}")

    result = service.schedule_counseling(
        employee_id=session.employee_id,
        counselor_id=session.counselor_id,
        counseling_type=counseling_type,
        session_date=session.session_date,
        duration_minutes=session.duration_minutes,
    )
    return result.to_dict()


@router.get("/mental-health/counseling/sessions/{session_id}", response_model=Dict[str, Any])
def get_counseling_session(session_id: str):
    """获取心理咨询会话详情"""
    service = get_wellness_service().mental_health
    result = service.get_counseling_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result.to_dict()


@router.post("/mental-health/counseling/sessions/{session_id}/complete", response_model=Dict[str, Any])
def complete_counseling_session(session_id: str, data: CounselingSessionComplete):
    """完成心理咨询会话"""
    service = get_wellness_service().mental_health
    result = service.complete_counseling_session(
        session_id=session_id,
        notes=data.notes,
        follow_up_required=data.follow_up_required,
        follow_up_date=data.follow_up_date,
    )
    return result.to_dict()


@router.get("/mental-health/employees/{employee_id}/counseling-sessions", response_model=List[Dict[str, Any]])
def list_counseling_sessions(employee_id: str):
    """列出员工的心理咨询会话"""
    service = get_wellness_service().mental_health
    results = service.list_counseling_sessions(employee_id)
    return [r.to_dict() for r in results]


@router.post("/mental-health/resources", response_model=Dict[str, Any])
def create_wellness_resource(resource: WellnessResourceCreate):
    """添加健康资源"""
    service = get_wellness_service().mental_health
    result = service.add_wellness_resource(
        title=resource.title,
        description=resource.description,
        resource_type=resource.resource_type,
        category=resource.category,
        url=resource.url,
        content=resource.content,
        tags=resource.tags,
    )
    return result.to_dict()


@router.get("/mental-health/resources", response_model=List[Dict[str, Any]])
def list_wellness_resources(
    category: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    """列出健康资源"""
    service = get_wellness_service().mental_health
    results = service.list_wellness_resources(
        category=category,
        is_featured=is_featured,
        search=search,
    )
    return [r.to_dict() for r in results]


@router.get("/mental-health/statistics/stress", response_model=Dict[str, Any])
def get_stress_statistics():
    """获取压力统计数据"""
    service = get_wellness_service().mental_health
    return service.get_stress_statistics()


# ============================================================================
# 工作生活平衡 API
# ============================================================================

@router.post("/work-life/work-hours", response_model=Dict[str, Any])
def log_work_hours(work_log: WorkHourLogCreate):
    """记录工时"""
    service = get_wellness_service().work_life_balance
    result = service.log_work_hours(
        employee_id=work_log.employee_id,
        work_date=work_log.work_date,
        start_time=work_log.start_time,
        end_time=work_log.end_time,
        break_minutes=work_log.break_minutes,
        work_type=work_log.work_type,
        project_id=work_log.project_id,
        task_description=work_log.task_description,
    )
    return result.to_dict()


@router.get("/work-life/employees/{employee_id}/work-hours", response_model=List[Dict[str, Any]])
def list_work_hours(employee_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """列出员工的工时记录"""
    service = get_wellness_service().work_life_balance
    conn = service.db._get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM work_hour_logs WHERE employee_id = ?"
    params = [employee_id]

    if start_date:
        query += " AND work_date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND work_date <= ?"
        params.append(end_date.isoformat())

    query += " ORDER BY work_date DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [WorkHourLog.from_dict(dict(row)).to_dict() for row in rows]


@router.post("/work-life/overtime", response_model=Dict[str, Any])
def record_overtime(overtime: OvertimeRecordCreate):
    """记录加班"""
    service = get_wellness_service().work_life_balance
    result = service.record_overtime(
        employee_id=overtime.employee_id,
        overtime_date=overtime.overtime_date,
        start_time=overtime.start_time,
        end_time=overtime.end_time,
        reason=overtime.reason,
        compensation_type=overtime.compensation_type,
    )
    return result.to_dict()


@router.post("/work-life/overtime/{overtime_id}/approve", response_model=Dict[str, Any])
def approve_overtime(overtime_id: str, data: OvertimeApprove):
    """审批加班"""
    service = get_wellness_service().work_life_balance
    try:
        result = service.approve_overtime(
            overtime_id=overtime_id,
            approver_id=data.approver_id,
            compensation_hours=data.compensation_hours,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/work-life/employees/{employee_id}/overtime", response_model=List[Dict[str, Any]])
def list_overtime(employee_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """列出员工的加班记录"""
    service = get_wellness_service().work_life_balance
    results = service.list_overtime_records(employee_id, start_date, end_date)
    return [r.to_dict() for r in results]


@router.post("/work-life/balance/calculate", response_model=Dict[str, Any])
def calculate_balance_score(employee_id: str, period_start: Optional[date] = None, period_end: Optional[date] = None):
    """计算工作生活平衡分数"""
    service = get_wellness_service().work_life_balance
    result = service.calculate_balance_score(employee_id, period_start, period_end)
    return result.to_dict()


@router.get("/work-life/employees/{employee_id}/balance-history", response_model=List[Dict[str, Any]])
def get_balance_history(employee_id: str, months: int = Query(6, ge=1, le=24)):
    """获取工作生活平衡历史"""
    service = get_wellness_service().work_life_balance
    results = service.get_balance_history(employee_id, months=months)
    return [r.to_dict() for r in results]


# ============================================================================
# 福利管理 API
# ============================================================================

@router.post("/benefits/plans", response_model=Dict[str, Any])
def create_benefit_plan(plan: BenefitPlanCreate):
    """创建福利计划"""
    service = get_wellness_service().benefits

    try:
        benefit_type = BenefitType(plan.benefit_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid benefit type: {plan.benefit_type}")

    result = service.create_benefit_plan(
        name=plan.name,
        description=plan.description,
        benefit_type=benefit_type,
        coverage_type=plan.coverage_type,
        coverage_criteria=plan.coverage_criteria,
        provider=plan.provider,
        coverage_amount=plan.coverage_amount,
        employee_contribution=plan.employee_contribution,
        employer_contribution=plan.employer_contribution,
        effective_date=plan.effective_date,
    )
    return result.to_dict()


@router.get("/benefits/plans", response_model=List[Dict[str, Any]])
def list_benefit_plans(benefit_type: Optional[str] = None, is_active: bool = True):
    """列出福利计划"""
    service = get_wellness_service().benefits

    bt = None
    if benefit_type:
        try:
            bt = BenefitType(benefit_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid benefit type: {benefit_type}")

    results = service.list_benefit_plans(benefit_type=bt, is_active=is_active)
    return [r.to_dict() for r in results]


@router.post("/benefits/enroll", response_model=Dict[str, Any])
def enroll_employee_benefit(enrollment: EmployeeBenefitEnroll):
    """员工注册福利计划"""
    service = get_wellness_service().benefits
    result = service.enroll_employee(
        employee_id=enrollment.employee_id,
        plan_id=enrollment.plan_id,
        beneficiary_name=enrollment.beneficiary_name,
        beneficiary_relationship=enrollment.beneficiary_relationship,
        coverage_start_date=enrollment.coverage_start_date,
    )
    return result.to_dict()


@router.get("/benefits/employees/{employee_id}/benefits", response_model=List[Dict[str, Any]])
def get_employee_benefits(employee_id: str):
    """获取员工的福利"""
    service = get_wellness_service().benefits
    results = service.get_employee_benefits(employee_id)
    return [r.to_dict() for r in results]


@router.get("/benefits/employees/{employee_id}/leave-balance", response_model=List[Dict[str, Any]])
def get_employee_leave_balance(employee_id: str, year: Optional[int] = None):
    """获取员工假期余额"""
    service = get_wellness_service().benefits
    results = service.get_all_leave_balances(employee_id, year=year)
    return [r.to_dict() for r in results]


@router.post("/benefits/leave-requests", response_model=Dict[str, Any])
def create_leave_request(leave: LeaveRequestCreate):
    """申请假期"""
    service = get_wellness_service().benefits

    try:
        leave_type = LeaveType(leave.leave_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid leave type: {leave.leave_type}")

    try:
        result = service.request_leave(
            employee_id=leave.employee_id,
            leave_type=leave_type,
            start_date=leave.start_date,
            end_date=leave.end_date,
            reason=leave.reason,
            handover_notes=leave.handover_notes,
            contact_during_leave=leave.contact_during_leave,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/benefits/leave-requests/{leave_id}/approve", response_model=Dict[str, Any])
def approve_leave_request(leave_id: str, data: LeaveApprove):
    """审批假期"""
    service = get_wellness_service().benefits
    try:
        result = service.approve_leave(leave_id=leave_id, approver_id=data.approver_id)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/benefits/leave-requests/{leave_id}/reject", response_model=Dict[str, Any])
def reject_leave_request(leave_id: str, data: LeaveReject):
    """拒绝假期申请"""
    service = get_wellness_service().benefits
    try:
        result = service.reject_leave(
            leave_id=leave_id,
            approver_id=data.approver_id,
            rejection_reason=data.rejection_reason,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/benefits/leave-requests", response_model=List[Dict[str, Any]])
def list_leave_requests(employee_id: Optional[str] = None, status: Optional[str] = None):
    """列出假期申请"""
    service = get_wellness_service().benefits

    st = None
    if status:
        try:
            st = LeaveStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid leave status: {status}")

    results = service.list_leave_requests(employee_id=employee_id, status=st)
    return [r.to_dict() for r in results]


@router.post("/benefits/subsidies", response_model=Dict[str, Any])
def create_subsidy_record(subsidy: SubsidyRecordCreate):
    """记录补贴"""
    service = get_wellness_service().benefits
    result = service.record_subsidy(
        employee_id=subsidy.employee_id,
        subsidy_type=subsidy.subsidy_type,
        amount=subsidy.amount,
        period_start=subsidy.period_start,
        period_end=subsidy.period_end,
        description=subsidy.description,
    )
    return result.to_dict()


@router.get("/benefits/employees/{employee_id}/subsidies", response_model=List[Dict[str, Any]])
def list_employee_subsidies(employee_id: str, period_start: Optional[date] = None, period_end: Optional[date] = None):
    """列出员工的补贴记录"""
    service = get_wellness_service().benefits
    results = service.list_subsidies(employee_id, period_start, period_end)
    return [r.to_dict() for r in results]


# ============================================================================
# 满意度调查 API
# ============================================================================

@router.post("/surveys", response_model=Dict[str, Any])
def create_satisfaction_survey(survey: SatisfactionSurveyCreate):
    """创建满意度调查问卷"""
    service = get_wellness_service().survey

    try:
        survey_type = SurveyType(survey.survey_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid survey type: {survey.survey_type}")

    result = service.create_survey(
        title=survey.title,
        description=survey.description,
        survey_type=survey_type,
        is_anonymous=survey.is_anonymous,
        target_audience=survey.target_audience,
        target_criteria=survey.target_criteria,
        start_date=survey.start_date,
        end_date=survey.end_date,
    )
    return result.to_dict()


@router.post("/surveys/questions", response_model=Dict[str, Any])
def add_survey_question(question: SurveyQuestionCreate):
    """添加调查问题"""
    service = get_wellness_service().survey

    try:
        question_type = QuestionType(question.question_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid question type: {question.question_type}")

    result = service.add_question(
        survey_id=question.survey_id,
        question_text=question.question_text,
        question_type=question_type,
        order=question.order,
        is_required=question.is_required,
        options=question.options,
        min_value=question.min_value,
        max_value=question.max_value,
        min_label=question.min_label,
        max_label=question.max_label,
    )
    return result.to_dict()


@router.get("/surveys/{survey_id}", response_model=Dict[str, Any])
def get_survey(survey_id: str):
    """获取问卷详情"""
    service = get_wellness_service().survey
    result = service.get_survey(survey_id)
    if not result:
        raise HTTPException(status_code=404, detail="Survey not found")
    return result.to_dict()


@router.get("/surveys/{survey_id}/questions", response_model=List[Dict[str, Any]])
def get_survey_questions(survey_id: str):
    """获取问卷问题列表"""
    service = get_wellness_service().survey
    results = service.get_survey_questions(survey_id)
    return [r.to_dict() for r in results]


@router.get("/surveys", response_model=List[Dict[str, Any]])
def list_surveys(survey_type: Optional[str] = None, is_active: Optional[bool] = None):
    """列出问卷"""
    service = get_wellness_service().survey

    st = None
    if survey_type:
        try:
            st = SurveyType(survey_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid survey type: {survey_type}")

    results = service.list_surveys(survey_type=st, is_active=is_active)
    return [r.to_dict() for r in results]


@router.post("/surveys/responses", response_model=Dict[str, Any])
def submit_survey_response(response: SurveyResponseCreate):
    """提交问卷回复"""
    service = get_wellness_service().survey
    result = service.submit_response(
        survey_id=response.survey_id,
        employee_id=response.employee_id,
        responses=response.responses,
        overall_score=response.overall_score,
        comments=response.comments,
        completion_time_seconds=response.completion_time_seconds,
        device_type=response.device_type,
    )
    return result.to_dict()


@router.post("/pulse-surveys", response_model=Dict[str, Any])
def create_pulse_survey(pulse: PulseSurveyCreate):
    """创建脉冲调查"""
    service = get_wellness_service().survey

    try:
        question_type = QuestionType(pulse.question_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid question type: {pulse.question_type}")

    result = service.create_pulse_survey(
        title=pulse.title,
        question=pulse.question,
        question_type=question_type,
        target_audience=pulse.target_audience,
        expires_hours=pulse.expires_hours,
    )
    return result.to_dict()


@router.get("/pulse-surveys", response_model=List[Dict[str, Any]])
def list_pulse_surveys(is_active: bool = True):
    """列出脉冲调查"""
    service = get_wellness_service().survey
    results = service.get_pulse_surveys(is_active=is_active)
    return [r.to_dict() for r in results]


@router.post("/pulse-surveys/responses", response_model=Dict[str, Any])
def submit_pulse_response(response: PulseResponseCreate):
    """提交脉冲调查回复"""
    service = get_wellness_service().survey
    result = service.submit_pulse_response(
        survey_id=response.survey_id,
        score=response.score,
        employee_id=response.employee_id,
        comments=response.comments,
    )
    return result.to_dict()


@router.get("/surveys/{survey_id}/statistics", response_model=Dict[str, Any])
def get_survey_statistics(survey_id: str):
    """获取问卷统计"""
    service = get_wellness_service().survey
    return service.get_survey_statistics(survey_id)


@router.get("/satisfaction/trends", response_model=List[Dict[str, Any]])
def get_satisfaction_trends(period: str = "monthly", months: int = 6):
    """获取满意度趋势"""
    service = get_wellness_service().survey
    results = service.calculate_satisfaction_trend(period, months)
    return [r.to_dict() for r in results]


# ============================================================================
# 离职风险预测 API
# ============================================================================

@router.post("/turnover/predict", response_model=Dict[str, Any])
def predict_turnover_risk(prediction: TurnoverPredictionCreate):
    """预测离职风险"""
    service = get_wellness_service().turnover_prediction
    result = service.predict_turnover_risk(
        employee_id=prediction.employee_id,
        work_hour_trend=prediction.work_hour_trend,
        satisfaction_score=prediction.satisfaction_score,
        performance_trend=prediction.performance_trend,
        overtime_frequency=prediction.overtime_frequency,
        leave_utilization=prediction.leave_utilization,
        engagement_score=prediction.engagement_score,
        career_growth=prediction.career_growth,
    )
    return result.to_dict()


@router.get("/turnover/employees/{employee_id}/risk", response_model=Dict[str, Any])
def get_employee_turnover_risk(employee_id: str):
    """获取员工离职风险预测"""
    service = get_wellness_service().turnover_prediction
    result = service.get_prediction(employee_id)
    if not result:
        raise HTTPException(status_code=404, detail="No prediction found for this employee")
    return result.to_dict()


@router.get("/turnover/high-risk", response_model=List[Dict[str, Any]])
def list_high_risk_employees(min_risk_level: str = "medium"):
    """列出高风险员工"""
    service = get_wellness_service().turnover_prediction

    try:
        risk_level = RiskLevel(min_risk_level)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid risk level: {min_risk_level}")

    results = service.list_high_risk_employees(risk_level)
    return results


@router.post("/turnover/interventions", response_model=Dict[str, Any])
def create_retention_intervention(intervention: RetentionInterventionCreate):
    """创建留任干预措施"""
    service = get_wellness_service().turnover_prediction

    try:
        intervention_type = InterventionType(intervention.intervention_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid intervention type: {intervention.intervention_type}")

    result = service.create_intervention(
        employee_id=intervention.employee_id,
        intervention_type=intervention_type,
        description=intervention.description,
        priority=intervention.priority,
        proposed_by=intervention.proposed_by,
        assigned_to=intervention.assigned_to,
        expected_impact=intervention.expected_impact,
        cost_estimate=intervention.cost_estimate,
    )
    return result.to_dict()


@router.get("/turnover/interventions", response_model=List[Dict[str, Any]])
def list_interventions(employee_id: Optional[str] = None, status: Optional[str] = None):
    """列出干预措施"""
    service = get_wellness_service().turnover_prediction

    st = None
    if status:
        try:
            st = InterventionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid intervention status: {status}")

    results = service.list_interventions(employee_id=employee_id, status=st)
    return [r.to_dict() for r in results]


@router.post("/turnover/interventions/{intervention_id}/complete", response_model=Dict[str, Any])
def complete_intervention(intervention_id: str, actual_impact: Optional[str] = None):
    """完成干预措施"""
    service = get_wellness_service().turnover_prediction
    try:
        result = service.complete_intervention(intervention_id, actual_impact)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# 敬业度 API
# ============================================================================

@router.post("/engagement/scores", response_model=Dict[str, Any])
def calculate_engagement_score(score: EngagementScoreCreate):
    """计算敬业度分数"""
    service = get_wellness_service().engagement
    result = service.calculate_engagement_score(
        employee_id=score.employee_id,
        dimension_scores=score.dimension_scores,
        behavioral_indicators=score.behavioral_indicators,
        survey_score=score.survey_score,
        manager_assessment=score.manager_assessment,
        peer_assessment=score.peer_assessment,
    )
    return result.to_dict()


@router.get("/engagement/employees/{employee_id}/score", response_model=Dict[str, Any])
def get_employee_engagement_score(employee_id: str):
    """获取员工敬业度分数"""
    service = get_wellness_service().engagement
    result = service.get_engagement_score(employee_id)
    if not result:
        raise HTTPException(status_code=404, detail="No engagement score found")
    return result.to_dict()


@router.get("/engagement/employees/{employee_id}/history", response_model=List[Dict[str, Any]])
def get_engagement_history(employee_id: str, months: int = Query(6, ge=1, le=24)):
    """获取敬业度历史"""
    service = get_wellness_service().engagement
    results = service.get_engagement_history(employee_id, months=months)
    return [r.to_dict() for r in results]


# ============================================================================
# 仪表盘 API
# ============================================================================

@router.get("/dashboard/{employee_id}", response_model=Dict[str, Any])
def get_wellness_dashboard(employee_id: str):
    """获取员工福祉仪表盘"""
    service = get_wellness_service()
    return service.get_wellness_dashboard(employee_id)


@router.get("/alerts", response_model=List[Dict[str, Any]])
def list_alerts(employee_id: Optional[str] = None, alert_type: Optional[str] = None, is_resolved: bool = False):
    """列出预警"""
    service = get_wellness_service()

    filters = {"is_resolved": 1 if is_resolved else 0}
    if employee_id:
        filters["employee_id"] = employee_id
    if alert_type:
        filters["alert_type"] = alert_type

    rows = service.db.list("wellness_alerts", filters, order_by="triggered_at DESC", limit=100)
    return rows


@router.post("/alerts/{alert_id}/acknowledge", response_model=Dict[str, Any])
def acknowledge_alert(alert_id: str, acknowledged_by: str):
    """确认预警"""
    service = get_wellness_service()
    alert = service.db.get("wellness_alerts", alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert["is_acknowledged"] = 1
    alert["acknowledged_by"] = acknowledged_by
    alert["acknowledged_at"] = datetime.now().isoformat()
    service.db.update("wellness_alerts", alert_id, alert)
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=Dict[str, Any])
def resolve_alert(alert_id: str, resolved_by: str, resolution_notes: Optional[str] = None):
    """解决预警"""
    service = get_wellness_service()
    alert = service.db.get("wellness_alerts", alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert["is_resolved"] = 1
    alert["resolved_by"] = resolved_by
    alert["resolved_at"] = datetime.now().isoformat()
    alert["resolution_notes"] = resolution_notes
    service.db.update("wellness_alerts", alert_id, alert)
    return alert
