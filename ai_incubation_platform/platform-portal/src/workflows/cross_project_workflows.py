"""
跨项目工作流 - 预定义的复杂工作流模板

这些工作流协调多个子项目完成复杂任务，体现 AI Native 的自主编排能力。
"""
import logging
from typing import Dict, Any, List
from datetime import datetime

from tools.routing_tools import cross_project_workflow as execute_cross_project_workflow

logger = logging.getLogger(__name__)


async def startup_journey_workflow(
    user_id: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    创业旅程工作流

    为想要创业的用户提供全方位支持：
    1. ai-opportunity-miner: 发现商机
    2. ai-hires-human: 发布任务找人
    3. ai-community-buying: 寻找团购资源

    Args:
        user_id: 用户 ID
        input_data: 输入数据，包含创业方向、预算等

    Returns:
        工作流执行结果
    """
    logger.info(f"[Startup Journey] Starting for user {user_id}")

    projects = ["ai-opportunity-miner", "ai-hires-human", "ai-community-buying"]

    result = await execute_cross_project_workflow(
        workflow_name="startup_journey",
        projects_involved=projects,
        input_data=input_data,
    )

    return {
        "workflow_name": "startup_journey",
        "description": "创业旅程 - 为创业者提供商机发现、任务发布、资源整合的全流程支持",
        "steps": [
            {"step": 1, "project": "ai-opportunity-miner", "action": "发现市场机会"},
            {"step": 2, "project": "ai-hires-human", "action": "发布任务招募人才"},
            {"step": 3, "project": "ai-community-buying", "action": "寻找团购资源降低成本"},
        ],
        "result": result,
    }


async def talent_pipeline_workflow(
    user_id: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    人才管道工作流

    构建企业人才供应链：
    1. ai-employee-platform: 寻找候选人
    2. human-ai-community: 查看社区信誉
    3. ai-hires-human: 创建雇佣合同

    Args:
        user_id: 用户 ID
        input_data: 输入数据，包含岗位要求、薪资范围等

    Returns:
        工作流执行结果
    """
    logger.info(f"[Talent Pipeline] Starting for user {user_id}")

    projects = ["ai-employee-platform", "human-ai-community", "ai-hires-human"]

    result = await execute_cross_project_workflow(
        workflow_name="talent_pipeline",
        projects_involved=projects,
        input_data=input_data,
    )

    return {
        "workflow_name": "talent_pipeline",
        "description": "人才管道 - 从候选人发现、信誉背调到合同创建的一站式招聘流程",
        "steps": [
            {"step": 1, "project": "ai-employee-platform", "action": "匹配候选人"},
            {"step": 2, "project": "human-ai-community", "action": "查询社区信誉"},
            {"step": 3, "project": "ai-hires-human", "action": "创建雇佣合同"},
        ],
        "result": result,
    }


async def full_stack_analysis_workflow(
    user_id: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    全栈分析工作流

    全面分析系统性能和代码质量：
    1. ai-code-understanding: 分析代码结构
    2. loganalyzer-agent: 分析系统日志
    3. ai-runtime-optimizer: 优化运行时性能

    Args:
        user_id: 用户 ID
        input_data: 输入数据，包含代码仓库地址、日志路径等

    Returns:
        工作流执行结果
    """
    logger.info(f"[Full Stack Analysis] Starting for user {user_id}")

    projects = ["ai-code-understanding", "loganalyzer-agent", "ai-runtime-optimizer"]

    result = await execute_cross_project_workflow(
        workflow_name="full_stack_analysis",
        projects_involved=projects,
        input_data=input_data,
    )

    return {
        "workflow_name": "full_stack_analysis",
        "description": "全栈分析 - 从代码质量、日志异常到性能优化的全面系统诊断",
        "steps": [
            {"step": 1, "project": "ai-code-understanding", "action": "代码架构分析"},
            {"step": 2, "project": "loganalyzer-agent", "action": "日志异常检测"},
            {"step": 3, "project": "ai-runtime-optimizer", "action": "性能优化建议"},
        ],
        "result": result,
    }


async def community_growth_workflow(
    user_id: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    社区增长工作流

    促进社区活跃度和成员增长：
    1. human-ai-community: 分析社区参与度
    2. ai-traffic-booster: 引流推广
    3. matchmaker-agent: 成员匹配

    Args:
        user_id: 用户 ID
        input_data: 输入数据，包含社区 ID、目标群体等

    Returns:
        工作流执行结果
    """
    logger.info(f"[Community Growth] Starting for user {user_id}")

    projects = ["human-ai-community", "ai-traffic-booster", "matchmaker-agent"]

    result = await execute_cross_project_workflow(
        workflow_name="community_growth",
        projects_involved=projects,
        input_data=input_data,
    )

    return {
        "workflow_name": "community_growth",
        "description": "社区增长 - 从参与度分析、流量引入到成员匹配的全方位社区运营方案",
        "steps": [
            {"step": 1, "project": "human-ai-community", "action": "社区活跃度分析"},
            {"step": 2, "project": "ai-traffic-booster", "action": "流量引入"},
            {"step": 3, "project": "matchmaker-agent", "action": "成员智能匹配"},
        ],
        "result": result,
    }


# 工作流注册表
WORKFLOW_REGISTRY = {
    "startup_journey": startup_journey_workflow,
    "talent_pipeline": talent_pipeline_workflow,
    "full_stack_analysis": full_stack_analysis_workflow,
    "community_growth": community_growth_workflow,
}


def get_workflow(workflow_name: str):
    """获取工作流处理函数"""
    return WORKFLOW_REGISTRY.get(workflow_name)


def list_workflows() -> List[Dict[str, Any]]:
    """列出所有可用工作流"""
    return [
        {
            "name": name,
            "func": func.__name__,
        }
        for name, func in WORKFLOW_REGISTRY.items()
    ]
