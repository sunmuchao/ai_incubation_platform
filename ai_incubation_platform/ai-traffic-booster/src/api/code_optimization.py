"""
AI 代码优化 API - P2 优化草稿 (代码改动)

提供代码级优化建议生成、补丁生成和预览功能
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, Body

from ai.code_optimizer import (
    CodeChange,
    CodeOptimizationLevel,
    CodeChangeType,
)
from ai.recommendation_engine import recommendation_engine
from ai.anomaly_detection import anomaly_detection_service
from ai.root_cause_analysis import root_cause_analysis_service


router = APIRouter(prefix="/ai/code-optimization", tags=["AI Code Optimization"])


# ==================== Schema 定义 ====================

class CodeOptimizationRequest(BaseModel):
    """代码优化请求"""
    suggestion_id: Optional[str] = None
    page_url: Optional[str] = None
    optimization_type: str = "seo"  # seo, performance, conversion
    code_type: str = "html"  # html, css, javascript, meta


class CodePreviewResponse(BaseModel):
    """代码预览响应"""
    change_id: str
    change_type: str
    target_file: str
    target_selector: Optional[str]
    description: str
    original_code: Optional[str]
    modified_code: str
    diff: str
    confidence: float
    expected_impact: str
    application_instructions: str


# ==================== API 端点 ====================

@router.post("/generate", response_model=List[CodePreviewResponse])
async def generate_code_optimization(
    request: CodeOptimizationRequest,
):
    """
    生成代码级优化建议

    基于优化建议生成可执行的代码改动

    - **suggestion_id**: 优化建议 ID（可选）
    - **page_url**: 目标页面 URL
    - **optimization_type**: 优化类型 (seo, performance, conversion)
    - **code_type**: 代码类型 (html, css, javascript, meta)
    """
    # 生成代码改动建议
    changes = code_change_generator.generate_changes(
        optimization_type=request.optimization_type,
        page_url=request.page_url,
        code_type=request.code_type,
    )

    return [c.to_dict() for c in changes]


@router.post("/generate-for-anomaly")
async def generate_code_for_anomaly(
    metric_name: str = Query(..., description="指标名称"),
    current_value: float = Query(..., description="当前值"),
    historical_values: List[float] = Body(..., description="历史值列表"),
    page_url: Optional[str] = Body(None, description="目标页面 URL"),
):
    """
    为流量异常生成代码修复方案

    1. 检测异常
    2. 根因分析
    3. 生成优化建议
    4. 生成代码改动
    """
    # 异常检测
    anomaly = anomaly_detection_service.detect_anomalies(
        metric_name=metric_name,
        current_value=current_value,
        historical_values=historical_values,
    )

    if not anomaly.is_anomaly:
        return {"status": "no_anomaly", "message": "未检测到异常"}

    # 根因分析
    analysis = root_cause_analysis_service.analyze(anomaly=anomaly)

    # 生成优化建议
    suggestions = recommendation_engine.generate_suggestions(analysis)

    # 生成代码改动
    all_changes = []
    for suggestion in suggestions[:3]:  # 最多处理前 3 个建议
        changes = code_change_generator.generate_changes_for_suggestion(
            suggestion=suggestion,
            page_url=page_url,
        )
        all_changes.extend(changes)

    return {
        "status": "completed",
        "anomaly": anomaly.to_dict(),
        "analysis_summary": analysis.analysis_summary,
        "suggestions_count": len(suggestions),
        "code_changes": [c.to_dict() for c in all_changes],
    }


@router.get("/templates/{change_type}")
async def get_code_template(
    change_type: str,
    optimization_goal: str = Query("seo", description="优化目标"),
):
    """
    获取代码模板

    返回常见优化场景的代码模板
    """
    templates = code_change_generator.get_template(change_type, optimization_goal)

    return {
        "change_type": change_type,
        "optimization_goal": optimization_goal,
        "templates": templates,
    }


@router.get("/examples")
async def get_code_examples():
    """
    获取代码优化示例

    展示各种类型的代码改动示例
    """
    examples = {
        "seo_meta_tags": {
            "description": "SEO Meta 标签优化",
            "original": "<title>首页</title>",
            "modified": "<title>核心产品与服务 | 品牌名称 - 2026 最新</title>\n<meta name=\"description\" content=\"提供优质的产品与服务，专注于...\">\n<meta name=\"keywords\" content=\"关键词 1, 关键词 2, 关键词 3\">",
            "impact": "提升搜索引擎理解和排名"
        },
        "structured_data": {
            "description": "结构化数据 (Schema.org)",
            "code": """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "公司名称",
  "url": "https://example.com",
  "logo": "https://example.com/logo.png"
}
</script>""",
            "impact": "增强搜索结果显示（富片段）"
        },
        "lazy_loading": {
            "description": "图片懒加载",
            "original": '<img src="image.jpg" alt="描述">',
            "modified": '<img src="placeholder.jpg" data-src="image.jpg" alt="描述" loading="lazy" class="lazyload">',
            "impact": "提升页面加载速度"
        },
        "critical_css": {
            "description": "关键 CSS 内联",
            "description_detail": "将首屏关键 CSS 内联到 HTML，其余 CSS 异步加载",
            "impact": "提升首屏渲染速度"
        }
    }

    return {"examples": examples}


@router.get("/best-practices")
async def get_best_practices():
    """
    获取代码优化最佳实践

    返回 SEO、性能、转化率优化的最佳实践指南
    """
    return {
        "seo": {
            "title_optimization": "标题应包含核心关键词，长度 50-60 字符",
            "meta_description": "描述应有吸引力，长度 150-160 字符",
            "heading_structure": "使用 H1/H2/H3 层级结构，H1 仅用一次",
            "internal_linking": "添加相关内容内部链接，传递页面权重",
            "image_alt": "所有图片应有描述性 alt 文本",
            "structured_data": "添加 Schema.org 结构化数据"
        },
        "performance": {
            "image_optimization": "压缩图片，使用 WebP 格式",
            "lazy_loading": "非首屏资源使用懒加载",
            "css_minification": "压缩 CSS 文件，移除未使用样式",
            "js_defer": "非关键 JS 使用 defer/async 加载",
            "caching": "设置合理的浏览器缓存策略",
            "cdn": "使用 CDN 分发静态资源"
        },
        "conversion": {
            "cta_placement": "CTA 按钮放在首屏和关键决策点",
            "form_optimization": "减少表单字段，提供清晰指引",
            "trust_signals": "添加信任标志（评价、认证、保障）",
            "urgency_scarcity": "适度使用紧迫感元素（限时、限量）",
            "mobile_optimization": "确保移动端体验流畅"
        }
    }
