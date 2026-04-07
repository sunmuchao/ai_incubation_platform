"""
P9 阶段数据模型 - AI 能力图谱与自动化工作流

模型列表:
1. CapabilityNode - 能力图谱节点
2. CapabilityEdge - 能力图谱边
3. CapabilityGraph - AI 员工能力图谱
4. Workflow - 工作流定义
5. WorkflowExecution - 工作流执行记录
6. WorkflowTemplate - 工作流模板
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 枚举类型 ====================

class CapabilityRelationship(str, Enum):
    """能力关系类型"""
    REQUIRES = "requires"  # 需要 (前置技能)
    ENHANCES = "enhances"  # 增强 (协同效应)
    CONFLICTS = "conflicts"  # 冲突 (互斥技能)
    RELATED = "related"  # 相关


class WorkflowNodeType(str, Enum):
    """工作流节点类型"""
    AI_TASK = "ai_task"  # AI 任务执行
    CONDITION = "condition"  # 条件判断
    PARALLEL = "parallel"  # 并行分支
    MERGE = "merge"  # 合并分支
    MANUAL = "manual"  # 人工介入


class WorkflowStatus(str, Enum):
    """工作流状态"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 激活
    ARCHIVED = "archived"  # 归档


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    PAUSED = "paused"  # 已暂停


class RetryPolicyType(str, Enum):
    """重试策略类型"""
    NONE = "none"  # 不重试
    FIXED = "fixed"  # 固定间隔
    EXPONENTIAL = "exponential"  # 指数退避


class SortOrder(str, Enum):
    """排序顺序"""
    ASC = "asc"
    DESC = "desc"


# ==================== AI 能力图谱模型 ====================

class CapabilityNode(BaseModel):
    """能力图谱节点"""
    id: str
    name: str  # 技能名称
    category: str  # 技能类别
    proficiency: float = 0.0  # 熟练度 0-1
    training_count: int = 0  # 训练次数
    last_trained: Optional[datetime] = None
    usage_count: int = 0  # 使用次数
    success_rate: float = 0.0  # 成功率
    avg_execution_time: float = 0.0  # 平均执行时间 (秒)
    metadata: Dict[str, Any] = {}  # 附加信息


class CapabilityEdge(BaseModel):
    """能力图谱边"""
    source_id: str  # 源节点 ID
    target_id: str  # 目标节点 ID
    relationship: CapabilityRelationship  # 关系类型
    strength: float = 0.0  # 关系强度 0-1
    description: Optional[str] = None  # 关系描述


class CapabilityGraph(BaseModel):
    """AI 员工能力图谱"""
    employee_id: str
    employee_name: str
    nodes: List[CapabilityNode] = []
    edges: List[CapabilityEdge] = []

    # 图谱分析结果
    centrality_scores: Dict[str, float] = {}  # 中心性分数
    core_capabilities: List[str] = []  # 核心能力 (高中心性)
    isolated_capabilities: List[str] = []  # 孤立能力

    # 进化建议
    evolution_suggestions: List[Dict[str, Any]] = []
    """
    建议格式:
    {
        "type": "add_skill" | "enhance_skill" | "combine_skills",
        "description": "建议描述",
        "priority": "high" | "medium" | "low",
        "related_nodes": ["node_id1", "node_id2"],
        "expected_benefit": "预期收益描述"
    }
    """

    generated_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class IndustryBenchmark(BaseModel):
    """行业基准数据"""
    category: str  # 技能类别
    avg_proficiency: float  # 平均熟练度
    avg_training_count: int  # 平均训练次数
    top_capabilities: List[Dict[str, Any]]  # 热门能力
    trending_capabilities: List[Dict[str, Any]]  # 趋势能力
    salary_range: Dict[str, float]  # 市场价格范围


class CapabilityGraphResponse(BaseModel):
    """能力图谱响应"""
    success: bool
    graph: Optional[CapabilityGraph] = None
    message: str = ""


