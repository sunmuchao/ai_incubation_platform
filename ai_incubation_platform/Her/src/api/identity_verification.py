"""
多源身份核验 API

# FUTURE: Identity 身份验证增强，暂不启用 - 前端未集成

Identity 功能接口：
- 提交各类身份验证申请
- 查询验证状态
- 获取信任勋章
- 查看信任分
"""
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from utils.logger import logger
from auth.jwt import get_current_user
from db.database import get_db, SessionLocal
from services.identity_verification_service import IdentityVerificationService

router = APIRouter(prefix="/api/identity", tags=["identity-verification"])


# ============= 请求/响应模型 =============

class EducationVerificationRequest(BaseModel):
    """学历认证请求"""
    school_name: str = Field(..., description="学校名称")
    degree_type: str = Field(..., description="学历类型：associate/bachelor/master/doctor")
    major: str = Field(default="", description="专业")
    graduation_year: int = Field(..., description="毕业年份")
    chsi_verification_id: Optional[str] = Field(default=None, description="学信网验证码")


class OccupationVerificationRequest(BaseModel):
    """职业认证请求"""
    company_name: str = Field(..., description="公司名称")
    position: str = Field(..., description="职位")
    work_years: int = Field(default=0, description="工作年限")
    work_email: Optional[str] = Field(default=None, description="工作邮箱")
    verification_method: str = Field(default="email", description="验证方式：email/certificate/social_security")


class TrustScoreResponse(BaseModel):
    """信任分响应"""
    success: bool
    data: Dict
    message: Optional[str] = None


class TrustBadgesResponse(BaseModel):
    """信任勋章响应"""
    success: bool
    data: List[Dict]
    total: int


class VerificationResponse(BaseModel):
    """验证响应"""
    success: bool
    message: str
    data: Optional[Dict] = None


# ============= 辅助函数 =============

def get_identity_service(db: Session = Depends(get_db)) -> IdentityVerificationService:
    """获取身份验证服务实例（依赖注入）"""
    return IdentityVerificationService(db)


# ============= API 端点 =============

@router.get("/trust-score", response_model=TrustScoreResponse)
async def get_trust_score(
    current_user: str = Depends(get_current_user)
):
    """
    获取我的信任分

    信任分基于多源身份认证情况计算，范围 0-100
    """
    user_id = current_user
    service = get_identity_service()

    try:
        score_info = service.get_trust_score(user_id)
        return TrustScoreResponse(
            success=True,
            data=score_info,
            message=f"当前信任分为{score_info['trust_score']}，等级为{score_info['trust_level']}"
        )
    except Exception as e:
        logger.error(f"Failed to get trust score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trust-badges", response_model=TrustBadgesResponse)
async def get_trust_badges(
    current_user: str = Depends(get_current_user)
):
    """
    获取我的信任勋章

    返回用户已获得的所有活跃信任勋章
    """
    user_id = current_user
    service = get_identity_service()

    try:
        badges = service.get_user_trust_badges(user_id)
        return TrustBadgesResponse(
            success=True,
            data=badges,
            total=len(badges)
        )
    except Exception as e:
        logger.error(f"Failed to get trust badges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/education/submit", response_model=VerificationResponse)
