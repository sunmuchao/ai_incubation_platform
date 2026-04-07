"""
社区团购 API 路由（增强版）

增强功能:
- 统一异常处理
- 分页支持
- 结构化日志
- 事务管理
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.product import (
    Product, ProductCreate, GroupBuy, GroupBuyCreate, GroupBuyStatus, Order,
    ProductStatus, OrderStatus, GroupBuyJoinRequest
)
from pydantic import BaseModel
from config.database import get_db
from core.pagination import PaginationParams, PaginatedResponse, create_paginated_response
from core.exceptions import (
    ProductNotFoundError, GroupBuyNotFoundError,
    InsufficientStockError, GroupBuyNotOpenError,
    GroupBuyFullError, UserAlreadyJoinedError,
    PermissionError, GroupBuyExpiredError
)

router = APIRouter(prefix="/api", tags=["community_buying"])


# ========== 请求/响应模型 ==========
class GroupJoinResponse(BaseModel):
    """加入团购响应"""
    message: str
    group_id: str
    current_size: int
    target_size: int
    status: str
    join_record_id: Optional[str] = None


class OrderUpdateRequest(BaseModel):
    """订单状态更新请求"""
    status: OrderStatus


# ========== 商品接口 ==========
@router.get("/products", response_model=List[Product], summary="获取商品列表")
async def list_products(
    status: Optional[str] = Query(None, description="商品状态过滤：active/sold-out/inactive"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取商品列表，支持分页和状态过滤

    - **status**: 可选，过滤商品状态
    - **page**: 页码（从 1 开始）
    - **page_size**: 每页数量（1-100）
    """
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)

    # 转换状态参数
    status_enum = ProductStatus(status.strip().lower()) if status else None

    # 计算分页
    offset = (page - 1) * page_size

    # 查询商品
    products, total = gb_service.list_products(
        status=status_enum,
        limit=page_size,
        offset=offset
    )

    # 返回分页响应
    return create_paginated_response(
        items=products,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/products", response_model=Product, summary="创建商品")
async def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    """创建新商品"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)
    return gb_service.create_product(product_data)


@router.get("/products/{product_id}", response_model=Product, summary="获取商品详情")
async def get_product(product_id: str, db: Session = Depends(get_db)):
    """获取单个商品详情"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)
    product = gb_service.get_product(product_id)

    if not product:
        raise ProductNotFoundError(product_id)

    return product


# ========== 团购接口 ==========
@router.get("/groups", response_model=List[GroupBuy], summary="获取活跃团购列表")
async def list_active_groups(
    product_id: Optional[str] = Query(None, description="按商品 ID 过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取进行中的团购列表，支持分页"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)

    offset = (page - 1) * page_size
    groups, total = gb_service.list_active_group_buys(
        product_id=product_id,
        limit=page_size,
        offset=offset
    )

    return create_paginated_response(
        items=groups,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/groups/all", response_model=List[GroupBuy], summary="获取所有团购")
async def list_all_groups(
    status: Optional[str] = Query(None, description="团购状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取所有团购，可按状态过滤"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)

    offset = (page - 1) * page_size

    if status:
        try:
            status_enum = GroupBuyStatus(status.strip().lower())
            groups, total = gb_service.list_group_buys_by_status(
                status=status_enum,
                limit=page_size,
                offset=offset
            )
        except ValueError:
            raise ValueError(f"无效的团购状态：{status}")
    else:
        # 获取所有状态的团购
        all_groups = []
        total = 0
        for status_enum in GroupBuyStatus:
            groups, _ = gb_service.list_group_buys_by_status(
                status=status_enum,
                limit=100,
                offset=0
            )
            all_groups.extend(groups)
            total += len(groups)

        # 手动分页
        groups = all_groups[offset:offset + page_size]
        total = len(all_groups)

    return create_paginated_response(
        items=groups,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/groups", response_model=GroupBuy, summary="发起团购")
async def create_group_buy(group_data: GroupBuyCreate, db: Session = Depends(get_db)):
    """发起新的团购"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)
    return gb_service.create_group_buy(group_data)


@router.get("/groups/{group_id}", response_model=GroupBuy, summary="获取团购详情")
async def get_group_buy(group_id: str, db: Session = Depends(get_db)):
    """获取团购详细信息"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)
    gb = gb_service.get_group_buy(group_id)

    if not gb:
        raise GroupBuyNotFoundError(group_id)

    return gb


@router.post("/groups/{group_id}/join", response_model=GroupJoinResponse, summary="加入团购")
async def join_group_buy(
    group_id: str,
    request: GroupBuyJoinRequest,
    db: Session = Depends(get_db)
):
    """用户加入团购"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)

    try:
        group_buy, join_record = gb_service.join_group_buy(group_id, request.user_id)
        return GroupJoinResponse(
            message="加入成功",
            group_id=group_id,
            current_size=group_buy.current_size,
            target_size=group_buy.target_size,
            status=group_buy.status.value,
            join_record_id=join_record.id
        )
    except ValueError as e:
        raise GroupBuyNotFoundError(group_id)
    except GroupBuyNotOpenError as e:
        raise
    except UserAlreadyJoinedError as e:
        raise
    except GroupBuyFullError as e:
        raise
    except InsufficientStockError as e:
        raise


@router.delete("/groups/{group_id}", summary="取消团购")
async def cancel_group_buy(
    group_id: str,
    operator_id: str = Query(..., description="操作者 ID（团长 ID）"),
    db: Session = Depends(get_db)
):
    """取消团购，仅团长可操作"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)

    try:
        success = gb_service.cancel_group_buy(group_id, operator_id)
        if not success:
            raise GroupBuyNotFoundError(group_id)
        return {"message": "团购已取消"}
    except PermissionError:
        raise
    except GroupBuyNotOpenError:
        raise


# ========== 订单接口 ==========
@router.get("/orders/{order_id}", response_model=Order, summary="获取订单详情")
async def get_order(order_id: str, db: Session = Depends(get_db)):
    """获取订单详细信息"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)
    order = gb_service.get_order(order_id)

    if not order:
        raise Exception(f"订单不存在：{order_id}")

    return order


@router.get("/users/{user_id}/orders", response_model=List[Order], summary="获取用户订单列表")
async def get_user_orders(
    user_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取指定用户的所有订单，支持分页"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)

    offset = (page - 1) * page_size
    orders, total = gb_service.get_user_orders(
        user_id=user_id,
        limit=page_size,
        offset=offset
    )

    return create_paginated_response(
        items=orders,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/groups/{group_id}/orders", response_model=List[Order], summary="获取团购订单列表")
async def get_group_orders(group_id: str, db: Session = Depends(get_db)):
    """获取指定团购对应的所有订单"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)

    # 先检查团购是否存在
    group = gb_service.get_group_buy(group_id)
    if not group:
        raise GroupBuyNotFoundError(group_id)

    return gb_service.get_group_orders(group_id)


@router.patch("/orders/{order_id}/status", summary="更新订单状态")
async def update_order_status(
    order_id: str,
    status_data: OrderUpdateRequest,
    db: Session = Depends(get_db)
):
    """更新订单状态"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)
    order = gb_service.update_order_status(order_id, status_data.status)

    if not order:
        raise Exception(f"订单不存在：{order_id}")

    return {
        "message": "订单状态更新成功",
        "order_id": order_id,
        "status": status_data.status.value
    }


# ========== 统计查询接口 ==========
@router.get("/users/{user_id}/join-records", summary="获取用户参团记录")
async def get_user_join_records(user_id: str, db: Session = Depends(get_db)):
    """获取用户的所有参团记录"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)
    records = gb_service.get_user_join_records(user_id)

    return {
        "user_id": user_id,
        "total_joined": len(records),
        "records": records
    }


@router.get("/groups/{group_id}/join-records", summary="获取团购参团记录")
async def get_group_join_records(group_id: str, db: Session = Depends(get_db)):
    """获取团购的所有参团记录"""
    from services.groupbuy_service_enhanced import GroupBuyServiceEnhanced

    gb_service = GroupBuyServiceEnhanced(db)

    # 先检查团购是否存在
    group = gb_service.get_group_buy(group_id)
    if not group:
        raise GroupBuyNotFoundError(group_id)

    records = gb_service.get_group_join_records(group_id)

    return {
        "group_id": group_id,
        "total_members": len(records),
        "records": records
    }
