"""
第 3 轮迭代：P1 幻觉控制增强 - 置信度评分系统

增强功能：
1. 多维度置信度评分（语法、语义、事实）
2. 置信度可视化支持
3. 低置信度内容自动标记
4. 引用质量评估
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re


class ConfidenceLevel(Enum):
    """置信度等级"""
    HIGH = "high"       # 0.8-1.0
    MEDIUM = "medium"   # 0.6-0.8
    LOW = "low"         # 0.4-0.6
    VERY_LOW = "very_low"  # 0.0-0.4


@dataclass
class ConfidenceScore:
    """置信度评分详情"""
    overall: float  # 综合置信度 0-1
    level: ConfidenceLevel  # 置信度等级

    # 分项评分
    syntax_score: float = 1.0      # 语法准确性
    semantic_score: float = 1.0    # 语义一致性
    fact_score: float = 1.0        # 事实准确性
    citation_score: float = 1.0    # 引用质量

    # 评分详情
    scoring_details: Dict[str, Any] = field(default_factory=dict)

    # 风险标记
    risk_flags: List[str] = field(default_factory=list)

    @classmethod
    def compute(
        cls,
        syntax: float = 1.0,
        semantic: float = 1.0,
        fact: float = 1.0,
        citation: float = 1.0,
        weights: Optional[Dict[str, float]] = None
    ) -> "ConfidenceScore":
        """
        计算综合置信度

        默认权重：
        - 事实准确性：40%
        - 引用质量：30%
        - 语义一致性：20%
        - 语法准确性：10%
        """
        weights = weights or {
            'fact': 0.4,
            'citation': 0.3,
            'semantic': 0.2,
            'syntax': 0.1
        }

        # 加权平均
        overall = (
            fact * weights['fact'] +
            citation * weights['citation'] +
            semantic * weights['semantic'] +
            syntax * weights['syntax']
        )

        # 确定等级
        if overall >= 0.8:
            level = ConfidenceLevel.HIGH
        elif overall >= 0.6:
            level = ConfidenceLevel.MEDIUM
        elif overall >= 0.4:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.VERY_LOW

        return cls(
            overall=round(overall, 3),
            level=level,
            syntax_score=round(syntax, 3),
            semantic_score=round(semantic, 3),
            fact_score=round(fact, 3),
            citation_score=round(citation, 3),
            scoring_details={
                'weights': weights,
                'weighted_sum': {
                    'fact': round(fact * weights['fact'], 3),
                    'citation': round(citation * weights['citation'], 3),
                    'semantic': round(semantic * weights['semantic'], 3),
                    'syntax': round(syntax * weights['syntax'], 3)
                }
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall': self.overall,
            'level': self.level.value,
            'scores': {
                'syntax': self.syntax_score,
                'semantic': self.semantic_score,
                'fact': self.fact_score,
                'citation': self.citation_score
            },
            'scoring_details': self.scoring_details,
            'risk_flags': self.risk_flags
        }

    def to_visualization_data(self) -> Dict[str, Any]:
        """生成可视化数据"""
        return {
            'gauge': {
                'value': self.overall,
                'min': 0,
                'max': 1,
                'ranges': [
                    {'min': 0, 'max': 0.4, 'color': '#ef4444', 'label': '极低'},
                    {'min': 0.4, 'max': 0.6, 'color': '#f59e0b', 'label': '低'},
                    {'min': 0.6, 'max': 0.8, 'color': '#3b82f6', 'label': '中'},
                    {'min': 0.8, 'max': 1.0, 'color': '#22c55e', 'label': '高'}
                ]
            },
            'radar': {
                'dimensions': [
                    {'name': '语法', 'value': self.syntax_score},
                    {'name': '语义', 'value': self.semantic_score},
                    {'name': '事实', 'value': self.fact_score},
                    {'name': '引用', 'value': self.citation_score}
                ]
            },
            'level': self.level.value,
            'risk_flags': self.risk_flags
        }


@dataclass
class CitationQuality:
    """引用质量评估"""
    total_citations: int = 0
    high_quality: int = 0      # similarity > 0.8
    medium_quality: int = 0    # similarity 0.6-0.8
    low_quality: int = 0       # similarity < 0.6

    coverage_ratio: float = 0.0  # 内容被引用覆盖的比例
    avg_similarity: float = 0.0  # 平均相似度

    def compute_score(self) -> float:
        """计算引用质量分数"""
        if self.total_citations == 0:
            return 0.0

        # 质量加权
        quality_score = (
            self.high_quality * 1.0 +
            self.medium_quality * 0.7 +
            self.low_quality * 0.3
        ) / self.total_citations

        # 覆盖率因子
        coverage_factor = min(1.0, self.coverage_ratio * 1.5)

        return round(quality_score * 0.6 + coverage_factor * 0.4, 3)


class EnhancedHallucinationValidator:
    """
    增强版幻觉验证器
    在原有基础上增加置信度评分和可视化支持
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.thresholds = {
            'high_confidence': self.config.get('high_confidence_threshold', 0.8),
            'medium_confidence': self.config.get('medium_confidence_threshold', 0.6),
            'low_confidence': self.config.get('low_confidence_threshold', 0.4),
            'min_citation_similarity': self.config.get('min_citation_similarity', 0.6),
        }

        # 风险模式检测
        self.risk_patterns = {
            'strong_claim': [r'肯定', r'一定', r'绝对', r'必然', r'毫无疑问'],
            'vague_reference': [r'可能', r'也许', r'大概', r'似乎'],
            'unverifiable': [r'据说', r'听说', r'有人说'],
            'future_claim': [r'将会', r'将要', r'预计'],
        }

    def compute_confidence(
        self,
        content: str,
        citations: List[Dict[str, Any]],
        validation_errors: List[str],
        validation_warnings: List[str]
    ) -> ConfidenceScore:
        """
        计算综合置信度

        Args:
            content: 生成内容
            citations: 引用列表
            validation_errors: 验证错误
            validation_warnings: 验证警告

        Returns:
            ConfidenceScore: 置信度评分
        """
        # 1. 语法评分 - 基于错误数量
        syntax_score = max(0.0, 1.0 - len(validation_errors) * 0.15)

        # 2. 语义评分 - 基于警告数量
        semantic_score = max(0.0, 1.0 - len(validation_warnings) * 0.1)

        # 3. 事实评分 - 基于风险模式检测
        fact_score = self._compute_fact_score(content)

        # 4. 引用评分 - 基于引用质量
        citation_score = self._compute_citation_score(citations, content)

        # 综合计算
        confidence = ConfidenceScore.compute(
            syntax=syntax_score,
            semantic=semantic_score,
            fact=fact_score,
            citation=citation_score
        )

        # 添加风险标记
        confidence.risk_flags = self._detect_risks(content, validation_errors, validation_warnings)

        # 存储详情
        confidence.scoring_details.update({
            'content_length': len(content),
            'citation_count': len(citations),
            'error_count': len(validation_errors),
            'warning_count': len(validation_warnings)
        })

        return confidence

    def _compute_fact_score(self, content: str) -> float:
        """计算事实准确性分数"""
        score = 1.0

        # 检测风险模式
        for risk_type, patterns in self.risk_patterns.items():
            for pattern in patterns:
                if pattern in content:
                    if risk_type == 'strong_claim':
                        score -= 0.05  # 过于确定的陈述
                    elif risk_type == 'vague_reference':
                        score -= 0.03  # 模糊引用
                    elif risk_type == 'unverifiable':
                        score -= 0.1   # 无法验证
                    elif risk_type == 'future_claim':
                        score -= 0.02  # 未来声明

        return max(0.0, score)

    def _compute_citation_score(self, citations: List[Dict[str, Any]], content: str) -> float:
        """计算引用质量分数"""
        if not citations:
            return 0.3  # 无引用但内容可能仍然正确

        quality = CitationQuality(
            total_citations=len(citations)
        )

        # 分析引用质量
        for cit in citations:
            sim = cit.get('similarity', 0)
            if sim >= 0.8:
                quality.high_quality += 1
            elif sim >= 0.6:
                quality.medium_quality += 1
            else:
                quality.low_quality += 1

        # 计算平均相似度
        quality.avg_similarity = sum(c.get('similarity', 0) for c in citations) / len(citations)

        # 估算覆盖率
        sentence_count = len(re.split(r'[。？！\n]', content))
        quality.coverage_ratio = min(1.0, len(citations) / max(1, sentence_count))

        return quality.compute_score()

    def _detect_risks(
        self,
        content: str,
        errors: List[str],
        warnings: List[str]
    ) -> List[str]:
        """检测风险标记"""
        risks = []

        # 错误风险
        if errors:
            risks.append(f"发现 {len(errors)} 个事实错误")

        # 警告风险
        if warnings:
            risks.append(f"发现 {len(warnings)} 个潜在问题")

        # 无引用风险
        if '引用' in content and '没有' in content:
            risks.append("内容声称有引用但实际未找到")

        # 风险模式
        for risk_type, patterns in self.risk_patterns.items():
            for pattern in patterns:
                if pattern in content:
                    risks.append(f"检测到{risk_type}表述")
                    break

        return risks

    def generate_confidence_report(
        self,
        content: str,
        confidence: ConfidenceScore,
        citations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成置信度报告"""
        return {
            'summary': {
                'overall_confidence': confidence.overall,
                'level': confidence.level.value,
                'recommendation': self._get_recommendation(confidence)
            },
            'detailed_scores': confidence.to_dict(),
            'visualization': confidence.to_visualization_data(),
            'citations': {
                'total': len(citations),
                'high_quality': sum(1 for c in citations if c.get('similarity', 0) >= 0.8),
                'list': citations[:5]  # 最多 5 个引用
            },
            'risks': confidence.risk_flags,
            'suggestions': self._generate_suggestions(confidence, citations)
        }

    def _get_recommendation(self, confidence: ConfidenceScore) -> str:
        """获取推荐操作"""
        if confidence.level == ConfidenceLevel.HIGH:
            return "内容可信度高，可直接使用"
        elif confidence.level == ConfidenceLevel.MEDIUM:
            return "内容基本可信，建议人工复核"
        elif confidence.level == ConfidenceLevel.LOW:
            return "内容可信度低，需要谨慎使用"
        else:
            return "内容可信度极低，不建议使用"

    def _generate_suggestions(
        self,
        confidence: ConfidenceScore,
        citations: List[Dict[str, Any]]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if confidence.citation_score < 0.6:
            suggestions.append("增加更多代码引用以增强可信度")

        if confidence.fact_score < 0.6:
            suggestions.append("避免使用过于绝对的表述")

        if confidence.semantic_score < 0.6:
            suggestions.append("检查语义一致性，确保描述与代码相符")

        if confidence.syntax_score < 0.6:
            suggestions.append("修正已识别的事实错误")

        if not citations:
            suggestions.append("添加代码引用以支持论述")

        return suggestions


# 便捷函数
def create_confidence_display(
    confidence: ConfidenceScore,
    format: str = 'json'
) -> str:
    """生成置信度展示"""
    data = confidence.to_visualization_data()

    if format == 'json':
        return json.dumps(data, indent=2, ensure_ascii=False)

    elif format == 'text':
        lines = [
            "=" * 40,
            f"置信度评分：{confidence.overall:.1%}",
            f"等级：{confidence.level.value}",
            "-" * 40,
            f"语法准确性：{confidence.syntax_score:.1%}",
            f"语义一致性：{confidence.semantic_score:.1%}",
            f"事实准确性：{confidence.fact_score:.1%}",
            f"引用质量：  {confidence.citation_score:.1%}",
            "-" * 40,
        ]
        if confidence.risk_flags:
            lines.append("风险标记:")
            for flag in confidence.risk_flags:
                lines.append(f"  ⚠️ {flag}")
        lines.append("=" * 40)
        return "\n".join(lines)

    return json.dumps(data, indent=2, ensure_ascii=False)
