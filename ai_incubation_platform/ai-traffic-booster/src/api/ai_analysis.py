"""
AI 能力 API 路由

提供 AI 驱动的异常检测、根因分析、优化建议等能力
"""
from fastapi import APIRouter, Query, Body, Path
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field

from schemas.common import Response
from core.response import success
from core.exceptions import AnalyticsQueryFailedException

from ai.anomaly_detection import anomaly_detection_service, AnomalyDetectionResult
from ai.root_cause_analysis import root_cause_analysis_service, RootCauseAnalysisResult
from ai.recommendation_engine import recommendation_engine, OptimizationSuggestion
from ai.effect_validator import effect_validator, ExecutionStatus

router = APIRouter(prefix="/ai", tags=["AI 能力分析"])


# ==================== 请求/响应 Schema ====================

class AnomalyCheckRequest(BaseModel):
    """异常检测请求"""
    metric_name: str = Field(description="指标名称")
    current_value: float = Field(description="当前值")
    historical_values: List[float] = Field(description="历史值列表")
    domain: Optional[str] = Field(default=None, description="域名")


class AnomalyDetectionResponse(BaseModel):
    """异常检测响应"""
    is_anomaly: bool
    anomaly_type: Optional[str]
    severity: Optional[str]
    metric_name: str
    current_value: float
    expected_value: float
    deviation: float
    z_score: float
    confidence: float
    description: str


class RootCauseAnalysisRequest(BaseModel):
    """根因分析请求"""
    anomaly_data: Dict[str, Any] = Field(description="异常检测数据")
    domain: Optional[str] = Field(default=None, description="域名")
    check_date: Optional[date] = Field(default=None, description="检查日期")


class OptimizationSuggestionResponse(BaseModel):
    """优化建议响应"""
    suggestion_id: str
    title: str
    description: str
    suggestion_type: str
    priority: str
    effort: str
    expected_impact: float
    confidence: float
    action_steps: List[str]
    related_metrics: List[str]
    estimated_timeline: str


class ExecutionTrackRequest(BaseModel):
    """执行追踪请求"""
    suggestion_id: str = Field(description="建议 ID")
    user_id: Optional[str] = Field(default=None, description="用户 ID")


class EffectValidationRequest(BaseModel):
    """效果验证请求"""
    execution_id: str = Field(description="执行 ID")
    metric_name: str = Field(description="验证指标")
    baseline_data: List[float] = Field(description="基线数据")
    current_data: List[float] = Field(description="当前数据")


# ==================== 异常检测 API ====================

@router.post("/anomaly/detect", response_model=Response[AnomalyDetectionResponse])
async def detect_anomaly(request: AnomalyCheckRequest):
    """
    检测单个指标异常

    - 使用 Z-score 统计方法识别异常
    - 支持自定义阈值配置
    - 返回异常类型和严重度
    """
    result = anomaly_detection_service.detect_anomalies(
        metric_name=request.metric_name,
        current_value=request.current_value,
        historical_values=request.historical_values,
        context={"domain": request.domain}
    )

    return success(data=AnomalyDetectionResponse(
        is_anomaly=result.is_anomaly,
        anomaly_type=result.anomaly_type.value if result.anomaly_type else None,
        severity=result.severity.value if result.severity else None,
        metric_name=result.metric_name,
        current_value=result.current_value,
        expected_value=result.expected_value,
        deviation=result.deviation,
        z_score=result.z_score,
        confidence=result.confidence,
        description=result.description
    ))


@router.get("/anomaly/traffic", summary="检测流量异常")
async def detect_traffic_anomaly(
    domain: Optional[str] = Query(default=None, description="域名"),
    check_date: Optional[date] = Query(default=None, description="检查日期")
):
    """
    检测流量相关指标的异常

    - 自动检测访客数、页面浏览量、转化率、跳出率等指标
    - 基于过去 30 天数据建立基线
    - 返回所有检测到的异常
    """
    results = anomaly_detection_service.detect_traffic_anomaly(domain, check_date)

    return success(data={
        "anomalies": [r.to_dict() for r in results],
        "anomaly_count": len(results),
        "critical_count": sum(1 for r in results if r.severity and r.severity.value == "critical"),
        "warning_count": sum(1 for r in results if r.severity and r.severity.value == "warning")
    })


@router.get("/anomaly/keyword/{keyword}", summary="检测关键词排名异常")
async def detect_keyword_anomaly(
    keyword: str = Path(..., description="关键词"),
    current_position: int = Query(..., description="当前排名"),
    historical_positions: str = Query(..., description="历史排名列表（逗号分隔）")
):
    """检测特定关键词的排名异常"""
    try:
        positions = [int(p) for p in historical_positions.split(",")]
    except ValueError:
        raise AnalyticsQueryFailedException("历史排名格式错误，应为逗号分隔的整数")

    result = anomaly_detection_service.detect_keyword_ranking_anomaly(
        keyword=keyword,
        current_position=current_position,
        historical_positions=positions
    )

    return success(data=result.to_dict())


