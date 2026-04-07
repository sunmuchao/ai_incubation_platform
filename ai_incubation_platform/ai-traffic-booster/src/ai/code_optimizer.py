"""
AI 代码级优化建议生成器

功能:
- 基于 AI 分析结果生成可执行的代码级优化建议
- 与 ai-code-understanding 协同生成代码改动
- 生成可一键应用的代码补丁
- 支持多种优化类型：SEO、性能、转化优化

协同 Agent:
- ai-code-understanding: 代码理解和改动生成
- ai-runtime-optimizer: 运行态性能定位
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date
from enum import Enum
import logging
import uuid
import json

from ai.anomaly_detection import AnomalyDetectionResult, AnomalyType, AnomalySeverity
from ai.root_cause_analysis import RootCauseAnalysisResult, RootCause, RootCauseCategory
from ai.recommendation_engine import OptimizationSuggestion, SuggestionType, SuggestionPriority

logger = logging.getLogger(__name__)


class CodeChangeType(str, Enum):
    """代码改动类型"""
    HTML_MODIFICATION = "html_modification"  # HTML 修改
    CSS_MODIFICATION = "css_modification"  # CSS 修改
    JAVASCRIPT_MODIFICATION = "javascript_modification"  # JavaScript 修改
    META_TAG_UPDATE = "meta_tag_update"  # Meta 标签更新
    STRUCTURED_DATA = "structured_data"  # 结构化数据
    LAZY_LOADING = "lazy_loading"  # 懒加载
    IMAGE_OPTIMIZATION = "image_optimization"  # 图片优化
    CACHING_CONFIG = "caching_config"  # 缓存配置
    CDN_CONFIG = "cdn_config"  # CDN 配置


class CodeOptimizationLevel(str, Enum):
    """代码优化级别"""
    SNIPPET = "snippet"  # 代码片段
    COMPONENT = "component"  # 组件级别
    PAGE = "page"  # 页面级别
    GLOBAL = "global"  # 全局配置


class CodeChange:
    """代码改动"""
    def __init__(
        self,
        change_id: str,
        change_type: CodeChangeType,
        target_file: str,
        target_selector: Optional[str],
        description: str,
        old_code: Optional[str],
        new_code: str,
        diff: str,
        language: str,
        confidence: float,
        estimated_impact: float,
        implementation_notes: List[str],
        rollback_plan: str,
        related_suggestion_id: Optional[str] = None
    ):
        self.change_id = change_id
        self.change_type = change_type
        self.target_file = target_file
        self.target_selector = target_selector
        self.description = description
        self.old_code = old_code
        self.new_code = new_code
        self.diff = diff
        self.language = language
        self.confidence = confidence
        self.estimated_impact = estimated_impact
        self.implementation_notes = implementation_notes
        self.rollback_plan = rollback_plan
        self.related_suggestion_id = related_suggestion_id
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "target_file": self.target_file,
            "target_selector": self.target_selector,
            "description": self.description,
            "old_code": self.old_code,
            "new_code": self.new_code,
            "diff": self.diff,
            "language": self.language,
            "confidence": round(self.confidence, 2),
            "estimated_impact": round(self.estimated_impact, 4),
            "implementation_notes": self.implementation_notes,
            "rollback_plan": self.rollback_plan,
            "related_suggestion_id": self.related_suggestion_id,
            "created_at": self.created_at.isoformat()
        }


class CodeOptimizationSuggestion:
    """代码优化建议"""
    def __init__(
        self,
        suggestion_id: str,
        title: str,
        description: str,
        optimization_level: CodeOptimizationLevel,
        changes: List[CodeChange],
        expected_impact: float,
        confidence: float,
        effort_estimate: str,
        risk_level: str,
        testing_recommendations: List[str],
        monitoring_metrics: List[str]
    ):
        self.suggestion_id = suggestion_id
        self.title = title
        self.description = description
        self.optimization_level = optimization_level
        self.changes = changes
        self.expected_impact = expected_impact
        self.confidence = confidence
        self.effort_estimate = effort_estimate
        self.risk_level = risk_level
        self.testing_recommendations = testing_recommendations
        self.monitoring_metrics = monitoring_metrics
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "title": self.title,
            "description": self.description,
            "optimization_level": self.optimization_level.value,
            "changes": [c.to_dict() for c in self.changes],
            "expected_impact": round(self.expected_impact, 4),
            "confidence": round(self.confidence, 2),
            "effort_estimate": self.effort_estimate,
            "risk_level": self.risk_level,
            "testing_recommendations": self.testing_recommendations,
            "monitoring_metrics": self.monitoring_metrics,
            "created_at": self.created_at.isoformat()
        }


class CodeOptimizerService:
    """
    AI 代码级优化建议生成服务

    基于 AI 分析结果生成可执行的代码改动:
    - SEO 代码改动（Title/Meta/结构化数据）
    - 性能优化代码建议
    - 转化优化代码改动
    - 生成可一键应用的代码补丁
    """

    def __init__(self):
        # 代码改动模板库
        self._code_templates = self._initialize_code_templates()

        # 代码改动配置
        self.default_confidence = 0.8
        self.default_risk_level = "medium"

    def _initialize_code_templates(self) -> Dict[str, List[Dict]]:
        """初始化代码改动模板"""
        return {
            "seo_optimization": {
                "title_meta": {
                    "type": CodeChangeType.META_TAG_UPDATE,
                    "level": CodeOptimizationLevel.PAGE,
                    "html_snippet": self._get_title_meta_template(),
                    "implementation_notes": [
                        "将生成的代码替换到页面<head>标签内",
                        "确保每个页面有唯一的 Title 和 Meta Description",
                        "Title 长度控制在 50-60 字符",
                        "Meta Description 长度控制在 150-160 字符"
                    ]
                },
                "structured_data": {
                    "type": CodeChangeType.STRUCTURED_DATA,
                    "level": CodeOptimizationLevel.PAGE,
                    "json_ld_snippet": self._get_structured_data_template(),
                    "implementation_notes": [
                        "将 JSON-LD 代码添加到页面<head>标签内",
                        "根据实际情况调整 schema 类型和属性",
                        "使用 Google Rich Results Test 验证"
                    ]
                },
                "heading_optimization": {
                    "type": CodeChangeType.HTML_MODIFICATION,
                    "level": CodeOptimizationLevel.PAGE,
                    "implementation_notes": [
                        "确保每个页面只有一个 H1 标签",
                        "H1 应包含核心关键词",
                        "使用 H2-H6 建立清晰的内容层级"
                    ]
                }
            },
            "performance_optimization": {
                "image_lazy_load": {
                    "type": CodeChangeType.LAZY_LOADING,
                    "level": CodeOptimizationLevel.COMPONENT,
                    "html_attribute": 'loading="lazy"',
                    "implementation_notes": [
                        "为非首屏图片添加 loading='lazy' 属性",
                        "考虑使用 Intersection Observer API 实现自定义懒加载",
                        "确保有合适的占位符避免布局偏移"
                    ]
                },
                "image_optimization": {
                    "type": CodeChangeType.IMAGE_OPTIMIZATION,
                    "level": CodeOptimizationLevel.GLOBAL,
                    "implementation_notes": [
                        "使用 WebP 等现代图片格式",
                        "实现响应式图片（srcset）",
                        "压缩图片质量至 80-85%",
                        "使用 CDN 进行图片分发"
                    ]
                },
                "css_minification": {
                    "type": CodeChangeType.CSS_MODIFICATION,
                    "level": CodeOptimizationLevel.GLOBAL,
                    "implementation_notes": [
                        "使用工具压缩 CSS 文件",
                        "移除未使用的 CSS",
                        "考虑使用 CSS-in-JS 或 CSS Modules"
                    ]
                },
                "js_defer": {
                    "type": CodeChangeType.JAVASCRIPT_MODIFICATION,
                    "level": CodeOptimizationLevel.GLOBAL,
                    "html_attribute": 'defer',
                    "implementation_notes": [
                        "为非关键 JS 添加 defer 属性",
                        "将分析脚本改为异步加载",
                        "考虑使用 Web Workers 处理复杂计算"
                    ]
                }
            },
            "conversion_optimization": {
                "cta_enhancement": {
                    "type": CodeChangeType.HTML_MODIFICATION,
                    "level": CodeOptimizationLevel.COMPONENT,
                    "implementation_notes": [
                        "使用对比色突出 CTA 按钮",
                        "确保 CTA 在首屏可见",
                        "添加微动画吸引注意力",
                        "优化移动端 CTA 尺寸（至少 44x44px）"
                    ]
                },
                "social_proof": {
                    "type": CodeChangeType.HTML_MODIFICATION,
                    "level": CodeOptimizationLevel.COMPONENT,
                    "html_snippet": self._get_social_proof_template(),
                    "implementation_notes": [
                        "在关键转化点附近添加社会证明",
                        "使用真实的用户评价和案例",
                        "展示权威认证和奖项"
                    ]
                },
                "urgency_element": {
                    "type": CodeChangeType.JAVASCRIPT_MODIFICATION,
                    "level": CodeOptimizationLevel.COMPONENT,
                    "js_snippet": self._get_countdown_timer_template(),
                    "implementation_notes": [
                        "在促销页面添加倒计时元素",
                        "确保倒计时真实有效",
                        "避免过度使用造成用户疲劳"
                    ]
                },
                "form_optimization": {
                    "type": CodeChangeType.HTML_MODIFICATION,
                    "level": CodeOptimizationLevel.COMPONENT,
                    "implementation_notes": [
                        "减少表单字段数量",
                        "添加实时表单验证",
                        "使用自动填充和输入提示",
                        "显示进度指示器"
                    ]
                }
            },
            "ux_optimization": {
                "mobile_responsive": {
                    "type": CodeChangeType.CSS_MODIFICATION,
                    "level": CodeOptimizationLevel.GLOBAL,
                    "implementation_notes": [
                        "使用响应式设计适配不同屏幕",
                        "确保移动端字体大小至少 16px",
                        "优化触控目标尺寸",
                        "测试主流设备和浏览器"
                    ]
                },
                "navigation_improvement": {
                    "type": CodeChangeType.HTML_MODIFICATION,
                    "level": CodeOptimizationLevel.GLOBAL,
                    "implementation_notes": [
                        "添加面包屑导航",
                        "优化主导航菜单结构",
                        "添加站内搜索功能",
                        "确保导航在所有页面一致"
                    ]
                }
            }
        }

    def _get_title_meta_template(self) -> str:
        """获取 Title/Meta 模板"""
        return '''<title>{page_title} | {site_name}</title>
<meta name="description" content="{meta_description}">
<meta name="keywords" content="{keywords}">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="{meta_description}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{page_title}">
<meta name="twitter:description" content="{meta_description}">'''

    def _get_structured_data_template(self) -> str:
        """获取结构化数据模板"""
        return '''<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{headline}",
  "description": "{description}",
  "image": "{image_url}",
  "author": {
    "@type": "Person",
    "name": "{author_name}"
  },
  "publisher": {
    "@type": "Organization",
    "name": "{publisher_name}",
    "logo": {
      "@type": "ImageObject",
      "url": "{logo_url}"
    }
  },
  "datePublished": "{publish_date}",
  "dateModified": "{modify_date}"
}
</script>'''

    def _get_social_proof_template(self) -> str:
        """获取社会证明模板"""
        return '''<div class="social-proof">
  <div class="trust-badges">
    <span class="badge">⭐⭐⭐⭐⭐ 4.9/5 用户评分</span>
    <span class="badge">🏆 行业认证</span>
    <span class="badge">👥 10,000+ 活跃用户</span>
  </div>
  <div class="testimonials">
    <blockquote>
      <p>"这个产品彻底改变了我们的工作方式..."</p>
      <cite>— 张三，某科技公司 CEO</cite>
    </blockquote>
  </div>
</div>'''

    def _get_countdown_timer_template(self) -> str:
        """获取倒计时定时器模板"""
        return '''<script>
function initCountdown(targetDate) {
  const countdownEl = document.getElementById('countdown');

  function update() {
    const now = new Date().getTime();
    const distance = targetDate - now;

    if (distance < 0) {
      countdownEl.innerHTML = '已结束';
      return;
    }

    const hours = Math.floor(distance / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000);

    countdownEl.innerHTML = `${hours}小时 ${minutes}分 ${seconds}秒`;
  }

  update();
  setInterval(update, 1000);
}
</script>'''

    def generate_code_suggestions(
        self,
        analysis_result: RootCauseAnalysisResult,
        page_content: Optional[str] = None,
        tech_stack: Optional[Dict[str, Any]] = None
    ) -> List[CodeOptimizationSuggestion]:
        """
        基于根因分析结果生成代码优化建议

        Args:
            analysis_result: 根因分析结果
            page_content: 页面内容（可选，用于更精准的改动建议）
            tech_stack: 技术栈信息（可选）

        Returns:
            代码优化建议列表
        """
        suggestions = []
        tech_stack = tech_stack or self._detect_tech_stack(page_content)

        # 根据根因类别生成代码改动
        for root_cause in analysis_result.root_causes:
            cause_suggestions = self._generate_code_suggestions_for_cause(
                root_cause=root_cause,
                anomaly=analysis_result.anomaly,
                page_content=page_content,
                tech_stack=tech_stack
            )
            suggestions.extend(cause_suggestions)

        # 根据异常类型生成额外的代码建议
        anomaly_suggestions = self._generate_code_suggestions_for_anomaly(
            anomaly=analysis_result.anomaly,
            page_content=page_content,
            tech_stack=tech_stack
        )
        suggestions.extend(anomaly_suggestions)

        # 去重和优先级排序
        suggestions = self._deduplicate_and_sort(suggestions)

        return suggestions

    def generate_suggestion_from_optimization(
        self,
        optimization_suggestion: OptimizationSuggestion,
        page_content: Optional[str] = None,
        tech_stack: Optional[Dict[str, Any]] = None
    ) -> Optional[CodeOptimizationSuggestion]:
        """
        将优化建议转换为代码级建议

        Args:
            optimization_suggestion: AI 优化建议
            page_content: 页面内容
            tech_stack: 技术栈信息

        Returns:
            代码优化建议
        """
        tech_stack = tech_stack or self._detect_tech_stack(page_content)

        # 根据建议类型映射到代码改动模板
        template_mapping = {
            SuggestionType.SEO_OPTIMIZATION: ["title_meta", "structured_data", "heading_optimization"],
            SuggestionType.CONTENT_IMPROVEMENT: ["heading_optimization", "navigation_improvement"],
            SuggestionType.CONVERSION_OPTIMIZATION: ["cta_enhancement", "social_proof", "urgency_element", "form_optimization"],
            SuggestionType.PERFORMANCE_IMPROVEMENT: ["image_lazy_load", "image_optimization", "css_minification", "js_defer"],
            SuggestionType.UX_IMPROVEMENT: ["mobile_responsive", "navigation_improvement"]
        }

        templates_to_use = template_mapping.get(
            optimization_suggestion.suggestion_type,
            ["heading_optimization"]
        )

        changes = []
        for template_name in templates_to_use:
            change = self._create_code_change_from_template(
                template_name=template_name,
                context={
                    "suggestion": optimization_suggestion,
                    "page_content": page_content,
                    "tech_stack": tech_stack
                }
            )
            if change:
                changes.append(change)

        if not changes:
            return None

        return CodeOptimizationSuggestion(
            suggestion_id=f"code_{optimization_suggestion.suggestion_id}",
            title=f"代码实现：{optimization_suggestion.title}",
            description=f"将优化建议'{optimization_suggestion.title}'转换为可执行的代码改动",
            optimization_level=CodeOptimizationLevel.PAGE,
            changes=changes,
            expected_impact=optimization_suggestion.expected_impact,
            confidence=optimization_suggestion.confidence,
            effort_estimate=optimization_suggestion.estimated_timeline,
            risk_level=self._evaluate_risk(changes),
            testing_recommendations=self._get_testing_recommendations(changes),
            monitoring_metrics=optimization_suggestion.related_metrics
        )

    def generate_patch(self, suggestion: CodeOptimizationSuggestion) -> str:
        """
        生成可应用的代码补丁

        Args:
            suggestion: 代码优化建议

        Returns:
            补丁字符串（Unified Diff 格式）
        """
        patches = []

        for change in suggestion.changes:
            if change.diff:
                patches.append(change.diff)
            else:
                # 生成简化版补丁说明
                patch = f"""--- a/{change.target_file}
