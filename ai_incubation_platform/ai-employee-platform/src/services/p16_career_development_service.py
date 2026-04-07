"""
P16 职业发展规划 - 服务层
版本：v16.0.0
主题：职业发展规划 (Career Development Planning)
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
import math

from models.p16_models import (
    # 枚举
    SkillLevel, SkillCategory, CareerPathType, MentorshipStatus, DevelopmentPlanStatus,
    GoalType, GoalStatus, DependencyType, PromotionReadiness,
    # 模型
    Skill, SkillDependency, EmployeeSkill, SkillGrowth,
    CareerRole, RoleTransition, CareerPathRecommendation,
    DevelopmentPlan, DevelopmentGoal, DevelopmentActivity,
    MentorProfile, MenteeProfile, MentorshipMatch, MentorshipSession,
    PromotionReadinessAssessment, PromotionHistory,
    # 数据库
    CareerDevelopmentDB,
)


# ============================================================================
# 技能图谱服务
# ============================================================================

class SkillGraphService:
    """技能图谱服务"""

    def __init__(self, db: CareerDevelopmentDB):
        self.db = db

    def create_skill(self, name: str, description: str, category: SkillCategory,
                     parent_skill_id: Optional[str] = None,
                     tags: Optional[List[str]] = None) -> Skill:
        """创建技能"""
        skill = Skill(
            name=name,
            description=description,
            category=category,
            parent_skill_id=parent_skill_id,
            tags=tags or [],
        )
        self.db.insert("skills", skill.to_dict())
        return skill

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能详情"""
        data = self.db.get("skills", skill_id)
        return Skill.from_dict(data) if data else None

    def list_skills(self, category: Optional[SkillCategory] = None,
                    parent_skill_id: Optional[str] = None,
                    search: Optional[str] = None,
                    limit: int = 100) -> List[Skill]:
        """列出技能"""
        filters = {}
        if category:
            filters["category"] = category.value
        if parent_skill_id is not None:
            filters["parent_skill_id"] = parent_skill_id if parent_skill_id else ""

        rows = self.db.list("skills", filters, order_by="name ASC", limit=limit)

        if search:
            rows = [r for r in rows if search.lower() in r["name"].lower() or search.lower() in (r.get("description") or "").lower()]

        return [Skill.from_dict(row) for row in rows]

    def update_skill(self, skill_id: str, name: Optional[str] = None,
                     description: Optional[str] = None,
                     tags: Optional[List[str]] = None) -> Optional[Skill]:
        """更新技能"""
        skill = self.get_skill(skill_id)
        if not skill:
            return None

        update_data = {}
        if name:
            update_data["name"] = name
        if description:
            update_data["description"] = description
        if tags:
            update_data["tags"] = tags

        if update_data:
            self.db.update("skills", skill_id, update_data)
            return self.get_skill(skill_id)
        return skill

    def delete_skill(self, skill_id: str) -> bool:
        """删除技能"""
        return self.db.delete("skills", skill_id)

    def add_dependency(self, from_skill_id: str, to_skill_id: str,
                       dependency_type: DependencyType,
                       strength: float = 1.0) -> SkillDependency:
        """添加技能依赖关系"""
        dep = SkillDependency(
            from_skill_id=from_skill_id,
            to_skill_id=to_skill_id,
            dependency_type=dependency_type,
            strength=strength,
        )
        self.db.insert("skill_dependencies", dep.to_dict())
        return dep

    def get_prerequisites(self, skill_id: str) -> List[Tuple[Skill, DependencyType, float]]:
        """获取技能的前置技能"""
        rows = self.db.query(
            "SELECT s.*, sd.dependency_type, sd.strength FROM skills s "
            "JOIN skill_dependencies sd ON s.id = sd.from_skill_id "
            "WHERE sd.to_skill_id = ? ORDER BY sd.strength DESC",
            (skill_id,)
        )
        return [(Skill.from_dict(row), DependencyType(row["dependency_type"]), row["strength"]) for row in rows]

    def get_dependent_skills(self, skill_id: str) -> List[Tuple[Skill, DependencyType, float]]:
        """获取依赖该技能的其他技能"""
        rows = self.db.query(
            "SELECT s.*, sd.dependency_type, sd.strength FROM skills s "
            "JOIN skill_dependencies sd ON s.id = sd.to_skill_id "
            "WHERE sd.from_skill_id = ? ORDER BY sd.strength DESC",
            (skill_id,)
        )
        return [(Skill.from_dict(row), DependencyType(row["dependency_type"]), row["strength"]) for row in rows]

    def get_skill_tree(self, root_skill_id: Optional[str] = None) -> Dict[str, Any]:
        """获取技能树（从根节点或指定技能开始）"""
        # 如果没有指定根节点，获取所有顶级技能
        if root_skill_id is None:
            root_skills = self.list_skills(parent_skill_id="")
        else:
            root_skill = self.get_skill(root_skill_id)
            if not root_skill:
                return {"error": "Skill not found"}
            root_skills = [root_skill]

        def build_tree(skill: Skill) -> Dict[str, Any]:
            children = self.list_skills(parent_skill_id=skill.id)
            return {
                "skill": skill.to_dict(),
                "children": [build_tree(child) for child in children],
            }

        return {
            "roots": [build_tree(skill) for skill in root_skills],
        }

    def get_learning_path(self, from_skill_id: str, to_skill_id: str) -> List[Skill]:
        """获取从起点技能到目标技能的学习路径"""
        # 使用 BFS 查找最短路径
        from collections import deque

        visited = set()
        queue = deque([(from_skill_id, [from_skill_id])])

        while queue:
            current_id, path = queue.popleft()

            if current_id == to_skill_id:
                return [self.get_skill(sid) for sid in path if self.get_skill(sid)]

            if current_id in visited:
                continue
            visited.add(current_id)

            # 获取当前技能指向的所有技能
            dependents = self.get_dependent_skills(current_id)
            for dep_skill, _, _ in dependents:
                if dep_skill.id not in visited:
                    queue.append((dep_skill.id, path + [dep_skill.id]))

        return []  # 无路径


