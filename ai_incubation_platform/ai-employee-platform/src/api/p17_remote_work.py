"""
P17 远程工作支持 - API 路由层
版本：v17.0.0
日期：2026-04-05
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from models.p17_models import WorkMode, PresenceStatus as PresenceStatusEnum, ActivityType, TeamEventType
from services.p17_remote_work_service import (
    RemoteWorkService, RemoteWorkSessionService, PresenceService,
    VirtualWorkspaceService, WorkActivityService, TeamEventService,
    TimezoneCoordinationService, VirtualWaterCoolerService,
    RemoteWorkPolicyService, RemoteWorkMetricsService, RemoteWorkDB
)

router = APIRouter(prefix="/api/remote-work", tags=["P17 远程工作支持"])

# 全局服务实例（懒加载）
_remote_work_service = None


def get_service() -> RemoteWorkService:
    """获取远程工作服务实例"""
    global _remote_work_service
    if _remote_work_service is None:
        _remote_work_service = RemoteWorkService()
    return _remote_work_service


# ==================== Pydantic 模型 ====================

class StartSessionRequest(BaseModel):
    work_mode: str = WorkMode.REMOTE.value
    location: Optional[str] = None


class EndSessionRequest(BaseModel):
    notes: Optional[str] = None


class SetPresenceRequest(BaseModel):
    status: str
    work_mode: str = WorkMode.OFFICE.value
    status_message: Optional[str] = None
    until_minutes: Optional[int] = None
    timezone: Optional[str] = None


class CreateWorkspaceRequest(BaseModel):
    name: str
    workspace_type: str = "office"
    capacity: int = 10
    description: Optional[str] = None
    is_private: bool = False
    amenities: Optional[List[str]] = None


class StartActivityRequest(BaseModel):
    activity_type: str
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    description: Optional[str] = None
    is_focus_time: bool = False


class CreateEventRequest(BaseModel):
    title: str
    event_type: str = TeamEventType.VIRTUAL_HAPPY_HOUR.value
    start_time: Optional[str] = None
    duration_minutes: int = 60
    description: Optional[str] = None
    virtual_workspace_id: Optional[str] = None
    meeting_link: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None


class RSVPRequest(BaseModel):
    status: str = "going"


class CreateCoordinationRequest(BaseModel):
    team_id: str
    members: List[Dict[str, Any]]


class CreatePolicyRequest(BaseModel):
    name: str
    description: Optional[str] = None
    remote_days_required: int = 0
    office_days_required: int = 0
    core_hours_start: Optional[str] = None
    core_hours_end: Optional[str] = None
    allowed_countries: Optional[List[str]] = None
    equipment_allowance: Optional[float] = None
    internet_allowance: Optional[float] = None


class AddMessageRequest(BaseModel):
    content: str


# ==================== 远程工作会话 API ====================

@router.post("/sessions/start")
async def start_session(request: StartSessionRequest, employee_id: str = Query(...)):
    """开始远程工作会话"""
    service = get_service().session_service
    session = service.start_session(
        employee_id=employee_id,
        work_mode=request.work_mode,
        location=request.location
    )
    return {"success": True, "session": session.to_dict()}


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, request: EndSessionRequest):
    """结束远程工作会话"""
    service = get_service().session_service
    session = service.end_session(session_id, notes=request.notes)
    if session:
        return {"success": True, "session": session.to_dict()}
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话详情"""
    service = get_service().session_service
    session = service.get_session(session_id)
    if session:
        return {"session": session.to_dict()}
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/sessions/employee/{employee_id}")
async def list_sessions(employee_id: str, limit: int = Query(100, ge=1, le=1000)):
    """列出员工的会话历史"""
    service = get_service().session_service
    sessions = service.list_sessions(employee_id, limit)
    return {"sessions": [s.to_dict() for s in sessions]}


