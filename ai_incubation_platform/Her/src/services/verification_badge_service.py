"""
P6 信任标识体系服务

参考 Bumble 蓝色徽章、青藤之恋学历认证等竞品功能，
实现多层级的信任标识体系。
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import json
import uuid

from db.models import (
    VerificationBadgeDB, EducationVerificationDB, CareerVerificationDB,
    IdentityVerificationDB, PhotoDB, UserMembershipDB
)
from services.base_service import BaseService


# 徽章类型定义
BADGE_TYPES = {
    "identity_verified": {
        "name": "实名认证",
        "description": "已通过身份证实名认证",
        "icon_url": "/badges/identity_verified.png",
        "display_order": 1,
        "required_service": IdentityVerificationDB,
    },
    "face_verified": {
        "name": "人脸核身",
        "description": "已通过人脸核身认证",
        "icon_url": "/badges/face_verified.png",
        "display_order": 2,
        "required_service": IdentityVerificationDB,
    },
    "photo_verified": {
        "name": "照片验证",
        "description": "已通过照片姿势验证",
        "icon_url": "/badges/photo_verified.png",
        "display_order": 3,
        "required_service": PhotoDB,
    },
    "education_verified": {
        "name": "学历认证",
        "description": "已验证学历信息",
        "icon_url": "/badges/education_verified.png",
        "display_order": 4,
        "required_service": EducationVerificationDB,
    },
    "career_verified": {
        "name": "职业认证",
        "description": "已验证职业信息",
        "icon_url": "/badges/career_verified.png",
        "display_order": 5,
        "required_service": CareerVerificationDB,
    },
    "phone_verified": {
        "name": "手机认证",
        "description": "已验证手机号码",
        "icon_url": "/badges/phone_verified.png",
        "display_order": 6,
    },
    "email_verified": {
        "name": "邮箱认证",
        "description": "已验证邮箱地址",
        "icon_url": "/badges/email_verified.png",
        "display_order": 7,
    },
    "premium_member": {
        "name": "付费会员",
        "description": "标准版或以上会员",
        "icon_url": "/badges/premium.png",
        "display_order": 8,
        "required_service": UserMembershipDB,
    },
    "vip_member": {
        "name": "VIP 会员",
        "description": "Premium 会员",
        "icon_url": "/badges/vip.png",
        "display_order": 9,
        "required_service": UserMembershipDB,
    },
    "active_user": {
        "name": "活跃用户",
        "description": "近期活跃用户",
        "icon_url": "/badges/active.png",
        "display_order": 10,
    },
    "early_adopter": {
        "name": "早期用户",
        "description": "平台早期支持者",
        "icon_url": "/badges/early_adopter.png",
        "display_order": 11,
    },
}


class VerificationBadgeService(BaseService):
    """信任标识体系服务"""

    def __init__(self, db: Session):
        super().__init__(db)

    def get_user_badges(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有徽章"""
        badges = self.db.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.user_id == user_id,
            VerificationBadgeDB.status == "active"
        ).order_by(VerificationBadgeDB.display_order).all()

        return [
            {
                "id": badge.id,
                "badge_type": badge.badge_type,
                "name": BADGE_TYPES.get(badge.badge_type, {}).get("name", badge.badge_type),
                "description": badge.description or BADGE_TYPES.get(badge.badge_type, {}).get("description", ""),
                "icon_url": badge.icon_url or BADGE_TYPES.get(badge.badge_type, {}).get("icon_url", ""),
                "display_order": badge.display_order,
                "issued_at": badge.issued_at.isoformat() if badge.issued_at else None,
                "expires_at": badge.expires_at.isoformat() if badge.expires_at else None,
            }
            for badge in badges
        ]

    def get_trust_score(self, user_id: str) -> Dict[str, Any]:
        """
        计算用户信任评分

        基于用户获得的认证徽章数量和类型，计算综合信任评分 (0-100)
        """
        badges = self.get_user_badges(user_id)

        # 核心认证权重
        badge_weights = {
            "identity_verified": 20,
            "face_verified": 15,
            "photo_verified": 15,
            "education_verified": 10,
            "career_verified": 10,
            "phone_verified": 5,
            "email_verified": 5,
            "premium_member": 10,
            "vip_member": 15,
            "active_user": 5,
            "early_adopter": 5,
        }

        score = 0
        max_score = 100
        earned_badges = [b["badge_type"] for b in badges]

        for badge_type in earned_badges:
            score += badge_weights.get(badge_type, 0)

        # 限制最高 100 分
        score = min(score, max_score)

        # 信任等级
        if score >= 80:
            level = "极高"
            level_code = "very_high"
        elif score >= 60:
            level = "高"
            level_code = "high"
        elif score >= 40:
            level = "中等"
            level_code = "medium"
        elif score >= 20:
            level = "低"
            level_code = "low"
        else:
            level = "极低"
            level_code = "very_low"

        return {
            "score": score,
            "max_score": max_score,
            "level": level,
            "level_code": level_code,
            "badge_count": len(badges),
            "badges": badges,
        }

    def award_badge(self, user_id: str, badge_type: str,
                    verification_data: Optional[Dict] = None,
                    expires_days: Optional[int] = None) -> VerificationBadgeDB:
        """授予用户徽章"""
        if badge_type not in BADGE_TYPES:
            raise ValueError(f"未知的徽章类型：{badge_type}")

        badge_info = BADGE_TYPES[badge_type]

        # 检查是否已有该徽章
        existing = self.db.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.user_id == user_id,
            VerificationBadgeDB.badge_type == badge_type,
            VerificationBadgeDB.status == "active"
        ).first()

        if existing:
            return existing

        # 创建新徽章
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        badge = VerificationBadgeDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            badge_type=badge_type,
            status="active",
            verification_data=json.dumps(verification_data) if verification_data else "",
            expires_at=expires_at,
            display_order=badge_info.get("display_order", 10),
            icon_url=badge_info.get("icon_url"),
            description=badge_info.get("description"),
        )

        self.db.add(badge)
        self.db.commit()
        self.db.refresh(badge)

        return badge

    def revoke_badge(self, user_id: str, badge_type: str,
                     reason: str = "") -> bool:
        """撤销用户徽章"""
        badge = self.db.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.user_id == user_id,
            VerificationBadgeDB.badge_type == badge_type,
            VerificationBadgeDB.status == "active"
        ).first()

        if not badge:
            return False

        badge.status = "suspended"
        self.db.commit()

        return True

    def check_and_award_badges(self, user_id: str) -> List[str]:
        """检查并自动授予符合条件的徽章"""
        awarded = []

        # 检查实名认证
        identity = self.db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.user_id == user_id,
            IdentityVerificationDB.verification_status == "verified"
        ).first()

        if identity:
            if "identity_verified" not in [b.badge_type for b in self.get_user_badges_query(user_id)]:
                self.award_badge(user_id, "identity_verified")
                awarded.append("identity_verified")

            if identity.verification_type == "advanced" and identity.face_similarity_score:
                if "face_verified" not in [b.badge_type for b in self.get_user_badges_query(user_id)]:
                    self.award_badge(user_id, "face_verified")
                    awarded.append("face_verified")

        # 检查照片验证
        verified_photos = self.db.query(PhotoDB).filter(
            PhotoDB.user_id == user_id,
            PhotoDB.is_verified == True
        ).count()

        if verified_photos > 0:
            if "photo_verified" not in [b.badge_type for b in self.get_user_badges_query(user_id)]:
                self.award_badge(user_id, "photo_verified")
                awarded.append("photo_verified")

        # 检查学历认证
        education = self.db.query(EducationVerificationDB).filter(
            EducationVerificationDB.user_id == user_id,
            EducationVerificationDB.verification_status == "verified"
        ).first()

        if education:
            if "education_verified" not in [b.badge_type for b in self.get_user_badges_query(user_id)]:
                self.award_badge(user_id, "education_verified")
                awarded.append("education_verified")

        # 检查职业认证
        career = self.db.query(CareerVerificationDB).filter(
            CareerVerificationDB.user_id == user_id,
            CareerVerificationDB.verification_status == "verified"
        ).first()

        if career:
            if "career_verified" not in [b.badge_type for b in self.get_user_badges_query(user_id)]:
                self.award_badge(user_id, "career_verified")
                awarded.append("career_verified")

        # 检查会员状态
        membership = self.db.query(UserMembershipDB).filter(
            UserMembershipDB.user_id == user_id,
            UserMembershipDB.status == "active"
        ).first()

        if membership:
            if membership.tier == "premium":
                if "vip_member" not in [b.badge_type for b in self.get_user_badges_query(user_id)]:
                    self.award_badge(user_id, "vip_member")
                    awarded.append("vip_member")
            elif membership.tier == "standard":
                if "premium_member" not in [b.badge_type for b in self.get_user_badges_query(user_id)]:
                    self.award_badge(user_id, "premium_member")
                    awarded.append("premium_member")

        return awarded

    def get_user_badges_query(self, user_id: str) -> List[VerificationBadgeDB]:
        """获取用户徽章查询结果"""
        return self.db.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.user_id == user_id,
            VerificationBadgeDB.status == "active"
        ).all()

    def submit_education_verification(self, user_id: str,
                                      school_name: str,
                                      degree: Optional[str] = None,
                                      major: Optional[str] = None,
                                      graduation_year: Optional[int] = None,
                                      certificate_url: Optional[str] = None,
                                      student_id_url: Optional[str] = None) -> EducationVerificationDB:
        """提交学历认证申请"""
        verification = EducationVerificationDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            school_name=school_name,
            degree=degree,
            major=major,
            graduation_year=graduation_year,
            certificate_url=certificate_url,
            student_id_url=student_id_url,
            verification_status="pending",
        )

        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)

        return verification

    def submit_career_verification(self, user_id: str,
                                   company_name: Optional[str] = None,
                                   position: Optional[str] = None,
                                   industry: Optional[str] = None,
                                   work_email: Optional[str] = None,
                                   work_certificate_url: Optional[str] = None) -> CareerVerificationDB:
        """提交职业认证申请"""
        verification = CareerVerificationDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            company_name=company_name,
            position=position,
            industry=industry,
            work_email=work_email,
            work_certificate_url=work_certificate_url,
            verification_status="pending",
        )

        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)

        return verification

    def approve_education_verification(self, verification_id: str,
                                       school_type: Optional[str] = None) -> bool:
        """批准学历认证"""
        verification = self.db.query(EducationVerificationDB).filter(
            EducationVerificationDB.id == verification_id
        ).first()

        if not verification:
            return False

        verification.verification_status = "verified"
        verification.verified_at = datetime.utcnow()
        verification.school_type = school_type

        self.db.commit()

        # 自动授予学历认证徽章
        self.award_badge(verification.user_id, "education_verified")

        return True

    def approve_career_verification(self, verification_id: str,
                                    company_type: Optional[str] = None) -> bool:
        """批准职业认证"""
        verification = self.db.query(CareerVerificationDB).filter(
            CareerVerificationDB.id == verification_id
        ).first()

        if not verification:
            return False

        verification.verification_status = "verified"
        verification.verified_at = datetime.utcnow()
        verification.company_type = company_type

        self.db.commit()

        # 自动授予职业认证徽章
        self.award_badge(verification.user_id, "career_verified")

        return True

    def reject_verification(self, verification_id: str,
                            verification_type: str,
                            reason: str) -> bool:
        """拒绝认证申请"""
        if verification_type == "education":
            verification = self.db.query(EducationVerificationDB).filter(
                EducationVerificationDB.id == verification_id
            ).first()
        elif verification_type == "career":
            verification = self.db.query(CareerVerificationDB).filter(
                CareerVerificationDB.id == verification_id
            ).first()
        else:
            return False

        if not verification:
            return False

        verification.verification_status = "rejected"
        self.db.commit()

        return True

    def get_verification_stats(self) -> Dict[str, Any]:
        """获取认证统计信息"""
        total_users = self.db.query(func.count(VerificationBadgeDB.user_id.distinct())).scalar()

        badge_counts = self.db.query(
            VerificationBadgeDB.badge_type,
            func.count(VerificationBadgeDB.id)
        ).filter(
            VerificationBadgeDB.status == "active"
        ).group_by(VerificationBadgeDB.badge_type).all()

        education_stats = self.db.query(
            EducationVerificationDB.verification_status,
            func.count(EducationVerificationDB.id)
        ).group_by(EducationVerificationDB.verification_status).all()

        career_stats = self.db.query(
            CareerVerificationDB.verification_status,
            func.count(CareerVerificationDB.id)
        ).group_by(CareerVerificationDB.verification_status).all()

        return {
            "total_badged_users": total_users,
            "badge_counts": dict(badge_counts),
            "education_verifications": dict(education_stats),
            "career_verifications": dict(career_stats),
        }