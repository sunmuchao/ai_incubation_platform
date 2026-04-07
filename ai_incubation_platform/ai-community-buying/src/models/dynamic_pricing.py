"""
P1 动态定价引擎 - 模型定义

包含：
1. 价格实体模型
2. 定价策略模型
3. 价格历史记录
4. 价格弹性测试
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
import uuid


class PricingStrategyType(str, Enum):
    """定价策略类型"""
    STATIC = "static"              # 固定价格
    DYNAMIC_GROUP = "dynamic_group" # 基于成团概率的动态定价
    DEMAND_BASED = "demand_based"   # 基于需求弹性定价
    COMPETITOR_BASED = "competitor_based"  # 竞品价格跟随
    TIME_BASED = "time_based"       # 时间段定价
    INVENTORY_BASED = "inventory_based"  # 库存压力定价
    PERSONALIZED = "personalized"   # 个性化定价


class PriceAdjustmentReason(str, Enum):
    """价格调整原因"""
    LOW_DEMAND = "low_demand"          # 需求不足
    HIGH_DEMAND = "high_demand"        # 需求旺盛
    LOW_GROUP_PROBABILITY = "low_group_probability"  # 成团概率低
    HIGH_COMPETITOR_PRICE = "high_competitor_price"  # 竞品价格高
    LOW_COMPETITOR_PRICE = "low_competitor_price"    # 竞品价格低
    INVENTORY_PRESSURE = "inventory_pressure"  # 库存压力
    PEAK_TIME = "peak_time"            # 高峰时段
    OFF_PEAK_TIME = "off_peak_time"    # 低峰时段
    PROMOTION = "promotion"            # 促销活动
    MANUAL_ADJUST = "manual_adjust"    # 手动调整


class PriceStatus(str, Enum):
    """价格状态"""
    ACTIVE = "active"      # 生效中
    EXPIRED = "expired"    # 已过期
    SCHEDULED = "scheduled" # 待生效


class DynamicPrice(BaseModel):
    """动态价格模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    community_id: str
    base_price: float  # 基础价格
    current_price: float  # 当前价格
    min_price: float  # 最低价格（保护价）
    max_price: float  # 最高价格（限价）
    adjustment_amount: float = 0.0  # 调整金额（正数涨价，负数降价）
    adjustment_percentage: float = 0.0  # 调整百分比
    adjustment_reason: Optional[PriceAdjustmentReason] = None
    strategy_type: PricingStrategyType = PricingStrategyType.STATIC
    strategy_config: Optional[Dict] = None  # 策略配置
    status: PriceStatus = PriceStatus.ACTIVE
    effective_from: datetime = Field(default_factory=datetime.now)
    effective_to: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def apply_adjustment(self, amount: float, reason: PriceAdjustmentReason):
        """应用价格调整"""
        self.adjustment_amount = amount
        self.adjustment_percentage = amount / self.base_price if self.base_price > 0 else 0
        self.adjustment_reason = reason
        self.current_price = max(self.min_price, min(self.max_price, self.base_price + amount))
        self.updated_at = datetime.now()

    def get_price_info(self) -> Dict:
        """获取价格信息"""
        return {
            "product_id": self.product_id,
            "community_id": self.community_id,
            "base_price": self.base_price,
            "current_price": self.current_price,
            "adjustment": self.adjustment_amount,
            "adjustment_percentage": f"{self.adjustment_percentage * 100:.2f}%",
            "reason": self.adjustment_reason.value if self.adjustment_reason else None,
            "strategy": self.strategy_type.value,
            "status": self.status.value
        }


class PriceHistory(BaseModel):
    """价格历史记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    community_id: str
    old_price: float
    new_price: float
    adjustment_amount: float
    adjustment_reason: Optional[PriceAdjustmentReason] = None
    strategy_type: PricingStrategyType
    trigger_source: str  # 触发来源：system/user/api
    trigger_id: Optional[str] = None  # 触发源 ID（如预测 ID、订单 ID）
    extra_data: Optional[Dict] = None  # 额外数据
    created_at: datetime = Field(default_factory=datetime.now)


class PricingStrategy(BaseModel):
    """定价策略模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    strategy_type: PricingStrategyType
    description: Optional[str] = None
    is_active: bool = True
    priority: int = 0  # 优先级，数字越大优先级越高
    config: Dict = Field(default_factory=dict)  # 策略配置
    # 策略参数示例：
    # dynamic_group: {min_group_probability: 0.3, price_elasticity: 0.5}
    # demand_based: {demand_threshold_low: 0.3, demand_threshold_high: 0.7, price_adjustment_low: -0.1, price_adjustment_high: 0.1}
    # competitor_based: {follow_competitor: true, price_match_percentage: 0.95, min_margin: 0.1}
    # time_based: {peak_hours: [9, 10, 11, 20, 21], peak_adjustment: 0.05, off_peak_adjustment: -0.05}
    # inventory_based: {high_stock_threshold: 0.8, low_stock_threshold: 0.2, high_stock_adjustment: -0.1, low_stock_adjustment: 0.05}
    # personalized: {user_segment_config: {...}}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def evaluate(self, context: Dict) -> Optional[float]:
        """
        评估策略，返回建议的价格调整金额
        需要在服务层实现具体逻辑
        """
        return None


