"""
AI 员工模型
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
from enum import Enum
import hashlib
import jwt
from jwt import PyJWTError


class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillCategory(str, Enum):
    """技能分类 - 标准化技能体系"""
    TECHNICAL = "technical"  # 技术类：编程、数据分析等
    DESIGN = "design"  # 设计类：UI/UX、平面设计等
    WRITING = "writing"  # 写作类：文案、翻译、内容创作等
    MARKETING = "marketing"  # 营销类：SEO、社交媒体、广告等
    BUSINESS = "business"  # 商务类：咨询、财务、法务等
    SUPPORT = "support"  # 支持类：客服、虚拟助理等
    AI_SPECIALIZED = "ai_specialized"  # AI 专用：prompt 工程、模型调优等


class ReviewType(str, Enum):
    """评价类型"""
    HIRER_TO_EMPLOYEE = "hirer_to_employee"  # 租赁者评员工
    OWNER_TO_HIRER = "owner_to_hirer"  # 所有者评租赁者


class EmployerStatus(str, Enum):
    """雇主状态"""
    ACTIVE = "active"  # 活跃
    OFFLINE = "offline"  # 离线
    SUSPENDED = "suspended"  # 暂停
    VERIFIED = "verified"  # 已认证


class EmployeeStatus(str, Enum):
    AVAILABLE = "available"
    HIRED = "hired"
    TRAINING = "training"
    OFFLINE = "offline"


class TrainingDataType(str, Enum):
    """训练数据类型"""
    PROMPT = "prompt"  # 提示词模板
    KNOWLEDGE = "knowledge"  # 知识库文件
    EXAMPLE = "example"  # 示例对话
    FINE_TUNE = "fine_tune"  # 微调数据集
    TOOL_CONFIG = "tool_config"  # 工具配置


class TrainingStatus(str, Enum):
    """训练任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中风险
    HIGH = "high"  # 高风险
    BLOCKED = "blocked"  # 已封禁


class TenantStatus(str, Enum):
    """租户状态"""
    ACTIVE = "active"  # 活跃
    SUSPENDED = "suspended"  # 已暂停
    CANCELLED = "cancelled"  # 已注销
    TRIAL = "trial"  # 试用中


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"  # 租户管理员
    OWNER = "owner"  # AI员工所有者
    HIRER = "hirer"  # 租赁者
    FINANCE = "finance"  # 财务人员


class BillingCycle(str, Enum):
    """账单周期"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class InvoiceStatus(str, Enum):
    """发票状态"""
    DRAFT = "draft"  # 草稿
    ISSUED = "issued"  # 已开具
    PAID = "paid"  # 已支付
    OVERDUE = "overdue"  # 逾期
    CANCELLED = "cancelled"  # 已作废


class PaymentStatus(str, Enum):
    """支付状态"""
    PENDING = "pending"  # 待支付
    PROCESSING = "processing"  # 处理中
    SUCCESS = "success"  # 支付成功
    FAILED = "failed"  # 支付失败
    REFUNDED = "refunded"  # 已退款


class PaymentMethod(str, Enum):
    """支付方式"""
    ALIPAY = "alipay"  # 支付宝
    WECHAT = "wechat"  # 微信支付
    CREDIT_CARD = "credit_card"  # 信用卡
    BANK_TRANSFER = "bank_transfer"  # 银行转账
    BALANCE = "balance"  # 余额支付


class AIEmployee(BaseModel):
    """AI 员工模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # 所属租户ID
    name: str
    owner_id: str
    avatar: Optional[str] = None
    description: str

    # 技能列表
    skills: Dict[str, SkillLevel] = Field(default_factory=dict)

    # 状态
    status: EmployeeStatus = EmployeeStatus.AVAILABLE

    # 定价（每小时）
    hourly_rate: float = 10.0

    # 统计数据
    total_jobs: int = 0
    total_earnings: float = 0.0
    rating: float = 5.0
    review_count: int = 0

    # 训练数据与版本化
    current_training_version: Optional[str] = None  # 当前使用的训练数据版本
    training_versions: List[str] = Field(default_factory=list)  # 所有训练版本ID列表
    agent_config: Dict[str, Any] = Field(default_factory=dict)  # Agent运行时配置
    deerflow_agent_id: Optional[str] = None  # DeerFlow Agent实例ID

    # 评级与风控
    risk_level: RiskLevel = RiskLevel.LOW  # 风险等级
    risk_score: float = 0.0  # 风险评分，0-100，越高越危险
    violation_count: int = 0  # 违规次数
    last_risk_check: Optional[datetime] = None  # 上次风险检查时间
    is_verified: bool = False  # 是否通过平台认证

    # 创建时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TrainingDataVersion(BaseModel):
    """训练数据版本"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    version: str  # 语义化版本号，如 v1.0.0
    data_type: TrainingDataType
    data_hash: str  # 数据内容哈希，用于校验
    data_path: str  # 数据存储路径
    description: str  # 版本描述
    created_by: str  # 创建者ID
    created_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def calculate_hash(cls, content: str) -> str:
        """计算数据内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()


