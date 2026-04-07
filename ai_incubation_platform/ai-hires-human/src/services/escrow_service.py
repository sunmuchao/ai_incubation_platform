"""
Escrow 资金托管服务。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from models.escrow import (
    EscrowCreate,
    EscrowDisputeRequest,
    EscrowResolutionRequest,
    EscrowStatus,
    EscrowTransaction,
)
from models.payment import TransactionType, PaymentTransaction
from services.payment_service import payment_service

logger = logging.getLogger(__name__)


class EscrowService:
    """
    Escrow 资金托管服务，提供以下功能：
    1. 资金托管账户管理
    2. 任务发布时资金冻结
    3. 验收通过后资金释放
    4. 争议仲裁资金分配
    5. 退款处理
    """

    def __init__(self) -> None:
        # Escrow 交易记录：task_id -> EscrowTransaction
        self._escrows: Dict[str, EscrowTransaction] = {}
        # 用户 Escrow 索引：user_id -> [task_id, ...]
        self._employer_escrows: Dict[str, List[str]] = {}
        self._worker_escrows: Dict[str, List[str]] = {}

    def create_escrow(self, request: EscrowCreate) -> EscrowTransaction:
        """
        创建 Escrow 托管，冻结雇主资金。

        流程：
        1. 检查雇主余额是否充足
        2. 扣除雇主账户相应金额（本金 + 平台服务费）
        3. 创建 Escrow 记录
        4. 资金标记为冻结状态
        """
        if request.task_id in self._escrows:
            raise ValueError(f"Escrow already exists for task {request.task_id}")

        # 计算金额
        principal_amount = request.principal_amount
        platform_fee = max(principal_amount * request.platform_fee_rate, 1.0)  # 最低 1 元
        total_amount = principal_amount + platform_fee

        # 检查并扣除雇主余额
        wallet = payment_service.get_wallet_balance(request.ai_employer_id)
        if wallet.balance < total_amount:
            raise ValueError(
                f"Insufficient balance: required {total_amount}, "
                f"available {wallet.balance}"
            )

        # 扣除雇主余额（转到 Escrow 托管账户）
        wallet.balance -= total_amount
        wallet.updated_at = datetime.now()

        # 创建 Escrow 记录
        escrow = EscrowTransaction(
            task_id=request.task_id,
            ai_employer_id=request.ai_employer_id,
            principal_amount=principal_amount,
            platform_fee=platform_fee,
            total_amount=total_amount,
            status=EscrowStatus.FUNDED,
            funded_at=datetime.now(),
        )

        self._escrows[request.task_id] = escrow

        # 建立索引
        if request.ai_employer_id not in self._employer_escrows:
            self._employer_escrows[request.ai_employer_id] = []
        self._employer_escrows[request.ai_employer_id].append(request.task_id)

        logger.info(
            "Escrow created: task_id=%s, employer=%s, total=%.2f, principal=%.2f, fee=%.2f",
            request.task_id, request.ai_employer_id, total_amount, principal_amount, platform_fee
        )

        return escrow

    def get_escrow(self, task_id: str) -> Optional[EscrowTransaction]:
        """获取 Escrow 详情。"""
        return self._escrows.get(task_id)

    def release_escrow(
        self,
        task_id: str,
        worker_id: str,
        operator_id: str,
    ) -> Tuple[EscrowTransaction, PaymentTransaction]:
        """
        释放 Escrow 资金给工人。

        验收通过后调用，将托管资金（扣除平台服务费后）转入工人账户。
        返回 (Escrow 交易，支付交易)
        """
        escrow = self._escrows.get(task_id)
        if not escrow:
            raise ValueError(f"Escrow not found for task {task_id}")

        if escrow.status != EscrowStatus.FUNDED:
            raise ValueError(f"Escrow not in FUNDED status: {escrow.status}")

        # 更新工人 ID（如果之前未设置）
        if not escrow.worker_id:
            escrow.worker_id = worker_id
            self._worker_escrows.setdefault(worker_id, []).append(task_id)

        # 计算工人应得金额（本金 - 平台服务费）
        worker_amount = escrow.principal_amount

        # 将工人金额转入工人钱包
        worker_wallet = payment_service.get_wallet_balance(worker_id)
        worker_wallet.balance += worker_amount
        worker_wallet.updated_at = datetime.now()

        # 平台服务费计入平台收入（这里简化处理，实际应有专门的平台账户）
        platform_wallet = payment_service.get_wallet_balance("platform")
        platform_wallet.balance += escrow.platform_fee
        platform_wallet.updated_at = datetime.now()

        # 创建支付交易记录
        payment_tx = PaymentTransaction(
            transaction_type=TransactionType.TASK_PAYMENT,
            amount=escrow.total_amount,
            payer_id=escrow.ai_employer_id,
            payee_id=worker_id,
            task_id=task_id,
            payment_method="escrow_release",
            description=f"Escrow 释放：任务 {task_id}",
            fee_amount=escrow.platform_fee,
            status="success",
            completed_at=datetime.now(),
        )

        # 更新 Escrow 状态
        escrow.status = EscrowStatus.RELEASED
        escrow.released_at = datetime.now()
        escrow.released_by = operator_id
        escrow.updated_at = datetime.now()

        logger.info(
            "Escrow released: task_id=%s, worker=%s, amount=%.2f, fee=%.2f",
            task_id, worker_id, worker_amount, escrow.platform_fee
        )

        return escrow, payment_tx

    def refund_escrow(
        self,
        task_id: str,
        operator_id: str,
        reason: Optional[str] = None,
    ) -> Tuple[EscrowTransaction, PaymentTransaction]:
        """
        退款 Escrow 资金给雇主。

        任务取消或验收不通过时调用，将托管资金（全额）退回雇主账户。
        返回 (Escrow 交易，支付交易)
        """
        escrow = self._escrows.get(task_id)
        if not escrow:
            raise ValueError(f"Escrow not found for task {task_id}")

        if escrow.status != EscrowStatus.FUNDED:
            raise ValueError(f"Escrow not in FUNDED status: {escrow.status}")

        # 将全额资金退回雇主钱包
        employer_wallet = payment_service.get_wallet_balance(escrow.ai_employer_id)
        employer_wallet.balance += escrow.total_amount
        employer_wallet.updated_at = datetime.now()

        # 创建退款交易记录
        refund_tx = PaymentTransaction(
            transaction_type=TransactionType.TASK_REFUND,
            amount=escrow.total_amount,
            payer_id="platform",
            payee_id=escrow.ai_employer_id,
            task_id=task_id,
            payment_method="escrow_refund",
            description=reason or f"Escrow 退款：任务 {task_id}",
            status="success",
            completed_at=datetime.now(),
        )

        # 更新 Escrow 状态
        escrow.status = EscrowStatus.REFUNDED
        escrow.refunded_at = datetime.now()
        escrow.refunded_by = operator_id
        escrow.updated_at = datetime.now()

        logger.info(
            "Escrow refunded: task_id=%s, employer=%s, amount=%.2f",
            task_id, escrow.ai_employer_id, escrow.total_amount
        )

        return escrow, refund_tx

    def dispute_escrow(self, request: EscrowDisputeRequest) -> EscrowTransaction:
        """
        对 Escrow 提出争议。

        争议期间资金保持冻结状态。
        """
        escrow = self._escrows.get(request.task_id)
        if not escrow:
            raise ValueError(f"Escrow not found for task {request.task_id}")

        if escrow.status != EscrowStatus.FUNDED:
            raise ValueError(f"Escrow not in FUNDED status: {escrow.status}")

        # 更新 Escrow 状态为争议中
        escrow.status = EscrowStatus.DISPUTED
        escrow.dispute_reason = request.reason
        escrow.updated_at = datetime.now()

        logger.info(
            "Escrow disputed: task_id=%s, requester=%s, reason=%s",
            request.task_id, request.requester_id, request.reason
        )

        return escrow

    def resolve_escrow_dispute(self, request: EscrowResolutionRequest) -> EscrowTransaction:
        """
        仲裁 Escrow 争议。

        resolution 选项：
        - "employer_full": 全额退款给雇主
        - "worker_full": 全额支付给工人
        - "split": 按比例分配
        """
        escrow = self._escrows.get(request.task_id)
        if not escrow:
            raise ValueError(f"Escrow not found for task {request.task_id}")

        if escrow.status != EscrowStatus.DISPUTED:
            raise ValueError(f"Escrow not in DISPUTED status: {escrow.status}")

        resolution = request.resolution
        split_ratio = request.split_ratio or 0.0

        if resolution == "employer_full":
            # 全额退款给雇主
            employer_wallet = payment_service.get_wallet_balance(escrow.ai_employer_id)
            employer_wallet.balance += escrow.total_amount
            employer_wallet.updated_at = datetime.now()

        elif resolution == "worker_full":
            # 全额支付给工人（本金 + 服务费都给工人）
            worker_wallet = payment_service.get_wallet_balance(escrow.worker_id)
            worker_wallet.balance += escrow.principal_amount + escrow.platform_fee
            worker_wallet.updated_at = datetime.now()

        elif resolution == "split":
            # 按比例分配：工人获得 split_ratio * principal，雇主获得剩余部分
            # 如果没有设置 worker_id，使用请求中的信息或跳过工人部分
            if not escrow.worker_id:
                # 尝试从争议原因推断或设置默认值
                escrow.worker_id = "unknown_worker"

            worker_amount = escrow.principal_amount * split_ratio
            employer_amount = escrow.total_amount - worker_amount

            worker_wallet = payment_service.get_wallet_balance(escrow.worker_id)
            worker_wallet.balance += worker_amount
            worker_wallet.updated_at = datetime.now()

            employer_wallet = payment_service.get_wallet_balance(escrow.ai_employer_id)
            employer_wallet.balance += employer_amount
            employer_wallet.updated_at = datetime.now()

        else:
            raise ValueError(f"Invalid resolution: {resolution}")

        # 更新 Escrow 状态
        escrow.status = EscrowStatus.RELEASED
        escrow.dispute_resolution = resolution
        escrow.split_ratio = split_ratio
        escrow.resolved_by = request.resolver_id
        escrow.released_at = datetime.now()
        escrow.updated_at = datetime.now()

        logger.info(
            "Escrow dispute resolved: task_id=%s, resolution=%s, split_ratio=%s",
            request.task_id, resolution, split_ratio
        )

        return escrow

    def get_employer_escrows(self, employer_id: str) -> List[EscrowTransaction]:
        """获取雇主的所有 Escrow 记录。"""
        task_ids = self._employer_escrows.get(employer_id, [])
        return [self._escrows[tid] for tid in task_ids if tid in self._escrows]

    def get_worker_escrows(self, worker_id: str) -> List[EscrowTransaction]:
        """获取工人的所有 Escrow 记录。"""
        task_ids = self._worker_escrows.get(worker_id, [])
        return [self._escrows[tid] for tid in task_ids if tid in self._escrows]

    def list_escrows_by_status(self, status: EscrowStatus) -> List[EscrowTransaction]:
        """按状态列出 Escrow 记录。"""
        return [e for e in self._escrows.values() if e.status == status]

    def get_escrow_summary(self) -> Dict:
        """获取 Escrow 汇总统计。"""
        total_funded = sum(
            e.total_amount for e in self._escrows.values() if e.status == EscrowStatus.FUNDED
        )
        total_released = sum(
            e.total_amount for e in self._escrows.values() if e.status == EscrowStatus.RELEASED
        )
        total_disputed = sum(
            e.total_amount for e in self._escrows.values() if e.status == EscrowStatus.DISPUTED
        )

        return {
            "total_escrows": len(self._escrows),
            "total_funded": total_funded,
            "total_released": total_released,
            "total_disputed": total_disputed,
            "status_counts": {
                status.value: len([e for e in self._escrows.values() if e.status == status])
                for status in EscrowStatus
            },
        }


escrow_service = EscrowService()
