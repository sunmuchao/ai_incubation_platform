# -*- coding: utf-8 -*-
"""
v14.0.0 绩效评估增强 - API 路由层

绩效评估 API 端点：
- 360 度评估反馈
- OKR 目标管理
- 绩效仪表盘
- 1 对 1 会议记录
- 晋升推荐

作者：AI Employee Platform Team
创建日期：2026-04-05
版本：v14.0.0
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config.database import get_db
from services.performance_service import (
    PerformanceService,
    ReviewCycleService,
    PerformanceReviewService,
    ReviewDimensionService,
    ObjectiveService,
    KeyResultService,
    PerformanceMetricsService,
    OneOnOneMeetingService,
    PromotionService,
    BenchmarkService,
)
from models.p14_models import (
    ReviewType, ReviewStatus, ReviewCycleStatus,
    ObjectiveStatus, MetricType, ActionItemStatus, PromotionStatus,
)

router = APIRouter(prefix="/api/performance", tags=["Performance v14"])


# ==================== Pydantic 模型 ====================

# --- 评估周期 ---
class ReviewCycleCreate(BaseModel):
    name: str = Field(..., description="周期名称")
    description: Optional[str] = Field(None, description="描述")
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    review_type: ReviewType = Field(default=ReviewType._360, description="评估类型")
    target_employee_ids: Optional[List[str]] = Field(None, description="目标员工 ID 列表")


class ReviewCycleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    start_date: str
    end_date: str
    review_type: str
    target_employee_ids: Optional[List[str]]
    status: str
    created_at: str
    progress: Dict[str, Any]


# --- 绩效评估 ---
class PerformanceReviewCreate(BaseModel):
    employee_id: str = Field(..., description="被评估的员工 ID")
    reviewer_id: str = Field(..., description="评估人 ID")
    review_type: ReviewType = Field(default=ReviewType.MANAGER, description="评估类型")
    cycle_id: Optional[str] = Field(None, description="所属周期 ID")
    due_date: Optional[datetime] = Field(None, description="截止日期")


class PerformanceReviewUpdate(BaseModel):
    scores: Optional[Dict[str, float]] = Field(None, description="维度分数")
    comments: Optional[str] = Field(None, description="文字评价")
    strengths: Optional[List[str]] = Field(None, description="优势列表")
    areas_for_improvement: Optional[List[str]] = Field(None, description="待改进领域")
    goals: Optional[List[str]] = Field(None, description="下期目标")


class PerformanceReviewResponse(BaseModel):
    id: str
    employee_id: str
    reviewer_id: str
    review_type: str
    status: str
    scores: Dict[str, float]
    overall_score: Optional[float]
    comments: Optional[str]
    strengths: List[str]
    areas_for_improvement: List[str]
    goals: List[str]
    created_at: str
    is_overdue: bool


# --- 评估维度 ---
class ReviewDimensionCreate(BaseModel):
    name: str = Field(..., description="维度名称")
    description: Optional[str] = Field(None, description="维度描述")
    weight: float = Field(default=1.0, description="权重")
    max_score: float = Field(default=5.0, description="满分")
    cycle_id: Optional[str] = Field(None, description="所属周期 ID")
    dimension_type: str = Field(default="custom", description="维度类型")


class ReviewDimensionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    weight: float
    max_score: float
    dimension_type: str


# --- OKR 目标 ---
class ObjectiveCreate(BaseModel):
    title: str = Field(..., description="目标标题")
    description: Optional[str] = Field(None, description="目标描述")
    start_date: datetime = Field(..., description="开始日期")
    due_date: datetime = Field(..., description="截止日期")
    employee_id: Optional[str] = Field(None, description="所属员工 ID")
    department_id: Optional[str] = Field(None, description="所属部门 ID")
    company_id: Optional[str] = Field(None, description="公司 ID")
    parent_objective_id: Optional[str] = Field(None, description="上级目标 ID")


class ObjectiveUpdate(BaseModel):
    title: Optional[str] = Field(None, description="目标标题")
    description: Optional[str] = Field(None, description="目标描述")
    progress: Optional[float] = Field(None, description="进度", ge=0, le=100)
    status: Optional[ObjectiveStatus] = Field(None, description="状态")
    confidence_level: Optional[int] = Field(None, description="信心指数", ge=1, le=10)


class KeyResultCreate(BaseModel):
    objective_id: str = Field(..., description="关联目标 ID")
    title: str = Field(..., description="关键结果标题")
    description: Optional[str] = Field(None, description="描述")
    target_value: float = Field(..., description="目标值")
    metric_type: MetricType = Field(default=MetricType.NUMBER, description="指标类型")
    start_value: float = Field(default=0.0, description="起始值")
    unit: Optional[str] = Field(None, description="单位")
    stretch_target: Optional[float] = Field(None, description="延展目标")


class KeyResultProgressUpdate(BaseModel):
    current_value: float = Field(..., description="当前值")
    add_checkpoint: bool = Field(default=True, description="是否添加检查点")


class ObjectiveResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    start_date: str
    due_date: str
    progress: float
    status: str
    confidence_level: int
    key_results_count: int


class KeyResultResponse(BaseModel):
    id: str
    objective_id: str
    title: str
    description: Optional[str]
    metric_type: str
    unit: Optional[str]
    start_value: float
    target_value: float
    current_value: float
    progress: float
    stretch_target: Optional[float]
    is_stretch: bool


# --- 绩效指标 ---
class PerformanceMetricsCreate(BaseModel):
    employee_id: str = Field(..., description="员工 ID")
    period_start: datetime = Field(..., description="周期开始")
    period_end: datetime = Field(..., description="周期结束")
    efficiency_metrics: Optional[Dict[str, Any]] = Field(None, description="效率指标")
    quality_metrics: Optional[Dict[str, Any]] = Field(None, description="质量指标")
    contribution_metrics: Optional[Dict[str, Any]] = Field(None, description="贡献指标")
    growth_metrics: Optional[Dict[str, Any]] = Field(None, description="成长指标")


class PerformanceMetricsResponse(BaseModel):
    id: str
    employee_id: str
    period_start: str
    period_end: str
    efficiency_metrics: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    contribution_metrics: Dict[str, Any]
    growth_metrics: Dict[str, Any]
    overall_performance_score: Optional[float]
    created_at: str


# --- 1 对 1 会议 ---
class OneOnOneMeetingCreate(BaseModel):
    employee_id: str = Field(..., description="员工 ID")
    manager_id: str = Field(..., description="管理者 ID")
    meeting_date: datetime = Field(..., description="会议日期")
    agenda: Optional[str] = Field(None, description="议程")
    meeting_type: str = Field(default="regular", description="会议类型")
    duration_minutes: Optional[int] = Field(default=30, description="时长（分钟）")


class OneOnOneMeetingUpdate(BaseModel):
    notes: Optional[str] = Field(None, description="会议笔记")
    summary: Optional[str] = Field(None, description="摘要")
    topics_discussed: Optional[List[str]] = Field(None, description="讨论话题")
    follow_up_date: Optional[datetime] = Field(None, description="下次会议日期")


class ActionItemCreate(BaseModel):
    meeting_id: str = Field(..., description="会议 ID")
    description: str = Field(..., description="行动描述")
    owner_id: str = Field(..., description="负责人 ID")
    priority: str = Field(default="medium", description="优先级")
    owner_type: str = Field(default="employee", description="负责人类型")
    due_date: Optional[datetime] = Field(None, description="截止日期")


class ActionItemUpdate(BaseModel):
    status: Optional[ActionItemStatus] = Field(None, description="状态")
    notes: Optional[str] = Field(None, description="备注")


class OneOnOneMeetingResponse(BaseModel):
    id: str
    employee_id: str
    manager_id: str
    meeting_date: str
    meeting_type: str
    agenda: Optional[str]
    notes: Optional[str]
    summary: Optional[str]
    topics_discussed: List[str]
    follow_up_date: Optional[str]
    action_items_count: int
    completed_action_items: int


class ActionItemResponse(BaseModel):
    id: str
    meeting_id: str
    description: str
    priority: str
    owner_id: str
    status: str
    due_date: Optional[str]
    completed_at: Optional[str]
    notes: Optional[str]
    is_overdue: bool


# --- 晋升推荐 ---
class PromotionRecommendationCreate(BaseModel):
    employee_id: str = Field(..., description="员工 ID")
    current_level: str = Field(..., description="当前等级")
    performance_score: Optional[float] = Field(None, description="绩效分数")
    tenure_months: Optional[int] = Field(None, description="在职月数")
    skills_assessment: Optional[Dict[str, Any]] = Field(None, description="技能评估")


class PromotionApproval(BaseModel):
    reviewed_by: str = Field(..., description="审批人 ID")
    review_comments: Optional[str] = Field(None, description="审批意见")


class PromotionRecommendationResponse(BaseModel):
    id: str
    employee_id: str
    current_level: str
    recommended_level: str
    recommendation_score: float
    reasons: List[str]
    supporting_evidence: List[Dict]
    performance_score: Optional[float]
    tenure_months: Optional[int]
    status: str
    reviewed_by: Optional[str]
    review_comments: Optional[str]
    created_at: str


# ==================== 评估周期 API ====================

@router.post("/cycles", response_model=ReviewCycleResponse, tags=["Review Cycles"])
def create_review_cycle(
    cycle_data: ReviewCycleCreate,
    db: Session = Depends(get_db),
):
    """创建评估周期"""
    service = ReviewCycleService(db)
    cycle = service.create_cycle(
        name=cycle_data.name,
        start_date=cycle_data.start_date,
        end_date=cycle_data.end_date,
        description=cycle_data.description,
        review_type=cycle_data.review_type,
        target_employee_ids=cycle_data.target_employee_ids,
    )
    return cycle.to_dict()


@router.get("/cycles", response_model=List[ReviewCycleResponse], tags=["Review Cycles"])
def list_review_cycles(
    status: Optional[ReviewCycleStatus] = Query(None, description="状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
):
    """获取评估周期列表"""
    service = ReviewCycleService(db)
    cycles = service.list_cycles(status=status, limit=limit, offset=offset)
    return [c.to_dict() for c in cycles]


@router.get("/cycles/{cycle_id}", response_model=ReviewCycleResponse, tags=["Review Cycles"])
def get_review_cycle(
    cycle_id: str,
    db: Session = Depends(get_db),
):
    """获取评估周期详情"""
    service = ReviewCycleService(db)
    cycle = service.get_cycle(cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Review cycle not found")
    return cycle.to_dict()


@router.post("/cycles/{cycle_id}/launch", response_model=ReviewCycleResponse, tags=["Review Cycles"])
def launch_review_cycle(
    cycle_id: str,
    db: Session = Depends(get_db),
):
    """启动评估周期"""
    service = ReviewCycleService(db)
    try:
        cycle = service.launch_cycle(cycle_id)
        return cycle.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cycles/{cycle_id}/complete", response_model=ReviewCycleResponse, tags=["Review Cycles"])
def complete_review_cycle(
    cycle_id: str,
    db: Session = Depends(get_db),
):
    """完成评估周期"""
    service = ReviewCycleService(db)
    try:
        cycle = service.complete_cycle(cycle_id)
        return cycle.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cycles/{cycle_id}/progress", tags=["Review Cycles"])
def get_cycle_progress(
    cycle_id: str,
    db: Session = Depends(get_db),
):
    """获取周期进度"""
    service = ReviewCycleService(db)
    try:
        return service.get_cycle_progress(cycle_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== 绩效评估 API ====================

@router.post("/reviews", response_model=PerformanceReviewResponse, tags=["Performance Reviews"])
def create_performance_review(
    review_data: PerformanceReviewCreate,
    db: Session = Depends(get_db),
):
    """创建绩效评估"""
    service = PerformanceReviewService(db)
    review = service.create_review(
        employee_id=review_data.employee_id,
        reviewer_id=review_data.reviewer_id,
        review_type=review_data.review_type,
        cycle_id=review_data.cycle_id,
        due_date=review_data.due_date,
    )
    return review.to_dict()


@router.get("/reviews/{review_id}", response_model=PerformanceReviewResponse, tags=["Performance Reviews"])
def get_performance_review(
    review_id: str,
    db: Session = Depends(get_db),
):
    """获取绩效评估详情"""
    service = PerformanceReviewService(db)
    review = service.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Performance review not found")
    return review.to_dict()


@router.put("/reviews/{review_id}", response_model=PerformanceReviewResponse, tags=["Performance Reviews"])
def update_performance_review(
    review_id: str,
    review_data: PerformanceReviewUpdate,
    db: Session = Depends(get_db),
):
    """更新绩效评估"""
    service = PerformanceReviewService(db)
    try:
        review = service.update_review(
            review_id=review_id,
            scores=review_data.scores,
            comments=review_data.comments,
            strengths=review_data.strengths,
            areas_for_improvement=review_data.areas_for_improvement,
            goals=review_data.goals,
        )
        return review.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reviews/{review_id}/submit", response_model=PerformanceReviewResponse, tags=["Performance Reviews"])
def submit_performance_review(
    review_id: str,
    db: Session = Depends(get_db),
):
    """提交绩效评估"""
    service = PerformanceReviewService(db)
    try:
        review = service.submit_review(review_id)
        return review.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reviews/{review_id}/complete", response_model=PerformanceReviewResponse, tags=["Performance Reviews"])
def complete_performance_review(
    review_id: str,
    db: Session = Depends(get_db),
):
    """完成绩效评估"""
    service = PerformanceReviewService(db)
    try:
        review = service.complete_review(review_id)
        return review.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/employees/{employee_id}/reviews", response_model=List[PerformanceReviewResponse], tags=["Performance Reviews"])
def get_employee_reviews(
    employee_id: str,
    status: Optional[ReviewStatus] = Query(None, description="状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db),
):
    """获取员工的绩效评估列表"""
    service = PerformanceReviewService(db)
    reviews = service.get_employee_reviews(employee_id, status=status, limit=limit)
    return [r.to_dict() for r in reviews]


@router.get("/reviews/statistics", tags=["Performance Reviews"])
def get_review_statistics(
    cycle_id: Optional[str] = Query(None, description="周期 ID"),
    db: Session = Depends(get_db),
):
    """获取评估统计"""
    service = PerformanceReviewService(db)
    return service.get_review_statistics(cycle_id=cycle_id)


# ==================== 评估维度 API ====================

@router.post("/dimensions", response_model=ReviewDimensionResponse, tags=["Review Dimensions"])
def create_review_dimension(
    dimension_data: ReviewDimensionCreate,
    db: Session = Depends(get_db),
):
    """创建评估维度"""
    service = ReviewDimensionService(db)
    dimension = service.create_dimension(
        name=dimension_data.name,
        description=dimension_data.description,
        weight=dimension_data.weight,
        max_score=dimension_data.max_score,
        cycle_id=dimension_data.cycle_id,
        dimension_type=dimension_data.dimension_type,
    )
    return dimension.to_dict()


@router.get("/dimensions", response_model=List[ReviewDimensionResponse], tags=["Review Dimensions"])
def list_review_dimensions(
    cycle_id: Optional[str] = Query(None, description="周期 ID 筛选"),
    db: Session = Depends(get_db),
):
    """获取评估维度列表"""
    service = ReviewDimensionService(db)
    dimensions = service.list_dimensions(cycle_id=cycle_id)
    return [d.to_dict() for d in dimensions]


# ==================== OKR 目标 API ====================

@router.post("/objectives", tags=["OKR Objectives"])
def create_objective(
    objective_data: ObjectiveCreate,
    db: Session = Depends(get_db),
):
    """创建 OKR 目标"""
    service = ObjectiveService(db)
    objective = service.create_objective(
        title=objective_data.title,
        description=objective_data.description,
        start_date=objective_data.start_date,
        due_date=objective_data.due_date,
        employee_id=objective_data.employee_id,
        department_id=objective_data.department_id,
        company_id=objective_data.company_id,
        parent_objective_id=objective_data.parent_objective_id,
    )
    return objective.to_dict()


@router.get("/objectives/{objective_id}", tags=["OKR Objectives"])
def get_objective(
    objective_id: str,
    db: Session = Depends(get_db),
):
    """获取目标详情"""
    service = ObjectiveService(db)
    objective = service.get_objective(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")
    return objective.to_dict()


@router.put("/objectives/{objective_id}", tags=["OKR Objectives"])
def update_objective(
    objective_id: str,
    objective_data: ObjectiveUpdate,
    db: Session = Depends(get_db),
):
    """更新目标"""
    service = ObjectiveService(db)
    try:
        objective = service.update_objective(
            objective_id=objective_id,
            title=objective_data.title,
            description=objective_data.description,
            progress=objective_data.progress,
            status=objective_data.status,
            confidence_level=objective_data.confidence_level,
        )
        return objective.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/objectives/{objective_id}", tags=["OKR Objectives"])
def delete_objective(
    objective_id: str,
    db: Session = Depends(get_db),
):
    """删除目标"""
    service = ObjectiveService(db)
    try:
        service.delete_objective(objective_id)
        return {"message": "Objective deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/employees/{employee_id}/objectives", tags=["OKR Objectives"])
def get_employee_objectives(
    employee_id: str,
    status: Optional[ObjectiveStatus] = Query(None, description="状态筛选"),
    include_children: bool = Query(False, description="是否包含子目标"),
    db: Session = Depends(get_db),
):
    """获取员工的目标列表"""
    service = ObjectiveService(db)
    objectives = service.get_employee_objectives(employee_id, status=status, include_children=include_children)
    return [o.to_dict() for o in objectives]


@router.post("/objectives/{objective_id}/key-results", response_model=KeyResultResponse, tags=["OKR Key Results"])
def create_key_result(
    objective_id: str,
    kr_data: KeyResultCreate,
    db: Session = Depends(get_db),
):
    """创建关键结果"""
    service = KeyResultService(db)
    try:
        key_result = service.create_key_result(
            objective_id=objective_id,
            title=kr_data.title,
            description=kr_data.description,
            target_value=kr_data.target_value,
            metric_type=kr_data.metric_type,
            start_value=kr_data.start_value,
            unit=kr_data.unit,
            stretch_target=kr_data.stretch_target,
        )
        return key_result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/key-results/{kr_id}/progress", response_model=KeyResultResponse, tags=["OKR Key Results"])
def update_key_result_progress(
    kr_id: str,
    progress_data: KeyResultProgressUpdate,
    db: Session = Depends(get_db),
):
    """更新关键结果进度"""
    service = KeyResultService(db)
    try:
        key_result = service.update_key_result_progress(
            kr_id=kr_id,
            current_value=progress_data.current_value,
            add_checkpoint=progress_data.add_checkpoint,
        )
        return key_result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/key-results/{kr_id}", tags=["OKR Key Results"])
def delete_key_result(
    kr_id: str,
    db: Session = Depends(get_db),
):
    """删除关键结果"""
    service = KeyResultService(db)
    try:
        service.delete_key_result(kr_id)
        return {"message": "Key result deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/objectives/tree", tags=["OKR Objectives"])
def get_objective_tree(
    root_id: Optional[str] = Query(None, description="根目标 ID"),
    db: Session = Depends(get_db),
):
    """获取目标树形结构"""
    service = ObjectiveService(db)
    try:
        return service.get_objective_tree(root_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== 绩效指标 API ====================

@router.post("/metrics", response_model=PerformanceMetricsResponse, tags=["Performance Metrics"])
def create_performance_metrics(
    metrics_data: PerformanceMetricsCreate,
    db: Session = Depends(get_db),
):
    """创建绩效指标快照"""
    service = PerformanceMetricsService(db)
    metrics = service.create_metrics(
        employee_id=metrics_data.employee_id,
        period_start=metrics_data.period_start,
        period_end=metrics_data.period_end,
        efficiency_metrics=metrics_data.efficiency_metrics,
        quality_metrics=metrics_data.quality_metrics,
        contribution_metrics=metrics_data.contribution_metrics,
        growth_metrics=metrics_data.growth_metrics,
    )
    return metrics.to_dict()


@router.get("/metrics/{employee_id}", response_model=List[PerformanceMetricsResponse], tags=["Performance Metrics"])
def get_employee_metrics(
    employee_id: str,
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db),
):
    """获取员工的绩效指标历史"""
    service = PerformanceMetricsService(db)
    metrics = service.get_employee_metrics(employee_id, limit=limit)
    return [m.to_dict() for m in metrics]


@router.get("/metrics/{employee_id}/trend", tags=["Performance Metrics"])
def get_metrics_trend(
    employee_id: str,
    metric_name: str = Query(..., description="指标名称"),
    periods: int = Query(6, ge=1, le=24, description="周期数量"),
    db: Session = Depends(get_db),
):
    """获取指标趋势"""
    service = PerformanceMetricsService(db)
    return service.get_metrics_trend(employee_id, metric_name, periods)


@router.get("/dashboard", tags=["Performance Dashboard"])
def get_performance_dashboard(
    employee_ids: Optional[str] = Query(None, description="员工 ID 列表，逗号分隔"),
    db: Session = Depends(get_db),
):
    """获取综合仪表盘数据"""
    service = PerformanceMetricsService(db)
    employee_ids_list = employee_ids.split(",") if employee_ids else None
    return service.get_dashboard(employee_ids_list)


@router.get("/benchmarks", tags=["Performance Benchmarks"])
def get_benchmarks(
    db: Session = Depends(get_db),
):
    """获取绩效基准数据"""
    service = BenchmarkService(db)
    return service.get_benchmarks()


# ==================== 1 对 1 会议 API ====================

@router.post("/one-on-ones", tags=["One-on-One Meetings"])
def create_one_on_one_meeting(
    meeting_data: OneOnOneMeetingCreate,
    db: Session = Depends(get_db),
):
    """创建 1 对 1 会议记录"""
    service = OneOnOneMeetingService(db)
    meeting = service.create_meeting(
        employee_id=meeting_data.employee_id,
        manager_id=meeting_data.manager_id,
        meeting_date=meeting_data.meeting_date,
        agenda=meeting_data.agenda,
        meeting_type=meeting_data.meeting_type,
        duration_minutes=meeting_data.duration_minutes,
    )
    return meeting.to_dict()


@router.get("/one-on-ones/{meeting_id}", tags=["One-on-One Meetings"])
def get_one_on_one_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
):
    """获取会议详情"""
    service = OneOnOneMeetingService(db)
    meeting = service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting.to_dict()


@router.put("/one-on-ones/{meeting_id}", tags=["One-on-One Meetings"])
def update_one_on_one_meeting(
    meeting_id: str,
    meeting_data: OneOnOneMeetingUpdate,
    db: Session = Depends(get_db),
):
    """更新会议记录"""
    service = OneOnOneMeetingService(db)
    try:
        meeting = service.update_meeting(
            meeting_id=meeting_id,
            notes=meeting_data.notes,
            summary=meeting_data.summary,
            topics_discussed=meeting_data.topics_discussed,
            follow_up_date=meeting_data.follow_up_date,
        )
        return meeting.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/employees/{employee_id}/one-on-ones", tags=["One-on-One Meetings"])
def get_employee_meetings(
    employee_id: str,
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db),
):
    """获取员工的会议列表"""
    service = OneOnOneMeetingService(db)
    meetings = service.get_employee_meetings(employee_id, limit=limit)
    return [m.to_dict() for m in meetings]


@router.post("/one-on-ones/{meeting_id}/action-items", response_model=ActionItemResponse, tags=["Action Items"])
def create_action_item(
    meeting_id: str,
    action_data: ActionItemCreate,
    db: Session = Depends(get_db),
):
    """创建行动项"""
    service = OneOnOneMeetingService(db)
    try:
        action_item = service.create_action_item(
            meeting_id=meeting_id,
            description=action_data.description,
            owner_id=action_data.owner_id,
            priority=action_data.priority,
            owner_type=action_data.owner_type,
            due_date=action_data.due_date,
        )
        return action_item.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/action-items/{action_item_id}", response_model=ActionItemResponse, tags=["Action Items"])
def update_action_item(
    action_item_id: str,
    action_data: ActionItemUpdate,
    db: Session = Depends(get_db),
):
    """更新行动项"""
    service = OneOnOneMeetingService(db)
    try:
        action_item = service.update_action_item(
            action_item_id=action_item_id,
            status=action_data.status,
            notes=action_data.notes,
        )
        return action_item.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/one-on-ones/{meeting_id}/action-items", tags=["Action Items"])
def get_meeting_action_items(
    meeting_id: str,
    db: Session = Depends(get_db),
):
    """获取会议的行动项列表"""
    service = OneOnOneMeetingService(db)
    action_items = service.get_action_items(meeting_id)
    return [ai.to_dict() for ai in action_items]


# ==================== 晋升推荐 API ====================

@router.post("/promotions/recommend", response_model=PromotionRecommendationResponse, tags=["Promotion Recommendations"])
def generate_promotion_recommendation(
    promotion_data: PromotionRecommendationCreate,
    db: Session = Depends(get_db),
):
    """生成晋升推荐"""
    service = PromotionService(db)
    recommendation = service.generate_promotion_recommendation(
        employee_id=promotion_data.employee_id,
        current_level=promotion_data.current_level,
        performance_score=promotion_data.performance_score,
        tenure_months=promotion_data.tenure_months,
        skills_assessment=promotion_data.skills_assessment,
    )
    return recommendation.to_dict()


@router.get("/promotions/{recommendation_id}", response_model=PromotionRecommendationResponse, tags=["Promotion Recommendations"])
def get_promotion_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
):
    """获取晋升推荐详情"""
    service = PromotionService(db)
    recommendation = service.get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Promotion recommendation not found")
    return recommendation.to_dict()


@router.get("/promotions/pending", response_model=List[PromotionRecommendationResponse], tags=["Promotion Recommendations"])
def get_pending_promotions(
    db: Session = Depends(get_db),
):
    """获取待审批的晋升推荐"""
    service = PromotionService(db)
    recommendations = service.get_pending_promotions()
    return [r.to_dict() for r in recommendations]


@router.post("/promotions/{recommendation_id}/approve", response_model=PromotionRecommendationResponse, tags=["Promotion Recommendations"])
def approve_promotion(
    recommendation_id: str,
    approval_data: PromotionApproval,
    db: Session = Depends(get_db),
):
    """审批晋升"""
    service = PromotionService(db)
    try:
        recommendation = service.approve_promotion(
            recommendation_id=recommendation_id,
            reviewed_by=approval_data.reviewed_by,
            review_comments=approval_data.review_comments,
        )
        return recommendation.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/promotions/{recommendation_id}/reject", response_model=PromotionRecommendationResponse, tags=["Promotion Recommendations"])
def reject_promotion(
    recommendation_id: str,
    approval_data: PromotionApproval,
    db: Session = Depends(get_db),
):
    """拒绝晋升"""
    service = PromotionService(db)
    try:
        recommendation = service.reject_promotion(
            recommendation_id=recommendation_id,
            reviewed_by=approval_data.reviewed_by,
            review_comments=approval_data.review_comments,
        )
        return recommendation.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/employees/{employee_id}/promotions", response_model=List[PromotionRecommendationResponse], tags=["Promotion Recommendations"])
def get_employee_promotions(
    employee_id: str,
    status: Optional[PromotionStatus] = Query(None, description="状态筛选"),
    db: Session = Depends(get_db),
):
    """获取员工的晋升推荐历史"""
    service = PromotionService(db)
    recommendations = service.get_employee_recommendations(employee_id, status=status)
    return [r.to_dict() for r in recommendations]


# ==================== 健康检查 ====================

@router.get("/health", tags=["Health"])
def performance_health_check():
    """绩效评估服务健康检查"""
    return {
        "status": "healthy",
        "service": "performance",
        "version": "v14.0.0",
        "features": [
            "360 度评估反馈",
            "OKR 目标管理",
            "绩效仪表盘",
            "1 对 1 会议记录",
            "晋升推荐",
        ],
    }
