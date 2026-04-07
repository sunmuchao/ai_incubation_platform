"""
钱包服务 - 管理用户钱包和交易
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime
import logging
import uuid
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.economy_models import (
    DBWallet, DBWalletTransaction, WalletStatusEnum,
    TransactionTypeEnum, TransactionStatusEnum
)
from models.economy import (
    Wallet, WalletTransaction, WalletStatus,
    WalletTransactionType, TransactionStatus
)

logger = logging.getLogger(__name__)


class WalletService:
    """钱包服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_wallet(
        self,
        owner_id: str,
        owner_type: str = "member"
    ) -> Wallet:
        """创建钱包"""
        wallet = DBWallet(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            owner_type=owner_type,
            status=WalletStatusEnum.ACTIVE,
            balance=0,
            pending_balance=0,
            total_income=0,
            total_spent=0,
        )
        self.db.add(wallet)
        await self.db.commit()
        await self.db.refresh(wallet)

        logger.info(f"创建钱包：{wallet.id} for {owner_id}")
        return self._to_domain_model(wallet)

    async def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """获取钱包"""
        result = await self.db.execute(
            select(DBWallet).where(DBWallet.id == wallet_id)
        )
        db_wallet = result.scalar_one_or_none()
        if db_wallet:
            return self._to_domain_model(db_wallet)
        return None

    async def get_wallet_by_owner(
        self,
        owner_id: str,
        owner_type: str = "member"
    ) -> Optional[Wallet]:
        """根据所有者获取钱包"""
        result = await self.db.execute(
            select(DBWallet).where(
                DBWallet.owner_id == owner_id,
                DBWallet.owner_type == owner_type
            )
        )
        db_wallet = result.scalar_one_or_none()
        if db_wallet:
            return self._to_domain_model(db_wallet)
        return None

    async def get_or_create_wallet(
        self,
        owner_id: str,
        owner_type: str = "member"
    ) -> Wallet:
        """获取或创建钱包"""
        wallet = await self.get_wallet_by_owner(owner_id, owner_type)
        if wallet:
            return wallet
        return await self.create_wallet(owner_id, owner_type)

    async def update_balance(
        self,
        wallet_id: str,
        amount: int,
        transaction_type: TransactionTypeEnum,
        description: str = None,
        related_user_id: str = None,
        related_content_id: str = None,
        related_subscription_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Wallet:
        """
        更新钱包余额

        Args:
            wallet_id: 钱包 ID
            amount: 金额（分），正数增加，负数减少
            transaction_type: 交易类型
            description: 描述
            related_user_id: 相关用户 ID
            related_content_id: 相关内容 ID
            related_subscription_id: 相关订阅 ID
            metadata: 元数据

        Returns:
            更新后的钱包
        """
        result = await self.db.execute(
            select(DBWallet).where(DBWallet.id == wallet_id)
        )
        wallet = result.scalar_one_or_none()

        if not wallet:
            raise ValueError(f"Wallet {wallet_id} not found")

        if wallet.status != WalletStatusEnum.ACTIVE:
            raise ValueError(f"Wallet is not active: {wallet.status}")

        # 检查余额是否足够
        if amount < 0 and wallet.balance < abs(amount):
            raise ValueError(f"Insufficient balance: {wallet.balance} < {abs(amount)}")

        # 更新余额
        if amount >= 0:
            wallet.balance += amount
            wallet.total_income += amount
        else:
            wallet.balance += amount  # amount 是负数
            wallet.total_spent += abs(amount)

        # 创建交易记录
        transaction = DBWalletTransaction(
            id=str(uuid.uuid4()),
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            amount=amount,
            related_user_id=related_user_id,
            related_content_id=related_content_id,
            related_subscription_id=related_subscription_id,
            status=TransactionStatusEnum.COMPLETED,
            description=description,
            extra_data=json.dumps(metadata) if metadata else None,
            completed_at=datetime.now(),
        )
        self.db.add(transaction)

        await self.db.commit()
        await self.db.refresh(wallet)

        logger.info(
            f"钱包 {wallet_id} 余额变更：{amount} 分，"
            f"类型：{transaction_type.value}, "
            f"新余额：{wallet.balance} 分"
        )

        return self._to_domain_model(wallet)

    async def deposit(
        self,
        wallet_id: str,
        amount: int,
        description: str = "充值"
    ) -> Wallet:
        """充值"""
        return await self.update_balance(
            wallet_id=wallet_id,
            amount=amount,
            transaction_type=TransactionTypeEnum.DEPOSIT,
            description=description
        )

    async def withdraw(
        self,
        wallet_id: str,
        amount: int,
        description: str = "提现"
    ) -> Wallet:
        """提现"""
        return await self.update_balance(
            wallet_id=wallet_id,
            amount=-amount,
            transaction_type=TransactionTypeEnum.WITHDRAW,
            description=description
        )

    async def get_transactions(
        self,
        wallet_id: str,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[TransactionTypeEnum] = None
    ) -> List[WalletTransaction]:
        """获取交易记录"""
        query = select(DBWalletTransaction).where(
            DBWalletTransaction.wallet_id == wallet_id
        )

        if transaction_type:
            query = query.where(DBWalletTransaction.transaction_type == transaction_type)

        query = query.order_by(desc(DBWalletTransaction.created_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        transactions = result.scalars().all()

        return [self._transaction_to_domain_model(tx) for tx in transactions]

    async def get_transaction(self, transaction_id: str) -> Optional[WalletTransaction]:
        """获取交易详情"""
        result = await self.db.execute(
            select(DBWalletTransaction).where(DBWalletTransaction.id == transaction_id)
        )
        db_transaction = result.scalar_one_or_none()
        if db_transaction:
            return self._transaction_to_domain_model(db_transaction)
        return None

    async def get_income_summary(
        self,
        wallet_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取收入统计"""
        from datetime import timedelta
        start_date = datetime.now() - timedelta(days=days)

        # 收入类交易类型
        income_types = [
            TransactionTypeEnum.DEPOSIT,
            TransactionTypeEnum.TIP_RECEIVED,
            TransactionTypeEnum.SUBSCRIPTION_RECEIVED,
            TransactionTypeEnum.CREATOR_FUND,
            TransactionTypeEnum.REFUND,
        ]

        result = await self.db.execute(
            select(
                DBWalletTransaction.transaction_type,
                func.sum(DBWalletTransaction.amount).label('total'),
                func.count(DBWalletTransaction.id).label('count')
            ).where(
                DBWalletTransaction.wallet_id == wallet_id,
                DBWalletTransaction.transaction_type.in_(income_types),
                DBWalletTransaction.created_at >= start_date,
                DBWalletTransaction.status == TransactionStatusEnum.COMPLETED
            ).group_by(DBWalletTransaction.transaction_type)
        )

        rows = result.all()

        summary = {
            "wallet_id": wallet_id,
            "period_days": days,
            "total_income": 0,
            "by_type": {}
        }

        for row in rows:
            type_name = row[0].value
            total = row[1] or 0
            count = row[2] or 0
            summary["by_type"][type_name] = {
                "amount": total,
                "count": count
            }
            summary["total_income"] += total

        return summary

    def _to_domain_model(self, db_wallet: DBWallet) -> Wallet:
        """转换为领域模型"""
        status_map = {
            WalletStatusEnum.ACTIVE: WalletStatus.ACTIVE,
            WalletStatusEnum.FROZEN: WalletStatus.FROZEN,
            WalletStatusEnum.CLOSED: WalletStatus.CLOSED,
        }
        return Wallet(
            id=db_wallet.id,
            owner_id=db_wallet.owner_id,
            owner_type=db_wallet.owner_type,
            status=status_map[db_wallet.status],
            balance=db_wallet.balance,
            pending_balance=db_wallet.pending_balance,
            total_income=db_wallet.total_income,
            total_spent=db_wallet.total_spent,
            creator_fund_balance=db_wallet.creator_fund_balance,
            created_at=db_wallet.created_at,
            updated_at=db_wallet.updated_at,
        )

    def _transaction_to_domain_model(self, db_tx: DBWalletTransaction) -> WalletTransaction:
        """转换为交易领域模型"""
        type_map = {
            TransactionTypeEnum.DEPOSIT: WalletTransactionType.DEPOSIT,
            TransactionTypeEnum.TIP_RECEIVED: WalletTransactionType.TIP_RECEIVED,
            TransactionTypeEnum.SUBSCRIPTION_RECEIVED: WalletTransactionType.SUBSCRIPTION_RECEIVED,
            TransactionTypeEnum.CREATOR_FUND: WalletTransactionType.CREATOR_FUND,
            TransactionTypeEnum.REFUND: WalletTransactionType.REFUND,
            TransactionTypeEnum.WITHDRAW: WalletTransactionType.WITHDRAW,
            TransactionTypeEnum.TIP_SENT: WalletTransactionType.TIP_SENT,
            TransactionTypeEnum.SUBSCRIPTION_PAID: WalletTransactionType.SUBSCRIPTION_PAID,
            TransactionTypeEnum.PURCHASE: WalletTransactionType.PURCHASE,
            TransactionTypeEnum.ADJUSTMENT: WalletTransactionType.ADJUSTMENT,
            TransactionTypeEnum.FEE: WalletTransactionType.FEE,
            TransactionTypeEnum.SPLIT: WalletTransactionType.SPLIT,
        }
        status_map = {
            TransactionStatusEnum.PENDING: TransactionStatus.PENDING,
            TransactionStatusEnum.COMPLETED: TransactionStatus.COMPLETED,
            TransactionStatusEnum.FAILED: TransactionStatus.FAILED,
            TransactionStatusEnum.REFUNDED: TransactionStatus.REFUNDED,
        }
        return WalletTransaction(
            id=db_tx.id,
            wallet_id=db_tx.wallet_id,
            transaction_type=type_map[db_tx.transaction_type],
            amount=db_tx.amount,
            related_user_id=db_tx.related_user_id,
            related_content_id=db_tx.related_content_id,
            related_subscription_id=db_tx.related_subscription_id,
            status=status_map[db_tx.status],
            description=db_tx.description,
            metadata=json.loads(db_tx.extra_data) if db_tx.extra_data else {},
            created_at=db_tx.created_at,
            completed_at=db_tx.completed_at,
        )


# 全局服务实例
_wallet_service = None


def get_wallet_service(db: AsyncSession) -> WalletService:
    """获取钱包服务实例"""
    global _wallet_service
    if _wallet_service is None or _wallet_service.db is not db:
        _wallet_service = WalletService(db)
    return _wallet_service