class TrainingTask(BaseModel):
    """训练任务"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    version_id: str  # 关联的训练数据版本ID
    status: TrainingStatus = TrainingStatus.PENDING
    deerflow_task_id: Optional[str] = None  # DeerFlow训练任务ID
    model_version: Optional[str] = None  # 训练后的模型版本
    # 注意：metrics 不能使用可变默认值 dict，否则会跨实例共享
    metrics: Dict[str, float] = Field(default_factory=dict)  # 训练指标（准确率、损失等）
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AIEmployeeCreate(BaseModel):
    """创建 AI 员工请求"""
    tenant_id: str  # 所属租户ID
    name: str
    description: str
    # 注意：不能使用可变默认值 dict，否则多次实例化会共享同一个 dict
    skills: Dict[str, SkillLevel] = Field(default_factory=dict)
    # P0: 最小计费与定价字段应为正数，避免出现负/零价格导致的计费异常
    hourly_rate: float = Field(gt=0, default=10.0)
    agent_config: Dict[str, Any] = Field(default_factory=dict)  # Agent运行时配置


class RentalRequest(BaseModel):
    """租赁请求"""
    employee_id: str
    hirer_id: str
    # P0: 计费与最小定价字段需要保证订单时长为正数
    duration_hours: int = Field(gt=0)
    # P0: 任务描述不能为空，作为订单/风控/审计的最小可用信息
    task_description: str = Field(min_length=1)


class TrainingDataUploadRequest(BaseModel):
    """训练数据上传请求"""
    data_type: TrainingDataType
    # P1: 训练数据内容/路径必须非空，避免生成空哈希与不可用版本
    content: str = Field(min_length=1)  # 数据内容或文件路径
    description: str
    version: str  # 版本号，如 v1.0.0


class TrainingStartRequest(BaseModel):
    """开始训练请求"""
    version_id: str
    training_config: Dict[str, Any] = Field(default_factory=dict)


class ReviewSubmitRequest(BaseModel):
    """提交评价请求"""
    rating: float = Field(ge=1, le=5)
    review: Optional[str] = None
    review_tags: List[str] = Field(default_factory=list)


# ======================================
# P2 新增模型：多租户、认证、账单、支付
# ======================================

class Tenant(BaseModel):
    """租户模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # 租户名称
    contact_name: str  # 联系人姓名
    contact_email: EmailStr  # 联系人邮箱
    contact_phone: Optional[str] = None
    status: TenantStatus = TenantStatus.TRIAL
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    max_employees: int = 10  # 最大可创建AI员工数量
    max_concurrent_jobs: int = 5  # 最大并发任务数
    storage_quota_gb: int = 10  # 存储配额（GB）
    used_storage_gb: float = 0.0  # 已使用存储
    trial_end_at: Optional[datetime] = None  # 试用期结束时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 扩展字段


