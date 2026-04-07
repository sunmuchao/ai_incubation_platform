"""
AI 优化建议生成引擎

功能:
- 基于数据分析生成针对性优化建议
- 建议优先级排序
- 预期效果评估
- 可执行行动方案
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from enum import Enum
import logging

from .anomaly_detection import AnomalyDetectionResult, AnomalyType, AnomalySeverity
from .root_cause_analysis import RootCauseAnalysisResult, RootCause, RootCauseCategory

logger = logging.getLogger(__name__)


class SuggestionType(str, Enum):
    """建议类型"""
    SEO_OPTIMIZATION = "seo_optimization"       # SEO 优化
    CONTENT_IMPROVEMENT = "content_improvement"  # 内容改进
    TECHNICAL_FIX = "technical_fix"             # 技术修复
    UX_IMPROVEMENT = "ux_improvement"           # 用户体验优化
    TRAFFIC_ACQUISITION = "traffic_acquisition" # 流量获取
    CONVERSION_OPTIMIZATION = "conversion_optimization"  # 转化优化
    PERFORMANCE_IMPROVEMENT = "performance_improvement"  # 性能优化


class SuggestionPriority(str, Enum):
    """建议优先级"""
    CRITICAL = "critical"  # 紧急，需立即处理
    HIGH = "high"          # 高优先级
    MEDIUM = "medium"      # 中优先级
    LOW = "low"            # 低优先级


class SuggestionEffort(str, Enum):
    """实施难度"""
    LOW = "low"        # 低难度，可快速实施
    MEDIUM = "medium"  # 中等难度
    HIGH = "high"      # 高难度，需要较多资源


class OptimizationSuggestion:
    """优化建议"""
    def __init__(
        self,
        suggestion_id: str,
        title: str,
        description: str,
        suggestion_type: SuggestionType,
        priority: SuggestionPriority,
        effort: SuggestionEffort,
        expected_impact: float,  # 预期提升百分比 0-1
        confidence: float,       # 建议置信度 0-1
        action_steps: List[str],
        related_metrics: List[str],
        estimated_timeline: str,  # 预计实施时间
        data_evidence: List[str]
    ):
        self.suggestion_id = suggestion_id
        self.title = title
        self.description = description
        self.suggestion_type = suggestion_type
        self.priority = priority
        self.effort = effort
        self.expected_impact = expected_impact
        self.confidence = confidence
        self.action_steps = action_steps
        self.related_metrics = related_metrics
        self.estimated_timeline = estimated_timeline
        self.data_evidence = data_evidence
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "title": self.title,
            "description": self.description,
            "suggestion_type": self.suggestion_type.value,
            "priority": self.priority.value,
            "effort": self.effort.value,
            "expected_impact": round(self.expected_impact, 4),
            "confidence": round(self.confidence, 2),
            "action_steps": self.action_steps,
            "related_metrics": self.related_metrics,
            "estimated_timeline": self.estimated_timeline,
            "data_evidence": self.data_evidence,
            "created_at": self.created_at.isoformat()
        }


class RecommendationEngine:
    """
    AI 优化建议生成引擎

    基于异常检测和根因分析结果，生成可执行的优化建议
    """

    def __init__(self):
        self._suggestion_counter = 0
        # 建议模板库
        self._suggestion_templates = self._initialize_templates()

    def _initialize_templates(self) -> Dict[str, List[Dict]]:
        """初始化建议模板"""
        return {
            SuggestionType.SEO_OPTIMIZATION.value: [
                {
                    "title": "优化页面 Title 和 Meta Description",
                    "description": "更新页面的标题标签和 Meta 描述，使其更具吸引力并包含目标关键词",
                    "action_steps": [
                        "分析当前 Title 和 Meta Description 的长度和质量",
                        "确保 Title 包含核心关键词且不超过 60 字符",
                        "编写吸引人的 Meta Description(150-160 字符)",
                        "确保每个页面有唯一的 Title 和 Meta"
                    ],
                    "estimated_timeline": "1-2 天",
                    "effort": SuggestionEffort.LOW.value
                },
                {
                    "title": "改进内部链接结构",
                    "description": "优化网站内部链接，提升页面权重传递和爬虫抓取效率",
                    "action_steps": [
                        "审核现有内部链接结构",
                        "在相关内容间添加上下文链接",
                        "优化导航菜单和面包屑",
                        "创建站点地图并提交到 Google"
                    ],
                    "estimated_timeline": "3-5 天",
                    "effort": SuggestionEffort.MEDIUM.value
                }
            ],
            SuggestionType.CONTENT_IMPROVEMENT.value: [
                {
                    "title": "扩展优质内容长度",
                    "description": "增加内容深度和覆盖面，提升页面价值",
                    "action_steps": [
                        "分析竞品内容长度和结构",
                        "添加更多实用信息和案例",
                        "使用图表、列表等丰富内容形式",
                        "确保内容覆盖用户搜索意图"
                    ],
                    "estimated_timeline": "3-7 天",
                    "effort": SuggestionEffort.MEDIUM.value
                }
            ],
            SuggestionType.CONVERSION_OPTIMIZATION.value: [
                {
                    "title": "优化 CTA 按钮",
                    "description": "改进行动号召按钮的设计、文案和位置",
                    "action_steps": [
                        "分析当前 CTA 的点击率数据",
                        "测试不同的 CTA 文案（如'立即开始'vs'免费试用'）",
                        "优化 CTA 按钮颜色和尺寸对比",
                        "将 CTA 放置在更显著的位置"
                    ],
                    "estimated_timeline": "2-3 天",
                    "effort": SuggestionEffort.LOW.value
                },
                {
                    "title": "简化转化流程",
                    "description": "减少转化流程中的步骤和摩擦点",
                    "action_steps": [
                        "绘制当前转化流程图",
                        "识别并移除不必要的步骤",
                        "减少表单填写字段",
                        "添加进度指示器"
                    ],
                    "estimated_timeline": "5-10 天",
                    "effort": SuggestionEffort.HIGH.value
                }
            ],
            SuggestionType.TRAFFIC_ACQUISITION.value: [
                {
                    "title": "拓展长尾关键词",
                    "description": "针对搜索量较低但竞争小的长尾关键词进行优化",
                    "action_steps": [
                        "使用关键词工具发现长尾机会",
                        "创建针对性的内容页面",
                        "在现有内容中自然融入长尾词",
                        "监控长尾词排名和流量变化"
                    ],
                    "estimated_timeline": "1-2 周",
                    "effort": SuggestionEffort.MEDIUM.value
                }
            ]
        }

    def generate_suggestions(
        self,
        analysis_result: RootCauseAnalysisResult,
        context: Optional[Dict[str, Any]] = None
    ) -> List[OptimizationSuggestion]:
        """
        基于根因分析结果生成优化建议

        Args:
            analysis_result: 根因分析结果
            context: 上下文信息

        Returns:
            优化建议列表
        """
        suggestions = []

        # 根据根因类别生成对应建议
        for root_cause in analysis_result.root_causes:
            cause_suggestions = self._generate_suggestions_for_cause(root_cause, analysis_result.anomaly)
            suggestions.extend(cause_suggestions)

        # 根据异常类型生成通用建议
        anomaly_suggestions = self._generate_suggestions_for_anomaly(analysis_result.anomaly)
        suggestions.extend(anomaly_suggestions)

        # 去重和优先级排序
        suggestions = self._deduplicate_and_sort(suggestions)

        return suggestions

    def generate_proactive_suggestions(
        self,
        domain: Optional[str] = None,
        check_date: Optional[date] = None
    ) -> List[OptimizationSuggestion]:
        """
        生成主动优化建议（无异常时也提供改进建议）

        Args:
            domain: 域名
            check_date: 检查日期

        Returns:
            主动优化建议列表
        """
        suggestions = []

        # 生成常规的 SEO 优化建议
        suggestions.append(self._create_suggestion(
            suggestion_type=SuggestionType.SEO_OPTIMIZATION,
            title="定期进行 SEO 健康检查",
            description="建立定期的 SEO 健康检查机制，持续监控和优化网站 SEO 表现",
            priority=SuggestionPriority.MEDIUM,
            effort=SuggestionEffort.LOW,
            expected_impact=0.1,
            confidence=0.8,
            action_steps=[
                "每周检查 Google Search Console 的错误和警告",
                "每月审核核心关键词排名变化",
                "每季度进行全面的 SEO 审计",
                "建立 SEO 问题响应流程"
            ],
            related_metrics=["seo_score", "keyword_rankings", "organic_traffic"],
            estimated_timeline="持续进行",
            data_evidence=["定期 SEO 检查可预防 80% 的严重 SEO 问题"]
        ))

        # 生成内容优化建议
        suggestions.append(self._create_suggestion(
            suggestion_type=SuggestionType.CONTENT_IMPROVEMENT,
            title="创建内容更新计划",
            description="定期更新现有内容，保持内容的新鲜度和相关性",
            priority=SuggestionPriority.MEDIUM,
            effort=SuggestionEffort.MEDIUM,
            expected_impact=0.15,
            confidence=0.75,
            action_steps=[
                "识别需要更新的高流量旧内容",
                "更新过时的统计数据和引用",
                "添加新的见解和案例",
                "重新发布并推广更新后的内容"
            ],
            related_metrics=["page_views", "avg_time_on_page", "keyword_rankings"],
            estimated_timeline="每月更新 2-4 篇",
            data_evidence=["更新旧内容可带来平均 110% 的流量增长"]
        ))

        return suggestions

    def _generate_suggestions_for_cause(
        self,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult
    ) -> List[OptimizationSuggestion]:
        """根据根因生成建议"""
        suggestions = []

        if root_cause.category == RootCauseCategory.KEYWORD_RANKING:
            suggestions.append(self._create_suggestion(
                suggestion_type=SuggestionType.SEO_OPTIMIZATION,
                title="优化下滑关键词的页面内容",
                description=f"针对排名下滑的关键词进行内容优化，恢复并提升排名",
                priority=SuggestionPriority.HIGH,
                effort=SuggestionEffort.MEDIUM,
                expected_impact=0.2,
                confidence=0.8,
                action_steps=[
                    "分析下滑关键词的搜索意图",
                    "对比排名靠前竞品的内容",
                    "优化页面内容以更好满足用户需求",
                    "增加相关内部链接",
                    "考虑添加多媒体内容增强体验"
                ],
                related_metrics=["keyword_rankings", "organic_traffic", "page_views"],
                estimated_timeline="1-2 周",
                data_evidence=root_cause.evidence
            ))

        elif root_cause.category == RootCauseCategory.TRAFFIC_SOURCE:
            suggestions.append(self._create_suggestion(
                suggestion_type=SuggestionType.TRAFFIC_ACQUISITION,
                title="恢复下滑的流量来源渠道",
                description="针对表现下滑的流量来源制定恢复策略",
                priority=SuggestionPriority.HIGH,
                effort=SuggestionEffort.MEDIUM,
                expected_impact=0.25,
                confidence=0.75,
                action_steps=root_cause.recommended_actions,
                related_metrics=["traffic_sources", "visitors"],
                estimated_timeline="2-4 周",
                data_evidence=root_cause.evidence
            ))

        elif root_cause.category == RootCauseCategory.PAGE_PERFORMANCE:
            suggestions.append(self._create_suggestion(
                suggestion_type=SuggestionType.SEO_OPTIMIZATION,
                title="提升低分页面的 SEO 质量",
                description="针对 SEO 分数偏低的页面进行系统性优化",
                priority=SuggestionPriority.MEDIUM,
                effort=SuggestionEffort.MEDIUM,
                expected_impact=0.15,
                confidence=0.8,
                action_steps=[
                    "审核页面 Title 和 Meta Description",
                    "优化 heading 结构 (H1/H2/H3)",
                    "增加高质量原创内容",
                    "优化图片 alt 文本",
                    "改善页面加载速度"
                ],
                related_metrics=["seo_score", "page_views", "exit_rate"],
                estimated_timeline="1-2 周",
                data_evidence=root_cause.evidence
            ))

        elif root_cause.category == RootCauseCategory.CONTENT_ISSUE:
            suggestions.append(self._create_suggestion(
                suggestion_type=SuggestionType.CONTENT_IMPROVEMENT,
                title="改善内容质量和用户匹配度",
                description="优化内容以更好匹配用户搜索意图，降低跳出率",
                priority=SuggestionPriority.HIGH,
                effort=SuggestionEffort.HIGH,
                expected_impact=0.2,
                confidence=0.7,
                action_steps=[
                    "分析用户搜索意图与内容匹配度",
                    "优化内容结构和可读性",
                    "在首屏提供核心价值信息",
                    "添加相关内容推荐",
                    "增加互动元素提升参与度"
                ],
                related_metrics=["bounce_rate", "avg_time_on_page", "pages_per_session"],
                estimated_timeline="2-3 周",
                data_evidence=root_cause.evidence
            ))

        # 添加根因对应的建议
        for action in root_cause.recommended_actions[:3]:
            suggestions.append(self._create_suggestion(
                suggestion_type=self._map_category_to_type(root_cause.category),
                title=action,
                description=f"针对{root_cause.description}的执行建议",
                priority=self._map_confidence_to_priority(root_cause.confidence),
                effort=SuggestionEffort.MEDIUM,
                expected_impact=root_cause.impact_score * 0.5,
                confidence=0.7,
                action_steps=[action],
                related_metrics=[root_cause.category.value],
                estimated_timeline="3-5 天",
                data_evidence=root_cause.evidence
            ))

        return suggestions

    def _generate_suggestions_for_anomaly(
        self,
        anomaly: AnomalyDetectionResult
    ) -> List[OptimizationSuggestion]:
        """根据异常类型生成通用建议"""
        suggestions = []

        if anomaly.anomaly_type == AnomalyType.TRAFFIC_DROP:
            suggestions.append(self._create_suggestion(
                suggestion_type=SuggestionType.TRAFFIC_ACQUISITION,
                title="启动流量恢复应急计划",
                description="针对流量显著下跌启动应急响应机制",
                priority=SuggestionPriority.CRITICAL if anomaly.severity == AnomalySeverity.CRITICAL else SuggestionPriority.HIGH,
                effort=SuggestionEffort.HIGH,
                expected_impact=0.3,
                confidence=0.75,
                action_steps=[
                    "立即检查 Google Search Console 是否有惩罚通知",
                    "确认网站技术问题（服务器、DNS、robots.txt）",
                    "分析竞品流量是否同期变化",
                    "检查是否有季节性因素影响",
                    "回顾近期网站改动历史"
                ],
                related_metrics=["visitors", "page_views", "organic_traffic"],
                estimated_timeline="1-2 周",
                data_evidence=[anomaly.description]
            ))

        elif anomaly.anomaly_type == AnomalyType.CONVERSION_DROP:
            suggestions.append(self._create_suggestion(
                suggestion_type=SuggestionType.CONVERSION_OPTIMIZATION,
                title="排查转化漏斗问题",
                description="针对转化率下跌进行漏斗分析和优化",
                priority=SuggestionPriority.HIGH,
                effort=SuggestionEffort.MEDIUM,
                expected_impact=0.25,
                confidence=0.7,
                action_steps=[
                    "分析转化漏斗各步骤的流失率变化",
                    "检查转化流程是否有技术故障",
                    "测试不同设备和浏览器的转化流程",
                    "调研用户反馈和投诉",
                    "进行 A/B 测试寻找最优方案"
                ],
                related_metrics=["conversion_rate", "bounce_rate", "exit_rate"],
                estimated_timeline="1-2 周",
                data_evidence=[anomaly.description]
            ))

        return suggestions

    def _create_suggestion(
        self,
        suggestion_type: SuggestionType,
        title: str,
        description: str,
        priority: SuggestionPriority,
        effort: SuggestionEffort,
        expected_impact: float,
        confidence: float,
        action_steps: List[str],
        related_metrics: List[str],
        estimated_timeline: str,
        data_evidence: List[str]
    ) -> OptimizationSuggestion:
        """创建优化建议实例"""
        self._suggestion_counter += 1
        suggestion_id = f"sugg_{datetime.now().strftime('%Y%m%d')}_{self._suggestion_counter:04d}"

        return OptimizationSuggestion(
            suggestion_id=suggestion_id,
            title=title,
            description=description,
            suggestion_type=suggestion_type,
            priority=priority,
            effort=effort,
            expected_impact=expected_impact,
            confidence=confidence,
            action_steps=action_steps,
            related_metrics=related_metrics,
            estimated_timeline=estimated_timeline,
            data_evidence=data_evidence
        )

    def _map_category_to_type(self, category: RootCauseCategory) -> SuggestionType:
        """映射根因类别到建议类型"""
        mapping = {
            RootCauseCategory.KEYWORD_RANKING: SuggestionType.SEO_OPTIMIZATION,
            RootCauseCategory.TRAFFIC_SOURCE: SuggestionType.TRAFFIC_ACQUISITION,
            RootCauseCategory.PAGE_PERFORMANCE: SuggestionType.SEO_OPTIMIZATION,
            RootCauseCategory.CONTENT_ISSUE: SuggestionType.CONTENT_IMPROVEMENT,
            RootCauseCategory.DEVICE_ISSUE: SuggestionType.UX_IMPROVEMENT,
            RootCauseCategory.TECHNICAL_ISSUE: SuggestionType.TECHNICAL_FIX,
        }
        return mapping.get(category, SuggestionType.SEO_OPTIMIZATION)

    def _map_confidence_to_priority(self, confidence: str) -> SuggestionPriority:
        """映射置信度到优先级"""
        mapping = {
            "high": SuggestionPriority.HIGH,
            "medium": SuggestionPriority.MEDIUM,
            "low": SuggestionPriority.LOW
        }
        return mapping.get(confidence, SuggestionPriority.MEDIUM)

    def _deduplicate_and_sort(
        self,
        suggestions: List[OptimizationSuggestion]
    ) -> List[OptimizationSuggestion]:
        """去重并按优先级排序"""
        # 按标题去重
        seen_titles = set()
        unique_suggestions = []

        for sugg in suggestions:
            if sugg.title not in seen_titles:
                seen_titles.add(sugg.title)
                unique_suggestions.append(sugg)

        # 按优先级排序
        priority_order = {
            SuggestionPriority.CRITICAL: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3
        }

        unique_suggestions.sort(
            key=lambda x: (priority_order[x.priority], -x.expected_impact)
        )

        return unique_suggestions


# 全局服务实例
recommendation_engine = RecommendationEngine()
