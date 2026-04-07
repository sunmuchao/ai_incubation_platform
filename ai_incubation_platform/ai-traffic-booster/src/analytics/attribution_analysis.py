"""
归因分析服务

功能:
- 首次点击归因
- 末次点击归因
- 线性归因
- 时间衰减归因
- U 型归因
- 数据驱动归因
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from collections import defaultdict
from enum import Enum
import logging
import math

from schemas.analytics import TrackingEvent, EventType
from analytics.event_tracking import event_tracking_service

logger = logging.getLogger(__name__)


class AttributionModel(str, Enum):
    """归因模型枚举"""
    FIRST_CLICK = "first_click"         # 首次点击归因
    LAST_CLICK = "last_click"           # 末次点击归因
    LINEAR = "linear"                   # 线性归因
    TIME_DECAY = "time_decay"           # 时间衰减归因
    U_SHAPED = "u_shaped"               # U 型归因
    POSITION_BASED = "position_based"   # 位置加权归因


class AttributionResult:
    """归因结果"""
    def __init__(
        self,
        model: AttributionModel,
        channel_credits: Dict[str, float],
        total_conversions: int,
        total_value: float,
        analyzed_at: datetime = None
    ):
        self.model = model
        self.channel_credits = channel_credits
        self.total_conversions = total_conversions
        self.total_value = total_value
        self.analyzed_at = analyzed_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model.value,
            "channel_credits": {k: round(v, 4) for k, v in self.channel_credits.items()},
            "total_conversions": self.total_conversions,
            "total_value": round(self.total_value, 2),
            "analyzed_at": self.analyzed_at.isoformat()
        }


class AttributionAnalysisService:
    """
    归因分析服务

    对标 Google Analytics 的归因分析能力:
    - 多种归因模型支持
    - 渠道贡献评估
    - 归因对比分析
    """

    def __init__(self):
        # 归因模型配置
        self.u_shaped_first_last_credit = 0.4  # U 型模型首末触点各占 40%
        self.position_based_first_last_credit = 0.4  # 位置加权模型首末触点各占 40%
        self.time_decay_half_life = 7  # 时间衰减半衰期（天）

    def analyze_attribution(
        self,
        start_date: date,
        end_date: date,
        model: AttributionModel = AttributionModel.LAST_CLICK,
        conversion_event: str = "purchase",
        domain: Optional[str] = None
    ) -> AttributionResult:
        """
        执行归因分析

        Args:
            start_date: 开始日期
            end_date: 结束日期
            model: 归因模型
            conversion_event: 转化事件名称
            domain: 域名

        Returns:
            归因结果
        """
        # 获取事件数据
        events = event_tracking_service.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        if not events:
            return AttributionResult(
                model=model,
                channel_credits={},
                total_conversions=0,
                total_value=0
            )

        # 按用户分组事件
        user_events = self._group_by_user(events)

        # 识别转化路径
        conversion_paths = self._identify_conversion_paths(
            user_events, conversion_event
        )

        # 根据归因模型计算渠道贡献
        channel_credits = self._calculate_attribution(
            conversion_paths, model
        )

        # 计算总转化和价值
        total_conversions = len(conversion_paths)
        total_value = sum(path.get("value", 0) for path in conversion_paths)

        return AttributionResult(
            model=model,
            channel_credits=channel_credits,
            total_conversions=total_conversions,
            total_value=total_value
        )

    def compare_models(
        self,
        start_date: date,
        end_date: date,
        conversion_event: str = "purchase",
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        对比不同归因模型的结果

        Args:
            start_date: 开始日期
            end_date: 结束日期
            conversion_event: 转化事件名称
            domain: 域名

        Returns:
            模型对比结果
        """
        models = [
            AttributionModel.FIRST_CLICK,
            AttributionModel.LAST_CLICK,
            AttributionModel.LINEAR,
            AttributionModel.TIME_DECAY,
            AttributionModel.U_SHAPED
        ]

        results = {}
        for model in models:
            result = self.analyze_attribution(
                start_date, end_date, model, conversion_event, domain
            )
            results[model.value] = result.channel_credits

        # 计算模型间差异
        model_comparison = self._compare_model_results(results)

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "conversion_event": conversion_event,
            "models": results,
            "model_comparison": model_comparison
        }

    def analyze_channel_performance(
        self,
        start_date: date,
        end_date: date,
        conversion_event: str = "purchase"
    ) -> Dict[str, Any]:
        """
        分析渠道表现（多模型综合）

        Args:
            start_date: 开始日期
            end_date: 结束日期
            conversion_event: 转化事件名称

        Returns:
            渠道表现分析
        """
        # 获取各模型结果
        models_result = self.compare_models(
            start_date, end_date, conversion_event
        )

        # 计算各渠道的平均贡献
        all_channels = set()
        for model_credits in models_result["models"].values():
            all_channels.update(model_credits.keys())

        channel_performance = {}
        for channel in all_channels:
            credits = [
                models_result["models"][model].get(channel, 0)
                for model in models_result["models"]
            ]
            avg_credit = sum(credits) / len(credits) if credits else 0

            # 计算贡献稳定性
            credit_variance = self._calculate_variance(credits)

            channel_performance[channel] = {
                "avg_credit": round(avg_credit, 4),
                "credit_variance": round(credit_variance, 4),
                "stability": "高" if credit_variance < 0.05 else "中" if credit_variance < 0.15 else "低"
            }

        # 排序
        sorted_channels = sorted(
            channel_performance.items(),
            key=lambda x: x[1]["avg_credit"],
            reverse=True
        )

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "channel_performance": dict(sorted_channels),
            "top_channels": [ch for ch, _ in sorted_channels[:5]],
            "insights": self._generate_channel_insights(channel_performance)
        }

    def get_path_assisted_conversions(
        self,
        start_date: date,
        end_date: date,
        conversion_event: str = "purchase"
    ) -> Dict[str, Any]:
        """
        获取辅助转化数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            conversion_event: 转化事件名称

        Returns:
            辅助转化分析
        """
        events = event_tracking_service.get_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        if not events:
            return {"error": "未找到事件数据"}

        user_events = self._group_by_user(events)
        conversion_paths = self._identify_conversion_paths(user_events, conversion_event)

        # 统计各渠道的辅助转化和最终转化
        channel_assists = defaultdict(int)
        channel_last_clicks = defaultdict(int)

        for path in conversion_paths:
            touches = path["touches"]
            if len(touches) > 1:
                # 除最后触点外都是辅助
                for touch in touches[:-1]:
                    channel_assists[touch["channel"]] += 1
            # 最后触点
            channel_last_clicks[touches[-1]["channel"]] += 1

        # 计算辅助转化价值
        all_channels = set(channel_assists.keys()) | set(channel_last_clicks.keys())

        channel_data = {}
        for channel in all_channels:
            assists = channel_assists[channel]
            last_clicks = channel_last_clicks[channel]
            total = assists + last_clicks

            channel_data[channel] = {
                "assisted_conversions": assists,
                "last_click_conversions": last_clicks,
                "total_conversions": total,
                "assist_ratio": round(assists / total, 2) if total > 0 else 0
            }

        # 识别高辅助价值渠道
        high_assist_channels = [
            ch for ch, data in channel_data.items()
            if data["assist_ratio"] > 0.5 and data["assisted_conversions"] > 10
        ]

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "total_conversion_paths": len(conversion_paths),
            "channel_data": channel_data,
            "high_assist_channels": high_assist_channels,
            "insights": self._generate_assist_insights(channel_data)
        }

    def _group_by_user(
        self,
        events: List[TrackingEvent]
    ) -> Dict[str, List[TrackingEvent]]:
        """按用户分组事件"""
        user_events = defaultdict(list)

        for event in events:
            # 优先使用 user_id，否则使用 session_id
            user_id = event.user.user_id or event.user.session_id
            user_events[user_id].append(event)

        # 按时间排序
        for user_id, user_event_list in user_events.items():
            user_event_list.sort(key=lambda e: e.timestamp)

        return dict(user_events)

    def _identify_conversion_paths(
        self,
        user_events: Dict[str, List[TrackingEvent]],
        conversion_event: str
    ) -> List[Dict[str, Any]]:
        """识别转化路径"""
        conversion_paths = []

        for user_id, events in user_events.items():
            # 查找转化事件
            for i, event in enumerate(events):
                if event.event_name == conversion_event:
                    # 构建转化前的触点路径
                    touches = []
                    for j in range(i + 1):  # 包含转化事件本身
                        e = events[j]
                        channel = self._extract_channel(e)
                        touches.append({
                            "channel": channel,
                            "timestamp": e.timestamp,
                            "event": e.event_name,
                            "page": e.page_url
                        })

                    conversion_paths.append({
                        "user_id": user_id,
                        "touches": touches,
                        "value": event.value or 1.0,
                        "conversion_time": event.timestamp
                    })
                    break  # 每个用户只计算第一次转化

        return conversion_paths

    def _extract_channel(self, event: TrackingEvent) -> str:
        """从事件中提取渠道信息"""
        # 优先从 properties 中获取
        if event.properties:
            channel = event.properties.get("utm_source") or event.properties.get("channel")
            if channel:
                return channel

            # 从 referrer 推断
            referrer = event.context.referrer or ""
            if "google" in referrer.lower():
                return "google_organic"
            elif "facebook" in referrer.lower():
                return "facebook"
            elif "twitter" in referrer.lower():
                return "twitter"
            elif "linkedin" in referrer.lower():
                return "linkedin"

        # 从事件类型推断
        if event.event_type == EventType.PAGE_VIEW:
            return "direct"

        return "unknown"

    def _calculate_attribution(
        self,
        conversion_paths: List[Dict[str, Any]],
        model: AttributionModel
    ) -> Dict[str, float]:
        """根据归因模型计算渠道贡献"""
        channel_credits = defaultdict(float)

        for path in conversion_paths:
            touches = path["touches"]
            value = path.get("value", 1.0)

            if not touches:
                continue

            # 根据模型分配贡献
            if model == AttributionModel.FIRST_CLICK:
                self._apply_first_click(touches, channel_credits, value)
            elif model == AttributionModel.LAST_CLICK:
                self._apply_last_click(touches, channel_credits, value)
            elif model == AttributionModel.LINEAR:
                self._apply_linear(touches, channel_credits, value)
            elif model == AttributionModel.TIME_DECAY:
                self._apply_time_decay(touches, channel_credits, value)
            elif model == AttributionModel.U_SHAPED:
                self._apply_u_shaped(touches, channel_credits, value)
            elif model == AttributionModel.POSITION_BASED:
                self._apply_position_based(touches, channel_credits, value)

        # 归一化
        total = sum(channel_credits.values())
        if total > 0:
            for channel in channel_credits:
                channel_credits[channel] = channel_credits[channel] / total

        return dict(channel_credits)

    def _apply_first_click(
        self,
        touches: List[Dict],
        credits: defaultdict,
        value: float
    ):
        """首次点击归因 - 100% 归因于第一个触点"""
        if touches:
            channel = touches[0]["channel"]
            if channel not in credits:
                credits[channel] = 0.0
            credits[channel] += value

    def _apply_last_click(
        self,
        touches: List[Dict],
        credits: defaultdict,
        value: float
    ):
        """末次点击归因 - 100% 归因于最后一个触点"""
        if touches:
            channel = touches[-1]["channel"]
            if channel not in credits:
                credits[channel] = 0.0
            credits[channel] += value

    def _apply_linear(
        self,
        touches: List[Dict],
        credits: defaultdict,
        value: float
    ):
        """线性归因 - 平均分配给所有触点"""
        if touches:
            credit_per_touch = value / len(touches)
            for touch in touches:
                channel = touch["channel"]
                if channel not in credits:
                    credits[channel] = 0.0
                credits[channel] += credit_per_touch

    def _apply_time_decay(
        self,
        touches: List[Dict],
        credits: defaultdict,
        value: float
    ):
        """时间衰减归因 - 越接近转化权重越高"""
        if not touches:
            return

        # 使用指数衰减
        weights = []
        conversion_time = touches[-1]["timestamp"]

        for touch in touches:
            days_before = (conversion_time - touch["timestamp"]).days
            # 半衰期衰减
            weight = math.pow(0.5, days_before / self.time_decay_half_life)
            weights.append(weight)

        total_weight = sum(weights)
        if total_weight > 0:
            for i, touch in enumerate(touches):
                channel = touch["channel"]
                if channel not in credits:
                    credits[channel] = 0.0
                credits[channel] += value * (weights[i] / total_weight)

    def _apply_u_shaped(
        self,
        touches: List[Dict],
        credits: defaultdict,
        value: float
    ):
        """U 型归因 - 首末触点各 40%，中间平分 20%"""
        if not touches:
            return

        n = len(touches)

        if n == 1:
            credits[touches[0]["channel"]] += value
            return

        first_last_credit = value * self.u_shaped_first_last_credit
        middle_credit = value * (1 - 2 * self.u_shaped_first_last_credit)

        # 首个触点
        first_channel = touches[0]["channel"]
        if first_channel not in credits:
            credits[first_channel] = 0.0
        credits[first_channel] += first_last_credit

        # 中间触点平分
        if n > 2:
            credit_per_middle = middle_credit / (n - 2)
            for touch in touches[1:-1]:
                channel = touch["channel"]
                if channel not in credits:
                    credits[channel] = 0.0
                credits[channel] += credit_per_middle

        # 末个触点
        last_channel = touches[-1]["channel"]
        if last_channel not in credits:
            credits[last_channel] = 0.0
        credits[last_channel] += first_last_credit

    def _apply_position_based(
        self,
        touches: List[Dict],
        credits: defaultdict,
        value: float
    ):
        """位置加权归因 - 类似 U 型，首末各 40%，中间平分 20%"""
        # 与 U 型相同，可配置不同权重
        self._apply_u_shaped(touches, credits, value)

    def _compare_model_results(
        self,
        results: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """对比不同模型的结果"""
        all_channels = set()
        for model_credits in results.values():
            all_channels.update(model_credits.keys())

        comparison = {}
        for channel in all_channels:
            credits_by_model = {
                model: credits.get(channel, 0)
                for model, credits in results.items()
            }
            values = list(credits_by_model.values())

            comparison[channel] = {
                "credits_by_model": credits_by_model,
                "max_credit": max(values) if values else 0,
                "min_credit": min(values) if values else 0,
                "variance": self._calculate_variance(values)
            }

        # 识别模型敏感渠道
        sensitive_channels = [
            ch for ch, data in comparison.items()
            if data["variance"] > 0.1
        ]

        return {
            "channel_comparison": comparison,
            "model_sensitive_channels": sensitive_channels
        }

    def _calculate_variance(self, values: List[float]) -> float:
        """计算方差"""
        if len(values) < 2:
            return 0

        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)

    def _generate_channel_insights(
        self,
        channel_performance: Dict[str, Dict]
    ) -> List[str]:
        """生成渠道洞察"""
        insights = []

        # 找出表现最好的渠道
        top_channel = max(
            channel_performance.items(),
            key=lambda x: x[1]["avg_credit"]
        )
        if top_channel:
            insights.append(
                f"{top_channel[0]}是贡献最大的渠道，平均贡献{top_channel[1]['avg_credit']*100:.1f}%"
            )

        # 找出不稳定的渠道
        unstable = [
            ch for ch, data in channel_performance.items()
            if data["stability"] == "低"
        ]
        if unstable:
            insights.append(
                f"渠道 {', '.join(unstable)} 的贡献在不同模型间差异较大，建议深入分析"
            )

        return insights

    def _generate_assist_insights(
        self,
        channel_data: Dict[str, Dict]
    ) -> List[str]:
        """生成辅助转化洞察"""
        insights = []

        high_assist = [
            ch for ch, data in channel_data.items()
            if data["assist_ratio"] > 0.5
        ]
        if high_assist:
            insights.append(
                f"渠道 {', '.join(high_assist)} 主要起辅助作用，不应仅基于末次点击评估其价值"
            )

        last_click_dominant = [
            ch for ch, data in channel_data.items()
            if data["assist_ratio"] < 0.2 and data["last_click_conversions"] > 10
        ]
        if last_click_dominant:
            insights.append(
                f"渠道 {', '.join(last_click_dominant)} 主要是最终转化触点，是转化的临门一脚"
            )

        return insights


# 全局服务实例
attribution_analysis_service = AttributionAnalysisService()
