"""
P6 数据分析增强 - 数据库实体模型

包含:
1. 销售报表 (Sales Reports) - 日报/周报/月报
2. 用户行为分析 (User Behavior Analytics) - 转化漏斗/留存分析
3. 商品分析 (Product Analytics) - 销售排行/库存周转
4. 预测分析 (Predictive Analytics) - 销量预测/趋势预测
5. 自定义报表 (Custom Reports) - 用户自定义分析报表
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum, Boolean, Index, Numeric, Float, JSON, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
import enum

from config.database import Base


# ====================  enums  ====================

class ReportType(enum.Enum):
    """报表类型"""
    DAILY = "daily"         # 日报
    WEEKLY = "weekly"       # 周报
    MONTHLY = "monthly"     # 月报
    CUSTOM = "custom"       # 自定义


class ReportStatus(enum.Enum):
    """报表状态"""
    PENDING = "pending"     # 待生成
    GENERATING = "generating"  # 生成中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"       # 失败


class FunnelStage(enum.Enum):
    """漏斗阶段"""
    IMPRESSION = "impression"   # 曝光
    CLICK = "click"             # 点击
    DETAIL = "detail"           # 查看详情
    CART = "cart"               # 加入购物车
    CHECKOUT = "checkout"       # 提交订单
    PAYMENT = "payment"         # 支付成功


class UserSegment(enum.Enum):
    """用户分群"""
    NEW_USER = "new_user"           # 新用户 (注册<7 天)
    ACTIVE_USER = "active_user"     # 活跃用户 (7 天内有购买)
    SILENT_USER = "silent_user"     # 沉默用户 (30 天无购买)
    LOST_USER = "lost_user"         # 流失用户 (60 天无购买)
    HIGH_VALUE = "high_value"       # 高价值用户 (累计消费前 20%)


class TrendDirection(enum.Enum):
    """趋势方向"""
    UP = "up"               # 上升
    DOWN = "down"           # 下降
    STABLE = "stable"       # 平稳


# ====================  销售报表实体  ====================

class SalesReportEntity(Base):
    """销售报表实体 - 日报/周报/月报"""
    __tablename__ = "sales_reports"

    id = Column(String(64), primary_key=True)
    report_type = Column(Enum(ReportType), nullable=False)  # daily/weekly/monthly
    report_date = Column(Date, nullable=False, index=True)  # 报表日期 (日报为当天，周报为周一，月报为 1 号)
    period_start = Column(Date, nullable=False)  # 周期开始
    period_end = Column(Date, nullable=False)  # 周期结束

    # 核心指标
    gmv = Column(Numeric(14, 2), default=0)  # 商品交易总额
    total_sales = Column(Numeric(14, 2), default=0)  # 实际销售额 (已完成订单)
    total_orders = Column(Integer, default=0)  # 订单总数
    paid_orders = Column(Integer, default=0)  # 已支付订单数
    completed_orders = Column(Integer, default=0)  # 已完成订单数
    cancelled_orders = Column(Integer, default=0)  # 已取消订单数
    refunded_orders = Column(Integer, default=0)  # 已退款订单数

    # 用户指标
    total_users = Column(Integer, default=0)  # 下单用户数
    new_users = Column(Integer, default=0)  # 新用户数
    active_users = Column(Integer, default=0)  # 活跃用户数
    avg_order_value = Column(Numeric(10, 2), default=0)  # 客单价

    # 商品指标
    total_products = Column(Integer, default=0)  # 销售商品数
    top_product_id = Column(String(64))  # 热销商品 ID
    top_product_sales = Column(Numeric(14, 2), default=0)  # 热销商品销售额

    # 环比数据
    prev_period_gmv = Column(Numeric(14, 2), default=0)  # 上期 GMV
    gmv_growth_rate = Column(Numeric(6, 4), default=0)  # GMV 环比增长率 (小数形式，如 0.15 表示 15%)
    prev_period_orders = Column(Integer, default=0)  # 上期订单数
    orders_growth_rate = Column(Numeric(6, 4), default=0)  # 订单环比增长率

    # 团长维度 (可选，按团长筛选时使用)
    organizer_id = Column(String(64), index=True)  # 团长 ID，为空表示平台汇总
    community_id = Column(String(64), index=True)  # 社区 ID，为空表示平台汇总

    # 报表元数据
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING)
    generated_at = Column(DateTime)  # 生成时间
    data_hash = Column(String(64))  # 数据哈希，用于去重

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_report_type_date", "report_type", "report_date"),
        Index("idx_organizer_date", "organizer_id", "report_date"),
    )


class SalesReportDetailEntity(Base):
    """销售报表明细 - 按商品/社区/团长维度的明细数据"""
    __tablename__ = "sales_report_details"

    id = Column(String(64), primary_key=True)
    report_id = Column(String(64), ForeignKey("sales_reports.id"), nullable=False, index=True)
    dimension_type = Column(String(32), nullable=False)  # product/community/organizer/category
    dimension_id = Column(String(64), nullable=False)  # 维度 ID (商品 ID/社区 ID/团长 ID/分类)
    dimension_name = Column(String(128))  # 维度名称

    # 指标数据
    gmv = Column(Numeric(14, 2), default=0)
    sales = Column(Numeric(14, 2), default=0)
    orders = Column(Integer, default=0)
    quantity = Column(Integer, default=0)  # 销售件数
    users = Column(Integer, default=0)  # 下单用户数

    # 排名
    rank = Column(Integer)  # 在该维度中的排名

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_report_dimension", "report_id", "dimension_type", "dimension_id"),
    )


# ====================  用户行为分析实体  ====================

class UserFunnelEntity(Base):
    """用户转化漏斗实体"""
    __tablename__ = "user_funnels"

    id = Column(String(64), primary_key=True)
    funnel_date = Column(Date, nullable=False, index=True)  # 统计日期
    period_type = Column(String(32), default="daily")  # daily/weekly/monthly

    # 漏斗各阶段用户数
    impression_count = Column(Integer, default=0)  # 曝光用户数
    click_count = Column(Integer, default=0)  # 点击用户数
    detail_count = Column(Integer, default=0)  # 查看详情用户数
    cart_count = Column(Integer, default=0)  # 加购用户数
    checkout_count = Column(Integer, default=0)  # 提交订单用户数
    payment_count = Column(Integer, default=0)  # 支付用户数

    # 转化率
    click_rate = Column(Numeric(6, 4), default=0)  # 点击率 = click/impression
    detail_rate = Column(Numeric(6, 4), default=0)  # 详情率 = detail/click
    cart_rate = Column(Numeric(6, 4), default=0)  # 加购率 = detail/cart
    checkout_rate = Column(Numeric(6, 4), default=0)  # 下单率 = cart/checkout
    payment_rate = Column(Numeric(6, 4), default=0)  # 支付率 = checkout/payment
    overall_conversion_rate = Column(Numeric(6, 4), default=0)  # 整体转化率 = impression/payment

    # 维度
    organizer_id = Column(String(64), index=True)  # 团长 ID
    community_id = Column(String(64), index=True)  # 社区 ID
    product_id = Column(String(64), index=True)  # 商品 ID (可选)
    channel = Column(String(32))  # 流量渠道 (app/web/wechat)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_funnel_date_period", "funnel_date", "period_type"),
    )


class UserRetentionEntity(Base):
    """用户留存分析实体"""
    __tablename__ = "user_retentions"

    id = Column(String(64), primary_key=True)
    cohort_date = Column(Date, nullable=False, index=True)  # 队列日期 (用户首次购买日期)
    cohort_type = Column(String(32), default="daily")  # daily/weekly/monthly

    #  cohort 规模
    cohort_size = Column(Integer, default=0)  # 队列用户数

    # 各期留存用户数 (动态 JSON 存储)
    # 格式：{"day_1": 100, "day_7": 80, "day_14": 60, "day_30": 40}
    retention_users = Column(JSON)
    # 各期留存率
    # 格式：{"day_1": 0.8, "day_7": 0.6, "day_14": 0.45, "day_30": 0.3}
    retention_rates = Column(JSON)

    # 统计周期
    period_days = Column(Integer, default=30)  # 统计天数

    # 维度
    organizer_id = Column(String(64), index=True)
    community_id = Column(String(64), index=True)
    user_segment = Column(Enum(UserSegment))  # 用户分群

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_retention_cohort", "cohort_date", "cohort_type"),
    )


class UserBehaviorEntity(Base):
    """用户行为分析实体 - 单用户行为追踪汇总"""
    __tablename__ = "user_behaviors"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    behavior_date = Column(Date, nullable=False, index=True)

    # 行为统计
    view_count = Column(Integer, default=0)  # 浏览次数
    click_count = Column(Integer, default=0)  # 点击次数
    cart_count = Column(Integer, default=0)  # 加购次数
    order_count = Column(Integer, default=0)  # 下单次数
    payment_count = Column(Integer, default=0)  # 支付次数

    # 时间指标
    total_session_time = Column(Integer, default=0)  # 总会话时长 (秒)
    session_count = Column(Integer, default=0)  # 会话次数
    avg_session_time = Column(Numeric(8, 2), default=0)  # 平均会话时长

    # 偏好
    favorite_category = Column(String(64))  # 偏好分类
    favorite_price_range = Column(String(32))  # 偏好价格带 (0-50/50-100/100+)

    # 价值
    total_spent = Column(Numeric(12, 2), default=0)  # 当日消费金额
    accumulated_spent = Column(Numeric(14, 2), default=0)  # 累计消费金额

    # 分群
    user_segment = Column(Enum(UserSegment), default=UserSegment.ACTIVE_USER)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_user_behavior_date", "user_id", "behavior_date"),
    )


# ====================  商品分析实体  ====================

class ProductSalesRankEntity(Base):
    """商品销售排行实体"""
    __tablename__ = "product_sales_ranks"

    id = Column(String(64), primary_key=True)
    rank_date = Column(Date, nullable=False, index=True)  # 排行日期
    period_type = Column(String(32), default="daily")  # daily/weekly/monthly
    rank_type = Column(String(32), default="sales")  # sales/quantity/profit

    # 排名维度
    organizer_id = Column(String(64), index=True)  # 团长 ID
    community_id = Column(String(64), index=True)  # 社区 ID
    category = Column(String(64), index=True)  # 商品分类

    # 排名数据 (JSON 数组存储 TOP N)
    # 格式：[{"rank": 1, "product_id": "xxx", "product_name": "xxx", "sales": 1000, "quantity": 50}]
    top_products = Column(JSON)

    # 统计信息
    total_products = Column(Integer, default=0)  # 参与排名的商品总数
    total_sales = Column(Numeric(14, 2), default=0)  # 总销售额

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ProductTurnoverEntity(Base):
    """商品库存周转分析实体"""
    __tablename__ = "product_turnovers"

    id = Column(String(64), primary_key=True)
    product_id = Column(String(64), nullable=False, index=True)
    organizer_id = Column(String(64), index=True)
    analysis_date = Column(Date, nullable=False, index=True)

    # 库存指标
    beginning_inventory = Column(Integer, default=0)  # 期初库存
    ending_inventory = Column(Integer, default=0)  # 期末库存
    avg_inventory = Column(Integer, default=0)  # 平均库存
    sold_quantity = Column(Integer, default=0)  # 销售数量

    # 周转指标
    turnover_rate = Column(Numeric(8, 4), default=0)  # 库存周转率 = 销售数量 / 平均库存
    turnover_days = Column(Numeric(8, 2), default=0)  # 周转天数 = 365 / 周转率

    # 健康度评估
    health_status = Column(String(32))  # healthy/overstock/risk
    # 建议
    suggestion = Column(String(256))  # 备货建议

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_product_turnover_date", "product_id", "analysis_date"),
    )


class ProductProfitEntity(Base):
    """商品利润分析实体"""
    __tablename__ = "product_profits"

    id = Column(String(64), primary_key=True)
    product_id = Column(String(64), nullable=False, index=True)
    organizer_id = Column(String(64), index=True)
    analysis_date = Column(Date, nullable=False, index=True)
    period_type = Column(String(32), default="daily")

    # 收入
    revenue = Column(Numeric(14, 2), default=0)  # 销售收入
    quantity = Column(Integer, default=0)  # 销售数量

    # 成本
    cost = Column(Numeric(14, 2), default=0)  # 商品成本
    commission = Column(Numeric(14, 2), default=0)  # 团长佣金
    platform_fee = Column(Numeric(14, 2), default=0)  # 平台费用
    logistics = Column(Numeric(14, 2), default=0)  # 物流成本
    total_cost = Column(Numeric(14, 2), default=0)  # 总成本

    # 利润
    gross_profit = Column(Numeric(14, 2), default=0)  # 毛利润
    net_profit = Column(Numeric(14, 2), default=0)  # 净利润
    profit_margin = Column(Numeric(6, 4), default=0)  # 利润率

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ====================  预测分析实体  ====================

class SalesPredictionEntity(Base):
    """销量预测实体"""
    __tablename__ = "sales_predictions"

    id = Column(String(64), primary_key=True)
    product_id = Column(String(64), nullable=False, index=True)
    organizer_id = Column(String(64), index=True)
    community_id = Column(String(64), index=True)

    # 预测信息
    predict_date = Column(Date, nullable=False, index=True)  # 预测目标日期
    predicted_quantity = Column(Integer, default=0)  # 预测销量
    predicted_sales = Column(Numeric(14, 2), default=0)  # 预测销售额

    # 置信度
    confidence_level = Column(Numeric(5, 4), default=0)  # 置信度 (0-1)
    prediction_range_low = Column(Integer, default=0)  # 预测下限
    prediction_range_high = Column(Integer, default=0)  # 预测上限

    # 模型信息
    model_name = Column(String(64))  # 使用的模型名称
    model_version = Column(String(32))  # 模型版本

    # 实际值 (用于模型评估)
    actual_quantity = Column(Integer)  # 实际销量
    actual_sales = Column(Numeric(14, 2))  # 实际销售额
    error_rate = Column(Numeric(6, 4))  # 误差率
    is_accurate = Column(Boolean)  # 是否准确 (误差<20%)

    # 预测时间
    predicted_at = Column(DateTime, default=datetime.now)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_prediction_product_date", "product_id", "predict_date"),
    )


class SalesTrendEntity(Base):
    """销售趋势分析实体"""
    __tablename__ = "sales_trends"

    id = Column(String(64), primary_key=True)
    trend_date = Column(Date, nullable=False, index=True)
    period_type = Column(String(32), default="daily")

    # 维度
    organizer_id = Column(String(64), index=True)
    community_id = Column(String(64), index=True)
    category = Column(String(64), index=True)

    # 趋势指标
    current_value = Column(Numeric(14, 2), default=0)  # 当前值
    prev_value = Column(Numeric(14, 2), default=0)  # 上期值
    change_value = Column(Numeric(14, 2), default=0)  # 变化值
    change_rate = Column(Numeric(6, 4), default=0)  # 变化率

    # 趋势方向
    trend_direction = Column(Enum(TrendDirection), default=TrendDirection.STABLE)
    trend_strength = Column(String(32))  # strong/moderate/weak

    # 移动平均
    ma_7d = Column(Numeric(14, 2))  # 7 日移动平均
    ma_30d = Column(Numeric(14, 2))  # 30 日移动平均

    # 季节性因子
    seasonal_factor = Column(Numeric(6, 4), default=1.0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ====================  自定义报表实体  ====================

class CustomReportEntity(Base):
    """自定义报表实体"""
    __tablename__ = "custom_reports"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    report_name = Column(String(128), nullable=False)
    report_description = Column(Text)

    # 报表配置 (JSON 格式)
    # 格式：
    # {
    #     "dimensions": ["date", "product", "community"],
    #     "metrics": ["gmv", "orders", "users"],
    #     "filters": [{"field": "status", "op": "=", "value": "completed"}],
    #     "group_by": ["category"],
    #     "order_by": {"field": "gmv", "direction": "desc"},
    #     "limit": 100
    # }
    config = Column(JSON, nullable=False)

    # 报表类型
    report_type = Column(String(32), default="custom")  # custom/template
    template_id = Column(String(64))  # 模板 ID (如果使用模板)

    # 调度配置 (可选)
    schedule_enabled = Column(Boolean, default=False)
    schedule_cron = Column(String(64))  # cron 表达式
    schedule_recipients = Column(JSON)  # 接收者列表

    # 状态
    is_active = Column(Boolean, default=True)
    last_generated_at = Column(DateTime)
    next_run_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CustomReportResultEntity(Base):
    """自定义报表结果实体"""
    __tablename__ = "custom_report_results"

    id = Column(String(64), primary_key=True)
    report_id = Column(String(64), ForeignKey("custom_reports.id"), nullable=False, index=True)
    generated_at = Column(DateTime, nullable=False, index=True)

    # 查询结果 (JSON 格式)
    # 格式：
    # {
    #     "columns": ["date", "category", "gmv", "orders"],
    #     "data": [
    #         {"date": "2026-04-05", "category": "fruit", "gmv": 1000, "orders": 50},
    #         ...
    #     ],
    #     "summary": {"total_gmv": 10000, "total_orders": 500}
    # }
    result_data = Column(JSON, nullable=False)

    # 执行信息
    execution_time_ms = Column(Integer)  # 执行耗时 (毫秒)
    row_count = Column(Integer)  # 结果行数
    status = Column(String(32), default="success")  # success/failed
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.now)