+++ b/{change.target_file}
@@ -0,0 +1,{len(change.new_code.split(chr(10)))} @@
+{change.description}
+代码改动类型：{change.change_type.value}
+目标选择器：{change.target_selector or 'N/A'}"""
                patches.append(patch)

        return "\n\n".join(patches)

    def export_as_json(self, suggestion: CodeOptimizationSuggestion) -> str:
        """
        导出为 JSON 格式

        Args:
            suggestion: 代码优化建议

        Returns:
            JSON 字符串
        """
        return json.dumps(suggestion.to_dict(), indent=2, ensure_ascii=False)

    def _generate_code_suggestions_for_cause(
        self,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult,
        page_content: Optional[str],
        tech_stack: Dict[str, Any]
    ) -> List[CodeOptimizationSuggestion]:
        """根据根因生成代码建议"""
        suggestions = []

        if root_cause.category == RootCauseCategory.KEYWORD_RANKING:
            # 关键词排名问题 - 生成 SEO 代码改动
            suggestion = self._create_seo_suggestion(root_cause, anomaly, page_content, tech_stack)
            suggestions.append(suggestion)

        elif root_cause.category == RootCauseCategory.PAGE_PERFORMANCE:
            # 页面性能问题 - 生成性能优化代码
            suggestion = self._create_performance_suggestion(root_cause, anomaly, page_content, tech_stack)
            suggestions.append(suggestion)

        elif root_cause.category == RootCauseCategory.CONTENT_ISSUE:
            # 内容问题 - 生成内容和 UX 优化代码
            suggestion = self._create_content_suggestion(root_cause, anomaly, page_content, tech_stack)
            suggestions.append(suggestion)

        elif root_cause.category == RootCauseCategory.CONVERSION_ISSUE:
            # 转化问题 - 生成转化优化代码
            suggestion = self._create_conversion_suggestion(root_cause, anomaly, page_content, tech_stack)
            suggestions.append(suggestion)

        return suggestions

    def _create_seo_suggestion(
        self,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult,
        page_content: Optional[str],
        tech_stack: Dict[str, Any]
    ) -> CodeOptimizationSuggestion:
        """创建 SEO 代码优化建议"""
        changes = [
            self._create_meta_tag_change(root_cause, page_content),
            self._create_structured_data_change(root_cause, page_content),
            self._create_heading_change(root_cause, page_content)
        ]

        return CodeOptimizationSuggestion(
            suggestion_id=f"seo_{uuid.uuid4().hex[:8]}",
            title="SEO 代码优化方案",
            description=f"针对{root_cause.description}的 SEO 代码改动方案",
            optimization_level=CodeOptimizationLevel.PAGE,
            changes=changes,
            expected_impact=0.15,
            confidence=0.8,
            effort_estimate="1-2 小时",
            risk_level="low",
            testing_recommendations=[
                "使用 Google Search Console 验证 Meta 标签",
                "使用 Rich Results Test 验证结构化数据",
                "检查页面在 SERP 中的显示效果"
            ],
            monitoring_metrics=["organic_traffic", "keyword_rankings", "click_through_rate"]
        )

    def _create_performance_suggestion(
        self,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult,
        page_content: Optional[str],
        tech_stack: Dict[str, Any]
    ) -> CodeOptimizationSuggestion:
        """创建性能优化代码建议"""
        changes = [
            self._create_image_optimization_change(page_content, tech_stack),
            self._create_js_defer_change(page_content),
            self._create_css_optimization_change(page_content, tech_stack)
        ]

        return CodeOptimizationSuggestion(
            suggestion_id=f"perf_{uuid.uuid4().hex[:8]}",
            title="页面性能优化方案",
            description=f"针对{root_cause.description}的性能优化代码改动",
            optimization_level=CodeOptimizationLevel.GLOBAL,
            changes=changes,
            expected_impact=0.2,
            confidence=0.75,
            effort_estimate="2-4 小时",
            risk_level="low",
            testing_recommendations=[
                "使用 PageSpeed Insights 测试优化前后对比",
                "使用 Lighthouse 进行性能审计",
                "在真实设备上测试加载速度"
            ],
            monitoring_metrics=["page_load_time", "first_contentful_paint", "time_to_interactive"]
        )

    def _create_content_suggestion(
        self,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult,
        page_content: Optional[str],
        tech_stack: Dict[str, Any]
    ) -> CodeOptimizationSuggestion:
        """创建内容优化代码建议"""
        changes = [
            self._create_heading_structure_change(page_content),
            self._create_content_layout_change(page_content),
            self._create_internal_link_change(page_content)
        ]

        return CodeOptimizationSuggestion(
            suggestion_id=f"content_{uuid.uuid4().hex[:8]}",
            title="内容结构优化方案",
            description=f"针对{root_cause.description}的内容结构改动",
            optimization_level=CodeOptimizationLevel.PAGE,
            changes=changes,
            expected_impact=0.12,
            confidence=0.7,
            effort_estimate="1-3 小时",
            risk_level="low",
            testing_recommendations=[
                "检查标题层级的逻辑性",
                "验证内部链接的有效性",
                "测试不同设备的阅读体验"
            ],
            monitoring_metrics=["avg_time_on_page", "bounce_rate", "scroll_depth"]
        )

    def _create_conversion_suggestion(
        self,
        root_cause: RootCause,
        anomaly: AnomalyDetectionResult,
        page_content: Optional[str],
        tech_stack: Dict[str, Any]
    ) -> CodeOptimizationSuggestion:
        """创建转化优化代码建议"""
        changes = [
            self._create_cta_enhancement_change(page_content, tech_stack),
            self._create_social_proof_change(page_content),
            self._create_form_optimization_change(page_content)
        ]

        return CodeOptimizationSuggestion(
            suggestion_id=f"conv_{uuid.uuid4().hex[:8]}",
            title="转化优化代码方案",
            description=f"针对{root_cause.description}的转化优化代码改动",
            optimization_level=CodeOptimizationLevel.COMPONENT,
            changes=changes,
            expected_impact=0.25,
            confidence=0.75,
            effort_estimate="2-4 小时",
            risk_level="medium",
            testing_recommendations=[
                "进行 A/B 测试验证效果",
                "检查移动端的显示效果",
                "验证表单提交功能正常"
            ],
            monitoring_metrics=["conversion_rate", "click_through_rate", "form_completion_rate"]
        )

    def _generate_code_suggestions_for_anomaly(
        self,
        anomaly: AnomalyDetectionResult,
        page_content: Optional[str],
        tech_stack: Dict[str, Any]
    ) -> List[CodeOptimizationSuggestion]:
        """根据异常类型生成代码建议"""
        suggestions = []

        if anomaly.anomaly_type == AnomalyType.CONVERSION_DROP:
            suggestion = self._create_conversion_suggestion(
                RootCause(RootCauseCategory.CONTENT_ISSUE, anomaly.description, "medium", [], 0.5, [], []),
                anomaly,
                page_content,
                tech_stack
            )
            suggestions.append(suggestion)

        elif anomaly.anomaly_type == AnomalyType.BOUNCE_RATE_SPIKE:
            suggestion = self._create_content_suggestion(
                RootCause(RootCauseCategory.CONTENT_ISSUE, anomaly.description, "medium", [], 0.5, [], []),
                anomaly,
                page_content,
                tech_stack
            )
            suggestions.append(suggestion)

        return suggestions

    def _create_code_change_from_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> Optional[CodeChange]:
        """从模板创建代码改动"""
        # 查找模板
        for category, templates in self._code_templates.items():
            if template_name in templates:
                template = templates[template_name]
                return self._instantiate_template(template, template_name, context)

        return None

    def _instantiate_template(
        self,
        template: Dict,
        template_name: str,
        context: Dict[str, Any]
    ) -> CodeChange:
        """实例化模板为代码改动"""
        change_id = f"change_{uuid.uuid4().hex[:8]}"
        suggestion = context.get("suggestion")

        # 生成具体的代码改动
        old_code, new_code, diff = self._generate_code_diff(template, template_name, context)

        return CodeChange(
            change_id=change_id,
            change_type=template["type"],
            target_file=self._determine_target_file(template_name, context),
            target_selector=self._determine_target_selector(template_name, context),
            description=f"实施{template_name}优化",
            old_code=old_code,
            new_code=new_code,
            diff=diff,
            language=self._determine_language(template["type"]),
            confidence=self.default_confidence,
            estimated_impact=suggestion.expected_impact if suggestion else 0.1,
            implementation_notes=template.get("implementation_notes", []),
            rollback_plan=self._create_rollback_plan(template, context),
            related_suggestion_id=suggestion.suggestion_id if suggestion else None
        )

    def _generate_code_diff(
        self,
        template: Dict,
        template_name: str,
        context: Dict[str, Any]
    ) -> Tuple[Optional[str], str, str]:
        """生成代码 diff"""
        # 简化实现，实际应该基于页面内容生成具体的 diff
        page_content = context.get("page_content", "")

        if template_name == "title_meta":
            old_code = "<title>当前标题</title>"
            new_code = """<title>优化后的标题 | 网站名称</title>
