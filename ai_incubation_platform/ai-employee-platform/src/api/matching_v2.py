"""
P12 高级匹配算法增强 - API 路由层

提供以下 API 端点：
- 向量匹配相关
- 文化适配相关
- 历史表现增强相关
- 薪资分析相关
- 可解释性报告相关
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from models.p12_models import (
    EmployeeVector, JobVector, CulturalFitProfile, CulturalFitMatch,
    WeightedPerformanceScore, EmployeeSalaryAnalysis, MatchExplanation,
    CommunicationStyle, FeedbackStyle, WorkSchedulePreference,
    DecisionStyle, CollaborationStyle, p12_storage
)
from services.matching_v2_service import (
    vector_matching_service, cultural_fit_service,
    enhanced_performance_service, salary_analysis_service,
    match_explanation_service, matching_v2_service
)


router = APIRouter(prefix="/api/matching-v2", tags=["Matching V2 - 高级匹配算法"])


# ==================== 请求/响应模型 ====================

class VectorizeEmployeeRequest(BaseModel):
    """生成员工向量请求"""
    employee_id: str
    skills: Dict[str, str] = Field(default_factory=dict)
    description: Optional[str] = None
    category: Optional[str] = None
    experience_years: Optional[int] = None


class VectorizeJobRequest(BaseModel):
    """生成职位向量请求"""
    job_id: Optional[str] = None
    title: str
    description: str
    required_skills: Dict[str, int] = Field(default_factory=dict)
    category: Optional[str] = None


class MatchVectorRequest(BaseModel):
    """向量相似度匹配请求"""
    job: Dict[str, Any]
    employee_ids: Optional[List[str]] = None
    use_cache: bool = True


class CreateCulturalProfileRequest(BaseModel):
    """创建文化档案请求"""
    user_id: str
    user_type: str = "employee"
    communication_style: Optional[str] = None
    feedback_style: Optional[str] = None
    work_schedule_preference: Optional[str] = None
    timezone: str = "UTC"
    working_hours_start: int = 9
    working_hours_end: int = 18
    decision_style: Optional[str] = None
    collaboration_style: Optional[str] = None
    meeting_preference: str = "video"
    documentation_preference: str = "detailed"


class AssessCulturalFitRequest(BaseModel):
    """评估文化适配度请求"""
    employee_id: str
    employer_id: str


class CalculatePerformanceRequest(BaseModel):
    """计算加权表现请求"""
    employee_id: str
    project_history: Optional[List[Dict[str, Any]]] = None


class GenerateExplanationRequest(BaseModel):
    """生成匹配解释请求"""
    match_id: str
    employee: Dict[str, Any]
    job: Dict[str, Any]
    match_scores: Dict[str, float]


class EnhancedMatchRequest(BaseModel):
    """增强版匹配请求"""
    job: Dict[str, Any]
    employees: List[Dict[str, Any]]
    include_explanation: bool = False


# ==================== 向量匹配 API ====================

@router.post("/vectorize-employee", response_model=Dict[str, Any])
async def vectorize_employee(request: VectorizeEmployeeRequest):
    """
    生成员工技能向量

    将员工的技能、经验等文本信息转换为嵌入向量，用于语义匹配
    """
    # 构建员工数据
    employee = {
        'id': request.employee_id,
        'skills': request.skills,
        'description': request.description,
        'category': request.category,
        'experience_years': request.experience_years
    }

    # 生成向量
    vector = vector_matching_service.vectorize_employee(employee)

    return {
        'success': True,
        'employee_id': request.employee_id,
        'vector_id': vector.id,
        'vector_dimension': len(vector.skill_vector),
        'model_version': vector.vector_model_version,
        'skill_tags': vector.skill_tags,
        'created_at': vector.created_at.isoformat()
    }


@router.post("/vectorize-job", response_model=Dict[str, Any])
async def vectorize_job(request: VectorizeJobRequest):
    """
    生成职位需求向量

    将职位描述、技能要求等转换为嵌入向量
    """
    job = {
        'id': request.job_id or str(uuid.uuid4()),
        'title': request.title,
        'description': request.description,
        'required_skills': request.required_skills,
        'category': request.category
    }

    vector = vector_matching_service.vectorize_job(job)

    return {
        'success': True,
        'job_id': job['id'],
        'vector_id': vector.id,
        'vector_dimension': len(vector.job_vector),
        'model_version': vector.vector_model_version,
        'created_at': vector.created_at.isoformat()
    }


@router.post("/match-vector", response_model=Dict[str, Any])
async def match_vector(request: MatchVectorRequest):
    """
    基于向量相似度匹配员工

    使用语义相似度计算员工与职位的匹配度
    """
    job = request.job

    # 如果没有指定员工 ID，使用存储中的所有员工
    if request.employee_ids:
        employees = []
        for emp_id in request.employee_ids:
            # 实际应从数据库获取，这里用模拟数据
            employees.append({
                'id': emp_id,
                'name': f'Employee {emp_id[:8]}',
                'skills': {'Python': 'advanced'},
                'category': 'engineering'
            })
    else:
        # 返回错误，需要提供员工列表
        raise HTTPException(status_code=400, detail="需要提供 employee_ids 或 employees 列表")

    results = vector_matching_service.match_by_vector_similarity(
        job, employees, use_cache=request.use_cache
    )

    return {
        'success': True,
        'job_id': job.get('id'),
        'total_matches': len(results),
        'matches': results
    }


@router.get("/similarity/{employee_id}/{job_id}")
async def get_similarity(employee_id: str, job_id: str):
    """
    获取员工与职位的相似度分数
    """
    cached = vector_matching_service.get_cached_similarity(employee_id, job_id)
    if cached is not None:
        return {
            'success': True,
            'employee_id': employee_id,
            'job_id': job_id,
            'similarity': cached,
            'from_cache': True
        }

    return {
        'success': False,
        'message': '缓存未找到，请先进行匹配计算',
        'employee_id': employee_id,
        'job_id': job_id
    }


# ==================== 文化适配 API ====================

@router.post("/cultural-fit", response_model=Dict[str, Any])
async def create_cultural_profile(request: CreateCulturalProfileRequest):
    """
    创建文化适配档案

    记录用户的沟通风格、工作偏好等文化特征
    """
    profile_data = {
        'communication_style': request.communication_style,
        'feedback_style': request.feedback_style,
        'work_schedule_preference': request.work_schedule_preference,
        'timezone': request.timezone,
        'working_hours_start': request.working_hours_start,
        'working_hours_end': request.working_hours_end,
        'decision_style': request.decision_style,
        'collaboration_style': request.collaboration_style,
        'meeting_preference': request.meeting_preference,
        'documentation_preference': request.documentation_preference
    }

    profile = cultural_fit_service.create_cultural_profile(
        user_id=request.user_id,
        user_type=request.user_type,
        profile_data=profile_data
    )

    return {
        'success': True,
        'profile_id': profile.id,
        'user_id': profile.user_id,
        'user_type': profile.user_type,
        'communication_style': profile.communication_style.value,
        'feedback_style': profile.feedback_style.value,
        'work_schedule_preference': profile.work_schedule_preference.value,
        'decision_style': profile.decision_style.value,
        'collaboration_style': profile.collaboration_style.value
    }


@router.get("/cultural-fit/{user_id}", response_model=Dict[str, Any])
async def get_cultural_profile(user_id: str):
    """
    获取用户的文化适配档案
    """
    profile = p12_storage.get_cultural_profile(user_id)

    if not profile:
        raise HTTPException(status_code=404, detail="文化档案不存在")

    return {
        'success': True,
        'profile': {
            'id': profile.id,
            'user_id': profile.user_id,
            'user_type': profile.user_type,
            'communication_style': profile.communication_style.value,
            'feedback_style': profile.feedback_style.value,
            'work_schedule_preference': profile.work_schedule_preference.value,
            'decision_style': profile.decision_style.value,
            'collaboration_style': profile.collaboration_style.value,
            'timezone': profile.timezone,
            'working_hours': f"{profile.working_hours_start}:00 - {profile.working_hours_end}:00"
        }
    }


@router.post("/cultural-fit/assess", response_model=Dict[str, Any])
async def assess_cultural_fit(request: AssessCulturalFitRequest):
    """
    评估员工与雇主的文化适配度
    """
    employee_profile = p12_storage.get_cultural_profile(request.employee_id)
    employer_profile = p12_storage.get_cultural_profile(request.employer_id)

    if not employee_profile:
        raise HTTPException(status_code=404, detail="员工文化档案不存在")
    if not employer_profile:
        raise HTTPException(status_code=404, detail="雇主文化档案不存在")

    match = cultural_fit_service.assess_cultural_fit(employee_profile, employer_profile)

    return {
        'success': True,
        'match': {
            'employee_id': request.employee_id,
            'employer_id': request.employer_id,
            'overall_fit_score': match.overall_fit_score,
            'dimensions': {
                'communication_fit': match.communication_fit,
                'feedback_fit': match.feedback_fit,
                'schedule_fit': match.schedule_fit,
                'decision_fit': match.decision_fit,
                'collaboration_fit': match.collaboration_fit
            },
            'strengths': match.strengths,
            'potential_conflicts': match.potential_conflicts,
            'suggestions': match.suggestions
        }
    }


# ==================== 历史表现增强 API ====================

@router.get("/performance/{employee_id}/detailed", response_model=Dict[str, Any])
async def get_detailed_performance(employee_id: str):
    """
    获取员工的详细表现评估
    """
    # 模拟员工数据
    employee = {
        'id': employee_id,
        'rating': 4.5,
        'completion_rate': 0.95,
        'rehire_rate': 0.8,
        'on_time_delivery_rate': 0.9
    }

    perf_score = enhanced_performance_service.calculate_weighted_performance(employee)

    return {
        'success': True,
        'employee_id': employee_id,
        'performance': {
            'overall_score': perf_score.overall_score,
            'breakdown': {
                'rating_score': perf_score.rating_score,
                'completion_rate_score': perf_score.completion_rate_score,
                'rehire_rate_score': perf_score.rehire_rate_score,
                'on_time_delivery_score': perf_score.on_time_delivery_score
            },
            'adjustments': {
                'time_decay_multiplier': perf_score.time_decay_multiplier,
                'complexity_bonus': perf_score.complexity_bonus,
                'client_type_weight': perf_score.client_type_weight
            },
            'trend': {
                'direction': perf_score.trend.trend_direction if perf_score.trend else 'stable',
                'percentage': perf_score.trend.trend_percentage if perf_score.trend else 0,
                'analysis': perf_score.trend.trend_analysis if perf_score.trend else '数据不足'
            }
        }
    }


@router.post("/performance/weighted", response_model=Dict[str, Any])
async def calculate_weighted_performance(request: CalculatePerformanceRequest):
    """
    计算加权表现分数（可传入项目历史）
    """
    employee = {
        'id': request.employee_id,
        'rating': 4.5,
        'completion_rate': 0.95,
        'rehire_rate': 0.8,
        'on_time_delivery_rate': 0.9
    }

    perf_score = enhanced_performance_service.calculate_weighted_performance(
        employee, request.project_history
    )

    return {
        'success': True,
        'employee_id': request.employee_id,
        'performance': {
            'overall_score': perf_score.overall_score,
            'breakdown': perf_score.breakdown,
            'trend': {
                'direction': perf_score.trend.trend_direction if perf_score.trend else 'stable',
                'percentage': perf_score.trend.trend_percentage if perf_score.trend else 0
            }
        }
    }


# ==================== 薪资分析 API ====================

@router.get("/salary-analysis/{employee_id}", response_model=Dict[str, Any])
async def get_salary_analysis(employee_id: str):
    """
    分析员工薪资的市场定位
    """
    # 模拟员工数据
    employee = {
        'id': employee_id,
        'hourly_rate': 50,
        'category': 'engineering',
        'level': 'intermediate',
        'rating': 4.5
    }

    analysis = salary_analysis_service.analyze_employee_salary(employee)

    return {
        'success': True,
        'employee_id': employee_id,
        'analysis': {
            'current_rate': analysis.current_rate,
            'market_percentile': analysis.market_percentile,
            'vs_median': analysis.vs_median,
            'pricing_strategy': analysis.pricing_strategy,
            'value_score': analysis.value_score,
            'suggested_range': {
                'min': analysis.suggested_rate_min,
                'max': analysis.suggested_rate_max
            },
            'suggestions': analysis.pricing_suggestions
        }
    }


@router.get("/salary-analysis/market-benchmark")
async def get_market_benchmark(
    category: str = Query("engineering", description="技能类别"),
    level: str = Query("intermediate", description="经验水平")
):
    """
    获取市场薪资基准
    """
    benchmark = salary_analysis_service.get_market_benchmark(category, level)

    return {
        'success': True,
        'benchmark': {
            'category': benchmark.skill_category,
            'level': benchmark.experience_level,
            'percentiles': {
                'p10': benchmark.percentile_10,
                'p25': benchmark.percentile_25,
                'p50': benchmark.percentile_50,
                'p75': benchmark.percentile_75,
                'p90': benchmark.percentile_90
            },
            'sample_size': benchmark.sample_size,
            'currency': benchmark.currency,
            'period': benchmark.period
        }
    }


# ==================== 可解释性报告 API ====================

@router.post("/explanation/generate", response_model=Dict[str, Any])
async def generate_explanation(request: GenerateExplanationRequest):
    """
    生成匹配解释报告
    """
    explanation = match_explanation_service.generate_explanation(
        match_id=request.match_id,
        employee=request.employee,
        job=request.job,
        match_scores=request.match_scores
    )

    return {
        'success': True,
        'explanation': {
            'id': explanation.id,
            'match_id': explanation.match_id,
            'overall_score': explanation.overall_score,
            'confidence_level': explanation.confidence_level,
            'score_breakdown': {
                'skill_match': explanation.score_breakdown.skill_match,
                'performance_match': explanation.score_breakdown.performance_match,
                'cultural_fit': explanation.score_breakdown.cultural_fit,
                'price_fit': explanation.score_breakdown.price_fit,
                'vector_similarity': explanation.score_breakdown.vector_similarity
            },
            'strengths': [
                {'category': s.category, 'description': s.description, 'impact': s.impact_score}
                for s in explanation.strengths
            ],
            'risks': [
                {'category': r.category, 'description': r.description, 'severity': r.severity}
                for r in explanation.risks
            ],
            'suggestions': explanation.suggestions,
            'explanation_text': explanation.explanation_text,
            'key_factors': explanation.key_factors
        }
    }


@router.get("/explanation/{match_id}", response_model=Dict[str, Any])
async def get_explanation(match_id: str):
    """
    获取已生成的匹配解释报告
    """
    explanation = p12_storage.get_match_explanation(match_id)

    if not explanation:
        raise HTTPException(status_code=404, detail="匹配解释报告不存在")

    return {
        'success': True,
        'explanation': {
            'id': explanation.id,
            'match_id': explanation.match_id,
            'employee_id': explanation.employee_id,
            'overall_score': explanation.overall_score,
            'confidence_level': explanation.confidence_level,
            'score_breakdown': {
                'skill_match': explanation.score_breakdown.skill_match,
                'performance_match': explanation.score_breakdown.performance_match,
                'cultural_fit': explanation.score_breakdown.cultural_fit,
                'price_fit': explanation.score_breakdown.price_fit,
                'vector_similarity': explanation.score_breakdown.vector_similarity
            },
            'strengths': [
                {'category': s.category, 'description': s.description, 'impact': s.impact_score}
                for s in explanation.strengths
            ],
            'risks': [
                {'category': r.category, 'description': r.description, 'severity': r.severity}
                for r in explanation.risks
            ],
            'suggestions': explanation.suggestions,
            'explanation_text': explanation.explanation_text
        }
    }


# ==================== 增强版匹配 API ====================

@router.post("/enhanced-match", response_model=Dict[str, Any])
async def enhanced_match(request: EnhancedMatchRequest):
    """
    增强版匹配算法

    整合向量相似度、文化适配、历史表现加权、薪资分析等 v12 所有特性
    """
    results = matching_v2_service.enhanced_match(
        job=request.job,
        employees=request.employees,
        include_explanation=request.include_explanation
    )

    return {
        'success': True,
        'job_id': request.job.get('id'),
        'total_matches': len(results),
        'matches': results
    }


# ==================== 演示/测试端点 ====================

@router.get("/demo/full-match")
async def demo_full_match():
    """
    演示完整匹配流程

    创建测试数据并执行完整匹配
    """
    # 1. 创建测试员工
    test_employee = {
        'id': 'emp_demo_001',
        'name': '张三',
        'skills': {
            'Python': 'expert',
            'Machine Learning': 'advanced',
            'Data Analysis': 'advanced'
        },
        'description': '资深机器学习工程师，专注于自然语言处理和推荐系统',
        'category': 'engineering',
        'level': 'advanced',
        'hourly_rate': 75,
        'rating': 4.7,
        'completion_rate': 0.96,
        'rehire_rate': 0.85,
        'availability_score': 80
    }

    # 2. 创建测试职位
    test_job = {
        'id': 'job_demo_001',
        'title': '机器学习工程师',
        'description': '需要开发 NLP 模型和推荐算法，要求精通 Python 和深度学习框架',
        'required_skills': {
            'Python': 5,
            'Machine Learning': 5,
            'Deep Learning': 4,
            'NLP': 4
        },
        'category': 'engineering',
        'budget_min': 60,
        'budget_max': 100
    }

    # 3. 生成向量
    emp_vector = vector_matching_service.vectorize_employee(test_employee)
    job_vector = vector_matching_service.vectorize_job(test_job)

    # 4. 创建文化档案
    emp_culture = cultural_fit_service.create_cultural_profile(
        user_id=test_employee['id'],
        user_type='employee',
        profile_data={
            'communication_style': 'moderate',
            'feedback_style': 'direct',
            'work_schedule_preference': 'flexible',
            'decision_style': 'data_driven',
            'collaboration_style': 'collaborative'
        }
    )

    employer_culture = cultural_fit_service.create_cultural_profile(
        user_id='employer_demo_001',
        user_type='employer',
        profile_data={
            'communication_style': 'moderate',
            'feedback_style': 'direct',
            'work_schedule_preference': 'flexible',
            'decision_style': 'data_driven',
            'collaboration_style': 'collaborative'
        }
    )

    # 5. 计算各项分数
    vector_results = vector_matching_service.match_by_vector_similarity(
        test_job, [test_employee]
    )
    perf_score = enhanced_performance_service.calculate_weighted_performance(test_employee)
    salary_analysis = salary_analysis_service.analyze_employee_salary(test_employee)
    cultural_match = cultural_fit_service.assess_cultural_fit(emp_culture, employer_culture)

    # 6. 生成解释报告
    match_scores = {
        'skill_score': vector_results[0]['vector_similarity'],
        'performance_score': perf_score.overall_score,
        'cultural_fit': cultural_match.overall_fit_score,
        'price_score': 100 - abs(salary_analysis.vs_median),
        'availability_score': test_employee['availability_score'],
        'vector_similarity': vector_results[0]['vector_similarity'],
        'overall_score': (
            vector_results[0]['vector_similarity'] * 0.35 +
            perf_score.overall_score * 0.30 +
            salary_analysis.value_score * 0.20 +
            test_employee['availability_score'] * 0.15
        )
    }

    explanation = match_explanation_service.generate_explanation(
        match_id='demo_match_001',
        employee=test_employee,
        job=test_job,
        match_scores=match_scores
    )

    return {
        'success': True,
        'demo_results': {
            'employee': {
                'id': test_employee['id'],
                'name': test_employee['name'],
                'skills': list(test_employee['skills'].keys())
            },
            'job': {
                'id': test_job['id'],
                'title': test_job['title']
            },
            'vector_similarity': {
                'employee_vector_id': emp_vector.id,
                'job_vector_id': job_vector.id,
                'similarity': vector_results[0]['vector_similarity']
            },
            'performance': {
                'overall_score': perf_score.overall_score,
                'trend': perf_score.trend.trend_direction if perf_score.trend else 'stable'
            },
            'salary_analysis': {
                'current_rate': salary_analysis.current_rate,
                'market_percentile': salary_analysis.market_percentile,
                'pricing_strategy': salary_analysis.pricing_strategy,
                'value_score': salary_analysis.value_score
            },
            'cultural_fit': {
                'overall_score': cultural_match.overall_fit_score,
                'strengths': cultural_match.strengths,
                'suggestions': cultural_match.suggestions
            },
            'explanation': {
                'overall_score': explanation.overall_score,
                'confidence_level': explanation.confidence_level,
                'explanation_text': explanation.explanation_text,
                'key_factors': explanation.key_factors,
                'suggestions': explanation.suggestions
            }
        }
    }
