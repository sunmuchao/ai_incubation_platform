"""
AI 行为信用分 API

# FUTURE: 信贷功能，暂不启用 - 前端未集成

P0 功能接口：
- 获取信用分
- 查看信用记录
- 提交申诉
"""
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from typing import Dict, List, Optional
from pydantic import BaseModel
from utils.logger import logger
from auth.jwt import get_current_user
from services.behavior_credit_service import behavior_credit_service

router = APIRouter(prefix="/api/credit", tags=["credit"])


# ============= 请求/响应模型 =============

class CreditInfoResponse(BaseModel):
    """信用信息响应"""
    success: bool
    data: Dict
    message: Optional[str] = None


class CreditHistoryResponse(BaseModel):
    """信用记录历史响应"""
    success: bool
    data: List[Dict]
    total: int


class AppealRequest(BaseModel):
    """申诉请求"""
    event_id: str
    appeal_reason: str


class AppealResponse(BaseModel):
    """申诉响应"""
    success: bool
    message: str


class RestrictionsResponse(BaseModel):
    """限制检查响应"""
    success: bool
    data: Dict
    message: Optional[str] = None


# ============= API 端点 =============

@router.get("/score", response_model=CreditInfoResponse)
async def get_credit_score(current_user: dict = Depends(get_current_user)):
    """
    获取我的信用分

    返回用户的当前信用分数、等级和详细信息
    """
    user_id = current_user.get("user_id")

    try:
        info = behavior_credit_service.get_credit_info(user_id)
        return CreditInfoResponse(
            success=True,
            data=info,
            message=f"当前信用分为{info['credit_score']}，等级为{info['credit_level']}"
        )
    except Exception as e:
        logger.error(f"Failed to get credit score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=CreditHistoryResponse)
async def get_credit_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    获取信用记录历史

    返回用户的所有信用记录事件
    """
    user_id = current_user.get("user_id")

    try:
        history = behavior_credit_service.get_credit_history(user_id, limit, offset)
        return CreditHistoryResponse(
            success=True,
            data=history,
            total=len(history)
        )
    except Exception as e:
        logger.error(f"Failed to get credit history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{target_user_id}")
async def get_other_user_credit(
    target_user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    查看他人信用等级

    仅显示信用等级，不显示具体分数
    """
    try:
        info = behavior_credit_service.get_credit_info(target_user_id)
        # 只返回等级和描述，不显示具体分数
        return {
            "success": True,
            "data": {
                "user_id": target_user_id,
                "credit_level": info["credit_level"],
                "level_description": info["level_description"],
                "is_recommended": info["credit_level"] in ["S", "A", "B"]
            }
        }
    except Exception as e:
        logger.error(f"Failed to get other user credit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/appeal", response_model=AppealResponse)
async def submit_appeal(
    request: AppealRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    提交申诉

    对信用记录有异议时可提交申诉
    """
    user_id = current_user.get("user_id")

    try:
        success, message = behavior_credit_service.submit_appeal(
            request.event_id,
            user_id,
            request.appeal_reason
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return AppealResponse(
            success=True,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit appeal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/restrictions/check", response_model=RestrictionsResponse)
async def check_restrictions(current_user: dict = Depends(get_current_user)):
    """
    检查我的限制状态

    返回当前用户因信用分导致的功能限制
    """
    user_id = current_user.get("user_id")

    try:
        restrictions = behavior_credit_service.check_restrictions(user_id)
        return RestrictionsResponse(
            success=True,
            data=restrictions,
            message=None
        )
    except Exception as e:
        logger.error(f"Failed to check restrictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/event/record")
async def record_behavior_event(
    event_type: str = Body(..., embed=True),
    description: str = Body(..., embed=True),
    target_user_id: Optional[str] = Body(default=None, embed=True),
    evidence: Optional[Dict] = Body(default=None, embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    记录行为事件（管理员接口）

    用于手动记录用户行为事件
    """
    # 这里可以添加管理员权限检查
    user_id = target_user_id or current_user.get("user_id")

    try:
        success, message, score_change = behavior_credit_service.record_event(
            user_id=user_id,
            event_type=event_type,
            description=description,
            source="manual",
            evidence=evidence
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": message,
            "score_change": score_change
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record behavior event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_credit_stats(current_user: dict = Depends(get_current_user)):
    """
    获取信用统计（管理员接口）

    返回平台整体的信用分布统计
    """
    try:
        stats = behavior_credit_service.get_credit_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get credit stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
