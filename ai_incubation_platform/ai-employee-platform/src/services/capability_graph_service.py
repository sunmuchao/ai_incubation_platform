"""
P9-001: AI 员工能力图谱服务

功能:
1. 构建 AI 员工能力图谱
2. 计算能力相似度
3. 生成进化路径建议
4. 获取行业基准数据
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from models.p9_models import (
    CapabilityNode,
    CapabilityEdge,
    CapabilityRelationship,
    CapabilityGraph,
    IndustryBenchmark,
    SimilarEmployee,
    EvolutionPath,
    EvolutionPathRequest,
)

logger = logging.getLogger(__name__)


class CapabilityGraphService:
    """
    AI 员工能力图谱服务

    使用 NetworkX 构建和分析能力图谱（轻量级方案）
    生产环境可迁移到 Neo4j
    """

    def __init__(self):
        # 内存存储图谱数据
        self._graphs: Dict[str, CapabilityGraph] = {}
        # 行业基准缓存
        self._benchmarks: Dict[str, IndustryBenchmark] = {}
        # 预定义的技能关系
        self._skill_relationships = self._init_skill_relationships()

    def _init_skill_relationships(self) -> Dict[str, List[Dict[str, Any]]]:
        """初始化预定义的技能关系"""
        return {
            # Python 相关
            "python": [
                {"target": "data_analysis", "relationship": "enhances", "strength": 0.8},
                {"target": "machine_learning", "relationship": "requires", "strength": 0.7},
                {"target": "web_scraping", "relationship": "enhances", "strength": 0.6},
            ],
            # 数据分析相关
            "data_analysis": [
                {"target": "statistics", "relationship": "requires", "strength": 0.9},
                {"target": "visualization", "relationship": "enhances", "strength": 0.7},
                {"target": "machine_learning", "relationship": "enhances", "strength": 0.6},
            ],
            # 机器学习相关
            "machine_learning": [
                {"target": "deep_learning", "relationship": "enhances", "strength": 0.8},
                {"target": "nlp", "relationship": "related", "strength": 0.7},
                {"target": "computer_vision", "relationship": "related", "strength": 0.7},
            ],
            # NLP 相关
            "nlp": [
                {"target": "text_classification", "relationship": "enhances", "strength": 0.8},
                {"target": "sentiment_analysis", "relationship": "enhances", "strength": 0.8},
                {"target": "translation", "relationship": "related", "strength": 0.6},
            ],
            # 写作相关
            "writing": [
                {"target": "editing", "relationship": "enhances", "strength": 0.7},
                {"target": "translation", "relationship": "related", "strength": 0.5},
                {"target": "content_strategy", "relationship": "enhances", "strength": 0.6},
            ],
            # 设计相关
            "design": [
                {"target": "ui_design", "relationship": "enhances", "strength": 0.8},
                {"target": "ux_design", "relationship": "enhances", "strength": 0.8},
                {"target": "prototyping", "relationship": "enhances", "strength": 0.7},
            ],
        }

    def build_graph(self, employee_id: str, employee_data: Dict[str, Any]) -> CapabilityGraph:
        """
        构建 AI 员工能力图谱

        Args:
            employee_id: 员工 ID
            employee_data: 员工数据，包含 skills, training_history 等

        Returns:
            CapabilityGraph: 构建的能力图谱
        """
        nodes = []
        edges = []
        skills = employee_data.get("skills", {})
        training_history = employee_data.get("training_history", [])
        usage_stats = employee_data.get("usage_stats", {})

        # 创建节点
        centrality_scores = {}
        for skill_name, skill_data in skills.items():
            node_id = f"skill_{skill_name}"
            proficiency = skill_data.get("proficiency", 0.0) if isinstance(skill_data, dict) else skill_data

            # 计算训练次数
            training_count = sum(
                1 for t in training_history
                if t.get("skill") == skill_name
            )

            # 获取使用统计
            skill_usage = usage_stats.get(skill_name, {})
            usage_count = skill_usage.get("count", 0)
            success_rate = skill_usage.get("success_rate", 0.0)
            avg_execution_time = skill_usage.get("avg_time", 0.0)

            # 获取最后训练时间
            last_trained = None
            for t in training_history:
                if t.get("skill") == skill_name and t.get("completed_at"):
                    last_trained = datetime.fromisoformat(t["completed_at"]) if isinstance(t["completed_at"], str) else t["completed_at"]

            node = CapabilityNode(
                id=node_id,
                name=skill_name,
                category=self._get_skill_category(skill_name),
                proficiency=float(proficiency),
                training_count=training_count,
                last_trained=last_trained,
                usage_count=usage_count,
                success_rate=success_rate,
                avg_execution_time=avg_execution_time,
                metadata=skill_data if isinstance(skill_data, dict) else {}
            )
            nodes.append(node)
            centrality_scores[node_id] = proficiency  # 简化：用熟练度作为中心性

        # 创建边
        skill_names = set(skills.keys())
        for skill_name in skill_names:
            relationships = self._skill_relationships.get(skill_name, [])
            for rel in relationships:
                target_skill = rel["target"]
                if target_skill in skill_names:
                    edge = CapabilityEdge(
                        source_id=f"skill_{skill_name}",
                        target_id=f"skill_{target_skill}",
                        relationship=CapabilityRelationship(rel["relationship"]),
                        strength=rel["strength"],
                        description=f"{skill_name} {rel['relationship']} {target_skill}"
                    )
                    edges.append(edge)

        # 创建图谱
        graph = CapabilityGraph(
            employee_id=employee_id,
            employee_name=employee_data.get("name", "Unknown"),
            nodes=nodes,
            edges=edges,
            centrality_scores=centrality_scores,
            core_capabilities=self._find_core_capabilities(nodes, edges),
            isolated_capabilities=self._find_isolated_capabilities(nodes, edges),
            evolution_suggestions=self._generate_evolution_suggestions(nodes, edges),
            generated_at=datetime.now()
        )

        # 缓存图谱
        self._graphs[employee_id] = graph

        logger.info(f"Built capability graph for employee {employee_id}: {len(nodes)} nodes, {len(edges)} edges")
        return graph

    def _get_skill_category(self, skill_name: str) -> str:
        """获取技能类别"""
        category_keywords = {
            "technical": ["python", "java", "javascript", "sql", "api", "database"],
            "design": ["design", "ui", "ux", "figma", "sketch", "photoshop"],
            "writing": ["writing", "editing", "translation", "content", "copywriting"],
            "analysis": ["analysis", "statistics", "visualization", "excel"],
            "ai_specialized": ["machine_learning", "deep_learning", "nlp", "computer_vision", "pytorch", "tensorflow"],
            "marketing": ["marketing", "seo", "sem", "social_media", "advertising"],
            "business": ["strategy", "consulting", "finance", "project_management"],
        }

        skill_lower = skill_name.lower()
        for category, keywords in category_keywords.items():
            if any(kw in skill_lower for kw in keywords):
                return category
        return "other"

    def _find_core_capabilities(self, nodes: List[CapabilityNode], edges: List[CapabilityEdge]) -> List[str]:
        """查找核心能力（高中心性的能力）"""
        if not nodes:
            return []

        # 计算每个节点的度数
        degree_count = {node.id: 0 for node in nodes}
        for edge in edges:
            degree_count[edge.source_id] = degree_count.get(edge.source_id, 0) + 1
            degree_count[edge.target_id] = degree_count.get(edge.target_id, 0) + 1

        # 找出度数最高的 3 个能力
        sorted_by_degree = sorted(degree_count.items(), key=lambda x: x[1], reverse=True)
        return [node_id for node_id, _ in sorted_by_degree[:3]]

    def _find_isolated_capabilities(self, nodes: List[CapabilityNode], edges: List[CapabilityEdge]) -> List[str]:
        """查找孤立能力（没有连接的能力）"""
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.source_id)
            connected_nodes.add(edge.target_id)

        return [node.id for node in nodes if node.id not in connected_nodes]

    def _generate_evolution_suggestions(self, nodes: List[CapabilityNode], edges: List[CapabilityEdge]) -> List[Dict[str, Any]]:
        """生成进化建议"""
        suggestions = []
        node_ids = {node.id for node in nodes}
        node_map = {node.id: node for node in nodes}

        # 建议 1: 增强低熟练度的核心相关技能
        for node in nodes:
            if node.proficiency < 0.5:
                relationships = self._skill_relationships.get(node.name, [])
                for rel in relationships:
                    target_id = f"skill_{rel['target']}"
                    if target_id in node_ids:
                        target_node = node_map.get(target_id)
                        if target_node and target_node.proficiency > 0.7:
                            suggestions.append({
                                "type": "enhance_skill",
                                "description": f"增强 {node.name} 技能，以更好地配合 {rel['target']}",
                                "priority": "medium",
                                "related_nodes": [node.id, target_id],
                                "expected_benefit": "提升技能协同效应"
                            })
                            break

        # 建议 2: 添加与核心能力相关的技能
        core_ids = self._find_core_capabilities(nodes, edges)
        for core_id in core_ids[:2]:  # 只看前两个核心能力
            core_node = node_map.get(core_id)
            if core_node:
                relationships = self._skill_relationships.get(core_node.name, [])
                for rel in relationships:
                    target_id = f"skill_{rel['target']}"
                    if target_id not in node_ids and rel["relationship"] == "enhances":
                        suggestions.append({
                            "type": "add_skill",
                            "description": f"学习 {rel['target']} 技能，增强核心能力 {core_node.name}",
                            "priority": "high",
                            "related_nodes": [core_id],
                            "expected_benefit": "扩展核心能力边界"
                        })
                        break

        # 建议 3: 连接孤立能力
        isolated = self._find_isolated_capabilities(nodes, edges)
        for isolated_id in isolated[:2]:  # 只看前两个孤立能力
            isolated_node = node_map.get(isolated_id)
            if isolated_node:
                suggestions.append({
                    "type": "combine_skills",
                    "description": f"将 {isolated_node.name} 与其他技能结合使用",
                    "priority": "low",
                    "related_nodes": [isolated_id],
                    "expected_benefit": "提升技能利用率"
                })

        return suggestions[:5]  # 最多返回 5 个建议

    def get_graph(self, employee_id: str) -> Optional[CapabilityGraph]:
        """获取 AI 员工能力图谱"""
        if employee_id in self._graphs:
            return self._graphs[employee_id]
        return None

    def calculate_similarity(self, employee_id1: str, employee_id2: str) -> float:
        """
        计算两个 AI 员工的能力相似度

        使用 Jaccard 相似度 + 熟练度加权
        """
        graph1 = self._graphs.get(employee_id1)
        graph2 = self._graphs.get(employee_id2)

        if not graph1 or not graph2:
            return 0.0

        # 技能集合
        skills1 = {node.name.lower(): node.proficiency for node in graph1.nodes}
        skills2 = {node.name.lower(): node.proficiency for node in graph2.nodes}

        if not skills1 or not skills2:
            return 0.0

        # 共同技能
        common_skills = set(skills1.keys()) & set(skills2.keys())
        all_skills = set(skills1.keys()) | set(skills2.keys())

        # Jaccard 相似度
        jaccard = len(common_skills) / len(all_skills) if all_skills else 0.0

        # 熟练度相似度（共同技能的熟练度差异）
        proficiency_similarity = 0.0
        if common_skills:
            diffs = []
            for skill in common_skills:
                diff = abs(skills1[skill] - skills2[skill])
                diffs.append(1 - diff)  # 差异越小，相似度越高
            proficiency_similarity = sum(diffs) / len(diffs)

        # 综合相似度 (Jaccard 60% + 熟练度 40%)
        return 0.6 * jaccard + 0.4 * proficiency_similarity

    def find_similar_employees(
        self,
        employee_id: str,
        all_employees: List[Dict[str, Any]],
        limit: int = 5
    ) -> List[SimilarEmployee]:
        """
        查找相似的 AI 员工

        Args:
            employee_id: 参考员工 ID
            all_employees: 所有员工数据列表
            limit: 返回数量限制

        Returns:
            List[SimilarEmployee]: 相似员工列表
        """
        if employee_id not in self._graphs:
            return []

        similar_employees = []

        for emp in all_employees:
            if emp["id"] == employee_id:
                continue

            # 确保目标员工有图谱
            if emp["id"] not in self._graphs:
                self.build_graph(emp["id"], emp)

            similarity = self.calculate_similarity(employee_id, emp["id"])

            if similarity > 0.1:  # 阈值
                # 计算共同能力和独特能力
                graph1 = self._graphs[employee_id]
                graph2 = self._graphs[emp["id"]]

                skills1 = {node.name for node in graph1.nodes}
                skills2 = {node.name for node in graph2.nodes}

                similar_emp = SimilarEmployee(
                    employee_id=emp["id"],
                    employee_name=emp.get("name", "Unknown"),
                    similarity_score=round(similarity, 3),
                    common_capabilities=list(skills1 & skills2)[:5],
                    unique_capabilities=list(skills2 - skills1)[:5],
                    rating=emp.get("rating", 0.0),
                    hourly_rate=emp.get("hourly_rate", 0.0)
                )
                similar_employees.append(similar_emp)

        # 按相似度排序
        similar_employees.sort(key=lambda x: x.similarity_score, reverse=True)
        return similar_employees[:limit]

    def generate_evolution_path(
        self,
        request: EvolutionPathRequest,
        employee_data: Dict[str, Any]
    ) -> Optional[EvolutionPath]:
        """
        生成进化路径

        Args:
            request: 进化路径请求
            employee_data: 员工数据

        Returns:
            EvolutionPath: 进化路径
        """
        if request.employee_id not in self._graphs:
            self.build_graph(request.employee_id, employee_data)

        graph = self._graphs[request.employee_id]
        if not graph:
            return None

        # 当前状态
        current_state = {
            node.name: {
                "proficiency": node.proficiency,
                "category": node.category
            }
            for node in graph.nodes
        }

        # 目标状态（基于目标角色或自动推荐）
        target_state = self._determine_target_state(employee_data, request.target_role)

        # 生成步骤
        steps = self._generate_steps(graph, current_state, target_state, request.budget)

        return EvolutionPath(
            employee_id=request.employee_id,
            current_state=current_state,
            target_state=target_state,
            steps=steps,
            total_estimated_cost=sum(s.get("estimated_cost", 0) for s in steps),
            total_estimated_time=self._estimate_total_time(steps),
            expected_roi=self._calculate_expected_roi(current_state, target_state)
        )

    def _determine_target_state(
        self,
        employee_data: Dict[str, Any],
        target_role: Optional[str]
    ) -> Dict[str, Any]:
        """确定目标能力状态"""
        # 预定义的角色能力要求
        role_requirements = {
            "data_scientist": {
                "python": 0.9,
                "machine_learning": 0.8,
                "data_analysis": 0.9,
                "statistics": 0.8,
                "visualization": 0.7,
            },
            "nlp_engineer": {
                "python": 0.8,
                "nlp": 0.9,
                "machine_learning": 0.8,
                "deep_learning": 0.7,
                "pytorch": 0.7,
            },
            "full_stack_developer": {
                "javascript": 0.9,
                "python": 0.7,
                "react": 0.8,
                "nodejs": 0.8,
                "database": 0.7,
            },
            "ui_designer": {
                "design": 0.9,
                "ui_design": 0.9,
                "figma": 0.8,
                "prototyping": 0.7,
            },
        }

        if target_role and target_role in role_requirements:
            return role_requirements[target_role]

        # 自动推荐：在当前能力基础上提升 20%
        current_skills = employee_data.get("skills", {})
        target = {}
        for skill_name, skill_data in current_skills.items():
            current_prof = skill_data.get("proficiency", 0.0) if isinstance(skill_data, dict) else skill_data
            target[skill_name] = min(1.0, current_prof + 0.2)

        return target

    def _generate_steps(
        self,
        graph: CapabilityGraph,
        current_state: Dict[str, Any],
        target_state: Dict[str, Any],
        budget: Optional[float]
    ) -> List[Dict[str, Any]]:
        """生成进化步骤"""
        steps = []
        step_num = 1

        # 找出需要提升的技能
        for skill_name, target_prof in target_state.items():
            current_prof = current_state.get(skill_name, {}).get("proficiency", 0.0)

            if current_prof < target_prof:
                improvement_needed = target_prof - current_prof
                estimated_cost = improvement_needed * 100  # 简单估算
                estimated_hours = improvement_needed * 10

                steps.append({
                    "step": step_num,
                    "action": "training",
                    "capability": skill_name,
                    "current_proficiency": round(current_prof, 2),
                    "target_proficiency": round(target_prof, 2),
                    "estimated_cost": estimated_cost,
                    "estimated_time": f"{estimated_hours:.1f} hours",
                    "expected_improvement": round(improvement_needed, 2)
                })
                step_num += 1

        # 按成本效益排序（改进幅度/成本）
        steps.sort(key=lambda x: x["expected_improvement"] / max(x["estimated_cost"], 1), reverse=True)

        # 如果有限制预算，截断步骤
        if budget:
            total_cost = 0
            filtered_steps = []
            for step in steps:
                if total_cost + step["estimated_cost"] <= budget:
                    filtered_steps.append(step)
                    total_cost += step["estimated_cost"]
            steps = filtered_steps

        return steps

    def _estimate_total_time(self, steps: List[Dict[str, Any]]) -> str:
        """估算总时间"""
        total_hours = 0
        for step in steps:
            time_str = step.get("estimated_time", "0 hours")
            try:
                hours = float(time_str.split()[0])
                total_hours += hours
            except (ValueError, IndexError):
                pass

        if total_hours < 24:
            return f"{total_hours:.1f} hours"
        elif total_hours < 168:
            return f"{total_hours / 24:.1f} days"
        else:
            return f"{total_hours / 168:.1f} weeks"

    def _calculate_expected_roi(
        self,
        current_state: Dict[str, Any],
        target_state: Dict[str, Any]
    ) -> float:
        """计算预期投资回报率"""
        # 简单估算：能力提升幅度 * 100
        current_avg = sum(s.get("proficiency", 0) for s in current_state.values()) / max(len(current_state), 1)
        target_avg = sum(target_state.values()) / max(len(target_state), 1)

        improvement = target_avg - current_avg
        roi = improvement * 100  # 简化计算

        return round(roi, 2)

    def get_industry_benchmark(self, category: str) -> List[IndustryBenchmark]:
        """
        获取行业基准数据

        Args:
            category: 技能类别

        Returns:
            List[IndustryBenchmark]: 基准数据列表
        """
        # 模拟数据（实际应从数据库或外部 API 获取）
        benchmarks = {
            "technical": [
                IndustryBenchmark(
                    category="python",
                    avg_proficiency=0.65,
                    avg_training_count=15,
                    top_capabilities=[
                        {"name": "python", "demand_score": 0.9},
                        {"name": "sql", "demand_score": 0.8},
                        {"name": "api", "demand_score": 0.75},
                    ],
                    trending_capabilities=[
                        {"name": "pytorch", "growth_rate": 0.5},
                        {"name": "langchain", "growth_rate": 0.8},
                    ],
                    salary_range={"min": 8000, "max": 30000}
                ),
            ],
            "ai_specialized": [
                IndustryBenchmark(
                    category="machine_learning",
                    avg_proficiency=0.55,
                    avg_training_count=20,
                    top_capabilities=[
                        {"name": "machine_learning", "demand_score": 0.95},
                        {"name": "deep_learning", "demand_score": 0.85},
                        {"name": "nlp", "demand_score": 0.8},
                    ],
                    trending_capabilities=[
                        {"name": "llm", "growth_rate": 0.9},
                        {"name": "rag", "growth_rate": 0.7},
                    ],
                    salary_range={"min": 15000, "max": 50000}
                ),
            ],
        }

        return benchmarks.get(category, [])


# 单例
capability_graph_service = CapabilityGraphService()
