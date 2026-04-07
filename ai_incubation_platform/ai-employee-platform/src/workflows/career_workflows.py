"""
职业职业发展工作流

基于 DeerFlow 2.0 的多步工作流编排:
- AutoCareerPlanningWorkflow: 自主职业发展规划工作流
- AutoSkillGapAnalysisWorkflow: 自主技能差距分析工作流
"""
import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==================== 装饰器定义 ====================
def step(order: int = 0):
    """工作流步骤装饰器"""
    def decorator(func):
        func._is_step = True
        func._step_order = order
        return func
    return decorator


def workflow(name: str):
    """工作流类装饰器"""
    def decorator(cls):
        cls._workflow_name = name
        return cls
    return decorator


# ==================== 自主职业发展规划工作流 ====================

@workflow(name="auto_career_planning")
class AutoCareerPlanningWorkflow:
    """
    自主职业发展规划工作流

    流程：
    1. 识别职业目标 - 从员工输入或历史数据提取目标
    2. 分析能力差距 - 对比当前能力与目标要求
    3. 生成发展计划 - 制定阶段性发展计划
    4. 推荐学习资源 - 匹配个性化学习资源
    5. 设置里程碑 - 定义可衡量的里程碑
    6. 定期追踪进度 - 建立进度追踪机制
    """

    def __init__(self):
        self.trace_id = None

    @step(order=1)
    async def identify_goal(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 1: 识别职业目标

        从员工输入或历史数据中提取职业目标
        """
        employee_id = input_data.get("employee_id")
        target_role = input_data.get("target_role")
        timeframe_months = input_data.get("timeframe_months", 12)
        trace_id = input_data.get("trace_id", f"career-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        self.trace_id = trace_id

        logger.info(f"[{trace_id}] Step 1: 识别职业目标 - {employee_id}")

        goal = {
            "employee_id": employee_id,
            "target_role": target_role,
            "timeframe_months": timeframe_months,
            "goal_type": "promotion" if target_role else "exploration",
            "motivation": "寻求职业发展和成长",
            "confidence_level": 0.8
        }

        return {
            "career_goal": goal,
            "employee_id": employee_id,
            "trace_id": trace_id
        }

    @step(order=2)
    async def analyze_gap(self, step1_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: 分析能力差距

        对比员工当前能力与目标职位要求的差距
        """
        if "error" in step1_result:
            return step1_result

        employee_id = step1_result.get("employee_id")
        goal = step1_result.get("career_goal", {})
        target_role = goal.get("target_role")
        trace_id = self.trace_id or "unknown"

        logger.info(f"[{trace_id}] Step 2: 分析能力差距")

        try:
            try:
                from tools.career_tools import analyze_skill_gap_handler
            except ImportError:
                from ..tools.career_tools import analyze_skill_gap_handler

            if target_role:
                gap_analysis = await analyze_skill_gap_handler(
                    employee_id=employee_id,
                    target_role_id=target_role
                )
            else:
                # 如果没有指定目标，进行通用能力评估
                gap_analysis = {
                    "success": True,
                    "analysis": {
                        "skill_gap_summary": {
                            "gap_percentage": 30.0,
                            "missing_count": 3,
                            "mastered_count": 7
                        },
                        "missing_skills": [
                            {"skill": "System Design", "priority": "high"},
                            {"skill": "Leadership", "priority": "medium"},
                            {"skill": "Cloud Architecture", "priority": "medium"}
                        ],
                        "readiness_score": 70.0
                    }
                }

            return {
                **step1_result,
                "gap_analysis": gap_analysis
            }

        except Exception as e:
            logger.error(f"[{trace_id}] Step 2 失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    @step(order=3)
    async def generate_plan(self, step2_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: 生成发展计划

        基于能力差距分析，制定阶段性发展计划
        """
        if "error" in step2_result:
            return step2_result

        goal = step2_result.get("career_goal", {})
        gap_analysis = step2_result.get("gap_analysis", {}).get("analysis", {})
        trace_id = self.trace_id or "unknown"
        timeframe = goal.get("timeframe_months", 12)

        logger.info(f"[{trace_id}] Step 3: 生成发展计划")

        missing_skills = gap_analysis.get("missing_skills", [])
        readiness = gap_analysis.get("readiness_score", 50)

        # 生成阶段性计划
        phases = []
        phase_duration = timeframe // 3  # 平均分为 3 个阶段

        # 阶段 1: 基础能力建设
        phases.append({
            "phase": 1,
            "name": "基础能力建设",
            "duration_months": phase_duration,
            "focus_areas": [s["skill"] for s in missing_skills[:2]] if missing_skills else ["核心技能"],
            "objectives": [
                f"掌握 {missing_skills[0]['skill'] if missing_skills else '核心技能'} 基础知识",
                "完成相关在线课程",
                "参与实践项目"
            ],
            "success_metrics": [
                "完成 1 门相关课程并获得证书",
                "在项目中应用所学技能",
                "获得导师/主管认可"
            ]
        })

        # 阶段 2: 实战能力提升
        phases.append({
            "phase": 2,
            "name": "实战能力提升",
            "duration_months": phase_duration,
            "focus_areas": [s["skill"] for s in missing_skills[2:4]] if len(missing_skills) > 2 else ["项目经验"],
            "objectives": [
                "主导一个中型项目",
                f"提升 {missing_skills[2]['skill'] if len(missing_skills) > 2 else '实战'} 能力",
                "建立项目成果集"
            ],
            "success_metrics": [
                "成功交付 1 个项目",
                "获得项目相关方好评",
                "形成可展示的成果"
            ]
        })

        # 阶段 3: 影响力建设
        phases.append({
            "phase": 3,
            "name": "影响力建设",
            "duration_months": timeframe - 2 * phase_duration,
            "focus_areas": ["影响力", "领导力", "知识分享"],
            "objectives": [
                "在团队/公司内分享知识",
                "辅导初级同事",
                "准备晋升/转岗材料"
            ],
            "success_metrics": [
                "完成至少 1 次技术分享",
                "辅导 1 名同事",
                "准备完整的晋升材料"
            ]
        })

        development_plan = {
            "plan_id": f"plan-{trace_id}",
            "employee_id": step2_result.get("employee_id"),
            "goal": goal,
            "phases": phases,
            "total_duration_months": timeframe,
            "expected_outcome": f"达到 {readiness + 20:.0f}% 的准备度",
            "risk_factors": [
                "时间投入不足",
                "缺乏实践机会",
                "缺少反馈和指导"
            ],
            "mitigation_strategies": [
                "每周固定学习时间",
                "主动争取项目机会",
                "定期与导师沟通"
            ]
        }

        return {
            **step2_result,
            "development_plan": development_plan
        }

    @step(order=4)
    async def recommend_resources(self, step3_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: 推荐学习资源

        为每个发展阶段匹配个性化学习资源
        """
        if "error" in step3_result:
            return step3_result

        employee_id = step3_result.get("employee_id")
        plan = step3_result.get("development_plan", {})
        trace_id = self.trace_id or "unknown"

        logger.info(f"[{trace_id}] Step 4: 推荐学习资源")

        try:
            try:
                from tools.career_tools import recommend_learning_resources_handler
            except ImportError:
                from ..tools.career_tools import recommend_learning_resources_handler

            # 收集所有需要学习的技能
            all_skills = []
            for phase in plan.get("phases", []):
                all_skills.extend(phase.get("focus_areas", []))

            # 为每个技能领域推荐资源
            all_resources = []
            for skill in set(all_skills):
                if skill:
                    resources = await recommend_learning_resources_handler(
                        employee_id=employee_id,
                        skill_area=skill,
                        limit=3
                    )
                    if resources.get("success"):
                        all_resources.extend(resources.get("resources", []))

            # 去重并分类
            categorized_resources = {
                "courses": [r for r in all_resources if r.get("type") == "course"],
                "books": [r for r in all_resources if r.get("type") == "book"],
                "projects": [r for r in all_resources if r.get("type") == "project"],
                "workshops": [r for r in all_resources if r.get("type") == "workshop"]
            }

            return {
                **step3_result,
                "learning_resources": categorized_resources,
                "total_resources": len(all_resources)
            }

        except Exception as e:
            logger.error(f"[{trace_id}] Step 4 失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    @step(order=5)
    async def set_milestones(self, step4_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 5: 设置里程碑

        定义可衡量的里程碑和检查点
        """
        if "error" in step4_result:
            return step4_result

        plan = step4_result.get("development_plan", {})
        trace_id = self.trace_id or "unknown"

        logger.info(f"[{trace_id}] Step 5: 设置里程碑")

        milestones = []
        start_date = date.today()

        cumulative_months = 0
        for i, phase in enumerate(plan.get("phases", [])):
            cumulative_months += phase.get("duration_months", 0)
            milestone_date = start_date + timedelta(days=cumulative_months * 30)

            milestones.append({
                "milestone_id": f"ms-{i+1}-{trace_id}",
                "phase": i + 1,
                "name": f"完成{phase.get('name', f'阶段{i+1}')}",
                "target_date": milestone_date.isoformat(),
                "success_criteria": phase.get("success_metrics", []),
                "check_in_required": True,
                "reviewer": "manager"
            })

        return {
            **step4_result,
            "milestones": milestones,
            "total_milestones": len(milestones)
        }

    @step(order=6)
    async def track_progress(self, step5_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 6: 建立进度追踪机制

        设置定期追踪和反馈机制
        """
        if "error" in step5_result:
            return step5_result

        employee_id = step5_result.get("employee_id")
        milestones = step5_result.get("milestones", [])
        trace_id = self.trace_id or "unknown"

        logger.info(f"[{trace_id}] Step 6: 建立进度追踪机制")

        tracking_config = {
            "employee_id": employee_id,
            "plan_id": f"plan-{trace_id}",
            "check_in_frequency": "biweekly",
            "milestone_reviews": [
                {
                    "milestone_id": m["milestone_id"],
                    "review_type": "formal",
                    "reviewers": ["manager", "mentor"],
                    "evidence_required": True
                }
                for m in milestones
            ],
            "progress_metrics": [
                "课程完成度",
                "项目参与度",
                "技能提升评估",
                "导师/主管反馈"
            ],
            "alert_conditions": [
                {"condition": "milestone_missed", "action": "notify_manager"},
                {"condition": "progress_stalled", "action": "schedule_coaching"},
                {"condition": "goal_achieved", "action": "celebrate_and_update"}
            ],
            "next_check_in": (date.today() + timedelta(weeks=2)).isoformat()
        }

        return {
            **step5_result,
            "tracking_config": tracking_config,
            "workflow_completed": True,
            "completed_at": datetime.now().isoformat()
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行完整工作流"""
        result = input_data.copy()

        steps = [
            self.identify_goal,
            self.analyze_gap,
            self.generate_plan,
            self.recommend_resources,
            self.set_milestones,
            self.track_progress
        ]

        for step_func in steps:
            if result.get("error"):
                break
            try:
                result = await step_func(result)
            except Exception as e:
                result["error"] = str(e)
                break

        return result


# ==================== 自主技能差距分析工作流 ====================

@workflow(name="auto_skill_gap_analysis")
class AutoSkillGapAnalysisWorkflow:
    """
    自主技能差距分析工作流

    流程：
    1. 获取员工技能档案 - 收集当前技能信息
    2. 获取目标职位要求 - 收集目标技能要求
    3. 技能映射对比 - 逐项对比技能差距
    4. 差距优先级排序 - 按重要性和紧急性排序
    5. 生成填补计划 - 制定技能提升计划
    6. 推荐具体行动 - 提供可执行的行动建议
    """

    @step(order=1)
    async def get_employee_profile(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: 获取员工技能档案"""
        employee_id = input_data.get("employee_id")
        trace_id = input_data.get("trace_id", f"gap-{datetime.now().strftime('%Y%m%d%H%M%S')}")

        logger.info(f"[{trace_id}] Step 1: 获取员工技能档案")

        try:
            try:
                from tools.talent_tools import analyze_employee_profile_handler
            except ImportError:
                from ..tools.talent_tools import analyze_employee_profile_handler

            profile = await analyze_employee_profile_handler(
                employee_id=employee_id,
                include_projects=True
            )

            return {
                "employee_profile": profile,
                "employee_id": employee_id,
                "trace_id": trace_id
            }

        except Exception as e:
            logger.error(f"[{trace_id}] Step 1 失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    @step(order=2)
    async def get_target_requirements(self, step1_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: 获取目标职位要求"""
        if "error" in step1_result:
            return step1_result

        target_role_id = step1_result.get("target_role_id")
        trace_id = step1_result.get("trace_id", "unknown")

        logger.info(f"[{trace_id}] Step 2: 获取目标职位要求 - {target_role_id}")

        try:
            try:
                from services.p16_career_development_service import CareerDevelopmentService
            except ImportError:
                from ..services.p16_career_development_service import CareerDevelopmentService

            career_service = CareerDevelopmentService()
            role = career_service.career_path.get_career_role(target_role_id)

            if role:
                requirements = {
                    "role_id": role.id,
                    "role_name": role.name,
                    "role_level": role.level,
                    "required_skills": role.required_skills,
                    "recommended_skills": role.recommended_skills or [],
                    "salary_range": {
                        "min": role.salary_range_min,
                        "max": role.salary_range_max
                    }
                }
            else:
                requirements = {
                    "role_id": target_role_id,
                    "role_name": "Unknown",
                    "required_skills": {},
                    "recommended_skills": []
                }

            return {
                **step1_result,
                "target_requirements": requirements
            }

        except Exception as e:
            logger.error(f"[{trace_id}] Step 2 失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    @step(order=3)
    async def compare_skills(self, step2_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: 技能映射对比"""
        if "error" in step2_result:
            return step2_result

        profile = step2_result.get("employee_profile", {})
        requirements = step2_result.get("target_requirements", {})
        trace_id = step2_result.get("trace_id", "unknown")

        logger.info(f"[{trace_id}] Step 3: 技能映射对比")

        # 获取员工技能
        employee_skills = profile.get("skills", [])
        employee_skill_names = {s.get("name", "").lower() for s in employee_skills}

        # 对比分析
        required_skills = requirements.get("required_skills", {})
        comparison = {
            "mastered": [],
            "partial": [],
            "missing": []
        }

        for skill_name, required_level in required_skills.items():
            if skill_name.lower() in employee_skill_names:
                comparison["mastered"].append({
                    "skill": skill_name,
                    "required_level": required_level,
                    "status": "mastered"
                })
            else:
                comparison["missing"].append({
                    "skill": skill_name,
                    "required_level": required_level,
                    "priority": "critical" if required_level >= 4 else "important"
                })

        # 计算总体匹配度
        total_skills = len(required_skills)
        mastered_count = len(comparison["mastered"])
        gap_percentage = (total_skills - mastered_count) / total_skills * 100 if total_skills > 0 else 0

        return {
            **step2_result,
            "skill_comparison": comparison,
            "gap_summary": {
                "total_required": total_skills,
                "mastered": mastered_count,
                "missing": len(comparison["missing"]),
                "gap_percentage": round(gap_percentage, 1),
                "readiness_score": round(100 - gap_percentage, 1)
            }
        }

    @step(order=4)
    async def prioritize_gaps(self, step3_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: 差距优先级排序"""
        if "error" in step3_result:
            return step3_result

        comparison = step3_result.get("skill_comparison", {})
        trace_id = step3_result.get("trace_id", "unknown")

        logger.info(f"[{trace_id}] Step 4: 差距优先级排序")

        missing_skills = comparison.get("missing", [])

        # 按优先级排序
        critical_gaps = [s for s in missing_skills if s.get("priority") == "critical"]
        important_gaps = [s for s in missing_skills if s.get("priority") == "important"]

        prioritized_gaps = {
            "critical": critical_gaps,
            "important": important_gaps,
            "nice_to_have": comparison.get("partial", [])
        }

        # 生成学习顺序建议
        learning_order = []
        for i, skill in enumerate(critical_gaps + important_gaps):
            learning_order.append({
                "order": i + 1,
                "skill": skill["skill"],
                "priority": skill["priority"],
                "estimated_months": 2 if skill["priority"] == "critical" else 3,
                "prerequisites": [],  # 简化处理
                "rationale": f"{'核心要求，优先学习' if skill['priority'] == 'critical' else '重要补充，后续学习'}"
            })

        return {
            **step3_result,
            "prioritized_gaps": prioritized_gaps,
            "learning_order": learning_order
        }

    @step(order=5)
    async def generate_bridge_plan(self, step4_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 5: 生成填补计划"""
        if "error" in step4_result:
            return step4_result

        learning_order = step4_result.get("learning_order", [])
        gap_summary = step4_result.get("gap_summary", {})
        trace_id = step4_result.get("trace_id", "unknown")

        logger.info(f"[{trace_id}] Step 5: 生成填补计划")

        # 制定填补计划
        bridge_plan = {
            "plan_id": f"bridge-{trace_id}",
            "overall_readiness": gap_summary.get("readiness_score", 0),
            "estimated_total_time_months": sum(item.get("estimated_months", 0) for item in learning_order),
            "phases": [],
            "success_criteria": []
        }

        # 按阶段组织
        current_phase = None
        for item in learning_order[:6]:  # 最多处理前 6 个
            phase_num = (item["order"] - 1) // 2 + 1

            if phase_num != current_phase:
                current_phase = phase_num
                bridge_plan["phases"].append({
                    "phase": phase_num,
                    "name": f"阶段{phase_num}",
                    "skills": [],
                    "estimated_months": 0
                })

            phase = bridge_plan["phases"][-1]
            phase["skills"].append(item["skill"])
            phase["estimated_months"] += item["estimated_months"]

        # 成功标准
        bridge_plan["success_criteria"] = [
            f"掌握 {len(learning_order)} 项关键技能",
            "完成相关项目实践",
            "获得技能认证或主管认可",
            f"准备度达到 80% 以上"
        ]

        return {
            **step4_result,
            "bridge_plan": bridge_plan
        }

    @step(order=6)
    async def recommend_actions(self, step5_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 6: 推荐具体行动"""
        if "error" in step5_result:
            return step5_result

        employee_id = step5_result.get("employee_id")
        bridge_plan = step5_result.get("bridge_plan", {})
        trace_id = step5_result.get("trace_id", "unknown")

        logger.info(f"[{trace_id}] Step 6: 推荐具体行动")

        # 生成具体行动建议
        actions = []
        for i, phase in enumerate(bridge_plan.get("phases", [])):
            for skill in phase.get("skills", []):
                actions.append({
                    "action_id": f"act-{len(actions)+1}-{trace_id}",
                    "phase": i + 1,
                    "skill": skill,
                    "recommended_actions": [
                        f"完成{skill}入门课程",
                        f"阅读{skill}相关书籍",
                        f"参与{skill}相关项目",
                        f"寻找{skill}领域的导师"
                    ],
                    "resources_needed": [
                        {"type": "course", "topic": skill},
                        {"type": "book", "topic": skill},
                        {"type": "project", "topic": skill}
                    ],
                    "time_commitment": "4-6 小时/周",
                    "success_metric": f"能够独立完成{skill}相关任务"
                })

        return {
            **step5_result,
            "recommended_actions": actions,
            "workflow_completed": True,
            "completed_at": datetime.now().isoformat()
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行完整工作流"""
        result = input_data.copy()

        steps = [
            self.get_employee_profile,
            self.get_target_requirements,
            self.compare_skills,
            self.prioritize_gaps,
            self.generate_bridge_plan,
            self.recommend_actions
        ]

        for step_func in steps:
            if result.get("error"):
                break
            try:
                result = await step_func(result)
            except Exception as e:
                result["error"] = str(e)
                break

        return result
