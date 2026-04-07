"""
分析工具
封装趋势分析、竞品分析、数据获取等功能，供 DeerFlow 2.0 Agent 调用
"""
from typing import List, Dict, Any
import logging
import sys
import os

# 确保能导入 models 和 services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.opportunity_service import opportunity_service

logger = logging.getLogger(__name__)


# ============================================================
# 工具处理器实现
# ============================================================

async def _analyze_trend_handler(keyword: str, days: int = 30) -> Dict[str, Any]:
    """趋势分析处理器"""
    try:
        trend = await opportunity_service.generate_trend_analysis(keyword, days)

        return {
            "success": True,
            "trend": {
                "keyword": trend.keyword,
                "trend_score": trend.trend_score,
                "growth_rate": trend.growth_rate,
                "related_keywords": trend.related_keywords,
                "data_points": trend.data_points,
                "extra": trend.extra if hasattr(trend, 'extra') else {},
            },
            "message": f"完成对 '{keyword}' 的趋势分析",
        }
    except Exception as e:
        logger.error(f"Failed to analyze trend: {str(e)}")
        return {"success": False, "error": str(e)}


async def _analyze_competition_handler(industry: str, days: int = 60) -> Dict[str, Any]:
    """竞品分析处理器"""
    try:
        analysis = await opportunity_service.analyze_competition(industry, days)

        return {
            "success": True,
            "analysis": {
                "industry": analysis.get("industry", industry),
                "companies": analysis.get("companies", []),
                "products": analysis.get("products", []),
                "llm_analysis": analysis.get("llm_analysis", {}),
            },
            "message": f"完成对 '{industry}' 行业的竞争格局分析",
        }
    except Exception as e:
        logger.error(f"Failed to analyze competition: {str(e)}")
        return {"success": False, "error": str(e)}


async def _fetch_news_handler(keywords: List[str], days: int = 7) -> Dict[str, Any]:
    """获取新闻处理器"""
    try:
        result = await opportunity_service.get_news_data(keywords, days)

        return {
            "success": True,
            "count": result.get("count", 0),
            "articles": result.get("articles", []),
            "message": f"获取到 {result.get('count', 0)} 篇相关新闻",
        }
    except Exception as e:
        logger.error(f"Failed to fetch news: {str(e)}")
        return {"success": False, "error": str(e)}


async def _fetch_reports_handler(keywords: List[str]) -> Dict[str, Any]:
    """获取行业报告处理器"""
    try:
        result = await opportunity_service.get_industry_reports(keywords)

        return {
            "success": True,
            "count": result.get("count", 0),
            "reports": result.get("reports", []),
            "message": f"获取到 {result.get('count', 0)} 篇行业报告",
        }
    except Exception as e:
        logger.error(f"Failed to fetch reports: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================================================
# Tool 定义：遵循 DeerFlow 2.0 工具规范
# ============================================================

ANALYZE_TREND_TOOL = {
    "name": "analyze_trend",
    "description": "生成市场趋势分析报告。基于关键词分析市场趋势、增长率、相关关键词等。",
    "input_schema": {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "要分析的关键词，如 '人工智能'"
            },
            "days": {
                "type": "integer",
                "description": "分析最近 N 天的数据",
                "default": 30,
                "minimum": 1,
                "maximum": 365
            }
        },
        "required": ["keyword"]
    },
    "handler": _analyze_trend_handler,
    "audit_log": True,
}

ANALYZE_COMPETITION_TOOL = {
    "name": "analyze_competition",
    "description": "分析行业竞争格局。识别主要竞品、市场份额、进入壁垒等。",
    "input_schema": {
        "type": "object",
        "properties": {
            "industry": {
                "type": "string",
                "description": "行业名称，如 '新能源汽车'"
            },
            "days": {
                "type": "integer",
                "description": "分析最近 N 天的数据",
                "default": 60
            }
        },
        "required": ["industry"]
    },
    "handler": _analyze_competition_handler,
    "audit_log": True,
}

FETCH_NEWS_TOOL = {
    "name": "fetch_news",
    "description": "获取新闻数据。从公开新闻源或模拟数据源获取相关新闻文章。",
    "input_schema": {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "关键词列表"
            },
            "days": {
                "type": "integer",
                "description": "获取最近 N 天的新闻",
                "default": 7
            }
        },
        "required": ["keywords"]
    },
    "handler": _fetch_news_handler,
    "audit_log": False,
}

FETCH_REPORTS_TOOL = {
    "name": "fetch_reports",
    "description": "获取行业报告数据。从行业报告源获取相关研究报告。",
    "input_schema": {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "关键词列表"
            }
        },
        "required": ["keywords"]
    },
    "handler": _fetch_reports_handler,
    "audit_log": False,
}


# ============================================================
# 工具注册表
# ============================================================

ANALYSIS_TOOLS = [
    ANALYZE_TREND_TOOL,
    ANALYZE_COMPETITION_TOOL,
    FETCH_NEWS_TOOL,
    FETCH_REPORTS_TOOL,
]


def get_analysis_tools() -> List[Dict]:
    """获取所有分析工具"""
    return ANALYSIS_TOOLS


def get_tool_by_name(name: str):
    """根据名称获取工具"""
    for tool in ANALYSIS_TOOLS:
        if tool["name"] == name:
            return tool
    return None
