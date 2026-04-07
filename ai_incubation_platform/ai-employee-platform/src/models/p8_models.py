"""
P8 阶段数据模型 - 企业数据分析与绩效管理

模型列表:
1. EnterpriseDashboard - 企业数据看板
2. PerformanceReview - 绩效评估
3. Department - 企业部门/组织架构
4. WebhookSubscription - Webhook 订阅
5. ExportReport - 导出报告
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== 枚举类型 ====================

class ReportType(str, Enum):
    """报告类型"""
    PERFORMANCE = "performance"  # 绩效报告
    ANALYTICS = "analytics"  # 数据分析报告
    FINANCIAL = "financial"  # 财务报告
    USAGE = "usage"  # 使用量报告


class ReportFormat(str, Enum):
    """报告格式"""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


class WebhookEventType(str, Enum):
    """Webhook 事件类型"""
    ORDER_CREATED = "order.created"
    ORDER_COMPLETED = "order.completed"
    PAYMENT_RECEIVED = "payment.received"
    EMPLOYEE_HIRED = "employee.hired"
    EMPLOYEE_RELEASED = "employee.released"
    DISPUTE_CREATED = "dispute.created"
    DISPUTE_RESOLVED = "dispute.resolved"


class WebhookStatus(str, Enum):
    """Webhook 状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class DepartmentLevel(str, Enum):
    """部门层级"""
    HEADQUARTERS = "headquarters"  # 总部
    DIVISION = "division"  # 事业部
    DEPARTMENT = "department"  # 部门
    TEAM = "team"  # 团队


class PerformanceLevel(str, Enum):
    """绩效等级"""
    S = "S"  # 卓越 (90-100)
    A = "A"  # 优秀 (80-89)
    B = "B"  # 良好 (70-79)
    C = "C"  # 合格 (60-69)
    D = "D"  # 待改进 (<60)


# ==================== 企业数据看板模型 ====================

class DashboardMetrics(BaseModel):
    """看板核心指标"""
    total_employees: int = 0  # AI 员工总数
    active_employees: int = 0  # 活跃员工数
    total_orders: int = 0  # 总订单数
    completed_orders: int = 0  # 已完成订单数
    total_revenue: float = 0.0  # 总收入
    total_cost: float = 0.0  # 总成本
    avg_employee_rating: float = 0.0  # 平均员工评分
    avg_order_completion_time: float = 0.0  # 平均订单完成时间 (小时)
    employee_utilization_rate: float = 0.0  # 员工利用率


class DashboardTrend(BaseModel):
    """趋势数据"""
    date: str  # 日期
    value: float  # 数值
    change_rate: float = 0.0  # 变化率


class DashboardChart(BaseModel):
    """图表数据"""
    chart_type: str  # line, bar, pie
    title: str  # 图表标题
    data: List[Dict[str, Any]]  # 图表数据
    labels: List[str]  # 标签


class EnterpriseDashboard(BaseModel):
    """企业数据看板"""
    tenant_id: str
    user_id: str
    period: str  # today, week, month, quarter, year
    metrics: DashboardMetrics
    trends: Dict[str, List[DashboardTrend]]  # 各指标的趋势数据
    charts: List[DashboardChart]
    top_employees: List[Dict[str, Any]]  # 表现最好的员工
    alerts: List[Dict[str, str]]  # 警告/提醒
    generated_at: datetime = Field(default_factory=datetime.now)


# ==================== 绩效管理模型 ====================

class KPIMetric(BaseModel):
    """KPI 指标"""
    metric_id: str
    metric_name: str  # 指标名称
    target_value: float  # 目标值
    actual_value: float  # 实际值
    weight: float = 1.0  # 权重
    score: float = 0.0  # 得分
    trend: str = "stable"  # upward, downward, stable


class PerformanceReview(BaseModel):
    """绩效评估"""
    id: str
    employee_id: str
    employee_name: str
    reviewer_id: str
    tenant_id: str
    review_period: str  # 2024-Q1, 2024-01
    kpi_metrics: List[KPIMetric]
    overall_score: float = 0.0
    performance_level: PerformanceLevel = PerformanceLevel.C
    strengths: List[str] = []  # 优势
    areas_for_improvement: List[str] = []  # 待改进领域
    comments: Optional[str] = None
    status: str = "draft"  # draft, submitted, approved
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class PerformanceHistory(BaseModel):
    """绩效历史"""
    employee_id: str
    reviews: List[PerformanceReview]
    average_score: float
    trend: str  # improving, declining, stable


