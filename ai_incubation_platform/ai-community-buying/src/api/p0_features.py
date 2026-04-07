"""
P0 优先级功能 API 路由

包含：
1. 限时秒杀功能 (任务#13)
2. 新人专享体系 (任务#14)
3. 拼单返现机制 (任务#30)
4. 库存紧张提示 (任务#56)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from config.database import get_db
from services.flash_sale_service import FlashSaleService
from services.newbie_service import NewbieService
from services.groupbuy_cashback_service import GroupBuyCashbackService
from services.stock_alert_service import StockAlertService

logger = logging.getLogger(__name__)

# 创建路由器
flash_sale_router = APIRouter(prefix="/api/flash-sale", tags=["限时秒杀"])
newbie_router = APIRouter(prefix="/api/newbie", tags=["新人专享"])
cashback_router = APIRouter(prefix="/api/group-buy-cashback", tags=["拼单返现"])
stock_alert_router = APIRouter(prefix="/api/stock-alert", tags=["库存提示"])


# ==================== 限时秒杀 API ====================

@flash_sale_router.post("/create")
def create_flash_sale(
    product_id: str,
    title: str,
    flash_price: float,
    flash_stock: int,
    start_time: datetime,
    end_time: datetime,
    created_by: str,
    min_group_size: int = 1,
    max_group_size: int = 10,
    per_user_limit: int = 1,
    db: Session = Depends(get_db)
):
    """创建秒杀活动"""
    service = FlashSaleService(db)
    try:
        flash_sale = service.create_flash_sale(
            product_id=product_id,
            title=title,
            flash_price=flash_price,
            flash_stock=flash_stock,
            start_time=start_time,
            end_time=end_time,
            created_by=created_by,
            min_group_size=min_group_size,
            max_group_size=max_group_size,
            per_user_limit=per_user_limit
        )
        return {
            "success": True,
            "data": {
                "id": flash_sale.id,
                "product_id": flash_sale.product_id,
                "title": flash_sale.title,
                "flash_price": flash_sale.flash_price,
                "flash_stock": flash_sale.flash_stock,
                "start_time": flash_sale.start_time.isoformat(),
                "end_time": flash_sale.end_time.isoformat(),
                "status": flash_sale.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@flash_sale_router.get("/list")
def list_flash_sales(
    status: Optional[str] = None,
    product_id: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """获取秒杀列表"""
    service = FlashSaleService(db)
    sales = service.list_flash_sales(
        status=status,
        product_id=product_id,
        limit=limit,
        offset=offset
    )
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "product_id": s.product_id,
                "title": s.title,
                "flash_price": s.flash_price,
                "flash_stock": s.flash_stock,
                "purchased_count": s.purchased_count,
                "view_count": s.view_count,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "status": s.status
            }
            for s in sales
        ]
    }


@flash_sale_router.get("/{flash_sale_id}")
def get_flash_sale(flash_sale_id: str, db: Session = Depends(get_db)):
    """获取秒杀详情"""
    service = FlashSaleService(db)
    try:
        flash_sale = service.get_flash_sale(flash_sale_id)
        return {
            "success": True,
            "data": {
                "id": flash_sale.id,
                "product_id": flash_sale.product_id,
                "title": flash_sale.title,
                "flash_price": flash_sale.flash_price,
                "flash_stock": flash_sale.flash_stock,
                "total_stock": flash_sale.total_stock,
                "purchased_count": flash_sale.purchased_count,
                "view_count": flash_sale.view_count,
                "min_group_size": flash_sale.min_group_size,
                "max_group_size": flash_sale.max_group_size,
                "per_user_limit": flash_sale.per_user_limit,
                "start_time": flash_sale.start_time.isoformat(),
                "end_time": flash_sale.end_time.isoformat(),
                "status": flash_sale.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@flash_sale_router.post("/{flash_sale_id}/order")
def place_flash_sale_order(
    flash_sale_id: str,
    quantity: int = Query(default=1, ge=1),
    user_id: str = Header(..., alias="X-User-ID"),
    device_fingerprint: Optional[str] = Header(None, alias="X-Device-Fingerprint"),
    ip_address: Optional[str] = Header(None, alias="X-IP-Address"),
    db: Session = Depends(get_db)
):
    """秒杀下单"""
    service = FlashSaleService(db)
    try:
        order = service.place_order(
            flash_sale_id=flash_sale_id,
            user_id=user_id,
            quantity=quantity,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address
        )
        return {
            "success": True,
            "data": {
                "order_id": order.id,
                "order_number": order.order_number,
                "flash_sale_id": order.flash_sale_id,
                "product_id": order.product_id,
                "quantity": order.quantity,
                "unit_price": order.unit_price,
                "total_amount": order.total_amount,
                "status": order.status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@flash_sale_router.get("/{flash_sale_id}/countdown")
def get_countdown(flash_sale_id: str, db: Session = Depends(get_db)):
    """获取秒杀倒计时"""
    service = FlashSaleService(db)
    try:
        countdown = service.get_countdown(flash_sale_id)
        return {
            "success": True,
            "data": countdown
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@flash_sale_router.get("/{flash_sale_id}/my-orders")
def get_my_orders(flash_sale_id: str, user_id: str = Header(..., alias="X-User-ID"), db: Session = Depends(get_db)):
    """获取用户的秒杀订单"""
    service = FlashSaleService(db)
    orders = service.get_user_orders(flash_sale_id, user_id)
    return {
        "success": True,
        "data": [
            {
                "order_id": o.id,
                "order_number": o.order_number,
                "quantity": o.quantity,
                "unit_price": o.unit_price,
                "total_amount": o.total_amount,
                "status": o.status,
                "created_at": o.created_at.isoformat()
            }
            for o in orders
        ]
    }


# ==================== 新人专享 API ====================

@newbie_router.get("/eligibility")
def check_newbie_eligibility(
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """检查新人资格"""
    service = NewbieService(db)
    result = service.check_newbie_eligibility(user_id)
    return {
        "success": True,
        "data": result
    }


@newbie_router.get("/products")
def get_newbie_products(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取新人专享商品列表"""
    service = NewbieService(db)
    products = service.get_newbie_products(limit=limit)
    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "product_id": p.product_id,
                "newbie_price": p.newbie_price,
                "original_price": p.original_price,
                "stock_limit": p.stock_limit,
                "purchased_count": p.purchased_count,
                "per_user_limit": p.per_user_limit,
                "is_active": p.is_active
            }
            for p in products
        ]
    }


