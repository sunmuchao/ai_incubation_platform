"""
策略相关数据模型
"""
from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional
from enum import Enum
import re


class StrategyType(str, Enum):
    METRICS = "metrics"
    USAGE = "usage"
    HOLISTIC = "holistic"
    CODE_GENERATION = "code_generation"


class StrategyPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class StrategyCondition(BaseModel):
    """策略触发条件"""
    field: str = Field(..., description="检查字段路径，支持点号嵌套")
    operator: str = Field(..., description="比较操作符: gt, lt, eq, ne, contains, matches")
    value: Any = Field(..., description="比较值")
    negate: bool = Field(False, description="是否取反")

    @validator("operator")
    def validate_operator(cls, v):
        allowed_ops = {"gt", "lt", "eq", "ne", "contains", "matches"}
        if v not in allowed_ops:
            raise ValueError(f"Operator must be one of {allowed_ops}")
        return v


class StrategyAction(BaseModel):
    """策略执行动作"""
    suggestion_type: str = Field(..., description="建议类型")
    message_template: str = Field(..., description="消息模板，支持 {field} 变量")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    priority: StrategyPriority = Field(default=StrategyPriority.MEDIUM, description="优先级")
    evidence_fields: List[str] = Field(default_factory=list, description="需要包含的证据字段")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    @validator("confidence")
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class CodeGenerationRule(BaseModel):
    """代码生成规则"""
    suggestion_type: str = Field(..., description="关联的建议类型")
    patch_id: str = Field(..., description="补丁ID前缀")
    title_template: str = Field(..., description="标题模板")
    rationale_template: str = Field(..., description="说明模板")
    risk_level: str = Field(..., description="风险等级: low/medium/high/none")
    file_guess_template: str = Field(..., description="文件路径推测模板")
    code_template: str = Field(..., description="代码模板")
    language: str = Field("python", description="代码语言")
    implementation_kind: str = Field("snippet", description="实现类型")


class AnalysisStrategy(BaseModel):
    """分析策略定义"""
    id: str = Field(..., description="策略唯一标识")
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    type: StrategyType = Field(..., description="策略类型")
    enabled: bool = Field(True, description="是否启用")
    conditions: List[StrategyCondition] = Field(default_factory=list, description="触发条件")
    actions: List[StrategyAction] = Field(default_factory=list, description="执行动作")
    code_rules: List[CodeGenerationRule] = Field(default_factory=list, description="代码生成规则")
    priority: StrategyPriority = Field(default=StrategyPriority.MEDIUM, description="策略优先级")
    tags: List[str] = Field(default_factory=list, description="标签")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class StrategyCreateRequest(BaseModel):
    """创建策略请求"""
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    type: StrategyType = Field(..., description="策略类型")
    enabled: bool = Field(True, description="是否启用")
    conditions: List[StrategyCondition] = Field(default_factory=list, description="触发条件")
    actions: List[StrategyAction] = Field(default_factory=list, description="执行动作")
    code_rules: List[CodeGenerationRule] = Field(default_factory=list, description="代码生成规则")
    priority: StrategyPriority = Field(default=StrategyPriority.MEDIUM, description="策略优先级")
    tags: List[str] = Field(default_factory=list, description="标签")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class StrategyUpdateRequest(BaseModel):
    """更新策略请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[StrategyType] = None
    enabled: Optional[bool] = None
    conditions: Optional[List[StrategyCondition]] = None
    actions: Optional[List[StrategyAction]] = None
    code_rules: Optional[List[CodeGenerationRule]] = None
    priority: Optional[StrategyPriority] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class RuntimeStrategyExecutionPlan(BaseModel):
    """
    运行态策略执行计划（用于 /holistic-analyze 与 /code-proposals）。
    - 规则引擎为主，LLM 为可选增强（默认走全局开关）
    - 可按需指定策略类型与策略ID过滤
    - 可选输入追踪ID：用于建议项与代码提案的可追踪ID生成
    """

    # 仅影响分析/建议生成阶段
    analysis_strategy_types: Optional[List[StrategyType]] = Field(
        default=None,
        description="本次建议生成阶段启用的策略类型（默认：METRICS + USAGE；若显式包含 HOLISTIC 则会执行 HOLISTIC 策略）",
    )
    # 可选：仅执行这些策略ID（过滤 enabled 策略后再应用）
    strategy_ids: Optional[List[str]] = Field(
        default=None,
        description="可选：仅执行这些策略ID",
    )

    # 可选 LLM 增强覆盖：None 表示使用全局配置；True/False 表示强制开/关
    llm_enabled: Optional[bool] = Field(
        default=None,
        description="可选：覆盖全局LLM增强开关（None=使用全局）",
    )

    # 仅影响代码提案生成阶段：指定来源策略类型（用于筛选 code_rules）
    code_strategy_types: Optional[List[StrategyType]] = Field(
        default=None,
        description="可选：用于筛选代码规则来源的策略类型（默认：包含 legacy code_rules，保证可生成补丁）",
    )

    trace_id: Optional[str] = Field(
        default=None,
        description="可选：输入追踪ID（用于建议/补丁可追踪链路）",
    )

    @validator("trace_id")
    def validate_trace_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # 防止注入/过长；保留常见分隔符
        if not re.fullmatch(r"[a-zA-Z0-9_-]{4,64}", v):
            raise ValueError("trace_id must match [a-zA-Z0-9_-]{4,64}")
        return v

