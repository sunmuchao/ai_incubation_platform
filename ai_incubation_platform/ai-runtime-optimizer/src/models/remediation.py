"""
P6 自主修复引擎 - 数据模型
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"  # 可逆、影响小，无需审批
    MEDIUM = "medium"  # 可逆、影响中等，需 1 人审批
    HIGH = "high"  # 可逆、影响大，需 2 人审批
    CRITICAL = "critical"  # 不可逆、影响大，禁止自动执行


class RemediationCategory(str, Enum):
    """修复脚本分类"""
    CPU_OPTIMIZATION = "cpu_optimization"  # CPU 优化
    MEMORY_OPTIMIZATION = "memory_optimization"  # 内存优化
    DATABASE_OPTIMIZATION = "database_optimization"  # 数据库优化
    CACHE_OPTIMIZATION = "cache_optimization"  # 缓存优化
    CONFIG_ADJUSTMENT = "config_adjustment"  # 配置调整
    RESTART_SERVICE = "restart_service"  # 重启服务
    SCALE_RESOURCE = "scale_resource"  # 资源扩容
    MAINTENANCE = "maintenance"  # 维护操作


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"  # 等待中
    PENDING_APPROVAL = "pending_approval"  # 等待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    ROLLED_BACK = "rolled_back"  # 已回滚
    TIMEOUT = "timeout"  # 超时


class ScriptParameterType(str, Enum):
    """脚本参数类型"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"


class ScriptParameter(BaseModel):
    """脚本参数定义"""
    name: str = Field(..., description="参数名称")
    type: ScriptParameterType = Field(..., description="参数类型")
    default: Optional[Any] = Field(default=None, description="默认值")
    description: str = Field(default="", description="参数描述")
    required: bool = Field(default=False, description="是否必填")
    validation: Optional[Dict[str, Any]] = Field(default=None, description="验证规则")


class VerificationStep(BaseModel):
    """验证步骤"""
    name: str = Field(..., description="步骤名称")
    check: str = Field(..., description="检查命令/表达式")
    expected: Any = Field(..., description="期望结果")
    timeout: int = Field(default=30, description="超时时间 (秒)")
    retry_count: int = Field(default=3, description="重试次数")
    retry_interval: int = Field(default=5, description="重试间隔 (秒)")


class ResourceLimits(BaseModel):
    """资源限制"""
    max_cpu_percent: float = Field(default=50.0, description="最大 CPU 使用率 (%)")
    max_memory_mb: int = Field(default=512, description="最大内存使用 (MB)")
    max_disk_io_mb: int = Field(default=100, description="最大磁盘 IO (MB/s)")
    max_network_connections: int = Field(default=10, description="最大网络连接数")


class RemediationScript(BaseModel):
    """修复脚本模型"""
    script_id: str = Field(..., description="脚本 ID")
    name: str = Field(..., description="脚本名称")
    description: str = Field(..., description="脚本描述")
    category: RemediationCategory = Field(..., description="脚本分类")
    target_type: str = Field(..., description="目标类型 (service, database, cache 等)")

    # 脚本内容
    script_content: str = Field(..., description="脚本内容 (Shell/Python)")
    parameters: List[ScriptParameter] = Field(default_factory=list, description="参数列表")

    # 安全配置
    risk_level: RiskLevel = Field(..., description="风险等级")
    timeout_seconds: int = Field(default=120, description="超时时间 (秒)")
    resource_limits: Optional[ResourceLimits] = Field(default=None, description="资源限制")

    # 验证配置
    verification_steps: List[VerificationStep] = Field(default_factory=list, description="验证步骤")
    rollback_script: Optional[str] = Field(default=None, description="回滚脚本")

    # 元数据
    version: str = Field(default="1.0.0", description="版本号")
    author: str = Field(default="system", description="作者")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    tags: List[str] = Field(default_factory=list, description="标签")
    enabled: bool = Field(default=True, description="是否启用")


class ExecutionStep(BaseModel):
    """执行步骤记录"""
    name: str = Field(..., description="步骤名称")
    status: ExecutionStatus = Field(..., description="步骤状态")
    message: str = Field(default="", description="执行信息")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    output: Optional[str] = Field(default=None, description="执行输出")


class RemediationExecution(BaseModel):
    """修复执行记录"""
    execution_id: str = Field(..., description="执行 ID")
    script_id: str = Field(..., description="脚本 ID")
    script_name: str = Field(default="", description="脚本名称")
    target_service: str = Field(..., description="目标服务")
    target_type: str = Field(default="service", description="目标类型")

    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行参数")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="执行状态")

    # 执行过程
    execution_log: List[str] = Field(default_factory=list, description="执行日志")
    steps: List[ExecutionStep] = Field(default_factory=list, description="执行步骤")

    # 执行结果
    metrics_before: Optional[Dict[str, Any]] = Field(default=None, description="执行前指标")
    metrics_after: Optional[Dict[str, Any]] = Field(default=None, description="执行后指标")
    improvement: Optional[str] = Field(default=None, description="改善描述")

    # 回滚信息
    rollback_available: bool = Field(default=False, description="是否可回滚")
    rollback_executed: bool = Field(default=False, description="是否已执行回滚")
    rollback_log: List[str] = Field(default_factory=list, description="回滚日志")

    # 审批信息
    require_approval: bool = Field(default=False, description="是否需要审批")
    approved_by: Optional[str] = Field(default=None, description="审批人")
    approved_at: Optional[datetime] = Field(default=None, description="审批时间")
    rejected_by: Optional[str] = Field(default=None, description="拒绝人")
    rejected_reason: Optional[str] = Field(default=None, description="拒绝原因")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")

    # 估计信息
    estimated_duration_seconds: int = Field(default=60, description="估计耗时 (秒)")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="风险等级")