class SimilarEmployee(BaseModel):
    """相似 AI 员工"""
    employee_id: str
    employee_name: str
    similarity_score: float  # 相似度 0-1
    common_capabilities: List[str]  # 共同能力
    unique_capabilities: List[str]  # 独特能力
    rating: float
    hourly_rate: float


class EvolutionPathRequest(BaseModel):
    """进化路径请求"""
    employee_id: str
    target_role: Optional[str] = None  # 目标角色
    budget: Optional[float] = None  # 训练预算
    timeline: Optional[str] = None  # 时间范围 (1month, 3months, etc.)


class EvolutionPath(BaseModel):
    """进化路径"""
    employee_id: str
    current_state: Dict[str, Any]  # 当前能力状态
    target_state: Dict[str, Any]  # 目标能力状态
    steps: List[Dict[str, Any]]  # 进化步骤
    """
    步骤格式:
    {
        "step": 1,
        "action": "training",
        "capability": "skill_name",
        "estimated_cost": 100.0,
        "estimated_time": "2 hours",
        "expected_improvement": 0.1
    }
    """
    total_estimated_cost: float
    total_estimated_time: str
    expected_roi: float  # 预期投资回报率


# ==================== 自动化工作流模型 ====================

class RetryPolicy(BaseModel):
    """重试策略"""
    policy_type: RetryPolicyType = RetryPolicyType.NONE
    max_retries: int = 0
    fixed_interval_seconds: int = 60
    exponential_base: float = 2.0
    exponential_max_seconds: int = 3600


class WorkflowNode(BaseModel):
    """工作流节点"""
    id: str
    name: str
    node_type: WorkflowNodeType = WorkflowNodeType.AI_TASK
    ai_employee_id: Optional[str] = None  # 负责的 AI 员工 (AI_TASK 类型)
    task_description: str  # 任务描述
    input_mapping: Dict[str, str] = {}  # 输入参数映射
    output_mapping: Dict[str, str] = {}  # 输出参数映射
    timeout_seconds: int = 300  # 超时时间
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    dependencies: List[str] = []  # 依赖的前置节点 ID 列表
    condition: Optional[str] = None  # 条件表达式 (CONDITION 类型)
    parallel_nodes: Optional[List[str]] = None  # 并行节点 ID 列表 (PARALLEL 类型)
    metadata: Dict[str, Any] = {}


class WorkflowEdge(BaseModel):
    """工作流边"""
    source_id: str
    target_id: str
    condition: Optional[str] = None  # 转移条件
    label: Optional[str] = None  # 边标签


class Workflow(BaseModel):
    """工作流定义"""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    status: WorkflowStatus = WorkflowStatus.DRAFT
    tenant_id: str
    created_by: str

    # 工作流结构
    nodes: List[WorkflowNode] = []
    edges: List[WorkflowEdge] = []

    # 输入输出定义
    input_schema: Dict[str, Any] = {}  # JSON Schema
    output_schema: Dict[str, Any] = {}  # JSON Schema

    # 全局配置
    timeout_seconds: int = 3600  # 全局超时
    error_handling: str = "fail_fast"  # fail_fast, continue, rollback

    # 统计
    execution_count: int = 0
    success_rate: float = 0.0
    avg_execution_time: float = 0.0

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class WorkflowTemplate(BaseModel):
    """工作流模板"""
    id: str
    name: str
    description: str
    category: str  # 模板类别
    workflow: Workflow  # 内嵌工作流定义
    is_public: bool = False
    author_id: str
    usage_count: int = 0
    rating: float = 0.0
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)


class NodeExecution(BaseModel):
    """节点执行记录"""
    node_id: str
    node_name: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    input_data: Dict[str, Any] = {}
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: float = 0.0  # 秒
    ai_employee_id: Optional[str] = None


