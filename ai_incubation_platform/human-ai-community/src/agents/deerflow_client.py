"""
DeerFlow 2.0 客户端封装

提供与 DeerFlow Agent 框架的集成，支持工作流编排和工具调用。
当 DeerFlow 不可用时，自动降级到本地执行模式。
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# 尝试导入 DeerFlow，如果不可用则使用降级模式
try:
    import httpx
    DEERFLOW_HTTPX_AVAILABLE = True
except ImportError:
    DEERFLOW_HTTPX_AVAILABLE = False
    logger.warning("httpx not available, DeerFlow client will be disabled")


@dataclass
class DeerFlowConfig:
    """DeerFlow 配置"""
    api_key: Optional[str] = None
    base_url: str = "https://api.deerflow.ai/v1"
    timeout: int = 30
    max_retries: int = 3


class DeerFlowClient:
    """
    DeerFlow 2.0 客户端

    提供 Agent 工作流编排和工具调用的统一接口。
    支持降级模式：当 DeerFlow 服务不可用时，使用本地工具执行。
    """

    def __init__(self, config: Optional[DeerFlowConfig] = None):
        self.config = config or DeerFlowConfig(
            api_key=os.getenv("DEERFLOW_API_KEY"),
            base_url=os.getenv("DEERFLOW_BASE_URL", "https://api.deerflow.ai/v1"),
        )
        self._available = False
        self._client = None
        self._initialize()

    def _initialize(self):
        """初始化客户端连接"""
        if not DEERFLOW_HTTPX_AVAILABLE:
            logger.warning("DeerFlow client disabled: httpx not available")
            return

        if not self.config.api_key:
            logger.warning("DeerFlow API key not configured, using fallback mode")
            return

        try:
            self._client = httpx.Client(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
            )
            self._available = True
            logger.info("DeerFlow client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize DeerFlow client: {e}")
            self._available = False

    def is_available(self) -> bool:
        """检查 DeerFlow 服务是否可用"""
        return self._available and self._client is not None

    async def run_workflow(self, workflow_name: str, **input_data) -> Dict[str, Any]:
        """
        运行 DeerFlow 工作流

        Args:
            workflow_name: 工作流名称
            **input_data: 工作流输入参数

        Returns:
            工作流执行结果
        """
        if not self.is_available():
            logger.warning(f"DeerFlow unavailable, cannot run workflow: {workflow_name}")
            raise RuntimeError("DeerFlow service unavailable")

        try:
            response = self._client.post(
                f"/workflows/{workflow_name}/run",
                json={"input": input_data},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to run workflow {workflow_name}: {e}")
            raise

    async def call_tool(self, tool_name: str, **input_data) -> Dict[str, Any]:
        """
        调用 DeerFlow 工具

        Args:
            tool_name: 工具名称
            **input_data: 工具输入参数

        Returns:
            工具执行结果
        """
        if not self.is_available():
            logger.warning(f"DeerFlow unavailable, cannot call tool: {tool_name}")
            raise RuntimeError("DeerFlow service unavailable")

        try:
            response = self._client.post(
                f"/tools/{tool_name}/call",
                json={"input": input_data},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise

    async def list_workflows(self) -> List[str]:
        """列出可用的工作流"""
        if not self.is_available():
            return []

        try:
            response = self._client.get("/workflows")
            response.raise_for_status()
            data = response.json()
            return [wf["name"] for wf in data.get("workflows", [])]
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return []

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出可用的工具"""
        if not self.is_available():
            return []

        try:
            response = self._client.get("/tools")
            response.raise_for_status()
            return response.json().get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    def close(self):
        """关闭客户端连接"""
        if self._client:
            self._client.close()


# 全局客户端实例
_deerflow_client: Optional[DeerFlowClient] = None


def get_deerflow_client(config: Optional[DeerFlowConfig] = None) -> DeerFlowClient:
    """获取 DeerFlow 客户端单例"""
    global _deerflow_client
    if _deerflow_client is None:
        _deerflow_client = DeerFlowClient(config)
    return _deerflow_client


def is_deerflow_available() -> bool:
    """检查 DeerFlow 是否可用"""
    client = get_deerflow_client()
    return client.is_available()


class LocalWorkflowRunner:
    """
    本地工作流执行器（降级模式）

    当 DeerFlow 服务不可用时，使用本地工具注册表执行工作流。
    """

    def __init__(self, tools_registry: Dict[str, Any]):
        self.tools_registry = tools_registry
        self._execution_history: List[Dict[str, Any]] = []

    async def run_workflow(self, workflow_name: str, **input_data) -> Dict[str, Any]:
        """
        本地执行工作流

        工作流定义为工具调用序列。每个步骤的输出作为下一步的输入。
        """
        logger.info(f"Running local workflow: {workflow_name}")

        # 根据工作流名称路由到对应的本地实现
        if workflow_name == "community_moderation":
            return await self._run_moderation_workflow(input_data)
        elif workflow_name == "content_recommendation":
            return await self._run_recommendation_workflow(input_data)
        elif workflow_name == "member_matching":
            return await self._run_matching_workflow(input_data)
        else:
            raise ValueError(f"Unknown workflow: {workflow_name}")

    async def _run_moderation_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """内容审核工作流"""
        result = {
            "workflow": "community_moderation",
            "steps": [],
            "final_decision": None,
        }

        # Step 1: 内容分析
        if "content" in input_data:
            analysis_result = await self._call_local_tool("analyze_content", {
                "content": input_data["content"],
                "context": input_data.get("context", ""),
            })
            result["steps"].append({"step": "analyze_content", "result": analysis_result})

        # Step 2: 规则匹配
        if "content" in input_data:
            rule_result = await self._call_local_tool("check_rules", {
                "content": input_data["content"],
                "analysis": result["steps"][0]["result"] if result["steps"] else None,
            })
            result["steps"].append({"step": "check_rules", "result": rule_result})

        # Step 3: 决策
        result["final_decision"] = await self._call_local_tool("make_moderation_decision", {
            "analysis": result["steps"][0]["result"] if result["steps"] else None,
            "rule_check": result["steps"][1]["result"] if len(result["steps"]) > 1 else None,
        })

        self._execution_history.append({
            "workflow": workflow_name,
            "timestamp": datetime.now().isoformat(),
            "result": result,
        })

        return result

    async def _run_recommendation_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """内容推荐工作流"""
        result = {
            "workflow": "content_recommendation",
            "recommendations": [],
        }

        # 调用推荐工具
        if "user_id" in input_data:
            rec_result = await self._call_local_tool("get_recommendations", {
                "user_id": input_data["user_id"],
                "limit": input_data.get("limit", 10),
            })
            result["recommendations"] = rec_result.get("items", [])

        return result

    async def _run_matching_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """成员匹配工作流"""
        result = {
            "workflow": "member_matching",
            "matches": [],
        }

        # 调用匹配工具
        if "member_id" in input_data:
            match_result = await self._call_local_tool("find_matching_members", {
                "member_id": input_data["member_id"],
                "criteria": input_data.get("criteria", {}),
            })
            result["matches"] = match_result.get("matches", [])

        return result

    async def _call_local_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用本地工具"""
        if tool_name not in self.tools_registry:
            logger.warning(f"Tool not found: {tool_name}")
            return {"error": f"Tool not found: {tool_name}"}

        tool = self.tools_registry[tool_name]
        try:
            if hasattr(tool, "run"):
                return await tool.run(input_data)
            elif callable(tool):
                return await tool(input_data)
            else:
                return {"error": f"Invalid tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}: {e}")
            return {"error": str(e)}