# ============================================================================
# 员工技能服务
# ============================================================================

class EmployeeSkillService:
    """员工技能服务"""

    def __init__(self, db: CareerDevelopmentDB):
        self.db = db

    def add_employee_skill(self, employee_id: str, skill_id: str,
                           level: SkillLevel, years_of_experience: float = 0,
                           self_assessed: bool = True,
                           evidence: Optional[str] = None) -> EmployeeSkill:
        """添加员工技能"""
        # 检查是否已存在
        existing = self.get_employee_skill_by_skill(employee_id, skill_id)
        if existing:
            # 更新现有技能
            update_data = {
                "level": level.value,
                "years_of_experience": years_of_experience,
                "self_assessed": self_assessed,
                "evidence": evidence,
                "verified": False,
            }
            self.db.update("employee_skills", existing.id, update_data)
            return self.get_employee_skill(existing.id)

        emp_skill = EmployeeSkill(
            employee_id=employee_id,
            skill_id=skill_id,
            level=level,
            years_of_experience=years_of_experience,
            self_assessed=self_assessed,
            evidence=evidence,
        )
        self.db.insert("employee_skills", emp_skill.to_dict())
        return emp_skill

    def get_employee_skill(self, record_id: str) -> Optional[EmployeeSkill]:
        """获取员工技能记录"""
        data = self.db.get("employee_skills", record_id)
        return EmployeeSkill.from_dict(data) if data else None

    def get_employee_skill_by_skill(self, employee_id: str, skill_id: str) -> Optional[EmployeeSkill]:
        """根据员工 ID 和技能 ID 获取技能记录"""
        rows = self.db.list("employee_skills", {"employee_id": employee_id, "skill_id": skill_id})
        return EmployeeSkill.from_dict(rows[0]) if rows else None

    def list_employee_skills(self, employee_id: str,
                             level: Optional[SkillLevel] = None,
                             category: Optional[SkillCategory] = None) -> List[Dict[str, Any]]:
        """列出员工的技能（包含技能详情）"""
        filters = {"employee_id": employee_id}
        rows = self.db.list("employee_skills", filters)

        result = []
        for row in rows:
            emp_skill = EmployeeSkill.from_dict(row)
            skill = self.db.get("skills", emp_skill.skill_id)
            if skill:
                skill_obj = Skill.from_dict(skill)
                if level and emp_skill.level != level:
                    continue
                if category and skill_obj.category != category:
                    continue
                result.append({
                    "employee_skill": emp_skill,
                    "skill": skill_obj,
                })

        return result

    def verify_skill(self, record_id: str, verified: bool = True) -> bool:
        """验证技能"""
        return self.db.update("employee_skills", record_id, {"verified": verified})

    def record_skill_growth(self, employee_id: str, skill_id: str,
                            from_level: SkillLevel, to_level: SkillLevel,
                            growth_type: str) -> SkillGrowth:
        """记录技能成长"""
        growth = SkillGrowth(
            employee_id=employee_id,
            skill_id=skill_id,
            from_level=from_level,
            to_level=to_level,
            growth_type=growth_type,
        )
        self.db.insert("skill_growth", growth.to_dict())

        # 同时更新员工技能等级
        emp_skill = self.get_employee_skill_by_skill(employee_id, skill_id)
        if emp_skill:
            self.db.update("employee_skills", emp_skill.id, {
                "level": to_level.value,
                "verified": False,
            })

        return growth

    def get_skill_growth_history(self, employee_id: str,
                                  skill_id: Optional[str] = None,
                                  limit: int = 50) -> List[SkillGrowth]:
        """获取技能成长历史"""
        filters = {"employee_id": employee_id}
        if skill_id:
            filters["skill_id"] = skill_id

        rows = self.db.list("skill_growth", filters, order_by="recorded_at DESC", limit=limit)
        return [SkillGrowth.from_dict(row) for row in rows]


