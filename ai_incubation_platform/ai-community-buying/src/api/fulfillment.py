"""
履约追踪 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from config.database import get_db
from services.fulfillment_service import FulfillmentService
from models.product import (
    FulfillmentStatus, EventType,
    Fulfillment, FulfillmentEvent,
    FulfillmentCreate, FulfillmentUpdate, FulfillmentEventCreate
)
from models.entities import FulfillmentEntity, FulfillmentEventEntity
from core.pagination import PaginationParams, PaginatedResponse
from core.exceptions import AppException

router = APIRouter(prefix="/api/fulfillment", tags=["履约追踪"])


def _convert_entity_to_model(entity: FulfillmentEntity) -> Fulfillment:
    """将实体转换为模型"""
    return Fulfillment(
        id=entity.id,
        order_id=entity.order_id,
        group_buy_id=entity.group_buy_id,
        status=entity.status,
        tracking_number=entity.tracking_number,
        carrier=entity.carrier,
        warehouse_id=entity.warehouse_id,
        shipped_at=entity.shipped_at,
        delivered_at=entity.delivered_at,
        completed_at=entity.completed_at,
        cancelled_at=entity.cancelled_at,
        cancel_reason=entity.cancel_reason,
        notes=entity.notes,
        created_at=entity.created_at,
        updated_at=entity.updated_at
    )


def _convert_event_entity_to_model(entity: FulfillmentEventEntity) -> FulfillmentEvent:
    """将事件实体转换为模型"""
    import json
    return FulfillmentEvent(
        id=entity.id,
        fulfillment_id=entity.fulfillment_id,
        event_type=entity.event_type,
        event_time=entity.event_time,
        location=entity.location,
        description=entity.description,
        operator=entity.operator,
        extra_data=json.loads(entity.extra_data) if entity.extra_data else None,
        created_at=entity.created_at
    )


@router.post("", response_model=Fulfillment, summary="创建履约记录")
def create_fulfillment(
    data: FulfillmentCreate,
    db: Session = Depends(get_db)
):
    """创建新的履约记录"""
    service = FulfillmentService(db)
    fulfillment, success = service.create_fulfillment(data.model_dump())

    if not success:
        raise AppException(
            code="FULFILLMENT_CREATE_FAILED",
            message="创建履约记录失败"
        )

    return _convert_entity_to_model(fulfillment)


@router.get("/{fulfillment_id}", response_model=Fulfillment, summary="获取履约记录详情")
def get_fulfillment(fulfillment_id: str, db: Session = Depends(get_db)):
    """获取履约记录详细信息"""
    service = FulfillmentService(db)
    fulfillment = service.get_fulfillment(fulfillment_id)

    if not fulfillment:
        raise AppException(
            code="FULFILLMENT_NOT_FOUND",
            message="履约记录不存在",
            status=404
        )

    return _convert_entity_to_model(fulfillment)


@router.put("/{fulfillment_id}/status", response_model=Fulfillment, summary="更新履约状态")
def update_fulfillment_status(
    fulfillment_id: str,
    data: FulfillmentUpdate,
    db: Session = Depends(get_db)
):
    """更新履约状态"""
    service = FulfillmentService(db)
    fulfillment, success = service.update_status(
        fulfillment_id,
        data.status,
        data.notes
    )

    if not success:
        raise AppException(
            code="FULFILLMENT_UPDATE_FAILED",
            message="更新履约状态失败"
        )

    return _convert_entity_to_model(fulfillment)


@router.post("/{fulfillment_id}/events", response_model=FulfillmentEvent, summary="创建履约事件")
def create_fulfillment_event(
    fulfillment_id: str,
    data: FulfillmentEventCreate,
    db: Session = Depends(get_db)
):
    """添加履约事件记录"""
    service = FulfillmentService(db)
    event, success = service.create_event(
        fulfillment_id,
        data.event_type,
        data.description,
        data.location,
        data.operator,
        data.extra_data
    )

    if not success:
        raise AppException(
            code="FULFILLMENT_EVENT_CREATE_FAILED",
            message="创建履约事件失败"
        )

    return _convert_event_entity_to_model(event)


@router.get("/{fulfillment_id}/events", response_model=List[FulfillmentEvent], summary="获取履约事件列表")
def get_fulfillment_events(fulfillment_id: str, db: Session = Depends(get_db)):
    """获取履约记录的所有事件"""
    service = FulfillmentService(db)

    # 先验证履约记录是否存在
    fulfillment = service.get_fulfillment(fulfillment_id)
    if not fulfillment:
        raise AppException(
            code="FULFILLMENT_NOT_FOUND",
            message="履约记录不存在",
            status=404
        )

    events = service.get_fulfillment_events(fulfillment_id)
    return [_convert_event_entity_to_model(e) for e in events]


@router.get("", response_model=PaginatedResponse[Fulfillment], summary="获取履约记录列表")
def list_fulfillments(
    status: Optional[str] = Query(None, description="状态过滤"),
    group_buy_id: Optional[str] = Query(None, description="团购 ID 过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取履约记录列表（支持分页）"""
    service = FulfillmentService(db)

    offset = (page - 1) * page_size
    fulfillments, total = service.list_fulfillments(
        status=status,
        group_buy_id=group_buy_id,
        limit=page_size,
        offset=offset
    )

    items = [_convert_entity_to_model(f) for f in fulfillments]

    return PaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total
    )


