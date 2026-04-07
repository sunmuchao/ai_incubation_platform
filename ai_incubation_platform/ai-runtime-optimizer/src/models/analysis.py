"""
分析相关数据模型
"""
from pydantic import BaseModel, Field, UUID4, validator
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid
from datetime import datetime


class MetricsSnapshot(BaseModel):
    """运行时指标快照"""
    service_name: str = Field(..., description="服务名")
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    error_rate: Optional[float] = Field(None, description="0~1")
    extra: Optional[Dict[str, Any]] = None

    @validator("service_name")
    def validate_service_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("service_name must be a non-empty string")
        return v.strip()

    @validator("cpu_percent")
    def validate_cpu_percent(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0 or v > 100:
            raise ValueError("cpu_percent must be between 0 and 100")
        return v

    @validator("memory_mb")
    def validate_memory_mb(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("memory_mb must be >= 0")
        return v

    @validator("latency_p99_ms")
    def validate_latency_p99_ms(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("latency_p99_ms must be >= 0")
        return v

    @validator("error_rate")
    def validate_error_rate(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0 or v > 1:
            raise ValueError("error_rate must be between 0 and 1")
        return v


class RouteUsageStat(BaseModel):
    """路由级使用统计"""
    path: str
    requests: int = Field(0, description="周期内请求量")
    p99_ms: Optional[float] = None
    error_rate: Optional[float] = Field(None, description="0~1")

    @validator("path")
    def validate_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("path must be a non-empty string")
        return v.strip()

    @validator("requests")
    def validate_requests(cls, v: int) -> int:
        if v < 0:
            raise ValueError("requests must be >= 0")
        return v

    @validator("p99_ms")
    def validate_p99_ms(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("p99_ms must be >= 0")
        return v

    @validator("error_rate")
    def validate_error_rate(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0 or v > 1:
            raise ValueError("error_rate must be between 0 and 1")
        return v


class UsageSummary(BaseModel):
    """用户对系统的使用情况聚合（来自埋点、网关日志、产品分析等）。"""
    service_name: str
    period: str = Field("7d", description="统计周期说明，如 7d、24h")
    top_routes: List[RouteUsageStat] = Field(default_factory=list)
    feature_adoption: Optional[Dict[str, float]] = Field(
        None, description="功能标识 -> 活跃用户占比或渗透率，0~1"
    )
    notes: Optional[str] = Field(None, description="业务备注，如大促、版本发布")

    @validator("service_name")
    def validate_service_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("service_name must be a non-empty string")
        return v.strip()

    @validator("feature_adoption")
    def validate_feature_adoption(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("feature_adoption must be an object")
        for k, ratio in v.items():
            if not k or not str(k).strip():
                raise ValueError("feature_adoption contains an empty feature key")
            if ratio is None or not (0 <= ratio <= 1):
                raise ValueError("feature_adoption values must be between 0 and 1")
        return v


class SuggestionPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Suggestion(BaseModel):
    """分析建议项"""
    id: str = Field(default_factory=lambda: f"suggestion-{uuid.uuid4().hex[:8]}")
    trace_id: Optional[str] = Field(default=None, description="输入追踪ID（可选）")
    analysis_id: Optional[str] = Field(
        default=None, description="关联的分析结果ID（用于端到端追踪）"
    )
    strategy_id: str = Field(..., description="关联的策略ID")
    type: str = Field(..., description="建议类型")
    action: str = Field(..., description="建议的操作内容")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    priority: SuggestionPriority = Field(default=SuggestionPriority.MEDIUM, description="优先级")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="证据数据")
    tags: List[str] = Field(default_factory=list, description="标签")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")

    @validator("confidence")
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class CodePatch(BaseModel):
    """代码变更提案"""
    id: str = Field(default_factory=lambda: f"patch-{uuid.uuid4().hex[:8]}")
    trace_id: Optional[str] = Field(default=None, description="输入追踪ID（可选）")
    proposal_id: Optional[str] = Field(
        default=None, description="关联的代码提案结果ID（用于端到端追踪）"
    )
    suggestion_id: Optional[str] = Field(None, description="关联的建议ID")
    strategy_id: Optional[str] = Field(None, description="关联的策略ID")
    title: str = Field(..., description="补丁标题")
    rationale: str = Field(..., description="补丁说明与理由")
    risk: str = Field(..., description="风险等级: low/medium/high/none")
    file_guess: Optional[str] = Field(None, description="推测的修改文件路径")
    language: str = Field("python", description="代码语言")
    implementation_kind: str = Field("snippet", description="实现类型: snippet/diff/documentation")
    code: str = Field(..., description="代码内容")
    type: str = Field(..., description="补丁类型")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")

    @validator("risk")
    def validate_risk(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "none"}
        if v not in allowed:
            raise ValueError(f"risk must be one of {sorted(allowed)}")
        return v

    @validator("implementation_kind")
    def validate_implementation_kind(cls, v: str) -> str:
        allowed = {"snippet", "diff", "documentation"}
        if v not in allowed:
            raise ValueError(f"implementation_kind must be one of {sorted(allowed)}")
        return v


class AnalysisResult(BaseModel):
    """分析结果"""
    id: str = Field(default_factory=lambda: f"analysis-{uuid.uuid4().hex[:12]}")
    service: str = Field(..., description="服务名称")
    config_hint: Optional[str] = Field(None, description="配置提示")
    trace_id: Optional[str] = Field(default=None, description="输入追踪ID（可选）")
    suggestions: List[Suggestion] = Field(default_factory=list, description="建议列表")
    usage_insights: List[Dict[str, Any]] = Field(default_factory=list, description="用户使用洞察")
    usage_informed: bool = Field(False, description="是否使用了用户行为数据")
    code_proposals_endpoint: str = Field("/api/runtime/code-proposals", description="代码提案端点")
    note: str = Field("", description="备注信息")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CodeProposalsResult(BaseModel):
    """代码提案结果"""
    id: str = Field(default_factory=lambda: f"proposal-{uuid.uuid4().hex[:12]}")
    service: str = Field(..., description="服务名称")
    patches: List[CodePatch] = Field(default_factory=list, description="补丁列表")
    trace_id: Optional[str] = Field(default=None, description="输入追踪ID（可选）")
    requires_human_review: bool = Field(True, description="是否需要人工评审")
    requires_ci: bool = Field(True, description="是否需要CI检查")
    auto_merge_allowed: bool = Field(False, description="是否允许自动合并")
    disclaimer: str = Field(
        default="本响应为结构化草案与示例片段。真实「实现代码」应在受控分支由 LLM/模板生成 "
                "unified diff，经测试与评审后再合并。",
        description="免责声明"
    )
    suggestions_echo: List[str] = Field(default_factory=list, description="关联的建议类型列表")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
