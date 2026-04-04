"""
商品模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid
from enum import Enum


class ProductStatus(str, Enum):
    """商品状态"""
    ACTIVE = "active"       # 可售卖
    SOLD_OUT = "sold_out"   # 售罄
    INACTIVE = "inactive"   # 下架


class GroupBuyStatus(str, Enum):
    """团购状态"""
    OPEN = "open"           # 招募中
    SUCCESS = "success"     # 成团成功
    FAILED = "failed"       # 成团失败
    EXPIRED = "expired"     # 已过期
    CANCELLED = "cancelled" # 已取消


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"        # 待支付
    PAID = "paid"              # 已支付
    DELIVERING = "delivering"  # 配送中
    COMPLETED = "completed"    # 已完成
    CANCELLED = "cancelled"    # 已取消
    REFUNDED = "refunded"      # 已退款


class Product(BaseModel):
    """商品模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float  # 团购价
    original_price: float  # 原价
    image_url: Optional[str] = None
    stock: int = 0  # 总库存
    locked_stock: int = 0  # 已锁定库存（参与团购但未最终成交）
    sold_stock: int = 0  # 已售出库存
    min_group_size: int = 2  # 最小成团人数
    max_group_size: int = 10  # 最大成团人数
    status: ProductStatus = ProductStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class GroupBuy(BaseModel):
    """团购模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    organizer_id: str  # 团长 ID
    product: Optional[Product] = None  # 关联商品信息
    target_size: int  # 目标成团人数
    current_size: int = 1  # 当前参团人数
    status: GroupBuyStatus = GroupBuyStatus.OPEN
    deadline: datetime  # 团购截止时间
    members: List[str] = Field(default_factory=list)  # 成员 ID 列表
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """检查团购是否已过期"""
        return datetime.now() > self.deadline

    def can_join(self, user_id: str) -> bool:
        """检查用户是否可以加入该团购"""
        if self.status != GroupBuyStatus.OPEN:
            return False
        if self.is_expired():
            return False
        if user_id in self.members:
            return False
        if len(self.members) >= self.target_size:
            return False
        return True


class Order(BaseModel):
    """订单模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    group_buy_id: str
    product_id: str
    quantity: int = 1
    unit_price: float  # 单价
    total_amount: float  # 总金额
    status: OrderStatus = OrderStatus.PENDING
    payment_time: Optional[datetime] = None
    delivery_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class GroupJoinRecord(BaseModel):
    """参团记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    group_buy_id: str
    user_id: str
    join_time: datetime = Field(default_factory=datetime.now)
    order_id: Optional[str] = None
    status: str = "joined"  # joined, paid, cancelled


class ProductCreate(BaseModel):
    """创建商品请求"""
    name: str
    description: str
    price: float
    original_price: float
    stock: int
    min_group_size: int = 2
    max_group_size: int = 10
    image_url: Optional[str] = None


class GroupBuyCreate(BaseModel):
    """发起团购请求"""
    product_id: str
    organizer_id: str
    target_size: int = 2
    duration_hours: int = 24  # 团购持续时长，默认24小时


class GroupBuyJoinRequest(BaseModel):
    """加入团购请求"""
    user_id: str