class AutoRemediationRule(BaseModel):
    """自动修复规则"""
    rule_id: str = Field(..., description="规则 ID")
    name: str = Field(..., description="规则名称")
    description: str = Field(default="", description="规则描述")

    # 触发条件
    trigger_condition: Dict[str, Any] = Field(..., description="触发条件")
    # 示例：{"metric": "cpu_percent", "operator": "greater_than", "threshold": 90, "duration_minutes": 10}

    # 执行配置
    script_id: str = Field(..., description="关联脚本 ID")
    script_parameters: Dict[str, Any] = Field(default_factory=dict, description="脚本参数")

    # 限流配置
    cooldown_minutes: int = Field(default=60, description="冷却时间 (分钟)")
    max_executions_per_day: int = Field(default=3, description="每日最大执行次数")
    require_approval: bool = Field(default=True, description="是否需要审批")

    # 启用状态
    enabled: bool = Field(default=False, description="是否启用")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_triggered_at: Optional[datetime] = Field(default=None, description="最后触发时间")
    execution_count_today: int = Field(default=0, description="今日执行次数")
    created_by: str = Field(default="system", description="创建人")


class ApprovalRequest(BaseModel):
    """审批请求"""
    execution_id: str = Field(..., description="执行 ID")
    approver: str = Field(..., description="审批人")
    action: str = Field(..., description="审批动作：approve/reject")
    reason: Optional[str] = Field(default=None, description="审批意见")


class RemediationStats(BaseModel):
    """修复统计"""
    total_executions: int = Field(default=0, description="总执行次数")
    successful_executions: int = Field(default=0, description="成功次数")
    failed_executions: int = Field(default=0, description="失败次数")
    rolled_back_executions: int = Field(default=0, description="回滚次数")
    success_rate: float = Field(default=0.0, description="成功率")
    avg_duration_seconds: float = Field(default=0.0, description="平均耗时 (秒)")
    total_executions_today: int = Field(default=0, description="今日执行次数")
    scripts_count: int = Field(default=0, description="脚本数量")
    auto_rules_count: int = Field(default=0, description="自动规则数量")


class ImpactAnalysis(BaseModel):
    """影响分析模型 - 用于评估修复操作的影响范围"""
    affected_services: List[str] = Field(default_factory=list, description="受影响的服务列表")
    affected_users: Optional[int] = Field(default=None, description="预估影响用户数")
    downtime_estimate_minutes: Optional[int] = Field(default=None, description="预估停机时间 (分钟)")
    performance_impact: Optional[str] = Field(default=None, description="性能影响描述")
    data_loss_risk: Optional[str] = Field(default=None, description="数据丢失风险评估")
    rollback_complexity: Optional[str] = Field(default=None, description="回滚复杂度评估")
    dependencies: List[str] = Field(default_factory=list, description="相关依赖列表")
    risk_assessment: Optional[str] = Field(default=None, description="综合风险评估")


class RemediationCase(BaseModel):
    """修复案例模型 - 用于记录和学习历史修复经验"""
    case_id: str = Field(..., description="案例 ID")
    execution_id: str = Field(..., description="关联执行 ID")
    script_id: str = Field(..., description="关联脚本 ID")
    problem_description: str = Field(..., description="问题描述")
    root_cause: Optional[str] = Field(default=None, description="根本原因")
    solution_applied: str = Field(..., description="应用的解决方案")
    outcome: str = Field(..., description="结果")
    lessons_learned: Optional[str] = Field(default=None, description="经验教训")
    similar_issues: List[str] = Field(default_factory=list, description="类似问题 ID 列表")
    tags: List[str] = Field(default_factory=list, description="标签")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    created_by: str = Field(default="system", description="创建人")
    effectiveness_score: Optional[float] = Field(default=None, description="有效性评分 (0-1)")


class RemediationExecutionEnhanced(RemediationExecution):
    """增强的修复执行记录 - 包含影响分析和案例信息"""
    impact_analysis: Optional[ImpactAnalysis] = Field(default=None, description="影响分析")
    case_id: Optional[str] = Field(default=None, description="关联案例 ID")
    pre_check_results: Optional[Dict[str, Any]] = Field(default=None, description="预检查结果")
    post_check_results: Optional[Dict[str, Any]] = Field(default=None, description="后检查结果")
    change_window: Optional[Dict[str, Any]] = Field(default=None, description="变更时间窗口")
    stakeholder_notifications: List[str] = Field(default_factory=list, description="相关方通知列表")
