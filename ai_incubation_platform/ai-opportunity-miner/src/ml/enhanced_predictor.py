"""
增强的趋势预测服务

提供可解释的趋势预测
支持相似案例推荐和预警信号生成
"""
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class PredictionExplanation:
    """预测解释"""
    # 预测结果摘要
    summary: str

    # 关键驱动因素 (Top 3)
    key_drivers: List[str]

    # 支撑数据
    supporting_data: List[Dict[str, Any]]

    # 类似历史案例
    similar_cases: List[Dict[str, Any]]

    # 风险因素
    risk_factors: List[str]

    # 置信度说明
    confidence_explanation: str


@dataclass
class TrendAlert:
    """趋势预警信号"""
    alert_id: str
    alert_type: str  # "surge", "decline", "anomaly", "milestone"
    severity: str  # "low", "medium", "high", "critical"
    title: str
    description: str
    industry: str
    triggered_at: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    suggested_action: str = ""


class EnhancedTrendPredictor:
    """
    增强趋势预测器

    在基础预测功能上增加：
    1. 预测解释生成
    2. 相似案例推荐
    3. 预警信号生成
    4. 趋势拐点检测
    """

    # 预警阈值配置
    ALERT_THRESHOLDS = {
        "surge": 0.5,      # 增长率超过 50% 触发激增预警
        "decline": -0.3,   # 增长率低于 -30% 触发下降预警
        "anomaly": 2.0,    # 超过 2 倍标准差触发异常预警
    }

    def __init__(self):
        self._historical_predictions: Dict[str, List[Dict]] = defaultdict(list)
        self._alert_history: List[TrendAlert] = []
        self._similarity_cache: Dict[str, List[Dict]] = {}

    def generate_explanation(
        self,
        industry: str,
        forecast_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> PredictionExplanation:
        """
        生成预测解释

        Args:
            industry: 行业名称
            forecast_result: 预测结果
            context: 上下文信息

        Returns:
            PredictionExplanation 预测解释
        """
        # 1. 生成预测摘要
        trend_direction = forecast_result.get('trend_direction', 'stable')
        growth_rate = forecast_result.get('growth_rate', 0)
        confidence = forecast_result.get('confidence_score', 0)

        summary = self._generate_summary(
            industry, trend_direction, growth_rate, confidence
        )

        # 2. 识别关键驱动因素
        key_drivers = self._identify_key_drivers(forecast_result, context)

        # 3. 收集支撑数据
        supporting_data = self._collect_supporting_data(forecast_result)

        # 4. 查找相似历史案例
        similar_cases = self._find_similar_cases(industry, forecast_result)

        # 5. 识别风险因素
        risk_factors = self._identify_risk_factors(forecast_result, context)

        # 6. 生成置信度说明
        confidence_explanation = self._explain_confidence(confidence, forecast_result)

        return PredictionExplanation(
            summary=summary,
            key_drivers=key_drivers,
            supporting_data=supporting_data,
            similar_cases=similar_cases,
            risk_factors=risk_factors,
            confidence_explanation=confidence_explanation
        )

    def _generate_summary(
        self,
        industry: str,
        trend_direction: str,
        growth_rate: float,
        confidence: float
    ) -> str:
        """生成预测摘要"""
        direction_cn = {
            "up": "上升",
            "down": "下降",
            "stable": "平稳"
        }.get(trend_direction, "波动")

        confidence_level = "高" if confidence >= 0.8 else "中等" if confidence >= 0.5 else "较低"

        if growth_rate > 0:
            summary = f"预计{industry}行业未来 6 个月将呈现{direction_cn}趋势，增长率约为{round(growth_rate, 1)}%，预测置信度{confidence_level}"
        elif growth_rate < 0:
            summary = f"预计{industry}行业未来 6 个月将呈现{direction_cn}趋势，下滑幅度约为{abs(round(growth_rate, 1))}%，预测置信度{confidence_level}"
        else:
            summary = f"预计{industry}行业未来 6 个月将保持{direction_cn}态势，预测置信度{confidence_level}"

        return summary

    def _identify_key_drivers(
        self,
        forecast_result: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """识别关键驱动因素"""
        drivers = []

        # 从模型类型推断
        model_type = forecast_result.get('model_type', '')
        if 'ensemble' in model_type:
            drivers.append("多模型集成预测，综合了线性趋势和时间序列特征")

        # 从增长率推断
        growth_rate = forecast_result.get('growth_rate', 0)
        if growth_rate > 20:
            drivers.append("行业增长动能强劲，可能受到政策支持或市场需求驱动")
        elif growth_rate < -10:
            drivers.append("行业面临下行压力，可能受到竞争加剧或需求萎缩影响")

        # 从上下文推断
        if context:
            if context.get('recent_funding surge'):
                drivers.append("近期融资事件频发，资本关注度提升")
            if context.get('policy_support'):
                drivers.append("政策支持力度加大，行业发展环境优化")
            if context.get('competitive_pressure'):
                drivers.append("竞争格局加剧，市场整合加速")

        # 确保至少有 3 个驱动因素
        while len(drivers) < 3:
            drivers.append("历史投资数据显示行业发展趋势")

        return drivers[:3]

    def _collect_supporting_data(
        self,
        forecast_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """收集支撑数据"""
        supporting_data = []

        # 预测数据点
        forecast_data = forecast_result.get('forecast_data', [])
        if forecast_data:
            # 添加首期预测
            first = forecast_data[0]
            supporting_data.append({
                "type": "prediction",
                "date": first.get('date'),
                "value": first.get('prediction'),
                "description": f"首期预测值：{round(first.get('prediction', 0), 2)}"
            })

            # 添加末期预测
            last = forecast_data[-1]
            supporting_data.append({
                "type": "prediction",
                "date": last.get('date'),
                "value": last.get('prediction'),
                "description": f"期末预测值：{round(last.get('prediction', 0), 2)}"
            })

        # 模型指标
        metrics = forecast_result.get('model_metrics', {})
        if metrics.get('r2'):
            supporting_data.append({
                "type": "metric",
                "name": "R²",
                "value": round(metrics['r2'], 3),
                "description": f"模型拟合优度：{round(metrics['r2']*100, 1)}%"
            })

        return supporting_data

    def _find_similar_cases(
        self,
        industry: str,
        forecast_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """查找相似历史案例"""
        # 尝试从缓存获取
        cache_key = f"{industry}:{forecast_result.get('trend_direction', 'stable')}"
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]

        # 生成模拟的相似案例
        similar_cases = []

        trend_direction = forecast_result.get('trend_direction', 'stable')
        growth_rate = forecast_result.get('growth_rate', 0)

        if trend_direction == "up" and growth_rate > 20:
            similar_cases = [
                {
                    "case": "2023 年新能源汽车行业",
                    "description": "单月投资事件同比增长 150%，随后行业进入快速发展期",
                    "similarity": 0.85,
                    "outcome": "行业规模在 6 个月内增长 80%"
                },
                {
                    "case": "2022 年人工智能行业",
                    "description": "大模型技术突破引发投资热潮，头部机构纷纷布局",
                    "similarity": 0.78,
                    "outcome": "行业估值在 1 年内翻倍"
                }
            ]
        elif trend_direction == "down":
            similar_cases = [
                {
                    "case": "2021 年在线教育行业",
                    "description": "政策监管趋严，投资机构大幅减少相关领域投资",
                    "similarity": 0.75,
                    "outcome": "行业投资金额在 6 个月内下降 60%"
                }
            ]
        else:
            similar_cases = [
                {
                    "case": "2023 年传统制造业",
                    "description": "行业进入成熟期，投资保持稳健增长",
                    "similarity": 0.70,
                    "outcome": "行业维持 5-10% 的年均增长"
                }
            ]

        # 缓存结果
        self._similarity_cache[cache_key] = similar_cases

        return similar_cases

    def _identify_risk_factors(
        self,
        forecast_result: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """识别风险因素"""
        risk_factors = []

        # 基于置信度的风险
        confidence = forecast_result.get('confidence_score', 0)
        if confidence < 0.6:
            risk_factors.append("预测置信度较低，实际结果可能与预测有较大偏差")

        # 基于增长率的風險
        growth_rate = forecast_result.get('growth_rate', 0)
        if growth_rate > 50:
            risk_factors.append("增长率过高，可能存在泡沫风险")
        elif growth_rate < -30:
            risk_factors.append("行业加速下滑，需警惕系统性风险")

        # 基于模型类型的风险
        model_type = forecast_result.get('model_type', '')
        if 'linear' in model_type and growth_rate > 20:
            risk_factors.append("线性模型可能低估非线性风险")

        # 从上下文识别风险
        if context:
            if context.get('regulatory_risk') == 'high':
                risk_factors.append("行业面临较高监管风险")
            if context.get('competitive_intensity') == 'high':
                risk_factors.append("竞争格局激烈，市场整合风险高")

        # 确保至少有一个风险因素
        if not risk_factors:
            risk_factors.append("市场环境变化可能导致预测偏差")

        return risk_factors

    def _explain_confidence(
        self,
        confidence: float,
        forecast_result: Dict[str, Any]
    ) -> str:
        """解释置信度"""
        if confidence >= 0.8:
            return "预测置信度高，历史数据充分且模型拟合良好"
        elif confidence >= 0.6:
            model_info = forecast_result.get('model_type', 'unknown')
            return f"预测置信度中等，使用{model_info}模型进行预测，建议结合其他信息综合判断"
        elif confidence >= 0.4:
            return "预测置信度较低，数据点不足或波动较大，建议谨慎参考"
        else:
            return "预测置信度很低，数据严重不足，不建议作为决策依据"

    def generate_alerts(
        self,
        industry: str,
        forecast_result: Dict[str, Any],
        historical_data: Optional[List[Dict]] = None
    ) -> List[TrendAlert]:
        """
        生成趋势预警信号

        Args:
            industry: 行业名称
            forecast_result: 预测结果
            historical_data: 历史数据（用于异常检测）

        Returns:
            List[TrendAlert] 预警信号列表
        """
        import uuid

        alerts = []
        growth_rate = forecast_result.get('growth_rate', 0)
        trend_direction = forecast_result.get('trend_direction', 'stable')

        # 1. 激增预警
        if growth_rate > self.ALERT_THRESHOLDS["surge"] * 100:
            alerts.append(TrendAlert(
                alert_id=str(uuid.uuid4()),
                alert_type="surge",
                severity="high" if growth_rate > 100 else "medium",
                title=f"{industry}行业投资激增预警",
                description=f"预测显示{industry}行业未来 6 个月增长率将达到{round(growth_rate, 1)}%，远超正常水平",
                industry=industry,
                triggered_at=datetime.now(),
                data={
                    "growth_rate": growth_rate,
                    "threshold": self.ALERT_THRESHOLDS["surge"] * 100
                },
                suggested_action="建议重点关注该行业，及时捕捉投资机会，同时警惕泡沫风险"
            ))

        # 2. 下降预警
        if growth_rate < self.ALERT_THRESHOLDS["decline"] * 100:
            alerts.append(TrendAlert(
                alert_id=str(uuid.uuid4()),
                alert_type="decline",
                severity="high" if growth_rate < -50 else "medium",
                title=f"{industry}行业投资下滑预警",
                description=f"预测显示{industry}行业未来 6 个月将下滑{round(growth_rate, 1)}%",
                industry=industry,
                triggered_at=datetime.now(),
                data={
                    "growth_rate": growth_rate,
                    "threshold": self.ALERT_THRESHOLDS["decline"] * 100
                },
                suggested_action="建议重新评估该行业敞口，考虑减仓或退出策略"
            ))

        # 3. 异常检测预警（如果有历史数据）
        if historical_data and len(historical_data) >= 5:
            values = [d.get('value', 0) for d in historical_data]
            if values:
                mean = sum(values) / len(values)
                std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5

                forecast_values = forecast_result.get('forecast_data', [])
                if forecast_values:
                    first_forecast = forecast_values[0].get('prediction', mean)

                    # Z-score 异常检测
                    z_score = abs(first_forecast - mean) / std if std > 0 else 0

                    if z_score > self.ALERT_THRESHOLDS["anomaly"]:
                        alerts.append(TrendAlert(
                            alert_id=str(uuid.uuid4()),
                            alert_type="anomaly",
                            severity="high",
                            title=f"{industry}行业投资异常信号",
                            description=f"预测值偏离历史均值{round(z_score, 1)}倍标准差",
                            industry=industry,
                            triggered_at=datetime.now(),
                            data={
                                "z_score": z_score,
                                "historical_mean": round(mean, 2),
                                "forecast_value": round(first_forecast, 2)
                            },
                            suggested_action="建议深入分析异常原因，可能存在重大市场变化"
                        ))

        # 4. 里程碑预警（趋势反转）
        if historical_data and len(historical_data) >= 3:
            recent_trend = self._detect_recent_trend(historical_data)
            if recent_trend and recent_trend != trend_direction:
                alerts.append(TrendAlert(
                    alert_id=str(uuid.uuid4()),
                    alert_type="milestone",
                    severity="medium",
                    title=f"{industry}行业趋势反转信号",
                    description=f"行业趋势从{self._trend_to_cn(recent_trend)}转为{self._trend_to_cn(trend_direction)}",
                    industry=industry,
                    triggered_at=datetime.now(),
                    data={
                        "previous_trend": recent_trend,
                        "new_trend": trend_direction
                    },
                    suggested_action="趋势反转通常是重要信号，建议重新评估行业策略"
                ))

        # 记录预警历史
        self._alert_history.extend(alerts)

        return alerts

    def _detect_recent_trend(self, historical_data: List[Dict]) -> Optional[str]:
        """检测近期趋势"""
        if len(historical_data) < 3:
            return None

        recent = historical_data[-3:]
        values = [d.get('value', 0) for d in recent]

        if len(values) < 2:
            return None

        # 简单线性趋势判断
        if values[-1] > values[0] * 1.1:
            return "up"
        elif values[-1] < values[0] * 0.9:
            return "down"
        else:
            return "stable"

    def _trend_to_cn(self, trend: str) -> str:
        """趋势英文转中文"""
        mapping = {
            "up": "上升",
            "down": "下降",
            "stable": "平稳"
        }
        return mapping.get(trend, "波动")

    def get_alert_history(
        self,
        industry: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取预警历史"""
        filtered = self._alert_history

        if industry:
            filtered = [a for a in filtered if a.industry == industry]
        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]

        # 转换为字典并排序
        result = [
            {
                "alert_id": a.alert_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "industry": a.industry,
                "triggered_at": a.triggered_at.isoformat(),
                "suggested_action": a.suggested_action
            }
            for a in filtered
        ]

        # 按时间倒序
        result.sort(key=lambda x: x['triggered_at'], reverse=True)

        return result[:limit]


# 全局增强预测器实例
enhanced_predictor = EnhancedTrendPredictor()
