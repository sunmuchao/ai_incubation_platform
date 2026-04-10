"""
Agent Skills 包

提供所有 Agent Skill 的实现和注册。
"""
from typing import List
from agent.skills.base import BaseSkill
from agent.skills.registry import SkillRegistry, get_skill_registry, initialize_default_skills
from agent.skills.matchmaking_skill import MatchmakingSkill, get_matchmaking_skill
from agent.skills.precommunication_skill import PreCommunicationSkill, get_precommunication_skill
from agent.skills.omniscient_insight_skill import OmniscientInsightSkill, get_omniscient_insight_skill
from agent.skills.relationship_coach_skill import RelationshipCoachSkill, get_relationship_coach_skill
from agent.skills.date_planning_skill import DatePlanningSkill, get_date_planning_skill
from agent.skills.bill_analysis_skill import BillAnalysisSkill, get_bill_analysis_skill
# 注：geo_location, gift_ordering 已删除，改用 REST API

__all__ = [
    # 基类
    "BaseSkill",

    # 注册表
    "SkillRegistry",
    "get_skill_registry",
    "initialize_default_skills",

    # P0 Skills - 核心 AI Native 能力
    "MatchmakingSkill",
    "get_matchmaking_skill",
    "PreCommunicationSkill",
    "get_precommunication_skill",
    "OmniscientInsightSkill",
    "get_omniscient_insight_skill",

    # P1 Skills - 增强 AI 自主性
    "RelationshipCoachSkill",
    "get_relationship_coach_skill",
    "DatePlanningSkill",
    "get_date_planning_skill",

    # P19 Skills - 外部服务集成
    "BillAnalysisSkill",
    "get_bill_analysis_skill",
]

# 技能元数据
SKILL_METADATA = {
    "matchmaking_assistant": {
        "name": "匹配助手",
        "priority": "P0",
        "category": "core",
        "description": "AI 红娘助手，帮助用户找到合适的匹配对象"
    },
    "pre_communication": {
        "name": "AI 预沟通",
        "priority": "P0",
        "category": "core",
        "description": "AI 替身预沟通服务"
    },
    "omniscient_insight": {
        "name": "AI 感知",
        "priority": "P0",
        "category": "core",
        "description": "AI 全知感知系统"
    },
    "relationship_coach": {
        "name": "关系教练",
        "priority": "P1",
        "category": "relationship",
        "description": "关系维护教练"
    },
    "date_planning": {
        "name": "约会策划",
        "priority": "P1",
        "category": "dating",
        "description": "AI 约会策划师"
    },
    "bill_analysis": {
        "name": "账单分析",
        "priority": "P19",
        "category": "external_service",
        "description": "基于消费水平的真实匹配服务"
    }
    # 注：geo_location, gift_ordering 已删除，改用 REST API
}


def get_skill_info(skill_name: str) -> dict:
    """
    获取 Skill 详细信息

    Args:
        skill_name: Skill 名称

    Returns:
        Skill 信息字典
    """
    metadata = SKILL_METADATA.get(skill_name, {})
    registry = get_skill_registry()
    skill_metadata = registry.get_metadata(skill_name) or {}

    return {
        **metadata,
        **skill_metadata,
        "available": skill_name in registry._skills
    }


def list_all_skills() -> List[dict]:
    """
    列出所有 Skill 信息

    Returns:
        Skill 信息列表
    """
    registry = get_skill_registry()
    skills = registry.list_skills()

    result = []
    for skill in skills:
        extra_info = SKILL_METADATA.get(skill["name"], {})
        result.append({
            **skill,
            **extra_info
        })

    return result
