"""
人才管理工作流

基于 DeerFlow 2.0 的多步工作流编排:
- AutoTalentMatchWorkflow: 自主人才匹配工作流
- AutoPerformanceReviewWorkflow: 自主绩效评估工作流
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==================== 装饰器导入 ====================
# 使用本地定义的装饰器，避免循环依赖
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


# ==================== 自主人才匹配工作流 ====================

@workflow(name="auto_talent_match")
class AutoTalentMatchWorkflow:
    """
    自主人才匹配工作流

    流程：
    1. 分析员工画像 - 获取员工技能、绩效、发展偏好
    2. 扫描可用机会 - 搜索内部转岗/晋升/项目机会
    3. 匹配度计算 - 计算员工与各机会的匹配分数
    4. 生成推荐 - 生成 Top N 推荐列表及理由
    5. 发送通知 - 向员工推送匹配结果
    6. 追踪反馈 - 记录员工对推荐的反馈
    """

    def __init__(self):
        self.trace_id = None

    @step(order=1)
    async def analyze_employee(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 1: 分析员工画像

        收集员工的技能、绩效历史、发展偏好等信息
        """
        employee_id = input_data.get("employee_id")
        trace_id = input_data.get("trace_id", f"match-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        self.trace_id = trace_id

        logger.info(f"[{trace_id}] Step 1: 分析员工画像 - {employee_id}")

        try:
            try:
                from tools.talent_tools import analyze_employee_profile_handler
            except ImportError:
                from ..tools.talent_tools import analyze_employee_profile_handler

            profile_result = await analyze_employee_profile_handler(
                employee_id=employee_id,
                include_projects=True
            )

            if not profile_result.get("success"):
                return {"error": "Failed to analyze employee profile", "trace_id": trace_id}

            return {
                "employee_profile": profile_result,
                "employee_id": employee_id
            }

        except Exception as e:
            logger.error(f"[{trace_id}] Step 1 失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    @step(order=2)
    async def scan_opportunities(self, step1_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: 扫描可用机会

        搜索内部转岗、晋升、项目等机会
        """
        if "error" in step1_result:
            return step1_result

        employee_id = step1_result.get("employee_id")
        profile = step1_result.get("employee_profile", {})
        trace_id = self.trace_id or "unknown"

        logger.info(f"[{trace_id}] Step 2: 扫描可用机会")

        try:
            try:
                from tools.talent_tools import match_opportunities_handler
            except ImportError:
                from ..tools.talent_tools import match_opportunities_handler

            # 扫描所有类型的机会
            opportunities_result = await match_opportunities_handler(
                employee_id=employee_id,
                opportunity_type="all",
                limit=20
            )

            return {
                **step1_result,
                "opportunities": opportunities_result,
                "employee_profile": profile
            }

        except Exception as e:
            logger.error(f"[{trace_id}] Step 2 失败：{e}")
            return {"error": str(e), "trace_id": trace_id}

    @step(order=3)
    async def calculate_match(self, step2_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: 匹配度计算

        基于技能匹配度、绩效表现、文化适配度等计算综合分数
        """
        if "error" in step2_result:
            return step2_result

        opportunities = step2_result.get("opportunities", {}).get("opportunities", [])
        profile = step2_result.get("employee_profile", {})
        trace_id = self.trace_id or "unknown"

        logger.info(f"[{trace_id}] Step 3: 计算匹配度 - {len(opportunities)} 个机会")

        # 重新排序，按匹配度排序
        opportunities.sort(key=lambda x: x.get("match_score", 0), reverse=True)

        # 为每个机会添加详细的匹配分析
        for opp in opportunities[:10]:  # 只处理前 10 个
            # 计算技能匹配度
            skill_match = self._calculate_skill_match(profile, opp)
            opp["detailed_analysis"] = {
                "skill_match_score": skill_match,
                "experience_fit": self._calculate_experience_fit(profile, opp),
                "growth_potential": self._calculate_growth_potential(profile, opp)
            }

        return {
            **step2_result,
            "opportunities": opportunities,
            "match_calculated": True
        }

    def _calculate_skill_match(self, profile: Dict, opportunity: Dict) -> float:
        """计算技能匹配度"""
        # 简化实现，实际应使用向量相似度
        return opportunity.get("match_score", 0.5)

    def _calculate_experience_fit(self, profile: Dict, opportunity: Dict) -> float:
        """计算经验适配度"""
        # 简化实现
        perf_history = profile.get("performance_history", [])
        if not perf_history:
            return 0.5
        avg_score = sum(p.get("score", 0) for p in perf_history) / len(perf_history)
        return min(avg_score / 5.0, 1.0)

    def _calculate_growth_potential(self, profile: Dict, opportunity: Dict) -> float:
        """计算成长潜力"""
        # 简化实现
        return 0.7 if opportunity.get("type") == "promotion" else 0.5

    @step(order=4)
    async def generate_recommendations(self, step3_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: 生成推荐

        生成 Top N 推荐列表，包含详细理由和下一步行动
        """
        if "error" in step3_result:
            return step3_result

        opportunities = step3_result.get("opportunities", [])
        trace_id = self.trace_id or "unknown"

        logger.info(f"[{trace_id}] Step 4: 生成推荐")

        recommendations = []
        for i, opp in enumerate(opportunities[:5]):  # Top 5 推荐
            rec = {
                "rank": i + 1,
                "opportunity": opp,
                "recommendation_reason": self._generate_recommendation_reason(opp),
                "action_items": self._generate_action_items(opp),
                "confidence": opp.get("match_score", 0.5),
                "ai_commentary": self._generate_ai_commentary(opp)
            }
            recommendations.append(rec)

        return {
            **step3_result,
            "recommendations": recommendations,
            "total_recommendations": len(recommendations)
        }

    def _generate_recommendation_reason(self, opportunity: Dict) -> str:
        """生成推荐理由"""
        opp_type = opportunity.get("type", "unknown")
        match_score = opportunity.get("match_score", 0)

        if opp_type == "promotion":
            return f"基于你的优秀绩效表现（匹配度 {match_score:.0%}），你已准备好晋升"
        elif opp_type == "transfer":
            return f"你的技能与该岗位高度匹配（{match_score:.0%}），是理想的转岗机会"
        elif opp_type == "project":
            return f"该项目能发挥你的核心优势，匹配度 {match_score:.0%}"
        return f"这是一个适合你的发展机会，匹配度 {match_score:.0%}"

    def _generate_action_items(self, opportunity: Dict) -> List[str]:
        """生成下一步行动项"""
        actions = []
        opp_type = opportunity.get("type")

        if opp_type == "promotion":
            actions = [
                "更新个人简历",
                "与直属经理沟通晋升意向",
                "准备晋升答辩材料"
            ]
        elif opp_type == "transfer":
            actions = [
                "了解目标岗位的具体要求",
                "联系目标团队负责人",
                "准备内部面试"
            ]
        elif opp_type == "project":
            actions = [
                "查看项目详细文档",
                "联系项目负责人报名",
                "评估时间安排"
            ]

        return actions

    def _generate_ai_commentary(self, opportunity: Dict) -> str:
        """生成 AI 点评"""
        match_score = opportunity.get("match_score", 0)
        if match_score >= 0.8:
            return "强烈推荐！这是一个非常好的机会，建议优先考虑。"
        elif match_score >= 0.6:
            return "值得考虑的机会，建议进一步了解详细信息。"
        else:
            return "可以作为备选方案，建议先提升相关技能。"

    @step(order=5)
    async def notify_employee(self, step4_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 5: 发送通知

        向员工推送匹配结果和推荐
        """
        if "error" in step4_result:
            return step4_result

        employee_id = step4_result.get("employee_id")
        recommendations = step4_result.get("recommendations", [])
        trace_id = self.trace_id or "unknown"

        logger.info(f"[{trace_id}] Step 5: 发送通知给员工 {employee_id}")

        # 模拟通知发送
        notification = {
            "notification_id": f"notif-{trace_id}",
            "employee_id": employee_id,
            "type": "talent_match_recommendations",
            "title": f"为你找到 {len(recommendations)} 个发展机会",
            "content": self._generate_notification_content(recommendations),
            "sent_at": datetime.now().isoformat(),
            "channels": ["in_app", "email"],
            "status": "sent"
        }

        return {
            **step4_result,
            "notification": notification
        }

    def _generate_notification_content(self, recommendations: List[Dict]) -> str:
        """生成通知内容"""
        if not recommendations:
            return "暂无匹配的机会"

        top_rec = recommendations[0]
        opp_name = top_rec.get("opportunity", {}).get("role_name", "未知机会")
        return f"我们为你找到了 {len(recommendations)} 个发展机会，最匹配的是：{opp_name}。立即查看详情！"

    @step(order=6)
    async def track_feedback(self, step5_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 6: 追踪反馈

        记录员工对推荐的反馈（点击、忽略、申请等）
        """
        if "error" in step5_result:
            return step5_result

        notification = step5_result.get("notification", {})
        trace_id = self.trace_id or "unknown"

        logger.info(f"[{trace_id}] Step 6: 追踪反馈")

        # 初始化反馈追踪（实际应用中会等待用户行为）
        feedback_tracking = {
            "notification_id": notification.get("notification_id"),
            "tracking_enabled": True,
            "metrics_to_track": [
                "open_rate",
                "click_through_rate",
                "application_rate",
                "dismissal_rate"
            ],
            "tracking_period_days": 30
        }

        return {
            **step5_result,
            "feedback_tracking": feedback_tracking,
            "workflow_completed": True,
            "completed_at": datetime.now().isoformat()
        }

    # ==================== 工作流执行入口 ====================

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行完整工作流

        按顺序执行所有步骤，传递中间结果
        """
        result = input_data.copy()

        # 依次执行每个步骤
        steps = [
            self.analyze_employee,
            self.scan_opportunities,
            self.calculate_match,
            self.generate_recommendations,
            self.notify_employee,
            self.track_feedback
        ]

        for step_func in steps:
            if result.get("error"):
                logger.warning(f"工作流提前终止，原因：{result['error']}")
                break

            try:
                result = await step_func(result)
            except Exception as e:
                logger.error(f"工作流步骤执行失败：{e}")
                result["error"] = str(e)
                break

        return result


# ==================== 自主绩效评估工作流 ====================

@workflow(name="auto_performance_review")
class AutoPerformanceReviewWorkflow:
    """
    自主绩效评估工作流

    流程：
    1. 收集绩效数据 - 汇总 OKR 完成度、项目成果、同事反馈
    2. AI 分析评估 - 多维度绩效分析
    3. 生成改进建议 - 识别优势和待改进领域
    4. 制定行动计划 - 生成具体改进步骤
    5. 发送评估报告 - 向员工和管理者推送报告
    """

    @step(order=1)
    async def collect_performance_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: 收集绩效数据"""
        employee_id = input_data.get("employee_id")
        period = input_data.get("period", "quarterly")
        trace_id = input_data.get("trace_id", f"perf-{datetime.now().strftime('%Y%m%d%H%M%S')}")

        logger.info(f"[{trace_id}] Step 1: 收集绩效数据 - {employee_id}")

        # 模拟绩效数据收集
        performance_data = {
            "employee_id": employee_id,
            "period": period,
            "okr_completion_rate": 0.85,
            "projects_completed": 3,
            "peer_feedback_count": 5,
            "manager_feedback": "表现优秀，期待更大突破",
            "self_assessment": "总体满意，希望提升技术深度"
        }

        return {
            "performance_data": performance_data,
            "employee_id": employee_id,
            "trace_id": trace_id
        }

    @step(order=2)
    async def ai_analysis(self, step1_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: AI 分析评估"""
        if "error" in step1_result:
            return step1_result

        trace_id = step1_result.get("trace_id", "unknown")
        logger.info(f"[{trace_id}] Step 2: AI 分析评估")

        # AI 多维度分析
        analysis = {
            "overall_rating": "Excellent",
            "overall_score": 4.5,
            "dimensions": {
                "technical_excellence": {"score": 4.7, "comment": "技术能力突出"},
                "collaboration": {"score": 4.3, "comment": "团队合作良好"},
                "ownership": {"score": 4.5, "comment": "主动承担责任"},
                "communication": {"score": 4.2, "comment": "沟通清晰有效"},
                "innovation": {"score": 4.6, "comment": "持续提出创新方案"}
            },
            "trend": "improving",
            "percentile_rank": 85
        }

        return {
            **step1_result,
            "ai_analysis": analysis
        }

    @step(order=3)
    async def generate_improvement_suggestions(self, step2_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: 生成改进建议"""
        if "error" in step2_result:
            return step2_result

        trace_id = step2_result.get("trace_id", "unknown")
        logger.info(f"[{trace_id}] Step 3: 生成改进建议")

        analysis = step2_result.get("ai_analysis", {})

        # 识别优势和待改进领域
        suggestions = {
            "strengths": [
                "技术深度和专业能力突出",
                "项目交付质量高",
                "主动帮助团队成员"
            ],
            "areas_for_improvement": [
                "可以增加跨团队影响力",
                "建议提升公开演讲能力",
                "可以更多参与技术决策"
            ],
            "prioritized_actions": [
                {
                    "action": "在公司技术大会做一次分享",
                    "category": "visibility",
                    "priority": "high",
                    "expected_impact": "提升个人影响力和沟通能力"
                },
                {
                    "action": "参与架构设计讨论",
                    "category": "technical_leadership",
                    "priority": "medium",
                    "expected_impact": "提升技术领导力"
                }
            ]
        }

        return {
            **step2_result,
            "suggestions": suggestions
        }

    @step(order=4)
    async def create_action_plan(self, step3_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: 制定行动计划"""
        if "error" in step3_result:
            return step3_result

        trace_id = step3_result.get("trace_id", "unknown")
        logger.info(f"[{trace_id}] Step 4: 制定行动计划")

        suggestions = step3_result.get("suggestions", {})

        # 生成详细的行动计划
        action_plan = {
            "plan_id": f"plan-{trace_id}",
            "timeline": "next_quarter",
            "goals": [
                {
                    "goal": "提升技术影响力",
                    "actions": [
                        {"what": "准备技术分享", "when": "4 周内", "success_metric": "完成一次部门级分享"},
                        {"what": "撰写技术博客", "when": "8 周内", "success_metric": "发表 2 篇博客"}
                    ]
                },
                {
                    "goal": "加强跨团队协作",
                    "actions": [
                        {"what": "参与跨团队项目", "when": "持续", "success_metric": "至少参与 1 个跨团队项目"},
                        {"what": "组织技术交流会", "when": "12 周内", "success_metric": "组织一次交流会"}
                    ]
                }
            ],
            "check_in_schedule": "biweekly"
        }

        return {
            **step3_result,
            "action_plan": action_plan
        }

    @step(order=5)
    async def send_review_report(self, step4_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 5: 发送评估报告"""
        if "error" in step4_result:
            return step4_result

        employee_id = step4_result.get("employee_id")
        trace_id = step4_result.get("trace_id", "unknown")

        logger.info(f"[{trace_id}] Step 5: 发送评估报告")

        # 生成评估报告
        report = {
            "report_id": f"report-{trace_id}",
            "employee_id": employee_id,
            "type": "performance_review",
            "summary": {
                "rating": step4_result.get("ai_analysis", {}).get("overall_rating", "N/A"),
                "score": step4_result.get("ai_analysis", {}).get("overall_score", 0),
                "key_achievements": step4_result.get("suggestions", {}).get("strengths", [])[:3],
                "focus_areas": step4_result.get("suggestions", {}).get("areas_for_improvement", [])[:3]
            },
            "action_plan": step4_result.get("action_plan"),
            "next_review_date": "2025-04-01",
            "sent_to": ["employee", "manager"],
            "sent_at": datetime.now().isoformat()
        }

        return {
            **step4_result,
            "review_report": report,
            "workflow_completed": True,
            "completed_at": datetime.now().isoformat()
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行完整工作流"""
        result = input_data.copy()

        steps = [
            self.collect_performance_data,
            self.ai_analysis,
            self.generate_improvement_suggestions,
            self.create_action_plan,
            self.send_review_report
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
