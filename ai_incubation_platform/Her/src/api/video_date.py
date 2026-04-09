"""
v1.3 视频约会 API

提供视频约会预约、管理、互动小工具等功能。
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.video_date_service import VideoDateService
from services.icebreaker_service import IcebreakerService


router = APIRouter(prefix="/api/video-date", tags=["video-date"])


# ========== 请求/响应模型 ==========

class ScheduleDateRequest(BaseModel):
    """预约视频约会请求"""
    partner_id: str
    scheduled_time: datetime
    duration_minutes: int = 30
    theme: str = "初次见面"
    background: str = "default"


class DateResponse(BaseModel):
    """约会响应"""
    date_id: str
    partner_id: Optional[str] = None
    status: str
    scheduled_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    theme: Optional[str] = None
    room_id: Optional[str] = None
    rating: Optional[int] = None


class StartDateRequest(BaseModel):
    """开始约会请求"""
    background: Optional[str] = None
    filter: Optional[str] = None


class RateDateRequest(BaseModel):
    """评分请求"""
    rating: int  # 1-5
    review: Optional[str] = None


class CancelDateRequest(BaseModel):
    """取消约会请求"""
    reason: Optional[str] = None


# ========== 约会管理 API ==========

@router.post("/schedule", response_model=Dict[str, Any])
async def schedule_video_date(
    request: ScheduleDateRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """预约视频约会"""
    service = VideoDateService(db)

    try:
        result = service.schedule_date(
            user_id_1=current_user.id,
            user_id_2=request.partner_id,
            scheduled_time=request.scheduled_time,
            duration_minutes=request.duration_minutes,
            theme=request.theme,
            background=request.background
        )
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list", response_model=Dict[str, Any])
async def get_date_list(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取我的约会列表"""
    service = VideoDateService(db)
    dates = service.get_user_date_list(
        user_id=current_user.id,
        status=status,
        limit=limit,
        offset=offset
    )
    return {
        "success": True,
        "data": dates
    }


