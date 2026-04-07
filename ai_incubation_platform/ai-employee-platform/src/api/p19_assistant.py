"""
P19 AI 助手增强 - API 路由层
版本：v19.0.0
主题：AI 助手增强 (智能工作助手、日程管理、会议摘要、工作简报)
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from models.p19_assistant_models import (
    TaskPriority, TaskStatus, RecommendationType, MeetingType,
    MeetingStatus, ReportType, ReportStatus
)
from services.p19_assistant_service import (
    WorkAssistantService, SmartScheduleService, MeetingSummaryService,
    AutoReportService, AssistantService
)


router = APIRouter(prefix="/api/assistant", tags=["P19 AI 助手增强"])

# 初始化服务
assistant_service = AssistantService()


# ==================== Pydantic 模型 ====================

class AssistantCreateRequest(BaseModel):
    assistant_type: str
    name: str = "工作助手"
    description: Optional[str] = None
    preferences: Dict[str, Any] = {}


class TaskRecommendationRequest(BaseModel):
    recommendation_type: str
    title: str
    task_id: Optional[int] = None
    employee_id: Optional[int] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = {}


class ScheduleCreateRequest(BaseModel):
    title: str
    start_time: str
    end_time: str
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: List[int] = []
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    recurrence_end: Optional[str] = None
    priority: str = "medium"
    timezone: str = "UTC"


class ScheduleUpdateRequest(BaseModel):
    title: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[int]] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = None
    recurrence_end: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    timezone: Optional[str] = None


class MeetingCreateRequest(BaseModel):
    title: str
    meeting_type: str
    start_time: str
    end_time: str
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: List[int] = []
    agenda: Optional[str] = None


class MeetingUpdateRequest(BaseModel):
    title: Optional[str] = None
    meeting_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[int]] = None
    status: Optional[str] = None
    agenda: Optional[str] = None


class ActionItemCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    due_date: Optional[str] = None
    priority: str = "medium"


class ReportCreateRequest(BaseModel):
    report_type: str
    period_start: str
    period_end: str
    title: Optional[str] = None
    content: Optional[str] = None
    tasks_completed: List[int] = []
    time_spent_hours: float = 0.0
    achievements: List[str] = []
    blockers: List[str] = []
    next_steps: List[str] = []


class ReportTemplateCreateRequest(BaseModel):
    name: str
    report_type: str
    template_content: str
    description: Optional[str] = None
    sections: List[str] = []
    is_default: bool = False


class AutoReportRequest(BaseModel):
    report_type: str
    period_start: str
    period_end: str
    template_id: Optional[int] = None


# ==================== AI 助手管理 ====================

@router.post("/assistants")
async def create_assistant(user_id: int = Query(...), request: AssistantCreateRequest = Body(...)):
    """创建 AI 助手"""
    try:
        assistant = assistant_service.work_assistant.create_assistant(
            user_id=user_id,
            assistant_type=request.assistant_type,
            name=request.name,
            description=request.description,
            preferences=request.preferences
        )
        return {"success": True, "data": assistant.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assistants")
async def get_user_assistants(user_id: int = Query(...)):
    """获取用户的助手列表"""
    assistants = assistant_service.work_assistant.get_user_assistants(user_id)
    return {"success": True, "data": [a.to_dict() for a in assistants]}


# ==================== 任务推荐 ====================

@router.post("/task-recommendations")
async def create_task_recommendation(user_id: int = Query(...), request: TaskRecommendationRequest = Body(...)):
    """创建任务推荐"""
    try:
        recommendation = assistant_service.work_assistant.create_task_recommendation(
            user_id=user_id,
            recommendation_type=request.recommendation_type,
            title=request.title,
            task_id=request.task_id,
            employee_id=request.employee_id,
            description=request.description,
            reason=request.reason,
            confidence_score=request.confidence_score,
            metadata=request.metadata
        )
        return {"success": True, "data": recommendation.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task-recommendations")
async def get_task_recommendations(user_id: int = Query(...), limit: int = Query(50)):
    """获取任务推荐列表"""
    recommendations = assistant_service.work_assistant.get_recommendations(user_id, limit)
    return {"success": True, "data": [r.to_dict() for r in recommendations]}


@router.post("/task-recommendations/{recommendation_id}/accept")
async def accept_task_recommendation(recommendation_id: int):
    """接受任务推荐"""
    success = assistant_service.work_assistant.accept_recommendation(recommendation_id)
    return {"success": success}


@router.post("/task-recommendations/generate-priority")
async def generate_priority_recommendations(user_id: int = Query(...), tasks: List[Dict] = Body(...)):
    """生成任务优先级推荐"""
    recommendations = assistant_service.work_assistant.generate_task_priority_recommendations(user_id, tasks)
    return {"success": True, "data": [r.to_dict() for r in recommendations]}


@router.post("/task-recommendations/generate-employee")
async def generate_employee_recommendations(user_id: int = Query(...),
                                             task_description: str = Body(..., embed=True),
                                             budget: float = Body(None)):
    """生成 AI 员工推荐"""
    recommendations = assistant_service.work_assistant.generate_ai_employee_recommendations(
        user_id, task_description, budget
    )
    return {"success": True, "data": [r.to_dict() for r in recommendations]}


# ==================== 日程管理 ====================

@router.post("/schedules")
async def create_schedule(user_id: int = Query(...), request: ScheduleCreateRequest = Body(...)):
    """创建日程"""
    try:
        schedule = assistant_service.smart_schedule.create_schedule(
            user_id=user_id,
            title=request.title,
            start_time=request.start_time,
            end_time=request.end_time,
            description=request.description,
            location=request.location,
            attendees=request.attendees,
            is_recurring=request.is_recurring,
            recurrence_pattern=request.recurrence_pattern,
            recurrence_end=request.recurrence_end,
            priority=request.priority,
            timezone=request.timezone
        )
        return {"success": True, "data": schedule.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: int):
    """获取日程详情"""
    schedule = assistant_service.smart_schedule.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"success": True, "data": schedule.to_dict()}


@router.get("/schedules")
async def get_user_schedules(user_id: int = Query(...),
                              start_date: str = Query(None),
                              end_date: str = Query(None)):
    """获取用户日程列表"""
    schedules = assistant_service.smart_schedule.get_user_schedules(user_id, start_date, end_date)
    return {"success": True, "data": [s.to_dict() for s in schedules]}


@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id: int, request: ScheduleUpdateRequest):
    """更新日程"""
    schedule = assistant_service.smart_schedule.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(schedule, key, value)

    updated = assistant_service.smart_schedule.update_schedule(schedule)
    return {"success": True, "data": updated.to_dict()}


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """删除日程"""
    success = assistant_service.smart_schedule.delete_schedule(schedule_id)
    return {"success": success}


@router.post("/schedules/{schedule_id}/conflicts")
async def detect_schedule_conflicts(schedule_id: int, user_id: int = Query(...)):
    """检测日程冲突"""
    schedule = assistant_service.smart_schedule.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    conflicts = assistant_service.smart_schedule.detect_conflicts(user_id, schedule)
    return {"success": True, "data": [c.to_dict() for c in conflicts]}


@router.post("/schedules/suggest-alternatives")
async def suggest_alternative_times(user_id: int = Query(...),
                                     start_time: str = Body(..., embed=True),
                                     end_time: str = Body(..., embed=True),
                                     duration_minutes: int = Body(60)):
    """建议替代时间"""
    schedule = type('SmartSchedule', (), {
        'start_time': start_time,
        'end_time': end_time,
        'id': None
    })()

    alternatives = assistant_service.smart_schedule.suggest_alternative_times(
        user_id, schedule, duration_minutes
    )
    return {"success": True, "data": alternatives}


# ==================== 会议管理 ====================

@router.post("/meetings")
async def create_meeting(organizer_id: int = Query(...), request: MeetingCreateRequest = Body(...)):
    """创建会议"""
    try:
        meeting = assistant_service.meeting_summary.create_meeting(
            title=request.title,
            meeting_type=request.meeting_type,
            organizer_id=organizer_id,
            start_time=request.start_time,
            end_time=request.end_time,
            description=request.description,
            location=request.location,
            attendees=request.attendees,
            agenda=request.agenda
        )
        return {"success": True, "data": meeting.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: int):
    """获取会议详情"""
    meeting = assistant_service.meeting_summary.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"success": True, "data": meeting.to_dict()}


@router.get("/meetings")
async def get_user_meetings(user_id: int = Query(...), status: str = Query(None)):
    """获取用户会议列表"""
    meetings = assistant_service.meeting_summary.get_user_meetings(user_id, status)
    return {"success": True, "data": [m.to_dict() for m in meetings]}


@router.put("/meetings/{meeting_id}")
async def update_meeting(meeting_id: int, request: MeetingUpdateRequest):
    """更新会议"""
    meeting = assistant_service.meeting_summary.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(meeting, key, value)

    updated = assistant_service.meeting_summary.update_meeting(meeting)
    return {"success": True, "data": updated.to_dict()}


@router.delete("/meetings/{meeting_id}")
async def delete_meeting(meeting_id: int):
    """删除会议"""
    success = assistant_service.meeting_summary.delete_meeting(meeting_id)
    return {"success": success}


@router.post("/meetings/{meeting_id}/summary")
async def generate_meeting_summary(meeting_id: int,
                                    transcript: str = Body(None, embed=True),
                                    notes: str = Body(None, embed=True)):
    """生成会议摘要"""
    try:
        summary = assistant_service.meeting_summary.generate_summary(
            meeting_id, transcript, notes
        )
        return {"success": True, "data": summary.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meetings/{meeting_id}/summary")
async def get_meeting_summary(meeting_id: int):
    """获取会议摘要"""
    # 简化实现：获取最新的摘要
    from models.p19_assistant_models import get_assistant_db
    db = get_assistant_db()
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM p19_meeting_summaries
        WHERE meeting_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (meeting_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Summary not found")

    return {"success": True, "data": dict(row)}


@router.post("/meetings/{meeting_id}/action-items")
async def create_action_item(meeting_id: int, request: ActionItemCreateRequest):
    """创建会议行动项"""
    try:
        action_item = assistant_service.meeting_summary.create_action_item(
            meeting_id=meeting_id,
            title=request.title,
            description=request.description,
            assignee_id=request.assignee_id,
            due_date=request.due_date,
            priority=request.priority
        )
        return {"success": True, "data": action_item.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meetings/{meeting_id}/action-items")
async def get_meeting_action_items(meeting_id: int):
    """获取会议行动项列表"""
    action_items = assistant_service.meeting_summary.get_meeting_action_items(meeting_id)
    return {"success": True, "data": [a.to_dict() for a in action_items]}


@router.post("/action-items/{action_item_id}/complete")
async def complete_action_item(action_item_id: int,
                                completion_notes: str = Body(None, embed=True)):
    """完成行动项"""
    success = assistant_service.meeting_summary.complete_action_item(
        action_item_id, completion_notes
    )
    return {"success": success}


# ==================== 工作报告 ====================

@router.post("/reports")
async def create_report(user_id: int = Query(...), request: ReportCreateRequest = Body(...)):
    """创建工作报告"""
    try:
        report = assistant_service.auto_report.create_report(
            user_id=user_id,
            report_type=request.report_type,
            period_start=request.period_start,
            period_end=request.period_end,
            title=request.title,
            content=request.content,
            tasks_completed=request.tasks_completed,
            time_spent_hours=request.time_spent_hours,
            achievements=request.achievements,
            blockers=request.blockers,
            next_steps=request.next_steps
        )
        return {"success": True, "data": report.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}")
async def get_report(report_id: int):
    """获取报告详情"""
    report = assistant_service.auto_report.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"success": True, "data": report.to_dict()}


@router.get("/reports")
async def get_user_reports(user_id: int = Query(...),
                            report_type: str = Query(None),
                            limit: int = Query(50)):
    """获取用户报告列表"""
    reports = assistant_service.auto_report.get_user_reports(user_id, report_type, limit)
    return {"success": True, "data": [r.to_dict() for r in reports]}


@router.put("/reports/{report_id}")
async def update_report(report_id: int, update_data: Dict[str, Any] = Body(...)):
    """更新报告"""
    report = assistant_service.auto_report.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    for key, value in update_data.items():
        if hasattr(report, key):
            setattr(report, key, value)

    updated = assistant_service.auto_report.update_report(report)
    return {"success": True, "data": updated.to_dict()}


@router.delete("/reports/{report_id}")
async def delete_report(report_id: int):
    """删除报告"""
    success = assistant_service.auto_report.delete_report(report_id)
    return {"success": success}


@router.post("/reports/auto-generate")
async def generate_auto_report(user_id: int = Query(...), request: AutoReportRequest = Body(...)):
    """自动生成报告"""
    try:
        report = assistant_service.auto_report.generate_auto_report(
            user_id=user_id,
            report_type=request.report_type,
            period_start=request.period_start,
            period_end=request.period_end,
            template_id=request.template_id
        )
        return {"success": True, "data": report.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 报告模板 ====================

@router.post("/report-templates")
async def create_report_template(user_id: int = Query(...), request: ReportTemplateCreateRequest = Body(...)):
    """创建报告模板"""
    try:
        template = assistant_service.auto_report.create_template(
            user_id=user_id,
            name=request.name,
            report_type=request.report_type,
            template_content=request.template_content,
            description=request.description,
            sections=request.sections,
            is_default=request.is_default
        )
        return {"success": True, "data": template.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report-templates")
async def get_user_templates(user_id: int = Query(...)):
    """获取用户模板列表"""
    templates = assistant_service.auto_report.get_user_templates(user_id)
    return {"success": True, "data": [t.to_dict() for t in templates]}


# ==================== 仪表盘 ====================

@router.get("/dashboard")
async def get_assistant_dashboard(user_id: int = Query(...)):
    """获取 AI 助手仪表盘"""
    dashboard = assistant_service.get_dashboard(user_id)
    return {"success": True, "data": dashboard}
