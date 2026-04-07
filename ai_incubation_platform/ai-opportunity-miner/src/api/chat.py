"""
对话式 API

提供自然语言交互接口，支持：
- 商机查询
- 趋势分析
- 主动推送配置
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    """对话请求"""
    query: str = Field(..., description="用户自然语言查询")
    context: Optional[Dict] = Field(None, description="对话上下文")


class ChatResponse(BaseModel):
    """对话响应"""
    query: str
    intent: str
    response: str
    data: Optional[Dict] = None
    suggestions: List[str] = Field(default_factory=list)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话式查询接口

    用户可以使用自然语言查询商机、分析趋势等
    """
    from agents.opportunity_agent import get_opportunity_agent

    agent = get_opportunity_agent()
    result = await agent.chat_query(request.query)

    # 生成建议
    suggestions = _generate_suggestions(result.get("intent", ""))

    return ChatResponse(
        query=request.query,
        intent=result.get("intent", "unknown"),
        response=result.get("response", ""),
        data=result.get("data"),
        suggestions=suggestions
    )


def _generate_suggestions(intent: str) -> List[str]:
    """根据意图生成建议"""
    suggestions_map = {
        "discover_opportunities": [
            "查看高价值商机",
            "按行业筛选",
            "启用主动推送"
        ],
        "analyze_trend": [
            "查看相关商机",
            "对比多个行业",
            "导出趋势报告"
        ],
        "enable_alerts": [
            "查看警报历史",
            "配置推送渠道",
            "调整警报阈值"
        ],
        "unknown": [
            "帮我找人工智能领域的商机",
            "分析新能源行业趋势",
            "启用高价值商机推送"
        ]
    }
    return suggestions_map.get(intent, suggestions_map["unknown"])


@router.get("/intents")
async def list_intents():
    """列出支持的意图"""
    return {
        "intents": [
            {
                "name": "discover_opportunities",
                "description": "发现商机",
                "examples": [
                    "帮我找人工智能领域的商机",
                    "最近有什么新的投资机会",
                    "显示所有高价值商机"
                ]
            },
            {
                "name": "analyze_trend",
                "description": "分析趋势",
                "examples": [
                    "分析新能源行业趋势",
                    "人工智能的发展趋势如何",
                    "哪个行业增长最快"
                ]
            },
            {
                "name": "evaluate_opportunity",
                "description": "评估商机",
                "examples": [
                    "评估这个商机的价值",
                    "这个机会有多大的成功概率",
                    "是否值得投入"
                ]
            },
            {
                "name": "enable_alerts",
                "description": "启用主动推送",
                "examples": [
                    "有重要机会时通知我",
                    "启用高价值商机推送",
                    "配置警报通知"
                ]
            }
        ]
    }


@router.post("/proactive")
async def enable_proactive_mode(
    keywords: Optional[List[str]] = None,
    industries: Optional[List[str]] = None,
    confidence_threshold: float = 0.7
):
    """
    启用主动推送模式

    AI 将自动监控并推送高价值商机
    """
    from agents.opportunity_agent import get_opportunity_agent

    agent = get_opportunity_agent()
    result = await agent.proactive_discovery(
        keywords=keywords,
        industries=industries
    )

    return {
        "status": "proactive_mode_enabled",
        "keywords_monitored": keywords or ["人工智能", "数字经济", "智能制造"],
        "industries_monitored": industries or ["人工智能", "新能源", "生物医药"],
        "confidence_threshold": confidence_threshold,
        "discovery_result": result
    }


@router.get("/suggestions")
async def get_suggestions():
    """获取智能建议列表"""
    from agents.opportunity_agent import get_opportunity_agent

    agent = get_opportunity_agent()

    # 基于当前数据生成建议
    suggestions = []

    # 检查是否有高价值待处理商机
    list_result = await agent.execute_tool("list_opportunities")
    if list_result.get("count", 0) > 0:
        opportunities = list_result.get("opportunities", [])
        high_value = [o for o in opportunities if o.get("potential_value", 0) >= 1000000]
        if high_value:
            suggestions.append({
                "type": "action",
                "title": f"发现 {len(high_value)} 条高价值商机",
                "suggestion": "建议优先查看这些商机",
                "action": "/opportunities?filter=high_value"
            })

    return {
        "suggestions": suggestions,
        "generated_at": datetime.now().isoformat()
    }
