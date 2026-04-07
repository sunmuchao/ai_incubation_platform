"""
人才管理工具集

提供 AI 可调用的核心人才管理工具:
- 员工画像分析
- 机会匹配
- 团队构成分析
- 绩效评估
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio

logger = logging.getLogger(__name__)


# ==================== 工具实现函数 ====================

async def analyze_employee_profile_handler(
    employee_id: str,
    include_projects: bool = True
) -> Dict[str, Any]:
    """
    分析员工能力画像

    Args:
        employee_id: 员工 ID
        include_projects: 是否包含项目历史

    Returns:
        员工画像分析结果
    """
    try:
        try:
            from services.p16_career_development_service import CareerDevelopmentService
            from api.employees_db import get_employee_by_id
        except ImportError:
            from ..services.p16_career_development_service import CareerDevelopmentService
            from ..api.employees_db import get_employee_by_id

        career_service = CareerDevelopmentService()

        # 获取员工基本信息
        # 简化处理，实际应从数据库获取
        employee = {
            "id": employee_id,
            "name": f"Employee_{employee_id[:8]}",
            "current_role": "Software Engineer",
            "department": "Engineering",
            "hire_date": "2023-01-15"
        }

        # 获取员工技能
        skills_data = career_service.employee_skill.list_employee_skills(
            employee_id=employee_id
        )
        skills = [
            {
                "name": s["skill"].name if "skill" in s else "Unknown",
                "level": s["employee_skill"].level.value if "employee_skill" in s else "beginner",
                "years": s["employee_skill"].years_of_experience if "employee_skill" in s else 0
            }
            for s in skills_data
        ]

        # 获取职业发展计划
        plans = career_service.development_plan.list_plans(employee_id=employee_id)

        # 获取绩效历史（模拟）
        performance_history = [
            {"period": "2024-Q4", "score": 4.5, "rating": "Excellent"},
            {"period": "2024-Q3", "score": 4.3, "rating": "Excellent"},
            {"period": "2024-Q2", "score": 4.1, "rating": "Good"}
        ]

        # AI 分析摘要
        profile_summary = {
            "strengths": [],
            "areas_for_improvement": [],
            "career_trajectory": "growing",
            "flight_risk": "low",
            "readiness_for_promotion": 0.7
        }

        if len(skills) >= 5:
            profile_summary["strengths"].append("技能广度优秀")
        if len(plans) > 0:
            profile_summary["strengths"].append("有明确的职业发展计划")

        return {
            "success": True,
            "employee": employee,
            "skills": skills,
            "performance_history": performance_history,
            "development_plans": [p.to_dict() for p in plans] if plans else [],
            "profile_summary": profile_summary,
            "analyzed_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"分析员工画像失败 {employee_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "employee_id": employee_id
        }


async def match_opportunities_handler(
    employee_id: str,
    opportunity_type: str = "all",
    limit: int = 10
) -> Dict[str, Any]:
    """
    匹配人才与机会

    Args:
        employee_id: 员工 ID
        opportunity_type: 机会类型 (transfer/promotion/project/all)
        limit: 最大返回数量

    Returns:
        匹配的机会列表
    """
    try:
        try:
            from services.p16_career_development_service import CareerDevelopmentService
        except ImportError:
            from ..services.p16_career_development_service import CareerDevelopmentService

        career_service = CareerDevelopmentService()

        # 获取员工当前角色和技能
        employee_skills = career_service.employee_skill.list_employee_skills(
            employee_id=employee_id
        )

        # 获取推荐职业路径
        recommendations = career_service.career_path.get_recommendations(
            employee_id=employee_id,
            limit=limit
        )

        opportunities = []

        # 晋升机会
        if opportunity_type in ["promotion", "all"]:
            for rec in recommendations:
                target_role = career_service.career_path.get_career_role(rec.to_role_id)
                if target_role and target_role.level > 5:  # 高级别职位
                    opportunities.append({
                        "type": "promotion",
                        "role_id": rec.to_role_id,
                        "role_name": target_role.name,
                        "match_score": rec.match_score,
                        "readiness": rec.readiness_score,
                        "key_gaps": rec.key_skills_to_develop or [],
                        "salary_range": {
                            "min": target_role.salary_range_min,
                            "max": target_role.salary_range_max
                        }
                    })

        # 转岗机会
        if opportunity_type in ["transfer", "all"]:
            all_roles = career_service.career_path.list_career_roles(limit=20)
            for role in all_roles:
                if role.path_type != "management":  # 非管理路线的转岗
                    opportunities.append({
                        "type": "transfer",
                        "role_id": role.id,
                        "role_name": role.name,
                        "path_type": role.path_type,
                        "match_score": 0.75,  # 简化处理
                        "skills_match": len(employee_skills)
                    })

        # 项目机会（模拟）
        if opportunity_type in ["project", "all"]:
            projects = [
                {
                    "id": "proj_001",
                    "name": "AI 平台重构",
                    "required_skills": ["Python", "Architecture"],
                    "duration_months": 6,
                    "match_score": 0.85
                },
                {
                    "id": "proj_002",
                    "name": "数据中台建设",
                    "required_skills": ["Data Engineering", "SQL"],
                    "duration_months": 4,
                    "match_score": 0.72
                }
            ]
            for proj in projects:
                opportunities.append({
                    "type": "project",
                    "project_id": proj["id"],
                    "project_name": proj["name"],
                    "duration_months": proj["duration_months"],
                    "match_score": proj["match_score"]
                })

        # 按匹配度排序
        opportunities.sort(key=lambda x: x.get("match_score", 0), reverse=True)

        return {
            "success": True,
            "employee_id": employee_id,
            "opportunities": opportunities[:limit],
            "total_found": len(opportunities),
            "opportunity_type_filter": opportunity_type,
            "matched_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"匹配机会失败 {employee_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "employee_id": employee_id
        }


async def analyze_team_composition_handler(
    department_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    分析团队构成并提出优化建议

    Args:
        department_id: 部门 ID（可选）

    Returns:
        团队构成分析报告
    """
    try:
        # 模拟团队分析数据
        analysis = {
            "department_id": department_id or "all",
            "team_size": 25,
            "composition": {
                "by_level": {
                    "junior": 8,
                    "mid": 10,
                    "senior": 5,
                    "lead": 2
                },
                "by_skill_category": {
                    "engineering": 15,
                    "product": 5,
                    "design": 3,
                    "data": 2
                },
                "by_tenure": {
                    "0-1_year": 6,
                    "1-3_years": 10,
                    "3-5_years": 6,
                    "5+_years": 3
                }
            },
            "diversity_metrics": {
                "gender_ratio": "55:45",
                "age_distribution": "25-40 avg",
                "background_diversity": "high"
            },
            "skill_gaps": [
                {"skill": "Machine Learning", "gap_severity": "high", "needed_count": 3},
                {"skill": "Cloud Architecture", "gap_severity": "medium", "needed_count": 2}
            ],
            "recommendations": [
                {
                    "type": "hiring",
                    "priority": "high",
                    "action": "招聘 2 名机器学习工程师",
                    "rationale": "支持 AI 战略发展"
                },
                {
                    "type": "training",
                    "priority": "medium",
                    "action": "组织云架构培训",
                    "rationale": "提升团队技术深度"
                },
                {
                    "type": "retention",
                    "priority": "medium",
                    "action": "关注 1-3 年经验员工的职业发展",
                    "rationale": "该群体占比最高，流失风险较大"
                }
            ],
            "health_score": 78,
            "analyzed_at": datetime.now().isoformat()
        }

        return {
            "success": True,
            "analysis": analysis
        }

    except Exception as e:
        logger.error(f"团队分析失败：{e}")
        return {
            "success": False,
            "error": str(e)
        }


