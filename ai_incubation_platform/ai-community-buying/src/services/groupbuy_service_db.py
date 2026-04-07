"""
社区团购服务（数据库持久化版本）
保持与原有服务接口完全兼容，替换内存存储为数据库存储
"""
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from models.product import (
    Product, ProductCreate, GroupBuy, GroupBuyCreate,
    ProductStatus, GroupBuyStatus, Order, OrderStatus,
    GroupJoinRecord
)
from models.entities import (
    ProductEntity, GroupBuyEntity, GroupMemberEntity,
    OrderEntity
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


class GroupBuyServiceDB:
    """团购服务（数据库版本）"""

    def __init__(self, db: Session):
        self.db = db

    # ========== 商品管理 ==========
    def create_product(self, data: ProductCreate) -> Product:
        """创建商品"""
        product_entity = ProductEntity(**data.model_dump())
        # stock 为 0 时应视为售罄
        if product_entity.stock <= 0:
            product_entity.status = ProductStatus.SOLD_OUT
        self.db.add(product_entity)
        self.db.commit()
        self.db.refresh(product_entity)

        product = Product(
            id=product_entity.id,
            name=product_entity.name,
            description=product_entity.description,
            price=product_entity.price,
            original_price=product_entity.original_price,
            image_url=product_entity.image_url,
            stock=product_entity.stock,
            locked_stock=product_entity.locked_stock,
            sold_stock=product_entity.sold_stock,
            min_group_size=product_entity.min_group_size,
            max_group_size=product_entity.max_group_size,
            status=product_entity.status,
            created_at=product_entity.created_at,
            updated_at=product_entity.updated_at
        )
        logger.info(f"商品创建成功: {product.id} - {product.name}")
        return product

    def get_product(self, product_id: str) -> Optional[Product]:
        """获取商品详情"""
        product_entity = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if not product_entity:
            return None
        return Product(
            id=product_entity.id,
            name=product_entity.name,
            description=product_entity.description,
            price=product_entity.price,
            original_price=product_entity.original_price,
            image_url=product_entity.image_url,
            stock=product_entity.stock,
            locked_stock=product_entity.locked_stock,
            sold_stock=product_entity.sold_stock,
            min_group_size=product_entity.min_group_size,
            max_group_size=product_entity.max_group_size,
            status=product_entity.status,
            created_at=product_entity.created_at,
            updated_at=product_entity.updated_at
        )

    def list_products(self, status: Optional[ProductStatus] = None) -> List[Product]:
        """获取商品列表"""
        query = self.db.query(ProductEntity)
        if status:
            query = query.filter(ProductEntity.status == status)
        product_entities = query.order_by(ProductEntity.created_at.desc()).all()
        products = []
        for p in product_entities:
            products.append(Product(
                id=p.id,
                name=p.name,
                description=p.description,
                price=p.price,
                original_price=p.original_price,
                image_url=p.image_url,
                stock=p.stock,
                locked_stock=p.locked_stock,
                sold_stock=p.sold_stock,
                min_group_size=p.min_group_size,
                max_group_size=p.max_group_size,
                status=p.status,
                created_at=p.created_at,
                updated_at=p.updated_at
            ))
        return products

    def update_product_stock(self, product_id: str, stock_change: int) -> Optional[Product]:
        """更新商品库存"""
        product_entity = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if not product_entity:
            return None

        new_stock = product_entity.stock + stock_change
        if new_stock < 0:
            raise InsufficientStockError(f"商品 {product_id} 库存不足")

        product_entity.stock = new_stock
        product_entity.updated_at = datetime.now()

        # 自动更新商品状态
        if product_entity.stock <= 0 and product_entity.status == ProductStatus.ACTIVE:
            product_entity.status = ProductStatus.SOLD_OUT
            logger.info(f"商品 {product_id} 已售罄")
        elif product_entity.stock > 0 and product_entity.status == ProductStatus.SOLD_OUT:
            product_entity.status = ProductStatus.ACTIVE

        self.db.commit()
        self.db.refresh(product_entity)
        return Product(
            id=product_entity.id,
            name=product_entity.name,
            description=product_entity.description,
            price=product_entity.price,
            original_price=product_entity.original_price,
            image_url=product_entity.image_url,
            stock=product_entity.stock,
            locked_stock=product_entity.locked_stock,
            sold_stock=product_entity.sold_stock,
            min_group_size=product_entity.min_group_size,
            max_group_size=product_entity.max_group_size,
            status=product_entity.status,
            created_at=product_entity.created_at,
            updated_at=product_entity.updated_at
        )

    def _lock_stock(self, product_id: str, quantity: int = 1) -> bool:
        """锁定库存（用户参团时调用）"""
        product_entity = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if not product_entity:
            return False

        available_stock = product_entity.stock - product_entity.locked_stock
        if available_stock < quantity:
            raise InsufficientStockError(f"商品 {product_id} 可用库存不足")

        product_entity.locked_stock += quantity
        product_entity.updated_at = datetime.now()
        self.db.commit()

        logger.info(f"库存锁定成功: 商品 {product_id}, 锁定 {quantity} 件, 剩余可用: {available_stock - quantity}")
        return True

    def _unlock_stock(self, product_id: str, quantity: int = 1) -> bool:
        """解锁库存（团购失败/用户取消时调用）"""
        product_entity = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if not product_entity:
            return False

        if product_entity.locked_stock < quantity:
            logger.warning(f"库存解锁异常: 商品 {product_id} 锁定库存不足")
            return False

        product_entity.locked_stock -= quantity
        product_entity.updated_at = datetime.now()
        self.db.commit()

        logger.info(f"库存解锁成功: 商品 {product_id}, 解锁 {quantity} 件")
        return True

    def _deduct_stock(self, product_id: str, quantity: int = 1) -> bool:
        """扣减库存（团购成功时调用）"""
        product_entity = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if not product_entity:
            return False

        if product_entity.locked_stock < quantity:
            logger.error(f"库存扣减异常: 商品 {product_id} 锁定库存不足")
            return False

        product_entity.locked_stock -= quantity
        product_entity.sold_stock += quantity
        product_entity.stock -= quantity
        if product_entity.stock <= 0 and product_entity.status == ProductStatus.ACTIVE:
            product_entity.status = ProductStatus.SOLD_OUT
            logger.info(f"商品 {product_id} 已售罄")
        elif product_entity.stock > 0 and product_entity.status == ProductStatus.SOLD_OUT:
            product_entity.status = ProductStatus.ACTIVE
        product_entity.updated_at = datetime.now()
        self.db.commit()

        logger.info(
            f"库存扣减成功: 商品 {product_id}, 扣减 {quantity} 件, "
            f"已售: {product_entity.sold_stock}, 剩余: {product_entity.stock}"
        )
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
        group_buy_entity = GroupBuyEntity(
            product_id=data.product_id,
            organizer_id=data.organizer_id,
            target_size=data.target_size,
            deadline=datetime.now() + timedelta(hours=data.duration_hours)
        )
        self.db.add(group_buy_entity)
        self.db.flush()

        # 添加团长为第一个成员
        member = GroupMemberEntity(
            group_buy_id=group_buy_entity.id,
            user_id=data.organizer_id
        )
        self.db.add(member)

        # 锁定团长对应的库存
        self._lock_stock(data.product_id)

        self.db.commit()
        self.db.refresh(group_buy_entity)

        group_buy = GroupBuy(
            id=group_buy_entity.id,
            product_id=group_buy_entity.product_id,
            organizer_id=group_buy_entity.organizer_id,
            product=product,
            target_size=group_buy_entity.target_size,
            current_size=group_buy_entity.current_size,
            status=group_buy_entity.status,
            deadline=group_buy_entity.deadline,
            members=[data.organizer_id],
            created_at=group_buy_entity.created_at,
            updated_at=group_buy_entity.updated_at
        )

        logger.info(f"团购创建成功: {group_buy.id}, 商品: {product.name}, 团长: {data.organizer_id}")
        return group_buy

    def get_group_buy(self, group_buy_id: str) -> Optional[GroupBuy]:
        """获取团购详情"""
        group_buy_entity = self.db.query(GroupBuyEntity).filter(GroupBuyEntity.id == group_buy_id).first()
        if not group_buy_entity:
            return None

        # 过期后必须立刻解锁库存并更新状态，避免“只尝试 join/查询但不列表”的场景漏处理
        if group_buy_entity.status == GroupBuyStatus.OPEN and group_buy_entity.deadline < datetime.now():
            # 显式构造，避免 Pydantic 在 members: List[str] 上解析 ORM 关系导致类型不一致
            group = GroupBuy(
                id=group_buy_entity.id,
                product_id=group_buy_entity.product_id,
                organizer_id=group_buy_entity.organizer_id,
                product=self.get_product(group_buy_entity.product_id),
                target_size=group_buy_entity.target_size,
                current_size=group_buy_entity.current_size,
                status=group_buy_entity.status,
                deadline=group_buy_entity.deadline,
                members=[m.user_id for m in group_buy_entity.members],
                created_at=group_buy_entity.created_at,
                updated_at=group_buy_entity.updated_at
            )
            self._handle_group_failure(group, reason="expired")
            group_buy_entity = self.db.query(GroupBuyEntity).filter(GroupBuyEntity.id == group_buy_id).first()

        group_buy = GroupBuy(
            id=group_buy_entity.id,
            product_id=group_buy_entity.product_id,
            organizer_id=group_buy_entity.organizer_id,
            product=self.get_product(group_buy_entity.product_id),
            target_size=group_buy_entity.target_size,
            current_size=group_buy_entity.current_size,
            status=group_buy_entity.status,
            deadline=group_buy_entity.deadline,
            members=[m.user_id for m in group_buy_entity.members],
            created_at=group_buy_entity.created_at,
            updated_at=group_buy_entity.updated_at
        )

        return group_buy

    def list_active_group_buys(self, product_id: Optional[str] = None) -> List[GroupBuy]:
        """获取活跃团购"""
        # 先清理过期团购
        self._cleanup_expired_groups()

        query = self.db.query(GroupBuyEntity).filter(GroupBuyEntity.status == GroupBuyStatus.OPEN)
        if product_id:
            query = query.filter(GroupBuyEntity.product_id == product_id)

        group_entities = query.order_by(GroupBuyEntity.created_at.desc()).all()

        groups = []
        for entity in group_entities:
            group = GroupBuy(
                id=entity.id,
                product_id=entity.product_id,
                organizer_id=entity.organizer_id,
                product=self.get_product(entity.product_id),
                target_size=entity.target_size,
                current_size=entity.current_size,
                status=entity.status,
                deadline=entity.deadline,
                members=[m.user_id for m in entity.members],
                created_at=entity.created_at,
                updated_at=entity.updated_at
            )
            groups.append(group)

        return groups

    def list_group_buys_by_status(self, status: GroupBuyStatus) -> List[GroupBuy]:
        """按状态获取团购列表"""
        group_entities = self.db.query(GroupBuyEntity).filter(GroupBuyEntity.status == status).all()

        groups = []
        for entity in group_entities:
            group = GroupBuy(
                id=entity.id,
                product_id=entity.product_id,
                organizer_id=entity.organizer_id,
                product=self.get_product(entity.product_id),
                target_size=entity.target_size,
                current_size=entity.current_size,
                status=entity.status,
                deadline=entity.deadline,
                members=[m.user_id for m in entity.members],
                created_at=entity.created_at,
                updated_at=entity.updated_at
            )
            groups.append(group)

        return groups

    def join_group_buy(self, group_buy_id: str, user_id: str) -> Tuple[GroupBuy, GroupJoinRecord]:
        """加入团购"""
        group_buy = self.get_group_buy(group_buy_id)
        if not group_buy:
            raise ValueError(f"团购 {group_buy_id} 不存在")

        # 检查团购状态
        if not group_buy.can_join(user_id):
            if group_buy.status != GroupBuyStatus.OPEN:
                if group_buy.status == GroupBuyStatus.EXPIRED:
                    raise GroupBuyNotOpenError(f"团购 {group_buy_id} 已过期")
                if group_buy.status == GroupBuyStatus.CANCELLED:
                    raise GroupBuyNotOpenError(f"团购 {group_buy_id} 已取消")
                if group_buy.status == GroupBuyStatus.FAILED:
                    raise GroupBuyNotOpenError(f"团购 {group_buy_id} 成团失败")
                if group_buy.status == GroupBuyStatus.SUCCESS:
                    raise GroupBuyNotOpenError(f"团购 {group_buy_id} 已成团")
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
        member = GroupMemberEntity(
            group_buy_id=group_buy_id,
            user_id=user_id
        )
        self.db.add(member)

        # 更新团购人数
        group_buy_entity = self.db.query(GroupBuyEntity).filter(GroupBuyEntity.id == group_buy_id).first()
        group_buy_entity.current_size = len(group_buy.members) + 1
        group_buy_entity.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(group_buy_entity)

        # 创建参团记录
        join_record = GroupJoinRecord(
            group_buy_id=group_buy_id,
            user_id=user_id
        )

        logger.info(f"用户 {user_id} 加入团购 {group_buy_id}, 当前人数: {group_buy_entity.current_size}/{group_buy.target_size}")

        # 重新获取完整的团购信息
        updated_group = self.get_group_buy(group_buy_id)

        # 发送进度通知
        from services.notification_service import notification_service
        group_entity = self.db.query(GroupBuyEntity).filter(GroupBuyEntity.id == group_buy_id).first()
        notification_service.send_group_progress_notification(self.db, group_entity)

        # 检查是否成团
        if updated_group.current_size >= updated_group.target_size:
            self._handle_group_success(updated_group)
            # 发送成团成功通知
            notification_service.send_group_result_notification(self.db, group_entity, success=True)
            updated_group = self.get_group_buy(group_buy_id)

        return updated_group, join_record

    def _handle_group_success(self, group_buy: GroupBuy) -> None:
        """处理团购成功逻辑"""
        group_buy_entity = self.db.query(GroupBuyEntity).filter(GroupBuyEntity.id == group_buy.id).first()
        group_buy_entity.status = GroupBuyStatus.SUCCESS
        group_buy_entity.updated_at = datetime.now()
        self.db.commit()

        # 扣减所有成员的库存
        for _ in group_buy.members:
            self._deduct_stock(group_buy.product_id)

        # 创建订单
        for user_id in group_buy.members:
            order_entity = OrderEntity(
                user_id=user_id,
                group_buy_id=group_buy.id,
                product_id=group_buy.product_id,
                unit_price=group_buy.product.price,
                total_amount=group_buy.product.price
            )
            self.db.add(order_entity)
            self.db.flush()

            # 更新成员记录关联订单ID
            member = self.db.query(GroupMemberEntity).filter(
                GroupMemberEntity.group_buy_id == group_buy.id,
                GroupMemberEntity.user_id == user_id
            ).first()
            if member:
                member.order_id = order_entity.id

        self.db.commit()
        logger.info(f"团购 {group_buy.id} 成团成功! 人数: {group_buy.current_size}, 商品: {group_buy.product.name}")

    def _handle_group_failure(self, group_buy: GroupBuy, reason: str = "failed") -> None:
        """处理团购失败逻辑"""
        group_buy_entity = self.db.query(GroupBuyEntity).filter(GroupBuyEntity.id == group_buy.id).first()

        if reason == "expired":
            group_buy_entity.status = GroupBuyStatus.EXPIRED
        elif reason == "cancelled":
            group_buy_entity.status = GroupBuyStatus.CANCELLED
        elif reason == "failed":
            group_buy_entity.status = GroupBuyStatus.FAILED
        else:
            group_buy_entity.status = GroupBuyStatus.FAILED

        group_buy_entity.updated_at = datetime.now()
        self.db.commit()

        # 解锁所有成员的库存
        for _ in group_buy.members:
            self._unlock_stock(group_buy.product_id)

        # 发送团购失败通知
        from services.notification_service import notification_service
        notification_service.send_group_result_notification(self.db, group_buy_entity, success=False)

        logger.info(f"团购 {group_buy.id} {reason}, 已解锁 {len(group_buy.members)} 件库存")

    def _cleanup_expired_groups(self) -> None:
        """清理过期团购"""
        now = datetime.now()
        expired_groups = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.status == GroupBuyStatus.OPEN,
            GroupBuyEntity.deadline < now
        ).all()

        for group_entity in expired_groups:
            # 显式构造，避免 Pydantic 解析 members ORM 关系
            group = GroupBuy(
                id=group_entity.id,
                product_id=group_entity.product_id,
                organizer_id=group_entity.organizer_id,
                product=self.get_product(group_entity.product_id),
                target_size=group_entity.target_size,
                current_size=group_entity.current_size,
                status=group_entity.status,
                deadline=group_entity.deadline,
                members=[m.user_id for m in group_entity.members],
                created_at=group_entity.created_at,
                updated_at=group_entity.updated_at
            )
            self._handle_group_failure(group, reason="expired")

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
        order_entity = self.db.query(OrderEntity).filter(OrderEntity.id == order_id).first()
        if not order_entity:
            return None
        return Order(
            id=order_entity.id,
            user_id=order_entity.user_id,
            group_buy_id=order_entity.group_buy_id,
            product_id=order_entity.product_id,
            quantity=order_entity.quantity,
            unit_price=order_entity.unit_price,
            total_amount=order_entity.total_amount,
            status=order_entity.status,
            payment_time=order_entity.payment_time,
            delivery_time=order_entity.delivery_time,
            completed_time=order_entity.completed_time,
            created_at=order_entity.created_at,
            updated_at=order_entity.updated_at
        )

    def get_user_orders(self, user_id: str) -> List[Order]:
        """获取用户订单列表"""
        order_entities = self.db.query(OrderEntity).filter(OrderEntity.user_id == user_id).all()
        orders = []
        for o in order_entities:
            orders.append(Order(
                id=o.id,
                user_id=o.user_id,
                group_buy_id=o.group_buy_id,
                product_id=o.product_id,
                quantity=o.quantity,
                unit_price=o.unit_price,
                total_amount=o.total_amount,
                status=o.status,
                payment_time=o.payment_time,
                delivery_time=o.delivery_time,
                completed_time=o.completed_time,
                created_at=o.created_at,
                updated_at=o.updated_at
            ))
        return orders

    def get_group_orders(self, group_buy_id: str) -> List[Order]:
        """获取团购对应的订单列表"""
        order_entities = self.db.query(OrderEntity).filter(OrderEntity.group_buy_id == group_buy_id).all()
        orders = []
        for o in order_entities:
            orders.append(Order(
                id=o.id,
                user_id=o.user_id,
                group_buy_id=o.group_buy_id,
                product_id=o.product_id,
                quantity=o.quantity,
                unit_price=o.unit_price,
                total_amount=o.total_amount,
                status=o.status,
                payment_time=o.payment_time,
                delivery_time=o.delivery_time,
                completed_time=o.completed_time,
                created_at=o.created_at,
                updated_at=o.updated_at
            ))
        return orders

    def update_order_status(self, order_id: str, status: OrderStatus) -> Optional[Order]:
        """更新订单状态"""
        order_entity = self.db.query(OrderEntity).filter(OrderEntity.id == order_id).first()
        if not order_entity:
            return None

        order_entity.status = status
        order_entity.updated_at = datetime.now()

        if status == OrderStatus.PAID:
            order_entity.payment_time = datetime.now()
        elif status == OrderStatus.DELIVERING:
            order_entity.delivery_time = datetime.now()
        elif status == OrderStatus.COMPLETED:
            order_entity.completed_time = datetime.now()

        self.db.commit()
        self.db.refresh(order_entity)

        logger.info(f"订单 {order_id} 状态更新为: {status}")
        return Order(
            id=order_entity.id,
            user_id=order_entity.user_id,
            group_buy_id=order_entity.group_buy_id,
            product_id=order_entity.product_id,
            quantity=order_entity.quantity,
            unit_price=order_entity.unit_price,
            total_amount=order_entity.total_amount,
            status=order_entity.status,
            payment_time=order_entity.payment_time,
            delivery_time=order_entity.delivery_time,
            completed_time=order_entity.completed_time,
            created_at=order_entity.created_at,
            updated_at=order_entity.updated_at
        )

    # ========== 统计查询 ==========
    def get_user_join_records(self, user_id: str) -> List[GroupJoinRecord]:
        """获取用户的参团记录"""
        members = self.db.query(GroupMemberEntity).filter(GroupMemberEntity.user_id == user_id).all()
        records = []
        for member in members:
            if member.order_id:
                record_status = "paid"
            else:
                group_status = self.db.query(GroupBuyEntity.status).filter(GroupBuyEntity.id == member.group_buy_id).scalar()
                if group_status == GroupBuyStatus.EXPIRED:
                    record_status = "expired"
                elif group_status == GroupBuyStatus.CANCELLED:
                    record_status = "cancelled"
                elif group_status == GroupBuyStatus.FAILED:
                    record_status = "failed"
                else:
                    record_status = "joined"
            record = GroupJoinRecord(
                group_buy_id=member.group_buy_id,
                user_id=member.user_id,
                join_time=member.join_time,
                order_id=member.order_id,
                status=record_status
            )
            records.append(record)
        return records

    def get_group_join_records(self, group_buy_id: str) -> List[GroupJoinRecord]:
        """获取团购的参团记录"""
        members = self.db.query(GroupMemberEntity).filter(GroupMemberEntity.group_buy_id == group_buy_id).all()
        records = []
        for member in members:
            if member.order_id:
                record_status = "paid"
            else:
                group_status = self.db.query(GroupBuyEntity.status).filter(GroupBuyEntity.id == member.group_buy_id).scalar()
                if group_status == GroupBuyStatus.EXPIRED:
                    record_status = "expired"
                elif group_status == GroupBuyStatus.CANCELLED:
                    record_status = "cancelled"
                elif group_status == GroupBuyStatus.FAILED:
                    record_status = "failed"
                else:
                    record_status = "joined"
            record = GroupJoinRecord(
                group_buy_id=member.group_buy_id,
                user_id=member.user_id,
                join_time=member.join_time,
                order_id=member.order_id,
                status=record_status
            )
            records.append(record)
        return records
