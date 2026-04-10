"""
P11 感官洞察 API 端点

包含：
1. AI 视频面诊（情感翻译官）- 微表情捕捉、语音情感分析、情感报告生成
2. 物理安全守护神 - 位置安全监测、语音异常检测、分级响应机制

架构说明：
- API 层仅做参数校验、鉴权和响应格式化
- 业务逻辑在 Skill 层（EmotionAnalysisSkill, SafetyGuardianSkill）
- Service 层提供数据库操作和外部服务调用
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from agent.skills.emotion_analysis_skill import get_emotion_analysis_skill
from agent.skills.safety_guardian_skill import get_safety_guardian_skill
from services.p11_services import emotion_report_service
from services.p11_safety_service import safety_monitoring_service
from models.p11_models import EmotionAnalysisDB, EmotionReportDB, SafetyCheckDB, SafetyAlertDB, SafetyPlanDB, DateSafetySessionDB


# Router 实例
router_emotion_analysis = APIRouter(prefix="/api/p11/emotion", tags=["P11 情感分析"])
router_safety = APIRouter(prefix="/api/p11/safety", tags=["P11 安全监测"])
router_reports = APIRouter(prefix="/api/p11/reports", tags=["P11 情感报告"])


# ============= Pydantic 模型 =============

# 情感分析请求/响应模型
class MicroExpressionAnalysisRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    facial_data: Dict[str, Any] = Field(..., description="面部识别数据")


class VoiceEmotionAnalysisRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    voice_data: Dict[str, Any] = Field(..., description="语音特征数据")


class CombinedAnalysisRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    facial_data: Dict[str, Any] = Field(..., description="面部数据")
    voice_data: Dict[str, Any] = Field(..., description="语音数据")


class AnalysisResponse(BaseModel):
    analysis_id: str
    dominant_emotion: Optional[str]
    confidence: float
    emotional_state_summary: Optional[str]
    ai_insights: Optional[str]


# 安全检查请求/响应模型
class LocationSafetyCheckRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="会话 ID")
    partner_user_id: Optional[str] = Field(None, description="约会对象 ID")
    location_data: Dict[str, Any] = Field(..., description="位置数据")


class VoiceAnomalyCheckRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="会话 ID")
    partner_user_id: Optional[str] = Field(None, description="约会对象 ID")
    voice_data: Dict[str, Any] = Field(..., description="语音数据")


class ScheduledCheckinRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    user_status: str = Field("ok", description="用户状态：ok, concern, need_help")
    note: Optional[str] = Field(None, description="备注")


class SafetyCheckResponse(BaseModel):
    check_id: str
    risk_level: str
    risk_score: float
    alert_triggered: bool
    alert_id: Optional[str]


# 安全计划模型
class EmergencyContact(BaseModel):
    name: str
    relationship: str
    phone: str
    priority: int = 1
    notify_on_alert_levels: List[str] = ["urgent", "critical"]


class SafetyPlanRequest(BaseModel):
    emergency_contacts: List[EmergencyContact] = Field(..., description="紧急联系人列表")
    safety_preferences: Dict[str, Any] = Field(..., description="安全偏好设置")


class SafetyPlanResponse(BaseModel):
    plan_id: str
    emergency_contacts: List[Dict[str, Any]]
    safety_preferences: Dict[str, Any]


# 约会安全会话模型
class DateSafetySessionRequest(BaseModel):
    partner_user_id: Optional[str] = Field(None, description="约会对象 ID")
    date_id: Optional[str] = Field(None, description="约会 ID")
    scheduled_start: datetime = Field(..., description="计划开始时间")
    scheduled_end: datetime = Field(..., description="计划结束时间")


class DateSafetySessionResponse(BaseModel):
    session_id: str
    status: str
    scheduled_start: datetime
    scheduled_end: datetime


# 警报响应模型
class SafetyAlertResponse(BaseModel):
    alert_id: str
    alert_level: str
    alert_type: str
    alert_title: str
    alert_message: str
    response_status: str
    created_at: datetime


# ============= 情感分析 API =============
# API 层仅做参数校验和响应格式化，业务逻辑在 Skill 层

@router_emotion_analysis.post("/analyze/micro-expression", response_model=AnalysisResponse)
async def analyze_micro_expression(
    request: MicroExpressionAnalysisRequest,
    user_id: str = Body(..., embed=True)
):
    """
    分析微表情

    接收计算机视觉模型输出的面部数据，分析用户的微表情情感。
    通过 EmotionAnalysisSkill 处理 AI 决策逻辑。
    """
    try:
        import uuid
        # 调用 Skill 层处理业务逻辑
        skill = get_emotion_analysis_skill()
        result = await skill.execute(
            session_id=request.session_id,
            analysis_type="micro_expression",
            facial_data=request.facial_data,
            context={"user_id": user_id}
        )

        analysis_result = result.get("analysis_result", {})

        return AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            dominant_emotion=analysis_result.get("dominant_emotion"),
            confidence=analysis_result.get("emotion_confidence", 0),
            emotional_state_summary=analysis_result.get("ai_insights"),
            ai_insights=result.get("ai_message")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_emotion_analysis.post("/analyze/voice-emotion", response_model=AnalysisResponse)
async def analyze_voice_emotion(
    request: VoiceEmotionAnalysisRequest,
    user_id: str = Body(..., embed=True)
):
    """
    分析语音情感

    接收语音分析模型输出的特征数据，分析用户的语音情感。
    通过 EmotionAnalysisSkill 处理 AI 决策逻辑。
    """
    try:
        import uuid
        # 调用 Skill 层处理业务逻辑
        skill = get_emotion_analysis_skill()
        result = await skill.execute(
            session_id=request.session_id,
            analysis_type="voice_emotion",
            voice_data=request.voice_data,
            context={"user_id": user_id}
        )

        analysis_result = result.get("analysis_result", {})

        return AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            dominant_emotion=analysis_result.get("dominant_emotion"),
            confidence=analysis_result.get("emotion_confidence", 0),
            emotional_state_summary=analysis_result.get("ai_insights"),
            ai_insights=result.get("ai_message")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_emotion_analysis.post("/analyze/combined", response_model=AnalysisResponse)
async def analyze_combined(
    request: CombinedAnalysisRequest,
    user_id: str = Body(..., embed=True)
):
    """
    综合分析（微表情 + 语音）

    同时分析面部表情和语音情感，生成综合的情感分析报告。
    通过 EmotionAnalysisSkill 处理 AI 决策逻辑。
    """
    try:
        import uuid
        # 调用 Skill 层处理业务逻辑
        skill = get_emotion_analysis_skill()
        result = await skill.execute(
            session_id=request.session_id,
            analysis_type="combined",
            facial_data=request.facial_data,
            voice_data=request.voice_data,
            context={"user_id": user_id}
        )

        analysis_result = result.get("analysis_result", {})

        return AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            dominant_emotion=analysis_result.get("dominant_emotion"),
            confidence=analysis_result.get("emotion_confidence", 0),
            emotional_state_summary=analysis_result.get("ai_insights"),
            ai_insights=result.get("ai_message")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_emotion_analysis.get("/history/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_analysis_history(
    user_id: str,
    limit: int = 10
):
    """获取用户的情感分析历史（直接查询数据库）"""
    try:
        from services.p11_services import emotion_analysis_service
        analyses = emotion_analysis_service.get_user_analyses(user_id, limit)
        return [{
            "id": a.id,
            "session_id": a.session_id,
            "analysis_type": a.analysis_type,
            "combined_emotion": a.combined_emotion,
            "emotion_confidence": a.emotion_confidence,
            "emotional_state_summary": a.emotional_state_summary,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in analyses]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 安全监测 API =============
# API 层仅做参数校验和响应格式化，业务逻辑在 Skill 层

@router_safety.post("/check/location", response_model=SafetyCheckResponse)
async def check_location_safety(
    request: LocationSafetyCheckRequest,
    user_id: str = Body(..., embed=True)
):
    """
    执行位置安全检查

    评估当前位置的安全性，通过 SafetyGuardianSkill 处理 AI 决策逻辑。
    """
    try:
        import uuid
        # 调用 Skill 层处理业务逻辑
        skill = get_safety_guardian_skill()
        result = await skill.execute(
            session_id=request.session_id or f"loc_{datetime.now().timestamp()}",
            check_type="location",
            user_id=user_id,
            location_data=request.location_data,
            partner_user_id=request.partner_user_id
        )

        safety_result = result.get("safety_check_result", {})

        return SafetyCheckResponse(
            check_id=safety_result.get("check_id") or str(uuid.uuid4()),
            risk_level=result.get("alert_level") or "low",
            risk_score=safety_result.get("risk_score", 0),
            alert_triggered=result.get("alert_triggered", False),
            alert_id=result.get("emergency_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.post("/check/voice", response_model=SafetyCheckResponse)
async def check_voice_anomaly(
    request: VoiceAnomalyCheckRequest,
    user_id: str = Body(..., embed=True)
):
    """
    执行语音异常检测

    分析语音中的异常信号，通过 SafetyGuardianSkill 处理 AI 决策逻辑。
    """
    try:
        import uuid
        # 调用 Skill 层处理业务逻辑
        skill = get_safety_guardian_skill()
        result = await skill.execute(
            session_id=request.session_id or f"voice_{datetime.now().timestamp()}",
            check_type="voice",
            user_id=user_id,
            audio_features=request.voice_data,
            partner_user_id=request.partner_user_id
        )

        safety_result = result.get("safety_check_result", {})

        return SafetyCheckResponse(
            check_id=safety_result.get("check_id") or str(uuid.uuid4()),
            risk_level=result.get("alert_level") or "low",
            risk_score=safety_result.get("risk_score", 0),
            alert_triggered=result.get("alert_triggered", False),
            alert_id=result.get("emergency_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.post("/checkin", response_model=SafetyCheckResponse)
async def perform_checkin(
    request: ScheduledCheckinRequest,
    user_id: str = Body(..., embed=True)
):
    """
    执行定时签到

    用户主动签到报告安全状态，通过 SafetyGuardianSkill 处理。
    """
    try:
        import uuid
        # 调用 Skill 层处理业务逻辑
        skill = get_safety_guardian_skill()
        result = await skill.execute(
            session_id=request.session_id,
            check_type="scheduled_checkin",
            user_id=user_id,
            context={"user_status": request.user_status, "note": request.note}
        )

        safety_result = result.get("safety_check_result", {})

        # 根据用户状态调整风险等级
        risk_level = safety_result.get("risk_level") or "low"
        if request.user_status == "need_help":
            risk_level = "high"
        elif request.user_status == "concern":
            risk_level = "medium"

        return SafetyCheckResponse(
            check_id=safety_result.get("check_id") or str(uuid.uuid4()),
            risk_level=risk_level,
            risk_score=safety_result.get("risk_score", 0),
            alert_triggered=request.user_status == "need_help",
            alert_id=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.get("/alerts/{user_id}", response_model=List[SafetyAlertResponse])
async def get_user_alerts(
    user_id: str,
    limit: int = 20
):
    """获取用户的安全警报历史"""
    try:
        alerts = safety_monitoring_service.get_safety_alerts(user_id, limit)
        return [{
            "alert_id": a.id,
            "alert_level": a.alert_level,
            "alert_type": a.alert_type,
            "alert_title": a.alert_title,
            "alert_message": a.alert_message,
            "response_status": a.response_status,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in alerts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.post("/alert/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    user_id: str = Body(..., embed=True)
):
    """确认警报"""
    try:
        success = safety_monitoring_service.acknowledge_alert(alert_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"status": "success", "message": "Alert acknowledged"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.post("/alert/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    user_id: str = Body(..., embed=True),
    resolution_notes: str = Body(..., embed=True),
    is_false_alarm: bool = Body(False, embed=True)
):
    """解决警报"""
    try:
        success = safety_monitoring_service.resolve_alert(
            alert_id, user_id, resolution_notes, is_false_alarm
        )
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"status": "success", "message": "Alert resolved"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.post("/plan", response_model=SafetyPlanResponse)
async def create_safety_plan(
    request: SafetyPlanRequest,
    user_id: str = Body(..., embed=True)
):
    """创建或更新用户安全计划"""
    try:
        plan_id = safety_monitoring_service.create_safety_plan(
            user_id=user_id,
            emergency_contacts=[c.dict() for c in request.emergency_contacts],
            safety_preferences=request.safety_preferences
        )

        plan = safety_monitoring_service.get_user_safety_plan(user_id)

        return SafetyPlanResponse(
            plan_id=plan_id,
            emergency_contacts=plan.emergency_contacts if plan else [],
            safety_preferences=plan.safety_preferences if plan else {}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.get("/plan/{user_id}", response_model=SafetyPlanResponse)
async def get_safety_plan(user_id: str):
    """获取用户安全计划"""
    try:
        plan = safety_monitoring_service.get_user_safety_plan(user_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Safety plan not found")

        return SafetyPlanResponse(
            plan_id=plan.id,
            emergency_contacts=plan.emergency_contacts or [],
            safety_preferences=plan.safety_preferences or {}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.post("/date-session", response_model=DateSafetySessionResponse)
async def create_date_safety_session(
    request: DateSafetySessionRequest,
    user_id: str = Body(..., embed=True)
):
    """创建约会安全会话"""
    try:
        session_id = safety_monitoring_service.create_date_safety_session(
            user_id=user_id,
            partner_user_id=request.partner_user_id,
            date_id=request.date_id,
            scheduled_start=request.scheduled_start,
            scheduled_end=request.scheduled_end
        )

        return DateSafetySessionResponse(
            session_id=session_id,
            status="scheduled",
            scheduled_start=request.scheduled_start,
            scheduled_end=request.scheduled_end
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.post("/date-session/{session_id}/start")
async def start_date_safety_session(session_id: str, user_id: str = Body(..., embed=True)):
    """开始约会安全会话"""
    try:
        success = safety_monitoring_service.start_date_safety_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "success", "message": "Session started"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_safety.post("/date-session/{session_id}/complete")
async def complete_date_safety_session(
    session_id: str,
    user_id: str = Body(..., embed=True),
    safety_rating: int = Body(..., ge=1, le=5, embed=True),
    feedback: Optional[str] = Body(None, embed=True)
):
    """完成约会安全会话"""
    try:
        success = safety_monitoring_service.complete_date_safety_session(
            session_id, safety_rating, feedback
        )
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "success", "message": "Session completed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 情感报告 API =============

@router_reports.post("/generate/{session_id}")
async def generate_emotion_report(
    session_id: str,
    user_id: str = Body(..., embed=True)
):
    """生成会话情感报告"""
    try:
        report_id = emotion_report_service.generate_session_report(
            user_id=user_id,
            session_id=session_id
        )
        return {"status": "success", "report_id": report_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_reports.get("/history/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_reports(
    user_id: str,
    limit: int = 10
):
    """获取用户的情感报告历史"""
    try:
        reports = emotion_report_service.get_user_reports(user_id, limit)
        return [{
            "id": r.id,
            "session_id": r.session_id,
            "report_type": r.report_type,
            "title": r.title,
            "summary": r.summary,
            "emotional_metrics": r.emotional_metrics,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in reports]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 移动端紧急求助 API =============

class EmergencyRequest(BaseModel):
    """紧急求助请求"""
    session_id: Optional[str] = Field(None, description="会话 ID")
    location_data: Dict[str, Any] = Field(..., description="当前位置数据")
    emergency_type: str = Field("general", description="紧急类型：general, medical, danger, harassment")
    note: Optional[str] = Field(None, description="备注说明")


class EmergencyResponse(BaseModel):
    """紧急求助响应"""
    emergency_id: str
    alert_level: str
    status: str
    emergency_contacts_notified: int
    message: str


@router_safety.post("/emergency", response_model=EmergencyResponse)
async def trigger_emergency(
    request: EmergencyRequest,
    user_id: str = Body(..., embed=True)
):
    """
    触发紧急求助

    移动端专用的紧急求助按钮，通过 SafetyGuardianSkill 处理 AI 决策：
    1. 立即创建安全警报
    2. 通知所有紧急联系人
    3. 记录当前位置和时间
    """
    try:
        # 调用 Skill 层处理紧急求助逻辑
        skill = get_safety_guardian_skill()
        result = await skill.trigger_emergency(
            user_id=user_id,
            emergency_type=request.emergency_type,
            location_data=request.location_data,
            note=request.note,
            session_id=request.session_id
        )

        emergency_data = result.get("emergency_data", {})

        return EmergencyResponse(
            emergency_id=emergency_data.get("emergency_id", ""),
            alert_level=emergency_data.get("alert_level", "critical"),
            status=emergency_data.get("status", "active"),
            emergency_contacts_notified=emergency_data.get("contacts_notified", 0),
            message=result.get("ai_message", "紧急求助已触发")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NotifyContactRequest(BaseModel):
    """通知紧急联系人请求"""
    session_id: Optional[str] = Field(None, description="会话 ID")
    contact_index: int = Field(0, description="联系人索引，默认第一个")
    message: Optional[str] = Field(None, description="自定义消息")
    location_data: Optional[Dict[str, Any]] = Field(None, description="当前位置数据")
    share_location: bool = Field(True, description="是否分享位置")


class NotifyContactResponse(BaseModel):
    """通知紧急联系人响应"""
    notification_id: str
    contact_name: str
    contact_phone: str
    notified_at: str
    location_shared: bool
    message: str


@router_safety.post("/notify-contact", response_model=NotifyContactResponse)
async def notify_emergency_contact(
    request: NotifyContactRequest,
    user_id: str = Body(..., embed=True)
):
    """
    通知紧急联系人

    手动触发通知指定的紧急联系人，通过 SafetyGuardianSkill 处理。
    """
    try:
        # 调用 Skill 层处理通知逻辑
        skill = get_safety_guardian_skill()
        result = await skill.notify_emergency_contact(
            user_id=user_id,
            contact_index=request.contact_index,
            session_id=request.session_id,
            message=request.message,
            location_data=request.location_data if request.share_location else None,
            share_location=request.share_location
        )

        notification_data = result.get("notification_data", {})

        return NotifyContactResponse(
            notification_id=notification_data.get("notification_id", ""),
            contact_name=notification_data.get("contact_name", ""),
            contact_phone=notification_data.get("contact_phone", ""),
            notified_at=notification_data.get("notified_at", datetime.now().isoformat()),
            location_shared=request.share_location,
            message=result.get("ai_message", "已通知紧急联系人")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
