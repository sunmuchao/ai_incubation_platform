"""
P8 钱包增强服务

提供：
- 钱包充值
- 自动扣费/定期扣费
- 账单分期支付
- 钱包转账
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid

from models.db_models import (
    WalletDB, PaymentTransactionDB, PaymentStatusEnum,
    TenantDB, UserDB, InvoiceDB
)
from config.logging_config import get_logger

logger = get_logger(__name__)


class AutoDeductionPlanDB:
    """自动扣费计划（内存模型，实际应使用数据库）"""

    def __init__(
        self,
        id: str,
        tenant_id: str,
        user_id: str,
        name: str,
        amount: float,
        frequency: str,  # daily, weekly, monthly
        next_deduction_date: datetime,
        target_type: str,  # invoice, subscription, installment
        target_id: str,
        status: str = "active",  # active, paused, completed, cancelled
        total_amount: Optional[float] = None,
        deducted_amount: float = 0.0,
        remaining_amount: Optional[float] = None,
        deduction_count: int = 0,
        max_deductions: Optional[int] = None,
        payment_method: str = "balance",
        created_at: Optional[datetime] = None,
        last_deduction_at: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        self.id = id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.name = name
        self.amount = amount
        self.frequency = frequency
        self.next_deduction_date = next_deduction_date
        self.target_type = target_type
        self.target_id = target_id
        self.status = status
        self.total_amount = total_amount
        self.deducted_amount = deducted_amount
        self.remaining_amount = remaining_amount
        self.deduction_count = deduction_count
        self.max_deductions = max_deductions
        self.payment_method = payment_method
        self.created_at = created_at or datetime.utcnow()
        self.last_deduction_at = last_deduction_at
        self.end_date = end_date


class WalletEnhancedService:
    """
    钱包增强服务

    功能：
    - 钱包充值（记录充值历史）
    - 自动扣费计划管理
    - 账单分期支付
    - 钱包转账
    """

    def __init__(self, db: Session):
        self.db = db
        self._auto_deduction_plans: Dict[str, AutoDeductionPlanDB] = {}

    # ==================== 钱包充值 ====================

    def recharge_wallet(
        self,
        tenant_id: str,
        user_id: str,
        amount: float,
        payment_method: str,
        transaction_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        钱包充值

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            amount: 充值金额
            payment_method: 支付方式 (alipay/wechat_pay/bank_transfer)
            transaction_id: 第三方支付交易 ID
            description: 描述

        Returns:
            {
                "success": True,
                "recharge_id": "充值记录 ID",
                "amount": 充值金额,
                "new_balance": 充值后余额
            }
        """
        try:
            # 获取或创建钱包
            wallet = self.db.query(WalletDB).filter(
                WalletDB.tenant_id == tenant_id
            ).first()

            if not wallet:
                wallet = WalletDB(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    balance=0.0,
                    currency="CNY"
                )
                self.db.add(wallet)

            # 记录充值前的余额
            old_balance = wallet.balance

            # 更新钱包余额
            wallet.balance += amount
            wallet.total_recharge += amount
            wallet.updated_at = datetime.utcnow()

            # 创建充值记录
            recharge_id = transaction_id or str(uuid.uuid4())
            recharge_record = PaymentTransactionDB(
                id=recharge_id,
                tenant_id=tenant_id,
                user_id=user_id,
                amount=amount,
                payment_method=PaymentMethodEnum(payment_method),
                status=PaymentStatusEnum.SUCCESS,
                payment_data={
                    "type": "recharge",
                    "description": description or "钱包充值",
                    "payment_method": payment_method,
                    "third_party_transaction_id": transaction_id
                },
                created_at=datetime.utcnow()
            )
            self.db.add(recharge_record)

            # 提交事务
            self.db.commit()

            logger.info(f"钱包充值成功：tenant={tenant_id}, amount={amount}, new_balance={wallet.balance}")

            return {
                "success": True,
                "recharge_id": recharge_id,
                "amount": amount,
                "old_balance": old_balance,
                "new_balance": wallet.balance,
                "message": "充值成功"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"钱包充值失败：{e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "充值失败"
            }

    def get_recharge_history(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        获取充值历史
        """
        query = self.db.query(PaymentTransactionDB).filter(
            PaymentTransactionDB.tenant_id == tenant_id,
            PaymentTransactionDB.payment_data["type"].as_string() == "recharge"
        )

        if start_date:
            query = query.filter(PaymentTransactionDB.created_at >= start_date)
        if end_date:
            query = query.filter(PaymentTransactionDB.created_at <= end_date)

        total = query.count()
        payments = query.order_by(
            PaymentTransactionDB.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [
            {
                "recharge_id": p.id,
                "amount": p.amount,
                "payment_method": p.payment_method.value,
                "status": p.status.value,
                "transaction_id": p.payment_data.get("third_party_transaction_id"),
                "description": p.payment_data.get("description"),
                "created_at": p.created_at.isoformat()
            }
            for p in payments
        ], total

    # ==================== 自动扣费计划 ====================

    def create_auto_deduction_plan(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        amount: float,
        frequency: str,
        target_type: str,
        target_id: str,
        total_amount: Optional[float] = None,
        max_deductions: Optional[int] = None,
        payment_method: str = "balance",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        创建自动扣费计划

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            name: 计划名称
            amount: 每次扣费金额
            frequency: 扣费频率 (daily, weekly, monthly)
            target_type: 目标类型 (invoice, subscription, installment)
            target_id: 目标 ID
            total_amount: 总金额（可选，用于分期付款）
            max_deductions: 最大扣费次数
            payment_method: 支付方式
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {
                "success": True,
                "plan_id": "扣费计划 ID",
                "plan_details": {...}
            }
        """
        # 计算下次扣费日期
        now = datetime.utcnow()
        if start_date:
            next_deduction = start_date
        else:
            if frequency == "daily":
                next_deduction = now + timedelta(days=1)
            elif frequency == "weekly":
                next_deduction = now + timedelta(weeks=1)
            else:  # monthly
                next_deduction = now + timedelta(days=30)

        # 计算剩余金额
        remaining_amount = total_amount if total_amount else None

        plan_id = str(uuid.uuid4())
        plan = AutoDeductionPlanDB(
            id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            amount=amount,
            frequency=frequency,
            next_deduction_date=next_deduction,
            target_type=target_type,
            target_id=target_id,
            status="active",
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            max_deductions=max_deductions,
            payment_method=payment_method,
            end_date=end_date
        )

        self._auto_deduction_plans[plan_id] = plan

        logger.info(f"创建自动扣费计划：{plan_id}, name={name}, amount={amount}, frequency={frequency}")

        return {
            "success": True,
            "plan_id": plan_id,
            "plan_details": {
                "id": plan.id,
                "name": plan.name,
                "amount": plan.amount,
                "frequency": plan.frequency,
                "next_deduction_date": plan.next_deduction_date.isoformat(),
                "total_amount": plan.total_amount,
                "remaining_amount": plan.remaining_amount,
                "max_deductions": plan.max_deductions
            },
            "message": "自动扣费计划创建成功"
        }

    def get_auto_deduction_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取自动扣费计划详情"""
        plan = self._auto_deduction_plans.get(plan_id)
        if not plan:
            return None

        return {
            "id": plan.id,
            "tenant_id": plan.tenant_id,
            "user_id": plan.user_id,
            "name": plan.name,
            "amount": plan.amount,
            "frequency": plan.frequency,
            "status": plan.status,
            "next_deduction_date": plan.next_deduction_date.isoformat(),
            "total_amount": plan.total_amount,
            "deducted_amount": plan.deducted_amount,
            "remaining_amount": plan.remaining_amount,
            "deduction_count": plan.deduction_count,
            "max_deductions": plan.max_deductions,
            "payment_method": plan.payment_method,
            "created_at": plan.created_at.isoformat(),
            "last_deduction_at": plan.last_deduction_at.isoformat() if plan.last_deduction_at else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None
        }

    def list_auto_deduction_plans(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取自动扣费计划列表"""
        plans = []
        for plan in self._auto_deduction_plans.values():
            if plan.tenant_id != tenant_id:
                continue
            if user_id and plan.user_id != user_id:
                continue
            if status and plan.status != status:
                continue

            plans.append({
                "id": plan.id,
                "name": plan.name,
                "amount": plan.amount,
                "frequency": plan.frequency,
                "status": plan.status,
                "next_deduction_date": plan.next_deduction_date.isoformat(),
                "deducted_amount": plan.deducted_amount,
                "remaining_amount": plan.remaining_amount
            })

        return plans

    def cancel_auto_deduction_plan(self, plan_id: str, user_id: str) -> Dict[str, Any]:
        """取消自动扣费计划"""
        plan = self._auto_deduction_plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "计划不存在"}

        if plan.user_id != user_id:
            return {"success": False, "error": "无权操作此计划"}

        plan.status = "cancelled"
        logger.info(f"取消自动扣费计划：{plan_id}")

        return {"success": True, "message": "计划已取消"}

    def process_auto_deductions(self) -> Dict[str, Any]:
        """
        处理到期的自动扣费

        应该由定时任务调用
        """
        now = datetime.utcnow()
        results = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "total_amount": 0.0,
            "details": []
        }

        for plan in self._auto_deduction_plans.values():
            if plan.status != "active":
                continue

            if plan.next_deduction_date > now:
                continue

            # 检查是否超过最大扣费次数
            if plan.max_deductions and plan.deduction_count >= plan.max_deductions:
                plan.status = "completed"
                continue

            # 检查剩余金额
            if plan.remaining_amount is not None and plan.remaining_amount <= 0:
                plan.status = "completed"
                continue

            # 获取钱包
            wallet = self.db.query(WalletDB).filter(
                WalletDB.tenant_id == plan.tenant_id
            ).first()

            if not wallet or wallet.balance < plan.amount:
                results["failed"] += 1
                results["details"].append({
                    "plan_id": plan.id,
                    "name": plan.name,
                    "error": "钱包余额不足"
                })
                continue

            # 执行扣费
            old_balance = wallet.balance
            wallet.balance -= plan.amount
            wallet.total_consumption += plan.amount
            wallet.updated_at = datetime.utcnow()

            # 记录扣费
            deduction_record = PaymentTransactionDB(
                id=str(uuid.uuid4()),
                tenant_id=plan.tenant_id,
                user_id=plan.user_id,
                amount=plan.amount,
                payment_method=PaymentMethodEnum(plan.payment_method),
                status=PaymentStatusEnum.SUCCESS,
                payment_data={
                    "type": "auto_deduction",
                    "plan_id": plan.id,
                    "plan_name": plan.name,
                    "target_type": plan.target_type,
                    "target_id": plan.target_id
                }
            )
            self.db.add(deduction_record)

            # 更新计划状态
            plan.deducted_amount += plan.amount
            if plan.remaining_amount is not None:
                plan.remaining_amount -= plan.amount
            plan.deduction_count += 1
            plan.last_deduction_at = now

            # 计算下次扣费日期
            if plan.frequency == "daily":
                plan.next_deduction_date = now + timedelta(days=1)
            elif plan.frequency == "weekly":
                plan.next_deduction_date = now + timedelta(weeks=1)
            else:  # monthly
                plan.next_deduction_date = now + timedelta(days=30)

            # 检查是否完成
            if (
                plan.remaining_amount is not None and plan.remaining_amount <= 0
            ) or (
                plan.max_deductions and plan.deduction_count >= plan.max_deductions
            ):
                plan.status = "completed"

            results["success"] += 1
            results["total_amount"] += plan.amount
            results["details"].append({
                "plan_id": plan.id,
                "name": plan.name,
                "amount": plan.amount,
                "new_balance": wallet.balance,
                "deduction_count": plan.deduction_count
            })

            results["processed"] += 1

        # 提交事务
        try:
            self.db.commit()
            logger.info(f"处理自动扣费完成：processed={results['processed']}, success={results['success']}, failed={results['failed']}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"处理自动扣费失败：{e}", exc_info=True)
            results["error"] = str(e)

        return results

    # ==================== 账单分期支付 ====================

    def create_installment_plan(
        self,
        tenant_id: str,
        user_id: str,
        invoice_id: str,
        total_amount: float,
        installments: int,
        payment_method: str = "balance"
    ) -> Dict[str, Any]:
        """
        创建账单分期支付计划

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            invoice_id: 账单 ID
            total_amount: 总金额
            installments: 分期期数
            payment_method: 支付方式

        Returns:
            {
                "success": True,
                "plan_id": "分期计划 ID",
                "installment_amount": 每期金额,
                "total_amount": 总金额,
                "installments": 期数
            }
        """
        installment_amount = total_amount / installments

        # 创建自动扣费计划
        result = self.create_auto_deduction_plan(
            tenant_id=tenant_id,
            user_id=user_id,
            name=f"账单分期-{invoice_id}",
            amount=installment_amount,
            frequency="monthly",
            target_type="invoice",
            target_id=invoice_id,
            total_amount=total_amount,
            max_deductions=installments,
            payment_method=payment_method
        )

        if result["success"]:
            result["installment_amount"] = installment_amount
            result["total_amount"] = total_amount
            result["installments"] = installments

        return result

    # ==================== 钱包转账 ====================

    def transfer_wallet(
        self,
        from_tenant_id: str,
        to_tenant_id: str,
        user_id: str,
        amount: float,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        钱包转账

        Args:
            from_tenant_id: 转出租户 ID
            to_tenant_id: 转入租户 ID
            user_id: 用户 ID
            amount: 转账金额
            description: 描述

        Returns:
            {
                "success": True,
                "transfer_id": "转账记录 ID",
                "amount": 转账金额
            }
        """
        try:
            # 获取转出钱包
            from_wallet = self.db.query(WalletDB).filter(
                WalletDB.tenant_id == from_tenant_id
            ).first()

            if not from_wallet:
                return {"success": False, "error": "转出钱包不存在"}

            if from_wallet.balance < amount:
                return {"success": False, "error": "余额不足"}

            # 获取转入钱包
            to_wallet = self.db.query(WalletDB).filter(
                WalletDB.tenant_id == to_tenant_id
            ).first()

            if not to_wallet:
                to_wallet = WalletDB(
                    id=str(uuid.uuid4()),
                    tenant_id=to_tenant_id,
                    balance=0.0,
                    currency="CNY"
                )
                self.db.add(to_wallet)

            # 执行转账
            from_wallet.balance -= amount
            to_wallet.balance += amount
            from_wallet.updated_at = datetime.utcnow()
            to_wallet.updated_at = datetime.utcnow()

            # 记录转账
            transfer_id = str(uuid.uuid4())
            transfer_record = PaymentTransactionDB(
                id=transfer_id,
                tenant_id=from_tenant_id,
                user_id=user_id,
                amount=amount,
                payment_method=PaymentMethodEnum.balance,
                status=PaymentStatusEnum.SUCCESS,
                payment_data={
                    "type": "transfer",
                    "description": description or "钱包转账",
                    "to_tenant_id": to_tenant_id
                }
            )
            self.db.add(transfer_record)

            # 记录接收
            receive_record = PaymentTransactionDB(
                id=str(uuid.uuid4()),
                tenant_id=to_tenant_id,
                user_id=user_id,
                amount=amount,
                payment_method=PaymentMethodEnum.balance,
                status=PaymentStatusEnum.SUCCESS,
                payment_data={
                    "type": "transfer_receive",
                    "description": description or "接收转账",
                    "from_tenant_id": from_tenant_id
                }
            )
            self.db.add(receive_record)

            self.db.commit()

            logger.info(f"钱包转账成功：from={from_tenant_id}, to={to_tenant_id}, amount={amount}")

            return {
                "success": True,
                "transfer_id": transfer_id,
                "amount": amount,
                "from_balance": from_wallet.balance,
                "to_balance": to_wallet.balance,
                "message": "转账成功"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"钱包转账失败：{e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "转账失败"
            }


# 全局服务实例
wallet_enhanced_service = WalletEnhancedService(None)  # 需要传入 db session
