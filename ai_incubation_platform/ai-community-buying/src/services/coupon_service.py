"""
优惠券服务 - 优惠券创建、领取、使用和核销
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid
import logging

from models.entities import (
    CouponTemplateEntity, CouponEntity, ProductEntity
)
from models.product import (
    CouponTemplate, Coupon, CouponStatus, CouponType
)

logger = logging.getLogger(__name__)


class CouponService:
    """优惠券服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== 优惠券模板管理 ==========

    def create_template(self, data: Dict) -> CouponTemplate:
        """创建优惠券模板"""
        template = CouponTemplateEntity(
            name=data["name"],
            type=data.get("type", "fixed"),
            value=data["value"],
            min_purchase=data.get("min_purchase", 0.0),
            max_discount=data.get("max_discount"),
            total_quantity=data.get("total_quantity", 1000),
            issued_quantity=0,
            used_quantity=0,
            valid_from=data["valid_from"],
            valid_to=data["valid_to"],
            applicable_products=data.get("applicable_products"),
            applicable_categories=data.get("applicable_categories"),
            user_limit=data.get("user_limit", 1),
            is_active=data.get("is_active", True)
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)

        logger.info(f"优惠券模板创建成功：{template.id} - {template.name}")
        return self._template_entity_to_model(template)

    def get_template(self, template_id: str) -> Optional[CouponTemplate]:
        """获取优惠券模板详情"""
        template = self.db.query(CouponTemplateEntity).filter(
            CouponTemplateEntity.id == template_id
        ).first()
        return self._template_entity_to_model(template) if template else None

    def list_templates(
        self,
        active_only: bool = True,
        limit: int = 50
    ) -> List[CouponTemplate]:
        """获取优惠券模板列表"""
        query = self.db.query(CouponTemplateEntity)
        if active_only:
            query = query.filter(CouponTemplateEntity.is_active == True)
        templates = query.order_by(
            CouponTemplateEntity.valid_from.desc()
        ).limit(limit).all()
        return [self._template_entity_to_model(t) for t in templates]

    def update_template(self, template_id: str, updates: Dict) -> Optional[CouponTemplate]:
        """更新优惠券模板"""
        template = self.db.query(CouponTemplateEntity).filter(
            CouponTemplateEntity.id == template_id
        ).first()
        if not template:
            return None

        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)

        self.db.commit()
        self.db.refresh(template)
        return self._template_entity_to_model(template)

    def delete_template(self, template_id: str) -> bool:
        """删除优惠券模板（软删除，设为不活跃）"""
        template = self.db.query(CouponTemplateEntity).filter(
            CouponTemplateEntity.id == template_id
        ).first()
        if not template:
            return False

        template.is_active = False
        self.db.commit()
        return True

    # ========== 优惠券领取 ==========

    def claim_coupon(self, user_id: str, template_id: str) -> Dict:
        """用户领取优惠券"""
        template = self.db.query(CouponTemplateEntity).filter(
            CouponTemplateEntity.id == template_id
        ).first()

        if not template:
            return {"success": False, "error": "优惠券模板不存在"}

        if not template.is_active:
            return {"success": False, "error": "优惠券模板已停用"}

        # 检查发放总量
        if template.issued_quantity >= template.total_quantity:
            return {"success": False, "error": "优惠券已领完"}

        # 检查每人限领
        if template.user_limit > 0:
            user_count = self.db.query(CouponEntity).filter(
                CouponEntity.user_id == user_id,
                CouponEntity.template_id == template_id
            ).count()
            if user_count >= template.user_limit:
                return {"success": False, "error": f"每人限领{template.user_limit}张"}

        # 检查有效期
        now = datetime.now()
        if now < template.valid_from:
            return {"success": False, "error": "优惠券尚未开始发放"}
        if now > template.valid_to:
            return {"success": False, "error": "优惠券已过期"}

        # 生成优惠券码
        coupon_code = self._generate_coupon_code(template_id, user_id)

        # 创建优惠券
        coupon = CouponEntity(
            user_id=user_id,
            template_id=template_id,
            code=coupon_code,
            status="available",
            valid_from=template.valid_from,
            valid_to=template.valid_to
        )
        self.db.add(coupon)

        # 更新模板发放数量
        template.issued_quantity += 1

        self.db.commit()
        self.db.refresh(coupon)

        logger.info(
            f"优惠券领取成功：用户 {user_id}, 模板 {template_id}, 券码 {coupon_code}"
        )
        return {
            "success": True,
            "coupon": self._coupon_entity_to_model(coupon),
            "template_name": template.name
        }

    def _generate_coupon_code(self, template_id: str, user_id: str) -> str:
        """生成唯一优惠券码"""
        unique_id = uuid.uuid4().hex[:8].upper()
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"CPN-{timestamp}-{unique_id}"

    # ========== 优惠券使用 ==========

    def use_coupon(
        self,
        user_id: str,
        coupon_id: str,
        order_amount: float
    ) -> Dict:
        """用户使用优惠券"""
        coupon = self.db.query(CouponEntity).filter(
            CouponEntity.id == coupon_id,
            CouponEntity.user_id == user_id
        ).first()

        if not coupon:
            return {"success": False, "error": "优惠券不存在"}

        if coupon.status != "available":
            return {"success": False, "error": f"优惠券状态不可用：{coupon.status}"}

        # 检查有效期
        now = datetime.now()
        if now < coupon.valid_from or now > coupon.valid_to:
            coupon.status = "expired"
            self.db.commit()
            return {"success": False, "error": "优惠券已过期"}

        # 获取模板信息
        template = self.db.query(CouponTemplateEntity).filter(
            CouponTemplateEntity.id == coupon.template_id
        ).first()
        if not template:
            return {"success": False, "error": "优惠券模板不存在"}

        # 检查最低消费金额
        if order_amount < template.min_purchase:
            return {
                "success": False,
                "error": f"订单金额需满{template.min_purchase}元可用"
            }

        # 检查适用商品
        if template.applicable_products:
            # 这里简化处理，实际需要检查订单中的商品
            import json
            applicable_products = json.loads(template.applicable_products)
            # 如果需要检查商品，调用方需要传入商品 ID 列表

        # 计算优惠金额
        discount_amount = self._calculate_discount(
            template=template,
            order_amount=order_amount
        )

        # 更新优惠券状态
        coupon.status = "used"
        coupon.used_at = now

        # 更新模板使用数量
        template.used_quantity += 1

        self.db.commit()

        logger.info(
            f"优惠券使用成功：用户 {user_id}, 券码 {coupon.code}, "
            f"订单金额 {order_amount}, 优惠 {discount_amount}"
        )
        return {
            "success": True,
            "discount_amount": discount_amount,
            "coupon_code": coupon.code,
            "order_amount": order_amount,
            "final_amount": order_amount - discount_amount
        }

    def _calculate_discount(
        self,
        template: CouponTemplateEntity,
        order_amount: float
    ) -> float:
        """计算优惠金额"""
        if template.type == "fixed":
            # 满减券：直接减免固定金额
            discount = template.value
        elif template.type == "discount":
            # 折扣券：按比例折扣
            discount = order_amount * template.value

            # 应用最大优惠金额限制
            if template.max_discount and discount > template.max_discount:
                discount = template.max_discount
        else:
            discount = 0

        # 确保优惠金额不超过订单金额
        discount = min(discount, order_amount)

        return round(discount, 2)

    # ========== 优惠券查询 ==========

    def get_coupon(self, coupon_id: str) -> Optional[Coupon]:
        """获取优惠券详情"""
        coupon = self.db.query(CouponEntity).filter(
            CouponEntity.id == coupon_id
        ).first()
        return self._coupon_entity_to_model(coupon) if coupon else None

    def get_user_coupons(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Coupon]:
        """获取用户的优惠券列表"""
        query = self.db.query(CouponEntity).filter(
            CouponEntity.user_id == user_id
        )

        if status:
            query = query.filter(CouponEntity.status == status)

        coupons = query.order_by(
            CouponEntity.valid_to.desc()
        ).limit(limit).all()

        return [self._coupon_entity_to_model(c) for c in coupons]

    def get_coupon_by_code(self, code: str) -> Optional[Coupon]:
        """通过券码获取优惠券"""
        coupon = self.db.query(CouponEntity).filter(
            CouponEntity.code == code
        ).first()
        return self._coupon_entity_to_model(coupon) if coupon else None

    def list_available_coupons_for_order(
        self,
        user_id: str,
        order_amount: float,
        product_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """获取订单可用的优惠券列表"""
        coupons = self.get_user_coupons(user_id, status="available")
        now = datetime.now()

        available = []
        for coupon in coupons:
            # 检查有效期
            if coupon.valid_from > now or coupon.valid_to < now:
                continue

            # 获取模板信息
            template = self.get_template(coupon.template_id)
            if not template or not template.is_active:
                continue

            # 检查最低消费金额
            if order_amount < template.min_purchase:
                continue

            # 检查适用商品
            if product_ids and template.applicable_products:
                import json
                applicable = json.loads(template.applicable_products)
                if not any(pid in applicable for pid in product_ids):
                    continue

            # 计算优惠金额
            discount = self._calculate_discount(
                self.db.query(CouponTemplateEntity).filter(
                    CouponTemplateEntity.id == template.id
                ).first(),
                order_amount
            )

            available.append({
                "coupon": coupon,
                "template": template,
                "discount_amount": discount
            })

        # 按优惠金额排序
        available.sort(key=lambda x: x["discount_amount"], reverse=True)
        return available

    # ========== 过期处理 ==========

    def expire_unused_coupons(self) -> int:
        """过期未使用的优惠券"""
        now = datetime.now()

        coupons = self.db.query(CouponEntity).filter(
            CouponEntity.status == "available",
            CouponEntity.valid_to < now
        ).all()

        count = 0
        for coupon in coupons:
            coupon.status = "expired"
            count += 1

        if count > 0:
            self.db.commit()
            logger.info(f"过期优惠券处理完成：{count}张")

        return count

    # ========== 工具方法 ==========

    def _template_entity_to_model(self, entity: CouponTemplateEntity) -> CouponTemplate:
        """实体转模型"""
        import json
        return CouponTemplate(
            id=entity.id,
            name=entity.name,
            type=CouponType(entity.type),
            value=entity.value,
            min_purchase=entity.min_purchase,
            max_discount=entity.max_discount,
            total_quantity=entity.total_quantity,
            issued_quantity=entity.issued_quantity,
            used_quantity=entity.used_quantity,
            valid_from=entity.valid_from,
            valid_to=entity.valid_to,
            applicable_products=json.loads(entity.applicable_products) if entity.applicable_products else None,
            applicable_categories=json.loads(entity.applicable_categories) if entity.applicable_categories else None,
            user_limit=entity.user_limit,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    def _coupon_entity_to_model(self, entity: CouponEntity) -> Coupon:
        """实体转模型"""
        return Coupon(
            id=entity.id,
            user_id=entity.user_id,
            template_id=entity.template_id,
            code=entity.code,
            status=CouponStatus(entity.status),
            order_id=entity.order_id,
            valid_from=entity.valid_from,
            valid_to=entity.valid_to,
            used_at=entity.used_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
