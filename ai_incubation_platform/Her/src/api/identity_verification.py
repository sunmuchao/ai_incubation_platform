"""
实名认证 API

P4 新增:
- 身份证 OCR 识别
- 人脸核身
- 认证状态管理
- 认证标识体系
"""
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.identity_verification_service import IdentityVerificationService


router = APIRouter(prefix="/api/auth", tags=["实名认证"])


# ============= Pydantic 模型 =============

class VerificationSubmitRequest(BaseModel):
    """提交实名认证请求"""
    real_name: str = Field(..., description="真实姓名")
    id_number: str = Field(..., description="身份证号")
    verification_type: str = Field(default="basic", description="认证类型：basic/advanced")
    id_front_url: Optional[str] = Field(default=None, description="身份证正面照片 URL")
    id_back_url: Optional[str] = Field(default=None, description="身份证反面照片 URL")


class VerificationResponse(BaseModel):
    """实名认证响应"""
    id: str
    user_id: str
    real_name: str
    verification_status: str
    verification_type: str
    verification_badge: Optional[str] = None
    verified_at: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class VerificationStatusResponse(BaseModel):
    """认证状态响应"""
    is_verified: bool
    status: str
    message: Optional[str] = None
    verification_type: Optional[str] = None
    badge: Optional[str] = None
    verified_at: Optional[str] = None
    expires_at: Optional[str] = None
    rejection_reason: Optional[str] = None


class OCRSubmitRequest(BaseModel):
    """提交 OCR 结果请求"""
    ocr_data: Dict[str, Any] = Field(..., description="OCR 识别结果")


class FaceVerifyRequest(BaseModel):
    """提交人脸核身请求"""
    face_verify_url: str = Field(..., description="人脸核身照片 URL")
    similarity_score: float = Field(..., description="人脸相似度 (0-1)")


class ModerateVerificationRequest(BaseModel):
    """审核认证请求"""
    status: str = Field(..., description="审核状态：approved/rejected")
    reason: Optional[str] = Field(default=None, description="拒绝原因")
    badge: Optional[str] = Field(default=None, description="认证标识")


# ============= API 端点 =============

@router.post("/verify-identity", response_model=VerificationResponse, summary="提交实名认证申请")
async def submit_verification(
    request: VerificationSubmitRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    提交实名认证申请

    - **real_name**: 真实姓名
    - **id_number**: 身份证号
    - **verification_type**: 认证类型 (basic/advanced)
    - **id_front_url**: 身份证正面照片 URL
    - **id_back_url**: 身份证反面照片 URL
    """
    service = IdentityVerificationService(db)

    try:
        verification = service.submit_verification(
            user_id=current_user.id,
            real_name=request.real_name,
            id_number=request.id_number,
            verification_type=request.verification_type,
            id_front_url=request.id_front_url,
            id_back_url=request.id_back_url
        )
        return verification
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/verify-status", response_model=VerificationStatusResponse, summary="获取认证状态")
async def get_verification_status(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取当前用户的实名认证状态"""
    service = IdentityVerificationService(db)
    status = service.get_verification_status(current_user.id)
    return status


@router.post("/verify-ocr", summary="提交 OCR 识别结果")
async def submit_ocr_result(
    request: OCRSubmitRequest,
    verification_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    提交 OCR 识别结果

    - **verification_id**: 认证记录 ID
    - **ocr_data**: OCR 识别结果
    """
    service = IdentityVerificationService(db)

    try:
        verification = service.submit_ocr_result(
            verification_id=verification_id,
            ocr_data=request.ocr_data
        )
        return {"message": "OCR 结果已提交", "verification_id": verification.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify-face", summary="提交人脸核身结果")
async def submit_face_verification(
    request: FaceVerifyRequest,
    verification_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    提交人脸核身结果

    - **verification_id**: 认证记录 ID
    - **face_verify_url**: 人脸核身照片 URL
    - **similarity_score**: 人脸相似度
    """
    service = IdentityVerificationService(db)

    try:
        verification = service.submit_face_verification(
            verification_id=verification_id,
            face_verify_url=request.face_verify_url,
            similarity_score=request.similarity_score
        )
        return {"message": "人脸核身结果已提交", "verification_id": verification.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify-approve/{verification_id}", response_model=VerificationResponse, summary="批准认证申请")
async def approve_verification(
    verification_id: str,
    request: ModerateVerificationRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    批准认证申请 (仅管理员可用)

    - **status**: 审核状态 (approved/rejected)
    - **reason**: 拒绝原因
    - **badge**: 认证标识
    """
    service = IdentityVerificationService(db)

    try:
        if request.status == "approved":
            verification = service.approve_verification(
                verification_id=verification_id,
                badge=request.badge
            )
        else:
            verification = service.reject_verification(
                verification_id=verification_id,
                reason=request.reason
            )
        return verification
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify-reject/{verification_id}", response_model=VerificationResponse, summary="拒绝认证申请")
async def reject_verification(
    verification_id: str,
    reason: str = Form(..., description="拒绝原因"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    拒绝认证申请 (仅管理员可用)

    - **verification_id**: 认证记录 ID
    - **reason**: 拒绝原因
    """
    service = IdentityVerificationService(db)

    try:
        verification = service.reject_verification(
            verification_id=verification_id,
            reason=reason
        )
        return verification
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/verify-check/{user_id}", summary="检查用户认证状态")
async def check_user_verification(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """检查指定用户的认证状态"""
    service = IdentityVerificationService(db)
    is_verified = service.is_verified(user_id)
    return {"user_id": user_id, "is_verified": is_verified}


@router.post("/simulate-ocr", summary="模拟 OCR 扫描")
async def simulate_ocr(
    id_front_url: str = Form(...),
    id_back_url: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    模拟 OCR 扫描 (开发/测试用)

    实际生产环境应调用阿里云/腾讯云等第三方 OCR 服务
    """
    service = IdentityVerificationService(db)
    ocr_result = service.simulate_ocr_scan(id_front_url, id_back_url)
    return ocr_result


@router.post("/simulate-face-compare", summary="模拟人脸比对")
async def simulate_face_compare(
    id_photo_url: str = Form(...),
    face_photo_url: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    模拟人脸比对 (开发/测试用)

    实际生产环境应调用阿里云/腾讯云等第三方人脸比对服务
    """
    service = IdentityVerificationService(db)
    result = service.simulate_face_compare(id_photo_url, face_photo_url)
    return result


@router.get("/stats", summary="获取认证统计信息")
async def get_verification_stats(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取实名认证统计信息 (仅管理员可用)"""
    service = IdentityVerificationService(db)
    stats = service.get_verification_stats()
    return stats


@router.get("/list/verified", summary="获取已认证用户列表")
async def get_verified_users(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取已认证用户列表"""
    service = IdentityVerificationService(db)
    users = service.get_verified_users(limit=limit)

    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url
        }
        for user in users
    ]
