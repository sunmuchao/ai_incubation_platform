"""
知识图谱模块 v2
支持 1000+ 节点的增强型图谱数据结构
为 AI 根因推理 v2 提供图谱基础设施
"""
import logging
from typing import Dict, List, Optional, Any, Tuple, Set, Iterator
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """节点类型"""
    SERVICE = "service"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    API_GATEWAY = "api_gateway"
    LOAD_BALANCER = "load_balancer"
    EXTERNAL_SERVICE = "external_service"
    STORAGE = "storage"
    CDN = "cdn"
    CONTAINER = "container"
    POD = "pod"
    HOST = "host"
    CLUSTER = "cluster"
    CONFIG = "config"  # 配置节点
    DEPLOYMENT = "deployment"  # 部署节点
    CHANGE_EVENT = "change_event"  # 变更事件节点
    ALERT = "alert"  # 告警节点
    METRIC = "metric"  # 指标节点


class EdgeType(str, Enum):
    """边类型"""
    # 服务依赖关系
    CALLS = "calls"  # 服务调用
    DEPENDS_ON = "depends_on"  # 依赖
    USES = "uses"  # 使用
    ROUTES_TO = "routes_to"  # 路由到
    HOSTS = "hosts"  # 托管
    CONTAINS = "contains"  # 包含
    BELONGS_TO = "belongs_to"  # 属于

    # 因果关系
    CAUSES = "causes"  # 导致
    TRIGGERS = "triggers"  # 触发
    CORRELATES_WITH = "correlates_with"  # 相关

    # 变更关系
    CHANGED_BY = "changed_by"  # 被...变更
    AFFECTS = "affects"  # 影响
    DEPLOYED_IN = "deployed_in"  # 部署于

    # 指标关系
    HAS_METRIC = "has_metric"  # 拥有指标
    IMPACTS_METRIC = "impacts_metric"  # 影响指标


