"""
评价、雇主档案、技能 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.employee import (
    Review, ReviewDimension, ReviewType, EmployerProfile, SkillTag, EmployeeSkill,
    SkillLevel, SkillCategory,
    ReviewSubmitRequestV2, ReviewResponseRequest,
    EmployerProfileCreateRequest, EmployerProfileUpdateRequest,
    SkillTagCreateRequest, EmployeeSkillAddRequest
)
from models.db_models import ReviewTypeEnum, EmployerStatusEnum, SkillCategoryEnum, SkillLevelEnum
from services.review_service import review_service, employer_profile_service, skill_service

router = APIRouter(prefix="/api", tags=["reviews", "employers", "skills"])


# ======================================
# 评价相关接口
# ======================================

@router.post("/reviews", response_model=Review)
async def create_review(request: ReviewSubmitRequestV2, order_id: str, tenant_id: str, reviewer_id: str):
    """创建评价（双向）"""
    # 获取订单信息（实际应该从订单服务获取）
    # 这里简化处理，假设调用方能提供正确的 employee_id 和 reviewee_id
    from services.employee_service import employee_service
    order = employee_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 确定评价类型和被评价者
    if request.review_type == ReviewType.HIRER_TO_EMPLOYEE:
        reviewee_id = order.owner_id  # 员工所有者
    else:
        reviewee_id = order.hirer_id  # 租赁者

    review_db = review_service.create_review(
        tenant_id=tenant_id,
        order_id=order_id,
        employee_id=order.employee_id,
        reviewer_id=reviewer_id,
        reviewee_id=reviewee_id,
        review_type=ReviewTypeEnum(request.review_type.value),
        rating=request.rating,
        review_text=request.review_text,
        review_tags=request.review_tags,
        communication=request.communication,
        quality=request.quality,
        timeliness=request.timeliness,
        professionalism=request.professionalism,
        is_public=request.is_public
    )

    if not review_db:
        raise HTTPException(status_code=400, detail="Failed to create review. Order may not be completed or review already exists.")

    return _convert_review_db_to_model(review_db)


@router.get("/reviews/{review_id}", response_model=Review)
async def get_review(review_id: str):
    """获取评价详情"""
    review_db = review_service.get_review(review_id)
    if not review_db:
        raise HTTPException(status_code=404, detail="Review not found")
    return _convert_review_db_to_model(review_db)


@router.get("/reviews", response_model=List[Review])
async def list_reviews(
    tenant_id: Optional[str] = None,
    employee_id: Optional[str] = None,
    review_type: Optional[ReviewType] = None,
    min_rating: float = Query(0, ge=0, le=5),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """获取评价列表"""
    review_type_enum = ReviewTypeEnum(review_type.value) if review_type else None
    reviews_db = review_service.list_reviews(
        tenant_id=tenant_id,
        employee_id=employee_id,
        review_type=review_type_enum,
        min_rating=min_rating,
        limit=limit,
        offset=offset
    )
    return [_convert_review_db_to_model(r) for r in reviews_db]


@router.post("/reviews/{review_id}/like")
async def like_review(review_id: str):
    """点赞评价"""
    if not review_service.like_review(review_id):
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review liked successfully"}


@router.post("/reviews/{review_id}/respond")
async def respond_review(review_id: str, request: ReviewResponseRequest):
    """回复评价"""
    if not review_service.respond_to_review(review_id, request.response_text):
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review responded successfully"}


# ======================================
# 雇主档案接口
# ======================================

@router.post("/employer-profiles", response_model=EmployerProfile)
async def create_employer_profile(request: EmployerProfileCreateRequest, tenant_id: str):
    """创建雇主档案"""
    profile_db = employer_profile_service.create_profile(
        tenant_id=tenant_id,
        user_id=request.user_id,
        company_name=request.company_name,
        industry=request.industry,
        company_size=request.company_size,
        description=request.description
    )
    if not profile_db:
        raise HTTPException(status_code=400, detail="Failed to create profile. User may already have a profile.")
    return _convert_employer_profile_db_to_model(profile_db)


@router.get("/employer-profiles/{profile_id}", response_model=EmployerProfile)
async def get_employer_profile(profile_id: str):
    """获取雇主档案"""
    profile_db = employer_profile_service.get_profile(profile_id)
    if not profile_db:
        raise HTTPException(status_code=404, detail="Employer profile not found")
    return _convert_employer_profile_db_to_model(profile_db)


@router.get("/employer-profiles/user/{user_id}", response_model=EmployerProfile)
async def get_employer_profile_by_user(user_id: str):
    """通过用户 ID 获取雇主档案"""
    profile_db = employer_profile_service.get_profile_by_user(user_id)
    if not profile_db:
        raise HTTPException(status_code=404, detail="Employer profile not found")
    return _convert_employer_profile_db_to_model(profile_db)


@router.put("/employer-profiles/{profile_id}", response_model=EmployerProfile)
async def update_employer_profile(profile_id: str, request: EmployerProfileUpdateRequest):
    """更新雇主档案"""
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    profile_db = employer_profile_service.update_profile(profile_id, **update_data)
    if not profile_db:
        raise HTTPException(status_code=404, detail="Employer profile not found")
    return _convert_employer_profile_db_to_model(profile_db)


@router.get("/employer-profiles", response_model=List[EmployerProfile])
async def list_employer_profiles(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """获取雇主档案列表"""
    profiles_db = employer_profile_service.list_profiles(
        tenant_id=tenant_id,
        status=status,
        limit=limit,
        offset=offset
    )
    return [_convert_employer_profile_db_to_model(p) for p in profiles_db]


# ======================================
# 技能标签接口
# ======================================

@router.post("/skill-tags", response_model=SkillTag)
async def create_skill_tag(request: SkillTagCreateRequest):
    """创建技能标签"""
    skill_tag_db = skill_service.create_skill_tag(
        name=request.name,
        category=SkillCategoryEnum(request.category.value),
        parent_skill_id=request.parent_skill_id,
        description=request.description,
        has_certification=request.has_certification,
        certification_name=request.certification_name
    )
    if not skill_tag_db:
        raise HTTPException(status_code=400, detail="Failed to create skill tag. Name may already exist.")
    return _convert_skill_tag_db_to_model(skill_tag_db)


@router.get("/skill-tags/{skill_tag_id}", response_model=SkillTag)
async def get_skill_tag(skill_tag_id: str):
    """获取技能标签"""
    skill_tag_db = skill_service.get_skill_tag(skill_tag_id)
    if not skill_tag_db:
        raise HTTPException(status_code=404, detail="Skill tag not found")
    return _convert_skill_tag_db_to_model(skill_tag_db)


@router.get("/skill-tags", response_model=List[SkillTag])
async def list_skill_tags(
    category: Optional[SkillCategory] = None,
    parent_skill_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """获取技能标签列表"""
    category_enum = SkillCategoryEnum(category.value) if category else None
    skill_tags_db = skill_service.list_skill_tags(
        category=category_enum,
        parent_skill_id=parent_skill_id,
        limit=limit,
        offset=offset
    )
    return [_convert_skill_tag_db_to_model(s) for s in skill_tags_db]


@router.post("/employees/{employee_id}/skills", response_model=EmployeeSkill)
async def add_employee_skill(employee_id: str, request: EmployeeSkillAddRequest):
    """添加员工技能"""
    skill_tag_db = skill_service.get_skill_tag(request.skill_tag_id)
    if not skill_tag_db:
        raise HTTPException(status_code=404, detail="Skill tag not found")

    employee_skill_db = skill_service.add_employee_skill(
        employee_id=employee_id,
        skill_tag_id=request.skill_tag_id,
        skill_name=skill_tag_db.name,
        level=SkillLevelEnum(request.level.value),
        years_of_experience=request.years_of_experience,
        certified=request.certified,
        certification_id=request.certification_id,
        portfolio_items=request.portfolio_items
    )
    if not employee_skill_db:
        raise HTTPException(status_code=400, detail="Failed to add skill. Employee may already have this skill.")
    return _convert_employee_skill_db_to_model(employee_skill_db)


@router.delete("/employees/{employee_id}/skills/{skill_tag_id}")
async def remove_employee_skill(employee_id: str, skill_tag_id: str):
    """移除员工技能"""
    if not skill_service.remove_employee_skill(employee_id, skill_tag_id):
        raise HTTPException(status_code=404, detail="Employee skill not found")
    return {"message": "Skill removed successfully"}


@router.get("/employees/{employee_id}/skills", response_model=List[EmployeeSkill])
async def list_employee_skills(employee_id: str):
    """获取员工技能列表"""
    skills_db = skill_service.list_employee_skills(employee_id)
    return [_convert_employee_skill_db_to_model(s) for s in skills_db]


# ======================================
# 转换函数
# ======================================

def _convert_review_db_to_model(review_db) -> Review:
    """将 ReviewDB 转换为 Review 模型"""
    return Review(
        id=review_db.id,
        tenant_id=review_db.tenant_id,
        order_id=review_db.order_id,
        employee_id=review_db.employee_id,
        reviewer_id=review_db.reviewer_id,
        reviewee_id=review_db.reviewee_id,
        review_type=ReviewType(review_db.review_type.value),
        rating=review_db.rating,
        review_text=review_db.review_text,
        review_tags=review_db.review_tags,
        dimensions=ReviewDimension(
            communication=review_db.communication,
            quality=review_db.quality,
            timeliness=review_db.timeliness,
            professionalism=review_db.professionalism
        ),
        is_public=review_db.is_public,
        is_hidden=review_db.is_hidden,
        likes=review_db.likes,
        response=review_db.response,
        response_at=review_db.response_at,
        created_at=review_db.created_at,
        updated_at=review_db.updated_at
    )


def _convert_employer_profile_db_to_model(profile_db) -> EmployerProfile:
    """将 EmployerProfileDB 转换为 EmployerProfile 模型"""
    from models.employee import EmployerStatus
    return EmployerProfile(
        id=profile_db.id,
        tenant_id=profile_db.tenant_id,
        user_id=profile_db.user_id,
        company_name=profile_db.company_name,
        industry=profile_db.industry,
        company_size=profile_db.company_size,
        description=profile_db.description,
        total_hires=profile_db.total_hires,
        total_spent=profile_db.total_spent,
        active_jobs=profile_db.active_jobs,
        rating=profile_db.rating,
        review_count=profile_db.review_count,
        avg_response_time_hours=profile_db.avg_response_time_hours,
        rehire_rate=profile_db.rehire_rate,
        status=EmployerStatus(profile_db.status.value),
        is_verified=profile_db.is_verified,
        verification_badges=profile_db.verification_badges,
        risk_score=profile_db.risk_score,
        violation_count=profile_db.violation_count,
        created_at=profile_db.created_at,
        updated_at=profile_db.updated_at
    )


def _convert_skill_tag_db_to_model(skill_tag_db) -> SkillTag:
    """将 SkillTagDB 转换为 SkillTag 模型"""
    return SkillTag(
        id=skill_tag_db.id,
        name=skill_tag_db.name,
        category=SkillCategory(skill_tag_db.category.value),
        parent_skill_id=skill_tag_db.parent_skill_id,
        description=skill_tag_db.description,
        usage_count=skill_tag_db.usage_count,
        avg_hourly_rate=skill_tag_db.avg_hourly_rate,
        has_certification=skill_tag_db.has_certification,
        certification_name=skill_tag_db.certification_name,
        created_at=skill_tag_db.created_at
    )


def _convert_employee_skill_db_to_model(skill_db) -> EmployeeSkill:
    """将 EmployeeSkillDB 转换为 EmployeeSkill 模型"""
    return EmployeeSkill(
        id=skill_db.id,
        employee_id=skill_db.employee_id,
        skill_tag_id=skill_db.skill_tag_id,
        skill_name=skill_db.skill_name,
        level=SkillLevel(skill_db.level.value),
        years_of_experience=skill_db.years_of_experience,
        certified=skill_db.certified,
        certification_id=skill_db.certification_id,
        portfolio_items=skill_db.portfolio_items,
        verified_at=skill_db.verified_at,
        created_at=skill_db.created_at
    )