# ============================================================================
# 职业路径服务
# ============================================================================

class CareerPathService:
    """职业路径服务"""

    def __init__(self, db: CareerDevelopmentDB):
        self.db = db

    def create_career_role(self, name: str, description: str, level: int,
                           path_type: CareerPathType,
                           required_skills: Dict[str, int],
                           recommended_skills: Optional[List[str]] = None,
                           salary_range_min: Optional[int] = None,
                           salary_range_max: Optional[int] = None) -> CareerRole:
        """创建职业角色"""
        role = CareerRole(
            name=name,
            description=description,
            level=level,
            path_type=path_type,
            required_skills=required_skills,
            recommended_skills=recommended_skills or [],
            salary_range_min=salary_range_min,
            salary_range_max=salary_range_max,
        )
        self.db.insert("career_roles", role.to_dict())
        return role

    def get_career_role(self, role_id: str) -> Optional[CareerRole]:
        """获取职业角色详情"""
        data = self.db.get("career_roles", role_id)
        return CareerRole.from_dict(data) if data else None

    def list_career_roles(self, path_type: Optional[CareerPathType] = None,
                          level: Optional[int] = None,
                          search: Optional[str] = None,
                          limit: int = 100) -> List[CareerRole]:
        """列出职业角色"""
        filters = {}
        if path_type:
            filters["path_type"] = path_type.value
        if level:
            filters["level"] = level

        rows = self.db.list("career_roles", filters, order_by="level ASC, name ASC", limit=limit)

        if search:
            rows = [r for r in rows if search.lower() in r["name"].lower()]

        return [CareerRole.from_dict(row) for row in rows]

    def add_role_transition(self, from_role_id: str, to_role_id: str,
                            typical_duration_months: int,
                            transition_difficulty: str,
                            key_skills_to_develop: Optional[List[str]] = None) -> RoleTransition:
        """添加角色转换路径"""
        transition = RoleTransition(
            from_role_id=from_role_id,
            to_role_id=to_role_id,
            typical_duration_months=typical_duration_months,
            transition_difficulty=transition_difficulty,
            key_skills_to_develop=key_skills_to_develop or [],
        )
        self.db.insert("role_transitions", transition.to_dict())
        return transition

    def get_role_transitions(self, from_role_id: Optional[str] = None,
                             to_role_id: Optional[str] = None) -> List[RoleTransition]:
        """获取角色转换路径"""
        filters = {}
        if from_role_id:
            filters["from_role_id"] = from_role_id
        if to_role_id:
            filters["to_role_id"] = to_role_id

        rows = self.db.list("role_transitions", filters)
        return [RoleTransition.from_dict(row) for row in rows]

    def recommend_career_paths(self, employee_id: str,
                               current_role_id: Optional[str] = None,
                               limit: int = 5) -> List[CareerPathRecommendation]:
        """推荐职业路径"""
        # 获取员工技能
        emp_skill_rows = self.db.list("employee_skills", {"employee_id": employee_id})
        employee_skills = {}
        for row in emp_skill_rows:
            skill_id = row["skill_id"]
            level_value = row["level"]
            # 转换 level 为数值
            level_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4, "master": 5}
            employee_skills[skill_id] = level_map.get(level_value, 1)

        # 获取所有角色
        all_roles = self.list_career_roles()
        recommendations = []

        for role in all_roles:
            if current_role_id and role.id == current_role_id:
                continue

            # 计算匹配度
            match_score, skill_gaps = self._calculate_role_match(employee_skills, role)

            if match_score > 0.3:  # 只推荐匹配度>30% 的角色
                reasoning = self._generate_career_reasoning(role, match_score, skill_gaps)
                estimated_months = self._estimate_timeline(skill_gaps)

                rec = CareerPathRecommendation(
                    employee_id=employee_id,
                    recommended_role_id=role.id,
                    current_role_id=current_role_id,
                    match_score=match_score,
                    reasoning=reasoning,
                    skill_gaps=skill_gaps,
                    estimated_timeline_months=estimated_months,
                    confidence=min(0.9, match_score + 0.1),
                )
                self.db.insert("career_path_recommendations", rec.to_dict())
                recommendations.append(rec)

        # 按匹配度排序
        recommendations.sort(key=lambda x: x.match_score, reverse=True)
        return recommendations[:limit]

    def _calculate_role_match(self, employee_skills: Dict[str, int],
                              role: CareerRole) -> Tuple[float, Dict[str, int]]:
        """计算角色匹配度和技能差距"""
        required = role.required_skills
        if not required:
            return 0.5, {}

        total_gap = 0
        skill_gaps = {}

        for skill_id, required_level in required.items():
            current_level = employee_skills.get(skill_id, 0)
            gap = required_level - current_level
            if gap > 0:
                total_gap += gap
                skill_gaps[skill_id] = gap

        # 匹配度 = 1 - (总差距 / (技能数 * 5))
        max_possible_gap = len(required) * 5
        match_score = max(0, 1 - (total_gap / max_possible_gap))

        return match_score, skill_gaps

    def _generate_career_reasoning(self, role: CareerRole, match_score: float,
                                   skill_gaps: Dict[str, int]) -> str:
        """生成推荐理由"""
        if match_score >= 0.8:
            base = f"您与{role.name}岗位高度匹配"
        elif match_score >= 0.5:
            base = f"您具备{role.name}岗位的基础能力"
        else:
            base = f"{role.name}岗位可能是您的发展目标"

        if skill_gaps:
            gap_count = len(skill_gaps)
            base += f"，还需要提升{gap_count}项关键技能"

        return base

    def _estimate_timeline(self, skill_gaps: Dict[str, int]) -> int:
        """估算达成时间（月）"""
        if not skill_gaps:
            return 0

        # 假设每个技能等级差距需要 2-3 个月
        total_gap = sum(skill_gaps.values())
        return max(1, int(total_gap * 2.5))

    def save_recommendation(self, recommendation: CareerPathRecommendation) -> str:
        """保存推荐结果"""
        return self.db.insert("career_path_recommendations", recommendation.to_dict())

    def get_recommendations(self, employee_id: str, limit: int = 10) -> List[CareerPathRecommendation]:
        """获取员工的职业路径推荐"""
        rows = self.db.list("career_path_recommendations",
                           {"employee_id": employee_id},
                           order_by="created_at DESC",
                           limit=limit)
        return [CareerPathRecommendation.from_dict(row) for row in rows]