class User(BaseModel):
    """用户模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # 所属租户ID
    username: str
    email: EmailStr
    hashed_password: str
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    role: UserRole = UserRole.HIRER
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        exclude = ["hashed_password"]


class UsageRecord(BaseModel):
    """用量记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    user_id: str
    resource_type: str  # 资源类型：employee_rental, storage, training, api_call
    resource_id: Optional[str] = None  # 关联资源ID
    quantity: float  # 使用量
    unit: str  # 单位：hours, gb, count
    unit_price: float  # 单价
    total_amount: float  # 总费用
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


class Invoice(BaseModel):
    """账单发票"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    invoice_number: str  # 发票编号
    period_start: datetime  # 账单周期开始
    period_end: datetime  # 账单周期结束
    total_amount: float  # 总金额
    paid_amount: float = 0.0  # 已支付金额
    due_date: datetime  # 到期日
    status: InvoiceStatus = InvoiceStatus.DRAFT
    items: List[Dict[str, Any]] = Field(default_factory=list)  # 账单明细
    payment_status: PaymentStatus = PaymentStatus.PENDING
    issued_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PaymentTransaction(BaseModel):
    """支付交易记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    user_id: str
    invoice_id: Optional[str] = None  # 关联发票ID
    order_id: Optional[str] = None  # 关联订单ID
    amount: float
    currency: str = "CNY"
    payment_method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    third_party_transaction_id: Optional[str] = None  # 第三方支付交易号
    payment_data: Dict[str, Any] = Field(default_factory=dict)  # 支付相关数据
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Wallet(BaseModel):
    """租户钱包"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    balance: float = 0.0  # 可用余额
    frozen_balance: float = 0.0  # 冻结余额
    total_recharge: float = 0.0  # 累计充值
    total_consumption: float = 0.0  # 累计消费
    currency: str = "CNY"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# 请求模型
class TenantCreateRequest(BaseModel):
    """创建租户请求"""
    name: str
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    billing_cycle: BillingCycle = BillingCycle.MONTHLY


class UserCreateRequest(BaseModel):
    """创建用户请求"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.HIRER


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class PaymentRequest(BaseModel):
    """支付请求"""
    amount: float
    payment_method: PaymentMethod
    order_id: Optional[str] = None
    invoice_id: Optional[str] = None
    return_url: Optional[str] = None


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"       # 待确认
    CONFIRMED = "confirmed"   # 已确认
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消
    REFUNDED = "refunded"     # 已退款


