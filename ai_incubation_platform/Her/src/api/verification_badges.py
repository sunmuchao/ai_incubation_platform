"""
P6 信任标识体系 API

提供认证徽章管理、学历认证、职业认证等功能。
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.verification_badge_service import VerificationBadgeService


router = APIRouter(prefix="/api/verification", tags=["verification"])


@router.get("/badges")
async def get_user_badges(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取用户的信任徽章"""
    service = VerificationBadgeService(db)
    badges = service.get_user_badges(current_user.id)

    return {
        "success": True,
        "data": badges
    }


@router.get("/trust-score")
async def get_trust_score(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取用户信任评分"""
    service = VerificationBadgeService(db)
    trust_data = service.get_trust_score(current_user.id)

    return {
        "success": True,
        "data": trust_data
    }


@router.get("/badges/all")
async def get_all_badge_types(
    db: Session = Depends(get_db)
):
    """获取所有可用的徽章类型"""
    from services.verification_badge_service import BADGE_TYPES

    badge_list = [
        {
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "icon_url": info["icon_url"],
            "display_order": info["display_order"],
        }
        for key, info in BADGE_TYPES.items()
    ]

    return {
        "success": True,
        "data": badge_list
    }


@router.post("/education/submit")
async def submit_education_verification(
    school_name: str = Body(...),
    degree: Optional[str] = Body(default=None),
    major: Optional[str] = Body(default=None),
    graduation_year: Optional[int] = Body(default=None),
    certificate_url: Optional[str] = Body(default=None),
    student_id_url: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """提交学历认证申请"""
    service = VerificationBadgeService(db)

    try:
        verification = service.submit_education_verification(
            user_id=current_user.id,
            school_name=school_name,
            degree=degree,
            major=major,
            graduation_year=graduation_year,
            certificate_url=certificate_url,
            student_id_url=student_id_url,
        )
        return {
            "success": True,
            "data": {
                "verification_id": verification.id,
                "status": verification.verification_status,
                "created_at": verification.created_at.isoformat(),
            },
            "message": "认证申请已提交，请等待审核"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/career/submit")
async def submit_career_verification(
    company_name: Optional[str] = Body(default=None),
    position: Optional[str] = Body(default=None),
    industry: Optional[str] = Body(default=None),
    work_email: Optional[str] = Body(default=None),
    work_certificate_url: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """提交职业认证申请"""
    service = VerificationBadgeService(db)

    try:
        verification = service.submit_career_verification(
            user_id=current_user.id,
            company_name=company_name,
            position=position,
            industry=industry,
            work_email=work_email,
            work_certificate_url=work_certificate_url,
        )
        return {
            "success": True,
            "data": {
                "verification_id": verification.id,
                "status": verification.verification_status,
                "created_at": verification.created_at.isoformat(),
            },
            "message": "认证申请已提交，请等待审核"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/education/status")
async def get_education_verification_status(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取学历认证状态"""
    from db.models import EducationVerificationDB

    verification = db.query(EducationVerificationDB).filter(
        EducationVerificationDB.user_id == current_user.id
    ).order_by(EducationVerificationDB.created_at.desc()).first()

    if not verification:
        return {
            "success": True,
            "data": None,
            "message": "暂无认证记录"
        }

    return {
        "success": True,
        "data": {
            "id": verification.id,
            "school_name": verification.school_name,
            "degree": verification.degree,
            "major": verification.major,
            "graduation_year": verification.graduation_year,
            "status": verification.verification_status,
            "verified_at": verification.verified_at.isoformat() if verification.verified_at else None,
        }
    }


@router.get("/career/status")
async def get_career_verification_status(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取职业认证状态"""
    from db.models import CareerVerificationDB

    verification = db.query(CareerVerificationDB).filter(
        CareerVerificationDB.user_id == current_user.id
    ).order_by(CareerVerificationDB.created_at.desc()).first()

    if not verification:
        return {
            "success": True,
            "data": None,
            "message": "暂无认证记录"
        }

    return {
        "success": True,
        "data": {
            "id": verification.id,
            "company_name": verification.company_name,
            "position": verification.position,
            "industry": verification.industry,
            "status": verification.verification_status,
            "verified_at": verification.verified_at.isoformat() if verification.verified_at else None,
        }
    }


@router.post("/education/approve/{verification_id}")
async def approve_education_verification(
    verification_id: str,
    school_type: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """批准学历认证（管理员）"""
    from utils.admin_check import require_admin
    require_admin(current_user)  # 管理员权限检查

    service = VerificationBadgeService(db)

    success = service.approve_education_verification(verification_id, school_type)

    if success:
        return {
            "success": True,
            "message": "学历认证已批准"
        }
    else:
        raise HTTPException(status_code=404, detail="认证记录不存在")


@router.post("/career/approve/{verification_id}")
async def approve_career_verification(
    verification_id: str,
    company_type: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """批准职业认证（管理员）"""
    from utils.admin_check import require_admin
    require_admin(current_user)  # 管理员权限检查

    service = VerificationBadgeService(db)

    success = service.approve_career_verification(verification_id, company_type)

    if success:
        return {
            "success": True,
            "message": "职业认证已批准"
        }
    else:
        raise HTTPException(status_code=404, detail="认证记录不存在")


@router.get("/stats")
async def get_verification_stats(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取认证统计（管理员）"""
    from utils.admin_check import require_admin
    require_admin(current_user)  # 管理员权限检查

    service = VerificationBadgeService(db)

    stats = service.get_verification_stats()

    return {
        "success": True,
        "data": stats
    }


@router.get("/user/{user_id}/badges")
async def get_user_badges_public(
    user_id: str,
    db: Session = Depends(get_db)
):
    """公开接口：获取用户的信任徽章（用于展示）"""
    service = VerificationBadgeService(db)
    badges = service.get_user_badges(user_id)
    trust_score = service.get_trust_score(user_id)

    return {
        "success": True,
        "data": {
            "badges": badges,
            "trust_score": trust_score,
        }
    }