"""
P6 阶段 API 路由：AI 信誉体系与行为追溯链

提供 AI Agent 信誉管理、行为追溯查询、治理报告等功能
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import db_manager
from sqlalchemy.ext.asyncio import AsyncSession
from services.agent_reputation_service import get_agent_reputation_service
from services.behavior_trace_service import get_behavior_trace_service
from services.governance_report_service import get_governance_report_service
from services.ai_moderator_service import get_ai_moderator_learning_service
from models.p6_entities import (
    AgentType, GovernanceReportType, GovernanceReportStatus, GovernanceReportVisibility,
    BehaviorTraceStatus, AgentReputationCreate, BehaviorTraceCreate, GovernanceReportCreate
)

router = APIRouter(prefix="/api/p6", tags=["p6-features"])


# ==================== AI 信誉体系 API ====================

@router.get("/agent-reputation")
async def list_agent_reputations(
    agent_type: Optional[str] = Query(None, description="Agent 类型"),
    min_reputation_score: Optional[float] = Query(None, ge=0, le=1, description="最小信誉分数"),
    is_active: Optional[bool] = Query(None, description="是否活跃"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    获取 AI Agent 信誉列表

    - **agent_type**: Agent 类型过滤 (moderator, assistant, recommender, creator)
    - **min_reputation_score**: 最小信誉分数
    - **is_active**: 活跃状态过滤
    - **limit**: 返回数量
    - **offset**: 偏移量
    """
    async with db_manager._session_factory() as session:
        service = get_agent_reputation_service(session)

        agent_type_enum = AgentType(agent_type) if agent_type else None
        agents = await service.list_agents(
            agent_type=agent_type_enum,
            min_reputation_score=min_reputation_score,
            is_active=is_active,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "agents": [
                {
                    "id": a.id,
                    "agent_id": a.agent_id,
                    "agent_name": a.agent_name,
                    "agent_type": a.agent_type,
                    "reputation_score": a.reputation_score,
                    "total_actions": a.total_actions,
                    "positive_actions": a.positive_actions,
                    "negative_actions": a.negative_actions,
                    "accuracy_score": a.accuracy_score,
                    "fairness_score": a.fairness_score,
                    "transparency_score": a.transparency_score,
                    "is_active": a.is_active,
                    "last_action_time": a.last_action_time.isoformat() if a.last_action_time else None
                }
                for a in agents
            ],
            "total": len(agents)
        }


