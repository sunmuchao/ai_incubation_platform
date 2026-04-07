"""
AI 自主优化服务 - 自动 A/B 测试设计与执行

功能:
- 基于根因分析自动生成 A/B 测试假设
- 自动设计测试变体方案
- 计算最小样本量和测试周期
- 自动启动和执行测试
- 测试结果自动分析和推荐
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from enum import Enum
import logging
import math
import uuid

from ai.anomaly_detection import AnomalyDetectionResult, AnomalyType, AnomalySeverity
from ai.root_cause_analysis import RootCauseAnalysisResult, RootCause, RootCauseCategory
from ai.recommendation_engine import OptimizationSuggestion, SuggestionType, SuggestionPriority
from ab_test.service import ab_test_service
from schemas.ab_test import (
    ABTestCreateRequest,
    ABTestVariant,
    ABTestGoal,
    ABTestResponse,
    ABTestStatus
)

logger = logging.getLogger(__name__)


class TestHypothesisType(str, Enum):
    """测试假设类型"""
    HEADLINE_OPTIMIZATION = "headline_optimization"  # 标题优化
    CTA_OPTIMIZATION = "cta_optimization"  # CTA 优化
    CONTENT_LAYOUT = "content_layout"  # 内容布局
    COLOR_DESIGN = "color_design"  # 颜色设计
    PRICING_STRATEGY = "pricing_strategy"  # 定价策略
    SOCIAL_PROOF = "social_proof"  # 社会证明
    URGENCY_SCARCITY = "urgency_scarcity"  # 紧迫感/稀缺性
    NAVIGATION_IMPROVEMENT = "navigation_improvement"  # 导航优化
    PAGE_SPEED = "page_speed"  # 页面速度
    MOBILE_UX = "mobile_ux"  # 移动端体验


class AutoTestDesign:
    """自动测试设计方案"""
    def __init__(
        self,
        hypothesis: str,
        hypothesis_type: TestHypothesisType,
        hypothesis_type_description: str,
        page_url: str,
        variants: List[Dict[str, Any]],
        primary_metric: str,
        secondary_metrics: List[str],
        minimum_sample_size: int,
        estimated_duration_days: int,
        confidence_level: float,
        statistical_power: float,
        minimum_detectable_effect: float,
        rationale: str,
        expected_impact: float,
        implementation_complexity: str,
        related_suggestion_id: Optional[str] = None
    ):
        self.test_id = f"auto_test_{uuid.uuid4().hex[:8]}"
        self.hypothesis = hypothesis
        self.hypothesis_type = hypothesis_type
        self.hypothesis_type_description = hypothesis_type_description
        self.page_url = page_url
        self.variants = variants
        self.primary_metric = primary_metric
        self.secondary_metrics = secondary_metrics
        self.minimum_sample_size = minimum_sample_size
        self.estimated_duration_days = estimated_duration_days
        self.confidence_level = confidence_level
        self.statistical_power = statistical_power
        self.minimum_detectable_effect = minimum_detectable_effect
        self.rationale = rationale
        self.expected_impact = expected_impact
        self.implementation_complexity = implementation_complexity
        self.related_suggestion_id = related_suggestion_id
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "hypothesis": self.hypothesis,
            "hypothesis_type": self.hypothesis_type.value,
            "hypothesis_type_description": self.hypothesis_type_description,
            "page_url": self.page_url,
            "variants": self.variants,
            "primary_metric": self.primary_metric,
            "secondary_metrics": self.secondary_metrics,
            "minimum_sample_size": self.minimum_sample_size,
            "estimated_duration_days": self.estimated_duration_days,
            "confidence_level": round(self.confidence_level, 2),
            "statistical_power": round(self.statistical_power, 2),
            "minimum_detectable_effect": round(self.minimum_detectable_effect, 4),
            "rationale": self.rationale,
            "expected_impact": round(self.expected_impact, 4),
            "implementation_complexity": self.implementation_complexity,
            "related_suggestion_id": self.related_suggestion_id,
            "created_at": self.created_at.isoformat()
        }


class AutoABTestService:
    """
    AI 自主 A/B 测试服务

    基于 AI 分析结果自动设计和执行 A/B 测试:
    - 从根因分析生成测试假设
    - 自动设计测试变体
    - 计算统计参数
    - 自动执行和监控
    - 结果分析和推荐
    """

    def __init__(self):
        # A/B 测试假设模板库
        self._hypothesis_templates = self._initialize_hypothesis_templates()

        # 统计参数配置
        self.default_confidence_level = 0.95  # 置信水平
        self.default_statistical_power = 0.80  # 统计功效
        self.default_mde = 0.05  # 最小可检测效应 (5%)
        self.baseline_conversion_rate = 0.03  # 默认基线转化率 3%

        # 流量估算（每日访客）
        self.estimated_daily_visitors = 1000

    def _initialize_hypothesis_templates(self) -> Dict[str, List[Dict]]:
        """初始化测试假设模板"""
        return {
            RootCauseCategory.KEYWORD_RANKING.value: [
                {
                    "type": TestHypothesisType.HEADLINE_OPTIMIZATION,
                    "description": "优化页面标题以提升关键词相关性",
                    "hypothesis_pattern": "通过将页面标题从'{current}'改为'{optimized}'，可以提升关键词'{keyword}'的排名和点击率",
                    "page_selector": "ranking_keywords",
                    "variants_generator": "_generate_headline_variants"
                },
                {
                    "type": TestHypothesisType.CONTENT_LAYOUT,
                    "description": "调整内容布局以提升用户停留时间",
                    "hypothesis_pattern": "通过优化内容结构和布局，可以提升用户参与度和页面 SEO 表现",
                    "page_selector": "low_engagement_pages",
                    "variants_generator": "_generate_content_layout_variants"
                }
            ],
            RootCauseCategory.CONTENT_ISSUE.value: [
                {
                    "type": TestHypothesisType.CONTENT_LAYOUT,
                    "description": "改进内容可读性以降低跳出率",
                    "hypothesis_pattern": "通过改进内容结构和可读性，可以降低跳出率并提升用户参与度",
                    "page_selector": "high_bounce_pages",
                    "variants_generator": "_generate_content_variants"
                }
            ],
            "conversion_optimization": [
                {
                    "type": TestHypothesisType.CTA_OPTIMIZATION,
                    "description": "优化 CTA 按钮以提升转化率",
                    "hypothesis_pattern": "通过将 CTA 按钮从'{current}'改为'{optimized}'，可以提升转化率",
                    "page_selector": "conversion_pages",
                    "variants_generator": "_generate_cta_variants"
                },
                {
                    "type": TestHypothesisType.SOCIAL_PROOF,
                    "description": "添加社会证明元素以增强信任感",
                    "hypothesis_pattern": "通过添加用户评价/案例/认证等社会证明，可以提升转化率",
                    "page_selector": "conversion_pages",
                    "variants_generator": "_generate_social_proof_variants"
                },
                {
                    "type": TestHypothesisType.URGENCY_SCARCITY,
                    "description": "添加紧迫感元素以促进立即行动",
                    "hypothesis_pattern": "通过添加限时/限量等紧迫感元素，可以提升转化率",
                    "page_selector": "conversion_pages",
                    "variants_generator": "_generate_urgency_variants"
                }
            ],
            "traffic_acquisition": [
                {
                    "type": TestHypothesisType.NAVIGATION_IMPROVEMENT,
                    "description": "优化导航结构以提升页面发现性",
                    "hypothesis_pattern": "通过优化导航结构和内部链接，可以提升页面访问深度",
                    "page_selector": "entry_pages",
                    "variants_generator": "_generate_navigation_variants"
                }
            ]
        }

    def generate_test_designs(
        self,
        analysis_result: RootCauseAnalysisResult,
        context: Optional[Dict[str, Any]] = None
    ) -> List[AutoTestDesign]:
        """
        基于根因分析结果自动生成测试设计方案

        Args:
            analysis_result: 根因分析结果
            context: 上下文信息（包含页面数据、当前表现等）

        Returns:
            自动测试设计方案列表
        """
        test_designs = []
        context = context or {}

        # 根据根因类别选择假设模板
        for root_cause in analysis_result.root_causes:
            templates = self._get_relevant_templates(root_cause)

            for template in templates:
                design = self._create_test_design(
                    template=template,
                    root_cause=root_cause,
                    anomaly=analysis_result.anomaly,
                    context=context
                )
                if design:
                    test_designs.append(design)

        # 根据异常类型生成额外的测试设计
        anomaly_designs = self._generate_anomaly_based_tests(analysis_result.anomaly, context)
        test_designs.extend(anomaly_designs)

        # 去重和优先级排序
        test_designs = self._deduplicate_and_prioritize(test_designs)

        return test_designs

    def generate_proactive_tests(
        self,
        page_url: str,
        page_type: str,
        current_metrics: Dict[str, float],
        benchmark_metrics: Optional[Dict[str, float]] = None
    ) -> List[AutoTestDesign]:
        """
        生成主动优化测试建议（无异常时）

        Args:
            page_url: 页面 URL
            page_type: 页面类型（home, product, blog, landing 等）
            current_metrics: 当前指标
            benchmark_metrics: 行业基准指标

        Returns:
            测试设计方案列表
        """
        test_designs = []
        benchmark_metrics = benchmark_metrics or self._get_industry_benchmarks(page_type)

        # 识别低于基准的指标
        improvement_opportunities = []
        for metric, current_value in current_metrics.items():
            if metric in benchmark_metrics:
                benchmark = benchmark_metrics[metric]
                if current_value < benchmark * 0.9:  # 低于基准 10%
                    gap = (benchmark - current_value) / benchmark
                    improvement_opportunities.append({
                        "metric": metric,
                        "current": current_value,
                        "benchmark": benchmark,
                        "gap": gap
                    })

        # 为每个改进机会生成测试设计
        for opportunity in improvement_opportunities:
            design = self._create_benchmark_test_design(
                page_url=page_url,
                page_type=page_type,
                opportunity=opportunity,
                context={"current_metrics": current_metrics}
            )
            if design:
                test_designs.append(design)

        return test_designs

    def execute_test(
        self,
        test_design: AutoTestDesign,
        created_by: str = "system"
    ) -> Optional[ABTestResponse]:
        """
        执行测试设计 - 创建并启动 A/B 测试

        Args:
            test_design: 测试设计方案
            created_by: 创建者

        Returns:
            创建的 A/B 测试
        """
        try:
            # 将测试设计转换为 A/B 测试创建请求
            request = self._convert_design_to_request(test_design, created_by)

            # 创建测试
            test = ab_test_service.create_test(request, created_by)

            # 自动启动测试
            test = ab_test_service.start_test(test.id)

            logger.info(f"自动 A/B 测试已创建并启动：{test.id}, hypothesis: {test_design.hypothesis}")

            return test

        except Exception as e:
            logger.error(f"执行自动 A/B 测试失败：{e}")
            return None

    def analyze_test_result(
        self,
        test_id: str
    ) -> Dict[str, Any]:
        """
        分析测试结果并生成建议

        Args:
            test_id: 测试 ID

        Returns:
            分析结果和建议
        """
        test = ab_test_service.get_test_detail(test_id)
        result = ab_test_service.get_test_result(test_id)

        if not test or not result:
            return {"error": "测试或结果不存在"}

        analysis = {
            "test_id": test_id,
            "test_name": test.name,
            "status": test.status.value,
            "has_winner": result.has_winner,
            "can_terminate": result.can_terminate,
            "conclusion": result.conclusion,
            "recommendations": result.recommendations,
            "ai_analysis": self._generate_ai_analysis(test, result),
            "next_steps": self._generate_next_steps(test, result)
        }

        return analysis

    def _get_relevant_templates(self, root_cause: RootCause) -> List[Dict]:
        """获取相关的测试假设模板"""
        templates = []

        # 直接匹配根因类别
        if root_cause.category.value in self._hypothesis_templates:
            templates.extend(self._hypothesis_templates[root_cause.category.value])

        # 映射到通用优化类别
        if root_cause.category in [RootCauseCategory.KEYWORD_RANKING, RootCauseCategory.PAGE_PERFORMANCE]:
            templates.extend(self._hypothesis_templates.get("conversion_optimization", []))

        if root_cause.category == RootCauseCategory.CONTENT_ISSUE:
            templates.extend(self._hypothesis_templates.get("traffic_acquisition", []))

        return templates

    def _create_test_design(
        self,
        template: Dict,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult,
        context: Dict[str, Any]
    ) -> Optional[AutoTestDesign]:
        """创建测试设计方案"""
        # 生成假设
        hypothesis = self._generate_hypothesis(template, root_cause, anomaly, context)

        # 选择目标页面
        page_url = self._select_target_page(template, root_cause, context)
        if not page_url:
            page_url = context.get("default_page", "/")

        # 生成变体
        variants = self._generate_variants(template, root_cause, context)

        # 选择主要指标
        primary_metric = self._select_primary_metric(root_cause, anomaly)

        # 计算样本量
        sample_size = self._calculate_sample_size(
            baseline_rate=self._get_baseline_rate(primary_metric, context),
            mde=self.default_mde,
            confidence=self.default_confidence_level,
            power=self.default_statistical_power
        )

        # 估算测试周期
        duration_days = math.ceil(sample_size / max(self.estimated_daily_visitors, 100))
        duration_days = max(duration_days, 7)  # 至少 7 天

        # 生成理由说明
        rationale = self._generate_rationale(template, root_cause, anomaly)

        # 评估预期影响
        expected_impact = self._estimate_impact(template, root_cause, anomaly)

        # 评估实施复杂度
        complexity = self._evaluate_complexity(template)

        return AutoTestDesign(
            hypothesis=hypothesis,
            hypothesis_type=template["type"],
            hypothesis_type_description=template["description"],
            page_url=page_url,
            variants=variants,
            primary_metric=primary_metric,
            secondary_metrics=self._get_secondary_metrics(primary_metric),
            minimum_sample_size=sample_size,
            estimated_duration_days=duration_days,
            confidence_level=self.default_confidence_level,
            statistical_power=self.default_statistical_power,
            minimum_detectable_effect=self.default_mde,
            rationale=rationale,
            expected_impact=expected_impact,
            implementation_complexity=complexity
        )

    def _generate_hypothesis(
        self,
        template: Dict,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult,
        context: Dict[str, Any]
    ) -> str:
        """生成测试假设"""
        pattern = template.get("hypothesis_pattern", "优化此页面可以提升关键指标")

        # 填充模板变量
        hypothesis = pattern.format(
            current=context.get("current_value", "当前方案"),
            optimized=context.get("optimized_value", "优化方案"),
            keyword=context.get("keyword", "目标关键词"),
            metric=anomaly.metric_name,
            impact=f"{abs(anomaly.deviation) * 100:.1f}%"
        )

        return hypothesis

    def _select_target_page(
        self,
        template: Dict,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> str:
        """选择目标页面"""
        pages = context.get("available_pages", [])

        if not pages:
            return "/"

        selector_type = template.get("page_selector", "")

        if selector_type == "ranking_keywords":
            # 选择受关键词排名影响的页面
            return pages[0] if pages else "/"
        elif selector_type == "high_bounce_pages":
            # 选择跳出率最高的页面
            return max(pages, key=lambda p: context.get(f"{p}_bounce_rate", 0)) if pages else "/"
        elif selector_type == "conversion_pages":
            # 选择转化页面
            return next((p for p in pages if "checkout" in p or "pricing" in p), pages[0] if pages else "/")

        return pages[0] if pages else "/"

    def _generate_variants(
        self,
        template: Dict,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成测试变体"""
        variants_generator = template.get("variants_generator", "_generate_default_variants")

        # 调用对应的变体生成方法
        if hasattr(self, variants_generator):
            return getattr(self, variants_generator)(template, root_cause, context)

        return self._generate_default_variants(template, root_cause, context)

    def _generate_headline_variants(
        self,
        template: Dict,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成标题优化变体"""
        current_title = context.get("current_title", "当前标题")
        keyword = context.get("target_keyword", "关键词")

        return [
            {
                "name": "对照组",
                "description": f"原标题：{current_title}",
                "content": {"title": current_title},
                "is_control": True,
                "traffic_percentage": 0.5
            },
            {
                "name": "测试组 A - 关键词前置",
                "description": f"将关键词'{keyword}'前置到标题开头",
                "content": {"title": f"{keyword} - {current_title.split(' - ')[-1] if ' - ' in current_title else current_title}"},
                "is_control": False,
                "traffic_percentage": 0.5
            }
        ]

    def _generate_cta_variants(
        self,
        template: Dict,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成 CTA 优化变体"""
        current_cta = context.get("current_cta", "立即购买")

        cta_alternatives = {
            "立即购买": ["免费试用", "开始使用", "获取报价", "查看更多"],
            "注册": ["免费加入", "立即开始", "创建账号"],
            "下载": ["免费获取", "立即下载", "获取资源"]
        }

        alternatives = cta_alternatives.get(current_cta, ["立即开始"])

        variants = [{
            "name": "对照组",
            "description": f"原 CTA: {current_cta}",
            "content": {"cta_text": current_cta},
            "is_control": True,
            "traffic_percentage": 0.5
        }]

        for i, alt in enumerate(alternatives[:2]):
            variants.append({
                "name": f"测试组{chr(65+i)} - {alt}",
                "description": f"CTA 文案：{alt}",
                "content": {"cta_text": alt},
                "is_control": False,
                "traffic_percentage": 0.5 / len(alternatives[:2])
            })

        # 重新分配流量比例使总和为 1
        total_variants = len(variants)
        traffic_per_variant = 1.0 / total_variants
        for variant in variants:
            variant["traffic_percentage"] = traffic_per_variant

        return variants

    def _generate_content_variants(
        self,
        template: Dict,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成内容优化变体"""
        return [
            {
                "name": "对照组",
                "description": "原始内容布局",
                "content": {"layout": "original"},
                "is_control": True,
                "traffic_percentage": 0.5
            },
            {
                "name": "测试组 A - 结构化布局",
                "description": "添加目录、小标题、摘要的结构化布局",
                "content": {
                    "layout": "structured",
                    "features": ["toc", "subheadings", "summary_box", "key_takeaways"]
                },
                "is_control": False,
                "traffic_percentage": 0.5
            }
        ]

    def _generate_social_proof_variants(
        self,
        template: Dict,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成社会证明变体"""
        return [
            {
                "name": "对照组",
                "description": "无社会证明元素",
                "content": {"social_proof": False},
                "is_control": True,
                "traffic_percentage": 0.5
            },
            {
                "name": "测试组 A - 用户评价",
                "description": "添加用户评价和评分",
                "content": {
                    "social_proof": True,
                    "type": "testimonials",
                    "elements": ["star_rating", "user_reviews", "case_study"]
                },
                "is_control": False,
                "traffic_percentage": 0.5
            }
        ]

    def _generate_urgency_variants(
        self,
        template: Dict,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成紧迫感变体"""
        return [
            {
                "name": "对照组",
                "description": "无紧迫感元素",
                "content": {"urgency": False},
                "is_control": True,
                "traffic_percentage": 0.5
            },
            {
                "name": "测试组 A - 限时优惠",
                "description": "添加限时优惠倒计时",
                "content": {
                    "urgency": True,
                    "type": "countdown",
                    "message": "优惠仅剩{hours}小时",
                    "elements": ["countdown_timer", "limited_offer_badge"]
                },
                "is_control": False,
                "traffic_percentage": 0.5
            }
        ]

    def _generate_default_variants(
        self,
        template: Dict,
        root_cause: RootCause,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """默认变体生成"""
        return [
            {
                "name": "对照组",
                "description": "当前方案",
                "content": {"variant": "control"},
                "is_control": True,
                "traffic_percentage": 0.5
            },
            {
                "name": "测试组 A",
                "description": template["description"],
                "content": {"variant": "treatment_a"},
                "is_control": False,
                "traffic_percentage": 0.5
            }
        ]

    def _select_primary_metric(
        self,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult
    ) -> str:
        """选择主要指标"""
        metric_mapping = {
            RootCauseCategory.KEYWORD_RANKING: "organic_traffic",
            RootCauseCategory.CONTENT_ISSUE: "bounce_rate",
            RootCauseCategory.PAGE_PERFORMANCE: "avg_time_on_page",
            RootCauseCategory.TRAFFIC_SOURCE: "visitors",
        }

        # 根据根因类别选择
        if root_cause.category in metric_mapping:
            return metric_mapping[root_cause.category]

        # 根据异常类型选择
        if anomaly.anomaly_type == AnomalyType.CONVERSION_DROP:
            return "conversion_rate"
        elif anomaly.anomaly_type == AnomalyType.TRAFFIC_DROP:
            return "visitors"

        return "conversion_rate"

    def _get_secondary_metrics(self, primary_metric: str) -> List[str]:
        """获取次要指标列表"""
        secondary_mapping = {
            "conversion_rate": ["bounce_rate", "avg_session_duration", "pages_per_session"],
            "visitors": ["page_views", "bounce_rate", "avg_session_duration"],
            "bounce_rate": ["avg_time_on_page", "pages_per_session", "conversion_rate"],
            "avg_time_on_page": ["bounce_rate", "scroll_depth", "conversion_rate"]
        }
        return secondary_mapping.get(primary_metric, ["bounce_rate", "conversion_rate"])

    def _calculate_sample_size(
        self,
        baseline_rate: float,
        mde: float,
        confidence: float,
        power: float
    ) -> int:
        """
        计算最小样本量

        使用两比例检验的样本量公式
        """
        if baseline_rate <= 0 or baseline_rate >= 1:
            baseline_rate = self.baseline_conversion_rate

        # Z 值（置信水平）
        z_alpha = 1.96 if confidence == 0.95 else 1.645

        # Z 值（统计功效）
        z_beta = 0.84 if power == 0.80 else 1.28

        # 最小可检测效应
        effect_size = mde

        # 计算样本量
        p1 = baseline_rate
        p2 = p1 * (1 + effect_size)

        if p2 >= 1:
            p2 = 0.99

        pooled_p = (p1 + p2) / 2

        numerator = (z_alpha * math.sqrt(2 * pooled_p * (1 - pooled_p)) +
                    z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        denominator = (p1 - p2) ** 2

        if denominator == 0:
            return 1000  # 默认样本量

        sample_size_per_variant = math.ceil(numerator / denominator)

        return sample_size_per_variant * 2  # 两个变体

    def _get_baseline_rate(self, metric: str, context: Dict[str, Any]) -> float:
        """获取基线转化率"""
        baseline_rates = {
            "conversion_rate": 0.03,
            "bounce_rate": 0.50,
            "avg_time_on_page": 60,
            "visitors": 1000
        }

        # 从上下文获取实际基线
        if metric in context:
            return context[metric]

        return baseline_rates.get(metric, 0.03)

    def _generate_rationale(
        self,
        template: Dict,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult
    ) -> str:
        """生成测试设计理由"""
        return (
            f"基于根因分析：{root_cause.description} (置信度：{root_cause.confidence.value})\n"
            f"异常检测：{anomaly.description}\n"
            f"测试类型：{template['type'].value} - {template['description']}"
        )

    def _estimate_impact(
        self,
        template: Dict,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult
    ) -> float:
        """估算预期影响"""
        # 基于根因影响分数和置信度估算
        base_impact = root_cause.impact_score

        # 根据测试类型调整
        type_multipliers = {
            TestHypothesisType.CTA_OPTIMIZATION: 1.2,
            TestHypothesisType.HEADLINE_OPTIMIZATION: 0.8,
            TestHypothesisType.CONTENT_LAYOUT: 1.0,
            TestHypothesisType.SOCIAL_PROOF: 1.1,
            TestHypothesisType.URGENCY_SCARCITY: 1.3
        }

        multiplier = type_multipliers.get(template["type"], 1.0)

        # 置信度调整
        confidence_multipliers = {
            "high": 1.2,
            "medium": 1.0,
            "low": 0.8
        }
        conf_mult = confidence_multipliers.get(root_cause.confidence.value, 1.0)

        return min(0.5, base_impact * multiplier * conf_mult)

    def _evaluate_complexity(self, template: Dict) -> str:
        """评估实施复杂度"""
        # 基于测试类型评估复杂度
        low_complexity_types = [
            TestHypothesisType.HEADLINE_OPTIMIZATION,
            TestHypothesisType.CTA_OPTIMIZATION,
            TestHypothesisType.COLOR_DESIGN
        ]
        medium_complexity_types = [
            TestHypothesisType.CONTENT_LAYOUT,
            TestHypothesisType.SOCIAL_PROOF,
            TestHypothesisType.NAVIGATION_IMPROVEMENT
        ]

        if template["type"] in low_complexity_types:
            return "low"
        elif template["type"] in medium_complexity_types:
            return "medium"
        else:
            return "high"

    def _generate_anomaly_based_tests(
        self,
        anomaly: AnomalyDetectionResult,
        context: Dict[str, Any]
    ) -> List[AutoTestDesign]:
        """基于异常类型生成测试设计"""
        tests = []

        if anomaly.anomaly_type == AnomalyType.CONVERSION_DROP:
            # 转化率下跌 - 生成 CTA 优化测试
            from ai.root_cause_analysis import RootCause, RootCauseCategory
            design = AutoTestDesign(
                hypothesis="通过优化转化流程可以降低流失率",
                hypothesis_type=TestHypothesisType.CTA_OPTIMIZATION,
                hypothesis_type_description="优化 CTA 和转化流程",
                page_url=context.get("conversion_page", "/checkout"),
                variants=self._generate_cta_variants({}, RootCause(RootCauseCategory.CONTENT_ISSUE, "转化率下跌", "medium", [], 0.5, [], []), context),
                primary_metric="conversion_rate",
                secondary_metrics=["bounce_rate", "exit_rate"],
                minimum_sample_size=self._calculate_sample_size(0.03, 0.1, 0.95, 0.8),
                estimated_duration_days=14,
                confidence_level=0.95,
                statistical_power=0.8,
                minimum_detectable_effect=0.1,
                rationale=f"响应转化率异常下跌 ({anomaly.deviation*100:.1f}%)",
                expected_impact=0.15,
                implementation_complexity="medium"
            )
            tests.append(design)

        return tests

    def _deduplicate_and_prioritize(
        self,
        test_designs: List[AutoTestDesign]
    ) -> List[AutoTestDesign]:
        """去重并按优先级排序"""
        # 按假设去重
        seen_hypotheses = set()
        unique_designs = []

        for design in test_designs:
            if design.hypothesis not in seen_hypotheses:
                seen_hypotheses.add(design.hypothesis)
                unique_designs.append(design)

        # 按预期影响和实施复杂度排序
        complexity_order = {"low": 0, "medium": 1, "high": 2}

        unique_designs.sort(
            key=lambda x: (-x.expected_impact, complexity_order.get(x.implementation_complexity, 1))
        )

        return unique_designs

    def _deduplicate_and_prioritize(
        self,
        test_designs: List[AutoTestDesign]
    ) -> List[AutoTestDesign]:
        """去重并按优先级排序"""
        # 按假设去重
        seen_hypotheses = set()
        unique_designs = []

        for design in test_designs:
            if design.hypothesis not in seen_hypotheses:
                seen_hypotheses.add(design.hypothesis)
                unique_designs.append(design)

        # 按预期影响和实施复杂度排序
        complexity_order = {"low": 0, "medium": 1, "high": 2}

        unique_designs.sort(
            key=lambda x: (-x.expected_impact, complexity_order.get(x.implementation_complexity, 1))
        )

        return unique_designs

    def _convert_design_to_request(
        self,
        test_design: AutoTestDesign,
        created_by: str
    ) -> ABTestCreateRequest:
        """将测试设计转换为 A/B 测试创建请求"""
        # 创建变体对象
        variants = []
        for var_data in test_design.variants:
            variant = ABTestVariant(
                id=f"var_{uuid.uuid4().hex[:8]}",
                name=var_data["name"],
                description=var_data["description"],
                traffic_percentage=var_data["traffic_percentage"],
                content=var_data["content"],
                is_control=var_data.get("is_control", False)
            )
            variants.append(variant)

        # 创建目标
        goals = [
            ABTestGoal(
                name=f"提升{test_design.primary_metric}",
                metric=test_design.primary_metric,
                target_value=test_design.minimum_detectable_effect,
                operator="increase"
            )
        ]

        return ABTestCreateRequest(
            name=f"AI 自主测试：{test_design.hypothesis[:50]}...",
            description=test_design.rationale,
            page_url=test_design.page_url,
            variants=variants,
            goals=goals,
            start_time=datetime.now() + timedelta(hours=1),
            end_time=None,
            confidence_level=test_design.confidence_level,
            minimum_sample_size=test_design.minimum_sample_size
        )

    def _generate_ai_analysis(
        self,
        test: ABTestResponse,
        result: Any
    ) -> Dict[str, Any]:
        """生成 AI 分析"""
        # 分析测试结果的统计显著性
        winner_metric = None
        winner_name = None

        if result.has_winner:
            for metric in result.metrics:
                if metric.is_winner:
                    winner_metric = metric
                    winner_name = metric.variant_name
                    break

        return {
            "statistical_confidence": result.confidence_level if result.has_winner else "不足",
            "winner": winner_name,
            "improvement": f"{winner_metric.improvement*100:.1f}%" if winner_metric else "N/A",
            "recommendation": "全量切换" if result.has_winner else "继续测试或重新设计",
            "learning": self._extract_learning(test, result)
        }

    def _extract_learning(
        self,
        test: ABTestResponse,
        result: Any
    ) -> str:
        """从测试结果中提取学习"""
        if result.has_winner:
            return f"获胜方案证明了{test.variants[0].description}比{test.variants[1].description}更有效"
        else:
            return "本次测试未产生统计显著差异，建议调整测试变量或增加样本量"

    def _generate_next_steps(
        self,
        test: ABTestResponse,
        result: Any
    ) -> List[str]:
        """生成下一步行动建议"""
        next_steps = []

        if result.has_winner:
            next_steps.append(f"全量部署获胜方案：{result.winner_id}")
            next_steps.append("监控全量后的效果表现")
            next_steps.append("记录学习并应用到类似页面")
        elif result.can_terminate:
            next_steps.append("考虑提前终止测试或延长测试时间")
            next_steps.append("分析是否有细分群体表现出差异")
        else:
            next_steps.append(f"继续运行测试，还需{result.remaining_sample_size}个样本")
            next_steps.append("避免在测试期间修改其他变量")

        return next_steps

    def _get_industry_benchmarks(self, page_type: str) -> Dict[str, float]:
        """获取行业基准指标"""
        benchmarks = {
            "home": {
                "conversion_rate": 0.04,
                "bounce_rate": 0.40,
                "avg_time_on_page": 90
            },
            "product": {
                "conversion_rate": 0.05,
                "bounce_rate": 0.35,
                "avg_time_on_page": 120
            },
            "blog": {
                "conversion_rate": 0.02,
                "bounce_rate": 0.60,
                "avg_time_on_page": 180
            },
            "landing": {
                "conversion_rate": 0.08,
                "bounce_rate": 0.30,
                "avg_time_on_page": 60
            }
        }
        return benchmarks.get(page_type, benchmarks["home"])


# 全局服务实例
auto_ab_test_service = AutoABTestService()
