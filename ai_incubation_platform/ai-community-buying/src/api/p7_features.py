"""
P7 阶段 - 游戏化运营和砍价玩法 API 路由

包含:
1. 成就系统 API
2. 排行榜 API
3. 砍价玩法 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from config.database import get_db
from services.p7_services import AchievementService, LeaderboardService, BargainService
from models.p7_entities import (
    AchievementType, AchievementTier, AchievementStatus,
    LeaderboardType, LeaderboardPeriod, BargainStatus
)
# AchievementBadge 在 p7_entities 中定义，这里不需要导入
from core.exceptions import AppException

router = APIRouter(prefix="/api/p7", tags=["P7 游戏化运营"])

# ====================  成就系统 API  ====================

achievement_router = APIRouter(prefix="/achievements", tags=["成就系统"])


@achievement_router.get("/definitions", response_model=List[Dict])
def get_achievement_definitions(
    is_active: bool = Query(True, description="是否只显示有效的成就"),
    db: Session = Depends(get_db)
):
    """获取所有成就定义"""
    service = AchievementService(db)
    achievements = service.get_all_achievements(is_active)

    return [
        {
            "id": a.id,
            "achievement_code": a.achievement_code,
            "achievement_name": a.achievement_name,
            "achievement_type": a.achievement_type.value,
            "tier": a.tier.value,
            "condition_description": a.condition_description,
            "condition_target": a.condition_target,
            "reward_type": a.reward_type,
            "reward_value": a.reward_value,
            "reward_description": a.reward_description,
            "icon_url": a.icon_url,
            "description": a.description,
            "is_hidden": a.is_hidden
        }
        for a in achievements
    ]


@achievement_router.get("/my", response_model=List[Dict])
def get_my_achievements(
    user_id: str = Query(..., description="用户 ID"),
    status: Optional[str] = Query(None, description="成就状态筛选"),
    db: Session = Depends(get_db)
):
    """获取我的成就列表"""
    service = AchievementService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    status_enum = AchievementStatus(status) if status else None
    achievements = service.get_user_achievements(user_id, status_enum)

    return [
        {
            "achievement": {
                "id": a["achievement"].id,
                "achievement_code": a["achievement"].achievement_code,
                "achievement_name": a["achievement"].achievement_name,
                "tier": a["achievement"].tier.value,
                "icon_url": a["achievement"].icon_url
            },
            "progress": a["user_achievement"].current_progress,
            "target": a["user_achievement"].target_progress,
            "progress_percent": a["progress_percent"],
            "status": a["user_achievement"].status.value,
            "unlocked_at": a["user_achievement"].unlocked_at.isoformat() if a["user_achievement"].unlocked_at else None,
            "claimed_at": a["user_achievement"].claimed_at.isoformat() if a["user_achievement"].claimed_at else None
        }
        for a in achievements
    ]


@achievement_router.get("/badges", response_model=List[Dict])
def get_my_badges(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """获取我的徽章列表"""
    service = AchievementService(db)
    badges = service.get_user_badges(user_id)

    return [
        {
            "id": b.id,
            "badge_name": b.badge_name,
            "badge_icon": b.badge_icon,
            "tier": b.tier.value,
            "is_equipped": b.is_equipped,
            "equipped_at": b.equipped_at.isoformat() if b.equipped_at else None
        }
        for b in badges
    ]


@achievement_router.post("/claim/{achievement_id}")
def claim_achievement_reward(
    achievement_id: str,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """领取成就奖励"""
    service = AchievementService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    reward, success = service.claim_achievement_reward(user_id, achievement_id)

    if not success:
        raise AppException(
            code="ACHIEVEMENT_CLAIM_FAILED",
            message=reward.get("error", "领取奖励失败"),
            status=400
        )

    return {
        "success": True,
        "message": "奖励领取成功",
        "reward": reward
    }


@achievement_router.post("/check-progress")
def check_achievement_progress(
    user_id: str = Query(..., description="用户 ID"),
    achievement_type: str = Query(..., description="成就类型"),
    check_all: bool = Query(False, description="是否检查所有成就"),
    db: Session = Depends(get_db)
):
    """检查并更新成就进度"""
    service = AchievementService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    try:
        type_enum = AchievementType(achievement_type)
    except ValueError:
        raise AppException(
            code="INVALID_ACHIEVEMENT_TYPE",
            message=f"无效的成就类型：{achievement_type}",
            status=400
        )

    # 获取当前进度并检查
    total_progress = service._get_user_total_progress(user_id, type_enum)
    unlocked = service.check_and_unlock_achievements(user_id, type_enum, total_progress, check_all)

    return {
        "success": True,
        "current_progress": total_progress,
        "newly_unlocked": [
            {
                "achievement_name": u["achievement"].achievement_name,
                "tier": u["achievement"].tier.value,
                "message": u["message"]
            }
            for u in unlocked
        ]
    }


# ====================  排行榜 API  ====================

leaderboard_router = APIRouter(prefix="/leaderboards", tags=["排行榜"])


@leaderboard_router.get("/", response_model=List[Dict])
def get_leaderboard(
    leaderboard_type: str = Query(..., description="排行榜类型"),
    period: str = Query(..., description="周期"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """获取排行榜数据"""
    service = LeaderboardService(db)

    try:
        type_enum = LeaderboardType(leaderboard_type)
        period_enum = LeaderboardPeriod(period)
    except ValueError as e:
        raise AppException(
            code="INVALID_LEADERBOARD_PARAM",
            message=f"无效的参数：{str(e)}",
            status=400
        )

    rankings = service.get_leaderboard(type_enum, period_enum, limit)

    return rankings


@leaderboard_router.get("/my-rank")
def get_my_rank(
    user_id: str = Query(..., description="用户 ID"),
    leaderboard_type: str = Query(..., description="排行榜类型"),
    period: str = Query(..., description="周期"),
    db: Session = Depends(get_db)
):
    """获取我的排名"""
    service = LeaderboardService(db)

    try:
        type_enum = LeaderboardType(leaderboard_type)
        period_enum = LeaderboardPeriod(period)
    except ValueError as e:
        raise AppException(
            code="INVALID_LEADERBOARD_PARAM",
            message=f"无效的参数：{str(e)}",
            status=400
        )

    rank = service.get_user_rank(user_id, type_enum, period_enum)

    if not rank:
        return {
            "success": True,
            "message": "暂无排名数据",
            "rank": None
        }

    return {
        "success": True,
        "rank": rank
    }


# ====================  砍价玩法 API  ====================

bargain_router = APIRouter(prefix="/bargain", tags=["砍价玩法"])


@bargain_router.get("/activities", response_model=List[Dict])
def get_bargain_activities(
    db: Session = Depends(get_db)
):
    """获取进行中的砍价活动"""
    service = BargainService(db)
    activities = service.get_active_activities()

    return [
        {
            "id": a.id,
            "activity_name": a.activity_name,
            "product_id": a.product_id,
            "original_price": float(a.original_price),
            "floor_price": float(a.floor_price),
            "initial_price": float(a.initial_price),
            "max_bargain_count": a.max_bargain_count,
            "required_bargain_count": a.required_bargain_count,
            "start_time": a.start_time.isoformat(),
            "end_time": a.end_time.isoformat(),
            "duration_hours": a.duration_hours,
            "total_stock": a.total_stock,
            "used_stock": a.used_stock,
            "remaining_stock": a.total_stock - a.used_stock,
            "status": a.status,
            "description": a.description,
            "image_url": a.image_url
        }
        for a in activities
    ]


@bargain_router.get("/activities/{activity_id}")
def get_bargain_activity_detail(
    activity_id: str,
    db: Session = Depends(get_db)
):
    """获取砍价活动详情"""
    service = BargainService(db)
    activity = service.get_activity_by_id(activity_id)

    if not activity:
        raise AppException(
            code="BARGAIN_ACTIVITY_NOT_FOUND",
            message="砍价活动不存在",
            status=404
        )

    return {
        "id": activity.id,
        "activity_name": activity.activity_name,
        "product_id": activity.product_id,
        "original_price": float(activity.original_price),
        "floor_price": float(activity.floor_price),
        "max_bargain_count": activity.max_bargain_count,
        "min_bargain_amount": float(activity.min_bargain_amount),
        "max_bargain_amount": float(activity.max_bargain_amount),
        "start_time": activity.start_time.isoformat(),
        "end_time": activity.end_time.isoformat(),
        "description": activity.description,
        "image_url": activity.image_url
    }


@bargain_router.post("/start")
def start_bargain(
    activity_id: str = Query(..., description="活动 ID"),
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """发起砍价"""
    service = BargainService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    bargain_order, error = service.create_bargain_order(activity_id, user_id)

    if error:
        raise AppException(
            code="BARGAIN_START_FAILED",
            message=error,
            status=400
        )

    return {
        "success": True,
        "message": "砍价发起成功",
        "data": {
            "id": bargain_order.id,
            "bargain_no": bargain_order.bargain_no,
            "activity_id": bargain_order.activity_id,
            "product_id": bargain_order.product_id,
            "original_price": float(bargain_order.original_price),
            "current_price": float(bargain_order.current_price),
            "floor_price": float(bargain_order.floor_price),
            "bargain_count": bargain_order.bargain_count,
            "remaining_bargains": bargain_order.remaining_bargains,
            "status": bargain_order.status.value,
            "started_at": bargain_order.started_at.isoformat(),
            "expires_at": bargain_order.expires_at.isoformat()
        }
    }


@bargain_router.get("/my-orders", response_model=List[Dict])
def get_my_bargain_orders(
    user_id: str = Query(..., description="用户 ID"),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: Session = Depends(get_db)
):
    """获取我的砍价订单"""
    from sqlalchemy import and_

    query = db.query(BargainOrderEntity).filter(
        BargainOrderEntity.user_id == user_id
    )

    if status:
        try:
            status_enum = BargainStatus(status)
            query = query.filter(BargainOrderEntity.status == status_enum)
        except ValueError:
            pass

    orders = query.order_by(BargainOrderEntity.created_at.desc()).all()

    return [
        {
            "id": o.id,
            "bargain_no": o.bargain_no,
            "activity_id": o.activity_id,
            "product_id": o.product_id,
            "original_price": float(o.original_price),
            "current_price": float(o.current_price),
            "floor_price": float(o.floor_price),
            "bargain_count": o.bargain_count,
            "remaining_bargains": o.remaining_bargains,
            "status": o.status.value,
            "started_at": o.started_at.isoformat(),
            "expires_at": o.expires_at.isoformat(),
            "completed_at": o.completed_at.isoformat() if o.completed_at else None,
            "order_id": o.order_id
        }
        for o in orders
    ]


@bargain_router.get("/orders/{order_id}")
def get_bargain_order_detail(
    order_id: str,
    db: Session = Depends(get_db)
):
    """获取砍价订单详情"""
    service = BargainService(db)
    order = service.get_bargain_order(order_id)

    if not order:
        raise AppException(
            code="BARGAIN_ORDER_NOT_FOUND",
            message="砍价订单不存在",
            status=404
        )

    # 获取助力记录
    helps = service.get_bargain_helps(order_id)

    return {
        "id": order.id,
        "bargain_no": order.bargain_no,
        "activity_id": order.activity_id,
        "product_id": order.product_id,
        "user_id": order.user_id,
        "original_price": float(order.original_price),
        "current_price": float(order.current_price),
        "floor_price": float(order.floor_price),
        "bargain_count": order.bargain_count,
        "remaining_bargains": order.remaining_bargains,
        "status": order.status.value,
        "started_at": order.started_at.isoformat(),
        "expires_at": order.expires_at.isoformat(),
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "helpers": [
            {
                "helper_user_id": h.helper_user_id,
                "bargain_amount": float(h.bargain_amount),
                "price_before": float(h.price_before),
                "price_after": float(h.price_after),
                "created_at": h.created_at.isoformat()
            }
            for h in helps
        ]
    }


@bargain_router.post("/help")
def help_bargain(
    bargain_order_id: str = Query(..., description="砍价订单 ID"),
    helper_user_id: str = Query(..., description="助力者用户 ID"),
    db: Session = Depends(get_db)
):
    """帮助砍价"""
    service = BargainService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", helper_user_id)

    result, error = service.help_bargain(bargain_order_id, helper_user_id)

    if error:
        raise AppException(
            code="BARGAIN_HELP_FAILED",
            message=error,
            status=400
        )

    return {
        "success": True,
        "message": "砍价成功" if not result["is_success"] else "恭喜！砍价成功！",
        "data": result
    }


@bargain_router.post("/orders/{order_id}/complete")
def complete_bargain_order(
    order_id: str,
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """完成砍价订单 (生成正式订单)"""
    service = BargainService(db)
    service.set_request_context(f"req_{datetime.now().timestamp()}", user_id)

    success, error = service.complete_bargain_order(order_id, user_id)

    if not success:
        raise AppException(
            code="BARGAIN_COMPLETE_FAILED",
            message=error,
            status=400
        )

    return {
        "success": True,
        "message": "砍价成功，订单已生成"
    }


# 导入实体以便在 API 中使用
from models.p7_entities import BargainOrderEntity