# ==================== 企业组织架构模型 ====================

class Department(BaseModel):
    """企业部门"""
    id: str
    tenant_id: str
    name: str
    parent_id: Optional[str] = None  # 父部门 ID
    level: DepartmentLevel = DepartmentLevel.DEPARTMENT
    manager_id: Optional[str] = None  # 部门经理 ID
    description: Optional[str] = None
    budget: Optional[float] = None  # 部门预算
    employee_count: int = 0  # 员工数量
    ai_employee_ids: List[str] = []  # AI 员工 ID 列表
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class DepartmentTree(BaseModel):
    """部门树形结构"""
    department: Department
    children: List["DepartmentTree"] = []
    total_ai_employees: int = 0  # 包含子部门的 AI 员工总数


class OrganizationChart(BaseModel):
    """组织架构图"""
    tenant_id: str
    root_departments: List[DepartmentTree]
    total_departments: int
    total_ai_employees: int


# ==================== Webhook 集成模型 ====================

class WebhookSubscription(BaseModel):
    """Webhook 订阅"""
    id: str
    tenant_id: str
    created_by: str
    name: str
    url: str
    events: List[WebhookEventType]
    status: WebhookStatus = WebhookStatus.ACTIVE
    secret: str  # 用于签名验证
    headers: Optional[Dict[str, str]] = None  # 自定义请求头
    retry_policy: Dict[str, Any] = {}  # 重试策略
    last_triggered_at: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class WebhookDelivery(BaseModel):
    """Webhook 投递记录"""
    id: str
    subscription_id: str
    event_type: WebhookEventType
    payload: Dict[str, Any]
    status: str  # pending, success, failed
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    attempts: int = 0
    next_retry_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


class WebhookPayload(BaseModel):
    """Webhook  payloads"""
    event_id: str
    event_type: WebhookEventType
    tenant_id: str
    timestamp: datetime
    data: Dict[str, Any]


# ==================== 数据导出模型 ====================

class ExportRequest(BaseModel):
    """导出请求"""
    report_type: ReportType
    format: ReportFormat = ReportFormat.PDF
    period: str  # 时间范围
    filters: Optional[Dict[str, Any]] = None  # 筛选条件
    include_charts: bool = True  # 是否包含图表
    include_raw_data: bool = False  # 是否包含原始数据


class ExportReport(BaseModel):
    """导出报告"""
    id: str
    tenant_id: str
    requested_by: str
    report_type: ReportType
    format: ReportFormat
    status: str  # pending, processing, completed, failed
    file_url: Optional[str] = None
    file_size: Optional[int] = None  # 字节
    period: str
    filters: Optional[Dict[str, Any]] = None
    progress: float = 0.0  # 进度百分比
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # 文件过期时间


class ReportTemplate(BaseModel):
    """报告模板"""
    id: str
    tenant_id: str
    name: str
    report_type: ReportType
    format: ReportFormat
    template_config: Dict[str, Any]  # 模板配置
    is_default: bool = False
    created_by: str
    created_at: datetime = Field(default_factory=datetime.now)


# ==================== API 请求/响应模型 ====================

class DashboardResponse(BaseModel):
    """看板响应"""
    success: bool
    dashboard: EnterpriseDashboard
    message: str = ""


class PerformanceReviewRequest(BaseModel):
    """绩效评估请求"""
    employee_id: str
    review_period: str
    kpi_metrics: List[Dict[str, Any]]
    comments: Optional[str] = None


class PerformanceReviewResponse(BaseModel):
    """绩效评估响应"""
    success: bool
    review: PerformanceReview
    message: str = ""


class DepartmentRequest(BaseModel):
    """部门创建/更新请求"""
    name: str
    parent_id: Optional[str] = None
    level: DepartmentLevel = DepartmentLevel.DEPARTMENT
    manager_id: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[float] = None


class DepartmentResponse(BaseModel):
    """部门响应"""
    success: bool
    department: Department
    message: str = ""


class WebhookRequest(BaseModel):
    """Webhook 创建请求"""
    name: str
    url: str
    events: List[WebhookEventType]
    headers: Optional[Dict[str, str]] = None


class WebhookResponse(BaseModel):
    """Webhook 响应"""
    success: bool
    subscription: WebhookSubscription
    message: str = ""


class ExportResponse(BaseModel):
    """导出响应"""
    success: bool
    report: ExportReport
    message: str = ""
