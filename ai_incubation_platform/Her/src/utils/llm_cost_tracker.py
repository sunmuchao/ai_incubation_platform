"""
LLM 成本追踪与监控

每次 LLM 调用都记录：
- Token 消耗（输入/输出）
- 估算成本（按模型定价）
- 响应时间
- 调用上下文（用户ID、场景）

用途：
- 成本控制：识别高成本调用
- 性能优化：发现慢调用
- 用户分析：哪些用户消耗最多
"""

from typing import Dict, Optional, Any
from datetime import datetime
import time
from dataclasses import dataclass, field
from utils.logger import logger


# ==================== 模型定价表 ====================
# 价格单位：元 / 1K tokens

MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI 模型
    "gpt-4o": {"input": 0.025, "output": 0.10},  # 约 $0.005/1K input, $0.015/1K output
    "gpt-4o-mini": {"input": 0.0015, "output": 0.006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},

    # Claude 模型
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},

    # 国产模型（估算）
    "deepseek-chat": {"input": 0.001, "output": 0.002},
    "qwen-max": {"input": 0.002, "output": 0.006},
    "glm-4": {"input": 0.001, "output": 0.002},

    # 默认（未知模型）
    "default": {"input": 0.002, "output": 0.004},
}


@dataclass
class LLMCallRecord:
    """LLM 调用记录"""
    call_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # 调用上下文
    user_id: Optional[str] = None
    endpoint: str = ""  # 调用场景（如 matching, bias_analysis, precommunication）
    model: str = ""

    # Token 统计
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # 成本估算（元）
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0

    # 性能指标
    response_time_ms: int = 0
    cached: bool = False  # 是否命中缓存

    # 状态
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "call_id": self.call_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "total_cost": self.total_cost,
            "response_time_ms": self.response_time_ms,
            "cached": self.cached,
            "success": self.success,
            "error_message": self.error_message,
        }


