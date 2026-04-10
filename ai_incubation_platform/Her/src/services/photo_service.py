"""
照片管理服务

P4 新增:
- 照片上传
- 照片审核
- 照片展示
- 照片验证机制

P20 增强:
- 缓存失效集成
- 继承 BaseService 统一数据库会话管理
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.models import PhotoDB
from cache import cache_manager
from services.base_service import BaseService


class PhotoService(BaseService[PhotoDB]):
    """照片管理服务"""

    # 允许的照片类型
    ALLOWED_PHOTO_TYPES = ["profile", "avatar", "verification", "lifestyle"]

    # 最大照片数量
    MAX_PHOTOS_PER_USER = 9

    # 照片审核状态
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    def __init__(self, db: Optional[Session] = None):
        """
        初始化照片服务

        Args:
            db: 数据库会话（可选，支持依赖注入）
        """
        super().__init__(db, PhotoDB)
        self.upload_dir = "uploads/photos"

    def upload_photo(
        self,
        user_id: str,
        photo_url: str,
        photo_type: str = "profile",
        ai_tags: Optional[List[str]] = None,
        ai_quality_score: Optional[float] = None
    ) -> PhotoDB:
        """
        上传照片

        Args:
            user_id: 用户 ID
            photo_url: 照片 URL
            photo_type: 照片类型
            ai_tags: AI 分析标签
            ai_quality_score: AI 质量评分

        Returns:
            PhotoDB: 照片记录
        """
        if photo_type not in self.ALLOWED_PHOTO_TYPES:
            raise ValueError(f"无效的照片类型：{photo_type}")

        # 检查用户照片数量限制
        existing_photos = self.get_user_photos(user_id)
        if len(existing_photos) >= self.MAX_PHOTOS_PER_USER:
            raise ValueError(f"最多上传{self.MAX_PHOTOS_PER_USER}张照片")

        # 创建照片记录
        photo = PhotoDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            photo_url=photo_url,
            photo_type=photo_type,
            display_order=len(existing_photos),
            moderation_status=self.STATUS_PENDING,
            ai_tags=json.dumps(ai_tags or []),
            ai_quality_score=ai_quality_score
        )

        self.db.add(photo)
        self.db.commit()
        self.db.refresh(photo)

        # P20 增强：照片上传后失效用户缓存（待审核状态下缓存可能仍是旧的，但为了简单统一失效）
        cache_manager.get_instance().invalidate_on_profile_update(user_id)

        return photo

    def get_user_photos(self, user_id: str, approved_only: bool = False) -> List[PhotoDB]:
        """
        获取用户照片列表

        Args:
            user_id: 用户 ID
            approved_only: 是否只返回已审核通过的照片

        Returns:
            List[PhotoDB]: 照片列表
        """
        query = self.db.query(PhotoDB).filter(
            and_(
                PhotoDB.user_id == user_id,
                PhotoDB.is_active == True
            )
        )

        if approved_only:
            query = query.filter(PhotoDB.moderation_status == self.STATUS_APPROVED)

        return query.order_by(PhotoDB.display_order, PhotoDB.created_at).all()

    def get_photo(self, photo_id: str) -> Optional[PhotoDB]:
        """获取照片详情（仅返回活跃照片）"""
        return self.db.query(PhotoDB).filter(
            and_(PhotoDB.id == photo_id, PhotoDB.is_active == True)
        ).first()

    def update_photo_order(self, user_id: str, photo_ids: List[str]) -> bool:
        """
        更新照片排序

        Args:
            user_id: 用户 ID
            photo_ids: 按新顺序排列的照片 ID 列表

        Returns:
            bool: 是否成功
        """
        photos = self.get_user_photos(user_id)
        photo_map = {p.id: p for p in photos}

        for index, photo_id in enumerate(photo_ids):
            if photo_id in photo_map:
                photo_map[photo_id].display_order = index

        self.db.commit()
        return True

    def delete_photo(self, photo_id: str, user_id: str) -> bool:
        """
        删除照片

        Args:
            photo_id: 照片 ID
            user_id: 用户 ID (用于权限验证)

        Returns:
            bool: 是否成功
        """
        photo = self.get_photo(photo_id)
        if not photo or photo.user_id != user_id:
            return False

        # 软删除
        photo.is_active = False
        self.db.commit()

        # 重新排序
        remaining_photos = self.get_user_photos(user_id)
        for index, p in enumerate(remaining_photos):
            p.display_order = index
        self.db.commit()

        # P20 增强：照片删除后失效用户缓存
        cache_manager.get_instance().invalidate_on_profile_update(user_id)

        return True

    def moderate_photo(
        self,
        photo_id: str,
        moderator_id: str,
        status: str,
        reason: Optional[str] = None
    ) -> Optional[PhotoDB]:
        """
        审核照片

        Args:
            photo_id: 照片 ID
            moderator_id: 审核员 ID
            status: 审核状态 (approved/rejected)
            reason: 审核原因

        Returns:
            PhotoDB: 更新后的照片记录
        """
        photo = self.get_photo(photo_id)
        if not photo:
            return None

        if status not in [self.STATUS_APPROVED, self.STATUS_REJECTED]:
            raise ValueError(f"无效的审核状态：{status}")

        photo.moderation_status = status
        photo.moderation_reason = reason
        photo.moderated_by = moderator_id
        photo.moderated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(photo)

        # P20 增强：照片审核通过后失效用户缓存（因为头像可能变了）
        if status == self.STATUS_APPROVED:
            cache_manager.get_instance().invalidate_on_profile_update(photo.user_id)

        return photo

    def ai_moderate_photo(
        self,
        photo_id: str,
        is_safe: bool,
        ai_tags: Optional[List[str]] = None,
        quality_score: Optional[float] = None
    ) -> Optional[PhotoDB]:
        """
        AI 自动审核照片

        Args:
            photo_id: 照片 ID
            is_safe: 是否安全
            ai_tags: AI 分析标签
            quality_score: 质量评分

        Returns:
            PhotoDB: 更新后的照片记录
        """
        photo = self.get_photo(photo_id)
        if not photo:
            return None

        # 更新 AI 分析结果
        if ai_tags:
            photo.ai_tags = json.dumps(ai_tags)
        if quality_score is not None:
            photo.ai_quality_score = quality_score

        # AI 审核结果
        if is_safe:
            photo.moderation_status = self.STATUS_APPROVED
        else:
            photo.moderation_status = self.STATUS_REJECTED
            photo.moderation_reason = "AI 检测到不适当内容"

        photo.moderated_by = "ai"
        photo.moderated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(photo)

        return photo

    def verify_photo_pose(
        self,
        photo_id: str,
        user_id: str,
        pose: str,
        is_match: bool
    ) -> Optional[PhotoDB]:
        """
        验证照片姿势 (真人验证)

        Args:
            photo_id: 照片 ID
            user_id: 用户 ID
            pose: 验证姿势
            is_match: 是否匹配

        Returns:
            PhotoDB: 更新后的照片记录
        """
        photo = self.get_photo(photo_id)
        if not photo or photo.user_id != user_id:
            return None

        if is_match:
            photo.is_verified = True
            photo.verification_pose = pose
            photo.moderation_status = self.STATUS_APPROVED
        else:
            photo.is_verified = False
            photo.moderation_status = self.STATUS_REJECTED
            photo.moderation_reason = "姿势验证不匹配"

        self.db.commit()
        self.db.refresh(photo)

        return photo

    def get_verified_photos_count(self, user_id: str) -> int:
        """获取用户已验证照片数量"""
        return self.db.query(PhotoDB).filter(
            and_(
                PhotoDB.user_id == user_id,
                PhotoDB.is_verified == True,
                PhotoDB.is_active == True
            )
        ).count()

    def get_avatar_url(self, user_id: str) -> Optional[str]:
        """获取用户头像 URL"""
        avatar = self.db.query(PhotoDB).filter(
            and_(
                PhotoDB.user_id == user_id,
                PhotoDB.photo_type == "avatar",
                PhotoDB.moderation_status == self.STATUS_APPROVED,
                PhotoDB.is_active == True
            )
        ).order_by(PhotoDB.display_order).first()

        if avatar:
            return avatar.photo_url

        # 如果没有头像，返回第一张审核通过的照片
        first_photo = self.db.query(PhotoDB).filter(
            and_(
                PhotoDB.user_id == user_id,
                PhotoDB.moderation_status == self.STATUS_APPROVED,
                PhotoDB.is_active == True
            )
        ).order_by(PhotoDB.display_order).first()

        return first_photo.photo_url if first_photo else None

    def increment_view_count(self, photo_id: str) -> bool:
        """增加照片查看次数"""
        photo = self.get_photo(photo_id)
        if photo:
            photo.view_count += 1
            self.db.commit()
            return True
        return False

    def increment_like_count(self, photo_id: str) -> bool:
        """增加照片点赞次数"""
        photo = self.get_photo(photo_id)
        if photo:
            photo.like_count += 1
            self.db.commit()
            return True
        return False
