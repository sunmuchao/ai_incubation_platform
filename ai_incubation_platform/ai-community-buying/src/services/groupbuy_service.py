"""
社区团购服务
"""
from typing import List, Optional, Dict, Tuple
from models.product import (
    Product, ProductCreate, GroupBuy, GroupBuyCreate,
    ProductStatus, GroupBuyStatus, Order, OrderStatus,
    GroupJoinRecord
)
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class InsufficientStockError(Exception):
    """库存不足异常"""
    pass


class GroupBuyNotOpenError(Exception):
    """团购未开启异常"""
    pass


class GroupBuyFullError(Exception):
    """团购已满异常"""
    pass


class UserAlreadyJoinedError(Exception):
    """用户已参团异常"""
    pass


class GroupBuyService:
    """团购服务"""

    def __init__(self):
        self._products: Dict[str, Product] = {}
        self._group_buys: Dict[str, GroupBuy] = {}
        self._orders: Dict[str, Order] = {}
        self._join_records: Dict[str, GroupJoinRecord] = {}

    # ========== 商品管理 ==========
    def create_product(self, data: ProductCreate) -> Product:
        """创建商品"""
        product = Product(**data.model_dump())
        self._products[product.id] = product
        logger.info(f"商品创建成功: {product.id} - {product.name}")
        return product

    def get_product(self, product_id: str) -> Optional[Product]:
        """获取商品详情"""
        return self._products.get(product_id)

    def list_products(self, status: Optional[ProductStatus] = None) -> List[Product]:
        """获取商品列表"""
        products = list(self._products.values())
        if status:
            products = [p for p in products if p.status == status]
        return sorted(products, key=lambda x: x.created_at, reverse=True)

    def update_product_stock(self, product_id: str, stock_change: int) -> Optional[Product]:
        """更新商品库存"""
        product = self.get_product(product_id)
        if not product:
            return None

        new_stock = product.stock + stock_change
        if new_stock < 0:
            raise InsufficientStockError(f"商品 {product_id} 库存不足")

        product.stock = new_stock
        product.updated_at = datetime.now()

        # 自动更新商品状态
        if product.stock <= 0 and product.status == ProductStatus.ACTIVE:
            product.status = ProductStatus.SOLD_OUT
            logger.info(f"商品 {product_id} 已售罄")
        elif product.stock > 0 and product.status == ProductStatus.SOLD_OUT:
            product.status = ProductStatus.ACTIVE

        return product

    def _lock_stock(self, product_id: str, quantity: int = 1) -> bool:
        """锁定库存（用户参团时调用）"""
        product = self.get_product(product_id)
        if not product:
            return False

        available_stock = product.stock - product.locked_stock
        if available_stock < quantity:
            raise InsufficientStockError(f"商品 {product_id} 可用库存不足")

        product.locked_stock += quantity
        product.updated_at = datetime.now()
        logger.info(f"库存锁定成功: 商品 {product_id}, 锁定 {quantity} 件, 剩余可用: {available_stock - quantity}")
        return True

    def _unlock_stock(self, product_id: str, quantity: int = 1) -> bool:
        """解锁库存（团购失败/用户取消时调用）"""
        product = self.get_product(product_id)
        if not product:
            return False

        if product.locked_stock < quantity:
            logger.warning(f"库存解锁异常: 商品 {product_id} 锁定库存不足")
            return False

        product.locked_stock -= quantity
        product.updated_at = datetime.now()
        logger.info(f"库存解锁成功: 商品 {product_id}, 解锁 {quantity} 件")
        return True

    def _deduct_stock(self, product_id: str, quantity: int = 1) -> bool:
        """扣减库存（团购成功时调用）"""
        product = self.get_product(product_id)
        if not product:
            return False

        if product.locked_stock < quantity:
            logger.error(f"库存扣减异常: 商品 {product_id} 锁定库存不足")
            return False

        product.locked_stock -= quantity
        product.sold_stock += quantity
        product.updated_at = datetime.now()
        logger.info(f"库存扣减成功: 商品 {product_id}, 扣减 {quantity} 件, 已售: {product.sold_stock}")
        return True

    # ========== 团购管理 ==========
    def create_group_buy(self, data: GroupBuyCreate) -> GroupBuy:
        """发起团购"""
        # 检查商品是否存在且可售卖
        product = self.get_product(data.product_id)
        if not product or product.status != ProductStatus.ACTIVE:
            raise ValueError(f"商品 {data.product_id} 不可用")

        # 检查商品库存
        if product.stock <= 0:
            raise InsufficientStockError(f"商品 {data.product_id} 库存不足")

        # 校验成团人数范围
        if data.target_size < product.min_group_size or data.target_size > product.max_group_size:
            raise ValueError(f"成团人数需在 {product.min_group_size} - {product.max_group_size} 之间")

        # 创建团购
        group_buy = GroupBuy(
            product_id=data.product_id,
            organizer_id=data.organizer_id,
            target_size=data.target_size,
            deadline=datetime.now() + timedelta(hours=data.duration_hours),
            product=product
        )
        group_buy.members.append(data.organizer_id)

        # 锁定团长对应的库存
        self._lock_stock(data.product_id)

        # 创建参团记录
        join_record = GroupJoinRecord(
            group_buy_id=group_buy.id,
            user_id=data.organizer_id
        )
        self._join_records[join_record.id] = join_record

        self._group_buys[group_buy.id] = group_buy
        logger.info(f"团购创建成功: {group_buy.id}, 商品: {product.name}, 团长: {data.organizer_id}")
        return group_buy

    def get_group_buy(self, group_buy_id: str) -> Optional[GroupBuy]:
        """获取团购详情"""
        gb = self._group_buys.get(group_buy_id)
        if gb and not gb.product:
            # 补充商品信息
            gb.product = self.get_product(gb.product_id)
        return gb

    def list_active_group_buys(self, product_id: Optional[str] = None) -> List[GroupBuy]:
        """获取活跃团购"""
        # 先清理过期团购
        self._cleanup_expired_groups()

        groups = [gb for gb in self._group_buys.values() if gb.status == GroupBuyStatus.OPEN]
        if product_id:
            groups = [gb for gb in groups if gb.product_id == product_id]

        # 补充商品信息
        for gb in groups:
            if not gb.product:
                gb.product = self.get_product(gb.product_id)

        return sorted(groups, key=lambda x: x.created_at, reverse=True)

    def list_group_buys_by_status(self, status: GroupBuyStatus) -> List[GroupBuy]:
        """按状态获取团购列表"""
        groups = [gb for gb in self._group_buys.values() if gb.status == status]
        for gb in groups:
            if not gb.product:
                gb.product = self.get_product(gb.product_id)
        return groups

    def join_group_buy(self, group_buy_id: str, user_id: str) -> Tuple[GroupBuy, GroupJoinRecord]:
        """加入团购"""
        group_buy = self.get_group_buy(group_buy_id)
        if not group_buy:
            raise ValueError(f"团购 {group_buy_id} 不存在")

        # 检查团购状态
        if not group_buy.can_join(user_id):
            if group_buy.status != GroupBuyStatus.OPEN:
                raise GroupBuyNotOpenError(f"团购 {group_buy_id} 已关闭")
            if group_buy.is_expired():
                raise GroupBuyNotOpenError(f"团购 {group_buy_id} 已过期")
            if user_id in group_buy.members:
                raise UserAlreadyJoinedError(f"用户 {user_id} 已加入该团购")
            if len(group_buy.members) >= group_buy.target_size:
                raise GroupBuyFullError(f"团购 {group_buy_id} 已满员")

        # 锁定库存
        self._lock_stock(group_buy.product_id)

        # 添加成员
        group_buy.members.append(user_id)
        group_buy.current_size = len(group_buy.members)
        group_buy.updated_at = datetime.now()

        # 创建参团记录
        join_record = GroupJoinRecord(
            group_buy_id=group_buy_id,
            user_id=user_id
        )
        self._join_records[join_record.id] = join_record

        logger.info(f"用户 {user_id} 加入团购 {group_buy_id}, 当前人数: {group_buy.current_size}/{group_buy.target_size}")

        # 检查是否成团
        if group_buy.current_size >= group_buy.target_size:
            self._handle_group_success(group_buy)

        return group_buy, join_record

    def _handle_group_success(self, group_buy: GroupBuy) -> None:
        """处理团购成功逻辑"""
        group_buy.status = GroupBuyStatus.SUCCESS
        group_buy.updated_at = datetime.now()

        # 扣减所有成员的库存
        for _ in group_buy.members:
            self._deduct_stock(group_buy.product_id)

        # 创建订单
        for user_id in group_buy.members:
            order = Order(
                user_id=user_id,
                group_buy_id=group_buy.id,
                product_id=group_buy.product_id,
                unit_price=group_buy.product.price,
                total_amount=group_buy.product.price
            )
            self._orders[order.id] = order

            # 更新参团记录关联订单ID
            for record in self._join_records.values():
                if record.group_buy_id == group_buy.id and record.user_id == user_id:
                    record.order_id = order.id
                    record.status = "paid"
                    break

        logger.info(f"团购 {group_buy.id} 成团成功! 人数: {group_buy.current_size}, 商品: {group_buy.product.name}")

    def _handle_group_failure(self, group_buy: GroupBuy, reason: str = "failed") -> None:
        """处理团购失败逻辑"""
        if reason == "expired":
            group_buy.status = GroupBuyStatus.EXPIRED
        else:
            group_buy.status = GroupBuyStatus.FAILED

        group_buy.updated_at = datetime.now()

        # 解锁所有成员的库存
        for _ in group_buy.members:
            self._unlock_stock(group_buy.product_id)

        # 更新参团记录状态
        for record in self._join_records.values():
            if record.group_buy_id == group_buy.id:
                record.status = "cancelled"

        logger.info(f"团购 {group_buy.id} {reason}, 已解锁 {len(group_buy.members)} 件库存")

    def _cleanup_expired_groups(self) -> None:
        """清理过期团购"""
        now = datetime.now()
        for gb in self._group_buys.values():
            if gb.status == GroupBuyStatus.OPEN and gb.deadline < now:
                self._handle_group_failure(gb, reason="expired")

    def cancel_group_buy(self, group_buy_id: str, operator_id: str) -> bool:
        """取消团购（仅团长可取消）"""
        group_buy = self.get_group_buy(group_buy_id)
        if not group_buy:
            return False

        if group_buy.organizer_id != operator_id:
            raise PermissionError("仅团长可取消团购")

        if group_buy.status != GroupBuyStatus.OPEN:
            raise GroupBuyNotOpenError("仅可取消进行中的团购")

        self._handle_group_failure(group_buy, reason="cancelled")
        return True

    # ========== 订单管理 ==========
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单详情"""
        return self._orders.get(order_id)

    def get_user_orders(self, user_id: str) -> List[Order]:
        """获取用户订单列表"""
        return [o for o in self._orders.values() if o.user_id == user_id]

    def get_group_orders(self, group_buy_id: str) -> List[Order]:
        """获取团购对应的订单列表"""
        return [o for o in self._orders.values() if o.group_buy_id == group_buy_id]

    def update_order_status(self, order_id: str, status: OrderStatus) -> Optional[Order]:
        """更新订单状态"""
        order = self.get_order(order_id)
        if not order:
            return None

        order.status = status
        order.updated_at = datetime.now()

        if status == OrderStatus.PAID:
            order.payment_time = datetime.now()
        elif status == OrderStatus.DELIVERING:
            order.delivery_time = datetime.now()
        elif status == OrderStatus.COMPLETED:
            order.completed_time = datetime.now()

        logger.info(f"订单 {order_id} 状态更新为: {status}")
        return order

    # ========== 统计查询 ==========
    def get_user_join_records(self, user_id: str) -> List[GroupJoinRecord]:
        """获取用户的参团记录"""
        return [r for r in self._join_records.values() if r.user_id == user_id]

    def get_group_join_records(self, group_buy_id: str) -> List[GroupJoinRecord]:
        """获取团购的参团记录"""
        return [r for r in self._join_records.values() if r.group_buy_id == group_buy_id]


# 全局服务实例
group_buy_service = GroupBuyService()
