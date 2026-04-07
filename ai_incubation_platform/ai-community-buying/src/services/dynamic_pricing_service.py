"""
P1 动态定价引擎 - 服务层

提供以下核心能力：
1. 基于成团概率的动态定价
2. 基于需求弹性的价格优化
3. 竞品价格对比与跟随
4. 价格历史追踪
5. 价格弹性 A/B 测试
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from sqlalchemy.sql import func as sql_func
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import json
import logging
import math

from models.pricing_entities import (
    DynamicPriceEntity, PriceHistoryEntity, PricingStrategyEntity,
    PriceElasticityTestEntity, CompetitorPriceEntity
)
from models.entities import OrderEntity, GroupBuyEntity, ProductEntity
from models.product import OrderStatus
from models.dynamic_pricing import (
    PricingStrategyType, PriceAdjustmentReason, PriceStatus,
    DynamicPrice, PriceHistory, PricingStrategy, PriceElasticityTest
)
from core.logging_config import get_logger

logger = get_logger("services.dynamic_pricing")


class DynamicPricingService:
    """动态定价服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""

    def set_request_context(self, request_id: str, user_id: str = ""):
        """设置请求上下文"""
        self.request_id = request_id
        self.user_id = user_id

    def _log(self, level: str, message: str, extra: dict = None):
        """结构化日志"""
        log_data = {"request_id": self.request_id, "user_id": self.user_id}
        if extra:
            log_data.update(extra)
        getattr(self.logger, level)(message, extra=log_data)

    # ==================== 动态价格管理 ====================

    def create_dynamic_price(self, data: Dict) -> Tuple[Optional[DynamicPriceEntity], bool]:
        """创建动态价格配置"""
        try:
            # 检查是否已存在
            existing = self.db.query(DynamicPriceEntity).filter(
                and_(
                    DynamicPriceEntity.product_id == data["product_id"],
                    DynamicPriceEntity.community_id == data["community_id"]
                )
            ).first()

            if existing:
                self._log("warning", "动态价格已存在，执行更新", {
                    "product_id": data["product_id"],
                    "community_id": data["community_id"]
                })
                return self.update_dynamic_price(existing.id, data)

            min_price = data.get("min_price", data["base_price"] * 0.8)
            max_price = data.get("max_price", data["base_price"] * 1.5)

            entity = DynamicPriceEntity(
                product_id=data["product_id"],
                community_id=data["community_id"],
                base_price=data["base_price"],
                current_price=data["base_price"],
                min_price=min_price,
                max_price=max_price,
                strategy_type=data.get("strategy_type", PricingStrategyType.STATIC),
                strategy_config=json.dumps(data.get("strategy_config", {})),
                status=PriceStatus.ACTIVE
            )

            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)

            self._log("info", "动态价格创建成功", {
                "price_id": entity.id,
                "product_id": entity.product_id,
                "current_price": entity.current_price
            })

            return entity, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建动态价格失败：{str(e)}", {"data": data})
            return None, False

    def update_dynamic_price(self, price_id: str, data: Dict) -> Tuple[Optional[DynamicPriceEntity], bool]:
        """更新动态价格"""
        try:
            entity = self.db.query(DynamicPriceEntity).filter(
                DynamicPriceEntity.id == price_id
            ).first()

            if not entity:
                self._log("error", "动态价格不存在", {"price_id": price_id})
                return None, False

            # 记录价格历史（如果价格有变化）
            if data.get("current_price") and data["current_price"] != entity.current_price:
                self._record_price_history(
                    entity,
                    entity.current_price,
                    data["current_price"],
                    data.get("adjustment_reason", PriceAdjustmentReason.MANUAL_ADJUST)
                )

            # 更新字段
            if "current_price" in data:
                entity.current_price = data["current_price"]
            if "adjustment_amount" in data:
                entity.adjustment_amount = data["adjustment_amount"]
            if "adjustment_percentage" in data:
                entity.adjustment_percentage = data["adjustment_percentage"]
            if "adjustment_reason" in data:
                entity.adjustment_reason = data["adjustment_reason"]
            if "strategy_config" in data:
                entity.strategy_config = json.dumps(data["strategy_config"])
            if "status" in data:
                entity.status = data["status"]
            if "effective_to" in data:
                entity.effective_to = data["effective_to"]
            if "min_price" in data:
                entity.min_price = data["min_price"]
            if "max_price" in data:
                entity.max_price = data["max_price"]

            entity.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(entity)

            self._log("info", "动态价格更新成功", {
                "price_id": price_id,
                "current_price": entity.current_price
            })

            return entity, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"更新动态价格失败：{str(e)}", {"price_id": price_id})
            return None, False

    def _record_price_history(self, price_entity: DynamicPriceEntity, old_price: float,
                              new_price: float, reason: PriceAdjustmentReason,
                              trigger_source: str = "system", trigger_id: str = None,
                              extra_data: Dict = None):
        """记录价格历史"""
        try:
            history = PriceHistoryEntity(
                product_id=price_entity.product_id,
                community_id=price_entity.community_id,
                old_price=old_price,
                new_price=new_price,
                adjustment_amount=new_price - old_price,
                adjustment_reason=reason,
                strategy_type=price_entity.strategy_type,
                trigger_source=trigger_source,
                trigger_id=trigger_id,
                extra_data=json.dumps(extra_data or {})
            )
            self.db.add(history)
        except Exception as e:
            self._log("error", f"记录价格历史失败：{str(e)}")

    def get_dynamic_price(self, price_id: str) -> Optional[DynamicPriceEntity]:
        """获取动态价格详情"""
        return self.db.query(DynamicPriceEntity).filter(
            DynamicPriceEntity.id == price_id
        ).first()

    def get_price_for_product(self, product_id: str, community_id: str) -> Optional[DynamicPriceEntity]:
        """获取商品在指定社区的价格"""
        return self.db.query(DynamicPriceEntity).filter(
            and_(
                DynamicPriceEntity.product_id == product_id,
                DynamicPriceEntity.community_id == community_id,
                DynamicPriceEntity.status == PriceStatus.ACTIVE
            )
        ).first()

    def list_prices(self, product_id: str = None, community_id: str = None,
                    status: PriceStatus = None, limit: int = 100) -> List[DynamicPriceEntity]:
        """获取价格列表"""
        query = self.db.query(DynamicPriceEntity)

        if product_id:
            query = query.filter(DynamicPriceEntity.product_id == product_id)
        if community_id:
            query = query.filter(DynamicPriceEntity.community_id == community_id)
        if status:
            query = query.filter(DynamicPriceEntity.status == status)

        return query.order_by(DynamicPriceEntity.updated_at.desc()).limit(limit).all()

    def get_price_history(self, product_id: str, community_id: str = None,
                          hours: int = 24) -> List[PriceHistoryEntity]:
        """获取价格历史"""
        query = self.db.query(PriceHistoryEntity).filter(
            PriceHistoryEntity.product_id == product_id
        )

        if community_id:
            query = query.filter(PriceHistoryEntity.community_id == community_id)

        cutoff_time = datetime.now() - timedelta(hours=hours)
        query = query.filter(PriceHistoryEntity.created_at >= cutoff_time)

        return query.order_by(PriceHistoryEntity.created_at.desc()).all()

    # ==================== 核心定价算法 ====================

    def calculate_dynamic_price(self, product_id: str, community_id: str,
                                context: Dict = None) -> Dict:
        """
        计算动态价格

        Args:
            product_id: 商品 ID
            community_id: 社区 ID
            context: 上下文信息（包含团购、需求、竞品等数据）

        Returns:
            价格计算结果
        """
        # 获取动态价格配置
        price_entity = self.get_price_for_product(product_id, community_id)

        if not price_entity:
            # 没有动态价格配置，返回基础价格
            product = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
            if product:
                return {
                    "product_id": product_id,
                    "community_id": community_id,
                    "base_price": product.price,
                    "current_price": product.price,
                    "adjustment": 0,
                    "reason": "no_dynamic_pricing_config",
                    "strategy": "static"
                }
            return {"error": "product_not_found"}

        # 获取激活的定价策略
        strategies = self.db.query(PricingStrategyEntity).filter(
            PricingStrategyEntity.is_active == True
        ).order_by(PricingStrategyEntity.priority.desc()).all()

        total_adjustment = 0.0
        applied_reasons = []
        applied_strategies = []

        for strategy in strategies:
            config = json.loads(strategy.config) if strategy.config else {}
            adjustment, reason = self._evaluate_strategy(strategy, price_entity, context or {}, config)

            if adjustment != 0:
                total_adjustment += adjustment
                applied_reasons.append(reason)
                applied_strategies.append(strategy.strategy_type.value)

        # 应用价格边界
        new_price = price_entity.base_price + total_adjustment
        new_price = max(price_entity.min_price, min(price_entity.max_price, new_price))

        # 确定主要原因
        main_reason = applied_reasons[0] if applied_reasons else PriceAdjustmentReason.MANUAL_ADJUST

        return {
            "product_id": product_id,
            "community_id": community_id,
            "base_price": price_entity.base_price,
            "current_price": new_price,
            "adjustment": new_price - price_entity.base_price,
            "adjustment_percentage": (new_price - price_entity.base_price) / price_entity.base_price if price_entity.base_price > 0 else 0,
            "reason": main_reason,
            "strategies_applied": applied_strategies,
            "min_price": price_entity.min_price,
            "max_price": price_entity.max_price
        }

    def _evaluate_strategy(self, strategy: PricingStrategyEntity, price_entity: DynamicPriceEntity,
                           context: Dict, config: Dict) -> Tuple[float, PriceAdjustmentReason]:
        """评估单个策略，返回价格调整和原因"""
        strategy_type = strategy.strategy_type

        if strategy_type == PricingStrategyType.DYNAMIC_GROUP:
            return self._evaluate_group_probability_strategy(price_entity, context, config)
        elif strategy_type == PricingStrategyType.DEMAND_BASED:
            return self._evaluate_demand_based_strategy(price_entity, context, config)
        elif strategy_type == PricingStrategyType.COMPETITOR_BASED:
            return self._evaluate_competitor_based_strategy(price_entity, context, config)
        elif strategy_type == PricingStrategyType.TIME_BASED:
            return self._evaluate_time_based_strategy(price_entity, context, config)
        elif strategy_type == PricingStrategyType.INVENTORY_BASED:
            return self._evaluate_inventory_based_strategy(price_entity, context, config)

        return 0.0, None

    def _evaluate_group_probability_strategy(self, price_entity: DynamicPriceEntity,
                                              context: Dict, config: Dict) -> Tuple[float, PriceAdjustmentReason]:
        """基于成团概率的定价策略"""
        group_probability = context.get("group_probability", 0.5)
        min_probability = config.get("min_group_probability", 0.3)
        price_elasticity = config.get("price_elasticity", 0.5)

        if group_probability < min_probability:
            # 成团概率低，降价刺激
            adjustment = -price_entity.base_price * price_elasticity * (min_probability - group_probability)
            return adjustment, PriceAdjustmentReason.LOW_GROUP_PROBABILITY

        return 0.0, None

    def _evaluate_demand_based_strategy(self, price_entity: DynamicPriceEntity,
                                         context: Dict, config: Dict) -> Tuple[float, PriceAdjustmentReason]:
        """基于需求弹性的定价策略"""
        demand_level = context.get("demand_level", 0.5)  # 0-1, 1 表示高需求
        demand_low = config.get("demand_threshold_low", 0.3)
        demand_high = config.get("demand_threshold_high", 0.7)
        adjustment_low = config.get("price_adjustment_low", -0.1)
        adjustment_high = config.get("price_adjustment_high", 0.1)

        if demand_level < demand_low:
            # 需求低，降价
            adjustment = price_entity.base_price * adjustment_low
            return adjustment, PriceAdjustmentReason.LOW_DEMAND
        elif demand_level > demand_high:
            # 需求高，涨价
            adjustment = price_entity.base_price * adjustment_high
            return adjustment, PriceAdjustmentReason.HIGH_DEMAND

        return 0.0, None

    def _evaluate_competitor_based_strategy(self, price_entity: DynamicPriceEntity,
                                             context: Dict, config: Dict) -> Tuple[float, PriceAdjustmentReason]:
        """基于竞品价格的定价策略"""
        follow_competitor = config.get("follow_competitor", True)
        price_match_pct = config.get("price_match_percentage", 0.95)
        min_margin = config.get("min_margin", 0.1)

        competitor_price = context.get("competitor_price")
        if not competitor_price or not follow_competitor:
            return 0.0, None

        # 计算目标价格
        target_price = competitor_price * price_match_pct

        # 确保不低于最低利润率
        min_price_with_margin = price_entity.base_price * (1 - min_margin)
        target_price = max(target_price, min_price_with_margin)

        adjustment = target_price - price_entity.base_price

        if adjustment < 0:
            return adjustment, PriceAdjustmentReason.LOW_COMPETITOR_PRICE
        elif adjustment > 0:
            return adjustment, PriceAdjustmentReason.HIGH_COMPETITOR_PRICE

        return 0.0, None

    def _evaluate_time_based_strategy(self, price_entity: DynamicPriceEntity,
                                      context: Dict, config: Dict) -> Tuple[float, PriceAdjustmentReason]:
        """基于时间段的定价策略"""
        current_hour = datetime.now().hour
        peak_hours = config.get("peak_hours", [9, 10, 11, 20, 21])
        peak_adjustment = config.get("peak_adjustment", 0.05)
        off_peak_adjustment = config.get("off_peak_adjustment", -0.05)

        if current_hour in peak_hours:
            return price_entity.base_price * peak_adjustment, PriceAdjustmentReason.PEAK_TIME
        else:
            return price_entity.base_price * off_peak_adjustment, PriceAdjustmentReason.OFF_PEAK_TIME

    def _evaluate_inventory_based_strategy(self, price_entity: DynamicPriceEntity,
                                           context: Dict, config: Dict) -> Tuple[float, PriceAdjustmentReason]:
        """基于库存压力的定价策略"""
        product = self.db.query(ProductEntity).filter(
            ProductEntity.id == price_entity.product_id
        ).first()

        if not product or product.stock == 0:
            return 0.0, None

        stock_ratio = (product.stock - product.sold_stock) / product.stock
        high_stock_threshold = config.get("high_stock_threshold", 0.8)
        low_stock_threshold = config.get("low_stock_threshold", 0.2)
        high_stock_adjustment = config.get("high_stock_adjustment", -0.1)

        if stock_ratio > high_stock_threshold:
            # 库存压力大，降价促销
            adjustment = price_entity.base_price * high_stock_adjustment
            return adjustment, PriceAdjustmentReason.INVENTORY_PRESSURE

        return 0.0, None

    # ==================== 价格弹性测试 ====================

    def create_elasticity_test(self, data: Dict) -> Tuple[Optional[PriceElasticityTestEntity], bool]:
        """创建价格弹性测试"""
        try:
            entity = PriceElasticityTestEntity(
                product_id=data["product_id"],
                community_id=data["community_id"],
                test_name=data["test_name"],
                control_price=data["control_price"],
                variant_prices=json.dumps(data["variant_prices"]),
                traffic_allocation=json.dumps(data["traffic_allocation"]),
                target_metric=data.get("target_metric", "conversion_rate"),
                status="pending"
            )

            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)

            self._log("info", "价格弹性测试创建成功", {
                "test_id": entity.id,
                "test_name": entity.test_name
            })

            return entity, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建价格弹性测试失败：{str(e)}", {"data": data})
            return None, False

    def start_elasticity_test(self, test_id: str) -> Tuple[bool, str]:
        """启动价格弹性测试"""
        entity = self.db.query(PriceElasticityTestEntity).filter(
            PriceElasticityTestEntity.id == test_id
        ).first()

        if not entity:
            return False, "测试不存在"

        if entity.status != "pending":
            return False, f"测试状态不正确：{entity.status}"

        entity.status = "running"
        entity.start_time = datetime.now()
        entity.updated_at = datetime.now()

        self.db.commit()
        self._log("info", "价格弹性测试已启动", {"test_id": test_id})

        return True, "测试已启动"

    def complete_elasticity_test(self, test_id: str, control_metrics: Dict,
                                  variant_metrics: Dict) -> Tuple[bool, float]:
        """完成价格弹性测试并计算弹性系数"""
        entity = self.db.query(PriceElasticityTestEntity).filter(
            PriceElasticityTestEntity.id == test_id
        ).first()

        if not entity:
            self._log("error", "测试不存在", {"test_id": test_id})
            return False, 0.0

        variant_prices = json.loads(entity.variant_prices)

        # 计算弹性系数
        control_conversion = control_metrics.get("conversion_rate", 0)
        variant_conversion = variant_metrics.get("conversion_rate", 0)

        if control_conversion == 0 or entity.control_price == 0:
            self._log("warning", "无法计算弹性系数，数据不足", {"test_id": test_id})
            return False, 0.0

        demand_change_pct = (variant_conversion - control_conversion) / control_conversion
        price_change_pct = (variant_prices[0] - entity.control_price) / entity.control_price

        if price_change_pct == 0:
            elasticity = 0.0
        else:
            elasticity = demand_change_pct / price_change_pct

        entity.control_metrics = json.dumps(control_metrics)
        entity.variant_metrics = json.dumps(variant_metrics)
        entity.elasticity_coefficient = elasticity
        entity.status = "completed"
        entity.end_time = datetime.now()
        entity.updated_at = datetime.now()

        self.db.commit()
        self._log("info", "价格弹性测试已完成", {
            "test_id": test_id,
            "elasticity": elasticity
        })

        return True, elasticity

    def get_elasticity_test(self, test_id: str) -> Optional[PriceElasticityTestEntity]:
        """获取弹性测试详情"""
        return self.db.query(PriceElasticityTestEntity).filter(
            PriceElasticityTestEntity.id == test_id
        ).first()

    # ==================== 竞品价格追踪 ====================

    def update_competitor_price(self, data: Dict) -> Tuple[Optional[CompetitorPriceEntity], bool]:
        """更新竞品价格"""
        try:
            # 检查是否已存在
            existing = self.db.query(CompetitorPriceEntity).filter(
                and_(
                    CompetitorPriceEntity.product_id == data["product_id"],
                    CompetitorPriceEntity.competitor_name == data["competitor_name"]
                )
            ).first()

            if existing:
                existing.competitor_price = data["competitor_price"]
                existing.competitor_stock_status = data.get("competitor_stock_status", "in_stock")
                existing.crawled_at = datetime.now()
                existing.updated_at = datetime.now()
            else:
                entity = CompetitorPriceEntity(
                    product_id=data["product_id"],
                    competitor_name=data["competitor_name"],
                    competitor_product_id=data.get("competitor_product_id"),
                    competitor_price=data["competitor_price"],
                    competitor_stock_status=data.get("competitor_stock_status", "in_stock")
                )
                self.db.add(entity)

            self.db.commit()

            self._log("info", "竞品价格更新成功", {
                "product_id": data["product_id"],
                "competitor": data["competitor_name"],
                "price": data["competitor_price"]
            })

            return existing or entity, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"更新竞品价格失败：{str(e)}", {"data": data})
            return None, False

    def get_competitor_prices(self, product_id: str) -> List[CompetitorPriceEntity]:
        """获取商品的竞品价格"""
        return self.db.query(CompetitorPriceEntity).filter(
            CompetitorPriceEntity.product_id == product_id
        ).all()

    # ==================== 定价策略管理 ====================

    def create_strategy(self, data: Dict) -> Tuple[Optional[PricingStrategyEntity], bool]:
        """创建定价策略"""
        try:
            entity = PricingStrategyEntity(
                name=data["name"],
                strategy_type=data["strategy_type"],
                description=data.get("description"),
                is_active=data.get("is_active", True),
                priority=data.get("priority", 0),
                config=json.dumps(data.get("config", {}))
            )

            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)

            self._log("info", "定价策略创建成功", {
                "strategy_id": entity.id,
                "name": entity.name
            })

            return entity, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建定价策略失败：{str(e)}", {"data": data})
            return None, False

    def list_strategies(self, is_active: bool = True) -> List[PricingStrategyEntity]:
        """获取定价策略列表"""
        query = self.db.query(PricingStrategyEntity)
        if is_active:
            query = query.filter(PricingStrategyEntity.is_active == True)
        return query.order_by(PricingStrategyEntity.priority.desc()).all()

    # ==================== 统计报表 ====================

    def get_price_stats(self, product_id: str = None, days: int = 7) -> Dict:
        """获取价格统计"""
        cutoff_time = datetime.now() - timedelta(days=days)

        query = self.db.query(
            PriceHistoryEntity.product_id,
            func.count(PriceHistoryEntity.id).label("adjustment_count"),
            func.avg(PriceHistoryEntity.old_price).label("avg_old_price"),
            func.avg(PriceHistoryEntity.new_price).label("avg_new_price"),
            func.avg(PriceHistoryEntity.adjustment_amount).label("avg_adjustment")
        ).filter(
            PriceHistoryEntity.created_at >= cutoff_time
        )

        if product_id:
            query = query.filter(PriceHistoryEntity.product_id == product_id)

        result = query.group_by(PriceHistoryEntity.product_id).all()

        return {
            "period_days": days,
            "products": [
                {
                    "product_id": r.product_id,
                    "adjustment_count": r.adjustment_count,
                    "avg_old_price": r.avg_old_price,
                    "avg_new_price": r.avg_new_price,
                    "avg_adjustment": r.avg_adjustment
                }
                for r in result
            ]
        }
