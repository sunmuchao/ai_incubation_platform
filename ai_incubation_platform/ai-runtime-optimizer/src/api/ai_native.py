"""
AI Native API - AI 原生对话式交互端点

This module provides AI Native API endpoints for:
- Natural language queries
- Autonomous optimization
- AI-driven diagnostics
- Generative UI data
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai-native"])


# Request/Response Models

class AIAskRequest(BaseModel):
    """Natural language query request."""
    question: str = Field(..., description="User's natural language question")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class AIAskResponse(BaseModel):
    """Natural language query response."""
    answer: str = Field(..., description="AI's natural language answer")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Supporting evidence")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Suggested actions")
    confidence: float = Field(..., description="Confidence score (0-1)")


class AIDiagnoseRequest(BaseModel):
    """Deep diagnosis request."""
    service: Optional[str] = Field(default=None, description="Service to diagnose")
    symptoms: Optional[List[str]] = Field(default=None, description="Observed symptoms")
    time_window: int = Field(default=300, description="Time window in seconds")


class AIDiagnoseResponse(BaseModel):
    """Deep diagnosis response."""
    diagnosis_id: str = Field(..., description="Unique diagnosis ID")
    root_cause: str = Field(..., description="Identified root cause")
    confidence: float = Field(..., description="Confidence score (0-1)")
    evidence_chain: List[Dict[str, Any]] = Field(default_factory=list, description="Evidence chain")
    impact_assessment: Dict[str, Any] = Field(default_factory=dict, description="Impact assessment")
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Recommended actions")
    natural_language_report: str = Field(..., description="Human-readable report")


class AIRemediateRequest(BaseModel):
    """Autonomous remediation request."""
    diagnosis_id: Optional[str] = Field(default=None, description="Associated diagnosis ID")
    action: Optional[Dict[str, Any]] = Field(default=None, description="Specific action to execute")
    auto_approve: bool = Field(default=False, description="Auto-approve high-confidence actions")


class AIRemediateResponse(BaseModel):
    """Autonomous remediation response."""
    success: bool = Field(..., description="Whether execution succeeded")
    action_name: str = Field(..., description="Executed action name")
    details: Dict[str, Any] = Field(default_factory=dict, description="Execution details")
    validation_result: Optional[Dict[str, Any]] = Field(default=None, description="Validation result")
    rollback_performed: bool = Field(default=False, description="Whether rollback was performed")


class AIOptimizeRequest(BaseModel):
    """Proactive optimization request."""
    service: Optional[str] = Field(default=None, description="Service to optimize")
    goals: Optional[List[str]] = Field(default=None, description="Optimization goals")
    auto_execute: bool = Field(default=False, description="Auto-execute high-confidence optimizations")


class AIOptimizeResponse(BaseModel):
    """Proactive optimization response."""
    success: bool = Field(..., description="Whether optimization succeeded")
    optimization_name: str = Field(..., description="Optimization identifier")
    recommendations: List[Dict[str, Any]] = Field(default_factory=list, description="Optimization recommendations")
    pr_url: Optional[str] = Field(default=None, description="Pull request URL if created")


class AIDashboardRequest(BaseModel):
    """Generative dashboard request."""
    service: Optional[str] = Field(default=None, description="Service filter")
    focus: Optional[str] = Field(default=None, description="Focus area (performance, errors, costs)")


class AIDashboardResponse(BaseModel):
    """Generative dashboard response."""
    status: str = Field(..., description="Overall system status")
    health_score: float = Field(..., description="Health score (0-100)")
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Active alerts")
    key_metrics: Dict[str, Any] = Field(default_factory=dict, description="Key metrics")
    ai_insights: List[str] = Field(default_factory=list, description="AI-generated insights")
    suggested_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Suggested actions")


# AI Agent accessor

def get_optimizer_agent():
    """Lazy load the optimizer agent."""
    from agents.optimizer_agent import get_optimizer_agent as _get_agent
    return _get_agent()


def get_diagnosis_class():
    """Lazy load the Diagnosis class."""
    from models.signals import Diagnosis
    return Diagnosis


# API Endpoints

@router.post("/ask", response_model=AIAskResponse)
async def ai_ask(request: AIAskRequest):
    """
    AI Native natural language Q&A.

    Ask questions about system status, performance, issues in natural language.
    AI will understand the intent and provide comprehensive answers with evidence.

    Example:
    ```
    POST /api/ai/ask
    {
        "question": "支付服务为什么延迟高？"
    }
    ```
    """
    logger.info(f"AI ask: {request.question}")

    try:
        agent = get_optimizer_agent()

        # Use DeerFlow workflow or local analysis to answer
        # This is a simplified implementation - in production, this would use LLM

        answer = f"正在分析您的问题：{request.question}"
        evidence = []
        actions = []
        confidence = 0.8

        # Analyze the question type and route to appropriate handler
        question_lower = request.question.lower()

        if "延迟" in request.question or "latency" in question_lower or "慢" in request.question:
            # Latency-related question
            answer = await _analyze_latency_question(request.question, request.context)
        elif "错误" in request.question or "error" in question_lower or "失败" in request.question:
            # Error-related question
            answer = await _analyze_error_question(request.question, request.context)
        elif "瓶颈" in request.question or "bottleneck" in question_lower:
            # Bottleneck question
            answer = await _analyze_bottleneck_question(request.question, request.context)
        else:
            # General question
            answer = await _analyze_general_question(request.question, request.context)

        return AIAskResponse(
            answer=answer,
            evidence=evidence,
            actions=actions,
            confidence=confidence
        )

    except Exception as e:
        logger.error(f"AI ask failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")


@router.post("/diagnose", response_model=AIDiagnoseResponse)
async def ai_diagnose(request: AIDiagnoseRequest):
    """
    AI-driven deep diagnosis.

    Multi-agent协同诊断，构建完整证据链，输出自然语言报告。
    """
    logger.info(f"AI diagnose: service={request.service}, symptoms={request.symptoms}")

    try:
        agent = get_optimizer_agent()

        # Perceive signals
        signals = await agent.perceive(service=request.service)

        if not signals:
            return AIDiagnoseResponse(
                diagnosis_id=str(datetime.now().timestamp()),
                root_cause="No issues detected",
                confidence=1.0,
                evidence_chain=[],
                impact_assessment={},
                recommended_actions=[],
                natural_language_report="系统运行正常，未检测到异常。"
            )

        # Diagnose
        diagnosis = await agent.diagnose(signals)

        return AIDiagnoseResponse(
            diagnosis_id=diagnosis.id,
            root_cause=diagnosis.root_cause,
            confidence=diagnosis.confidence,
            evidence_chain=diagnosis.evidence,
            impact_assessment=diagnosis.impact_assessment,
            recommended_actions=diagnosis.recommended_actions,
            natural_language_report=diagnosis.report
        )

    except Exception as e:
        logger.error(f"AI diagnose failed: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnosis failed: {str(e)}")


@router.post("/remediate", response_model=AIRemediateResponse)
async def ai_remediate(request: AIRemediateRequest):
    """
    Autonomous remediation execution.

    AI 自主执行修复操作，包含安全检查和效果验证。
    """
    logger.info(f"AI remediate: diagnosis_id={request.diagnosis_id}, auto_approve={request.auto_approve}")

    try:
        agent = get_optimizer_agent()

        # If no specific action provided, get from diagnosis
        if not request.action and request.diagnosis_id:
            # In production, would fetch diagnosis and extract recommended action
            raise HTTPException(status_code=400, detail="Either diagnosis_id or action must be provided")

        # Create a pseudo-diagnosis for execution
        Diagnosis = get_diagnosis_class()
        diagnosis = Diagnosis(
            id=request.diagnosis_id or "manual",
            root_cause="Manual remediation request",
            confidence=1.0 if request.auto_approve else 0.5,
            evidence=[],
            affected_services=[],
            impact_assessment={},
            report="Manual remediation",
            recommended_actions=[request.action] if request.action else []
        )

        result = await agent.remediate(diagnosis, auto_execute=request.auto_approve)

        return AIRemediateResponse(
            success=result.success,
            action_name=result.action_name,
            details=result.details,
            validation_result=result.validation_result,
            rollback_performed=result.rollback_performed
        )

    except Exception as e:
        logger.error(f"AI remediate failed: {e}")
        raise HTTPException(status_code=500, detail=f"Remediation failed: {str(e)}")


@router.post("/optimize", response_model=AIOptimizeResponse)
async def ai_optimize(request: AIOptimizeRequest):
    """
    Proactive optimization generation.

    AI 主动分析瓶颈，生成优化建议，自动提交 PR。
    """
    logger.info(f"AI optimize: service={request.service}, goals={request.goals}")

    try:
        agent = get_optimizer_agent()

        context = {
            "service": request.service,
            "goals": request.goals or [],
        }

        result = await agent.optimize(context=context)

        return AIOptimizeResponse(
            success=result.success,
            optimization_name=result.action_name,
            recommendations=result.details.get("recommendations", []),
            pr_url=result.details.get("pr_url")
        )

    except Exception as e:
        logger.error(f"AI optimize failed: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get("/dashboard", response_model=AIDashboardResponse)
async def ai_dashboard(
    service: Optional[str] = None,
    focus: Optional[str] = None
):
    """
    Generative dashboard - AI dynamically generates dashboard based on context.

    AI 根据当前状态动态生成个性化仪表板。
    """
    logger.info(f"AI dashboard: service={service}, focus={focus}")

    try:
        agent = get_optimizer_agent()

        # Get current system state
        signals = await agent.perceive(service=service)

        # Determine status based on signals
        critical_signals = [s for s in signals if getattr(s, "severity", "") == "critical"]
        high_signals = [s for s in signals if getattr(s, "severity", "") == "high"]

        if critical_signals:
            status = "critical"
            health_score = 20.0
        elif high_signals:
            status = "warning"
            health_score = 60.0
        else:
            status = "healthy"
            health_score = 95.0

        # Generate AI insights
        ai_insights = []
        if critical_signals:
            ai_insights.append(f"检测到 {len(critical_signals)} 个严重问题，需要立即处理")
        if high_signals:
            ai_insights.append(f"检测到 {len(high_signals)} 个高优先级问题")
        if not ai_insights:
            ai_insights.append("系统运行正常，所有指标在健康范围内")

        # Suggested actions
        suggested_actions = []
        if critical_signals:
            suggested_actions.append({
                "type": "immediate_action",
                "priority": "critical",
                "description": "立即处理严重告警",
                "action": "review_alerts"
            })

        return AIDashboardResponse(
            status=status,
            health_score=health_score,
            active_alerts=[
                {"id": s.id, "severity": s.severity, "type": s.type}
                for s in signals[:10]  # Limit to 10
            ],
            key_metrics={},
            ai_insights=ai_insights,
            suggested_actions=suggested_actions
        )

    except Exception as e:
        logger.error(f"AI dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")


@router.post("/autonomous-loop")
async def autonomous_loop(
    service: Optional[str] = None,
    auto_execute: bool = True
):
    """
    Full autonomous optimization loop.

    执行完整的 AI 自主运维循环：感知 → 诊断 → 修复 → 优化
    """
    logger.info(f"Autonomous loop: service={service}, auto_execute={auto_execute}")

    try:
        agent = get_optimizer_agent()
        result = await agent.analyze_and_optimize(service=service, auto_execute=auto_execute)
        return result

    except Exception as e:
        logger.error(f"Autonomous loop failed: {e}")
        raise HTTPException(status_code=500, detail=f"Autonomous loop failed: {str(e)}")


# Helper functions for question analysis

async def _analyze_latency_question(question: str, context: Optional[Dict] = None) -> str:
    """Analyze latency-related questions."""
    # In production, this would query actual metrics and use LLM
    return (
        "检测到延迟问题。可能的原因包括：\n"
        "1. 数据库查询缓慢 - 检查慢查询日志\n"
        "2. 外部 API 响应超时 - 检查依赖服务状态\n"
        "3. 资源竞争 - 检查 CPU/内存使用率\n"
        "4. 网络延迟 - 检查网络状况\n\n"
        "建议执行诊断以获取更精确的根因分析。"
    )


async def _analyze_error_question(question: str, context: Optional[Dict] = None) -> str:
    """Analyze error-related questions."""
    return (
        "检测到错误率异常。可能的原因包括：\n"
        "1. 代码异常 - 检查最近的变更\n"
        "2. 依赖服务故障 - 检查服务依赖状态\n"
        "3. 配置问题 - 检查配置变更\n"
        "4. 资源耗尽 - 检查内存/连接池\n\n"
        "建议查看错误日志和链路追踪以定位具体原因。"
    )


async def _analyze_bottleneck_question(question: str, context: Optional[Dict] = None) -> str:
    """Analyze bottleneck-related questions."""
    return (
        "性能瓶颈分析需要综合多维度数据：\n"
        "1. CPU 密集型 - 检查计算密集操作\n"
        "2. IO 密集型 - 检查磁盘/网络 IO\n"
        "3. 数据库瓶颈 - 检查慢查询和锁等待\n"
        "4. 内存瓶颈 - 检查 GC 频率和堆使用\n\n"
        "建议执行性能分析以获取详细的瓶颈定位。"
    )


async def _analyze_general_question(question: str, context: Optional[Dict] = None) -> str:
    """Analyze general questions."""
    return (
        f"收到问题：{question}\n\n"
        "系统当前状态概览：\n"
        "- 服务数量：正在获取...\n"
        "- 活跃告警：正在检查...\n"
        "- 健康评分：计算中...\n\n"
        "请使用更具体的问题或执行 /api/ai/dashboard 获取系统概览。"
    )


@router.get("/tools")
async def list_ai_tools():
    """List all available AI tools."""
    from tools.registry import list_tools
    return {"tools": list_tools()}


@router.post("/tools/{tool_name}/invoke")
async def invoke_ai_tool(tool_name: str, parameters: Dict[str, Any]):
    """Invoke an AI tool by name."""
    from tools.registry import invoke_tool

    try:
        result = await invoke_tool(tool_name, **parameters)
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Tool invocation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")