# ============================================================================
# 发展计划服务
# ============================================================================

class DevelopmentPlanService:
    """发展计划服务"""

    def __init__(self, db: CareerDevelopmentDB):
        self.db = db

    def create_plan(self, employee_id: str, plan_name: str,
                    status: DevelopmentPlanStatus = DevelopmentPlanStatus.DRAFT,
                    target_role_id: Optional[str] = None,
                    start_date: Optional[date] = None,
                    target_completion_date: Optional[date] = None,
                    manager_id: Optional[str] = None,
                    mentor_id: Optional[str] = None,
                    notes: Optional[str] = None) -> DevelopmentPlan:
        """创建发展计划"""
        plan = DevelopmentPlan(
            employee_id=employee_id,
            plan_name=plan_name,
            status=status,
            target_role_id=target_role_id,
            start_date=start_date,
            target_completion_date=target_completion_date,
            manager_id=manager_id,
            mentor_id=mentor_id,
            notes=notes,
        )
        self.db.insert("development_plans", plan.to_dict())
        return plan

    def get_plan(self, plan_id: str) -> Optional[DevelopmentPlan]:
        """获取发展计划详情"""
        data = self.db.get("development_plans", plan_id)
        return DevelopmentPlan.from_dict(data) if data else None

    def list_plans(self, employee_id: Optional[str] = None,
                   status: Optional[DevelopmentPlanStatus] = None,
                   limit: int = 100) -> List[DevelopmentPlan]:
        """列出发展计划"""
        filters = {}
        if employee_id:
            filters["employee_id"] = employee_id
        if status:
            filters["status"] = status.value

        rows = self.db.list("development_plans", filters, order_by="created_at DESC", limit=limit)
        return [DevelopmentPlan.from_dict(row) for row in rows]

    def update_plan_status(self, plan_id: str, status: DevelopmentPlanStatus) -> bool:
        """更新计划状态"""
        return self.db.update("development_plans", plan_id, {"status": status.value})

    def create_goal(self, plan_id: str, goal_type: GoalType, title: str,
                    description: str, status: GoalStatus = GoalStatus.NOT_STARTED,
                    skill_id: Optional[str] = None,
                    target_level: Optional[SkillLevel] = None,
                    priority: int = 1,
                    due_date: Optional[date] = None) -> DevelopmentGoal:
        """创建发展目标"""
        goal = DevelopmentGoal(
            plan_id=plan_id,
            goal_type=goal_type,
            title=title,
            description=description,
            status=status,
            skill_id=skill_id,
            target_level=target_level,
            priority=priority,
            due_date=due_date,
        )
        self.db.insert("development_goals", goal.to_dict())
        return goal

    def get_goal(self, goal_id: str) -> Optional[DevelopmentGoal]:
        """获取目标详情"""
        data = self.db.get("development_goals", goal_id)
        return DevelopmentGoal.from_dict(data) if data else None

    def list_goals(self, plan_id: str,
                   status: Optional[GoalStatus] = None,
                   order_by_priority: bool = True) -> List[DevelopmentGoal]:
        """列出计划目标"""
        filters = {"plan_id": plan_id}
        if status:
            filters["status"] = status.value

        order = "priority ASC, due_date ASC" if order_by_priority else "created_at DESC"
        rows = self.db.list("development_goals", filters, order_by=order)
        return [DevelopmentGoal.from_dict(row) for row in rows]

    def update_goal_status(self, goal_id: str, status: GoalStatus,
                           progress_percent: Optional[float] = None) -> bool:
        """更新目标状态"""
        update_data = {"status": status.value}
        if progress_percent is not None:
            update_data["progress_percent"] = progress_percent
        if status == GoalStatus.COMPLETED:
            update_data["completed_at"] = datetime.now().isoformat()
        return self.db.update("development_goals", goal_id, update_data)

    def update_goal_progress(self, goal_id: str, progress_percent: float) -> bool:
        """更新目标进度"""
        return self.db.update("development_goals", goal_id, {"progress_percent": progress_percent})

    def add_activity(self, goal_id: str, activity_type: str, title: str,
                     description: str, hours_spent: float = 0.0,
                     evidence_url: Optional[str] = None) -> DevelopmentActivity:
        """添加发展活动"""
        activity = DevelopmentActivity(
            goal_id=goal_id,
            activity_type=activity_type,
            title=title,
            description=description,
            hours_spent=hours_spent,
            evidence_url=evidence_url,
        )
        self.db.insert("development_activities", activity.to_dict())

        # 更新目标进度
        self._recalculate_goal_progress(goal_id)

        return activity

    def complete_activity(self, activity_id: str, feedback: Optional[str] = None) -> bool:
        """完成发展活动"""
        update_data = {"completed": True, "completed_at": datetime.now().isoformat()}
        if feedback:
            update_data["feedback"] = feedback
        return self.db.update("development_activities", activity_id, update_data)

    def get_activity(self, activity_id: str) -> Optional[DevelopmentActivity]:
        """获取活动详情"""
        data = self.db.get("development_activities", activity_id)
        return DevelopmentActivity.from_dict(data) if data else None

    def list_activities(self, goal_id: str, completed: Optional[bool] = None) -> List[DevelopmentActivity]:
        """列出活动"""
        filters = {"goal_id": goal_id}
        if completed is not None:
            filters["completed"] = 1 if completed else 0

        rows = self.db.list("development_activities", filters, order_by="created_at DESC")
        return [DevelopmentActivity.from_dict(row) for row in rows]

    def _recalculate_goal_progress(self, goal_id: str):
        """重新计算目标进度"""
        activities = self.list_activities(goal_id)
        if not activities:
            return

        completed = sum(1 for a in activities if a.completed)
        progress = (completed / len(activities)) * 100
        self.update_goal_progress(goal_id, progress)

    def get_plan_progress(self, plan_id: str) -> Dict[str, Any]:
        """获取计划进度"""
        goals = self.list_goals(plan_id)
        if not goals:
            return {"total_goals": 0, "completed_goals": 0, "progress_percent": 0}

        completed = sum(1 for g in goals if g.status == GoalStatus.COMPLETED)
        total_progress = sum(g.progress_percent for g in goals) / len(goals)

        return {
            "total_goals": len(goals),
            "completed_goals": completed,
            "in_progress_goals": sum(1 for g in goals if g.status == GoalStatus.IN_PROGRESS),
            "progress_percent": round(total_progress, 1),
        }


