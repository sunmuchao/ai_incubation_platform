"""
支付与结算 API。
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional

from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.payment import (
    PaymentRequest,
    PaymentTransaction,
    PayoutRequest,
    TaskPaymentRequest,
    Wallet,
)
from services.payment_service import payment_service

router = APIRouter(prefix="/api/payment", tags=["payment"])


@router.post("/deposit", response_model=PaymentTransaction)
async def create_deposit(request: PaymentRequest):
    """账户充值（Mock实现，直接到账）。"""
    try:
        return payment_service.create_deposit(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payout", response_model=PaymentTransaction)
async def create_payout(request: PayoutRequest):
    """工人提现（Mock实现，直接到账）。"""
    try:
        return payment_service.create_payout(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/task-payment", response_model=dict)
async def process_task_payment(request: TaskPaymentRequest):
    """处理任务支付（验收通过后触发）。"""
    try:
        payment_tx, fee_tx = payment_service.process_task_payment(request)
        return {
            "message": "Task payment processed successfully",
            "payment_transaction": payment_tx,
            "fee_transaction": fee_tx,
            "worker_received_amount": request.amount - fee_tx.amount
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refund/{task_id}", response_model=PaymentTransaction)
async def refund_task_payment(task_id: str, reason: Optional[str] = None):
    """任务退款。"""
    tx = payment_service.refund_task_payment(task_id, reason)
    if not tx:
        raise HTTPException(
            status_code=400,
            detail="Refund failed: no successful payment found for this task"
        )
    return tx


@router.get("/wallets/{user_id}", response_model=Wallet)
async def get_wallet_balance(user_id: str):
    """获取用户钱包余额。"""
    return payment_service.get_wallet_balance(user_id)


@router.get("/transactions/{transaction_id}", response_model=PaymentTransaction)
async def get_transaction(transaction_id: str):
    """获取交易详情。"""
    tx = payment_service.get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.get("/users/{user_id}/transactions", response_model=List[PaymentTransaction])
async def list_user_transactions(user_id: str, limit: int = 20):
    """列出用户的交易记录。"""
    return payment_service.list_user_transactions(user_id, limit)


@router.get("/tasks/{task_id}/transactions", response_model=List[PaymentTransaction])
async def list_task_transactions(task_id: str):
    """列出任务相关的所有交易。"""
    return payment_service.list_task_transactions(task_id)
