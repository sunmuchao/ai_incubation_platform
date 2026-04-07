"""
实时数据仪表板 - 数据模型。
"""
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DashboardSnapshotDB(Base):
    """仪表板快照表 - 定时存储各项指标快照。"""
    __tablename__ = "dashboard_snapshots"

    # 快照标识
    snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    snapshot_type: Mapped[str] = mapped_column(String(50), index=True, default="overview")  # overview/tasks/workers/quality/financial

    # 时间维度
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)
    time_range: Mapped[str] = mapped_column(String(20), default="realtime")  # realtime/hourly/daily/weekly/monthly

    # 核心指标（JSON 存储，灵活扩展）
    metrics: Mapped[Dict] = mapped_column(JSON, default=dict)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class DashboardMetricConfigDB(Base):
    """仪表板指标配置表 - 定义指标的计算方式和展示配置。"""
    __tablename__ = "dashboard_metric_configs"

    metric_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(200))  # 指标中文名
    metric_category: Mapped[str] = mapped_column(String(50), index=True)  # 指标类别：tasks/workers/quality/financial/system

    # 计算配置
    calculation_method: Mapped[str] = mapped_column(String(50), default="count")  # count/sum/avg/ratio
    data_source: Mapped[str] = mapped_column(String(100))  # 数据来源表
    filter_conditions: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)  # 过滤条件

    # 展示配置
    display_type: Mapped[str] = mapped_column(String(50), default="number")  # number/percentage/currency/trend
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 单位
    precision: Mapped[int] = mapped_column(Integer, default=2)  # 小数精度
    threshold_warning: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 预警阈值
    threshold_critical: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 严重阈值

    # 更新配置
    update_frequency: Mapped[str] = mapped_column(String(20), default="realtime")  # realtime/minute/hour/day
    retention_days: Mapped[int] = mapped_column(Integer, default=30)  # 数据保留天数

    # 状态
    is_enabled: Mapped[bool] = mapped_column(Integer, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    # 审计
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class DashboardAlertDB(Base):
    """仪表板告警表 - 记录指标触发的告警。"""
    __tablename__ = "dashboard_alerts"

    alert_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    metric_key: Mapped[str] = mapped_column(String(100), index=True)
    alert_level: Mapped[str] = mapped_column(String(20), default="warning")  # info/warning/critical

    # 告警内容
    alert_title: Mapped[str] = mapped_column(String(200))
    alert_message: Mapped[str] = mapped_column(Text)
    current_value: Mapped[float] = mapped_column(Float)
    threshold_value: Mapped[float] = mapped_column(Float)

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/acknowledged/resolved
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 时间戳
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)