class NodeHealth(str, Enum):
    """节点健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class MetricValue:
    """指标值"""
    metric_name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class KnowledgeNode:
    """知识图谱节点"""
    node_id: str
    node_type: NodeType
    name: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, MetricValue] = field(default_factory=dict)
    health: NodeHealth = NodeHealth.UNKNOWN
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # 运行时数据
    anomaly_score: float = 0.0
    is_root_cause: bool = False
    inference_score: float = 0.0
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "health": self.health.value,
            "tags": self.tags,
            "anomaly_score": self.anomaly_score,
            "is_root_cause": self.is_root_cause,
            "inference_score": self.inference_score,
            "evidence": self.evidence
        }

    def update_metric(self, metric_name: str, value: float, unit: str = ""):
        """更新指标值"""
        self.metrics[metric_name] = MetricValue(
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow()
        )
        self.updated_at = datetime.utcnow()

    def update_health(self):
        """基于指标更新健康状态"""
        error_rate = self.metrics.get("error_rate", MetricValue("", 0)).value
        latency = self.metrics.get("latency_p99_ms", MetricValue("", 0)).value
        cpu = self.metrics.get("cpu_percent", MetricValue("", 0)).value

        # 健康状态判断逻辑
        if error_rate > 0.5 or latency > 5000 or cpu > 95:
            self.health = NodeHealth.UNHEALTHY
        elif error_rate > 0.1 or latency > 1000 or cpu > 80:
            self.health = NodeHealth.DEGRADED
        elif error_rate > 0 or latency > 0 or cpu > 0:
            self.health = NodeHealth.HEALTHY
        else:
            self.health = NodeHealth.UNKNOWN


@dataclass
class KnowledgeEdge:
    """知识图谱边"""
    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    # 运行时数据
    propagation_score: float = 0.0
    latency_ms: Optional[float] = None
    error_rate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "metadata": self.metadata,
            "propagation_score": self.propagation_score,
            "latency_ms": self.latency_ms,
            "error_rate": self.error_rate
        }


@dataclass
class ChangeEvent:
    """变更事件"""
    event_id: str
    event_type: str  # deployment, config_change, scale, etc.
    service_id: str
    timestamp: datetime
    description: str = ""
    actor: str = ""  # 执行变更的人/系统
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_nodes: List[str] = field(default_factory=list)
    impact_score: float = 0.0  # 影响程度评分

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "service_id": self.service_id,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "actor": self.actor,
            "metadata": self.metadata,
            "related_nodes": self.related_nodes,
            "impact_score": self.impact_score
        }


class KnowledgeGraph:
    """
    增强型知识图谱

    功能:
    1. 支持 1000+ 节点的高效存储和查询
    2. 服务依赖图谱
    3. 指标关联图谱
    4. 变更事件图谱
    5. 高效的图遍历算法
    """

    def __init__(self, max_history_size: int = 10000):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[KnowledgeEdge] = []
        self.change_events: List[ChangeEvent] = []

        # 邻接表（支持高效遍历）
        self.adjacency_out: Dict[str, List[str]] = defaultdict(list)  # node_id -> [edge_ids]
        self.adjacency_in: Dict[str, List[str]] = defaultdict(list)   # node_id -> [edge_ids]

        # 索引
        self._type_index: Dict[NodeType, Set[str]] = defaultdict(set)  # type -> node_ids
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)        # tag -> node_ids
        self._name_index: Dict[str, Set[str]] = defaultdict(set)       # name -> node_ids

        # 边索引
        self._edge_by_type: Dict[EdgeType, List[str]] = defaultdict(list)

        # 历史
        self._change_history: deque = deque(maxlen=max_history_size)

        # 统计
        self._stats = {
            "total_nodes": 0,
            "total_edges": 0,
            "total_events": 0
        }

    # ==================== 节点操作 ====================

    def add_node(self, node: KnowledgeNode) -> str:
        """添加节点"""
        self.nodes[node.node_id] = node

        # 更新索引
        self._type_index[node.node_type].add(node.node_id)
        self._name_index[node.name].add(node.node_id)
        for tag in node.tags:
            self._tag_index[tag].add(node.node_id)

        self._stats["total_nodes"] = len(self.nodes)
        return node.node_id

    def remove_node(self, node_id: str) -> bool:
        """删除节点"""
        if node_id not in self.nodes:
            return False

        node = self.nodes[node_id]

        # 删除相关边
        self.remove_edges_by_node(node_id)

        # 删除节点
        del self.nodes[node_id]

        # 更新索引
        self._type_index[node.node_type].discard(node_id)
        self._name_index[node.name].discard(node_id)
        for tag in node.tags:
            self._tag_index[tag].discard(node_id)

        self._stats["total_nodes"] = len(self.nodes)
        return True

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """获取节点"""
        return self.nodes.get(node_id)

    def nodes_by_type(self, node_type: NodeType) -> List[KnowledgeNode]:
        """按类型获取节点"""
        node_ids = self._type_index.get(node_type, set())
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def nodes_by_tag(self, tag: str) -> List[KnowledgeNode]:
        """按标签获取节点"""
        node_ids = self._tag_index.get(tag, set())
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def search_nodes(self, query: str) -> List[KnowledgeNode]:
        """搜索节点（按名称）"""
        node_ids = self._name_index.get(query.lower(), set())
        results = [self.nodes[nid] for nid in node_ids if nid in self.nodes]

        # 如果没有精确匹配，进行模糊搜索
        if not results:
            query_lower = query.lower()
            results = [
                node for node in self.nodes.values()
                if query_lower in node.name.lower() or query_lower in node.description.lower()
            ]

        return results

    # ==================== 边操作 ====================

    def add_edge(self, edge: KnowledgeEdge) -> str:
        """添加边"""
        self.edges.append(edge)

        # 更新邻接表
        self.adjacency_out[edge.source_id].append(edge.edge_id)
        self.adjacency_in[edge.target_id].append(edge.edge_id)

        # 更新边类型索引
        self._edge_by_type[edge.edge_type].append(edge.edge_id)

        self._stats["total_edges"] = len(self.edges)
        return edge.edge_id

    def remove_edge(self, edge_id: str) -> bool:
        """删除边"""
        edge = next((e for e in self.edges if e.edge_id == edge_id), None)
        if not edge:
            return False

        # 从邻接表移除
        if edge.edge_id in self.adjacency_out[edge.source_id]:
            self.adjacency_out[edge.source_id].remove(edge.edge_id)
        if edge.edge_id in self.adjacency_in[edge.target_id]:
            self.adjacency_in[edge.target_id].remove(edge.edge_id)

        # 从类型索引移除
        if edge.edge_id in self._edge_by_type[edge.edge_type]:
            self._edge_by_type[edge.edge_type].remove(edge.edge_id)

        self.edges = [e for e in self.edges if e.edge_id != edge_id]
        self._stats["total_edges"] = len(self.edges)
        return True

    def remove_edges_by_node(self, node_id: str):
        """删除与节点相关的所有边"""
        # 删除出边
        edge_ids_to_remove = list(self.adjacency_out.get(node_id, []))
        for edge_id in edge_ids_to_remove:
            self.remove_edge(edge_id)

        # 删除入边
        edge_ids_to_remove = list(self.adjacency_in.get(node_id, []))
        for edge_id in edge_ids_to_remove:
            self.remove_edge(edge_id)

    def get_edges(self, source_id: str = None, target_id: str = None,
                  edge_type: EdgeType = None) -> List[KnowledgeEdge]:
        """获取边"""
        results = self.edges

        if source_id:
            edge_ids = self.adjacency_out.get(source_id, [])
            results = [e for e in results if e.edge_id in edge_ids]

        if target_id:
            edge_ids = self.adjacency_in.get(target_id, [])
            results = [e for e in results if e.edge_id in edge_ids]

        if edge_type:
            edge_ids = self._edge_by_type.get(edge_type, [])
            results = [e for e in results if e.edge_id in edge_ids]

        return results

    # ==================== 图遍历 ====================

    def get_neighbors(self, node_id: str, direction: str = "out") -> List[KnowledgeNode]:
        """获取邻居节点"""
        if direction == "out":
            edge_ids = self.adjacency_out.get(node_id, [])
            edge_ids = self.adjacency_out.get(node_id, [])
            neighbors = []
            for edge in self.edges:
                if edge.edge_id in edge_ids:
                    if edge.target_id in self.nodes:
                        neighbors.append(self.nodes[edge.target_id])
            return neighbors
        elif direction == "in":
            edge_ids = self.adjacency_in.get(node_id, [])
            neighbors = []
            for edge in self.edges:
                if edge.edge_id in edge_ids:
                    if edge.source_id in self.nodes:
                        neighbors.append(self.nodes[edge.source_id])
            return neighbors
        else:
            return list(set(self.get_neighbors(node_id, "out") + self.get_neighbors(node_id, "in")))

    def get_upstream(self, node_id: str) -> List[KnowledgeNode]:
        """获取上游节点（依赖我的节点）"""
        return self.get_neighbors(node_id, "in")

    def get_downstream(self, node_id: str) -> List[KnowledgeNode]:
        """获取下游节点（我依赖的节点）"""
        return self.get_neighbors(node_id, "out")

    def find_path(self, source_id: str, target_id: str,
                  max_depth: int = 10) -> List[List[str]]:
        """查找所有路径（BFS）"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return []

        paths = []
        queue = deque([(source_id, [source_id])])
        visited_at_depth: Dict[str, int] = {source_id: 0}

        while queue:
            current, path = queue.popleft()

            if current == target_id:
                paths.append(path)
                continue

            if len(path) >= max_depth:
                continue

            for neighbor in self.get_downstream(current):
                neighbor_depth = visited_at_depth.get(neighbor.node_id, float('inf'))
                if neighbor.node_id not in path or visited_at_depth.get(neighbor.node_id, float('inf')) > len(path) + 1:
                    new_path = path + [neighbor.node_id]
                    queue.append((neighbor.node_id, new_path))
                    visited_at_depth[neighbor.node_id] = len(new_path)

        return paths

    def find_all_paths_to(self, target_id: str, max_results: int = 100) -> List[List[str]]:
        """找到所有到目标节点的路径"""
        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            if len(paths) >= max_results:
                return

            if current == target_id:
                paths.append(path[:])
                return

            for neighbor in self.get_downstream(current):
                if neighbor.node_id not in visited:
                    visited.add(neighbor.node_id)
                    path.append(neighbor.node_id)
                    dfs(neighbor.node_id, path, visited)
                    path.pop()
                    visited.remove(neighbor.node_id)

        for start_node_id in self.nodes:
            if start_node_id != target_id:
                dfs(start_node_id, [start_node_id], {start_node_id})

        return paths

    def find_connected_components(self) -> List[Set[str]]:
        """查找连通分量"""
        visited = set()
        components = []

        for node_id in self.nodes:
            if node_id not in visited:
                component = set()
                queue = deque([node_id])

                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    component.add(current)

                    for neighbor in self.get_neighbors(current, "out"):
                        if neighbor.node_id not in visited:
                            queue.append(neighbor.node_id)

                    for neighbor in self.get_neighbors(current, "in"):
                        if neighbor.node_id not in visited:
                            queue.append(neighbor.node_id)

                components.append(component)

        return components

    # ==================== 变更事件 ====================

    def add_change_event(self, event: ChangeEvent):
        """添加变更事件"""
        self.change_events.append(event)

        # 创建变更事件节点
        event_node = KnowledgeNode(
            node_id=f"change_{event.event_id}",
            node_type=NodeType.CHANGE_EVENT,
            name=event.event_type,
            description=event.description,
            metadata=event.metadata,
            created_at=event.timestamp
        )
        self.add_node(event_node)

        # 连接到相关服务
        edge = KnowledgeEdge(
            edge_id=f"edge_{event.event_id}_{event.service_id}",
            source_id=event_node.node_id,
            target_id=event.service_id,
            edge_type=EdgeType.AFFECTS,
            weight=event.impact_score
        )
        self.add_edge(edge)

        self._stats["total_events"] = len(self.change_events)
        self._change_history.append(event)

    def get_recent_changes(self, hours: int = 24) -> List[ChangeEvent]:
        """获取最近的变更"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [e for e in self.change_events if e.timestamp > cutoff]

    def get_changes_affecting(self, node_id: str, hours: int = 24) -> List[ChangeEvent]:
        """获取影响特定节点的变更"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        changes = [e for e in self.change_events if e.timestamp > cutoff]

        # 检查变更是否影响该节点
        affected = []
        for change in changes:
            if change.service_id == node_id:
                affected.append(change)
            elif node_id in change.related_nodes:
                affected.append(change)
            else:
                # 检查图中是否有路径
                paths = self.find_path(change.service_id, node_id, max_depth=3)
                if paths:
                    affected.append(change)

        return affected

    # ==================== 指标关联 ====================

    def correlate_metrics(self, metric_name: str, threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """
        查找与指定指标相关的节点

        Returns:
            [(node_id, metric_name, correlation_score), ...]
        """
        results = []

        for node_id, node in self.nodes.items():
            if metric_name in node.metrics:
                value = node.metrics[metric_name].value
                # 简单相关性：基于值的异常程度
                correlation = min(1.0, value / 100) if metric_name in ["cpu_percent", "memory_percent", "error_rate"] else 0.5
                if correlation >= threshold:
                    results.append((node_id, metric_name, correlation))

        return sorted(results, key=lambda x: x[2], reverse=True)

    # ==================== 图谱分析 ====================

    def calculate_centrality(self) -> Dict[str, float]:
        """计算节点度中心性"""
        centrality = {}
        total_nodes = len(self.nodes)

        if total_nodes <= 1:
            return centrality

        for node_id in self.nodes:
            out_degree = len(self.adjacency_out.get(node_id, []))
            in_degree = len(self.adjacency_in.get(node_id, []))
            centrality[node_id] = (out_degree + in_degree) / (2 * (total_nodes - 1))

        return centrality

    def get_critical_nodes(self, top_k: int = 10) -> List[Tuple[str, float]]:
        """获取最关键的节点"""
        centrality = self.calculate_centrality()
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        node_types = {nt.value: len(nodes) for nt, nodes in self._type_index.items()}
        edge_types = {et.value: len(edges) for et, edges in self._edge_by_type.items()}

        return {
            **self._stats,
            "node_types": node_types,
            "edge_types": edge_types,
            "health_distribution": {
                h.value: sum(1 for n in self.nodes.values() if n.health == h)
                for h in NodeHealth
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """导出图谱数据"""
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "change_events": [event.to_dict() for event in self.change_events[-100:]],  # 最近 100 个
            "stats": self.get_stats()
        }

    def build_from_service_map(self, service_map_data: Dict[str, Any]) -> int:
        """从服务映射数据构建图谱"""
        added_count = 0

        # 添加服务节点
        services = service_map_data.get("services", [])
        for svc in services:
            node = KnowledgeNode(
                node_id=svc.get("id", str(uuid.uuid4())),
                node_type=NodeType(svc.get("type", "service")),
                name=svc.get("name", svc.get("id")),
                description=svc.get("description", ""),
                metadata=svc.get("metadata", {}),
                tags=svc.get("tags", []),
            )

            # 添加指标
            metrics = svc.get("metrics", {})
            for metric_name, value in metrics.items():
                node.update_metric(metric_name, value)

            node.update_health()
            self.add_node(node)
            added_count += 1

        # 添加依赖边
        edges = service_map_data.get("edges", [])
        for edge in edges:
            knowledge_edge = KnowledgeEdge(
                edge_id=f"edge_{edge.get('source')}_{edge.get('target')}",
                source_id=edge.get("source"),
                target_id=edge.get("target"),
                edge_type=EdgeType.CALLS,
                weight=edge.get("weight", 1.0),
                metadata={
                    "latency_ms": edge.get("latency_ms"),
                    "error_rate": edge.get("error_rate")
                },
                latency_ms=edge.get("latency_ms"),
                error_rate=edge.get("error_rate")
            )
            self.add_edge(knowledge_edge)

        logger.info(f"Built graph with {len(self.nodes)} nodes and {len(self.edges)} edges")
        return added_count


# ==================== 全局图谱实例 ====================

_knowledge_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """获取知识图谱实例"""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph


def reset_knowledge_graph():
    """重置知识图谱（用于测试）"""
    global _knowledge_graph
    _knowledge_graph = None
