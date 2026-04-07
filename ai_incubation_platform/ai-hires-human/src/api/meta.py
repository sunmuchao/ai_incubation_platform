"""
元数据 API — Agent 工具清单（与 DeerFlow 2.0 / 网关对接用）。
"""
from __future__ import annotations

import os
import sys

from fastapi import APIRouter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_tool_spec import get_agent_tool_bundle

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/agent-tools")
async def agent_tools():
    """返回 OpenAI-style tools + HTTP 映射，便于在网关中注册为可调用工具。"""
    return get_agent_tool_bundle()
