"""
付费功能服务层
- 优惠券管理
- 退款处理
- 发票管理
- 免费试用
- 订阅管理
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import uuid
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.payment import (
    CouponType, CouponStatus, CouponTier,
    Coupon, UserCoupon,
    RefundStatus, RefundReason, RefundRequest,
    InvoiceType, InvoiceStatus, Invoice,
    TrialStatus, FreeTrial,
    SubscriptionStatus, Subscription,
    ApplyCouponRequest, ApplyCouponResponse,
    PaymentStats, CouponStats, TrialStats,
)
from db.payment_models import (
    CouponDB, UserCouponDB, RefundDB, InvoiceDB, FreeTrialDB, SubscriptionDB,
)
from db.models import MembershipOrderDB, UserMembershipDB
from utils.logger import logger
from services.base_service import BaseService


class PaymentService(BaseService):
    """付费功能服务"""

    # ==================== 金额验证常量 ====================
    MIN_AMOUNT = 0.01  # 最小支付金额（分）
    MAX_AMOUNT = 100000.0  # 最大支付金额（10万元）

    def __init__(self, db: Session):
        super().__init__(db)

    # ==================== 金额验证方法 ====================

    def validate_amount(self, amount: float) -> Tuple[bool, str]:
        """
        验证支付金额

        Args:
            amount: 支付金额

        Returns:
            (是否有效, 错误消息)

        Raises:
            ValueError: 金额无效时抛出
        """
        if amount <= 0:
            raise ValueError(f"支付金额必须大于 0，当前金额：{amount}")

        if amount > self.MAX_AMOUNT:
            raise ValueError(f"支付金额不能超过 {self.MAX_AMOUNT} 元，当前金额：{amount}")

        # 精度验证：最多两位小数
        rounded = round(amount, 2)
        if abs(amount - rounded) > 0.0001:
            logger.warning(f"金额精度超过两位小数，将四舍五入：{amount} -> {rounded}")

        logger.info(f"金额验证通过：{amount}")
        return True, ""

    def validate_refund_amount(self, refund_amount: float, original_amount: float) -> Tuple[bool, str]:
        """
        验证退款金额

        Args:
            refund_amount: 退款金额
            original_amount: 原订单金额

        Returns:
            (是否有效, 错误消息)
        """
        if refund_amount <= 0:
            raise ValueError(f"退款金额必须大于 0，当前金额：{refund_amount}")

        if refund_amount > original_amount:
            raise ValueError(f"退款金额不能超过原订单金额 {original_amount} 元")

        return True, ""

    # ==================== 优惠券管理 ====================

    def create_coupon(self, coupon_data: dict) -> Coupon:
        """创建优惠券"""
        coupon = Coupon(
            code=coupon_data["code"].upper(),
            name=coupon_data["name"],
            description=coupon_data.get("description", ""),
            type=CouponType(coupon_data["type"]),
            value=coupon_data["value"],
            min_amount=coupon_data.get("min_amount", 0.0),
            max_discount=coupon_data.get("max_discount"),
            applicable_tiers=[CouponTier(t) for t in coupon_data.get("applicable_tiers", ["all"])],
            usage_limit=coupon_data.get("usage_limit"),
            per_user_limit=coupon_data.get("per_user_limit", 1),
            new_user_only=coupon_data.get("new_user_only", False),
            valid_until=datetime.now() + timedelta(days=coupon_data.get("valid_days", 30)),
            created_by=coupon_data.get("created_by"),
        )

        # 保存到数据库
        coupon_db = CouponDB(
            id=coupon.id,
            code=coupon.code,
            name=coupon.name,
            description=coupon.description,
            type=coupon.type.value,
            value=coupon.value,
            min_amount=coupon.min_amount,
            max_discount=coupon.max_discount,
            applicable_tiers=json.dumps([t.value for t in coupon.applicable_tiers]),
            applicable_products=json.dumps(coupon.applicable_products),
            usage_limit=coupon.usage_limit,
            usage_count=0,
            per_user_limit=coupon.per_user_limit,
            new_user_only=coupon.new_user_only,
            valid_from=coupon.valid_from,
            valid_until=coupon.valid_until,
            status=coupon.status.value,
            created_by=coupon.created_by,
        )

        self.db.add(coupon_db)
        self.db.commit()

        logger.info(f"创建优惠券：code={coupon.code}, name={coupon.name}")
        return coupon

    def get_coupon_by_code(self, code: str) -> Optional[Coupon]:
        """根据优惠码获取优惠券"""
        coupon_db = self.db.query(CouponDB).filter(
            CouponDB.code == code.upper()
        ).first()

        if not coupon_db:
            return None

        return self._coupon_db_to_model(coupon_db)

    def claim_coupon(self, user_id: str, coupon_code: str) -> Tuple[bool, str]:
        """用户领取优惠券"""
        coupon = self.get_coupon_by_code(coupon_code)
        if not coupon:
            return False, "优惠码不存在"

        if not coupon.is_valid():
            return False, "优惠券已过期或无效"

        # 检查是否已领取过
        existing = self.db.query(UserCouponDB).filter(
            UserCouponDB.user_id == user_id,
            UserCouponDB.coupon_code == coupon_code.upper()
        ).first()

        if existing:
            return False, "您已领取过该优惠券"

        # 检查是否是新用户专属
        if coupon.new_user_only:
            # 检查用户是否有过付费订单
            has_order = self.db.query(MembershipOrderDB).filter(
                MembershipOrderDB.user_id == user_id,
                MembershipOrderDB.status == "paid"
            ).first()
            if has_order:
                return False, "该优惠券仅限新用户领取"

        # 检查优惠券使用限制
        if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
            return False, "优惠券已领完"

        # 创建用户优惠券
        user_coupon = UserCouponDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            coupon_id=coupon.id,
            coupon_code=coupon.code.upper(),
            status="active",
            expires_at=coupon.valid_until,
        )

        self.db.add(user_coupon)
        self.db.commit()

        logger.info(f"用户领取优惠券：user_id={user_id}, code={coupon_code}")
        return True, "领取成功"

    def get_user_coupons(self, user_id: str, status: Optional[str] = None) -> List[UserCoupon]:
        """获取用户的优惠券"""
        query = self.db.query(UserCouponDB).filter(
            UserCouponDB.user_id == user_id
        )

        if status:
            query = query.filter(UserCouponDB.status == status)

        user_coupons = query.order_by(UserCouponDB.claimed_at.desc()).all()

        result = []
        for uc in user_coupons:
            coupon = self.get_coupon_by_code(uc.coupon_code)
            if coupon:
                result.append(UserCoupon(
                    id=uc.id,
                    user_id=uc.user_id,
                    coupon_id=uc.coupon_id,
                    coupon_code=uc.coupon_code,
                    status=CouponStatus(uc.status),
                    used_at=uc.used_at,
                    used_on_order_id=uc.used_on_order_id,
                    claimed_at=uc.claimed_at,
                    claim_source=uc.claim_source,
                    expires_at=uc.expires_at,
                ))
        return result

    def apply_coupon(self, user_id: str, request: ApplyCouponRequest) -> ApplyCouponResponse:
        """应用优惠券到订单"""
        coupon = self.get_coupon_by_code(request.coupon_code)
        if not coupon:
            return ApplyCouponResponse(
                valid=False,
                message="优惠码不存在",
                original_amount=request.amount,
                discount_amount=0.0,
                final_amount=request.amount,
            )

        if not coupon.is_valid():
            return ApplyCouponResponse(
                valid=False,
                message="优惠券已过期或无效",
                original_amount=request.amount,
                discount_amount=0.0,
                final_amount=request.amount,
            )

        # 检查是否适用于该会员等级
        if not coupon.can_apply_to_tier(request.tier):
            return ApplyCouponResponse(
                valid=False,
                message=f"该优惠券不适用于{request.tier}会员",
                original_amount=request.amount,
                discount_amount=0.0,
                final_amount=request.amount,
            )

        # 检查最低消费金额
        if request.amount < coupon.min_amount:
            return ApplyCouponResponse(
                valid=False,
                message=f"最低消费金额需达到{coupon.min_amount}元",
                original_amount=request.amount,
                discount_amount=0.0,
                final_amount=request.amount,
            )

        # 检查用户是否有该优惠券
        user_coupon = self.db.query(UserCouponDB).filter(
            UserCouponDB.user_id == user_id,
            UserCouponDB.coupon_code == request.coupon_code.upper(),
            UserCouponDB.status == "active"
        ).first()

        if not user_coupon:
            return ApplyCouponResponse(
                valid=False,
                message="您没有该优惠券",
                original_amount=request.amount,
                discount_amount=0.0,
                final_amount=request.amount,
            )

        # 计算折扣
        discount = coupon.calculate_discount(request.amount)

        return ApplyCouponResponse(
            valid=True,
            message="优惠券应用成功",
            original_amount=request.amount,
            discount_amount=discount,
            final_amount=request.amount - discount,
        )

    def use_coupon(self, user_coupon_id: str, order_id: str) -> bool:
        """使用优惠券"""
        user_coupon = self.db.query(UserCouponDB).filter(
            UserCouponDB.id == user_coupon_id
        ).first()

        if not user_coupon:
            return False

        user_coupon.status = "used"
        user_coupon.used_at = datetime.now()
        user_coupon.used_on_order_id = order_id

        # 更新优惠券使用次数
        coupon = self.db.query(CouponDB).filter(
            CouponDB.id == user_coupon.coupon_id
        ).first()
        if coupon:
            coupon.usage_count += 1
            coupon.updated_at = datetime.now()

        self.db.commit()
        return True

    def get_coupon_stats(self) -> CouponStats:
        """获取优惠券统计"""
        total = self.db.query(CouponDB).count()
        active = self.db.query(CouponDB).filter(CouponDB.status == "active").count()

        claimed = self.db.query(UserCouponDB).count()
        used = self.db.query(UserCouponDB).filter(UserCouponDB.status == "used").count()

        # 计算总折扣金额 (需要从订单中计算)
        # 这里简化处理
        total_discount = 0.0

        return CouponStats(
            total_coupons=total,
            active_coupons=active,
            total_claimed=claimed,
            total_used=used,
            total_discount_amount=total_discount,
        )

    # ==================== 退款管理 ====================

    def create_refund(self, order_id: str, user_id: str, reason: RefundReason, description: str = "") -> RefundRequest:
        """创建退款申请"""
        # 检查订单是否存在且已支付
        order = self.db.query(MembershipOrderDB).filter(
            MembershipOrderDB.id == order_id,
            MembershipOrderDB.user_id == user_id,
            MembershipOrderDB.status == "paid"
        ).first()

        if not order:
            raise ValueError("订单不存在或未支付")

        # 检查是否已有退款申请
        existing = self.db.query(RefundDB).filter(
            RefundDB.order_id == order_id
        ).first()

        if existing:
            raise ValueError("该订单已有退款申请")

        refund = RefundRequest(
            order_id=order_id,
            user_id=user_id,
            refund_amount=order.amount,
            reason=reason,
            description=description,
        )

        refund_db = RefundDB(
            id=refund.id,
            order_id=refund.order_id,
            user_id=refund.user_id,
            refund_amount=refund.refund_amount,
            reason=refund.reason.value,
            description=refund.description,
            status=RefundStatus.PENDING.value,
        )

        self.db.add(refund_db)
        self.db.commit()

        logger.info(f"创建退款申请：order_id={order_id}, user_id={user_id}")
        return refund

    def get_refund(self, refund_id: str) -> Optional[RefundRequest]:
        """获取退款申请"""
        refund_db = self.db.query(RefundDB).filter(
            RefundDB.id == refund_id
        ).first()

        if not refund_db:
            return None

        return self._refund_db_to_model(refund_db)

    def get_user_refunds(self, user_id: str) -> List[RefundRequest]:
        """获取用户的退款申请"""
        refunds = self.db.query(RefundDB).filter(
            RefundDB.user_id == user_id
        ).order_by(RefundDB.created_at.desc()).all()

        return [self._refund_db_to_model(r) for r in refunds]

    def approve_refund(self, refund_id: str, reviewed_by: str, note: str = "") -> bool:
        """批准退款"""
        refund_db = self.db.query(RefundDB).filter(
            RefundDB.id == refund_id
        ).first()

        if not refund_db:
            raise ValueError("退款申请不存在")

        refund_db.status = RefundStatus.APPROVED.value
        refund_db.reviewed_by = reviewed_by
        refund_db.reviewed_at = datetime.now()
        refund_db.review_note = note
        refund_db.updated_at = datetime.now()

        # 更新订单状态
        order = self.db.query(MembershipOrderDB).filter(
            MembershipOrderDB.id == refund_db.order_id
        ).first()
        if order:
            order.status = "refunded"

        self.db.commit()

        logger.info(f"批准退款：refund_id={refund_id}")
        return True

    def reject_refund(self, refund_id: str, reviewed_by: str, note: str = "") -> bool:
        """拒绝退款"""
        refund_db = self.db.query(RefundDB).filter(
            RefundDB.id == refund_id
        ).first()

        if not refund_db:
            raise ValueError("退款申请不存在")

        refund_db.status = RefundStatus.REJECTED.value
        refund_db.reviewed_by = reviewed_by
        refund_db.reviewed_at = datetime.now()
        refund_db.review_note = note
        refund_db.updated_at = datetime.now()

        self.db.commit()

        logger.info(f"拒绝退款：refund_id={refund_id}, reason={note}")
        return True

    def complete_refund(self, refund_id: str, transaction_id: str) -> bool:
        """完成退款"""
        refund_db = self.db.query(RefundDB).filter(
            RefundDB.id == refund_id
        ).first()

        if not refund_db:
            raise ValueError("退款申请不存在")

        refund_db.status = RefundStatus.COMPLETED.value
        refund_db.refund_transaction_id = transaction_id
        refund_db.refunded_at = datetime.now()
        refund_db.updated_at = datetime.now()

        self.db.commit()

        logger.info(f"完成退款：refund_id={refund_id}, transaction_id={transaction_id}")
        return True

    # ==================== 发票管理 ====================

    def create_invoice(self, order_id: str, user_id: str, invoice_data: dict) -> Invoice:
        """创建发票"""
        # 检查订单是否存在且已支付
        order = self.db.query(MembershipOrderDB).filter(
            MembershipOrderDB.id == order_id,
            MembershipOrderDB.user_id == user_id,
            MembershipOrderDB.status == "paid"
        ).first()

        if not order:
            raise ValueError("订单不存在或未支付")

        # 检查是否已有发票
        existing = self.db.query(InvoiceDB).filter(
            InvoiceDB.order_id == order_id
        ).first()

        if existing:
            raise ValueError("该订单已有发票")

        # 生成发票号码 (简化：使用时间戳)
        invoice_number = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
        invoice_code = "1100112233"  # 简化的发票代码

        tax_amount = order.amount * invoice_data.get("tax_rate", 0.06)

        invoice = Invoice(
            order_id=order_id,
            user_id=user_id,
            invoice_number=invoice_number,
            invoice_code=invoice_code,
            invoice_type=InvoiceType(invoice_data.get("invoice_type", "electronic")),
            amount=order.amount,
            tax_rate=invoice_data.get("tax_rate", 0.06),
            tax_amount=tax_amount,
            buyer_name=invoice_data["buyer_name"],
            buyer_tax_id=invoice_data["buyer_tax_id"],
            buyer_address=invoice_data.get("buyer_address", ""),
            buyer_phone=invoice_data.get("buyer_phone", ""),
            buyer_bank=invoice_data.get("buyer_bank", ""),
            sent_to_email=invoice_data.get("sent_to_email"),
            mailing_address=invoice_data.get("mailing_address"),
        )

        invoice_db = InvoiceDB(
            id=invoice.id,
            order_id=invoice.order_id,
            user_id=invoice.user_id,
            invoice_number=invoice.invoice_number,
            invoice_code=invoice.invoice_code,
            invoice_type=invoice.invoice_type.value,
            amount=invoice.amount,
            tax_rate=invoice.tax_rate,
            tax_amount=invoice.tax_amount,
            buyer_name=invoice.buyer_name,
            buyer_tax_id=invoice.buyer_tax_id,
            buyer_address=invoice.buyer_address,
            buyer_phone=invoice.buyer_phone,
            buyer_bank=invoice.buyer_bank,
            product_name=invoice.product_name,
            quantity=invoice.quantity,
            status=InvoiceStatus.PENDING.value,
            sent_to_email=invoice.sent_to_email,
            mailing_address=invoice.mailing_address,
        )

        self.db.add(invoice_db)
        self.db.commit()

        logger.info(f"创建发票：order_id={order_id}, invoice_number={invoice_number}")
        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """获取发票"""
        invoice_db = self.db.query(InvoiceDB).filter(
            InvoiceDB.id == invoice_id
        ).first()

        if not invoice_db:
            return None

        return self._invoice_db_to_model(invoice_db)

    def get_user_invoices(self, user_id: str) -> List[Invoice]:
        """获取用户的发票"""
        invoices = self.db.query(InvoiceDB).filter(
            InvoiceDB.user_id == user_id
        ).order_by(InvoiceDB.created_at.desc()).all()

        return [self._invoice_db_to_model(i) for i in invoices]

    def issue_invoice(self, invoice_id: str, invoice_url: Optional[str] = None) -> bool:
        """开具发票"""
        invoice_db = self.db.query(InvoiceDB).filter(
            InvoiceDB.id == invoice_id
        ).first()

        if not invoice_db:
            raise ValueError("发票不存在")

        invoice_db.status = InvoiceStatus.ISSUED.value
        invoice_db.issued_at = datetime.now()
        if invoice_url:
            invoice_db.invoice_url = invoice_url
        invoice_db.updated_at = datetime.now()

        self.db.commit()

        logger.info(f"开具发票：invoice_id={invoice_id}")
        return True

    def send_invoice(self, invoice_id: str, sent_to_email: str) -> bool:
        """发送发票"""
        invoice_db = self.db.query(InvoiceDB).filter(
            InvoiceDB.id == invoice_id
        ).first()

        if not invoice_db:
            raise ValueError("发票不存在")

        if invoice_db.status != InvoiceStatus.ISSUED.value:
            raise ValueError("发票尚未开具")

        invoice_db.sent_to_email = sent_to_email
        invoice_db.sent_at = datetime.now()
        invoice_db.status = InvoiceStatus.SENT.value
        invoice_db.updated_at = datetime.now()

        self.db.commit()

        logger.info(f"发送发票：invoice_id={invoice_id}, email={sent_to_email}")
        return True

    # ==================== 免费试用 ====================

    def start_free_trial(self, user_id: str, tier: str = "premium", duration_days: int = 7) -> Tuple[bool, str]:
        """开始免费试用"""
        # 检查用户是否已有试用记录
        existing = self.db.query(FreeTrialDB).filter(
            FreeTrialDB.user_id == user_id
        ).first()

        if existing:
            if existing.status == "in_progress":
                return False, "您已有进行中的试用"
            elif existing.status == "completed":
                return False, "您已使用过免费试用机会"

        # 检查用户是否已有付费会员
        membership = self.db.query(UserMembershipDB).filter(
            UserMembershipDB.user_id == user_id,
            UserMembershipDB.status == "active"
        ).first()

        if membership and membership.tier != "free":
            return False, "付费会员用户无法开始试用"

        # 创建试用记录
        now = datetime.now()
        ends_at = now + timedelta(days=duration_days)

        trial = FreeTrialDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tier=tier,
            duration_days=duration_days,
            started_at=now,
            ends_at=ends_at,
            status="in_progress",
        )

        self.db.add(trial)

        # 同时创建会员记录
        membership = UserMembershipDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tier=tier,
            status="active",
            start_date=now,
            end_date=ends_at,
            auto_renew=False,
        )

        self.db.add(membership)
        self.db.commit()

        logger.info(f"开始免费试用：user_id={user_id}, tier={tier}, days={duration_days}")
        return True, f"免费试用已开始，将持续{duration_days}天"

    def get_user_trial(self, user_id: str) -> Optional[FreeTrial]:
        """获取用户试用记录"""
        trial = self.db.query(FreeTrialDB).filter(
            FreeTrialDB.user_id == user_id
        ).first()

        if not trial:
            return None

        return FreeTrial(
            id=trial.id,
            user_id=trial.user_id,
            tier=trial.tier,
            duration_days=trial.duration_days,
            started_at=trial.started_at,
            ends_at=trial.ends_at,
            status=TrialStatus(trial.status),
            converted_to_paid=trial.converted_to_paid,
            converted_order_id=trial.converted_order_id,
            converted_at=trial.converted_at,
        )

    def check_trial_expiry(self):
        """检查并更新过期的试用"""
        now = datetime.now()

        trials = self.db.query(FreeTrialDB).filter(
            FreeTrialDB.status == "in_progress",
            FreeTrialDB.ends_at <= now
        ).all()

        for trial in trials:
            trial.status = "expired"
            trial.updated_at = now

        self.db.commit()
        logger.info(f"更新过期试用：count={len(trials)}")

    def mark_trial_converted(self, user_id: str, order_id: str) -> bool:
        """标记试用用户转化为付费用户"""
        trial = self.db.query(FreeTrialDB).filter(
            FreeTrialDB.user_id == user_id
        ).first()

        if not trial:
            return False

        trial.converted_to_paid = True
        trial.converted_order_id = order_id
        trial.converted_at = datetime.now()
        trial.status = "completed"
        trial.updated_at = datetime.now()

        self.db.commit()
        return True

    def get_trial_stats(self) -> TrialStats:
        """获取试用统计"""
        total = self.db.query(FreeTrialDB).count()
        active = self.db.query(FreeTrialDB).filter(FreeTrialDB.status == "in_progress").count()
        expired = self.db.query(FreeTrialDB).filter(FreeTrialDB.status == "expired").count()
        converted = self.db.query(FreeTrialDB).filter(FreeTrialDB.converted_to_paid == True).count()

        conversion_rate = converted / total if total > 0 else 0.0

        return TrialStats(
            total_trials=total,
            active_trials=active,
            expired_trials=expired,
            converted_trials=converted,
            conversion_rate=conversion_rate,
        )

    # ==================== 订阅管理 ====================

    def create_subscription(self, user_id: str, tier: str, interval: str, amount: float, provider: str = "") -> Subscription:
        """创建订阅"""
        now = datetime.now()
        if interval == "month":
            period_end = now + timedelta(days=30)
        elif interval == "quarter":
            period_end = now + timedelta(days=90)
        elif interval == "year":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        subscription = Subscription(
            user_id=user_id,
            tier=tier,
            interval=interval,
            amount=amount,
            provider=provider,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=period_end,
        )

        subscription_db = SubscriptionDB(
            id=subscription.id,
            user_id=subscription.user_id,
            tier=subscription.tier,
            interval=subscription.interval,
            amount=subscription.amount,
            provider=subscription.provider,
            provider_subscription_id=subscription.provider_subscription_id,
            status=subscription.status.value,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=False,
        )

        self.db.add(subscription_db)
        self.db.commit()

        logger.info(f"创建订阅：user_id={user_id}, tier={tier}, interval={interval}")
        return subscription

    def get_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户订阅"""
        subscription = self.db.query(SubscriptionDB).filter(
            SubscriptionDB.user_id == user_id
        ).first()

        if not subscription:
            return None

        return Subscription(
            id=subscription.id,
            user_id=subscription.user_id,
            tier=subscription.tier,
            interval=subscription.interval,
            amount=subscription.amount,
            provider=subscription.provider,
            provider_subscription_id=subscription.provider_subscription_id,
            status=SubscriptionStatus(subscription.status),
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            trial_start=subscription.trial_start,
            trial_end=subscription.trial_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            cancelled_at=subscription.cancelled_at,
            cancel_reason=subscription.cancel_reason,
        )

    def cancel_subscription(self, user_id: str, reason: str = "") -> bool:
        """取消订阅"""
        subscription = self.db.query(SubscriptionDB).filter(
            SubscriptionDB.user_id == user_id
        ).first()

        if not subscription:
            return False

        subscription.cancel_at_period_end = True
        subscription.cancelled_at = datetime.now()
        subscription.cancel_reason = reason
        subscription.status = SubscriptionStatus.CANCELLED.value
        subscription.updated_at = datetime.now()

        self.db.commit()

        logger.info(f"取消订阅：user_id={user_id}, reason={reason}")
        return True

    def get_payment_stats(self) -> PaymentStats:
        """获取支付统计"""
        total_orders = self.db.query(MembershipOrderDB).count()
        paid_orders = self.db.query(MembershipOrderDB).filter(
            MembershipOrderDB.status == "paid"
        ).count()

        # 总收入
        result = self.db.query(
            MembershipOrderDB.status,
            func.sum(MembershipOrderDB.amount).label('total')
        ).group_by(MembershipOrderDB.status).all()

        total_revenue = sum(r.total for r in result if r.status == "paid") or 0.0

        # 退款金额
        refunded_amount = self.db.query(
            func.sum(RefundDB.refund_amount).label('total')
        ).filter(RefundDB.status == "completed").scalar() or 0.0

        # 新增付费用户数
        new_paying_users = self.db.query(
            func.count(func.distinct(MembershipOrderDB.user_id))
        ).filter(MembershipOrderDB.status == "paid").scalar() or 0

        # 试用转化数
        converted_from_trial = self.db.query(FreeTrialDB).filter(
            FreeTrialDB.converted_to_paid == True
        ).count()

        return PaymentStats(
            total_orders=total_orders,
            paid_orders=paid_orders,
            total_revenue=total_revenue,
            refunded_amount=refunded_amount,
            net_revenue=total_revenue - refunded_amount,
            new_paying_users=new_paying_users,
            converted_from_trial=converted_from_trial,
        )

    # ==================== 辅助方法 ====================

    def _coupon_db_to_model(self, db: CouponDB) -> Coupon:
        """将数据库模型转换为业务模型"""
        return Coupon(
            id=db.id,
            code=db.code,
            name=db.name,
            description=db.description,
            type=CouponType(db.type),
            value=db.value,
            min_amount=db.min_amount,
            max_discount=db.max_discount,
            applicable_tiers=[CouponTier(t) for t in json.loads(db.applicable_tiers)],
            applicable_products=json.loads(db.applicable_products) if db.applicable_products else [],
            usage_limit=db.usage_limit,
            usage_count=db.usage_count,
            per_user_limit=db.per_user_limit,
            new_user_only=db.new_user_only,
            valid_from=db.valid_from,
            valid_until=db.valid_until,
            status=CouponStatus(db.status),
            created_at=db.created_at,
            updated_at=db.updated_at,
            created_by=db.created_by,
        )

    def _refund_db_to_model(self, db: RefundDB) -> RefundRequest:
        """将数据库模型转换为业务模型"""
        return RefundRequest(
            id=db.id,
            order_id=db.order_id,
            user_id=db.user_id,
            refund_amount=db.refund_amount,
            reason=RefundReason(db.reason),
            description=db.description,
            status=RefundStatus(db.status),
            reviewed_by=db.reviewed_by,
            reviewed_at=db.reviewed_at,
            review_note=db.review_note,
            refund_transaction_id=db.refund_transaction_id,
            refunded_at=db.refunded_at,
            created_at=db.created_at,
            updated_at=db.updated_at,
        )

    def _invoice_db_to_model(self, db: InvoiceDB) -> Invoice:
        """将数据库模型转换为业务模型"""
        return Invoice(
            id=db.id,
            order_id=db.order_id,
            user_id=db.user_id,
            invoice_number=db.invoice_number,
            invoice_code=db.invoice_code,
            invoice_type=InvoiceType(db.invoice_type),
            amount=db.amount,
            tax_rate=db.tax_rate,
            tax_amount=db.tax_amount,
            buyer_name=db.buyer_name,
            buyer_tax_id=db.buyer_tax_id,
            buyer_address=db.buyer_address,
            buyer_phone=db.buyer_phone,
            buyer_bank=db.buyer_bank,
            product_name=db.product_name,
            product_spec=db.product_spec,
            unit=db.unit,
            quantity=db.quantity,
            status=InvoiceStatus(db.status),
            invoice_url=db.invoice_url,
            sent_at=db.sent_at,
            sent_to_email=db.sent_to_email,
            mailing_address=db.mailing_address,
            mailing_no=db.mailing_no,
            mailed_at=db.mailed_at,
            created_at=db.created_at,
            issued_at=db.issued_at,
            updated_at=db.updated_at,
        )


def get_payment_service(db: Session = None):
    """
    获取支付服务实例

    Returns:
        (PaymentService 实例，是否需要关闭会话)

    Usage:
        service, should_close = get_payment_service()
        try:
            service.some_method()
        finally:
            if should_close:
                service.db.close()
    """
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    return PaymentService(db), should_close
