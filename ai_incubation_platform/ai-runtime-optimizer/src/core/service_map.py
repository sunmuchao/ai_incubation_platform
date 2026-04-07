"""
服务依赖映射：自动发现服务间调用关系，构建服务拓扑图
对标 Datadog Service Map 能力
"""
import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

logger = logging.getLogger(__name__)


class DependencyType(str, Enum):
    """依赖类型"""
    HTTP = "http"
    RPC = "rpc"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceNode:
    """服务节点"""
    id: str
    name: str
    type: str = "service"  # service, database, cache, etc.
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_seen_at: datetime = field(default_factory=datetime.utcnow)

    # 运行时指标
    latency_p50_ms: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    error_rate: Optional[float] = None
    requests_per_second: Optional[float] = None
    health_status: HealthStatus = HealthStatus.UNKNOWN

    # 资源指标
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    instance_count: int = 1


@dataclass
class DependencyEdge:
    """服务依赖边"""
    id: str
    source_service: str
    target_service: str
    dependency_type: DependencyType
    protocol: Optional[str] = None  # HTTP, gRPC, TCP, etc.
    endpoint: Optional[str] = None  # API path, DB table, etc.

    # 调用指标
    call_count: int = 0
    latency_p50_ms: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    error_count: int = 0
    error_rate: Optional[float] = None

    # 时间信息
    first_seen_at: datetime = field(default_factory=datetime.utcnow)
    last_seen_at: datetime = field(default_factory=datetime.utcnow)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> Optional[float]:
        if self.error_rate is not None:
            return 1.0 - self.error_rate
        return None


@dataclass
class ServicePath:
    """服务调用路径（用于关键路径分析）"""
    path: List[str]  # 服务 ID 列表
    total_latency_ms: float
    total_error_rate: float
    call_count: int
    is_critical: bool = False


