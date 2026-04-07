"""
Tool Registry - Central Registry for DeerFlow 2.0 Tools

All business operations are registered as tools with:
- name: Unique tool identifier
- description: Human-readable description for AI understanding
- input_schema: JSON Schema for parameter validation
- handler: Async function to execute the tool
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# Global tool registry
TOOLS_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    handler: Callable,
    tags: Optional[List[str]] = None,
):
    """
    Register a tool in the global registry.

    Args:
        name: Unique tool identifier
        description: Human-readable description for AI understanding
        input_schema: JSON Schema for parameter validation
        handler: Async function to execute the tool
        tags: Optional tags for categorization
    """
    TOOLS_REGISTRY[name] = {
        "name": name,
        "description": description,
        "input_schema": input_schema,
        "handler": handler,
        "tags": tags or [],
    }
    logger.info(f"Registered tool: {name}")


def get_tool(name: str) -> Optional[Dict[str, Any]]:
    """Get a tool by name."""
    return TOOLS_REGISTRY.get(name)


def list_tools(tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all registered tools, optionally filtered by tag.

    Args:
        tag: Optional tag filter

    Returns:
        List of tool definitions (without handlers)
    """
    tools = []
    for tool in TOOLS_REGISTRY.values():
        if tag and tag not in tool.get("tags", []):
            continue
        tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"],
            "tags": tool.get("tags", []),
        })
    return tools


async def invoke_tool(name: str, **parameters: Any) -> Dict[str, Any]:
    """
    Invoke a tool by name with parameters.

    Args:
        name: Tool name
        **parameters: Tool parameters

    Returns:
        Tool execution result
    """
    tool = get_tool(name)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")

    handler = tool["handler"]
    if asyncio.iscoroutinefunction(handler):
        return await handler(**parameters)
    return handler(**parameters)


# Initialize default tools
def init_default_tools():
    """Initialize default tools from performance_tools module."""
    try:
        from tools.performance_tools import register_performance_tools
        register_performance_tools()
        logger.info("Default performance tools registered")
    except Exception as e:
        logger.warning(f"Failed to register default tools: {e}")


# Auto-initialize on import
init_default_tools()