async def track_performance_handler(
    employee_id: str,
    period: str = "quarterly"
) -> Dict[str, Any]:
    """
    追踪绩效并提供改进建议

    Args:
        employee_id: 员工 ID
        period: 评估周期

    Returns:
        绩效评估结果
    """
    try:
        # 模拟绩效评估数据
        performance_data = {
            "employee_id": employee_id,
            "period": period,
            "overall_score": 4.5,
            "rating": "Excellent",
            "dimensions": {
                "technical_skills": {"score": 4.7, "trend": "up"},
                "communication": {"score": 4.2, "trend": "stable"},
                "teamwork": {"score": 4.6, "trend": "up"},
                "leadership": {"score": 4.0, "trend": "up"},
                "problem_solving": {"score": 4.8, "trend": "stable"}
            },
            "achievements": [
                "主导完成了 AI 平台重构项目",
                "提升了系统性能 30%",
                "辅导了 2 名初级工程师"
            ],
            "areas_for_improvement": [
                "可以更多地参与跨团队协作",
                "建议提升公开演讲能力"
            ],
            "ai_recommendations": [
                {
                    "category": "skill_development",
                    "action": "参加高级系统设计培训",
                    "expected_impact": "提升架构设计能力，为晋升做准备",
                    "priority": "high"
                },
                {
                    "category": "visibility",
                    "action": "在公司技术分享会上做一次演讲",
                    "expected_impact": "提升影响力和沟通能力",
                    "priority": "medium"
                }
            ],
            "promotion_readiness": {
                "ready": True,
                "confidence": 0.75,
                "next_level": "Senior Engineer",
                "remaining_gaps": ["系统设计深度", "跨团队影响力"]
            },
            "evaluated_at": datetime.now().isoformat()
        }

        return {
            "success": True,
            "performance": performance_data
        }

    except Exception as e:
        logger.error(f"绩效评估失败 {employee_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "employee_id": employee_id
        }


# ==================== 工具注册表 ====================

TOOLS_REGISTRY = {
    "analyze_employee_profile": {
        "name": "analyze_employee_profile",
        "description": "分析员工能力画像，包括技能、绩效历史、职业发展计划等",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "员工唯一标识符"
                },
                "include_projects": {
                    "type": "boolean",
                    "description": "是否包含项目历史",
                    "default": True
                }
            },
            "required": ["employee_id"]
        },
        "handler": analyze_employee_profile_handler
    },
    "match_opportunities": {
        "name": "match_opportunities",
        "description": "为员工匹配发展机会，包括晋升、转岗、项目等",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "员工唯一标识符"
                },
                "opportunity_type": {
                    "type": "string",
                    "description": "机会类型",
                    "enum": ["transfer", "promotion", "project", "all"],
                    "default": "all"
                },
                "limit": {
                    "type": "integer",
                    "description": "最大返回数量",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                }
            },
            "required": ["employee_id"]
        },
        "handler": match_opportunities_handler
    },
    "analyze_team_composition": {
        "name": "analyze_team_composition",
        "description": "分析团队构成，识别技能缺口并提出优化建议",
        "input_schema": {
            "type": "object",
            "properties": {
                "department_id": {
                    "type": "string",
                    "description": "部门 ID，不传则分析全公司"
                }
            }
        },
        "handler": analyze_team_composition_handler
    },
    "track_performance": {
        "name": "track_performance",
        "description": "追踪员工绩效并提供 AI 改进建议",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "员工唯一标识符"
                },
                "period": {
                    "type": "string",
                    "description": "评估周期",
                    "enum": ["weekly", "monthly", "quarterly", "yearly"],
                    "default": "quarterly"
                }
            },
            "required": ["employee_id"]
        },
        "handler": track_performance_handler
    }
}
