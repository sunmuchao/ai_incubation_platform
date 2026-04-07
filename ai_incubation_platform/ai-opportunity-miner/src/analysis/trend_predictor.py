"""
趋势预测增强模块
引入更高级的时间序列分析和预测算法
参考 CB Insights 的趋势预测能力
"""
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


class TrendPredictor:
    """趋势预测器"""

    def __init__(self):
        pass

    def fit_linear_regression(self, x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
        """
        拟合线性回归
        返回：斜率、截距、R 平方值
        """
        n = len(x)
        if n < 2:
            return 0, y[0] if len(y) > 0 else 0, 0

        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x ** 2)

        # 计算斜率和截距
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0, np.mean(y), 0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n

        # 计算 R 平方
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return slope, intercept, r_squared

    def predict_moving_average(self, values: List[float], window: int = 3) -> List[float]:
        """计算移动平均"""
        if len(values) < window:
            return values

        moving_avg = []
        for i in range(len(values) - window + 1):
            avg = np.mean(values[i:i + window])
            moving_avg.append(avg)

        return moving_avg

    def detect_inflection_point(self, values: List[float]) -> Optional[int]:
        """检测拐点"""
        if len(values) < 3:
            return None

        # 计算一阶差分（增长率）
        first_diff = np.diff(values)

        # 计算二阶差分（加速度）
        second_diff = np.diff(first_diff)

        # 找到符号变化的点
        for i in range(len(second_diff) - 1):
            if second_diff[i] * second_diff[i + 1] < 0:
                return i + 1

        return None

    def calculate_growth_stage(self, values: List[float]) -> str:
        """
        判断增长阶段
        基于技术采用曲线理论
        """
        if len(values) < 3:
            return "unknown"

        # 计算增长率
        growth_rates = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                growth_rates.append((values[i] - values[i - 1]) / values[i - 1])

        if not growth_rates:
            return "unknown"

        avg_growth = np.mean(growth_rates)
        growth_trend = np.diff(growth_rates)

        # 判断阶段
        if avg_growth > 0.5:
            if np.all(growth_trend > 0):
                return "explosive_growth"  # 爆发期
            else:
                return "rapid_growth"  # 快速增长期
        elif avg_growth > 0.2:
            return "steady_growth"  # 稳定增长期
        elif avg_growth > 0:
            return "mature"  # 成熟期
        else:
            return "decline"  # 衰退期

    def calculate_cagr(self, start_value: float, end_value: float, years: int) -> float:
        """计算复合年增长率 (CAGR)"""
        if start_value <= 0 or years <= 0:
            return 0
        return (end_value / start_value) ** (1 / years) - 1

    def calculate_market_concentration(self, market_shares: List[float]) -> Dict:
        """
        计算市场集中度指标
        """
        market_shares = sorted(market_shares, reverse=True)
        n = len(market_shares)

        if n == 0:
            return {"cr3": 0, "cr5": 0, "hhi": 0, "concentration_level": "unknown"}

        # CRn (集中率)
        cr3 = sum(market_shares[:3]) if n >= 3 else sum(market_shares)
        cr5 = sum(market_shares[:5]) if n >= 5 else sum(market_shares)

        # HHI (赫芬达尔 - 赫希曼指数)
        hhi = sum(s ** 2 for s in market_shares)

        # 判断集中度等级
        if hhi > 2500:
            concentration_level = "high"  # 高度集中
        elif hhi > 1500:
            concentration_level = "moderate"  # 中度集中
        else:
            concentration_level = "low"  # 低度集中

        return {
            "cr3": cr3,
            "cr5": cr5,
            "hhi": hhi,
            "concentration_level": concentration_level,
            "players_count": n
        }

    def analyze_keyword_momentum(self, keyword_counts: Dict[str, List[int]], window: int = 3) -> List[Dict]:
        """
        分析关键词动量
        识别增长最快的关键词
        """
        results = []

        for keyword, counts in keyword_counts.items():
            if len(counts) < window:
                continue

            # 计算近期平均 vs 前期平均
            recent_avg = np.mean(counts[-window:])
            old_avg = np.mean(counts[:-window]) if len(counts) > window else np.mean(counts[:window])

            if old_avg > 0:
                momentum = (recent_avg - old_avg) / old_avg
            else:
                momentum = 1.0 if recent_avg > 0 else 0

            # 计算趋势方向
            if len(counts) >= 2:
                trend = "up" if counts[-1] > counts[0] else "down" if counts[-1] < counts[0] else "stable"
            else:
                trend = "stable"

            results.append({
                "keyword": keyword,
                "momentum": momentum,
                "recent_avg": recent_avg,
                "old_avg": old_avg,
                "trend": trend,
                "total_count": sum(counts),
                "data_points": counts
            })

        # 按动量排序
        results.sort(key=lambda x: x["momentum"], reverse=True)

        return results

    def generate_trend_insights(
        self,
        data_points: List[Dict],
        keyword: str
    ) -> Dict:
        """
        生成趋势洞察
        """
        if not data_points:
            return {}

        # 提取值和日期
        values = [dp["value"] for dp in data_points]
        dates = [dp["month"] for dp in data_points]

        x = np.arange(len(values))

        # 线性回归分析
        slope, intercept, r_squared = self.fit_linear_regression(x, values)

        # 预测下个月
        next_month_value = slope * len(values) + intercept

        # 移动平均
        ma_3 = self.calculate_moving_average(values, 3)

        # 检测拐点
        inflection = self.detect_inflection_point(values)

        # 判断增长阶段
        growth_stage = self.calculate_growth_stage(values)

        # 计算 CAGR（如果有足够数据）
        if len(values) >= 12:
            cagr = self.calculate_cagr(values[0], values[-1], len(values) // 12)
        else:
            cagr = (values[-1] - values[0]) / values[0] if values[0] > 0 else 0

        # 生成洞察
        insights = []

        if slope > 0:
            insights.append(f"{keyword}呈现上升趋势，月均增长约{abs(slope):.1f}")
        elif slope < 0:
            insights.append(f"{keyword}呈现下降趋势，月均减少约{abs(slope):.1f}")
        else:
            insights.append(f"{keyword}趋势相对平稳")

        if r_squared > 0.7:
            insights.append(f"趋势拟合度高 (R²={r_squared:.2f})，趋势可信")
        elif r_squared < 0.3:
            insights.append(f"趋势波动较大 (R²={r_squared:.2f})")

        if inflection:
            insights.append(f"在时间点{inflection}附近检测到拐点")

        growth_stage_descriptions = {
            "explosive_growth": "处于爆发式增长阶段",
            "rapid_growth": "处于快速增长阶段",
            "steady_growth": "处于稳定增长阶段",
            "mature": "处于成熟期",
            "decline": "处于衰退期",
            "unknown": "数据不足，无法判断发展阶段"
        }
        insights.append(growth_stage_descriptions.get(growth_stage, ""))

        return {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "next_month_forecast": next_month_value,
            "moving_average_3": ma_3[-1] if ma_3 else None,
            "inflection_point": inflection,
            "growth_stage": growth_stage,
            "cagr": cagr,
            "insights": insights,
            "trend_direction": "up" if slope > 0 else "down" if slope < 0 else "stable"
        }

    def calculate_moving_average(self, values: List[float], window: int = 3) -> List[float]:
        """计算移动平均"""
        return self.predict_moving_average(values, window)

    def exponential_smoothing(self, values: List[float], alpha: float = 0.3) -> List[float]:
        """
        指数平滑
        alpha: 平滑系数，越大越重视近期数据
        """
        if not values:
            return []

        smoothed = [values[0]]
        for i in range(1, len(values)):
            smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[i - 1])

        return smoothed

    def detect_anomalies(self, values: List[float], threshold: float = 2.0) -> List[int]:
        """
        检测异常值
        使用 Z-score 方法
        """
        if len(values) < 3:
            return []

        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return []

        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                anomalies.append(i)

        return anomalies


