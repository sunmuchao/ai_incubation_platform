"""
支付与结算服务（Mock实现，供接口层使用）。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from models.payment import (
    PaymentRequest,
    PaymentStatus,
    PaymentTransaction,
    PayoutRequest,
    TaskPaymentRequest,
    TransactionType,
    Wallet,
)

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Mock支付服务，实现核心支付接口：
    1. 钱包管理
    2. 充值/提现
    3. 任务支付与结算
    4. 交易记录查询
    """

    def __init__(self) -> None:
        self._wallets: Dict[str, Wallet] = {}  # user_id -> Wallet
        self._transactions: Dict[str, PaymentTransaction] = {}  # transaction_id -> PaymentTransaction
        self._task_transactions: Dict[str, List[str]] = {}  # task_id -> [transaction_id]

        # 默认平台服务费比例
        self.DEFAULT_PLATFORM_FEE_RATE = 0.1  # 10%
        # 最低平台服务费
        self.MIN_PLATFORM_FEE = 1.0  # 1元

    def _get_or_create_wallet(self, user_id: str) -> Wallet:
        """获取或创建用户钱包。"""
        if user_id not in self._wallets:
            self._wallets[user_id] = Wallet(user_id=user_id)
        return self._wallets[user_id]

    def create_deposit(self, request: PaymentRequest) -> PaymentTransaction:
        """创建充值订单。"""
        tx = PaymentTransaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=request.amount,
            payer_id=request.user_id,
            payee_id="platform",
            payment_method=request.payment_method,
            description=request.description or "账户充值",
        )
        self._transactions[tx.id] = tx

        # Mock: 直接充值成功
        tx.status = PaymentStatus.SUCCESS
        tx.completed_at = datetime.now()
        wallet = self._get_or_create_wallet(request.user_id)
        wallet.balance += request.amount
        wallet.updated_at = datetime.now()

        logger.info("Deposit success: user_id=%s, amount=%.2f, tx_id=%s",
                    request.user_id, request.amount, tx.id)
        return tx

    def create_payout(self, request: PayoutRequest) -> PaymentTransaction:
        """创建提现申请。"""
        wallet = self._get_or_create_wallet(request.worker_id)
        if wallet.balance < request.amount:
            raise ValueError("Insufficient balance")

        tx = PaymentTransaction(
            transaction_type=TransactionType.WORKER_PAYOUT,
            amount=request.amount,
            payer_id="platform",
            payee_id=request.worker_id,
            payment_method=request.payout_method,
            description=f"提现到{request.payout_method}",
        )
        self._transactions[tx.id] = tx

        # 冻结提现金额
        wallet.balance -= request.amount
        wallet.frozen_balance += request.amount
        wallet.updated_at = datetime.now()

        # Mock: 直接提现成功
        tx.status = PaymentStatus.SUCCESS
        tx.completed_at = datetime.now()
        wallet.frozen_balance -= request.amount
        wallet.updated_at = datetime.now()

        logger.info("Payout success: worker_id=%s, amount=%.2f, tx_id=%s",
                    request.worker_id, request.amount, tx.id)
        return tx

    def process_task_payment(self, request: TaskPaymentRequest) -> Tuple[PaymentTransaction, PaymentTransaction]:
        """
        处理任务支付：
        1. 从雇主账户扣除任务金额
        2. 扣除平台服务费
        3. 将剩余金额结算到工人账户
        返回 (支付交易, 服务费交易)
        """
        # 计算平台服务费
        platform_fee = max(request.amount * request.platform_fee_rate, self.MIN_PLATFORM_FEE)
        worker_amount = request.amount - platform_fee

        # 检查雇主余额
        employer_wallet = self._get_or_create_wallet(request.ai_employer_id)
        if employer_wallet.balance < request.amount:
            raise ValueError("Employer insufficient balance")

        # 1. 创建任务支付交易（雇主 -> 平台）
        payment_tx = PaymentTransaction(
            transaction_type=TransactionType.TASK_PAYMENT,
            amount=request.amount,
            payer_id=request.ai_employer_id,
            payee_id="platform",
            task_id=request.task_id,
            description=f"任务支付: {request.task_id}",
            status=PaymentStatus.SUCCESS,
            completed_at=datetime.now(),
        )
        self._transactions[payment_tx.id] = payment_tx

        # 扣除雇主余额
        employer_wallet.balance -= request.amount
        employer_wallet.updated_at = datetime.now()

        # 2. 创建平台服务费交易
        fee_tx = PaymentTransaction(
            transaction_type=TransactionType.PLATFORM_FEE,
            amount=platform_fee,
            payer_id="platform",
            payee_id="platform",
            task_id=request.task_id,
            description=f"平台服务费: {request.task_id}",
            status=PaymentStatus.SUCCESS,
            completed_at=datetime.now(),
        )
        self._transactions[fee_tx.id] = fee_tx

        # 3. 结算给工人
        worker_wallet = self._get_or_create_wallet(request.worker_id)
        worker_wallet.balance += worker_amount
        worker_wallet.updated_at = datetime.now()

        # 记录任务关联交易
        if request.task_id not in self._task_transactions:
            self._task_transactions[request.task_id] = []
        self._task_transactions[request.task_id].extend([payment_tx.id, fee_tx.id])

        logger.info("Task payment processed: task_id=%s, total=%.2f, fee=%.2f, worker_get=%.2f",
                    request.task_id, request.amount, platform_fee, worker_amount)
        return payment_tx, fee_tx

    def refund_task_payment(self, task_id: str, reason: Optional[str] = None) -> Optional[PaymentTransaction]:
        """任务取消/验收不通过时退款给雇主。"""
        if task_id not in self._task_transactions:
            return None

        # 找到对应的支付交易
        payment_tx = None
        for tx_id in self._task_transactions[task_id]:
            tx = self._transactions.get(tx_id)
            if tx and tx.transaction_type == TransactionType.TASK_PAYMENT and tx.status == PaymentStatus.SUCCESS:
                payment_tx = tx
                break

        if not payment_tx:
            return None

        # 创建退款交易
        refund_tx = PaymentTransaction(
            transaction_type=TransactionType.TASK_REFUND,
            amount=payment_tx.amount,
            payer_id="platform",
            payee_id=payment_tx.payer_id,
            task_id=task_id,
            description=reason or f"任务退款: {task_id}",
            status=PaymentStatus.SUCCESS,
            completed_at=datetime.now(),
        )
        self._transactions[refund_tx.id] = refund_tx

        # 退回雇主余额
        if payment_tx.payer_id:
            employer_wallet = self._get_or_create_wallet(payment_tx.payer_id)
            employer_wallet.balance += payment_tx.amount
            employer_wallet.updated_at = datetime.now()

        logger.info("Task refund success: task_id=%s, amount=%.2f, tx_id=%s",
                    task_id, payment_tx.amount, refund_tx.id)
        return refund_tx

    def get_wallet_balance(self, user_id: str) -> Wallet:
        """获取用户钱包余额。"""
        return self._get_or_create_wallet(user_id)

    def get_transaction(self, transaction_id: str) -> Optional[PaymentTransaction]:
        """获取交易详情。"""
        return self._transactions.get(transaction_id)

    def list_user_transactions(self, user_id: str, limit: int = 20) -> List[PaymentTransaction]:
        """列出用户的交易记录。"""
        txs = [
            tx for tx in self._transactions.values()
            if tx.payer_id == user_id or tx.payee_id == user_id
        ]
        txs.sort(key=lambda x: x.created_at, reverse=True)
        return txs[:limit]

    def list_task_transactions(self, task_id: str) -> List[PaymentTransaction]:
        """列出任务相关的所有交易。"""
        tx_ids = self._task_transactions.get(task_id, [])
        return [self._transactions[tx_id] for tx_id in tx_ids if tx_id in self._transactions]


payment_service = PaymentService()