@newbie_router.post("/products/{product_id}/purchase")
def purchase_newbie_product(
    product_id: str,
    quantity: int = Query(default=1, ge=1),
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """购买新人专享商品"""
    service = NewbieService(db)
    try:
        result = service.purchase_newbie_product(user_id, product_id, quantity)
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@newbie_router.get("/coupons")
def claim_newbie_coupons(
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """领取新人券包"""
    service = NewbieService(db)
    result = service.claim_newbie_coupon(user_id)
    return {
        "success": True,
        "data": result
    }


@newbie_router.get("/tasks")
def get_newbie_tasks(
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """获取新人任务列表"""
    service = NewbieService(db)
    tasks = service.get_newbie_tasks(user_id)
    return {
        "success": True,
        "data": tasks
    }


@newbie_router.post("/tasks/{task_type}/complete")
def complete_newbie_task(
    task_type: str,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """完成新人任务"""
    service = NewbieService(db)
    result = service.complete_newbie_task(user_id, task_type)
    return {
        "success": True,
        "data": result
    }


# ==================== 拼单返现 API ====================

@cashback_router.post("/create")
def create_cashback_activity(
    groupbuy_id: str,
    target_participants: int = Query(default=3, ge=2),
    cashback_percentage: float = Query(default=0.2, ge=0.01, le=1),
    max_cashback_amount: Optional[float] = None,
    deadline_hours: int = Query(default=24, ge=1),
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """创建拼单返现活动"""
    service = GroupBuyCashbackService(db)
    try:
        cashback = service.create_cashback_activity(
            creator_user_id=user_id,
            groupbuy_id=groupbuy_id,
            target_participants=target_participants,
            cashback_percentage=cashback_percentage,
            max_cashback_amount=max_cashback_amount,
            deadline_hours=deadline_hours
        )
        return {
            "success": True,
            "data": {
                "id": cashback.id,
                "groupbuy_id": cashback.groupbuy_id,
                "target_participants": cashback.target_participants,
                "cashback_percentage": cashback.cashback_percentage,
                "current_participants": cashback.current_participants,
                "status": cashback.status,
                "deadline": cashback.deadline.isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@cashback_router.post("/{cashback_id}/join")
def join_cashback(
    cashback_id: str,
    payment_amount: float,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """参与拼单返现"""
    service = GroupBuyCashbackService(db)
    try:
        participant = service.join_cashback(cashback_id, user_id, payment_amount)
        return {
            "success": True,
            "data": {
                "participant_id": participant.id,
                "cashback_id": cashback_id,
                "payment_amount": participant.payment_amount,
                "cashback_amount": participant.cashback_amount,
                "cashback_status": participant.cashback_status
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@cashback_router.get("/{cashback_id}/progress")
def get_cashback_progress(
    cashback_id: str,
    db: Session = Depends(get_db)
):
    """获取拼单进度"""
    service = GroupBuyCashbackService(db)
    try:
        progress = service.get_cashback_progress(cashback_id)
        return {
            "success": True,
            "data": progress
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@cashback_router.get("/my")
def get_my_cashbacks(
    status: Optional[str] = None,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """获取我的拼单返现列表"""
    service = GroupBuyCashbackService(db)
    cashbacks = service.get_user_cashbacks(user_id, status)
    return {
        "success": True,
        "data": cashbacks
    }


@cashback_router.get("/records")
def get_cashback_records(
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """获取返现记录"""
    service = GroupBuyCashbackService(db)
    records = service.get_cashback_records(user_id)
    return {
        "success": True,
        "data": records
    }


@cashback_router.post("/withdraw/{record_id}")
def withdraw_cashback(
    record_id: str,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """提现返现"""
    service = GroupBuyCashbackService(db)
    result = service.withdraw_cashback(user_id, record_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return {
        "success": True,
        "data": result
    }


# ==================== 库存紧张提示 API ====================

@stock_alert_router.get("/product/{product_id}")
def get_stock_status(
    product_id: str,
    db: Session = Depends(get_db)
):
    """获取商品库存状态"""
    service = StockAlertService(db)
    try:
        status = service.get_stock_status(product_id)
        return {
            "success": True,
            "data": status
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@stock_alert_router.get("/product/{product_id}/enhanced")
def get_product_enhanced_info(
    product_id: str,
    db: Session = Depends(get_db)
):
    """获取商品增强信息（库存 + 热度）"""
    service = StockAlertService(db)
    try:
        info = service.get_product_enhanced_info(product_id)
        return {
            "success": True,
            "data": info
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@stock_alert_router.post("/product/{product_id}/view")
def track_product_view(
    product_id: str,
    session_id: str = Header(..., alias="X-Session-ID"),
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    device_type: Optional[str] = Header(None, alias="X-Device-Type"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """追踪商品浏览"""
    service = StockAlertService(db)
    ip_address = request.client.host if request else None
    service.track_view(
        product_id=product_id,
        session_id=session_id,
        user_id=user_id,
        ip_address=ip_address,
        device_type=device_type
    )
    return {"success": True, "message": "浏览已记录"}


@stock_alert_router.get("/product/{product_id}/viewers")
def get_product_viewers(
    product_id: str,
    db: Session = Depends(get_db)
):
    """获取商品当前浏览人数"""
    service = StockAlertService(db)
    count = service.get_viewers_count(product_id)
    return {
        "success": True,
        "data": {
            "product_id": product_id,
            "current_viewers": count
        }
    }


@stock_alert_router.get("/product/{product_id}/heatmap")
def get_product_heatmap(
    product_id: str,
    db: Session = Depends(get_db)
):
    """获取商品热度信息"""
    service = StockAlertService(db)
    try:
        heatmap = service.get_product_heatmap(product_id)
        return {
            "success": True,
            "data": heatmap
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@stock_alert_router.get("/low-stock")
def get_low_stock_products(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取库存紧张商品列表"""
    service = StockAlertService(db)
    products = service.get_low_stock_products(limit=limit)
    return {
        "success": True,
        "data": products
    }


@stock_alert_router.get("/hot-products")
def get_hot_products(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """获取热门商品列表"""
    service = StockAlertService(db)
    products = service.get_hot_products(limit=limit)
    return {
        "success": True,
        "data": products
    }


@stock_alert_router.post("/product/{product_id}/wishlist")
def track_wishlist(
    product_id: str,
    db: Session = Depends(get_db)
):
    """追踪商品收藏"""
    service = StockAlertService(db)
    service.track_wishlist(product_id)
    return {"success": True, "message": "收藏已记录"}


@stock_alert_router.post("/product/{product_id}/share")
def track_share(
    product_id: str,
    db: Session = Depends(get_db)
):
    """追踪商品分享"""
    service = StockAlertService(db)
    service.track_share(product_id)
    return {"success": True, "message": "分享已记录"}