@router.get("/sessions/employee/{employee_id}/active")
async def get_active_session(employee_id: str):
    """获取员工当前活跃的会话"""
    service = get_service().session_service
    session = service.get_active_session(employee_id)
    if session:
        return {"session": session.to_dict()}
    return {"session": None}


# ==================== 在线状态 API ====================

@router.post("/presence/set")
async def set_presence(request: SetPresenceRequest, employee_id: str = Query(...)):
    """设置在线状态"""
    service = get_service().presence_service
    presence = service.set_status(
        employee_id=employee_id,
        status=request.status,
        work_mode=request.work_mode,
        status_message=request.status_message,
        until_minutes=request.until_minutes,
        timezone=request.timezone
    )
    return {"success": True, "presence": presence.to_dict()}


@router.post("/presence/heartbeat")
async def update_heartbeat(employee_id: str = Query(...)):
    """更新心跳"""
    service = get_service().presence_service
    presence = service.update_heartbeat(employee_id)
    if presence:
        return {"success": True, "presence": presence.to_dict()}
    raise HTTPException(status_code=404, detail="Presence not found")


@router.get("/presence/{employee_id}")
async def get_presence(employee_id: str):
    """获取员工在线状态"""
    service = get_service().presence_service
    presence = service.get_status(employee_id)
    if presence:
        return {"presence": presence.to_dict()}
    return {"presence": None}


@router.get("/presence")
async def list_all_presence():
    """获取所有员工在线状态"""
    service = get_service().presence_service
    statuses = service.get_all_status()
    return {"presences": [s.to_dict() for s in statuses]}


@router.get("/presence/available")
async def get_available_employees():
    """获取可用状态的员工列表"""
    service = get_service().presence_service
    available = service.get_available_employees()
    return {"available_employees": [e.to_dict() for e in available]}


# ==================== 虚拟工作空间 API ====================

@router.post("/workspaces")
async def create_workspace(request: CreateWorkspaceRequest, owner_id: str = Query(...)):
    """创建虚拟工作空间"""
    service = get_service().workspace_service
    workspace = service.create_workspace(
        name=request.name,
        owner_id=owner_id,
        workspace_type=request.workspace_type,
        capacity=request.capacity,
        description=request.description,
        is_private=request.is_private,
        amenities=request.amenities
    )
    return {"success": True, "workspace": workspace.to_dict()}


@router.post("/workspaces/{workspace_id}/join")
async def join_workspace(workspace_id: str, employee_id: str = Query(...)):
    """加入虚拟工作空间"""
    service = get_service().workspace_service
    try:
        workspace = service.join_workspace(workspace_id, employee_id)
        if workspace:
            return {"success": True, "workspace": workspace.to_dict()}
        raise HTTPException(status_code=404, detail="Workspace not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspaces/{workspace_id}/leave")
async def leave_workspace(workspace_id: str, employee_id: str = Query(...)):
    """离开虚拟工作空间"""
    service = get_service().workspace_service
    workspace = service.leave_workspace(workspace_id, employee_id)
    if workspace:
        return {"success": True, "workspace": workspace.to_dict()}
    raise HTTPException(status_code=404, detail="Workspace not found")


@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str):
    """获取虚拟工作空间详情"""
    service = get_service().workspace_service
    workspace = service.get_workspace(workspace_id)
    if workspace:
        return {"workspace": workspace.to_dict()}
    raise HTTPException(status_code=404, detail="Workspace not found")


@router.get("/workspaces")
async def list_workspaces(owner_id: Optional[str] = Query(None),
                          workspace_type: Optional[str] = Query(None)):
    """列出虚拟工作空间"""
    service = get_service().workspace_service
    workspaces = service.list_workspaces(owner_id, workspace_type)
    return {"workspaces": [w.to_dict() for w in workspaces]}


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str):
    """删除虚拟工作空间"""
    service = get_service().workspace_service
    deleted = service.delete_workspace(workspace_id)
    if deleted:
        return {"success": True}
    raise HTTPException(status_code=404, detail="Workspace not found")


