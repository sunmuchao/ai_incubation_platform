"""
代码变更影响分析器

功能:
1. 分析代码变更的影响范围
2. 基于依赖图识别受影响的模块
3. 提供测试建议和风险评估
4. 支持变更影响评分
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ImpactLevel(Enum):
    """影响级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImpactType(Enum):
    """影响类型"""
    DIRECT = "direct"  # 直接影响
    TRANSITIVE = "transitive"  # 传递影响
    CIRCULAR = "circular"  # 循环依赖影响


class ImpactAnalysis:
    """影响分析结果"""

    def __init__(self, changed_file: str):
        self.changed_file = changed_file
        self.affected_files: List[Dict[str, Any]] = []
        self.impact_level: ImpactLevel = ImpactLevel.LOW
        self.impact_score: float = 0.0
        self.risk_factors: List[str] = []
        self.test_suggestions: List[str] = []
        self.summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "changed_file": self.changed_file,
            "affected_files": self.affected_files,
            "impact_level": self.impact_level.value,
            "impact_score": self.impact_score,
            "risk_factors": self.risk_factors,
            "test_suggestions": self.test_suggestions,
            "summary": self.summary
        }


class ChangeImpactAnalyzer:
    """
    变更影响分析器

    基于依赖图分析代码变更的影响范围
    """

    def __init__(
        self,
        dependency_graph: Any,
        index_pipeline: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.dependency_graph = dependency_graph
        self.index_pipeline = index_pipeline
        self.config = config or {}

        # 核心模块阈值（被依赖数超过此值为核心模块）
        self.core_module_threshold = self.config.get('core_module_threshold', 5)

        # 影响评分权重
        self.weights = {
            "direct_dependency": 1.0,
            "transitive_dependency": 0.5,
            "core_module": 2.0,
            "entrypoint": 3.0,
            "test_file": 0.3,
        }

    def analyze(
        self,
        changed_file: str,
        change_type: str = "modification",
        changed_symbols: Optional[List[str]] = None
    ) -> ImpactAnalysis:
        """
        分析变更影响

        Args:
            changed_file: 变更的文件路径
            change_type: 变更类型 (modification, deletion, addition)
            changed_symbols: 变更的符号列表（可选，用于更精确的分析）
        """
        analysis = ImpactAnalysis(changed_file)

        # 1. 获取直接依赖该文件的模块
        direct_dependents = self._get_direct_dependents(changed_file)
        for dep in direct_dependents:
            node = self.dependency_graph.nodes.get(dep, {})
            analysis.affected_files.append({
                "file": dep,
                "impact_type": ImpactType.DIRECT.value,
                "distance": 1,
                "node_type": getattr(node, 'node_type', 'module') if hasattr(node, 'node_type') else 'module',
                "in_degree": getattr(node, 'in_degree', 0) if hasattr(node, 'in_degree') else 0
            })

        # 2. 获取传递依赖（2 层以内）
        transitive_dependents = self._get_transitive_dependents(changed_file, max_depth=2)
        existing_files = {f["file"] for f in analysis.affected_files}
        for dep in transitive_dependents:
            if dep not in existing_files:
                node = self.dependency_graph.nodes.get(dep, {})
                analysis.affected_files.append({
                    "file": dep,
                    "impact_type": ImpactType.TRANSITIVE.value,
                    "distance": 2,
                    "node_type": getattr(node, 'node_type', 'module') if hasattr(node, 'node_type') else 'module',
                    "in_degree": getattr(node, 'in_degree', 0) if hasattr(node, 'in_degree') else 0
                })

        # 3. 检查是否影响入口点
        entrypoints_affected = self._check_entrypoints_affected(changed_file)

        # 4. 计算影响评分
        analysis.impact_score = self._calculate_impact_score(analysis.affected_files, entrypoints_affected)

        # 5. 确定影响级别
        analysis.impact_level = self._determine_impact_level(analysis.impact_score)

        # 6. 识别风险因素
        analysis.risk_factors = self._identify_risk_factors(
            changed_file,
            analysis.affected_files,
            change_type,
            entrypoints_affected
        )

        # 7. 生成测试建议
        analysis.test_suggestions = self._generate_test_suggestions(
            changed_file,
            analysis.affected_files,
            changed_symbols
        )

        # 8. 生成摘要
        analysis.summary = self._generate_summary(analysis)

        return analysis

    def _get_direct_dependents(self, file_path: str) -> Set[str]:
        """获取直接依赖该文件的模块"""
        return self.dependency_graph.get_dependents(file_path, recursive=False)

    def _get_transitive_dependents(self, file_path: str, max_depth: int = 2) -> Set[str]:
        """获取传递依赖的模块"""
        return self.dependency_graph.get_dependents(file_path, recursive=True)

    def _check_entrypoints_affected(self, changed_file: str) -> List[str]:
        """检查是否影响入口点"""
        affected_entrypoints = []
        for file_path, node in self.dependency_graph.nodes.items():
            if hasattr(node, 'node_type') and node.node_type == 'entrypoint':
                if file_path in self.dependency_graph.get_dependents(changed_file):
                    affected_entrypoints.append(file_path)
        return affected_entrypoints

    def _calculate_impact_score(
        self,
        affected_files: List[Dict[str, Any]],
        entrypoints_affected: List[str]
    ) -> float:
        """
        计算影响评分

        评分基于：
        - 直接影响数量 x 1.0
        - 传递影响数量 x 0.5
        - 核心模块 x 2.0
        - 入口点 x 3.0
        """
        score = 0.0

        for file_info in affected_files:
            base_score = self.weights.get(f"file_{file_info['impact_type']}", 1.0)

            # 核心模块加权
            if file_info.get('in_degree', 0) >= self.core_module_threshold:
                base_score *= self.weights["core_module"]

            # 入口点加权
            if file_info.get('node_type') == 'entrypoint':
                base_score *= self.weights["entrypoint"]

            score += base_score

        # 入口点额外加分
        score += len(entrypoints_affected) * self.weights["entrypoint"]

        return round(score, 2)

    def _determine_impact_level(self, score: float) -> ImpactLevel:
        """根据评分确定影响级别"""
        if score >= 20:
            return ImpactLevel.CRITICAL
        elif score >= 10:
            return ImpactLevel.HIGH
        elif score >= 3:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW

    def _identify_risk_factors(
        self,
        changed_file: str,
        affected_files: List[Dict[str, Any]],
        change_type: str,
        entrypoints_affected: List[str]
    ) -> List[str]:
        """识别风险因素"""
        risks = []

        # 删除操作风险
        if change_type == 'deletion':
            risks.append("文件删除操作，可能导致依赖该文件的模块失效")

        # 影响入口点
        if entrypoints_affected:
            risks.append(f"影响入口点：{', '.join(Path(e).name for e in entrypoints_affected)}")

        # 影响范围广
        if len(affected_files) > 10:
            risks.append(f"影响范围较大，共 {len(affected_files)} 个文件")

        # 核心模块变更
        for file_info in affected_files:
            if file_info.get('in_degree', 0) >= self.core_module_threshold:
                risks.append(f"核心模块 {Path(file_info['file']).name} 受影响")

        # 循环依赖风险
        cycles = self.dependency_graph.detect_cycles()
        for cycle in cycles:
            if changed_file in cycle:
                risks.append("变更文件位于循环依赖中")
                break

        # 变更类型风险
        if change_type == 'addition':
            risks.append("新增文件，需确认是否被正确导入使用")

        return risks

    def _generate_test_suggestions(
        self,
        changed_file: str,
        affected_files: List[Dict[str, Any]],
        changed_symbols: Optional[List[str]]
    ) -> List[str]:
        """生成测试建议"""
        suggestions = []

        # 直接影响的文件需要测试
        direct_files = [f for f in affected_files if f.get('impact_type') == 'direct']
        if direct_files:
            suggestions.append(f"优先测试直接依赖的 {len(direct_files)} 个模块")

        # 如果有变更符号，提供针对性建议
        if changed_symbols:
            symbol_names = [s.split(':')[-1] for s in changed_symbols if ':' in s]
            if symbol_names:
                suggestions.append(f"重点回归测试涉及的符号：{', '.join(symbol_names[:5])}")

        # 入口点相关的测试
        entrypoint_files = [f for f in affected_files if f.get('node_type') == 'entrypoint']
        if entrypoint_files:
            suggestions.append(f"入口点受影响，需进行端到端测试")

        # 影响范围广时的建议
        if len(affected_files) > 5:
            suggestions.append("影响范围较广，建议进行全面的回归测试")

        # 根据文件类型提供建议
        ext = Path(changed_file).suffix.lower()
        if ext == '.py':
            suggestions.append("运行 Python 单元测试：pytest tests/")
        elif ext in ['.js', '.ts']:
            suggestions.append("运行前端测试：npm test")

        return suggestions

    def _generate_summary(self, analysis: ImpactAnalysis) -> str:
        """生成摘要"""
        parts = []

        # 影响级别
        parts.append(f"影响级别：{analysis.impact_level.value.upper()}")

        # 影响范围
        direct_count = len([f for f in analysis.affected_files if f.get('impact_type') == 'direct'])
        transitive_count = len([f for f in analysis.affected_files if f.get('impact_type') == 'transitive'])
        parts.append(f"直接影响 {direct_count} 个模块，间接影响 {transitive_count} 个模块")

        # 风险因素
        if analysis.risk_factors:
            parts.append(f"风险因素：{len(analysis.risk_factors)} 项")

        # 测试建议
        if analysis.test_suggestions:
            parts.append(f"测试建议：{len(analysis.test_suggestions)} 项")

        return " | ".join(parts)

    def analyze_batch(
        self,
        changed_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量分析多个变更文件的影响

        Args:
            changed_files: [{file_path, change_type, symbols}, ...]
        """
        results = {}
        total_impact_score = 0.0
        all_affected_files = set()

        for file_info in changed_files:
            file_path = file_info.get('file_path', file_info.get('file'))
            change_type = file_info.get('change_type', 'modification')
            symbols = file_info.get('symbols')

            analysis = self.analyze(file_path, change_type, symbols)
            results[file_path] = analysis.to_dict()

            total_impact_score += analysis.impact_score
            for f in analysis.affected_files:
                all_affected_files.add(f['file'])

        return {
            "changed_files_count": len(changed_files),
            "total_impact_score": round(total_impact_score, 2),
            "total_affected_files": len(all_affected_files),
            "analyses": results,
            "overall_risk": self._determine_impact_level(total_impact_score).value
        }


# 便捷函数
def create_impact_analyzer(
    dependency_graph: Any,
    index_pipeline: Optional[Any] = None
) -> ChangeImpactAnalyzer:
    """创建影响分析器实例"""
    return ChangeImpactAnalyzer(
        dependency_graph=dependency_graph,
        index_pipeline=index_pipeline
    )
