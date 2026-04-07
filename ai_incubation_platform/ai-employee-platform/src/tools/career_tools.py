"""
职业发展工具集

提供 AI 可调用的职业发展相关工具:
- 职业路径规划
- 技能差距分析
- 学习资源推荐
- 导师匹配
"""
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional
import asyncio

logger = logging.getLogger(__name__)


# ==================== 工具实现函数 ====================

async def plan_career_path_handler(
    employee_id: str,
    target_role: Optional[str] = None,
    timeframe_months: int = 12
) -> Dict[str, Any]:
    """
    生成职业发展规划

    Args:
        employee_id: 员工 ID
        target_role: 目标职位（可选，不传则 AI 自动推荐）
        timeframe_months: 规划时间范围（月）

    Returns:
        职业发展规划
    """
    try:
        try:
            from services.p16_career_development_service import CareerDevelopmentService
        except ImportError:
            from ..services.p16_career_development_service import CareerDevelopmentService

        career_service = CareerDevelopmentService()

        # 获取员工当前技能
        employee_skills = career_service.employee_skill.list_employee_skills(
            employee_id=employee_id
        )

        # 获取职业推荐
        if target_role:
            # 如果指定了目标职位，获取该职位信息
            target_role_obj = career_service.career_path.get_career_role(target_role)
            recommendations = []
        else:
            # AI 自动推荐
            recommendations = career_service.career_path.get_recommendations(
                employee_id=employee_id,
                limit=3
            )

        # 生成发展规划
        plan = {
            "employee_id": employee_id,
            "current_state": {
                "skills_count": len(employee_skills),
                "top_skills": [
                    {
                        "name": s["skill"].name if "skill" in s else "Unknown",
                        "level": s["employee_skill"].level.value
                    }
                    for s in employee_skills[:5]
                ]
            },
            "target_state": None,
            "development_phases": [],
            "recommended_actions": [],
            "timeline": {
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "target_date": datetime.now().strftime("%Y-%m-%d"),
                "duration_months": timeframe_months
            }
        }

        if recommendations:
            rec = recommendations[0]
            target_role_obj = career_service.career_path.get_career_role(rec.to_role_id)
            if target_role_obj:
                plan["target_state"] = {
                    "role_id": rec.to_role_id,
                    "role_name": target_role_obj.name,
                    "role_level": target_role_obj.level,
                    "required_skills": target_role_obj.required_skills,
                    "salary_range": {
                        "min": target_role_obj.salary_range_min,
                        "max": target_role_obj.salary_range_max
                    },
                    "match_score": rec.match_score,
                    "readiness": rec.readiness_score
                }

                # 生成发展阶段
                gap_skills = rec.key_skills_to_develop or []
                plan["development_phases"] = [
                    {
                        "phase": 1,
                        "name": "基础能力建设",
                        "duration_months": 3,
                        "focus_areas": gap_skills[:2] if gap_skills else ["专业技能深化"],
                        "milestones": [
                            f"掌握 {gap_skills[0]} 基础" if gap_skills else "完成核心技能学习",
                            "完成 2 个相关项目实践"
                        ]
                    },
                    {
                        "phase": 2,
                        "name": "实战能力提升",
                        "duration_months": 4,
                        "focus_areas": gap_skills[2:4] if len(gap_skills) > 2 else ["项目经验积累"],
                        "milestones": [
                            f"独立完成 {gap_skills[2]} 相关项目" if len(gap_skills) > 2 else "主导一个中型项目",
                            "获得相关认证"
                        ]
                    },
                    {
                        "phase": 3,
                        "name": "影响力建设",
                        "duration_months": 5,
                        "focus_areas": ["团队协作", "知识分享", "领导力"],
                        "milestones": [
                            "在团队内做一次技术分享",
                            "辅导 1 名初级同事",
                            "准备晋升材料"
                        ]
                    }
                ]

        plan["recommended_actions"] = [
            {
                "action": "报名参加 Python 高级培训",
                "category": "learning",
                "priority": "high",
                "estimated_hours": 40,
                "resources": [
                    {"type": "course", "name": "Advanced Python Programming", "platform": "Coursera"},
                    {"type": "book", "name": "Fluent Python", "author": "Luciano Ramalho"}
                ]
            },
            {
                "action": "参与开源项目贡献",
                "category": "practice",
                "priority": "medium",
                "estimated_hours": 20
            },
            {
                "action": "寻找导师指导",
                "category": "mentorship",
                "priority": "medium",
                "estimated_hours": 2
            }
        ]

        return {
            "success": True,
            "plan": plan,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"职业规划失败 {employee_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "employee_id": employee_id
        }


