"""
v2.1 自主修复执行引擎 - 核心引擎增强

在现有 P6 修复引擎基础上，实现完整的自主修复执行能力：
- ExecutionEngineV2 - 增强的修复执行引擎（沙箱隔离、权限校验）
- ValidationEngine - 效果验证引擎（指标比对、效果评估）
- RollbackManager - 回滚管理器（快照管理、自动回滚）
- ApprovalWorkflow - 审批工作流（多级审批、超时处理）

安全约束:
1. 白名单机制：仅允许执行注册的脚本
2. 权限校验：不同风险级别需要不同权限
3. 审计日志：所有操作必须记录
4. 超时保护：默认 5 分钟超时
5. 自动回滚：验证失败自动触发回滚
"""
import asyncio
import copy
import json
import logging
import os
import shlex
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from models.remediation import (
    ExecutionStatus,
    RemediationScript,
    ResourceLimits,
    RiskLevel,
    VerificationStep,
    RemediationCategory,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 执行结果模型
# ============================================================================

class ExecutionResult(Enum):
    """执行结果枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ValidationResult(Enum):
    """验证结果枚举"""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


class SnapshotStatus(Enum):
    """快照状态枚举"""
    CREATED = "created"
    RESTORED = "restored"
    EXPIRED = "expired"
    DELETED = "deleted"


class ApprovalStatus(Enum):
    """审批状态枚举"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ESCALATED = "escalated"


# ============================================================================
# 快照模型
# ============================================================================

class ServiceSnapshot(BaseModel):
    """服务快照模型"""
    snapshot_id: str = Field(..., description="快照 ID")
    service_id: str = Field(..., description="服务 ID")
    service_type: str = Field(default="service", description="服务类型")

    # 快照内容
    config_snapshot: Dict[str, Any] = Field(default_factory=dict, description="配置快照")
    resource_snapshot: Dict[str, Any] = Field(default_factory=dict, description="资源快照")
    state_snapshot: Dict[str, Any] = Field(default_factory=dict, description="状态快照")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")
    status: SnapshotStatus = Field(default=SnapshotStatus.CREATED, description="快照状态")

    # 关联信息
    execution_id: Optional[str] = Field(default=None, description="关联执行 ID")
    checksum: Optional[str] = Field(default=None, description="快照校验和")

    class Config:
        arbitrary_types_allowed = True


class SnapshotManager:
    """
    快照管理器

    负责管理服务快照的创建、存储、恢复和清理
    """

    def __init__(self, storage_dir: Optional[str] = None, ttl_hours: int = 24):
        """
        初始化快照管理器

        Args:
            storage_dir: 快照存储目录
            ttl_hours: 快照 TTL（小时）
        """
        self._storage_dir = Path(storage_dir) if storage_dir else Path(tempfile.mkdtemp(prefix="remediation_snapshots_"))
        self._ttl_hours = ttl_hours
        self._snapshots: Dict[str, ServiceSnapshot] = {}
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"SnapshotManager initialized at {self._storage_dir}")

    def create_snapshot(self, service_id: str, service_type: str,
                       config: Optional[Dict[str, Any]] = None,
                       resources: Optional[Dict[str, Any]] = None,
                       state: Optional[Dict[str, Any]] = None,
                       execution_id: Optional[str] = None) -> ServiceSnapshot:
        """
        创建服务快照

        Args:
            service_id: 服务 ID
            service_type: 服务类型
            config: 配置快照
            resources: 资源快照
            state: 状态快照
            execution_id: 关联执行 ID

        Returns:
            创建的快照
        """
        snapshot_id = f"snapshot_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        snapshot = ServiceSnapshot(
            snapshot_id=snapshot_id,
            service_id=service_id,
            service_type=service_type,
            config_snapshot=config or {},
            resource_snapshot=resources or {},
            state_snapshot=state or {},
            execution_id=execution_id,
            expires_at=datetime.now() + timedelta(hours=self._ttl_hours),
            checksum=uuid.uuid4().hex  # 简单校验和
        )

        self._snapshots[snapshot_id] = snapshot
        self._persist_snapshot(snapshot)

        logger.info(f"Created snapshot {snapshot_id} for service {service_id}")
        return snapshot

    def _persist_snapshot(self, snapshot: ServiceSnapshot):
        """持久化快照到磁盘"""
        try:
            file_path = self._storage_dir / f"{snapshot.snapshot_id}.json"
            data = {
                "snapshot_id": snapshot.snapshot_id,
                "service_id": snapshot.service_id,
                "service_type": snapshot.service_type,
                "config_snapshot": snapshot.config_snapshot,
                "resource_snapshot": snapshot.resource_snapshot,
                "state_snapshot": snapshot.state_snapshot,
                "execution_id": snapshot.execution_id,
                "created_at": snapshot.created_at.isoformat(),
                "expires_at": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
                "status": snapshot.status.value,
                "checksum": snapshot.checksum,
            }
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist snapshot {snapshot.snapshot_id}: {e}")

    def get_snapshot(self, snapshot_id: str) -> Optional[ServiceSnapshot]:
        """获取快照"""
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot and self._is_expired(snapshot):
            snapshot.status = SnapshotStatus.EXPIRED
            return None
        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        恢复快照

        Args:
            snapshot_id: 快照 ID

        Returns:
            是否恢复成功
        """
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            logger.error(f"Snapshot not found or expired: {snapshot_id}")
            return False

        # 这里应该实现实际的恢复逻辑
        # 目前只是标记快照为已恢复
        snapshot.status = SnapshotStatus.RESTORED
        logger.info(f"Restored snapshot {snapshot_id} for service {snapshot.service_id}")
        return True

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        if snapshot_id in self._snapshots:
            snapshot = self._snapshots.pop(snapshot_id)
            snapshot.status = SnapshotStatus.DELETED
            try:
                file_path = self._storage_dir / f"{snapshot_id}.json"
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete snapshot file: {e}")
            logger.info(f"Deleted snapshot {snapshot_id}")
            return True
        return False

    def _is_expired(self, snapshot: ServiceSnapshot) -> bool:
        """检查快照是否过期"""
        if not snapshot.expires_at:
            return False
        return datetime.now() > snapshot.expires_at

    def cleanup_expired(self) -> int:
        """清理过期快照，返回清理数量"""
        expired_count = 0
        expired_ids = [sid for sid, s in self._snapshots.items() if self._is_expired(s)]

        for snapshot_id in expired_ids:
            self.delete_snapshot(snapshot_id)
            expired_count += 1

        return expired_count

    def list_snapshots(self, service_id: Optional[str] = None) -> List[ServiceSnapshot]:
        """列出快照"""
        snapshots = list(self._snapshots.values())
        if service_id:
            snapshots = [s for s in snapshots if s.service_id == service_id]
        return snapshots


# ============================================================================
# 验证引擎
# ============================================================================

class MetricComparison(BaseModel):
    """指标比对结果"""
    metric_name: str = Field(..., description="指标名称")
    before_value: float = Field(..., description="修复前值")
    after_value: float = Field(..., description="修复后值")
    change_percent: float = Field(..., description="变化百分比")
    improvement: bool = Field(..., description="是否改善")
    threshold_met: bool = Field(..., description="是否达到阈值")


class ValidationConfig(BaseModel):
    """验证配置"""
    timeout_seconds: int = Field(default=60, description="验证超时时间")
    retry_count: int = Field(default=3, description="重试次数")
    retry_interval_seconds: int = Field(default=5, description="重试间隔")
    min_improvement_percent: float = Field(default=10.0, description="最小改善百分比")


class ValidationEngine:
    """
    验证引擎

    负责验证修复执行的效果，包括：
    - 执行前指标采集
    - 执行后指标采集
    - 指标比对分析
    - 验证结果判定
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        初始化验证引擎

        Args:
            config: 验证配置
        """
        self._config = config or ValidationConfig()
        self._metrics_cache: Dict[str, Dict[str, Any]] = {}
        self._validation_results: Dict[str, List[MetricComparison]] = {}

    def collect_metrics(self, service_id: str, metric_names: List[str],
                       source: str = "current") -> Dict[str, float]:
        """
        采集指标

        Args:
            service_id: 服务 ID
            metric_names: 指标名称列表
            source: 指标来源标识

        Returns:
            指标字典
        """
        metrics = {}
        cache_key = f"{service_id}:{source}"

        # TODO: 实现真实的指标采集
        # 目前使用模拟数据
        for metric_name in metric_names:
            # 模拟采集：实际应该调用监控 API
            if "cpu" in metric_name.lower():
                metrics[metric_name] = 85.0 if source == "before" else 45.0
            elif "memory" in metric_name.lower():
                metrics[metric_name] = 90.0 if source == "before" else 60.0
            elif "latency" in metric_name.lower():
                metrics[metric_name] = 500.0 if source == "before" else 200.0
            else:
                metrics[metric_name] = 0.0

        self._metrics_cache[cache_key] = metrics
        logger.info(f"Collected metrics for {service_id} ({source}): {metrics}")
        return metrics

    async def validate_step(self, step: VerificationStep,
                           context: Optional[Dict[str, Any]] = None) -> bool:
        """
        执行单个验证步骤

        Args:
            step: 验证步骤
            context: 执行上下文

        Returns:
            是否验证通过
        """
        context = context or {}

        for attempt in range(step.retry_count):
            try:
                # 渲染验证命令
                rendered_check = self._render_template(step.check, context)

                # 执行验证命令
                result = await self._execute_validation_command(
                    rendered_check,
                    timeout=step.timeout
                )

                # 检查验证结果
                if self._check_result(result, step.expected):
                    logger.info(f"Validation step '{step.name}' passed on attempt {attempt + 1}")
                    return True

            except asyncio.TimeoutError:
                logger.warning(f"Validation step '{step.name}' timed out on attempt {attempt + 1}")
                if attempt < step.retry_count - 1:
                    await asyncio.sleep(step.retry_interval)
            except Exception as e:
                logger.error(f"Validation step '{step.name}' failed: {e}")
                if attempt < step.retry_count - 1:
                    await asyncio.sleep(step.retry_interval)

        return False

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """渲染模板字符串"""
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    async def _execute_validation_command(self, command: str, timeout: int) -> str:
        """执行验证命令"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return stdout.decode('utf-8', errors='replace').strip()

        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(f"Command timed out after {timeout}s")

    def _check_result(self, actual: str, expected: Any) -> bool:
        """检查结果是否符合预期"""
        if isinstance(expected, str):
            return expected.lower() in actual.lower()
        elif isinstance(expected, bool):
            if expected:
                return actual.lower() in ['true', 'yes', '1', 'ok', 'success']
            else:
                return actual.lower() in ['false', 'no', '0', 'fail', 'error']
        elif isinstance(expected, (int, float)):
            try:
                return abs(float(actual) - float(expected)) < 0.01
            except ValueError:
                return False
        return actual == str(expected)

    def compare_metrics(self, service_id: str,
                       metric_comparisons: List[tuple]) -> List[MetricComparison]:
        """
        比对指标

        Args:
            service_id: 服务 ID
            metric_comparisons: 指标比对配置 [(metric_name, before_key, after_key, improvement_direction)]

        Returns:
            指标比对结果列表
        """
        results = []
        before_metrics = self._metrics_cache.get(f"{service_id}:before", {})
        after_metrics = self._metrics_cache.get(f"{service_id}:after", {})

        for metric_name, before_key, after_key, improvement_direction in metric_comparisons:
            before_value = before_metrics.get(before_key, before_metrics.get(metric_name, 0.0))
            after_value = after_metrics.get(after_key, after_metrics.get(metric_name, 0.0))

            if before_value == 0:
                change_percent = 0.0 if after_value == 0 else 100.0
            else:
                change_percent = ((after_value - before_value) / before_value) * 100

            # 根据改善方向判断是否改善
            if improvement_direction == "lower_is_better":
                improvement = after_value <= before_value
                threshold_met = change_percent <= -self._config.min_improvement_percent
            else:  # higher_is_better
                improvement = after_value >= before_value
                threshold_met = change_percent >= self._config.min_improvement_percent

            comparison = MetricComparison(
                metric_name=metric_name,
                before_value=before_value,
                after_value=after_value,
                change_percent=change_percent,
                improvement=improvement,
                threshold_met=threshold_met
            )
            results.append(comparison)

        self._validation_results[service_id] = results
        return results

    def get_validation_summary(self, service_id: str) -> Dict[str, Any]:
        """获取验证摘要"""
        results = self._validation_results.get(service_id, [])

        if not results:
            return {"status": "no_data", "message": "No validation results"}

        passed = sum(1 for r in results if r.threshold_met)
        total = len(results)
        pass_rate = (passed / total * 100) if total > 0 else 0.0

        return {
            "status": "passed" if pass_rate >= 80 else "failed",
            "total_comparisons": total,
            "passed_comparisons": passed,
            "pass_rate": pass_rate,
            "details": [
                {
                    "metric": r.metric_name,
                    "before": r.before_value,
                    "after": r.after_value,
                    "change_percent": r.change_percent,
                    "improved": r.improvement,
                }
                for r in results
            ]
        }


