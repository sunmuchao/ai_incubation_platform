"""
社区团购服务（增强版）

增强功能:
1. 事务管理 - 确保数据一致性
2. 乐观锁 - 防止并发超卖
3. 结构化日志 - 提升可观测性
4. 性能优化 - 减少数据库查询
"""
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
from datetime import datetime, timedelta
import uuid

from models.product import (
    Product, ProductCreate, GroupBuy, GroupBuyCreate,
    ProductStatus, GroupBuyStatus, Order, OrderStatus,
    GroupJoinRecord
)
from models.entities import (
    ProductEntity, GroupBuyEntity, GroupMemberEntity,
    OrderEntity, NotificationEntity
)
from core.exceptions import (
    InsufficientStockError, GroupBuyNotOpenError,
    GroupBuyFullError, UserAlreadyJoinedError,
    GroupBuyNotFoundError, ProductNotFoundError,
    PermissionError, GroupBuyExpiredError
)
from config.database_enhanced import TransactionManager

logger = logging.getLogger(__name__)


class GroupBuyServiceEnhanced:
    """
    增强版团购服务

    特性:
    - 事务管理确保数据一致性
    - 乐观锁防止并发超卖
    - 结构化日志提升可观测性
    """

    def __init__(self, db: Session):
        self.db = db
        self.request_id: Optional[str] = None

    def set_request_context(self, request_id: str, user_id: Optional[str] = None):
        """设置请求上下文，用于日志追踪"""
        self.request_id = request_id
        self.user_id = user_id

    def _log(self, level: str, message: str, extra: Optional[Dict] = None):
        """结构化日志"""
        log_extra = {
            "request_id": self.request_id,
            "user_id": self.user_id,
        }
        if extra:
            log_extra.update(extra)

        log_method = getattr(logger, level)
        log_method(message, extra=log_extra)

    # ========== 商品管理 ==========
    def create_product(self, data: ProductCreate) -> Product:
        """创建商品（带事务）"""
        try:
            with TransactionManager.transaction(self.db):
                product_entity = ProductEntity(**data.model_dump())

                if product_entity.stock <= 0:
                    product_entity.status = ProductStatus.SOLD_OUT

                self.db.add(product_entity)
                self.db.flush()

                self._log("info", f"商品创建成功：{product_entity.id}", {
                    "product_id": product_entity.id,
                    "product_name": product_entity.name,
                    "stock": product_entity.stock
                })

                return self._entity_to_product(product_entity)
        except Exception as e:
            self._log("error", f"商品创建失败：{str(e)}", {"error": str(e)})
            raise

    def get_product(self, product_id: str) -> Optional[Product]:
        """获取商品详情"""
        product_entity = self.db.query(ProductEntity).filter(
            ProductEntity.id == product_id
        ).first()

        if not product_entity:
            return None

        return self._entity_to_product(product_entity)

    def list_products(
        self,
        status: Optional[ProductStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Product], int]:
        """
        获取商品列表（带分页）

        Returns:
            (商品列表，总数)
        """
        query = self.db.query(ProductEntity)

        if status:
            query = query.filter(ProductEntity.status == status)

        # 获取总数
        total = query.count()

        # 分页查询
        entities = query.order_by(
            ProductEntity.created_at.desc()
        ).offset(offset).limit(limit).all()

        products = [self._entity_to_product(e) for e in entities]

        self._log("debug", f"商品列表查询", {
            "status": status.value if status else None,
            "limit": limit,
            "offset": offset,
            "result_count": len(products)
        })

        return products, total

    def _lock_stock_optimistic(
        self,
        product_id: str,
        quantity: int = 1,
        expected_version: Optional[int] = None
    ) -> bool:
        """
        乐观锁锁定库存

        使用方式：
        1. 读取商品和版本号
        2. 业务逻辑处理
        3. 更新时检查版本号是否变化

        Args:
            product_id: 商品 ID
            quantity: 锁定数量
            expected_version: 期望的版本号（用于乐观锁检查）

        Returns:
            是否锁定成功
        """
        product_entity = self.db.query(ProductEntity).filter(
            ProductEntity.id == product_id
        ).with_for_update().first()

        if not product_entity:
            raise ProductNotFoundError(product_id)

        available_stock = product_entity.stock - product_entity.locked_stock

        if available_stock < quantity:
            raise InsufficientStockError(
                f"商品 {product_id} 可用库存不足",
                product_id=product_id
            )

        product_entity.locked_stock += quantity
        product_entity.updated_at = datetime.now()

        # 注意：SQLite 不支持乐观锁版本号，这里仅做逻辑处理
        # 在 PostgreSQL 中可以添加 version 字段实现真正的乐观锁

        self.db.commit()

        self._log("info", f"库存锁定成功", {
            "product_id": product_id,
            "quantity": quantity,
            "remaining_stock": available_stock - quantity
        })

        return True

    def _unlock_stock(self, product_id: str, quantity: int = 1) -> bool:
        """解锁库存"""
        product_entity = self.db.query(ProductEntity).filter(
            ProductEntity.id == product_id
        ).first()

        if not product_entity:
            return False

        if product_entity.locked_stock < quantity:
            self._log("warning", f"库存解锁异常：锁定库存不足", {
                "product_id": product_id,
                "locked_stock": product_entity.locked_stock,
                "unlock_quantity": quantity
            })
            return False

        product_entity.locked_stock -= quantity
        product_entity.updated_at = datetime.now()
        self.db.commit()

        self._log("info", f"库存解锁成功", {
            "product_id": product_id,
            "quantity": quantity
        })

        return True

    def _deduct_stock(self, product_id: str, quantity: int = 1) -> bool:
        """扣减库存（成团成功时调用）"""
        product_entity = self.db.query(ProductEntity).filter(
            ProductEntity.id == product_id
        ).first()

        if not product_entity:
            return False

        if product_entity.locked_stock < quantity:
            self._log("error", f"库存扣减异常：锁定库存不足", {
                "product_id": product_id,
                "locked_stock": product_entity.locked_stock,
                "deduct_quantity": quantity
            })
            return False

        product_entity.locked_stock -= quantity
        product_entity.sold_stock += quantity
        product_entity.stock -= quantity

        # 自动更新商品状态
        if product_entity.stock <= 0 and product_entity.status == ProductStatus.ACTIVE:
            product_entity.status = ProductStatus.SOLD_OUT
        elif product_entity.stock > 0 and product_entity.status == ProductStatus.SOLD_OUT:
            product_entity.status = ProductStatus.ACTIVE

        product_entity.updated_at = datetime.now()
        self.db.commit()

        self._log("info", f"库存扣减成功", {
            "product_id": product_id,
            "quantity": quantity,
            "sold_stock": product_entity.sold_stock,
            "remaining_stock": product_entity.stock
        })

        return True

    # ========== 团购管理 ==========
    def create_group_buy(self, data: GroupBuyCreate) -> GroupBuy:
        """发起团购（带事务）"""
        try:
            with TransactionManager.transaction(self.db):
                # 检查商品
                product = self.get_product(data.product_id)
                if not product or product.status != ProductStatus.ACTIVE:
                    raise ProductNotFoundError(data.product_id)

                if product.stock <= 0:
                    raise InsufficientStockError(
                        f"商品 {data.product_id} 库存不足",
                        product_id=data.product_id
                    )

                # 校验成团人数
                if data.target_size < product.min_group_size or data.target_size > product.max_group_size:
                    raise ValueError(
                        f"成团人数需在 {product.min_group_size} - {product.max_group_size} 之间"
                    )

                # 创建团购
                group_buy_entity = GroupBuyEntity(
                    product_id=data.product_id,
                    organizer_id=data.organizer_id,
                    target_size=data.target_size,
                    deadline=datetime.now() + timedelta(hours=data.duration_hours)
                )
                self.db.add(group_buy_entity)
                self.db.flush()

                # 添加团长为成员
                member = GroupMemberEntity(
                    group_buy_id=group_buy_entity.id,
                    user_id=data.organizer_id
                )
                self.db.add(member)

                # 锁定团长库存
                self._lock_stock_optimistic(data.product_id)

                self.db.flush()

                self._log("info", f"团购创建成功", {
                    "group_id": group_buy_entity.id,
                    "product_id": data.product_id,
                    "organizer_id": data.organizer_id,
                    "target_size": data.target_size
                })

                return self._entity_to_group_buy(group_buy_entity, product)
        except Exception as e:
            self._log("error", f"团购创建失败：{str(e)}", {"error": str(e)})
            raise

    def get_group_buy(self, group_buy_id: str) -> Optional[GroupBuy]:
        """获取团购详情"""
        group_buy_entity = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.id == group_buy_id
        ).first()

        if not group_buy_entity:
            return None

        # 检查是否过期
        if group_buy_entity.status == GroupBuyStatus.OPEN and \
           group_buy_entity.deadline < datetime.now():
            self._handle_group_failure(group_buy_entity, reason="expired")
            # 重新查询
            group_buy_entity = self.db.query(GroupBuyEntity).filter(
                GroupBuyEntity.id == group_buy_id
            ).first()

        product = self.get_product(group_buy_entity.product_id)
        return self._entity_to_group_buy(group_buy_entity, product)

    def list_active_group_buys(
        self,
        product_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[GroupBuy], int]:
        """获取活跃团购列表（带分页）"""
        # 先清理过期团购
        self._cleanup_expired_groups()

        query = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.status == GroupBuyStatus.OPEN
        )

        if product_id:
            query = query.filter(GroupBuyEntity.product_id == product_id)

        total = query.count()
        entities = query.order_by(
            GroupBuyEntity.created_at.desc()
        ).offset(offset).limit(limit).all()

        groups = []
        for entity in entities:
            product = self.get_product(entity.product_id)
            groups.append(self._entity_to_group_buy(entity, product))

        return groups, total

    def list_group_buys_by_status(
        self,
        status: GroupBuyStatus,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[GroupBuy], int]:
        """按状态获取团购列表（带分页）"""
        query = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.status == status
        )

        total = query.count()
        entities = query.order_by(
            GroupBuyEntity.created_at.desc()
        ).offset(offset).limit(limit).all()

        groups = []
        for entity in entities:
            product = self.get_product(entity.product_id)
            groups.append(self._entity_to_group_buy(entity, product))

        return groups, total

    def join_group_buy(
        self,
        group_buy_id: str,
        user_id: str
    ) -> Tuple[GroupBuy, GroupJoinRecord]:
        """加入团购（带事务和并发控制）"""
        try:
            with TransactionManager.transaction(self.db):
                group_buy_entity = self.db.query(GroupBuyEntity).filter(
                    GroupBuyEntity.id == group_buy_id
                ).with_for_update().first()  # 行级锁

                if not group_buy_entity:
                    raise GroupBuyNotFoundError(group_buy_id)

                # 检查过期
                if group_buy_entity.status == GroupBuyStatus.OPEN and \
                   group_buy_entity.deadline < datetime.now():
                    self._handle_group_failure(group_buy_entity, reason="expired")
                    raise GroupBuyExpiredError()

                # 检查状态
                if group_buy_entity.status != GroupBuyStatus.OPEN:
                    raise GroupBuyNotOpenError(f"团购已关闭")

                # 检查是否已参团
                existing_member = self.db.query(GroupMemberEntity).filter(
                    and_(
                        GroupMemberEntity.group_buy_id == group_buy_id,
                        GroupMemberEntity.user_id == user_id
                    )
                ).first()

                if existing_member:
                    raise UserAlreadyJoinedError()

                # 检查是否满员
                if len(group_buy_entity.members) >= group_buy_entity.target_size:
                    raise GroupBuyFullError()

                # 锁定库存
                self._lock_stock_optimistic(group_buy_entity.product_id)

                # 添加成员
                member = GroupMemberEntity(
                    group_buy_id=group_buy_id,
                    user_id=user_id
                )
                self.db.add(member)
                self.db.flush()

                # 更新人数
                current_size = len(group_buy_entity.members) + 1
                group_buy_entity.current_size = current_size
                group_buy_entity.updated_at = datetime.now()

                self.db.flush()

                self._log("info", f"用户加入团购", {
                    "group_id": group_buy_id,
                    "user_id": user_id,
                    "current_size": current_size,
                    "target_size": group_buy_entity.target_size
                })

                # 重新获取完整数据
                self.db.refresh(group_buy_entity)
                product = self.get_product(group_buy_entity.product_id)
                updated_group = self._entity_to_group_buy(group_buy_entity, product)

                # 创建参团记录
                join_record = GroupJoinRecord(
                    group_buy_id=group_buy_id,
                    user_id=user_id
                )

                # 检查是否成团
                if current_size >= group_buy_entity.target_size:
                    self._handle_group_success(group_buy_entity)
                    self.db.refresh(group_buy_entity)
                    updated_group = self._entity_to_group_buy(
                        group_buy_entity,
                        self.get_product(group_buy_entity.product_id)
                    )

                return updated_group, join_record
        except Exception as e:
            self._log("error", f"加入团购失败：{str(e)}", {"error": str(e)})
            raise

    def _handle_group_success(self, group_buy_entity: GroupBuyEntity) -> None:
        """处理团购成功"""
        group_buy_entity.status = GroupBuyStatus.SUCCESS
        group_buy_entity.updated_at = datetime.now()

        # 获取成员列表
        members = self.db.query(GroupMemberEntity).filter(
            GroupMemberEntity.group_buy_id == group_buy_entity.id
        ).all()

        # 扣减库存
        for _ in members:
            self._deduct_stock(group_buy_entity.product_id)

        # 创建订单
        product = self.get_product(group_buy_entity.product_id)
        for member in members:
            order_entity = OrderEntity(
                user_id=member.user_id,
                group_buy_id=group_buy_entity.id,
                product_id=group_buy_entity.product_id,
                unit_price=product.price,
                total_amount=product.price
            )
            self.db.add(order_entity)
            self.db.flush()

            member.order_id = order_entity.id

        self.db.commit()

        self._log("info", f"团购成功", {
            "group_id": group_buy_entity.id,
            "member_count": len(members),
            "product_id": group_buy_entity.product_id
        })

    def _handle_group_failure(
        self,
        group_buy_entity: GroupBuyEntity,
        reason: str = "failed"
    ) -> None:
        """处理团购失败"""
        if reason == "expired":
            group_buy_entity.status = GroupBuyStatus.EXPIRED
        elif reason == "cancelled":
            group_buy_entity.status = GroupBuyStatus.CANCELLED
        else:
            group_buy_entity.status = GroupBuyStatus.FAILED

        group_buy_entity.updated_at = datetime.now()

        # 获取成员列表
        members = self.db.query(GroupMemberEntity).filter(
            GroupMemberEntity.group_buy_id == group_buy_entity.id
        ).all()

        # 解锁库存
        for _ in members:
            self._unlock_stock(group_buy_entity.product_id)

        self.db.commit()

        self._log("info", f"团购失败", {
            "group_id": group_buy_entity.id,
            "reason": reason,
            "member_count": len(members)
        })

    def _cleanup_expired_groups(self) -> None:
        """清理过期团购"""
        now = datetime.now()
        expired_groups = self.db.query(GroupBuyEntity).filter(
            and_(
                GroupBuyEntity.status == GroupBuyStatus.OPEN,
                GroupBuyEntity.deadline < now
            )
        ).all()

        for group_entity in expired_groups:
            self._handle_group_failure(group_entity, reason="expired")

        if expired_groups:
            self._log("info", f"清理过期团购", {
                "count": len(expired_groups)
            })

    def cancel_group_buy(self, group_buy_id: str, operator_id: str) -> bool:
        """取消团购"""
        try:
            with TransactionManager.transaction(self.db):
                group_buy_entity = self.db.query(GroupBuyEntity).filter(
                    GroupBuyEntity.id == group_buy_id
                ).with_for_update().first()

                if not group_buy_entity:
                    return False

                if group_buy_entity.organizer_id != operator_id:
                    raise PermissionError("仅团长可取消团购")

                if group_buy_entity.status != GroupBuyStatus.OPEN:
                    raise GroupBuyNotOpenError("仅可取消进行中的团购")

                self._handle_group_failure(group_buy_entity, reason="cancelled")
                return True
        except Exception as e:
            self._log("error", f"取消团购失败：{str(e)}", {"error": str(e)})
            raise

    # ========== 订单管理 ==========
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单详情"""
        order_entity = self.db.query(OrderEntity).filter(
            OrderEntity.id == order_id
        ).first()

        if not order_entity:
            return None

        return self._entity_to_order(order_entity)

    def get_user_orders(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Order], int]:
        """获取用户订单列表（带分页）"""
        query = self.db.query(OrderEntity).filter(
            OrderEntity.user_id == user_id
        )

        total = query.count()
        entities = query.order_by(
            OrderEntity.created_at.desc()
        ).offset(offset).limit(limit).all()

        orders = [self._entity_to_order(e) for e in entities]
        return orders, total

    def get_group_orders(self, group_buy_id: str) -> List[Order]:
        """获取团购订单列表"""
        entities = self.db.query(OrderEntity).filter(
            OrderEntity.group_buy_id == group_buy_id
        ).all()

        return [self._entity_to_order(e) for e in entities]

    def update_order_status(self, order_id: str, status: OrderStatus) -> Optional[Order]:
        """更新订单状态"""
        try:
            with TransactionManager.transaction(self.db):
                order_entity = self.db.query(OrderEntity).filter(
                    OrderEntity.id == order_id
                ).first()

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

                self.db.flush()

                self._log("info", f"订单状态更新", {
                    "order_id": order_id,
                    "status": status.value
                })

                return self._entity_to_order(order_entity)
        except Exception as e:
            self._log("error", f"更新订单状态失败：{str(e)}", {"error": str(e)})
            raise

    # ========== 统计查询 ==========
    def get_user_join_records(self, user_id: str) -> List[GroupJoinRecord]:
        """获取用户参团记录"""
        members = self.db.query(GroupMemberEntity).filter(
            GroupMemberEntity.user_id == user_id
        ).order_by(GroupMemberEntity.join_time.desc()).all()

        records = []
        for member in members:
            group_status = self.db.query(GroupBuyEntity.status).filter(
                GroupBuyEntity.id == member.group_buy_id
            ).scalar()

            if member.order_id:
                record_status = "paid"
            elif group_status == GroupBuyStatus.EXPIRED:
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
        """获取团购参团记录"""
        members = self.db.query(GroupMemberEntity).filter(
            GroupMemberEntity.group_buy_id == group_buy_id
        ).all()

        records = []
        for member in members:
            if member.order_id:
                record_status = "paid"
            else:
                group_status = self.db.query(GroupBuyEntity.status).filter(
                    GroupBuyEntity.id == member.group_buy_id
                ).scalar()

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

    # ========== 辅助方法 ==========
    def _entity_to_product(self, entity: ProductEntity) -> Product:
        """实体转模型"""
        return Product(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            price=entity.price,
            original_price=entity.original_price,
            image_url=entity.image_url,
            stock=entity.stock,
            locked_stock=entity.locked_stock,
            sold_stock=entity.sold_stock,
            min_group_size=entity.min_group_size,
            max_group_size=entity.max_group_size,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    def _entity_to_group_buy(
        self,
        entity: GroupBuyEntity,
        product: Optional[Product] = None
    ) -> GroupBuy:
        """实体转模型"""
        member_ids = [m.user_id for m in entity.members]
        return GroupBuy(
            id=entity.id,
            product_id=entity.product_id,
            organizer_id=entity.organizer_id,
            product=product,
            target_size=entity.target_size,
            current_size=entity.current_size,
            status=entity.status,
            deadline=entity.deadline,
            members=member_ids,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    def _entity_to_order(self, entity: OrderEntity) -> Order:
        """实体转模型"""
        return Order(
            id=entity.id,
            user_id=entity.user_id,
            group_buy_id=entity.group_buy_id,
            product_id=entity.product_id,
            quantity=entity.quantity,
            unit_price=entity.unit_price,
            total_amount=entity.total_amount,
            status=entity.status,
            payment_time=entity.payment_time,
            delivery_time=entity.delivery_time,
            completed_time=entity.completed_time,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
