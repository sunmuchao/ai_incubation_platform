"""
社区团购 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.product import (
    Product, ProductCreate, GroupBuy, GroupBuyCreate,
    GroupBuyStatus, Order, OrderStatus, GroupBuyJoinRequest
)
from services.groupbuy_service import (
    group_buy_service, InsufficientStockError,
    GroupBuyNotOpenError, GroupBuyFullError,
    UserAlreadyJoinedError
)

router = APIRouter(prefix="/api", tags=["community_buying"])


# ========== 商品接口 ==========
@router.get("/products", response_model=List[Product], summary="获取商品列表")
async def list_products(
    status: Optional[str] = Query(None, description="商品状态过滤: active/sold_out/inactive")
):
    """获取商品列表，可按状态过滤"""
    try:
        status_enum = ProductStatus(status) if status else None
        return group_buy_service.list_products(status_enum)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的商品状态")


@router.post("/products", response_model=Product, summary="创建商品")
async def create_product(product_data: ProductCreate):
    """创建新商品"""
    try:
        return group_buy_service.create_product(product_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/products/{product_id}", response_model=Product, summary="获取商品详情")
async def get_product(product_id: str):
    """获取单个商品详情"""
    product = group_buy_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


# ========== 团购接口 ==========
@router.get("/groups", response_model=List[GroupBuy], summary="获取活跃团购列表")
async def list_active_groups(
    product_id: Optional[str] = Query(None, description="按商品ID过滤")
):
    """获取进行中的团购列表"""
    return group_buy_service.list_active_group_buys(product_id)


@router.get("/groups/all", response_model=List[GroupBuy], summary="获取所有团购")
async def list_all_groups(
    status: Optional[str] = Query(None, description="团购状态过滤: open/success/failed/expired/cancelled")
):
    """获取所有团购，可按状态过滤"""
    try:
        if status:
            status_enum = GroupBuyStatus(status)
            return group_buy_service.list_group_buys_by_status(status_enum)
        return list(group_buy_service._group_buys.values())
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的团购状态")


@router.post("/groups", response_model=GroupBuy, summary="发起团购")
async def create_group_buy(group_data: GroupBuyCreate):
    """发起新的团购"""
    try:
        return group_buy_service.create_group_buy(group_data)
    except InsufficientStockError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建团购失败: {str(e)}")


@router.get("/groups/{group_id}", response_model=GroupBuy, summary="获取团购详情")
async def get_group_buy(group_id: str):
    """获取团购详细信息"""
    gb = group_buy_service.get_group_buy(group_id)
    if not gb:
        raise HTTPException(status_code=404, detail="团购不存在")
    return gb


@router.post("/groups/{group_id}/join", summary="加入团购")
async def join_group_buy(group_id: str, request: GroupBuyJoinRequest):
    """用户加入团购"""
    try:
        group_buy, join_record = group_buy_service.join_group_buy(group_id, request.user_id)
        return {
            "message": "加入成功",
            "group_id": group_id,
            "current_size": group_buy.current_size,
            "target_size": group_buy.target_size,
            "status": group_buy.status,
            "join_record_id": join_record.id
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GroupBuyNotOpenError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserAlreadyJoinedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GroupBuyFullError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientStockError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加入团购失败: {str(e)}")


@router.delete("/groups/{group_id}", summary="取消团购")
async def cancel_group_buy(group_id: str, operator_id: str = Query(..., description="操作者ID（团长ID）")):
    """取消团购，仅团长可操作"""
    try:
        success = group_buy_service.cancel_group_buy(group_id, operator_id)
        if not success:
            raise HTTPException(status_code=404, detail="团购不存在")
        return {"message": "团购已取消"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except GroupBuyNotOpenError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 订单接口 ==========
@router.get("/orders/{order_id}", response_model=Order, summary="获取订单详情")
async def get_order(order_id: str):
    """获取订单详细信息"""
    order = group_buy_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.get("/users/{user_id}/orders", response_model=List[Order], summary="获取用户订单列表")
async def get_user_orders(user_id: str):
    """获取指定用户的所有订单"""
    return group_buy_service.get_user_orders(user_id)


@router.get("/groups/{group_id}/orders", response_model=List[Order], summary="获取团购订单列表")
async def get_group_orders(group_id: str):
    """获取指定团购对应的所有订单"""
    group = group_buy_service.get_group_buy(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="团购不存在")
    return group_buy_service.get_group_orders(group_id)


@router.patch("/orders/{order_id}/status", summary="更新订单状态")
async def update_order_status(
    order_id: str,
    status: str = Query(..., description="订单状态: pending/paid/delivering/completed/cancelled/refunded")
):
    """更新订单状态"""
    try:
        status_enum = OrderStatus(status)
        order = group_buy_service.update_order_status(order_id, status_enum)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        return {
            "message": "订单状态更新成功",
            "order_id": order_id,
            "status": status
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的订单状态")


# ========== 统计查询接口 ==========
@router.get("/users/{user_id}/join-records", summary="获取用户参团记录")
async def get_user_join_records(user_id: str):
    """获取用户的所有参团记录"""
    records = group_buy_service.get_user_join_records(user_id)
    return {
        "user_id": user_id,
        "total_joined": len(records),
        "records": records
    }


@router.get("/groups/{group_id}/join-records", summary="获取团购参团记录")
async def get_group_join_records(group_id: str):
    """获取团购的所有参团记录"""
    group = group_buy_service.get_group_buy(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="团购不存在")
    records = group_buy_service.get_group_join_records(group_id)
    return {
        "group_id": group_id,
        "total_members": len(records),
        "records": records
    }