# ==================== 工作活动 API ====================

@router.post("/activities/start")
async def start_activity(request: StartActivityRequest, employee_id: str = Query(...)):
    """开始工作活动"""
    service = get_service().activity_service
    activity = service.start_activity(
        employee_id=employee_id,
        activity_type=request.activity_type,
        project_id=request.project_id,
        task_id=request.task_id,
        description=request.description,
        is_focus_time=request.is_focus_time
    )
    return {"success": True, "activity": activity.to_dict()}


@router.post("/activities/{activity_id}/end")
async def end_activity(activity_id: str,
                       self_reported_productivity: Optional[int] = Query(None, ge=1, le=10)):
    """结束工作活动"""
    service = get_service().activity_service
    activity = service.end_activity(activity_id, self_reported_productivity)
    if activity:
        return {"success": True, "activity": activity.to_dict()}
    raise HTTPException(status_code=404, detail="Activity not found")


@router.post("/activities/log")
async def log_activity(
    employee_id: str = Query(...),
    activity_type: str = Body(...),
    start_time: str = Body(...),
    end_time: str = Body(...),
    duration_minutes: int = Body(...),
    project_id: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    is_focus_time: bool = Body(False)
):
    """记录已完成的活动"""
    service = get_service().activity_service
    activity = service.log_activity(
        employee_id=employee_id,
        activity_type=activity_type,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        duration_minutes=duration_minutes,
        project_id=project_id,
        description=description,
        is_focus_time=is_focus_time
    )
    return {"success": True, "activity": activity.to_dict()}


@router.get("/activities/{activity_id}")
async def get_activity(activity_id: str):
    """获取活动详情"""
    service = get_service().activity_service
    activity = service.get_activity(activity_id)
    if activity:
        return {"activity": activity.to_dict()}
    raise HTTPException(status_code=404, detail="Activity not found")


@router.get("/activities/employee/{employee_id}")
async def list_activities(employee_id: str,
                          start_date: Optional[str] = Query(None),
                          end_date: Optional[str] = Query(None)):
    """列出活动记录"""
    service = get_service().activity_service
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    activities = service.list_activities(employee_id, start_dt, end_dt)
    return {"activities": [a.to_dict() for a in activities]}


@router.post("/activities/employee/{employee_id}/daily-metrics")
async def calculate_daily_metrics(employee_id: str, date: str = Query(...)):
    """计算员工的每日工作指标"""
    service = get_service().activity_service
    metrics = service.calculate_daily_metrics(employee_id, date)
    return {"metrics": metrics.to_dict()}


# ==================== 团队活动 API ====================

@router.post("/events")
async def create_event(request: CreateEventRequest, organizer_id: str = Query(...)):
    """创建团队活动"""
    service = get_service().event_service
    start_time = datetime.fromisoformat(request.start_time) if request.start_time else None
    event = service.create_event(
        title=request.title,
        organizer_id=organizer_id,
        event_type=request.event_type,
        start_time=start_time,
        duration_minutes=request.duration_minutes,
        description=request.description,
        virtual_workspace_id=request.virtual_workspace_id,
        meeting_link=request.meeting_link,
        is_recurring=request.is_recurring,
        recurrence_pattern=request.recurrence_pattern
    )
    return {"success": True, "event": event.to_dict()}


@router.post("/events/{event_id}/rsvp")
async def rsvp_event(event_id: str, request: RSVPRequest, employee_id: str = Query(...)):
    """回复活动邀请"""
    service = get_service().event_service
    event = service.rsvp(event_id, employee_id, request.status)
    if event:
        return {"success": True, "event": event.to_dict()}
    raise HTTPException(status_code=404, detail="Event not found")


@router.post("/events/{event_id}/participants")
async def add_participant(event_id: str, employee_id: str = Query(...)):
    """添加参与者"""
    service = get_service().event_service
    event = service.add_participant(event_id, employee_id)
    if event:
        return {"success": True, "event": event.to_dict()}
    raise HTTPException(status_code=404, detail="Event not found")


