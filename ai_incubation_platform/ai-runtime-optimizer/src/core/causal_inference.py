"""
因果推断根因分析引擎 v2.2
基于 Pearl 因果推断理论和贝叶斯网络的根因定位系统

核心功能：
1. 因果图构建（DAG - 有向无环图）
2. 贝叶斯因果推断
3. 反事实推理
4. 因果效应量化
5. 多根因排序
"""
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


class CausalMarkovCondition:
    """马尔可夫条件：给定父节点，节点条件独立于所有非后代节点"""

    @staticmethod
    def d_separation(graph: 'CausalGraph', x: str, y: str, z: Set[str]) -> bool:
        """
        判断 X 和 Y 在给定 Z 条件下是否 d-分离

        d-分离准则：
        1. 链式结构 A -> B -> C：给定 B 时，A 和 C 分离
        2. 分支结构 A <- B -> C：给定 B 时，A 和 C 分离
        3. 对撞结构 A -> B <- C：给定 B 或其子孙时，A 和 C 不分离
        """
        # 使用贝叶斯球算法判断 d-分离
        return CausalMarkovCondition._bayes_ball(graph, x, y, z)

    @staticmethod
    def _bayes_ball(graph: 'CausalGraph', x: str, y: str, z: Set[str]) -> bool:
        """贝叶斯球算法判断 d-分离"""
        # 简化实现：基于路径阻断判断
        paths = graph.get_all_paths(x, y)

        for path in paths:
            if not CausalMarkovCondition._is_path_blocked(graph, path, z):
                return False  # 存在未阻断的路径，不分离

        return True  # 所有路径都被阻断，d-分离

    @staticmethod
    def _is_path_blocked(graph: 'CausalGraph', path: List[str], z: Set[str]) -> bool:
        """判断路径是否被阻断"""
        for i in range(1, len(path) - 1):
            prev_node = path[i - 1]
            current = path[i]
            next_node = path[i + 1]

            # 获取边的方向
            prev_to_curr = graph.has_edge(prev_node, current)
            curr_to_prev = graph.has_edge(current, prev_node)
            curr_to_next = graph.has_edge(current, next_node)
            next_to_curr = graph.has_edge(next_node, current)

            # 链式结构：-> current ->
            if prev_to_curr and curr_to_next:
                if current in z:
                    return True  # 路径被阻断

            # 分支结构：<- current ->
            elif curr_to_prev and curr_to_next:
                if current in z:
                    return True  # 路径被阻断

            # 对撞结构：-> current <-
            elif prev_to_curr and next_to_curr:
                # 对撞点只有在给定其子孙时才开放
                if CausalMarkovCondition._has_descendant_in_z(graph, current, z):
                    continue  # 路径开放
                return True  # 路径被阻断

        return False

    @staticmethod
    def _has_descendant_in_z(graph: 'CausalGraph', node: str, z: Set[str]) -> bool:
        """检查节点是否有子孙在条件集 Z 中"""
        if node in z:
            return True

        descendants = graph.get_descendants(node)
        return bool(descendants & z)


@dataclass
class CausalNode:
    """因果图节点"""
    id: str
    name: str
    node_type: str  # service, database, cache, etc.

    # 因果属性
    parents: Set[str] = field(default_factory=set)
    children: Set[str] = field(default_factory=set)

    # 状态概率分布（离散化）
    states: List[str] = field(default_factory=lambda: ["normal", "degraded", "failed"])
    prior_prob: Dict[str, float] = field(default_factory=dict)
    cpt: Dict[Tuple[str, ...], Dict[str, float]] = field(default_factory=dict)  # 条件概率表

    # 运行时指标
    current_state: str = "normal"
    anomaly_score: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type,
            "parents": list(self.parents),
            "children": list(self.children),
            "states": self.states,
            "prior_prob": self.prior_prob,
            "current_state": self.current_state,
            "anomaly_score": self.anomaly_score,
            "metrics": self.metrics
        }


@dataclass
class CausalEdge:
    """因果图边"""
    source: str
    target: str
    edge_type: str  # calls, depends_on, uses
    causal_strength: float = 1.0  # 因果强度 [0, 1]
    propagation_delay_ms: float = 0.0  # 传播延迟

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "causal_strength": self.causal_strength,
            "propagation_delay_ms": self.propagation_delay_ms
        }


@dataclass
class CausalPath:
    """因果路径"""
    path: List[str]
    total_causal_effect: float
    propagation_type: str  # direct, indirect, confounded
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "total_causal_effect": self.total_causal_effect,
            "propagation_type": self.propagation_type,
            "confidence": self.confidence
        }


