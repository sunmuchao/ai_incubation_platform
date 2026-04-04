"""
数据库实体模型
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from config.database import Base
from models.product import ProductStatus, GroupBuyStatus, OrderStatus


def generate_uuid():
    return str(uuid.uuid4())


class ProductEntity(Base):
    """商品数据库实体"""
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=False)
    image_url = Column(String)
    stock = Column(Integer, default=0)
    locked_stock = Column(Integer, default=0)
    sold_stock = Column(Integer, default=0)
    min_group_size = Column(Integer, default=2)
    max_group_size = Column(Integer, default=10)
    status = Column(Enum(ProductStatus), default=ProductStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    group_buys = relationship("GroupBuyEntity", back_populates="product")


class GroupBuyEntity(Base):
    """团购数据库实体"""
    __tablename__ = "group_buys"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    organizer_id = Column(String, nullable=False)
    target_size = Column(Integer, nullable=False)
    current_size = Column(Integer, default=1)
    status = Column(Enum(GroupBuyStatus), default=GroupBuyStatus.OPEN)
    deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    product = relationship("ProductEntity", back_populates="group_buys")
    members = relationship("GroupMemberEntity", back_populates="group_buy", cascade="all, delete-orphan")
    orders = relationship("OrderEntity", back_populates="group_buy")


class GroupMemberEntity(Base):
    """团购成员数据库实体"""
    __tablename__ = "group_members"

    id = Column(String, primary_key=True, default=generate_uuid)
    group_buy_id = Column(String, ForeignKey("group_buys.id"), nullable=False)
    user_id = Column(String, nullable=False)
    join_time = Column(DateTime, default=datetime.now)
    order_id = Column(String, ForeignKey("orders.id"))

    # 关联
    group_buy = relationship("GroupBuyEntity", back_populates="members")
    order = relationship("OrderEntity", back_populates="group_member", uselist=False)


class OrderEntity(Base):
    """订单数据库实体"""
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False)
    group_buy_id = Column(String, ForeignKey("group_buys.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_time = Column(DateTime)
    delivery_time = Column(DateTime)
    completed_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    group_buy = relationship("GroupBuyEntity", back_populates="orders")
    group_member = relationship("GroupMemberEntity", back_populates="order", uselist=False)


class NotificationEntity(Base):
    """通知数据库实体"""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # stock_alert, group_progress, group_success, group_failed
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    related_id = Column(String)  # 关联ID（商品ID、团购ID等）
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    read_at = Column(DateTime)


class ProductRecommendationEntity(Base):
    """商品推荐数据库实体"""
    __tablename__ = "product_recommendations"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    community_id = Column(String, nullable=False, index=True)
    score = Column(Float, default=0.0)  # 推荐分数
    reason = Column(String)  # 推荐理由
    created_at = Column(DateTime, default=datetime.now)
    expired_at = Column(DateTime)
