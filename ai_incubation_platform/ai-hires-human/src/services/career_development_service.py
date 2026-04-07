"""
职业发展支持服务。

v1.20.0 新增：职业发展支持功能
- 职业规划（长期目标/里程碑）
- 技能提升（学习资源/培训推荐）
- 就业指导（简历优化/面试辅导）
- 创业支持（商业计划/融资建议）
- 人脉拓展（引荐/内推）
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from models.career_development import (
    CareerGoal,
    CareerGoalCreate,
    CareerGoalUpdate,
    CareerMilestone,
    GoalStatus,
    GoalType,
    LearningResource,
    LearningResourceType,
    SkillLevel,
    SkillAssessment,
    LearningProgress,
    SkillImprovementPlan,
    ResumeFeedback,
    InterviewPreparation,
    JobApplication,
    BusinessIdea,
    BusinessPlan,
    FundingOpportunity,
    FundingType,
    StartupStage,
    MentorshipMatch,
    ProfessionalConnection,
    ConnectionType,
    ReferralOpportunity,
    NetworkingEvent,
    CareerGoalResponse,
    SkillImprovementResponse,
    CareerDevelopmentSummary,
)

from services.worker_profile_service import worker_profile_service

import logging

logger = logging.getLogger(__name__)


class CareerDevelopmentService:
    """
    职业发展支持服务。

    提供以下功能：
    1. 职业规划：目标设定、里程碑管理、进度跟踪
    2. 技能提升：技能评估、学习资源推荐、学习计划
    3. 就业指导：简历分析、面试准备、求职申请跟踪
    4. 创业支持：商业创意评估、商业计划书、融资机会匹配
    5. 人脉拓展：人脉管理、内推机会、活动推荐
    """

    def __init__(self) -> None:
        # 职业规划存储
        self._career_goals: Dict[str, CareerGoal] = {}
        self._worker_goals: Dict[str, List[str]] = {}  # worker_id -> [goal_ids]

        # 技能提升存储
        self._learning_resources: Dict[str, LearningResource] = {}
        self._skill_assessments: Dict[str, SkillAssessment] = {}
        self._learning_progress: Dict[str, LearningProgress] = {}
        self._skill_improvement_plans: Dict[str, SkillImprovementPlan] = {}
        self._worker_skill_plans: Dict[str, List[str]] = {}  # worker_id -> [plan_ids]

        # 就业指导存储
        self._resume_feedbacks: Dict[str, ResumeFeedback] = {}
        self._interview_preparations: Dict[str, InterviewPreparation] = {}
        self._job_applications: Dict[str, JobApplication] = {}
        self._worker_applications: Dict[str, List[str]] = {}  # worker_id -> [application_ids]

        # 创业支持存储
        self._business_ideas: Dict[str, BusinessIdea] = {}
        self._business_plans: Dict[str, BusinessPlan] = {}
        self._funding_opportunities: Dict[str, FundingOpportunity] = {}
        self._mentorship_matches: Dict[str, MentorshipMatch] = {}

        # 人脉拓展存储
        self._connections: Dict[str, ProfessionalConnection] = {}
        self._worker_connections: Dict[str, List[str]] = {}  # worker_id -> [connection_ids]
        self._referral_opportunities: Dict[str, ReferralOpportunity] = {}
        self._networking_events: Dict[str, NetworkingEvent] = {}

        # 初始化预置数据
        self._init_default_data()

    def _init_default_data(self) -> None:
        """初始化默认数据。"""
        # 预置学习资源
        default_resources = [
            LearningResource(
                resource_id="lr_001",
                title="Python 编程入门",
                description="从零开始学习 Python 编程基础",
                resource_type=LearningResourceType.COURSE,
                skill_name="python",
                provider="Coursera",
                url="https://coursera.org/python-intro",
                duration_hours=40.0,
                difficulty=SkillLevel.BEGINNER,
                rating=4.5,
                is_free=False,
                created_at=datetime.now()
            ),
            LearningResource(
                resource_id="lr_002",
                title="数据标注实战教程",
                description="学习专业数据标注技巧和工具",
                resource_type=LearningResourceType.TUTORIAL,
                skill_name="data_annotation",
                provider="Udemy",
                url="https://udemy.com/data-annotation",
                duration_hours=15.0,
                difficulty=SkillLevel.INTERMEDIATE,
                rating=4.3,
                is_free=False,
                created_at=datetime.now()
            ),
            LearningResource(
                resource_id="lr_003",
                title="内容审核指南",
                description="内容审核最佳实践和案例分析",
                resource_type=LearningResourceType.BOOK,
                skill_name="content_moderation",
                provider="O'Reilly",
                url="https://oreilly.com/content-moderation",
                duration_hours=20.0,
                difficulty=SkillLevel.INTERMEDIATE,
                rating=4.7,
                is_free=False,
                created_at=datetime.now()
            ),
            LearningResource(
                resource_id="lr_004",
                title="线下采集技巧",
                description="线下数据采集的实用技巧",
                resource_type=LearningResourceType.VIDEO,
                skill_name="field_collection",
                provider="YouTube",
                url="https://youtube.com/field-collection",
                duration_hours=5.0,
                difficulty=SkillLevel.BEGINNER,
                rating=4.0,
                is_free=True,
                created_at=datetime.now()
            ),
            LearningResource(
                resource_id="lr_005",
                title="AI 提示工程",
                description="学习如何与 AI 高效协作",
                resource_type=LearningResourceType.COURSE,
                skill_name="prompt_engineering",
                provider="edX",
                url="https://edx.org/prompt-engineering",
                duration_hours=25.0,
                difficulty=SkillLevel.INTERMEDIATE,
                rating=4.8,
                is_free=False,
                created_at=datetime.now()
            ),
        ]
        for resource in default_resources:
            self._learning_resources[resource.resource_id] = resource

        # 预置融资机会
        default_funding = [
            FundingOpportunity(
                opportunity_id="fo_001",
                title="种子轮投资",
                description="面向早期创业项目的种子轮投资",
                funding_type=FundingType.SEED,
                amount_range="$50K-$200K",
                investor_name="创新资本",
                investor_type="VC",
                requirements=["完整的商业计划书", "有 MVP", "团队至少 2 人"],
                deadline=datetime(2026, 12, 31),
                application_url="https://example.com/apply",
                created_at=datetime.now()
            ),
            FundingOpportunity(
                opportunity_id="fo_002",
                title="天使投资人网络",
                description="连接创业者与天使投资人的平台",
                funding_type=FundingType.ANGEL,
                amount_range="$20K-$100K",
                investor_name="天使汇",
                investor_type="Angel Network",
                requirements=["创意验证", "市场调研"],
                deadline=datetime(2026, 6, 30),
                application_url="https://example.com/angel",
                created_at=datetime.now()
            ),
        ]
        for funding in default_funding:
            self._funding_opportunities[funding.opportunity_id] = funding

        # 预置人脉活动
        default_events = [
            NetworkingEvent(
                event_id="ne_001",
                title="AI 与人力资源创新峰会",
                description="探讨 AI 在人力资源领域的应用与创新",
                event_type="conference",
                start_date=datetime(2026, 5, 15, 9, 0),
                end_date=datetime(2026, 5, 15, 17, 0),
                location="北京国际会议中心",
                virtual_url=None,
                organizer="人力资源协会",
                status="upcoming",
                created_at=datetime.now()
            ),
            NetworkingEvent(
                event_id="ne_002",
                title="自由职业者线上交流会",
                description="自由职业者经验分享与人脉拓展",
                event_type="webinar",
                start_date=datetime(2026, 4, 20, 20, 0),
                end_date=datetime(2026, 4, 20, 21, 30),
                location=None,
                virtual_url="https://zoom.us/join/123456",
                organizer="自由职业者社区",
                status="upcoming",
                created_at=datetime.now()
            ),
        ]
        for event in default_events:
            self._networking_events[event.event_id] = event

    # ========== 职业规划功能 ==========

    def create_career_goal(self, data: CareerGoalCreate) -> CareerGoal:
        """创建职业目标。"""
        now = datetime.now()
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"

        # 创建里程碑
        milestones = []
        for i, m in enumerate(data.milestones):
            milestone = CareerMilestone(
                milestone_id=f"m_{uuid.uuid4().hex[:6]}",
                goal_id=goal_id,
                title=m.get("title", f"里程碑{i + 1}"),
                description=m.get("description", ""),
                status=GoalStatus.DRAFT,
                target_date=datetime.fromisoformat(m["target_date"]) if m.get("target_date") else None,
                created_at=now
            )
            milestones.append(milestone)

        goal = CareerGoal(
            goal_id=goal_id,
            worker_id=data.worker_id,
            title=data.title,
            description=data.description,
            goal_type=data.goal_type,
            status=GoalStatus.DRAFT,
            target_date=data.target_date,
            created_at=now,
            updated_at=now,
            milestones=milestones,
            related_skills=data.related_skills
        )

        self._career_goals[goal_id] = goal

        # 关联到工人
        if data.worker_id not in self._worker_goals:
            self._worker_goals[data.worker_id] = []
        self._worker_goals[data.worker_id].append(goal_id)

        return goal

    def get_career_goal(self, goal_id: str) -> Optional[CareerGoal]:
        """获取职业目标详情。"""
        return self._career_goals.get(goal_id)

    def update_career_goal(self, goal_id: str, data: CareerGoalUpdate) -> Optional[CareerGoal]:
        """更新职业目标。"""
        goal = self._career_goals.get(goal_id)
        if not goal:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(goal, field) and value is not None:
                setattr(goal, field, value)

        goal.updated_at = datetime.now()
        return goal

    def delete_career_goal(self, goal_id: str) -> bool:
        """删除职业目标。"""
        goal = self._career_goals.get(goal_id)
        if not goal:
            return False

        # 从工人列表中移除
        if goal.worker_id in self._worker_goals:
            if goal_id in self._worker_goals[goal.worker_id]:
                self._worker_goals[goal.worker_id].remove(goal_id)

        del self._career_goals[goal_id]
        return True

    def list_worker_goals(
        self,
        worker_id: str,
        goal_type: Optional[GoalType] = None,
        status: Optional[GoalStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CareerGoal]:
        """列出工人的职业目标。"""
        goal_ids = self._worker_goals.get(worker_id, [])
        goals = [self._career_goals[gid] for gid in goal_ids if gid in self._career_goals]

        # 筛选
        if goal_type:
            goals = [g for g in goals if g.goal_type == goal_type]
        if status:
            goals = [g for g in goals if g.status == status]

        return goals[skip:skip + limit]

    def update_milestone_status(
        self,
        goal_id: str,
        milestone_id: str,
        status: GoalStatus
    ) -> Optional[CareerGoal]:
        """更新里程碑状态。"""
        goal = self._career_goals.get(goal_id)
        if not goal:
            return None

        for milestone in goal.milestones:
            if milestone.milestone_id == milestone_id:
                milestone.status = status
                if status == GoalStatus.COMPLETED:
                    milestone.completed_date = datetime.now()
                goal.updated_at = datetime.now()

                # 重新计算进度
                self._calculate_goal_progress(goal)
                break

        return goal

    def _calculate_goal_progress(self, goal: CareerGoal) -> None:
        """计算目标进度。"""
        if not goal.milestones:
            goal.progress = 0.0
            return

        completed = sum(1 for m in goal.milestones if m.status == GoalStatus.COMPLETED)
        goal.progress = (completed / len(goal.milestones)) * 100

        # 如果所有里程碑都完成，更新目标状态
        if completed == len(goal.milestones) and goal.status != GoalStatus.COMPLETED:
            goal.status = GoalStatus.COMPLETED

    # ========== 技能提升功能 ==========

    def assess_skill(
        self,
        worker_id: str,
        skill_name: str,
        current_level: SkillLevel,
        target_level: SkillLevel
    ) -> SkillAssessment:
        """评估工人技能水平。"""
        assessment_id = f"assess_{uuid.uuid4().hex[:8]}"

        # 获取工人画像
        worker = worker_profile_service.get_profile(worker_id)

        # 分析优劣势
        strengths = []
        weaknesses = []

        if worker:
            if skill_name in worker.skills:
                skill_level = worker.skills[skill_name]
                if skill_level in ["expert", "advanced"]:
                    strengths.append(f"已具备{skill_level}水平的技能")
                else:
                    weaknesses.append(f"技能水平有待提升（当前：{skill_level}）")

            if skill_name in worker.verified_skills:
                strengths.append("该技能已通过认证")

            if worker.completed_tasks > 50:
                strengths.append("有丰富的任务完成经验")

        if not strengths:
            weaknesses.append("需要系统性学习该技能")

        # 推荐学习资源
        recommended = self._recommend_learning_resources(skill_name, current_level)

        assessment = SkillAssessment(
            assessment_id=assessment_id,
            worker_id=worker_id,
            skill_name=skill_name,
            current_level=current_level,
            target_level=target_level,
            assessment_date=datetime.now(),
            strengths=strengths,
            weaknesses=weaknesses,
            recommended_resources=recommended,
            score=self._calculate_skill_score(current_level)
        )

        self._skill_assessments[assessment_id] = assessment
        return assessment

    def _calculate_skill_score(self, level: SkillLevel) -> float:
        """计算技能得分。"""
        scores = {
            SkillLevel.BEGINNER: 25.0,
            SkillLevel.INTERMEDIATE: 50.0,
            SkillLevel.ADVANCED: 75.0,
            SkillLevel.EXPERT: 95.0
        }
        return scores.get(level, 0.0)

    def _recommend_learning_resources(
        self,
        skill_name: str,
        current_level: SkillLevel
    ) -> List[str]:
        """推荐学习资源。"""
        recommended = []

        # 根据技能和等级推荐
        for resource in self._learning_resources.values():
            if resource.skill_name.lower() == skill_name.lower():
                # 推荐下一级难度的资源
                if self._is_next_level(resource.difficulty, current_level):
                    recommended.append(resource.resource_id)

        # 如果没有找到下一级资源，推荐同级的
        if not recommended:
            for resource in self._learning_resources.values():
                if resource.skill_name.lower() == skill_name.lower():
                    if resource.difficulty == current_level:
                        recommended.append(resource.resource_id)

        return recommended[:5]  # 最多 5 个

    def _is_next_level(self, resource_level: SkillLevel, current_level: SkillLevel) -> bool:
        """判断资源难度是否为下一级。"""
        order = [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED, SkillLevel.EXPERT]
        try:
            current_idx = order.index(current_level)
            resource_idx = order.index(resource_level)
            return resource_idx == current_idx or resource_idx == current_idx + 1
        except ValueError:
            return False

    def create_learning_plan(
        self,
        worker_id: str,
        skill_name: str,
        target_level: SkillLevel,
        target_date: Optional[datetime] = None
    ) -> SkillImprovementPlan:
        """创建技能提升计划。"""
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # 获取工人当前技能水平
        worker = worker_profile_service.get_profile(worker_id)
        current_level = SkillLevel.BEGINNER
        if worker and skill_name in worker.skills:
            skill_str = worker.skills[skill_name]
            current_level = self._str_to_skill_level(skill_str)

        # 推荐学习资源
        resource_ids = self._recommend_learning_resources(skill_name, current_level)

        plan = SkillImprovementPlan(
            plan_id=plan_id,
            worker_id=worker_id,
            skill_name=skill_name,
            current_level=current_level,
            target_level=target_level,
            target_date=target_date,
            status=GoalStatus.ACTIVE,
            resource_ids=resource_ids,
            weekly_hours=5,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self._skill_improvement_plans[plan_id] = plan

        if worker_id not in self._worker_skill_plans:
            self._worker_skill_plans[worker_id] = []
        self._worker_skill_plans[worker_id].append(plan_id)

        return plan

    def _str_to_skill_level(self, level_str: str) -> SkillLevel:
        """将字符串转换为技能等级。"""
        mapping = {
            "beginner": SkillLevel.BEGINNER,
            "intermediate": SkillLevel.INTERMEDIATE,
            "advanced": SkillLevel.ADVANCED,
            "expert": SkillLevel.EXPERT
        }
        return mapping.get(level_str.lower(), SkillLevel.BEGINNER)

    def get_learning_plan(self, plan_id: str) -> Optional[SkillImprovementPlan]:
        """获取学习计划详情。"""
        return self._skill_improvement_plans.get(plan_id)

    def update_learning_progress(
        self,
        plan_id: str,
        progress_percent: float,
        resource_id: Optional[str] = None
    ) -> Optional[SkillImprovementPlan]:
        """更新学习进度。"""
        plan = self._skill_improvement_plans.get(plan_id)
        if not plan:
            return None

        plan.progress = progress_percent
        plan.updated_at = datetime.now()

        # 如果完成，更新状态
        if progress_percent >= 100:
            plan.status = GoalStatus.COMPLETED

        # 记录学习进度
        if resource_id:
            progress_id = f"lp_{uuid.uuid4().hex[:8]}"
            lp = LearningProgress(
                progress_id=progress_id,
                worker_id=plan.worker_id,
                resource_id=resource_id,
                status=GoalStatus.ACTIVE,
                started_at=datetime.now(),
                progress_percent=progress_percent
            )
            self._learning_progress[progress_id] = lp

        return plan

    def list_learning_resources(
        self,
        skill_name: Optional[str] = None,
        resource_type: Optional[LearningResourceType] = None,
        difficulty: Optional[SkillLevel] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[LearningResource]:
        """列出学习资源。"""
        resources = list(self._learning_resources.values())

        if skill_name:
            resources = [r for r in resources if r.skill_name.lower() == skill_name.lower()]
        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        if difficulty:
            resources = [r for r in resources if r.difficulty == difficulty]

        return resources[skip:skip + limit]

    def get_learning_resource(self, resource_id: str) -> Optional[LearningResource]:
        """获取学习资源详情。"""
        return self._learning_resources.get(resource_id)

    # ========== 就业指导功能 ==========

    def analyze_resume(self, worker_id: str, resume_content: str) -> ResumeFeedback:
        """分析简历并提供反馈。"""
        feedback_id = f"resume_{uuid.uuid4().hex[:8]}"

        # 简化的简历分析逻辑
        score = 60.0  # 基础分
        section_scores = {}
        section_feedback = {}
        suggestions = []

        # 检查简历长度
        if len(resume_content) < 500:
            suggestions.append("简历内容过于简短，建议扩充到 500 字以上")
            score -= 10
        elif len(resume_content) > 2000:
            suggestions.append("简历内容过长，建议精简到 2000 字以内")

        # 检查关键词
        keywords = ["技能", "经验", "项目", "教育", "工作"]
        found_keywords = [kw for kw in keywords if kw in resume_content]
        if len(found_keywords) >= 4:
            section_scores["completeness"] = 90.0
            section_feedback["completeness"] = "简历结构完整"
        else:
            section_scores["completeness"] = 50.0
            section_feedback["completeness"] = "简历结构不完整，缺少关键部分"
            suggestions.append(f"建议补充以下内容：{[kw for kw in keywords if kw not in found_keywords]}")
            score -= 15

        # 检查联系方式
        if "@" in resume_content:
            section_scores["contact"] = 100.0
            section_feedback["contact"] = "包含有效的联系方式"
        else:
            section_scores["contact"] = 50.0
            section_feedback["contact"] = "缺少邮箱地址"
            suggestions.append("建议添加邮箱地址")
            score -= 10

        # ATS 兼容性评分
        ats_score = 70.0
        if any(kw in resume_content for kw in ["负责", "参与", "主导", "实现"]):
            ats_score += 10
        if len(resume_content.split("\n")) > 5:
            ats_score += 10

        # 总体建议
        if score >= 80:
            suggestions.append("简历整体质量良好，可直接用于求职")
        elif score >= 60:
            suggestions.append("简历需要进一步改进后再投递")
        else:
            suggestions.append("建议重新编写简历，或寻求专业简历优化服务")

        feedback = ResumeFeedback(
            feedback_id=feedback_id,
            worker_id=worker_id,
            resume_content=resume_content,
            overall_score=max(0, min(100, score)),
            section_scores=section_scores,
            section_feedback=section_feedback,
            overall_suggestions=suggestions,
            ats_score=ats_score,
            created_at=datetime.now()
        )

        self._resume_feedbacks[feedback_id] = feedback
        return feedback

    def prepare_interview(
        self,
        worker_id: str,
        job_title: str,
        company_name: Optional[str] = None,
        interview_type: str = "general"
    ) -> InterviewPreparation:
        """准备面试。"""
        prep_id = f"interview_{uuid.uuid4().hex[:8]}"

        # 根据职位和面试类型生成常见问题
        common_questions = self._generate_interview_questions(job_title, interview_type)

        # 面试技巧建议
        tips = self._generate_interview_tips(interview_type)

        prep = InterviewPreparation(
            prep_id=prep_id,
            worker_id=worker_id,
            job_title=job_title,
            company_name=company_name,
            interview_type=interview_type,
            preparation_status=GoalStatus.ACTIVE,
            common_questions=common_questions,
            tips=tips,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self._interview_preparations[prep_id] = prep
        return prep

    def _generate_interview_questions(
        self,
        job_title: str,
        interview_type: str
    ) -> List[Dict]:
        """生成面试常见问题。"""
        questions = []

        # 通用问题
        general_questions = [
            {"question": "请介绍一下你自己", "category": "general"},
            {"question": "你的优势是什么？", "category": "general"},
            {"question": "你为什么想加入我们公司？", "category": "general"},
            {"question": "描述一次你克服困难的经历", "category": "behavioral"},
            {"question": "你的职业规划是什么？", "category": "general"},
        ]

        # 技术问题
        technical_questions = [
            {"question": "请解释一下你简历中提到的这个项目", "category": "technical"},
            {"question": "你如何解决技术难题？", "category": "technical"},
            {"question": "请描述一个你优化的系统或流程", "category": "technical"},
        ]

        # 行为问题
        behavioral_questions = [
            {"question": "描述一次你与同事冲突的经历及如何解决", "category": "behavioral"},
            {"question": "你如何在压力下工作？", "category": "behavioral"},
            {"question": "描述一次你展现领导力的经历", "category": "behavioral"},
        ]

        questions.extend(general_questions[:3])

        if interview_type == "technical":
            questions.extend(technical_questions)
        elif interview_type == "behavioral":
            questions.extend(behavioral_questions)
        else:
            questions.extend(technical_questions[:1])
            questions.extend(behavioral_questions[:1])

        return questions

    def _generate_interview_tips(self, interview_type: str) -> List[str]:
        """生成面试技巧建议。"""
        tips = [
            "提前研究公司和职位信息",
            "准备好自我介绍（1-2 分钟）",
            "准备几个向面试官提问的问题",
            "面试前进行模拟练习",
            "注意着装和仪态"
        ]

        if interview_type == "technical":
            tips.extend([
                "复习基础知识和常用算法",
                "准备代码示例或项目演示",
                "遇到不会的问题要展示思考过程"
            ])
        elif interview_type == "behavioral":
            tips.extend([
                "使用 STAR 方法（情境、任务、行动、结果）回答问题",
                "准备具体的案例和故事",
                "强调你的贡献和成果"
            ])

        return tips

    def create_job_application(
        self,
        worker_id: str,
        job_title: str,
        company_name: str,
        job_description: Optional[str] = None,
        application_url: Optional[str] = None
    ) -> JobApplication:
        """创建求职申请。"""
        application_id = f"app_{uuid.uuid4().hex[:8]}"

        application = JobApplication(
            application_id=application_id,
            worker_id=worker_id,
            job_title=job_title,
            company_name=company_name,
            job_description=job_description,
            application_url=application_url,
            status="applied",
            applied_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self._job_applications[application_id] = application

        if worker_id not in self._worker_applications:
            self._worker_applications[worker_id] = []
        self._worker_applications[worker_id].append(application_id)

        return application

    def update_job_application_status(
        self,
        application_id: str,
        status: str
    ) -> Optional[JobApplication]:
        """更新求职申请状态。"""
        application = self._job_applications.get(application_id)
        if not application:
            return None

        application.status = status
        application.updated_at = datetime.now()

        return application

    def list_job_applications(
        self,
        worker_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[JobApplication]:
        """列出求职申请。"""
        application_ids = self._worker_applications.get(worker_id, [])
        applications = [
            self._job_applications[aid]
            for aid in application_ids
            if aid in self._job_applications
        ]

        if status:
            applications = [a for a in applications if a.status == status]

        return applications[skip:skip + limit]

    # ========== 创业支持功能 ==========

    def create_business_idea(
        self,
        worker_id: str,
        title: str,
        description: str,
        target_market: str = "",
        value_proposition: str = ""
    ) -> BusinessIdea:
        """创建商业创意。"""
        idea_id = f"idea_{uuid.uuid4().hex[:8]}"

        idea = BusinessIdea(
            idea_id=idea_id,
            worker_id=worker_id,
            title=title,
            description=description,
            target_market=target_market,
            value_proposition=value_proposition,
            status=StartupStage.IDEA,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self._business_ideas[idea_id] = idea
        return idea

    def get_business_idea(self, idea_id: str) -> Optional[BusinessIdea]:
        """获取商业创意详情。"""
        return self._business_ideas.get(idea_id)

    def create_business_plan(
        self,
        idea_id: str,
        worker_id: str,
        title: str
    ) -> BusinessPlan:
        """创建商业计划书。"""
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        idea = self._business_ideas.get(idea_id)

        plan = BusinessPlan(
            plan_id=plan_id,
            idea_id=idea_id,
            worker_id=worker_id,
            title=title,
            executive_summary=idea.description if idea else "",
            status=idea.status if idea else StartupStage.IDEA,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self._business_plans[plan_id] = plan
        return plan

    def get_funding_opportunities(
        self,
        funding_type: Optional[FundingType] = None,
        limit: int = 10
    ) -> List[FundingOpportunity]:
        """获取融资机会列表。"""
        opportunities = list(self._funding_opportunities.values())

        if funding_type:
            opportunities = [o for o in opportunities if o.funding_type == funding_type]

        return opportunities[:limit]

    def match_mentor(
        self,
        mentee_worker_id: str,
        mentor_areas: List[str]
    ) -> Optional[MentorshipMatch]:
        """匹配导师。"""
        # 简化的匹配逻辑
        # 实际应该基于技能、经验、可用性等进行匹配

        mentee = worker_profile_service.get_profile(mentee_worker_id)
        if not mentee:
            return None

        # 寻找潜在导师（这里简化处理）
        match_id = f"mentor_{uuid.uuid4().hex[:8]}"

        match = MentorshipMatch(
            match_id=match_id,
            mentee_worker_id=mentee_worker_id,
            mentor_worker_id="mentor_placeholder",  # 实际应该找到真实导师
            mentorship_areas=mentor_areas,
            match_reasons=["基于技能匹配", "基于行业经验"],
            match_score=75.0,
            status=GoalStatus.DRAFT,
            created_at=datetime.now()
        )

        self._mentorship_matches[match_id] = match
        return match

    # ========== 人脉拓展功能 ==========

    def add_connection(
        self,
        worker_id: str,
        connected_worker_id: str,
        connection_type: ConnectionType
    ) -> ProfessionalConnection:
        """添加人脉连接。"""
        connection_id = f"conn_{uuid.uuid4().hex[:8]}"

        # 获取双方信息以计算共同点
        worker = worker_profile_service.get_profile(worker_id)
        connected = worker_profile_service.get_profile(connected_worker_id)

        common_interests = []
        common_skills = []

        if worker and connected:
            # 计算共同技能
            worker_skills = set(worker.skills.keys())
            connected_skills = set(connected.skills.keys())
            common_skills = list(worker_skills & connected_skills)

        connection = ProfessionalConnection(
            connection_id=connection_id,
            worker_id=worker_id,
            connected_worker_id=connected_worker_id,
            connection_type=connection_type,
            common_interests=common_interests,
            common_skills=common_skills,
            status="active",
            created_at=datetime.now()
        )

        self._connections[connection_id] = connection

        if worker_id not in self._worker_connections:
            self._worker_connections[worker_id] = []
        self._worker_connections[worker_id].append(connection_id)

        return connection

    def list_connections(
        self,
        worker_id: str,
        connection_type: Optional[ConnectionType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProfessionalConnection]:
        """列出人脉连接。"""
        connection_ids = self._worker_connections.get(worker_id, [])
        connections = [
            self._connections[cid]
            for cid in connection_ids
            if cid in self._connections
        ]

        if connection_type:
            connections = [c for c in connections if c.connection_type == connection_type]

        return connections[skip:skip + limit]

    def create_referral_opportunity(
        self,
        worker_id: str,
        job_title: str,
        company_name: str,
        job_description: str = "",
        referral_bonus: Optional[str] = None
    ) -> ReferralOpportunity:
        """创建内推机会。"""
        referral_id = f"referral_{uuid.uuid4().hex[:8]}"

        referral = ReferralOpportunity(
            referral_id=referral_id,
            worker_id=worker_id,
            job_title=job_title,
            company_name=company_name,
            job_description=job_description,
            referral_bonus=referral_bonus,
            status="open",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self._referral_opportunities[referral_id] = referral
        return referral

    def list_referral_opportunities(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ReferralOpportunity]:
        """列出内推机会。"""
        opportunities = list(self._referral_opportunities.values())
        return opportunities[skip:skip + limit]

    def list_networking_events(
        self,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[NetworkingEvent]:
        """列出人脉活动。"""
        events = list(self._networking_events.values())

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if status:
            events = [e for e in events if e.status == status]

        return events[skip:skip + limit]

    def register_for_event(
        self,
        event_id: str,
        worker_id: str
    ) -> Optional[NetworkingEvent]:
        """注册参加活动。"""
        event = self._networking_events.get(event_id)
        if not event:
            return None

        if worker_id not in event.attendees:
            event.attendees.append(worker_id)
            event.attendee_count = len(event.attendees)
            event.updated_at = datetime.now()

        return event

    # ========== 综合分析功能 ==========

    def get_career_summary(self, worker_id: str) -> CareerDevelopmentSummary:
        """获取工人职业发展摘要。"""
        # 统计目标
        goals = self.list_worker_goals(worker_id)
        active_goals = sum(1 for g in goals if g.status == GoalStatus.ACTIVE)
        completed_goals = sum(1 for g in goals if g.status == GoalStatus.COMPLETED)

        # 统计技能提升计划
        plans = self._worker_skill_plans.get(worker_id, [])
        skills_in_progress = sum(
            1 for p in plans
            if p in self._skill_improvement_plans
            and self._skill_improvement_plans[p].status == GoalStatus.ACTIVE
        )

        # 统计学习时间
        learning_hours = 0.0
        for progress in self._learning_progress.values():
            if progress.worker_id == worker_id:
                resource = self._learning_resources.get(progress.resource_id)
                if resource and resource.duration_hours:
                    learning_hours += resource.duration_hours * (progress.progress_percent / 100)

        # 统计人脉
        connections = len(self._worker_connections.get(worker_id, []))

        # 统计求职申请
        applications = self.list_job_applications(worker_id)
        upcoming_interviews = sum(
            1 for a in applications
            if a.status in ["interviewing", "offered"]
        )

        # 统计内推机会
        referrals = len([
            r for r in self._referral_opportunities.values()
            if r.status == "open"
        ])

        # 获取简历评分（如果有）
        resume_score = None
        for feedback in self._resume_feedbacks.values():
            if feedback.worker_id == worker_id:
                resume_score = feedback.overall_score
                break

        return CareerDevelopmentSummary(
            worker_id=worker_id,
            active_goals=active_goals,
            completed_goals=completed_goals,
            skills_in_progress=skills_in_progress,
            learning_hours_total=learning_hours,
            resume_score=resume_score,
            connections_count=connections,
            upcoming_interviews=upcoming_interviews,
            referral_opportunities=referrals
        )


# 全局服务实例
career_development_service = CareerDevelopmentService()
