"""
匹配引擎基础模块

定义匹配引擎的抽象接口和数据结构，所有引擎实现需继承此基类。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class EngineType(Enum):
    """引擎类型"""
    RULE = "rule"       # 常规模式（免费）
    AGENTIC = "agentic" # 许愿模式（付费）


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"         # 需求合理，匹配池充足
    MEDIUM = "medium"   # 条件较多，匹配池可能受限
    HIGH = "high"       # 多个硬性条件叠加，匹配难度大
    EXTREME = "extreme" # 条件过于苛刻，匹配池极小


@dataclass
class MatchRequest:
    """
    匹配请求

    通用请求结构，适用于所有引擎
    """
    user_id: str
    limit: int = 10

    # 常规模式参数
    filters: Dict[str, Any] = field(default_factory=dict)

    # 许愿模式参数
    wish_description: Optional[str] = None  # 用户愿望描述
    conversation_history: List[Dict] = field(default_factory=list)  # 对话历史

    # 上下文信息
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """后处理"""
        if self.limit <= 0:
            self.limit = 10
        if self.limit > 50:
            self.limit = 50  # 限制最大返回数量


@dataclass
class MatchCandidate:
    """
    匹配候选人

    单个候选人的详细信息
    """
    user_id: str
    name: str
    score: float  # 匹配分数 0-1
    breakdown: Dict[str, float] = field(default_factory=dict)  # 分数分解

    # 基本信息
    age: Optional[int] = None
    location: Optional[str] = None
    gender: Optional[str] = None
    interests: List[str] = field(default_factory=list)
    bio: Optional[str] = None

    # 许愿模式专属字段
    match_points: List[str] = field(default_factory=list)      # 匹配点
    attention_points: List[str] = field(default_factory=list)  # 注意事项
    risk_warnings: List[str] = field(default_factory=list)     # 风险提示

    # AI 生成的推荐理由
    reasoning: Optional[str] = None


@dataclass
class RiskAnalysis:
    """
    风险分析结果

    许愿模式专属：AI顾问的风险分析
    """
    level: RiskLevel
    description: str
    warning: Optional[str] = None

    # 详细分析
    pool_size_estimate: Optional[int] = None    # 估计匹配池大小
    competition_level: Optional[str] = None     # 竞争程度
    potential_risks: List[str] = field(default_factory=list)  # 潜在风险

    # 建议
    suggestions: List[str] = field(default_factory=list)  # 调整建议

    # 免责声明
    disclaimer: str = "AI只负责帮你找和分析，最终能否聊得来取决于你们双方。感情需要经营。"


@dataclass
class WishAnalysis:
    """
    愿望分析结果

    许愿模式专属：AI顾问对用户愿望的分析
    """
    # 需求拆解
    core_needs: List[str] = field(default_factory=list)       # 核心需求
    hard_conditions: List[str] = field(default_factory=list)  # 硬性条件
    soft_preferences: List[str] = field(default_factory=list) # 软性偏好

    # 风险分析
    risk_analysis: Optional[RiskAnalysis] = None

    # AI建议
    suggestions: List[str] = field(default_factory=list)

    # 免责声明
    disclaimer: str = "AI只负责帮你找和分析，最终能否聊得来取决于你们双方。感情需要经营。"


@dataclass
class MatchResult:
    """
    匹配结果

    通用结果结构，适用于所有引擎
    """
    success: bool
    candidates: List[MatchCandidate] = field(default_factory=list)
    total_count: int = 0

    # 许愿模式专属字段
    wish_analysis: Optional[WishAnalysis] = None  # 愿望分析
    disclaimer: Optional[str] = None              # 免责声明

    # 错误信息
    error: Optional[str] = None
    error_code: Optional[str] = None

    # 元数据
    engine_type: EngineType = EngineType.RULE
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EngineMetrics:
    """
    引擎性能指标

    用于监控和统计
    """
    engine_type: EngineType
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # 响应时间统计
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0

    # 许愿模式专属
    wish_mode_sessions: int = 0      # 许愿会话数
    avg_iterations_per_session: float = 0.0  # 平均迭代次数
    avg_candidates_per_session: float = 0.0  # 平均候选人数

    # 时间窗口
    window_start: datetime = field(default_factory=datetime.now)
    window_end: Optional[datetime] = None

    def record_request(
        self,
        success: bool,
        latency_ms: float,
        iterations: int = 1,
        candidates_count: int = 0
    ):
        """
        记录一次请求

        Args:
            success: 是否成功
            latency_ms: 响应时间（毫秒）
            iterations: 迭代次数（许愿模式）
            candidates_count: 候选人数
        """
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # 更新延迟统计
        if self.total_requests == 1:
            self.avg_latency_ms = latency_ms
            self.min_latency_ms = latency_ms
            self.max_latency_ms = latency_ms
        else:
            # 滚动平均
            self.avg_latency_ms = (
                self.avg_latency_ms * (self.total_requests - 1) + latency_ms
            ) / self.total_requests
            self.min_latency_ms = min(self.min_latency_ms, latency_ms)
            self.max_latency_ms = max(self.max_latency_ms, latency_ms)

        # 许愿模式统计
        if self.engine_type == EngineType.AGENTIC:
            self.wish_mode_sessions += 1
            if self.wish_mode_sessions == 1:
                self.avg_iterations_per_session = iterations
                self.avg_candidates_per_session = candidates_count
            else:
                self.avg_iterations_per_session = (
                    self.avg_iterations_per_session * (self.wish_mode_sessions - 1)
                    + iterations
                ) / self.wish_mode_sessions
                self.avg_candidates_per_session = (
                    self.avg_candidates_per_session * (self.wish_mode_sessions - 1)
                    + candidates_count
                ) / self.wish_mode_sessions


class MatchEngine(ABC):
    """
    匹配引擎抽象基类

    所有匹配引擎需继承此类并实现核心方法。
    """

    engine_type: EngineType
    metrics: EngineMetrics

    @abstractmethod
    async def match(self, request: MatchRequest) -> MatchResult:
        """
        执行匹配

        Args:
            request: 匹配请求

        Returns:
            MatchResult: 匹配结果
        """
        pass

    @abstractmethod
    def get_metrics(self) -> EngineMetrics:
        """
        获取引擎指标

        Returns:
            EngineMetrics: 性能指标
        """
        pass

    @abstractmethod
    def reset_metrics(self) -> None:
        """
        重置指标

        清空统计数据，开始新的统计周期
        """
        pass

    # ============ 可选方法 ============

    def validate_request(self, request: MatchRequest) -> Optional[str]:
        """
        验证请求

        Args:
            request: 匹配请求

        Returns:
            None if valid, error message if invalid
        """
        if not request.user_id:
            return "user_id is required"
        if request.limit <= 0:
            return "limit must be positive"
        return None

    def pre_process(self, request: MatchRequest) -> MatchRequest:
        """
        预处理请求

        Args:
            request: 原始请求

        Returns:
            处理后的请求
        """
        return request

    def post_process(self, result: MatchResult) -> MatchResult:
        """
        后处理结果

        Args:
            result: 原始结果

        Returns:
            处理后的结果
        """
        result.engine_type = self.engine_type
        return result