"""
知识图谱核心数据结构

使用 NetworkX 作为底层图存储，支持复杂的图算法和查询
"""
from __future__ import annotations

import json
import networkx as nx
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Iterator
from collections import defaultdict
import logging

from .models import KGNode, KGEdge, NodeType, EdgeType, GraphStats

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """
    知识图谱核心类

    使用 NetworkX 作为底层存储，提供：
    1. 节点和边的增删查
    2. 图谱遍历和查询
    3. 路径分析
    4. 循环检测
    5. 核心节点识别
    6. 持久化存储
    """

    def __init__(self, project_name: str = "unknown"):
        self.project_name = project_name
        self.graph = nx.DiGraph()  # 有向图
        self._node_index: Dict[str, KGNode] = {}  # ID -> Node 映射
        self._edge_index: Dict[str, KGEdge] = {}  # ID -> Edge 映射
        self._file_to_nodes: Dict[str, Set[str]] = defaultdict(set)  # 文件 -> 节点 ID 映射
        self._symbol_index: Dict[str, Set[str]] = defaultdict(set)  # 符号名 -> 节点 ID 映射

    # ========== 节点操作 ==========

    def add_node(self, node: KGNode) -> None:
        """添加节点"""
        if node.id in self._node_index:
            # 更新现有节点
            self._node_index[node.id] = node
        else:
            self._node_index[node.id] = node
            self._file_to_nodes[node.file_path].add(node.id)
            if node.symbol_name:
                self._symbol_index[node.symbol_name].add(node.id)

        # 添加到 NetworkX 图
        self.graph.add_node(node.id, **node.to_dict())

    def get_node(self, node_id: str) -> Optional[KGNode]:
        """获取节点"""
        return self._node_index.get(node_id)

    def remove_node(self, node_id: str) -> None:
        """移除节点"""
        if node_id not in self._node_index:
            return

        node = self._node_index[node_id]
        self._file_to_nodes[node.file_path].discard(node_id)
        if node.symbol_name:
            self._symbol_index[node.symbol_name].discard(node_id)

        del self._node_index[node_id]
        if node_id in self.graph:
            self.graph.remove_node(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[KGNode]:
        """按类型获取节点"""
        return [n for n in self._node_index.values() if n.node_type == node_type]

    def get_nodes_by_file(self, file_path: str) -> List[KGNode]:
        """获取文件中的所有节点"""
        node_ids = self._file_to_nodes.get(file_path, set())
        return [self._node_index[nid] for nid in node_ids if nid in self._node_index]

    def find_nodes_by_symbol(self, symbol_name: str) -> List[KGNode]:
        """按符号名称查找节点"""
        node_ids = self._symbol_index.get(symbol_name, set())
        return [self._node_index[nid] for nid in node_ids if nid in self._node_index]

    def search_nodes(self, query: str, fuzzy: bool = False) -> List[KGNode]:
        """
        搜索节点

        Args:
            query: 搜索词
            fuzzy: 是否模糊匹配
        """
        results = []
        query_lower = query.lower()

        for node in self._node_index.values():
            matched = False

            # 精确匹配
            if not fuzzy:
                if query in node.name or query == node.symbol_name:
                    matched = True
            else:
                # 模糊匹配
                if query_lower in node.name.lower():
                    matched = True
                if node.symbol_name and query_lower in node.symbol_name.lower():
                    matched = True
                if node.file_path and query_lower in node.file_path.lower():
                    matched = True

            if matched:
                results.append(node)

        return results

    # ========== 边操作 ==========

    def add_edge(self, edge: KGEdge) -> None:
        """添加边"""
        if edge.id in self._edge_index:
            return  # 边已存在

        self._edge_index[edge.id] = edge
        self.graph.add_edge(edge.source, edge.target, **edge.to_dict())

    def get_edge(self, edge_id: str) -> Optional[KGEdge]:
        """获取边"""
        return self._edge_index.get(edge_id)

    def remove_edge(self, edge_id: str) -> None:
        """移除边"""
        if edge_id not in self._edge_index:
            return

        edge = self._edge_index[edge_id]
        del self._edge_index[edge_id]

        if self.graph.has_edge(edge.source, edge.target):
            self.graph.remove_edge(edge.source, edge.target)

    def get_edges(self, source_id: Optional[str] = None, target_id: Optional[str] = None,
                  edge_type: Optional[EdgeType] = None) -> List[KGEdge]:
        """
        获取边列表

        Args:
            source_id: 源节点 ID 过滤
            target_id: 目标节点 ID 过滤
            edge_type: 边类型过滤
        """
        results = []

        for edge in self._edge_index.values():
            if source_id and edge.source != source_id:
                continue
            if target_id and edge.target != target_id:
                continue
            if edge_type and edge.edge_type != edge_type:
                continue
            results.append(edge)

        return results

    def get_outgoing_edges(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[KGEdge]:
        """获取节点的出边"""
        return self.get_edges(source_id=node_id, edge_type=edge_type)

    def get_incoming_edges(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[KGEdge]:
        """获取节点的入边"""
        return self.get_edges(target_id=node_id, edge_type=edge_type)

    # ========== 图谱查询 ==========

    def get_neighbors(self, node_id: str, direction: str = "both",
                      edge_type: Optional[EdgeType] = None) -> List[KGNode]:
        """
        获取邻居节点

        Args:
            node_id: 节点 ID
            direction: "out" (出边), "in" (入边), "both" (双向)
            edge_type: 边类型过滤
        """
        neighbors = set()

        if direction in ["out", "both"]:
            for edge in self.get_outgoing_edges(node_id, edge_type):
                if edge.target in self._node_index:
                    neighbors.add(edge.target)

        if direction in ["in", "both"]:
            for edge in self.get_incoming_edges(node_id, edge_type):
                if edge.source in self._node_index:
                    neighbors.add(edge.source)

        return [self._node_index[nid] for nid in neighbors]

    def find_path(self, source_id: str, target_id: str,
                  max_depth: int = 10) -> List[List[str]]:
        """
        查找两个节点之间的路径

        Returns:
            路径列表，每个路径是节点 ID 列表
        """
        if source_id not in self.graph or target_id not in self.graph:
            return []

        try:
            # 使用 NetworkX 的最短路径算法
            path = nx.shortest_path(
                self.graph,
                source=source_id,
                target=target_id,
                cutoff=max_depth
            )
            return [path]
        except nx.NetworkXNoPath:
            return []
        except Exception as e:
            logger.debug(f"查找路径失败：{e}")
            return []

    def get_callers(self, node_id: str, recursive: bool = False, max_depth: int = 5) -> Set[str]:
        """
        获取调用该节点的所有节点

        Args:
            node_id: 目标节点 ID
            recursive: 是否递归查找
            max_depth: 最大深度（递归时使用）
        """
        callers = set()

        # 查找直接调用者
        for edge in self.get_incoming_edges(node_id, EdgeType.CALLS):
            callers.add(edge.source)

        if recursive:
            # 递归查找
            for caller_id in list(callers):
                if max_depth > 0:
                    indirect_callers = self.get_callers(caller_id, recursive=True, max_depth=max_depth - 1)
                    callers.update(indirect_callers)

        return callers

    def get_callees(self, node_id: str, recursive: bool = False, max_depth: int = 5) -> Set[str]:
        """
        获取该节点调用的所有节点

        Args:
            node_id: 目标节点 ID
            recursive: 是否递归查找
            max_depth: 最大深度（递归时使用）
        """
        callees = set()

        # 查找直接调用
        for edge in self.get_outgoing_edges(node_id, EdgeType.CALLS):
            callees.add(edge.target)

        if recursive:
            # 递归查找
            for callee_id in list(callees):
                if max_depth > 0:
                    indirect_callees = self.get_callees(callee_id, recursive=True, max_depth=max_depth - 1)
                    callees.update(indirect_callees)

        return callees

    def get_dependents(self, node_id: str, recursive: bool = True) -> Set[str]:
        """
        获取依赖该节点的所有节点（反向依赖）

        用于影响分析：修改这个节点会影响谁
        """
        dependents = set()
        visited = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # 查找所有指向当前节点的边
            for edge in self.get_incoming_edges(current):
                if edge.source not in visited:
                    dependents.add(edge.source)
                    if recursive:
                        queue.append(edge.source)

        return dependents

    def get_dependencies(self, node_id: str, recursive: bool = True) -> Set[str]:
        """
        获取该节点依赖的所有节点
        """
        dependencies = set()
        visited = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # 查找所有从当前节点出发的边
            for edge in self.get_outgoing_edges(current):
                if edge.target not in visited:
                    dependencies.add(edge.target)
                    if recursive:
                        queue.append(edge.target)

        return dependencies

    # ========== 图谱分析 ==========

    def detect_cycles(self) -> List[List[str]]:
        """检测图中的循环"""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles[:100]  # 限制返回数量
        except Exception as e:
            logger.debug(f"检测循环失败：{e}")
            return []

    def get_core_nodes(self, top_n: int = 10, by: str = "in_degree") -> List[Dict[str, Any]]:
        """
        获取核心节点

        Args:
            top_n: 返回数量
            by: 排序依据 ("in_degree" - 被依赖最多，"out_degree" - 依赖最多)
        """
        nodes_with_degree = []

        for node_id, node in self._node_index.items():
            in_deg = self.graph.in_degree(node_id) if node_id in self.graph else 0
            out_deg = self.graph.out_degree(node_id) if node_id in self.graph else 0

            nodes_with_degree.append({
                "node": node,
                "in_degree": in_deg,
                "out_degree": out_deg,
                "total_degree": in_deg + out_deg
            })

        if by == "in_degree":
            nodes_with_degree.sort(key=lambda x: x["in_degree"], reverse=True)
        elif by == "out_degree":
            nodes_with_degree.sort(key=lambda x: x["out_degree"], reverse=True)
        else:
            nodes_with_degree.sort(key=lambda x: x["total_degree"], reverse=True)

        result = []
        for item in nodes_with_degree[:top_n]:
            node_dict = item["node"].to_dict()
            node_dict["in_degree"] = item["in_degree"]
            node_dict["out_degree"] = item["out_degree"]
            result.append(node_dict)

        return result

    def get_stats(self) -> GraphStats:
        """获取图谱统计信息"""
        stats = GraphStats()
        stats.total_nodes = len(self._node_index)
        stats.total_edges = len(self._edge_index)

        # 按类型统计节点
        for node in self._node_index.values():
            node_type = node.node_type.value
            stats.nodes_by_type[node_type] = stats.nodes_by_type.get(node_type, 0) + 1

        # 按类型统计边
        for edge in self._edge_index.values():
            edge_type = edge.edge_type.value
            stats.edges_by_type[edge_type] = stats.edges_by_type.get(edge_type, 0) + 1

        # 计算度数统计
        if self.graph.number_of_nodes() > 0:
            degrees = [self.graph.degree(n) for n in self.graph.nodes()]
            in_degrees = [self.graph.in_degree(n) for n in self.graph.nodes()]
            out_degrees = [self.graph.out_degree(n) for n in self.graph.nodes()]

            stats.max_in_degree = max(in_degrees) if in_degrees else 0
            stats.max_out_degree = max(out_degrees) if out_degrees else 0
            stats.avg_in_degree = sum(in_degrees) / len(in_degrees) if in_degrees else 0
            stats.avg_out_degree = sum(out_degrees) / len(out_degrees) if out_degrees else 0

        # 循环检测
        stats.cycle_count = len(self.detect_cycles())

        # 连通分量
        try:
            stats.connected_components = nx.number_weakly_connected_components(self.graph)
        except:
            stats.connected_components = 1

        return stats

    # ========== 持久化 ==========

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "project_name": self.project_name,
            "nodes": [node.to_dict() for node in self._node_index.values()],
            "edges": [edge.to_dict() for edge in self._edge_index.values()],
            "stats": self.get_stats().to_dict()
        }

    def to_json(self, indent: int = 2) -> str:
        """导出为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, file_path: str) -> None:
        """保存到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, file_path: str) -> "KnowledgeGraph":
        """从文件加载"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        graph = cls(project_name=data.get("project_name", "unknown"))

        # 加载节点
        for node_data in data.get("nodes", []):
            node = KGNode.from_dict(node_data)
            graph.add_node(node)

        # 加载边
        for edge_data in data.get("edges", []):
            edge = KGEdge.from_dict(edge_data)
            graph.add_edge(edge)

        return graph

    def clear(self) -> None:
        """清空图谱"""
        self.graph.clear()
        self._node_index.clear()
        self._edge_index.clear()
        self._file_to_nodes.clear()
        self._symbol_index.clear()

    def __len__(self) -> int:
        """返回节点数量"""
        return len(self._node_index)

    def __iter__(self) -> Iterator[KGNode]:
        """遍历所有节点"""
        return iter(self._node_index.values())
