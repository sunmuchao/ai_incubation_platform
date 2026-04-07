"""
商机管理工具
封装商机相关的 CRUD 和发现功能，供 DeerFlow 2.0 Agent 调用
"""
from typing import List, Dict, Optional, Any
import logging
import sys
import os

# 确保能导入 models 和 services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.opportunity import BusinessOpportunity, OpportunityType, OpportunityStatus, RiskLabel, SourceType
from services.opportunity_service import opportunity_service

logger = logging.getLogger(__name__)


# ============================================================
# 工具处理器实现
# ============================================================

def _list_opportunities_handler(status: Optional[str] = None) -> Dict[str, Any]:
    """获取商机列表处理器"""
    try:
        opp_status = OpportunityStatus(status) if status else None
        opps = opportunity_service.list_opportunities(opp_status)

        # 序列化为 Dict
        result = [
            {
                "id": o.id,
                "title": o.title,
                "type": o.type.value,
                "confidence_score": o.confidence_score,
                "potential_value": o.potential_value,
                "potential_value_currency": o.potential_value_currency,
                "status": o.status.value,
                "created_at": o.created_at.isoformat(),
            }
            for o in opps
        ]

        return {
            "success": True,
            "count": len(result),
            "opportunities": result,
        }
    except Exception as e:
        logger.error(f"Failed to list opportunities: {str(e)}")
        return {"success": False, "error": str(e)}


def _get_opportunity_handler(opp_id: str) -> Dict[str, Any]:
    """获取商机详情处理器"""
    try:
        opp = opportunity_service.get_opportunity(opp_id)
        if not opp:
            return {"success": False, "error": f"Opportunity {opp_id} not found"}

        return {
            "success": True,
            "opportunity": {
                "id": opp.id,
                "title": opp.title,
                "description": opp.description,
                "type": opp.type.value,
                "confidence_score": opp.confidence_score,
                "potential_value": opp.potential_value,
                "potential_value_currency": opp.potential_value_currency,

                "source_type": opp.source_type.value,
                "source_name": opp.source_name,
                "source_url": opp.source_url,
                "source_publish_date": opp.source_publish_date.isoformat() if opp.source_publish_date else None,

                "risk_labels": [l.value for l in opp.risk_labels],
                "risk_score": opp.risk_score,
                "risk_description": opp.risk_description,

                "validation_steps": opp.validation_steps,
                "validation_status": opp.validation_status,
                "validation_notes": opp.validation_notes,

                "related_entities": opp.related_entities,
                "tags": opp.tags,
                "status": opp.status.value,
                "created_at": opp.created_at.isoformat(),
                "updated_at": opp.updated_at.isoformat(),
            }
        }
    except Exception as e:
        logger.error(f"Failed to get opportunity: {str(e)}")
        return {"success": False, "error": str(e)}


async def _discover_opportunities_handler(
    keywords: Optional[List[str]] = None,
    industry: Optional[str] = None,
    days: int = 30
) -> Dict[str, Any]:
    """发现商机处理器"""
    try:
        if industry:
            opps = await opportunity_service.discover_opportunities_by_industry(industry, days)
        elif keywords:
            opps = await opportunity_service.discover_opportunities_from_keywords(keywords, days)
        else:
            # 无参数时使用默认关键词
            opps = await opportunity_service.discover_opportunities_from_keywords(["人工智能", "数字经济"], days)

        result = [
            {
                "id": o.id,
                "title": o.title,
                "type": o.type.value,
                "confidence_score": o.confidence_score,
                "potential_value": o.potential_value,
                "source_type": o.source_type.value,
            }
            for o in opps
        ]

        return {
            "success": True,
            "count": len(result),
            "opportunities": result,
            "message": f"成功发现 {len(result)} 条商机",
        }
    except Exception as e:
        logger.error(f"Failed to discover opportunities: {str(e)}")
        return {"success": False, "error": str(e)}


def _export_opportunity_handler(opp_id: str, format: str = "markdown") -> Dict[str, Any]:
    """导出商机处理器"""
    try:
        result = opportunity_service.export_opportunity_report(opp_id, format)
        return result
    except Exception as e:
        logger.error(f"Failed to export opportunity: {str(e)}")
        return {"success": False, "error": str(e)}


# ============================================================
# Tool 定义：遵循 DeerFlow 2.0 工具规范
# ============================================================

LIST_OPPORTUNITIES_TOOL = {
    "name": "list_opportunities",
    "description": "获取商机列表，支持按状态筛选。返回商机的基本信息包括 ID、标题、类型、置信度、潜在价值等。",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["new", "validated", "expired"],
                "description": "可选，按状态筛选"
            }
        },
        "required": []
    },
    "handler": _list_opportunities_handler,
    "audit_log": True,
}

GET_OPPORTUNITY_TOOL = {
    "name": "get_opportunity",
    "description": "获取单条商机的详细信息，包括来源、风险评估、验证步骤、关联实体等。",
    "input_schema": {
        "type": "object",
        "properties": {
            "opp_id": {
                "type": "string",
                "description": "商机 ID"
            }
        },
        "required": ["opp_id"]
    },
    "handler": _get_opportunity_handler,
    "audit_log": False,
}

DISCOVER_OPPORTUNITIES_TOOL = {
    "name": "discover_opportunities",
    "description": "基于关键词或行业自动发现新商机。通过采集新闻、行业报告等数据源，AI 分析提取商机信号。",
    "input_schema": {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "关键词列表，如 ['人工智能', '智能制造']"
            },
            "industry": {
                "type": "string",
                "description": "行业名称，如 '新能源'"
            },
            "days": {
                "type": "integer",
                "description": "分析最近 N 天的数据",
                "default": 30
            }
        },
        "required": []
    },
    "handler": _discover_opportunities_handler,
    "audit_log": True,
}

EXPORT_OPPORTUNITY_TOOL = {
    "name": "export_opportunity",
    "description": "导出商机报告，支持 Markdown 和 PDF 格式。可用于分享或存档。",
    "input_schema": {
        "type": "object",
        "properties": {
            "opp_id": {
                "type": "string",
                "description": "商机 ID"
            },
            "format": {
                "type": "string",
                "enum": ["markdown", "pdf"],
                "description": "导出格式",
                "default": "markdown"
            }
        },
        "required": ["opp_id"]
    },
    "handler": _export_opportunity_handler,
    "audit_log": True,
}


# ============================================================
# 工具注册表
# ============================================================

OPPORTUNITY_TOOLS = [
    LIST_OPPORTUNITIES_TOOL,
    GET_OPPORTUNITY_TOOL,
    DISCOVER_OPPORTUNITIES_TOOL,
    EXPORT_OPPORTUNITY_TOOL,
]


def get_opportunity_tools() -> List[Dict]:
    """获取所有商机工具"""
    return OPPORTUNITY_TOOLS


def get_tool_by_name(name: str):
    """根据名称获取工具"""
    for tool in OPPORTUNITY_TOOLS:
        if tool["name"] == name:
            return tool
    return None