class ServiceMap:
    """服务依赖映射"""

    def __init__(self, max_history_edges: int = 10000):
        self._services: Dict[str, ServiceNode] = {}
        self._edges: Dict[str, DependencyEdge] = {}
        self._adjacency_list: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency_list: Dict[str, Set[str]] = defaultdict(set)

        # 边历史（用于趋势分析）
        self._edge_history: List[Tuple[datetime, str, Dict[str, Any]]] = []
        self._max_history_edges = max_history_edges

        # 服务指标历史（用于异常检测）
        self._service_metrics_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._max_metrics_history = 1000

    def register_service(
        self,
        service_id: str,
        name: str,
        service_type: str = "service",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceNode:
        """注册服务节点"""
        if service_id not in self._services:
            service = ServiceNode(
                id=service_id,
                name=name,
                type=service_type,
                tags=tags or [],
                metadata=metadata or {}
            )
            self._services[service_id] = service
            logger.info(f"Service registered: {service_id} ({name})")
        else:
            service = self._services[service_id]
            service.last_seen_at = datetime.utcnow()
            if name:
                service.name = name
            if service_type:
                service.type = service_type
            if tags:
                service.tags.extend(tags)
            if metadata:
                service.metadata.update(metadata)

        return service

    def record_dependency(
        self,
        source_service: str,
        target_service: str,
        dependency_type: DependencyType = DependencyType.UNKNOWN,
        protocol: Optional[str] = None,
        endpoint: Optional[str] = None,
        latency_ms: Optional[float] = None,
        is_error: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DependencyEdge:
        """记录服务间调用依赖"""
        # 确保服务节点存在
        self.register_service(source_service, source_service)
        self.register_service(target_service, target_service)

        # 生成边 ID
        edge_id = f"{source_service}->{target_service}:{endpoint or '*'}"

        if edge_id not in self._edges:
            edge = DependencyEdge(
                id=edge_id,
                source_service=source_service,
                target_service=target_service,
                dependency_type=dependency_type,
                protocol=protocol,
                endpoint=endpoint,
                metadata=metadata or {}
            )
            self._edges[edge_id] = edge
            self._adjacency_list[source_service].add(edge_id)
            self._reverse_adjacency_list[target_service].add(edge_id)
            logger.debug(f"Dependency recorded: {source_service} -> {target_service}")
        else:
            edge = self._edges[edge_id]

        # 更新边指标
        edge.call_count += 1
        edge.last_seen_at = datetime.utcnow()

        if latency_ms is not None:
            # 简单移动平均更新 P50/P99
            if edge.latency_p50_ms is None:
                edge.latency_p50_ms = latency_ms
                edge.latency_p99_ms = latency_ms
            else:
                # 简化计算：指数移动平均
                alpha = 0.3
                edge.latency_p50_ms = alpha * latency_ms + (1 - alpha) * edge.latency_p50_ms
                if latency_ms > edge.latency_p99_ms:
                    edge.latency_p99_ms = latency_ms

        if is_error:
            edge.error_count += 1

        # 计算错误率
        edge.error_rate = edge.error_count / edge.call_count if edge.call_count > 0 else None

        # 记录历史
        self._record_edge_history(edge_id, {
            "latency_ms": latency_ms,
            "is_error": is_error,
            "call_count": edge.call_count,
            "error_rate": edge.error_rate
        })

        # 更新服务健康状态
        self._update_service_health(source_service)
        self._update_service_health(target_service)

        return edge

    def _record_edge_history(self, edge_id: str, metrics: Dict[str, Any]):
        """记录边指标历史"""
        now = datetime.utcnow()
        self._edge_history.append((now, edge_id, metrics))

        # 清理过期历史
        if len(self._edge_history) > self._max_history_edges:
            self._edge_history = self._edge_history[-self._max_history_edges:]

    def record_service_metrics(
        self,
        service_id: str,
        metrics: Dict[str, Any]
    ):
        """记录服务指标"""
        if service_id in self._services:
            service = self._services[service_id]

            # 更新服务指标
            if "latency_p50_ms" in metrics:
                service.latency_p50_ms = metrics["latency_p50_ms"]
            if "latency_p99_ms" in metrics:
                service.latency_p99_ms = metrics["latency_p99_ms"]
            if "error_rate" in metrics:
                service.error_rate = metrics["error_rate"]
            if "requests_per_second" in metrics:
                service.requests_per_second = metrics["requests_per_second"]
            if "cpu_percent" in metrics:
                service.cpu_percent = metrics["cpu_percent"]
            if "memory_mb" in metrics:
                service.memory_mb = metrics["memory_mb"]
            if "instance_count" in metrics:
                service.instance_count = metrics["instance_count"]

            service.last_seen_at = datetime.utcnow()

            # 记录历史
            self._service_metrics_history[service_id].append({
                "timestamp": datetime.utcnow(),
                **metrics
            })

            # 清理过期历史
            if len(self._service_metrics_history[service_id]) > self._max_metrics_history:
                self._service_metrics_history[service_id] = \
                    self._service_metrics_history[service_id][-self._max_metrics_history:]

            # 更新健康状态
            self._update_service_health(service_id)

    def _update_service_health(self, service_id: str):
        """更新服务健康状态"""
        if service_id not in self._services:
            return

        service = self._services[service_id]

        # 基于错误率判断健康状态
        if service.error_rate is not None:
            if service.error_rate > 0.1:
                service.health_status = HealthStatus.UNHEALTHY
            elif service.error_rate > 0.01:
                service.health_status = HealthStatus.DEGRADED
            else:
                service.health_status = HealthStatus.HEALTHY

        # 基于延迟判断
        elif service.latency_p99_ms is not None:
            if service.latency_p99_ms > 5000:
                service.health_status = HealthStatus.UNHEALTHY
            elif service.latency_p99_ms > 1000:
                service.health_status = HealthStatus.DEGRADED
            else:
                service.health_status = HealthStatus.HEALTHY

        # 基于 CPU 判断
        elif service.cpu_percent is not None:
            if service.cpu_percent > 90:
                service.health_status = HealthStatus.DEGRADED
            else:
                service.health_status = HealthStatus.HEALTHY

        else:
            service.health_status = HealthStatus.UNKNOWN

    def get_service(self, service_id: str) -> Optional[ServiceNode]:
        """获取服务节点"""
        return self._services.get(service_id)

    def get_edge(self, edge_id: str) -> Optional[DependencyEdge]:
        """获取依赖边"""
        return self._edges.get(edge_id)

    def get_dependencies(self, service_id: str) -> List[DependencyEdge]:
        """获取服务的所有依赖边（出边和入边）"""
        edges = []

        # 出边（该服务调用的其他服务）
        for edge_id in self._adjacency_list.get(service_id, set()):
            if edge_id in self._edges:
                edges.append(self._edges[edge_id])

        # 入边（调用该服务的其他服务）
        for edge_id in self._reverse_adjacency_list.get(service_id, set()):
            if edge_id in self._edges:
                edges.append(self._edges[edge_id])

        return edges

    def get_upstream_services(self, service_id: str) -> List[str]:
        """获取上游服务（调用该服务的其他服务）"""
        upstream = []
        for edge_id in self._reverse_adjacency_list.get(service_id, set()):
            if edge_id in self._edges:
                edge = self._edges[edge_id]
                upstream.append(edge.source_service)
        return upstream

    def get_downstream_services(self, service_id: str) -> List[str]:
        """获取下游服务（该服务调用的其他服务）"""
        downstream = []
        for edge_id in self._adjacency_list.get(service_id, set()):
            if edge_id in self._edges:
                edge = self._edges[edge_id]
                downstream.append(edge.target_service)
        return downstream

    def find_paths(
        self,
        source_service: str,
        target_service: str,
        max_depth: int = 10
    ) -> List[ServicePath]:
        """查找两个服务之间的所有路径（BFS）"""
        if source_service not in self._services or target_service not in self._services:
            return []

        paths = []
        queue = [(source_service, [source_service], 0.0, 0.0, 1)]
        visited_paths = set()

        while queue and len(paths) < 100:  # 限制最大路径数
            current, path, total_latency, combined_error_rate, call_count = queue.pop(0)

            if current == target_service:
                path_key = "->".join(path)
                if path_key not in visited_paths:
                    paths.append(ServicePath(
                        path=path,
                        total_latency_ms=total_latency,
                        total_error_rate=1 - combined_error_rate,
                        call_count=call_count
                    ))
                    visited_paths.add(path_key)
                continue

            if len(path) >= max_depth:
                continue

            # 遍历下游服务
            for edge_id in self._adjacency_list.get(current, set()):
                edge = self._edges.get(edge_id)
                if edge:
                    next_service = edge.target_service
                    if next_service not in path:  # 避免循环
                        new_latency = total_latency + (edge.latency_p50_ms or 0)
                        new_error_rate = combined_error_rate * (1 - (edge.error_rate or 0))
                        new_call_count = min(call_count, edge.call_count)

                        queue.append((
                            next_service,
                            path + [next_service],
                            new_latency,
                            new_error_rate,
                            new_call_count
                        ))

        return paths

    def find_critical_paths(self, max_latency_threshold_ms: float = 1000) -> List[ServicePath]:
        """查找关键路径（高延迟或高错误率的路径）"""
        critical_paths = []

        # 从每个入口服务开始查找
        entry_services = self._find_entry_services()

        for entry in entry_services:
            # 查找所有 leaf 服务
            leaf_services = self._find_leaf_services()

            for leaf in leaf_services:
                paths = self.find_paths(entry, leaf)
                for path in paths:
                    if path.total_latency_ms > max_latency_threshold_ms or path.total_error_rate > 0.01:
                        path.is_critical = True
                        critical_paths.append(path)

        # 按延迟排序
        return sorted(critical_paths, key=lambda p: p.total_latency_ms, reverse=True)

    def _find_entry_services(self) -> List[str]:
        """查找入口服务（没有被其他服务调用的服务）"""
        all_services = set(self._services.keys())
        called_services = set()

        for edge in self._edges.values():
            called_services.add(edge.target_service)

        return list(all_services - called_services)

    def _find_leaf_services(self) -> List[str]:
        """查找叶子服务（没有调用其他服务的服务）"""
        all_services = set(self._services.keys())
        calling_services = set()

        for edge in self._edges.values():
            calling_services.add(edge.source_service)

        return list(all_services - calling_services)

    def get_bottleneck_services(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """识别瓶颈服务"""
        bottlenecks = []

        for service_id, service in self._services.items():
            score = 0
            reasons = []

            # 高延迟
            if service.latency_p99_ms and service.latency_p99_ms > 500:
                score += service.latency_p99_ms / 100
                reasons.append(f"high_latency_p99={service.latency_p99_ms}ms")

            # 高错误率
            if service.error_rate and service.error_rate > 0.01:
                score += service.error_rate * 100
                reasons.append(f"high_error_rate={service.error_rate:.2%}")

            # 高 CPU
            if service.cpu_percent and service.cpu_percent > 80:
                score += service.cpu_percent / 10
                reasons.append(f"high_cpu={service.cpu_percent}%")

            # 被多个服务依赖
            upstream_count = len(self.get_upstream_services(service_id))
            if upstream_count > 3:
                score += upstream_count * 5
                reasons.append(f"many_dependents={upstream_count}")

            if score > 0:
                bottlenecks.append({
                    "service_id": service_id,
                    "service_name": service.name,
                    "bottleneck_score": score,
                    "reasons": reasons,
                    "metrics": {
                        "latency_p99_ms": service.latency_p99_ms,
                        "error_rate": service.error_rate,
                        "cpu_percent": service.cpu_percent,
                        "upstream_count": upstream_count
                    }
                })

        return sorted(bottlenecks, key=lambda x: x["bottleneck_score"], reverse=True)[:top_n]

    def get_service_map_data(self) -> Dict[str, Any]:
        """获取服务映射数据（用于前端可视化）"""
        nodes = []
        edges = []

        for service_id, service in self._services.items():
            nodes.append({
                "id": service_id,
                "name": service.name,
                "type": service.type,
                "health_status": service.health_status.value,
                "tags": service.tags,
                "metrics": {
                    "latency_p50_ms": service.latency_p50_ms,
                    "latency_p99_ms": service.latency_p99_ms,
                    "error_rate": service.error_rate,
                    "requests_per_second": service.requests_per_second,
                    "cpu_percent": service.cpu_percent,
                    "memory_mb": service.memory_mb,
                    "instance_count": service.instance_count
                }
            })

        for edge_id, edge in self._edges.items():
            edges.append({
                "id": edge_id,
                "source": edge.source_service,
                "target": edge.target_service,
                "dependency_type": edge.dependency_type.value,
                "protocol": edge.protocol,
                "endpoint": edge.endpoint,
                "metrics": {
                    "call_count": edge.call_count,
                    "latency_p50_ms": edge.latency_p50_ms,
                    "latency_p99_ms": edge.latency_p99_ms,
                    "error_rate": edge.error_rate,
                    "success_rate": edge.success_rate
                }
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_services": len(nodes),
                "total_dependencies": len(edges),
                "healthy_services": len([n for n in nodes if n["health_status"] == "healthy"]),
                "degraded_services": len([n for n in nodes if n["health_status"] == "degraded"]),
                "unhealthy_services": len([n for n in nodes if n["health_status"] == "unhealthy"])
            }
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取服务映射统计"""
        return {
            "total_services": len(self._services),
            "total_dependencies": len(self._edges),
            "services_by_type": self._count_services_by_type(),
            "services_by_health": self._count_services_by_health(),
            "dependencies_by_type": self._count_dependencies_by_type(),
            "edge_history_size": len(self._edge_history)
        }

    def _count_services_by_type(self) -> Dict[str, int]:
        """按类型统计服务"""
        counts = defaultdict(int)
        for service in self._services.values():
            counts[service.type] += 1
        return dict(counts)

    def _count_services_by_health(self) -> Dict[str, int]:
        """按健康状态统计服务"""
        counts = defaultdict(int)
        for service in self._services.values():
            counts[service.health_status.value] += 1
        return dict(counts)

    def _count_dependencies_by_type(self) -> Dict[str, int]:
        """按类型统计依赖"""
        counts = defaultdict(int)
        for edge in self._edges.values():
            counts[edge.dependency_type.value] += 1
        return dict(counts)


# 全局服务映射实例
service_map = ServiceMap()


def create_sample_service_map():
    """创建示例服务映射数据"""
    # 注册服务
    service_map.register_service("api-gateway", "API Gateway", "service", tags=["ingress"])
    service_map.register_service("user-service", "User Service", "service", tags=["core"])
    service_map.register_service("order-service", "Order Service", "service", tags=["core"])
    service_map.register_service("payment-service", "Payment Service", "service", tags=["payment"])
    service_map.register_service("inventory-service", "Inventory Service", "service", tags=["inventory"])
    service_map.register_service("notification-service", "Notification Service", "service", tags=["notification"])
    service_map.register_service("postgres-main", "PostgreSQL Main", "database", tags=["database"])
    service_map.register_service("redis-cache", "Redis Cache", "cache", tags=["cache"])
    service_map.register_service("kafka", "Kafka", "message_queue", tags=["mq"])

    # 记录依赖关系
    service_map.record_dependency("api-gateway", "user-service", DependencyType.HTTP, "HTTP", "/api/users")
    service_map.record_dependency("api-gateway", "order-service", DependencyType.HTTP, "HTTP", "/api/orders")
    service_map.record_dependency("user-service", "postgres-main", DependencyType.DATABASE, "TCP", "users")
    service_map.record_dependency("user-service", "redis-cache", DependencyType.CACHE, "TCP", "user:session")
    service_map.record_dependency("order-service", "payment-service", DependencyType.RPC, "gRPC", "Payment")
    service_map.record_dependency("order-service", "inventory-service", DependencyType.RPC, "gRPC", "Inventory")
    service_map.record_dependency("order-service", "postgres-main", DependencyType.DATABASE, "TCP", "orders")
    service_map.record_dependency("payment-service", "postgres-main", DependencyType.DATABASE, "TCP", "payments")
    service_map.record_dependency("payment-service", "kafka", DependencyType.MESSAGE_QUEUE, "TCP", "payment-events")
    service_map.record_dependency("inventory-service", "postgres-main", DependencyType.DATABASE, "TCP", "inventory")
    service_map.record_dependency("notification-service", "kafka", DependencyType.MESSAGE_QUEUE, "TCP", "notifications")

    # 更新服务指标
    service_map.record_service_metrics("api-gateway", {
        "latency_p50_ms": 50,
        "latency_p99_ms": 150,
        "error_rate": 0.005,
        "requests_per_second": 1000,
        "cpu_percent": 45
    })

    service_map.record_service_metrics("user-service", {
        "latency_p50_ms": 30,
        "latency_p99_ms": 100,
        "error_rate": 0.002,
        "requests_per_second": 800,
        "cpu_percent": 35
    })

    service_map.record_service_metrics("order-service", {
        "latency_p50_ms": 100,
        "latency_p99_ms": 500,
        "error_rate": 0.015,
        "requests_per_second": 500,
        "cpu_percent": 65
    })

    service_map.record_service_metrics("payment-service", {
        "latency_p50_ms": 200,
        "latency_p99_ms": 800,
        "error_rate": 0.008,
        "requests_per_second": 300,
        "cpu_percent": 55
    })

    logger.info("Sample service map created")


# 初始化示例数据
create_sample_service_map()