# ==================== 根因分析 API ====================

@router.post("/root-cause/analyze", summary="执行根因分析")
async def analyze_root_cause(request: RootCauseAnalysisRequest):
    """
    基于异常检测结果执行根因分析

    - 多维度归因分析（流量来源、关键词、页面性能等）
    - 根因置信度评估
    - 生成可执行的改进建议
    """
    # 从请求数据重建异常对象
    anomaly_data = request.anomaly_data

    # 创建临时的异常结果对象用于分析
    from ai.anomaly_detection import AnomalyDetectionResult, AnomalyType, AnomalySeverity

    anomaly = AnomalyDetectionResult(
        is_anomaly=anomaly_data.get("is_anomaly", True),
        anomaly_type=AnomalyType(anomaly_data["anomaly_type"]) if anomaly_data.get("anomaly_type") else AnomalyType.TRAFFIC_DROP,
        severity=AnomalySeverity(anomaly_data["severity"]) if anomaly_data.get("severity") else AnomalySeverity.WARNING,
        metric_name=anomaly_data.get("metric_name", "unknown"),
        current_value=anomaly_data.get("current_value", 0),
        expected_value=anomaly_data.get("expected_value", 0),
        deviation=anomaly_data.get("deviation", 0),
        z_score=anomaly_data.get("z_score", 0),
        confidence=anomaly_data.get("confidence", 0.5),
        description=anomaly_data.get("description", "未知异常"),
        detected_at=datetime.now()
    )

    result = root_cause_analysis_service.analyze(
        anomaly=anomaly,
        domain=request.domain,
        check_date=request.check_date
    )

    return success(data=result.to_dict())


@router.get("/root-cause/traffic-drop", summary="流量下跌根因分析")
async def analyze_traffic_drop(
    domain: Optional[str] = Query(default=None, description="域名"),
    check_date: Optional[date] = Query(default=None, description="检查日期")
):
    """
    专门针对流量下跌场景的根因分析

    - 自动检测流量异常
    - 执行多维度根因分析
    - 返回主要原因和改进建议
    """
    # 先检测异常
    anomalies = anomaly_detection_service.detect_traffic_anomaly(domain, check_date)

    if not anomalies:
        return success(data={"message": "未检测到流量异常", "root_causes": []})

    # 找出最严重的流量下跌异常
    traffic_drop = None
    for anomaly in anomalies:
        if anomaly.anomaly_type and anomaly.anomaly_type.value == "traffic_drop":
            if traffic_drop is None or (anomaly.severity and anomaly.severity.value == "critical"):
                traffic_drop = anomaly

    if not traffic_drop:
        return success(data={"message": "未检测到流量下跌异常", "anomalies": [a.to_dict() for a in anomalies]})

    # 执行根因分析
    result = root_cause_analysis_service.analyze(
        anomaly=traffic_drop,
        domain=domain,
        check_date=check_date or date.today()
    )

    return success(data=result.to_dict())


# ==================== 优化建议 API ====================

@router.post("/suggestions/generate", response_model=Response[List[OptimizationSuggestionResponse]])
async def generate_suggestions(request: RootCauseAnalysisRequest):
    """
    基于根因分析生成优化建议

    - 生成针对性、可执行的优化建议
    - 建议优先级排序
    - 预期效果评估
    """
    # 先执行根因分析
    from ai.anomaly_detection import AnomalyDetectionResult, AnomalyType, AnomalySeverity

    anomaly_data = request.anomaly_data
    anomaly = AnomalyDetectionResult(
        is_anomaly=anomaly_data.get("is_anomaly", True),
        anomaly_type=AnomalyType(anomaly_data["anomaly_type"]) if anomaly_data.get("anomaly_type") else AnomalyType.TRAFFIC_DROP,
        severity=AnomalySeverity(anomaly_data["severity"]) if anomaly_data.get("severity") else AnomalySeverity.WARNING,
        metric_name=anomaly_data.get("metric_name", "unknown"),
        current_value=anomaly_data.get("current_value", 0),
        expected_value=anomaly_data.get("expected_value", 0),
        deviation=anomaly_data.get("deviation", 0),
        z_score=anomaly_data.get("z_score", 0),
        confidence=anomaly_data.get("confidence", 0.5),
        description=anomaly_data.get("description", "未知异常"),
        detected_at=datetime.now()
    )

    analysis_result = root_cause_analysis_service.analyze(
        anomaly=anomaly,
        domain=request.domain,
        check_date=request.check_date
    )

    # 生成建议
    suggestions = recommendation_engine.generate_suggestions(analysis_result)

    return success(data=[
        OptimizationSuggestionResponse(
            suggestion_id=s.suggestion_id,
            title=s.title,
            description=s.description,
            suggestion_type=s.suggestion_type.value,
            priority=s.priority.value,
            effort=s.effort.value,
            expected_impact=s.expected_impact,
            confidence=s.confidence,
            action_steps=s.action_steps,
            related_metrics=s.related_metrics,
            estimated_timeline=s.estimated_timeline
        )
        for s in suggestions
    ])


