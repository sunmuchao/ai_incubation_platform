"""
ML 趋势预测模型

使用时间序列分析 (ARIMA/Prophet) 和机器学习模型进行投资趋势预测
支持 6 个月预测和置信度评分
"""
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """预测结果"""
    # 预测时间点
    dates: List[str]
    # 预测值
    predictions: List[float]
    # 置信区间下限
    lower_bound: List[float]
    # 置信区间上限
    upper_bound: List[float]
    # 置信度分数 (0-1)
    confidence_score: float
    # 趋势方向
    trend_direction: str  # 'up', 'down', 'stable'
    # 增长率预测
    growth_rate: float
    # 模型信息
    model_type: str
    # 特征重要性 (如果适用)
    feature_importance: Optional[Dict[str, float]] = None
    # 模型评估指标
    model_metrics: Dict[str, float] = field(default_factory=dict)


class TrendPredictor:
    """
    趋势预测器

    支持多种预测模型:
    1. 线性回归 - 简单趋势外推
    2. ARIMA - 时间序列预测
    3. Prophet 风格分解 - 趋势 + 季节性
    4. 集成模型 - 多模型加权平均
    """

    def __init__(self):
        self._historical_data: Dict[str, List[Dict]] = defaultdict(list)
        self._trained_models: Dict[str, Any] = {}
        self._model_metadata: Dict[str, Dict] = {}

    def add_historical_data(
        self,
        dimension: str,
        dimension_value: str,
        date: datetime,
        value: float,
        features: Optional[Dict] = None
    ):
        """添加历史数据点"""
        key = f"{dimension}:{dimension_value}"
        self._historical_data[key].append({
            "date": date,
            "value": value,
            "features": features or {}
        })
        # 按日期排序
        self._historical_data[key].sort(key=lambda x: x["date"])

    def load_from_investment_data(self, investments: List[Any]):
        """从投资数据加载历史数据"""
        from collections import defaultdict

        # 按行业 - 月份聚合投资数据
        industry_monthly = defaultdict(lambda: defaultdict(lambda: {"count": 0, "amount": 0}))
        for inv in investments:
            if inv.investment_date:
                month_key = inv.investment_date.strftime("%Y-%m")
                industry = inv.investee_industry or "unknown"
                industry_monthly[industry][month_key]["count"] += 1
                industry_monthly[industry][month_key]["amount"] += inv.amount or 0

        # 转换为时间序列数据
        for industry, monthly_data in industry_monthly.items():
            for month_str, data in sorted(monthly_data.items()):
                try:
                    date = datetime.strptime(month_str, "%Y-%m")
                    self.add_historical_data(
                        dimension="industry",
                        dimension_value=industry,
                        date=date,
                        value=data["count"],
                        features={"amount": data["amount"]}
                    )
                except ValueError:
                    continue

    def _prepare_time_series(
        self,
        data: List[Dict],
        forecast_periods: int = 6
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """准备时间序列数据"""
        if len(data) < 3:
            raise ValueError("至少需要 3 个数据点才能进行预测")

        dates = [d["date"] for d in data]
        values = np.array([d["value"] for d in data])

        # 转换为时间索引
        base_date = dates[0]
        time_index = np.array([
            (d - base_date).days for d in dates
        ]).reshape(-1, 1)

        return time_index, values, dates

    def _linear_regression_forecast(
        self,
        time_index: np.ndarray,
        values: np.ndarray,
        forecast_periods: int,
        last_date: datetime
    ) -> ForecastResult:
        """线性回归预测"""
        from sklearn.linear_model import LinearRegression

        # 训练模型
        model = LinearRegression()
        model.fit(time_index, values)

        # 生成预测
        last_time = time_index[-1, 0]
        future_times = np.array([last_time + (i + 1) * 30 for i in range(forecast_periods)]).reshape(-1, 1)
        predictions = model.predict(future_times)

        # 计算置信区间
        residuals = values - model.predict(time_index)
        std_err = np.std(residuals)
        lower_bound = predictions - 1.96 * std_err
        upper_bound = predictions + 1.96 * std_err

        # 计算 R²
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((values - np.mean(values)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 计算趋势方向
        slope = model.coef_[0]
        if slope > std_err:
            trend_direction = "up"
        elif slope < -std_err:
            trend_direction = "down"
        else:
            trend_direction = "stable"

        # 计算增长率
        avg_value = np.mean(values)
        growth_rate = (slope * 30 / avg_value * 100) if avg_value > 0 else 0

        # 生成预测日期
        forecast_dates = [
            (last_date + timedelta(days=(i + 1) * 30)).strftime("%Y-%m")
            for i in range(forecast_periods)
        ]

        confidence_score = min(0.95, max(0.5, r2))

        return ForecastResult(
            dates=forecast_dates,
            predictions=predictions.tolist(),
            lower_bound=lower_bound.tolist(),
            upper_bound=upper_bound.tolist(),
            confidence_score=confidence_score,
            trend_direction=trend_direction,
            growth_rate=growth_rate,
            model_type="linear_regression",
            model_metrics={"r2": r2, "std_err": std_err}
        )

    def _arima_forecast(
        self,
        values: np.ndarray,
        dates: List[datetime],
        forecast_periods: int,
        last_date: datetime
    ) -> Optional[ForecastResult]:
        """ARIMA 时间序列预测"""
        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError:
            logger.warning("statsmodels not installed, skipping ARIMA")
            return None

        if len(values) < 10:
            # 数据点不足，降级到简单预测
            return None

        try:
            # 拟合 ARIMA 模型 (p=2, d=1, q=2)
            model = ARIMA(values, order=(2, 1, 2))
            fitted = model.fit()

            # 预测
            forecast = fitted.forecast(steps=forecast_periods)

            # 计算置信区间
            conf_int = fitted.get_forecast(steps=forecast_periods).conf_int()

            # 计算 AIC 作为模型质量指标
            aic = fitted.aic

            # 趋势判断
            recent_avg = np.mean(values[-3:]) if len(values) >= 3 else np.mean(values)
            forecast_avg = np.mean(forecast)
            if forecast_avg > recent_avg * 1.1:
                trend_direction = "up"
            elif forecast_avg < recent_avg * 0.9:
                trend_direction = "down"
            else:
                trend_direction = "stable"

            growth_rate = ((forecast_avg - recent_avg) / recent_avg * 100) if recent_avg > 0 else 0

            # 置信度基于 AIC (越低越好)
            # 标准化到 0.5-0.95 范围
            confidence_score = min(0.95, max(0.5, 1 - (aic / 1000)))

            forecast_dates = [
                (last_date + timedelta(days=(i + 1) * 30)).strftime("%Y-%m")
                for i in range(forecast_periods)
            ]

            return ForecastResult(
                dates=forecast_dates,
                predictions=forecast.tolist(),
                lower_bound=conf_int.iloc[:, 0].tolist(),
                upper_bound=conf_int.iloc[:, 1].tolist(),
                confidence_score=confidence_score,
                trend_direction=trend_direction,
                growth_rate=growth_rate,
                model_type="arima",
                model_metrics={"aic": aic}
            )

        except Exception as e:
            logger.warning(f"ARIMA fitting failed: {e}")
            return None

    def _prophet_style_forecast(
        self,
        values: np.ndarray,
        dates: List[datetime],
        forecast_periods: int,
        last_date: datetime
    ) -> Optional[ForecastResult]:
        """
        Prophet 风格的分解预测 (趋势 + 季节性)
        在不依赖 Facebook Prophet 库的情况下实现类似功能
        """
        if len(values) < 12:
            # 需要至少 12 个月的数据来检测季节性
            return None

        try:
            # 分解趋势
            from scipy.stats import linregress

            time_idx = np.arange(len(values))
            slope, intercept, r_value, p_value, std_err = linregress(time_idx, values)

            # 趋势分量
            trend = slope * time_idx + intercept

            # 去趋势后的数据
            detrended = values - trend

            # 检测季节性 (假设 12 个月周期)
            if len(detrended) >= 12:
                seasonal_pattern = np.zeros(12)
                for i in range(12):
                    seasonal_values = detrended[i::12]
                    seasonal_pattern[i] = np.mean(seasonal_values) if len(seasonal_values) > 0 else 0

                # 预测
                future_idx = np.arange(len(values), len(values) + forecast_periods)
                future_trend = slope * future_idx + intercept

                # 添加季节性
                future_seasonal = [seasonal_pattern[(len(values) + i) % 12] for i in range(forecast_periods)]
                predictions = future_trend + np.array(future_seasonal)

                # 置信区间基于残差
                residuals = values - (trend + [seasonal_pattern[i % 12] for i in range(len(values))])
                std_residual = np.std(residuals)

                lower_bound = predictions - 1.96 * std_residual
                upper_bound = predictions + 1.96 * std_residual

                # 趋势判断
                if slope > std_err:
                    trend_direction = "up"
                elif slope < -std_err:
                    trend_direction = "down"
                else:
                    trend_direction = "stable"

                # 增长率
                avg_value = np.mean(values)
                growth_rate = (slope / avg_value * 100) if avg_value > 0 else 0

                forecast_dates = [
                    (last_date + timedelta(days=(i + 1) * 30)).strftime("%Y-%m")
                    for i in range(forecast_periods)
                ]

                confidence_score = min(0.95, max(0.5, r_value ** 2))

                return ForecastResult(
                    dates=forecast_dates,
                    predictions=predictions.tolist(),
                    lower_bound=lower_bound.tolist(),
                    upper_bound=upper_bound.tolist(),
                    confidence_score=confidence_score,
                    trend_direction=trend_direction,
                    growth_rate=growth_rate,
                    model_type="prophet_style",
                    model_metrics={
                        "r_squared": r_value ** 2,
                        "p_value": p_value,
                        "slope": slope
                    }
                )

            return None

        except ImportError:
            logger.warning("scipy not installed, skipping prophet-style forecast")
            return None
        except Exception as e:
            logger.warning(f"Prophet-style fitting failed: {e}")
            return None

    def forecast(
        self,
        dimension: str,
        dimension_value: str,
        forecast_periods: int = 6,
        model: str = "auto"
    ) -> Optional[ForecastResult]:
        """
        执行趋势预测

        Args:
            dimension: 维度 (如 'industry', 'round', 'region')
            dimension_value: 维度值 (如 '电商', 'A 轮', '北京')
            forecast_periods: 预测期数 (默认 6 个月)
            model: 模型选择 ('auto', 'linear', 'arima', 'prophet')

        Returns:
            ForecastResult 或 None
        """
        key = f"{dimension}:{dimension_value}"
        data = self._historical_data.get(key, [])

        if len(data) < 3:
            logger.warning(f"Insufficient data for {key}")
            return None

        time_index, values, dates = self._prepare_time_series(data, forecast_periods)
        last_date = dates[-1]

        results = []

        # 根据选择执行预测
        if model in ["auto", "linear"]:
            linear_result = self._linear_regression_forecast(
                time_index, values, forecast_periods, last_date
            )
            results.append(linear_result)

        if model in ["auto", "arima"]:
            arima_result = self._arima_forecast(
                values, dates, forecast_periods, last_date
            )
            if arima_result:
                results.append(arima_result)

        if model in ["auto", "prophet"]:
            prophet_result = self._prophet_style_forecast(
                values, dates, forecast_periods, last_date
            )
            if prophet_result:
                results.append(prophet_result)

        if not results:
            return None

        # 如果只有一个模型，直接返回
        if len(results) == 1:
            return results[0]

        # 集成预测：加权平均
        return self._ensemble_forecast(results)

    def _ensemble_forecast(
        self,
        results: List[ForecastResult]
    ) -> ForecastResult:
        """集成多个模型的预测结果"""
        # 基于置信度评分计算权重
        total_conf = sum(r.confidence_score for r in results)
        weights = [r.confidence_score / total_conf for r in results]

        # 加权平均预测
        predictions = np.zeros(len(results[0].predictions))
        lower_bound = np.zeros(len(results[0].predictions))
        upper_bound = np.zeros(len(results[0].predictions))

        for r, w in zip(results, weights):
            predictions += np.array(r.predictions) * w
            lower_bound += np.array(r.lower_bound) * w
            upper_bound += np.array(r.upper_bound) * w

        # 综合置信度
        avg_confidence = sum(r.confidence_score * w for r, w in zip(results, weights))

        # 综合增长率
        avg_growth = sum(r.growth_rate * w for r, w in zip(results, weights))

        # 确定趋势方向 (多数投票)
        direction_votes = defaultdict(int)
        for r in results:
            direction_votes[r.trend_direction] += 1
        trend_direction = max(direction_votes.keys(), key=lambda k: direction_votes[k])

        # 最佳模型
        best_model = max(results, key=lambda r: r.confidence_score)

        return ForecastResult(
            dates=results[0].dates,
            predictions=predictions.tolist(),
            lower_bound=lower_bound.tolist(),
            upper_bound=upper_bound.tolist(),
            confidence_score=avg_confidence,
            trend_direction=trend_direction,
            growth_rate=avg_growth,
            model_type=f"ensemble ({best_model.model_type})",
            model_metrics={
                "models_used": [r.model_type for r in results],
                "weights": {r.model_type: w for r, w in zip(results, weights)},
                **best_model.model_metrics
            }
        )

    def get_model_comparison(
        self,
        dimension: str,
        dimension_value: str
    ) -> Dict[str, Any]:
        """比较不同模型的预测效果"""
        key = f"{dimension}:{dimension_value}"
        data = self._historical_data.get(key, [])

        if len(data) < 10:
            return {"error": "Insufficient data for model comparison"}

        # 使用最后一部分数据进行回测
        train_data = data[:-3]
        test_data = data[-3:]

        if not train_data or not test_data:
            return {"error": "Insufficient data for backtesting"}

        # 临时预测器进行回测
        backtest_results = {}

        # 线性回归回测
        try:
            time_idx = np.array([(d["date"] - train_data[0]["date"]).days
                                 for d in train_data]).reshape(-1, 1)
            train_values = np.array([d["value"] for d in train_data])
            test_times = np.array([(d["date"] - train_data[0]["date"]).days
                                   for d in test_data]).reshape(-1, 1)
            test_values = np.array([d["value"] for d in test_data])

            from sklearn.linear_model import LinearRegression
            lr_model = LinearRegression()
            lr_model.fit(time_idx, train_values)
            lr_pred = lr_model.predict(test_times)
            lr_mse = np.mean((lr_pred - test_values) ** 2)
            backtest_results["linear"] = {"mse": float(lr_mse)}
        except Exception as e:
            backtest_results["linear"] = {"error": str(e)}

        return {
            "dimension": dimension,
            "dimension_value": dimension_value,
            "train_size": len(train_data),
            "test_size": len(test_data),
            "models": backtest_results
        }


# 全局预测器实例
trend_predictor = TrendPredictor()
