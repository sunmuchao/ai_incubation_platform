"""
AI 根因推理引擎 v2
基于图谱和关联分析的根因推理系统，集成 LLM 增强可解释性
"""
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
import logging
import statistics
import json

logger = logging.getLogger(__name__)


# ==================== LLM 增强根因分析 ====================

class LLMEnhancedRootCauseInference:
    """LLM 增强的 AI 根因推理引擎 v2

    在 v1 基础上增加：
    1. 使用 LLM 生成自然语言的根因分析报告
    2. 将技术指标映射为业务影响说明
    3. 生成更具体的优化建议和代码修复方案
    4. 与 ai-code-understanding 协同生成修复代码
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._base_inference = AIRootCauseInference()
        self._analysis_history: List[Dict[str, Any]] = []

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self.llm_client = llm_client

    def build_graph_from_service_map(self, service_map_data: Dict[str, Any]):
        """从服务映射数据构建图谱"""
        self._base_inference.build_graph_from_service_map(service_map_data)

    def record_metric(self, service_id: str, metric_name: str, value: float, timestamp: datetime = None):
        """记录指标历史数据"""
        self._base_inference.record_metric(service_id, metric_name, value, timestamp)

    def record_anomaly(self, anomaly: Dict[str, Any]):
        """记录异常事件"""
        self._base_inference.record_anomaly(anomaly)

    def infer_root_cause_with_explanation(
        self,
        target_service: str = None,
        lookback_minutes: int = 30,
        include_llm_analysis: bool = True
    ) -> Dict[str, Any]:
        """执行根因推理并生成可解释报告

        Args:
            target_service: 目标服务（可选）
            lookback_minutes: 回溯时间（分钟）
            include_llm_analysis: 是否包含 LLM 分析（需要 LLM 客户端）

        Returns:
            包含可解释报告的推理结果
        """
        # 1. 执行基础根因推理
        base_result = self._base_inference.infer_root_cause(
            target_service=target_service,
            lookback_minutes=lookback_minutes
        )

        # 2. 生成技术指标摘要
        technical_summary = self._generate_technical_summary(base_result)

        # 3. 生成业务影响分析
        business_impact = self._analyze_business_impact(base_result)

        # 4. 使用 LLM 增强分析（如果可用）
        llm_analysis = None
        if include_llm_analysis and self.llm_client:
            try:
                llm_analysis = self._invoke_llm_analysis(base_result, technical_summary, business_impact)
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")
                llm_analysis = {"error": str(e), "fallback": True}

        # 5. 生成代码修复建议
        code_fix_suggestions = self._generate_code_fix_suggestions(base_result)

        # 6. 构建增强结果
        enhanced_result = {
            **base_result,
            "technical_summary": technical_summary,
            "business_impact": business_impact,
            "llm_analysis": llm_analysis,
            "code_fix_suggestions": code_fix_suggestions,
            "explainability": {
                "root_cause_chain": self._build_root_cause_chain(base_result),
                "evidence_trace": self._collect_evidence_trace(base_result),
                "confidence_factors": self._explain_confidence_factors(base_result)
            }
        }

        self._analysis_history.append(enhanced_result)
        return enhanced_result

    def _generate_technical_summary(self, result: Dict[str, Any]) -> str:
        """生成技术指标摘要"""
        root_causes = result.get("root_causes", [])
        if not root_causes:
            return "未检测到明显的根因"

        summary_parts = []
        for rc in root_causes[:3]:  # Top 3 根因
            node_id = rc.get("node_id", "unknown")
            node_type = rc.get("node_type", "service")
            score = rc.get("inference_score", 0)
            evidence = rc.get("evidence", [])

            anomaly_count = rc.get("anomaly_count", 0)
            is_root_cause = rc.get("is_root_cause", False)

            summary_parts.append(
                f"服务 {node_id} ({node_type}) 检测到 {anomaly_count} 个异常，"
                f"推理得分 {score:.2f}，{'确认为根因' if is_root_cause else '待观察'}。"
                f"关键证据：{'; '.join(evidence[:2]) if evidence else '无明显证据'}"
            )

        return " | ".join(summary_parts)

    def _analyze_business_impact(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """分析业务影响"""
        root_causes = result.get("root_causes", [])
        propagation_paths = result.get("propagation_paths", [])

        # 计算影响范围
        affected_services = set()
        for path in propagation_paths:
            affected_services.update(path.get("path", []))

        # 评估影响等级
        if len(root_causes) == 0:
            impact_level = "none"
            impact_description = "未检测到业务影响"
        elif len(affected_services) > 5 or len(root_causes) > 2:
            impact_level = "critical"
            impact_description = f"检测到严重故障，影响 {len(affected_services)} 个服务"
        elif len(affected_services) > 2:
            impact_level = "high"
            impact_description = f"检测到显著故障，影响 {len(affected_services)} 个服务"
        else:
            impact_level = "medium"
            impact_description = f"检测到局部故障，影响 {len(affected_services)} 个服务"

        # 估算业务指标影响
        estimated_impact = self._estimate_business_metrics_impact(root_causes)

        return {
            "impact_level": impact_level,
            "impact_description": impact_description,
            "affected_services_count": len(affected_services),
            "affected_services": list(affected_services),
            "root_causes_count": len(root_causes),
            "estimated_business_impact": estimated_impact
        }

    def _estimate_business_metrics_impact(self, root_causes: List[Dict]) -> Dict[str, Any]:
        """估算业务指标影响"""
        # 基于根因类型估算业务影响
        impact = {
            "revenue_risk": "low",
            "user_experience_impact": "low",
            "data_integrity_risk": "low"
        }

        for rc in root_causes:
            node_type = rc.get("node_type", "")
            metrics = rc.get("metrics", {})
            error_rate = metrics.get("error_rate", 0)
            latency = metrics.get("latency_p99_ms", 0)

            # 高错误率影响用户体验
            if error_rate > 0.1:
                impact["user_experience_impact"] = "high"
            elif error_rate > 0.05:
                impact["user_experience_impact"] = "medium"

            # 数据库问题影响数据完整性
            if node_type in ["database", "db"]:
                impact["data_integrity_risk"] = "medium"

            # 关键服务问题影响收入
            if rc.get("is_root_cause", False) and error_rate > 0.2:
                impact["revenue_risk"] = "high"
            elif error_rate > 0.1:
                impact["revenue_risk"] = "medium"

        return impact

    def _invoke_llm_analysis(
        self,
        base_result: Dict[str, Any],
        technical_summary: str,
        business_impact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用 LLM 进行深度分析"""
        prompt = f"""你是一个专业的系统可靠性工程师 (SRE)。请根据以下监控系统数据，分析系统故障的根因，并给出详细的解释和可执行的建议。

## 技术指标摘要
{technical_summary}

## 业务影响分析
- 影响等级：{business_impact.get('impact_level', 'unknown')}
- 影响描述：{business_impact.get('impact_description', 'N/A')}
- 影响服务数：{business_impact.get('affected_services_count', 0)}

## 详细根因数据
{json.dumps(base_result, ensure_ascii=False, indent=2, default=str)}

请输出以下内容：
1. 根因分析：用自然语言描述故障的根本原因
2. 影响链分析：描述故障如何在服务间传播
3. 紧急程度评估：评估需要多快响应
4. 具体行动建议：列出 3-5 个具体的、可执行的修复步骤
5. 长期改进建议：如何避免类似问题再次发生

请用简洁、结构化的方式输出。
"""

        response = self.llm_client.analyze(prompt)

        return {
            "analysis_text": response,
            "generated_at": datetime.utcnow().isoformat(),
            "model": getattr(self.llm_client, 'model', 'unknown')
        }

    def _generate_code_fix_suggestions(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成代码修复建议"""
        suggestions = []
        root_causes = result.get("root_causes", [])

        for rc in root_causes:
            node_type = rc.get("node_type", "")
            node_id = rc.get("node_id", "")
            evidence = rc.get("evidence", [])

            # 基于根因类型生成代码建议
            if "cpu" in str(evidence).lower() or "RESOURCE_EXHAUSTION" in str(rc):
                suggestions.append({
                    "type": "performance_optimization",
                    "target": node_id,
                    "title": f"优化 {node_id} 的 CPU 使用",
                    "description": "检测到 CPU 资源耗尽，建议进行性能优化",
                    "code_hint": "考虑使用异步 I/O、缓存热点数据、优化算法复杂度",
                    "priority": "high"
                })

            if "database" in node_type.lower():
                suggestions.append({
                    "type": "database_optimization",
                    "target": node_id,
                    "title": f"优化 {node_id} 数据库性能",
                    "description": "检测到数据库性能问题",
                    "code_hint": "考虑添加索引、优化查询语句、使用连接池",
                    "priority": "high"
                })

            if "error_rate" in str(evidence).lower():
                suggestions.append({
                    "type": "error_handling",
                    "target": node_id,
                    "title": f"增强 {node_id} 的错误处理",
                    "description": "检测到高错误率",
                    "code_hint": "考虑添加重试机制、熔断器、降级策略",
                    "priority": "medium"
                })

        return suggestions

    def _build_root_cause_chain(self, result: Dict[str, Any]) -> List[str]:
        """构建根因因果链"""
        chain = []
        root_causes = result.get("root_causes", [])
        propagation_paths = result.get("propagation_paths", [])

        for rc in root_causes:
            chain.append(f"[根因] {rc.get('node_id')} 发生 {rc.get('evidence', ['异常'])[0]}")

        for path in propagation_paths[:3]:
            path_str = " -> ".join(path.get("path", []))
            chain.append(f"[传播] {path_str}")

        return chain

    def _collect_evidence_trace(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """收集证据追踪"""
        trace = []
        root_causes = result.get("root_causes", [])

        for rc in root_causes:
            for evidence in rc.get("evidence", []):
                trace.append({
                    "node_id": rc.get("node_id"),
                    "evidence_type": evidence.get("type", "unknown") if isinstance(evidence, dict) else str(evidence),
                    "details": evidence
                })

        return trace

    def _explain_confidence_factors(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解释置信度因素"""
        root_causes = result.get("root_causes", [])
        confidence_level = result.get("confidence_level", "unknown")

        factors = {
            "confidence_level": confidence_level,
            "factors": []
        }

        for rc in root_causes:
            score = rc.get("inference_score", 0)
            evidence_count = len(rc.get("evidence", []))
            anomaly_count = rc.get("anomaly_count", 0)

            factors["factors"].append({
                "node_id": rc.get("node_id"),
                "inference_score": score,
                "evidence_count": evidence_count,
                "anomaly_count": anomaly_count,
                "is_root_cause": rc.get("is_root_cause", False)
            })

        return factors

    def get_analysis_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取分析历史"""
        return self._analysis_history[-limit:]


# ==================== 原有类保持不变 ====================


class RootCauseType(str, Enum):
    """根因类型"""
    SERVICE_FAILURE = "service_failure"  # 服务故障
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # 资源耗尽
    DEPENDENCY_FAILURE = "dependency_failure"  # 依赖故障
    CONFIG_CHANGE = "config_change"  # 配置变更
    TRAFFIC_SPIKE = "traffic_spike"  # 流量突增
    NETWORK_ISSUE = "network_issue"  # 网络问题
    DATABASE_ISSUE = "database_issue"  # 数据库问题
    EXTERNAL_SERVICE = "external_service"  # 外部服务问题


class ConfidenceLevel(str, Enum):
    """置信度等级"""
    VERY_HIGH = "very_high"  # > 90%
    HIGH = "high"  # 70-90%
    MEDIUM = "medium"  # 50-70%
    LOW = "low"  # 30-50%
    VERY_LOW = "very_low"  # < 30%


class InferenceNode:
    """推理节点"""

    def __init__(
        self,
        node_id: str,
        node_type: str,
        name: str,
        metrics: Dict[str, Any] = None,
        anomalies: List[Dict[str, Any]] = None
    ):
        self.node_id = node_id
        self.node_type = node_type  # service, database, cache, etc.
        self.name = name
        self.metrics = metrics or {}
        self.anomalies = anomalies or []
        self.inference_score = 0.0  # 推理得分
        self.is_root_cause = False
        self.evidence = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "metrics": self.metrics,
            "anomaly_count": len(self.anomalies),
            "inference_score": self.inference_score,
            "is_root_cause": self.is_root_cause,
            "evidence": self.evidence
        }


class InferenceEdge:
    """推理边（依赖关系）"""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        weight: float = 1.0,
        latency_ms: float = None,
        error_rate: float = None
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.edge_type = edge_type  # calls, depends_on, uses
        self.weight = weight
        self.latency_ms = latency_ms
        self.error_rate = error_rate
        self.propagation_score = 0.0  # 传播得分

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type,
            "weight": self.weight,
            "latency_ms": self.latency_ms,
            "error_rate": self.error_rate,
            "propagation_score": self.propagation_score
        }


class CausalGraph:
    """因果图谱"""

    def __init__(self):
        self.nodes: Dict[str, InferenceNode] = {}
        self.edges: List[InferenceEdge] = []
        self.adjacency: Dict[str, List[str]] = {}  # node_id -> [neighbor_ids]

    def add_node(self, node: InferenceNode):
        """添加节点"""
        self.nodes[node.node_id] = node
        if node.node_id not in self.adjacency:
            self.adjacency[node.node_id] = []

    def add_edge(self, edge: InferenceEdge):
        """添加边"""
        self.edges.append(edge)
        if edge.source_id not in self.adjacency:
            self.adjacency[edge.source_id] = []
        self.adjacency[edge.source_id].append(edge.target_id)

    def get_upstream(self, node_id: str) -> List[str]:
        """获取上游节点（依赖我的节点）"""
        upstream = []
        for edge in self.edges:
            if edge.target_id == node_id:
                upstream.append(edge.source_id)
        return upstream

    def get_downstream(self, node_id: str) -> List[str]:
        """获取下游节点（我依赖的节点）"""
        return self.adjacency.get(node_id, [])

    def get_all_paths_to(self, target_id: str) -> List[List[str]]:
        """获取所有到目标节点的路径"""
        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            if current == target_id:
                paths.append(path[:])
                return

            for neighbor in self.adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, path, visited)
                    path.pop()
                    visited.remove(neighbor)

        for start_node in self.nodes:
            if start_node != target_id:
                dfs(start_node, [start_node], {start_node})

        return paths


class AIRootCauseInference:
    """AI 根因推理引擎 v1

    功能:
    1. 构建服务依赖图谱
    2. 指标关联分析
    3. 异常传播路径分析
    4. 根因置信度评估
    5. 根因排序和解释
    """

    def __init__(self):
        self.graph = CausalGraph()
        self._metric_history: Dict[str, List[Dict[str, Any]]] = {}
        self._anomaly_history: List[Dict[str, Any]] = []
        self._inference_results: List[Dict[str, Any]] = []

        # 推理权重配置
        self.weights = {
            "anomaly_score": 0.3,  # 异常得分权重
            "propagation_score": 0.25,  # 传播得分权重
            "centrality_score": 0.2,  # 中心性得分权重
            "temporal_score": 0.15,  # 时间相关性权重
            "historical_score": 0.1  # 历史相似度权重
        }

    def build_graph_from_service_map(self, service_map_data: Dict[str, Any]):
        """从服务映射数据构建图谱"""
        self.graph = CausalGraph()

        # 添加服务节点
        services = service_map_data.get("services", [])
        for svc in services:
            node = InferenceNode(
                node_id=svc["id"],
                node_type=svc.get("type", "service"),
                name=svc.get("name", svc["id"]),
                metrics=svc.get("metrics", {})
            )
            self.graph.add_node(node)

        # 添加依赖边
        edges = service_map_data.get("edges", [])
        for edge in edges:
            inference_edge = InferenceEdge(
                source_id=edge.get("source"),
                target_id=edge.get("target"),
                edge_type="calls",
                weight=edge.get("weight", 1.0),
                latency_ms=edge.get("latency_ms"),
                error_rate=edge.get("error_rate")
            )
            self.graph.add_edge(inference_edge)

        logger.info(f"Built graph with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")

    def record_metric(self, service_id: str, metric_name: str, value: float, timestamp: datetime = None):
        """记录指标历史数据"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        key = f"{service_id}:{metric_name}"
        if key not in self._metric_history:
            self._metric_history[key] = []

        self._metric_history[key].append({
            "timestamp": timestamp,
            "value": value
        })

        # 保留最近 24 小时的数据
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self._metric_history[key] = [
            m for m in self._metric_history[key]
            if m["timestamp"] > cutoff
        ]

    def record_anomaly(self, anomaly: Dict[str, Any]):
        """记录异常事件"""
        self._anomaly_history.append({
            **anomaly,
            "recorded_at": datetime.utcnow()
        })

        # 保留最近 1000 条异常
        if len(self._anomaly_history) > 1000:
            self._anomaly_history = self._anomaly_history[-1000:]

    def infer_root_cause(
        self,
        target_service: str = None,
        lookback_minutes: int = 30
    ) -> Dict[str, Any]:
        """执行根因推理

        Args:
            target_service: 目标服务（可选，不传则分析所有服务）
            lookback_minutes: 回溯时间（分钟）

        Returns:
            推理结果
        """
        start_time = datetime.utcnow() - timedelta(minutes=lookback_minutes)

        # 1. 收集候选根因节点
        candidates = self._collect_candidates(start_time)

        # 2. 计算各维度得分
        for candidate in candidates:
            self._calculate_anomaly_score(candidate, start_time)
            self._calculate_propagation_score(candidate)
            self._calculate_centrality_score(candidate)
            self._calculate_temporal_score(candidate, start_time)
            self._calculate_historical_score(candidate)

        # 3. 计算综合得分
        for candidate in candidates:
            candidate.inference_score = self._calculate_composite_score(candidate)

        # 4. 排序并识别根因
        candidates.sort(key=lambda x: x.inference_score, reverse=True)

        # 5. 标记根因
        if candidates:
            top_score = candidates[0].inference_score
            for candidate in candidates:
                # 得分超过阈值且与最高分差距不大
                if candidate.inference_score >= 0.5 and \
                   (top_score - candidate.inference_score) < 0.3:
                    candidate.is_root_cause = True

        # 6. 构建推理结果
        result = self._build_inference_result(candidates, target_service, start_time)
        self._inference_results.append(result)

        return result

    def _collect_candidates(self, start_time: datetime) -> List[InferenceNode]:
        """收集候选根因节点"""
        candidates = []

        for node_id, node in self.graph.nodes.items():
            # 检查节点是否有异常
            has_anomaly = self._check_node_anomaly(node, start_time)
            if has_anomaly:
                candidates.append(node)

        # 如果没有明确异常节点，将所有节点作为候选
        if not candidates:
            candidates = list(self.graph.nodes.values())

        return candidates

    def _check_node_anomaly(self, node: InferenceNode, start_time: datetime) -> bool:
        """检查节点是否有异常"""
        # 检查指标异常
        for metric_name in ["error_rate", "latency_p99_ms", "cpu_percent", "memory_mb"]:
            key = f"{node.node_id}:{metric_name}"
            if key in self._metric_history:
                history = self._metric_history[key]
                recent = [m for m in history if m["timestamp"] > start_time]
                if recent:
                    values = [m["value"] for m in recent]
                    if len(values) >= 2:
                        # 简单异常检测：突增 50%
                        if values[-1] > values[0] * 1.5:
                            return True

        # 检查历史异常记录
        for anomaly in self._anomaly_history:
            if anomaly.get("service_name") == node.node_id:
                if anomaly.get("timestamp", datetime.min) > start_time:
                    return True

        return False

    def _calculate_anomaly_score(self, node: InferenceNode, start_time: datetime):
        """计算异常得分"""
        anomaly_count = 0
        max_deviation = 0.0

        for metric_name in ["error_rate", "latency_p99_ms", "cpu_percent"]:
            key = f"{node.node_id}:{metric_name}"
            if key in self._metric_history:
                history = self._metric_history[key]
                recent = [m for m in history if m["timestamp"] > start_time]

                if len(recent) >= 2:
                    values = [m["value"] for m in recent]
                    baseline = statistics.mean(values[:-1]) if values[:-1] else values[0]
                    current = values[-1]

                    if baseline > 0:
                        deviation = (current - baseline) / baseline
                        max_deviation = max(max_deviation, abs(deviation))
                        if deviation > 0.5:  # 50% 增长视为异常
                            anomaly_count += 1

        # 归一化得分
        node.evidence.append({
            "type": "anomaly",
            "anomaly_count": anomaly_count,
            "max_deviation": max_deviation
        })

        node.inference_score += min(1.0, anomaly_count * 0.2 + max_deviation * 0.3)

    def _calculate_propagation_score(self, node: InferenceNode):
        """计算传播得分（基于影响范围）"""
        downstream = self.graph.get_downstream(node.node_id)
        upstream = self.graph.get_upstream(node.node_id)

        # 下游节点越多，影响范围越大
        downstream_count = len(downstream)
        upstream_count = len(upstream)

        # 如果是叶子节点（没有下游），可能是根因
        if downstream_count == 0 and upstream_count > 0:
            propagation_score = 0.8
        # 如果是根节点（没有上游），可能是源头
        elif upstream_count == 0 and downstream_count > 0:
            propagation_score = 0.7
        else:
            # 中间节点，根据影响范围评分
            propagation_score = min(1.0, downstream_count * 0.1)

        node.evidence.append({
            "type": "propagation",
            "downstream_count": downstream_count,
            "upstream_count": upstream_count
        })

        node.inference_score += propagation_score * 0.25

    def _calculate_centrality_score(self, node: InferenceNode):
        """计算中心性得分"""
        total_nodes = len(self.graph.nodes)
        if total_nodes <= 1:
            return

        # 度中心性
        degree = len(self.graph.adjacency.get(node.node_id, []))
        degree_centrality = degree / (total_nodes - 1) if total_nodes > 1 else 0

        node.evidence.append({
            "type": "centrality",
            "degree": degree,
            "degree_centrality": degree_centrality
        })

        # 中心性高的节点更可能是关键节点
        node.inference_score += degree_centrality * 0.2

    def _calculate_temporal_score(self, node: InferenceNode, start_time: datetime):
        """计算时间相关性得分"""
        # 查找最早出现异常的节点
        earliest_anomaly = None

        for anomaly in self._anomaly_history:
            if anomaly.get("service_name") == node.node_id:
                anomaly_time = anomaly.get("timestamp")
                if anomaly_time and anomaly_time > start_time:
                    if earliest_anomaly is None or anomaly_time < earliest_anomaly:
                        earliest_anomaly = anomaly_time

        if earliest_anomaly:
            # 越早出现异常，越可能是根因
            time_from_start = (earliest_anomaly - start_time).total_seconds()
            lookback_seconds = 30 * 60  # 30 分钟

            temporal_score = max(0, 1 - (time_from_start / lookback_seconds))
        else:
            temporal_score = 0.5  # 没有时间信息时的默认值

        node.evidence.append({
            "type": "temporal",
            "earliest_anomaly": earliest_anomaly.isoformat() if earliest_anomaly else None,
            "temporal_score": temporal_score
        })

        node.inference_score += temporal_score * 0.15

    def _calculate_historical_score(self, node: InferenceNode):
        """计算历史相似度得分"""
        # 检查该节点历史上是否曾作为根因
        historical_root_cause_count = 0

        for result in self._inference_results:
            for cause in result.get("root_causes", []):
                if cause.get("node_id") == node.node_id and cause.get("is_root_cause"):
                    historical_root_cause_count += 1

        # 历史上频繁作为根因的节点，本次也更可能是根因
        historical_score = min(1.0, historical_root_cause_count * 0.2)

        node.evidence.append({
            "type": "historical",
            "historical_root_cause_count": historical_root_cause_count,
            "historical_score": historical_score
        })

        node.inference_score += historical_score * 0.1

    def _calculate_composite_score(self, node: InferenceNode) -> float:
        """计算综合得分"""
        # 各维度得分已在各自方法中累加
        # 这里进行归一化
        return min(1.0, node.inference_score)

    def _build_inference_result(
        self,
        candidates: List[InferenceNode],
        target_service: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """构建推理结果"""
        root_causes = [c for c in candidates if c.is_root_cause]

        # 构建传播路径
        propagation_paths = []
        for rc in root_causes:
            if target_service:
                paths = self.graph.get_all_paths_to(target_service)
                for path in paths[:3]:  # 最多 3 条路径
                    propagation_paths.append({
                        "root_cause": rc.node_id,
                        "target": target_service,
                        "path": path
                    })

        # 确定置信度
        if root_causes:
            max_score = max(rc.inference_score for rc in root_causes)
            if max_score >= 0.8:
                confidence_level = ConfidenceLevel.VERY_HIGH.value
            elif max_score >= 0.6:
                confidence_level = ConfidenceLevel.HIGH.value
            elif max_score >= 0.4:
                confidence_level = ConfidenceLevel.MEDIUM.value
            elif max_score >= 0.2:
                confidence_level = ConfidenceLevel.LOW.value
            else:
                confidence_level = ConfidenceLevel.VERY_LOW.value
        else:
            confidence_level = ConfidenceLevel.VERY_LOW.value

        # 推断根因类型
        root_cause_types = []
        for rc in root_causes:
            rc_type = self._infer_root_cause_type(rc)
            root_cause_types.append({
                "node_id": rc.node_id,
                "type": rc_type.value,
                "confidence": rc.inference_score
            })

        return {
            "inference_id": f"inference_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "lookback_start": start_time.isoformat(),
            "target_service": target_service,
            "confidence_level": confidence_level,
            "root_causes": [c.to_dict() for c in root_causes],
            "all_candidates": [c.to_dict() for c in candidates[:10]],  # Top 10
            "propagation_paths": propagation_paths,
            "root_cause_types": root_cause_types,
            "recommendations": self._generate_recommendations(root_causes)
        }

    def _infer_root_cause_type(self, node: InferenceNode) -> RootCauseType:
        """推断根因类型"""
        metrics = node.metrics or {}

        # 基于指标特征推断类型
        error_rate = metrics.get("error_rate", 0)
        cpu_percent = metrics.get("cpu_percent", 0)
        memory_mb = metrics.get("memory_mb", 0)
        latency_p99_ms = metrics.get("latency_p99_ms", 0)

        if error_rate > 0.5:
            return RootCauseType.SERVICE_FAILURE
        elif cpu_percent > 90:
            return RootCauseType.RESOURCE_EXHAUSTION
        elif node.node_type in ["database", "db"]:
            return RootCauseType.DATABASE_ISSUE
        elif node.node_type in ["cache", "redis"]:
            return RootCauseType.RESOURCE_EXHAUSTION
        elif latency_p99_ms > 1000:
            return RootCauseType.NETWORK_ISSUE
        else:
            return RootCauseType.SERVICE_FAILURE

    def _generate_recommendations(self, root_causes: List[InferenceNode]) -> List[str]:
        """生成处理建议"""
        recommendations = []

        for rc in root_causes:
            if rc.node_type == "database":
                recommendations.append(f"检查数据库 {rc.name} 的连接池和慢查询")
            elif rc.node_type == "cache":
                recommendations.append(f"检查缓存 {rc.name} 的内存使用和过期策略")
            elif "cpu" in str(rc.metrics):
                recommendations.append(f"检查服务 {rc.name} 的 CPU 使用，考虑扩容或优化")
            else:
                recommendations.append(f"检查服务 {rc.name} 的日志和依赖")

        return recommendations

    def get_inference_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取推理历史"""
        return self._inference_results[-limit:]


# ==================== 全局实例 ====================

_ai_root_cause_inference: Optional[AIRootCauseInference] = None
_ai_enhanced_root_cause_inference: Optional[LLMEnhancedRootCauseInference] = None


def get_ai_root_cause_inference() -> AIRootCauseInference:
    """获取 AI 根因推理实例"""
    global _ai_root_cause_inference
    if _ai_root_cause_inference is None:
        _ai_root_cause_inference = AIRootCauseInference()
    return _ai_root_cause_inference


def get_ai_enhanced_root_cause_inference() -> LLMEnhancedRootCauseInference:
    """获取 LLM 增强的 AI 根因推理实例"""
    global _ai_enhanced_root_cause_inference
    if _ai_enhanced_root_cause_inference is None:
        _ai_enhanced_root_cause_inference = LLMEnhancedRootCauseInference()
    return _ai_enhanced_root_cause_inference


def configure_enhanced_inference_with_llm(llm_client):
    """配置增强推理引擎的 LLM 客户端

    Args:
        llm_client: LLM 客户端实例（支持 analyze 和 generate_code 方法）

    Returns:
        配置后的增强推理引擎实例
    """
    engine = get_ai_enhanced_root_cause_inference()
    engine.set_llm_client(llm_client)
    logger.info(f"Enhanced root cause inference configured with LLM client: {type(llm_client).__name__}")
    return engine