@dataclass
class RootCauseHypothesis:
    """根因假设"""
    hypothesis_id: str
    candidate_service: str
    root_cause_type: str

    # 贝叶斯推断结果
    prior_probability: float  # 先验概率
    posterior_probability: float  # 后验概率
    likelihood: float  # 似然度

    # 因果效应
    total_effect: float  # 总因果效应
    direct_effect: float  # 直接因果效应
    indirect_effect: float  # 间接因果效应

    # 置信度评分
    confidence_score: float
    confidence_factors: Dict[str, float] = field(default_factory=dict)

    # 证据
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    # 反事实分析
    counterfactual: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "candidate_service": self.candidate_service,
            "root_cause_type": self.root_cause_type,
            "prior_probability": self.prior_probability,
            "posterior_probability": self.posterior_probability,
            "likelihood": self.likelihood,
            "total_effect": self.total_effect,
            "direct_effect": self.direct_effect,
            "indirect_effect": self.indirect_effect,
            "confidence_score": self.confidence_score,
            "confidence_factors": self.confidence_factors,
            "evidence": self.evidence,
            "counterfactual": self.counterfactual
        }


class CausalGraph:
    """
    因果图（DAG - 有向无环图）

    基于服务依赖关系构建因果结构，支持：
    1. 因果发现
    2. d-分离判断
    3. 因果效应计算
    4. 反事实推理
    """

    def __init__(self):
        self._nodes: Dict[str, CausalNode] = {}
        self._edges: Dict[str, CausalEdge] = {}
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: CausalNode):
        """添加因果节点"""
        self._nodes[node.id] = node
        logger.debug(f"Added causal node: {node.id}")

    def add_edge(self, edge: CausalEdge):
        """添加因果边"""
        if edge.source not in self._nodes or edge.target not in self._nodes:
            raise ValueError(f"Edge endpoints must exist in graph")

        edge_id = f"{edge.source}->{edge.target}"
        self._edges[edge_id] = edge
        self._adjacency[edge.source].add(edge.target)
        self._reverse_adjacency[edge.target].add(edge.source)

        # 更新节点的父子关系
        self._nodes[edge.source].children.add(edge.target)
        self._nodes[edge.target].parents.add(edge.source)

        logger.debug(f"Added causal edge: {edge.source} -> {edge.target}")

    def has_edge(self, source: str, target: str) -> bool:
        """检查是否存在边"""
        edge_id = f"{source}->{target}"
        return edge_id in self._edges

    def get_node(self, node_id: str) -> Optional[CausalNode]:
        """获取节点"""
        return self._nodes.get(node_id)

    def get_edge(self, source: str, target: str) -> Optional[CausalEdge]:
        """获取边"""
        edge_id = f"{source}->{target}"
        return self._edges.get(edge_id)

    def get_parents(self, node_id: str) -> Set[str]:
        """获取父节点（直接原因）"""
        return self._reverse_adjacency.get(node_id, set())

    def get_children(self, node_id: str) -> Set[str]:
        """获取子节点（直接影响）"""
        return self._adjacency.get(node_id, set())

    def get_ancestors(self, node_id: str) -> Set[str]:
        """获取祖先节点（所有上游原因）"""
        ancestors = set()
        to_visit = list(self.get_parents(node_id))

        while to_visit:
            current = to_visit.pop(0)
            if current not in ancestors:
                ancestors.add(current)
                to_visit.extend(self.get_parents(current))

        return ancestors

    def get_descendants(self, node_id: str) -> Set[str]:
        """获取子孙节点（所有下游影响）"""
        descendants = set()
        to_visit = list(self.get_children(node_id))

        while to_visit:
            current = to_visit.pop(0)
            if current not in descendants:
                descendants.add(current)
                to_visit.extend(self.get_children(current))

        return descendants

    def get_all_paths(self, source: str, target: str, max_depth: int = 10) -> List[List[str]]:
        """获取所有从 source 到 target 的路径"""
        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            if len(path) > max_depth:
                return

            if current == target:
                paths.append(path[:])
                return

            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, path, visited)
                    path.pop()
                    visited.remove(neighbor)

        if source in self._nodes and target in self._nodes:
            dfs(source, [source], {source})

        return paths

    def is_dag(self) -> bool:
        """检查是否为有向无环图"""
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for child in self._adjacency.get(node, set()):
                if child not in visited:
                    if has_cycle(child):
                        return True
                elif child in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self._nodes:
            if node not in visited:
                if has_cycle(node):
                    return False

        return True

    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        if not self.is_dag():
            raise ValueError("Graph is not a DAG")

        in_degree = {node: len(self._reverse_adjacency.get(node, set()))
                     for node in self._nodes}

        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for child in self._adjacency.get(current, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return result

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "edges": [edge.to_dict() for edge in self._edges.values()],
            "num_nodes": len(self._nodes),
            "num_edges": len(self._edges),
            "is_dag": self.is_dag()
        }


