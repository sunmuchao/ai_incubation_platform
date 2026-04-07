"""
用户新手引导数据模型 - v1.22 用户体验优化

提供新手引导流程的数据持久化
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, DECIMAL
from sqlalchemy.ext.asyncio import AsyncSession
from database import Base


class UserOnboardingProgressDB(Base):
    """用户新手引导进度数据库模型"""
    __tablename__ = "user_onboarding_progress"

    id = Column(String(36), primary_key=True, nullable=False)
    user_id = Column(String(36), nullable=False, index=True, unique=True, comment="用户 ID")

    # 整体进度
    overall_progress = Column(DECIMAL(5, 2), default=0.00, comment="整体进度百分比 0-100")
    onboarding_status = Column(String(20), default='not_started', index=True,
                               comment="引导状态：not_started/in_progress/completed/skipped")

    # 各步骤完成情况（核心步骤）
    step_profile_complete = Column(Boolean, default=False, comment="步骤 1：完善个人资料")
    step_verification_complete = Column(Boolean, default=False, comment="步骤 2：身份/技能认证")
    step_first_task_published = Column(Boolean, default=False, comment="步骤 3：发布首个任务")
    step_first_task_accepted = Column(Boolean, default=False, comment="步骤 3.5：任务被接受")
    step_first_task_completed = Column(Boolean, default=False, comment="步骤 4：完成首个任务（作为工人）")
    step_payment_setup_complete = Column(Boolean, default=False, comment="步骤 5：设置支付方式")
    step_capability_graph_complete = Column(Boolean, default=False, comment="步骤 6：定义 AI 能力缺口")

    # 扩展步骤（可选）
    step_team_created = Column(Boolean, default=False, comment="扩展：创建团队")
    step_api_integration = Column(Boolean, default=False, comment="扩展：API 集成")
    step_social_connection = Column(Boolean, default=False, comment="扩展：社交连接")

    # 时间追踪
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    skipped_at = Column(DateTime, nullable=True, comment="跳过时间")
    last_active_at = Column(DateTime, nullable=True, comment="最后活跃时间")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<UserOnboardingProgressDB(id={self.id}, user_id={self.user_id}, status={self.onboarding_status})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "overall_progress": float(self.overall_progress) if self.overall_progress else 0.0,
            "onboarding_status": self.onboarding_status,
            "steps": {
                "profile_complete": self.step_profile_complete,
                "verification_complete": self.step_verification_complete,
                "first_task_published": self.step_first_task_published,
                "first_task_accepted": self.step_first_task_accepted,
                "first_task_completed": self.step_first_task_completed,
                "payment_setup_complete": self.step_payment_setup_complete,
                "capability_graph_complete": self.step_capability_graph_complete,
                "team_created": self.step_team_created,
                "api_integration": self.step_api_integration,
                "social_connection": self.step_social_connection,
            },
            "timeline": {
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "skipped_at": self.skipped_at.isoformat() if self.skipped_at else None,
                "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OnboardingStepDefinitionDB(Base):
    """新手引导步骤定义数据库模型"""
    __tablename__ = "onboarding_step_definitions"

    id = Column(String(36), primary_key=True, nullable=False)
    step_key = Column(String(50), unique=True, nullable=False, comment="步骤键")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    description = Column(String(500), nullable=True, comment="步骤描述")

    # 步骤类型
    step_type = Column(String(20), nullable=False, comment="步骤类型：profile/verification/task/payment/graph/other")

    # 引导内容
    title = Column(String(100), nullable=False, comment="引导标题")
    guide_content = Column(String(2000), nullable=True, comment="引导内容（支持 Markdown）")
    tutorial_url = Column(String(500), nullable=True, comment="教程 URL")
    video_url = Column(String(500), nullable=True, comment="视频教程 URL")

    # 完成条件
    completion_condition = Column(String(200), nullable=True, comment="完成条件表达式")

    # 奖励
    reward_points = Column(Integer, default=0, comment="完成奖励积分")
    reward_badge = Column(String(50), nullable=True, comment="完成奖励徽章")

    # 排序和依赖
    sort_order = Column(Integer, default=0, comment="排序顺序")
    prerequisites = Column(String(500), nullable=True, comment="前置步骤（JSON 数组）")

    # 状态
    is_required = Column(Boolean, default=True, comment="是否必填")
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<OnboardingStepDefinitionDB(id={self.id}, step_key={self.step_key})>"

    def to_dict(self):
        """转换为字典"""
        import json

        prerequisites_list = []
        if self.prerequisites:
            try:
                prerequisites_list = json.loads(self.prerequisites)
            except (json.JSONDecodeError, TypeError):
                prerequisites_list = self.prerequisites.split(',') if self.prerequisites else []

        return {
            "id": self.id,
            "step_key": self.step_key,
            "display_name": self.display_name,
            "description": self.description,
            "step_type": self.step_type,
            "title": self.title,
            "guide_content": self.guide_content,
            "tutorial_url": self.tutorial_url,
            "video_url": self.video_url,
            "completion_condition": self.completion_condition,
            "reward": {
                "points": self.reward_points,
                "badge": self.reward_badge,
            },
            "sort_order": self.sort_order,
            "prerequisites": prerequisites_list,
            "is_required": self.is_required,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserBehaviorNudgeDB(Base):
    """用户行为引导数据库模型"""
    __tablename__ = "user_behavior_nudges"

    id = Column(String(36), primary_key=True, nullable=False)
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")

    # 引导类型
    nudge_type = Column(String(50), nullable=False, index=True, comment="引导类型")
    nudge_title = Column(String(200), nullable=False, comment="引导标题")
    nudge_content = Column(String(1000), nullable=False, comment="引导内容")

    # 引导上下文
    nudge_context = Column(String(2000), nullable=True, comment="引导上下文（JSON）")

    # 展示控制
    display_count = Column(Integer, default=0, comment="已展示次数")
    max_display_count = Column(Integer, default=3, comment="最大展示次数")
    is_dismissed = Column(Boolean, default=False, index=True, comment="用户是否已关闭")
    is_completed = Column(Boolean, default=False, index=True, comment="用户是否已完成引导行为")

    # 动作
    action_url = Column(String(500), nullable=True, comment="点击跳转 URL")
    action_button_text = Column(String(50), default='知道了', comment="动作按钮文本")

    # 时间控制
    dismissed_at = Column(DateTime, nullable=True, comment="关闭时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    expires_at = Column(DateTime, nullable=True, index=True, comment="过期时间")

    # 优先级
    priority = Column(Integer, default=0, comment="优先级（数字越大优先级越高）")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<UserBehaviorNudgeDB(id={self.id}, user_id={self.user_id}, type={self.nudge_type})>"

    def to_dict(self):
        """转换为字典"""
        import json

        context_dict = {}
        if self.nudge_context:
            try:
                context_dict = json.loads(self.nudge_context)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": self.id,
            "user_id": self.user_id,
            "nudge_type": self.nudge_type,
            "title": self.nudge_title,
            "content": self.nudge_content,
            "context": context_dict,
            "display_count": self.display_count,
            "max_display_count": self.max_display_count,
            "is_dismissed": self.is_dismissed,
            "is_completed": self.is_completed,
            "action": {
                "url": self.action_url,
                "button_text": self.action_button_text,
            } if self.action_url else None,
            "priority": self.priority,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
