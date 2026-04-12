"""
Agent 自主权管控 API

Values 功能接口：
- 获取/设置 AI 介入等级
- 查看介入历史
- 测试介入策略
"""
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from utils.logger import logger
from auth.jwt import get_current_user
from services.agent_intervention_service import agent_intervention_service

router = APIRouter(prefix="/api/agent/intervention", tags=["agent-intervention"])


# ============= 请求/响应模型 =============

class InterventionLevelRequest(BaseModel):
    """介入等级设置请求"""
    level: str = Field(..., description="介入等级：silent/private/suggestion/active/emergency")


class InterventionLevelResponse(BaseModel):
    """介入等级响应"""
    success: bool
    data: Dict
    message: Optional[str] = None


class InterventionCheckRequest(BaseModel):
    """介入检查请求"""
    event_type: str = Field(..., description="事件类型")
    event_data: Dict = Field(default_factory=dict, description="事件数据")


class InterventionCheckResponse(BaseModel):
    """介入检查响应"""
    success: bool
    data: Optional[Dict]
    message: Optional[str] = None


class InterventionHistoryResponse(BaseModel):
    """介入历史响应"""
    success: bool
    data: List[Dict]
    total: int


# ============= API 端点 =============

@router.get("/settings", response_model=InterventionLevelResponse)
async def get_intervention_settings(current_user: dict = Depends(get_current_user)):
    """
    获取我的 AI 介入设置

    返回用户当前的 AI 介入等级和描述
    """
    user_id = current_user.get("user_id")

    try:
        settings = agent_intervention_service.get_user_settings(user_id)
        return InterventionLevelResponse(
            success=True,
            data=settings,
            message=f"当前 AI 介入等级：{settings['intervention_level_name']}"
        )
    except Exception as e:
        logger.error(f"Failed to get intervention settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings", response_model=InterventionLevelResponse)
async def set_intervention_settings(
    request: InterventionLevelRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    设置我的 AI 介入等级

    可选等级：
    - silent: 仅在紧急情况下提醒
    - private: 适度提醒（默认）
    - suggestion: 主动提供建议（推荐）
    - active: 全方位指导（适合恋爱新手）
    - emergency: 仅紧急情况干预
    """
    user_id = current_user.get("user_id")

    try:
        success, message = agent_intervention_service.set_user_intervention_level(
            user_id,
            request.level
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return InterventionLevelResponse(
            success=True,
            data={"level": request.level},
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set intervention level: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check", response_model=InterventionCheckResponse)
async def check_intervention(
    request: InterventionCheckRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    检查介入策略（测试用）

    用于预览某类事件会触发什么级别的介入
    """
    user_id = current_user.get("user_id")

    try:
        config = agent_intervention_service.check_intervention(
            user_id,
            request.event_type,
            request.event_data
        )

        if config is None:
            return InterventionCheckResponse(
                success=True,
                data=None,
                message="当前设置下，此类事件不会触发介入"
            )

        return InterventionCheckResponse(
            success=True,
            data=config,
            message=f"将触发{config['action']}级别的介入"
        )
    except Exception as e:
        logger.error(f"Failed to check intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_intervention(
    event_type: str = Body(..., embed=True),
    event_data: Dict = Body(default_factory=dict, embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    执行介入（管理员接口）

    用于手动触发 AI 介入
    """
    user_id = current_user.get("user_id")

    try:
        # 检查是否需要介入
        config = agent_intervention_service.check_intervention(
            user_id,
            event_type,
            event_data
        )

        if config is None:
            return {
                "success": True,
                "message": "当前设置下无需介入，已记录事件",
                "action_taken": "log_only"
            }

        # 执行介入
        success, message = agent_intervention_service.execute_intervention(
            user_id,
            config
        )

        return {
            "success": success,
            "message": message,
            "action_taken": config.get("action"),
            "intervention_level": config.get("level")
        }
    except Exception as e:
        logger.error(f"Failed to execute intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=InterventionHistoryResponse)
async def get_intervention_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    获取介入历史

    返回 AI 介入的历史记录
    """
    user_id = current_user.get("user_id")

    try:
        history = agent_intervention_service.get_intervention_history(
            user_id,
            limit,
            offset
        )
        return InterventionHistoryResponse(
            success=True,
            data=history,
            total=len(history)
        )
    except Exception as e:
        logger.error(f"Failed to get intervention history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/levels")
async def get_intervention_levels():
    """
    获取所有可用的介入等级说明
    """
    return {
        "success": True,
        "data": {
            "silent": {
                "level": 0,
                "name": "minimal",
                "description": "仅在紧急情况下提醒（如安全风险）"
            },
            "private": {
                "level": 1,
                "name": "balanced",
                "description": "适度提醒（默认）"
            },
            "suggestion": {
                "level": 2,
                "name": "proactive",
                "description": "主动提供建议（推荐）"
            },
            "active": {
                "level": 3,
                "name": "intensive",
                "description": "全方位指导（适合恋爱新手）"
            },
            "emergency": {
                "level": 4,
                "name": "emergency",
                "description": "仅紧急情况干预"
            }
        }
    }