@router.post("/events/{event_id}/photos")
async def add_photo(event_id: str, photo_url: str = Query(...)):
    """添加活动照片"""
    service = get_service().event_service
    event = service.add_photo(event_id, photo_url)
    if event:
        return {"success": True, "event": event.to_dict()}
    raise HTTPException(status_code=404, detail="Event not found")


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """获取活动详情"""
    service = get_service().event_service
    event = service.get_event(event_id)
    if event:
        return {"event": event.to_dict()}
    raise HTTPException(status_code=404, detail="Event not found")


@router.get("/events")
async def list_events(organizer_id: Optional[str] = Query(None),
                      upcoming_only: bool = Query(False)):
    """列出活动"""
    service = get_service().event_service
    events = service.list_events(organizer_id, upcoming_only)
    return {"events": [e.to_dict() for e in events]}


@router.get("/events/{event_id}/rsvp-stats")
async def get_rsvp_stats(event_id: str):
    """获取活动回复统计"""
    service = get_service().event_service
    stats = service.get_rsvp_stats(event_id)
    return {"stats": stats}


# ==================== 时区协调 API ====================

@router.post("/timezone-coordination")
async def create_coordination(request: CreateCoordinationRequest):
    """创建时区协调记录"""
    service = get_service().timezone_service
    coordination = service.create_coordination(
        team_id=request.team_id,
        members=request.members
    )
    return {"success": True, "coordination": coordination.to_dict()}


@router.get("/timezone-coordination/{team_id}")
async def get_coordination(team_id: str):
    """获取时区协调记录"""
    service = get_service().timezone_service
    coordination = service.get_coordination(team_id)
    if coordination:
        return {"coordination": coordination.to_dict()}
    raise HTTPException(status_code=404, detail="Coordination not found")


@router.get("/timezone-coordination/{team_id}/meeting-times")
async def get_recommended_meeting_times(team_id: str):
    """获取推荐的会议时间"""
    service = get_service().timezone_service
    coordination = service.get_coordination(team_id)
    if coordination:
        return {
            "team_id": team_id,
            "recommended_meeting_times": coordination.preferred_meeting_times,
            "overlap_windows": coordination.overlap_windows
        }
    raise HTTPException(status_code=404, detail="Coordination not found")


# ==================== 虚拟茶水间 API ====================

@router.post("/water-cooler/start")
async def start_water_cooler(topic: Optional[str] = Query(None),
                             initiator_id: str = Query(...),
                             workspace_id: Optional[str] = Query(None)):
    """发起茶水间聊天"""
    service = get_service().water_cooler_service
    cooler = service.start_chat(initiator_id, topic, workspace_id)
    return {"success": True, "chat": cooler.to_dict()}


@router.post("/water-cooler/{chat_id}/join")
async def join_water_cooler(chat_id: str, employee_id: str = Query(...)):
    """加入茶水间聊天"""
    service = get_service().water_cooler_service
    cooler = service.join_chat(chat_id, employee_id)
    if cooler:
        return {"success": True, "chat": cooler.to_dict()}
    raise HTTPException(status_code=404, detail="Chat not found")


@router.post("/water-cooler/{chat_id}/message")
async def add_water_cooler_message(chat_id: str, request: AddMessageRequest,
                                    sender_id: str = Query(...)):
    """添加茶水间消息"""
    service = get_service().water_cooler_service
    cooler = service.add_message(chat_id, sender_id, request.content)
    if cooler:
        return {"success": True, "chat": cooler.to_dict()}
    raise HTTPException(status_code=404, detail="Chat not found")


@router.post("/water-cooler/{chat_id}/end")
async def end_water_cooler(chat_id: str):
    """结束茶水间聊天"""
    service = get_service().water_cooler_service
    cooler = service.end_chat(chat_id)
    if cooler:
        return {"success": True, "chat": cooler.to_dict()}
    raise HTTPException(status_code=404, detail="Chat not found")


