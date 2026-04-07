"""
AI 需求预测服务
负责销量预测、社区偏好分析、智能选品推荐
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import json
import logging
from collections import defaultdict

from models.entities import (
    DemandForecastEntity, CommunityPreferenceEntity,
    OrderEntity, GroupBuyEntity, ProductEntity
)
from models.product import OrderStatus
from core.logging_config import get_logger

logger = get_logger("services.demand_forecast")


class DemandForecastService:
    """AI 需求预测服务"""

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

    def create_forecast(self, data: dict) -> Tuple[Optional[DemandForecastEntity], bool]:
        """
        创建需求预测记录

        Args:
            data: 包含 product_id, community_id, forecast_date, forecast_quantity, confidence, features, model_version

        Returns:
            (预测实体，是否成功)
        """
        try:
            forecast = DemandForecastEntity(
                product_id=data["product_id"],
                community_id=data["community_id"],
                forecast_date=data["forecast_date"],
                forecast_quantity=data["forecast_quantity"],
                confidence=data.get("confidence", 0.0),
                features=json.dumps(data.get("features", {})) if data.get("features") else None,
                model_version=data.get("model_version", "v1")
            )

            self.db.add(forecast)
            self.db.commit()
            self.db.refresh(forecast)

            self._log("info", "需求预测创建成功", {
                "forecast_id": forecast.id,
                "product_id": data["product_id"],
                "community_id": data["community_id"],
                "forecast_quantity": data["forecast_quantity"]
            })

            return forecast, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建需求预测失败：{str(e)}", {"data": data})
            return None, False

    def update_forecast_actual(self, forecast_id: str, actual_quantity: int,
                               accuracy: float) -> Tuple[Optional[DemandForecastEntity], bool]:
        """
        更新预测实际值

        Args:
            forecast_id: 预测记录 ID
            actual_quantity: 实际销量
            accuracy: 预测准确率

        Returns:
            (预测实体，是否成功)
        """
        try:
            forecast = self.db.query(DemandForecastEntity).filter(
                DemandForecastEntity.id == forecast_id
            ).first()

            if not forecast:
                self._log("error", "预测记录不存在", {"forecast_id": forecast_id})
                return None, False

            forecast.actual_quantity = actual_quantity
            forecast.accuracy = accuracy
            forecast.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(forecast)

            self._log("info", "预测实际值更新成功", {
                "forecast_id": forecast_id,
                "actual_quantity": actual_quantity,
                "accuracy": accuracy
            })

            return forecast, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"更新预测实际值失败：{str(e)}", {"forecast_id": forecast_id})
            return None, False

    def get_forecast(self, forecast_id: str) -> Optional[DemandForecastEntity]:
        """获取预测记录详情"""
        return self.db.query(DemandForecastEntity).filter(
            DemandForecastEntity.id == forecast_id
        ).first()

    def list_forecasts(self, product_id: str = None, community_id: str = None,
                      date_from: datetime = None, date_to: datetime = None,
                      limit: int = 100) -> List[DemandForecastEntity]:
        """获取预测记录列表"""
        query = self.db.query(DemandForecastEntity)

        if product_id:
            query = query.filter(DemandForecastEntity.product_id == product_id)

        if community_id:
            query = query.filter(DemandForecastEntity.community_id == community_id)

        if date_from:
            query = query.filter(DemandForecastEntity.forecast_date >= date_from)

        if date_to:
            query = query.filter(DemandForecastEntity.forecast_date <= date_to)

        return query.order_by(DemandForecastEntity.forecast_date.desc()).limit(limit).all()

    def get_forecast_accuracy_stats(self, product_id: str = None,
                                    community_id: str = None) -> Dict:
        """
        获取预测准确率统计

        Args:
            product_id: 商品 ID
            community_id: 社区 ID

        Returns:
            统计字典
        """
        query = self.db.query(DemandForecastEntity).filter(
            DemandForecastEntity.actual_quantity.isnot(None)
        )

        if product_id:
            query = query.filter(DemandForecastEntity.product_id == product_id)

        if community_id:
            query = query.filter(DemandForecastEntity.community_id == community_id)

        forecasts = query.all()

        if not forecasts:
            return {
                "total_forecasts": 0,
                "avg_accuracy": 0.0,
                "avg_absolute_error": 0.0
            }

        total_accuracy = sum(f.accuracy for f in forecasts if f.accuracy is not None)
        valid_count = sum(1 for f in forecasts if f.accuracy is not None)

        # 计算平均绝对误差
        total_abs_error = sum(
            abs(f.forecast_quantity - f.actual_quantity)
            for f in forecasts if f.actual_quantity is not None
        )

        return {
            "total_forecasts": len(forecasts),
            "avg_accuracy": total_accuracy / valid_count if valid_count > 0 else 0.0,
            "avg_absolute_error": total_abs_error / len(forecasts) if forecasts else 0.0
        }

    def simple_moving_average_forecast(self, product_id: str, community_id: str,
                                       days: int = 7, future_days: int = 1) -> Dict:
        """
        简单移动平均预测

        基于过去 N 天的平均销量预测未来销量

        Args:
            product_id: 商品 ID
            community_id: 社区 ID
            days: 历史天数
            future_days: 预测未来天数

        Returns:
            预测结果
        """
        # 获取历史订单数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 查询历史销量
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
        ).all()

        if not results:
            return {
                "product_id": product_id,
                "community_id": community_id,
                "forecast_quantity": 0,
                "confidence": 0.0,
                "method": "simple_moving_average",
                "message": "无历史数据"
            }

        # 计算日平均销量
        total_quantity = sum(r.daily_quantity for r in results)
        avg_daily_quantity = total_quantity / len(results)

        # 预测未来销量
        forecast_quantity = int(avg_daily_quantity * future_days)

        # 计算置信度（基于数据点数量）
        confidence = min(1.0, len(results) / days)

        return {
            "product_id": product_id,
            "community_id": community_id,
            "forecast_date": (datetime.now() + timedelta(days=1)).date().isoformat(),
            "forecast_quantity": forecast_quantity,
            "confidence": confidence,
            "method": "simple_moving_average",
            "historical_days": days,
            "avg_daily_quantity": avg_daily_quantity
        }

    def analyze_community_preference(self, community_id: str) -> List[Dict]:
        """
        分析社区偏好

        Args:
            community_id: 社区 ID

        Returns:
            品类偏好列表
        """
        # 获取社区历史订单数据
        results = self.db.query(
            ProductEntity.id.label("product_id"),
            ProductEntity.name.label("product_name"),
            func.count(OrderEntity.id).label("order_count"),
            func.sum(OrderEntity.quantity).label("total_quantity"),
            func.sum(OrderEntity.total_amount).label("total_amount"),
            func.avg(OrderEntity.total_amount).label("avg_order_value")
        ).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).join(
            ProductEntity, OrderEntity.product_id == ProductEntity.id
        ).filter(
            GroupBuyEntity.organizer_id == community_id,  # 假设 community_id 对应团长
            OrderEntity.status == OrderStatus.COMPLETED
        ).group_by(
            ProductEntity.id, ProductEntity.name
        ).order_by(
            func.count(OrderEntity.id).desc()
        ).limit(50).all()

        if not results:
            return []

        # 计算偏好分数
        max_orders = max(r.order_count for r in results) if results else 1

        preferences = []
        for r in results:
            preference_score = r.order_count / max_orders if max_orders > 0 else 0

            preferences.append({
                "product_id": r.product_id,
                "product_name": r.product_name,
                "order_count": r.order_count,
                "total_quantity": r.total_quantity,
                "total_amount": r.total_amount,
                "avg_order_value": r.avg_order_value or 0,
                "preference_score": preference_score
            })

        return preferences

    def save_community_preference(self, community_id: str, category: str,
                                  preference_data: Dict) -> Optional[CommunityPreferenceEntity]:
        """
        保存社区偏好记录

        Args:
            community_id: 社区 ID
            category: 品类
            preference_data: 偏好数据

        Returns:
            保存的实体
        """
        try:
            # 检查是否已存在
            existing = self.db.query(CommunityPreferenceEntity).filter(
                and_(
                    CommunityPreferenceEntity.community_id == community_id,
                    CommunityPreferenceEntity.category == category
                )
            ).first()

            if existing:
                # 更新现有记录
                existing.preference_score = preference_data.get("preference_score", 0.0)
                existing.avg_order_value = preference_data.get("avg_order_value", 0.0)
                existing.purchase_frequency = preference_data.get("purchase_frequency", 0.0)
                existing.favorite_brands = json.dumps(preference_data.get("favorite_brands", []))
                existing.favorite_price_range = json.dumps(preference_data.get("favorite_price_range", {}))
                existing.sample_size = preference_data.get("sample_size", 0)
                existing.last_purchase_at = preference_data.get("last_purchase_at")
                existing.updated_at = datetime.now()
                entity = existing
            else:
                # 创建新记录
                entity = CommunityPreferenceEntity(
                    community_id=community_id,
                    category=category,
                    preference_score=preference_data.get("preference_score", 0.0),
                    avg_order_value=preference_data.get("avg_order_value", 0.0),
                    purchase_frequency=preference_data.get("purchase_frequency", 0.0),
                    favorite_brands=json.dumps(preference_data.get("favorite_brands", [])),
                    favorite_price_range=json.dumps(preference_data.get("favorite_price_range", {})),
                    sample_size=preference_data.get("sample_size", 0),
                    last_purchase_at=preference_data.get("last_purchase_at")
                )
                self.db.add(entity)

            self.db.commit()
            self.db.refresh(entity)

            self._log("info", "社区偏好保存成功", {
                "community_id": community_id,
                "category": category
            })

            return entity

        except Exception as e:
            self.db.rollback()
            self._log("error", f"保存社区偏好失败：{str(e)}", {
                "community_id": community_id,
                "category": category
            })
            return None

    def get_community_preferences(self, community_id: str) -> List[CommunityPreferenceEntity]:
        """获取社区偏好列表"""
        return self.db.query(CommunityPreferenceEntity).filter(
            CommunityPreferenceEntity.community_id == community_id
        ).order_by(CommunityPreferenceEntity.preference_score.desc()).all()

    def recommend_products_for_community(self, community_id: str,
                                         limit: int = 10) -> List[Dict]:
        """
        为社区推荐商品

        基于社区历史偏好和商品销售表现进行推荐

        Args:
            community_id: 社区 ID
            limit: 返回数量上限

        Returns:
            推荐商品列表
        """
        # 获取社区偏好
        preferences = self.analyze_community_preference(community_id)

        if not preferences:
            # 如果没有历史数据，返回全平台热销商品
            return self._get_platform_top_products(limit)

        # 基于偏好分数排序推荐
        recommendations = []
        for pref in preferences[:limit]:
            recommendations.append({
                "product_id": pref["product_id"],
                "product_name": pref["product_name"],
                "reason": f"社区偏好度 {pref['preference_score']:.2f}",
                "order_count": pref["order_count"],
                "preference_score": pref["preference_score"]
            })

        return recommendations

    def _get_platform_top_products(self, limit: int = 10) -> List[Dict]:
        """获取全平台热销商品"""
        results = self.db.query(
            ProductEntity.id,
            ProductEntity.name,
            func.sum(OrderEntity.quantity).label("total_quantity"),
            func.count(OrderEntity.id).label("order_count")
        ).join(
            GroupBuyEntity, OrderEntity.product_id == GroupBuyEntity.product_id
        ).filter(
            OrderEntity.status == OrderStatus.COMPLETED
        ).group_by(
            ProductEntity.id, ProductEntity.name
        ).order_by(
            func.sum(OrderEntity.quantity).desc()
        ).limit(limit).all()

        return [
            {
                "product_id": r.id,
                "product_name": r.name,
                "total_quantity": r.total_quantity,
                "order_count": r.order_count,
                "reason": "全平台热销"
            }
            for r in results
        ]
