"""
分享裂变系统 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from sqlalchemy.orm import Session

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.product import (
    ShareInvite, ShareRewardRule, ShareType,
    ShareLinkGenerateRequest, InviteConvertRequest
)
from services.share_service import ShareService
from config.database import get_db

router = APIRouter(prefix="/api/share", tags=["分享裂变"])


# ========== 分享链接生成 ==========

@router.post("/generate-link", summary="生成分享链接")
async def generate_share_link(
    request: ShareLinkGenerateRequest,
    db: Session = Depends(get_db)
):
    """生成分享链接/邀请码"""
    service = ShareService(db)
    result = service.generate_share_link(
        request.user_id,
        request.share_type.value,
        request.related_id
    )
    return result


# ========== 邀请转化 ==========

@router.post("/convert", summary="邀请转化")
async def convert_invite(
    request: InviteConvertRequest,
    db: Session = Depends(get_db)
):
    """邀请转化（被邀请人完成指定行为）"""
    service = ShareService(db)
    result = service.convert_invite(
        request.invite_code,
        request.invitee_id,
        request.order_amount or 0.0
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ========== 奖励规则管理 ==========

@router.post("/reward-rules", response_model=ShareRewardRule, summary="创建奖励规则")
async def create_reward_rule(
    rule_data: dict,
    db: Session = Depends(get_db)
):
    """创建分享奖励规则"""
    service = ShareService(db)
    try:
        return service.create_reward_rule(rule_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reward-rules", response_model=List[ShareRewardRule], summary="获取奖励规则列表")
async def list_reward_rules(
    active_only: bool = Query(True, description="是否仅获取启用的规则"),
    share_type: Optional[str] = Query(None, description="分享类型过滤：app/group/coupon"),
    db: Session = Depends(get_db)
):
    """获取分享奖励规则列表"""
    service = ShareService(db)
    return service.list_reward_rules(active_only, share_type)


@router.get("/reward-rules/{rule_id}", response_model=ShareRewardRule, summary="获取奖励规则详情")
async def get_reward_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """获取单个奖励规则详情"""
    service = ShareService(db)
    rule = service.get_reward_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="奖励规则不存在")
    return rule


@router.put("/reward-rules/{rule_id}", response_model=ShareRewardRule, summary="更新奖励规则")
async def update_reward_rule(
    rule_id: str,
    updates: dict,
    db: Session = Depends(get_db)
):
    """更新奖励规则"""
    service = ShareService(db)
    rule = service.update_reward_rule(rule_id, updates)
    if not rule:
        raise HTTPException(status_code=404, detail="奖励规则不存在")
    return rule


# ========== 邀请记录查询 ==========

@router.get("/invites/{invite_code}", response_model=ShareInvite, summary="获取邀请记录")
async def get_invite_record(
    invite_code: str,
    db: Session = Depends(get_db)
):
    """获取邀请记录详情"""
    service = ShareService(db)
    invite = service.get_invite_record(invite_code)
    if not invite:
        raise HTTPException(status_code=404, detail="邀请记录不存在")
    return invite


@router.get("/users/{user_id}/invites", response_model=List[ShareInvite], summary="获取用户邀请记录")
async def get_user_invites(
    user_id: str,
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """获取用户的邀请记录列表"""
    service = ShareService(db)
    return service.get_user_invites(user_id, limit)


@router.get("/users/{user_id}/stats", summary="获取用户邀请统计")
async def get_user_invite_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """获取用户邀请统计数据"""
    service = ShareService(db)
    return service.get_user_invite_stats(user_id)