# ============================================================================
# 导师匹配服务
# ============================================================================

class MentorshipService:
    """导师匹配服务"""

    def __init__(self, db: CareerDevelopmentDB):
        self.db = db

    def create_mentor_profile(self, employee_id: str,
                              areas_of_expertise: List[str],
                              mentoring_capacity: int = 3,
                              mentoring_style: Optional[str] = None) -> MentorProfile:
        """创建导师档案"""
        profile = MentorProfile(
            employee_id=employee_id,
            areas_of_expertise=areas_of_expertise,
            mentoring_capacity=mentoring_capacity,
            mentoring_style=mentoring_style,
        )
        self.db.insert("mentor_profiles", profile.to_dict())
        return profile

    def get_mentor_profile(self, profile_id: str) -> Optional[MentorProfile]:
        """获取导师档案"""
        data = self.db.get("mentor_profiles", profile_id)
        return MentorProfile.from_dict(data) if data else None

    def get_mentor_by_employee(self, employee_id: str) -> Optional[MentorProfile]:
        """根据员工 ID 获取导师档案"""
        rows = self.db.list("mentor_profiles", {"employee_id": employee_id})
        return MentorProfile.from_dict(rows[0]) if rows else None

    def update_mentor_availability(self, profile_id: str,
                                   availability: str,
                                   current_mentees: Optional[int] = None) -> bool:
        """更新导师可用性"""
        update_data = {"availability": availability}
        if current_mentees is not None:
            update_data["current_mentees"] = current_mentees
        return self.db.update("mentor_profiles", profile_id, update_data)

    def create_mentee_profile(self, employee_id: str,
                              development_goals: Optional[List[str]] = None,
                              preferred_mentor_style: Optional[str] = None) -> MenteeProfile:
        """创建学员档案"""
        profile = MenteeProfile(
            employee_id=employee_id,
            development_goals=development_goals or [],
            preferred_mentor_style=preferred_mentor_style,
        )
        self.db.insert("mentee_profiles", profile.to_dict())
        return profile

    def get_mentee_profile(self, profile_id: str) -> Optional[MenteeProfile]:
        """获取学员档案"""
        data = self.db.get("mentee_profiles", profile_id)
        return MenteeProfile.from_dict(data) if data else None

    def get_mentee_by_employee(self, employee_id: str) -> Optional[MenteeProfile]:
        """根据员工 ID 获取学员档案"""
        rows = self.db.list("mentee_profiles", {"employee_id": employee_id})
        return MenteeProfile.from_dict(rows[0]) if rows else None

    def match_mentor_mentee(self, mentor_id: str, mentee_id: str,
                            match_score: float, match_reason: str,
                            goals: Optional[List[str]] = None,
                            meeting_frequency: str = "biweekly") -> MentorshipMatch:
        """匹配导师和学员"""
        match = MentorshipMatch(
            mentor_id=mentor_id,
            mentee_id=mentee_id,
            match_score=match_score,
            match_reason=match_reason,
            status=MentorshipStatus.PENDING,
            goals=goals or [],
            meeting_frequency=meeting_frequency,
        )
        self.db.insert("mentorship_matches", match.to_dict())

        # 更新导师的学员数量
        mentor = self.get_mentor_profile(mentor_id)
        if mentor:
            self.update_mentor_availability(mentor_id, mentor.availability,
                                           mentor.current_mentees + 1)

        return match

    def auto_match(self, mentee_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """自动为学员匹配导师"""
        mentee = self.get_mentee_by_employee(mentee_id)
        if not mentee:
            return []

        # 获取所有可用导师
        mentor_rows = self.db.list("mentor_profiles", {"availability": "available"})
        mentors = [MentorProfile.from_dict(row) for row in mentor_rows]

        # 过滤掉已满的导师
        mentors = [m for m in mentors if m.current_mentees < m.mentoring_capacity]

        if not mentors:
            return []

        # 计算匹配分数
        matches = []
        for mentor in mentors:
            score, reason = self._calculate_mentor_match(mentor, mentee)
            matches.append({
                "mentor": mentor,
                "score": score,
                "reason": reason,
            })

        # 按分数排序
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limit]

    def _calculate_mentor_match(self, mentor: MentorProfile,
                                mentee: MenteeProfile) -> Tuple[float, str]:
        """计算导师学员匹配度"""
        # 基于技能匹配
        mentee_goals = set(mentee.development_goals)
        mentor_expertise = set(mentor.areas_of_expertise)

        if not mentee_goals:
            return 0.5, "基于基本可用性匹配"

        overlap = len(mentee_goals & mentor_expertise)
        base_score = overlap / len(mentee_goals) if mentee_goals else 0

        # 考虑导师风格
        style_bonus = 0.1 if mentee.preferred_mentor_style == mentor.mentoring_style else 0

        score = min(1.0, base_score + style_bonus)
        reason = f"技能匹配度{int(base_score * 100)}%"
        if style_bonus:
            reason += "，指导风格契合"

        return score, reason

    def accept_mentorship(self, match_id: str, start_date: date) -> bool:
        """接受导师关系"""
        match = self.get_mentorship_match(match_id)
        if not match:
            return False

        update_data = {
            "status": MentorshipStatus.ACTIVE.value,
            "start_date": start_date.isoformat(),
        }
        return self.db.update("mentorship_matches", match_id, update_data)

    def get_mentorship_match(self, match_id: str) -> Optional[MentorshipMatch]:
        """获取导师匹配记录"""
        data = self.db.get("mentorship_matches", match_id)
        return MentorshipMatch.from_dict(data) if data else None

    def list_mentorship_matches(self, mentor_id: Optional[str] = None,
                                mentee_id: Optional[str] = None,
                                status: Optional[MentorshipStatus] = None,
                                limit: int = 100) -> List[MentorshipMatch]:
        """列出导师匹配记录"""
        filters = {}
        if mentor_id:
            filters["mentor_id"] = mentor_id
        if mentee_id:
            filters["mentee_id"] = mentee_id
        if status:
            filters["status"] = status.value

        rows = self.db.list("mentorship_matches", filters, order_by="created_at DESC", limit=limit)
        return [MentorshipMatch.from_dict(row) for row in rows]

    def add_mentorship_session(self, match_id: str, session_date: datetime,
                               duration_minutes: int = 60,
                               topics_discussed: Optional[List[str]] = None,
                               notes: Optional[str] = None,
                               action_items: Optional[List[str]] = None,
                               next_session_date: Optional[date] = None) -> MentorshipSession:
        """添加导师会话记录"""
        session = MentorshipSession(
            match_id=match_id,
            session_date=session_date,
            duration_minutes=duration_minutes,
            topics_discussed=topics_discussed or [],
            notes=notes,
            action_items=action_items or [],
            next_session_date=next_session_date,
        )
        self.db.insert("mentorship_sessions", session.to_dict())
        return session

    def list_mentorship_sessions(self, match_id: str, limit: int = 50) -> List[MentorshipSession]:
        """列出导师会话"""
        rows = self.db.list("mentorship_sessions", {"match_id": match_id},
                           order_by="session_date DESC", limit=limit)
        return [MentorshipSession.from_dict(row) for row in rows]