class BayesianCausalInference:
    """
    贝叶斯因果推断引擎

    使用贝叶斯网络进行因果推断：
    1. 计算先验概率 P(X)
    2. 计算似然度 P(E|X)
    3. 计算后验概率 P(X|E) ∝ P(E|X) * P(X)
    4. 计算因果效应
    """

    def __init__(self, causal_graph: CausalGraph):
        self.graph = causal_graph
        self._intervention_history: List[Dict[str, Any]] = []

    def compute_prior_probability(self, node_id: str, state: str = "failed") -> float:
        """
        计算先验概率 P(X = state)

        基于节点的历史异常频率和当前状态
        """
        node = self.graph.get_node(node_id)
        if not node:
            return 0.0

        # 如果有先验概率定义，直接使用
        if state in node.prior_prob:
            return node.prior_prob[state]

        # 否则基于异常评分计算
        # 异常评分越高，故障先验概率越高
        anomaly_score = node.anomaly_score
        prior = anomaly_score  # 简化：直接用异常评分作为先验

        return min(1.0, prior)

    def compute_likelihood(self, node_id: str, evidence: Dict[str, Any]) -> float:
        """
        计算似然度 P(E|X)

        给定节点故障的条件下，观察到当前证据的概率
        """
        node = self.graph.get_node(node_id)
        if not node:
            return 0.0

        likelihood = 1.0

        # 基于子节点状态计算似然度
        for child_id in node.children:
            child = self.graph.get_node(child_id)
            if child and child.anomaly_score > 0.5:
                # 子节点异常，支持父节点故障的假设
                likelihood *= (0.5 + child.anomaly_score * 0.5)
            else:
                likelihood *= 0.5  # 中性

        # 基于指标证据
        if "error_rate" in evidence:
            if evidence["error_rate"] > 0.1:
                likelihood *= 1.5
            else:
                likelihood *= 0.8

        if "latency_p99_ms" in evidence:
            if evidence["latency_p99_ms"] > 1000:
                likelihood *= 1.3
            else:
                likelihood *= 0.9

        return min(1.0, likelihood)

    def compute_posterior_probability(
        self,
        node_id: str,
        evidence: Dict[str, Any]
    ) -> Tuple[float, float, float]:
        """
        计算后验概率 P(X|E)

        使用贝叶斯定理：P(X|E) = P(E|X) * P(X) / P(E)

        Returns:
            (posterior, likelihood, prior) 后验概率、似然度、先验概率
        """
        # 计算先验 P(X)
        prior = self.compute_prior_probability(node_id, "failed")

        # 计算似然度 P(E|X)
        likelihood = self.compute_likelihood(node_id, evidence)

        # 计算边际概率 P(E) - 使用全概率公式
        # P(E) = P(E|X)P(X) + P(E|¬X)P(¬X)
        # 创建反事实证据（将数值型证据减半）
        counterfactual_evidence = {}
        for k, v in evidence.items():
            if isinstance(v, (int, float)):
                counterfactual_evidence[k] = v * 0.5
            else:
                counterfactual_evidence[k] = v
        likelihood_not_x = self.compute_likelihood(node_id, counterfactual_evidence)
        prior_not_x = 1.0 - prior

        marginal_evidence = likelihood * prior + likelihood_not_x * prior_not_x

        # 避免除零
        if marginal_evidence < 1e-10:
            marginal_evidence = 1e-10

        # 后验概率
        posterior = (likelihood * prior) / marginal_evidence

        return min(1.0, posterior), likelihood, prior

    def compute_causal_effect(
        self,
        cause_node: str,
        effect_node: str,
        intervention_value: str = "failed"
    ) -> Tuple[float, float, float]:
        """
        计算因果效应 P(Y | do(X = intervention_value))

        使用 do-演算计算干预效应：
        - 总因果效应 (Total Effect)
        - 直接因果效应 (Direct Effect)
        - 间接因果效应 (Indirect Effect)

        Returns:
            (total_effect, direct_effect, indirect_effect)
        """
        # 检查是否存在因果路径
        paths = self.graph.get_all_paths(cause_node, effect_node)

        if not paths:
            return 0.0, 0.0, 0.0

        cause = self.graph.get_node(cause_node)
        effect = self.graph.get_node(effect_node)

        if not cause or not effect:
            return 0.0, 0.0, 0.0

        # 计算总因果效应
        # TE = P(Y | do(X=1)) - P(Y | do(X=0))
        p_y_do_x1 = self._compute_intervention_probability(effect_node, cause_node, "failed")
        p_y_do_x0 = self._compute_intervention_probability(effect_node, cause_node, "normal")

        total_effect = p_y_do_x1 - p_y_do_x0

        # 计算直接因果效应（通过直接边）
        direct_effect = 0.0
        if self.graph.has_edge(cause_node, effect_node):
            edge = self.graph.get_edge(cause_node, effect_node)
            direct_effect = edge.causal_strength * total_effect

        # 计算间接因果效应
        indirect_effect = total_effect - direct_effect

        return total_effect, direct_effect, indirect_effect

    def _compute_intervention_probability(
        self,
        target_node: str,
        intervention_node: str,
        intervention_value: str
    ) -> float:
        """
        计算干预概率 P(Y | do(X = value))

        使用截断因子分解公式：
        P(Y | do(X=x)) = Σ_{Z} P(Y | X=x, Z) P(Z)
        其中 Z 是 X 的父节点
        """
        target = self.graph.get_node(target_node)
        if not target:
            return 0.0

        # 简化实现：基于传播概率计算
        paths = self.graph.get_all_paths(intervention_node, target_node)

        if not paths:
            return 0.0

        # 累积路径传播概率
        total_prob = 0.0
        for path in paths:
            path_prob = 1.0
            for i in range(len(path) - 1):
                edge = self.graph.get_edge(path[i], path[i+1])
                if edge:
                    path_prob *= edge.causal_strength

            # 干预值影响
            if intervention_value == "failed":
                path_prob *= 1.0  # 故障状态完全传播
            else:
                path_prob *= 0.1  # 正常状态部分传播

            total_prob += path_prob

        # 归一化
        return min(1.0, total_prob / len(paths))

    def compute_counterfactual(
        self,
        hypothesis: RootCauseHypothesis,
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算反事实："如果 X 没有发生，Y 会怎样？"

        使用结构因果模型 (SCM) 的三步骤：
        1. 吸收：基于证据更新模型
        2. 行动：执行反事实干预 do(X = ¬x)
        3. 预测：计算结果

        Returns:
            反事实分析结果
        """
        node_id = hypothesis.candidate_service

        # 1. 吸收：计算后验
        posterior, likelihood, prior = self.compute_posterior_probability(node_id, evidence)

        # 2. 行动：反事实干预（假设节点正常）
        counterfactual_outcomes = {}

        for child_id in self.graph.get_children(node_id):
            # 计算在反事实世界中的子节点状态
            cf_effect, _, _ = self.compute_causal_effect(
                node_id, child_id, intervention_value="normal"
            )

            child = self.graph.get_node(child_id)
            if child:
                # 估计反事实下的异常评分
                cf_anomaly_score = max(0, child.anomaly_score - cf_effect)
                counterfactual_outcomes[child_id] = {
                    "original_anomaly_score": child.anomaly_score,
                    "counterfactual_anomaly_score": cf_anomaly_score,
                    "anomaly_reduction": child.anomaly_score - cf_anomaly_score,
                    "would_be_normal": cf_anomaly_score < 0.3
                }

        # 3. 预测：总体影响
        total_anomaly_reduction = sum(
            outcome["anomaly_reduction"]
            for outcome in counterfactual_outcomes.values()
        )

        num_would_be_normal = sum(
            1 for outcome in counterfactual_outcomes.values()
            if outcome["would_be_normal"]
        )

        return {
            "intervention": f"do({node_id} = normal)",
            "counterfactual_outcomes": counterfactual_outcomes,
            "total_anomaly_reduction": total_anomaly_reduction,
            "services_would_be_normal": num_would_be_normal,
            "total_affected_services": len(counterfactual_outcomes)
        }

    def record_intervention(self, intervention_result: Dict[str, Any]):
        """记录干预历史"""
        self._intervention_history.append({
            "timestamp": datetime.utcnow(),
            **intervention_result
        })

        # 保留最近 100 条记录
        if len(self._intervention_history) > 100:
            self._intervention_history = self._intervention_history[-100:]


class ConfidenceScorer:
    """
    置信度评分系统

    多维度评估根因假设的可信度：
    1. 统计置信度（贝叶斯后验概率）
    2. 因果置信度（因果效应强度）
    3. 时间置信度（时间先后顺序）
    4. 结构置信度（拓扑位置）
    5. 一致性置信度（多源证据一致）
    """

    def __init__(self):
        # 各维度权重
        self.weights = {
            "statistical": 0.25,    # 统计置信度
            "causal": 0.25,         # 因果置信度
            "temporal": 0.15,       # 时间置信度
            "structural": 0.20,     # 结构置信度
            "consistency": 0.15     # 一致性置信度
        }

    def compute_confidence(
        self,
        hypothesis: RootCauseHypothesis,
        causal_graph: CausalGraph,
        evidence: Dict[str, Any],
        anomaly_times: Dict[str, datetime]
    ) -> Tuple[float, Dict[str, float]]:
        """
        计算综合置信度

        Returns:
            (confidence_score, confidence_factors)
        """
        factors = {}

        # 1. 统计置信度（基于后验概率）
        factors["statistical"] = hypothesis.posterior_probability

        # 2. 因果置信度（基于因果效应）
        causal_confidence = min(1.0, hypothesis.total_effect)
        factors["causal"] = causal_confidence

        # 3. 时间置信度（原因先于结果）
        factors["temporal"] = self._compute_temporal_confidence(
            hypothesis.candidate_service,
            causal_graph,
            anomaly_times
        )

        # 4. 结构置信度（基于拓扑位置）
        factors["structural"] = self._compute_structural_confidence(
            hypothesis.candidate_service,
            causal_graph
        )

        # 5. 一致性置信度（多源证据一致）
        factors["consistency"] = self._compute_consistency_confidence(
            hypothesis.evidence
        )

        # 计算加权综合置信度
        confidence_score = sum(
            factors[dim] * self.weights[dim]
            for dim in self.weights
        )

        return confidence_score, factors

    def _compute_temporal_confidence(
        self,
        node_id: str,
        causal_graph: CausalGraph,
        anomaly_times: Dict[str, datetime]
    ) -> float:
        """
        计算时间置信度

        原则：根因应该先于其影响出现
        """
        if node_id not in anomaly_times:
            return 0.5  # 无时间信息

        node_time = anomaly_times[node_id]
        descendants = causal_graph.get_descendants(node_id)

        if not descendants:
            return 0.8  # 叶子节点，无需验证时间顺序

        # 检查是否所有子孙的异常时间都晚于当前节点
        violations = 0
        for descendant in descendants:
            if descendant in anomaly_times:
                if anomaly_times[descendant] < node_time:
                    violations += 1

        # 违反时间顺序的比例
        violation_ratio = violations / max(1, len(descendants))

        return 1.0 - violation_ratio

    def _compute_structural_confidence(
        self,
        node_id: str,
        causal_graph: CausalGraph
    ) -> float:
        """
        计算结构置信度

        原则：
        - 根节点（无父节点）更可能是根因
        - 对撞点更可能是根因
        """
        node = causal_graph.get_node(node_id)
        if not node:
            return 0.5

        parents = node.parents
        children = node.children

        # 根节点置信度高
        if len(parents) == 0:
            return 0.9

        # 对撞点（多个父节点指向同一节点）
        if len(parents) >= 2 and len(children) == 0:
            return 0.85

        # 中间节点，根据位置评分
        # 越靠近根节点（祖先少），越可能是根因
        ancestors = causal_graph.get_ancestors(node_id)
        ancestor_score = 1.0 / (1 + len(ancestors))

        return 0.5 + ancestor_score * 0.4

    def _compute_consistency_confidence(
        self,
        evidence: List[Dict[str, Any]]
    ) -> float:
        """
        计算一致性置信度

        原则：多源证据一致时置信度高
        """
        if not evidence:
            return 0.5

        # 统计证据类型
        evidence_types = defaultdict(int)
        for ev in evidence:
            if isinstance(ev, dict):
                ev_type = ev.get("type", "unknown")
            else:
                ev_type = str(ev)
            evidence_types[ev_type] += 1

        # 证据类型越多，一致性越高
        num_types = len(evidence_types)

        if num_types >= 3:
            return 0.9
        elif num_types == 2:
            return 0.7
        else:
            return 0.5


class CausalChainVisualizer:
    """
    因果链可视化数据生成器

    生成用于前端展示的因果链数据
    """

    @staticmethod
    def generate_causal_chain_data(
        causal_graph: CausalGraph,
        root_causes: List[RootCauseHypothesis],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        生成因果链可视化数据

        Returns:
            包含节点、边、高亮路径的可视化数据
        """
        # 排序根因
        sorted_causes = sorted(
            root_causes,
            key=lambda x: x.confidence_score,
            reverse=True
        )[:top_k]

        # 构建可视化节点
        nodes = []
        highlighted_nodes = set()
        for node_id, node in causal_graph._nodes.items():
            is_root_cause = any(rc.candidate_service == node_id for rc in sorted_causes)

            node_data = {
                "id": node_id,
                "name": node.name,
                "type": node.node_type,
                "state": node.current_state,
                "anomaly_score": node.anomaly_score,
                "is_root_cause": is_root_cause,
                "root_cause_confidence": 0.0
            }

            if is_root_cause:
                highlighted_nodes.add(node_id)
                for rc in sorted_causes:
                    if rc.candidate_service == node_id:
                        node_data["root_cause_confidence"] = rc.confidence_score
                        break

            nodes.append(node_data)

        # 构建可视化边
        edges = []
        highlighted_edges = set()
        for edge_id, edge in causal_graph._edges.items():
            is_causal_path = any(
                causal_graph.has_edge(edge.source, edge.target)
                for rc in sorted_causes
                for child in causal_graph.get_children(rc.candidate_service)
                if child == edge.target or child == edge.source
            )

            edge_data = {
                "id": edge_id,
                "source": edge.source,
                "target": edge.target,
                "type": edge.edge_type,
                "strength": edge.causal_strength,
                "is_highlighted": is_causal_path
            }

            if is_causal_path:
                highlighted_edges.add(edge_id)

            edges.append(edge_data)

        # 构建因果路径
        causal_paths = []
        for rc in sorted_causes:
            paths = CausalChainVisualizer._extract_causal_paths(
                causal_graph, rc.candidate_service
            )
            for path in paths:
                causal_paths.append({
                    "root_cause": rc.candidate_service,
                    "root_cause_type": rc.root_cause_type,
                    "confidence": rc.confidence_score,
                    "path": path["path"],
                    "causal_effect": path["causal_effect"]
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "highlighted_nodes": list(highlighted_nodes),
            "highlighted_edges": list(highlighted_edges),
            "causal_paths": causal_paths,
            "root_causes": [rc.to_dict() for rc in sorted_causes]
        }

    @staticmethod
    def _extract_causal_paths(
        causal_graph: CausalGraph,
        root_node: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """提取从根因出发的因果路径"""
        paths = []

        def dfs(current: str, path: List[str], effect: float, depth: int):
            if depth > max_depth:
                return

            children = causal_graph.get_children(current)
            if not children:
                # 叶子节点，记录路径
                if len(path) > 1:
                    paths.append({
                        "path": path[:],
                        "causal_effect": effect
                    })
                return

            for child in children:
                edge = causal_graph.get_edge(current, child)
                edge_strength = edge.causal_strength if edge else 0.5

                path.append(child)
                dfs(child, path, effect * edge_strength, depth + 1)
                path.pop()

        dfs(root_node, [root_node], 1.0, 0)
        return paths


# ==================== 主因果推断引擎 ====================

class CausalInferenceEngine:
    """
    因果推断根因分析引擎 v2.2

    整合所有组件，提供统一的根因分析接口
    """

    def __init__(self):
        self.graph = CausalGraph()
        self.bayesian_inference: Optional[BayesianCausalInference] = None
        self.confidence_scorer = ConfidenceScorer()
        self._analysis_history: List[Dict[str, Any]] = []

    def build_graph_from_service_map(self, service_map_data: Dict[str, Any]):
        """从服务映射数据构建因果图"""
        self.graph = CausalGraph()

        # 添加服务节点
        services = service_map_data.get("services", [])
        for svc in services:
            node = CausalNode(
                id=svc["id"],
                name=svc.get("name", svc["id"]),
                node_type=svc.get("type", "service"),
                metrics=svc.get("metrics", {})
            )

            # 设置先验概率（基于健康状态）
            health = svc.get("health_status", "unknown")
            if health == "unhealthy":
                node.prior_prob["failed"] = 0.8
                node.prior_prob["degraded"] = 0.15
                node.prior_prob["normal"] = 0.05
                node.current_state = "failed"
            elif health == "degraded":
                node.prior_prob["failed"] = 0.3
                node.prior_prob["degraded"] = 0.5
                node.prior_prob["normal"] = 0.2
                node.current_state = "degraded"
            else:
                node.prior_prob["failed"] = 0.05
                node.prior_prob["degraded"] = 0.15
                node.prior_prob["normal"] = 0.8
                node.current_state = "normal"

            # 异常评分
            anomaly_score = 0.0
            # 健康状态直接影响异常评分
            if health == "unhealthy":
                anomaly_score += 0.5
            elif health == "degraded":
                anomaly_score += 0.2

            # 指标异常
            if svc.get("metrics", {}).get("error_rate", 0) > 0.1:
                anomaly_score += 0.3
            if svc.get("metrics", {}).get("latency_p99_ms", 0) > 1000:
                anomaly_score += 0.2
            if svc.get("metrics", {}).get("cpu_percent", 0) > 90:
                anomaly_score += 0.2

            node.anomaly_score = min(1.0, anomaly_score)

            self.graph.add_node(node)

        # 添加依赖边
        edges = service_map_data.get("edges", [])
        for edge in edges:
            causal_edge = CausalEdge(
                source=edge.get("source"),
                target=edge.get("target"),
                edge_type=edge.get("dependency_type", "calls"),
                causal_strength=self._estimate_causal_strength(edge),
                propagation_delay_ms=edge.get("latency_p50_ms", 0)
            )
            self.graph.add_edge(causal_edge)

        # 初始化贝叶斯推断
        self.bayesian_inference = BayesianCausalInference(self.graph)

        logger.info(f"Built causal graph with {len(self.graph._nodes)} nodes and {len(self.graph._edges)} edges")

    def _estimate_causal_strength(self, edge: Dict[str, Any]) -> float:
        """基于边指标估计因果强度"""
        strength = 1.0

        # 错误率高的边，因果强度更高（故障更容易传播）
        error_rate = edge.get("metrics", {}).get("error_rate", 0)
        if error_rate > 0.1:
            strength = min(1.0, 0.8 + error_rate)

        # 调用频率高的边，影响更大
        call_count = edge.get("metrics", {}).get("call_count", 1)
        if call_count > 1000:
            strength = min(1.0, strength + 0.1)

        return strength

    def update_node_metrics(self, service_id: str, metrics: Dict[str, Any]):
        """更新节点指标"""
        node = self.graph.get_node(service_id)
        if node:
            node.metrics.update(metrics)

            # 重新计算异常评分
            anomaly_score = 0.0
            if metrics.get("error_rate", 0) > 0.1:
                anomaly_score += 0.4
            if metrics.get("latency_p99_ms", 0) > 1000:
                anomaly_score += 0.3
            if metrics.get("cpu_percent", 0) > 90:
                anomaly_score += 0.3

            node.anomaly_score = min(1.0, anomaly_score)

            # 更新状态
            if metrics.get("error_rate", 0) > 0.5:
                node.current_state = "failed"
            elif metrics.get("error_rate", 0) > 0.1:
                node.current_state = "degraded"
            else:
                node.current_state = "normal"

    def analyze(
        self,
        evidence: Dict[str, Any] = None,
        lookback_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        执行因果推断根因分析

        Args:
            evidence: 观察到的证据（可选）
            lookback_minutes: 回溯时间（分钟）

        Returns:
            根因分析结果
        """
        if not self.bayesian_inference:
            raise ValueError("Causal graph not built")

        # 1. 收集证据
        if evidence is None:
            evidence = self._collect_evidence(lookback_minutes)

        # 2. 生成根因假设
        hypotheses = self._generate_hypotheses(evidence)

        # 3. 贝叶斯推断
        for hypothesis in hypotheses:
            self._perform_bayesian_inference(hypothesis, evidence)

        # 4. 计算因果效应
        for hypothesis in hypotheses:
            self._compute_causal_effects(hypothesis)

        # 5. 置信度评分
        anomaly_times = self._collect_anomaly_times(evidence)
        for hypothesis in hypotheses:
            confidence, factors = self.confidence_scorer.compute_confidence(
                hypothesis, self.graph, evidence, anomaly_times
            )
            hypothesis.confidence_score = confidence
            hypothesis.confidence_factors = factors

        # 6. 反事实分析
        for hypothesis in hypotheses[:5]:  # Top 5
            hypothesis.counterfactual = self.bayesian_inference.compute_counterfactual(
                hypothesis, evidence
            )

        # 7. 排序
        hypotheses.sort(key=lambda x: x.confidence_score, reverse=True)

        # 8. 生成可视化数据
        visual_data = CausalChainVisualizer.generate_causal_chain_data(
            self.graph, hypotheses
        )

        # 9. 构建结果
        result = self._build_analysis_result(hypotheses, evidence, visual_data)

        self._analysis_history.append(result)
        return result

    def _collect_evidence(self, lookback_minutes: int) -> Dict[str, Any]:
        """收集证据"""
        evidence = {
            "anomaly_services": [],
            "metrics": {}
        }

        for node_id, node in self.graph._nodes.items():
            if node.anomaly_score > 0.3:
                evidence["anomaly_services"].append(node_id)
                evidence["metrics"][node_id] = node.metrics

        return evidence

    def _collect_anomaly_times(self, evidence: Dict[str, Any]) -> Dict[str, datetime]:
        """收集异常时间"""
        anomaly_times = {}
        now = datetime.utcnow()

        for i, service_id in enumerate(evidence.get("anomaly_services", [])):
            # 简化：基于索引模拟时间顺序
            anomaly_times[service_id] = now - timedelta(minutes=len(evidence["anomaly_services"]) - i)

        return anomaly_times

    def _generate_hypotheses(self, evidence: Dict[str, Any]) -> List[RootCauseHypothesis]:
        """生成根因假设"""
        hypotheses = []

        # 候选：所有异常服务
        candidates = evidence.get("anomaly_services", [])

        # 如果没有指定 anomaly_services，使用图中的节点（基于异常评分过滤）
        if not candidates:
            candidates = [
                node_id for node_id, node in self.graph._nodes.items()
                if node.anomaly_score > 0.3
            ]

        for i, service_id in enumerate(candidates):
            node = self.graph.get_node(service_id)
            if not node:
                continue

            # 确定根因类型
            root_cause_type = self._infer_root_cause_type(node)

            hypothesis = RootCauseHypothesis(
                hypothesis_id=f"hypothesis-{service_id}-{i}",
                candidate_service=service_id,
                root_cause_type=root_cause_type,
                prior_probability=0.5,  # 初始先验
                posterior_probability=0.5,
                likelihood=1.0,
                total_effect=0.0,
                direct_effect=0.0,
                indirect_effect=0.0,
                confidence_score=0.5,
                evidence=[
                    {"type": "anomaly", "service": service_id, "score": node.anomaly_score},
                    {"type": "metrics", "service": service_id, "data": node.metrics}
                ]
            )
            hypotheses.append(hypothesis)

        return hypotheses

    def _infer_root_cause_type(self, node: CausalNode) -> str:
        """推断根因类型"""
        metrics = node.metrics

        if metrics.get("cpu_percent", 0) > 90:
            return "resource_exhaustion"
        elif metrics.get("error_rate", 0) > 0.5:
            return "service_failure"
        elif node.node_type == "database":
            return "database_issue"
        elif node.node_type == "cache":
            return "cache_issue"
        else:
            return "service_exception"

    def _perform_bayesian_inference(
        self,
        hypothesis: RootCauseHypothesis,
        evidence: Dict[str, Any]
    ):
        """执行贝叶斯推断"""
        posterior, likelihood, prior = self.bayesian_inference.compute_posterior_probability(
            hypothesis.candidate_service,
            evidence.get("metrics", {}).get(hypothesis.candidate_service, {})
        )

        hypothesis.posterior_probability = posterior
        hypothesis.likelihood = likelihood
        hypothesis.prior_probability = prior

    def _compute_causal_effects(self, hypothesis: RootCauseHypothesis):
        """计算因果效应"""
        node = self.graph.get_node(hypothesis.candidate_service)
        if not node:
            return

        # 计算对每个子节点的因果效应
        total_effects = []
        direct_effects = []

        for child_id in node.children:
            total, direct, indirect = self.bayesian_inference.compute_causal_effect(
                hypothesis.candidate_service,
                child_id
            )
            total_effects.append(total)
            direct_effects.append(direct)

        # 平均因果效应
        hypothesis.total_effect = sum(total_effects) / max(1, len(total_effects))
        hypothesis.direct_effect = sum(direct_effects) / max(1, len(direct_effects))
        hypothesis.indirect_effect = hypothesis.total_effect - hypothesis.direct_effect

    def _build_analysis_result(
        self,
        hypotheses: List[RootCauseHypothesis],
        evidence: Dict[str, Any],
        visual_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建分析结果"""
        top_causes = hypotheses[:5] if hypotheses else []

        # 生成摘要
        if top_causes:
            top_cause = top_causes[0]
            summary = (
                f"检测到 {len(hypotheses)} 个潜在根因，"
                f"最可能的根因是 {top_cause.candidate_service} ({top_cause.root_cause_type})，"
                f"置信度 {top_cause.confidence_score:.1%}。"
            )
        else:
            summary = "未检测到明显的根因"

        # 生成建议
        recommendations = self._generate_recommendations(top_causes)

        return {
            "analysis_id": f"causal-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "summary": summary,
            "root_causes": [h.to_dict() for h in top_causes],
            "all_hypotheses": [h.to_dict() for h in hypotheses],
            "evidence": evidence,
            "causal_graph": self.graph.to_dict(),
            "visualization": visual_data,
            "recommendations": recommendations,
            "confidence_level": self._map_confidence_level(top_causes[0].confidence_score) if top_causes else "unknown"
        }

    def _generate_recommendations(self, top_causes: List[RootCauseHypothesis]) -> List[str]:
        """生成处理建议"""
        recommendations = []

        for cause in top_causes[:3]:
            if cause.root_cause_type == "resource_exhaustion":
                recommendations.append(f"检查 {cause.candidate_service} 的资源使用情况，考虑扩容或优化")
            elif cause.root_cause_type == "service_failure":
                recommendations.append(f"检查 {cause.candidate_service} 的日志和依赖服务")
            elif cause.root_cause_type == "database_issue":
                recommendations.append(f"检查 {cause.candidate_service} 的连接池和慢查询")
            elif cause.root_cause_type == "cache_issue":
                recommendations.append(f"检查 {cause.candidate_service} 的内存使用和缓存命中率")
            else:
                recommendations.append(f"调查 {cause.candidate_service} 的异常原因")

        # 添加反事实建议
        for cause in top_causes[:1]:
            if cause.counterfactual:
                cf = cause.counterfactual
                recommendations.append(
                    f"反事实分析：如果 {cause.candidate_service} 恢复正常，"
                    f"预计 {cf['services_would_be_normal']}/{cf['total_affected_services']} "
                    f"个服务将恢复正常"
                )

        return recommendations

    def _map_confidence_level(self, score: float) -> str:
        """映射置信度等级"""
        if score >= 0.8:
            return "very_high"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        elif score >= 0.2:
            return "low"
        else:
            return "very_low"

    def get_analysis_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取分析历史"""
        return self._analysis_history[-limit:]


# 全局实例
_causal_inference_engine: Optional[CausalInferenceEngine] = None


def get_causal_inference_engine() -> CausalInferenceEngine:
    """获取因果推断引擎实例"""
    global _causal_inference_engine
    if _causal_inference_engine is None:
        _causal_inference_engine = CausalInferenceEngine()
    return _causal_inference_engine


def create_sample_causal_graph() -> CausalGraph:
    """创建示例因果图"""
    graph = CausalGraph()

    # 添加节点
    nodes = [
        CausalNode(id="api-gateway", name="API Gateway", node_type="service"),
        CausalNode(id="user-service", name="User Service", node_type="service"),
        CausalNode(id="order-service", name="Order Service", node_type="service"),
        CausalNode(id="payment-service", name="Payment Service", node_type="service"),
        CausalNode(id="database", name="PostgreSQL", node_type="database"),
        CausalNode(id="cache", name="Redis Cache", node_type="cache"),
    ]

    for node in nodes:
        graph.add_node(node)

    # 添加边
    edges = [
        CausalEdge(source="api-gateway", target="user-service", edge_type="calls", causal_strength=0.9),
        CausalEdge(source="api-gateway", target="order-service", edge_type="calls", causal_strength=0.9),
        CausalEdge(source="user-service", target="database", edge_type="depends_on", causal_strength=0.95),
        CausalEdge(source="user-service", target="cache", edge_type="uses", causal_strength=0.8),
        CausalEdge(source="order-service", target="payment-service", edge_type="calls", causal_strength=0.9),
        CausalEdge(source="order-service", target="database", edge_type="depends_on", causal_strength=0.95),
        CausalEdge(source="payment-service", target="database", edge_type="depends_on", causal_strength=0.95),
    ]

    for edge in edges:
        graph.add_edge(edge)

    # 设置异常状态
    graph.get_node("database").anomaly_score = 0.9
    graph.get_node("database").current_state = "failed"

    graph.get_node("user-service").anomaly_score = 0.6
    graph.get_node("user-service").current_state = "degraded"

    graph.get_node("order-service").anomaly_score = 0.7
    graph.get_node("order-service").current_state = "degraded"

    graph.get_node("payment-service").anomaly_score = 0.5
    graph.get_node("payment-service").current_state = "degraded"

    return graph