class WorkflowExecution(BaseModel):
    """工作流执行记录"""
    id: str
    workflow_id: str
    workflow_version: str
    tenant_id: str
    triggered_by: str
    trigger_type: str  # manual, api, scheduled, event

    status: ExecutionStatus = ExecutionStatus.PENDING
    input_data: Dict[str, Any] = {}
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    node_executions: List[NodeExecution] = []
    current_node_id: Optional[str] = None

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: float = 0.0  # 总执行时间 (秒)

    created_at: datetime = Field(default_factory=datetime.now)


class ExecuteWorkflowRequest(BaseModel):
    """执行工作流请求"""
    input_data: Dict[str, Any] = {}
    trigger_type: str = "manual"
    callback_url: Optional[str] = None  # 回调 URL


class WorkflowExecutionResponse(BaseModel):
    """工作流执行响应"""
    success: bool
    execution: Optional[WorkflowExecution] = None
    message: str = ""


class WorkflowListParams(BaseModel):
    """工作流列表参数"""
    tenant_id: str
    status: Optional[WorkflowStatus] = None
    keyword: Optional[str] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: SortOrder = SortOrder.DESC


class SearchRequest(BaseModel):
    """高级搜索请求"""
    keyword: Optional[str] = None
    skills: List[str] = []  # 技能筛选
    min_rating: Optional[float] = None
    max_hourly_rate: Optional[float] = None
    availability: Optional[bool] = None
    categories: List[str] = []
    sort_by: str = "rating"
    sort_order: SortOrder = SortOrder.DESC
    page: int = 1
    page_size: int = 20


class SearchResult(BaseModel):
    """搜索结果"""
    employee_id: str
    employee_name: str
    avatar: Optional[str] = None
    description: Optional[str] = None
    skills: Dict[str, str] = {}
    rating: float
    review_count: int
    hourly_rate: float
    availability: str
    match_score: float  # 匹配分数 0-1
    matched_skills: List[str]  # 匹配的技能


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool
    results: List[SearchResult] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    filters: Dict[str, Any] = {}  # 可用筛选条件
    message: str = ""


class SavedSearch(BaseModel):
    """保存的搜索"""
    id: str
    name: str
    tenant_id: str
    user_id: str
    search_params: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    last_executed_at: Optional[datetime] = None


# ==================== 响应模型汇总 ====================

class IndustryBenchmarkResponse(BaseModel):
    """行业基准响应"""
    success: bool
    benchmarks: List[IndustryBenchmark] = []
    message: str = ""


class SimilarEmployeesResponse(BaseModel):
    """相似员工响应"""
    success: bool
    similar_employees: List[SimilarEmployee] = []
    message: str = ""


class EvolutionPathResponse(BaseModel):
    """进化路径响应"""
    success: bool
    evolution_path: Optional[EvolutionPath] = None
    message: str = ""


class WorkflowResponse(BaseModel):
    """工作流响应"""
    success: bool
    workflow: Optional[Workflow] = None
    message: str = ""


class WorkflowTemplateResponse(BaseModel):
    """工作流模板响应"""
    success: bool
    template: Optional[WorkflowTemplate] = None
    message: str = ""


class WorkflowTemplateListResponse(BaseModel):
    """工作流模板列表响应"""
    success: bool
    templates: List[WorkflowTemplate] = []
    total: int = 0
    message: str = ""


class WorkflowExecutionListResponse(BaseModel):
    """工作流执行列表响应"""
    success: bool
    executions: List[WorkflowExecution] = []
    total: int = 0
    message: str = ""


class WorkflowListResponse(BaseModel):
    """工作流列表响应"""
    success: bool
    workflows: List[Workflow] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    message: str = ""


class SavedSearchResponse(BaseModel):
    """保存的搜索响应"""
    success: bool
    saved_search: Optional[SavedSearch] = None
    message: str = ""


class SavedSearchListResponse(BaseModel):
    """保存的搜索列表响应"""
    success: bool
    saved_searches: List[SavedSearch] = []
    total: int = 0
    message: str = ""
