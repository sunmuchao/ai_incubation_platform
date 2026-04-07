"""
P16 职业发展规划 - API 路由层
版本：v16.0.0
主题：职业发展规划 API 端点
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field

from services.p16_career_development_service import (
    CareerDevelopmentService,
    SkillGraphService,
    EmployeeSkillService,
    CareerPathService,
    DevelopmentPlanService,
    MentorshipService,
    PromotionService,
)
from models.p16_models import (
    SkillLevel, SkillCategory, CareerPathType, MentorshipStatus,
    DevelopmentPlanStatus, GoalType, GoalStatus, DependencyType,
    PromotionReadiness, CareerDevelopmentDB,
)


# ============================================================================
# Pydantic 请求模型
# ============================================================================

class SkillCreateRequest(BaseModel):
    name: str
    description: str = ""
    category: str
    parent_skill_id: Optional[str] = None
    tags: Optional[List[str]] = None


class SkillUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class SkillDependencyRequest(BaseModel):
    from_skill_id: str
    to_skill_id: str
    dependency_type: str
    strength: float = 1.0


class EmployeeSkillRequest(BaseModel):
    employee_id: str
    skill_id: str
    level: str
    years_of_experience: float = 0
    self_assessed: bool = True
    evidence: Optional[str] = None


class CareerRoleRequest(BaseModel):
    name: str
    description: str = ""
    level: int
    path_type: str
    required_skills: Dict[str, int] = Field(default_factory=dict)
    recommended_skills: Optional[List[str]] = None
    salary_range_min: Optional[int] = None
    salary_range_max: Optional[int] = None


class RoleTransitionRequest(BaseModel):
    from_role_id: str
    to_role_id: str
    typical_duration_months: int
    transition_difficulty: str
    key_skills_to_develop: Optional[List[str]] = None


class DevelopmentPlanRequest(BaseModel):
    employee_id: str
    plan_name: str
    status: str = "draft"
    target_role_id: Optional[str] = None
    start_date: Optional[str] = None
    target_completion_date: Optional[str] = None
    manager_id: Optional[str] = None
    mentor_id: Optional[str] = None
    notes: Optional[str] = None


class DevelopmentGoalRequest(BaseModel):
    plan_id: str
    goal_type: str
    title: str
    description: str
    skill_id: Optional[str] = None
    target_level: Optional[str] = None
    priority: int = 1
    due_date: Optional[str] = None


class DevelopmentActivityRequest(BaseModel):
    goal_id: str
    activity_type: str
    title: str
    description: str
    hours_spent: float = 0.0
    evidence_url: Optional[str] = None


class MentorProfileRequest(BaseModel):
    employee_id: str
    areas_of_expertise: List[str]
    mentoring_capacity: int = 3
    mentoring_style: Optional[str] = None


class MenteeProfileRequest(BaseModel):
    employee_id: str
    development_goals: Optional[List[str]] = None
    preferred_mentor_style: Optional[str] = None


class MentorshipMatchRequest(BaseModel):
    mentor_id: str
    mentee_id: str
    goals: Optional[List[str]] = None
    meeting_frequency: str = "biweekly"


class MentorshipSessionRequest(BaseModel):
    match_id: str
    session_date: str
    duration_minutes: int = 60
    topics_discussed: Optional[List[str]] = None
    notes: Optional[str] = None
    action_items: Optional[List[str]] = None


class PromotionAssessmentRequest(BaseModel):
    employee_id: str
    target_role_id: str
    current_role_id: Optional[str] = None


class PromotionRecordRequest(BaseModel):
    employee_id: str
    to_role_id: str
    from_role_id: Optional[str] = None
    promotion_date: str
    promotion_type: str = "promotion"
    decision_maker_id: Optional[str] = None
    notes: Optional[str] = None


# ============================================================================
# 路由定义
# ============================================================================

router = APIRouter(prefix="/api/career-development", tags=["职业发展"])

# 初始化服务
career_service = CareerDevelopmentService()


# ============================================================================
# 技能图谱 API
# ============================================================================

@router.post("/skills", summary="创建技能")
async def create_skill(request: SkillCreateRequest):
    """创建新的技能定义"""
    try:
        category = SkillCategory(request.category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {request.category}")

    skill = career_service.skill_graph.create_skill(
        name=request.name,
        description=request.description,
        category=category,
        parent_skill_id=request.parent_skill_id,
        tags=request.tags,
    )
    return {"success": True, "data": skill.to_dict()}


@router.get("/skills/{skill_id}", summary="获取技能详情")
async def get_skill(skill_id: str):
    """获取技能详细信息"""
    skill = career_service.skill_graph.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"success": True, "data": skill.to_dict()}


@router.get("/skills", summary="列出技能")
async def list_skills(
    category: Optional[str] = Query(None),
    parent_skill_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """列出技能，支持筛选和搜索"""
    category_enum = SkillCategory(category) if category else None

    # 处理 parent_skill_id 参数：空字符串表示获取顶级技能
    if parent_skill_id == "":
        parent_skill_id = ""

    skills = career_service.skill_graph.list_skills(
        category=category_enum,
        parent_skill_id=parent_skill_id,
        search=search,
        limit=limit,
    )
    return {"success": True, "data": [s.to_dict() for s in skills], "total": len(skills)}


@router.put("/skills/{skill_id}", summary="更新技能")
async def update_skill(skill_id: str, request: SkillUpdateRequest):
    """更新技能信息"""
    skill = career_service.skill_graph.update_skill(
        skill_id=skill_id,
        name=request.name,
        description=request.description,
        tags=request.tags,
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"success": True, "data": skill.to_dict()}


@router.delete("/skills/{skill_id}", summary="删除技能")
async def delete_skill(skill_id: str):
    """删除技能"""
    success = career_service.skill_graph.delete_skill(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"success": True}


@router.post("/skills/dependencies", summary="添加技能依赖")
async def add_skill_dependency(request: SkillDependencyRequest):
    """添加技能之间的依赖关系"""
    try:
        dep_type = DependencyType(request.dependency_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid dependency type: {request.dependency_type}")

    dep = career_service.skill_graph.add_dependency(
        from_skill_id=request.from_skill_id,
        to_skill_id=request.to_skill_id,
        dependency_type=dep_type,
        strength=request.strength,
    )
    return {"success": True, "data": dep.to_dict()}


@router.get("/skills/{skill_id}/prerequisites", summary="获取前置技能")
async def get_prerequisites(skill_id: str):
    """获取技能的所有前置技能"""
    prereqs = career_service.skill_graph.get_prerequisites(skill_id)
    return {
        "success": True,
        "data": [
            {"skill": s.to_dict(), "dependency_type": t.value, "strength": str}
            for s, t, s in prereqs
        ]
    }


@router.get("/skills/{skill_id}/dependents", summary="获取依赖技能")
async def get_dependent_skills(skill_id: str):
    """获取依赖该技能的其他技能"""
    dependents = career_service.skill_graph.get_dependent_skills(skill_id)
    return {
        "success": True,
        "data": [
            {"skill": s.to_dict(), "dependency_type": t.value, "strength": str}
            for s, t, s in dependents
        ]
    }


@router.get("/skills/tree", summary="获取技能树")
async def get_skill_tree(root_skill_id: Optional[str] = Query(None)):
    """获取技能树结构"""
    tree = career_service.skill_graph.get_skill_tree(root_skill_id)
    return {"success": True, "data": tree}


@router.get("/skills/path", summary="获取学习路径")
async def get_learning_path(
    from_skill_id: str = Query(...),
    to_skill_id: str = Query(...)
):
    """获取从起点到目标技能的学习路径"""
    path = career_service.skill_graph.get_learning_path(from_skill_id, to_skill_id)
    return {
        "success": True,
        "data": [s.to_dict() for s in path],
        "path_length": len(path),
    }


# ============================================================================
# 员工技能 API
# ============================================================================

@router.post("/employees/skills", summary="添加员工技能")
async def add_employee_skill(request: EmployeeSkillRequest):
    """为员工添加技能记录"""
    try:
        level = SkillLevel(request.level)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid skill level: {request.level}")

    emp_skill = career_service.employee_skill.add_employee_skill(
        employee_id=request.employee_id,
        skill_id=request.skill_id,
        level=level,
        years_of_experience=request.years_of_experience,
        self_assessed=request.self_assessed,
        evidence=request.evidence,
    )
    return {"success": True, "data": emp_skill.to_dict()}


@router.get("/employees/{employee_id}/skills", summary="获取员工技能列表")
async def get_employee_skills(
    employee_id: str,
    level: Optional[str] = Query(None),
    category: Optional[str] = Query(None)
):
    """获取员工的所有技能"""
    level_enum = SkillLevel(level) if level else None
    category_enum = SkillCategory(category) if category else None

    skills_data = career_service.employee_skill.list_employee_skills(
        employee_id=employee_id,
        level=level_enum,
        category=category_enum,
    )
    return {
        "success": True,
        "data": [
            {
                "employee_skill": es["employee_skill"].to_dict(),
                "skill": es["skill"].to_dict(),
            }
            for es in skills_data
        ],
        "total": len(skills_data),
    }


@router.post("/employees/skills/verify", summary="验证技能")
async def verify_skill(record_id: str = Query(...), verified: bool = Query(True)):
    """验证员工技能"""
    success = career_service.employee_skill.verify_skill(record_id, verified)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"success": True}


@router.post("/employees/skills/growth", summary="记录技能成长")
async def record_skill_growth(
    employee_id: str = Query(...),
    skill_id: str = Query(...),
    from_level: str = Query(...),
    to_level: str = Query(...),
    growth_type: str = Query(...)
):
    """记录员工技能成长"""
    try:
        from_lvl = SkillLevel(from_level)
        to_lvl = SkillLevel(to_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid skill level")

    growth = career_service.employee_skill.record_skill_growth(
        employee_id=employee_id,
        skill_id=skill_id,
        from_level=from_lvl,
        to_level=to_lvl,
        growth_type=growth_type,
    )
    return {"success": True, "data": growth.to_dict()}


@router.get("/employees/{employee_id}/skills/growth-history", summary="获取技能成长历史")
async def get_skill_growth_history(
    employee_id: str,
    skill_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    """获取员工的技能成长历史记录"""
    history = career_service.employee_skill.get_skill_growth_history(
        employee_id=employee_id,
        skill_id=skill_id,
        limit=limit,
    )
    return {
        "success": True,
        "data": [h.to_dict() for h in history],
        "total": len(history),
    }


# ============================================================================
# 职业路径 API
# ============================================================================

@router.post("/career-roles", summary="创建职业角色")
async def create_career_role(request: CareerRoleRequest):
    """创建新的职业角色定义"""
    try:
        path_type = CareerPathType(request.path_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid path type: {request.path_type}")

    role = career_service.career_path.create_career_role(
        name=request.name,
        description=request.description,
        level=request.level,
        path_type=path_type,
        required_skills=request.required_skills,
        recommended_skills=request.recommended_skills,
        salary_range_min=request.salary_range_min,
        salary_range_max=request.salary_range_max,
    )
    return {"success": True, "data": role.to_dict()}


@router.get("/career-roles/{role_id}", summary="获取职业角色详情")
async def get_career_role(role_id: str):
    """获取职业角色详细信息"""
    role = career_service.career_path.get_career_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return {"success": True, "data": role.to_dict()}


@router.get("/career-roles", summary="列出职业角色")
async def list_career_roles(
    path_type: Optional[str] = Query(None),
    level: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """列出职业角色"""
    path_type_enum = CareerPathType(path_type) if path_type else None
    roles = career_service.career_path.list_career_roles(
        path_type=path_type_enum,
        level=level,
        search=search,
        limit=limit,
    )
    return {"success": True, "data": [r.to_dict() for r in roles], "total": len(roles)}


@router.post("/role-transitions", summary="添加角色转换路径")
async def add_role_transition(request: RoleTransitionRequest):
    """添加两个角色之间的转换路径"""
    transition = career_service.career_path.add_role_transition(
        from_role_id=request.from_role_id,
        to_role_id=request.to_role_id,
        typical_duration_months=request.typical_duration_months,
        transition_difficulty=request.transition_difficulty,
        key_skills_to_develop=request.key_skills_to_develop,
    )
    return {"success": True, "data": transition.to_dict()}


@router.get("/role-transitions", summary="获取角色转换路径")
async def get_role_transitions(
    from_role_id: Optional[str] = Query(None),
    to_role_id: Optional[str] = Query(None)
):
    """获取角色转换路径列表"""
    transitions = career_service.career_path.get_role_transitions(
        from_role_id=from_role_id,
        to_role_id=to_role_id,
    )
    return {"success": True, "data": [t.to_dict() for t in transitions]}


@router.post("/career-paths/recommend", summary="推荐职业路径")
async def recommend_career_paths(
    employee_id: str = Query(...),
    current_role_id: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=20)
):
    """为员工推荐职业路径"""
    recommendations = career_service.career_path.recommend_career_paths(
        employee_id=employee_id,
        current_role_id=current_role_id,
        limit=limit,
    )
    return {
        "success": True,
        "data": [r.to_dict() for r in recommendations],
        "total": len(recommendations),
    }


@router.get("/employees/{employee_id}/career-recommendations", summary="获取职业推荐")
async def get_career_recommendations(
    employee_id: str,
    limit: int = Query(10, ge=1, le=50)
):
    """获取员工的职业路径推荐历史"""
    recommendations = career_service.career_path.get_recommendations(
        employee_id=employee_id,
        limit=limit,
    )
    return {
        "success": True,
        "data": [r.to_dict() for r in recommendations],
        "total": len(recommendations),
    }


# ============================================================================
# 发展计划 API
# ============================================================================

@router.post("/development-plans", summary="创建发展计划")
async def create_development_plan(request: DevelopmentPlanRequest):
    """创建员工发展计划"""
    try:
        status = DevelopmentPlanStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

    start_date = date.fromisoformat(request.start_date) if request.start_date else None
    target_date = date.fromisoformat(request.target_completion_date) if request.target_completion_date else None

    plan = career_service.development_plan.create_plan(
        employee_id=request.employee_id,
        plan_name=request.plan_name,
        status=status,
        target_role_id=request.target_role_id,
        start_date=start_date,
        target_completion_date=target_date,
        manager_id=request.manager_id,
        mentor_id=request.mentor_id,
        notes=request.notes,
    )
    return {"success": True, "data": plan.to_dict()}


@router.get("/development-plans/{plan_id}", summary="获取发展计划详情")
async def get_development_plan(plan_id: str):
    """获取发展计划详细信息"""
    plan = career_service.development_plan.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"success": True, "data": plan.to_dict()}


@router.get("/employees/{employee_id}/development-plans", summary="获取员工发展计划")
async def get_employee_development_plans(
    employee_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """获取员工的发展计划列表"""
    status_enum = DevelopmentPlanStatus(status) if status else None
    plans = career_service.development_plan.list_plans(
        employee_id=employee_id,
        status=status_enum,
        limit=limit,
    )
    return {
        "success": True,
        "data": [p.to_dict() for p in plans],
        "total": len(plans),
    }


@router.put("/development-plans/{plan_id}/status", summary="更新计划状态")
async def update_plan_status(plan_id: str, status: str = Query(...)):
    """更新发展计划状态"""
    try:
        status_enum = DevelopmentPlanStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    success = career_service.development_plan.update_plan_status(plan_id, status_enum)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"success": True}


@router.post("/development-plans/goals", summary="创建发展目标")
async def create_development_goal(request: DevelopmentGoalRequest):
    """为发展计划添加目标"""
    try:
        goal_type = GoalType(request.goal_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid goal type: {request.goal_type}")

    target_level = SkillLevel(request.target_level) if request.target_level else None
    due_date = date.fromisoformat(request.due_date) if request.due_date else None

    goal = career_service.development_plan.create_goal(
        plan_id=request.plan_id,
        goal_type=goal_type,
        title=request.title,
        description=request.description,
        skill_id=request.skill_id,
        target_level=target_level,
        priority=request.priority,
        due_date=due_date,
    )
    return {"success": True, "data": goal.to_dict()}


@router.get("/development-plans/{plan_id}/goals", summary="获取计划目标")
async def get_development_goals(
    plan_id: str,
    status: Optional[str] = Query(None)
):
    """获取发展计划的所有目标"""
    status_enum = GoalStatus(status) if status else None
    goals = career_service.development_plan.list_goals(
        plan_id=plan_id,
        status=status_enum,
    )
    return {
        "success": True,
        "data": [g.to_dict() for g in goals],
        "total": len(goals),
    }


@router.put("/development-goals/{goal_id}/status", summary="更新目标状态")
async def update_goal_status(
    goal_id: str,
    status: str = Query(...),
    progress_percent: Optional[float] = Query(None)
):
    """更新发展目标状态"""
    try:
        status_enum = GoalStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    success = career_service.development_plan.update_goal_status(
        goal_id, status_enum, progress_percent
    )
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"success": True}


@router.post("/development-goals/activities", summary="添加发展活动")
async def add_development_activity(request: DevelopmentActivityRequest):
    """为发展目标添加活动"""
    activity = career_service.development_plan.add_activity(
        goal_id=request.goal_id,
        activity_type=request.activity_type,
        title=request.title,
        description=request.description,
        hours_spent=request.hours_spent,
        evidence_url=request.evidence_url,
    )
    return {"success": True, "data": activity.to_dict()}


@router.post("/development-activities/{activity_id}/complete", summary="完成活动")
async def complete_activity(activity_id: str, feedback: Optional[str] = Query(None)):
    """标记发展活动为完成"""
    success = career_service.development_plan.complete_activity(activity_id, feedback)
    if not success:
        raise HTTPException(status_code=404, detail="Activity not found")
    return {"success": True}


@router.get("/development-goals/{goal_id}/activities", summary="获取目标活动")
async def get_goal_activities(
    goal_id: str,
    completed: Optional[bool] = Query(None)
):
    """获取发展目标的所有活动"""
    activities = career_service.development_plan.list_activities(goal_id, completed)
    return {
        "success": True,
        "data": [a.to_dict() for a in activities],
        "total": len(activities),
    }


@router.get("/development-plans/{plan_id}/progress", summary="获取计划进度")
async def get_plan_progress(plan_id: str):
    """获取发展计划的整体进度"""
    progress = career_service.development_plan.get_plan_progress(plan_id)
    return {"success": True, "data": progress}


# ============================================================================
# 导师匹配 API
# ============================================================================

@router.post("/mentors", summary="创建导师档案")
async def create_mentor_profile(request: MentorProfileRequest):
    """创建导师档案"""
    profile = career_service.mentorship.create_mentor_profile(
        employee_id=request.employee_id,
        areas_of_expertise=request.areas_of_expertise,
        mentoring_capacity=request.mentoring_capacity,
        mentoring_style=request.mentoring_style,
    )
    return {"success": True, "data": profile.to_dict()}


@router.get("/mentors/{profile_id}", summary="获取导师档案")
async def get_mentor_profile(profile_id: str):
    """获取导师档案详情"""
    profile = career_service.mentorship.get_mentor_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Mentor profile not found")
    return {"success": True, "data": profile.to_dict()}


@router.get("/employees/{employee_id}/mentor-profile", summary="获取员工导师档案")
async def get_mentor_by_employee(employee_id: str):
    """根据员工 ID 获取导师档案"""
    profile = career_service.mentorship.get_mentor_by_employee(employee_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Mentor profile not found")
    return {"success": True, "data": profile.to_dict()}


@router.post("/mentees", summary="创建学员档案")
async def create_mentee_profile(request: MenteeProfileRequest):
    """创建学员档案"""
    profile = career_service.mentorship.create_mentee_profile(
        employee_id=request.employee_id,
        development_goals=request.development_goals,
        preferred_mentor_style=request.preferred_mentor_style,
    )
    return {"success": True, "data": profile.to_dict()}


@router.get("/employees/{employee_id}/mentee-profile", summary="获取学员档案")
async def get_mentee_by_employee(employee_id: str):
    """根据员工 ID 获取学员档案"""
    profile = career_service.mentorship.get_mentee_by_employee(employee_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Mentee profile not found")
    return {"success": True, "data": profile.to_dict()}


@router.post("/mentorship/auto-match", summary="自动匹配导师")
async def auto_match_mentor(
    mentee_id: str = Query(...),
    limit: int = Query(3, ge=1, le=10)
):
    """为学员自动匹配导师"""
    matches = career_service.mentorship.auto_match(mentee_id, limit)
    return {
        "success": True,
        "data": [
            {
                "mentor": m["mentor"].to_dict(),
                "score": m["score"],
                "reason": m["reason"],
            }
            for m in matches
        ],
        "total": len(matches),
    }


@router.post("/mentorship/matches", summary="创建导师匹配")
async def create_mentorship_match(request: MentorshipMatchRequest):
    """创建导师学员匹配记录"""
    # 获取 mentee profile
    mentee = career_service.mentorship.get_mentee_by_employee(request.mentee_id)
    if not mentee:
        raise HTTPException(status_code=400, detail="Mentee profile not found")

    # 计算匹配分数
    mentor = career_service.mentorship.get_mentor_by_employee(request.mentor_id)
    if not mentor:
        raise HTTPException(status_code=400, detail="Mentor profile not found")

    score, reason = career_service.mentorship._calculate_mentor_match(mentor, mentee)

    match = career_service.mentorship.match_mentor_mentee(
        mentor_id=request.mentor_id,
        mentee_id=request.mentee_id,
        match_score=score,
        match_reason=reason,
        goals=request.goals,
        meeting_frequency=request.meeting_frequency,
    )
    return {"success": True, "data": match.to_dict()}


@router.post("/mentorship/matches/{match_id}/accept", summary="接受导师关系")
async def accept_mentorship(match_id: str, start_date: str = Query(...)):
    """接受导师匹配"""
    try:
        start = date.fromisoformat(start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    success = career_service.mentorship.accept_mentorship(match_id, start)
    if not success:
        raise HTTPException(status_code=404, detail="Match not found")
    return {"success": True}


@router.get("/mentorship/matches", summary="获取导师匹配列表")
async def get_mentorship_matches(
    mentor_id: Optional[str] = Query(None),
    mentee_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """获取导师匹配记录列表"""
    status_enum = MentorshipStatus(status) if status else None
    matches = career_service.mentorship.list_mentorship_matches(
        mentor_id=mentor_id,
        mentee_id=mentee_id,
        status=status_enum,
        limit=limit,
    )
    return {
        "success": True,
        "data": [m.to_dict() for m in matches],
        "total": len(matches),
    }


@router.post("/mentorship/sessions", summary="添加导师会话")
async def add_mentorship_session(request: MentorshipSessionRequest):
    """添加导师会话记录"""
    try:
        session_date = datetime.fromisoformat(request.session_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    session = career_service.mentorship.add_mentorship_session(
        match_id=request.match_id,
        session_date=session_date,
        duration_minutes=request.duration_minutes,
        topics_discussed=request.topics_discussed,
        notes=request.notes,
        action_items=request.action_items,
    )
    return {"success": True, "data": session.to_dict()}


@router.get("/mentorship/matches/{match_id}/sessions", summary="获取导师会话列表")
async def get_mentorship_sessions(
    match_id: str,
    limit: int = Query(50, ge=1, le=500)
):
    """获取导师会话历史记录"""
    sessions = career_service.mentorship.list_mentorship_sessions(match_id, limit)
    return {
        "success": True,
        "data": [s.to_dict() for s in sessions],
        "total": len(sessions),
    }


# ============================================================================
# 晋升规划 API
# ============================================================================

@router.post("/promotion/assess", summary="评估晋升准备度")
async def assess_promotion_readiness(request: PromotionAssessmentRequest):
    """评估员工晋升准备度"""
    assessment = career_service.promotion.assess_promotion_readiness(
        employee_id=request.employee_id,
        target_role_id=request.target_role_id,
        current_role_id=request.current_role_id,
    )
    return {"success": True, "data": assessment.to_dict()}


@router.get("/promotion/assessments/{assessment_id}", summary="获取评估详情")
async def get_promotion_assessment(assessment_id: str):
    """获取晋升准备度评估详情"""
    assessment = career_service.promotion.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"success": True, "data": assessment.to_dict()}


@router.get("/employees/{employee_id}/promotion-assessments", summary="获取评估历史")
async def get_promotion_assessment_history(
    employee_id: str,
    limit: int = Query(10, ge=1, le=100)
):
    """获取员工的晋升评估历史"""
    assessments = career_service.promotion.list_assessments(employee_id, limit)
    return {
        "success": True,
        "data": [a.to_dict() for a in assessments],
        "total": len(assessments),
    }


@router.post("/promotion/record", summary="记录晋升历史")
async def record_promotion(request: PromotionRecordRequest):
    """记录员工晋升历史"""
    try:
        promotion_date = date.fromisoformat(request.promotion_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    history = career_service.promotion.record_promotion(
        employee_id=request.employee_id,
        to_role_id=request.to_role_id,
        promotion_date=promotion_date,
        from_role_id=request.from_role_id,
        promotion_type=request.promotion_type,
        decision_maker_id=request.decision_maker_id,
        notes=request.notes,
    )
    return {"success": True, "data": history.to_dict()}


@router.get("/employees/{employee_id}/promotion-history", summary="获取晋升历史")
async def get_promotion_history(employee_id: str):
    """获取员工的晋升历史记录"""
    history = career_service.promotion.get_promotion_history(employee_id)
    return {
        "success": True,
        "data": [h.to_dict() for h in history],
        "total": len(history),
    }


# ============================================================================
# 仪表盘 API
# ============================================================================

@router.get("/employees/{employee_id}/dashboard", summary="获取职业发展仪表盘")
async def get_career_dashboard(employee_id: str):
    """获取员工职业发展综合仪表盘"""
    dashboard = career_service.get_dashboard(employee_id)
    return {"success": True, "data": dashboard}