<meta name="description" content="优化的 Meta 描述，包含核心关键词，长度控制在 150-160 字符">"""
            diff = f"""--- a/page.html
+++ b/page.html
@@ -1,5 +1,7 @@
 <head>
-  <title>当前标题</title>
+  <title>优化后的标题 | 网站名称</title>
+  <meta name="description" content="优化的 Meta 描述">
+  <meta name="keywords" content="关键词 1, 关键词 2">
 </head>"""

        elif template_name == "structured_data":
            old_code = None
            new_code = template.get("json_ld_snippet", "")
            diff = f"""--- a/page.html
+++ b/page.html
@@ -0,0 +1,20 @@
+<script type="application/ld+json">
+{{
+  "@context": "https://schema.org",
+  "@type": "WebPage",
+  "name": "页面名称"
+}}
+</script>"""

        elif template_name == "cta_enhancement":
            old_code = '<a href="/signup" class="btn">立即购买</a>'
            new_code = '<a href="/signup" class="btn btn-primary cta-pulse">免费试用</a>'
            diff = f"""--- a/page.html
+++ b/page.html
@@ -10,7 +10,7 @@
-  <a href="/signup" class="btn">立即购买</a>
+  <a href="/signup" class="btn btn-primary cta-pulse">免费试用</a>
 </div>"""

        else:
            old_code = None
            new_code = f"<!-- {template_name} implementation -->"
            diff = f"<!-- {template_name} changes -->"

        return old_code, new_code, diff

    def _determine_target_file(self, template_name: str, context: Dict) -> str:
        """确定目标文件"""
        page_content = context.get("page_content")
        if page_content:
            return "page.html"

        file_mapping = {
            "title_meta": "page.html",
            "structured_data": "page.html",
            "cta_enhancement": "components/cta.html",
            "image_optimization": "assets/images/",
            "css_minification": "styles/main.css",
            "js_defer": "scripts/main.js"
        }
        return file_mapping.get(template_name, "page.html")

    def _determine_target_selector(self, template_name: str, context: Dict) -> Optional[str]:
        """确定目标 CSS 选择器"""
        selector_mapping = {
            "title_meta": "head > title",
            "cta_enhancement": ".cta-button",
            "heading_optimization": "h1",
            "social_proof": ".social-proof-section",
            "form_optimization": "form"
        }
        return selector_mapping.get(template_name)

    def _determine_language(self, change_type: CodeChangeType) -> str:
        """确定代码语言"""
        language_mapping = {
            CodeChangeType.HTML_MODIFICATION: "html",
            CodeChangeType.CSS_MODIFICATION: "css",
            CodeChangeType.JAVASCRIPT_MODIFICATION: "javascript",
            CodeChangeType.META_TAG_UPDATE: "html",
            CodeChangeType.STRUCTURED_DATA: "json",
            CodeChangeType.LAZY_LOADING: "javascript",
            CodeChangeType.IMAGE_OPTIMIZATION: "config",
            CodeChangeType.CACHING_CONFIG: "config",
            CodeChangeType.CDN_CONFIG: "config"
        }
        return language_mapping.get(change_type, "html")

    def _create_rollback_plan(self, template: Dict, context: Dict) -> str:
        """创建回滚方案"""
        return f"如需回滚，请将{template['type'].value}改动还原至原版本，建议使用版本控制系统进行回滚操作"

    def _evaluate_risk(self, changes: List[CodeChange]) -> str:
        """评估风险级别"""
        high_risk_types = [CodeChangeType.JAVASCRIPT_MODIFICATION]
        medium_risk_types = [CodeChangeType.HTML_MODIFICATION, CodeChangeType.CSS_MODIFICATION]
        low_risk_types = [CodeChangeType.META_TAG_UPDATE, CodeChangeType.STRUCTURED_DATA]

        for change in changes:
            if change.change_type in high_risk_types:
                return "medium"

        for change in changes:
            if change.change_type in medium_risk_types:
                return "low"

        return "low"

    def _get_testing_recommendations(self, changes: List[CodeChange]) -> List[str]:
        """获取测试建议"""
        recommendations = [
            "在 staging 环境先进行测试",
            "使用 A/B 测试验证效果",
            "监控关键指标变化"
        ]

        for change in changes:
            if change.change_type == CodeChangeType.JAVASCRIPT_MODIFICATION:
                recommendations.append("进行跨浏览器兼容性测试")
            elif change.change_type == CodeChangeType.CSS_MODIFICATION:
                recommendations.append("进行响应式设计测试")

        return recommendations

    def _detect_tech_stack(self, page_content: Optional[str]) -> Dict[str, Any]:
        """检测技术栈"""
        tech_stack = {
            "framework": "unknown",
            "css_framework": "unknown",
            "js_framework": "unknown"
        }

        if not page_content:
            return tech_stack

        # 检测常见框架特征
        if "react" in page_content.lower() or "ReactDOM" in page_content:
            tech_stack["framework"] = "React"
        elif "vue" in page_content.lower() or "Vue.component" in page_content:
            tech_stack["framework"] = "Vue"
        elif "angular" in page_content.lower():
            tech_stack["framework"] = "Angular"

        if "bootstrap" in page_content.lower():
            tech_stack["css_framework"] = "Bootstrap"
        elif "tailwind" in page_content.lower():
            tech_stack["css_framework"] = "Tailwind"

        return tech_stack

    def _deduplicate_and_sort(
        self,
        suggestions: List[CodeOptimizationSuggestion]
    ) -> List[CodeOptimizationSuggestion]:
        """去重并按优先级排序"""
        # 按标题去重
        seen_titles = set()
        unique_suggestions = []

        for sugg in suggestions:
            if sugg.title not in seen_titles:
                seen_titles.add(sugg.title)
                unique_suggestions.append(sugg)

        # 按预期影响和置信度排序
        unique_suggestions.sort(
            key=lambda x: (-x.expected_impact * x.confidence, x.risk_level)
        )

        return unique_suggestions

    # ========== 以下为各类型代码改动的具体实现方法 ==========

    def _create_meta_tag_change(self, root_cause: RootCause, page_content: Optional[str]) -> CodeChange:
        """创建 Meta 标签改动"""
        return CodeChange(
            change_id=f"meta_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.META_TAG_UPDATE,
            target_file="page.html",
            target_selector="head > title",
            description="优化页面 Title 和 Meta 标签",
            old_code="<title>当前标题</title>",
            new_code='<title>优化后的标题 | 网站名称</title>\n<meta name="description" content="优化的 Meta 描述">',
            diff='--- meta tags diff ---',
            language="html",
            confidence=0.9,
            estimated_impact=0.1,
            implementation_notes=[
                "Title 控制在 50-60 字符",
                "Meta Description 控制在 150-160 字符",
                "包含核心关键词"
            ],
            rollback_plan="还原原始 Title 和 Meta 标签"
        )

    def _create_structured_data_change(self, root_cause: RootCause, page_content: Optional[str]) -> CodeChange:
        """创建结构化数据改动"""
        return CodeChange(
            change_id=f"schema_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.STRUCTURED_DATA,
            target_file="page.html",
            target_selector="head",
            description="添加 Schema.org 结构化数据",
            old_code=None,
            new_code='<script type="application/ld+json">...</script>',
            diff='--- structured data diff ---',
            language="json",
            confidence=0.85,
            estimated_impact=0.08,
            implementation_notes=[
                "使用 JSON-LD 格式",
                "验证 schema 类型正确",
                "使用 Google Rich Results Test 验证"
            ],
            rollback_plan="移除添加的结构化数据脚本"
        )

    def _create_heading_change(self, root_cause: RootCause, page_content: Optional[str]) -> CodeChange:
        """创建标题改动"""
        return CodeChange(
            change_id=f"heading_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.HTML_MODIFICATION,
            target_file="page.html",
            target_selector="h1",
            description="优化 H1 标题结构和关键词",
            old_code="<h1>当前标题</h1>",
            new_code="<h1>包含关键词的优化标题</h1>",
            diff='--- heading diff ---',
            language="html",
            confidence=0.8,
            estimated_impact=0.12,
            implementation_notes=[
                "确保只有一个 H1",
                "H1 包含核心关键词",
                "建立清晰的 H1-H6 层级"
            ],
            rollback_plan="还原原始标题"
        )

    def _create_image_optimization_change(self, page_content: Optional[str], tech_stack: Dict) -> CodeChange:
        """创建图片优化改动"""
        return CodeChange(
            change_id=f"img_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.IMAGE_OPTIMIZATION,
            target_file="assets/images/",
            target_selector="img",
            description="图片格式优化和懒加载",
            old_code='<img src="image.jpg">',
            new_code='<img src="image.webp" loading="lazy" width="800" height="600">',
            diff='--- image optimization diff ---',
            language="html",
            confidence=0.85,
            estimated_impact=0.15,
            implementation_notes=[
                "转换为 WebP 格式",
                "添加懒加载属性",
                "指定宽高避免布局偏移"
            ],
            rollback_plan="还原原始图片格式"
        )

    def _create_js_defer_change(self, page_content: Optional[str]) -> CodeChange:
        """创建 JS 延迟加载改动"""
        return CodeChange(
            change_id=f"js_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.JAVASCRIPT_MODIFICATION,
            target_file="page.html",
            target_selector="script[src]",
            description="非关键 JS 添加 defer 属性",
            old_code='<script src="analytics.js"></script>',
            new_code='<script src="analytics.js" defer></script>',
            diff='--- JS defer diff ---',
            language="html",
            confidence=0.9,
            estimated_impact=0.1,
            implementation_notes=[
                "仅对非关键 JS 使用 defer",
                "确保脚本不依赖 DOMContentLoaded",
                "测试功能正常"
            ],
            rollback_plan="移除 defer 属性"
        )

    def _create_css_optimization_change(self, page_content: Optional[str], tech_stack: Dict) -> CodeChange:
        """创建 CSS 优化改动"""
        return CodeChange(
            change_id=f"css_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.CSS_MODIFICATION,
            target_file="styles/main.css",
            target_selector="*",
            description="CSS 压缩和关键 CSS 内联",
            old_code="/* 原始 CSS */",
            new_code="/* 压缩后的 CSS */",
            diff='--- CSS optimization diff ---',
            language="css",
            confidence=0.8,
            estimated_impact=0.1,
            implementation_notes=[
                "压缩 CSS 文件",
                "关键 CSS 内联到<head>",
                "移除未使用的 CSS"
            ],
            rollback_plan="还原原始 CSS 文件"
        )

    def _create_heading_structure_change(self, page_content: Optional[str]) -> CodeChange:
        """创建标题结构改动"""
        return CodeChange(
            change_id=f"heading_struct_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.HTML_MODIFICATION,
            target_file="page.html",
            target_selector="h1, h2, h3",
            description="优化标题层级结构",
            old_code="<!-- 原始标题结构 -->",
            new_code="<!-- 优化后的标题结构 -->",
            diff='--- heading structure diff ---',
            language="html",
            confidence=0.75,
            estimated_impact=0.1,
            implementation_notes=[
                "确保逻辑清晰的层级",
                "每个章节有明确的标题",
                "关键词自然融入标题"
            ],
            rollback_plan="还原原始标题结构"
        )

    def _create_content_layout_change(self, page_content: Optional[str]) -> CodeChange:
        """创建内容布局改动"""
        return CodeChange(
            change_id=f"layout_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.HTML_MODIFICATION,
            target_file="page.html",
            target_selector=".content",
            description="改进内容布局和可读性",
            old_code="<div class='content'>...</div>",
            new_code="<div class='content content-enhanced'>...</div>",
            diff='--- content layout diff ---',
            language="html",
            confidence=0.7,
            estimated_impact=0.08,
            implementation_notes=[
                "增加段落间距",
                "使用项目符号列表",
                "添加重点内容高亮"
            ],
            rollback_plan="还原原始布局"
        )

    def _create_internal_link_change(self, page_content: Optional[str]) -> CodeChange:
        """创建内部链接改动"""
        return CodeChange(
            change_id=f"link_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.HTML_MODIFICATION,
            target_file="page.html",
            target_selector="a[href]",
            description="添加相关内部链接",
            old_code="<!-- 原始链接 -->",
            new_code="<a href='/related-page' class='internal-link'>相关内容</a>",
            diff='--- internal link diff ---',
            language="html",
            confidence=0.75,
            estimated_impact=0.05,
            implementation_notes=[
                "在相关内容处添加链接",
                "使用描述性锚文本",
                "避免过度链接"
            ],
            rollback_plan="移除添加的内部链接"
        )

    def _create_cta_enhancement_change(self, page_content: Optional[str], tech_stack: Dict) -> CodeChange:
        """创建 CTA 优化改动"""
        return CodeChange(
            change_id=f"cta_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.HTML_MODIFICATION,
            target_file="page.html",
            target_selector=".cta-button",
            description="优化 CTA 按钮设计和文案",
            old_code='<a href="/signup" class="btn">立即购买</a>',
            new_code='<a href="/signup" class="btn btn-primary cta-pulse">免费试用</a>',
            diff='--- CTA enhancement diff ---',
            language="html",
            confidence=0.8,
            estimated_impact=0.2,
            implementation_notes=[
                "使用对比色突出 CTA",
                "优化文案强调价值",
                "添加微动画效果"
            ],
            rollback_plan="还原原始 CTA 设计"
        )

    def _create_social_proof_change(self, page_content: Optional[str]) -> CodeChange:
        """创建社会证明改动"""
        return CodeChange(
            change_id=f"social_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.HTML_MODIFICATION,
            target_file="page.html",
            target_selector=".social-proof",
            description="添加用户评价和信任徽章",
            old_code=None,
            new_code='<div class="social-proof">...</div>',
            diff='--- social proof diff ---',
            language="html",
            confidence=0.75,
            estimated_impact=0.15,
            implementation_notes=[
                "添加真实用户评价",
                "展示信任徽章和认证",
                "显示用户数量或活跃度"
            ],
            rollback_plan="移除社会证明模块"
        )

    def _create_form_optimization_change(self, page_content: Optional[str]) -> CodeChange:
        """创建表单优化改动"""
        return CodeChange(
            change_id=f"form_{uuid.uuid4().hex[:8]}",
            change_type=CodeChangeType.HTML_MODIFICATION,
            target_file="page.html",
            target_selector="form",
            description="简化表单并优化体验",
            old_code="<form>...</form>",
            new_code="<form class='optimized-form'>...</form>",
            diff='--- form optimization diff ---',
            language="html",
            confidence=0.75,
            estimated_impact=0.18,
            implementation_notes=[
                "减少必填字段",
                "添加实时验证反馈",
                "使用自动填充功能"
            ],
            rollback_plan="还原原始表单"
        )


# 全局服务实例
code_optimizer_service = CodeOptimizerService()