async def analyze_skill_gap_handler(
    employee_id: str,
    target_role_id: str
) -> Dict[str, Any]:
    """
    分析技能差距

    Args:
        employee_id: 员工 ID
        target_role_id: 目标职位 ID

    Returns:
        技能差距分析结果
    """
    try:
        try:
            from services.p16_career_development_service import CareerDevelopmentService
        except ImportError:
            from ..services.p16_career_development_service import CareerDevelopmentService

        career_service = CareerDevelopmentService()

        # 获取员工技能
        employee_skills = career_service.employee_skill.list_employee_skills(
            employee_id=employee_id
        )
        employee_skill_names = {
            s["skill"].name.lower() if "skill" in s else ""
            for s in employee_skills
        }

        # 获取目标职位要求
        target_role = career_service.career_path.get_career_role(target_role_id)
        if not target_role:
            return {
                "success": False,
                "error": f"目标职位不存在：{target_role_id}"
            }

        required_skills = target_role.required_skills
        recommended_skills = target_role.recommended_skills or []

        # 分析差距
        missing_skills = []
        partial_skills = []
        mastered_skills = []

        for skill_name, required_level in required_skills.items():
            if skill_name.lower() in employee_skill_names:
                mastered_skills.append({
                    "skill": skill_name,
                    "required_level": required_level,
                    "status": "mastered"
                })
            else:
                missing_skills.append({
                    "skill": skill_name,
                    "required_level": required_level,
                    "priority": "high" if required_level >= 4 else "medium"
                })

        # 计算总体差距
        total_required = len(required_skills)
        gap_percentage = len(missing_skills) / total_required if total_required > 0 else 0

        # 生成学习建议
        learning_recommendations = []
        for skill in missing_skills:
            learning_recommendations.append({
                "skill": skill["skill"],
                "suggested_actions": [
                    f"完成 {skill['skill']} 入门课程",
                    f"参与相关项目实践",
                    f"寻找该领域的导师指导"
                ],
                "estimated_time_months": 2 if skill["priority"] == "high" else 3,
                "resources": [
                    {"type": "online_course", "topic": skill["skill"]},
                    {"type": "book", "topic": skill["skill"]},
                    {"type": "project", "topic": skill["skill"]}
                ]
            })

        return {
            "success": True,
            "analysis": {
                "employee_id": employee_id,
                "target_role": {
                    "id": target_role_id,
                    "name": target_role.name,
                    "level": target_role.level
                },
                "skill_gap_summary": {
                    "total_required_skills": total_required,
                    "mastered_count": len(mastered_skills),
                    "missing_count": len(missing_skills),
                    "gap_percentage": round(gap_percentage * 100, 1)
                },
                "missing_skills": missing_skills,
                "mastered_skills": mastered_skills,
                "learning_recommendations": learning_recommendations[:5],
                "readiness_score": round((1 - gap_percentage) * 100, 1),
                "estimated_preparation_months": len(missing_skills) * 2
            },
            "analyzed_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"技能差距分析失败：{e}")
        return {
            "success": False,
            "error": str(e),
            "employee_id": employee_id,
            "target_role_id": target_role_id
        }


async def recommend_learning_resources_handler(
    employee_id: str,
    skill_area: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    推荐学习资源

    Args:
        employee_id: 员工 ID
        skill_area: 技能领域（可选）
        limit: 最大返回数量

    Returns:
        学习资源推荐列表
    """
    try:
        # 模拟学习资源推荐
        resources = [
            {
                "id": "res_001",
                "title": "Advanced Python Programming",
                "type": "course",
                "platform": "Coursera",
                "duration_hours": 40,
                "difficulty": "advanced",
                "skills_covered": ["Python", "Software Design", "Architecture"],
                "rating": 4.8,
                "url": "https://coursera.org/...",
                "match_reason": "基于你的 Python 技能提升需求"
            },
            {
                "id": "res_002",
                "title": "System Design Interview",
                "type": "book",
                "author": "Alex Xu",
                "difficulty": "intermediate",
                "skills_covered": ["System Design", "Architecture"],
                "rating": 4.7,
                "match_reason": "为晋升高级工程师做准备"
            },
            {
                "id": "res_003",
                "title": "Machine Learning Specialization",
                "type": "course",
                "platform": "edX",
                "duration_hours": 80,
                "difficulty": "intermediate",
                "skills_covered": ["Machine Learning", "Python", "Data Science"],
                "rating": 4.6,
                "match_reason": "扩展 AI/ML 技能栈"
            },
            {
                "id": "res_004",
                "title": "Leadership for Engineers",
                "type": "workshop",
                "provider": "Internal",
                "duration_hours": 16,
                "difficulty": "beginner",
                "skills_covered": ["Leadership", "Communication"],
                "rating": 4.5,
                "match_reason": "提升软技能，为管理路线做准备"
            }
        ]

        # 按匹配度排序
        if skill_area:
            resources = [r for r in resources if skill_area.lower() in " ".join(r["skills_covered"]).lower()]

        return {
            "success": True,
            "employee_id": employee_id,
            "resources": resources[:limit],
            "total_found": len(resources),
            "filter_applied": skill_area,
            "recommended_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"学习资源推荐失败：{e}")
        return {
            "success": False,
            "error": str(e)
        }


async def match_mentor_handler(
    employee_id: str,
    development_goals: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    匹配导师

    Args:
        employee_id: 员工 ID（学员）
        development_goals: 发展目标列表

    Returns:
        导师匹配结果
    """
    try:
        try:
            from services.p16_career_development_service import CareerDevelopmentService
        except ImportError:
            from ..services.p16_career_development_service import CareerDevelopmentService

        career_service = CareerDevelopmentService()

        # 获取学员档案（如果不存在则创建）
        mentee_profile = career_service.mentorship.get_mentee_by_employee(employee_id)
        if not mentee_profile:
            # 自动创建学员档案
            mentee_profile = career_service.mentorship.create_mentee_profile(
                employee_id=employee_id,
                development_goals=development_goals,
                preferred_mentor_style=None
            )

        # 自动匹配导师
        matches = career_service.mentorship.auto_match(
            mentee_id=employee_id,
            limit=3
        )

        mentor_results = []
        for match in matches:
            mentor = match.get("mentor")
            if mentor:
                mentor_results.append({
                    "mentor_id": mentor.employee_id,
                    "mentor_name": f"Mentor_{mentor.employee_id[:8]}",
                    "areas_of_expertise": mentor.areas_of_expertise,
                    "mentoring_style": mentor.mentoring_style,
                    "match_score": match.get("score", 0),
                    "match_reason": match.get("reason", ""),
                    "availability": "available" if mentor.mentoring_capacity > 0 else "busy"
                })

        return {
            "success": True,
            "employee_id": employee_id,
            "mentee_profile": mentee_profile.to_dict() if mentee_profile else None,
            "mentor_matches": mentor_results,
            "total_matches": len(mentor_results),
            "matched_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"导师匹配失败：{e}")
        return {
            "success": False,
            "error": str(e),
            "employee_id": employee_id
        }


async def create_development_plan_handler(
    employee_id: str,
    plan_name: str,
    target_role_id: Optional[str] = None,
    timeframe_months: int = 12
) -> Dict[str, Any]:
    """
    创建发展计划

    Args:
        employee_id: 员工 ID
        plan_name: 计划名称
        target_role_id: 目标职位 ID
        timeframe_months: 时间范围（月）

    Returns:
        创建的发展计划
    """
    try:
        try:
            from services.p16_career_development_service import CareerDevelopmentService
            from models.p16_models import DevelopmentPlanStatus
        except ImportError:
            from ..services.p16_career_development_service import CareerDevelopmentService
            from ..models.p16_models import DevelopmentPlanStatus

        career_service = CareerDevelopmentService()

        # 计算目标日期
        start_date = date.today()
        from datetime import timedelta
        target_date = start_date + timedelta(days=timeframe_months * 30)

        # 创建发展计划
        plan = career_service.development_plan.create_plan(
            employee_id=employee_id,
            plan_name=plan_name,
            status=DevelopmentPlanStatus.active,
            target_role_id=target_role_id,
            start_date=start_date,
            target_completion_date=target_date,
            manager_id=None,
            mentor_id=None,
            notes=f"AI 生成的职业发展计划，时间范围：{timeframe_months}个月"
        )

        return {
            "success": True,
            "plan": plan.to_dict(),
            "created_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"创建发展计划失败：{e}")
        return {
            "success": False,
            "error": str(e),
            "employee_id": employee_id
        }


# ==================== 工具注册表 ====================

TOOLS_REGISTRY = {
    "plan_career_path": {
        "name": "plan_career_path",
        "description": "为员工生成职业发展规划，包括发展阶段、里程碑和推荐行动",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "员工唯一标识符"
                },
                "target_role": {
                    "type": "string",
                    "description": "目标职位 ID，不传则 AI 自动推荐"
                },
                "timeframe_months": {
                    "type": "integer",
                    "description": "规划时间范围（月）",
                    "default": 12,
                    "minimum": 3,
                    "maximum": 36
                }
            },
            "required": ["employee_id"]
        },
        "handler": plan_career_path_handler
    },
    "analyze_skill_gap": {
        "name": "analyze_skill_gap",
        "description": "分析员工当前技能与目标职位要求的差距",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "员工唯一标识符"
                },
                "target_role_id": {
                    "type": "string",
                    "description": "目标职位 ID"
                }
            },
            "required": ["employee_id", "target_role_id"]
        },
        "handler": analyze_skill_gap_handler
    },
    "recommend_learning_resources": {
        "name": "recommend_learning_resources",
        "description": "根据员工发展需求推荐学习资源（课程、书籍、工作坊等）",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "员工唯一标识符"
                },
                "skill_area": {
                    "type": "string",
                    "description": "技能领域，如 'Python', 'Leadership' 等"
                },
                "limit": {
                    "type": "integer",
                    "description": "最大返回数量",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 20
                }
            },
            "required": ["employee_id"]
        },
        "handler": recommend_learning_resources_handler
    },
    "match_mentor": {
        "name": "match_mentor",
        "description": "为员工匹配适合的导师",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "员工唯一标识符（学员）"
                },
                "development_goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "发展目标列表"
                }
            },
            "required": ["employee_id"]
        },
        "handler": match_mentor_handler
    },
    "create_development_plan": {
        "name": "create_development_plan",
        "description": "为员工创建正式的发展计划记录",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "员工唯一标识符"
                },
                "plan_name": {
                    "type": "string",
                    "description": "计划名称"
                },
                "target_role_id": {
                    "type": "string",
                    "description": "目标职位 ID"
                },
                "timeframe_months": {
                    "type": "integer",
                    "description": "时间范围（月）",
                    "default": 12
                }
            },
            "required": ["employee_id", "plan_name"]
        },
        "handler": create_development_plan_handler
    }
}
