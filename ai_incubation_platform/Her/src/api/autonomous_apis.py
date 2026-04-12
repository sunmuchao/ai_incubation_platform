"""
自主代理引擎 API

提供心跳状态查询和用户推送偏好设置功能。

核心功能：
- 心跳状态查询：查看心跳调度器运行状态、规则执行历史
- 推送偏好设置：用户自定义推送开关、免打扰时段、主动程度
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from db.database import get_db
from auth.jwt import get_current_user
from db.autonomous_models import UserPushPreferencesDB, HeartbeatRuleStateDB, PushHistoryDB
from utils.logger import logger


router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])


# ============= Pydantic 模型 =============

class PushPreferencesRequest(BaseModel):
    """推送偏好设置请求"""
    push_enabled: Optional[bool] = Field(None, description="是否开启推送")
    proactive_level: Optional[str] = Field(None, description="主动程度：high/medium/low/none")
    quiet_hours_start: Optional[str] = Field(None, description="免打扰开始时间（HH:MM格式）")
    quiet_hours_end: Optional[str] = Field(None, description="免打扰结束时间（HH:MM格式）")
    preferred_channels: Optional[List[str]] = Field(None, description="偏好渠道")
    type_preferences: Optional[Dict[str, bool]] = Field(None, description="各类型推送开关")


class PushPreferencesResponse(BaseModel):
    """推送偏好设置响应"""
    user_id: str
    push_enabled: bool
    proactive_level: str
    quiet_hours_start: str
    quiet_hours_end: str
    preferred_channels: List[str]
    type_preferences: Dict[str, bool]
    updated_at: Optional[str] = None


class HeartbeatStatusResponse(BaseModel):
    """心跳状态响应"""
    is_running: bool
    heartbeat_interval: int
    last_heartbeat_time: Optional[str] = None
    next_heartbeat_time: Optional[str] = None
    rules_executed_count: int
    total_pushes_sent: int


class RuleStateResponse(BaseModel):
    """规则状态响应"""
    rule_name: str
    last_run_at: Optional[str]
    last_result: Optional[str]
    run_count: int
    action_count: int


class PushHistoryResponse(BaseModel):
    """推送历史响应"""
    id: str
    push_type: str
    title: Optional[str]
    message: Optional[str]
    push_status: str
    pushed_at: Optional[str]
    response_type: Optional[str]


# ============= 推送偏好设置 API =============

@router.get("/push-preferences", response_model=PushPreferencesResponse)
async def get_push_preferences(
    current_user: dict = Depends(get_current_user)
):
    """
    获取用户推送偏好设置

    返回用户的推送开关、主动程度、免打扰时段等配置
    """
    user_id = current_user["user_id"]
    logger.info(f"Getting push preferences for user: {user_id}")

    db = next(get_db())

    try:
        prefs = db.query(UserPushPreferencesDB).filter(
            UserPushPreferencesDB.user_id == user_id
        ).first()

        if not prefs:
            # 返回默认设置
            return PushPreferencesResponse(
                user_id=user_id,
                push_enabled=True,
                proactive_level="medium",
                quiet_hours_start="22:00",
                quiet_hours_end="08:00",
                preferred_channels=["push"],
                type_preferences={
                    "icebreaker": True,
                    "topic": True,
                    "activation": True,
                    "date": True,
                    "health": True
                },
                updated_at=None
            )

        return PushPreferencesResponse(
            user_id=prefs.user_id,
            push_enabled=prefs.push_enabled,
            proactive_level=prefs.proactive_level,
            quiet_hours_start=prefs.quiet_hours_start,
            quiet_hours_end=prefs.quiet_hours_end,
            preferred_channels=prefs.preferred_channels or ["push"],
            type_preferences=prefs.type_preferences or {},
            updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None
        )

    finally:
        db.close()


@router.put("/push-preferences", response_model=PushPreferencesResponse)
async def update_push_preferences(
    request: PushPreferencesRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    更新用户推送偏好设置

    用户可配置：
    - push_enabled: 是否开启推送
    - proactive_level: 主动程度（high=主动推进/medium=适中/low=仅提醒/none=完全关闭）
    - quiet_hours_start/end: 免打扰时段
    - preferred_channels: 偏好推送渠道
    - type_preferences: 各类型推送开关
    """
    user_id = current_user["user_id"]
    logger.info(f"Updating push preferences for user: {user_id}")

    db = next(get_db())

    try:
        prefs = db.query(UserPushPreferencesDB).filter(
            UserPushPreferencesDB.user_id == user_id
        ).first()

        if not prefs:
            # 创建新记录
            import uuid
            prefs = UserPushPreferencesDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                push_enabled=request.push_enabled or True,
                proactive_level=request.proactive_level or "medium",
                quiet_hours_start=request.quiet_hours_start or "22:00",
                quiet_hours_end=request.quiet_hours_end or "08:00",
                preferred_channels=request.preferred_channels or ["push"],
                type_preferences=request.type_preferences or {}
            )
            db.add(prefs)
        else:
            # 更新现有记录
            if request.push_enabled is not None:
                prefs.push_enabled = request.push_enabled
            if request.proactive_level is not None:
                # 验证主动程度
                valid_levels = ["high", "medium", "low", "none"]
                if request.proactive_level not in valid_levels:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid proactive_level. Must be one of: {valid_levels}"
                    )
                prefs.proactive_level = request.proactive_level
            if request.quiet_hours_start is not None:
                prefs.quiet_hours_start = request.quiet_hours_start
            if request.quiet_hours_end is not None:
                prefs.quiet_hours_end = request.quiet_hours_end
            if request.preferred_channels is not None:
                prefs.preferred_channels = request.preferred_channels
            if request.type_preferences is not None:
                prefs.type_preferences = request.type_preferences

        db.commit()
        db.refresh(prefs)

        logger.info(f"Push preferences updated for user: {user_id}")

        return PushPreferencesResponse(
            user_id=prefs.user_id,
            push_enabled=prefs.push_enabled,
            proactive_level=prefs.proactive_level,
            quiet_hours_start=prefs.quiet_hours_start,
            quiet_hours_end=prefs.quiet_hours_end,
            preferred_channels=prefs.preferred_channels or ["push"],
            type_preferences=prefs.type_preferences or {},
            updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update push preferences: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update preferences")
    finally:
        db.close()


# ============= 心跳状态查询 API =============

@router.get("/heartbeat/status", response_model=HeartbeatStatusResponse)
async def get_heartbeat_status():
    """
    获取心跳调度器状态

    返回心跳调度器的运行状态、执行统计等信息
    """
    logger.info("Getting heartbeat scheduler status")

    try:
        from agent.autonomous.scheduler import get_scheduler
        HeartbeatScheduler, _, _ = get_scheduler()
        scheduler = HeartbeatScheduler()

        status = scheduler.get_status()

        # 获取执行统计
        db = next(get_db())

        # 规则执行总数
        rules_executed = db.query(HeartbeatRuleStateDB).count()

        # 推送总数
        total_pushes = db.query(PushHistoryDB).filter(
            PushHistoryDB.push_status == "sent"
        ).count()

        # 最后心跳时间
        last_run = db.query(HeartbeatRuleStateDB).order_by(
            HeartbeatRuleStateDB.last_run_at.desc()
        ).first()

        db.close()

        return HeartbeatStatusResponse(
            is_running=status.get("is_running", False),
            heartbeat_interval=status.get("heartbeat_interval", 30),
            last_heartbeat_time=last_run.last_run_at.isoformat() if last_run and last_run.last_run_at else None,
            next_heartbeat_time=None,  # 需要计算下次心跳时间
            rules_executed_count=rules_executed,
            total_pushes_sent=total_pushes
        )

    except Exception as e:
        logger.error(f"Failed to get heartbeat status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get heartbeat status")


@router.get("/heartbeat/rules", response_model=List[RuleStateResponse])
async def get_heartbeat_rules(
    limit: int = 10
):
    """
    获取心跳规则执行状态

    返回各规则的执行历史、执行次数、结果统计
    """
    logger.info(f"Getting heartbeat rules state, limit={limit}")

    db = next(get_db())

    try:
        rules = db.query(HeartbeatRuleStateDB).order_by(
            HeartbeatRuleStateDB.last_run_at.desc()
        ).limit(limit).all()

        return [
            RuleStateResponse(
                rule_name=rule.rule_name,
                last_run_at=rule.last_run_at.isoformat() if rule.last_run_at else None,
                last_result=rule.last_result,
                run_count=rule.run_count,
                action_count=rule.action_count
            )
            for rule in rules
        ]

    finally:
        db.close()


@router.get("/push-history", response_model=List[PushHistoryResponse])
async def get_push_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    获取用户推送历史

    返回用户收到的推送记录、响应情况
    """
    user_id = current_user["user_id"]
    logger.info(f"Getting push history for user: {user_id}, limit={limit}")

    db = next(get_db())

    try:
        history = db.query(PushHistoryDB).filter(
            PushHistoryDB.user_id == user_id
        ).order_by(
            PushHistoryDB.pushed_at.desc()
        ).limit(limit).all()

        return [
            PushHistoryResponse(
                id=push.id,
                push_type=push.push_type,
                title=push.title,
                message=push.message,
                push_status=push.push_status,
                pushed_at=push.pushed_at.isoformat() if push.pushed_at else None,
                response_type=push.response_type
            )
            for push in history
        ]

    finally:
        db.close()


@router.post("/push-history/{push_id}/response")
async def record_push_response(
    push_id: str,
    response_type: str,
    action_taken: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    记录用户对推送的响应

    用于追踪推送效果，优化推送策略

    Args:
        push_id: 推送记录ID
        response_type: 响应类型（clicked/ignored/acted/dismissed）
        action_taken: 用户采取的具体行动
    """
    user_id = current_user["user_id"]
    logger.info(f"Recording push response: push_id={push_id}, user={user_id}, response={response_type}")

    db = next(get_db())

    try:
        push = db.query(PushHistoryDB).filter(
            PushHistoryDB.id == push_id,
            PushHistoryDB.user_id == user_id
        ).first()

        if not push:
            raise HTTPException(status_code=404, detail="Push record not found")

        push.response_type = response_type
        push.action_taken = action_taken
        push.responded_at = datetime.now()

        # 计算响应时间
        if push.pushed_at:
            delta = datetime.now() - push.pushed_at
            push.response_time_seconds = int(delta.total_seconds())

        # 标记转化成功
        if response_type == "acted":
            push.conversion_success = True

        db.commit()

        logger.info(f"Push response recorded: push_id={push_id}")

        return {"success": True, "message": "Response recorded"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record push response: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to record response")
    finally:
        db.close()


# ============= 主动程度说明 API =============

@router.get("/proactive-levels")
async def get_proactive_levels_info():
    """
    获取主动程度等级说明

    帮助用户理解各等级的含义，做出合适的选择
    """
    return {
        "levels": [
            {
                "name": "high",
                "label": "主动推进",
                "description": "红娘会主动帮你推进关系，频繁推送破冰建议、话题推荐、约会提醒",
                "push_frequency": "高（每日多次）",
                "suitable_for": "希望红娘积极帮忙推进的用户"
            },
            {
                "name": "medium",
                "label": "适中提醒",
                "description": "红娘会在关键时刻推送提醒，如新匹配、长时间沉默、约会安排",
                "push_frequency": "中（每日1-2次）",
                "suitable_for": "大多数用户，平衡主动与被动"
            },
            {
                "name": "low",
                "label": "仅提醒",
                "description": "红娘只在重要事件时推送，如匹配成功、约会提醒",
                "push_frequency": "低（每周1-2次）",
                "suitable_for": "不喜欢频繁打扰的用户"
            },
            {
                "name": "none",
                "label": "完全关闭",
                "description": "红娘不会主动推送任何消息，用户需主动查询",
                "push_frequency": "无",
                "suitable_for": "完全自主掌控的用户"
            }
        ]
    }


# ============= 导出 =============

__all__ = ["router"]