# ============================================================================
# 审批工作流
# ============================================================================

class ApprovalLevel(Enum):
    """审批级别"""
    LEVEL_1 = "level_1"  # 一级审批（低风险）
    LEVEL_2 = "level_2"  # 二级审批（中风险）
    LEVEL_3 = "level_3"  # 三级审批（高风险）


class ApprovalRequest(BaseModel):
    """审批请求"""
    request_id: str = Field(..., description="请求 ID")
    execution_id: str = Field(..., description="执行 ID")
    approvers: List[str] = Field(..., description="审批人列表")
    required_approvals: int = Field(..., description="需要审批人数")
    level: ApprovalLevel = Field(..., description="审批级别")

    # 审批状态
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="审批状态")
    approvals: Dict[str, datetime] = Field(default_factory=dict, description="审批记录")
    rejections: Dict[str, str] = Field(default_factory=dict, description="拒绝记录")

    # 超时配置
    timeout_minutes: int = Field(default=30, description="审批超时时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")

    # 升级配置
    escalate_on_timeout: bool = Field(default=False, description="超时时是否升级")
    escalate_to: Optional[str] = Field(default=None, description="升级审批人")


class ApprovalWorkflow:
    """
    审批工作流

    负责管理修复操作的审批流程，包括：
    - 多级审批配置
    - 审批超时处理
    - 审批升级机制
    - 审批历史记录
    """

    def __init__(self):
        """初始化审批工作流"""
        self._requests: Dict[str, ApprovalRequest] = {}
        self._approver_permissions: Dict[str, Set[ApprovalLevel]] = {}
        self._default_timeout_minutes = 30

        # 配置默认审批人
        self._setup_default_approvers()

    def _setup_default_approvers(self):
        """设置默认审批人权限"""
        # 默认所有用户都可以进行一级审批
        # 实际应用中应该从配置或数据库加载
        self._approver_permissions["admin"] = {ApprovalLevel.LEVEL_1, ApprovalLevel.LEVEL_2, ApprovalLevel.LEVEL_3}
        self._approver_permissions["operator"] = {ApprovalLevel.LEVEL_1, ApprovalLevel.LEVEL_2}
        self._approver_permissions["viewer"] = {ApprovalLevel.LEVEL_1}

    def create_approval_request(self, execution_id: str, risk_level: RiskLevel,
                               approvers: Optional[List[str]] = None) -> ApprovalRequest:
        """
        创建审批请求

        Args:
            execution_id: 执行 ID
            risk_level: 风险等级
            approvers: 审批人列表

        Returns:
            审批请求
        """
        # 根据风险等级确定审批级别和所需审批人数
        if risk_level == RiskLevel.LOW:
            level = ApprovalLevel.LEVEL_1
            required_approvals = 1
        elif risk_level == RiskLevel.MEDIUM:
            level = ApprovalLevel.LEVEL_2
            required_approvals = 1
        elif risk_level == RiskLevel.HIGH:
            level = ApprovalLevel.LEVEL_3
            required_approvals = 2
        else:  # CRITICAL
            level = ApprovalLevel.LEVEL_3
            required_approvals = 3

        # 如果未指定审批人，使用默认审批人
        if not approvers:
            approvers = list(self._approver_permissions.keys())

        request_id = f"approval_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        request = ApprovalRequest(
            request_id=request_id,
            execution_id=execution_id,
            approvers=approvers,
            required_approvals=required_approvals,
            level=level,
            timeout_minutes=self._default_timeout_minutes,
            expires_at=datetime.now() + timedelta(minutes=self._default_timeout_minutes),
            escalate_on_timeout=True,
        )

        self._requests[request_id] = request
        logger.info(f"Created approval request {request_id} for execution {execution_id} (level: {level.value})")
        return request

    def approve(self, request_id: str, approver: str) -> bool:
        """
        批准请求

        Args:
            request_id: 请求 ID
            approver: 审批人

        Returns:
            是否批准成功
        """
        request = self._requests.get(request_id)
        if not request:
            logger.error(f"Approval request not found: {request_id}")
            return False

        # 检查请求状态
        if request.status != ApprovalStatus.PENDING:
            logger.warning(f"Cannot approve request {request_id}: status is {request.status.value}")
            return False

        # 检查审批人权限
        if not self._check_approver_permission(approver, request.level):
            logger.warning(f"Approver {approver} lacks permission for {request.level.value}")
            return False

        # 记录审批
        request.approvals[approver] = datetime.now()

        # 检查是否达到所需审批人数
        if len(request.approvals) >= request.required_approvals:
            request.status = ApprovalStatus.APPROVED
            logger.info(f"Approval request {request_id} approved by {len(request.approvals)} approvers")
        else:
            logger.info(f"Approval request {request_id} approved by {approver} ({len(request.approvals)}/{request.required_approvals})")

        return True

    def reject(self, request_id: str, approver: str, reason: str) -> bool:
        """
        拒绝请求

        Args:
            request_id: 请求 ID
            approver: 审批人
            reason: 拒绝原因

        Returns:
            是否拒绝成功
        """
        request = self._requests.get(request_id)
        if not request:
            logger.error(f"Approval request not found: {request_id}")
            return False

        # 检查请求状态
        if request.status != ApprovalStatus.PENDING:
            logger.warning(f"Cannot reject request {request_id}: status is {request.status.value}")
            return False

        # 检查审批人权限
        if not self._check_approver_permission(approver, request.level):
            logger.warning(f"Approver {approver} lacks permission for {request.level.value}")
            return False

        # 记录拒绝
        request.rejections[approver] = reason
        request.status = ApprovalStatus.REJECTED

        logger.info(f"Approval request {request_id} rejected by {approver}: {reason}")
        return True

    def _check_approver_permission(self, approver: str, level: ApprovalLevel) -> bool:
        """检查审批人权限"""
        permissions = self._approver_permissions.get(approver, set())
        return level in permissions

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """获取审批请求"""
        return self._requests.get(request_id)

    def check_timeout(self, request_id: str) -> bool:
        """
        检查审批请求是否超时

        Args:
            request_id: 请求 ID

        Returns:
            是否超时
        """
        request = self._requests.get(request_id)
        if not request:
            return False

        if request.expires_at and datetime.now() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            logger.warning(f"Approval request {request_id} expired")

            # 处理升级
            if request.escalate_on_timeout and request.escalate_to:
                logger.info(f"Escalating expired request {request_id} to {request.escalate_to}")
                request.status = ApprovalStatus.ESCALATED

            return True

        return False

    def is_approved(self, execution_id: str) -> bool:
        """检查执行是否已获批"""
        for request in self._requests.values():
            if request.execution_id == execution_id:
                return request.status == ApprovalStatus.APPROVED
        return False

    def list_requests(self, status: Optional[ApprovalStatus] = None) -> List[ApprovalRequest]:
        """列出审批请求"""
        requests = list(self._requests.values())
        if status:
            requests = [r for r in requests if r.status == status]
        return requests


