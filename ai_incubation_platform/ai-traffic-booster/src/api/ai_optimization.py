"""
AI 自主优化 API - Layer 4 AI 自主优化功能接口

功能:
- 自动 A/B 测试设计与执行
- 代码级优化建议生成
- 优化效果验证与学习
- 学习洞察查询
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from pydantic import BaseModel, Field
import logging

from ai.auto_ab_test import auto_ab_test_service, AutoTestDesign, TestHypothesisType
from ai.code_optimizer import code_optimizer_service, CodeOptimizationSuggestion
from ai.learning_loop import learning_feedback_loop
from ai.anomaly_detection import AnomalyDetectionResult, AnomalyType, AnomalySeverity
from ai.root_cause_analysis import RootCauseAnalysisResult, RootCause, RootCauseCategory, RootCauseConfidence
from ai.recommendation_engine import OptimizationSuggestion, SuggestionType, SuggestionPriority, SuggestionEffort

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-optimization", tags=["AI 自主优化"])


# ========== 请求/响应模型 ==========

class TestDesignRequest(BaseModel):
    """测试设计请求"""
    root_causes: List[Dict[str, Any]] = Field(..., description="根因列表")
    anomaly: Dict[str, Any] = Field(..., description="异常检测结果")
    context: Optional[Dict[str, Any]] = Body(default=None, description="上下文信息")


class TestDesignResponse(BaseModel):
    """测试设计响应"""
    test_id: str
    hypothesis: str
    hypothesis_type: str
    hypothesis_type_description: str
    page_url: str
    variants: List[Dict[str, Any]]
    primary_metric: str
    secondary_metrics: List[str]
    minimum_sample_size: int
    estimated_duration_days: int
    confidence_level: float
    statistical_power: float
    minimum_detectable_effect: float
    rationale: str
    expected_impact: float
    implementation_complexity: str
    created_at: str


class ExecuteTestRequest(BaseModel):
    """执行测试请求"""
    test_id: str = Field(..., description="测试设计 ID")
    created_by: str = Field(default="system", description="创建者")


class ExecuteTestResponse(BaseModel):
    """执行测试响应"""
    success: bool
    test_id: Optional[str] = None
    message: str
    test_detail: Optional[Dict[str, Any]] = None


class CodeSuggestionRequest(BaseModel):
    """代码建议请求"""
    root_causes: List[Dict[str, Any]] = Field(..., description="根因列表")
    anomaly: Dict[str, Any] = Field(..., description="异常检测结果")
    page_content: Optional[str] = Field(default=None, description="页面内容")
    tech_stack: Optional[Dict[str, Any]] = Field(default=None, description="技术栈信息")


class CodeSuggestionResponse(BaseModel):
    """代码建议响应"""
    suggestion_id: str
    title: str
    description: str
    optimization_level: str
    changes: List[Dict[str, Any]]
    expected_impact: float
    confidence: float
    effort_estimate: str
    risk_level: str
    testing_recommendations: List[str]
    monitoring_metrics: List[str]
    created_at: str


class LearningInsightRequest(BaseModel):
    """学习洞察请求"""
    suggestion_type: Optional[str] = Field(default=None, description="建议类型")
    root_cause_category: Optional[str] = Field(default=None, description="根因类别")
    limit: int = Field(default=10, description="返回数量限制")


class LearningInsightResponse(BaseModel):
    """学习洞察响应"""
    type: str
    suggestion_type: Optional[str]
    root_cause_category: Optional[str]
    success_rate: Optional[float]
    avg_impact: Optional[float]
    recommendation: Optional[str]
    confidence: Optional[str]
    lessons: Optional[List[str]]
    total_samples: Optional[int]


class OptimizeSuggestionRankingRequest(BaseModel):
    """建议优先级优化请求"""
    suggestions: List[Dict[str, Any]] = Field(..., description="建议列表")
    context: Optional[Dict[str, Any]] = Body(default=None, description="上下文信息")


class RecommendationResponse(BaseModel):
    """推荐方案响应"""
    recommended_type: Optional[str]
    expected_success_rate: float
    expected_impact: float
    confidence: str
    reasoning: str


# ========== 自动 A/B 测试设计 API ==========

@router.post("/auto-ab-test/design",
             response_model=List[TestDesignResponse],
             summary="自动生成 A/B 测试设计方案",
             description="基于根因分析结果自动生成 A/B 测试设计方案")
async def generate_ab_test_designs(request: TestDesignRequest):
    """
    自动生成 A/B 测试设计方案

    - 根据根因分析结果生成测试假设
    - 自动设计测试变体方案
    - 计算最小样本量和测试周期
    - 返回多个测试设计方案按优先级排序
    """
    try:
        # 构建分析结果对象
        root_causes = [
            RootCause(
                category=RootCauseCategory(rc["category"]),
                description=rc["description"],
                confidence=RootCauseConfidence(rc["confidence"]),
                evidence=rc.get("evidence", []),
                impact_score=rc.get("impact_score", 0.5),
                contributing_factors=rc.get("contributing_factors", []),
                recommended_actions=rc.get("recommended_actions", [])
            )
            for rc in request.root_causes
        ]

        anomaly = AnomalyDetectionResult(
            is_anomaly=request.anomaly.get("is_anomaly", False),
            anomaly_type=AnomalyType(request.anomaly["anomaly_type"]) if request.anomaly.get("anomaly_type") else None,
            severity=AnomalySeverity(request.anomaly["severity"]) if request.anomaly.get("severity") else None,
            metric_name=request.anomaly.get("metric_name", ""),
            current_value=request.anomaly.get("current_value", 0),
            expected_value=request.anomaly.get("expected_value", 0),
            deviation=request.anomaly.get("deviation", 0),
            z_score=request.anomaly.get("z_score", 0),
            confidence=request.anomaly.get("confidence", 0),
            description=request.anomaly.get("description", "")
        )

        analysis_result = RootCauseAnalysisResult(
            anomaly=anomaly,
            root_causes=root_causes,
            primary_cause=root_causes[0] if root_causes else None,
            analysis_summary="基于根因分析生成测试设计"
        )

        # 生成测试设计
        designs = auto_ab_test_service.generate_test_designs(
            analysis_result=analysis_result,
            context=request.context or {}
        )

        # 转换为响应格式
        return [
            TestDesignResponse(**design.to_dict())
            for design in designs
        ]

    except Exception as e:
        logger.error(f"生成 A/B 测试设计失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-ab-test/execute",
             response_model=ExecuteTestResponse,
             summary="执行 A/B 测试设计",
             description="将测试设计创建为实际的 A/B 测试并自动启动")
async def execute_ab_test(request: ExecuteTestRequest):
    """
    执行 A/B 测试设计

    - 根据测试设计 ID 创建实际测试
    - 自动启动测试
    - 返回测试详情
    """
    try:
        # 这里需要一个方法来根据 test_id 获取设计
        # 简化处理，返回成功消息
        test = auto_ab_test_service.execute_test(
            test_design=None,  # 实际实现需要从存储获取
            created_by=request.created_by
        )

        if test:
            return ExecuteTestResponse(
                success=True,
                test_id=test.id,
                message="测试已成功创建并启动",
                test_detail={"id": test.id, "name": test.name, "status": test.status.value}
            )
        else:
            return ExecuteTestResponse(
                success=False,
                message="测试执行失败"
            )

    except Exception as e:
        logger.error(f"执行 A/B 测试失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-ab-test/{test_id}/analyze",
            response_model=Dict[str, Any],
            summary="分析 A/B 测试结果",
            description="分析已完成或进行中的 A/B 测试结果并生成 AI 建议")
async def analyze_ab_test_result(test_id: str):
    """
    分析 A/B 测试结果

    - 获取测试结果数据
    - 生成 AI 分析报告
    - 提供下一步行动建议
    """
    try:
        analysis = auto_ab_test_service.analyze_test_result(test_id)

        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])

        return analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析 A/B 测试结果失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 代码级优化建议 API ==========

@router.post("/code-optimizer/generate",
             response_model=List[CodeSuggestionResponse],
             summary="生成代码级优化建议",
             description="基于 AI 分析结果生成可执行的代码改动建议")
async def generate_code_suggestions(request: CodeSuggestionRequest):
    """
    生成代码级优化建议

    - 根据根因分析生成代码改动
    - 支持多种优化类型：SEO、性能、转化
    - 生成可一键应用的代码补丁
    """
    try:
        # 构建分析结果对象
        root_causes = [
            RootCause(
                category=RootCauseCategory(rc["category"]),
                description=rc["description"],
                confidence=RootCauseConfidence(rc["confidence"]),
                evidence=rc.get("evidence", []),
                impact_score=rc.get("impact_score", 0.5),
                contributing_factors=rc.get("contributing_factors", []),
                recommended_actions=rc.get("recommended_actions", [])
            )
            for rc in request.root_causes
        ]

        anomaly = AnomalyDetectionResult(
            is_anomaly=request.anomaly.get("is_anomaly", False),
            anomaly_type=AnomalyType(request.anomaly["anomaly_type"]) if request.anomaly.get("anomaly_type") else None,
            severity=AnomalySeverity(request.anomaly["severity"]) if request.anomaly.get("severity") else None,
            metric_name=request.anomaly.get("metric_name", ""),
            current_value=request.anomaly.get("current_value", 0),
            expected_value=request.anomaly.get("expected_value", 0),
            deviation=request.anomaly.get("deviation", 0),
            z_score=request.anomaly.get("z_score", 0),
            confidence=request.anomaly.get("confidence", 0),
            description=request.anomaly.get("description", "")
        )

        analysis_result = RootCauseAnalysisResult(
            anomaly=anomaly,
            root_causes=root_causes,
            primary_cause=root_causes[0] if root_causes else None,
            analysis_summary="基于根因分析生成代码优化建议"
        )

        # 生成代码优化建议
        suggestions = code_optimizer_service.generate_code_suggestions(
            analysis_result=analysis_result,
            page_content=request.page_content,
            tech_stack=request.tech_stack
        )

        # 转换为响应格式
        return [
            CodeSuggestionResponse(**suggestion.to_dict())
            for suggestion in suggestions
        ]

    except Exception as e:
        logger.error(f"生成代码优化建议失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code-optimizer/patch",
             response_model=Dict[str, str],
             summary="生成代码补丁",
             description="将代码优化建议导出为可应用的补丁格式")
async def generate_code_patch(suggestion_id: str):
    """
    生成代码补丁

    - 根据建议 ID 生成 Unified Diff 格式补丁
    - 支持 JSON 格式导出
    """
    try:
        # 这里需要从存储获取建议
        # 简化处理，返回示例补丁
        return {
            "patch": f"# 补丁生成需要 suggestion_id={suggestion_id}\n# 实际实现需要从存储获取建议数据",
            "format": "unified_diff"
        }

    except Exception as e:
        logger.error(f"生成代码补丁失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 闭环学习 API ==========

@router.get("/learning/insights",
            response_model=List[LearningInsightResponse],
            summary="获取学习洞察",
            description="获取基于历史优化经验的学习洞察")
async def get_learning_insights(
    suggestion_type: Optional[str] = Query(default=None, description="建议类型"),
    root_cause_category: Optional[str] = Query(default=None, description="根因类别"),
    limit: int = Query(default=10, description="返回数量限制")
):
    """
    获取学习洞察

    - 分析历史优化效果
    - 识别最有效的建议类型
    - 提供基于数据的推荐
    """
    try:
        insights = learning_feedback_loop.get_learning_insights(limit=limit)

        return [
            LearningInsightResponse(
                type=insight.get("type", ""),
                suggestion_type=insight.get("suggestion_type"),
                root_cause_category=insight.get("root_cause_category"),
                success_rate=insight.get("success_rate"),
                avg_impact=insight.get("avg_impact"),
                recommendation=insight.get("recommendation"),
                confidence=insight.get("confidence"),
                lessons=insight.get("lessons"),
                total_samples=insight.get("total_samples")
            )
            for insight in insights
        ]

    except Exception as e:
        logger.error(f"获取学习洞察失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/effectiveness",
            response_model=Dict[str, Any],
            summary="获取建议有效性统计",
            description="获取特定建议类型或根因类别的有效性统计")
async def get_suggestion_effectiveness(
    suggestion_type: Optional[str] = Query(default=None, description="建议类型"),
    root_cause_category: Optional[str] = Query(default=None, description="根因类别")
):
    """
    获取建议有效性统计

    - 查询历史成功率
    - 平均影响程度
    - 推荐等级
    """
    try:
        from ai.recommendation_engine import SuggestionType
        from ai.root_cause_analysis import RootCauseCategory

        st = SuggestionType(suggestion_type) if suggestion_type else None
        rc = RootCauseCategory(root_cause_category) if root_cause_category else None

        stats = learning_feedback_loop.get_suggestion_effectiveness(
            suggestion_type=st,
            root_cause_category=rc
        )

        return stats

    except Exception as e:
        logger.error(f"获取有效性统计失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/recommend",
             response_model=RecommendationResponse,
             summary="获取上下文推荐",
             description="基于历史学习和当前上下文获取推荐方案")
async def get_recommendation_for_context(
    root_cause_category: str = Query(..., description="根因类别"),
    anomaly_type: str = Query(..., description="异常类型"),
    context: Optional[Dict[str, Any]] = Body(default=None, description="上下文信息")
):
    """
    获取上下文推荐

    - 基于历史优化经验
    - 针对特定根因和异常类型
    - 提供最有效的建议类型推荐
    """
    try:
        recommendation = learning_feedback_loop.get_recommendation_for_context(
            root_cause_category=root_cause_category,
            anomaly_type=anomaly_type,
            context=context
        )

        return RecommendationResponse(**recommendation)

    except Exception as e:
        logger.error(f"获取推荐失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/report",
            response_model=Dict[str, Any],
            summary="导出学习报告",
            description="导出完整的优化学习报告（JSON 格式）")
async def export_learning_report():
    """
    导出学习报告

    - 包含所有聚合统计
    - 各类型建议性能
    - 根因类别有效性
    - 高价值学习洞察
    """
    try:
        import json
        report = json.loads(learning_feedback_loop.export_learning_report())
        return report

    except Exception as e:
        logger.error(f"导出学习报告失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 建议优先级优化 API ==========

@router.post("/suggestions/rank",
             response_model=List[Dict[str, Any]],
             summary="优化建议优先级排序",
             description="基于历史学习数据优化建议的优先级排序")
async def rank_suggestions(request: OptimizeSuggestionRankingRequest):
    """
    优化建议优先级排序

    - 基于历史效果调整预期影响
    - 根据成功率调整置信度
    - 重新排序返回最优建议列表
    """
    try:
        # 构建建议对象
        suggestions = []
        for sugg_data in request.suggestions:
            suggestion = OptimizationSuggestion(
                suggestion_id=sugg_data.get("suggestion_id", ""),
                title=sugg_data.get("title", ""),
                description=sugg_data.get("description", ""),
                suggestion_type=SuggestionType(sugg_data.get("suggestion_type", "seo_optimization")),
                priority=SuggestionPriority(sugg_data.get("priority", "medium")),
                effort=SuggestionEffort(sugg_data.get("effort", "medium")),
                expected_impact=sugg_data.get("expected_impact", 0.1),
                confidence=sugg_data.get("confidence", 0.7),
                action_steps=sugg_data.get("action_steps", []),
                related_metrics=sugg_data.get("related_metrics", []),
                estimated_timeline=sugg_data.get("estimated_timeline", ""),
                data_evidence=sugg_data.get("data_evidence", [])
            )
            suggestions.append(suggestion)

        # 调整优先级
        adjusted = learning_feedback_loop.adjust_suggestion_priority(
            suggestions=suggestions,
            context=request.context
        )

        # 返回排序后的建议
        return [suggestion.to_dict() for suggestion in adjusted]

    except Exception as e:
        logger.error(f"优化建议优先级失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 诊断入口 ==========

@router.get("/",
            response_model=Dict[str, Any],
            summary="AI 自主优化 API 入口",
            description="AI 自主优化能力概览和状态")
async def ai_optimization_root():
    """AI 自主优化 API 入口"""
    return {
        "service": "AI Traffic Booster - AI 自主优化服务",
        "version": "1.0.0",
        "capabilities": {
            "auto_ab_test": {
                "name": "自动 A/B 测试设计",
                "endpoint": "/ai-optimization/auto-ab-test/design",
                "description": "基于根因分析自动生成 A/B 测试方案"
            },
            "code_optimizer": {
                "name": "代码级优化建议",
                "endpoint": "/ai-optimization/code-optimizer/generate",
                "description": "生成可执行的代码改动建议"
            },
            "learning_loop": {
                "name": "闭环学习",
                "endpoint": "/ai-optimization/learning/insights",
                "description": "基于历史经验持续优化建议质量"
            }
        },
        "status": "running"
    }
