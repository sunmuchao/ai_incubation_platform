"""
知识图谱查询模块

提供高级查询功能：
1. 影响分析：修改某个节点会影响哪些节点
2. 调用链分析：完整调用路径追踪
3. 核心节点识别：基于图算法识别关键节点
4. 路径查询：两点间的依赖路径
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import logging

from .models import KGNode, KGEdge, NodeType, EdgeType
from .graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class KnowledgeGraphQuery:
    """
    知识图谱查询器

    提供丰富的查询方法，支持代码理解场景
    """

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    # ========== 影响分析 ==========

    def analyze_impact(self, node_id: str, include_indirect: bool = True) -> Dict[str, Any]:
        """
        分析节点变更的影响范围

        Args:
            node_id: 目标节点 ID
            include_indirect: 是否包含间接影响

        Returns:
            {
                "direct_impact": [受直接影响的节点],
                "indirect_impact": [受间接影响的节点],
                "impact_summary": {统计信息},
                "risk_level": "low|medium|high"
            }
        """
        node = self.graph.get_node(node_id)
        if not node:
            return {"error": f"节点不存在：{node_id}"}

        # 直接依赖该节点的节点
        direct_impact = set()
        for edge in self.graph.get_incoming_edges(node_id):
            direct_impact.add(edge.source)

        # 间接影响（递归）
        indirect_impact = set()
        if include_indirect:
            visited = set([node_id])
            queue = list(direct_impact)

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)

                # 查找依赖当前节点的节点
                for edge in self.graph.get_incoming_edges(current):
                    if edge.source not in direct_impact and edge.source not in indirect_impact:
                        indirect_impact.add(edge.source)
                        queue.append(edge.source)

        # 计算风险等级
        total_impact = len(direct_impact) + len(indirect_impact)
        if total_impact == 0:
            risk_level = "low"
        elif total_impact <= 5:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "node": node.to_dict(),
            "direct_impact": [self.graph.get_node(nid).to_dict() for nid in direct_impact if self.graph.get_node(nid)],
            "indirect_impact": [self.graph.get_node(nid).to_dict() for nid in indirect_impact if self.graph.get_node(nid)],
            "impact_summary": {
                "direct_count": len(direct_impact),
                "indirect_count": len(indirect_impact),
                "total_count": total_impact
            },
            "risk_level": risk_level
        }

    def get_change_impact(self, file_path: str) -> Dict[str, Any]:
        """
        分析文件变更的影响范围

        Args:
            file_path: 文件路径

        Returns:
            影响分析结果
        """
        # 获取文件中的所有节点
        file_nodes = self.graph.get_nodes_by_file(file_path)
        if not file_nodes:
            return {"error": f"文件中没有节点：{file_path}"}

        all_affected = set()
        impacted_by_type = defaultdict(list)

        for node in file_nodes:
            impact = self.analyze_impact(node.id)
            if "error" not in impact:
                for affected_node in impact.get("direct_impact", []):
                    all_affected.add(affected_node["id"])
                    node_type = affected_node.get("node_type", "unknown")
                    impacted_by_type[node_type].append(affected_node)

        return {
            "file_path": file_path,
            "nodes_in_file": len(file_nodes),
            "affected_nodes_count": len(all_affected),
            "affected_by_type": dict(impacted_by_type),
            "affected_files": list(set(
                self.graph.get_node(nid).file_path for nid in all_affected if self.graph.get_node(nid)
            ))
        }

    # ========== 调用链分析 ==========

    def get_call_chain(self, node_id: str, direction: str = "downstream",
                       max_depth: int = 10) -> Dict[str, Any]:
        """
        获取完整调用链

        Args:
            node_id: 起始节点 ID
            direction: "downstream" (调用谁), "upstream" (被谁调用)
            max_depth: 最大深度

        Returns:
            {
                "root": 节点信息，
                "chain": 调用链（分层结构）,
                "total_nodes": 涉及节点总数
            }
        """
        node = self.graph.get_node(node_id)
        if not node:
            return {"error": f"节点不存在：{node_id}"}

        chain = []
        visited = set()
        current_level = [node_id]
        depth = 0

        while current_level and depth < max_depth:
            level_nodes = []
            next_level = []

            for nid in current_level:
                if nid in visited:
                    continue
                visited.add(nid)

                node_info = self.graph.get_node(nid)
                if not node_info:
                    continue

                level_nodes.append(node_info.to_dict())

                # 获取下一层
                if direction == "downstream":
                    callees = self.graph.get_callees(nid, recursive=False)
                    next_level.extend(callees)
                else:
                    callers = self.graph.get_callers(nid, recursive=False)
                    next_level.extend(callers)

            if level_nodes:
                chain.append({
                    "depth": depth,
                    "nodes": level_nodes
                })

            current_level = next_level
            depth += 1

        return {
            "root": node.to_dict(),
            "direction": direction,
            "chain": chain,
            "total_nodes": len(visited),
            "max_depth_reached": depth
        }

    def find_call_paths(self, source_id: str, target_id: str,
                        max_paths: int = 5) -> List[Dict[str, Any]]:
        """
        查找两个节点之间的调用路径

        Args:
            source_id: 源节点 ID
            target_id: 目标节点 ID
            max_paths: 最大返回路径数
        """
        paths = self.graph.find_path(source_id, target_id)

        result = []
        for path in paths[:max_paths]:
            path_info = {
                "path": path,
                "length": len(path),
                "nodes": []
            }

            for nid in path:
                node = self.graph.get_node(nid)
                if node:
                    path_info["nodes"].append({
                        "id": node.id,
                        "name": node.display_name,
                        "type": node.node_type.value,
                        "file_path": node.file_path
                    })

            result.append(path_info)

        return result

    # ========== 核心节点识别 ==========

    def find_core_modules(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        查找核心模块（被依赖最多的模块）
        """
        return self.graph.get_core_nodes(top_n, by="in_degree")

    def find_hub_nodes(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        查找枢纽节点（连接最多的节点）
        """
        return self.graph.get_core_nodes(top_n, by="total_degree")

    def find_entry_points(self) -> List[Dict[str, Any]]:
        """
        查找入口点（只有入边没有出边的节点）
        """
        entry_points = []

        for node in self.graph:
            in_deg = self.graph.graph.in_degree(node.id) if node.id in self.graph.graph else 0
            out_deg = self.graph.graph.out_degree(node.id) if node.id in self.graph.graph else 0

            if in_deg > 0 and out_deg == 0:
                node_dict = node.to_dict()
                node_dict["in_degree"] = in_deg
                entry_points.append(node_dict)

        return sorted(entry_points, key=lambda x: x["in_degree"], reverse=True)[:20]

    # ========== 依赖分析 ==========

    def get_dependency_tree(self, node_id: str, max_depth: int = 5) -> Dict[str, Any]:
        """
        获取依赖树（该节点依赖什么）
        """
        node = self.graph.get_node(node_id)
        if not node:
            return {"error": f"节点不存在：{node_id}"}

        return {
            "root": node.to_dict(),
            "dependencies": self._build_dependency_tree(node_id, max_depth, set())
        }

    def _build_dependency_tree(self, node_id: str, max_depth: int,
                               visited: Set[str]) -> Optional[Dict[str, Any]]:
        """递归构建依赖树"""
        if node_id in visited or max_depth < 0:
            return None

        visited.add(node_id)
        node = self.graph.get_node(node_id)
        if not node:
            return None

        dependencies = self.graph.get_dependencies(node_id, recursive=False)

        children = []
        for dep_id in dependencies:
            child_tree = self._build_dependency_tree(dep_id, max_depth - 1, visited)
            if child_tree:
                children.append(child_tree)

        return {
            "node": node.to_dict(),
            "dependencies": children
        }

    def get_reverse_dependency_tree(self, node_id: str, max_depth: int = 5) -> Dict[str, Any]:
        """
        获取反向依赖树（谁依赖该节点）
        """
        node = self.graph.get_node(node_id)
        if not node:
            return {"error": f"节点不存在：{node_id}"}

        return {
            "root": node.to_dict(),
            "dependents": self._build_reverse_dependency_tree(node_id, max_depth, set())
        }

    def _build_reverse_dependency_tree(self, node_id: str, max_depth: int,
                                        visited: Set[str]) -> Optional[Dict[str, Any]]:
        """递归构建反向依赖树"""
        if node_id in visited or max_depth < 0:
            return None

        visited.add(node_id)
        node = self.graph.get_node(node_id)
        if not node:
            return None

        dependents = self.graph.get_dependents(node_id, recursive=False)

        children = []
        for dep_id in dependents:
            child_tree = self._build_reverse_dependency_tree(dep_id, max_depth - 1, visited)
            if child_tree:
                children.append(child_tree)

        return {
            "node": node.to_dict(),
            "dependents": children
        }

    # ========== 循环检测 ==========

    def find_cycles(self, node_type: Optional[NodeType] = None) -> List[Dict[str, Any]]:
        """
        检测循环依赖

        Args:
            node_type: 可选，只检测特定类型节点的循环
        """
        cycles = self.graph.detect_cycles()

        result = []
        for cycle in cycles[:20]:  # 限制返回数量
            cycle_info = {
                "length": len(cycle),
                "nodes": []
            }

            for nid in cycle:
                node = self.graph.get_node(nid)
                if node:
                    if node_type and node.node_type != node_type:
                        continue
                    cycle_info["nodes"].append({
                        "id": node.id,
                        "name": node.display_name,
                        "type": node.node_type.value,
                        "file_path": node.file_path
                    })

            if len(cycle_info["nodes"]) > 1:
                result.append(cycle_info)

        return result

    # ========== 搜索和浏览 ==========

    def search(self, query: str, node_type: Optional[NodeType] = None,
               fuzzy: bool = True) -> List[Dict[str, Any]]:
        """
        搜索节点

        Args:
            query: 搜索词
            node_type: 节点类型过滤
            fuzzy: 是否模糊匹配
        """
        results = self.graph.search_nodes(query, fuzzy=fuzzy)

        if node_type:
            results = [r for r in results if r.node_type == node_type]

        return [node.to_dict() for node in results[:50]]

    def get_file_overview(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件概览

        Returns:
            {
                "file_path": 文件路径，
                "nodes": [该文件中的节点],
                "internal_calls": [内部调用],
                "external_dependencies": [外部依赖],
                "dependents": [依赖该文件的节点]
            }
        """
        nodes = self.graph.get_nodes_by_file(file_path)
        if not nodes:
            return {"error": f"文件不存在：{file_path}"}

        node_ids = set(n.id for n in nodes)

        # 内部调用
        internal_calls = []
        external_deps = []
        dependents = []

        for node in nodes:
            #  outgoing edges
            for edge in self.graph.get_outgoing_edges(node.id):
                target = self.graph.get_node(edge.target)
                if not target:
                    continue

                if edge.edge_type == EdgeType.CALLS:
                    if target.file_path == file_path:
                        internal_calls.append({
                            "from": node.display_name,
                            "to": target.display_name,
                            "type": "call"
                        })
                    else:
                        external_deps.append({
                            "from": node.display_name,
                            "to": target.display_name,
                            "target_file": target.file_path,
                            "type": "external_call"
                        })

            # incoming edges (dependents)
            for edge in self.graph.get_incoming_edges(node.id):
                source = self.graph.get_node(edge.source)
                if source and source.file_path != file_path:
                    dependents.append({
                        "from": source.display_name,
                        "from_file": source.file_path,
                        "to": node.display_name,
                        "type": edge.edge_type.value
                    })

        return {
            "file_path": file_path,
            "nodes": [n.to_dict() for n in nodes],
            "node_count": len(nodes),
            "internal_calls": internal_calls[:20],
            "external_dependencies": external_deps[:20],
            "dependents": dependents[:20]
        }

    def get_symbol_info(self, symbol_name: str) -> Dict[str, Any]:
        """
        获取符号详细信息

        Returns:
            {
                "definitions": [定义位置],
                "references": [引用位置],
                "callers": [调用者],
                "callees": [被调用者]
            }
        """
        nodes = self.graph.find_nodes_by_symbol(symbol_name)

        if not nodes:
            return {"error": f"符号不存在：{symbol_name}"}

        result = {
            "symbol_name": symbol_name,
            "definitions": [],
            "references": [],
            "callers": [],
            "callees": []
        }

        for node in nodes:
            result["definitions"].append({
                "file_path": node.file_path,
                "line": node.start_line,
                "type": node.node_type.value,
                "node": node.to_dict()
            })

            # 查找引用
            for edge in self.graph.get_outgoing_edges(node.id):
                if edge.edge_type == EdgeType.REFERENCES:
                    result["references"].append({
                        "source_file": node.file_path,
                        "target": self.graph.get_node(edge.target).to_dict() if self.graph.get_node(edge.target) else None
                    })

            # 查找调用者
            callers = self.graph.get_callers(node.id)
            for caller_id in callers:
                caller = self.graph.get_node(caller_id)
                if caller:
                    result["callers"].append({
                        "name": caller.display_name,
                        "file_path": caller.file_path,
                        "node": caller.to_dict()
                    })

            # 查找被调用者
            callees = self.graph.get_callees(node.id)
            for callee_id in callees:
                callee = self.graph.get_node(callee_id)
                if callee:
                    result["callees"].append({
                        "name": callee.display_name,
                        "file_path": callee.file_path,
                        "node": callee.to_dict()
                    })

        return result

    # ========== 图谱统计 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        stats = self.graph.get_stats()
        return {
            "project_name": self.graph.project_name,
            **stats.to_dict()
        }

    def get_summary(self) -> Dict[str, Any]:
        """获取图谱摘要"""
        stats = self.get_stats()
        core_modules = self.find_core_modules(5)
        entry_points = self.find_entry_points()[:5]
        cycles = self.find_cycles()

        return {
            "overview": stats,
            "core_modules": core_modules,
            "entry_points": entry_points,
            "cycle_count": len(cycles),
            "has_cycles": len(cycles) > 0
        }
