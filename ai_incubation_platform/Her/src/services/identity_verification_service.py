"""
实名认证服务

P4 新增:
- 身份证 OCR 识别
- 人脸核身
- 认证状态管理
- 认证标识体系

P0 增强：
- 多源身份核验（学历/职业/收入/房产/无犯罪记录）
- 信任勋章体系
- 信任分计算
"""
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from utils.logger import logger
from db.models import IdentityVerificationDB, UserDB
from models.p0_identity_models import (
    TrustBadgeDB,
    TrustBadgeHistoryDB,
    EducationCredentialDB,
    OccupationCredentialDB,
    IncomeCredentialDB,
    PropertyCredentialDB,
)
from models.p17_models import TrustScoreDB


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

    # P0: 多源身份核验配置
    VERIFICATION_TYPES = {
        "real_name": {
            "name": "实名认证",
            "badge_type": "real_name_verified",
            "score_weight": 20,
            "required": True,
        },
        "education": {
            "name": "学历认证",
            "badge_type": "education_verified",
            "score_weight": 20,
            "required": False,
        },
        "occupation": {
            "name": "职业认证",
            "badge_type": "occupation_verified",
            "score_weight": 15,
            "required": False,
        },
        "income": {
            "name": "收入认证",
            "badge_type": "income_verified",
            "score_weight": 15,
            "required": False,
        },
        "property": {
            "name": "房产认证",
            "badge_type": "property_verified",
            "score_weight": 15,
            "required": False,
        },
        "criminal_record": {
            "name": "无犯罪记录",
            "badge_type": "criminal_clear",
            "score_weight": 15,
            "required": False,
        },
    }

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

    # ============================================
    # P0: 多源身份核验方法
    # ============================================

    def get_user_trust_badges(self, user_id: str) -> List[Dict]:
        """获取用户的信任勋章列表"""
        badges = self.db.query(TrustBadgeDB).filter(
            TrustBadgeDB.user_id == user_id,
            TrustBadgeDB.is_active == True,
            TrustBadgeDB.is_displayed == True
        ).all()

        return [
            {
                "id": badge.id,
                "badge_type": badge.badge_type,
                "badge_name": badge.badge_name,
                "badge_icon": badge.badge_icon,
                "badge_level": badge.badge_level,
                "badge_level_value": badge.badge_level_value,
                "earned_at": badge.earned_at.isoformat() if badge.earned_at else None,
            }
            for badge in badges
        ]

    def submit_education_verification(
        self,
        user_id: str,
        school_name: str,
        degree_type: str,
        major: str,
        graduation_year: int,
        chsi_verification_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        提交学历认证申请

        Args:
            user_id: 用户 ID
            school_name: 学校名称
            degree_type: 学历类型 (associate/bachelor/master/doctor)
            major: 专业
            graduation_year: 毕业年份
            chsi_verification_id: 学信网验证码

        Returns:
            (success, message, credential_id)
        """
        try:
            # 创建学历凭证
            credential = EducationCredentialDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                school_name=school_name,
                degree_type=degree_type,
                major=major,
                graduation_year=graduation_year,
                chsi_verification_id=chsi_verification_id,
                verification_status="pending"
            )
            self.db.add(credential)
            self.db.commit()

            logger.info(f"Education verification submitted: user={user_id}, school={school_name}")
            return True, "学历认证申请已提交", credential.id

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to submit education verification: {e}")
            return False, str(e), None

    def submit_occupation_verification(
        self,
        user_id: str,
        company_name: str,
        position: str,
        work_years: int,
        work_email: Optional[str] = None,
        verification_method: str = "email"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        提交职业认证申请

        Args:
            user_id: 用户 ID
            company_name: 公司名称
            position: 职位
            work_years: 工作年限
            work_email: 工作邮箱
            verification_method: 验证方式 (email/certificate/social_security)

        Returns:
            (success, message, credential_id)
        """
        try:
            credential = OccupationCredentialDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                company_name=company_name,
                position=position,
                work_years=work_years,
                work_email=work_email,
                verification_method=verification_method
            )
            self.db.add(credential)
            self.db.commit()

            logger.info(f"Occupation verification submitted: user={user_id}, company={company_name}")
            return True, "职业认证申请已提交", credential.id

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to submit occupation verification: {e}")
            return False, str(e), None

    def approve_education_verification(
        self,
        credential_id: str,
        level: str,
        level_value: int
    ) -> Tuple[bool, str]:
        """
        批准学历认证

        Args:
            credential_id: 凭证 ID
            level: 学历等级名称
            level_value: 学历等级数值

        Returns:
            (success, message)
        """
        credential = self.db.query(EducationCredentialDB).filter(
            EducationCredentialDB.id == credential_id
        ).first()

        if not credential:
            return False, "凭证不存在"

        try:
            credential.verification_status = "verified"
            credential.verified_at = datetime.utcnow()

            # 授予信任勋章
            self._award_trust_badge(
                credential.user_id,
                "education_verified",
                "学历认证",
                level,
                level_value,
                credential.id
            )

            # 重新计算信任分
            self.calculate_trust_score(credential.user_id)

            self.db.commit()
            logger.info(f"Education verification approved: user={credential.user_id}, level={level}")
            return True, "学历认证已通过"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to approve education verification: {e}")
            return False, str(e)

    def _award_trust_badge(
        self,
        user_id: str,
        badge_type: str,
        badge_name: str,
        level: Optional[str],
        level_value: int,
        source_verification_id: str
    ):
        """授予信任勋章"""
        # 检查勋章是否已存在
        existing_badge = self.db.query(TrustBadgeDB).filter(
            TrustBadgeDB.user_id == user_id,
            TrustBadgeDB.badge_type == badge_type
        ).first()

        badge_icons = {
            "real_name_verified": "🆔",
            "education_verified": "🎓",
            "occupation_verified": "💼",
            "income_verified": "💰",
            "property_verified": "🏠",
            "criminal_clear": "🛡️",
            "vehicle_verified": "🚗",
        }

        if existing_badge:
            existing_badge.is_active = True
            existing_badge.source_verification_id = source_verification_id
            existing_badge.badge_level = level
            existing_badge.badge_level_value = level_value
        else:
            badge = TrustBadgeDB(
                user_id=user_id,
                badge_type=badge_type,
                badge_name=badge_name,
                badge_icon=badge_icons.get(badge_type, "⭐"),
                badge_level=level,
                badge_level_value=level_value,
                source_verification_id=source_verification_id
            )
            self.db.add(badge)

            # 记录历史
            history = TrustBadgeHistoryDB(
                user_id=user_id,
                badge_type=badge_type,
                event_type="earned",
                event_data=json.dumps({"badge_name": badge_name, "level": level}),
                actor_id=user_id
            )
            self.db.add(history)

        self.db.commit()
        logger.info(f"Trust badge awarded: user={user_id}, badge_type={badge_type}")

    def calculate_trust_score(self, user_id: str) -> int:
        """
        计算用户信任分

        Returns:
            信任分数 (0-100)
        """
        badges = self.db.query(TrustBadgeDB).filter(
            TrustBadgeDB.user_id == user_id,
            TrustBadgeDB.is_active == True
        ).all()

        score = 0
        score_breakdown = {
            "real_name_score": 0,
            "education_score": 0,
            "occupation_score": 0,
            "income_score": 0,
            "property_score": 0,
            "background_score": 0,
        }

        for badge in badges:
            badge_config = None
            for v_type, config in self.VERIFICATION_TYPES.items():
                if config.get("badge_type") == badge.badge_type:
                    badge_config = config
                    break

            if not badge_config:
                continue

            score_weight = badge_config.get("score_weight", 0)

            if badge.badge_type == "real_name_verified":
                score_breakdown["real_name_score"] = score_weight
                score += score_weight

            elif badge.badge_type == "education_verified":
                level = badge.badge_level_value or 0
                level_score = min(score_weight, level * 5)
                score_breakdown["education_score"] = level_score
                score += level_score

            elif badge.badge_type == "occupation_verified":
                level_score = badge.badge_level_value or int(score_weight * 0.8)
                score_breakdown["occupation_score"] = min(score_weight, level_score)
                score += score_breakdown["occupation_score"]

            elif badge.badge_type == "income_verified":
                level_score = badge.badge_level_value or int(score_weight * 0.8)
                score_breakdown["income_score"] = min(score_weight, level_score)
                score += score_breakdown["income_score"]

            elif badge.badge_type == "property_verified":
                level_score = badge.badge_level_value or int(score_weight * 0.8)
                score_breakdown["property_score"] = min(score_weight, level_score)
                score += score_breakdown["property_score"]

            elif badge.badge_type == "criminal_clear":
                score_breakdown["background_score"] = score_weight
                score += score_weight

        # 更新或创建信任分记录
        trust_score = self.db.query(TrustScoreDB).filter(
            TrustScoreDB.user_id == user_id
        ).first()

        if trust_score:
            trust_score.trust_score = min(100, score)
            trust_score.trust_level = self._get_trust_level_name(min(100, score))
            trust_score.last_calculated_at = datetime.utcnow()
        else:
            trust_score = TrustScoreDB(
                user_id=user_id,
                trust_score=min(100, score),
                trust_level=self._get_trust_level_name(min(100, score)),
            )
            self.db.add(trust_score)

        self.db.commit()
        logger.info(f"Trust score calculated: user={user_id}, score={score}")

        return min(100, score)

    def _get_trust_level_name(self, score: int) -> str:
        """获取信任等级名称"""
        if score >= 90:
            return "diamond"
        elif score >= 80:
            return "platinum"
        elif score >= 60:
            return "gold"
        elif score >= 40:
            return "silver"
        else:
            return "bronze"

    def get_trust_score(self, user_id: str) -> Dict:
        """获取用户信任分详情"""
        trust_score = self.db.query(TrustScoreDB).filter(
            TrustScoreDB.user_id == user_id
        ).first()

        if not trust_score:
            score = self.calculate_trust_score(user_id)
            trust_score = self.db.query(TrustScoreDB).filter(
                TrustScoreDB.user_id == user_id
            ).first()

        if not trust_score:
            return {
                "user_id": user_id,
                "trust_score": 0,
                "trust_level": "bronze",
                "scores": {}
            }

        return {
            "user_id": user_id,
            "trust_score": trust_score.trust_score,
            "trust_level": trust_score.trust_level,
            "last_calculated_at": trust_score.last_calculated_at.isoformat() if trust_score.last_calculated_at else None
        }

    # ============================================
    # P0: 收入认证方法
    # ============================================

    def submit_income_verification(
        self,
        user_id: str,
        income_range: str,
        income_type: str = "salary",
        verification_method: str = "tax_record",
        bank_name: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        提交收入认证申请

        Args:
            user_id: 用户 ID
            income_range: 收入范围 (<5k/5k-10k/10k-20k/20k-30k/30k-50k/50k-100k/>100k)
            income_type: 收入类型 (salary/bonus/investment/business/other)
            verification_method: 验证方式 (tax_record/bank_statement/social_security)
            bank_name: 银行名称

        Returns:
            (success, message, credential_id)
        """
        try:
            credential = IncomeCredentialDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                income_range=income_range,
                income_type=income_type,
                verification_method=verification_method,
                bank_name=bank_name,
                verification_status="pending"
            )
            self.db.add(credential)
            self.db.commit()

            logger.info(f"Income verification submitted: user={user_id}, range={income_range}")
            return True, "收入认证申请已提交", credential.id

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to submit income verification: {e}")
            return False, str(e), None

    def approve_income_verification(
        self,
        credential_id: str,
        level_value: int,
    ) -> Tuple[bool, str]:
        """
        批准收入认证

        Args:
            credential_id: 凭证 ID
            level_value: 收入等级数值

        Returns:
            (success, message)
        """
        credential = self.db.query(IncomeCredentialDB).filter(
            IncomeCredentialDB.id == credential_id
        ).first()

        if not credential:
            return False, "凭证不存在"

        try:
            credential.verification_status = "verified"
            credential.verified_at = datetime.utcnow()

            # 授予信任勋章
            self._award_trust_badge(
                credential.user_id,
                "income_verified",
                "收入认证",
                None,
                level_value,
                credential.id
            )

            # 重新计算信任分
            self.calculate_trust_score(credential.user_id)

            self.db.commit()
            logger.info(f"Income verification approved: user={credential.user_id}")
            return True, "收入认证已通过"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to approve income verification: {e}")
            return False, str(e)

    # ============================================
    # P0: 房产认证方法
    # ============================================

    def submit_property_verification(
        self,
        user_id: str,
        property_location: str,
        property_type: str = "apartment",
        property_area: Optional[float] = None,
        property_value: Optional[float] = None,
        ownership_type: str = "sole",
        property_cert_hash: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        提交房产认证申请

        Args:
            user_id: 用户 ID
            property_location: 房产位置
            property_type: 房产类型 (apartment/villa/commercial/land)
            property_area: 面积（平方米）
            property_value: 估值（万元）
            ownership_type: 产权类型 (sole/joint/family)
            property_cert_hash: 房产证号哈希

        Returns:
            (success, message, credential_id)
        """
        try:
            credential = PropertyCredentialDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                property_location=property_location,
                property_type=property_type,
                property_area=property_area,
                property_value=property_value,
                ownership_type=ownership_type,
                property_cert_hash=property_cert_hash,
                verification_status="pending"
            )
            self.db.add(credential)
            self.db.commit()

            logger.info(f"Property verification submitted: user={user_id}, location={property_location}")
            return True, "房产认证申请已提交", credential.id

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to submit property verification: {e}")
            return False, str(e), None

    def approve_property_verification(
        self,
        credential_id: str,
        level_value: int,
    ) -> Tuple[bool, str]:
        """
        批准房产认证

        Args:
            credential_id: 凭证 ID
            level_value: 房产等级数值

        Returns:
            (success, message)
        """
        credential = self.db.query(PropertyCredentialDB).filter(
            PropertyCredentialDB.id == credential_id
        ).first()

        if not credential:
            return False, "凭证不存在"

        try:
            credential.verification_status = "verified"
            credential.verified_at = datetime.utcnow()

            # 授予信任勋章
            self._award_trust_badge(
                credential.user_id,
                "property_verified",
                "房产认证",
                None,
                level_value,
                credential.id
            )

            # 重新计算信任分
            self.calculate_trust_score(credential.user_id)

            self.db.commit()
            logger.info(f"Property verification approved: user={credential.user_id}")
            return True, "房产认证已通过"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to approve property verification: {e}")
            return False, str(e)

    # ============================================
    # P0: 无犯罪记录认证方法
    # ============================================

    def submit_criminal_record_verification(
        self,
        user_id: str,
        verification_method: str = "police_api",
        certificate_url: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        提交无犯罪记录认证申请

        Args:
            user_id: 用户 ID
            verification_method: 验证方式 (police_api/certificate)
            certificate_url: 无犯罪记录证明 URL

        Returns:
            (success, message, credential_id)
        """
        try:
            from models.p0_identity_models import OccupationCredentialDB

            credential = OccupationCredentialDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                company_name="公安机关",
                position="",
                work_years=0,
                verification_method=verification_method,
                proof_document_url=certificate_url,
            )
            self.db.add(credential)
            self.db.commit()

            logger.info(f"Criminal record verification submitted: user={user_id}")
            return True, "无犯罪记录认证申请已提交", credential.id

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to submit criminal record verification: {e}")
            return False, str(e), None

    def approve_criminal_record_verification(
        self,
        user_id: str,
    ) -> Tuple[bool, str]:
        """
        批准无犯罪记录认证

        Args:
            user_id: 用户 ID

        Returns:
            (success, message)
        """
        try:
            # 授予信任勋章
            self._award_trust_badge(
                user_id,
                "criminal_clear",
                "无犯罪记录",
                None,
                100,
                "criminal_record_approval"
            )

            # 重新计算信任分
            self.calculate_trust_score(user_id)

            self.db.commit()
            logger.info(f"Criminal record verification approved: user={user_id}")
            return True, "无犯罪记录认证已通过"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to approve criminal record verification: {e}")
            return False, str(e)

    # ============================================
    # P0: 外部 API 对接方法
    # ============================================

    def call_external_verification_api(
        self,
        api_name: str,
        params: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        调用外部验证 API

        Args:
            api_name: API 名称 (chsi/enterprise_email/tax_bureau/bank_verify/property_registry/police_record)
            params: API 参数

        Returns:
            (success, result, error_message)
        """
        # 获取 API 配置
        from models.p0_identity_models import ExternalVerificationAPIConfigDB

        config = self.db.query(ExternalVerificationAPIConfigDB).filter(
            ExternalVerificationAPIConfigDB.api_name == api_name,
            ExternalVerificationAPIConfigDB.is_active == True
        ).first()

        if not config:
            return False, {}, f"API 配置不存在：{api_name}"

        # Mock 外部 API 调用（实际应使用 requests 调用真实 API）
        if api_name == "chsi":
            return self._mock_chsi_api(params)
        elif api_name == "enterprise_email":
            return self._mock_enterprise_email_api(params)
        elif api_name == "tax_bureau":
            return self._mock_tax_bureau_api(params)
        elif api_name == "property_registry":
            return self._mock_property_registry_api(params)
        elif api_name == "police_record":
            return self._mock_police_record_api(params)
        else:
            return False, {}, f"不支持的 API: {api_name}"

    def _mock_chsi_api(self, params: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """Mock 学信网 API"""
        # 实际应调用：https://www.chsi.com.cn/api/verify
        student_id = params.get("student_id", "")
        school_name = params.get("school_name", "")

        # Mock 响应
        return True, {
            "verified": True,
            "student_name": "张三",
            "school_name": school_name,
            "degree_type": params.get("degree_type", "bachelor"),
            "major": "计算机科学",
            "graduation_date": "2020-06",
            "verification_id": f"CHSI_{uuid.uuid4().hex[:12]}",
        }, ""

    def _mock_enterprise_email_api(self, params: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """Mock 企业邮箱验证 API"""
        email = params.get("email", "")
        company_name = params.get("company_name", "")

        # Mock 验证
        is_valid = email.endswith("@company.com") or email.endswith("@enterprise.com")

        return True, {
            "verified": is_valid,
            "email": email,
            "company_name": company_name,
            "domain_verified": is_valid,
        }, ""

    def _mock_tax_bureau_api(self, params: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """Mock 税务局 API"""
        tax_id = params.get("tax_id", "")
        name = params.get("name", "")

        # Mock 响应
        return True, {
            "verified": True,
            "name": name,
            "tax_id": tax_id,
            "annual_income": params.get("annual_income", 200000),
            "tax_level": "A",
        }, ""

    def _mock_property_registry_api(self, params: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """Mock 房产登记 API"""
        cert_no = params.get("cert_no", "")
        owner_name = params.get("owner_name", "")

        # Mock 响应
        return True, {
            "verified": True,
            "owner_name": owner_name,
            "property_location": params.get("location", "北京市朝阳区 xxx"),
            "property_area": params.get("area", 100),
            "property_type": "住宅",
            "registration_date": "2020-01-01",
        }, ""

    def _mock_police_record_api(self, params: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """Mock 公安无犯罪记录 API"""
        id_number = params.get("id_number", "")
        name = params.get("name", "")

        # Mock 响应（假设都通过）
        return True, {
            "verified": True,
            "name": name,
            "id_number": id_number[:6] + "****" + id_number[-4:],
            "has_criminal_record": False,
            "certificate_no": f"POLICE_{uuid.uuid4().hex[:12]}",
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
        }, ""
