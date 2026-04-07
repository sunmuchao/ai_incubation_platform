"""
路由工具 - 路由请求到对应子项目并聚合结果
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# 子项目 API 端点映射
PROJECT_ENDPOINTS = {
    "ai-hires-human": {
        "base_url": "http://localhost:8001",
        "chat_endpoint": "/api/v1/chat",
        "task_endpoint": "/api/v1/tasks",
    },
    "ai-employee-platform": {
        "base_url": "http://localhost:8002",
        "chat_endpoint": "/api/v1/chat",
        "matching_endpoint": "/api/v1/matching",
    },
    "human-ai-community": {
        "base_url": "http://localhost:8003",
        "chat_endpoint": "/api/v1/chat",
        "posts_endpoint": "/api/v1/posts",
    },
    "ai-community-buying": {
        "base_url": "http://localhost:8004",
        "chat_endpoint": "/api/v1/chat",
        "products_endpoint": "/api/v1/products",
    },
    "ai-opportunity-miner": {
        "base_url": "http://localhost:8005",
        "chat_endpoint": "/api/v1/chat",
        "opportunities_endpoint": "/api/v1/opportunities",
    },
    "ai-runtime-optimizer": {
        "base_url": "http://localhost:8006",
        "optimize_endpoint": "/api/v1/optimize",
    },
    "ai-traffic-booster": {
        "base_url": "http://localhost:8007",
        "boost_endpoint": "/api/v1/boost",
    },
    "ai-code-understanding": {
        "base_url": "http://localhost:8008",
        "analyze_endpoint": "/api/v1/analyze",
    },
    "data-agent-connector": {
        "base_url": "http://localhost:8009",
        "connect_endpoint": "/api/v1/connect",
    },
    "matchmaker-agent": {
        "base_url": "http://localhost:8010",
        "match_endpoint": "/api/v1/match",
    },
    "loganalyzer-agent": {
        "base_url": "http://localhost:8011",
        "analyze_endpoint": "/api/v1/analyze",
    },
}


@dataclass
class RouteRequest:
    """路由请求"""
    project: str
    endpoint: str
    method: str = "POST"
    payload: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class RouteResponse:
    """路由响应"""
    project: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class ProjectRouter:
    """项目路由器"""

    def __init__(self):
        self._session = None
        self._timeout_seconds = 30

    async def _http_post(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """发送 HTTP POST 请求"""
        # 占位实现，实际应使用 aiohttp 或 httpx
        # 这里模拟一个响应
        await asyncio.sleep(0.1)  # 模拟网络延迟
        return {
            "status": "ok",
            "project": url.split(":")[1].replace("//", "") if "//" in url else "unknown",
            "message": f"Request forwarded to {url}",
            "payload_received": payload,
        }

    async def route(
        self,
        project: str,
        payload: Dict[str, Any],
        endpoint: Optional[str] = None,
    ) -> RouteResponse:
        """
        路由请求到指定子项目

        Args:
            project: 目标子项目名称
            payload: 请求负载
            endpoint: 可选的具体端点

        Returns:
            路由响应
        """
        logger.info(f"Routing to project: {project}")

        if project not in PROJECT_ENDPOINTS:
            return RouteResponse(
                project=project,
                success=False,
                error=f"Unknown project: {project}",
            )

        project_config = PROJECT_ENDPOINTS[project]
        target_url = project_config["base_url"] + (endpoint or project_config.get("chat_endpoint", "/"))

        start_time = datetime.now()

        try:
            # 实际实现应使用异步 HTTP 客户端
            # response = await self._session.post(target_url, json=payload, headers=headers)
            response_data = await self._http_post(target_url, payload, {})

            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            return RouteResponse(
                project=project,
                success=True,
                data=response_data,
                latency_ms=latency,
            )

        except Exception as e:
            logger.error(f"Failed to route to {project}: {e}")
            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            return RouteResponse(
                project=project,
                success=False,
                error=str(e),
                latency_ms=latency,
            )

    async def route_batch(
        self,
        requests: List[RouteRequest],
    ) -> List[RouteResponse]:
        """
        批量路由请求到多个子项目

        Args:
            requests: 路由请求列表

        Returns:
            路由响应列表
        """
        logger.info(f"Routing batch of {len(requests)} requests")

        tasks = [
            self.route(req.project, req.payload, req.endpoint)
            for req in requests
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                results.append(RouteResponse(
                    project=requests[i].project,
                    success=False,
                    error=str(response),
                ))
            else:
                results.append(response)

        return results


# 全局路由器实例
_router = ProjectRouter()


async def route_to_project(
    project: str,
    payload: Dict[str, Any],
    endpoint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    路由请求到对应子项目

    Args:
        project: 目标子项目名称
        payload: 请求负载，通常包含 user_id, message, context 等
        endpoint: 可选的具体 API 端点

    Returns:
        路由结果：
        - project: 目标项目
        - success: 是否成功
        - data: 返回数据
        - error: 错误信息（如果有）
        - latency_ms: 延迟毫秒数
    """
    logger.info(f"Routing to {project} with payload: {payload}")

    response = await _router.route(project, payload, endpoint)

    return {
        "project": response.project,
        "success": response.success,
        "data": response.data,
        "error": response.error,
        "latency_ms": response.latency_ms,
        "timestamp": response.timestamp.isoformat(),
    }


