"""
智能合约支付服务。
提供智能合约的创建、执行、支付触发等功能。
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from models.smart_contract import (
    ContractDisputeRequest,
    ContractDisputeResolution,
    ContractPaymentTrigger,
    ContractStatus,
    ContractType,
    CurrencyType,
    HourlyLog,
    Milestone,
    PaymentConditionType,
    SmartContract,
    SmartContractCreate,
    SmartContractSummary,
    SmartContractTemplate,
)
from models.escrow import EscrowStatus
from services.escrow_service import escrow_service
from services.payment_service import payment_service

logger = logging.getLogger(__name__)


class SimpleBlockchainProof:
    """简化的区块链存证（内存实现）。"""

    def __init__(self):
        self._proofs: Dict[str, Dict] = {}

    def create_proof(
        self,
        business_type: str,
        business_id: str,
        data_hash: str,
        data_summary: Dict,
        created_by: str = "system",
    ) -> Dict:
        """创建存证记录。"""
        proof_id = str(uuid.uuid4())
        proof = {
            "id": proof_id,
            "proof_id": proof_id,
            "business_type": business_type,
            "business_id": business_id,
            "data_hash": data_hash,
            "data_summary": data_summary,
            "created_by": created_by,
            "status": "confirmed",
            "transaction_hash": "0x" + hashlib.sha256(proof_id.encode()).hexdigest(),
            "block_number": 1000000 + hash(proof_id) % 100000,
            "created_at": datetime.now().isoformat(),
        }
        self._proofs[proof_id] = proof
        logger.info("Blockchain proof created: proof_id=%s, business_type=%s, business_id=%s",
                    proof_id, business_type, business_id)
        return proof


# 全局简单区块链存证实例
blockchain_proof_service = SimpleBlockchainProof()


class SmartContractService:
    """
    智能合约服务，提供以下功能：
    1. 合约模板管理
    2. 合约创建与执行
    3. 自动支付条件触发
    4. 里程碑管理
    5. 工时记录与审批
    6. 争议处理
    7. 区块链存证
    """

    def __init__(self) -> None:
        # 合约模板：template_id -> SmartContractTemplate
        self._templates: Dict[str, SmartContractTemplate] = {}
        # 合约实例：contract_id -> SmartContract
        self._contracts: Dict[str, SmartContract] = {}
        # 工时记录：log_id -> HourlyLog
        self._hourly_logs: Dict[str, HourlyLog] = {}
        # 用户合约索引
        self._employer_contracts: Dict[str, List[str]] = {}
        self._worker_contracts: Dict[str, List[str]] = {}

        # 初始化默认模板
        self._initialize_default_templates()

    def _initialize_default_templates(self) -> None:
        """初始化默认合约模板。"""
        # 固定价格模板
        fixed_price_template = SmartContractTemplate(
            name="固定价格合约",
            description="适用于一次性交付的任务，总金额固定",
            contract_type=ContractType.FIXED_PRICE,
            default_currency=CurrencyType.CNY,
            default_payment_condition=PaymentConditionType.AUTO_ON_DELIVERY,
            default_auto_release_hours=72,
            terms_and_conditions="1. 雇主发布任务时确定固定价格\n2. 工人交付后，雇主有 72 小时验收\n3. 验收通过或超时后自动支付",
        )
        self._templates["template_fixed_price"] = fixed_price_template

        # 小时计费模板
        hourly_template = SmartContractTemplate(
            name="小时计费合约",
            description="按实际工作时长计费，适用于持续性工作",
            contract_type=ContractType.HOURLY,
            default_currency=CurrencyType.CNY,
            default_payment_condition=PaymentConditionType.MANUAL,
            terms_and_conditions="1. 工人按小时记录工作时间\n2. 需要提供工作证明（截图/描述）\n3. 雇主审批工时后支付",
        )
        self._templates["template_hourly"] = hourly_template

        # 里程碑模板
        milestone_template = SmartContractTemplate(
            name="里程碑合约",
            description="分阶段交付，每个里程碑独立验收和支付",
            contract_type=ContractType.MILESTONE,
            default_currency=CurrencyType.CNY,
            default_payment_condition=PaymentConditionType.AUTO_ON_MILESTONE,
            terms_and_conditions="1. 合约分为多个里程碑\n2. 每个里程碑独立验收\n3. 里程碑验收通过后自动支付对应金额",
        )
        self._templates["template_milestone"] = milestone_template

        logger.info("Initialized %d default contract templates", len(self._templates))

    # ========== 模板管理 ==========

    def get_template(self, template_id: str) -> Optional[SmartContractTemplate]:
        """获取合约模板。"""
        return self._templates.get(template_id)

    def list_templates(self) -> List[SmartContractTemplate]:
        """列出所有启用的模板。"""
        return [t for t in self._templates.values() if t.is_active]

    # ========== 合约创建 ==========

    def create_contract(self, request: SmartContractCreate) -> SmartContract:
        """
        创建智能合约。

        流程：
        1. 验证输入参数
        2. 生成合约编号
        3. 计算合约金额
        4. 创建 Escrow 托管（如需要）
        5. 区块链存证
        """
        # 验证参数
        if request.contract_type == ContractType.FIXED_PRICE:
            if not request.total_amount or request.total_amount <= 0:
                raise ValueError("Fixed price contract requires positive total_amount")

        elif request.contract_type == ContractType.HOURLY:
            if not request.hourly_rate or request.hourly_rate <= 0:
                raise ValueError("Hourly contract requires positive hourly_rate")
            if not request.max_hours or request.max_hours <= 0:
                raise ValueError("Hourly contract requires positive max_hours")

        elif request.contract_type == ContractType.MILESTONE:
            if not request.milestones or len(request.milestones) == 0:
                raise ValueError("Milestone contract requires at least one milestone")

        # 生成合约编号
        contract_number = self._generate_contract_number()

        # 创建合约实例
        contract = SmartContract(
            contract_number=contract_number,
            contract_type=request.contract_type,
            ai_employer_id=request.ai_employer_id,
            worker_id=request.worker_id,
            task_id=request.task_id,
            currency=request.currency,
            platform_fee_rate=0.1,
            payment_condition=request.payment_condition,
            auto_release_hours=request.auto_release_hours,
            hourly_rate=request.hourly_rate,
            max_hours=request.max_hours,
            deliverables=request.deliverables,
            deadline=request.deadline,
            terms_and_conditions=request.terms_and_conditions or "",
        )

        # 计算金额
        if request.contract_type == ContractType.FIXED_PRICE:
            contract.total_amount = request.total_amount
            contract.remaining_amount = request.total_amount

        elif request.contract_type == ContractType.HOURLY:
            contract.total_amount = request.hourly_rate * request.max_hours
            contract.remaining_amount = contract.total_amount

        elif request.contract_type == ContractType.MILESTONE:
            # 创建里程碑
            for m in request.milestones:
                milestone = Milestone(
                    title=m.get("title", ""),
                    description=m.get("description", ""),
                    amount=m.get("amount", 0),
                    currency=request.currency,
                    acceptance_criteria=m.get("acceptance_criteria", ""),
                )
                contract.milestones.append(milestone)

            contract.total_amount = sum(m.amount for m in contract.milestones)
            contract.remaining_amount = contract.total_amount

        # 计算平台服务费
        contract.platform_fee = contract.total_amount * contract.platform_fee_rate

        # 设置状态为生效中
        contract.status = ContractStatus.ACTIVE
        contract.start_date = datetime.now()

        # 存储合约
        self._contracts[contract.id] = contract

        # 建立索引
        self._employer_contracts.setdefault(request.ai_employer_id, []).append(contract.id)
        self._worker_contracts.setdefault(request.worker_id, []).append(contract.id)

        # 创建 Escrow 托管（固定价格和里程碑合约需要）
        if request.contract_type in [ContractType.FIXED_PRICE, ContractType.MILESTONE]:
            self._create_escrow_for_contract(contract)

        # 区块链存证
        self._create_blockchain_proof(contract, "contract_created")

        logger.info(
            "Smart contract created: contract_id=%s, contract_number=%s, type=%s, employer=%s, worker=%s, amount=%.2f",
            contract.id, contract_number, request.contract_type.value,
            request.ai_employer_id, request.worker_id, contract.total_amount
        )

        return contract

    def _generate_contract_number(self) -> str:
        """生成合约编号。"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"SC-{timestamp}-{unique_id.upper()}"

    def _create_escrow_for_contract(self, contract: SmartContract) -> None:
        """为合约创建 Escrow 托管。"""
        from models.escrow import EscrowCreate

        escrow_request = EscrowCreate(
            task_id=contract.task_id or contract.id,
            ai_employer_id=contract.ai_employer_id,
            principal_amount=contract.total_amount,
            platform_fee_rate=contract.platform_fee_rate,
        )

        try:
            escrow_service.create_escrow(escrow_request)
            logger.info("Escrow created for contract: contract_id=%s", contract.id)
        except Exception as e:
            logger.warning("Failed to create escrow for contract %s: %s", contract.id, str(e))

    def _create_blockchain_proof(self, contract: SmartContract, event_type: str) -> None:
        """创建合约区块链存证。"""
        try:
            # 生成合约数据哈希
            contract_data = {
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "contract_type": contract.contract_type.value,
                "ai_employer_id": contract.ai_employer_id,
                "worker_id": contract.worker_id,
                "total_amount": contract.total_amount,
                "currency": contract.currency.value,
                "created_at": contract.created_at.isoformat(),
            }
            contract_hash = hashlib.sha256(json.dumps(contract_data, sort_keys=True).encode()).hexdigest()
            contract.contract_hash = contract_hash

            # 调用区块链存证服务
            blockchain_proof_service.create_proof(
                business_type=event_type,
                business_id=contract.id,
                data_hash=contract_hash,
                data_summary=contract_data,
                created_by=contract.created_by,
            )

            logger.info("Blockchain proof created for contract: contract_id=%s, hash=%s", contract.id, contract_hash)
        except Exception as e:
            logger.warning("Failed to create blockchain proof for contract %s: %s", contract.id, str(e))

    # ========== 合约查询 ==========

    def get_contract(self, contract_id: str) -> Optional[SmartContract]:
        """获取合约详情。"""
        return self._contracts.get(contract_id)

    def get_contract_by_number(self, contract_number: str) -> Optional[SmartContract]:
        """通过合约编号获取合约。"""
        for contract in self._contracts.values():
            if contract.contract_number == contract_number:
                return contract
        return None

    def get_employer_contracts(self, employer_id: str) -> List[SmartContract]:
        """获取雇主的所有合约。"""
        contract_ids = self._employer_contracts.get(employer_id, [])
        return [self._contracts[cid] for cid in contract_ids if cid in self._contracts]

    def get_worker_contracts(self, worker_id: str) -> List[SmartContract]:
        """获取工人的所有合约。"""
        contract_ids = self._worker_contracts.get(worker_id, [])
        return [self._contracts[cid] for cid in contract_ids if cid in self._contracts]

    def list_contracts_by_status(self, status: ContractStatus) -> List[SmartContract]:
        """按状态列出合约。"""
        return [c for c in self._contracts.values() if c.status == status]

    # ========== 合约执行 ==========

    def start_contract_execution(self, contract_id: str, worker_id: str) -> SmartContract:
        """
        开始合约执行。

        工人接受合约后调用。
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")

        if contract.worker_id != worker_id:
            raise ValueError("Not authorized for this contract")

        if contract.status != ContractStatus.ACTIVE:
            raise ValueError(f"Contract cannot start in status: {contract.status.value}")

        contract.status = ContractStatus.EXECUTING
        contract.updated_at = datetime.now()

        logger.info("Contract execution started: contract_id=%s", contract_id)
        return contract

    def submit_deliverables(
        self,
        contract_id: str,
        worker_id: str,
        deliverables: List[str],
        delivery_files: List[str],
    ) -> SmartContract:
        """
        提交交付物。

        工人完成工作后提交交付物。
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")

        if contract.worker_id != worker_id:
            raise ValueError("Not authorized for this contract")

        if contract.status != ContractStatus.EXECUTING:
            raise ValueError(f"Cannot submit deliverables in status: {contract.status.value}")

        # 更新交付物
        contract.deliverables = deliverables
        contract.delivery_files = delivery_files
        contract.updated_at = datetime.now()

        # 根据支付条件触发自动支付
        if contract.payment_condition == PaymentConditionType.AUTO_ON_DELIVERY:
            logger.info("Auto payment triggered on delivery for contract: %s", contract_id)
            # 触发自动支付流程（异步）
            self._trigger_auto_payment(contract, "auto_on_delivery")

        # 区块链存证
        self._create_blockchain_proof(contract, "deliverables_submitted")

        logger.info("Deliverables submitted for contract: contract_id=%s", contract_id)
        return contract

    # ========== 工时管理（小时计费合约）==========

    def log_work_hours(
        self,
        contract_id: str,
        worker_id: str,
        start_time: datetime,
        end_time: datetime,
        description: str = "",
        work_screenshot: Optional[str] = None,
    ) -> HourlyLog:
        """
        记录工时。

        小时计费合约的工人使用。
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")

        if contract.contract_type != ContractType.HOURLY:
            raise ValueError("Not an hourly contract")

        if contract.worker_id != worker_id:
            raise ValueError("Not authorized for this contract")

        # 计算工作时长
        hours_worked = (end_time - start_time).total_seconds() / 3600
        total_amount = hours_worked * contract.hourly_rate

        # 检查是否超过最大工时
        total_logged = self._get_total_logged_hours(contract_id)
        if total_logged + hours_worked > contract.max_hours:
            raise ValueError(
                f"Total hours ({total_logged + hours_worked}) would exceed max hours ({contract.max_hours})"
            )

        # 创建工时记录
        log = HourlyLog(
            contract_id=contract_id,
            worker_id=worker_id,
            start_time=start_time,
            end_time=end_time,
            hours_worked=hours_worked,
            description=description,
            work_screenshot=work_screenshot,
            hourly_rate=contract.hourly_rate,
            total_amount=total_amount,
        )

        self._hourly_logs[log.id] = log

        logger.info(
            "Work hours logged: log_id=%s, contract_id=%s, hours=%.2f, amount=%.2f",
            log.id, contract_id, hours_worked, total_amount
        )

        return log

    def _get_total_logged_hours(self, contract_id: str) -> float:
        """获取合约已记录的总工时。"""
        total = sum(
            log.hours_worked for log in self._hourly_logs.values()
            if log.contract_id == contract_id and log.status == "approved"
        )
        return total

    def approve_hourly_log(
        self,
        log_id: str,
        approver_id: str,
    ) -> HourlyLog:
        """
        审批工时记录。

        雇主审批工人的工时记录。
        """
        log = self._hourly_logs.get(log_id)
        if not log:
            raise ValueError(f"Hourly log not found: {log_id}")

        contract = self._contracts.get(log.contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {log.contract_id}")

        if contract.ai_employer_id != approver_id:
            raise ValueError("Not authorized to approve this log")

        if log.status != "pending":
            raise ValueError(f"Log already processed: {log.status}")

        # 更新工时记录状态
        log.status = "approved"
        log.approved_by = approver_id
        log.approved_at = datetime.now()

        # 更新合约已支付金额
        contract.paid_amount += log.total_amount
        contract.remaining_amount -= log.total_amount

        # 触发支付
        self._process_hourly_payment(log)

        logger.info("Hourly log approved: log_id=%s, amount=%.2f", log_id, log.total_amount)
        return log

    def reject_hourly_log(
        self,
        log_id: str,
        approver_id: str,
        reason: str,
    ) -> HourlyLog:
        """
        拒绝工时记录。

        雇主拒绝工人的工时记录。
        """
        log = self._hourly_logs.get(log_id)
        if not log:
            raise ValueError(f"Hourly log not found: {log_id}")

        contract = self._contracts.get(log.contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {log.contract_id}")

        if contract.ai_employer_id != approver_id:
            raise ValueError("Not authorized to reject this log")

        log.status = "rejected"
        log.rejection_reason = reason

        logger.info("Hourly log rejected: log_id=%s, reason=%s", log_id, reason)
        return log

    def _process_hourly_payment(self, log: HourlyLog) -> None:
        """处理工时支付。"""
        # 调用支付服务进行支付
        try:
            from models.payment import TaskPaymentRequest
            # 简化的支付处理
            logger.info("Processing hourly payment: log_id=%s, amount=%.2f", log.id, log.total_amount)
        except Exception as e:
            logger.error("Failed to process hourly payment: %s", str(e))

    # ========== 里程碑管理 ==========

    def complete_milestone(
        self,
        contract_id: str,
        milestone_id: str,
        worker_id: str,
    ) -> Milestone:
        """
        完成里程碑。

        工人完成里程碑后调用。
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")

        if contract.worker_id != worker_id:
            raise ValueError("Not authorized for this contract")

        # 找到里程碑
        milestone = None
        for m in contract.milestones:
            if m.id == milestone_id:
                milestone = m
                break

        if not milestone:
            raise ValueError(f"Milestone not found: {milestone_id}")

        if milestone.status != "pending":
            raise ValueError(f"Milestone already processed: {milestone.status}")

        # 更新里程碑状态
        milestone.status = "completed"
        milestone.completed_at = datetime.now()

        # 如果是自动支付，触发支付
        if contract.payment_condition == PaymentConditionType.AUTO_ON_MILESTONE:
            self._process_milestone_payment(contract, milestone)

        logger.info("Milestone completed: contract_id=%s, milestone_id=%s", contract_id, milestone_id)
        return milestone

    def verify_milestone(
        self,
        contract_id: str,
        milestone_id: str,
        verifier_id: str,
    ) -> Milestone:
        """
        验收里程碑。

        雇主验收里程碑。
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")

        if contract.ai_employer_id != verifier_id:
            raise ValueError("Not authorized to verify this milestone")

        milestone = None
        for m in contract.milestones:
            if m.id == milestone_id:
                milestone = m
                break

        if not milestone:
            raise ValueError(f"Milestone not found: {milestone_id}")

        milestone.status = "verified"
        milestone.verified_at = datetime.now()

        logger.info("Milestone verified: contract_id=%s, milestone_id=%s", contract_id, milestone_id)
        return milestone

    def _process_milestone_payment(
        self,
        contract: SmartContract,
        milestone: Milestone,
    ) -> None:
        """处理里程碑支付。"""
        # 更新合约支付金额
        contract.paid_amount += milestone.amount
        contract.remaining_amount -= milestone.amount
        milestone.paid_at = datetime.now()

        # 检查是否所有里程碑都已完成
        all_completed = all(m.status in ["verified", "paid"] for m in contract.milestones)
        if all_completed:
            contract.status = ContractStatus.COMPLETED

        logger.info(
            "Milestone payment processed: contract_id=%s, milestone_id=%s, amount=%.2f",
            contract.id, milestone.id, milestone.amount
        )

    # ========== 支付触发 ==========

    def trigger_payment(self, request: ContractPaymentTrigger) -> SmartContract:
        """
        触发合约支付。

        根据支付条件自动或手动触发支付。
        """
        contract = self._contracts.get(request.contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {request.contract_id}")

        if contract.status not in [ContractStatus.EXECUTING, ContractStatus.COMPLETED]:
            raise ValueError(f"Cannot trigger payment in status: {contract.status.value}")

        # 根据触发类型处理
        if request.trigger_type == "manual":
            # 手动触发支付
            self._process_manual_payment(contract, request.operator_id)

        elif request.trigger_type == "auto_on_time":
            # 超时自动支付
            if contract.auto_release_hours:
                deadline = contract.start_date + timedelta(hours=contract.auto_release_hours)
                if datetime.now() >= deadline:
                    self._process_auto_payment(contract, request.operator_id)

        elif request.trigger_type == "milestone_completed":
            # 里程碑完成支付
            if request.milestone_id:
                milestone = None
                for m in contract.milestones:
                    if m.id == request.milestone_id:
                        milestone = m
                        break
                if milestone and milestone.status == "verified":
                    self._process_milestone_payment(contract, milestone)

        return contract

    def _process_manual_payment(self, contract: SmartContract, operator_id: str) -> None:
        """处理手动支付。"""
        # 释放 Escrow 资金
        try:
            escrow_service.release_escrow(
                task_id=contract.task_id or contract.id,
                worker_id=contract.worker_id,
                operator_id=operator_id,
            )

            contract.paid_amount = contract.total_amount
            contract.remaining_amount = 0
            contract.status = ContractStatus.COMPLETED

            logger.info("Manual payment processed: contract_id=%s", contract.id)
        except Exception as e:
            logger.error("Failed to process manual payment: %s", str(e))
            raise

    def _process_auto_payment(self, contract: SmartContract, operator_id: str) -> None:
        """处理自动支付。"""
        self._process_manual_payment(contract, operator_id)

    def _trigger_auto_payment(self, contract: SmartContract, trigger_reason: str) -> None:
        """触发自动支付（异步）。"""
        # 实际实现中应该是异步任务
        logger.info("Auto payment triggered: contract_id=%s, reason=%s", contract.id, trigger_reason)

    # ========== 争议处理 ==========

    def dispute_contract(self, request: ContractDisputeRequest) -> SmartContract:
        """
        对合约提出争议。

        雇主或工人都可以提出争议。
        """
        contract = self._contracts.get(request.contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {request.contract_id}")

        # 更新合约状态
        contract.status = ContractStatus.DISPUTED
        contract.dispute_reason = request.reason
        contract.updated_at = datetime.now()

        # 区块链存证
        self._create_blockchain_proof(contract, "contract_disputed")

        logger.info(
            "Contract disputed: contract_id=%s, requester=%s, reason=%s",
            request.contract_id, request.requester_id, request.reason
        )

        return contract

    def resolve_dispute(self, request: ContractDisputeResolution) -> SmartContract:
        """
        解决合约争议。

        管理员或仲裁人解决争议。
        """
        contract = self._contracts.get(request.contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {request.contract_id}")

        if contract.status != ContractStatus.DISPUTED:
            raise ValueError(f"Contract not in disputed status: {contract.status.value}")

        resolution = request.resolution

        if resolution == "employer_full":
            # 全额退款给雇主
            self._refund_to_employer(contract, request.resolver_id)

        elif resolution == "worker_full":
            # 全额支付给工人
            self._pay_to_worker(contract, request.resolver_id)

        elif resolution == "split":
            # 按比例分配
            self._split_payment(contract, request.split_ratio, request.resolver_id)

        elif resolution == "custom":
            # 自定义分配
            if request.custom_distribution:
                self._custom_distribution(contract, request.custom_distribution, request.resolver_id)

        # 更新合约状态
        contract.dispute_resolution = resolution
        contract.status = ContractStatus.TERMINATED
        contract.updated_at = datetime.now()

        # 区块链存证
        self._create_blockchain_proof(contract, "dispute_resolved")

        logger.info(
            "Contract dispute resolved: contract_id=%s, resolution=%s",
            request.contract_id, resolution
        )

        return contract

    def _refund_to_employer(self, contract: SmartContract, resolver_id: str) -> None:
        """全额退款给雇主。"""
        try:
            escrow_service.refund_escrow(
                task_id=contract.task_id or contract.id,
                operator_id=resolver_id,
                reason="Dispute resolved: employer_full",
            )
            logger.info("Contract refunded to employer: contract_id=%s", contract.id)
        except Exception as e:
            logger.error("Failed to refund to employer: %s", str(e))

    def _pay_to_worker(self, contract: SmartContract, resolver_id: str) -> None:
        """全额支付给工人。"""
        try:
            escrow_service.release_escrow(
                task_id=contract.task_id or contract.id,
                worker_id=contract.worker_id,
                operator_id=resolver_id,
            )
            contract.paid_amount = contract.total_amount
            logger.info("Contract paid to worker: contract_id=%s", contract.id)
        except Exception as e:
            logger.error("Failed to pay to worker: %s", str(e))

    def _split_payment(
        self,
        contract: SmartContract,
        split_ratio: float,
        resolver_id: str,
    ) -> None:
        """按比例分配支付。"""
        try:
            # 简化处理：记录日志，实际实现需要调用 Escrow 服务的争议解决接口
            worker_amount = contract.principal_amount * split_ratio if hasattr(contract, 'principal_amount') else contract.total_amount * split_ratio
            logger.info("Contract payment split: contract_id=%s, ratio=%s, worker_amount=%.2f", contract.id, split_ratio, worker_amount)
        except Exception as e:
            logger.error("Failed to split payment: %s", str(e))

    def _custom_distribution(
        self,
        contract: SmartContract,
        distribution: Dict[str, float],
        resolver_id: str,
    ) -> None:
        """自定义分配支付。"""
        # 实现自定义分配逻辑
        logger.info("Custom distribution: contract_id=%s, distribution=%s", contract.id, distribution)

    # ========== 合约终止 ==========

    def terminate_contract(self, contract_id: str, operator_id: str, reason: str) -> SmartContract:
        """
        终止合约。

        管理员或双方协商终止合约。
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")

        if contract.status in [ContractStatus.COMPLETED, ContractStatus.TERMINATED]:
            raise ValueError(f"Cannot terminate contract in status: {contract.status.value}")

        # 退款给雇主
        self._refund_to_employer(contract, operator_id)

        contract.status = ContractStatus.TERMINATED
        contract.dispute_reason = reason
        contract.updated_at = datetime.now()

        logger.info("Contract terminated: contract_id=%s, reason=%s", contract_id, reason)
        return contract

    def pause_contract(self, contract_id: str, operator_id: str, reason: str) -> SmartContract:
        """暂停合约。"""
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")

        contract.status = ContractStatus.PAUSED
        contract.updated_at = datetime.now()

        logger.info("Contract paused: contract_id=%s, reason=%s", contract_id, reason)
        return contract

    def resume_contract(self, contract_id: str, operator_id: str) -> SmartContract:
        """恢复合约。"""
        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")

        if contract.status != ContractStatus.PAUSED:
            raise ValueError(f"Cannot resume contract in status: {contract.status.value}")

        contract.status = ContractStatus.EXECUTING
        contract.updated_at = datetime.now()

        logger.info("Contract resumed: contract_id=%s", contract_id)
        return contract

    # ========== 统计汇总 ==========

    def get_summary(self) -> SmartContractSummary:
        """获取合约汇总统计。"""
        contracts = list(self._contracts.values())

        by_type = {}
        by_currency = {}
        by_status = {}

        for c in contracts:
            # 按类型
            type_key = c.contract_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            # 按币种
            currency_key = c.currency.value
            by_currency[currency_key] = by_currency.get(currency_key, 0) + 1

            # 按状态
            status_key = c.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1

        return SmartContractSummary(
            total_contracts=len(contracts),
            active_contracts=len([c for c in contracts if c.status == ContractStatus.ACTIVE]),
            completed_contracts=len([c for c in contracts if c.status == ContractStatus.COMPLETED]),
            disputed_contracts=len([c for c in contracts if c.status == ContractStatus.DISPUTED]),
            total_value=sum(c.total_amount for c in contracts),
            total_paid=sum(c.paid_amount for c in contracts),
            by_type=by_type,
            by_currency=by_currency,
            by_status=by_status,
        )


# 导入 uuid
import uuid

# 创建全局服务实例
smart_contract_service = SmartContractService()