# ============================================================================
# 晋升规划服务
# ============================================================================

class PromotionService:
    """晋升规划服务"""

    def __init__(self, db: CareerDevelopmentDB):
        self.db = db

    def assess_promotion_readiness(self, employee_id: str, target_role_id: str,
                                   current_role_id: Optional[str] = None) -> PromotionReadinessAssessment:
        """评估晋升准备度"""
        target_role = self.db.get("career_roles", target_role_id)
        if not target_role:
            raise ValueError(f"Role {target_role_id} not found")

        target_role_obj = CareerRole.from_dict(target_role)

        # 获取员工技能
        emp_skill_rows = self.db.list("employee_skills", {"employee_id": employee_id})
        employee_skills = {}
        for row in emp_skill_rows:
            employee_skills[row["skill_id"]] = {
                "level": row["level"],
                "verified": row.get("verified", False),
            }

        # 计算技能差距
        skill_gaps = {}
        strengths = []
        total_gap = 0
        level_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4, "master": 5}

        for skill_id, required_level in target_role_obj.required_skills.items():
            emp_data = employee_skills.get(skill_id, {"level": "beginner", "verified": False})
            current_level = level_map.get(emp_data["level"], 1)
            gap = required_level - current_level

            skill_gaps[skill_id] = {
                "current": current_level,
                "required": required_level,
                "gap": gap,
            }

            if gap <= 0:
                strengths.append(skill_id)
            else:
                total_gap += gap

        # 计算准备度分数
        max_gap = len(target_role_obj.required_skills) * 5
        readiness_score = max(0, 100 - (total_gap / max_gap * 100)) if max_gap > 0 else 0

        # 确定准备度等级
        if readiness_score >= 90:
            overall_readiness = PromotionReadiness.EXCEEDED
        elif readiness_score >= 75:
            overall_readiness = PromotionReadiness.READY
        elif readiness_score >= 50:
            overall_readiness = PromotionReadiness.DEVELOPING
        else:
            overall_readiness = PromotionReadiness.NOT_READY

        # 生成发展建议
        recommendations = self._generate_promotion_recommendations(skill_gaps, target_role_obj)

        # 估算时间
        estimated_months = int(total_gap * 2) if total_gap > 0 else 0

        assessment = PromotionReadinessAssessment(
            employee_id=employee_id,
            target_role_id=target_role_id,
            current_role_id=current_role_id,
            overall_readiness=overall_readiness,
            readiness_score=round(readiness_score, 1),
            skill_gaps=skill_gaps,
            strengths=strengths,
            development_recommendations=recommendations,
            estimated_timeline_months=estimated_months if estimated_months > 0 else None,
        )

        self.db.insert("promotion_readiness_assessments", assessment.to_dict())
        return assessment

    def _generate_promotion_recommendations(self, skill_gaps: Dict[str, Dict],
                                            role: CareerRole) -> List[str]:
        """生成晋升发展建议"""
        recommendations = []

        # 按差距大小排序
        sorted_gaps = sorted(skill_gaps.items(), key=lambda x: x[1]["gap"], reverse=True)

        for skill_id, gap_data in sorted_gaps[:3]:  # 只返回前 3 个最大差距
            if gap_data["gap"] > 0:
                skill = self.db.get("skills", skill_id)
                skill_name = skill["name"] if skill else skill_id
                recommendations.append(f"提升{skill_name}技能至等级{gap_data['required']}")

        if not recommendations:
            recommendations.append("您已具备该岗位所需的核心技能，可以考虑申请晋升")

        return recommendations

    def get_assessment(self, assessment_id: str) -> Optional[PromotionReadinessAssessment]:
        """获取评估详情"""
        data = self.db.get("promotion_readiness_assessments", assessment_id)
        return PromotionReadinessAssessment.from_dict(data) if data else None

    def list_assessments(self, employee_id: str, limit: int = 10) -> List[PromotionReadinessAssessment]:
        """列出评估历史"""
        rows = self.db.list("promotion_readiness_assessments",
                           {"employee_id": employee_id},
                           order_by="created_at DESC",
                           limit=limit)
        return [PromotionReadinessAssessment.from_dict(row) for row in rows]

    def record_promotion(self, employee_id: str, to_role_id: str,
                         promotion_date: date,
                         from_role_id: Optional[str] = None,
                         promotion_type: str = "promotion",
                         decision_maker_id: Optional[str] = None,
                         notes: Optional[str] = None) -> PromotionHistory:
        """记录晋升历史"""
        history = PromotionHistory(
            employee_id=employee_id,
            from_role_id=from_role_id,
            to_role_id=to_role_id,
            promotion_date=promotion_date,
            promotion_type=promotion_type,
            decision_maker_id=decision_maker_id,
            notes=notes,
        )
        self.db.insert("promotion_history", history.to_dict())
        return history

    def get_promotion_history(self, employee_id: str) -> List[PromotionHistory]:
        """获取员工晋升历史"""
        rows = self.db.list("promotion_history", {"employee_id": employee_id},
                           order_by="promotion_date DESC")
        return [PromotionHistory.from_dict(row) for row in rows]