@router.get("/agent-reputation/ranking")
async def get_agent_ranking(
    agent_type: Optional[str] = Query(None, description="Agent 类型"),
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    获取 AI Agent 信誉排行榜

    - **agent_type**: Agent 类型过滤
    - **limit**: 返回数量
    """
    async with db_manager._session_factory() as session:
        service = get_agent_reputation_service(session)

        agent_type_enum = AgentType(agent_type) if agent_type else None
        rankings = await service.get_ranking(
            agent_type=agent_type_enum,
            limit=limit
        )

        return {
            "success": True,
            "rankings": [
                {
                    "rank": r.rank,
                    "agent_id": r.agent_id,
                    "agent_name": r.agent_name,
                    "agent_type": r.agent_type,
                    "reputation_score": r.reputation_score,
                    "total_actions": r.total_actions,
                    "accuracy_score": r.accuracy_score
                }
                for r in rankings
            ]
        }


@router.get("/agent-reputation/{agent_id}")
async def get_agent_reputation(agent_id: str):
    """
    获取指定 AI Agent 的信誉信息

    - **agent_id**: Agent 唯一标识
    """
    async with db_manager._session_factory() as session:
        service = get_agent_reputation_service(session)

        summary = await service.get_reputation_summary(agent_id)
        if not summary:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")

        return {
            "success": True,
            "agent": {
                "agent_id": summary.agent_id,
                "agent_name": summary.agent_name,
                "agent_type": summary.agent_type,
                "reputation_score": summary.reputation_score,
                "reputation_level": summary.reputation_level,
                "total_actions": summary.total_actions,
                "positive_rate": summary.positive_rate,
                "accuracy_score": summary.accuracy_score,
                "fairness_score": summary.fairness_score,
                "transparency_score": summary.transparency_score
            }
        }


@router.post("/agent-reputation")
async def create_agent_reputation(request: AgentReputationCreate):
    """
    创建 AI Agent 信誉记录

    - **agent_id**: Agent 唯一标识
    - **agent_name**: Agent 名称
    - **agent_type**: Agent 类型
    - **model_provider**: 模型提供方（可选）
    - **model_name**: 模型名称（可选）
    - **operator_id**: 运营者 ID（可选）
    """
    async with db_manager._session_factory() as session:
        service = get_agent_reputation_service(session)

        reputation = await service.create_agent_reputation(
            agent_id=request.agent_id,
            agent_name=request.agent_name,
            agent_type=request.agent_type,
            model_provider=request.model_provider,
            model_name=request.model_name,
            operator_id=request.operator_id
        )

        return {
            "success": True,
            "agent": {
                "id": reputation.id,
                "agent_id": reputation.agent_id,
                "agent_name": reputation.agent_name,
                "agent_type": reputation.agent_type,
                "reputation_score": reputation.reputation_score,
                "created_at": reputation.created_at.isoformat()
            }
        }


@router.post("/agent-reputation/{agent_id}/feedback")
async def add_agent_feedback(
    agent_id: str,
    rating: int = Query(..., ge=1, le=5, description="评分：1-5 分"),
    is_positive: Optional[bool] = Query(None, description="是否为正面反馈"),
    response_time_ms: Optional[float] = Query(None, description="响应时间（毫秒）")
):
    """
    添加 AI Agent 用户反馈

    - **agent_id**: Agent 唯一标识
    - **rating**: 评分 1-5 分
    - **is_positive**: 是否为正面反馈（可选，根据 rating 自动判断）
    - **response_time_ms**: 响应时间（可选）
    """
    async with db_manager._session_factory() as session:
        service = get_agent_reputation_service(session)

        # 如果没有指定 is_positive，根据 rating 自动判断
        if is_positive is None:
            is_positive = rating >= 4

        # 计算分数变化
        score_delta = (rating / 5 - 0.5) * 0.1  # -0.05 到 +0.05

        await service.add_user_feedback(
            agent_id=agent_id,
            is_positive=is_positive,
            response_time_ms=response_time_ms
        )

        if score_delta != 0:
            await service.update_reputation_score(
                agent_id=agent_id,
                score_delta=score_delta,
                action_type="user_feedback",
                is_positive=is_positive
            )

        return {
            "success": True,
            "message": "反馈已添加"
        }


@router.get("/agent-reputation/stats/overview")
async def get_reputation_overview():
    """获取 AI 信誉体系概览统计"""
    async with db_manager._session_factory() as session:
        service = get_agent_reputation_service(session)
        stats = await service.get_statistics()

        return {
            "success": True,
            "stats": stats
        }


# ==================== 行为追溯链 API ====================

@router.get("/behavior-trace")
async def list_behavior_traces(
    agent_id: Optional[str] = Query(None, description="Agent ID"),
    action_type: Optional[str] = Query(None, description="行为类型"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    resource_id: Optional[str] = Query(None, description="资源 ID"),
    status: Optional[str] = Query(None, description="状态"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    查询行为追溯记录列表

    - **agent_id**: Agent ID 过滤
    - **action_type**: 行为类型过滤
    - **resource_type**: 资源类型过滤
    - **resource_id**: 资源 ID 过滤
    - **status**: 状态过滤 (completed, failed, timeout, in_progress)
    - **start_time**: 开始时间过滤
    - **end_time**: 结束时间过滤
    - **limit**: 返回数量
    - **offset**: 偏移量
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        status_enum = BehaviorTraceStatus(status) if status else None
        traces = await service.list_traces(
            agent_id=agent_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status_enum,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "traces": [
                {
                    "id": t.id,
                    "trace_id": t.trace_id,
                    "parent_trace_id": t.parent_trace_id,
                    "agent_id": t.agent_id,
                    "agent_name": t.agent_name,
                    "action_type": t.action_type,
                    "resource_type": t.resource_type,
                    "resource_id": t.resource_id,
                    "status": t.status,
                    "confidence_score": t.confidence_score,
                    "duration_ms": t.duration_ms,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in traces
            ],
            "total": len(traces)
        }


@router.get("/behavior-trace/{trace_id}")
async def get_behavior_trace(trace_id: str):
    """
    获取行为追溯记录详情

    - **trace_id**: 追溯记录 ID
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        trace = await service.get_trace(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail=f"追溯记录 {trace_id} 不存在")

        return {
            "success": True,
            "trace": {
                "id": trace.id,
                "trace_id": trace.trace_id,
                "parent_trace_id": trace.parent_trace_id,
                "agent_id": trace.agent_id,
                "agent_name": trace.agent_name,
                "model_provider": trace.model_provider,
                "model_name": trace.model_name,
                "model_version": trace.model_version,
                "operator_id": trace.operator_id,
                "action_type": trace.action_type,
                "action_description": trace.action_description,
                "resource_type": trace.resource_type,
                "resource_id": trace.resource_id,
                "input_data": trace.input_data,
                "decision_process": trace.decision_process,
                "output_result": trace.output_result,
                "rules_applied": trace.rules_applied or [],
                "confidence_score": trace.confidence_score,
                "risk_assessment": trace.risk_assessment,
                "started_at": trace.started_at.isoformat() if trace.started_at else None,
                "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
                "duration_ms": trace.duration_ms,
                "status": trace.status,
                "error_message": trace.error_message,
                "user_feedback": trace.user_feedback,
                "review_result": trace.review_result
            }
        }


@router.get("/behavior-trace/chain/{root_trace_id}")
async def get_trace_chain(root_trace_id: str):
    """
    获取追溯链（包含所有子追溯）

    - **root_trace_id**: 根追溯 ID
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        chain = await service.get_trace_chain(root_trace_id)
        if not chain:
            raise HTTPException(status_code=404, detail=f"追溯链 {root_trace_id} 不存在")

        return {
            "success": True,
            "chain": {
                "chain_id": chain.chain_id,
                "root_trace": {
                    "trace_id": chain.root_trace.trace_id,
                    "action_type": chain.root_trace.action_type,
                    "agent_name": chain.root_trace.agent_name
                },
                "child_traces": [
                    {
                        "trace_id": t.trace_id,
                        "action_type": t.action_type,
                        "agent_name": t.agent_name
                    }
                    for t in chain.child_traces
                ],
                "total_duration_ms": chain.total_duration_ms,
                "decision_path": chain.decision_path
            }
        }


@router.post("/behavior-trace")
async def create_behavior_trace(request: BehaviorTraceCreate):
    """
    创建行为追溯记录

    - **agent_id**: Agent 标识
    - **agent_name**: Agent 名称
    - **action_type**: 行为类型
    - **input_data**: 输入数据
    - **output_result**: 输出结果
    - **action_description**: 行为描述（可选）
    - **resource_type**: 资源类型（可选）
    - **resource_id**: 资源 ID（可选）
    - **model_provider**: 模型提供方（可选）
    - **model_name**: 模型名称（可选）
    - **operator_id**: 运营者 ID（可选）
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        trace = await service.create_trace(
            agent_id=request.agent_id,
            agent_name=request.agent_name,
            action_type=request.action_type,
            input_data=request.input_data,
            output_result=request.output_result,
            action_description=request.action_description,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            model_provider=request.model_provider,
            model_name=request.model_name,
            operator_id=request.operator_id
        )

        return {
            "success": True,
            "trace_id": trace.id,
            "message": "追溯记录已创建"
        }


@router.post("/behavior-trace/{trace_id}/complete")
async def complete_behavior_trace(
    trace_id: str,
    output_result: Optional[Dict[str, Any]] = Body(None, description="输出结果"),
    decision_process: Optional[Dict[str, Any]] = Body(None, description="决策过程"),
    rules_applied: Optional[List[str]] = Body(None, description="应用的规则"),
    confidence_score: Optional[float] = Body(None, ge=0, le=1, description="置信度"),
    error_message: Optional[str] = Body(None, description="错误信息")
):
    """
    完成行为追溯记录

    - **trace_id**: 追溯记录 ID
    - **output_result**: 输出结果（可选）
    - **decision_process**: 决策过程详情（可选）
    - **rules_applied**: 应用的规则列表（可选）
    - **confidence_score**: 置信度分数（可选）
    - **error_message**: 错误信息（可选）
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        trace = await service.complete_trace(
            trace_id=trace_id,
            output_result=output_result,
            decision_process=decision_process,
            rules_applied=rules_applied,
            confidence_score=confidence_score,
            error_message=error_message
        )

        return {
            "success": True,
            "status": trace.status,
            "message": "追溯记录已完成"
        }


@router.post("/behavior-trace/{trace_id}/feedback")
async def add_trace_feedback(
    trace_id: str,
    feedback: Dict[str, Any]
):
    """
    添加行为追溯用户反馈

    - **trace_id**: 追溯记录 ID
    - **feedback**: 反馈数据，包含 rating(1-5), comment 等
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        await service.add_feedback(trace_id, feedback)

        return {
            "success": True,
            "message": "反馈已添加"
        }


@router.get("/behavior-trace/{trace_id}/transparency")
async def get_trace_transparency(trace_id: str):
    """
    获取追溯记录透明度报告

    - **trace_id**: 追溯记录 ID
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        report = await service.get_trace_transparency_report(trace_id)

        return {
            "success": True,
            "transparency_report": report
        }


@router.get("/behavior-trace/stats/overview")
async def get_trace_overview(
    agent_id: Optional[str] = Query(None, description="Agent ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间")
):
    """获取行为追溯概览统计"""
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        stats = await service.get_statistics(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time
        )

        return {
            "success": True,
            "stats": stats
        }


# ==================== 治理报告 API ====================

@router.get("/governance-report")
async def list_governance_reports(
    report_type: Optional[str] = Query(None, description="报告类型"),
    status: Optional[str] = Query(None, description="状态"),
    visibility: Optional[str] = Query(None, description="可见性"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    查询治理报告列表

    - **report_type**: 报告类型 (daily, weekly, monthly, special)
    - **status**: 状态 (draft, published, archived)
    - **visibility**: 可见性 (admin, moderator, public)
    - **start_time**: 开始时间过滤
    - **end_time**: 结束时间过滤
    - **limit**: 返回数量
    - **offset**: 偏移量
    """
    async with db_manager._session_factory() as session:
        service = get_governance_report_service(session)

        report_type_enum = GovernanceReportType(report_type) if report_type else None
        status_enum = GovernanceReportStatus(status) if status else None
        visibility_enum = GovernanceReportVisibility(visibility) if visibility else None

        reports = await service.list_reports(
            report_type=report_type_enum,
            status=status_enum,
            visibility=visibility_enum,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "reports": [
                {
                    "id": r.id,
                    "report_type": r.report_type,
                    "report_title": r.report_title,
                    "start_time": r.start_time.isoformat(),
                    "end_time": r.end_time.isoformat(),
                    "generated_at": r.generated_at.isoformat(),
                    "generated_by": r.generated_by,
                    "status": r.status,
                    "visibility": r.visibility,
                    "summary": r.summary
                }
                for r in reports
            ],
            "total": len(reports)
        }


@router.get("/governance-report/{report_id}")
async def get_governance_report(report_id: str):
    """
    获取治理报告详情

    - **report_id**: 报告 ID
    """
    async with db_manager._session_factory() as session:
        service = get_governance_report_service(session)

        report = await service.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"治理报告 {report_id} 不存在")

        return {
            "success": True,
            "report": {
                "id": report.id,
                "report_type": report.report_type,
                "report_title": report.report_title,
                "start_time": report.start_time.isoformat(),
                "end_time": report.end_time.isoformat(),
                "generated_at": report.generated_at.isoformat(),
                "generated_by": report.generated_by,
                "summary": report.summary,
                "content": report.content,
                "metrics": report.metrics,
                "status": report.status,
                "visibility": report.visibility
            }
        }