class LLMCostTracker:
    """
    LLM 成本追踪器

    单例模式，记录所有 LLM 调用

    使用方式：
        tracker = LLMCostTracker.get_instance()
        tracker.start_call("matching", user_id="123", model="gpt-4o")
        # ... 调用 LLM ...
        tracker.end_call(input_tokens=1000, output_tokens=500, cached=False)
    """

    _instance: Optional["LLMCostTracker"] = None

    def __new__(cls) -> "LLMCostTracker":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._records: list[LLMCallRecord] = []
            cls._instance._current_call: Optional[LLMCallRecord] = None
            cls._instance._stats: Dict[str, Any] = {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "cached_calls": 0,
                "error_calls": 0,
                "avg_response_time_ms": 0,
            }
        return cls._instance

    @classmethod
    def get_instance(cls) -> "LLMCostTracker":
        """获取单例实例"""
        return cls()

    def start_call(
        self,
        endpoint: str,
        user_id: Optional[str] = None,
        model: str = "",
    ) -> str:
        """
        开始记录一次 LLM 调用

        Args:
            endpoint: 调用场景（如 matching, bias_analysis）
            user_id: 用户 ID
            model: 使用的模型

        Returns:
            call_id: 调用 ID（用于追踪）
        """
        import uuid

        call_id = str(uuid.uuid4())[:8]

        self._current_call = LLMCallRecord(
            call_id=call_id,
            user_id=user_id,
            endpoint=endpoint,
            model=model,
            timestamp=datetime.now(),
        )

        logger.debug(f"[LLM成本] 开始调用 call_id={call_id}, endpoint={endpoint}, model={model}")

        return call_id

    def end_call(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached: bool = False,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> Optional[LLMCallRecord]:
        """
        结束记录一次 LLM 调用

        Args:
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            cached: 是否命中缓存
            success: 是否成功
            error_message: 错误信息（失败时）

        Returns:
            调用记录
        """
        if not self._current_call:
            logger.warning("[LLM成本] 没有 start_call 的记录，跳过")
            return None

        # 计算响应时间
        if self._current_call.timestamp:
            response_time_ms = int((datetime.now() - self._current_call.timestamp).total_seconds() * 1000)
        else:
            response_time_ms = 0

        # 计算 token 数（如果没有提供，估算）
        total_tokens = input_tokens + output_tokens

        # 计算成本
        pricing = MODEL_PRICING.get(self._current_call.model, MODEL_PRICING["default"])
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost

        # 更新记录
        self._current_call.input_tokens = input_tokens
        self._current_call.output_tokens = output_tokens
        self._current_call.total_tokens = total_tokens
        self._current_call.input_cost = input_cost
        self._current_call.output_cost = output_cost
        self._current_call.total_cost = total_cost
        self._current_call.response_time_ms = response_time_ms
        self._current_call.cached = cached
        self._current_call.success = success
        self._current_call.error_message = error_message

        # 添加到记录列表
        self._records.append(self._current_call)

        # 更新统计
        self._update_stats(self._current_call)

        # 打印日志
        if cached:
            logger.info(f"[LLM成本] 缓存命中 call_id={self._current_call.call_id}, endpoint={self._current_call.endpoint}")
        else:
            logger.info(
                f"[LLM成本] 调用完成 call_id={self._current_call.call_id}, "
                f"endpoint={self._current_call.endpoint}, "
                f"tokens={total_tokens}, "
                f"成本={total_cost:.4f}元, "
                f"耗时={response_time_ms}ms"
            )

        record = self._current_call
        self._current_call = None

        return record

    def _update_stats(self, record: LLMCallRecord) -> None:
        """更新统计数据"""
        self._stats["total_calls"] += 1

        if not record.cached:
            self._stats["total_tokens"] += record.total_tokens
            self._stats["total_cost"] += record.total_cost

        if record.cached:
            self._stats["cached_calls"] += 1

        if not record.success:
            self._stats["error_calls"] += 1

        # 更新平均响应时间
        total_time = self._stats.get("_total_response_time_ms", 0) + record.response_time_ms
        self._stats["_total_response_time_ms"] = total_time
        self._stats["avg_response_time_ms"] = total_time // self._stats["total_calls"]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        return {
            "total_calls": self._stats["total_calls"],
            "total_tokens": self._stats["total_tokens"],
            "total_cost": round(self._stats["total_cost"], 4),
            "cached_calls": self._stats["cached_calls"],
            "cache_rate": self._stats["cached_calls"] / max(self._stats["total_calls"], 1),
            "error_calls": self._stats["error_calls"],
            "error_rate": self._stats["error_calls"] / max(self._stats["total_calls"], 1),
            "avg_response_time_ms": self._stats["avg_response_time_ms"],
        }

    def get_recent_records(self, limit: int = 100) -> list[Dict[str, Any]]:
        """获取最近的调用记录"""
        return [r.to_dict() for r in self._records[-limit:]]

    def get_cost_by_endpoint(self) -> Dict[str, Dict[str, Any]]:
        """按场景统计成本"""
        endpoint_stats: Dict[str, Dict[str, Any]] = {}

        for record in self._records:
            if record.endpoint not in endpoint_stats:
                endpoint_stats[record.endpoint] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "avg_time_ms": 0,
                }

            stats = endpoint_stats[record.endpoint]
            stats["calls"] += 1
            stats["tokens"] += record.total_tokens
            stats["cost"] += record.total_cost
            stats["_total_time"] = stats.get("_total_time", 0) + record.response_time_ms
            stats["avg_time_ms"] = stats["_total_time"] // stats["calls"]

        # 清理临时字段
        for stats in endpoint_stats.values():
            stats.pop("_total_time", None)
            stats["cost"] = round(stats["cost"], 4)

        return endpoint_stats

    def clear_records(self) -> None:
        """清空记录（用于测试）"""
        self._records.clear()
        self._stats = {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "cached_calls": 0,
            "error_calls": 0,
            "avg_response_time_ms": 0,
        }
        logger.info("[LLM成本] 记录已清空")


# ==================== 全局实例 ====================

_cost_tracker: Optional[LLMCostTracker] = None


def get_llm_cost_tracker() -> LLMCostTracker:
    """获取 LLM 成本追踪器单例"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = LLMCostTracker.get_instance()
    return _cost_tracker


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数（粗略估算）

    规则：
    - 中文：约 1.5 tokens / 字
    - 英文：约 0.25 tokens / 字（4字符≈1token）
    - 其他：按字符数 / 4

    Args:
        text: 输入文本

    Returns:
        估算的 token 数
    """
    if not text:
        return 0

    # 分离中文和非中文
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars

    # 估算
    chinese_tokens = chinese_chars * 1.5
    other_tokens = other_chars / 4

    return int(chinese_tokens + other_tokens)


__all__ = [
    "LLMCostTracker",
    "LLMCallRecord",
    "get_llm_cost_tracker",
    "estimate_tokens",
    "MODEL_PRICING",
]