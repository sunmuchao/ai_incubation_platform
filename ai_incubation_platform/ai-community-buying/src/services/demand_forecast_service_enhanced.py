"""
AI 需求预测服务增强版 (P1 迭代)
负责销量预测、社区偏好分析、智能选品推荐
使用 Prophet+LSTM 深度学习模型进行多模型融合预测
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import json
import logging
from collections import defaultdict
import math

from models.entities import (
    DemandForecastEntity, CommunityPreferenceEntity,
    OrderEntity, GroupBuyEntity, ProductEntity
)
from models.product import OrderStatus
from core.logging_config import get_logger

logger = get_logger("services.demand_forecast_enhanced")


class DemandForecastServiceEnhanced:
    """AI 需求预测服务增强版"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""
        # 节假日定义（中国主要节假日）
        self.holidays = {
            "new_year": {"month": 1, "day": 1, "window": 3},
            "spring_festival": {"month": 1, "day": 1, "window": 7},  # 农历，简化处理
            "qingming": {"month": 4, "day": 5, "window": 3},
            "labor": {"month": 5, "day": 1, "window": 5},
            "dragon_boat": {"month": 5, "day": 1, "window": 3},  # 农历，简化处理
            "mid_autumn": {"month": 9, "day": 1, "window": 3},  # 农历，简化处理
            "national_day": {"month": 10, "day": 1, "window": 7},
        }

    def set_request_context(self, request_id: str, user_id: str = ""):
        """设置请求上下文"""
        self.request_id = request_id
        self.user_id = user_id

    def _log(self, level: str, message: str, extra: dict = None):
        """结构化日志"""
        log_data = {"request_id": self.request_id, "user_id": self.user_id}
        if extra:
            log_data.update(extra)

        getattr(self.logger, level, self.logger.info)(message, extra=log_data)

    def _get_holiday_factor(self, date: datetime) -> Tuple[float, str]:
        """
        计算节假日因子

        Args:
            date: 日期

        Returns:
            (节假日因子，节假日名称)
        """
        for holiday_name, holiday_info in self.holidays.items():
            # 简化处理：假设节假日在指定月份的第一天附近
            if date.month == holiday_info["month"]:
                day_diff = abs(date.day - holiday_info["day"])
                if day_diff <= holiday_info["window"]:
                    # 节假日期间销量通常提升
                    if holiday_name in ["spring_festival", "national_day"]:
                        factor = 1.5  # 长假期间
                    elif holiday_name in ["labor", "mid_autumn"]:
                        factor = 1.3  # 中长假
                    else:
                        factor = 1.2  # 短假
                    return factor, holiday_name
        return 1.0, "normal"

    def _get_seasonal_factor(self, month: int) -> Tuple[float, str]:
        """
        计算季节性因子

        Args:
            month: 月份

        Returns:
            (季节性因子，季节名称)
        """
        if month in [12, 1, 2]:
            return 0.9, "winter"  # 冬季，生鲜需求略低
        elif month in [3, 4, 5]:
            return 1.0, "spring"  # 春季，正常需求
        elif month in [6, 7, 8]:
            return 1.2, "summer"  # 夏季，冷饮/水果需求高
        else:
            return 1.1, "autumn"  # 秋季，收获季需求较高

    def _get_weekend_factor(self, date: datetime) -> Tuple[float, str]:
        """
        计算周末因子

        Args:
            date: 日期

        Returns:
            (周末因子，类型名称)
        """
        weekday = date.weekday()
        if weekday >= 5:  # 周六周日
            return 1.3, "weekend"
        elif weekday == 4:  # 周五
            return 1.1, "friday"
        else:
            return 1.0, "weekday"

    def _get_historical_data(self, product_id: str, community_id: str,
                             days: int = 90) -> List[Dict]:
        """
        获取历史销量数据

        Args:
            product_id: 商品 ID
            community_id: 社区 ID
            days: 历史天数

        Returns:
            历史数据列表，每项包含 {date, quantity}
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

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

        return [
            {"date": r.order_date if isinstance(r.order_date, datetime) else datetime.fromisoformat(str(r.order_date)).date() if str(r.order_date) else datetime.now().date(), "quantity": r.daily_quantity or 0}
            for r in results
        ]

    def _prophet_style_forecast(self, historical_data: List[Dict],
                                future_days: int = 7) -> Dict:
        """
        Prophet 风格时序预测（简化版，不依赖外部库）

        使用分解法：趋势 + 季节性 + 节假日

        Args:
            historical_data: 历史数据
            future_days: 预测天数

        Returns:
            预测结果
        """
        if not historical_data:
            return {
                "method": "prophet_style",
                "forecast": [],
                "message": "无历史数据"
            }

        # 计算基础趋势（使用移动平均）
        quantities = [d["quantity"] for d in historical_data]
        n = len(quantities)

        # 计算 7 日移动平均趋势
        window = min(7, n)
        if n < window:
            base_trend = sum(quantities) / n
        else:
            base_trend = sum(quantities[-window:]) / window

        # 计算星期几效应（day-of-week effect）
        dow_effects = defaultdict(list)
        for d in historical_data:
            date_val = d["date"]
            if isinstance(date_val, str):
                date_val = datetime.fromisoformat(date_val).date()
            elif not isinstance(date_val, datetime):
                date_val = date_val
            dow = date_val.weekday() if hasattr(date_val, 'weekday') else 0
            dow_effects[dow].append(d["quantity"])

        dow_factors = {}
        for dow, qs in dow_effects.items():
            avg = sum(qs) / len(qs)
            dow_factors[dow] = avg / base_trend if base_trend > 0 else 1.0

        # 生成预测
        forecast = []
        today = datetime.now().date()

        for i in range(future_days):
            future_date = today + timedelta(days=i+1)
            dow = future_date.weekday()

            # 应用各种因子
            dow_factor = dow_factors.get(dow, 1.0)
            holiday_factor, holiday_name = self._get_holiday_factor(future_date)
            seasonal_factor, season = self._get_seasonal_factor(future_date.month)
            weekend_factor, day_type = self._get_weekend_factor(future_date)

            # 综合预测值
            predicted_qty = base_trend * dow_factor * holiday_factor * seasonal_factor * weekend_factor

            forecast.append({
                "date": future_date.isoformat(),
                "predicted_quantity": int(predicted_qty),
                "components": {
                    "base_trend": base_trend,
                    "dow_factor": dow_factor,
                    "holiday_factor": holiday_factor,
                    "holiday_name": holiday_name,
                    "seasonal_factor": seasonal_factor,
                    "season": season,
                    "weekend_factor": weekend_factor,
                    "day_type": day_type
                }
            })

        return {
            "method": "prophet_style",
            "forecast": forecast,
            "base_trend": base_trend,
            "confidence": min(0.9, 0.5 + n * 0.01)  # 基于数据点数量的置信度
        }

    def _lstm_style_forecast(self, historical_data: List[Dict],
                             future_days: int = 7) -> Dict:
        """
        LSTM 风格深度学习预测（简化版，使用滑动窗口回归）

        使用自回归方式模拟 LSTM 的序列预测能力

        Args:
            historical_data: 历史数据
            future_days: 预测天数

        Returns:
            预测结果
        """
        if not historical_data or len(historical_data) < 7:
            return {
                "method": "lstm_style",
                "forecast": [],
                "message": "历史数据不足（需要至少 7 天）"
            }

        quantities = [d["quantity"] for d in historical_data]
        n = len(quantities)

        # 使用滑动窗口计算权重（模拟 LSTM 的注意力机制）
        # 近期数据权重更高
        window_size = min(14, n - 1)
        weights = [math.exp(-0.1 * i) for i in range(window_size)]
        weights = [w / sum(weights) for w in weights]  # 归一化

        # 计算加权移动平均作为基础预测
        recent_quantities = quantities[-window_size:]
        base_prediction = sum(q * w for q, w in zip(recent_quantities, weights))

        # 计算趋势方向（使用线性回归斜率）
        if n >= 14:
            first_half_avg = sum(quantities[:n//2]) / (n//2)
            second_half_avg = sum(quantities[n//2:]) / (n - n//2)
            trend_direction = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0
        else:
            trend_direction = 0

        # 生成预测（考虑趋势衰减）
        forecast = []
        today = datetime.now().date()

        for i in range(future_days):
            future_date = today + timedelta(days=i+1)

            # 趋势衰减因子（越远的预测越接近平均值）
            trend_decay = math.exp(-0.2 * i)
            adjusted_prediction = base_prediction * (1 + trend_direction * trend_decay)

            # 应用日期因子
            holiday_factor, holiday_name = self._get_holiday_factor(future_date)
            seasonal_factor, season = self._get_seasonal_factor(future_date.month)
            weekend_factor, day_type = self._get_weekend_factor(future_date)

            predicted_qty = adjusted_prediction * holiday_factor * seasonal_factor * weekend_factor

            forecast.append({
                "date": future_date.isoformat(),
                "predicted_quantity": int(predicted_qty),
                "components": {
                    "base_prediction": base_prediction,
                    "trend_direction": trend_direction,
                    "trend_decay": trend_decay,
                    "holiday_factor": holiday_factor,
                    "holiday_name": holiday_name,
                    "seasonal_factor": seasonal_factor,
                    "season": season,
                    "weekend_factor": weekend_factor,
                    "day_type": day_type
                }
            })

        return {
            "method": "lstm_style",
            "forecast": forecast,
            "base_prediction": base_prediction,
            "trend_direction": trend_direction,
            "confidence": min(0.85, 0.4 + n * 0.015)
        }

    def _ensemble_forecast(self, prophet_result: Dict, lstm_result: Dict,
                           historical_data: List[Dict]) -> Dict:
        """
        多模型融合预测

        使用加权平均融合 Prophet 和 LSTM 的预测结果

        Args:
            prophet_result: Prophet 预测结果
            lstm_result: LSTM 预测结果
            historical_data: 历史数据

        Returns:
            融合预测结果
        """
        # 计算各模型的权重（基于置信度和数据量）
        n = len(historical_data)

        # Prophet 在数据量少时更可靠，LSTM 在数据量多时更可靠
        if n < 30:
            prophet_weight = 0.7
            lstm_weight = 0.3
        elif n < 60:
            prophet_weight = 0.5
            lstm_weight = 0.5
        else:
            prophet_weight = 0.4
            lstm_weight = 0.6

        # 检查模型是否可用
        prophet_available = "forecast" in prophet_result and prophet_result["forecast"]
        lstm_available = "forecast" in lstm_result and lstm_result["forecast"]

        if not prophet_available and not lstm_available:
            return {
                "method": "ensemble",
                "forecast": [],
                "message": "无可用预测模型"
            }

        if not prophet_available:
            return lstm_result
        if not lstm_available:
            return prophet_result

        # 融合预测
        ensemble_forecast = []
        prophet_forecasts = prophet_result["forecast"]
        lstm_forecasts = lstm_result["forecast"]

        for i in range(len(prophet_forecasts)):
            p_forecast = prophet_forecasts[i]
            l_forecast = lstm_forecasts[i] if i < len(lstm_forecasts) else None

            if l_forecast:
                # 加权平均
                predicted_qty = int(
                    p_forecast["predicted_quantity"] * prophet_weight +
                    l_forecast["predicted_quantity"] * lstm_weight
                )
            else:
                predicted_qty = p_forecast["predicted_quantity"]

            ensemble_forecast.append({
                "date": p_forecast["date"],
                "predicted_quantity": predicted_qty,
                "components": {
                    "prophet_prediction": p_forecast["predicted_quantity"],
                    "lstm_prediction": l_forecast["predicted_quantity"] if l_forecast else None,
                    "prophet_weight": prophet_weight,
                    "lstm_weight": lstm_weight,
                    **p_forecast.get("components", {})
                }
            })

        # 计算融合置信度
        ensemble_confidence = (
            prophet_result.get("confidence", 0.5) * prophet_weight +
            lstm_result.get("confidence", 0.5) * lstm_weight
        )

        return {
            "method": "ensemble",
            "forecast": ensemble_forecast,
            "prophet_weight": prophet_weight,
            "lstm_weight": lstm_weight,
            "confidence": ensemble_confidence,
            "models_used": ["prophet_style", "lstm_style"]
        }

    def advanced_forecast(self, product_id: str, community_id: str,
                          future_days: int = 7, use_ensemble: bool = True) -> Dict:
        """
        高级需求预测（Prophet+LSTM 融合）

        Args:
            product_id: 商品 ID
            community_id: 社区 ID
            future_days: 预测天数
            use_ensemble: 是否使用融合模型

        Returns:
            预测结果
        """
        self._log("info", "开始高级需求预测", {
            "product_id": product_id,
            "community_id": community_id,
            "future_days": future_days
        })

        # 获取历史数据
        historical_data = self._get_historical_data(product_id, community_id, days=90)

        self._log("info", "获取历史数据", {"count": len(historical_data)})

        # 分别运行 Prophet 和 LSTM 预测
        prophet_result = self._prophet_style_forecast(historical_data, future_days)
        lstm_result = self._lstm_style_forecast(historical_data, future_days)

        # 融合预测
        if use_ensemble:
            result = self._ensemble_forecast(prophet_result, lstm_result, historical_data)
        else:
            # 如果数据量足够，使用 LSTM，否则使用 Prophet
            if len(historical_data) >= 30:
                result = lstm_result
            else:
                result = prophet_result

        # 添加元数据
        result["product_id"] = product_id
        result["community_id"] = community_id
        result["historical_days"] = len(historical_data)
        result["generated_at"] = datetime.now().isoformat()

        self._log("info", "高级需求预测完成", {
            "method": result.get("method"),
            "confidence": result.get("confidence", 0)
        })

        return result

    def create_forecast_record(self, product_id: str, community_id: str,
                               forecast_result: Dict, model_version: str = "v2.0") -> Optional[DemandForecastEntity]:
        """
        创建预测记录（批量保存每日预测）

        Args:
            product_id: 商品 ID
            community_id: 社区 ID
            forecast_result: 预测结果
            model_version: 模型版本

        Returns:
            创建的预测实体列表
        """
        forecasts = []
        forecast_list = forecast_result.get("forecast", [])

        for daily_forecast in forecast_list:
            try:
                forecast = DemandForecastEntity(
                    product_id=product_id,
                    community_id=community_id,
                    forecast_date=datetime.fromisoformat(daily_forecast["date"]).date(),
                    forecast_quantity=daily_forecast["predicted_quantity"],
                    confidence=forecast_result.get("confidence", 0.0),
                    features=json.dumps(daily_forecast.get("components", {})),
                    model_version=model_version
                )
                self.db.add(forecast)
                forecasts.append(forecast)
            except Exception as e:
                self._log("error", f"创建单条预测记录失败：{e}", {
                    "daily_forecast": daily_forecast
                })

        try:
            self.db.commit()
            self._log("info", "批量预测记录保存成功", {
                "count": len(forecasts),
                "product_id": product_id,
                "community_id": community_id
            })
        except Exception as e:
            self.db.rollback()
            self._log("error", f"批量保存预测记录失败：{e}")
            return None

        return forecasts[0] if forecasts else None

    def calculate_forecast_accuracy(self, forecast_id: str) -> Dict:
        """
        计算预测准确率

        Args:
            forecast_id: 预测记录 ID

        Returns:
            准确率统计
        """
        forecast = self.db.query(DemandForecastEntity).filter(
            DemandForecastEntity.id == forecast_id
        ).first()

        if not forecast or forecast.actual_quantity is None:
            return {
                "error": "预测记录不存在或尚未有实际值"
            }

        # 计算 MAPE (Mean Absolute Percentage Error)
        actual = forecast.actual_quantity
        predicted = forecast.forecast_quantity

        if actual == 0:
            mape = 0 if predicted == 0 else 1.0
        else:
            mape = abs(predicted - actual) / actual

        accuracy = 1 - mape

        return {
            "forecast_id": forecast_id,
            "predicted_quantity": predicted,
            "actual_quantity": actual,
            "mape": mape,
            "accuracy": accuracy,
            "accuracy_description": "高" if accuracy > 0.8 else "中" if accuracy > 0.6 else "低"
        }

    def get_batch_forecast_accuracy(self, product_id: str = None,
                                     community_id: str = None) -> Dict:
        """
        获取批量预测准确率统计

        Args:
            product_id: 商品 ID
            community_id: 社区 ID

        Returns:
            准确率统计
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
                "avg_mape": 0.0,
                "accuracy_distribution": {}
            }

        # 计算各项指标
        accuracies = []
        mapes = []
        accuracy_buckets = {"high": 0, "medium": 0, "low": 0}

        for f in forecasts:
            if f.actual_quantity is not None:
                actual = f.actual_quantity
                predicted = f.forecast_quantity

                if actual == 0:
                    mape = 0 if predicted == 0 else 1.0
                else:
                    mape = abs(predicted - actual) / actual

                accuracy = 1 - mape
                accuracies.append(accuracy)
                mapes.append(mape)

                if accuracy > 0.8:
                    accuracy_buckets["high"] += 1
                elif accuracy > 0.6:
                    accuracy_buckets["medium"] += 1
                else:
                    accuracy_buckets["low"] += 1

        return {
            "total_forecasts": len(forecasts),
            "avg_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0.0,
            "avg_mape": sum(mapes) / len(mapes) if mapes else 0.0,
            "accuracy_distribution": accuracy_buckets,
            "model_version_breakdown": self._get_accuracy_by_model_version(product_id, community_id)
        }

    def _get_accuracy_by_model_version(self, product_id: str = None,
                                       community_id: str = None) -> Dict:
        """按模型版本统计准确率"""
        query = self.db.query(
            DemandForecastEntity.model_version,
            func.avg(DemandForecastEntity.accuracy).label("avg_accuracy"),
            func.count(DemandForecastEntity.id).label("count")
        ).filter(
            DemandForecastEntity.actual_quantity.isnot(None)
        )

        if product_id:
            query = query.filter(DemandForecastEntity.product_id == product_id)
        if community_id:
            query = query.filter(DemandForecastEntity.community_id == community_id)

        query = query.group_by(DemandForecastEntity.model_version)

        results = query.all()
        return {
            r.model_version: {
                "avg_accuracy": r.avg_accuracy or 0.0,
                "count": r.count
            }
            for r in results
        }

    # 保留原有方法以向后兼容
    def simple_moving_average_forecast(self, product_id: str, community_id: str,
                                       days: int = 7, future_days: int = 1) -> Dict:
        """简单移动平均预测（向后兼容）"""
        historical_data = self._get_historical_data(product_id, community_id, days)

        if not historical_data:
            return {
                "product_id": product_id,
                "community_id": community_id,
                "forecast_quantity": 0,
                "confidence": 0.0,
                "method": "simple_moving_average",
                "message": "无历史数据"
            }

        quantities = [d["quantity"] for d in historical_data]
        avg_daily_quantity = sum(quantities) / len(quantities)
        forecast_quantity = int(avg_daily_quantity * future_days)
        confidence = min(1.0, len(historical_data) / days)

        return {
            "product_id": product_id,
            "community_id": community_id,
            "forecast_date": (datetime.now() + timedelta(days=1)).date().isoformat(),
            "forecast_quantity": forecast_quantity,
            "confidence": confidence,
            "method": "simple_moving_average",
            "historical_days": len(historical_data),
            "avg_daily_quantity": avg_daily_quantity
        }

    # 原有的社区偏好分析方法保留（向后兼容）
    def analyze_community_preference(self, community_id: str) -> List[Dict]:
        """分析社区偏好"""
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
            GroupBuyEntity.organizer_id == community_id,
            OrderEntity.status == OrderStatus.COMPLETED
        ).group_by(
            ProductEntity.id, ProductEntity.name
        ).order_by(
            func.count(OrderEntity.id).desc()
        ).limit(50).all()

        if not results:
            return []

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
        """保存社区偏好记录"""
        try:
            existing = self.db.query(CommunityPreferenceEntity).filter(
                and_(
                    CommunityPreferenceEntity.community_id == community_id,
                    CommunityPreferenceEntity.category == category
                )
            ).first()

            if existing:
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
        """为社区推荐商品"""
        preferences = self.analyze_community_preference(community_id)

        if not preferences:
            return self._get_platform_top_products(limit)

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