@router.post("/governance-report/daily")
async def generate_daily_report(
    date: Optional[str] = Query(None, description="报告日期 YYYY-MM-DD"),
    agent_id: str = Body("ai_moderator", description="AI Agent ID")
):
    """
    生成每日治理报告

    - **date**: 报告日期（默认昨天）
    - **agent_id**: AI Agent ID
    """
    async with db_manager._session_factory() as session:
        service = get_governance_report_service(session)

        date_obj = None
        if date:
            date_obj = datetime.strptime(date, "%Y-%m-%d")

        report = await service.generate_daily_report(
            date=date_obj,
            agent_id=agent_id
        )

        return {
            "success": True,
            "report_id": report.id,
            "report_title": report.report_title
        }


@router.post("/governance-report/weekly")
async def generate_weekly_report(
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    agent_id: str = Body("ai_moderator", description="AI Agent ID")
):
    """
    生成每周治理报告

    - **end_date**: 结束日期（默认今天）
    - **agent_id**: AI Agent ID
    """
    async with db_manager._session_factory() as session:
        service = get_governance_report_service(session)

        end_date_obj = None
        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

        report = await service.generate_weekly_report(
            end_date=end_date_obj,
            agent_id=agent_id
        )

        return {
            "success": True,
            "report_id": report.id,
            "report_title": report.report_title
        }


