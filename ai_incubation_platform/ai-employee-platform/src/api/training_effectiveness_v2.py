"""
P13 培训效果评估增强 - API 路由层

v13 新增 API 端点:
- 培训前后技能对比 (/api/training-effectiveness-v2/assessments)
- 培训 ROI 计算 (/api/training-effectiveness-v2/roi)
- 学习路径推荐 (/api/training-effectiveness-v2/learning-paths)
- 培训效果追踪 (/api/training-effectiveness-v2/impact)
- 技能认证集成 (/api/training-effectiveness-v2/certifications)
- 综合报告生成 (/api/training-effectiveness-v2/reports)
"""
from fastapi import APIRouter, HTTPException, Query, Body, Response
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from services.training_effectiveness_v2_service import training_effectiveness_v2_service
from models.p13_models import (
    AssessmentType, SkillLevel, LearningPathStatus,
    PathRecommendationReason, ROIStatus,
    CreateAssessmentRequest, AssessmentComparisonResponse,
    CalculateROIRequest, ROIResponse,
    CreateLearningPathRequest, LearningPathResponse,
    ImpactTrackerResponse
)

router = APIRouter(prefix="/api/training-effectiveness-v2", tags=["P13-培训效果评估增强"])


# ==================== 技能评估管理端点 ====================

