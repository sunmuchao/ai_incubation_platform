"""
P4 供应链与履约优化 - 数据库实体模型
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from config.database import Base


def generate_uuid():
    return str(uuid.uuid4())


# ========== P4 库存预警实体 ==========

class InventoryAlertEntity(Base):
    """库存预警记录数据库实体"""
    __tablename__ = "inventory_alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)  # 商品 ID
    community_id = Column(String, nullable=False, index=True)  # 社区 ID
    current_stock = Column(Integer, nullable=False)  # 当前库存
    threshold = Column(Integer, nullable=False)  # 预警阈值
    alert_level = Column(String, nullable=False)  # low:低库存，critical:严重缺货
    alert_type = Column(String, nullable=False)  # stock_low:库存不足，stock_out:缺货，expiry_warning:临期预警
    message = Column(String)  # 预警消息
    status = Column(String, default="active")  # active:活跃，handled:已处理，ignored:已忽略
    suggested_quantity = Column(Integer)  # 建议补货数量
    handler_id = Column(String)  # 处理人 ID
    handled_at = Column(DateTime)  # 处理时间
    handled_notes = Column(String)  # 处理备注
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    alert_actions = relationship("InventoryAlertActionEntity", back_populates="alert", cascade="all, delete-orphan")


class InventoryAlertActionEntity(Base):
    """库存预警处理行动记录"""
    __tablename__ = "inventory_alert_actions"

    id = Column(String, primary_key=True, default=generate_uuid)
    alert_id = Column(String, ForeignKey("inventory_alerts.id"), nullable=False)  # 预警记录 ID
    action_type = Column(String, nullable=False)  # restock:补货，transfer:调拨，discount:打折促销，remove:下架
    action_quantity = Column(Integer)  # 行动数量
    action_cost = Column(Float, default=0.0)  # 行动成本
    expected_effect_date = Column(DateTime)  # 预期生效日期
    status = Column(String, default="pending")  # pending:待执行，in_progress:执行中，completed:已完成，cancelled:已取消
    executor_id = Column(String)  # 执行人 ID
    executed_at = Column(DateTime)  # 执行时间
    notes = Column(String)  # 备注
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    alert = relationship("InventoryAlertEntity", back_populates="alert_actions")


# ========== P4 智能补货实体 ==========

class ReplenishmentSuggestionEntity(Base):
    """智能补货建议数据库实体"""
    __tablename__ = "replenishment_suggestions"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)  # 商品 ID
    community_id = Column(String, nullable=False, index=True)  # 社区 ID
    current_stock = Column(Integer, nullable=False)  # 当前库存
    predicted_demand = Column(Integer, nullable=False)  # 预测需求（未来 N 天）
    predicted_days = Column(Integer, default=7)  # 预测天数
    suggested_quantity = Column(Integer, nullable=False)  # 建议补货数量
    suggested_order_date = Column(DateTime)  # 建议下单日期
    expected_delivery_date = Column(DateTime)  # 预期到货日期
    priority = Column(String, default="normal")  # low:低，normal:普通，high:高，urgent:紧急
    confidence = Column(Float, default=0.0)  # 推荐置信度 (0-1)
    reason = Column(String)  # 推荐原因
    model_version = Column(String, default="v1")  # 模型版本
    status = Column(String, default="pending")  # pending:待处理，converted:已转为采购单，rejected:已拒绝
    converted_to_order_id = Column(String)  # 转化的采购订单 ID
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ========== P4 供应商管理实体 ==========

class SupplierEntity(Base):
    """供应商数据库实体"""
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # 供应商名称
    contact_person = Column(String)  # 联系人
    contact_phone = Column(String)  # 联系电话
    contact_email = Column(String)  # 联系邮箱
    address = Column(String)  # 地址
    category = Column(String, index=True)  # 主营品类
    rating = Column(Float, default=5.0)  # 供应商评分 (0-5)
    total_orders = Column(Integer, default=0)  # 累计订单数
    total_amount = Column(Float, default=0.0)  # 累计采购金额
    on_time_delivery_rate = Column(Float, default=1.0)  # 准时交付率 (0-1)
    quality_pass_rate = Column(Float, default=1.0)  # 质量合格率 (0-1)
    response_time_hours = Column(Float, default=24.0)  # 平均响应时间（小时）
    payment_terms_days = Column(Integer, default=7)  # 账期（天）
    min_order_amount = Column(Float, default=0.0)  # 最低订单金额
    delivery_lead_days = Column(Integer, default=3)  # 交付周期（天）
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    products = relationship("SupplierProductEntity", back_populates="supplier", cascade="all, delete-orphan")
    orders = relationship("PurchaseOrderEntity", back_populates="supplier")


class SupplierProductEntity(Base):
    """供应商商品关系数据库实体"""
    __tablename__ = "supplier_products"

    id = Column(String, primary_key=True, default=generate_uuid)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)  # 供应商 ID
    product_id = Column(String, ForeignKey("products.id"), nullable=False)  # 平台商品 ID
    supplier_product_name = Column(String)  # 供应商商品名称
    supplier_product_code = Column(String)  # 供应商商品编码
    cost_price = Column(Float, nullable=False)  # 采购单价
    min_order_quantity = Column(Integer, default=1)  # 最小起订量
    lead_days = Column(Integer, default=3)  # 交付周期（天）
    is_preferred = Column(Boolean, default=False)  # 是否首选供应商
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    supplier = relationship("SupplierEntity", back_populates="products")
    order_lines = relationship("PurchaseOrderLineEntity", back_populates="supplier_product")


# ========== P4 采购订单管理实体 ==========

class PurchaseOrderEntity(Base):
    """采购订单数据库实体"""
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    order_no = Column(String, unique=True, nullable=False, index=True)  # 采购单号
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)  # 供应商 ID
    community_id = Column(String, nullable=False, index=True)  # 社区 ID（采购到哪个社区）
    total_quantity = Column(Integer, default=0)  # 总数量
    total_amount = Column(Float, default=0.0)  # 总金额
    status = Column(String, default="draft")  # draft:草稿，submitted:已提交，confirmed:已确认，shipping:配送中，received:已收货，cancelled:已取消
    expected_delivery_date = Column(DateTime)  # 预期交付日期
    actual_delivery_date = Column(DateTime)  # 实际交付日期
    delivery_address = Column(String)  # 交付地址
    receiver_id = Column(String)  # 收货人 ID
    receiver_name = Column(String)  # 收货人姓名
    receiver_phone = Column(String)  # 收货人电话
    notes = Column(String)  # 备注
    submitted_at = Column(DateTime)  # 提交时间
    confirmed_at = Column(DateTime)  # 确认时间
    received_at = Column(DateTime)  # 收货时间
    cancelled_at = Column(DateTime)  # 取消时间
    cancel_reason = Column(String)  # 取消原因
    created_by = Column(String)  # 创建人 ID
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    supplier = relationship("SupplierEntity", back_populates="orders")
    lines = relationship("PurchaseOrderLineEntity", back_populates="order", cascade="all, delete-orphan")


class PurchaseOrderLineEntity(Base):
    """采购订单明细数据库实体"""
    __tablename__ = "purchase_order_lines"

    id = Column(String, primary_key=True, default=generate_uuid)
    order_id = Column(String, ForeignKey("purchase_orders.id"), nullable=False)  # 采购订单 ID
    product_id = Column(String, ForeignKey("products.id"), nullable=False)  # 商品 ID
    supplier_product_id = Column(String, ForeignKey("supplier_products.id"))  # 供应商商品 ID
    quantity = Column(Integer, nullable=False)  # 采购数量
    unit_cost = Column(Float, nullable=False)  # 采购单价
    line_total = Column(Float, nullable=False)  # 行总金额
    received_quantity = Column(Integer, default=0)  # 已收货数量
    quality_check_quantity = Column(Integer, default=0)  # 质检合格数量
    rejected_quantity = Column(Integer, default=0)  # 拒收数量
    quality_issue_reason = Column(String)  # 质量问题原因
    status = Column(String, default="pending")  # pending:待收货，partial:部分收货，completed:已完成
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    order = relationship("PurchaseOrderEntity", back_populates="lines")
    supplier_product = relationship("SupplierProductEntity", back_populates="order_lines")


# ========== P4 库存流水实体 ==========

class InventoryTransactionEntity(Base):
    """库存流水数据库实体"""
    __tablename__ = "inventory_transactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)  # 商品 ID
    community_id = Column(String, nullable=False, index=True)  # 社区 ID
    transaction_type = Column(String, nullable=False)  # purchase:采购入库，sales:销售出库，return:退货入库，adjust:库存调整，transfer:调拨
    quantity = Column(Integer, nullable=False)  # 变动数量（正数入库，负数出库）
    balance_before = Column(Integer, nullable=False)  # 变动前库存
    balance_after = Column(Integer, nullable=False)  # 变动后库存
    reference_type = Column(String)  # 关联类型（purchase_order/order/adjustment）
    reference_id = Column(String)  # 关联 ID
    operator_id = Column(String)  # 操作人 ID
    notes = Column(String)  # 备注
    created_at = Column(DateTime, default=datetime.now)

    # 索引
    __tablename__ = "inventory_transactions"
