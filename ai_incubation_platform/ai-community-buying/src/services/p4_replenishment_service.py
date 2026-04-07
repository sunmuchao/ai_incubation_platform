"""
P4 供应链服务 - 智能补货服务
负责销量预测、补货建议生成、补货策略优化
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import logging
import json

from models.entities import ProductEntity, OrderEntity, GroupBuyEntity
from models.p4_entities import ReplenishmentSuggestionEntity
from models.product import OrderStatus
from models.p4_models import Priority, ReplenishmentStatus
from core.logging_config import get_logger

logger = get_logger("services.p4.replenishment")


class ReplenishmentService:
    """智能补货服务"""

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

    def calculate_demand_forecast(self, product_id: str, community_id: str,
                                   days: int = 7) -> Dict:
        """
        计算需求预测

        基于历史销量数据，使用加权移动平均法预测未来需求

        Args:
            product_id: 商品 ID
            community_id: 社区 ID
            days: 预测天数

        Returns:
            预测结果字典
        """
        # 获取历史订单数据（过去 30 天）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # 查询历史销量（按日期分组）
        results = self.db.query(
            func.date(OrderEntity.created_at).label("order_date"),
            func.sum(OrderEntity.quantity).label("daily_quantity")
        ).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(
            OrderEntity.product_id == product_id,
            OrderEntity.status == OrderStatus.COMPLETED,
            OrderEntity.created_at >= start_date,
            OrderEntity.created_at <= end_date
        ).group_by(
            func.date(OrderEntity.created_at)
        ).order_by(
            func.date(OrderEntity.created_at)
        ).all()

        if not results:
            return {
                "product_id": product_id,
                "community_id": community_id,
                "forecast_quantity": 0,
                "confidence": 0.0,
                "message": "无历史数据"
            }

        # 计算加权移动平均（近期权重更高）
        total_weight = 0
        weighted_sum = 0
        for i, r in enumerate(results):
            weight = 1 + (i / len(results))  # 越近的数据权重越高
            weighted_sum += r.daily_quantity * weight
            total_weight += weight

        avg_daily_quantity = weighted_sum / total_weight if total_weight > 0 else 0

        # 预测未来销量
        forecast_quantity = int(avg_daily_quantity * days)

        # 计算置信度（基于数据点数量和历史稳定性）
        data_points = len(results)
        confidence = min(0.9, 0.3 + (data_points / 30) * 0.6)

        # 计算标准差（衡量波动性）
        if len(results) > 1:
            mean = sum(r.daily_quantity for r in results) / len(results)
            variance = sum((r.daily_quantity - mean) ** 2 for r in results) / len(results)
            std_dev = variance ** 0.5
            # 波动性越大，置信度越低
            confidence *= max(0.5, 1 - (std_dev / (mean + 1)))

        return {
            "product_id": product_id,
            "community_id": community_id,
            "forecast_quantity": forecast_quantity,
            "avg_daily_quantity": round(avg_daily_quantity, 2),
            "confidence": round(confidence, 2),
            "historical_days": data_points,
            "method": "weighted_moving_average"
        }

    def generate_replenishment_suggestion(self, product_id: str, community_id: str,
                                           forecast_days: int = 7,
                                           safety_stock_days: int = 3) -> Tuple[Optional[ReplenishmentSuggestionEntity], bool]:
        """
        生成补货建议

        Args:
            product_id: 商品 ID
            community_id: 社区 ID
            forecast_days: 预测天数
            safety_stock_days: 安全库存天数

        Returns:
            (补货建议实体，是否成功)
        """
        try:
            # 获取商品信息
            product = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
            if not product:
                self._log("error", "商品不存在", {"product_id": product_id})
                return None, False

            # 获取需求预测
            forecast = self.calculate_demand_forecast(product_id, community_id, forecast_days)
            predicted_demand = forecast.get("forecast_quantity", 0)
            confidence = forecast.get("confidence", 0.0)

            if predicted_demand <= 0:
                self._log("info", "无需求预测，不生成补货建议", {"product_id": product_id})
                return None, True

            # 计算安全库存
            avg_daily = forecast.get("avg_daily_quantity", 0)
            safety_stock = int(avg_daily * safety_stock_days)

            # 计算建议补货量
            current_stock = product.stock
            suggested_quantity = max(0, predicted_demand + safety_stock - current_stock)

            if suggested_quantity <= 0:
                self._log("info", "库存充足，不需要补货", {
                    "product_id": product_id,
                    "current_stock": current_stock
                })
                return None, True

            # 确定优先级
            if current_stock <= 0:
                priority = Priority.URGENT
            elif current_stock <= safety_stock:
                priority = Priority.HIGH
            elif current_stock <= predicted_demand * 0.5:
                priority = Priority.NORMAL
            else:
                priority = Priority.LOW

            # 计算建议下单日期和预期到货日期
            days_of_stock_left = current_stock / avg_daily if avg_daily > 0 else 0
            suggested_order_date = datetime.now() + timedelta(days=int(days_of_stock_left - forecast_days))
            expected_delivery_date = suggested_order_date + timedelta(days=3)  # 假设 3 天交付周期

            # 检查是否已存在待处理的补货建议
            existing = self.db.query(ReplenishmentSuggestionEntity).filter(
                and_(
                    ReplenishmentSuggestionEntity.product_id == product_id,
                    ReplenishmentSuggestionEntity.community_id == community_id,
                    ReplenishmentSuggestionEntity.status == ReplenishmentStatus.PENDING.value
                )
            ).first()

            if existing:
                self._log("info", "补货建议已存在", {"product_id": product_id, "suggestion_id": existing.id})
                return existing, True

            # 创建补货建议
            suggestion = ReplenishmentSuggestionEntity(
                product_id=product_id,
                community_id=community_id,
                current_stock=current_stock,
                predicted_demand=predicted_demand,
                predicted_days=forecast_days,
                suggested_quantity=suggested_quantity,
                suggested_order_date=suggested_order_date,
                expected_delivery_date=expected_delivery_date,
                priority=priority.value,
                confidence=confidence,
                reason=f"预测{forecast_days}天需求{predicted_demand}件，当前库存{current_stock}件，安全库存{safety_stock}件",
                model_version="v1"
            )

            self.db.add(suggestion)
            self.db.commit()
            self.db.refresh(suggestion)

            self._log("info", "补货建议生成成功", {
                "suggestion_id": suggestion.id,
                "product_id": product_id,
                "suggested_quantity": suggested_quantity,
                "priority": priority.value
            })

            return suggestion, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"生成补货建议失败：{str(e)}", {"product_id": product_id})
            return None, False

    def get_suggestion(self, suggestion_id: str) -> Optional[ReplenishmentSuggestionEntity]:
        """获取补货建议详情"""
        return self.db.query(ReplenishmentSuggestionEntity).filter(
            ReplenishmentSuggestionEntity.id == suggestion_id
        ).first()

    def list_suggestions(self, community_id: str = None, status: str = None,
                         priority: str = None, limit: int = 100) -> List[ReplenishmentSuggestionEntity]:
        """获取补货建议列表"""
        query = self.db.query(ReplenishmentSuggestionEntity)

        if community_id:
            query = query.filter(ReplenishmentSuggestionEntity.community_id == community_id)
        if status:
            query = query.filter(ReplenishmentSuggestionEntity.status == status)
        if priority:
            query = query.filter(ReplenishmentSuggestionEntity.priority == priority)

        return query.order_by(
            ReplenishmentSuggestionEntity.priority,
            ReplenishmentSuggestionEntity.created_at.desc()
        ).limit(limit).all()

    def accept_suggestion(self, suggestion_id: str, order_id: str = None) -> Tuple[Optional[ReplenishmentSuggestionEntity], bool]:
        """
        接受补货建议（转为采购订单）

        Args:
            suggestion_id: 建议 ID
            order_id: 转化的采购订单 ID

        Returns:
            (补货建议实体，是否成功)
        """
        try:
            suggestion = self.db.query(ReplenishmentSuggestionEntity).filter(
                ReplenishmentSuggestionEntity.id == suggestion_id
            ).first()

            if not suggestion:
                self._log("error", "补货建议不存在", {"suggestion_id": suggestion_id})
                return None, False

            suggestion.status = ReplenishmentStatus.CONVERTED.value
            suggestion.converted_to_order_id = order_id
            suggestion.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(suggestion)

            self._log("info", "补货建议已接受", {
                "suggestion_id": suggestion_id,
                "order_id": order_id
            })

            return suggestion, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"接受补货建议失败：{str(e)}", {"suggestion_id": suggestion_id})
            return None, False

    def reject_suggestion(self, suggestion_id: str, reason: str = None) -> Tuple[Optional[ReplenishmentSuggestionEntity], bool]:
        """
        拒绝补货建议

        Args:
            suggestion_id: 建议 ID
            reason: 拒绝原因

        Returns:
            (补货建议实体，是否成功)
        """
        try:
            suggestion = self.db.query(ReplenishmentSuggestionEntity).filter(
                ReplenishmentSuggestionEntity.id == suggestion_id
            ).first()

            if not suggestion:
                self._log("error", "补货建议不存在", {"suggestion_id": suggestion_id})
                return None, False

            suggestion.status = ReplenishmentStatus.REJECTED.value
            suggestion.reason = reason or suggestion.reason
            suggestion.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(suggestion)

            self._log("info", "补货建议已拒绝", {"suggestion_id": suggestion_id})

            return suggestion, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"拒绝补货建议失败：{str(e)}", {"suggestion_id": suggestion_id})
            return None, False

    def get_suggestion_stats(self, community_id: str = None) -> Dict:
        """
        获取补货建议统计

        Args:
            community_id: 社区 ID

        Returns:
            统计字典
        """
        query = self.db.query(ReplenishmentSuggestionEntity)

        if community_id:
            query = query.filter(ReplenishmentSuggestionEntity.community_id == community_id)

        return {
            "total": query.count(),
            "pending": query.filter(ReplenishmentSuggestionEntity.status == ReplenishmentStatus.PENDING.value).count(),
            "converted": query.filter(ReplenishmentSuggestionEntity.status == ReplenishmentStatus.CONVERTED.value).count(),
            "rejected": query.filter(ReplenishmentSuggestionEntity.status == ReplenishmentStatus.REJECTED.value).count(),
            "urgent": query.filter(ReplenishmentSuggestionEntity.priority == Priority.URGENT.value).count(),
            "high": query.filter(ReplenishmentSuggestionEntity.priority == Priority.HIGH.value).count()
        }

    def generate_all_suggestions(self, community_id: str = None,
                                  forecast_days: int = 7) -> int:
        """
        为所有商品生成补货建议

        Args:
            community_id: 社区 ID（可选）
            forecast_days: 预测天数

        Returns:
            生成的建议数量
        """
        # 获取所有活跃商品
        products = self.db.query(ProductEntity).filter(
            ProductEntity.status == ProductStatus.ACTIVE
        ).all()

        generated_count = 0
        for product in products:
            # 为每个商品生成补货建议
            suggestion, success = self.generate_replenishment_suggestion(
                product_id=product.id,
                community_id=community_id or "default",
                forecast_days=forecast_days
            )
            if success and suggestion:
                generated_count += 1

        return generated_count
