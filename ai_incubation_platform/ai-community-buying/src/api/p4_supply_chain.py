"""
P4 供应链与履约优化 API 路由
包含：库存预警、智能补货、供应商管理、采购订单管理
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from config.database import get_db
from services.p4_inventory_alert_service import InventoryAlertService
from services.p4_replenishment_service import ReplenishmentService
from services.p4_supplier_service import SupplierService
from services.p4_purchase_order_service import PurchaseOrderService
from models.p4_entities import (
    InventoryAlertEntity, ReplenishmentSuggestionEntity,
    SupplierEntity, PurchaseOrderEntity
)
from models.p4_models import (
    AlertStatus, ActionType, Priority, ReplenishmentStatus,
    PurchaseOrderStatus, InventoryAlertCreate, InventoryAlertActionCreate,
    SupplierCreate, SupplierUpdate, SupplierProductCreate,
    PurchaseOrderCreate, PurchaseOrderLineCreate
)
from core.exceptions import AppException

router = APIRouter(prefix="/api/p4", tags=["P4 供应链与履约优化"])


# ========== 库存预警 API ==========

@router.get("/inventory-alerts", summary="获取库存预警列表")
def get_inventory_alerts(
    community_id: Optional[str] = Query(None, description="社区 ID"),
    status: Optional[str] = Query(None, description="状态"),
    alert_level: Optional[str] = Query(None, description="预警等级"),
    limit: int = Query(100, ge=1, le=500, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """获取库存预警列表"""
    service = InventoryAlertService(db)
    alerts = service.list_alerts(
        community_id=community_id,
        status=status,
        alert_level=alert_level,
        limit=limit
    )
    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "product_id": a.product_id,
                "community_id": a.community_id,
                "current_stock": a.current_stock,
                "threshold": a.threshold,
                "alert_level": a.alert_level,
                "alert_type": a.alert_type,
                "message": a.message,
                "status": a.status,
                "suggested_quantity": a.suggested_quantity,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in alerts
        ]
    }


@router.get("/inventory-alerts/{alert_id}", summary="获取库存预警详情")
def get_inventory_alert(alert_id: str, db: Session = Depends(get_db)):
    """获取库存预警详细信息"""
    service = InventoryAlertService(db)
    alert = service.get_alert(alert_id)

    if not alert:
        raise AppException(
            code="ALERT_NOT_FOUND",
            message="库存预警不存在",
            status=404
        )

    return {
        "success": True,
        "data": {
            "id": alert.id,
            "product_id": alert.product_id,
            "community_id": alert.community_id,
            "current_stock": alert.current_stock,
            "threshold": alert.threshold,
            "alert_level": alert.alert_level,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "status": alert.status,
            "suggested_quantity": alert.suggested_quantity,
            "handler_id": alert.handler_id,
            "handled_at": alert.handled_at.isoformat() if alert.handled_at else None,
            "handled_notes": alert.handled_notes,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        }
    }


@router.post("/inventory-alerts/check", summary="检查库存并创建预警")
def check_inventory_and_create_alert(
    product_id: str = Query(..., description="商品 ID"),
    community_id: str = Query(..., description="社区 ID"),
    low_stock_threshold: int = Query(10, ge=1, description="低库存阈值"),
    critical_threshold: int = Query(5, ge=1, description="严重缺货阈值"),
    db: Session = Depends(get_db)
):
    """检查库存并创建预警"""
    service = InventoryAlertService(db)
    alert, success = service.check_inventory_and_create_alert(
        product_id=product_id,
        community_id=community_id,
        low_stock_threshold=low_stock_threshold,
        critical_threshold=critical_threshold
    )

    if not success:
        raise AppException(
            code="INVENTORY_CHECK_FAILED",
            message="检查库存失败"
        )

    return {
        "success": True,
        "alert": {
            "id": alert.id,
            "alert_level": alert.alert_level,
            "alert_type": alert.alert_type,
            "message": alert.message
        } if alert else None,
        "message": "库存充足" if not alert else "已创建预警"
    }


@router.post("/inventory-alerts/{alert_id}/handle", summary="处理库存预警")
def handle_inventory_alert(
    alert_id: str,
    handler_id: str = Query(..., description="处理人 ID"),
    notes: Optional[str] = Query(None, description="处理备注"),
    db: Session = Depends(get_db)
):
    """处理库存预警"""
    service = InventoryAlertService(db)
    alert, success = service.handle_alert(
        alert_id=alert_id,
        handler_id=handler_id,
        notes=notes
    )

    if not success:
        raise AppException(
            code="HANDLE_ALERT_FAILED",
            message="处理预警失败"
        )

    return {
        "success": True,
        "message": "预警已处理",
        "data": {
            "id": alert.id,
            "status": alert.status,
            "handled_at": alert.handled_at.isoformat() if alert.handled_at else None
        }
    }


@router.post("/inventory-alerts/{alert_id}/actions", summary="创建预警处理行动")
def create_inventory_alert_action(
    alert_id: str,
    action_type: str = Query(..., description="行动类型"),
    action_quantity: Optional[int] = Query(None, description="行动数量"),
    action_cost: float = Query(0.0, ge=0, description="行动成本"),
    notes: Optional[str] = Query(None, description="备注"),
    db: Session = Depends(get_db)
):
    """创建预警处理行动"""
    service = InventoryAlertService(db)
    action, success = service.create_action(
        alert_id=alert_id,
        action_type=action_type,
        action_quantity=action_quantity,
        action_cost=action_cost,
        notes=notes
    )

    if not success:
        raise AppException(
            code="CREATE_ACTION_FAILED",
            message="创建行动失败"
        )

    return {
        "success": True,
        "message": "行动已创建",
        "data": {
            "id": action.id,
            "action_type": action.action_type,
            "status": action.status
        }
    }


@router.get("/inventory-alerts/stats", summary="获取库存预警统计")
def get_inventory_alert_stats(
    community_id: Optional[str] = Query(None, description="社区 ID"),
    db: Session = Depends(get_db)
):
    """获取库存预警统计"""
    service = InventoryAlertService(db)
    stats = service.get_alert_stats(community_id=community_id)
    return {
        "success": True,
        "data": stats
    }


# ========== 智能补货 API ==========

@router.get("/replenishment-suggestions", summary="获取补货建议列表")
def get_replenishment_suggestions(
    community_id: Optional[str] = Query(None, description="社区 ID"),
    status: Optional[str] = Query(None, description="状态"),
    priority: Optional[str] = Query(None, description="优先级"),
    limit: int = Query(100, ge=1, le=500, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """获取补货建议列表"""
    service = ReplenishmentService(db)
    suggestions = service.list_suggestions(
        community_id=community_id,
        status=status,
        priority=priority,
        limit=limit
    )
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "product_id": s.product_id,
                "community_id": s.community_id,
                "current_stock": s.current_stock,
                "predicted_demand": s.predicted_demand,
                "predicted_days": s.predicted_days,
                "suggested_quantity": s.suggested_quantity,
                "priority": s.priority,
                "confidence": s.confidence,
                "reason": s.reason,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in suggestions
        ]
    }


@router.post("/replenishment-suggestions/generate", summary="生成补货建议")
def generate_replenishment_suggestion(
    product_id: str = Query(..., description="商品 ID"),
    community_id: str = Query(..., description="社区 ID"),
    forecast_days: int = Query(7, ge=1, le=30, description="预测天数"),
    db: Session = Depends(get_db)
):
    """生成补货建议"""
    service = ReplenishmentService(db)
    suggestion, success = service.generate_replenishment_suggestion(
        product_id=product_id,
        community_id=community_id,
        forecast_days=forecast_days
    )

    if not success:
        raise AppException(
            code="GENERATE_SUGGESTION_FAILED",
            message="生成补货建议失败"
        )

    return {
        "success": True,
        "data": {
            "id": suggestion.id,
            "suggested_quantity": suggestion.suggested_quantity,
            "priority": suggestion.priority,
            "confidence": suggestion.confidence,
            "reason": suggestion.reason
        } if suggestion else {"message": "库存充足，不需要补货"}
    }


@router.post("/replenishment-suggestions/{suggestion_id}/accept", summary="接受补货建议")
def accept_replenishment_suggestion(
    suggestion_id: str,
    order_id: Optional[str] = Query(None, description="转化的采购订单 ID"),
    db: Session = Depends(get_db)
):
    """接受补货建议"""
    service = ReplenishmentService(db)
    suggestion, success = service.accept_suggestion(
        suggestion_id=suggestion_id,
        order_id=order_id
    )

    if not success:
        raise AppException(
            code="ACCEPT_SUGGESTION_FAILED",
            message="接受补货建议失败"
        )

    return {
        "success": True,
        "message": "补货建议已接受",
        "data": {
            "id": suggestion.id,
            "status": suggestion.status,
            "converted_to_order_id": suggestion.converted_to_order_id
        }
    }


@router.post("/replenishment-suggestions/{suggestion_id}/reject", summary="拒绝补货建议")
def reject_replenishment_suggestion(
    suggestion_id: str,
    reason: Optional[str] = Query(None, description="拒绝原因"),
    db: Session = Depends(get_db)
):
    """拒绝补货建议"""
    service = ReplenishmentService(db)
    suggestion, success = service.reject_suggestion(
        suggestion_id=suggestion_id,
        reason=reason
    )

    if not success:
        raise AppException(
            code="REJECT_SUGGESTION_FAILED",
            message="拒绝补货建议失败"
        )

    return {
        "success": True,
        "message": "补货建议已拒绝",
        "data": {
            "id": suggestion.id,
            "status": suggestion.status
        }
    }


@router.get("/replenishment-suggestions/stats", summary="获取补货建议统计")
def get_replenishment_suggestion_stats(
    community_id: Optional[str] = Query(None, description="社区 ID"),
    db: Session = Depends(get_db)
):
    """获取补货建议统计"""
    service = ReplenishmentService(db)
    stats = service.get_suggestion_stats(community_id=community_id)
    return {
        "success": True,
        "data": stats
    }


# ========== 供应商管理 API ==========

@router.get("/suppliers", summary="获取供应商列表")
def get_suppliers(
    category: Optional[str] = Query(None, description="品类"),
    is_active: bool = Query(True, description="是否启用"),
    limit: int = Query(100, ge=1, le=500, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """获取供应商列表"""
    service = SupplierService(db)
    suppliers = service.list_suppliers(
        category=category,
        is_active=is_active,
        limit=limit
    )
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "contact_person": s.contact_person,
                "contact_phone": s.contact_phone,
                "category": s.category,
                "rating": s.rating,
                "on_time_delivery_rate": s.on_time_delivery_rate,
                "quality_pass_rate": s.quality_pass_rate,
                "is_active": s.is_active
            }
            for s in suppliers
        ]
    }


@router.get("/suppliers/{supplier_id}", summary="获取供应商详情")
def get_supplier(supplier_id: str, db: Session = Depends(get_db)):
    """获取供应商详细信息"""
    service = SupplierService(db)
    supplier = service.get_supplier(supplier_id)

    if not supplier:
        raise AppException(
            code="SUPPLIER_NOT_FOUND",
            message="供应商不存在",
            status=404
        )

    return {
        "success": True,
        "data": {
            "id": supplier.id,
            "name": supplier.name,
            "contact_person": supplier.contact_person,
            "contact_phone": supplier.contact_phone,
            "contact_email": supplier.contact_email,
            "address": supplier.address,
            "category": supplier.category,
            "rating": supplier.rating,
            "total_orders": supplier.total_orders,
            "total_amount": supplier.total_amount,
            "on_time_delivery_rate": supplier.on_time_delivery_rate,
            "quality_pass_rate": supplier.quality_pass_rate,
            "payment_terms_days": supplier.payment_terms_days,
            "delivery_lead_days": supplier.delivery_lead_days,
            "is_active": supplier.is_active
        }
    }


@router.post("/suppliers", summary="创建供应商")
def create_supplier(
    name: str = Query(..., description="供应商名称"),
    contact_person: Optional[str] = Query(None, description="联系人"),
    contact_phone: Optional[str] = Query(None, description="联系电话"),
    contact_email: Optional[str] = Query(None, description="联系邮箱"),
    category: Optional[str] = Query(None, description="品类"),
    rating: float = Query(5.0, ge=0, le=5, description="评分"),
    db: Session = Depends(get_db)
):
    """创建供应商"""
    service = SupplierService(db)
    data = {
        "name": name,
        "contact_person": contact_person,
        "contact_phone": contact_phone,
        "contact_email": contact_email,
        "category": category,
        "rating": rating
    }
    supplier, success = service.create_supplier(data)

    if not success:
        raise AppException(
            code="CREATE_SUPPLIER_FAILED",
            message="创建供应商失败"
        )

    return {
        "success": True,
        "message": "供应商创建成功",
        "data": {
            "id": supplier.id,
            "name": supplier.name
        }
    }


@router.get("/suppliers/stats", summary="获取供应商统计")
def get_supplier_stats(
    supplier_id: Optional[str] = Query(None, description="供应商 ID"),
    db: Session = Depends(get_db)
):
    """获取供应商统计"""
    service = SupplierService(db)
    stats = service.get_supplier_stats(supplier_id=supplier_id)
    return {
        "success": True,
        "data": stats
    }


@router.get("/suppliers/top", summary="获取顶级供应商")
def get_top_suppliers(
    limit: int = Query(10, ge=1, le=100, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """获取顶级供应商排行榜"""
    service = SupplierService(db)
    suppliers = service.get_top_suppliers(limit=limit)
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "rating": s.rating,
                "total_orders": s.total_orders,
                "on_time_delivery_rate": s.on_time_delivery_rate,
                "quality_pass_rate": s.quality_pass_rate
            }
            for s in suppliers
        ]
    }


# ========== 采购订单 API ==========

@router.get("/purchase-orders", summary="获取采购订单列表")
def get_purchase_orders(
    supplier_id: Optional[str] = Query(None, description="供应商 ID"),
    community_id: Optional[str] = Query(None, description="社区 ID"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(100, ge=1, le=500, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """获取采购订单列表"""
    service = PurchaseOrderService(db)
    orders = service.list_orders(
        supplier_id=supplier_id,
        community_id=community_id,
        status=status,
        limit=limit
    )
    return {
        "success": True,
        "data": [
            {
                "id": o.id,
                "order_no": o.order_no,
                "supplier_id": o.supplier_id,
                "community_id": o.community_id,
                "total_quantity": o.total_quantity,
                "total_amount": o.total_amount,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None
            }
            for o in orders
        ]
    }


@router.get("/purchase-orders/{order_id}", summary="获取采购订单详情")
def get_purchase_order(order_id: str, db: Session = Depends(get_db)):
    """获取采购订单详细信息"""
    service = PurchaseOrderService(db)
    order = service.get_order(order_id)

    if not order:
        raise AppException(
            code="PURCHASE_ORDER_NOT_FOUND",
            message="采购订单不存在",
            status=404
        )

    lines = service.get_order_lines(order_id)

    return {
        "success": True,
        "data": {
            "id": order.id,
            "order_no": order.order_no,
            "supplier_id": order.supplier_id,
            "community_id": order.community_id,
            "total_quantity": order.total_quantity,
            "total_amount": order.total_amount,
            "status": order.status,
            "expected_delivery_date": order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
            "delivery_address": order.delivery_address,
            "receiver_name": order.receiver_name,
            "notes": order.notes,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "lines": [
                {
                    "id": l.id,
                    "product_id": l.product_id,
                    "quantity": l.quantity,
                    "unit_cost": l.unit_cost,
                    "line_total": l.line_total,
                    "received_quantity": l.received_quantity,
                    "status": l.status
                }
                for l in lines
            ]
        }
    }


@router.get("/purchase-orders/stats", summary="获取采购订单统计")
def get_purchase_order_stats(
    supplier_id: Optional[str] = Query(None, description="供应商 ID"),
    community_id: Optional[str] = Query(None, description="社区 ID"),
    db: Session = Depends(get_db)
):
    """获取采购订单统计"""
    service = PurchaseOrderService(db)
    stats = service.get_order_stats(
        supplier_id=supplier_id,
        community_id=community_id
    )
    return {
        "success": True,
        "data": stats
    }
