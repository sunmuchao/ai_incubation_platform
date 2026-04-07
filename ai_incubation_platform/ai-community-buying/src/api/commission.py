"""
佣金系统 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from sqlalchemy.orm import Session

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.product import CommissionRule, CommissionRecord, OrganizerProfile, CommissionRuleCreate
from services.commission_service import CommissionService
from config.database import get_db

router = APIRouter(prefix="/api/commission", tags=["佣金系统"])


# ========== 佣金规则管理 ==========

@router.post("/rules", response_model=CommissionRule, summary="创建佣金规则")
async def create_commission_rule(
    rule_data: CommissionRuleCreate,
    db: Session = Depends(get_db)
):
    """创建新的佣金规则"""
    service = CommissionService(db)
    try:
        return service.create_rule(rule_data.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rules", response_model=List[CommissionRule], summary="获取佣金规则列表")
async def list_commission_rules(
    active_only: bool = Query(True, description="是否仅获取启用的规则"),
    db: Session = Depends(get_db)
):
    """获取佣金规则列表"""
    service = CommissionService(db)
    return service.list_rules(active_only)


@router.get("/rules/{rule_id}", response_model=CommissionRule, summary="获取佣金规则详情")
async def get_commission_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """获取单个佣金规则详情"""
    service = CommissionService(db)
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="佣金规则不存在")
    return rule


@router.put("/rules/{rule_id}", response_model=CommissionRule, summary="更新佣金规则")
async def update_commission_rule(
    rule_id: str,
    updates: dict,
    db: Session = Depends(get_db)
):
    """更新佣金规则"""
    service = CommissionService(db)
    rule = service.update_rule(rule_id, updates)
    if not rule:
        raise HTTPException(status_code=404, detail="佣金规则不存在")
    return rule


# ========== 团长档案管理 ==========

@router.get("/organizers/{user_id}", response_model=OrganizerProfile, summary="获取团长档案")
async def get_organizer_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    """获取团长档案信息"""
    service = CommissionService(db)
    profile = service.get_organizer_profile(user_id)
    if not profile:
        # 自动创建档案
        profile = service.create_organizer_profile(user_id)
    return profile


@router.get("/organizers", response_model=List[OrganizerProfile], summary="获取团长排行榜")
async def list_organizers(
    level: Optional[str] = Query(None, description="团长等级过滤：normal/gold/diamond"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """获取团长列表，按佣金排序"""
    service = CommissionService(db)
    return service.list_organizer_profiles(level, limit)


# ========== 佣金记录 ==========

@router.get("/organizers/{user_id}/records", response_model=List[CommissionRecord], summary="获取团长佣金记录")
async def get_organizer_commission_records(
    user_id: str,
    status: Optional[str] = Query(None, description="佣金状态过滤：pending/settled/withdrawn"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """获取团长的佣金记录列表"""
    service = CommissionService(db)
    return service.list_commission_records(user_id, status, limit)


# ========== 佣金结算 ==========

@router.post("/settle/{group_buy_id}", summary="结算团购佣金")
async def settle_group_commission(
    group_buy_id: str,
    db: Session = Depends(get_db)
):
    """结算团购佣金（团购成功后调用）"""
    service = CommissionService(db)
    record = service.settle_commission(group_buy_id)
    if not record:
        raise HTTPException(status_code=400, detail="佣金结算失败，请检查团购状态")
    return {
        "message": "佣金结算成功",
        "commission_amount": record.commission_amount,
        "status": record.status
    }


# ========== 佣金提现 ==========

@router.post("/withdraw", summary="佣金提现")
async def withdraw_commission(
    organizer_id: str = Query(..., description="团长 ID"),
    amount: float = Query(..., description="提现金额"),
    db: Session = Depends(get_db)
):
    """申请佣金提现"""
    service = CommissionService(db)
    result = service.withdraw_commission(organizer_id, amount)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
