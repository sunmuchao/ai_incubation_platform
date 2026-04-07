"""
Agents 层 - DeerFlow 2.0 Agent 实现

提供数据连接器领域的智能 Agent，负责：
1. 自主发现并连接数据源
2. 自主推断 schema 并转换
3. 对话式交互替代手动配置
"""
from .deerflow_client import DeerFlowClient, DeerFlowWorkflowResult
from .connector_agent import ConnectorAgent, AgentResponse, AgentState

__all__ = [
    "DeerFlowClient",
    "DeerFlowWorkflowResult",
    "ConnectorAgent",
    "AgentResponse",
    "AgentState",
]
