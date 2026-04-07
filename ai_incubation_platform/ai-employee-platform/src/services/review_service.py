"""
评价服务 - 支持双向评价
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from models.db_models import (
    ReviewDB, ReviewTypeEnum, EmployerProfileDB, SkillTagDB, EmployeeSkillDB,
    SkillLevelEnum, SkillCategoryEnum, OrderDB, AIEmployeeDB
)
from services.base_service import BaseService


class ReviewService(BaseService):
    """评价服务"""

    def create_review(
        self,
        tenant_id: str,
        order_id: str,
        employee_id: str,
        reviewer_id: str,
        reviewee_id: str,
        review_type: ReviewTypeEnum,
        rating: float,
        review_text: Optional[str] = None,
        review_tags: List[str] = None,
        communication: float = 5.0,
        quality: float = 5.0,
        timeliness: float = 5.0,
        professionalism: float = 5.0,
        is_public: bool = True
    ) -> Optional[ReviewDB]:
        """创建评价"""
        try:
            # 检查订单是否存在且已完成
            order = self.db.query(OrderDB).filter(OrderDB.id == order_id).first()
            if not order or order.status.value != "completed":
                return None

            # 检查是否已存在评价
            existing = self.db.query(ReviewDB).filter(
                ReviewDB.order_id == order_id,
                ReviewDB.review_type == review_type
            ).first()
            if existing:
                return None

            review = ReviewDB(
                tenant_id=tenant_id,
                order_id=order_id,
                employee_id=employee_id,
                reviewer_id=reviewer_id,
                reviewee_id=reviewee_id,
                review_type=review_type,
                rating=rating,
                review_text=review_text,
                review_tags=review_tags or [],
                communication=communication,
                quality=quality,
                timeliness=timeliness,
                professionalism=professionalism,
                is_public=is_public
            )
            self.db.add(review)
            self.db.commit()
            self.db.refresh(review)

            # 更新被评价者的评分
            self._update_reviewee_rating(reviewee_id, review_type)

            self.logger.info(f"Created review: {review.id} for order: {order_id}")
            return review
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create review: {str(e)}")
            raise

    def _update_reviewee_rating(self, reviewee_id: str, review_type: ReviewTypeEnum) -> None:
        """更新被评价者的平均评分"""
        if review_type == ReviewTypeEnum.HIRER_TO_EMPLOYEE:
            # 更新员工评分
            employee = self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == reviewee_id).first()
            if employee:
                reviews = self.db.query(ReviewDB).filter(
                    ReviewDB.reviewee_id == reviewee_id,
                    ReviewDB.review_type == ReviewTypeEnum.HIRER_TO_EMPLOYEE,
                    ReviewDB.is_hidden == False
                ).all()
                if reviews:
                    avg_rating = sum(r.rating for r in reviews) / len(reviews)
                    employee.rating = avg_rating
                    employee.review_count = len(reviews)
                    self.db.commit()
        else:
            # 更新雇主评分
            employer = self.db.query(EmployerProfileDB).filter(EmployerProfileDB.user_id == reviewee_id).first()
            if employer:
                reviews = self.db.query(ReviewDB).filter(
                    ReviewDB.reviewee_id == reviewee_id,
                    ReviewDB.review_type == ReviewTypeEnum.OWNER_TO_HIRER,
                    ReviewDB.is_hidden == False
                ).all()
                if reviews:
                    avg_rating = sum(r.rating for r in reviews) / len(reviews)
                    employer.rating = avg_rating
                    employer.review_count = len(reviews)
                    self.db.commit()

    def get_review(self, review_id: str) -> Optional[ReviewDB]:
        """获取评价详情"""
        return self.db.query(ReviewDB).filter(ReviewDB.id == review_id).first()

    def list_reviews(
        self,
        tenant_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        review_type: Optional[ReviewTypeEnum] = None,
        min_rating: float = 0,
        limit: int = 100,
        offset: int = 0
    ) -> List[ReviewDB]:
        """获取评价列表"""
        query = self.db.query(ReviewDB).filter(ReviewDB.is_hidden == False)
        if tenant_id:
            query = query.filter(ReviewDB.tenant_id == tenant_id)
        if employee_id:
            query = query.filter(ReviewDB.employee_id == employee_id)
        if review_type:
            query = query.filter(ReviewDB.review_type == review_type)
        if min_rating > 0:
            query = query.filter(ReviewDB.rating >= min_rating)
        return query.order_by(ReviewDB.created_at.desc()).offset(offset).limit(limit).all()

    def like_review(self, review_id: str) -> bool:
        """点赞评价"""
        review = self.get_review(review_id)
        if not review:
            return False
        review.likes += 1
        review.updated_at = datetime.now()
        self.db.commit()
        return True

    def respond_to_review(self, review_id: str, response_text: str) -> bool:
        """回复评价"""
        review = self.get_review(review_id)
        if not review:
            return False
        review.response = response_text
        review.response_at = datetime.now()
        review.updated_at = datetime.now()
        self.db.commit()
        return True

    def hide_review(self, review_id: str) -> bool:
        """隐藏评价（违规处理）"""
        review = self.get_review(review_id)
        if not review:
            return False
        review.is_hidden = True
        review.updated_at = datetime.now()
        self.db.commit()
        return True


class EmployerProfileService(BaseService):
    """雇主档案服务"""

    def create_profile(
        self,
        tenant_id: str,
        user_id: str,
        company_name: Optional[str] = None,
        industry: Optional[str] = None,
        company_size: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[EmployerProfileDB]:
        """创建雇主档案"""
        try:
            # 检查是否已存在
            existing = self.db.query(EmployerProfileDB).filter(
                EmployerProfileDB.user_id == user_id
            ).first()
            if existing:
                return None

            profile = EmployerProfileDB(
                tenant_id=tenant_id,
                user_id=user_id,
                company_name=company_name,
                industry=industry,
                company_size=company_size,
                description=description
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            self.logger.info(f"Created employer profile: {profile.id} for user: {user_id}")
            return profile
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create employer profile: {str(e)}")
            raise

    def get_profile(self, profile_id: str) -> Optional[EmployerProfileDB]:
        """获取雇主档案"""
        return self.db.query(EmployerProfileDB).filter(EmployerProfileDB.id == profile_id).first()

    def get_profile_by_user(self, user_id: str) -> Optional[EmployerProfileDB]:
        """通过用户 ID 获取雇主档案"""
        return self.db.query(EmployerProfileDB).filter(EmployerProfileDB.user_id == user_id).first()

    def update_profile(self, profile_id: str, **kwargs) -> Optional[EmployerProfileDB]:
        """更新雇主档案"""
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        profile.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def record_hire(self, user_id: str, amount: float) -> bool:
        """记录雇佣行为（更新统计）"""
        profile = self.get_profile_by_user(user_id)
        if not profile:
            return False
        profile.total_hires += 1
        profile.total_spent += amount
        profile.updated_at = datetime.now()
        self.db.commit()
        return True

    def list_profiles(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[EmployerProfileDB]:
        """获取雇主档案列表"""
        query = self.db.query(EmployerProfileDB)
        if tenant_id:
            query = query.filter(EmployerProfileDB.tenant_id == tenant_id)
        if status:
            query = query.filter(EmployerProfileDB.status == status)
        return query.offset(offset).limit(limit).all()


class SkillService(BaseService):
    """技能标签服务"""

    def create_skill_tag(
        self,
        name: str,
        category: SkillCategoryEnum,
        parent_skill_id: Optional[str] = None,
        description: Optional[str] = None,
        has_certification: bool = False,
        certification_name: Optional[str] = None
    ) -> Optional[SkillTagDB]:
        """创建技能标签"""
        try:
            # 检查是否已存在
            existing = self.db.query(SkillTagDB).filter(SkillTagDB.name == name).first()
            if existing:
                return None

            skill_tag = SkillTagDB(
                name=name,
                category=category,
                parent_skill_id=parent_skill_id,
                description=description,
                has_certification=has_certification,
                certification_name=certification_name
            )
            self.db.add(skill_tag)
            self.db.commit()
            self.db.refresh(skill_tag)
            self.logger.info(f"Created skill tag: {skill_tag.id}, name: {name}")
            return skill_tag
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create skill tag: {str(e)}")
            raise

    def get_skill_tag(self, skill_tag_id: str) -> Optional[SkillTagDB]:
        """获取技能标签"""
        return self.db.query(SkillTagDB).filter(SkillTagDB.id == skill_tag_id).first()

    def list_skill_tags(
        self,
        category: Optional[SkillCategoryEnum] = None,
        parent_skill_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SkillTagDB]:
        """获取技能标签列表"""
        query = self.db.query(SkillTagDB)
        if category:
            query = query.filter(SkillTagDB.category == category)
        if parent_skill_id:
            query = query.filter(SkillTagDB.parent_skill_id == parent_skill_id)
        return query.order_by(SkillTagDB.usage_count.desc()).offset(offset).limit(limit).all()

    def add_employee_skill(
        self,
        employee_id: str,
        skill_tag_id: str,
        skill_name: str,
        level: SkillLevelEnum,
        years_of_experience: Optional[float] = None,
        certified: bool = False,
        certification_id: Optional[str] = None,
        portfolio_items: List[str] = None
    ) -> Optional[EmployeeSkillDB]:
        """添加员工技能"""
        try:
            # 检查是否已存在
            existing = self.db.query(EmployeeSkillDB).filter(
                EmployeeSkillDB.employee_id == employee_id,
                EmployeeSkillDB.skill_tag_id == skill_tag_id
            ).first()
            if existing:
                return None

            employee_skill = EmployeeSkillDB(
                employee_id=employee_id,
                skill_tag_id=skill_tag_id,
                skill_name=skill_name,
                level=level,
                years_of_experience=years_of_experience,
                certified=certified,
                certification_id=certification_id,
                portfolio_items=portfolio_items or []
            )
            self.db.add(employee_skill)

            # 更新技能标签使用统计
            skill_tag = self.get_skill_tag(skill_tag_id)
            if skill_tag:
                skill_tag.usage_count += 1
                self.db.commit()

            self.db.refresh(employee_skill)
            self.logger.info(f"Added skill {skill_name} to employee {employee_id}")
            return employee_skill
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to add employee skill: {str(e)}")
            raise

    def remove_employee_skill(self, employee_id: str, skill_tag_id: str) -> bool:
        """移除员工技能"""
        employee_skill = self.db.query(EmployeeSkillDB).filter(
            EmployeeSkillDB.employee_id == employee_id,
            EmployeeSkillDB.skill_tag_id == skill_tag_id
        ).first()
        if not employee_skill:
            return False
        self.db.delete(employee_skill)
        self.db.commit()
        return True

    def list_employee_skills(self, employee_id: str) -> List[EmployeeSkillDB]:
        """获取员工技能列表"""
        return self.db.query(EmployeeSkillDB).filter(
            EmployeeSkillDB.employee_id == employee_id
        ).all()

    def search_employees_by_skill(
        self,
        skill_tag_id: str,
        min_level: Optional[SkillLevelEnum] = None,
        certified_only: bool = False,
        limit: int = 100
    ) -> List[EmployeeSkillDB]:
        """通过技能搜索员工"""
        query = self.db.query(EmployeeSkillDB).filter(
            EmployeeSkillDB.skill_tag_id == skill_tag_id
        )
        if min_level:
            level_order = {
                SkillLevelEnum.BEGINNER: 1,
                SkillLevelEnum.INTERMEDIATE: 2,
                SkillLevelEnum.ADVANCED: 3,
                SkillLevelEnum.EXPERT: 4
            }
            # 简化处理：在应用层过滤
            results = query.all()
            min_level_val = level_order.get(min_level, 1)
            results = [e for e in results if level_order.get(e.level, 1) >= min_level_val]
            if certified_only:
                results = [e for e in results if e.certified]
            return results[:limit]
        if certified_only:
            query = query.filter(EmployeeSkillDB.certified == True)
        return query.order_by(EmployeeSkillDB.level.desc()).limit(limit).all()


# 创建全局服务实例（延迟初始化 db）
from config.database import get_db
from config.logging_config import get_logger


class LazyService:
    """懒加载服务包装器"""

    def __init__(self, service_class):
        self._service_class = service_class
        self._service = None

    def _get_service(self):
        if self._service is None:
            db = next(get_db())
            self._service = self._service_class(db)
        return self._service

    def __getattr__(self, name):
        return getattr(self._get_service(), name)


# 懒加载服务实例
review_service = LazyService(ReviewService)
employer_profile_service = LazyService(EmployerProfileService)
skill_service = LazyService(SkillService)
