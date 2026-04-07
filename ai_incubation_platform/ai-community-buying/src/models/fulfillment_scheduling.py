"""
智能履约调度系统 - 数据模型
包含：配送路线、时间窗口、自提点、人流预测等实体
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, time
from enum import Enum
import uuid


class DeliveryStatus(str, Enum):
    """配送状态"""
    PENDING = "pending"           # 待配送
    PLANNED = "planned"           # 已规划路线
    IN_PROGRESS = "in_progress"   # 配送中
    COMPLETED = "completed"       # 配送完成
    FAILED = "failed"             # 配送失败
    EXCEPTION = "exception"       # 异常情况


class PickupPointStatus(str, Enum):
    """自提点状态"""
    ACTIVE = "active"             # 正常运营
    CROWDED = "crowded"           # 拥挤
    TEMP_CLOSED = "temp_closed"   # 临时关闭
    OFF_HOURS = "off_hours"       # 非营业时间


class TimeWindowType(str, Enum):
    """时间窗口类型"""
    FIXED = "fixed"               # 固定时间窗口
    FLEXIBLE = "flexible"         # 灵活时间窗口
    EXPRESS = "express"           # 即时配送


class PriorityLevel(str, Enum):
    """优先级等级"""
    LOW = "low"                   # 低优先级
    NORMAL = "normal"             # 普通优先级
    HIGH = "high"                 # 高优先级
    URGENT = "urgent"             # 紧急


class ExceptionType(str, Enum):
    """异常类型"""
    DELAY = "delay"                        # 配送延迟
    ROUTE_CHANGE = "route_change"          # 路线变更
    PICKUP_POINT_CLOSED = "pickup_point_closed"  # 自提点关闭
    CAPACITY_EXCEEDED = "capacity_exceeded"      # 容量超限
    WEATHER_IMPACT = "weather_impact"      # 天气影响
    TRAFFIC_IMPACT = "traffic_impact"      # 交通影响
    CUSTOMER_UNAVAILABLE = "customer_unavailable"  # 客户不在


class PickupPoint(BaseModel):
    """自提点模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                              # 自提点名称
    community_id: str                      # 所属社区 ID
    address: str                           # 详细地址
    latitude: float                        # 纬度
    longitude: float                       # 经度
    contact_name: str                      # 联系人姓名
    contact_phone: str                     # 联系电话
    opening_hours: Dict[str, Any]          # 营业时间 {"monday": {"open": "09:00", "close": "21:00"}}
    capacity: int = 100                    # 容量（可存放包裹数）
    current_load: int = 0                  # 当前负载
    status: PickupPointStatus = PickupPointStatus.ACTIVE
    avg_pickup_time: int = 15              # 平均取货时长（分钟）
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DeliveryRoute(BaseModel):
    """配送路线模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                              # 路线名称
    warehouse_id: str                      # 起始仓库 ID
    driver_id: Optional[str] = None        # 配送员 ID
    vehicle_id: Optional[str] = None       # 车辆 ID
    stops: List[Dict[str, Any]]            # 配送站点列表 [{"pickup_point_id": "...", "sequence": 1, "eta": "..."}]
    total_distance: float = 0.0            # 总距离（公里）
    estimated_duration: int = 0            # 预计时长（分钟）
    start_time: Optional[datetime] = None  # 出发时间
    end_time: Optional[datetime] = None    # 预计返回时间
    status: DeliveryStatus = DeliveryStatus.PENDING
    priority: PriorityLevel = PriorityLevel.NORMAL
    optimization_score: float = 0.0        # 优化分数（0-1）
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class DeliveryTask(BaseModel):
    """配送任务模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    route_id: str                          # 所属路线 ID
    order_id: str                          # 订单 ID
    fulfillment_id: str                    # 履约记录 ID
    pickup_point_id: str                   # 自提点 ID
    delivery_time_window: Optional[Dict]   # 配送时间窗口 {"start": "09:00", "end": "12:00"}
    window_type: TimeWindowType = TimeWindowType.FLEXIBLE
    priority: PriorityLevel = PriorityLevel.NORMAL
    sequence: int = 0                      # 配送顺序
    estimated_arrival: Optional[datetime] = None  # 预计到达时间
    actual_arrival: Optional[datetime] = None     # 实际到达时间
    status: DeliveryStatus = DeliveryStatus.PENDING
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TrafficFlowPrediction(BaseModel):
    """人流预测模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pickup_point_id: str                   # 自提点 ID
    prediction_date: datetime              # 预测日期
    hour: int                              # 小时 (0-23)
    predicted_flow: int                    # 预测人流量
    actual_flow: Optional[int] = None      # 实际人流量
    confidence: float = 0.0                # 置信度 (0-1)
    crowd_level: str = "normal"            # 拥挤等级：low, normal, high, crowded
    features: Optional[Dict] = None        # 特征数据
    model_version: str = "v1"              # 模型版本
    created_at: datetime = Field(default_factory=datetime.now)


class TimeWindowRecommendation(BaseModel):
    """时间窗口推荐模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fulfillment_id: str                    # 履约记录 ID
    pickup_point_id: str                   # 自提点 ID
    recommended_windows: List[Dict]        # 推荐时间窗口列表
    best_window_index: int = 0             # 最佳窗口索引
    recommendation_reason: str = ""        # 推荐理由
    confidence: float = 0.0                # 推荐置信度
    created_at: datetime = Field(default_factory=datetime.now)


