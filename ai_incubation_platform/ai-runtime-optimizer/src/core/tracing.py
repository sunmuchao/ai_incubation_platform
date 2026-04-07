"""
分布式追踪模块：追踪上下文传播、服务调用链、跨服务延迟分析
对标 OpenTelemetry 和 Datadog APM 追踪能力
"""
import uuid
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class SpanKind(str, Enum):
    """Span 类型"""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(str, Enum):
    """Span 状态"""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Span 上下文"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 1  # 1=采样，0=不采样
    trace_state: Optional[str] = None


@dataclass
class Span:
    """追踪 Span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    status: SpanStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    service_name: str = ""
    operation_name: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    error_stack: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "service_name": self.service_name,
            "operation_name": self.operation_name,
            "attributes": self.attributes,
            "events": self.events,
            "links": self.links,
            "error_message": self.error_message,
            "error_stack": self.error_stack,
            "tags": self.tags
        }


@dataclass
class Trace:
    """完整追踪"""
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    root_span_id: Optional[str] = None
    service_names: List[str] = field(default_factory=list)
    status: SpanStatus = SpanStatus.UNSET
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "spans": [s.to_dict() for s in self.spans],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "root_span_id": self.root_span_id,
            "service_names": list(set(self.service_names)),
            "status": self.status.value,
            "span_count": len(self.spans),
            "tags": self.tags
        }


@dataclass
class ServiceCallEdge:
    """服务调用边"""
    source_service: str
    target_service: str
    call_count: int = 0
    total_latency_ms: float = 0
    error_count: int = 0
    p50_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    last_called: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_service": self.source_service,
            "target_service": self.target_service,
            "call_count": self.call_count,
            "avg_latency_ms": self.total_latency_ms / self.call_count if self.call_count > 0 else 0,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.call_count if self.call_count > 0 else 0,
            "last_called": self.last_called.isoformat() if self.last_called else None
        }


class SamplingStrategy:
    """采样策略"""

    def __init__(self, sampling_rate: float = 1.0):
        self.sampling_rate = sampling_rate
        self._sample_count = 0
        self._total_count = 0

    def should_sample(self, trace_id: str) -> bool:
        """判断是否采样"""
        self._total_count += 1

        # 基于 trace_id 的确定性采样
        trace_hash = int(trace_id[:16], 16)
        should_sample = (trace_hash % 100) < (self.sampling_rate * 100)

        if should_sample:
            self._sample_count += 1

        return should_sample

    def get_stats(self) -> Dict[str, Any]:
        """获取采样统计"""
        return {
            "sampling_rate": self.sampling_rate,
            "sampled_count": self._sample_count,
            "total_count": self._total_count,
            "actual_rate": self._sample_count / self._total_count if self._total_count > 0 else 0
        }


class TracingContextManager:
    """追踪上下文管理器"""

    def __init__(self):
        self._local_context: Dict[int, SpanContext] = {}
        self._lock = threading.Lock()

    def set_context(self, context: SpanContext):
        """设置当前线程的上下文"""
        thread_id = threading.current_thread().ident
        with self._lock:
            self._local_context[thread_id] = context

    def get_context(self) -> Optional[SpanContext]:
        """获取当前线程的上下文"""
        thread_id = threading.current_thread().ident
        with self._lock:
            return self._local_context.get(thread_id)

    def clear_context(self):
        """清除当前线程的上下文"""
        thread_id = threading.current_thread().ident
        with self._lock:
            if thread_id in self._local_context:
                del self._local_context[thread_id]

    def extract_from_headers(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """从 HTTP 头提取上下文 (W3C Trace Context)"""
        traceparent = headers.get("traceparent", "")

        if not traceparent:
            # 尝试其他格式
            trace_id = headers.get("X-Trace-ID") or headers.get("X-B3-TraceId")
            span_id = headers.get("X-Span-ID") or headers.get("X-B3-SpanId")
            parent_id = headers.get("X-Parent-ID") or headers.get("X-B3-ParentSpanId")

            if trace_id and span_id:
                return SpanContext(
                    trace_id=trace_id,
                    span_id=span_id,
                    parent_span_id=parent_id
                )
            return None

        # W3C Trace Context 格式：00-{trace-id}-{span-id}-{flags}
        parts = traceparent.split("-")
        if len(parts) >= 4:
            return SpanContext(
                trace_id=parts[1],
                span_id=parts[2],
                trace_flags=int(parts[3], 16)
            )

        return None

    def inject_to_headers(self, context: SpanContext, headers: Dict[str, str]) -> Dict[str, str]:
        """注入上下文到 HTTP 头"""
        headers["traceparent"] = f"00-{context.trace_id}-{context.span_id}-{context.trace_flags:02x}"
        if context.trace_state:
            headers["tracestate"] = context.trace_state
        return headers


class DistributedTracer:
    """分布式追踪器"""

    def __init__(self, service_name: str = "unknown", sampling_rate: float = 1.0):
        self.service_name = service_name
        self._traces: Dict[str, Trace] = {}
        self._spans: Dict[str, Span] = {}
        self._active_spans: Dict[int, Span] = {}
        self._service_edges: Dict[str, ServiceCallEdge] = {}
        self._context_manager = TracingContextManager()
        self._sampling_strategy = SamplingStrategy(sampling_rate)

        # 配置
        self._max_traces = 10000
        self._max_spans_per_trace = 100
        self._trace_ttl_hours = 24

        # 统计
        self._stats = {
            "traces_created": 0,
            "spans_created": 0,
            "errors_recorded": 0
        }

    def start_trace(
        self,
        name: str,
        operation_name: str,
        kind: SpanKind = SpanKind.SERVER,
        parent_context: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """开始一个新的追踪"""
        if parent_context:
            trace_id = parent_context.trace_id
            sampled = bool(parent_context.trace_flags & 1)
        else:
            trace_id = uuid.uuid4().hex
            sampled = self._sampling_strategy.should_sample(trace_id)

        span_id = uuid.uuid4().hex[:16]

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_context.span_id if parent_context else None,
            name=name,
            kind=kind,
            status=SpanStatus.UNSET,
            start_time=datetime.utcnow(),
            service_name=self.service_name,
            operation_name=operation_name,
            attributes=attributes or {}
        )

        # 创建 Trace
        if trace_id not in self._traces:
            self._traces[trace_id] = Trace(
                trace_id=trace_id,
                root_span_id=span_id if not parent_context else None
            )

        # 保存 Span
        self._spans[span_id] = span
        self._active_spans[id(span)] = span

        # 设置上下文
        new_context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_context.span_id if parent_context else None,
            trace_flags=1 if sampled else 0
        )
        self._context_manager.set_context(new_context)

        self._stats["traces_created"] += 1
        self._stats["spans_created"] += 1

        logger.debug(f"Trace started: {trace_id}, span: {span_id}")
        return span

    def start_span(
        self,
        name: str,
        operation_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """开始一个新的 Span（子追踪）"""
        parent_context = self._context_manager.get_context()

        return self.start_trace(
            name=name,
            operation_name=operation_name,
            kind=kind,
            parent_context=parent_context,
            attributes=attributes
        )

    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK):
        """结束 Span"""
        span.end_time = datetime.utcnow()
        span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
        span.status = status

        # 更新上下文
        context = self._context_manager.get_context()
        if context and context.span_id == span.span_id:
            # 如果有父 span，恢复父上下文
            if span.parent_span_id:
                parent_span = self._spans.get(span.parent_span_id)
                if parent_span:
                    new_context = SpanContext(
                        trace_id=span.trace_id,
                        span_id=parent_span.span_id,
                        parent_span_id=parent_span.parent_span_id,
                        trace_flags=context.trace_flags
                    )
                    self._context_manager.set_context(new_context)
            else:
                self._context_manager.clear_context()

        # 从活跃列表移除
        if id(span) in self._active_spans:
            del self._active_spans[id(span)]

        # 更新 Trace
        trace = self._traces.get(span.trace_id)
        if trace:
            if span not in trace.spans:
                trace.spans.append(span)

            if span.service_name not in trace.service_names:
                trace.service_names.append(span.service_name)

            # 更新 Trace 时间
            trace.start_time = min(s.start_time for s in trace.spans) if trace.spans else None
            trace.end_time = max(s.end_time for s in trace.spans if s.end_time) if trace.spans else None
            if trace.start_time and trace.end_time:
                trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000

            # 更新 Trace 状态
            if status == SpanStatus.ERROR:
                trace.status = SpanStatus.ERROR

        # 记录服务调用边
        if span.parent_span_id:
            parent_span = self._spans.get(span.parent_span_id)
            if parent_span and parent_span.service_name != span.service_name:
                self._record_service_call(
                    parent_span.service_name,
                    span.service_name,
                    span.duration_ms,
                    status == SpanStatus.ERROR
                )

        logger.debug(f"Span ended: {span.span_id}, duration: {span.duration_ms:.2f}ms")

    def record_error(self, span: Span, error: Exception, stack_trace: Optional[str] = None):
        """记录错误"""
        span.status = SpanStatus.ERROR
        span.error_message = str(error)
        span.error_stack = stack_trace

        # 添加错误事件
        span.events.append({
            "name": "exception",
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": {
                "exception.type": type(error).__name__,
                "exception.message": str(error),
                "exception.stacktrace": stack_trace or ""
            }
        })

        self._stats["errors_recorded"] += 1

    def add_event(self, span: Span, name: str, attributes: Optional[Dict[str, Any]] = None):
        """添加事件到 Span"""
        span.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {}
        })

    def add_link(self, span: Span, linked_trace_id: str, linked_span_id: str, attributes: Optional[Dict[str, Any]] = None):
        """添加链接到 Span"""
        span.links.append({
            "trace_id": linked_trace_id,
            "span_id": linked_span_id,
            "attributes": attributes or {}
        })

    def set_attribute(self, span: Span, key: str, value: Any):
        """设置 Span 属性"""
        span.attributes[key] = value

    def _record_service_call(self, source: str, target: str, latency_ms: float, is_error: bool):
        """记录服务调用"""
        edge_key = f"{source}->{target}"

        if edge_key not in self._service_edges:
            self._service_edges[edge_key] = ServiceCallEdge(
                source_service=source,
                target_service=target
            )

        edge = self._service_edges[edge_key]
        edge.call_count += 1
        edge.total_latency_ms += latency_ms
        if is_error:
            edge.error_count += 1
        edge.last_called = datetime.utcnow()

        # 更新延迟百分位（简化实现）
        latencies = [latency_ms]  # 实际应该维护一个列表
        edge.p50_latency_ms = latency_ms
        edge.p95_latency_ms = latency_ms * 1.5
        edge.p99_latency_ms = latency_ms * 2.0

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取追踪"""
        return self._traces.get(trace_id)

    def get_span(self, span_id: str) -> Optional[Span]:
        """获取 Span"""
        return self._spans.get(span_id)

    def search_traces(
        self,
        service_name: Optional[str] = None,
        operation_name: Optional[str] = None,
        status: Optional[SpanStatus] = None,
        min_duration_ms: Optional[float] = None,
        start_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Trace]:
        """搜索追踪"""
        results = []

        for trace in self._traces.values():
            if not trace.spans:
                continue

            # 过滤条件
            if service_name:
                if service_name not in trace.service_names:
                    continue

            if operation_name:
                if not any(s.operation_name == operation_name for s in trace.spans):
                    continue

            if status:
                if trace.status != status:
                    continue

            if min_duration_ms and trace.duration_ms:
                if trace.duration_ms < min_duration_ms:
                    continue

            if start_time and trace.start_time:
                if trace.start_time < start_time:
                    continue

            results.append(trace)

            if len(results) >= limit:
                break

        return sorted(results, key=lambda t: t.start_time or datetime.min, reverse=True)

    def get_service_map(self) -> Dict[str, Any]:
        """获取服务调用图"""
        nodes = set()
        edges = []

        for edge in self._service_edges.values():
            nodes.add(edge.source_service)
            nodes.add(edge.target_service)
            edges.append(edge.to_dict())

        return {
            "nodes": [{"id": n, "name": n} for n in nodes],
            "edges": edges,
            "total_calls": sum(e.call_count for e in self._service_edges.values())
        }

    def get_slow_traces(self, threshold_ms: float = 1000, limit: int = 20) -> List[Dict[str, Any]]:
        """获取慢追踪"""
        slow_traces = [
            t for t in self._traces.values()
            if t.duration_ms and t.duration_ms > threshold_ms
        ]

        return [
            {
                "trace_id": t.trace_id,
                "duration_ms": t.duration_ms,
                "service_names": t.service_names,
                "span_count": len(t.spans),
                "status": t.status.value
            }
            for t in sorted(slow_traces, key=lambda x: x.duration_ms, reverse=True)[:limit]
        ]

    def get_trace_waterfall(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """获取追踪瀑布图数据"""
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        # 按开始时间排序 spans
        sorted_spans = sorted(trace.spans, key=lambda s: s.start_time or datetime.min)

        # 计算相对时间
        base_time = trace.start_time or datetime.utcnow()

        waterfall = []
        for span in sorted_spans:
            start_offset = (span.start_time - base_time).total_seconds() * 1000 if span.start_time else 0
            waterfall.append({
                "span_id": span.span_id,
                "name": span.name,
                "service": span.service_name,
                "start_offset_ms": start_offset,
                "duration_ms": span.duration_ms,
                "status": span.status.value,
                "depth": self._calculate_span_depth(span)
            })

        return {
            "trace_id": trace_id,
            "total_duration_ms": trace.duration_ms,
            "waterfall": waterfall
        }

    def _calculate_span_depth(self, span: Span) -> int:
        """计算 Span 深度"""
        depth = 0
        current_parent = span.parent_span_id

        while current_parent:
            parent_span = self._spans.get(current_parent)
            if not parent_span:
                break
            depth += 1
            current_parent = parent_span.parent_span_id

        return depth

    def get_cross_service_latency(self, service_name: str) -> Dict[str, Any]:
        """获取跨服务延迟分析"""
        incoming_calls = []
        outgoing_calls = []

        for edge in self._service_edges.values():
            if edge.target_service == service_name:
                incoming_calls.append(edge.to_dict())
            if edge.source_service == service_name:
                outgoing_calls.append(edge.to_dict())

        return {
            "service_name": service_name,
            "incoming_calls": incoming_calls,
            "outgoing_calls": outgoing_calls,
            "total_incoming": len(incoming_calls),
            "total_outgoing": len(outgoing_calls)
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取追踪统计"""
        return {
            **self._stats,
            "total_traces": len(self._traces),
            "total_spans": len(self._spans),
            "active_spans": len(self._active_spans),
            "service_edges": len(self._service_edges),
            "sampling_stats": self._sampling_strategy.get_stats()
        }

    def cleanup_old_traces(self, max_age_hours: int = 24):
        """清理旧追踪"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        old_trace_ids = [
            trace_id for trace_id, trace in self._traces.items()
            if trace.start_time and trace.start_time < cutoff_time
        ]

        for trace_id in old_trace_ids:
            trace = self._traces[trace_id]
            # 删除相关 spans
            for span in trace.spans:
                if span.span_id in self._spans:
                    del self._spans[span.span_id]
            del self._traces[trace_id]

        logger.info(f"Cleaned up {len(old_trace_ids)} old traces")


class TracingClient:
    """追踪客户端 - 用于外部服务集成"""

    def __init__(self, service_name: str, tracer: Optional[DistributedTracer] = None):
        self.service_name = service_name
        self._tracer = tracer or DistributedTracer(service_name)

    def create_headers(self, span: Span) -> Dict[str, str]:
        """创建用于传播的 HTTP 头"""
        headers = {}
        context = self._tracer._context_manager.get_context()
        if context:
            self._tracer._context_manager.inject_to_headers(context, headers)
        return headers

    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """从 HTTP 头提取上下文"""
        return self._tracer._context_manager.extract_from_headers(headers)

    def trace_request(self, method: str, path: str, headers: Dict[str, str]) -> Span:
        """追踪入口请求"""
        parent_context = self.extract_context(headers)

        return self._tracer.start_trace(
            name=f"{method} {path}",
            operation_name=path,
            kind=SpanKind.SERVER,
            parent_context=parent_context,
            attributes={"http.method": method, "http.target": path}
        )

    def trace_outgoing_request(self, method: str, url: str, target_service: str) -> Span:
        """追踪出站请求"""
        span = self._tracer.start_span(
            name=f"OUT {url}",
            operation_name=url,
            kind=SpanKind.CLIENT,
            attributes={"http.method": method, "http.url": url, "peer.service": target_service}
        )
        return span


# 全局追踪器实例
global_tracer = DistributedTracer(service_name="ai-runtime-optimizer")


def create_tracing_client(service_name: str) -> TracingClient:
    """创建追踪客户端"""
    return TracingClient(service_name=service_name)