class Order(BaseModel):
    """订单模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str  # 所属租户ID
    employee_id: str
    owner_id: str  # 员工所有者ID
    hirer_id: str  # 租赁者ID
    duration_hours: int
    task_description: str

    # 计费信息
    hourly_rate: float
    total_amount: float
    platform_fee_rate: float = 0.1  # 平台费率10%
    platform_fee: float
    owner_earning: float

    # 状态
    status: OrderStatus = OrderStatus.PENDING

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now)
    confirmed_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # 评价信息
    rating: Optional[float] = Field(None, ge=1, le=5)  # 评分1-5星
    review: Optional[str] = None
    review_tags: List[str] = Field(default_factory=list)  # 评价标签
    review_likes: int = 0  # 评价点赞数
    is_review_hidden: bool = False  # 是否隐藏评价

    # 风控信息
    risk_check_passed: bool = True  # 是否通过风险检查
    risk_factors: List[str] = Field(default_factory=list)  # 风险因素列表


# ======================================
# P3 新增模型：双向评价、雇主档案、技能体系
# ======================================

class ReviewDimension(BaseModel):
    """评价维度评分"""
    communication: float = Field(ge=0, le=5, default=5.0)  # 沟通能力
    quality: float = Field(ge=0, le=5, default=5.0)  # 工作质量
    timeliness: float = Field(ge=0, le=5, default=5.0)  # 时效性
    professionalism: float = Field(ge=0, le=5, default=5.0)  # 专业度


class Review(BaseModel):
    """双向评价模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    order_id: str
    employee_id: str
    reviewer_id: str  # 评价者 ID
    reviewee_id: str  # 被评价者 ID（员工所有者或租赁者）
    review_type: ReviewType
    rating: float = Field(ge=1, le=5)  # 总体评分
    review_text: Optional[str] = None
    review_tags: List[str] = Field(default_factory=list)
    # 维度评分
    dimensions: Optional[ReviewDimension] = None
    # 可见性
    is_public: bool = True  # 是否公开显示
    is_hidden: bool = False  # 是否被隐藏（违规）
    # 互动
    likes: int = 0
    response: Optional[str] = None  # 被评价者回复
    response_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class EmployerProfile(BaseModel):
    """雇主（租赁者）档案模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    user_id: str  # 关联的用户 ID
    company_name: Optional[str] = None  # 公司名称
    industry: Optional[str] = None  # 所属行业
    company_size: Optional[str] = None  # 公司规模
    description: Optional[str] = None  # 公司介绍
    # 统计数据
    total_hires: int = 0  # 总雇佣次数
    total_spent: float = 0.0  # 总消费金额
    active_jobs: int = 0  # 活跃职位数
    # 评价相关
    rating: float = 5.0  # 平均评分
    review_count: int = 0
    # 行为指标
    avg_response_time_hours: Optional[float] = None  # 平均响应时间（小时）
    rehire_rate: float = 0.0  # 复雇率
    # 状态
    status: EmployerStatus = EmployerStatus.ACTIVE
    is_verified: bool = False  # 是否通过平台认证
    verification_badges: List[str] = Field(default_factory=list)  # 认证标识
    # 风控
    risk_score: float = 0.0
    violation_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SkillTag(BaseModel):
    """标准化技能标签"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # 技能名称
    category: SkillCategory  # 所属分类
    parent_skill_id: Optional[str] = None  # 父技能 ID（用于技能树）
    description: Optional[str] = None
    # 使用统计
    usage_count: int = 0  # 被使用次数
    avg_hourly_rate: float = 0.0  # 平均时薪
    # 认证要求
    has_certification: bool = False
    certification_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class EmployeeSkill(BaseModel):
    """员工技能关联模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    skill_tag_id: str  # 关联标准化技能标签
    skill_name: str  # 冗余字段，便于查询
    level: SkillLevel
    years_of_experience: Optional[float] = None  # 从业年限
    certified: bool = False  # 是否已认证
    certification_id: Optional[str] = None  # 认证 ID
    portfolio_items: List[str] = Field(default_factory=list)  # 作品链接
    verified_at: Optional[datetime] = None  # 技能验证时间
    created_at: datetime = Field(default_factory=datetime.now)


# ======================================
# P3 请求模型
# ======================================

class ReviewSubmitRequestV2(BaseModel):
    """提交评价请求（增强版）"""
    review_type: ReviewType
    rating: float = Field(ge=1, le=5)
    review_text: Optional[str] = None
    review_tags: List[str] = Field(default_factory=list)
    # 维度评分
    communication: float = Field(ge=0, le=5, default=5.0)
    quality: float = Field(ge=0, le=5, default=5.0)
    timeliness: float = Field(ge=0, le=5, default=5.0)
    professionalism: float = Field(ge=0, le=5, default=5.0)
    is_public: bool = True


class ReviewResponseRequest(BaseModel):
    """回复评价请求"""
    response_text: str = Field(min_length=1, max_length=1000)


class EmployerProfileCreateRequest(BaseModel):
    """创建雇主档案请求"""
    user_id: str
    company_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    description: Optional[str] = None


class EmployerProfileUpdateRequest(BaseModel):
    """更新雇主档案请求"""
    company_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    description: Optional[str] = None


class SkillTagCreateRequest(BaseModel):
    """创建技能标签请求"""
    name: str
    category: SkillCategory
    parent_skill_id: Optional[str] = None
    description: Optional[str] = None
    has_certification: bool = False
    certification_name: Optional[str] = None


class EmployeeSkillAddRequest(BaseModel):
    """添加员工技能请求"""
    skill_tag_id: str
    level: SkillLevel
    years_of_experience: Optional[float] = None
    certified: bool = False
    certification_id: Optional[str] = None
    portfolio_items: List[str] = Field(default_factory=list)
