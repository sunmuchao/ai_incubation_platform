"""
P11 感官洞察 API 端点

包含：
1. AI 视频面诊（情感翻译官）- 微表情捕捉、语音情感分析、情感报告生成
2. 物理安全守护神 - 位置安全监测、语音异常检测、分级响应机制
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from services.p11_services import (
    emotion_analysis_service,
    emotion_report_service
)
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

@router_emotion_analysis.post("/analyze/micro-expression", response_model=AnalysisResponse)
async def analyze_micro_expression(
    request: MicroExpressionAnalysisRequest,
    user_id: str = Body(..., embed=True)
):
    """
    分析微表情

    接收计算机视觉模型输出的面部数据，分析用户的微表情情感。
    """
    try:
        analysis_id = emotion_analysis_service.analyze_micro_expression(
            user_id=user_id,
            session_id=request.session_id,
            facial_data=request.facial_data
        )

        # 获取分析结果
        analysis = emotion_analysis_service.get_analysis_by_session(request.session_id)

        return AnalysisResponse(
            analysis_id=analysis_id,
            dominant_emotion=analysis.combined_emotion if analysis else None,
            confidence=analysis.emotion_confidence if analysis else 0,
            emotional_state_summary=analysis.emotional_state_summary if analysis else None,
            ai_insights=analysis.ai_insights if analysis else None
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
    """
    try:
        analysis_id = emotion_analysis_service.analyze_voice_emotion(
            user_id=user_id,
            session_id=request.session_id,
            voice_data=request.voice_data
        )

        analysis = emotion_analysis_service.get_analysis_by_session(request.session_id)

        return AnalysisResponse(
            analysis_id=analysis_id,
            dominant_emotion=analysis.combined_emotion if analysis else None,
            confidence=analysis.emotion_confidence if analysis else 0,
            emotional_state_summary=analysis.emotional_state_summary if analysis else None,
            ai_insights=analysis.ai_insights if analysis else None
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
    """
    try:
        analysis_id = emotion_analysis_service.combined_analysis(
            user_id=user_id,
            session_id=request.session_id,
            facial_data=request.facial_data,
            voice_data=request.voice_data
        )

        analysis = emotion_analysis_service.get_analysis_by_session(request.session_id)

        return AnalysisResponse(
            analysis_id=analysis_id,
            dominant_emotion=analysis.combined_emotion if analysis else None,
            confidence=analysis.emotion_confidence if analysis else 0,
            emotional_state_summary=analysis.emotional_state_summary if analysis else None,
            ai_insights=analysis.ai_insights if analysis else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_emotion_analysis.get("/history/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_analysis_history(
    user_id: str,
    limit: int = 10
):
    """获取用户的情感分析历史"""
    try:
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

@router_safety.post("/check/location", response_model=SafetyCheckResponse)
async def check_location_safety(
    request: LocationSafetyCheckRequest,
    user_id: str = Body(..., embed=True)
):
    """
    执行位置安全检查

    评估当前位置的安全性，包括：
    - 是否在预设的安全区域
    - 是否是公共场所
    - 是否偏僻
    - 附近是否有安全设施
    """
    try:
        result = safety_monitoring_service.perform_location_safety_check(
            user_id=user_id,
            location_data=request.location_data,
            session_id=request.session_id,
            partner_user_id=request.partner_user_id
        )

        return SafetyCheckResponse(
            check_id=result["check_id"],
            risk_level=result["risk_level"],
            risk_score=result["risk_score"],
            alert_triggered=result["alert_triggered"],
            alert_id=result.get("alert_id")
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

    分析语音中的异常信号，包括：
    - 求救关键词检测
    - 压力水平分析
    - 背景噪音评估
    """
    try:
        result = safety_monitoring_service.perform_voice_anomaly_check(
            user_id=user_id,
            voice_data=request.voice_data,
            session_id=request.session_id,
            partner_user_id=request.partner_user_id
        )

        return SafetyCheckResponse(
            check_id=result["check_id"],
            risk_level=result["risk_level"],
            risk_score=result["risk_score"],
            alert_triggered=result["alert_triggered"],
            alert_id=result.get("alert_id")
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

    用户主动签到报告安全状态。
    """
    try:
        result = safety_monitoring_service.perform_scheduled_checkin(
            user_id=user_id,
            session_id=request.session_id,
            user_status=request.user_status,
            note=request.note
        )

        return SafetyCheckResponse(
            check_id=result["check_id"],
            risk_level=result["risk_level"],
            risk_score=result["risk_score"],
            alert_triggered=result["alert_triggered"],
            alert_id=result.get("alert_id")
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

    移动端专用的紧急求助按钮，触发后：
    1. 立即创建安全警报
    2. 通知所有紧急联系人
    3. 记录当前位置和时间
    """
    try:
        result = safety_monitoring_service.trigger_emergency(
            user_id=user_id,
            session_id=request.session_id,
            location_data=request.location_data,
            emergency_type=request.emergency_type,
            note=request.note
        )

        return EmergencyResponse(
            emergency_id=result["emergency_id"],
            alert_level=result["alert_level"],
            status=result["status"],
            emergency_contacts_notified=result["contacts_notified"],
            message=result["message"]
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

    手动触发通知指定的紧急联系人，可选择是否分享当前位置。
    """
    try:
        result = safety_monitoring_service.notify_emergency_contact(
            user_id=user_id,
            session_id=request.session_id,
            contact_index=request.contact_index,
            custom_message=request.message,
            location_data=request.location_data if request.share_location else None
        )

        return NotifyContactResponse(
            notification_id=result["notification_id"],
            contact_name=result["contact_name"],
            contact_phone=result["contact_phone"],
            notified_at=result["notified_at"],
            location_shared=result["location_shared"],
            message=result["message"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
