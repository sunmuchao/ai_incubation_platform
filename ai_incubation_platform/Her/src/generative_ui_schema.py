"""
Generative UI Schema - 前后端共享映射定义

这个文件定义了所有 Generative UI 组件的映射关系。
前端和后端必须保持同步，新增组件时必须在此注册。

使用方式：
- 后端：from generative_ui_schema import GENERATIVE_UI_SCHEMA
- 前端：参考 frontend/src/types/generativeUI.ts

维护规则：
1. 新增组件必须在此注册
2. 必填 props 必须明确标注
3. 前端对应的 generativeCard 值必须与 frontend_card 一致
"""

from typing import Dict, List, Any, TypedDict, Optional


class ComponentSchema(TypedDict):
    """组件 Schema 定义"""
    backend_type: str  # 后端返回的 component_type
    frontend_card: str  # 前端对应的 generativeCard 值
    required_props: List[str]  # 必填 props
    description: str  # 组件描述


# ==================== Generative UI Schema ====================

GENERATIVE_UI_SCHEMA: Dict[str, ComponentSchema] = {
    # ===== 匹配相关 =====
    "MatchCardList": {
        "backend_type": "MatchCardList",
        "frontend_card": "match",
        "required_props": ["matches"],
        "description": "匹配结果列表，展示候选人卡片",
    },
    "DailyRecommendCard": {
        "backend_type": "DailyRecommendCard",
        "frontend_card": "match",
        "required_props": ["matches", "is_daily"],
        "description": "每日推荐卡片",
    },

    # ===== 信息收集 =====
    "ProfileQuestionCard": {
        "backend_type": "ProfileQuestionCard",
        "frontend_card": "profile_question",
        "required_props": ["question", "question_type", "options", "dimension"],
        "description": "用户画像问题卡片",
    },
    "QuickStartCard": {
        "backend_type": "QuickStartCard",
        "frontend_card": "quick_start",
        "required_props": ["question", "question_type", "options", "dimension"],
        "description": "快速入门问题卡片（本地处理，不调用后端）",
    },

    # ===== 预沟通相关 =====
    "PreCommunicationPanel": {
        "backend_type": "PreCommunicationPanel",
        "frontend_card": "precommunication",
        "required_props": ["sessions"],
        "description": "AI 预沟通会话列表",
    },
    "PreCommunicationDialog": {
        "backend_type": "PreCommunicationDialog",
        "frontend_card": "precommunication-dialog",
        "required_props": ["messages"],
        "description": "AI 预沟通对话历史",
    },

    # ===== 约会相关 =====
    "DatePlanCard": {
        "backend_type": "DatePlanCard",
        "frontend_card": "feature",
        "required_props": ["plans"],
        "description": "约会方案卡片",
    },
    "DateSuggestionCard": {
        "backend_type": "DateSuggestionCard",
        "frontend_card": "feature",
        "required_props": ["suggestions"],
        "description": "约会建议卡片",
    },

    # ===== 分析相关 =====
    "CompatibilityChart": {
        "backend_type": "CompatibilityChart",
        "frontend_card": "analysis",
        "required_props": ["overall_score", "dimensions"],
        "description": "兼容性分析图表",
    },
    "RelationshipHealthCard": {
        "backend_type": "RelationshipHealthCard",
        "frontend_card": "analysis",
        "required_props": ["health_score"],
        "description": "关系健康度卡片",
    },
    "RelationshipReportCard": {
        "backend_type": "RelationshipReportCard",
        "frontend_card": "analysis",
        "required_props": ["report_data"],
        "description": "关系分析报告",
    },

    # ===== 功能展示 =====
    "CapabilityCard": {
        "backend_type": "CapabilityCard",
        "frontend_card": "feature",
        "required_props": ["intro", "features"],
        "description": "能力介绍卡片",
    },
    "TopicsCard": {
        "backend_type": "TopicsCard",
        "frontend_card": "feature",
        "required_props": ["topics"],
        "description": "话题推荐卡片",
    },
    "IcebreakerCard": {
        "backend_type": "IcebreakerCard",
        "frontend_card": "feature",
        "required_props": ["icebreakers"],
        "description": "破冰建议卡片",
    },

    # ===== 简单响应 =====
    "SimpleResponse": {
        "backend_type": "SimpleResponse",
        "frontend_card": None,  # 不渲染卡片，只显示文本
        "required_props": [],
        "description": "简单文本响应",
    },
    "AIResponseCard": {
        "backend_type": "AIResponseCard",
        "frontend_card": None,
        "required_props": [],
        "description": "AI 响应卡片（纯文本）",
    },

    # ===== 学习结果确认 =====
    "LearningConfirmationCard": {
        "backend_type": "LearningConfirmationCard",
        "frontend_card": "learning_confirmation",
        "required_props": ["insights"],
        "description": "AI 学习结果确认卡片（用户确认是否更新画像）",
    },
}


# ==================== 辅助函数 ====================

def get_frontend_card(backend_type: str) -> Optional[str]:
    """
    根据后端 component_type 获取前端 generativeCard 值

    Args:
        backend_type: 后端返回的 component_type

    Returns:
        前端对应的 generativeCard 值，如果没有则返回 None
    """
    schema = GENERATIVE_UI_SCHEMA.get(backend_type)
    return schema.get("frontend_card") if schema else None


def validate_props(backend_type: str, props: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    验证 props 是否满足必填要求

    Args:
        backend_type: 后端返回的 component_type
        props: 实际传入的 props

    Returns:
        (是否有效, 缺失的 props 列表)
    """
    schema = GENERATIVE_UI_SCHEMA.get(backend_type)
    if not schema:
        return False, [f"未知的 component_type: {backend_type}"]

    required = schema.get("required_props", [])
    missing = [p for p in required if p not in props]

    return len(missing) == 0, missing


def list_all_components() -> List[Dict[str, Any]]:
    """
    列出所有已注册的组件

    Returns:
        组件信息列表
    """
    return [
        {
            "backend_type": schema["backend_type"],
            "frontend_card": schema["frontend_card"],
            "required_props": schema["required_props"],
            "description": schema["description"],
        }
        for schema in GENERATIVE_UI_SCHEMA.values()
    ]


# ==================== 导出 ====================

__all__ = [
    "GENERATIVE_UI_SCHEMA",
    "ComponentSchema",
    "get_frontend_card",
    "validate_props",
    "list_all_components",
]