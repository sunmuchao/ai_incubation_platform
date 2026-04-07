"""
P18 阶段 API 路由 - 组织文化构建 (Organizational Culture Building)

路由列表:
1. 文化价值观管理
2. 员工认可与奖励
3. 团队凝聚力建设
4. 文化契合度评估
5. 多样性与包容性
6. 文化脉冲调查
7. 积分兑换
8. 文化指标仪表盘
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from datetime import datetime

from models.p18_models import (
    CultureValueType, RecognitionType, RecognitionCategory, AwardTier,
    TeamEventType, InclusionInitiativeType, DiversityDimension, SentimentLevel
)
from services.p18_culture_service import CultureService

router = APIRouter(prefix="/api/culture", tags=["P18 - 组织文化构建"])

# 初始化服务（使用默认数据库路径）
culture_service = CultureService("test.db")


# ==================== 文化价值观管理 ====================

@router.post("/values", summary="创建文化价值观")
async def create_culture_value(
    tenant_id: str = Query(..., description="租户 ID"),
    name: str = Query(..., description="价值观名称"),
    description: str = Query(..., description="价值观描述"),
    value_type: CultureValueType = Query(..., description="价值观类型"),
    behavioral_indicators: List[str] = Body([], description="行为指标列表"),
    priority: int = Query(1, description="优先级"),
    created_by: str = Query("", description="创建者 ID")
) -> Dict[str, Any]:
    """
    创建组织文化价值观
    
    - **tenant_id**: 租户 ID
    - **name**: 价值观名称，如"客户第一"
    - **description**: 价值观描述
    - **value_type**: 价值观类型 (core/behavioral/operational/aspirational)
    - **behavioral_indicators**: 行为指标列表
    - **priority**: 优先级，数字越小越优先
    """
    try:
        value = culture_service.create_culture_value(
            tenant_id=tenant_id,
            name=name,
            description=description,
            value_type=value_type,
            behavioral_indicators=behavioral_indicators,
            priority=priority,
            created_by=created_by
        )
        return {
            "success": True,
            "message": "文化价值观创建成功",
            "data": value.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/values", summary="列出文化价值观")
async def list_culture_values(
    tenant_id: str = Query(..., description="租户 ID"),
    active_only: bool = Query(True, description="是否只列出活跃的价值观")
) -> Dict[str, Any]:
    """列出组织的所有文化价值观"""
    try:
        values = culture_service.list_culture_values(tenant_id, active_only)
        return {
            "success": True,
            "data": [v.to_dict() for v in values]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/values/{value_id}", summary="获取文化价值观详情")
async def get_culture_value(value_id: str) -> Dict[str, Any]:
    """获取指定文化价值观的详情"""
    try:
        value = culture_service.list_culture_values("")  # 需要遍历查找
        for v in culture_service.culture_value_service.db.list_culture_values("", active_only=False):
            if v.id == value_id:
                return {
                    "success": True,
                    "data": v.to_dict()
                }
        raise HTTPException(status_code=404, detail="价值观不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/values/{value_id}", summary="更新文化价值观")
async def update_culture_value(
    value_id: str,
    name: Optional[str] = Query(None, description="价值观名称"),
    description: Optional[str] = Query(None, description="价值观描述"),
    behavioral_indicators: Optional[List[str]] = Body(None, description="行为指标列表"),
    priority: Optional[int] = Query(None, description="优先级")
) -> Dict[str, Any]:
    """更新文化价值观"""
    try:
        value = culture_service.culture_value_service.update_value(
            value_id=value_id,
            name=name,
            description=description,
            behavioral_indicators=behavioral_indicators,
            priority=priority
        )
        if not value:
            raise HTTPException(status_code=404, detail="价值观不存在")
        
        return {
            "success": True,
            "message": "文化价值观更新成功",
            "data": value.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/values/{value_id}", summary="删除文化价值观")
async def delete_culture_value(value_id: str) -> Dict[str, Any]:
    """删除（停用）文化价值观"""
    try:
        success = culture_service.culture_value_service.deactivate_value(value_id)
        if not success:
            raise HTTPException(status_code=404, detail="价值观不存在")
        
        return {
            "success": True,
            "message": "文化价值观已停用"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/values/{value_id}/alignments", summary="评估员工文化对齐度")
async def assess_employee_alignment(
    value_id: str,
    employee_id: str = Query(..., description="员工 ID"),
    alignment_score: float = Query(..., description="对齐度分数 0-100", ge=0, le=100),
    assessor_id: str = Query(..., description="评估者 ID"),
    evidence_examples: List[str] = Body([], description="证据示例"),
    comments: str = Query("", description="评语"),
    improvement_suggestions: List[str] = Body([], description="改进建议")
) -> Dict[str, Any]:
    """评估员工对某个文化价值观的对齐度"""
    try:
        alignment = culture_service.assess_employee_alignment(
            employee_id=employee_id,
            culture_value_id=value_id,
            alignment_score=alignment_score,
            assessor_id=assessor_id,
            evidence_examples=evidence_examples,
            comments=comments,
            improvement_suggestions=improvement_suggestions
        )
        return {
            "success": True,
            "message": "文化对齐度评估完成",
            "data": alignment.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees/{employee_id}/alignment-summary", summary="获取员工文化对齐度汇总")
async def get_employee_alignment_summary(employee_id: str) -> Dict[str, Any]:
    """获取员工对所有文化价值观的对齐度汇总"""
    try:
        summary = culture_service.culture_value_service.get_employee_alignment_summary(employee_id)
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 员工认可与奖励 ====================

@router.post("/recognitions", summary="给予员工认可")
async def give_recognition(
    tenant_id: str = Query(..., description="租户 ID"),
    recipient_id: str = Query(..., description="被认可人 ID"),
    giver_id: str = Query(..., description="给予认可的人 ID"),
    recognition_type: RecognitionType = Query(..., description="认可类型"),
    category: RecognitionCategory = Query(..., description="认可分类"),
    title: str = Query(..., description="认可标题"),
    description: str = Query(..., description="认可描述"),
    points: int = Query(0, description="奖励积分"),
    culture_value_ids: List[str] = Body([], description="关联的价值观 ID 列表"),
    recipient_type: str = Query("individual", description="认可对象类型：individual/team")
) -> Dict[str, Any]:
    """
    给予员工或团队认可
    
    - **recognition_type**: 认可类型 (peer/manager/team/company/automated)
    - **category**: 认可分类 (innovation/collaboration/excellence/culture_fit 等)
    """
    try:
        recognition = culture_service.give_recognition(
            tenant_id=tenant_id,
            recipient_id=recipient_id,
            giver_id=giver_id,
            recognition_type=recognition_type,
            category=category,
            title=title,
            description=description,
            points=points,
            culture_value_ids=culture_value_ids,
            recipient_type=recipient_type
        )
        return {
            "success": True,
            "message": "认可已提交",
            "data": recognition.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recognitions/{recognition_id}/approve", summary="批准认可")
async def approve_recognition(
    recognition_id: str,
    approver_id: str = Query(..., description="审批人 ID")
) -> Dict[str, Any]:
    """批准认可记录（如需要审批）"""
    try:
        recognition = culture_service.approve_recognition(recognition_id, approver_id)
        if not recognition:
            raise HTTPException(status_code=400, detail="无法批准该认可")
        
        return {
            "success": True,
            "message": "认可已批准",
            "data": recognition.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recognitions/{recognition_id}/reject", summary="拒绝认可")
async def reject_recognition(
    recognition_id: str,
    approver_id: str = Query(..., description="审批人 ID")
) -> Dict[str, Any]:
    """拒绝认可记录"""
    try:
        recognition = culture_service.reject_recognition(recognition_id, approver_id)
        if not recognition:
            raise HTTPException(status_code=400, detail="无法拒绝该认可")
        
        return {
            "success": True,
            "message": "认可已拒绝",
            "data": recognition.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recognitions/{recognition_id}", summary="获取认可详情")
async def get_recognition(recognition_id: str) -> Dict[str, Any]:
    """获取认可记录详情"""
    try:
        recognition = culture_service.recognition_service.get_recognition(recognition_id)
        if not recognition:
            raise HTTPException(status_code=404, detail="认可记录不存在")
        
        return {
            "success": True,
            "data": recognition.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees/{employee_id}/recognitions", summary="获取员工认可历史")
async def get_employee_recognitions(
    employee_id: str,
    tenant_id: str = Query(..., description="租户 ID"),
    limit: int = Query(50, description="返回数量限制")
) -> Dict[str, Any]:
    """获取员工的认可历史记录"""
    try:
        summary = culture_service.recognition_service.get_employee_recognition_summary(employee_id, tenant_id)
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 徽章系统 ====================

@router.post("/badges", summary="创建徽章")
async def create_badge(
    tenant_id: str = Query(..., description="租户 ID"),
    name: str = Query(..., description="徽章名称"),
    description: str = Query(..., description="徽章描述"),
    category: RecognitionCategory = Query(..., description="徽章分类"),
    tier: AwardTier = Query(..., description="徽章等级"),
    icon_url: str = Query("", description="徽章图标 URL"),
    criteria: Dict[str, Any] = Body({}, description="获取标准"),
    points_value: int = Query(0, description="积分价值")
) -> Dict[str, Any]:
    """创建新的徽章"""
    try:
        badge = culture_service.create_badge(
            tenant_id=tenant_id,
            name=name,
            description=description,
            category=category,
            tier=tier,
            icon_url=icon_url,
            criteria=criteria,
            points_value=points_value
        )
        return {
            "success": True,
            "message": "徽章创建成功",
            "data": badge.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/badges", summary="列出徽章")
async def list_badges(
    tenant_id: str = Query(..., description="租户 ID"),
    active_only: bool = Query(True, description="是否只列出活跃的徽章")
) -> Dict[str, Any]:
    """列出所有可用的徽章"""
    try:
        badges = culture_service.badge_service.list_badges(tenant_id, active_only)
        return {
            "success": True,
            "data": [b.to_dict() for b in badges]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/badges/award", summary="授予员工徽章")
async def award_badge(
    tenant_id: str = Query(..., description="租户 ID"),
    employee_id: str = Query(..., description="员工 ID"),
    badge_id: str = Query(..., description="徽章 ID"),
    recognition_id: Optional[str] = Query(None, description="关联的认可记录 ID"),
    expires_at: Optional[str] = Query(None, description="过期时间 (ISO 格式)")
) -> Dict[str, Any]:
    """授予员工徽章"""
    try:
        expires = datetime.fromisoformat(expires_at) if expires_at else None
        employee_badge = culture_service.award_badge(
            tenant_id=tenant_id,
            employee_id=employee_id,
            badge_id=badge_id,
            recognition_id=recognition_id,
            expires_at=expires
        )
        return {
            "success": True,
            "message": "徽章授予成功",
            "data": employee_badge.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees/{employee_id}/badges", summary="获取员工徽章")
async def get_employee_badges(employee_id: str) -> Dict[str, Any]:
    """获取员工已获得的所有徽章"""
    try:
        badges = culture_service.badge_service.get_employee_badges(employee_id)
        return {
            "success": True,
            "data": [b.to_dict() for b in badges]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 团队凝聚力建设 ====================

@router.post("/team-events", summary="创建团队活动")
async def create_team_event(
    tenant_id: str = Query(..., description="租户 ID"),
    team_id: str = Query(..., description="团队 ID"),
    organizer_id: str = Query(..., description="组织者 ID"),
    event_type: TeamEventType = Query(..., description="活动类型"),
    title: str = Query(..., description="活动标题"),
    description: str = Query(..., description="活动描述"),
    start_time: str = Query(..., description="开始时间 (ISO 格式)"),
    end_time: str = Query(..., description="结束时间 (ISO 格式)"),
    location: str = Query("", description="地点或虚拟链接"),
    max_participants: int = Query(0, description="最大参与人数 (0 为无限制)"),
    budget: Optional[float] = Query(None, description="预算")
) -> Dict[str, Any]:
    """创建团队凝聚力建设活动"""
    try:
        event = culture_service.create_team_event(
            tenant_id=tenant_id,
            team_id=team_id,
            organizer_id=organizer_id,
            event_type=event_type,
            title=title,
            description=description,
            start_time=datetime.fromisoformat(start_time),
            end_time=datetime.fromisoformat(end_time),
            location=location,
            max_participants=max_participants,
            budget=budget
        )
        return {
            "success": True,
            "message": "团队活动创建成功",
            "data": event.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team-events/{event_id}/join", summary="加入团队活动")
async def join_team_event(event_id: str, employee_id: str = Query(..., description="员工 ID")) -> Dict[str, Any]:
    """员工加入团队活动"""
    try:
        event = culture_service.join_team_event(event_id, employee_id)
        if not event:
            raise HTTPException(status_code=400, detail="无法加入该活动（可能已满或已结束）")
        
        return {
            "success": True,
            "message": "已成功加入活动",
            "data": event.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team-events/{event_id}/leave", summary="离开团队活动")
async def leave_team_event(event_id: str, employee_id: str = Query(..., description="员工 ID")) -> Dict[str, Any]:
    """员工离开团队活动"""
    try:
        event = culture_service.team_cohesion_service.leave_event(event_id, employee_id)
        if not event:
            raise HTTPException(status_code=400, detail="无法离开该活动")
        
        return {
            "success": True,
            "message": "已离开活动",
            "data": event.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team-events/{event_id}/complete", summary="完成团队活动")
async def complete_team_event(
    event_id: str,
    photos: List[str] = Body([], description="活动照片 URL 列表"),
    feedback_summary: str = Body("", description="反馈总结")
) -> Dict[str, Any]:
    """标记团队活动为已完成"""
    try:
        event = culture_service.team_cohesion_service.complete_event(event_id, photos, feedback_summary)
        if not event:
            raise HTTPException(status_code=400, detail="无法完成该活动")
        
        return {
            "success": True,
            "message": "活动已完成",
            "data": event.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team-events/{event_id}/cancel", summary="取消团队活动")
async def cancel_team_event(event_id: str) -> Dict[str, Any]:
    """取消团队活动"""
    try:
        success = culture_service.team_cohesion_service.cancel_event(event_id)
        if not success:
            raise HTTPException(status_code=400, detail="无法取消该活动")
        
        return {
            "success": True,
            "message": "活动已取消"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team-events/{event_id}", summary="获取团队活动详情")
async def get_team_event(event_id: str) -> Dict[str, Any]:
    """获取团队活动详情"""
    try:
        event = culture_service.team_cohesion_service.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="活动不存在")
        
        return {
            "success": True,
            "data": event.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team-events", summary="列出团队活动")
async def list_team_events(
    tenant_id: str = Query(..., description="租户 ID"),
    team_id: Optional[str] = Query(None, description="团队 ID（可选）")
) -> Dict[str, Any]:
    """列出团队活动"""
    try:
        events = culture_service.list_team_events(tenant_id, team_id)
        return {
            "success": True,
            "data": [e.to_dict() for e in events]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teams/{team_id}/cohesion-metrics", summary="获取团队凝聚力指标")
async def get_team_cohesion_metrics(
    team_id: str,
    tenant_id: str = Query(..., description="租户 ID")
) -> Dict[str, Any]:
    """获取团队凝聚力指标"""
    try:
        metrics = culture_service.team_cohesion_service.get_team_cohesion_metrics(team_id, tenant_id)
        return {
            "success": True,
            "data": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 文化契合度评估 ====================

@router.post("/culture-fit/assessments", summary="创建文化契合度评估")
async def create_culture_fit_assessment(
    tenant_id: str = Query(..., description="租户 ID"),
    employee_id: str = Query(..., description="员工 ID"),
    assessor_id: str = Query(..., description="评估者 ID"),
    assessment_type: str = Query(..., description="评估类型：self/manager/peer/team"),
    overall_score: float = Query(..., description="总体分数 0-100", ge=0, le=100),
    dimension_scores: Dict[str, float] = Body({}, description="各维度分数"),
    strengths: List[str] = Body([], description="优势列表"),
    development_areas: List[str] = Body([], description="待发展领域"),
    comments: str = Query("", description="评语"),
    recommendations: List[str] = Body([], description="建议列表")
) -> Dict[str, Any]:
    """创建员工文化契合度评估"""
    try:
        assessment = culture_service.create_culture_fit_assessment(
            tenant_id=tenant_id,
            employee_id=employee_id,
            assessor_id=assessor_id,
            assessment_type=assessment_type,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            strengths=strengths,
            development_areas=development_areas,
            comments=comments,
            recommendations=recommendations
        )
        return {
            "success": True,
            "message": "文化契合度评估完成",
            "data": assessment.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees/{employee_id}/culture-fit", summary="获取员工文化契合度评估历史")
async def get_employee_culture_fit(employee_id: str) -> Dict[str, Any]:
    """获取员工的文化契合度评估历史"""
    try:
        assessments = culture_service.culture_fit_service.get_employee_assessments(employee_id)
        return {
            "success": True,
            "data": [a.to_dict() for a in assessments]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 多样性与包容性 ====================

@router.post("/diversity/metrics", summary="记录多样性指标")
async def record_diversity_metric(
    tenant_id: str = Query(..., description="租户 ID"),
    dimension: DiversityDimension = Query(..., description="多样性维度"),
    distribution: Dict[str, float] = Body({}, description="分布比例"),
    representation_rate: float = Query(..., description="代表性比例", ge=0, le=1),
    inclusion_index: float = Query(..., description="包容性指数", ge=0, le=100),
    team_id: Optional[str] = Query(None, description="团队 ID（可选）"),
    comments: str = Query("", description="备注")
) -> Dict[str, Any]:
    """记录多样性指标数据"""
    try:
        metric = culture_service.record_diversity_metric(
            tenant_id=tenant_id,
            dimension=dimension,
            distribution=distribution,
            representation_rate=representation_rate,
            inclusion_index=inclusion_index,
            team_id=team_id,
            comments=comments
        )
        return {
            "success": True,
            "message": "多样性指标已记录",
            "data": metric.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diversity/metrics", summary="获取多样性指标趋势")
async def get_diversity_metrics(
    tenant_id: str = Query(..., description="租户 ID"),
    dimension: DiversityDimension = Query(..., description="多样性维度"),
    team_id: Optional[str] = Query(None, description="团队 ID（可选）")
) -> Dict[str, Any]:
    """获取多样性指标历史趋势"""
    try:
        metrics = culture_service.diversity_service.get_diversity_trends(tenant_id, dimension)
        return {
            "success": True,
            "data": [m.to_dict() for m in metrics]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inclusion/initiatives", summary="创建包容性举措")
async def create_inclusion_initiative(
    tenant_id: str = Query(..., description="租户 ID"),
    initiative_type: InclusionInitiativeType = Query(..., description="举措类型"),
    title: str = Query(..., description="举措标题"),
    description: str = Query(..., description="举措描述"),
    owner_id: str = Query(..., description="负责人 ID"),
    target_dimensions: List[DiversityDimension] = Body([], description="目标多样性维度"),
    start_date: str = Query(..., description="开始日期 (ISO 格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (ISO 格式)"),
    budget: Optional[float] = Query(None, description="预算")
) -> Dict[str, Any]:
    """创建包容性举措"""
    try:
        initiative = culture_service.create_inclusion_initiative(
            tenant_id=tenant_id,
            initiative_type=initiative_type,
            title=title,
            description=description,
            owner_id=owner_id,
            target_dimensions=target_dimensions,
            start_date=datetime.fromisoformat(start_date),
            end_date=datetime.fromisoformat(end_date) if end_date else None,
            budget=budget
        )
        return {
            "success": True,
            "message": "包容性举措已创建",
            "data": initiative.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inclusion/initiatives", summary="列出包容性举措")
async def list_inclusion_initiatives(
    tenant_id: str = Query(..., description="租户 ID"),
    status: Optional[str] = Query(None, description="状态筛选")
) -> Dict[str, Any]:
    """列出包容性举措"""
    try:
        initiatives = culture_service.diversity_service.list_initiatives(tenant_id, status)
        return {
            "success": True,
            "data": [i.to_dict() for i in initiatives]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 文化脉冲调查 ====================

@router.post("/pulses", summary="创建文化脉冲调查")
async def create_culture_pulse(
    tenant_id: str = Query(..., description="租户 ID"),
    title: str = Query(..., description="调查标题"),
    question: str = Query(..., description="调查问题"),
    question_type: str = Query("scale", description="问题类型：scale/multiple_choice/open"),
    scale_min: int = Query(1, description="量表最小值"),
    scale_max: int = Query(5, description="量表最大值"),
    scale_labels: Dict[str, str] = Body({}, description="量表标签"),
    options: List[str] = Body([], description="多选选项"),
    is_anonymous: bool = Query(True, description="是否匿名"),
    frequency: str = Query("weekly", description="频率：daily/weekly/monthly/quarterly"),
    created_by: str = Query("", description="创建者 ID")
) -> Dict[str, Any]:
    """创建文化脉冲调查"""
    try:
        pulse = culture_service.create_culture_pulse(
            tenant_id=tenant_id,
            title=title,
            question=question,
            question_type=question_type,
            scale_min=scale_min,
            scale_max=scale_max,
            scale_labels={int(k): v for k, v in scale_labels.items()},
            options=options,
            is_anonymous=is_anonymous,
            frequency=frequency,
            created_by=created_by
        )
        return {
            "success": True,
            "message": "文化脉冲调查已创建",
            "data": pulse.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pulses", summary="列出文化脉冲调查")
async def list_culture_pulses(
    tenant_id: str = Query(..., description="租户 ID"),
    active_only: bool = Query(True, description="是否只列出活跃的调查")
) -> Dict[str, Any]:
    """列出文化脉冲调查"""
    try:
        pulses = culture_service.pulse_service.list_pulses(tenant_id, active_only)
        return {
            "success": True,
            "data": [p.to_dict() for p in pulses]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pulses/{pulse_id}/responses", summary="提交脉冲调查回复")
async def submit_pulse_response(
    pulse_id: str,
    respondent_id: str = Query(..., description="回复者 ID"),
    response_value: Optional[float] = Query(None, description="量表/选择值"),
    response_text: Optional[str] = Body(None, description="开放文本回复"),
    is_anonymous: bool = Query(True, description="是否匿名回复")
) -> Dict[str, Any]:
    """提交文化脉冲调查回复"""
    try:
        response = culture_service.submit_pulse_response(
            pulse_id=pulse_id,
            respondent_id=respondent_id,
            response_value=response_value,
            response_text=response_text,
            is_anonymous=is_anonymous
        )
        return {
            "success": True,
            "message": "回复已提交",
            "data": response.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pulses/{pulse_id}/results", summary="获取脉冲调查结果")
async def get_pulse_results(pulse_id: str) -> Dict[str, Any]:
    """获取文化脉冲调查结果统计"""
    try:
        results = culture_service.pulse_service.get_pulse_results(pulse_id)
        return {
            "success": True,
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 积分兑换 ====================

@router.post("/redemptions", summary="请求积分兑换")
async def request_redemption(
    tenant_id: str = Query(..., description="租户 ID"),
    employee_id: str = Query(..., description="员工 ID"),
    reward_name: str = Query(..., description="奖励名称"),
    reward_description: str = Query(..., description="奖励描述"),
    points_cost: int = Query(..., description="所需积分")
) -> Dict[str, Any]:
    """请求积分兑换奖励"""
    try:
        redemption = culture_service.request_redemption(
            tenant_id=tenant_id,
            employee_id=employee_id,
            reward_name=reward_name,
            reward_description=reward_description,
            points_cost=points_cost
        )
        return {
            "success": True,
            "message": "兑换请求已提交",
            "data": redemption.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/redemptions/{redemption_id}/approve", summary="批准积分兑换")
async def approve_redemption(
    redemption_id: str,
    approver_id: str = Query(..., description="审批人 ID")
) -> Dict[str, Any]:
    """批准积分兑换请求"""
    try:
        redemption = culture_service.redemption_service.approve_redemption(redemption_id, approver_id)
        if not redemption:
            raise HTTPException(status_code=400, detail="无法批准该兑换")
        
        return {
            "success": True,
            "message": "兑换已批准",
            "data": redemption.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/redemptions/{redemption_id}/fulfill", summary="完成积分兑换")
async def fulfill_redemption(redemption_id: str) -> Dict[str, Any]:
    """完成积分兑换（已发放奖励）"""
    try:
        redemption = culture_service.redemption_service.fulfill_redemption(redemption_id)
        if not redemption:
            raise HTTPException(status_code=400, detail="无法完成该兑换")
        
        return {
            "success": True,
            "message": "兑换已完成",
            "data": redemption.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employees/{employee_id}/redemptions", summary="获取员工积分兑换历史")
async def get_employee_redemptions(employee_id: str) -> Dict[str, Any]:
    """获取员工的积分兑换历史记录"""
    try:
        redemptions = culture_service.redemption_service.get_employee_redemptions(employee_id)
        return {
            "success": True,
            "data": [r.to_dict() for r in redemptions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 文化指标仪表盘 ====================

@router.post("/metrics/calculate", summary="计算文化指标")
async def calculate_culture_metrics(
    tenant_id: str = Query(..., description="租户 ID"),
    employee_ids: List[str] = Body([], description="员工 ID 列表")
) -> Dict[str, Any]:
    """计算每日文化指标"""
    try:
        metrics = culture_service.calculate_daily_metrics(tenant_id, employee_ids)
        return {
            "success": True,
            "data": metrics.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", summary="获取文化仪表盘")
async def get_culture_dashboard(
    tenant_id: str = Query(..., description="租户 ID"),
    days: int = Query(30, description="天数范围")
) -> Dict[str, Any]:
    """获取组织文化健康度仪表盘"""
    try:
        dashboard = culture_service.get_culture_dashboard(tenant_id, days)
        return {
            "success": True,
            "data": dashboard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 系统信息 ====================

@router.get("/info", summary="P18 文化服务信息")
async def get_culture_service_info() -> Dict[str, Any]:
    """获取 P18 服务信息和功能列表"""
    return {
        "version": "18.0.0",
        "features": [
            "文化价值观管理",
            "员工认可与奖励",
            "徽章系统",
            "团队凝聚力建设",
            "文化契合度评估",
            "多样性与包容性",
            "文化脉冲调查",
            "积分兑换",
            "文化指标仪表盘"
        ],
        "endpoints": {
            "culture_values": "/api/culture/values",
            "recognitions": "/api/culture/recognitions",
            "badges": "/api/culture/badges",
            "team_events": "/api/culture/team-events",
            "culture_fit": "/api/culture/culture-fit",
            "diversity": "/api/culture/diversity",
            "pulses": "/api/culture/pulses",
            "redemptions": "/api/culture/redemptions",
            "dashboard": "/api/culture/dashboard"
        }
    }