@router.get("/suggestions/proactive", summary="获取主动优化建议")
async def get_proactive_suggestions(
    domain: Optional[str] = Query(default=None, description="域名")
):
    """
    获取主动优化建议（无异常时也提供改进建议）

    - 常规 SEO 优化建议
    - 内容改进建议
    - 流量获取建议
    """
    suggestions = recommendation_engine.generate_proactive_suggestions(domain)

    return success(data={
        "suggestions": [
            OptimizationSuggestionResponse(
                suggestion_id=s.suggestion_id,
                title=s.title,
                description=s.description,
                suggestion_type=s.suggestion_type.value,
                priority=s.priority.value,
                effort=s.effort.value,
                expected_impact=s.expected_impact,
                confidence=s.confidence,
                action_steps=s.action_steps,
                related_metrics=s.related_metrics,
                estimated_timeline=s.estimated_timeline
            )
            for s in suggestions
        ],
        "total": len(suggestions)
    })


# ==================== 执行追踪 API ====================

@router.post("/execution/track", summary="追踪建议执行")
async def track_execution(request: ExecutionTrackRequest):
    """
    开始追踪优化建议的执行

    - 创建执行记录
    - 标记执行状态
    """
    execution = effect_validator.track_execution(
        suggestion_id=request.suggestion_id,
        user_id=request.user_id
    )

    return success(data=execution.to_dict(), message="开始追踪执行")


@router.post("/execution/complete", summary="标记执行完成")
async def complete_execution(
    execution_id: str = Body(..., description="执行 ID"),
    notes: Optional[str] = Body(default=None, description="执行备注"),
    code_changes: Optional[str] = Body(default=None, description="代码改动")
):
    """标记建议执行为完成"""
    execution = effect_validator.complete_execution(
        execution_id=execution_id,
        notes=notes,
        code_changes=code_changes
    )

    if not execution:
        raise AnalyticsQueryFailedException("执行记录不存在")

    return success(data=execution.to_dict(), message="执行已完成")


@router.post("/effect/validate", summary="验证优化效果")
async def validate_effect(request: EffectValidationRequest):
    """
    验证优化建议的执行效果

    - 统计显著性检验
    - 效果评估
    - 置信度计算
    """
    validation = effect_validator.validate_effect(
        execution_id=request.execution_id,
        metric_name=request.metric_name,
        baseline_data=request.baseline_data,
        current_data=request.current_data
    )

    if not validation:
        raise AnalyticsQueryFailedException("验证失败")

    return success(data=validation.to_dict())


@router.get("/effect/insights", summary="获取学习洞察")
async def get_learning_insights():
    """
    获取学习洞察

    - 哪些类型的建议最有效
    - 建议成功率统计
    - 持续改进建议
    """
    insights = effect_validator.get_learning_insights()

    return success(data={
        "insights": insights,
        "total_types": len(insights)
    })


# ==================== AI 智能诊断 API ====================

@router.get("/diagnose/full", summary="完整智能诊断")
async def full_diagnosis(
    domain: Optional[str] = Query(default=None, description="域名"),
    check_date: Optional[date] = Query(default=None, description="检查日期")
):
    """
    执行完整的 AI 智能诊断

    - 异常检测
    - 根因分析
    - 优化建议生成
    """
    # 1. 异常检测
    anomalies = anomaly_detection_service.detect_traffic_anomaly(domain, check_date)

    # 2. 对每个异常执行根因分析
    root_causes_results = []
    all_suggestions = []

    for anomaly in anomalies:
        if anomaly.is_anomaly:
            analysis = root_cause_analysis_service.analyze(anomaly, domain, check_date)
            root_causes_results.append(analysis.to_dict())

            suggestions = recommendation_engine.generate_suggestions(analysis)
            all_suggestions.extend(suggestions)

    # 3. 去重和排序建议
    seen_ids = set()
    unique_suggestions = []
    for sugg in all_suggestions:
        if sugg.suggestion_id not in seen_ids:
            seen_ids.add(sugg.suggestion_id)
            unique_suggestions.append(sugg)

    # 4. 生成诊断报告
    return success(data={
        "diagnosis_time": datetime.now().isoformat(),
        "domain": domain,
        "anomalies_detected": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies],
        "root_causes_analysis": root_causes_results,
        "suggestions_count": len(unique_suggestions),
        "suggestions": [
            OptimizationSuggestionResponse(
                suggestion_id=s.suggestion_id,
                title=s.title,
                description=s.description,
                suggestion_type=s.suggestion_type.value,
                priority=s.priority.value,
                effort=s.effort.value,
                expected_impact=s.expected_impact,
                confidence=s.confidence,
                action_steps=s.action_steps,
                related_metrics=s.related_metrics,
                estimated_timeline=s.estimated_timeline
            )
            for s in unique_suggestions[:10]  # 只返回前 10 个建议
        ],
        "summary": f"检测到{len(anomalies)}个异常，生成{len(unique_suggestions)}条优化建议"
    })
