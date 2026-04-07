"""
Tools 层 - 供 AI Agent 调用的工具注册表
"""
from .task_tools import TOOLS_REGISTRY as TASK_TOOLS
from .worker_tools import TOOLS_REGISTRY as WORKER_TOOLS
from .verification_tools import TOOLS_REGISTRY as VERIFICATION_TOOLS

# 合并所有工具注册表
TOOLS_REGISTRY = {}
TOOLS_REGISTRY.update(TASK_TOOLS)
TOOLS_REGISTRY.update(WORKER_TOOLS)
TOOLS_REGISTRY.update(VERIFICATION_TOOLS)

__all__ = ["TOOLS_REGISTRY", "TASK_TOOLS", "WORKER_TOOLS", "VERIFICATION_TOOLS"]
