"""
人脸认证服务

参考 Tinder Blue Star 认证徽章：
- 人脸照片与身份证照片比对
- 活体检测（眨眼、张嘴等动作）
- 认证徽章发放
- 认证状态管理
"""
import uuid
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from models.face_verification import (
    FaceVerificationStatus,
    FaceVerificationMethod,
    VerificationBadgeType,
    FaceVerificationRequest,
    FaceVerificationResponse,
    UserVerificationStatus,
    VERIFICATION_BADGE_CONFIG,
    FaceVerificationDB,
    VerificationBadgeDB,
)
from utils.logger import logger
from db.models import IdentityVerificationDB
from services.base_service import BaseService


class FaceVerificationService(BaseService):
    """人脸认证服务"""

    # 认证阈值配置
    SIMILARITY_THRESHOLD = 80.0  # 相似度阈值（百分比）
    LIVENESS_THRESHOLD = 85.0  # 活体检测阈值（百分比）
    MAX_RETRY_COUNT = 3  # 最大重试次数

    def __init__(self, db: Session):
        super().__init__(db)

    def get_user_verification_status(self, user_id: str) -> UserVerificationStatus:
        """获取用户认证状态汇总"""
        # 获取人脸认证状态
        face_verification = self.db.query(FaceVerificationDB).filter(
            FaceVerificationDB.user_id == user_id
        ).first()

        face_verified = face_verification and face_verification.status == FaceVerificationStatus.VERIFIED.value

        # 获取身份认证状态
        id_verification = self.db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.user_id == user_id,
            IdentityVerificationDB.verification_status == "verified"
        ).first()

        id_verified = id_verification is not None

        # 获取学历认证状态（如果有）
        education_verified = False
        try:
            from models.identity_models import EducationCredentialDB
            education = self.db.query(EducationCredentialDB).filter(
                EducationCredentialDB.user_id == user_id,
                EducationCredentialDB.verification_status == "verified"
            ).first()
            education_verified = education is not None
        except Exception:
            pass

        # 获取职业认证状态（如果有）
        occupation_verified = False
        try:
            from models.identity_models import OccupationCredentialDB
            occupation = self.db.query(OccupationCredentialDB).filter(
                OccupationCredentialDB.user_id == user_id,
                OccupationCredentialDB.verification_status == "verified"
            ).first()
            occupation_verified = occupation is not None
        except Exception:
            pass

        # 获取当前徽章
        badge = self._get_current_badge(user_id)

        # 计算信任分
        trust_score = self._calculate_trust_score(
            face_verified, id_verified, education_verified, occupation_verified
        )

        return UserVerificationStatus(
            user_id=user_id,
            face_verified=face_verified,
            face_verification_id=face_verification.id if face_verification else None,
            face_verification_date=face_verification.completed_at if face_verification else None,
            id_verified=id_verified,
            id_verification_id=id_verification.id if id_verification else None,
            education_verified=education_verified,
            occupation_verified=occupation_verified,
            current_badge=badge.badge_type if badge else None,
            badge_display_name=badge.display_name if badge else None,
            badge_display_icon=badge.display_icon if badge else None,
            badge_display_color=badge.display_color if badge else None,
            trust_score=trust_score,
        )

    def _get_current_badge(self, user_id: str) -> Optional[VerificationBadgeDB]:
        """获取用户当前徽章"""
        return self.db.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.user_id == user_id,
            VerificationBadgeDB.status == "active"
        ).first()

    def _calculate_trust_score(
        self,
        face_verified: bool,
        id_verified: bool,
        education_verified: bool,
        occupation_verified: bool
    ) -> int:
        """计算信任分"""
        score = 0
        if face_verified:
            score += 20
        if id_verified:
            score += 20
        if education_verified:
            score += 15
        if occupation_verified:
            score += 15
        return min(score, 100)

    def _determine_badge_type(
        self,
        face_verified: bool,
        id_verified: bool,
        education_verified: bool,
        occupation_verified: bool
    ) -> Optional[VerificationBadgeType]:
        """根据认证状态确定徽章类型"""
        if face_verified and id_verified and education_verified and occupation_verified:
            return VerificationBadgeType.DIAMOND_STAR
        elif face_verified and id_verified and education_verified:
            return VerificationBadgeType.PLATINUM_STAR
        elif face_verified and id_verified:
            return VerificationBadgeType.GOLD_STAR
        elif face_verified:
            return VerificationBadgeType.BLUE_STAR
        return None

    def start_verification(
        self,
        user_id: str,
        method: FaceVerificationMethod
    ) -> FaceVerificationResponse:
        """开始人脸认证"""
        # 检查是否已有认证记录
        existing = self.db.query(FaceVerificationDB).filter(
            FaceVerificationDB.user_id == user_id
        ).first()

        if existing and existing.status == FaceVerificationStatus.VERIFIED.value:
            return FaceVerificationResponse(
                success=False,
                message="您已完成人脸认证",
                verification_id=existing.id,
                status=FaceVerificationStatus.VERIFIED,
            )

        if existing and existing.retry_count >= self.MAX_RETRY_COUNT:
            return FaceVerificationResponse(
                success=False,
                message=f"认证失败次数已达上限（{self.MAX_RETRY_COUNT}次），请联系客服",
                verification_id=existing.id,
                status=FaceVerificationStatus(existing.status),
            )

        # 创建或更新认证记录
        verification_id = str(uuid.uuid4())
        if existing:
            existing.method = method.value
            existing.status = FaceVerificationStatus.IN_PROGRESS.value
            existing.updated_at = datetime.now()
            self.db.commit()
            verification_id = existing.id
        else:
            verification = FaceVerificationDB(
                id=verification_id,
                user_id=user_id,
                method=method.value,
                status=FaceVerificationStatus.IN_PROGRESS.value,
            )
            self.db.add(verification)
            self.db.commit()

        logger.info(f"Face verification started: user={user_id}, method={method}")

        return FaceVerificationResponse(
            success=True,
            message="认证流程已开始，请按要求提交照片",
            verification_id=verification_id,
            status=FaceVerificationStatus.IN_PROGRESS,
        )

    def submit_verification(
        self,
        user_id: str,
        request: FaceVerificationRequest
    ) -> FaceVerificationResponse:
        """提交人脸认证"""
        # 获取认证记录
        verification = self.db.query(FaceVerificationDB).filter(
            FaceVerificationDB.user_id == user_id
        ).first()

        if not verification:
            return FaceVerificationResponse(
                success=False,
                message="请先开始认证流程",
                status=FaceVerificationStatus.NOT_STARTED,
            )

        if verification.status == FaceVerificationStatus.VERIFIED.value:
            return FaceVerificationResponse(
                success=False,
                message="已完成认证",
                status=FaceVerificationStatus.VERIFIED,
            )

        # 保存照片哈希
        photo_hash = hashlib.sha256(request.photo_base64.encode()).hexdigest()
        verification.photo_hash = photo_hash
        verification.submitted_at = datetime.now()
        verification.status = FaceVerificationStatus.SUBMITTED.value

        # 模拟人脸比对（实际应调用阿里云/腾讯云人脸核身 API）
        similarity_score, liveness_score = self._mock_face_verification(request)

        verification.similarity_score = similarity_score
        verification.liveness_score = liveness_score

        # 判断认证是否通过
        is_passed = (
            similarity_score >= self.SIMILARITY_THRESHOLD and
            liveness_score >= self.LIVENESS_THRESHOLD
        )

        if is_passed:
            verification.is_passed = True
            verification.status = FaceVerificationStatus.VERIFIED.value
            verification.completed_at = datetime.now()

            # 发放认证徽章
            badge_type = self._issue_verification_badge(user_id, verification.id)

            self.db.commit()

            logger.info(f"Face verification passed: user={user_id}, similarity={similarity_score}, liveness={liveness_score}")

            return FaceVerificationResponse(
                success=True,
                message="人脸认证成功！您已获得认证徽章",
                verification_id=verification.id,
                status=FaceVerificationStatus.VERIFIED,
                similarity_score=similarity_score,
                liveness_score=liveness_score,
                badge_type=badge_type,
            )
        else:
            verification.is_passed = False
            verification.status = FaceVerificationStatus.FAILED.value
            verification.failure_reason = self._get_failure_reason(similarity_score, liveness_score)
            verification.retry_count += 1
            verification.updated_at = datetime.now()

            self.db.commit()

            logger.warning(f"Face verification failed: user={user_id}, similarity={similarity_score}, liveness={liveness_score}")

            return FaceVerificationResponse(
                success=False,
                message=verification.failure_reason,
                verification_id=verification.id,
                status=FaceVerificationStatus.FAILED,
                similarity_score=similarity_score,
                liveness_score=liveness_score,
            )

    def _mock_face_verification(
        self,
        request: FaceVerificationRequest
    ) -> Tuple[float, float]:
        """模拟人脸验证（实际应调用第三方 API）"""
        # 模拟结果：随机生成相似度和活体分数
        # 实际实现应调用：
        # - 阿里云：人脸核身 API（https://help.aliyun.com/product/face-verification.html）
        # - 腾讯云：人脸核身 API（https://cloud.tencent.com/product/fv）

        import random
        # 模拟 85% 成功率
        if random.random() > 0.15:
            similarity_score = random.uniform(85, 99)
            liveness_score = random.uniform(90, 99)
        else:
            similarity_score = random.uniform(50, 75)
            liveness_score = random.uniform(40, 80)

        return similarity_score, liveness_score

    def _get_failure_reason(self, similarity: float, liveness: float) -> str:
        """获取失败原因"""
        reasons = []
        if similarity < self.SIMILARITY_THRESHOLD:
            reasons.append(f"人脸相似度不足（{similarity:.1f}%，需≥{self.SIMILARITY_THRESHOLD}%）")
        if liveness < self.LIVENESS_THRESHOLD:
            reasons.append(f"活体检测未通过（{liveness:.1f}%，需≥{self.LIVENESS_THRESHOLD}%）")

        if not reasons:
            return "认证失败，请重试"
        return "；".join(reasons)

    def _issue_verification_badge(
        self,
        user_id: str,
        verification_id: str
    ) -> VerificationBadgeType:
        """发放认证徽章"""
        # 获取用户完整认证状态
        status = self.get_user_verification_status(user_id)

        # 确定徽章类型
        badge_type = self._determine_badge_type(
            True,  # 刚完成人脸认证
            status.id_verified,
            status.education_verified,
            status.occupation_verified
        )

        if not badge_type:
            badge_type = VerificationBadgeType.BLUE_STAR

        # 获取徽章配置
        badge_config = VERIFICATION_BADGE_CONFIG[badge_type]

        # 创建徽章记录
        badge_id = str(uuid.uuid4())
        badge = VerificationBadgeDB(
            id=badge_id,
            user_id=user_id,
            badge_type=badge_type.value,
            status="active",
            face_verification_id=verification_id,
            display_name=badge_config["name"],
            display_icon=badge_config["icon"],
            display_color=badge_config["color"],
            expires_at=datetime.now() + timedelta(days=365),  # 一年有效期
        )
        self.db.add(badge)

        logger.info(f"Verification badge issued: user={user_id}, badge={badge_type}")

        return badge_type

    def retry_verification(self, user_id: str) -> FaceVerificationResponse:
        """重试人脸认证"""
        verification = self.db.query(FaceVerificationDB).filter(
            FaceVerificationDB.user_id == user_id
        ).first()

        if not verification:
            return FaceVerificationResponse(
                success=False,
                message="未找到认证记录",
                status=FaceVerificationStatus.NOT_STARTED,
            )

        if verification.retry_count >= self.MAX_RETRY_COUNT:
            return FaceVerificationResponse(
                success=False,
                message=f"认证失败次数已达上限（{self.MAX_RETRY_COUNT}次）",
                status=FaceVerificationStatus.FAILED,
            )

        # 重置状态为进行中
        verification.status = FaceVerificationStatus.IN_PROGRESS.value
        verification.updated_at = datetime.now()
        self.db.commit()

        return FaceVerificationResponse(
            success=True,
            message=f"可继续认证（剩余 {self.MAX_RETRY_COUNT - verification.retry_count} 次机会）",
            verification_id=verification.id,
            status=FaceVerificationStatus.IN_PROGRESS,
        )

    def get_verification_record(self, user_id: str) -> Optional[FaceVerificationDB]:
        """获取用户认证记录"""
        return self.db.query(FaceVerificationDB).filter(
            FaceVerificationDB.user_id == user_id
        ).first()

    def check_user_verified(self, user_id: str) -> bool:
        """检查用户是否已认证"""
        verification = self.db.query(FaceVerificationDB).filter(
            FaceVerificationDB.user_id == user_id,
            FaceVerificationDB.status == FaceVerificationStatus.VERIFIED.value
        ).first()

        return verification is not None

    def get_badge_display_info(self, badge_type: VerificationBadgeType) -> dict:
        """获取徽章展示信息"""
        config = VERIFICATION_BADGE_CONFIG.get(badge_type)
        if not config:
            return {
                "icon": "⭐",
                "color": "#1890ff",
                "name": "已认证",
            }
        return {
            "icon": config["icon"],
            "color": config["color"],
            "name": config["name"],
            "description": config["description"],
        }


# 服务工厂函数
def get_face_verification_service(db: Session) -> FaceVerificationService:
    """获取人脸认证服务实例"""
    return FaceVerificationService(db)