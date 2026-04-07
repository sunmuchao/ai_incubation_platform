"""
P6 自主修复引擎 - REST API

提供自主修复引擎的 REST API 接口
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from core.remediation_engine import (
    get_orchestrator,
    get_script_library,
    RemediationScriptLibrary,
    ExecutionSandbox,
    RemediationOrchestrator,
)
from models.remediation import (
    RemediationScript,
    RemediationExecution,
    ExecutionStatus,
    RiskLevel,
    RemediationCategory,
    AutoRemediationRule,
    RemediationStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/remediation", tags=["remediation"])


# ============================================================================
# 请求/响应模型
# ============================================================================

class ScriptListResponse(BaseModel):
    """脚本列表响应"""
    scripts: List[RemediationScript]
    total: int


class ScriptDetailResponse(BaseModel):
    """脚本详情响应"""
    script: RemediationScript


class ExecuteRequest(BaseModel):
    """执行请求"""
    script_id: str = Field(..., description="脚本 ID")
    target_service: str = Field(..., description="目标服务")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行参数")
    require_approval: bool = Field(default=True, description="是否需要审批")
    target_type: str = Field(default="service", description="目标类型")


class ExecuteResponse(BaseModel):
    """执行响应"""
    execution_id: str
    status: str
    script_name: str
    target_service: str
    created_at: datetime
    estimated_duration_seconds: int
    risk_level: str
    rollback_available: bool


class ApproveRequest(BaseModel):
    """审批请求"""
    approver: str = Field(..., description="审批人")
    reason: Optional[str] = Field(default=None, description="审批意见")


class RollbackRequest(BaseModel):
    """回滚请求"""
    operator: str = Field(..., description="操作人")
    reason: Optional[str] = Field(default=None, description="回滚原因")


class AutoRuleRequest(BaseModel):
    """自动规则创建请求"""
    name: str = Field(..., description="规则名称")
    description: str = Field(default="", description="规则描述")
    trigger_condition: Dict[str, Any] = Field(..., description="触发条件")
    script_id: str = Field(..., description="脚本 ID")
    script_parameters: Dict[str, Any] = Field(default_factory=dict, description="脚本参数")
    cooldown_minutes: int = Field(default=60, description="冷却时间")
    max_executions_per_day: int = Field(default=3, description="每日最大执行次数")
    require_approval: bool = Field(default=True, description="是否需要审批")


class AutoRuleListResponse(BaseModel):
    """自动规则列表响应"""
    rules: List[AutoRemediationRule]
    total: int


class ExecutionListResponse(BaseModel):
    """执行记录列表响应"""
    executions: List[RemediationExecution]
    total: int


class StatsResponse(BaseModel):
    """统计响应"""
    stats: RemediationStats


# ============================================================================
# 脚本管理 API
# ============================================================================

@router.get("/scripts", response_model=ScriptListResponse)
async def list_scripts(
    category: Optional[RemediationCategory] = Query(None, description="脚本分类"),
    enabled_only: bool = Query(True, description="是否只返回启用的脚本")
):
    """
    获取所有可用的修复脚本

    - **category**: 按分类过滤
    - **enabled_only**: 是否只返回启用的脚本
    """
    library = get_script_library()
    scripts = library.list_scripts(category=category, enabled_only=enabled_only)

    return {
        "scripts": scripts,
        "total": len(scripts)
    }


@router.get("/scripts/{script_id}", response_model=ScriptDetailResponse)
async def get_script(script_id: str):
    """
    获取脚本详情

    - **script_id**: 脚本 ID
    """
    library = get_script_library()
    script = library.get_script(script_id)

    if not script:
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")

    return {"script": script}


@router.post("/scripts", status_code=201)
async def create_script(script: RemediationScript):
    """
    添加自定义修复脚本

    需要管理员权限
    """
    library = get_script_library()

    # 验证脚本内容
    if not script.script_content:
        raise HTTPException(status_code=400, detail="Script content is required")

    # 添加脚本
    library.add_script(script)

    return {
        "message": "Script created successfully",
        "script_id": script.script_id
    }


@router.delete("/scripts/{script_id}")
async def delete_script(script_id: str):
    """
    删除脚本

    需要管理员权限
    """
    library = get_script_library()

    if not library.delete_script(script_id):
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")

    return {"message": f"Script {script_id} deleted successfully"}


@router.put("/scripts/{script_id}/enable")
async def enable_script(script_id: str, enabled: bool = Query(..., description="是否启用")):
    """启用/禁用脚本"""
    library = get_script_library()

    if not library.enable_script(script_id, enabled):
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")

    status = "enabled" if enabled else "disabled"
    return {"message": f"Script {script_id} {status}"}


# ============================================================================
# 执行 API
# ============================================================================

@router.post("/execute", response_model=ExecuteResponse, status_code=201)
async def execute_remediation(request: ExecuteRequest):
    """
    手动触发修复

    执行指定的修复脚本
    """
    orchestrator = get_orchestrator()

    # 验证脚本存在
    library = get_script_library()
    script = library.get_script(request.script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script not found: {request.script_id}")

    # 创建执行记录
    try:
        execution = orchestrator.create_execution(
            script_id=request.script_id,
            target_service=request.target_service,
            parameters=request.parameters,
            require_approval=request.require_approval,
            target_type=request.target_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 如果不需要审批，直接执行
    if not request.require_approval:
        import asyncio
        asyncio.create_task(orchestrator.execute(execution.execution_id))

    return ExecuteResponse(
        execution_id=execution.execution_id,
        status=execution.status.value,
        script_name=execution.script_name,
        target_service=execution.target_service,
        created_at=execution.created_at,
        estimated_duration_seconds=execution.estimated_duration_seconds,
        risk_level=execution.risk_level.value,
        rollback_available=execution.rollback_available,
    )


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """
    获取执行状态

    返回执行的详细信息，包括进度、日志、结果等
    """
    orchestrator = get_orchestrator()
    execution = orchestrator.get_execution(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    return execution


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    status: Optional[ExecutionStatus] = Query(None, description="执行状态"),
    target_service: Optional[str] = Query(None, description="目标服务"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制")
):
    """
    列出执行记录

    - **status**: 按状态过滤
    - **target_service**: 按目标服务过滤
    - **limit**: 返回数量限制
    """
    orchestrator = get_orchestrator()
    executions = orchestrator.list_executions(
        status=status,
        target_service=target_service,
        limit=limit,
    )

    return {
        "executions": executions,
        "total": len(executions)
    }


@router.post("/execute/{execution_id}/approve")
async def approve_execution(execution_id: str, request: ApproveRequest):
    """
    审批修复执行

    - **approver**: 审批人
    - **reason**: 审批意见
    """
    orchestrator = get_orchestrator()

    success = await orchestrator.approve_execution(execution_id, request.approver)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve execution")

    # 审批通过后自动执行
    import asyncio
    asyncio.create_task(orchestrator.execute(execution_id))

    return {"message": "Execution approved and started"}


@router.post("/execute/{execution_id}/reject")
async def reject_execution(execution_id: str, request: ApproveRequest):
    """
    拒绝修复执行

    - **approver**: 拒绝人
    - **reason**: 拒绝原因
    """
    orchestrator = get_orchestrator()

    success = await orchestrator.reject_execution(
        execution_id,
        request.approver,
        request.reason or ""
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reject execution")

    return {"message": "Execution rejected"}


@router.post("/executions/{execution_id}/rollback")
async def rollback_execution(execution_id: str, request: RollbackRequest):
    """
    执行回滚

    仅当执行成功且有回滚脚本时可回滚
    """
    orchestrator = get_orchestrator()

    execution = orchestrator.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    if execution.status != ExecutionStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot rollback execution with status: {execution.status.value}"
        )

    success = await orchestrator.rollback_execution(execution_id)
    if not success:
        raise HTTPException(status_code=400, detail="Rollback failed")

    return {"message": "Execution rolled back successfully"}


# ============================================================================
# 自动修复规则 API
# ============================================================================

@router.post("/auto-rules", status_code=201)
async def create_auto_rule(request: AutoRuleRequest):
    """
    创建自动修复规则

    配置自动触发的修复规则
    """
    orchestrator = get_orchestrator()

    # 验证脚本存在
    library = get_script_library()
    script = library.get_script(request.script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script not found: {request.script_id}")

    # 生成规则 ID
    rule_id = f"rule_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(orchestrator._auto_rules) + 1:03d}"

    rule = AutoRemediationRule(
        rule_id=rule_id,
        name=request.name,
        description=request.description,
        trigger_condition=request.trigger_condition,
        script_id=request.script_id,
        script_parameters=request.script_parameters,
        cooldown_minutes=request.cooldown_minutes,
        max_executions_per_day=request.max_executions_per_day,
        require_approval=request.require_approval,
        enabled=False,  # 默认禁用，需要手动启用
    )

    orchestrator.create_auto_rule(rule)

    return {
        "message": "Auto rule created successfully",
        "rule_id": rule_id
    }


@router.get("/auto-rules", response_model=AutoRuleListResponse)
async def list_auto_rules(enabled_only: bool = Query(True, description="是否只返回启用的规则")):
    """
    获取自动修复规则列表

    - **enabled_only**: 是否只返回启用的规则
    """
    orchestrator = get_orchestrator()
    rules = orchestrator.list_auto_rules(enabled_only=enabled_only)

    return {
        "rules": rules,
        "total": len(rules)
    }


@router.get("/auto-rules/{rule_id}")
async def get_auto_rule(rule_id: str):
    """获取自动修复规则详情"""
    orchestrator = get_orchestrator()
    rule = orchestrator.get_auto_rule(rule_id)

    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    return rule


@router.delete("/auto-rules/{rule_id}")
async def delete_auto_rule(rule_id: str):
    """删除自动修复规则"""
    orchestrator = get_orchestrator()

    if not orchestrator.delete_auto_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    return {"message": f"Rule {rule_id} deleted successfully"}


@router.put("/auto-rules/{rule_id}/enable")
async def enable_auto_rule(rule_id: str, enabled: bool = Query(..., description="是否启用")):
    """启用/禁用自动修复规则"""
    orchestrator = get_orchestrator()

    if not orchestrator.enable_auto_rule(rule_id, enabled):
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

    status = "enabled" if enabled else "disabled"
    return {"message": f"Rule {rule_id} {status}"}


# ============================================================================
# 统计 API
# ============================================================================

@router.get("/stats")
async def get_stats():
    """
    获取修复统计

    返回执行次数、成功率、平均耗时等统计信息
    """
    orchestrator = get_orchestrator()
    stats_data = orchestrator.get_execution_stats()

    stats = RemediationStats(
        total_executions=stats_data['total_executions'],
        successful_executions=stats_data['successful_executions'],
        failed_executions=stats_data['failed_executions'],
        rolled_back_executions=stats_data['rolled_back_executions'],
        success_rate=stats_data['success_rate'],
        avg_duration_seconds=stats_data['avg_duration_seconds'],
        total_executions_today=stats_data['total_executions_today'],
        scripts_count=stats_data['scripts_count'],
        auto_rules_count=stats_data['auto_rules_count'],
    )

    return {"stats": stats}


# ============================================================================
# 健康检查
# ============================================================================

@router.get("/health")
async def health_check():
    """健康检查"""
    library = get_script_library()

    return {
        "status": "healthy",
        "scripts_loaded": library.get_script_count(),
    }


# ============================================================================
# v1.1 新增：影响分析和案例管理 API
# ============================================================================

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from core.remediation_engine import (
    get_impact_analyzer,
    get_case_library,
    ImpactAnalyzer,
    CaseLibrary,
)
from models.remediation import (
    ImpactAnalysis,
    RemediationCase,
)


class ImpactAnalysisRequest(BaseModel):
    """影响分析请求"""
    script_id: str = Field(..., description="脚本 ID")
    target_service: str = Field(..., description="目标服务")
    action_type: str = Field(default="remediation", description="操作类型")


class ImpactAnalysisResponse(BaseModel):
    """影响分析响应"""
    impact_analysis: ImpactAnalysis
    script_name: str
    risk_level: str


class CreateCaseRequest(BaseModel):
    """创建案例请求"""
    execution_id: str = Field(..., description="执行 ID")
    problem_description: Optional[str] = Field(default="", description="问题描述")
    root_cause: Optional[str] = Field(default="", description="根本原因")
    lessons_learned: Optional[str] = Field(default="", description="经验教训")
    created_by: str = Field(default="system", description="创建人")


class CreateCaseResponse(BaseModel):
    """创建案例响应"""
    case_id: str
    execution_id: str
    outcome: str
    effectiveness_score: Optional[float]


class CaseListResponse(BaseModel):
    """案例列表响应"""
    cases: List[RemediationCase]
    total: int


class SimilarCaseRequest(BaseModel):
    """相似案例查询请求"""
    script_id: str = Field(..., description="脚本 ID")
    problem_keywords: Optional[List[str]] = Field(default=None, description="问题关键词")


class SimilarCaseResponse(BaseModel):
    """相似案例响应"""
    cases: List[RemediationCase]
    total: int


class CaseStatsResponse(BaseModel):
    """案例统计响应"""
    total_cases: int
    successful_cases: int
    success_rate: float
    average_effectiveness_score: float


class SetDependenciesRequest(BaseModel):
    """设置服务依赖请求"""
    dependencies: Dict[str, List[str]] = Field(..., description="服务依赖关系 {service_id: [dependency_ids]}")


@router.post("/v1.1/analyze-impact", response_model=ImpactAnalysisResponse)
async def analyze_impact(request: ImpactAnalysisRequest):
    """
    分析修复操作的影响

    在执行修复前，分析该操作可能带来的影响：
    - 受影响的服务列表
    - 预估停机时间
    - 回滚复杂度
    - 综合风险评估

    这对于高风险操作尤其重要，可帮助决策是否执行修复。
    """
    analyzer = get_impact_analyzer()
    library = get_script_library()

    # 获取脚本
    script = library.get_script(request.script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script not found: {request.script_id}")

    # 执行影响分析
    impact = analyzer.analyze_impact(
        target_service=request.target_service,
        script=script,
        action_type=request.action_type
    )

    return ImpactAnalysisResponse(
        impact_analysis=impact,
        script_name=script.name,
        risk_level=script.risk_level.value
    )


@router.post("/v1.1/cases/create", response_model=CreateCaseResponse)
async def create_case(request: CreateCaseRequest):
    """
    从执行记录创建案例

    将成功的修复或失败的尝试记录为案例，用于：
    - 经验积累
    - 未来类似问题的参考
    - 效果追踪
    """
    case_lib = get_case_library()
    orchestrator = get_orchestrator()

    # 获取执行记录
    execution = orchestrator.get_execution(request.execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {request.execution_id}")

    # 创建案例
    case = case_lib.create_case_from_execution(
        execution=execution,
        problem_description=request.problem_description,
        root_cause=request.root_cause,
        lessons_learned=request.lessons_learned,
        created_by=request.created_by
    )

    return CreateCaseResponse(
        case_id=case.case_id,
        execution_id=case.execution_id,
        outcome=case.outcome,
        effectiveness_score=case.effectiveness_score
    )


@router.get("/v1.1/cases/{case_id}", response_model=RemediationCase)
async def get_case(case_id: str):
    """获取案例详情"""
    case_lib = get_case_library()
    case = case_lib.get_case(case_id)

    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    return case


@router.get("/v1.1/cases", response_model=CaseListResponse)
async def list_cases(
    tag: Optional[str] = Query(None, description="标签过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制")
):
    """
    列出修复案例

    可按标签过滤，查看特定类型的修复案例
    """
    case_lib = get_case_library()
    cases = case_lib.list_cases(tag=tag, limit=limit)

    return {
        "cases": cases,
        "total": len(cases)
    }


@router.post("/v1.1/cases/similar", response_model=SimilarCaseResponse)
async def search_similar_cases(request: SimilarCaseRequest):
    """
    搜索相似案例

    当遇到新问题时，搜索历史上类似的修复案例，参考其解决方案和经验教训。
    这可以大大缩短问题排查时间，避免重复踩坑。
    """
    case_lib = get_case_library()
    cases = case_lib.search_similar_cases(
        script_id=request.script_id,
        problem_keywords=request.problem_keywords
    )

    return {
        "cases": cases,
        "total": len(cases)
    }


@router.get("/v1.1/cases/stats")
async def get_case_stats():
    """获取案例统计信息"""
    case_lib = get_case_library()
    stats = case_lib.get_stats()

    return stats


@router.get("/v1.1/cases/by-execution/{execution_id}", response_model=RemediationCase)
async def get_case_by_execution(execution_id: str):
    """通过执行 ID 获取关联的案例"""
    case_lib = get_case_library()
    case = case_lib.get_case_by_execution(execution_id)

    if not case:
        raise HTTPException(
            status_code=404,
            detail=f"No case found for execution: {execution_id}"
        )

    return case


@router.post("/v1.1/set-dependencies")
async def set_service_dependencies(request: SetDependenciesRequest):
    """
    设置服务依赖关系

    用于影响分析时计算受影响的服务范围。
    格式：{"service_a": ["service_b", "service_c"]} 表示 service_a 依赖 service_b 和 service_c
    """
    analyzer = get_impact_analyzer()
    analyzer.set_dependencies(request.dependencies)

    return {
        "message": "Service dependencies updated",
        "services_count": len(request.dependencies)
    }


@router.get("/v1.1/health")
async def health_check_v11():
    """v1.1 功能健康检查"""
    analyzer = get_impact_analyzer()
    case_lib = get_case_library()

    return {
        "status": "healthy",
        "components": {
            "impact_analyzer": "healthy",
            "case_library": "healthy"
        },
        "stats": {
            "cases_count": len(case_lib._cases),
            "dependencies_configured": len(analyzer._service_dependencies) > 0
        }
    }