@router.post("/governance-report/monthly")
async def generate_monthly_report(
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    agent_id: str = Body("ai_moderator", description="AI Agent ID")
):
    """
    生成每月治理报告

    - **end_date**: 结束日期（默认今天）
    - **agent_id**: AI Agent ID
    """
    async with db_manager._session_factory() as session:
        service = get_governance_report_service(session)

        end_date_obj = None
        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

        report = await service.generate_monthly_report(
            end_date=end_date_obj,
            agent_id=agent_id
        )

        return {
            "success": True,
            "report_id": report.id,
            "report_title": report.report_title
        }


@router.post("/governance-report/special")
async def generate_special_report(
    title: str = Body(..., description="报告标题"),
    description: str = Body(..., description="事件描述"),
    start_time: str = Body(..., description="事件开始时间 YYYY-MM-DD"),
    end_time: str = Body(..., description="事件结束时间 YYYY-MM-DD"),
    agent_id: str = Body("ai_moderator", description="AI Agent ID")
):
    """
    生成特殊事件治理报告

    - **title**: 报告标题
    - **description**: 事件描述
    - **start_time**: 事件开始时间 YYYY-MM-DD
    - **end_time**: 事件结束时间 YYYY-MM-DD
    - **agent_id**: AI Agent ID
    """
    async with db_manager._session_factory() as session:
        service = get_governance_report_service(session)

        start_time_obj = datetime.strptime(start_time, "%Y-%m-%d")
        end_time_obj = datetime.strptime(end_time, "%Y-%m-%d")

        report = await service.generate_special_report(
            title=title,
            description=description,
            start_time=start_time_obj,
            end_time=end_time_obj,
            agent_id=agent_id
        )

        return {
            "success": True,
            "report_id": report.id,
            "report_title": report.report_title
        }


