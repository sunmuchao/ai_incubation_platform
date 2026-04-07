"""
优惠券系统 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.product import (
    CouponTemplate, Coupon, CouponStatus, CouponType,
    CouponTemplateCreate, CouponClaimRequest, CouponUseRequest
)
from services.coupon_service import CouponService
from config.database import get_db

router = APIRouter(prefix="/api/coupons", tags=["优惠券系统"])


# ========== 优惠券模板管理 ==========

@router.post("/templates", response_model=CouponTemplate, summary="创建优惠券模板")
async def create_coupon_template(
    template_data: CouponTemplateCreate,
    db: Session = Depends(get_db)
):
    """创建新的优惠券模板"""
    service = CouponService(db)
    try:
        return service.create_template(template_data.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates", response_model=List[CouponTemplate], summary="获取优惠券模板列表")
async def list_coupon_templates(
    active_only: bool = Query(True, description="是否仅获取启用的模板"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """获取优惠券模板列表"""
    service = CouponService(db)
    return service.list_templates(active_only, limit)


@router.get("/templates/{template_id}", response_model=CouponTemplate, summary="获取优惠券模板详情")
async def get_coupon_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """获取单个优惠券模板详情"""
    service = CouponService(db)
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="优惠券模板不存在")
    return template


@router.delete("/templates/{template_id}", summary="删除优惠券模板")
async def delete_coupon_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """软删除优惠券模板（设为不活跃）"""
    service = CouponService(db)
    success = service.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="优惠券模板不存在")
    return {"message": "优惠券模板已停用"}


# ========== 优惠券领取 ==========

@router.post("/claim", summary="领取优惠券")
async def claim_coupon(
    request: CouponClaimRequest,
    db: Session = Depends(get_db)
):
    """用户领取优惠券"""
    service = CouponService(db)
    result = service.claim_coupon(request.user_id, request.template_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ========== 优惠券使用 ==========

@router.post("/use", summary="使用优惠券")
async def use_coupon(
    request: CouponUseRequest,
    db: Session = Depends(get_db)
):
    """用户使用优惠券"""
    service = CouponService(db)
    result = service.use_coupon(request.user_id, request.coupon_id, request.order_amount)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ========== 优惠券查询 ==========

@router.get("/{coupon_id}", response_model=Coupon, summary="获取优惠券详情")
async def get_coupon(
    coupon_id: str,
    db: Session = Depends(get_db)
):
    """获取单个优惠券详情"""
    service = CouponService(db)
    coupon = service.get_coupon(coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    return coupon


@router.get("/users/{user_id}", response_model=List[Coupon], summary="获取用户优惠券列表")
async def get_user_coupons(
    user_id: str,
    status: Optional[str] = Query(None, description="优惠券状态：available/used/expired"),
    limit: int = Query(50, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """获取用户的优惠券列表"""
    service = CouponService(db)
    return service.get_user_coupons(user_id, status, limit)


@router.get("/code/{code}", response_model=Coupon, summary="通过券码获取优惠券")
async def get_coupon_by_code(
    code: str,
    db: Session = Depends(get_db)
):
    """通过券码获取优惠券"""
    service = CouponService(db)
    coupon = service.get_coupon_by_code(code)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    return coupon


@router.get("/users/{user_id}/available-for-order", summary="获取订单可用优惠券")
async def get_available_coupons_for_order(
    user_id: str,
    order_amount: float = Query(..., description="订单金额"),
    product_ids: Optional[str] = Query(None, description="商品 ID 列表，逗号分隔"),
    db: Session = Depends(get_db)
):
    """获取订单可用的优惠券列表"""
    service = CouponService(db)
    products = product_ids.split(",") if product_ids else None
    return service.list_available_coupons_for_order(user_id, order_amount, products)


# ========== 管理接口 ==========

@router.post("/admin/expire-unused", summary="过期未使用的优惠券")
async def expire_unused_coupons(
    db: Session = Depends(get_db)
):
    """批量过期未使用的优惠券"""
    service = CouponService(db)
    count = service.expire_unused_coupons()
    return {"message": f"已过期 {count} 张优惠券"}
