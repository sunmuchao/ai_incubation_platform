"""
约会提醒 API

提醒用户的约会安排：
- 创建约会计划
- 约会前提醒
- 约会准备建议
- 约会后反馈
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from db.database import get_db
from services.date_reminder_service import DateReminderService, get_date_reminder_service
from utils.logger import logger

router = APIRouter(prefix="/api/date-reminder", tags=["Date Reminder"])


class CreateDatePlanRequest(BaseModel):
    """创建约会计划请求"""
    partner_id: str
    date_time: str  # ISO 格式
    location: str
    activity: str
    notes: Optional[str] = None
    reminder_settings: Optional[Dict[str, bool]] = None


class DatePlanResponse(BaseModel):
    """约会计划响应"""
    plan_id: str
    user_id: str
    partner_id: str
    date_time: str
    location: str
    activity: str
    notes: Optional[str] = None
    reminder_settings: Dict[str, bool]
    status: str
    created_at: str


class DateFeedbackRequest(BaseModel):
    """约会反馈请求"""
    plan_id: str
    rating: int  # 1-5
    feedback: Optional[str] = None


@router.post("/create", response_model=DatePlanResponse)
async def create_date_plan(
    user_id: str,
    request: CreateDatePlanRequest,
    db: Session = Depends(get_db)
):
    """
    创建约会计划

    设置约会时间、地点、活动和提醒
    """
    try:
        service = get_date_reminder_service(db)

        # 解析时间
        date_time = datetime.fromisoformat(request.date_time)

        result = service.create_date_plan(
            user_id=user_id,
            partner_id=request.partner_id,
            date_time=date_time,
            location=request.location,
            activity=request.activity,
            notes=request.notes,
            reminder_settings=request.reminder_settings
        )

        logger.info(f"Date plan created: {result['plan_id']}")
        return result
    except Exception as e:
        logger.error(f"Failed to create date plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upcoming/{user_id}")
async def get_upcoming_dates(
    user_id: str,
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    获取即将到来的约会
    """
    try:
        service = get_date_reminder_service(db)
        dates = service.get_upcoming_dates(user_id, limit)
        return {"dates": dates}
    except Exception as e:
        logger.error(f"Failed to get upcoming dates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reminders/{user_id}")
async def get_pending_reminders(user_id: str, db: Session = Depends(get_db)):
    """
    获取待发送的提醒

    用于检查需要发送的约会提醒
    """
    try:
        service = get_date_reminder_service(db)
        reminders = service.get_pending_reminders(user_id)
        return {"reminders": reminders}
    except Exception as e:
        logger.error(f"Failed to get pending reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prepare/{plan_id}")
async def get_preparation_suggestions(
    plan_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    AI 生成约会准备建议

    根据约会计划、双方资料生成准备建议
    """
    try:
        # 获取约会计划
        from models.date_reminder import DatePlanDB
        from db.models import UserDB

        plan = db.query(DatePlanDB).filter(DatePlanDB.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="约会计划不存在")

        # 获取用户资料
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        partner = db.query(UserDB).filter(UserDB.id == plan.partner_id).first()

        if not user or not partner:
            raise HTTPException(status_code=404, detail="用户不存在")

        date_plan = {
            "date_time": plan.date_time.isoformat(),
            "location": plan.location,
            "activity": plan.activity,
            "notes": plan.notes
        }

        user_profile = {
            "interests": user.interests,
            "bio": user.bio
        }

        partner_profile = {
            "interests": partner.interests,
            "bio": partner.bio
        }

        service = get_date_reminder_service(db)
        suggestions = await service.generate_date_preparation_suggestions(
            date_plan=date_plan,
            user_profile=user_profile,
            partner_profile=partner_profile
        )

        return {"suggestions": suggestions}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status")
async def update_date_status(
    plan_id: str,
    status: str,  # scheduled/completed/cancelled/postponed
    db: Session = Depends(get_db)
):
    """
    更新约会状态
    """
    try:
        service = get_date_reminder_service(db)
        success = service.update_date_status(plan_id, status)
        if success:
            return {"success": True, "message": "状态已更新"}
        else:
            return {"success": False, "message": "约会计划不存在"}
    except Exception as e:
        logger.error(f"Failed to update status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def record_date_feedback(
    user_id: str,
    request: DateFeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    记录约会反馈
    """
    try:
        service = get_date_reminder_service(db)
        result = service.record_date_feedback(
            plan_id=request.plan_id,
            user_id=user_id,
            rating=request.rating,
            feedback=request.feedback
        )
        return result
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))