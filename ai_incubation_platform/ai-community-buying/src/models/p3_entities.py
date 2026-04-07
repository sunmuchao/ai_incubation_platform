"""
P3 用户增长与运营工具 - 数据库实体模型

包含：
1. 邀请裂变系统 (Referral System) - 老带新邀请关系链
2. 任务中心 (Task Center) - 新手任务、日常任务、活动任务
3. 会员成长体系 (Membership Growth) - 会员等级、成长值、权益
4. 运营活动模板 (Campaign Templates) - 限时抢购、拼团活动
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum, Boolean, Index, Numeric, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from config.database import Base


# ====================  Enums  ====================

class InviteStatus(enum.Enum):
    """邀请状态"""
    PENDING = "pending"         # 待转化
    REGISTERED = "registered"   # 已注册
    ACTIVATED = "activated"     # 已激活（完成首单）
    REWARDED = "rewarded"       # 已奖励


class TaskType(enum.Enum):
    """任务类型"""
    NEWBIE = "newbie"           # 新手任务
    DAILY = "daily"             # 日常任务
    WEEKLY = "weekly"           # 每周任务
    ACTIVITY = "activity"       # 活动任务
    GROWTH = "growth"           # 成长任务


class TaskStatus(enum.Enum):
    """任务状态"""
    NOT_STARTED = "not_started" # 未开始
    IN_PROGRESS = "in_progress" # 进行中
    COMPLETED = "completed"     # 已完成
    CLAIMED = "claimed"         # 已领取奖励


class TaskRewardType(enum.Enum):
    """任务奖励类型"""
    POINTS = "points"           # 积分
    COUPON = "coupon"           # 优惠券
    CASH = "cash"               # 现金
    GROWTH_VALUE = "growth_value"  # 成长值


class MemberLevel(enum.Enum):
    """会员等级"""
    NORMAL = "normal"           # 普通会员
    SILVER = "silver"           # 白银会员
    GOLD = "gold"               # 黄金会员
    PLATINUM = "platinum"       # 铂金会员
    DIAMOND = "diamond"         # 钻石会员


class LevelRuleType(enum.Enum):
    """等级规则类型"""
    GROWTH_VALUE = "growth_value"  # 成长值
    TOTAL_ORDER = "total_order"    # 累计订单
    TOTAL_AMOUNT = "total_amount"  # 累计金额


class CampaignType(enum.Enum):
    """活动类型"""
    FLASH_SALE = "flash_sale"   # 限时抢购
    GROUP_BUY = "group_buy"     # 拼团活动
    COUPON_RAIN = "coupon_rain" # 优惠券雨
    NEW_USER_SPECIAL = "new_user_special"  # 新人专享


class CampaignStatus(enum.Enum):
    """活动状态"""
    DRAFT = "draft"             # 草稿
    SCHEDULED = "scheduled"     # 已排期
    ACTIVE = "active"           # 进行中
    ENDED = "ended"             # 已结束
    CANCELLED = "cancelled"     # 已取消


# ====================  邀请裂变系统  ====================

class InviteRelationEntity(Base):
    """邀请关系实体 - 记录用户邀请关系链"""
    __tablename__ = "invite_relations"

    id = Column(String(64), primary_key=True)
    inviter_id = Column(String(64), nullable=False, index=True)  # 邀请人 ID
    invitee_id = Column(String(64), nullable=False, unique=True, index=True)  # 被邀请人 ID
    invite_code = Column(String(32), nullable=False, index=True)  # 邀请码

    # 邀请状态
    status = Column(Enum(InviteStatus), default=InviteStatus.PENDING)

    # 奖励信息
    inviter_reward = Column(Numeric(10, 2), default=0)  # 邀请人奖励金额
    invitee_reward = Column(Numeric(10, 2), default=0)  # 被邀请人奖励金额

    # 转化信息
    first_order_id = Column(String(64))  # 首单 ID（激活条件）
    first_order_amount = Column(Numeric(10, 2))  # 首单金额

    # 时间信息
    registered_at = Column(DateTime)  # 注册时间
    activated_at = Column(DateTime)  # 激活时间（完成首单）
    rewarded_at = Column(DateTime)  # 奖励时间

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_inviter_status", "inviter_id", "status"),
    )


class InviteRewardRuleEntity(Base):
    """邀请奖励规则实体"""
    __tablename__ = "invite_reward_rules"

    id = Column(String(64), primary_key=True)
    rule_name = Column(String(64), nullable=False, unique=True)  # 规则名称

    # 奖励配置
    inviter_cash_reward = Column(Numeric(10, 2), default=10)  # 邀请人现金奖励
    invitee_cash_reward = Column(Numeric(10, 2), default=5)   # 被邀请人现金奖励
    inviter_points_reward = Column(Integer, default=100)      # 邀请人积分奖励
    invitee_points_reward = Column(Integer, default=50)       # 被邀请人积分奖励

    # 激活条件
    min_order_amount = Column(Numeric(10, 2), default=20)  # 首单最低金额
    max_reward_per_day = Column(Numeric(10, 2), default=500)  # 每日奖励上限

    # 状态
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class InviteRecordEntity(Base):
    """邀请记录实体 - 统计邀请数据"""
    __tablename__ = "invite_records"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)  # 用户 ID

    # 统计数据
    total_invites = Column(Integer, default=0)      # 累计邀请人数
    registered_count = Column(Integer, default=0)   # 已注册人数
    activated_count = Column(Integer, default=0)    # 已激活人数
    total_reward = Column(Numeric(12, 2), default=0)  # 累计奖励

    # 周期统计
    today_invites = Column(Integer, default=0)
    week_invites = Column(Integer, default=0)
    month_invites = Column(Integer, default=0)

    # 排名
    ranking = Column(Integer, default=0)  # 排行榜名次

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_user_id", "user_id", unique=True),
    )


# ====================  任务中心  ====================

class TaskDefinitionEntity(Base):
    """任务定义实体 - 任务模板配置"""
    __tablename__ = "task_definitions"

    id = Column(String(64), primary_key=True)
    task_code = Column(String(64), nullable=False, unique=True)  # 任务编码
    task_name = Column(String(128), nullable=False)  # 任务名称
    task_type = Column(Enum(TaskType), nullable=False)  # 任务类型

    # 任务描述
    description = Column(String(256))  # 任务描述
    icon_url = Column(String(256))     # 任务图标

    # 任务目标
    target_type = Column(String(32), nullable=False)  # 目标类型（order_count/view_count/share_count 等）
    target_value = Column(Integer, nullable=False)   # 目标值

    # 任务奖励
    reward_type = Column(Enum(TaskRewardType), nullable=False)
    reward_value = Column(Integer, nullable=False)   # 奖励数值
    reward_extra = Column(String(256))               # 额外奖励信息（JSON）

    # 任务限制
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    max_participants = Column(Integer, default=0)    # 最大参与人数（0 表示不限）
    user_limit = Column(Integer, default=1)          # 每人限完成次数（0 表示不限）

    # 状态
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class UserTaskEntity(Base):
    """用户任务实体 - 用户任务进度追踪"""
    __tablename__ = "user_tasks"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), ForeignKey("task_definitions.id"), nullable=False)

    # 任务状态
    status = Column(Enum(TaskStatus), default=TaskStatus.NOT_STARTED)

    # 任务进度
    current_value = Column(Integer, default=0)  # 当前进度值
    target_value = Column(Integer, nullable=False)  # 目标值

    # 奖励信息
    reward_claimed = Column(Boolean, default=False)  # 奖励是否已领取
    reward_claimed_at = Column(DateTime)

    # 时间信息
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_user_task_unique", "user_id", "task_id", unique=True),
        Index("idx_user_task_status", "user_id", "status"),
    )


class TaskProgressLogEntity(Base):
    """任务进度日志实体 - 记录任务进度变更"""
    __tablename__ = "task_progress_logs"

    id = Column(String(64), primary_key=True)
    user_task_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)

    # 进度变更
    old_value = Column(Integer, default=0)
    new_value = Column(Integer, nullable=False)
    increment = Column(Integer, default=0)

    # 变更原因
    action_type = Column(String(32), nullable=False)  # 触发行动类型
    action_id = Column(String(64))  # 关联行动 ID（如订单 ID）

    remark = Column(String(256))

    created_at = Column(DateTime, default=datetime.now, index=True)


# ====================  会员成长体系  ====================

class MemberProfileEntity(Base):
    """会员档案实体 - 用户会员信息"""
    __tablename__ = "member_profiles"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, unique=True, index=True)

    # 会员等级
    current_level = Column(Enum(MemberLevel), default=MemberLevel.NORMAL)
    next_level = Column(Enum(MemberLevel))  # 下一等级

    # 成长值
    growth_value = Column(Integer, default=0)  # 当前成长值
    total_growth_value = Column(Integer, default=0)  # 累计成长值
    growth_value_history = Column(Integer, default=0)  # 历史成长值（用于降级计算）

    # 会员统计
    total_orders = Column(Integer, default=0)      # 累计订单数
    total_amount = Column(Numeric(14, 2), default=0)  # 累计消费金额
    member_days = Column(Integer, default=0)       # 会员天数

    # 会员权益
    benefits = Column(String(512))  # 当前享有的权益（JSON 字符串）

    # 等级变更
    last_level_up_at = Column(DateTime)
    last_level_down_at = Column(DateTime)
    next_review_at = Column(DateTime)  # 下次等级审核时间

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class MemberLevelConfigEntity(Base):
    """会员等级配置实体"""
    __tablename__ = "member_level_configs"

    id = Column(String(64), primary_key=True)
    level = Column(Enum(MemberLevel), nullable=False, unique=True)
    level_name = Column(String(32), nullable=False)  # 等级名称

    # 升级条件
    min_growth_value = Column(Integer, default=0)  # 最低成长值要求
    min_total_orders = Column(Integer, default=0)  # 最低订单数要求
    min_total_amount = Column(Numeric(14, 2), default=0)  # 最低消费金额要求

    # 会员权益
    benefits = Column(Text)  # 权益描述（JSON 字符串）
    benefit_codes = Column(String(256))  # 权益编码列表（逗号分隔）

    # 保级条件
    min_maintain_growth_value = Column(Integer)  # 保级最低成长值
    review_period_days = Column(Integer, default=90)  # 等级审核周期（天）

    # 状态
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class GrowthValueLogEntity(Base):
    """成长值流水实体"""
    __tablename__ = "growth_value_logs"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)

    # 成长值变更
    change_value = Column(Integer, nullable=False)  # 变更值（正数增加，负数减少）
    value_before = Column(Integer, default=0)  # 变更前成长值
    value_after = Column(Integer, nullable=False)  # 变更后成长值

    # 变更原因
    action_type = Column(String(32), nullable=False)  # 订单完成/签到/评价等
    action_id = Column(String(64))  # 关联行动 ID

    remark = Column(String(256))

    created_at = Column(DateTime, default=datetime.now, index=True)


class MemberBenefitEntity(Base):
    """会员权益实体 - 权益使用记录"""
    __tablename__ = "member_benefits"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    level = Column(Enum(MemberLevel), nullable=False)  # 权益等级

    # 权益信息
    benefit_code = Column(String(32), nullable=False)  # 权益编码
    benefit_name = Column(String(128), nullable=False)  # 权益名称
    benefit_value = Column(String(256))  # 权益值（如优惠券 ID、折扣率等）

    # 使用状态
    status = Column(String(32), default="available")  # available/used/expired
    used_at = Column(DateTime)
    expires_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_user_benefit", "user_id", "status"),
    )


# ====================  运营活动模板  ====================

class CampaignTemplateEntity(Base):
    """运营活动模板实体"""
    __tablename__ = "campaign_templates"

    id = Column(String(64), primary_key=True)
    template_name = Column(String(128), nullable=False)  # 模板名称
    campaign_type = Column(Enum(CampaignType), nullable=False)  # 活动类型

    # 活动配置
    config = Column(Text, nullable=False)  # 活动配置（JSON 字符串）
    rules = Column(Text)  # 活动规则（JSON 字符串）

    # 模板元数据
    thumbnail = Column(String(256))  # 缩略图
    description = Column(String(512))  # 模板描述
    tags = Column(String(256))  # 标签列表（逗号分隔）

    # 状态
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)  # 使用次数

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CampaignInstanceEntity(Base):
    """运营活动实例实体 - 基于模板创建的具体活动"""
    __tablename__ = "campaign_instances"

    id = Column(String(64), primary_key=True)
    campaign_no = Column(String(32), nullable=False, unique=True)  # 活动编号
    template_id = Column(String(64), ForeignKey("campaign_templates.id"))  # 模板 ID

    # 活动信息
    campaign_name = Column(String(128), nullable=False)  # 活动名称
    campaign_type = Column(Enum(CampaignType), nullable=False)  # 活动类型

    # 活动时间
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # 活动状态
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT)

    # 活动配置（从模板复制，可覆盖）
    config = Column(Text, nullable=False)
    rules = Column(Text)

    # 活动数据
    participant_count = Column(Integer, default=0)  # 参与人数
    order_count = Column(Integer, default=0)  # 订单数
    gmv = Column(Numeric(14, 2), default=0)  # GMV

    # 创建信息
    creator_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CampaignParticipantEntity(Base):
    """活动参与者实体"""
    __tablename__ = "campaign_participants"

    id = Column(String(64), primary_key=True)
    campaign_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)

    # 参与信息
    participated_at = Column(DateTime, default=datetime.now)
    order_id = Column(String(64))  # 关联订单 ID

    # 奖励信息
    reward_type = Column(String(32))  # 奖励类型
    reward_value = Column(String(64))  # 奖励值
    reward_status = Column(String(32), default="pending")  # pending/granted/used

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_campaign_user", "campaign_id", "user_id", unique=True),
    )


# ====================  关联关系  ====================

# TaskDefinition 与 UserTask 一对多
TaskDefinitionEntity.user_tasks = relationship(
    "UserTaskEntity",
    back_populates="task",
    foreign_keys="UserTaskEntity.task_id",
    primaryjoin="TaskDefinitionEntity.id == UserTaskEntity.task_id"
)

# 为 UserTask 添加反向关联
UserTaskEntity.task = relationship(
    "TaskDefinitionEntity",
    back_populates="user_tasks",
    foreign_keys=[UserTaskEntity.task_id],
    primaryjoin="TaskDefinitionEntity.id == UserTaskEntity.task_id"
)

# CampaignTemplate 与 CampaignInstance 一对多
CampaignTemplateEntity.instances = relationship(
    "CampaignInstanceEntity",
    back_populates="template",
    foreign_keys="CampaignInstanceEntity.template_id",
    primaryjoin="CampaignTemplateEntity.id == CampaignInstanceEntity.template_id"
)

# 为 CampaignInstance 添加反向关联
CampaignInstanceEntity.template = relationship(
    "CampaignTemplateEntity",
    back_populates="instances",
    foreign_keys=[CampaignInstanceEntity.template_id],
    primaryjoin="CampaignTemplateEntity.id == CampaignInstanceEntity.template_id"
)
