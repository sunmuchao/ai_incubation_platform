"""
团长管理后台 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from config.database import get_db
from services.organizer_dashboard_service import OrganizerDashboardService
from models.product import DashboardStats, GroupBuy, GroupJoinRecord
from models.entities import OrganizerDashboardEntity, GroupBuyEntity, GroupMemberEntity
from core.pagination import PaginationParams, PaginatedResponse

router = APIRouter(prefix="/api/organizer", tags=["团长管理"])


def _convert_group_entity_to_model(entity: GroupBuyEntity) -> GroupBuy:
    """将团购实体转换为模型"""
    return GroupBuy(
        id=entity.id,
        product_id=entity.product_id,
        organizer_id=entity.organizer_id,
        target_size=entity.target_size,
        current_size=entity.current_size,
        status=entity.status.value,
        deadline=entity.deadline,
        created_at=entity.created_at,
        updated_at=entity.updated_at
    )


def _convert_member_entity_to_model(entity: GroupMemberEntity) -> GroupJoinRecord:
    """将成员实体转换为模型"""
    return GroupJoinRecord(
        id=entity.id,
        group_buy_id=entity.group_buy_id,
        user_id=entity.user_id,
        join_time=entity.join_time,
        order_id=entity.order_id,
        status="joined"
    )


@router.get("/dashboard/{user_id}", response_model=DashboardStats, summary="获取团长仪表盘")
def get_organizer_dashboard(
    user_id: str,
    db: Session = Depends(get_db)
):
    """获取团长仪表盘统计数据"""
    service = OrganizerDashboardService(db)
    stats = service.get_dashboard_stats(user_id)
    return DashboardStats(**stats)


@router.post("/dashboard/{user_id}/snapshot", summary="保存仪表盘快照")
def save_dashboard_snapshot(
    user_id: str,
    db: Session = Depends(get_db)
):
    """保存团长仪表盘数据快照"""
    service = OrganizerDashboardService(db)
    snapshot = service.save_dashboard_snapshot(user_id)
    return {
        "success": True,
        "snapshot_id": snapshot.id,
        "data_date": snapshot.data_date.isoformat()
    }


@router.get("/dashboard/{user_id}/history", summary="获取仪表盘历史数据")
def get_dashboard_history(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="天数"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """获取团长仪表盘历史快照数据"""
    service = OrganizerDashboardService(db)
    snapshots = service.get_dashboard_history(user_id, days, limit)

    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "data_date": s.data_date.isoformat(),
                "total_sales": s.total_sales,
                "total_orders": s.total_orders,
                "total_customers": s.total_customers,
                "total_commission": s.total_commission,
                "today_sales": s.today_sales,
                "today_orders": s.today_orders,
                "pending_orders": s.pending_orders,
                "pending_delivery": s.pending_delivery,
                "completed_orders": s.completed_orders,
                "refund_orders": s.refund_orders,
                "customer_satisfaction": s.customer_satisfaction
            }
            for s in snapshots
        ]
    }


@router.get("/dashboard/{user_id}/sales-trend", summary="获取销售趋势")
def get_sales_trend(
    user_id: str,
    days: int = Query(7, ge=1, le=90, description="天数"),
    db: Session = Depends(get_db)
):
    """获取销售趋势数据"""
    service = OrganizerDashboardService(db)
    trend_data = service.get_sales_trend(user_id, days)
    return {
        "success": True,
        "data": trend_data
    }


@router.get("/dashboard/{user_id}/top-products", summary="获取热销商品 TOP 榜")
def get_top_products(
    user_id: str,
    limit: int = Query(10, ge=1, le=100, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """获取团长负责的热销商品 TOP 榜"""
    service = OrganizerDashboardService(db)
    top_products = service.get_top_products(user_id, limit)
    return {
        "success": True,
        "data": top_products
    }


@router.get("/{organizer_id}/groups", response_model=PaginatedResponse[GroupBuy], summary="获取团长团购列表")
def get_organizer_groups(
    organizer_id: str,
    status: Optional[str] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取团长负责的所有团购"""
    service = OrganizerDashboardService(db)

    offset = (page - 1) * page_size
    groups, total = service.get_group_list(
        organizer_id=organizer_id,
        status=status,
        limit=page_size,
        offset=offset
    )

    items = [_convert_group_entity_to_model(g) for g in groups]

    return PaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total
    )


@router.get("/groups/{group_buy_id}/members", response_model=PaginatedResponse[GroupJoinRecord], summary="获取团购成员列表")
def get_group_members(
    group_buy_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取团购成员列表"""
    service = OrganizerDashboardService(db)

    offset = (page - 1) * page_size
    members, total = service.get_member_list(
        group_buy_id=group_buy_id,
        limit=page_size,
        offset=offset
    )

    items = [_convert_member_entity_to_model(m) for m in members]

    return PaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total
    )


@router.get("/{organizer_id}/customers", summary="获取客户列表")
def get_organizer_customers(
    organizer_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取团长负责的客户列表（去重后的用户）"""
    service = OrganizerDashboardService(db)

    offset = (page - 1) * page_size
    customers, total = service.get_customer_list(
        organizer_id=organizer_id,
        limit=page_size,
        offset=offset
    )

    return PaginatedResponse(
        items=customers,
        page=page,
        page_size=page_size,
        total=total
    )
