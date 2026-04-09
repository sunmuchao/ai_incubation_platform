"""
DeerFlow 2.0 客户端封装

提供红娘 Agent 专用的 DeerFlow 客户端，支持工具注册和工作流编排。
"""
from typing import Optional, Any, Dict, List
from utils.logger import logger
from config import settings

# 尝试导入 DeerFlow，如果未安装则降级为本地模式
try:
    from deerflow.client import DeerFlowClient
    DEERFLOW_AVAILABLE = True
except ImportError:
    DeerFlowClient = None  # type: ignore
    DEERFLOW_AVAILABLE = False
    logger.warning("DeerFlow not installed, running in local mode")


class MatchmakerAgent:
    """
    红娘 Agent 封装类

    将匹配流程封装为 DeerFlow 可编排的工作流，支持：
    - 画像读取
    - 匹配计算
    - 解释生成
    - 结果留痕
    """

    def __init__(self):
        self.client: Optional[Any] = None
        self.tools: Dict[str, callable] = {}
        self._initialized = False

        if DEERFLOW_AVAILABLE:
            try:
                self.client = DeerFlowClient()
                logger.info("DeerFlow client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize DeerFlow client: {e}")
                self.client = None

    def register_tool(self, name: str, handler: callable, description: str, input_schema: dict) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            handler: 处理函数
            description: 工具描述
            input_schema: 输入参数 JSONSchema
        """
        self.tools[name] = {
            "handler": handler,
            "description": description,
            "input_schema": input_schema
        }
        logger.info(f"Tool registered: {name}")

    def get_tool(self, name: str) -> Optional[dict]:
        """获取已注册的工具"""
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        """获取所有已注册的工具名称"""
        return list(self.tools.keys())

    async def execute_tool(self, tool_name: str, **kwargs) -> dict:
        """
        执行工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        try:
            logger.info(f"Executing tool: {tool_name}, params: {kwargs}")
            result = await tool["handler"](**kwargs) if hasattr(tool["handler"], '__await__') else tool["handler"](**kwargs)
            logger.info(f"Tool execution completed: {tool_name}")
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {e}")
            return {"success": False, "error": str(e)}

    async def run_match_workflow(self, user_id: str, limit: int = 10) -> dict:
        """
        运行匹配工作流（本地模式）

        工作流步骤：
        1. 读取用户画像
        2. 执行匹配计算
        3. 生成匹配解释
        4. 记录匹配历史

        Args:
            user_id: 用户 ID
            limit: 返回匹配数量上限

        Returns:
            匹配结果
        """
        workflow_steps = [
            ("profile_read", {"user_id": user_id}),
            ("match_compute", {"user_id": user_id, "limit": limit}),
            ("reasoning_generate", {"user_id": user_id}),
            ("log_record", {"user_id": user_id, "action": "match"})
        ]

        results = {}
        for step_name, params in workflow_steps:
            if step_name not in self.tools:
                logger.warning(f"Tool not found for step: {step_name}, skipping...")
                continue

            result = await self.execute_tool(step_name, **params)
            results[step_name] = result

            if not result.get("success"):
                logger.error(f"Workflow step failed: {step_name}, error: {result.get('error')}")
                # 非致命错误继续执行后续步骤

        return results

    def is_deerflow_ready(self) -> bool:
        """检查 DeerFlow 是否可用"""
        return DEERFLOW_AVAILABLE and self.client is not None


# 全局 Agent 实例
_agent_instance: Optional[MatchmakerAgent] = None


def get_matchmaker_agent() -> MatchmakerAgent:
    """获取红娘 Agent 单例实例"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MatchmakerAgent()
    return _agent_instance
