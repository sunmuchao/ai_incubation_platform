"""
P7 智能匹配算法 API

提供基于技能、历史表现和用户偏好的智能匹配功能
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/matching", tags=["P7-智能匹配"])

# 导入服务
from services.matching_service import (
    matching_service, MatchScore, JobRequirement, MatchingConfig
)


# ==================== 请求/响应模型 ====================

class SkillRequirement(BaseModel):
    """技能需求"""
    skill_name: str
    importance: int = Field(ge=1, le=5, description="重要程度 1-5")
    min_level: Optional[str] = Field(None, description="最低技能等级要求")


class JobRequirementCreate(BaseModel):
    """创建职位需求"""
    title: str
    description: str
    required_skills: Dict[str, int] = Field(default_factory=dict)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    preferred_level: Optional[str] = None
    category: Optional[str] = None
    urgency: int = Field(ge=1, le=5, default=3)
    preferences: Dict[str, Any] = Field(default_factory=dict)


class MatchRequest(BaseModel):
    """匹配请求"""
    requirement: JobRequirementCreate
    user_id: Optional[str] = None
    config: Optional[Dict[str, float]] = None


class MatchResult(BaseModel):
    """匹配结果 (v2 增强)"""
    employee_id: str
    employee_name: str
    overall_score: float
    skill_score: float
    performance_score: float
    preference_score: float
    price_score: float
    availability_score: float
    timezone_score: float = 0.0  # v2 新增：时区匹配分数
    language_score: float = 0.0  # v2 新增：语言匹配分数
    match_reasons: List[str]
    recommendation: str


class MatchResponse(BaseModel):
    """匹配响应 (v2 增强)"""
    requirement_id: str
    total_matches: int
    matches: List[MatchResult]
    search_time_ms: float
    algorithm_version: str = "v2.0"  # v2 版本号


class ExplanationResponse(BaseModel):
    """推荐解释响应"""
    employee_id: str
    employee_name: str
    overall_match: str
    top_reasons: List[str]
    score_breakdown: Dict[str, str]
    strengths: List[str]
    considerations: List[str]


class MatchFeedbackRequest(BaseModel):
    """匹配反馈请求"""
    requirement_id: str
    employee_id: str
    selected: bool
    feedback: Optional[str] = None


class EmployeeSkillsUpdate(BaseModel):
    """员工技能更新"""
    skills: Dict[str, str]
    hourly_rate: Optional[float] = None
    status: Optional[str] = None


class UserPreferencesUpdate(BaseModel):
    """用户偏好更新"""
    preferred_categories: Optional[List[str]] = None
    price_range: Optional[Dict[str, float]] = None
    preferred_level: Optional[str] = None
    preferred_skills: Optional[List[str]] = None


# ==================== API 端点 ====================

@router.post("/requirements", response_model=Dict[str, str])
async def create_job_requirement(req: JobRequirementCreate):
    """
    创建职位需求

    - **title**: 职位名称
    - **description**: 职位描述
    - **required_skills**: 需要的技能字典 {技能名：重要程度 1-5}
    - **budget_min**: 预算下限（可选）
    - **budget_max**: 预算上限（可选）
    - **preferred_level**: 偏好技能等级（可选）
    """
    requirement_id = str(uuid.uuid4())
    requirement = JobRequirement(
        id=requirement_id,
        title=req.title,
        description=req.description,
        required_skills=req.required_skills,
        budget_min=req.budget_min,
        budget_max=req.budget_max,
        preferred_level=req.preferred_level,
        category=req.category,
        urgency=req.urgency,
        preferences=req.preferences
    )
    matching_service._job_requirements[requirement_id] = requirement

    return {
        "requirement_id": requirement_id,
        "message": "职位需求创建成功",
        "status": "created"
    }


@router.post("/match", response_model=MatchResponse)
async def match_employees(req: MatchRequest):
    """
    智能匹配员工 (v2 增强)

    根据职位需求、用户偏好和历史表现，智能推荐最适合的员工

    ## v2 新增匹配维度

    1. **技能匹配 (30%)**: 员工技能与职位需求的匹配程度
    2. **历史表现 (20%)**: 员工的评分、完成订单数、复雇率
    3. **用户偏好 (15%)**: 用户的历史合作和显式偏好
    4. **价格匹配 (15%)**: 员工时薪与职位预算的匹配程度
    5. **可用性 (10%)**: 员工当前状态和响应时间
    6. **时区匹配 (5%)**: 员工时区与工作时间的匹配程度
    7. **语言匹配 (5%)**: 员工语言能力与职位语言要求

    ## v2 新增功能

    - **匹配结果缓存**: 相同请求直接返回缓存结果，加速 20-30 倍
    - **时间可用性匹配**: 检查工时和日程冲突
    """
    start_time = datetime.now()

    # 创建职位需求对象
    requirement = JobRequirement(
        id=str(uuid.uuid4()),
        title=req.requirement.title,
        description=req.requirement.description,
        required_skills=req.requirement.required_skills,
        budget_min=req.requirement.budget_min,
        budget_max=req.requirement.budget_max,
        preferred_level=req.requirement.preferred_level,
        category=req.requirement.category,
        urgency=req.requirement.urgency,
        preferences=req.requirement.preferences
    )

    # 创建匹配配置
    config = None
    if req.config:
        config = MatchingConfig(**req.config)

    # 执行匹配
    matches = matching_service.match_employees(
        requirement=requirement,
        user_id=req.user_id,
        config=config
    )

    # 计算耗时
    search_time_ms = (datetime.now() - start_time).total_seconds() * 1000

    # 转换结果格式
    result_matches = []
    for match in matches:
        # 生成推荐语
        if match.overall_score >= 80:
            recommendation = "强烈推荐 - 完美匹配您的需求"
        elif match.overall_score >= 60:
            recommendation = "推荐 - 符合大部分要求"
        elif match.overall_score >= 40:
            recommendation = "可考虑 - 基本符合要求"
        else:
            recommendation = "备选 - 部分要求不匹配"

        result_matches.append(MatchResult(
            employee_id=match.employee_id,
            employee_name=match.employee_name,
            overall_score=match.overall_score,
            skill_score=match.skill_score,
            performance_score=match.performance_score,
            preference_score=match.preference_score,
            price_score=match.price_score,
            availability_score=match.availability_score,
            timezone_score=match.timezone_score,
            language_score=match.language_score,
            match_reasons=match.match_reasons,
            recommendation=recommendation
        ))

    return MatchResponse(
        requirement_id=requirement.id,
        total_matches=len(result_matches),
        matches=result_matches,
        search_time_ms=round(search_time_ms, 2),
        algorithm_version="v2.0"
    )


@router.get("/explain/{employee_id}", response_model=ExplanationResponse)
async def get_recommendation_explanation(employee_id: str, requirement_id: Optional[str] = Query(None)):
    """
    获取推荐解释

    解释为什么向用户推荐这个员工，包括：
    - 匹配度分析
    - 优势说明
    - 考虑因素
    """
    # 获取员工匹配信息（简化版，实际应从存储中获取）
    if employee_id not in matching_service._employees:
        raise HTTPException(status_code=404, detail="员工不存在")

    employee = matching_service._employees[employee_id]

    # 创建一个虚拟匹配对象用于解释
    match = matching_service.match_employees(
        requirement=JobRequirement(
            id=requirement_id or "temp",
            title="临时需求",
            description="",
            required_skills={}
        ),
        user_id=None
    )

    if match:
        for m in match:
            if m.employee_id == employee_id:
                explanation = matching_service.get_recommendation_explanation(m)
                return ExplanationResponse(**explanation)

    # 默认解释
    return ExplanationResponse(
        employee_id=employee_id,
        employee_name=employee.get('name', 'Unknown'),
        overall_match="50%",
        top_reasons=["暂无详细匹配数据"],
        score_breakdown={
            "skill_match": "50%",
            "performance": "50%",
            "preferences": "50%",
            "price_fit": "50%",
            "availability": "50%"
        },
        strengths=["数据不足"],
        considerations=[]
    )


@router.post("/feedback")
async def submit_feedback(req: MatchFeedbackRequest):
    """
    提交匹配反馈

    用于优化匹配算法：
    - 记录用户是否选择了推荐的员工
    - 收集用户对推荐结果的评价
    """
    matching_service.record_match_feedback(
        requirement_id=req.requirement_id,
        employee_id=req.employee_id,
        user_selected=req.selected,
        feedback=req.feedback
    )

    return {
        "message": "反馈提交成功",
        "status": "recorded"
    }


@router.get("/statistics")
async def get_match_statistics(requirement_id: Optional[str] = Query(None)):
    """
    获取匹配统计信息

    - 总匹配次数
    - 用户选择率
    - 算法效果分析
    """
    stats = matching_service.get_match_statistics(requirement_id)
    return {
        "statistics": stats,
        "algorithm_version": "v1.0",
        "last_updated": datetime.now().isoformat()
    }


@router.get("/config")
async def get_matching_config():
    """
    获取当前匹配算法配置 (v2 增强)
    """
    config = matching_service.config
    return {
        "config": {
            "skill_weight": config.skill_weight,
            "performance_weight": config.performance_weight,
            "preference_weight": config.preference_weight,
            "price_weight": config.price_weight,
            "availability_weight": config.availability_weight,
            "timezone_weight": config.timezone_weight,  # v2 新增
            "language_weight": config.language_weight,  # v2 新增
            "min_match_score": config.min_match_score,
            "max_results": config.max_results,
            "enable_cache": config.enable_cache,  # v2 新增
            "cache_ttl_seconds": config.cache_ttl_seconds  # v2 新增
        },
        "version": "v2.0"
    }


@router.put("/config")
async def update_matching_config(
    skill_weight: Optional[float] = Query(None, ge=0, le=1),
    performance_weight: Optional[float] = Query(None, ge=0, le=1),
    preference_weight: Optional[float] = Query(None, ge=0, le=1),
    price_weight: Optional[float] = Query(None, ge=0, le=1),
    availability_weight: Optional[float] = Query(None, ge=0, le=1),
    timezone_weight: Optional[float] = Query(None, ge=0, le=1),  # v2 新增
    language_weight: Optional[float] = Query(None, ge=0, le=1),  # v2 新增
    min_match_score: Optional[float] = Query(None, ge=0, le=100),
    max_results: Optional[int] = Query(None, ge=1, le=100),
    enable_cache: Optional[bool] = Query(None),  # v2 新增
    cache_ttl_seconds: Optional[int] = Query(None, ge=60)  # v2 新增
):
    """
    更新匹配算法配置 (v2 增强)

    可调整各维度的权重，注意所有权重的和应该等于 1.0

    v2 新增参数:
    - **timezone_weight**: 时区匹配权重
    - **language_weight**: 语言匹配权重
    - **enable_cache**: 是否启用缓存
    - **cache_ttl_seconds**: 缓存过期时间（秒）
    """
    if skill_weight is not None:
        matching_service.config.skill_weight = skill_weight
    if performance_weight is not None:
        matching_service.config.performance_weight = performance_weight
    if preference_weight is not None:
        matching_service.config.preference_weight = preference_weight
    if price_weight is not None:
        matching_service.config.price_weight = price_weight
    if availability_weight is not None:
        matching_service.config.availability_weight = availability_weight
    if timezone_weight is not None:
        matching_service.config.timezone_weight = timezone_weight
    if language_weight is not None:
        matching_service.config.language_weight = language_weight
    if min_match_score is not None:
        matching_service.config.min_match_score = min_match_score
    if max_results is not None:
        matching_service.config.max_results = max_results
    if enable_cache is not None:
        matching_service.config.enable_cache = enable_cache
    if cache_ttl_seconds is not None:
        matching_service.config.cache_ttl_seconds = cache_ttl_seconds

    return {
        "message": "配置更新成功",
        "config": {
            "skill_weight": matching_service.config.skill_weight,
            "performance_weight": matching_service.config.performance_weight,
            "preference_weight": matching_service.config.preference_weight,
            "price_weight": matching_service.config.price_weight,
            "availability_weight": matching_service.config.availability_weight,
            "timezone_weight": matching_service.config.timezone_weight,
            "language_weight": matching_service.config.language_weight,
            "min_match_score": matching_service.config.min_match_score,
            "max_results": matching_service.config.max_results,
            "enable_cache": matching_service.config.enable_cache,
            "cache_ttl_seconds": matching_service.config.cache_ttl_seconds
        },
        "version": "v2.0"
    }


# ==================== 员工和用户数据管理端点 ====================

@router.post("/employees/register")
async def register_employee(employee_data: Dict[str, Any]):
    """
    注册员工到匹配系统

    需要提供员工的基本信息、技能、状态等数据
    """
    if 'id' not in employee_data:
        employee_data['id'] = str(uuid.uuid4())

    matching_service.register_employee(employee_data)

    return {
        "message": "员工注册成功",
        "employee_id": employee_data['id']
    }


@router.put("/employees/{employee_id}/skills")
async def update_employee_skills(employee_id: str, skills_update: EmployeeSkillsUpdate):
    """
    更新员工技能和状态
    """
    if employee_id not in matching_service._employees:
        raise HTTPException(status_code=404, detail="员工不存在")

    employee = matching_service._employees[employee_id]
    employee['skills'] = skills_update.skills

    if skills_update.hourly_rate is not None:
        employee['hourly_rate'] = skills_update.hourly_rate
    if skills_update.status is not None:
        employee['status'] = skills_update.status

    return {
        "message": "员工信息更新成功",
        "employee_id": employee_id
    }


@router.put("/employees/{employee_id}/stats")
async def update_employee_stats(employee_id: str, stats: Dict[str, Any]):
    """
    更新员工统计数据

    包括：rating, total_jobs, rehire_rate, completion_rate, violation_count 等
    """
    matching_service.update_employee_stats(employee_id, stats)

    return {
        "message": "统计数据更新成功",
        "employee_id": employee_id
    }


@router.post("/users/{user_id}/preferences")
async def update_user_preferences(user_id: str, preferences: UserPreferencesUpdate):
    """
    更新用户偏好

    用于个性化推荐：
    - 偏好类别
    - 价格范围
    - 技能等级偏好
    - 历史合作记录
    """
    pref_dict = preferences.model_dump(exclude_none=True)
    matching_service.set_user_preference(user_id, pref_dict)

    return {
        "message": "用户偏好更新成功",
        "user_id": user_id
    }


@router.get("/users/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    """
    获取用户偏好
    """
    preferences = matching_service._user_preferences.get(user_id, {})
    return {
        "user_id": user_id,
        "preferences": preferences
    }


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """
    匹配服务健康检查
    """
    return {
        "status": "healthy",
        "service": "matching_service",
        "version": "v1.0",
        "registered_employees": len(matching_service._employees),
        "active_requirements": len(matching_service._job_requirements)
    }