@router.get("/order/{order_id}", response_model=Fulfillment, summary="根据订单 ID 获取履约记录")
def get_fulfillment_by_order(order_id: str, db: Session = Depends(get_db)):
    """根据订单 ID 获取履约记录"""
    service = FulfillmentService(db)
    fulfillment = service.get_fulfillment_by_order(order_id)

    if not fulfillment:
        raise AppException(
            code="FULFILLMENT_NOT_FOUND",
            message="履约记录不存在",
            status=404
        )

    return _convert_entity_to_model(fulfillment)


@router.get("/user/{user_id}", response_model=PaginatedResponse[Fulfillment], summary="获取用户履约记录")
def get_user_fulfillments(
    user_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取指定用户的所有履约记录"""
    service = FulfillmentService(db)

    offset = (page - 1) * page_size
    fulfillments, total = service.get_user_fulfillments(
        user_id=user_id,
        limit=page_size,
        offset=offset
    )

    items = [_convert_entity_to_model(f) for f in fulfillments]

    return PaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total
    )


@router.get("/organizer/{organizer_id}", response_model=PaginatedResponse[Fulfillment], summary="获取团长履约记录")
def get_organizer_fulfillments(
    organizer_id: str,
    status: Optional[str] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取团长负责的所有履约记录"""
    service = FulfillmentService(db)

    offset = (page - 1) * page_size
    fulfillments, total = service.get_organizer_fulfillments(
        organizer_id=organizer_id,
        status=status,
        limit=page_size,
        offset=offset
    )

    items = [_convert_entity_to_model(f) for f in fulfillments]

    return PaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total
    )


@router.post("/{fulfillment_id}/cancel", response_model=Fulfillment, summary="取消履约")
def cancel_fulfillment(
    fulfillment_id: str,
    reason: str = Query(..., description="取消原因"),
    db: Session = Depends(get_db)
):
    """取消履约记录"""
    service = FulfillmentService(db)
    fulfillment, success = service.cancel_fulfillment(fulfillment_id, reason)

    if not success:
        raise AppException(
            code="FULFILLMENT_CANCEL_FAILED",
            message="取消履约失败"
        )

    return _convert_entity_to_model(fulfillment)


@router.get("/stats/summary", summary="获取履约统计")
def get_fulfillment_stats(
    group_buy_id: Optional[str] = Query(None, description="团购 ID"),
    db: Session = Depends(get_db)
):
    """获取履约统计信息"""
    service = FulfillmentService(db)
    return service.get_fulfillment_stats(group_buy_id)