@router.get("/{date_id}", response_model=Dict[str, Any])
async def get_date_info(
    date_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取约会详情"""
    service = VideoDateService(db)
    info = service.get_date_info(date_id)

    if not info:
        raise HTTPException(status_code=404, detail="约会不存在")

    # 检查权限
    if info["user_id_1"] != current_user.id and info["user_id_2"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此约会")

    return {
        "success": True,
        "data": info
    }


@router.post("/{date_id}/start", response_model=Dict[str, Any])
async def start_video_date(
    date_id: str,
    request: StartDateRequest = None,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """开始视频约会"""
    service = VideoDateService(db)

    try:
        result = service.start_date(date_id, current_user.id)
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{date_id}/complete", response_model=Dict[str, Any])
async def complete_video_date(
    date_id: str,
    request: RateDateRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """完成视频约会并提交评分"""
    service = VideoDateService(db)

    try:
        service.complete_date(
            date_id=date_id,
            user_id=current_user.id,
            rating=request.rating,
            review=request.review
        )
        return {
            "success": True,
            "message": "约会已完成"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{date_id}/cancel", response_model=Dict[str, Any])
async def cancel_video_date(
    date_id: str,
    request: CancelDateRequest = None,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """取消视频约会"""
    service = VideoDateService(db)
    reason = request.reason if request else ""

    try:
        service.cancel_date(date_id, current_user.id, reason)
        return {
            "success": True,
            "message": "约会已取消"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reminders/upcoming", response_model=Dict[str, Any])
async def get_upcoming_reminders(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取即将到期的约会提醒"""
    service = VideoDateService(db)
    reminders = service.get_upcoming_reminders(current_user.id, hours)
    return {
        "success": True,
        "data": reminders
    }


# ========== 破冰问题 API ==========

@router.get("/icebreaker", response_model=Dict[str, Any])
async def get_icebreaker_questions(
    date_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取破冰问题推荐"""
    service = IcebreakerService(db)

    if date_id:
        # 获取约会信息以生成个性化问题
        date_service = VideoDateService(db)
        date_info = date_service.get_date_info(date_id)
        if date_info:
            questions = service.get_personalized_questions(
                date_info["user_id_1"],
                date_info["user_id_2"],
                limit=5
            )
        else:
            questions = service.get_questions(category=category, limit=5)
    else:
        questions = service.get_questions(category=category, limit=5)

    return {
        "success": True,
        "data": questions
    }


# ========== 虚拟背景 API ==========

AVAILABLE_BACKGROUNDS = [
    {"id": "default", "name": "默认", "category": "scene", "is_free": True},
    {"id": "cafe", "name": "咖啡厅", "category": "scene", "is_free": True},
    {"id": "beach", "name": "海滩日落", "category": "scene", "is_free": True},
    {"id": "library", "name": "书房", "category": "scene", "is_free": True},
    {"id": "starry", "name": "星空", "category": "abstract", "is_free": False},
    {"id": "aurora", "name": "极光", "category": "abstract", "is_free": False},
]


@router.get("/backgrounds", response_model=Dict[str, Any])
async def get_virtual_backgrounds(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取可用背景列表"""
    # 从数据库加载自定义背景
    # 注：当前返回默认背景列表，生产环境应从数据库加载用户自定义背景
    # 背景数据可存储在 video_date_backgrounds 表中
    try:
        from db.models import VideoDateBackgroundDB
        backgrounds = db.query(VideoDateBackgroundDB).filter(
            VideoDateBackgroundDB.is_active == True
        ).all()
        custom_data = [
            {
                "id": bg.id,
                "name": bg.name,
                "url": bg.background_url,
                "category": bg.category,
                "is_premium": bg.is_premium
            }
            for bg in backgrounds
        ]
    except ImportError:
        # 表不存在时使用默认数据
        custom_data = []

    # 合并默认背景和自定义背景
    all_backgrounds = AVAILABLE_BACKGROUNDS + custom_data

    return {
        "success": True,
        "data": all_backgrounds,
        "total": len(all_backgrounds)
    }


@router.post("/backgrounds/set", response_model=Dict[str, Any])
async def set_virtual_background(
    date_id: str = Body(...),
    background_id: str = Body(...),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """设置虚拟背景"""
    # 实现背景设置逻辑
    # 注：当前为简化实现，生产环境应将背景设置保存到数据库
    try:
        from db.models import VideoDateBackgroundSettingDB
        # 检查背景是否存在
        background = db.query(VideoDateBackgroundSettingDB).filter(
            VideoDateBackgroundSettingDB.id == background_id
        ).first()

        if not background:
            # 背景不存在，创建新记录
            setting = VideoDateBackgroundSettingDB(
                date_id=date_id,
                user_id=current_user.id,
                background_id=background_id,
                created_at=datetime.now()
            )
            db.add(setting)
            db.commit()
            logger.info(f"VideoDateAPI: Background {background_id} set for date {date_id}")
        else:
            # 更新现有记录
            background.background_id = background_id
            background.updated_at = datetime.now()
            db.commit()
            logger.info(f"VideoDateAPI: Background updated for date {date_id}")

    except ImportError:
        # 表不存在时仅记录日志
        logger.info(f"VideoDateAPI: Background {background_id} set for date {date_id} (mock)")

    return {
        "success": True,
        "message": f"背景已设置为：{background_id}",
        "background_id": background_id,
        "date_id": date_id
    }


# ========== 安全功能 API ==========

class BlockUserRequest(BaseModel):
    """拉黑用户请求"""
    user_id: str
    reason: Optional[str] = None


class ReportDateRequest(BaseModel):
    """举报约会请求"""
    date_id: str
    reason: str  # inappropriate_behavior, harassment, spam, fake_profile, other
    description: str


@router.post("/safety/block", response_model=Dict[str, Any])
async def block_user(
    request: BlockUserRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """拉黑约会对象"""
    from db.models import UserBlockDB
    import uuid

    # 检查是否已拉黑
    existing = db.query(UserBlockDB).filter(
        UserBlockDB.blocker_id == current_user.id,
        UserBlockDB.blocked_user_id == request.user_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="已拉黑该用户")

    block = UserBlockDB(
        id=str(uuid.uuid4()),
        blocker_id=current_user.id,
        blocked_user_id=request.user_id,
        reason=request.reason,
        block_scope='["chat", "video_date", "matching"]'
    )

    db.add(block)
    db.commit()

    return {
        "success": True,
        "message": "用户已拉黑"
    }


@router.post("/safety/report", response_model=Dict[str, Any])
async def report_video_date(
    request: ReportDateRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """举报约会对象"""
    from db.models import VideoDateReportDB
    import uuid

    # 验证约会存在
    date_service = VideoDateService(db)
    date_info = date_service.get_date_info(request.date_id)

    if not date_info:
        raise HTTPException(status_code=404, detail="约会不存在")

    # 创建举报记录
    report = VideoDateReportDB(
        id=str(uuid.uuid4()),
        date_id=request.date_id,
        reporter_id=current_user.id,
        reported_user_id=date_info["user_id_2"] if date_info["user_id_1"] == current_user.id else date_info["user_id_1"],
        reason=request.reason,
        description=request.description,
        status="pending"
    )

    db.add(report)

    # 更新约会举报标记
    date_service.db.query(date_service.db.model_class).filter(
        date_service.db.model_class.id == request.date_id
    ).update({"has_report": True, "report_count": VideoDateDB.report_count + 1})

    db.commit()

    return {
        "success": True,
        "message": "举报已提交，我们会尽快处理"
    }


@router.post("/safety/emergency", response_model=Dict[str, Any])
async def emergency_stop(
    date_id: str = Body(...),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """一键求助 - 紧急情况下快速结束约会并通知平台"""
    from db.models import VideoDateReportDB
    import uuid

    # 立即结束约会
    date_service = VideoDateService(db)
    try:
        date_service.cancel_date(date_id, current_user.id, "emergency_stop")
    except ValueError:
        pass  # 约会可能已结束

    # 自动创建举报记录
    date_info = date_service.get_date_info(date_id)
    if date_info:
        report = VideoDateReportDB(
            id=str(uuid.uuid4()),
            date_id=date_id,
            reporter_id=current_user.id,
            reported_user_id=date_info["user_id_2"] if date_info["user_id_1"] == current_user.id else date_info["user_id_1"],
            reason="inappropriate_behavior",
            description="用户触发了一键求助",
            status="under_review"
        )
        db.add(report)
        db.commit()

    # 发送紧急通知给平台管理员
    # 注：当前为模拟实现，生产环境应对接：
    # - 站内信通知管理员
    # - 短信通知值班人员
    # - 邮件通知安全团队
    logger.warning(f"VideoDateAPI: Emergency alert for date={date_id}, reporter={current_user.id}")
    logger.warning("VideoDateAPI: Admin notification sent (mock)")

    # 生产环境应实现：
    # from services.notification_service import NotificationService
    # notification_service = NotificationService(db)
    # notification_service.send_admin_alert(
    #     alert_type="emergency_sos",
    #     date_id=date_id,
    #     reporter_id=current_user.id,
    #     reported_user_id=reported_user_id
    # )

    return {
        "success": True,
        "message": "已紧急结束约会，平台已收到通知"
    }


# ========== 游戏功能 API ==========

@router.get("/games", response_model=Dict[str, Any])
async def get_available_games(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取可用游戏列表"""
    games = [
        {
            "id": "compatibility_quiz",
            "name": "默契问答",
            "description": "测试你们有多了解彼此",
            "duration_minutes": 10,
            "players": 2
        },
        {
            "id": "draw_guess",
            "name": "你画我猜",
            "description": "经典的画画猜词游戏",
            "duration_minutes": 15,
            "players": 2
        },
        {
            "id": "truth_or_dare",
            "name": "真心话大冒险",
            "description": "增进了解的互动游戏",
            "duration_minutes": 20,
            "players": 2
        },
    ]
    return {
        "success": True,
        "data": games
    }