@router.get("/water-cooler/{chat_id}")
async def get_water_cooler(chat_id: str):
    """获取茶水间聊天详情"""
    service = get_service().water_cooler_service
    cooler = service.get_chat(chat_id)
    if cooler:
        return {"chat": cooler.to_dict()}
    raise HTTPException(status_code=404, detail="Chat not found")


@router.get("/water-cooler")
async def list_active_water_coolers():
    """列出活跃的茶水间聊天"""
    service = get_service().water_cooler_service
    chats = service.list_active_chats()
    return {"chats": [c.to_dict() for c in chats]}


# ==================== 远程工作政策 API ====================

@router.post("/policies")
async def create_policy(request: CreatePolicyRequest,
                        organization_id: str = Query(...)):
    """创建远程工作政策"""
    service = get_service().policy_service
    policy = service.create_policy(
        organization_id=organization_id,
        name=request.name,
        description=request.description,
        remote_days_required=request.remote_days_required,
        office_days_required=request.office_days_required,
        core_hours_start=request.core_hours_start,
        core_hours_end=request.core_hours_end,
        allowed_countries=request.allowed_countries,
        equipment_allowance=request.equipment_allowance,
        internet_allowance=request.internet_allowance
    )
    return {"success": True, "policy": policy.to_dict()}


@router.get("/policies/{policy_id}")
async def get_policy(policy_id: str):
    """获取远程工作政策详情"""
    service = get_service().policy_service
    policy = service.get_policy(policy_id)
    if policy:
        return {"policy": policy.to_dict()}
    raise HTTPException(status_code=404, detail="Policy not found")


@router.get("/policies/organization/{organization_id}")
async def list_policies(organization_id: str):
    """列出组织的远程工作政策"""
    service = get_service().policy_service
    policies = service.list_policies(organization_id)
    return {"policies": [p.to_dict() for p in policies]}


@router.get("/policies/{policy_id}/compliance")
async def check_compliance(policy_id: str, employee_id: str = Query(...),
                           week_start: str = Query(...)):
    """检查员工是否符合政策要求"""
    service = get_service().policy_service
    policy = service.get_policy(policy_id)
    if policy:
        compliance = service.check_compliance(
            employee_id=employee_id,
            policy=policy,
            week_start=datetime.fromisoformat(week_start)
        )
        return {"compliance": compliance}
    raise HTTPException(status_code=404, detail="Policy not found")


# ==================== 远程工作指标 API ====================

@router.get("/metrics/{employee_id}/{date}")
async def get_daily_metrics(employee_id: str, date: str):
    """获取每日指标"""
    service = get_service().metrics_service
    metrics = service.get_daily_metrics(employee_id, date)
    if metrics:
        return {"metrics": metrics.to_dict()}
    return {"metrics": None}


@router.get("/metrics/{employee_id}/weekly")
async def get_weekly_metrics(employee_id: str,
                             week_start: str = Query(...)):
    """获取每周指标汇总"""
    service = get_service().metrics_service
    metrics = service.get_weekly_metrics(
        employee_id=employee_id,
        week_start=datetime.fromisoformat(week_start)
    )
    return {"metrics": metrics}


@router.get("/metrics/team")
async def get_team_metrics(employee_ids: List[str] = Query(...),
                           date: str = Query(...)):
    """获取团队指标"""
    service = get_service().metrics_service
    team_metrics = service.get_team_metrics(employee_ids, date)
    return {"team_metrics": team_metrics}


# ==================== 仪表盘 API ====================

@router.get("/dashboard/{employee_id}")
async def get_dashboard(employee_id: str):
    """获取远程工作仪表盘"""
    service = get_service()
    dashboard = service.get_dashboard(employee_id)
    return {"dashboard": dashboard}


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "remote-work",
        "version": "17.0.0"
    }