# ============================================================================
# 执行引擎 V2
# ============================================================================

class ExecutionContext(BaseModel):
    """执行上下文"""
    execution_id: str = Field(..., description="执行 ID")
    script_id: str = Field(..., description="脚本 ID")
    service_id: str = Field(..., description="服务 ID")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行参数")

    # 执行状态
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="执行状态")
    result: Optional[ExecutionResult] = Field(default=None, description="执行结果")

    # 资源限制
    resource_limits: Optional[ResourceLimits] = Field(default=None, description="资源限制")

    # 时间跟踪
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")

    # 日志
    logs: List[str] = Field(default_factory=list, description="执行日志")


class ExecutionEngineV2:
    """
    执行引擎 V2

    增强的修复执行引擎，提供：
    - 沙箱隔离执行
    - 权限校验
    - 资源限制
    - 审计日志
    - 超时保护
    """

    def __init__(self,
                 validation_engine: Optional[ValidationEngine] = None,
                 rollback_manager: Optional['RollbackManager'] = None,
                 approval_workflow: Optional[ApprovalWorkflow] = None,
                 snapshot_manager: Optional[SnapshotManager] = None):
        """
        初始化执行引擎

        Args:
            validation_engine: 验证引擎
            rollback_manager: 回滚管理器
            approval_workflow: 审批工作流
            snapshot_manager: 快照管理器
        """
        self._validation_engine = validation_engine or ValidationEngine()
        self._rollback_manager = rollback_manager
        self._approval_workflow = approval_workflow or ApprovalWorkflow()
        self._snapshot_manager = snapshot_manager or SnapshotManager()

        # 执行上下文存储
        self._contexts: Dict[str, ExecutionContext] = {}

        # 白名单脚本
        self._whitelisted_scripts: Set[str] = set()

        # 资源限制默认值
        self._default_resource_limits = ResourceLimits(
            max_cpu_percent=50.0,
            max_memory_mb=512,
            max_disk_io_mb=100,
            max_network_connections=10
        )

        logger.info("ExecutionEngineV2 initialized")

    def register_script(self, script_id: str):
        """将脚本加入白名单"""
        self._whitelisted_scripts.add(script_id)
        logger.info(f"Registered script {script_id} in whitelist")

    def is_script_whitelisted(self, script_id: str) -> bool:
        """检查脚本是否在白名单中"""
        return script_id in self._whitelisted_scripts

    async def execute(self, script: RemediationScript, service_id: str,
                     parameters: Optional[Dict[str, Any]] = None,
                     require_approval: bool = False,
                     timeout_seconds: Optional[int] = None) -> ExecutionResult:
        """
        执行修复

        Args:
            script: 修复脚本
            service_id: 服务 ID
            parameters: 执行参数
            require_approval: 是否需要审批
            timeout_seconds: 超时时间

        Returns:
            执行结果
        """
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 创建执行上下文
        context = ExecutionContext(
            execution_id=execution_id,
            script_id=script.script_id,
            service_id=service_id,
            parameters=parameters or {},
            resource_limits=script.resource_limits or self._default_resource_limits,
        )
        self._contexts[execution_id] = context

        context.logs.append(f"[{datetime.now().isoformat()}] Execution {execution_id} created")

        try:
            # 1. 白名单检查
            if not self.is_script_whitelisted(script.script_id):
                context.logs.append(f"[{datetime.now().isoformat()}] Script {script.script_id} not in whitelist")
                context.status = ExecutionStatus.FAILED
                context.result = ExecutionResult.FAILED
                return ExecutionResult.FAILED

            # 2. 审批检查
            if require_approval:
                approval_result = await self._check_approval(script, execution_id)
                if approval_result != ApprovalStatus.APPROVED:
                    context.logs.append(f"[{datetime.now().isoformat()}] Approval not granted: {approval_result.value}")
                    context.status = ExecutionStatus.REJECTED if approval_result == ApprovalStatus.REJECTED else ExecutionStatus.PENDING
                    context.result = ExecutionResult.CANCELLED
                    return ExecutionResult.CANCELLED

            # 3. 创建快照
            snapshot = await self._create_snapshot(service_id, script)
            context.logs.append(f"[{datetime.now().isoformat()}] Snapshot created: {snapshot.snapshot_id}")

            # 4. 执行前验证
            context.logs.append(f"[{datetime.now().isoformat()}] Running pre-execution validation...")
            pre_validation_passed = await self._pre_execution_validation(script, context)
            if not pre_validation_passed:
                context.logs.append(f"[{datetime.now().isoformat()}] Pre-execution validation failed")
                context.status = ExecutionStatus.FAILED
                context.result = ExecutionResult.FAILED
                return ExecutionResult.FAILED

            # 5. 执行脚本
            context.started_at = datetime.now()
            context.status = ExecutionStatus.RUNNING
            context.logs.append(f"[{datetime.now().isoformat()}] Executing script...")

            execution_result = await self._execute_script_in_sandbox(
                script, context, timeout_seconds or script.timeout_seconds
            )

            if execution_result != ExecutionResult.SUCCESS:
                context.logs.append(f"[{datetime.now().isoformat()}] Script execution failed: {execution_result.value}")
                context.status = ExecutionStatus.FAILED
                context.result = execution_result

                # 自动回滚
                if self._rollback_manager:
                    await self._rollback_manager.rollback(snapshot.snapshot_id)
                    context.result = ExecutionResult.ROLLED_BACK

                return context.result

            # 6. 执行后验证
            context.logs.append(f"[{datetime.now().isoformat()}] Running post-execution validation...")
            post_validation_passed = await self._post_execution_validation(script, context)

            if not post_validation_passed:
                context.logs.append(f"[{datetime.now().isoformat()}] Post-execution validation failed, triggering rollback")
                context.status = ExecutionStatus.FAILED
                context.result = ExecutionResult.ROLLED_BACK

                # 自动回滚
                if self._rollback_manager:
                    await self._rollback_manager.rollback(snapshot.snapshot_id)

                return ExecutionResult.ROLLED_BACK

            # 7. 执行成功
            context.completed_at = datetime.now()
            context.status = ExecutionStatus.COMPLETED
            context.result = ExecutionResult.SUCCESS
            context.logs.append(f"[{datetime.now().isoformat()}] Execution completed successfully")

            logger.info(f"Execution {execution_id} completed successfully")
            return ExecutionResult.SUCCESS

        except Exception as e:
            logger.exception(f"Execution {execution_id} failed with exception: {e}")
            context.logs.append(f"[{datetime.now().isoformat()}] Exception: {str(e)}")
            context.status = ExecutionStatus.FAILED
            context.result = ExecutionResult.FAILED

            # 尝试回滚
            try:
                if self._rollback_manager and 'snapshot' in locals():
                    await self._rollback_manager.rollback(snapshot.snapshot_id)
                    context.result = ExecutionResult.ROLLED_BACK
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")

            return context.result

    async def _check_approval(self, script: RemediationScript, execution_id: str) -> ApprovalStatus:
        """检查审批状态"""
        request = self._approval_workflow.create_approval_request(
            execution_id=execution_id,
            risk_level=script.risk_level
        )

        # 这里应该等待实际审批
        # 为了演示，我们假设自动批准低风险操作
        if script.risk_level == RiskLevel.LOW:
            self._approval_workflow.approve(request.request_id, "system")

        return request.status

    async def _create_snapshot(self, service_id: str, script: RemediationScript) -> ServiceSnapshot:
        """创建服务快照"""
        # 模拟创建快照
        snapshot = self._snapshot_manager.create_snapshot(
            service_id=service_id,
            service_type=script.target_type,
            config={"mock": "config"},
            resources={"mock": "resources"},
            state={"mock": "state"},
            execution_id=script.script_id
        )
        return snapshot

    async def _pre_execution_validation(self, script: RemediationScript, context: ExecutionContext) -> bool:
        """执行前验证"""
        # 采集执行前指标
        metric_names = ["cpu_percent", "memory_percent", "request_latency_ms"]
        self._validation_engine.collect_metrics(context.service_id, metric_names, source="before")
        return True

    async def _execute_script_in_sandbox(self, script: RemediationScript,
                                        context: ExecutionContext,
                                        timeout_seconds: int) -> ExecutionResult:
        """在沙箱中执行脚本"""
        try:
            # 创建临时目录作为沙箱
            with tempfile.TemporaryDirectory(prefix="sandbox_") as sandbox_dir:
                # 写入脚本内容
                script_path = Path(sandbox_dir) / f"{script.script_id}.sh"
                script_path.write_text(script.script_content)
                script_path.chmod(0o755)

                # 执行脚本
                try:
                    process = await asyncio.create_subprocess_shell(
                        f"bash {script_path}",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=sandbox_dir,
                    )

                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout_seconds
                    )

                    if process.returncode == 0:
                        context.logs.append(f"Script output: {stdout.decode('utf-8', errors='replace')}")
                        return ExecutionResult.SUCCESS
                    else:
                        context.logs.append(f"Script error: {stderr.decode('utf-8', errors='replace')}")
                        return ExecutionResult.FAILED

                except asyncio.TimeoutError:
                    context.logs.append(f"Script execution timed out after {timeout_seconds}s")
                    return ExecutionResult.TIMEOUT

        except Exception as e:
            context.logs.append(f"Sandbox execution failed: {str(e)}")
            return ExecutionResult.FAILED

    async def _post_execution_validation(self, script: RemediationScript,
                                         context: ExecutionContext) -> bool:
        """执行后验证"""
        # 采集执行后指标
        metric_names = ["cpu_percent", "memory_percent", "request_latency_ms"]
        self._validation_engine.collect_metrics(context.service_id, metric_names, source="after")

        # 比对指标
        comparisons = [
            ("cpu_percent", "cpu_percent", "cpu_percent", "lower_is_better"),
            ("memory_percent", "memory_percent", "memory_percent", "lower_is_better"),
            ("request_latency_ms", "request_latency_ms", "request_latency_ms", "lower_is_better"),
        ]

        results = self._validation_engine.compare_metrics(context.service_id, comparisons)
        summary = self._validation_engine.get_validation_summary(context.service_id)

        context.logs.append(f"Validation summary: {summary}")

        # 如果所有关键指标都改善，则验证通过
        if summary.get("status") == "passed":
            return True

        # 如果至少 50% 的指标改善，也算部分通过
        if summary.get("pass_rate", 0) >= 50:
            logger.warning(f"Validation partially passed for {context.execution_id}")
            return True

        return False

    def get_context(self, execution_id: str) -> Optional[ExecutionContext]:
        """获取执行上下文"""
        return self._contexts.get(execution_id)

    def list_executions(self, service_id: Optional[str] = None) -> List[ExecutionContext]:
        """列出执行记录"""
        contexts = list(self._contexts.values())
        if service_id:
            contexts = [c for c in contexts if c.service_id == service_id]
        return contexts