class DeliveryException(BaseModel):
    """配送异常模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    route_id: Optional[str] = None         # 关联路线 ID
    task_id: Optional[str] = None          # 关联任务 ID
    fulfillment_id: str                    # 履约记录 ID
    exception_type: ExceptionType          # 异常类型
    severity: str = "low"                  # 严重程度：low, medium, high, critical
    description: str                       # 异常描述
    detected_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None       # 解决方案
    impact_assessment: Optional[Dict] = None  # 影响评估
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ========== 请求/响应模型 ==========

class PickupPointCreate(BaseModel):
    """创建自提点请求"""
    name: str
    community_id: str
    address: str
    latitude: float
    longitude: float
    contact_name: str
    contact_phone: str
    opening_hours: Optional[Dict] = None
    capacity: int = 100


class PickupPointUpdate(BaseModel):
    """更新自提点请求"""
    name: Optional[str] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    opening_hours: Optional[Dict] = None
    capacity: Optional[int] = None
    status: Optional[PickupPointStatus] = None


class DeliveryRouteCreate(BaseModel):
    """创建配送路线请求"""
    name: str
    warehouse_id: str
    driver_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    stops: List[Dict[str, Any]] = []
    priority: PriorityLevel = PriorityLevel.NORMAL


class DeliveryRouteOptimizeRequest(BaseModel):
    """路线优化请求"""
    warehouse_id: str
    pickup_point_ids: List[str]           # 需要配送的自提点 ID 列表
    vehicle_capacity: Optional[int] = None  # 车辆容量
    max_distance: Optional[float] = None   # 最大行驶距离
    time_windows: Optional[Dict] = None    # 时间窗口约束
    priority_points: Optional[List[str]] = None  # 高优先级自提点


class DeliveryTaskCreate(BaseModel):
    """创建配送任务请求"""
    route_id: str
    order_id: str
    fulfillment_id: str
    pickup_point_id: str
    delivery_time_window: Optional[Dict] = None
    window_type: TimeWindowType = TimeWindowType.FLEXIBLE
    priority: PriorityLevel = PriorityLevel.NORMAL


class TimeWindowRecommendRequest(BaseModel):
    """时间窗口推荐请求"""
    fulfillment_id: str
    pickup_point_id: str
    preferred_date: Optional[datetime] = None
    window_duration: int = 60              # 窗口时长（分钟）


class ExceptionReportRequest(BaseModel):
    """异常上报请求"""
    route_id: Optional[str] = None
    task_id: Optional[str] = None
    fulfillment_id: str
    exception_type: ExceptionType
    description: str
    severity: str = "low"
    impact_assessment: Optional[Dict] = None


class ExceptionResolveRequest(BaseModel):
    """异常解决请求"""
    resolution: str
