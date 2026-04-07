"""
薪酬管理 API 路由。
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body

from models.compensation import (
    SalaryBenchmarkRequest,
    SalarySurveyRequest,
    NegotiationAdviceRequest,
    NegotiationPosition,
    RaiseRecommendationRequest,
    BenefitsPackageRequest,
    AdjustmentReason,
    TransparencyLevel,
    IndustryType,
    ExperienceLevel,
    WorkMode,
)
from services.compensation_service import get_compensation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compensation", tags=["compensation"])


# ===== 薪资基准查询 =====

@router.get("/benchmark")
async def get_salary_benchmark(
    job_title: Optional[str] = Query(None, description="职位名称"),
    skill: str = Query(..., description="核心技能"),
    industry: Optional[IndustryType] = Query(None, description="行业类型"),
    location: Optional[str] = Query(None, description="地区"),
    experience_level: Optional[ExperienceLevel] = Query(None, description="经验级别"),
    work_mode: Optional[WorkMode] = Query(None, description="工作模式"),
):
    """
    获取薪资基准数据。

    - **job_title**: 职位名称（可选）
    - **skill**: 核心技能（必填）
    - **industry**: 行业类型（可选，默认 tech）
    - **location**: 地区（可选，默认北京）
    - **experience_level**: 经验级别（可选，默认 mid）
    - **work_mode**: 工作模式（可选，默认 hybrid）

    返回指定维度的市场薪资范围统计。
    """
    service = get_compensation_service()

    request = SalaryBenchmarkRequest(
        job_title=job_title,
        skill=skill,
        industry=industry,
        location=location,
        experience_level=experience_level,
        work_mode=work_mode
    )

    benchmark = service.get_salary_benchmark(request)
    salary_range = service.get_market_salary_range(request)

    return {
        "benchmark": benchmark.dict() if benchmark else None,
        "salary_range": salary_range.dict(),
        "request": request.dict()
    }


@router.get("/benchmarks")
async def list_salary_benchmarks(
    skill: Optional[str] = Query(None, description="技能过滤"),
    industry: Optional[IndustryType] = Query(None, description="行业过滤"),
    location: Optional[str] = Query(None, description="地区过滤"),
):
    """
    列出薪资基准数据。

    支持按技能、行业、地区进行过滤。
    """
    service = get_compensation_service()
    benchmarks = service.list_salary_benchmarks(skill, industry, location)
    return {
        "benchmarks": [b.dict() for b in benchmarks],
        "count": len(benchmarks)
    }


@router.get("/trends")
async def get_salary_trends(
    skill: str = Query(..., description="技能名称"),
    months: int = Query(12, ge=1, le=24, description="月数"),
):
    """
    获取薪酬趋势数据。

    返回指定技能在过去 N 个月的薪资变化趋势。
    """
    service = get_compensation_service()
    trends = service.get_salary_trends(skill, months)
    return {
        "skill": skill,
        "months": months,
        "trends": trends
    }


# ===== 薪酬调查 =====

@router.post("/survey")
async def conduct_salary_survey(
    request: SalarySurveyRequest,
):
    """
    进行薪酬调查。

    支持多维度（技能、行业、地区、经验级别）的薪酬调查。
    """
    service = get_compensation_service()
    survey = service.conduct_salary_survey(request)
    return {
        "survey": survey.dict(),
        "message": "薪酬调查完成"
    }


@router.get("/survey/{survey_id}")
async def get_salary_survey(
    survey_id: str,
):
    """
    获取薪酬调查结果。
    """
    service = get_compensation_service()
    # 在实际实现中应该从存储中获取
    raise HTTPException(status_code=404, detail="Survey not found")


# ===== 薪资谈判支持 =====

@router.post("/negotiation")
async def generate_negotiation_advice(
    request: NegotiationAdviceRequest,
):
    """
    生成薪资谈判建议。

    根据用户立场（雇主/工人）生成个性化的谈判策略和建议。
    """
    service = get_compensation_service()
    advice = service.generate_negotiation_advice(request)
    return {
        "advice": advice.dict(),
        "message": f"已生成{request.position.value}视角的谈判建议"
    }


@router.get("/negotiation/{advice_id}")
async def get_negotiation_advice(
    advice_id: str,
):
    """
    获取谈判建议详情。
    """
    service = get_compensation_service()
    # 在实际实现中应该从存储中获取
    raise HTTPException(status_code=404, detail="Advice not found")


# ===== 调薪建议 =====

@router.post("/raise-recommendation")
async def generate_raise_recommendation(
    request: RaiseRecommendationRequest,
):
    """
    生成调薪建议。

    基于绩效表现和市场薪酬水平生成调薪建议。
    """
    service = get_compensation_service()
    adjustment = service.generate_raise_recommendation(request)
    return {
        "adjustment": adjustment.dict(),
        "message": f"已生成调薪建议：{adjustment.increase_percentage*100:.1f}%涨幅"
    }


@router.get("/raise-recommendation")
async def list_raise_recommendations(
    worker_id: Optional[str] = Query(None, description="工人 ID"),
    status: Optional[str] = Query(None, description="状态"),
):
    """
    列出调薪建议。

    支持按工人 ID 和状态过滤。
    """
    service = get_compensation_service()
    adjustments = service.list_adjustments(worker_id, status)
    return {
        "adjustments": [a.dict() for a in adjustments],
        "count": len(adjustments)
    }


@router.get("/raise-recommendation/{adjustment_id}")
async def get_raise_recommendation(
    adjustment_id: str,
):
    """
    获取调薪建议详情。
    """
    service = get_compensation_service()
    # 在实际实现中应该从存储中获取
    raise HTTPException(status_code=404, detail="Adjustment not found")


# ===== 福利管理 =====

@router.post("/benefits")
async def create_benefits_package(
    request: BenefitsPackageRequest,
):
    """
    创建福利包。

    基于预算和偏好生成包含保险、股票、补贴的福利组合。
    """
    service = get_compensation_service()
    package = service.create_benefits_package(request)
    return {
        "package": package.dict(),
        "total_annual_value": package.total_annual_value,
        "message": f"已创建福利包：{package.package_name}"
    }


@router.get("/benefits")
async def list_benefits_packages():
    """
    列出所有福利包。
    """
    service = get_compensation_service()
    packages = service.list_benefits_packages()
    return {
        "packages": [p.dict() for p in packages],
        "count": len(packages)
    }


@router.get("/benefits/{package_id}")
async def get_benefits_package(
    package_id: str,
):
    """
    获取福利包详情。
    """
    service = get_compensation_service()
    package = service.get_benefits_package(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return {
        "package": package.dict()
    }


# ===== 薪酬透明度 =====

@router.put("/transparency/{task_id}")
async def set_compensation_transparency(
    task_id: str,
    employer_id: str = Body(..., description="雇主 ID"),
    level: TransparencyLevel = Body(..., description="透明度级别"),
    show_salary_range: bool = Body(False, description="是否显示薪资范围"),
    show_benefits: bool = Body(False, description="是否显示福利"),
):
    """
    设置薪酬透明度。

    - **PUBLIC**: 完全公开，所有人可见
    - **LIMITED**: 部分公开，仅对投标人可见
    - **PRIVATE**: 保密，仅中标后可见
    """
    service = get_compensation_service()
    transparency = service.set_compensation_transparency(
        task_id, employer_id, level, show_salary_range, show_benefits
    )
    return {
        "transparency": transparency.dict(),
        "message": f"已设置薪酬透明度为{level.value}"
    }


@router.get("/transparency/{task_id}")
async def get_compensation_transparency(
    task_id: str,
):
    """
    获取薪酬透明度设置。
    """
    service = get_compensation_service()
    transparency = service.get_compensation_transparency(task_id)
    if not transparency:
        raise HTTPException(status_code=404, detail="Transparency setting not found")
    return {
        "transparency": transparency.dict()
    }


# ===== 薪酬公平性分析 =====

@router.post("/equity-analysis")
async def analyze_pay_equity(
    employer_id: str = Body(..., description="雇主 ID"),
    include_gender: bool = Body(True, description="是否包含性别分析"),
    include_ethnicity: bool = Body(False, description="是否包含种族分析"),
):
    """
    分析薪酬公平性。

    检测性别、种族等维度的薪酬差距，生成公平性报告。
    """
    service = get_compensation_service()
    analysis = service.analyze_pay_equity(employer_id, include_gender, include_ethnicity)
    return {
        "analysis": analysis.dict(),
        "message": f"薪酬公平性分析完成，得分：{analysis.equity_score:.1f}"
    }


@router.get("/equity-analysis/{analysis_id}")
async def get_equity_analysis(
    analysis_id: str,
):
    """
    获取公平性分析报告。
    """
    service = get_compensation_service()
    analysis = service.get_equity_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {
        "analysis": analysis.dict()
    }


# ===== 辅助端点 =====

@router.get("/skills")
async def list_skills():
    """
    列出支持的技能。
    """
    skills = [
        {"id": "python", "name": "Python 开发"},
        {"id": "java", "name": "Java 开发"},
        {"id": "javascript", "name": "JavaScript/Node.js"},
        {"id": "sql", "name": "SQL/数据分析"},
        {"id": "product_management", "name": "产品管理"},
        {"id": "ui_design", "name": "UI/UX 设计"},
        {"id": "data_science", "name": "数据科学"},
        {"id": "machine_learning", "name": "机器学习"},
        {"id": "devops", "name": "DevOps"},
        {"id": "content_writing", "name": "内容写作"},
    ]
    return {"skills": skills}


@router.get("/industries")
async def list_industries():
    """
    列出支持的行业。
    """
    industries = [
        {"id": "tech", "name": "互联网/科技"},
        {"id": "finance", "name": "金融"},
        {"id": "healthcare", "name": "医疗"},
        {"id": "education", "name": "教育"},
        {"id": "retail", "name": "零售"},
        {"id": "manufacturing", "name": "制造"},
        {"id": "media", "name": "媒体"},
        {"id": "other", "name": "其他"},
    ]
    return {"industries": industries}


@router.get("/experience-levels")
async def list_experience_levels():
    """
    列出经验级别。
    """
    levels = [
        {"id": "entry", "name": "入门级 (0-2 年)"},
        {"id": "junior", "name": "初级 (2-5 年)"},
        {"id": "mid", "name": "中级 (5-10 年)"},
        {"id": "senior", "name": "高级 (10-15 年)"},
        {"id": "expert", "name": "专家级 (15+ 年)"},
    ]
    return {"experience_levels": levels}