async def aggregate_results(
    results: List[Dict[str, Any]],
    aggregation_mode: str = "merge",
) -> Dict[str, Any]:
    """
    聚合多个子项目的结果

    Args:
        results: 子项目返回结果列表
        aggregation_mode: 聚合模式
            - "merge": 合并所有结果
            - "select_best": 选择最佳结果（基于置信度）
            - "concatenate": 串联所有结果

    Returns:
        聚合后的结果
    """
    logger.info(f"Aggregating {len(results)} results with mode: {aggregation_mode}")

    if not results:
        return {
            "aggregated": True,
            "mode": aggregation_mode,
            "count": 0,
            "data": None,
        }

    successful_results = [r for r in results if r.get("success", False)]
    failed_results = [r for r in results if not r.get("success", False)]

    if aggregation_mode == "merge":
        # 合并所有成功结果
        merged_data = {}
        for result in successful_results:
            project = result.get("project", "unknown")
            merged_data[project] = result.get("data", {})

        return {
            "aggregated": True,
            "mode": aggregation_mode,
            "count": len(successful_results),
            "failed_count": len(failed_results),
            "data": merged_data,
            "failures": [{"project": r.get("project"), "error": r.get("error")} for r in failed_results],
        }

    elif aggregation_mode == "select_best":
        # 选择置信度最高的结果
        if not successful_results:
            return {
                "aggregated": True,
                "mode": aggregation_mode,
                "count": 0,
                "data": None,
                "error": "No successful results to select from",
            }

        # 简单选择第一个成功结果（实际实现应基于置信度）
        best_result = successful_results[0]
        return {
            "aggregated": True,
            "mode": aggregation_mode,
            "count": len(successful_results),
            "selected_project": best_result.get("project"),
            "data": best_result.get("data"),
        }

    elif aggregation_mode == "concatenate":
        # 串联所有结果
        concatenated = []
        for result in successful_results:
            concatenated.append({
                "project": result.get("project"),
                "data": result.get("data"),
            })

        return {
            "aggregated": True,
            "mode": aggregation_mode,
            "count": len(successful_results),
            "data": concatenated,
        }

    else:
        return {
            "aggregated": False,
            "error": f"Unknown aggregation mode: {aggregation_mode}",
        }


async def cross_project_workflow(
    workflow_name: str,
    projects_involved: List[str],
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    执行跨项目工作流

    Args:
        workflow_name: 工作流名称
        projects_involved: 参与的子项目列表
        input_data: 输入数据

    Returns:
        工作流执行结果

    示例工作流：
    - "startup_journey": 创业旅程 - 同时调用商机挖掘、任务发布、团购资源
    - "talent_pipeline": 人才管道 - 同时调用员工平台、社区匹配、培训系统
    - "full_stack_analysis": 全栈分析 - 同时调用代码理解、日志分析、性能优化
    """
    logger.info(f"Executing cross-project workflow: {workflow_name}")
    logger.info(f"Projects involved: {projects_involved}")

    start_time = datetime.now()

    # 构建并行请求
    route_requests = [
        RouteRequest(
            project=project,
            endpoint=None,  # 使用默认端点
            payload={
                **input_data,
                "workflow_context": {
                    "workflow_name": workflow_name,
                    "coordinator": "platform-portal",
                    "timestamp": start_time.isoformat(),
                },
            },
        )
        for project in projects_involved
    ]

    # 并行执行所有请求
    responses = await _router.route_batch(route_requests)

    # 聚合结果
    aggregation_result = await aggregate_results(
        [
            {
                "project": resp.project,
                "success": resp.success,
                "data": resp.data,
                "error": resp.error,
            }
            for resp in responses
        ],
        aggregation_mode="merge",
    )

    total_latency = int((datetime.now() - start_time).total_seconds() * 1000)

    return {
        "workflow_name": workflow_name,
        "projects_involved": projects_involved,
        "total_latency_ms": total_latency,
        "individual_results": [
            {
                "project": resp.project,
                "success": resp.success,
                "latency_ms": resp.latency_ms,
            }
            for resp in responses
        ],
        "aggregated_data": aggregation_result.get("data"),
    }


# 注册工具
from .registry import register_tool

register_tool(
    name="route_to_project",
    description="路由请求到对应子项目 API",
    input_schema={
        "type": "object",
        "properties": {
            "project": {
                "type": "string",
                "description": "目标子项目名称",
            },
            "payload": {
                "type": "object",
                "description": "请求负载",
            },
            "endpoint": {
                "type": "string",
                "description": "可选的具体 API 端点",
            },
        },
        "required": ["project", "payload"],
    },
    handler=route_to_project,
)

register_tool(
    name="aggregate_results",
    description="聚合多个子项目的返回结果",
    input_schema={
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {"type": "object"},
                "description": "子项目返回结果列表",
            },
            "aggregation_mode": {
                "type": "string",
                "enum": ["merge", "select_best", "concatenate"],
                "description": "聚合模式",
            },
        },
        "required": ["results"],
    },
    handler=aggregate_results,
)

register_tool(
    name="cross_project_workflow",
    description="执行跨项目工作流，协调多个子项目完成复杂任务",
    input_schema={
        "type": "object",
        "properties": {
            "workflow_name": {
                "type": "string",
                "description": "工作流名称",
            },
            "projects_involved": {
                "type": "array",
                "items": {"type": "string"},
                "description": "参与的子项目列表",
            },
            "input_data": {
                "type": "object",
                "description": "输入数据",
            },
        },
        "required": ["workflow_name", "projects_involved", "input_data"],
    },
    handler=cross_project_workflow,
)
