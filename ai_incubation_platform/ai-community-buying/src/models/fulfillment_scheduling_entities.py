"""
智能履约调度系统 - 数据库实体模型
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import json
from config.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class PickupPointEntity(Base):
    """自提点数据库实体"""
    __tablename__ = "pickup_points"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)  # 自提点名称
    community_id = Column(String, nullable=False, index=True)  # 所属社区 ID
    address = Column(String, nullable=False)  # 详细地址
    latitude = Column(Float, nullable=False)  # 纬度
    longitude = Column(Float, nullable=False)  # 经度
    contact_name = Column(String, nullable=False)  # 联系人姓名
    contact_phone = Column(String, nullable=False)  # 联系电话
    opening_hours = Column(JSON)  # 营业时间 JSON
    capacity = Column(Integer, default=100)  # 容量
    current_load = Column(Integer, default=0)  # 当前负载
    status = Column(String, default="active")  # active, crowded, temp_closed, off_hours
    avg_pickup_time = Column(Integer, default=15)  # 平均取货时长（分钟）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    delivery_tasks = relationship("DeliveryTaskEntity", back_populates="pickup_point")
    traffic_predictions = relationship("TrafficFlowPredictionEntity", back_populates="pickup_point")


class DeliveryRouteEntity(Base):
    """配送路线数据库实体"""
    __tablename__ = "delivery_routes"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # 路线名称
    warehouse_id = Column(String, nullable=False, index=True)  # 起始仓库 ID
    driver_id = Column(String, index=True)  # 配送员 ID
    vehicle_id = Column(String)  # 车辆 ID
    stops = Column(JSON)  # 配送站点列表 JSON
    total_distance = Column(Float, default=0.0)  # 总距离（公里）
    estimated_duration = Column(Integer, default=0)  # 预计时长（分钟）
    start_time = Column(DateTime)  # 出发时间
    end_time = Column(DateTime)  # 预计返回时间
    status = Column(String, default="pending")  # pending, planned, in_progress, completed, failed, exception
    priority = Column(String, default="normal")  # low, normal, high, urgent
    optimization_score = Column(Float, default=0.0)  # 优化分数（0-1）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime)

    # 关联
    tasks = relationship("DeliveryTaskEntity", back_populates="route")
    exceptions = relationship("DeliveryExceptionEntity", back_populates="route")


class DeliveryTaskEntity(Base):
    """配送任务数据库实体"""
    __tablename__ = "delivery_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    route_id = Column(String, ForeignKey("delivery_routes.id"), nullable=False, index=True)  # 所属路线 ID
    order_id = Column(String, nullable=False, index=True)  # 订单 ID
    fulfillment_id = Column(String, nullable=False, index=True)  # 履约记录 ID
    pickup_point_id = Column(String, ForeignKey("pickup_points.id"), nullable=False)  # 自提点 ID
    delivery_time_window_start = Column(String)  # 配送时间窗口开始 "09:00"
    delivery_time_window_end = Column(String)  # 配送时间窗口结束 "12:00"
    window_type = Column(String, default="flexible")  # fixed, flexible, express
    priority = Column(String, default="normal")  # low, normal, high, urgent
    sequence = Column(Integer, default=0)  # 配送顺序
    estimated_arrival = Column(DateTime)  # 预计到达时间
    actual_arrival = Column(DateTime)  # 实际到达时间
    status = Column(String, default="pending")  # pending, planned, in_progress, completed, failed, exception
    notes = Column(Text)  # 备注
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    route = relationship("DeliveryRouteEntity", back_populates="tasks")
    pickup_point = relationship("PickupPointEntity", back_populates="delivery_tasks")
    exception = relationship("DeliveryExceptionEntity", back_populates="task", uselist=False)


class TrafficFlowPredictionEntity(Base):
    """人流预测数据库实体"""
    __tablename__ = "traffic_flow_predictions"

    id = Column(String, primary_key=True, default=generate_uuid)
    pickup_point_id = Column(String, ForeignKey("pickup_points.id"), nullable=False, index=True)  # 自提点 ID
    prediction_date = Column(DateTime, nullable=False, index=True)  # 预测日期
    hour = Column(Integer, nullable=False)  # 小时 (0-23)
    predicted_flow = Column(Integer, nullable=False)  # 预测人流量
    actual_flow = Column(Integer)  # 实际人流量
    confidence = Column(Float, default=0.0)  # 置信度 (0-1)
    crowd_level = Column(String, default="normal")  # low, normal, high, crowded
    features = Column(JSON)  # 特征数据 JSON
    model_version = Column(String, default="v1")  # 模型版本
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    pickup_point = relationship("PickupPointEntity", back_populates="traffic_predictions")


class TimeWindowRecommendationEntity(Base):
    """时间窗口推荐数据库实体"""
    __tablename__ = "time_window_recommendations"

    id = Column(String, primary_key=True, default=generate_uuid)
    fulfillment_id = Column(String, nullable=False, index=True)  # 履约记录 ID
    pickup_point_id = Column(String, nullable=False, index=True)  # 自提点 ID
    recommended_windows = Column(JSON, nullable=False)  # 推荐时间窗口列表 JSON
    best_window_index = Column(Integer, default=0)  # 最佳窗口索引
    recommendation_reason = Column(String)  # 推荐理由
    confidence = Column(Float, default=0.0)  # 推荐置信度
    created_at = Column(DateTime, default=datetime.now)


class DeliveryExceptionEntity(Base):
    """配送异常数据库实体"""
    __tablename__ = "delivery_exceptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    route_id = Column(String, ForeignKey("delivery_routes.id"), index=True)  # 关联路线 ID
    task_id = Column(String, ForeignKey("delivery_tasks.id"), index=True)  # 关联任务 ID
    fulfillment_id = Column(String, nullable=False, index=True)  # 履约记录 ID
    exception_type = Column(String, nullable=False)  # 异常类型
    severity = Column(String, default="low")  # low, medium, high, critical
    description = Column(Text, nullable=False)  # 异常描述
    detected_at = Column(DateTime, nullable=False, default=datetime.now)  # 检测时间
    resolved_at = Column(DateTime)  # 解决时间
    resolution = Column(Text)  # 解决方案
    impact_assessment = Column(JSON)  # 影响评估 JSON
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    route = relationship("DeliveryRouteEntity", back_populates="exceptions")
    task = relationship("DeliveryTaskEntity", back_populates="exception")
