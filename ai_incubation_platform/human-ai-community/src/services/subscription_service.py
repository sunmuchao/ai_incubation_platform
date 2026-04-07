"""
订阅服务 - 管理创作者订阅功能
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timedelta
import logging
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.economy_models import (
    DBSubscription, DBSubscriptionBenefit, DBWallet,
    SubscriptionTierEnum, SubscriptionPeriodEnum, SubscriptionStatusEnum,
    TransactionStatusEnum, TransactionTypeEnum
)
from models.economy import (
    Subscription, SubscriptionTier, SubscriptionPeriod, SubscriptionStatus,
    SubscriptionBenefit
)
from services.wallet_service import WalletService

logger = logging.getLogger(__name__)


# 订阅等级默认配置
SUBSCRIPTION_CONFIG = {
    SubscriptionTierEnum.FREE: {
        "name": "免费",
        "price_monthly": 0,
        "benefits": ["查看公开内容"]
    },
    SubscriptionTierEnum.BASIC: {
        "name": "基础版",
        "price_monthly": 3000,  # 30 元/月
        "benefits": ["查看专属内容", "免广告"]
    },
    SubscriptionTierEnum.PREMIUM: {
        "name": "高级版",
        "price_monthly": 6800,  # 68 元/月
        "benefits": ["查看专属内容", "提前观看", "免广告", "专属徽章"]
    },
    SubscriptionTierEnum.VIP: {
        "name": "VIP",
        "price_monthly": 12800,  # 128 元/月
        "benefits": ["查看专属内容", "提前观看", "免广告", "专属徽章", "优先支持", "打赏 9 折"]
    },
    SubscriptionTierEnum.EXCLUSIVE: {
        "name": "专属",
        "price_monthly": 29800,  # 298 元/月
        "benefits": ["全部内容", "1 对 1 咨询", "定制内容", "专属社群", "打赏 8 折"]
    }
}

# 订阅周期系数
PERIOD_PRICING = {
    SubscriptionPeriodEnum.MONTHLY: 1.0,      # 月付原价
    SubscriptionPeriodEnum.QUARTERLY: 2.7,    # 季付 9 折
    SubscriptionPeriodEnum.YEARLY: 10.0,      # 年付约 8.3 折
}


class SubscriptionService:
    """订阅服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_service = WalletService(db)

    def _calculate_price(
        self,
        tier: SubscriptionTierEnum,
        period: SubscriptionPeriodEnum
    ) -> int:
        """计算订阅价格（分）"""
        base_price = SUBSCRIPTION_CONFIG[tier]["price_monthly"]
        period_multiplier = PERIOD_PRICING[period]
        return int(base_price * period_multiplier)

    def _calculate_next_billing(
        self,
        period: SubscriptionPeriodEnum,
        from_date: datetime = None
    ) -> datetime:
        """计算下次扣费日期"""
        from_date = from_date or datetime.now()

        if period == SubscriptionPeriodEnum.MONTHLY:
            # 下个月同日
            if from_date.month == 12:
                return from_date.replace(year=from_date.year + 1, month=1)
            else:
                return from_date.replace(month=from_date.month + 1)

        elif period == SubscriptionPeriodEnum.QUARTERLY:
            # 3 个月后
            month = from_date.month + 3
            year = from_date.year
            if month > 12:
                month -= 12
                year += 1
            return from_date.replace(month=month, year=year)

        elif period == SubscriptionPeriodEnum.YEARLY:
            # 1 年后
            return from_date.replace(year=from_date.year + 1)

        return from_date + timedelta(days=30)  # 默认 30 天

    async def create_subscription(
        self,
        subscriber_id: str,
        creator_id: str,
        tier: SubscriptionTier,
        period: SubscriptionPeriod
    ) -> Subscription:
        """
        创建订阅

        流程：
        1. 计算订阅价格
        2. 获取或创建 subscriber 钱包
        3. 获取或创建 creator 钱包
        4. 扣款并记录交易
        5. 创建订阅记录

        Args:
            subscriber_id: 订阅者 ID
            creator_id: 创作者 ID
            tier: 订阅等级
            period: 订阅周期

        Returns:
            订阅记录
        """
        # 转换枚举
        tier_enum = SubscriptionTierEnum(tier.value)
        period_enum = SubscriptionPeriodEnum(period.value)

        # 计算价格
        price = self._calculate_price(tier_enum, period_enum)

        # 检查是否已有活跃订阅
        existing = await self.get_active_subscription(subscriber_id, creator_id)
        if existing:
            raise ValueError(f"已有活跃订阅：{existing.id}")

        # 获取钱包
        subscriber_wallet = await self.wallet_service.get_or_create_wallet(subscriber_id, "member")
        creator_wallet = await self.wallet_service.get_or_create_wallet(creator_id, "member")

        # 平台分成（20%）
        platform_rate = 0.2
        platform_fee = int(price * platform_rate)
        creator_amount = price - platform_fee

        # 检查余额
        if subscriber_wallet.balance < price:
            raise ValueError(f"余额不足：{subscriber_wallet.balance} < {price}")

        # 创建订阅记录
        now = datetime.now()
        subscription = DBSubscription(
            id=str(uuid.uuid4()),
            subscriber_id=subscriber_id,
            creator_id=creator_id,
            tier=tier_enum,
            period=period_enum,
            price=price,
            status=SubscriptionStatusEnum.ACTIVE,
            start_date=now,
            next_billing_date=self._calculate_next_billing(period_enum, now),
            total_paid=price,
            billing_count=1,
        )
        self.db.add(subscription)
        await self.db.flush()

        try:
            # 扣款
            await self.wallet_service.update_balance(
                wallet_id=subscriber_wallet.id,
                amount=-price,
                transaction_type=TransactionTypeEnum.SUBSCRIPTION_PAID,
                description=f"订阅创作者 {creator_id} ({tier.value}/{period.value})",
                related_user_id=creator_id,
                metadata={
                    "subscription_id": subscription.id,
                    "tier": tier.value,
                    "period": period.value
                }
            )

            # 给创作者加款
            await self.wallet_service.update_balance(
                wallet_id=creator_wallet.id,
                amount=creator_amount,
                transaction_type=TransactionTypeEnum.SUBSCRIPTION_RECEIVED,
                description=f"收到订阅收入（{tier.value}/{period.value}）",
                related_user_id=subscriber_id,
                metadata={
                    "subscription_id": subscription.id,
                    "gross_amount": price,
                    "platform_fee": platform_fee
                }
            )

            # 平台分成
            platform_wallet = await self.wallet_service.get_or_create_wallet("platform", "system")
            await self.wallet_service.update_balance(
                wallet_id=platform_wallet.id,
                amount=platform_fee,
                transaction_type=TransactionTypeEnum.FEE,
                description=f"订阅平台分成 ({platform_rate*100}%)",
                related_user_id=creator_id,
                metadata={
                    "subscription_id": subscription.id,
                    "rate": platform_rate
                }
            )

            await self.db.commit()
            await self.db.refresh(subscription)

            logger.info(
                f"订阅创建成功：{subscription.id}, "
                f"订阅者：{subscriber_id}, 创作者：{creator_id}, "
                f"价格：{price}分，创作者收益：{creator_amount}分"
            )

            return self._to_domain_model(subscription)

        except Exception as e:
            subscription.status = SubscriptionStatusEnum.PENDING
            await self.db.commit()
            logger.error(f"创建订阅失败：{e}")
            raise

    async def cancel_subscription(self, subscription_id: str) -> Subscription:
        """取消订阅"""
        result = await self.db.execute(
            select(DBSubscription).where(DBSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise ValueError(f"订阅不存在：{subscription_id}")

        if subscription.status != SubscriptionStatusEnum.ACTIVE:
            raise ValueError(f"订阅状态异常：{subscription.status.value}")

        subscription.status = SubscriptionStatusEnum.CANCELLED
        subscription.cancelled_at = datetime.now()
        subscription.next_billing_date = None

        await self.db.commit()
        await self.db.refresh(subscription)

        logger.info(f"订阅已取消：{subscription_id}")
        return self._to_domain_model(subscription)

    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """获取订阅详情"""
        result = await self.db.execute(
            select(DBSubscription).where(DBSubscription.id == subscription_id)
        )
        db_subscription = result.scalar_one_or_none()
        if db_subscription:
            return self._to_domain_model(db_subscription)
        return None

    async def get_active_subscription(
        self,
        subscriber_id: str,
        creator_id: str
    ) -> Optional[Subscription]:
        """获取活跃订阅"""
        result = await self.db.execute(
            select(DBSubscription).where(
                DBSubscription.subscriber_id == subscriber_id,
                DBSubscription.creator_id == creator_id,
                DBSubscription.status == SubscriptionStatusEnum.ACTIVE
            )
        )
        db_subscription = result.scalar_one_or_none()
        if db_subscription:
            return self._to_domain_model(db_subscription)
        return None

    async def get_subscriptions_by_subscriber(
        self,
        subscriber_id: str,
        status: Optional[SubscriptionStatus] = None,
        limit: int = 50
    ) -> List[Subscription]:
        """获取订阅者的订阅列表"""
        query = select(DBSubscription).where(
            DBSubscription.subscriber_id == subscriber_id
        )

        if status:
            status_enum = SubscriptionStatusEnum(status.value)
            query = query.where(DBSubscription.status == status_enum)

        query = query.order_by(desc(DBSubscription.created_at)).limit(limit)

        result = await self.db.execute(query)
        subscriptions = result.scalars().all()
        return [self._to_domain_model(sub) for sub in subscriptions]

    async def get_subscriptions_by_creator(
        self,
        creator_id: str,
        status: Optional[SubscriptionStatus] = None,
        limit: int = 50
    ) -> List[Subscription]:
        """获取创作者的订阅者列表"""
        query = select(DBSubscription).where(
            DBSubscription.creator_id == creator_id
        )

        if status:
            status_enum = SubscriptionStatusEnum(status.value)
            query = query.where(DBSubscription.status == status_enum)

        query = query.order_by(desc(DBSubscription.created_at)).limit(limit)

        result = await self.db.execute(query)
        subscriptions = result.scalars().all()
        return [self._to_domain_model(sub) for sub in subscriptions]

    async def get_subscriber_count(
        self,
        creator_id: str
    ) -> Dict[str, int]:
        """获取创作者订阅者统计"""
        # 总订阅数
        total_result = await self.db.execute(
            select(func.count(DBSubscription.id)).where(
                DBSubscription.creator_id == creator_id
            )
        )
        total = total_result.scalar() or 0

        # 活跃订阅数
        active_result = await self.db.execute(
            select(func.count(DBSubscription.id)).where(
                DBSubscription.creator_id == creator_id,
                DBSubscription.status == SubscriptionStatusEnum.ACTIVE
            )
        )
        active = active_result.scalar() or 0

        # 按等级统计
        tier_result = await self.db.execute(
            select(
                DBSubscription.tier,
                func.count(DBSubscription.id)
            ).where(
                DBSubscription.creator_id == creator_id,
                DBSubscription.status == SubscriptionStatusEnum.ACTIVE
            ).group_by(DBSubscription.tier)
        )
        tier_stats = {}
        for row in tier_result.all():
            tier_name = row[0].value
            tier_stats[tier_name] = row[1] or 0

        return {
            "total": total,
            "active": active,
            "by_tier": tier_stats
        }

    async def get_revenue_summary(
        self,
        creator_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取创作者订阅收入统计"""
        from datetime import timedelta
        start_date = datetime.now() - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.count(DBSubscription.id).label('count'),
                func.sum(DBSubscription.total_paid).label('total_revenue')
            ).where(
                DBSubscription.creator_id == creator_id,
                DBSubscription.start_date >= start_date
            )
        )
        row = result.one()

        return {
            "creator_id": creator_id,
            "period_days": days,
            "subscription_count": row[0] or 0,
            "total_revenue": row[1] or 0,
        }

    async def get_subscription_benefits(
        self,
        tier: SubscriptionTier
    ) -> List[SubscriptionBenefit]:
        """获取订阅等级权益"""
        tier_enum = SubscriptionTierEnum(tier.value)

        result = await self.db.execute(
            select(DBSubscriptionBenefit).where(
                DBSubscriptionBenefit.tier == tier_enum
            )
        )
        benefits = result.scalars().all()

        if not benefits:
            # 返回默认权益
            config = SUBSCRIPTION_CONFIG.get(tier_enum, {})
            default_benefits = config.get("benefits", [])
            return [
                SubscriptionBenefit(
                    tier=tier,
                    name=benefit,
                    description=benefit
                )
                for benefit in default_benefits
            ]

        return [
            SubscriptionBenefit(
                id=b.id,
                tier=SubscriptionTier(b.tier.value),
                name=b.name,
                description=b.description,
                icon=b.icon,
            )
            for b in benefits
        ]

    def _to_domain_model(self, db_sub: DBSubscription) -> Subscription:
        """转换为领域模型"""
        tier_map = {
            SubscriptionTierEnum.FREE: SubscriptionTier.FREE,
            SubscriptionTierEnum.BASIC: SubscriptionTier.BASIC,
            SubscriptionTierEnum.PREMIUM: SubscriptionTier.PREMIUM,
            SubscriptionTierEnum.VIP: SubscriptionTier.VIP,
            SubscriptionTierEnum.EXCLUSIVE: SubscriptionTier.EXCLUSIVE,
        }
        period_map = {
            SubscriptionPeriodEnum.MONTHLY: SubscriptionPeriod.MONTHLY,
            SubscriptionPeriodEnum.QUARTERLY: SubscriptionPeriod.QUARTERLY,
            SubscriptionPeriodEnum.YEARLY: SubscriptionPeriod.YEARLY,
        }
        status_map = {
            SubscriptionStatusEnum.ACTIVE: SubscriptionStatus.ACTIVE,
            SubscriptionStatusEnum.EXPIRED: SubscriptionStatus.EXPIRED,
            SubscriptionStatusEnum.CANCELLED: SubscriptionStatus.CANCELLED,
            SubscriptionStatusEnum.PENDING: SubscriptionStatus.PENDING,
        }
        return Subscription(
            id=db_sub.id,
            subscriber_id=db_sub.subscriber_id,
            creator_id=db_sub.creator_id,
            tier=tier_map[db_sub.tier],
            period=period_map[db_sub.period],
            price=db_sub.price,
            status=status_map[db_sub.status],
            start_date=db_sub.start_date,
            next_billing_date=db_sub.next_billing_date,
            cancelled_at=db_sub.cancelled_at,
            expired_at=db_sub.expired_at,
            total_paid=db_sub.total_paid,
            billing_count=db_sub.billing_count,
            created_at=db_sub.created_at,
            updated_at=db_sub.updated_at,
        )


# 全局服务实例
_subscription_service = None


def get_subscription_service(db: AsyncSession) -> SubscriptionService:
    """获取订阅服务实例"""
    global _subscription_service
    if _subscription_service is None or _subscription_service.db is not db:
        _subscription_service = SubscriptionService(db)
    return _subscription_service