@router.post("/assessments", response_model=Dict[str, Any])
async def create_assessment(request: CreateAssessmentRequest):
    """
    创建技能评估记录

    用于培训前测、后测或跟踪评估
    """
    try:
        data = request.model_dump()
        assessment = training_effectiveness_v2_service.create_assessment(data)

        return {
            "message": "技能评估创建成功",
            "assessment_id": assessment.id,
            "assessment_type": assessment.assessment_type.value,
            "overall_score": assessment.overall_score,
            "overall_level": assessment.overall_level.value,
            "skills_assessed": list(assessment.skill_scores.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assessments/{assessment_id}", response_model=Dict[str, Any])
async def get_assessment(assessment_id: str):
    """
    获取技能评估详情
    """
    assessment = training_effectiveness_v2_service.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")

    return {
        "id": assessment.id,
        "employee_id": assessment.employee_id,
        "assessment_type": assessment.assessment_type.value,
        "skill_scores": assessment.skill_scores,
        "skill_levels": {k: v.value for k, v in assessment.skill_levels.items()},
        "overall_score": assessment.overall_score,
        "overall_level": assessment.overall_level.value,
        "created_at": assessment.created_at.isoformat(),
        "comments": assessment.comments
    }


@router.get("/employees/{employee_id}/assessments", response_model=Dict[str, Any])
async def get_employee_assessments(
    employee_id: str,
    assessment_type: Optional[str] = Query(None, description="评估类型 (pre_assessment/post_assessment/follow_up_assessment)"),
    training_id: Optional[str] = Query(None, description="培训 ID 过滤")
):
    """
    获取员工的技能评估列表
    """
    atype = AssessmentType(assessment_type) if assessment_type else None
    assessments = training_effectiveness_v2_service.get_employee_assessments(
        employee_id, atype, training_id
    )

    return {
        "employee_id": employee_id,
        "total": len(assessments),
        "assessments": [
            {
                "id": a.id,
                "type": a.assessment_type.value,
                "overall_score": a.overall_score,
                "overall_level": a.overall_level.value,
                "skills_count": len(a.skill_scores),
                "created_at": a.created_at.isoformat(),
                "training_id": a.training_id
            }
            for a in assessments
        ]
    }


@router.post("/assessments/compare", response_model=AssessmentComparisonResponse)
async def compare_assessments(
    employee_id: str = Body(..., description="员工 ID"),
    pre_assessment_id: str = Body(..., description="培训前评估 ID"),
    post_assessment_id: str = Body(..., description="培训后评估 ID")
):
    """
    对比培训前后评估结果

    计算技能提升幅度和整体改善程度
    """
    result = training_effectiveness_v2_service.compare_assessments(
        employee_id, pre_assessment_id, post_assessment_id
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return AssessmentComparisonResponse(**result)


@router.get("/employees/{employee_id}/skill-summary", response_model=Dict[str, Any])
async def get_skill_summary(employee_id: str):
    """
    获取员工技能汇总

    整合所有评估记录，生成技能画像
    """
    assessments = training_effectiveness_v2_service.get_employee_assessments(employee_id)

    if not assessments:
        return {
            "employee_id": employee_id,
            "total_assessments": 0,
            "skills": {},
            "latest_overall_score": 0,
            "latest_level": "beginner"
        }

    # 整合所有技能分数（取最新评估的分数）
    latest = assessments[0]  # 按时间倒序，第一个是最新的
    all_skills = {}

    for skill, score in latest.skill_scores.items():
        all_skills[skill] = {
            "score": score,
            "level": latest.skill_levels.get(skill, SkillLevel.BEGINNER).value
        }

    return {
        "employee_id": employee_id,
        "total_assessments": len(assessments),
        "skills": all_skills,
        "latest_overall_score": latest.overall_score,
        "latest_level": latest.overall_level.value,
        "assessment_history": [
            {
                "date": a.created_at.isoformat(),
                "type": a.assessment_type.value,
                "score": a.overall_score
            }
            for a in assessments[:10]  # 最近 10 次
        ]
    }


# ==================== 培训 ROI 计算端点 ====================

@router.post("/roi/calculate", response_model=ROIResponse)
async def calculate_roi(request: CalculateROIRequest):
    """
    计算培训投资回报率 (ROI)

    ROI = (收益 - 成本) / 成本 * 100%
    """
    data = request.model_dump()
    roi = training_effectiveness_v2_service.calculate_training_roi(data)

    return ROIResponse(
        employee_id=roi.employee_id,
        training_id=roi.training_id,
        roi_percentage=roi.roi_percentage,
        roi_status=roi.roi_status.value,
        total_cost=roi.total_cost,
        total_benefit=roi.total_benefit,
        payback_period_days=roi.payback_period_days,
        breakdown={
            "training_cost": roi.training_cost,
            "time_cost": roi.time_cost_hours * data.get('hourly_rate', 50),
            "opportunity_cost": roi.opportunity_cost,
            "productivity_gain": roi.productivity_gain,
            "quality_improvement": roi.quality_improvement,
            "time_savings": roi.time_savings,
            "error_reduction": roi.error_reduction
        }
    )


@router.get("/employees/{employee_id}/rois", response_model=Dict[str, Any])
async def get_employee_rois(
    employee_id: str,
    period_days: int = Query(30, description="统计周期（天）")
):
    """
    获取员工的 ROI 记录
    """
    rois = training_effectiveness_v2_service.get_employee_rois(employee_id, period_days)

    return {
        "employee_id": employee_id,
        "period_days": period_days,
        "total": len(rois),
        "rois": [
            {
                "id": r.id,
                "training_id": r.training_id,
                "roi_percentage": r.roi_percentage,
                "roi_status": r.roi_status.value,
                "total_cost": r.total_cost,
                "total_benefit": r.total_benefit,
                "payback_period_days": r.payback_period_days,
                "created_at": r.created_at.isoformat()
            }
            for r in rois
        ]
    }


@router.post("/roi/aggregate", response_model=Dict[str, Any])
async def aggregate_roi(employee_ids: List[str] = Body(..., description="员工 ID 列表")):
    """
    聚合计算多个员工的 ROI

    用于企业级培训效果分析
    """
    result = training_effectiveness_v2_service.aggregate_roi(employee_ids)
    return result


# ==================== 学习路径推荐端点 ====================

@router.post("/learning-paths", response_model=LearningPathResponse)
async def create_learning_path(request: CreateLearningPathRequest):
    """
    创建个性化学习路径

    基于目标技能和当前水平的差距，生成学习路径
    """
    data = request.model_dump()
    path = training_effectiveness_v2_service.create_learning_path(data)

    return LearningPathResponse(
        path_id=path.id,
        employee_id=path.employee_id,
        goal_name=path.goal_name,
        status=path.status.value,
        overall_progress=path.overall_progress,
        total_items=len(path.path_items),
        completed_items=sum(1 for item in path.path_items if item.is_completed),
        estimated_hours=path.estimated_total_hours,
        path_items=[
            {
                "id": item.id,
                "name": item.content_name,
                "type": item.content_type,
                "sequence": item.sequence_order,
                "is_prerequisite": item.is_prerequisite,
                "estimated_hours": item.estimated_hours,
                "is_completed": item.is_completed,
                "target_skills": item.target_skills
            }
            for item in path.path_items
        ],
        recommendations=[
            f"优先完成{item.content_name}" for item in path.path_items if item.is_prerequisite
        ]
    )


@router.get("/learning-paths/{path_id}", response_model=Dict[str, Any])
async def get_learning_path(path_id: str):
    """
    获取学习路径详情
    """
    path = training_effectiveness_v2_service.get_learning_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")

    return {
        "id": path.id,
        "goal_name": path.goal_name,
        "status": path.status.value,
        "overall_progress": path.overall_progress,
        "skill_gaps": path.skill_gaps,
        "path_items": [
            {
                "id": item.id,
                "name": item.content_name,
                "is_completed": item.is_completed,
                "score": item.score
            }
            for item in path.path_items
        ],
        "created_at": path.created_at.isoformat(),
        "estimated_completion_date": path.estimated_completion_date.isoformat() if path.estimated_completion_date else None
    }


@router.get("/employees/{employee_id}/learning-paths", response_model=Dict[str, Any])
async def get_employee_learning_paths(employee_id: str):
    """
    获取员工的学习路径列表
    """
    paths = training_effectiveness_v2_service.get_employee_learning_paths(employee_id)

    return {
        "employee_id": employee_id,
        "total": len(paths),
        "paths": [
            {
                "id": p.id,
                "goal_name": p.goal_name,
                "status": p.status.value,
                "progress": p.overall_progress,
                "items_count": len(p.path_items),
                "estimated_hours": p.estimated_total_hours,
                "created_at": p.created_at.isoformat()
            }
            for p in paths
        ]
    }


@router.put("/learning-paths/{path_id}/progress", response_model=Dict[str, Any])
async def update_learning_path_progress(
    path_id: str,
    item_id: str = Body(..., description="学习项目 ID"),
    completed: bool = Body(..., description="是否完成"),
    score: Optional[float] = Body(None, description="完成分数")
):
    """
    更新学习路径进度
    """
    training_effectiveness_v2_service.update_path_progress(path_id, item_id, completed, score)

    path = training_effectiveness_v2_service.get_learning_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")

    return {
        "path_id": path_id,
        "new_progress": path.overall_progress,
        "new_status": path.status.value,
        "completed_items": sum(1 for item in path.path_items if item.is_completed),
        "total_items": len(path.path_items)
    }


@router.post("/learning-paths/recommend", response_model=LearningPathResponse)
async def recommend_learning_path(
    employee_id: str = Body(..., description="员工 ID"),
    current_skills: Dict[str, float] = Body(..., description="当前技能 {skill: score}"),
    target_role: str = Body(..., description="目标角色")
):
    """
    基于目标角色推荐学习路径
    """
    path = training_effectiveness_v2_service.recommend_learning_path(
        employee_id, current_skills, target_role
    )

    return LearningPathResponse(
        path_id=path.id,
        employee_id=path.employee_id,
        goal_name=path.goal_name,
        status=path.status.value,
        overall_progress=path.overall_progress,
        total_items=len(path.path_items),
        completed_items=0,
        estimated_hours=path.estimated_total_hours,
        path_items=[
            {
                "id": item.id,
                "name": item.content_name,
                "type": item.content_type,
                "sequence": item.sequence_order,
                "estimated_hours": item.estimated_hours,
                "target_skills": item.target_skills
            }
            for item in path.path_items
        ],
        recommendations=[
            f"建议从{path.path_items[0].content_name}开始学习",
            f"预计需要{path.estimated_total_hours}小时完成",
            f"将提升{len(path.skill_gaps)}项技能"
        ]
    )


# ==================== 培训效果追踪端点 ====================

@router.post("/impact-trackers", response_model=Dict[str, Any])
async def create_impact_tracker(
    employee_id: str = Body(..., description="员工 ID"),
    training_id: str = Body(..., description="培训 ID"),
    training_name: str = Body(..., description="培训名称"),
    pre_score: float = Body(..., description="培训前评分"),
    post_score: float = Body(..., description="培训后评分"),
    tenant_id: str = Body("default", description="租户 ID")
):
    """
    创建培训效果追踪器

    用于长期追踪培训对员工表现的影响
    """
    tracker = training_effectiveness_v2_service.create_impact_tracker(
        employee_id, training_id, training_name, pre_score, post_score, tenant_id
    )

    return {
        "tracker_id": tracker.id,
        "employee_id": tracker.employee_id,
        "training_name": tracker.training_name,
        "pre_score": tracker.pre_training_score,
        "post_score": tracker.post_training_score,
        "improvement_percentage": tracker.improvement_percentage,
        "impact_level": tracker.impact_level,
        "tracking_end_date": tracker.tracking_end_date.isoformat()
    }


@router.post("/impact-trackers/{tracker_id}/follow-up", response_model=Dict[str, Any])
async def add_follow_up_score(
    tracker_id: str,
    score: float = Body(..., description="跟踪评估分数"),
    metrics: Optional[Dict[str, Any]] = Body(None, description="相关指标")
):
    """
    添加跟踪评估分数

    用于追踪技能保持情况和衰减率
    """
    training_effectiveness_v2_service.add_follow_up_score(tracker_id, score, metrics)

    tracker = training_effectiveness_v2_service.get_impact_tracker(tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="追踪器不存在")

    return {
        "tracker_id": tracker_id,
        "skill_retention_rate": tracker.skill_retention_rate,
        "skill_decay_rate": tracker.skill_decay_rate,
        "follow_up_count": len(tracker.follow_up_scores),
        "last_tracked_at": tracker.last_tracked_at.isoformat()
    }


@router.get("/impact-trackers/{tracker_id}", response_model=Dict[str, Any])
async def get_impact_tracker(tracker_id: str):
    """
    获取培训效果追踪器详情
    """
    tracker = training_effectiveness_v2_service.get_impact_tracker(tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="追踪器不存在")

    return {
        "id": tracker.id,
        "training_name": tracker.training_name,
        "pre_score": tracker.pre_training_score,
        "post_score": tracker.post_training_score,
        "improvement_percentage": tracker.improvement_percentage,
        "skill_retention_rate": tracker.skill_retention_rate,
        "skill_decay_rate": tracker.skill_decay_rate,
        "impact_level": tracker.impact_level,
        "follow_up_scores": tracker.follow_up_scores,
        "created_at": tracker.created_at.isoformat(),
        "last_tracked_at": tracker.last_tracked_at.isoformat()
    }


@router.get("/employees/{employee_id}/impact-trackers", response_model=Dict[str, Any])
async def get_employee_impact_trackers(employee_id: str):
    """
    获取员工的培训效果追踪器列表
    """
    trackers = training_effectiveness_v2_service.get_employee_impact_trackers(employee_id)

    return {
        "employee_id": employee_id,
        "total": len(trackers),
        "trackers": [
            {
                "id": t.id,
                "training_name": t.training_name,
                "improvement_percentage": t.improvement_percentage,
                "impact_level": t.impact_level,
                "skill_retention_rate": t.skill_retention_rate,
                "follow_up_count": len(t.follow_up_scores)
            }
            for t in trackers
        ]
    }


# ==================== 认证集成端点 ====================

@router.post("/certifications/integrate", response_model=Dict[str, Any])
async def integrate_certification(
    employee_id: str = Body(..., description="员工 ID"),
    user_id: str = Body(..., description="用户 ID"),
    certification_id: str = Body(..., description="认证 ID"),
    certification_name: str = Body(..., description="认证名称"),
    exam_score: float = Body(..., description="考试成绩"),
    exam_passed: bool = Body(..., description="是否通过"),
    mapped_skills: Dict[str, float] = Body(default_factory=dict, description="映射技能"),
    tenant_id: str = Body("default", description="租户 ID")
):
    """
    集成认证系统

    将 P5 认证系统与培训效果评估关联
    """
    data = {
        "employee_id": employee_id,
        "user_id": user_id,
        "certification_id": certification_id,
        "certification_name": certification_name,
        "exam_score": exam_score,
        "exam_passed": exam_passed,
        "mapped_skills": mapped_skills,
        "tenant_id": tenant_id
    }

    cert = training_effectiveness_v2_service.integrate_certification(data)

    return {
        "cert_id": cert.id,
        "certification_name": cert.certification_name,
        "exam_score": cert.exam_score,
        "exam_passed": cert.exam_passed,
        "mapped_skills": cert.mapped_skills,
        "passed_at": cert.passed_at.isoformat() if cert.passed_at else None
    }


@router.get("/employees/{employee_id}/certifications", response_model=Dict[str, Any])
async def get_employee_certifications(employee_id: str):
    """
    获取员工的认证记录
    """
    certs = training_effectiveness_v2_service.get_employee_certifications(employee_id)

    return {
        "employee_id": employee_id,
        "total": len(certs),
        "certifications": [
            {
                "id": c.id,
                "name": c.certification_name,
                "level": c.certification_level,
                "score": c.exam_score,
                "passed": c.exam_passed,
                "mapped_skills_count": len(c.mapped_skills)
            }
            for c in certs
        ]
    }


# ==================== 综合报告端点 ====================

@router.get("/employees/{employee_id}/report", response_model=Dict[str, Any])
async def generate_effectiveness_report(
    employee_id: str,
    period: str = Query("last_90_days", description="报告周期 (last_30_days/last_90_days/last_365_days)")
):
    """
    生成培训效果综合报告

    整合评估、ROI、学习路径、认证等所有数据
    """
    report = training_effectiveness_v2_service.generate_effectiveness_report(employee_id, period)

    return {
        "report_id": report.id,
        "employee_id": report.employee_id,
        "period": report.report_period,
        "generated_at": report.generated_at.isoformat(),
        "summary": {
            "total_trainings": report.total_trainings,
            "completed_trainings": report.completed_trainings,
            "skills_improved_count": len(report.skills_improved),
            "average_improvement": report.average_improvement,
            "total_training_cost": report.total_training_cost,
            "total_benefit": report.total_benefit,
            "average_roi": report.average_roi,
            "certifications_earned": report.passed_certifications,
            "learning_paths_completed": report.completed_learning_paths
        },
        "insights": report.insights,
        "recommendations": report.recommendations
    }


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """
    培训效果评估增强服务健康检查
    """
    return {
        "status": "healthy",
        "service": "training_effectiveness_v2_service",
        "version": "v13.0.0",
        "features": [
            "skill_assessment",
            "pre_post_comparison",
            "roi_calculation",
            "learning_path_recommendation",
            "impact_tracking",
            "certification_integration",
            "comprehensive_report"
        ]
    }