async def submit_education_verification(
    request: EducationVerificationRequest,
    current_user: str = Depends(get_current_user)
):
    """
    提交学历认证申请

    需要提供的信息：
    - 学校名称
    - 学历类型（专科/本科/硕士/博士）
    - 专业
    - 毕业年份
    - 学信网验证码（可选）
    """
    user_id = current_user
    service = get_identity_service()

    try:
        success, message, credential_id = service.submit_education_verification(
            user_id=user_id,
            school_name=request.school_name,
            degree_type=request.degree_type,
            major=request.major,
            graduation_year=request.graduation_year,
            chsi_verification_id=request.chsi_verification_id
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return VerificationResponse(
            success=True,
            message=message,
            data={"credential_id": credential_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit education verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/occupation/submit", response_model=VerificationResponse)
async def submit_occupation_verification(
    request: OccupationVerificationRequest,
    current_user: str = Depends(get_current_user)
):
    """
    提交职业认证申请

    需要提供的信息：
    - 公司名称
    - 职位
    - 工作年限
    - 工作邮箱（可选）
    - 验证方式（企业邮箱/在职证明/社保记录）
    """
    user_id = current_user
    service = get_identity_service()

    try:
        success, message, credential_id = service.submit_occupation_verification(
            user_id=user_id,
            company_name=request.company_name,
            position=request.position,
            work_years=request.work_years,
            work_email=request.work_email,
            verification_method=request.verification_method
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return VerificationResponse(
            success=True,
            message=message,
            data={"credential_id": credential_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit occupation verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verifications")
async def get_user_verifications(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    获取我的验证记录

    返回所有类型的身份验证记录
    """
    user_id = current_user

    try:
        from db.models import IdentityVerificationDB
        from models.identity_models import EducationCredentialDB, OccupationCredentialDB

        verifications = []

        # 获取基础实名认证记录
        basic_verifications = db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.user_id == user_id
        ).order_by(IdentityVerificationDB.created_at.desc()).all()

        for v in basic_verifications:
            verifications.append({
                "type": "identity",
                "verification_type": v.verification_type if hasattr(v, 'verification_type') else "real_name",
                "status": v.verification_status,
                "created_at": v.created_at.isoformat() if v.created_at else None
            })

        # 获取学历认证记录
        education_verifications = db.query(EducationCredentialDB).filter(
            EducationCredentialDB.user_id == user_id
        ).order_by(EducationCredentialDB.created_at.desc()).all()

        for v in education_verifications:
            verifications.append({
                "type": "education",
                "verification_type": "education",
                "status": v.verification_status,
                "school_name": v.school_name,
                "degree_type": v.degree_type,
                "created_at": v.created_at.isoformat() if v.created_at else None
            })

        # 获取职业认证记录
        occupation_verifications = db.query(OccupationCredentialDB).filter(
            OccupationCredentialDB.user_id == user_id
        ).order_by(OccupationCredentialDB.created_at.desc()).all()

        for v in occupation_verifications:
            verifications.append({
                "type": "occupation",
                "verification_type": "occupation",
                "status": v.verification_status,
                "company_name": v.company_name,
                "position": v.position,
                "created_at": v.created_at.isoformat() if v.created_at else None
            })

        return {
            "success": True,
            "data": verifications,
            "total": len(verifications)
        }

    except Exception as e:
        logger.error(f"Failed to get verifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_verification_types():
    """
    获取所有可用的验证类型说明
    """
    return {
        "success": True,
        "data": {
            "real_name": {
                "name": "实名认证",
                "icon": "🆔",
                "score_weight": 20,
                "required": True,
                "description": "通过身份证实名认证"
            },
            "education": {
                "name": "学历认证",
                "icon": "🎓",
                "score_weight": 20,
                "required": False,
                "description": "通过学信网或学历证书认证"
            },
            "occupation": {
                "name": "职业认证",
                "icon": "💼",
                "score_weight": 15,
                "required": False,
                "description": "通过企业邮箱或在职证明认证"
            },
            "income": {
                "name": "收入认证",
                "icon": "💰",
                "score_weight": 15,
                "required": False,
                "description": "通过纳税记录或银行流水认证"
            },
            "property": {
                "name": "房产认证",
                "icon": "🏠",
                "score_weight": 15,
                "required": False,
                "description": "通过房产证认证"
            },
            "criminal_record": {
                "name": "无犯罪记录",
                "icon": "🛡️",
                "score_weight": 15,
                "required": False,
                "description": "通过公安 API 认证"
            }
        }
    }


@router.post("/income/submit", response_model=VerificationResponse)
async def submit_income_verification(
    income_range: str = Body(..., description="收入范围"),
    income_type: str = Body(default="salary", description="收入类型"),
    verification_method: str = Body(default="tax_record", description="验证方式"),
    bank_name: Optional[str] = Body(None, description="银行名称"),
    current_user: str = Depends(get_current_user)
):
    """
    提交收入认证申请

    需要提供的信息：
    - 收入范围 (<5k/5k-10k/10k-20k/20k-30k/30k-50k/>100k)
    - 收入类型 (salary/bonus/investment/business/other)
    - 验证方式 (tax_record/bank_statement/social_security)
    """
    user_id = current_user
    service = get_identity_service()

    try:
        success, message, credential_id = service.submit_income_verification(
            user_id=user_id,
            income_range=income_range,
            income_type=income_type,
            verification_method=verification_method,
            bank_name=bank_name,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return VerificationResponse(
            success=True,
            message=message,
            data={"credential_id": credential_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit income verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/property/submit", response_model=VerificationResponse)
async def submit_property_verification(
    property_location: str = Body(..., description="房产位置"),
    property_type: str = Body(default="apartment", description="房产类型"),
    property_area: Optional[float] = Body(None, description="面积（平方米）"),
    property_value: Optional[float] = Body(None, description="估值（万元）"),
    ownership_type: str = Body(default="sole", description="产权类型"),
    current_user: str = Depends(get_current_user)
):
    """
    提交房产认证申请

    需要提供的信息：
    - 房产位置
    - 房产类型 (apartment/villa/commercial/land)
    - 面积（平方米）
    - 估值（万元）
    - 产权类型 (sole/joint/family)
    """
    user_id = current_user
    service = get_identity_service()

    try:
        success, message, credential_id = service.submit_property_verification(
            user_id=user_id,
            property_location=property_location,
            property_type=property_type,
            property_area=property_area,
            property_value=property_value,
            ownership_type=ownership_type,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return VerificationResponse(
            success=True,
            message=message,
            data={"credential_id": credential_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit property verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/criminal-record/submit", response_model=VerificationResponse)
async def submit_criminal_record_verification(
    verification_method: str = Body(default="police_api", description="验证方式"),
    current_user: str = Depends(get_current_user)
):
    """
    提交无犯罪记录认证申请

    通过公安 API 或无犯罪记录证明书进行认证。
    """
    user_id = current_user
    service = get_identity_service()

    try:
        success, message, credential_id = service.submit_criminal_record_verification(
            user_id=user_id,
            verification_method=verification_method,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return VerificationResponse(
            success=True,
            message=message,
            data={"credential_id": credential_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit criminal record verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/external-api/call")
async def call_external_verification_api(
    api_name: str = Body(..., description="API 名称"),
    params: Dict[str, Any] = Body(..., description="API 参数"),
    current_user: str = Depends(get_current_user)
):
    """
    调用外部验证 API

    支持的 API：
    - chsi: 学信网 API
    - enterprise_email: 企业邮箱验证
    - tax_bureau: 税务局 API
    - property_registry: 房产登记 API
    - police_record: 公安无犯罪记录 API
    """
    service = get_identity_service()

    try:
        success, result, error = service.call_external_verification_api(api_name, params)

        if not success:
            raise HTTPException(status_code=400, detail=error)

        return {
            "success": True,
            "data": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to call external API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/education/{credential_id}/approve")
async def approve_education_verification(
    credential_id: str,
    level: str = Query(..., description="学历等级"),
    level_value: int = Query(..., description="学历等级数值"),
    current_user: str = Depends(get_current_user)
):
    """
    批准学历认证（管理员功能）
    """
    service = get_identity_service()

    try:
        success, message = service.approve_education_verification(credential_id, level, level_value)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve education verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/income/{credential_id}/approve")
async def approve_income_verification(
    credential_id: str,
    level_value: int = Query(..., description="收入等级数值"),
    current_user: str = Depends(get_current_user)
):
    """
    批准收入认证（管理员功能）
    """
    service = get_identity_service()

    try:
        success, message = service.approve_income_verification(credential_id, level_value)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve income verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/property/{credential_id}/approve")
async def approve_property_verification(
    credential_id: str,
    level_value: int = Query(..., description="房产等级数值"),
    current_user: str = Depends(get_current_user)
):
    """
    批准房产认证（管理员功能）
    """
    service = get_identity_service()

    try:
        success, message = service.approve_property_verification(credential_id, level_value)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve property verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trust-levels")
async def get_trust_levels():
    """
    获取信任等级说明
    """
    return {
        "success": True,
        "data": {
            "diamond": {
                "name": "钻石",
                "min_score": 90,
                "description": "极高信任度，全方位优先推荐"
            },
            "platinum": {
                "name": "铂金",
                "min_score": 80,
                "description": "高度可信，优先匹配权"
            },
            "gold": {
                "name": "黄金",
                "min_score": 60,
                "description": "普通可信用户"
            },
            "silver": {
                "name": "白银",
                "min_score": 40,
                "description": "基础可信用户"
            },
            "bronze": {
                "name": "青铜",
                "min_score": 0,
                "description": "新用户或信息不完善"
            }
        }
    }
