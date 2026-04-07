"""
P4 供应链服务 - 采购订单管理服务
负责采购订单创建、状态管理、收货管理
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import logging

from models.p4_entities import (
    PurchaseOrderEntity, PurchaseOrderLineEntity,
    SupplierEntity, SupplierProductEntity
)
from models.entities import ProductEntity
from models.p4_models import PurchaseOrderStatus, OrderLineStatus, TransactionType
from core.logging_config import get_logger

logger = get_logger("services.p4.purchase_order")


class PurchaseOrderService:
    """采购订单管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""

    def set_request_context(self, request_id: str, user_id: str = ""):
        """设置请求上下文"""
        self.request_id = request_id
        self.user_id = user_id

    def _log(self, level: str, message: str, extra: dict = None):
        """结构化日志"""
        log_data = {"request_id": self.request_id, "user_id": self.user_id}
        if extra:
            log_data.update(extra)
        getattr(self.logger, level)(message, extra=log_data)

    def _generate_order_no(self) -> str:
        """生成采购单号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        import random
        suffix = str(random.randint(1000, 9999))
        return f"PO{timestamp}{suffix}"

    def create_purchase_order(self, data: dict, lines: List[dict],
                               created_by: str = None) -> Tuple[Optional[PurchaseOrderEntity], bool]:
        """
        创建采购订单

        Args:
            data: 包含 supplier_id, community_id, expected_delivery_date, delivery_address 等
            lines: 订单明细列表，每项包含 product_id, quantity, unit_cost
            created_by: 创建人 ID

        Returns:
            (采购订单实体，是否成功)
        """
        try:
            # 验证供应商是否存在
            supplier = self.db.query(SupplierEntity).filter(
                SupplierEntity.id == data["supplier_id"]
            ).first()

            if not supplier:
                self._log("error", "供应商不存在", {"supplier_id": data["supplier_id"]})
                return None, False

            # 创建采购订单
            order = PurchaseOrderEntity(
                order_no=self._generate_order_no(),
                supplier_id=data["supplier_id"],
                community_id=data["community_id"],
                expected_delivery_date=data.get("expected_delivery_date"),
                delivery_address=data.get("delivery_address"),
                receiver_name=data.get("receiver_name"),
                receiver_phone=data.get("receiver_phone"),
                notes=data.get("notes"),
                status=PurchaseOrderStatus.DRAFT.value,
                created_by=created_by
            )

            self.db.add(order)
            self.db.flush()  # 获取 order.id

            # 创建订单明细
            total_quantity = 0
            total_amount = 0.0

            for line_data in lines:
                # 验证商品是否存在
                product = self.db.query(ProductEntity).filter(
                    ProductEntity.id == line_data["product_id"]
                ).first()

                if not product:
                    self._log("error", "商品不存在", {"product_id": line_data["product_id"]})
                    continue

                line = PurchaseOrderLineEntity(
                    order_id=order.id,
                    product_id=line_data["product_id"],
                    quantity=line_data["quantity"],
                    unit_cost=line_data["unit_cost"],
                    line_total=line_data["quantity"] * line_data["unit_cost"]
                )

                if "supplier_product_id" in line_data:
                    line.supplier_product_id = line_data["supplier_product_id"]

                self.db.add(line)

                total_quantity += line_data["quantity"]
                total_amount += line.line_total

            # 更新订单总计
            order.total_quantity = total_quantity
            order.total_amount = total_amount

            self.db.commit()
            self.db.refresh(order)

            self._log("info", "采购订单创建成功", {
                "order_id": order.id,
                "order_no": order.order_no,
                "total_amount": total_amount
            })

            return order, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建采购订单失败：{str(e)}", {"data": data})
            return None, False

    def get_order(self, order_id: str) -> Optional[PurchaseOrderEntity]:
        """获取采购订单详情"""
        return self.db.query(PurchaseOrderEntity).filter(
            PurchaseOrderEntity.id == order_id
        ).first()

    def get_order_by_no(self, order_no: str) -> Optional[PurchaseOrderEntity]:
        """根据单号获取采购订单"""
        return self.db.query(PurchaseOrderEntity).filter(
            PurchaseOrderEntity.order_no == order_no
        ).first()

    def list_orders(self, supplier_id: str = None, community_id: str = None,
                    status: str = None, limit: int = 100) -> List[PurchaseOrderEntity]:
        """获取采购订单列表"""
        query = self.db.query(PurchaseOrderEntity)

        if supplier_id:
            query = query.filter(PurchaseOrderEntity.supplier_id == supplier_id)
        if community_id:
            query = query.filter(PurchaseOrderEntity.community_id == community_id)
        if status:
            query = query.filter(PurchaseOrderEntity.status == status)

        return query.order_by(PurchaseOrderEntity.created_at.desc()).limit(limit).all()

    def submit_order(self, order_id: str) -> Tuple[Optional[PurchaseOrderEntity], bool]:
        """
        提交采购订单（从草稿到已提交）

        Args:
            order_id: 订单 ID

        Returns:
            (采购订单实体，是否成功)
        """
        try:
            order = self.db.query(PurchaseOrderEntity).filter(
                PurchaseOrderEntity.id == order_id
            ).first()

            if not order:
                self._log("error", "采购订单不存在", {"order_id": order_id})
                return None, False

            if order.status != PurchaseOrderStatus.DRAFT.value:
                self._log("error", "只有草稿状态的订单可以提交", {
                    "order_id": order_id,
                    "current_status": order.status
                })
                return None, False

            order.status = PurchaseOrderStatus.SUBMITTED.value
            order.submitted_at = datetime.now()
            order.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(order)

            self._log("info", "采购订单已提交", {"order_id": order_id})

            return order, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"提交采购订单失败：{str(e)}", {"order_id": order_id})
            return None, False

    def confirm_order(self, order_id: str) -> Tuple[Optional[PurchaseOrderEntity], bool]:
        """
        确认采购订单

        Args:
            order_id: 订单 ID

        Returns:
            (采购订单实体，是否成功)
        """
        try:
            order = self.db.query(PurchaseOrderEntity).filter(
                PurchaseOrderEntity.id == order_id
            ).first()

            if not order:
                self._log("error", "采购订单不存在", {"order_id": order_id})
                return None, False

            if order.status != PurchaseOrderStatus.SUBMITTED.value:
                self._log("error", "只有已提交状态的订单可以确认", {
                    "order_id": order_id,
                    "current_status": order.status
                })
                return None, False

            order.status = PurchaseOrderStatus.CONFIRMED.value
            order.confirmed_at = datetime.now()
            order.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(order)

            self._log("info", "采购订单已确认", {"order_id": order_id})

            return order, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"确认采购订单失败：{str(e)}", {"order_id": order_id})
            return None, False

    def ship_order(self, order_id: str) -> Tuple[Optional[PurchaseOrderEntity], bool]:
        """
        发货采购订单

        Args:
            order_id: 订单 ID

        Returns:
            (采购订单实体，是否成功)
        """
        try:
            order = self.db.query(PurchaseOrderEntity).filter(
                PurchaseOrderEntity.id == order_id
            ).first()

            if not order:
                self._log("error", "采购订单不存在", {"order_id": order_id})
                return None, False

            if order.status != PurchaseOrderStatus.CONFIRMED.value:
                self._log("error", "只有已确认状态的订单可以发货", {
                    "order_id": order_id,
                    "current_status": order.status
                })
                return None, False

            order.status = PurchaseOrderStatus.SHIPPING.value
            order.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(order)

            self._log("info", "采购订单已发货", {"order_id": order_id})

            return order, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"发货采购订单失败：{str(e)}", {"order_id": order_id})
            return None, False

    def receive_order(self, order_id: str, lines: List[dict],
                      receiver_id: str = None) -> Tuple[Optional[PurchaseOrderEntity], bool]:
        """
        收货采购订单

        Args:
            order_id: 订单 ID
            lines: 收货明细，每项包含 line_id, received_quantity, quality_check_quantity, rejected_quantity
            receiver_id: 收货人 ID

        Returns:
            (采购订单实体，是否成功)
        """
        try:
            order = self.db.query(PurchaseOrderEntity).filter(
                PurchaseOrderEntity.id == order_id
            ).first()

            if not order:
                self._log("error", "采购订单不存在", {"order_id": order_id})
                return None, False

            if order.status not in [PurchaseOrderStatus.CONFIRMED.value, PurchaseOrderStatus.SHIPPING.value]:
                self._log("error", "只有已确认或配送中的订单可以收货", {
                    "order_id": order_id,
                    "current_status": order.status
                })
                return None, False

            # 更新订单明细
            all_completed = True
            for line_data in lines:
                line = self.db.query(PurchaseOrderLineEntity).filter(
                    PurchaseOrderLineEntity.id == line_data["line_id"]
                ).first()

                if not line:
                    continue

                line.received_quantity = line_data.get("received_quantity", line.quantity)
                line.quality_check_quantity = line_data.get("quality_check_quantity", line.received_quantity)
                line.rejected_quantity = line_data.get("rejected_quantity", 0)

                if line_data.get("quality_issue_reason"):
                    line.quality_issue_reason = line_data["quality_issue_reason"]

                # 更新状态
                if line.received_quantity >= line.quantity:
                    line.status = OrderLineStatus.COMPLETED.value
                elif line.received_quantity > 0:
                    line.status = OrderLineStatus.PARTIAL.value
                else:
                    all_completed = False

                line.updated_at = datetime.now()

            # 检查是否所有明细都已完成
            if all_completed:
                order.status = PurchaseOrderStatus.RECEIVED.value
                order.received_at = datetime.now()
                order.actual_delivery_date = datetime.now()

            order.receiver_id = receiver_id
            order.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(order)

            self._log("info", "采购订单已收货", {"order_id": order_id})

            return order, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"收货采购订单失败：{str(e)}", {"order_id": order_id})
            return None, False

    def cancel_order(self, order_id: str, reason: str,
                     cancelled_by: str = None) -> Tuple[Optional[PurchaseOrderEntity], bool]:
        """
        取消采购订单

        Args:
            order_id: 订单 ID
            reason: 取消原因
            cancelled_by: 取消人 ID

        Returns:
            (采购订单实体，是否成功)
        """
        try:
            order = self.db.query(PurchaseOrderEntity).filter(
                PurchaseOrderEntity.id == order_id
            ).first()

            if not order:
                self._log("error", "采购订单不存在", {"order_id": order_id})
                return None, False

            if order.status in [PurchaseOrderStatus.RECEIVED.value, PurchaseOrderStatus.CANCELLED.value]:
                self._log("error", "已收货或已取消的订单不能取消", {
                    "order_id": order_id,
                    "current_status": order.status
                })
                return None, False

            order.status = PurchaseOrderStatus.CANCELLED.value
            order.cancel_reason = reason
            order.cancelled_at = datetime.now()
            order.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(order)

            self._log("info", "采购订单已取消", {"order_id": order_id, "reason": reason})

            return order, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"取消采购订单失败：{str(e)}", {"order_id": order_id})
            return None, False

    def get_order_lines(self, order_id: str) -> List[PurchaseOrderLineEntity]:
        """获取订单明细列表"""
        return self.db.query(PurchaseOrderLineEntity).filter(
            PurchaseOrderLineEntity.order_id == order_id
        ).all()

    def get_order_stats(self, supplier_id: str = None,
                        community_id: str = None) -> Dict:
        """
        获取采购订单统计

        Args:
            supplier_id: 供应商 ID
            community_id: 社区 ID

        Returns:
            统计字典
        """
        query = self.db.query(PurchaseOrderEntity)

        if supplier_id:
            query = query.filter(PurchaseOrderEntity.supplier_id == supplier_id)
        if community_id:
            query = query.filter(PurchaseOrderEntity.community_id == community_id)

        return {
            "total": query.count(),
            "draft": query.filter(PurchaseOrderEntity.status == PurchaseOrderStatus.DRAFT.value).count(),
            "submitted": query.filter(PurchaseOrderEntity.status == PurchaseOrderStatus.SUBMITTED.value).count(),
            "confirmed": query.filter(PurchaseOrderEntity.status == PurchaseOrderStatus.CONFIRMED.value).count(),
            "shipping": query.filter(PurchaseOrderEntity.status == PurchaseOrderStatus.SHIPPING.value).count(),
            "received": query.filter(PurchaseOrderEntity.status == PurchaseOrderStatus.RECEIVED.value).count(),
            "cancelled": query.filter(PurchaseOrderEntity.status == PurchaseOrderStatus.CANCELLED.value).count(),
            "total_amount": query.with_entities(func.sum(PurchaseOrderEntity.total_amount)).scalar() or 0.0
        }
