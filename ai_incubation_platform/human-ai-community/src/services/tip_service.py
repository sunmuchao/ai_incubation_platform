"""
打赏服务 - 管理内容打赏功能
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime
import logging
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.economy_models import (
    DBTip, DBWallet, DBWalletTransaction,
    TipTierEnum, TransactionStatusEnum, TransactionTypeEnum
)
from models.economy import Tip, TipTier, TransactionStatus, TipMessage
from services.wallet_service import WalletService

logger = logging.getLogger(__name__)


class TipService:
    """打赏服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_service = WalletService(db)

    def _calculate_tip_tier(self, amount: int) -> TipTier:
        """根据金额计算打赏等级"""
        if amount <= 1000:  # 10 元以下
            return TipTier.SMALL
        elif amount <= 5000:  # 50 元以下
            return TipTier.MEDIUM
        elif amount <= 20000:  # 200 元以下
            return TipTier.LARGE
        else:
            return TipTier.WHALE

    async def send_tip(
        self,
        sender_id: str,
        receiver_id: str,
        amount: int,
        content_id: str,
        content_type: str,
        message: Optional[str] = None,
        is_anonymous: bool = False,
        is_public_message: bool = True
    ) -> Tip:
        """
        发送打赏

        流程：
        1. 获取或创建 sender 和 receiver 的钱包
        2. 从 sender 钱包扣除金额
        3. 向 receiver 钱包添加金额（扣除平台分成）
        4. 记录平台分成
        5. 创建打赏记录

        Args:
            sender_id: 打赏者 ID
            receiver_id: 接收者 ID
            amount: 金额（分）
            content_id: 内容 ID
            content_type: 内容类型
            message: 打赏留言
            is_anonymous: 是否匿名
            is_public_message: 留言是否公开

        Returns:
            打赏记录
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # 获取或创建钱包
        sender_wallet = await self.wallet_service.get_or_create_wallet(sender_id, "member")
        receiver_wallet = await self.wallet_service.get_or_create_wallet(receiver_id, "member")

        # 平台分成比例（10%）
        platform_rate = 0.1
        platform_fee = int(amount * platform_rate)
        receiver_amount = amount - platform_fee

        # 检查 sender 余额
        if sender_wallet.balance < amount:
            raise ValueError(f"Insufficient balance: {sender_wallet.balance} < {amount}")

        # 创建打赏记录（先创建，状态为 pending）
        tip = DBTip(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_type="member",
            receiver_id=receiver_id,
            receiver_type="member",
            amount=amount,
            tip_tier=self._calculate_tip_tier(amount),
            content_id=content_id,
            content_type=content_type,
            message=message,
            is_anonymous=is_anonymous,
            is_public_message=is_public_message,
            status=TransactionStatusEnum.PENDING,
        )
        self.db.add(tip)
        await self.db.flush()  # 获取 tip.id

        try:
            # 从 sender 扣款
            await self.wallet_service.update_balance(
                wallet_id=sender_wallet.id,
                amount=-amount,
                transaction_type=TransactionTypeEnum.TIP_SENT,
                description=f"打赏内容 {content_id}",
                related_user_id=receiver_id,
                related_content_id=content_id,
                metadata={"tip_id": tip.id}
            )

            # 向 receiver 加款
            await self.wallet_service.update_balance(
                wallet_id=receiver_wallet.id,
                amount=receiver_amount,
                transaction_type=TransactionTypeEnum.TIP_RECEIVED,
                description=f"收到来自{'匿名' if is_anonymous else sender_id}的打赏",
                related_user_id=sender_id,
                related_content_id=content_id,
                metadata={"tip_id": tip.id, "gross_amount": amount, "platform_fee": platform_fee}
            )

            # 记录平台分成
            platform_wallet = await self.wallet_service.get_or_create_wallet("platform", "system")
            await self.wallet_service.update_balance(
                wallet_id=platform_wallet.id,
                amount=platform_fee,
                transaction_type=TransactionTypeEnum.FEE,
                description=f"打赏平台分成 ({platform_rate*100}%)",
                related_user_id=receiver_id,
                related_content_id=content_id,
                metadata={"tip_id": tip.id, "rate": platform_rate}
            )

            # 更新打赏记录状态
            tip.status = TransactionStatusEnum.COMPLETED
            tip.processed_at = datetime.now()

            await self.db.commit()
            await self.db.refresh(tip)

            logger.info(
                f"打赏完成：{tip.id}, 金额：{amount}分，"
                f"接收：{receiver_amount}分，平台分成：{platform_fee}分"
            )

            return self._to_domain_model(tip)

        except Exception as e:
            # 回滚
            tip.status = TransactionStatusEnum.FAILED
            await self.db.commit()
            logger.error(f"打赏失败：{e}")
            raise

    async def get_tip(self, tip_id: str) -> Optional[Tip]:
        """获取打赏记录"""
        result = await self.db.execute(
            select(DBTip).where(DBTip.id == tip_id)
        )
        db_tip = result.scalar_one_or_none()
        if db_tip:
            return self._to_domain_model(db_tip)
        return None

    async def get_tips_by_content(
        self,
        content_id: str,
        content_type: str,
        limit: int = 50
    ) -> List[Tip]:
        """获取内容的打赏记录"""
        result = await self.db.execute(
            select(DBTip).where(
                DBTip.content_id == content_id,
                DBTip.content_type == content_type,
                DBTip.status == TransactionStatusEnum.COMPLETED
            ).order_by(desc(DBTip.amount)).limit(limit)
        )
        tips = result.scalars().all()
        return [self._to_domain_model(tip) for tip in tips]

    async def get_tips_by_sender(
        self,
        sender_id: str,
        limit: int = 50
    ) -> List[Tip]:
        """获取用户的打赏记录"""
        result = await self.db.execute(
            select(DBTip).where(
                DBTip.sender_id == sender_id,
                DBTip.is_anonymous == False  # 只显示非匿名打赏
            ).order_by(desc(DBTip.created_at)).limit(limit)
        )
        tips = result.scalars().all()
        return [self._to_domain_model(tip) for tip in tips]

    async def get_tips_by_receiver(
        self,
        receiver_id: str,
        limit: int = 50
    ) -> List[Tip]:
        """获取用户收到的打赏记录"""
        result = await self.db.execute(
            select(DBTip).where(
                DBTip.receiver_id == receiver_id,
                DBTip.status == TransactionStatusEnum.COMPLETED
            ).order_by(desc(DBTip.created_at)).limit(limit)
        )
        tips = result.scalars().all()
        return [self._to_domain_model(tip) for tip in tips]

    async def get_tip_summary_by_content(
        self,
        content_id: str,
        content_type: str
    ) -> Dict[str, Any]:
        """获取内容的打赏统计"""
        result = await self.db.execute(
            select(
                func.count(DBTip.id).label('tip_count'),
                func.sum(DBTip.amount).label('total_amount'),
                func.avg(DBTip.amount).label('avg_amount')
            ).where(
                DBTip.content_id == content_id,
                DBTip.content_type == content_type,
                DBTip.status == TransactionStatusEnum.COMPLETED
            )
        )
        row = result.one()

        return {
            "content_id": content_id,
            "content_type": content_type,
            "tip_count": row[0] or 0,
            "total_amount": row[1] or 0,
            "avg_amount": float(row[2]) if row[2] else 0,
        }

    async def get_tip_summary_by_receiver(
        self,
        receiver_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取用户收到的打赏统计"""
        from datetime import timedelta
        start_date = datetime.now() - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.count(DBTip.id).label('tip_count'),
                func.sum(DBTip.amount).label('total_amount'),
                func.avg(DBTip.amount).label('avg_amount'),
                func.max(DBTip.amount).label('max_amount')
            ).where(
                DBTip.receiver_id == receiver_id,
                DBTip.status == TransactionStatusEnum.COMPLETED,
                DBTip.created_at >= start_date
            )
        )
        row = result.one()

        # 按等级统计
        tier_result = await self.db.execute(
            select(
                DBTip.tip_tier,
                func.count(DBTip.id).label('count'),
                func.sum(DBTip.amount).label('total')
            ).where(
                DBTip.receiver_id == receiver_id,
                DBTip.status == TransactionStatusEnum.COMPLETED,
                DBTip.created_at >= start_date
            ).group_by(DBTip.tip_tier)
        )
        tier_stats = {}
        for row_tier in tier_result.all():
            tier_name = row_tier[0].value if row_tier[0] else "unknown"
            tier_stats[tier_name] = {
                "count": row_tier[1] or 0,
                "total": row_tier[2] or 0
            }

        return {
            "receiver_id": receiver_id,
            "period_days": days,
            "tip_count": row[0] or 0,
            "total_amount": row[1] or 0,
            "avg_amount": float(row[2]) if row[2] else 0,
            "max_amount": row[3] or 0,
            "by_tier": tier_stats,
        }

    def _to_domain_model(self, db_tip: DBTip) -> Tip:
        """转换为领域模型"""
        tier_map = {
            TipTierEnum.SMALL: TipTier.SMALL,
            TipTierEnum.MEDIUM: TipTier.MEDIUM,
            TipTierEnum.LARGE: TipTier.LARGE,
            TipTierEnum.WHALE: TipTier.WHALE,
        }
        status_map = {
            TransactionStatusEnum.PENDING: TransactionStatus.PENDING,
            TransactionStatusEnum.COMPLETED: TransactionStatus.COMPLETED,
            TransactionStatusEnum.FAILED: TransactionStatus.FAILED,
            TransactionStatusEnum.REFUNDED: TransactionStatus.REFUNDED,
        }
        return Tip(
            id=db_tip.id,
            sender_id=db_tip.sender_id,
            sender_type=db_tip.sender_type,
            receiver_id=db_tip.receiver_id,
            receiver_type=db_tip.receiver_type,
            amount=db_tip.amount,
            tip_tier=tier_map[db_tip.tip_tier] if db_tip.tip_tier else None,
            content_id=db_tip.content_id,
            content_type=db_tip.content_type,
            message=db_tip.message,
            is_anonymous=db_tip.is_anonymous,
            is_public_message=db_tip.is_public_message,
            status=status_map[db_tip.status],
            created_at=db_tip.created_at,
            processed_at=db_tip.processed_at,
        )


# 全局服务实例
_tip_service = None


def get_tip_service(db: AsyncSession) -> TipService:
    """获取打赏服务实例"""
    global _tip_service
    if _tip_service is None or _tip_service.db is not db:
        _tip_service = TipService(db)
    return _tip_service
