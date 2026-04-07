"""
实名认证服务

P4 新增:
- 身份证 OCR 识别
- 人脸核身
- 认证状态管理
- 认证标识体系
"""
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.models import IdentityVerificationDB, UserDB


class IdentityVerificationService:
    """实名认证服务"""

    # 认证状态
    STATUS_PENDING = "pending"
    STATUS_VERIFIED = "verified"
    STATUS_REJECTED = "rejected"
    STATUS_EXPIRED = "expired"

    # 认证类型
    TYPE_BASIC = "basic"  # 仅身份证
    TYPE_ADVANCED = "advanced"  # 身份证 + 人脸

    # 认证标识
    BADGE_VERIFIED = "verified"
    BADGE_PREMIUM = "premium"
    BADGE_VIP = "vip"

    def __init__(self, db: Session):
        self.db = db
        # 模拟第三方服务配置 (实际应使用阿里云/腾讯云等)
        self.ocr_service_url = "https://api.example.com/ocr"
        self.face_verify_url = "https://api.example.com/face-verify"

    def _hash_id_number(self, id_number: str) -> str:
        """对身份证号进行哈希 (用于去重验证)"""
        return hashlib.sha256(id_number.encode()).hexdigest()

    def submit_verification(
        self,
        user_id: str,
        real_name: str,
        id_number: str,
        verification_type: str = TYPE_BASIC,
        id_front_url: Optional[str] = None,
        id_back_url: Optional[str] = None
    ) -> IdentityVerificationDB:
        """
        提交实名认证申请

        Args:
            user_id: 用户 ID
            real_name: 真实姓名
            id_number: 身份证号
            verification_type: 认证类型
            id_front_url: 身份证正面照片 URL
            id_back_url: 身份证反面照片 URL

        Returns:
            IdentityVerificationDB: 认证记录
        """
        # 检查用户是否已提交过认证
        existing = self.get_verification_by_user(user_id)
        if existing and existing.verification_status == self.STATUS_VERIFIED:
            raise ValueError("用户已完成实名认证")

        # 检查身份证号是否已被使用 (防止重复注册)
        id_hash = self._hash_id_number(id_number)
        duplicate = self.db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.id_number_hash == id_hash
        ).first()
        if duplicate:
            raise ValueError("该身份证号已被使用")

        # 创建认证记录
        verification = IdentityVerificationDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            real_name=real_name,
            id_number=id_number,  # 生产环境应加密存储
            id_number_hash=id_hash,
            verification_status=self.STATUS_PENDING,
            verification_type=verification_type,
            id_front_url=id_front_url,
            id_back_url=id_back_url
        )

        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)

        return verification

    def submit_ocr_result(
        self,
        verification_id: str,
        ocr_data: Dict[str, Any]
    ) -> IdentityVerificationDB:
        """
        提交 OCR 识别结果

        Args:
            verification_id: 认证记录 ID
            ocr_data: OCR 识别结果

        Returns:
            IdentityVerificationDB: 更新后的认证记录
        """
        verification = self.get_verification(verification_id)
        if not verification:
            raise ValueError("认证记录不存在")

        verification.ocr_data = json.dumps(ocr_data)
        self.db.commit()
        self.db.refresh(verification)

        return verification

    def submit_face_verification(
        self,
        verification_id: str,
        face_verify_url: str,
        similarity_score: float
    ) -> IdentityVerificationDB:
        """
        提交人脸核身结果

        Args:
            verification_id: 认证记录 ID
            face_verify_url: 人脸核身照片 URL
            similarity_score: 人脸相似度 (0-1)

        Returns:
            IdentityVerificationDB: 更新后的认证记录
        """
        verification = self.get_verification(verification_id)
        if not verification:
            raise ValueError("认证记录不存在")

        verification.face_verify_url = face_verify_url
        verification.face_similarity_score = similarity_score
        self.db.commit()
        self.db.refresh(verification)

        return verification

    def approve_verification(
        self,
        verification_id: str,
        badge: Optional[str] = None,
        valid_days: int = 365
    ) -> IdentityVerificationDB:
        """
        批准认证申请

        Args:
            verification_id: 认证记录 ID
            badge: 认证标识
            valid_days: 有效期 (天)

        Returns:
            IdentityVerificationDB: 更新后的认证记录
        """
        verification = self.get_verification(verification_id)
        if not verification:
            raise ValueError("认证记录不存在")

        verification.verification_status = self.STATUS_VERIFIED
        verification.verified_at = datetime.utcnow()
        verification.expires_at = datetime.utcnow() + timedelta(days=valid_days)
        verification.verification_badge = badge or self.BADGE_VERIFIED

        # 更新用户表中的认证状态
        user = self.db.query(UserDB).filter(UserDB.id == verification.user_id).first()
        if user:
            user.name = verification.real_name  # 更新真实姓名

        self.db.commit()
        self.db.refresh(verification)

        return verification

    def reject_verification(
        self,
        verification_id: str,
        reason: str
    ) -> IdentityVerificationDB:
        """
        拒绝认证申请

        Args:
            verification_id: 认证记录 ID
            reason: 拒绝原因

        Returns:
            IdentityVerificationDB: 更新后的认证记录
        """
        verification = self.get_verification(verification_id)
        if not verification:
            raise ValueError("认证记录不存在")

        verification.verification_status = self.STATUS_REJECTED
        verification.rejection_reason = reason

        self.db.commit()
        self.db.refresh(verification)

        return verification

    def get_verification(self, verification_id: str) -> Optional[IdentityVerificationDB]:
        """获取认证记录"""
        return self.db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.id == verification_id
        ).first()

    def get_verification_by_user(self, user_id: str) -> Optional[IdentityVerificationDB]:
        """获取用户的认证记录"""
        return self.db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.user_id == user_id
        ).order_by(IdentityVerificationDB.created_at.desc()).first()

    def get_verification_status(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户认证状态

        Args:
            user_id: 用户 ID

        Returns:
            Dict: 认证状态信息
        """
        verification = self.get_verification_by_user(user_id)

        if not verification:
            return {
                "is_verified": False,
                "status": "not_submitted",
                "message": "未提交认证申请"
            }

        result = {
            "is_verified": verification.verification_status == self.STATUS_VERIFIED,
            "status": verification.verification_status,
            "verification_type": verification.verification_type,
            "badge": verification.verification_badge,
            "verified_at": verification.verified_at.isoformat() if verification.verified_at else None,
            "expires_at": verification.expires_at.isoformat() if verification.expires_at else None
        }

        if verification.verification_status == self.STATUS_REJECTED:
            result["rejection_reason"] = verification.rejection_reason

        return result

    def is_verified(self, user_id: str) -> bool:
        """检查用户是否已认证"""
        verification = self.get_verification_by_user(user_id)
        if not verification:
            return False

        # 检查是否过期
        if verification.expires_at and verification.expires_at < datetime.utcnow():
            verification.verification_status = self.STATUS_EXPIRED
            self.db.commit()
            return False

        return verification.verification_status == self.STATUS_VERIFIED

    def get_verified_users(self, limit: int = 100) -> List[UserDB]:
        """获取已认证用户列表"""
        verified_user_ids = self.db.query(IdentityVerificationDB.user_id).filter(
            IdentityVerificationDB.verification_status == self.STATUS_VERIFIED
        ).limit(limit).all()

        user_ids = [uid[0] for uid in verified_user_ids]
        return self.db.query(UserDB).filter(UserDB.id.in_(user_ids)).all()

    def get_verification_stats(self) -> Dict[str, int]:
        """获取认证统计信息"""
        total = self.db.query(IdentityVerificationDB).count()
        pending = self.db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.verification_status == self.STATUS_PENDING
        ).count()
        verified = self.db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.verification_status == self.STATUS_VERIFIED
        ).count()
        rejected = self.db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.verification_status == self.STATUS_REJECTED
        ).count()

        return {
            "total": total,
            "pending": pending,
            "verified": verified,
            "rejected": rejected
        }

    def simulate_ocr_scan(self, id_front_url: str, id_back_url: str) -> Dict[str, Any]:
        """
        模拟 OCR 扫描 (实际应调用第三方服务)

        Args:
            id_front_url: 身份证正面照片 URL
            id_back_url: 身份证反面照片 URL

        Returns:
            Dict: OCR 识别结果
        """
        # 这里模拟第三方 OCR 服务的返回结果
        # 实际应调用阿里云/腾讯云等 OCR API
        return {
            "name": "张三",
            "id_number": "110101199001011234",
            "gender": "男",
            "ethnicity": "汉",
            "birth": "1990 年 1 月 1 日",
            "address": "北京市东城区某某街道",
            "issuing_authority": "北京市公安局东城分局",
            "valid_period": "2010.01.01-2030.01.01"
        }

    def simulate_face_compare(
        self,
        id_photo_url: str,
        face_photo_url: str
    ) -> Dict[str, Any]:
        """
        模拟人脸比对 (实际应调用第三方服务)

        Args:
            id_photo_url: 身份证照片 URL
            face_photo_url: 人脸核身照片 URL

        Returns:
            Dict: 人脸比对结果
        """
        # 这里模拟第三方人脸比对服务的返回结果
        # 实际应调用阿里云/腾讯云等人脸比对 API
        import random
        similarity = random.uniform(0.85, 0.99)

        return {
            "similarity": similarity,
            "is_match": similarity > 0.80,
            "face_quality": random.uniform(0.7, 1.0),
            "liveness_detected": True
        }