# ============================================================================
# 统一外观服务
# ============================================================================

class CareerDevelopmentService:
    """职业发展统一外观服务"""

    def __init__(self, db: Optional[CareerDevelopmentDB] = None):
        self.db = db or CareerDevelopmentDB()
        self.skill_graph = SkillGraphService(self.db)
        self.employee_skill = EmployeeSkillService(self.db)
        self.career_path = CareerPathService(self.db)
        self.development_plan = DevelopmentPlanService(self.db)
        self.mentorship = MentorshipService(self.db)
        self.promotion = PromotionService(self.db)

    def get_dashboard(self, employee_id: str) -> Dict[str, Any]:
        """获取职业发展仪表盘"""
        # 获取员工技能
        skills_data = self.employee_skill.list_employee_skills(employee_id)
        skill_count = len(skills_data)

        # 获取发展计划
        plans = self.development_plan.list_plans(employee_id, status=DevelopmentPlanStatus.ACTIVE)
        active_plan = plans[0] if plans else None
        plan_progress = None
        if active_plan:
            plan_progress = self.development_plan.get_plan_progress(active_plan.id)

        # 获取职业推荐
        recommendations = self.career_path.get_recommendations(employee_id, limit=3)

        # 获取导师关系
        mentee = self.mentorship.get_mentee_by_employee(employee_id)
        active_mentorship = None
        if mentee:
            matches = self.mentorship.list_mentorship_matches(
                mentee_id=mentee.id,
                status=MentorshipStatus.ACTIVE
            )
            if matches:
                active_mentorship = matches[0]

        return {
            "skill_count": skill_count,
            "active_plan": active_plan.to_dict() if active_plan else None,
            "plan_progress": plan_progress,
            "top_recommendations": [r.to_dict() for r in recommendations],
            "has_mentor": active_mentorship is not None,
            "mentorship_details": active_mentorship.to_dict() if active_mentorship else None,
        }
