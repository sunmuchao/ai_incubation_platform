"""
用户反馈数据模型 - v1.22 用户体验优化

提供用户反馈功能的数据持久化
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.asyncio import AsyncSession
from database import Base


class UserFeedbackDB(Base):
    """用户反馈数据库模型"""
    __tablename__ = "user_feedback"

    id = Column(String(36), primary_key=True, nullable=False)
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")

    # 反馈类型
    feedback_type = Column(String(20), nullable=False, index=True, comment="反馈类型：bug/feature/complaint/compliment/other")
    category = Column(String(50), nullable=True, index=True, comment="反馈分类")

    # 反馈内容
    title = Column(String(100), nullable=False, comment="反馈标题")
    description = Column(Text, nullable=False, comment="反馈详细描述")

    # 附件
    screenshots = Column(String(2000), nullable=True, comment="截图 URLs(JSON 字符串)")
    attachments = Column(String(2000), nullable=True, comment="其他附件 URLs(JSON 字符串)")

    # 联系方式（可选）
    contact_info = Column(String(100), nullable=True, comment="联系方式（邮箱/电话）")

    # 反馈状态
    status = Column(String(20), default='pending', index=True, comment="状态：pending/investigated/resolved/rejected")
    priority = Column(String(10), default='normal', comment="优先级：low/normal/high/critical")

    # 处理信息
    internal_notes = Column(Text, nullable=True, comment="内部备注")
    assigned_to = Column(String(36), nullable=True, comment="处理人 ID")

    # 回复信息
    response = Column(Text, nullable=True, comment="官方回复")
    responded_at = Column(DateTime, nullable=True, comment="回复时间")
    resolved_at = Column(DateTime, nullable=True, comment="解决时间")

    # 用户满意度（可选）
    satisfaction_rating = Column(Integer, nullable=True, comment="满意度评分 1-5")
    satisfaction_comment = Column(String(500), nullable=True, comment="满意度评价")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<UserFeedbackDB(id={self.id}, user_id={self.user_id}, type={self.feedback_type})>"

    def to_dict(self):
        """转换为字典"""
        import json

        screenshots_list = []
        if self.screenshots:
            try:
                screenshots_list = json.loads(self.screenshots)
            except (json.JSONDecodeError, TypeError):
                screenshots_list = self.screenshots.split(',') if self.screenshots else []

        attachments_list = []
        if self.attachments:
            try:
                attachments_list = json.loads(self.attachments)
            except (json.JSONDecodeError, TypeError):
                attachments_list = self.attachments.split(',') if self.attachments else []

        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.feedback_type,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "screenshots": screenshots_list,
            "attachments": attachments_list,
            "contact_info": self.contact_info,
            "status": self.status,
            "priority": self.priority,
            "internal_notes": self.internal_notes,
            "assigned_to": self.assigned_to,
            "response": self.response,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "satisfaction_rating": self.satisfaction_rating,
            "satisfaction_comment": self.satisfaction_comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FeedbackCategoryDB(Base):
    """反馈分类数据库模型（用于预定义分类）"""
    __tablename__ = "feedback_categories"

    id = Column(String(36), primary_key=True, nullable=False)
    category_key = Column(String(50), unique=True, nullable=False, comment="分类键")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    description = Column(String(500), nullable=True, comment="分类描述")

    # 关联反馈类型
    feedback_type = Column(String(20), nullable=False, comment="关联的反馈类型")

    # 排序和状态
    sort_order = Column(Integer, default=0, comment="排序顺序")
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<FeedbackCategoryDB(id={self.id}, category_key={self.category_key})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "category_key": self.category_key,
            "display_name": self.display_name,
            "description": self.description,
            "feedback_type": self.feedback_type,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