class PriceElasticityTest(BaseModel):
    """价格弹性测试（A/B 测试）"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    community_id: str
    test_name: str
    # 对照组价格
    control_price: float
    # 实验组价格（可以有多个）
    variant_prices: List[float]
    # 测试配置
    traffic_allocation: Dict[str, float] = Field(default_factory=dict)  # 流量分配，如 {"control": 0.5, "variant_a": 0.5}
    # 测试指标
    target_metric: str = "conversion_rate"  # conversion_rate, gmv, profit
    # 测试结果
    control_metrics: Optional[Dict] = None  # 对照组指标
    variant_metrics: Optional[Dict] = None  # 实验组指标
    elasticity_coefficient: Optional[float] = None  # 价格弹性系数
    # 测试状态
    status: str = "pending"  # pending, running, completed, stopped
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def calculate_elasticity(self) -> Optional[float]:
        """计算价格弹性系数"""
        if not self.control_metrics or not self.variant_metrics:
            return None

        # 弹性系数 = (需求变化百分比) / (价格变化百分比)
        control_conversion = self.control_metrics.get("conversion_rate", 0)
        variant_conversion = self.variant_metrics.get("conversion_rate", 0)

        if control_conversion == 0 or self.control_price == 0:
            return None

        demand_change_pct = (variant_conversion - control_conversion) / control_conversion
        price_change_pct = (self.variant_prices[0] - self.control_price) / self.control_price

        if price_change_pct == 0:
            return None

        self.elasticity_coefficient = demand_change_pct / price_change_pct
        return self.elasticity_coefficient


class CompetitorPrice(BaseModel):
    """竞品价格信息"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str  # 我方商品 ID
    competitor_name: str  # 竞品平台名称
    competitor_product_id: Optional[str] = None  # 竞品商品 ID
    competitor_price: float  # 竞品价格
    competitor_stock_status: str = "in_stock"  # in_stock, out_of_stock, limited
    price_diff_percentage: float = 0.0  # 价格差异百分比
    crawled_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)


# ========== 请求/响应模型 ==========

class DynamicPriceCreate(BaseModel):
    """创建动态价格请求"""
    product_id: str
    community_id: str
    base_price: float
    min_price: Optional[float] = None  # 默认 base_price * 0.8
    max_price: Optional[float] = None  # 默认 base_price * 1.5
    strategy_type: PricingStrategyType = PricingStrategyType.STATIC
    strategy_config: Optional[Dict] = None


class DynamicPriceUpdate(BaseModel):
    """更新动态价格请求"""
    current_price: Optional[float] = None
    adjustment_amount: Optional[float] = None
    adjustment_reason: Optional[PriceAdjustmentReason] = None
    strategy_config: Optional[Dict] = None
    status: Optional[PriceStatus] = None
    effective_to: Optional[datetime] = None


class PriceAdjustmentRequest(BaseModel):
    """手动调价请求"""
    adjustment_type: str  # absolute: 绝对值，percentage: 百分比
    adjustment_value: float  # 调整值
    reason: PriceAdjustmentReason
    effective_to: Optional[datetime] = None


class PricingStrategyCreate(BaseModel):
    """创建定价策略请求"""
    name: str
    strategy_type: PricingStrategyType
    description: Optional[str] = None
    is_active: bool = True
    priority: int = 0
    config: Dict = Field(default_factory=dict)


class PriceElasticityTestCreate(BaseModel):
    """创建价格弹性测试请求"""
    product_id: str
    community_id: str
    test_name: str
    control_price: float
    variant_prices: List[float]
    traffic_allocation: Dict[str, float]
    target_metric: str = "conversion_rate"
