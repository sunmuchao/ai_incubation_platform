"""
跨 Agent 协同 - Schema 定义
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Agent 类型"""
    TRAFFIC = "traffic_booster"        # 流量分析 Agent
    RUNTIME = "runtime_optimizer"      # 运行态优化 Agent
    CODE = "code_understanding"        # 代码理解 Agent
    DATA = "data_connector"            # 数据连接 Agent


class WorkflowStatus(str, Enum):
    """工作流状态"""
    PENDING = "pending"      # 待处理
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    TIMEOUT = "timeout"      # 超时


class WorkflowStepStatus(str, Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentCapability(BaseModel):
    """Agent 能力描述"""
    agent_type: AgentType
    endpoint: str
    capabilities: List[str]
    health_status: str = "unknown"
    last_checked: Optional[datetime] = None


class WorkflowStep(BaseModel):
    """工作流步骤"""
    step_id: str
    step_name: str
    agent_type: AgentType
    endpoint: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class WorkflowExecution(BaseModel):
    """工作流执行实例"""
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    trigger_type: str  # "auto" (自动触发) 或 "manual" (手动触发)
    trigger_event: Dict[str, Any]  # 触发事件的详细信息
    steps: List[WorkflowStep]
    final_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: Optional[int] = None


# ============= 请求/响应模型 =============

class AgentHealthCheckResponse(BaseModel):
    """Agent 健康检查响应"""
    agents: List[AgentCapability]
    overall_status: str
    checked_at: datetime


class WorkflowTriggerRequest(BaseModel):
    """工作流触发请求"""
    workflow_name: str = Field(..., description="工作流名称")
    trigger_type: str = Field("manual", description="触发类型：auto/manual")
    trigger_event: Dict[str, Any] = Field(..., description="触发事件数据")
    priority: str = Field("normal", description="优先级：high/normal/low")


class WorkflowListResponse(BaseModel):
    """工作流列表响应"""
    workflows: List[WorkflowExecution]
    total: int
    filters: Dict[str, Any]


class WorkflowDetailResponse(BaseModel):
    """工作流详情响应"""
    workflow: WorkflowExecution


# ============= 跨 Agent 诊断工作流专用模型 =============

class TrafficAnomalyEvent(BaseModel):
    """流量异常事件"""
    anomaly_id: str
    metric_name: str
    current_value: float
    expected_value: float
    deviation: float
    z_score: float
    severity: str
    description: str
    detected_at: datetime


class RuntimeDiagnosisRequest(BaseModel):
    """运行态诊断请求"""
    anomaly_event: TrafficAnomalyEvent
    context: Optional[Dict[str, Any]] = None


class RuntimeDiagnosisResult(BaseModel):
    """运行态诊断结果"""
    diagnosis_id: str
    anomaly_correlation: float  # 异常相关性 0-1
    runtime_metrics: Dict[str, Any]  # 运行态指标
    suspicious_services: List[Dict[str, Any]]  # 可疑服务列表
    performance_bottlenecks: List[Dict[str, Any]]  # 性能瓶颈
    recommended_actions: List[str]  # 建议操作
    confidence: float  # 置信度


class CodeAnalysisRequest(BaseModel):
    """代码分析请求"""
    runtime_diagnosis: RuntimeDiagnosisResult
    project_path: str
    scope: Optional[List[str]] = None  # 限定分析范围


class CodeChangeSuggestion(BaseModel):
    """代码变更建议"""
    suggestion_id: str
    file_path: str
    line_number: Optional[int]
    change_type: str  # "fix", "optimize", "refactor"
    description: str
    before_code: Optional[str]
    after_code: Optional[str]
    impact_analysis: List[str]  # 影响分析
    priority: str  # "high", "medium", "low"


class CodeAnalysisResult(BaseModel):
    """代码分析结果"""
    analysis_id: str
    root_cause_code: Optional[str]  # 根因代码位置
    suggestions: List[CodeChangeSuggestion]
    affected_modules: List[str]
    estimated_fix_time: str  # 预计修复时间
    risk_level: str  # "high", "medium", "low"


class CrossAgentDiagnosisReport(BaseModel):
    """跨 Agent 诊断报告"""
    report_id: str
    workflow_id: str
    anomaly_summary: Dict[str, Any]
    runtime_diagnosis: Optional[RuntimeDiagnosisResult]
    code_analysis: Optional[CodeAnalysisResult]
    final_recommendations: List[str]
    action_plan: List[Dict[str, Any]]
    created_at: datetime