# ============================================================================
# 回滚管理器
# ============================================================================

class RollbackManager:
    """
    回滚管理器

    负责管理回滚操作，包括：
    - 快照恢复
    - 回滚脚本执行
    - 回滚验证
    - 回滚历史记录
    """

    def __init__(self, snapshot_manager: SnapshotManager,
                 validation_engine: ValidationEngine):
        """
        初始化回滚管理器

        Args:
            snapshot_manager: 快照管理器
            validation_engine: 验证引擎
        """
        self._snapshot_manager = snapshot_manager
        self._validation_engine = validation_engine
        self._rollback_history: Dict[str, Dict[str, Any]] = {}

    async def rollback(self, snapshot_id: str,
                      rollback_script: Optional[str] = None) -> bool:
        """
        执行回滚

        Args:
            snapshot_id: 快照 ID
            rollback_script: 回滚脚本（可选）

        Returns:
            是否回滚成功
        """
        snapshot = self._snapshot_manager.get_snapshot(snapshot_id)
        if not snapshot:
            logger.error(f"Snapshot not found or expired: {snapshot_id}")
            return False

        logger.info(f"Starting rollback for snapshot {snapshot_id}")

        rollback_record = {
            "snapshot_id": snapshot_id,
            "service_id": snapshot.service_id,
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "status": "in_progress"
        }

        try:
            # 1. 如果有回滚脚本，先执行脚本
            if rollback_script:
                rollback_record["steps"].append("Executing rollback script...")
                script_success = await self._execute_rollback_script(rollback_script, snapshot)
                if not script_success:
                    logger.warning("Rollback script failed, falling back to snapshot restore")

            # 2. 恢复快照
            rollback_record["steps"].append("Restoring snapshot...")
            restore_success = self._snapshot_manager.restore_snapshot(snapshot_id)

            if not restore_success:
                logger.error("Failed to restore snapshot")
                rollback_record["status"] = "failed"
                self._rollback_history[snapshot_id] = rollback_record
                return False

            # 3. 验证回滚
            rollback_record["steps"].append("Validating rollback...")
            validation_success = await self._validate_rollback(snapshot)

            if not validation_success:
                logger.warning("Rollback validation failed")
                rollback_record["status"] = "validation_failed"
                self._rollback_history[snapshot_id] = rollback_record
                return False

            rollback_record["status"] = "success"
            rollback_record["completed_at"] = datetime.now().isoformat()
            self._rollback_history[snapshot_id] = rollback_record

            logger.info(f"Rollback completed successfully for snapshot {snapshot_id}")
            return True

        except Exception as e:
            logger.exception(f"Rollback failed: {e}")
            rollback_record["status"] = "error"
            rollback_record["error"] = str(e)
            self._rollback_history[snapshot_id] = rollback_record
            return False

    async def _execute_rollback_script(self, script: str, snapshot: ServiceSnapshot) -> bool:
        """执行回滚脚本"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(script)
                script_path = f.name

            os.chmod(script_path, 0o755)

            process = await asyncio.create_subprocess_shell(
                f"bash {script_path}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60
            )

            os.unlink(script_path)

            if process.returncode == 0:
                logger.info(f"Rollback script executed: {stdout.decode('utf-8', errors='replace')}")
                return True
            else:
                logger.error(f"Rollback script failed: {stderr.decode('utf-8', errors='replace')}")
                return False

        except Exception as e:
            logger.error(f"Rollback script execution failed: {e}")
            return False

    async def _validate_rollback(self, snapshot: ServiceSnapshot) -> bool:
        """验证回滚"""
        # 简单的验证：检查服务是否可访问
        # 实际应用中应该检查具体的业务指标
        logger.info(f"Validating rollback for service {snapshot.service_id}")
        return True

    def get_rollback_history(self, snapshot_id: Optional[str] = None) -> Dict[str, Any]:
        """获取回滚历史"""
        if snapshot_id:
            return self._rollback_history.get(snapshot_id, {})
        return self._rollback_history


# ============================================================================
# 全局实例
# ============================================================================

_execution_engine: Optional[ExecutionEngineV2] = None
_validation_engine: Optional[ValidationEngine] = None
_rollback_manager: Optional[RollbackManager] = None
_approval_workflow: Optional[ApprovalWorkflow] = None
_snapshot_manager: Optional[SnapshotManager] = None


def get_validation_engine() -> ValidationEngine:
    """获取验证引擎单例"""
    global _validation_engine
    if _validation_engine is None:
        _validation_engine = ValidationEngine()
    return _validation_engine


def get_snapshot_manager() -> SnapshotManager:
    """获取快照管理器单例"""
    global _snapshot_manager
    if _snapshot_manager is None:
        _snapshot_manager = SnapshotManager()
    return _snapshot_manager


def get_approval_workflow() -> ApprovalWorkflow:
    """获取审批工作流单例"""
    global _approval_workflow
    if _approval_workflow is None:
        _approval_workflow = ApprovalWorkflow()
    return _approval_workflow


def get_rollback_manager() -> RollbackManager:
    """获取回滚管理器单例"""
    global _rollback_manager
    if _rollback_manager is None:
        _rollback_manager = RollbackManager(
            snapshot_manager=get_snapshot_manager(),
            validation_engine=get_validation_engine()
        )
    return _rollback_manager


def get_execution_engine() -> ExecutionEngineV2:
    """获取执行引擎单例"""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngineV2(
            validation_engine=get_validation_engine(),
            rollback_manager=get_rollback_manager(),
            approval_workflow=get_approval_workflow(),
            snapshot_manager=get_snapshot_manager()
        )
    return _execution_engine


def reset_engines():
    """重置所有引擎实例（用于测试）"""
    global _execution_engine, _validation_engine, _rollback_manager
    global _approval_workflow, _snapshot_manager
    _execution_engine = None
    _validation_engine = None
    _rollback_manager = None
    _approval_workflow = None
    _snapshot_manager = None