@router.post("/governance-report/{report_id}/publish")
async def publish_governance_report(
    report_id: str,
    visibility: str = Body("moderator", description="可见性：admin, moderator, public")
):
    """
    发布治理报告

    - **report_id**: 报告 ID
    - **visibility**: 可见性
    """
    async with db_manager._session_factory() as session:
        service = get_governance_report_service(session)

        visibility_enum = GovernanceReportVisibility(visibility)
        report = await service.publish_report(report_id, visibility_enum)

        return {
            "success": True,
            "report_id": report.id,
            "status": report.status,
            "visibility": report.visibility
        }


@router.get("/transparency-report/{agent_id}")
async def get_transparency_report(agent_id: str):
    """
    获取 AI Agent 透明度报告

    - **agent_id**: Agent 唯一标识
    """
    async with db_manager._session_factory() as session:
        service = get_governance_report_service(session)

        report = await service.get_transparency_report(agent_id)

        return {
            "success": True,
            "transparency_report": report
        }


# ==================== P7 可视化数据 API ====================

@router.get("/behavior-trace/{trace_id}/visualization")
async def get_trace_visualization(trace_id: str):
    """
    获取行为追溯链可视化数据

    - **trace_id**: 追溯记录 ID

    返回可用于图形化展示追溯链的节点和边数据
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        try:
            data = await service.get_visualization_data(trace_id)
            return {
                "success": True,
                "data": data
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.get("/agent-reputation/{agent_id}/timeline")
async def get_agent_timeline(
    agent_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(default=50, ge=1, le=200)
):
    """
    获取 AI Agent 行为追溯时间线数据

    - **agent_id**: Agent 唯一标识
    - **start_time**: 开始时间过滤
    - **end_time**: 结束时间过滤
    - **limit**: 返回数量
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        data = await service.get_agent_trace_timeline(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        return {
            "success": True,
            "data": data
        }


@router.get("/behavior-trace/stats/graph")
async def get_trace_graph_stats(
    agent_id: Optional[str] = Query(None, description="Agent ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间")
):
    """
    获取行为追溯图谱统计信息

    - **agent_id**: Agent ID 过滤
    - **start_time**: 开始时间
    - **end_time**: 结束时间

    返回行为类型分布、Agent 分布、状态分布等图谱数据
    """
    async with db_manager._session_factory() as session:
        service = get_behavior_trace_service(session)

        data = await service.get_trace_graph_stats(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time
        )

        return {
            "success": True,
            "data": data
        }


# ==================== P7 AI 版主增强 API ====================

@router.post("/ai-moderator/learn")
async def ai_moderator_learn(
    limit: int = Query(default=100, ge=10, le=1000, description="分析的决策数量")
):
    """
    AI 版主从人工审核决策中学习

    - **limit**: 分析的决策数量（10-1000）

    AI 版主分析历史人工审核决策，学习人类的判断标准，并提供阈值调整建议
    """
    async with db_manager._session_factory() as session:
        service = get_ai_moderator_learning_service(session)

        result = await service.learn_from_human_decisions(limit=limit)

        return {
            "success": True,
            "data": result
        }


@router.get("/ai-moderator/stats")
async def get_ai_moderator_stats():
    """
    获取 AI 版主统计信息

    返回 AI 版主的处理数量、准确率等统计信息
    """
    from services.ai_moderator_service import get_ai_moderator_service

    async with db_manager._session_factory() as session:
        service = get_ai_moderator_service(session)

        stats = await service.get_auto_moderation_stats()

        return {
            "success": True,
            "data": stats
        }


@router.post("/ai-moderator/batch-process")
async def ai_moderator_batch_process(
    batch_size: int = Query(default=50, ge=1, le=500, description="每批处理的举报数量"),
    dry_run: bool = Query(default=False, description="是否为演习模式（不实际处理）")
):
    """
    AI 版主批量处理举报

    - **batch_size**: 每批处理的举报数量（1-500）
    - **dry_run**: 是否为演习模式（只分析不实际处理）

    批量自动处理待处理举报，根据违规概率自动确认或忽略
    """
    from services.ai_moderator_service import get_ai_moderator_service

    async with db_manager._session_factory() as session:
        service = get_ai_moderator_service(session)

        # 演习模式只分析不处理
        if dry_run:
            result = await service.auto_process_reports(batch_size=batch_size)
            # 演习模式回滚数据库操作
            await session.rollback()
            return {
                "success": True,
                "dry_run": True,
                "data": result
            }

        result = await service.auto_process_reports(batch_size=batch_size)

        return {
            "success": True,
            "dry_run": False,
            "data": result
        }