class TechnologyAdoptionCurve:
    """
    技术采用曲线分析
    基于创新扩散理论
    """

    # 采用者类别占比
    INNOVATORS = 0.025  # 创新者
    EARLY_ADOPTERS = 0.135  # 早期采用者
    EARLY_MAJORITY = 0.34  # 早期大众
    LATE_MAJORITY = 0.34  # 晚期大众
    LAGGARDS = 0.16  # 落后者

    def __init__(self):
        self.predictor = TrendPredictor()

    def identify_adoption_stage(self, market_data: Dict) -> str:
        """
        识别技术采用阶段
        """
        penetration_rate = market_data.get("penetration_rate", 0)  # 市场渗透率
        growth_rate = market_data.get("growth_rate", 0)  # 增长率

        if penetration_rate < 0.025:
            return "innovators"  # 创新者阶段
        elif penetration_rate < 0.16:
            return "early_adopters"  # 早期采用者阶段
        elif penetration_rate < 0.50:
            if growth_rate > 0.3:
                return "early_majority_growth"  # 早期大众快速增长
            else:
                return "early_majority"  # 早期大众阶段
        elif penetration_rate < 0.84:
            return "late_majority"  # 晚期大众阶段
        else:
            return "laggards"  # 落后者阶段

    def predict_crossing_chasm(self, current_penetration: float, growth_rate: float) -> Dict:
        """
        预测跨越鸿沟的可能性
        """
        # 鸿沟位于早期采用者和早期大众之间（约 16% 渗透率）
        chasm_threshold = 0.16

        if current_penetration < chasm_threshold:
            # 计算到达鸿沟的时间
            if growth_rate > 0:
                periods_to_chasm = (chasm_threshold - current_penetration) / growth_rate
                return {
                    "approaching_chasm": True,
                    "periods_to_chasm": int(periods_to_chasm),
                    "chasm_crossing_probability": self._calculate_crossing_probability(growth_rate)
                }
            else:
                return {
                    "approaching_chasm": False,
                    "risk": "negative_growth",
                    "chasm_crossing_probability": 0.1
                }
        else:
            return {
                "approaching_chasm": False,
                "status": "crossed_chasm" if current_penetration > 0.5 else "post_chasm_growth"
            }

    def _calculate_crossing_probability(self, growth_rate: float) -> float:
        """计算跨越鸿沟的概率"""
        # 简化的概率模型
        if growth_rate > 0.5:
            return 0.8
        elif growth_rate > 0.3:
            return 0.6
        elif growth_rate > 0.1:
            return 0.4
        else:
            return 0.2


# 全局单例
trend_predictor = TrendPredictor()
technology_adoption_curve = TechnologyAdoptionCurve()
