"""
供 DeerFlow / LLM function-calling 使用的工具描述与 HTTP 映射。

本服务本身不内嵌 Agent 运行时（见 PLATFORM_AGENT_STANDARD.md），由上游通过 REST 调用；
本模块便于在网关中注册为 Tool / MCP。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

PUBLIC_BASE = os.getenv("AI_HIRES_HUMAN_PUBLIC_BASE_URL", "http://127.0.0.1:8004").rstrip("/")


def openai_style_tools() -> List[Dict[str, Any]]:
    """OpenAI Chat Completions `tools` 兼容结构。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "human_escalation_create_task",
                "description": (
                    "当当前 AI/Agent 无法独立完成目标时（尤其需要真人在物理世界到场、线下采集、"
                    "或需人类合规判断），向「AI 雇佣真人平台」发布任务，由真人接单执行。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ai_employer_id": {
                            "type": "string",
                            "description": "上游 Agent / 租户标识，用于验收与幂等。",
                        },
                        "title": {"type": "string"},
                        "description": {"type": "string", "description": "任务说明，真人可读。"},
                        "capability_gap": {
                            "type": "string",
                            "description": "为何 AI 无法独立完成（必填建议）。",
                        },
                        "interaction_type": {
                            "type": "string",
                            "enum": ["digital", "physical", "hybrid"],
                            "description": "交互形态：纯线上 / 物理世界 / 混合。",
                        },
                        "acceptance_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "验收检查项列表。",
                        },
                        "location_hint": {
                            "type": "string",
                            "description": "线下任务可选地点提示（勿填敏感隐私）。",
                        },
                        "required_skills": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "技能标签，如 {\"role\": \"线下采集\"}。",
                        },
                        "reward_amount": {"type": "number"},
                        "reward_currency": {"type": "string", "default": "CNY"},
                        "callback_url": {
                            "type": "string",
                            "description": "验收通过后异步 POST 结果（JSON）的 URL，可选。",
                        },
                        "publish_immediately": {
                            "type": "boolean",
                            "default": True,
                            "description": "是否创建后立即进入可接单状态。",
                        },
                    },
                    "required": [
                        "ai_employer_id",
                        "title",
                        "description",
                        "capability_gap",
                    ],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_workers_by_skill",
                "description": "根据技能搜索工人，用于匹配合适的真人执行者。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skills": {
                            "type": "string",
                            "description": "技能标签，逗号分隔（如：线下采集，数据标注）。",
                        },
                        "location": {
                            "type": "string",
                            "description": "地点模糊匹配。",
                        },
                        "min_level": {
                            "type": "integer",
                            "default": 0,
                            "description": "最低等级。",
                        },
                        "min_rating": {
                            "type": "number",
                            "default": 0.0,
                            "description": "最低评分。",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_worker_profile",
                "description": "获取指定工人的详细画像，包括技能、完成任务数、评分等。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "worker_id": {
                            "type": "string",
                            "description": "工人 ID。",
                        },
                    },
                    "required": ["worker_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_platform_stats",
                "description": "获取平台整体统计数据，用于 Agent 决策参考。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_task_completion_report",
                "description": "获取任务完成情况报表，支持按时间分组。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "开始日期 (YYYY-MM-DD)。",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "结束日期 (YYYY-MM-DD)。",
                        },
                        "group_by": {
                            "type": "string",
                            "enum": ["day", "week", "month", "status", "priority"],
                            "default": "day",
                        },
                    },
                },
            },
        },
    ]


def http_tool_mapping() -> Dict[str, Any]:
    """将函数名映射到本服务 REST 端点，供网关在收到 tool call 时代理转发。"""
    return {
        "human_escalation_create_task": {
            "method": "POST",
            "url": f"{PUBLIC_BASE}/api/tasks",
            "body": "TaskCreate JSON（与 OpenAPI /docs 一致）",
        },
        "search_workers_by_skill": {
            "method": "GET",
            "url": f"{PUBLIC_BASE}/api/workers/search",
            "params": "skills, location, min_level, min_rating",
        },
        "get_worker_profile": {
            "method": "GET",
            "url": f"{PUBLIC_BASE}/api/workers/{{worker_id}}",
        },
        "get_platform_stats": {
            "method": "GET",
            "url": f"{PUBLIC_BASE}/api/admin/stats",
        },
        "get_task_completion_report": {
            "method": "GET",
            "url": f"{PUBLIC_BASE}/api/reports/task-completion",
            "params": "start_date, end_date, group_by",
        },
        "poll_or_callback": {
            "note": "创建后可用 GET /api/tasks/{task_id} 轮询；若设置了 callback_url，验收通过后会收到 task.completed 事件。",
        },
    }


def get_agent_tool_bundle() -> Dict[str, Any]:
    return {
        "service": "ai-hires-human",
        "version": "0.5.0",
        "public_base_url": PUBLIC_BASE,
        "openai_tools": openai_style_tools(),
        "http_mapping": http_tool_mapping(),
        "docs": f"{PUBLIC_BASE}/docs",
    }
