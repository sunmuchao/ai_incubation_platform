"""
P6 - 支付服务

功能：
1. 订单支付处理
2. 支付回调验证
3. 退款处理
4. 支付记录管理
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from models.db_models import (
    OrderDB, PaymentRecordDB, UserDB, OrderStatus, RefundStatus,
    TrialRecordDB, SubscriptionTier
)
from services.payment_gateway import PaymentManager, get_payment_manager, PaymentGatewayError
from services.user_service import UserService
import logging

logger = logging.getLogger(__name__)


class PaymentService:
    """支付服务"""

    # 订单过期时间（分钟）
    ORDER_EXPIRE_MINUTES = 30

    # 退款策略配置
    REFUND_POLICY = {
        "auto_refund_days": 7,  # 7 天内可自动退款
        "refund_fee_rate": 0.0,  # 退款手续费率（0%）
    }

    def __init__(self, db: Session):
        self.db = db
        self.payment_manager = get_payment_manager()
        self.user_service = UserService(db)

    # ==================== 订单支付 ====================

    def create_order(
        self,
        user_id: str,
        product_type: str,
        subscription_tier: str = None,
        billing_cycle: str = "monthly",
        invoice_required: bool = False,
        invoice_title: str = None,
        invoice_tax_id: str = None,
        notes: str = None,
    ) -> OrderDB:
        """
        创建订单

        Args:
            user_id: 用户 ID
            product_type: 产品类型 (subscription/topup)
            subscription_tier: 订阅等级 (free/pro/enterprise)
            billing_cycle: 计费周期 (monthly/yearly)
            invoice_required: 是否需要发票
            invoice_title: 发票抬头
            invoice_tax_id: 税号
            notes: 备注

        Returns:
            OrderDB: 订单对象
        """
        user = self.user_service.get_user(user_id)
        if not user:
            raise ValueError(f"用户不存在：{user_id}")

        # 计算金额
        if product_type == "subscription" and subscription_tier:
            plan = self.user_service.get_subscription_plan(subscription_tier)
            base_amount = plan["price"]

            # 年付优惠（8 折）
            if billing_cycle == "yearly":
                discount_rate = 0.8
                amount = base_amount * 12  # 年付原价
                discount_amount = amount * (1 - discount_rate)  # 优惠金额
                paid_amount = amount * discount_rate  # 实付金额
            else:
                amount = base_amount
                discount_amount = 0
                paid_amount = base_amount
        else:
            amount = 0
            discount_amount = 0
            paid_amount = 0

        # 生成订单号
        order_no = self._generate_order_no()

        # 创建订单
        order = OrderDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            order_no=order_no,
            product_type=product_type,
            subscription_tier=subscription_tier,
            billing_cycle=billing_cycle,
            amount=amount,
            discount_amount=discount_amount,
            paid_amount=amount - discount_amount,
            currency="CNY",
            status=OrderStatus.PENDING,
            invoice_required=invoice_required,
            invoice_title=invoice_title,
            invoice_tax_id=invoice_tax_id,
            notes=notes,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=self.ORDER_EXPIRE_MINUTES),
        )

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        logger.info(f"创建订单：order_no={order_no}, user_id={user_id}, amount={amount}")

        return order

    def initiate_payment(
        self,
        order_id: str,
        payment_method: str = "mock",
    ) -> Dict[str, Any]:
        """
        发起支付

        Args:
            order_id: 订单 ID
            payment_method: 支付方式 (mock/alipay/wechat/stripe)

        Returns:
            dict: 支付信息
        """
        order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
        if not order:
            raise ValueError(f"订单不存在：{order_id}")

        if order.status != OrderStatus.PENDING:
            raise ValueError(f"订单状态不允许支付：{order.status.value}")

        # 检查订单是否过期
        if order.expires_at and datetime.now() > order.expires_at:
            order.status = OrderStatus.EXPIRED
            self.db.commit()
            raise ValueError("订单已过期")

        # 调用支付网关创建支付
        try:
            gateway = self.payment_manager.get_gateway(payment_method)
            payment_result = gateway.create_payment(
                order_no=order.order_no,
                amount=order.paid_amount,
                description=f"AI Opportunity Miner - {order.product_type}",
            )
        except PaymentGatewayError as e:
            logger.error(f"支付网关错误：{e}")
            raise ValueError(f"支付失败：{str(e)}")

        # 创建支付记录
        payment_record = PaymentRecordDB(
            id=str(uuid.uuid4()),
            order_id=order_id,
            user_id=order.user_id,
            payment_method=payment_method,
            transaction_id=payment_result.get("transaction_id"),
            amount=order.paid_amount,
            currency=order.currency,
            status="pending",
            created_at=datetime.now(),
        )

        self.db.add(payment_record)
        self.db.commit()

        logger.info(f"发起支付：order_id={order_id}, payment_method={payment_method}")

        return {
            "order": order.to_dict(),
            "payment": payment_result,
        }

    def process_callback(
        self,
        payment_method: str,
        callback_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        处理支付回调

        Args:
            payment_method: 支付方式
            callback_data: 回调数据

        Returns:
            dict: 处理结果
        """
        # 验证回调
        gateway = self.payment_manager.get_gateway(payment_method)
        verified, result = gateway.verify_callback(callback_data)

        if not verified:
            logger.warning(f"支付回调验证失败：{result}")
            return {"success": False, "message": f"回调验证失败：{result}"}

        transaction_id = result
        order = self.db.query(OrderDB).filter(OrderDB.order_no == callback_data.get("order_no")).first()
        if not order:
            logger.warning(f"订单不存在：{callback_data.get('order_no')}")
            return {"success": False, "message": "订单不存在"}

        # 更新订单状态
        order.status = OrderStatus.PAID
        order.payment_method = payment_method
        order.transaction_id = transaction_id
        order.payment_time = datetime.now()
        order.paid_at = datetime.now()

        # 更新支付记录
        payment_record = self.db.query(PaymentRecordDB).filter(
            PaymentRecordDB.transaction_id == transaction_id
        ).first()
        if payment_record:
            payment_record.status = "success"
            payment_record.paid_at = datetime.now()
            payment_record.callback_data = callback_data

        # 如果是订阅订单，更新用户订阅状态
        if order.product_type == "subscription" and order.subscription_tier:
            self.user_service.upgrade_subscription(order.user_id, order.subscription_tier)

            # 设置订阅过期时间
            user = self.user_service.get_user(order.user_id)
            if order.billing_cycle == "yearly":
                user.subscription_expires_at = datetime.now() + timedelta(days=365)
            else:
                user.subscription_expires_at = datetime.now() + timedelta(days=30)

            # 如果有试用记录，标记为已转化
            trial = self.db.query(TrialRecordDB).filter(
                TrialRecordDB.user_id == order.user_id,
                TrialRecordDB.status == "active"
            ).first()
            if trial:
                trial.status = "converted"
                trial.converted_at = datetime.now()
                trial.converted_tier = order.subscription_tier

        self.db.commit()

        logger.info(f"支付回调处理成功：order_no={order.order_no}, transaction_id={transaction_id}")

        return {
            "success": True,
            "order_no": order.order_no,
            "transaction_id": transaction_id,
        }

    # ==================== 退款管理 ====================

    def request_refund(
        self,
        order_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        申请退款

        Args:
            order_id: 订单 ID
            reason: 退款原因

        Returns:
            dict: 退款结果
        """
        order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
        if not order:
            raise ValueError(f"订单不存在：{order_id}")

        if order.status != OrderStatus.PAID:
            raise ValueError(f"订单未支付，无法退款")

        # 检查是否在退款期限内
        days_since_payment = (datetime.now() - order.paid_at).days if order.paid_at else 999
        if days_since_payment > self.REFUND_POLICY["auto_refund_days"]:
            # 超过自动退款期限，需要人工审核
            order.refund_status = RefundStatus.PENDING
            order.refund_reason = reason
            self.db.commit()

            logger.info(f"退款申请待审核：order_no={order.order_no}, days={days_since_payment}")
            return {
                "success": True,
                "status": "pending",
                "message": "退款申请已提交，等待审核（超过 7 天自动退款期限）",
            }

        # 自动退款
        try:
            gateway = self.payment_manager.get_gateway(order.payment_method)
            refund_result = gateway.refund(
                transaction_id=order.transaction_id,
                amount=order.paid_amount,
                reason=reason,
            )

            if refund_result.get("success"):
                # 更新订单状态
                order.status = OrderStatus.REFUNDED
                order.refund_status = RefundStatus.COMPLETED
                order.refund_time = datetime.now()
                order.refund_amount = order.paid_amount
                order.refund_reason = reason

                # 更新支付记录
                payment_record = self.db.query(PaymentRecordDB).filter(
                    PaymentRecordDB.order_id == order_id
                ).first()
                if payment_record:
                    payment_record.status = "refunded"

                # 如果是订阅订单，降级到免费版
                if order.product_type == "subscription":
                    self.user_service.cancel_subscription(order.user_id)

                    # 更新试用记录
                    trial = self.db.query(TrialRecordDB).filter(
                        TrialRecordDB.user_id == order.user_id
                    ).first()
                    if trial and trial.status == "converted":
                        trial.status = "cancelled"
                        trial.cancelled_at = datetime.now()
                        trial.cancel_reason = reason

                self.db.commit()

                logger.info(f"退款成功：order_no={order.order_no}, refund_id={refund_result.get('refund_id')}")

                return {
                    "success": True,
                    "status": "completed",
                    "refund_id": refund_result.get("refund_id"),
                    "message": "退款已成功处理",
                }
            else:
                raise ValueError(f"退款失败：{refund_result.get('error')}")

        except PaymentGatewayError as e:
            logger.error(f"退款失败：{e}")
            # 记录退款失败，等待人工处理
            order.refund_status = RefundStatus.PENDING
            order.refund_reason = reason
            self.db.commit()

            return {
                "success": False,
                "status": "pending",
                "message": f"退款处理失败，已转为人工审核：{str(e)}",
            }

    def approve_refund(self, order_id: str, admin_user_id: str) -> Dict[str, Any]:
        """
        批准退款（管理员操作）

        Args:
            order_id: 订单 ID
            admin_user_id: 管理员用户 ID

        Returns:
            dict: 处理结果
        """
        order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
        if not order:
            raise ValueError(f"订单不存在：{order_id}")

        if order.refund_status != RefundStatus.PENDING:
            raise ValueError(f"订单退款状态不是待审核：{order.refund_status.value if order.refund_status else 'None'}")

        # 执行退款逻辑（与自动退款类似）
        return self.request_refund(order_id, order.refund_reason or "管理员批准退款")

    def reject_refund(self, order_id: str, reason: str, admin_user_id: str) -> Dict[str, Any]:
        """
        拒绝退款（管理员操作）

        Args:
            order_id: 订单 ID
            reason: 拒绝原因
            admin_user_id: 管理员用户 ID

        Returns:
            dict: 处理结果
        """
        order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
        if not order:
            raise ValueError(f"订单不存在：{order_id}")

        order.refund_status = RefundStatus.REJECTED
        order.refund_reason = f"{order.refund_reason or ''} [拒绝原因：{reason}]"
        self.db.commit()

        logger.info(f"退款已拒绝：order_no={order.order_no}, reason={reason}")

        return {
            "success": True,
            "message": f"退款已拒绝：{reason}",
        }

    # ==================== 订单查询 ====================

    def get_order(self, order_id: str) -> Optional[OrderDB]:
        """获取订单详情"""
        return self.db.query(OrderDB).filter(OrderDB.id == order_id).first()

    def get_order_by_no(self, order_no: str) -> Optional[OrderDB]:
        """通过订单号获取订单"""
        return self.db.query(OrderDB).filter(OrderDB.order_no == order_no).first()

    def get_user_orders(
        self,
        user_id: str,
        status: str = None,
        limit: int = 50,
    ) -> List[OrderDB]:
        """获取用户订单列表"""
        query = self.db.query(OrderDB).filter(OrderDB.user_id == user_id)

        if status:
            query = query.filter(OrderDB.status == OrderStatus(status))

        return query.order_by(OrderDB.created_at.desc()).limit(limit).all()

    def get_payment_record(self, transaction_id: str) -> Optional[PaymentRecordDB]:
        """获取支付记录"""
        return self.db.query(PaymentRecordDB).filter(
            PaymentRecordDB.transaction_id == transaction_id
        ).first()

    # ==================== 工具方法 ====================

    def _generate_order_no(self) -> str:
        """生成订单号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"ORD{timestamp}{unique_id}"


# 全局单例
_payment_service_instances = {}


def get_payment_service(db: Session) -> PaymentService:
    """获取支付服务实例"""
    return PaymentService(db)
