"""
P4 供应链服务 - 供应商管理服务
负责供应商信息管理、评估、供应商商品管理
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import logging

from models.p4_entities import SupplierEntity, SupplierProductEntity
from models.entities import ProductEntity
from models.p4_models import SupplierStats
from core.logging_config import get_logger

logger = get_logger("services.p4.supplier")


class SupplierService:
    """供应商管理服务"""

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

    def create_supplier(self, data: dict) -> Tuple[Optional[SupplierEntity], bool]:
        """
        创建供应商

        Args:
            data: 包含 name, contact_person, contact_phone, contact_email, address, category 等

        Returns:
            (供应商实体，是否成功)
        """
        try:
            supplier = SupplierEntity(
                name=data["name"],
                contact_person=data.get("contact_person"),
                contact_phone=data.get("contact_phone"),
                contact_email=data.get("contact_email"),
                address=data.get("address"),
                category=data.get("category"),
                rating=data.get("rating", 5.0),
                payment_terms_days=data.get("payment_terms_days", 7),
                min_order_amount=data.get("min_order_amount", 0.0),
                delivery_lead_days=data.get("delivery_lead_days", 3)
            )

            self.db.add(supplier)
            self.db.commit()
            self.db.refresh(supplier)

            self._log("info", "供应商创建成功", {
                "supplier_id": supplier.id,
                "supplier_name": supplier.name
            })

            return supplier, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建供应商失败：{str(e)}", {"data": data})
            return None, False

    def get_supplier(self, supplier_id: str) -> Optional[SupplierEntity]:
        """获取供应商详情"""
        return self.db.query(SupplierEntity).filter(
            SupplierEntity.id == supplier_id
        ).first()

    def list_suppliers(self, category: str = None, is_active: bool = True,
                       limit: int = 100) -> List[SupplierEntity]:
        """获取供应商列表"""
        query = self.db.query(SupplierEntity)

        if category:
            query = query.filter(SupplierEntity.category == category)
        if is_active is not None:
            query = query.filter(SupplierEntity.is_active == is_active)

        return query.order_by(SupplierEntity.rating.desc()).limit(limit).all()

    def update_supplier(self, supplier_id: str, data: dict) -> Tuple[Optional[SupplierEntity], bool]:
        """
        更新供应商

        Args:
            supplier_id: 供应商 ID
            data: 更新数据

        Returns:
            (供应商实体，是否成功)
        """
        try:
            supplier = self.db.query(SupplierEntity).filter(
                SupplierEntity.id == supplier_id
            ).first()

            if not supplier:
                self._log("error", "供应商不存在", {"supplier_id": supplier_id})
                return None, False

            # 更新字段
            updatable_fields = [
                "name", "contact_person", "contact_phone", "contact_email",
                "address", "category", "rating", "payment_terms_days",
                "min_order_amount", "delivery_lead_days", "is_active"
            ]

            for field in updatable_fields:
                if field in data:
                    setattr(supplier, field, data[field])

            supplier.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(supplier)

            self._log("info", "供应商更新成功", {"supplier_id": supplier_id})

            return supplier, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"更新供应商失败：{str(e)}", {"supplier_id": supplier_id})
            return None, False

    def delete_supplier(self, supplier_id: str) -> bool:
        """
        删除供应商（软删除）

        Args:
            supplier_id: 供应商 ID

        Returns:
            是否成功
        """
        try:
            supplier = self.db.query(SupplierEntity).filter(
                SupplierEntity.id == supplier_id
            ).first()

            if not supplier:
                self._log("error", "供应商不存在", {"supplier_id": supplier_id})
                return False

            supplier.is_active = False
            supplier.updated_at = datetime.now()

            self.db.commit()

            self._log("info", "供应商已停用", {"supplier_id": supplier_id})

            return True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"停用供应商失败：{str(e)}", {"supplier_id": supplier_id})
            return False

    def update_supplier_metrics(self, supplier_id: str,
                                 order_amount: float = 0,
                                 on_time: bool = True,
                                 quality_passed: bool = True,
                                 response_hours: float = 24.0) -> Tuple[Optional[SupplierEntity], bool]:
        """
        更新供应商指标

        Args:
            supplier_id: 供应商 ID
            order_amount: 订单金额
            on_time: 是否准时交付
            quality_passed: 质量是否合格
            response_hours: 响应时间（小时）

        Returns:
            (供应商实体，是否成功)
        """
        try:
            supplier = self.db.query(SupplierEntity).filter(
                SupplierEntity.id == supplier_id
            ).first()

            if not supplier:
                self._log("error", "供应商不存在", {"supplier_id": supplier_id})
                return None, False

            # 更新累计指标
            supplier.total_orders += 1
            supplier.total_amount += order_amount

            # 更新速率指标（移动平均）
            total_orders = supplier.total_orders
            if total_orders == 1:
                supplier.on_time_delivery_rate = 1.0 if on_time else 0.0
                supplier.quality_pass_rate = 1.0 if quality_passed else 0.0
                supplier.response_time_hours = response_hours
            else:
                # 简单移动平均
                supplier.on_time_delivery_rate = (
                    (supplier.on_time_delivery_rate * (total_orders - 1)) + (1.0 if on_time else 0.0)
                ) / total_orders
                supplier.quality_pass_rate = (
                    (supplier.quality_pass_rate * (total_orders - 1)) + (1.0 if quality_passed else 0.0)
                ) / total_orders
                supplier.response_time_hours = (
                    (supplier.response_time_hours * (total_orders - 1)) + response_hours
                ) / total_orders

            supplier.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(supplier)

            self._log("info", "供应商标标更新成功", {
                "supplier_id": supplier_id,
                "total_orders": supplier.total_orders
            })

            return supplier, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"更新供应商标标失败：{str(e)}", {"supplier_id": supplier_id})
            return None, False

    def add_supplier_product(self, supplier_id: str, data: dict) -> Tuple[Optional[SupplierProductEntity], bool]:
        """
        添加供应商商品

        Args:
            supplier_id: 供应商 ID
            data: 包含 product_id, cost_price, min_order_quantity, lead_days 等

        Returns:
            (供应商商品实体，是否成功)
        """
        try:
            # 验证供应商是否存在
            supplier = self.db.query(SupplierEntity).filter(
                SupplierEntity.id == supplier_id
            ).first()

            if not supplier:
                self._log("error", "供应商不存在", {"supplier_id": supplier_id})
                return None, False

            # 验证商品是否存在
            product = self.db.query(ProductEntity).filter(
                ProductEntity.id == data["product_id"]
            ).first()

            if not product:
                self._log("error", "商品不存在", {"product_id": data["product_id"]})
                return None, False

            # 检查是否已存在该商品关系
            existing = self.db.query(SupplierProductEntity).filter(
                and_(
                    SupplierProductEntity.supplier_id == supplier_id,
                    SupplierProductEntity.product_id == data["product_id"]
                )
            ).first()

            if existing:
                self._log("info", "供应商商品关系已存在", {
                    "supplier_id": supplier_id,
                    "product_id": data["product_id"]
                })
                return existing, True

            # 创建供应商商品关系
            supplier_product = SupplierProductEntity(
                supplier_id=supplier_id,
                product_id=data["product_id"],
                supplier_product_name=data.get("supplier_product_name", product.name),
                supplier_product_code=data.get("supplier_product_code"),
                cost_price=data["cost_price"],
                min_order_quantity=data.get("min_order_quantity", 1),
                lead_days=data.get("lead_days", 3),
                is_preferred=data.get("is_preferred", False)
            )

            self.db.add(supplier_product)
            self.db.commit()
            self.db.refresh(supplier_product)

            self._log("info", "供应商商品添加成功", {
                "supplier_id": supplier_id,
                "product_id": data["product_id"]
            })

            return supplier_product, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"添加供应商商品失败：{str(e)}", {"supplier_id": supplier_id, "data": data})
            return None, False

    def get_supplier_products(self, supplier_id: str,
                               is_active: bool = True) -> List[SupplierProductEntity]:
        """获取供应商商品列表"""
        query = self.db.query(SupplierProductEntity).filter(
            SupplierProductEntity.supplier_id == supplier_id
        )

        if is_active is not None:
            query = query.filter(SupplierProductEntity.is_active == is_active)

        return query.all()

    def get_preferred_suppliers(self, product_id: str) -> List[SupplierEntity]:
        """
        获取商品的首选供应商

        Args:
            product_id: 商品 ID

        Returns:
            首选供应商列表
        """
        suppliers = self.db.query(SupplierEntity).join(
            SupplierProductEntity, SupplierEntity.id == SupplierProductEntity.supplier_id
        ).filter(
            SupplierProductEntity.product_id == product_id,
            SupplierProductEntity.is_preferred == True,
            SupplierEntity.is_active == True
        ).order_by(SupplierEntity.rating.desc()).all()

        return suppliers

    def search_suppliers(self, keyword: str = None, category: str = None,
                         min_rating: float = 0.0) -> List[SupplierEntity]:
        """
        搜索供应商

        Args:
            keyword: 关键词
            category: 品类
            min_rating: 最低评分

        Returns:
            供应商列表
        """
        query = self.db.query(SupplierEntity).filter(SupplierEntity.is_active == True)

        if keyword:
            query = query.filter(
                (SupplierEntity.name.contains(keyword)) |
                (SupplierEntity.contact_person.contains(keyword))
            )

        if category:
            query = query.filter(SupplierEntity.category == category)

        if min_rating > 0:
            query = query.filter(SupplierEntity.rating >= min_rating)

        return query.order_by(SupplierEntity.rating.desc()).all()

    def get_supplier_stats(self, supplier_id: str = None) -> Dict:
        """
        获取供应商统计

        Args:
            supplier_id: 供应商 ID（可选）

        Returns:
            统计字典
        """
        query = self.db.query(SupplierEntity)

        if supplier_id:
            supplier = query.filter(SupplierEntity.id == supplier_id).first()
            if not supplier:
                return {}
            return {
                "supplier_id": supplier_id,
                "supplier_name": supplier.name,
                "total_orders": supplier.total_orders,
                "total_amount": supplier.total_amount,
                "on_time_delivery_rate": supplier.on_time_delivery_rate,
                "quality_pass_rate": supplier.quality_pass_rate,
                "rating": supplier.rating
            }

        # 总体统计
        return {
            "total_suppliers": query.count(),
            "active_suppliers": query.filter(SupplierEntity.is_active == True).count(),
            "avg_rating": query.with_entities(func.avg(SupplierEntity.rating)).scalar() or 0.0,
            "avg_delivery_rate": query.with_entities(func.avg(SupplierEntity.on_time_delivery_rate)).scalar() or 0.0,
            "avg_quality_rate": query.with_entities(func.avg(SupplierEntity.quality_pass_rate)).scalar() or 0.0
        }

    def get_top_suppliers(self, limit: int = 10) -> List[SupplierEntity]:
        """
        获取顶级供应商（按评分和订单量）

        Args:
            limit: 返回数量上限

        Returns:
            顶级供应商列表
        """
        return self.db.query(SupplierEntity).filter(
            SupplierEntity.is_active == True
        ).order_by(
            SupplierEntity.rating.desc(),
            SupplierEntity.total_orders.desc()
        ).limit(limit).all()
