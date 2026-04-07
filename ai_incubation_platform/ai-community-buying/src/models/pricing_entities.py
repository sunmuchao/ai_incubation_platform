"""
P1 动态定价引擎 - 数据库实体模型
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from config.database import Base
from models.dynamic_pricing import PricingStrategyType, PriceAdjustmentReason, PriceStatus


def generate_uuid():
    return str(uuid.uuid4())


class DynamicPriceEntity(Base):
    """动态价格数据库实体"""
    __tablename__ = "dynamic_prices"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    community_id = Column(String, nullable=False, index=True)
    base_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    adjustment_amount = Column(Float, default=0.0)
    adjustment_percentage = Column(Float, default=0.0)
    adjustment_reason = Column(Enum(PriceAdjustmentReason))
    strategy_type = Column(Enum(PricingStrategyType), default=PricingStrategyType.STATIC)
    strategy_config = Column(Text)  # JSON 字符串
    status = Column(Enum(PriceStatus), default=PriceStatus.ACTIVE)
    effective_from = Column(DateTime, default=datetime.now)
    effective_to = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    product = relationship("ProductEntity", backref="dynamic_prices")


class PriceHistoryEntity(Base):
    """价格历史数据库实体"""
    __tablename__ = "price_histories"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    community_id = Column(String, nullable=False, index=True)
    old_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    adjustment_amount = Column(Float, nullable=False)
    adjustment_reason = Column(Enum(PriceAdjustmentReason))
    strategy_type = Column(Enum(PricingStrategyType), nullable=False)
    trigger_source = Column(String, nullable=False)  # system/user/api
    trigger_id = Column(String)
    extra_data = Column(Text)  # JSON 字符串
    created_at = Column(DateTime, default=datetime.now, index=True)


class PricingStrategyEntity(Base):
    """定价策略数据库实体"""
    __tablename__ = "pricing_strategies"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    strategy_type = Column(Enum(PricingStrategyType), nullable=False)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    config = Column(Text, nullable=False)  # JSON 字符串
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PriceElasticityTestEntity(Base):
    """价格弹性测试数据库实体"""
    __tablename__ = "price_elasticity_tests"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    community_id = Column(String, nullable=False, index=True)
    test_name = Column(String, nullable=False)
    control_price = Column(Float, nullable=False)
    variant_prices = Column(String, nullable=False)  # JSON 字符串，存储数组
    traffic_allocation = Column(String, nullable=False)  # JSON 字符串
    target_metric = Column(String, default="conversion_rate")
    control_metrics = Column(String)  # JSON 字符串
    variant_metrics = Column(String)  # JSON 字符串
    elasticity_coefficient = Column(Float)
    status = Column(String, default="pending")  # pending, running, completed, stopped
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CompetitorPriceEntity(Base):
    """竞品价格数据库实体"""
    __tablename__ = "competitor_prices"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    competitor_name = Column(String, nullable=False)
    competitor_product_id = Column(String)
    competitor_price = Column(Float, nullable=False)
    competitor_stock_status = Column(String, default="in_stock")
    price_diff_percentage = Column(Float, default=0.0)
    crawled_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    product = relationship("ProductEntity", backref="competitor_prices")
