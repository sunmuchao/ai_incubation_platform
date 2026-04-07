"""
AI 查询助手服务层

提供自然语言查询、结果解释、报告生成等核心服务
"""
import re
import json
import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from models.query_assistant import (
    QueryHistory, QueryFavorite, SavedReport, QueryTemplate,
    QueryIntent, QueryStatus, QueryEntities, TimeRange, Filter, Comparison
)
from repositories.query_repository import QueryAssistantRepository

logger = logging.getLogger(__name__)


class TimeUnit(Enum):
    """时间单位"""
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


@dataclass
class ParsedQuery:
    """解析后的查询"""
    intent: QueryIntent
    entities: QueryEntities
    confidence: float  # 解析置信度
    original_text: str


@dataclass
class QueryResult:
    """查询结果"""
    query: QueryHistory
    data: Dict[str, Any]
    interpretation: str
    suggestions: List[str] = field(default_factory=list)


class NaturalLanguageParser:
    """
    自然语言查询解析器

    将用户的自然语言查询解析为结构化的 QueryEntities
    """

    def __init__(self):
        # 时间表达式映射
        self.time_patterns = {
            r'上周 | 过去一周 | 最近一周|last\s*week': ("last_7_days", 7),
            r'上月 | 过去一月 | 最近一月|last\s*month': ("last_30_days", 30),
            r'今天|today|this\s*day': ("today", 1),
            r'昨天|yesterday': ("yesterday", 1),
            r'最近 7 天|past\s*7\s*days': ("last_7_days", 7),
            r'最近 30 天|past\s*30\s*days': ("last_30_days", 30),
            r'最近 90 天|past\s*90\s*days': ("last_90_days", 90),
            r'这个月|this\s*month': ("this_month", 0),
            r'上个月|last\s*month': ("last_month", 0),
            r'今年|this\s*year': ("this_year", 0),
            r'去年同期|same\s*period\s*last\s*year': ("yoy", 0),
        }

        # 指标映射
        self.metric_patterns = {
            r'流量|traffic|sessions': "sessions",
            r'访问 | 会话': "sessions",
            r'pv|页面浏览 | 页面访问量|page\s*view': "pv",
            r'uv|用户数 | 独立用户|unique\s*visitor': "uv",
            r'跳出率|bounce\s*rate': "bounce_rate",
            r'转化率|conversion\s*rate': "conversion_rate",
            r'转化|conversions': "conversions",
            r'留存率|retention\s*rate': "retention_rate",
            r'平均停留时长|avg\s*time.*spent': "avg_time_on_page",
            r'点击率|ctr|click.*rate': "ctr",
        }

        # 维度映射
        self.dimension_patterns = {
            r'页面|page|url|path': "page_path",
            r'来源 | 渠道|source|channel': "source",
            r'设备|device|terminal': "device_type",
            r'地区 | 城市|geo|location': "country",
            r'浏览器|browser': "browser",
            r'操作系统|os|operating.*system': "os",
            r'日期|时间|date|time': "date",
        }

        # 意图关键词
        self.intent_patterns = {
            r'趋势|trend|how.*change': QueryIntent.TREND_QUERY,
            r'对比 | 比较|compare|vs': QueryIntent.COMPARISON_QUERY,
            r'哪个.*最|what.*most|highest|top|ranking': QueryIntent.PAGE_QUERY,
            r'为什么|why|reason|cause': QueryIntent.ROOT_CAUSE_QUERY,
            r'异常 | 问题|anomaly|issue|drop|decrease': QueryIntent.ANOMALY_QUERY,
            r'建议 | 如何提升|recommend|how to improve': QueryIntent.RECOMMENDATION_QUERY,
            r'留存|retention': QueryIntent.USER_QUERY,
            r'转化|conversion': QueryIntent.USER_QUERY,
            r'竞品|competitor': QueryIntent.COMPETITOR_QUERY,
            r'流量.*多少|traffic.*how.*much': QueryIntent.TRAFFIC_QUERY,
        }

    def parse(self, query_text: str) -> ParsedQuery:
        """
        解析自然语言查询

        Args:
            query_text: 用户输入的自然语言查询

        Returns:
            解析后的查询对象
        """
        query_text_lower = query_text.lower()

        # 1. 识别意图
        intent, intent_confidence = self._identify_intent(query_text_lower)

        # 2. 提取时间范围
        time_range = self._extract_time_range(query_text_lower)

        # 3. 提取指标
        metrics = self._extract_metrics(query_text_lower)

        # 4. 提取维度
        dimensions = self._extract_dimensions(query_text_lower)

        # 5. 提取筛选条件
        filters = self._extract_filters(query_text)

        # 6. 提取比较配置
        comparison = self._extract_comparison(query_text_lower)

        # 7. 提取排序和限制
        order_by, order_direction, limit = self._extract_ordering(query_text_lower)

        # 构建实体对象
        entities = QueryEntities(
            time_range=time_range,
            metrics=metrics if metrics else ["sessions"],  # 默认指标
            dimensions=dimensions,
            filters=filters,
            comparison=comparison,
            order_by=order_by,
            order_direction=order_direction,
            limit=limit
        )

        # 计算整体置信度
        confidence = self._calculate_confidence(
            intent_confidence,
            bool(time_range),
            bool(metrics),
            bool(dimensions)
        )

        return ParsedQuery(
            intent=intent,
            entities=entities,
            confidence=confidence,
            original_text=query_text
        )

    def _identify_intent(self, query_text: str) -> Tuple[QueryIntent, float]:
        """识别查询意图"""
        for pattern, intent in self.intent_patterns.items():
            if re.search(pattern, query_text):
                return intent, 0.9

        # 默认意图
        return QueryIntent.GENERAL_QUERY, 0.5

    def _extract_time_range(self, query_text: str) -> Optional[TimeRange]:
        """提取时间范围"""
        for pattern, (period, days) in self.time_patterns.items():
            if re.search(pattern, query_text):
                return TimeRange(relative_period=period)

        # 尝试提取具体日期
        date_pattern = r'(\d{4}-\d{2}-\d{2})\s*(?:to|至)\s*(\d{4}-\d{2}-\d{2})'
        match = re.search(date_pattern, query_text)
        if match:
            return TimeRange(
                start_date=datetime.strptime(match.group(1), "%Y-%m-%d"),
                end_date=datetime.strptime(match.group(2), "%Y-%m-%d")
            )

        return None

    def _extract_metrics(self, query_text: str) -> List[str]:
        """提取指标"""
        metrics = []
        for pattern, metric in self.metric_patterns.items():
            if re.search(pattern, query_text):
                metrics.append(metric)
        return metrics

    def _extract_dimensions(self, query_text: str) -> List[str]:
        """提取维度"""
        dimensions = []
        for pattern, dim in self.dimension_patterns.items():
            if re.search(pattern, query_text):
                dimensions.append(dim)
        return dimensions

    def _extract_filters(self, query_text: str) -> List[Filter]:
        """提取筛选条件"""
        filters = []

        # 页面筛选：包含某个路径
        page_pattern = r'页面.*包含 | 包含.*页面|page.*contain|contain.*page'
        if re.search(page_pattern, query_text, re.IGNORECASE):
            # 提取路径
            path_match = re.search(r'["\']([^"\']+)["\']', query_text)
            if path_match:
                filters.append(Filter(
                    field="page_path",
                    operator="contains",
                    value=path_match.group(1)
                ))

        # 设备筛选：移动端/桌面端
        if re.search(r'移动 | 手机|mobile', query_text):
            filters.append(Filter(field="device_type", operator="equals", value="mobile"))
        if re.search(r'桌面 | 电脑|desktop', query_text):
            filters.append(Filter(field="device_type", operator="equals", value="desktop"))

        # 来源筛选
        source_match = re.search(r'来源.*?["\']([^"\']+)["\']', query_text)
        if source_match:
            filters.append(Filter(
                field="source",
                operator="equals",
                value=source_match.group(1)
            ))

        return filters

    def _extract_comparison(self, query_text: str) -> Optional[Comparison]:
        """提取比较配置"""
        if re.search(r'环比|previous\s*period|last\s*period', query_text):
            return Comparison(compare_type="previous_period")
        if re.search(r'同比|same\s*period|last\s*year', query_text):
            return Comparison(compare_type="same_period_last_year")
        if re.search(r'竞品|competitor', query_text):
            return Comparison(compare_type="competitor")
        if re.search(r'行业.*基准|industry.*benchmark', query_text):
            return Comparison(compare_type="benchmark")
        return None

    def _extract_ordering(self, query_text: str) -> Tuple[Optional[str], str, int]:
        """提取排序和限制配置"""
        order_by = None
        order_direction = "desc"
        limit = 10

        # 最高/最多
        if re.search(r'最高 | 最多|highest|most|top', query_text):
            order_direction = "desc"
            limit = 1

        # 最低/最少
        if re.search(r'最低 | 最少|lowest|least', query_text):
            order_direction = "asc"
            limit = 1

        # 前 N 个
        top_n = re.search(r'前 (\d+) 个|top\s*(\d+)', query_text)
        if top_n:
            limit = int(top_n.group(1) or top_n.group(2))

        # 排行榜
        if re.search(r'排行榜 | 排名|ranking', query_text):
            order_direction = "desc"

        return order_by, order_direction, limit

    def _calculate_confidence(self, intent_conf: float, has_time: bool,
                             has_metrics: bool, has_dimensions: bool) -> float:
        """计算整体解析置信度"""
        confidence = intent_conf

        # 有时间范围增加置信度
        if has_time:
            confidence += 0.05
        # 有指标增加置信度
        if has_metrics:
            confidence += 0.05
        # 有维度增加置信度
        if has_dimensions:
            confidence += 0.05

        return min(confidence, 1.0)


class QueryExecutor:
    """
    查询执行器

    根据解析后的查询实体执行数据查询
    """

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode  # 演示模式使用 Mock 数据

    def execute(self, entities: QueryEntities, intent: QueryIntent) -> Dict[str, Any]:
        """
        执行查询

        Args:
            entities: 查询实体
            intent: 查询意图

        Returns:
            查询结果数据
        """
        if self.mock_mode:
            return self._execute_mock(entities, intent)
        else:
            return self._execute_real(entities, intent)

    def _execute_mock(self, entities: QueryEntities, intent: QueryIntent) -> Dict[str, Any]:
        """执行 Mock 查询（演示用）"""
        # 根据意图生成不同的 Mock 数据
        if intent == QueryIntent.TRAFFIC_QUERY:
            return self._mock_traffic_data(entities)
        elif intent == QueryIntent.TREND_QUERY:
            return self._mock_trend_data(entities)
        elif intent == QueryIntent.PAGE_QUERY:
            return self._mock_page_ranking(entities)
        elif intent == QueryIntent.COMPARISON_QUERY:
            return self._mock_comparison_data(entities)
        elif intent in [QueryIntent.ANOMALY_QUERY, QueryIntent.ROOT_CAUSE_QUERY]:
            return self._mock_anomaly_data(entities)
        elif intent == QueryIntent.RECOMMENDATION_QUERY:
            return self._mock_recommendation_data(entities)
        else:
            return self._mock_general_data(entities)

    def _mock_traffic_data(self, entities: QueryEntities) -> Dict[str, Any]:
        """Mock 流量数据"""
        return {
            "summary": {
                "sessions": 15234,
                "pv": 45678,
                "uv": 12345,
                "bounce_rate": 0.42,
                "avg_time_on_page": 245
            },
            "period": entities.time_range.relative_period if entities.time_range else "last_7_days",
            "comparison": {
                "sessions_change": 0.15,
                "pv_change": 0.12,
                "uv_change": 0.08
            }
        }

    def _mock_trend_data(self, entities: QueryEntities) -> Dict[str, Any]:
        """Mock 趋势数据"""
        import random
        base = 500
        dates = []
        values = []

        period = entities.time_range.relative_period if entities.time_range else "last_30_days"
        days = 30 if "30" in period else 7 if "7" in period else 90

        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i)).strftime("%Y-%m-%d")
            dates.append(date)
            # 模拟有波动的趋势
            value = base + random.randint(-100, 200) + (i * 5)
            values.append({"date": date, "sessions": value})

        return {
            "trend": values,
            "summary": {
                "total_sessions": sum(v["sessions"] for v in values),
                "avg_daily_sessions": sum(v["sessions"] for v in values) // len(values),
                "growth_rate": 0.15
            }
        }

    def _mock_page_ranking(self, entities: QueryEntities) -> Dict[str, Any]:
        """Mock 页面排行数据"""
        pages = [
            {"page_path": "/products/ai-tool", "pv": 5234, "uv": 4123, "bounce_rate": 0.35},
            {"page_path": "/blog/seo-guide", "pv": 4521, "uv": 3890, "bounce_rate": 0.28},
            {"page_path": "/", "pv": 3890, "uv": 3456, "bounce_rate": 0.45},
            {"page_path": "/pricing", "pv": 2345, "uv": 2100, "bounce_rate": 0.32},
            {"page_path": "/about", "pv": 1890, "uv": 1567, "bounce_rate": 0.55},
            {"page_path": "/contact", "pv": 1234, "uv": 1100, "bounce_rate": 0.40},
            {"page_path": "/blog", "pv": 1100, "uv": 980, "bounce_rate": 0.38},
            {"page_path": "/docs", "pv": 890, "uv": 756, "bounce_rate": 0.25},
            {"page_path": "/features", "pv": 756, "uv": 654, "bounce_rate": 0.30},
            {"page_path": "/login", "pv": 567, "uv": 500, "bounce_rate": 0.60},
        ]
        return {"pages": pages[:entities.limit]}

    def _mock_comparison_data(self, entities: QueryEntities) -> Dict[str, Any]:
        """Mock 对比数据"""
        return {
            "current_period": {
                "sessions": 15234,
                "pv": 45678,
                "uv": 12345,
                "conversion_rate": 0.035
            },
            "previous_period": {
                "sessions": 13245,
                "pv": 40567,
                "uv": 11456,
                "conversion_rate": 0.032
            },
            "change": {
                "sessions": 0.15,
                "pv": 0.126,
                "uv": 0.078,
                "conversion_rate": 0.094
            }
        }

    def _mock_anomaly_data(self, entities: QueryEntities) -> Dict[str, Any]:
        """Mock 异常检测数据"""
        return {
            "anomalies": [
                {
                    "metric": "sessions",
                    "date": "2026-04-03",
                    "expected": 2100,
                    "actual": 1456,
                    "deviation": -0.31,
                    "severity": "high"
                }
            ],
            "possible_causes": [
                {
                    "factor": "organic_search",
                    "impact": 0.45,
                    "description": "自然搜索流量下降 45%"
                },
                {
                    "factor": "page_speed",
                    "impact": 0.25,
                    "description": "页面加载时间增加 2 秒"
                }
            ]
        }

    def _mock_recommendation_data(self, entities: QueryEntities) -> Dict[str, Any]:
        """Mock 推荐数据"""
        return {
            "recommendations": [
                {
                    "type": "seo",
                    "priority": "high",
                    "title": "优化核心页面标题和描述",
                    "description": "首页和产品页的 Title/Description 可以进一步优化，提升 CTR",
                    "expected_impact": 0.15,
                    "effort": "low"
                },
                {
                    "type": "content",
                    "priority": "medium",
                    "title": "增加博客更新频率",
                    "description": "博客文章带来 40% 的新增流量，建议每周至少发布 2 篇",
                    "expected_impact": 0.20,
                    "effort": "medium"
                },
                {
                    "type": "technical",
                    "priority": "medium",
                    "title": "优化移动端页面加载速度",
                    "description": "移动端跳出率比桌面端高 30%，主要因为加载速度慢",
                    "expected_impact": 0.10,
                    "effort": "medium"
                }
            ]
        }

    def _mock_general_data(self, entities: QueryEntities) -> Dict[str, Any]:
        """Mock 通用数据"""
        return {
            "summary": {
                "sessions": 15234,
                "pv": 45678,
                "uv": 12345
            }
        }

    def _execute_real(self, entities: QueryEntities, intent: QueryIntent) -> Dict[str, Any]:
        """执行真实查询（待实现 - 需要对接实际数据源）"""
        # TODO: 对接实际的数据源
        logger.warning("Real query execution not yet implemented")
        return self._execute_mock(entities, intent)


class ResultInterpreter:
    """
    结果解释器

    使用 AI 生成数据解读和建议
    """

    def __init__(self):
        self._llm_client = None  # 可以集成 LLM 服务

    def interpret(self, data: Dict[str, Any], intent: QueryIntent,
                 original_query: str) -> Tuple[str, List[str]]:
        """
        解释查询结果

        Args:
            data: 查询结果数据
            intent: 查询意图
            original_query: 原始查询文本

        Returns:
            (解读文本，建议列表)
        """
        if intent == QueryIntent.TRAFFIC_QUERY:
            return self._interpret_traffic(data, original_query)
        elif intent == QueryIntent.TREND_QUERY:
            return self._interpret_trend(data, original_query)
        elif intent == QueryIntent.PAGE_QUERY:
            return self._interpret_ranking(data, original_query)
        elif intent == QueryIntent.COMPARISON_QUERY:
            return self._interpret_comparison(data, original_query)
        elif intent in [QueryIntent.ANOMALY_QUERY, QueryIntent.ROOT_CAUSE_QUERY]:
            return self._interpret_anomaly(data, original_query)
        elif intent == QueryIntent.RECOMMENDATION_QUERY:
            return self._interpret_recommendations(data, original_query)
        else:
            return self._interpret_general(data, original_query)

    def _interpret_traffic(self, data: Dict, query: str) -> Tuple[str, List[str]]:
        """解释流量数据"""
        summary = data.get("summary", {})
        comparison = data.get("comparison", {})

        sessions = summary.get("sessions", 0)
        sessions_change = comparison.get("sessions_change", 0)

        trend_desc = "增长" if sessions_change > 0 else "下降" if sessions_change < 0 else "持平"
        change_pct = abs(sessions_change * 100)

        interpretation = (
            f"根据您的数据，{query}的查询结果显示：\n\n"
            f"**流量概况**:\n"
            f"- 会话数：{sessions:,} 次\n"
            f"- PV（页面浏览量）：{summary.get('pv', 0):,} 次\n"
            f"- UV（独立用户数）：{summary.get('uv', 0):,} 人\n"
            f"- 跳出率：{summary.get('bounce_rate', 0)*100:.1f}%\n\n"
            f"**趋势分析**:\n"
            f"与前一周相比，流量{trend_desc}{change_pct:.1f}%，"
            f"这是一个{'积极' if sessions_change > 0 else '需要关注' if sessions_change < 0 else '稳定'}的信号。"
        )

        suggestions = []
        if sessions_change < -0.1:
            suggestions.append("建议检查流量下跌的具体原因，可以查看各渠道流量变化")
        if summary.get("bounce_rate", 0) > 0.5:
            suggestions.append("跳出率偏高，建议优化页面内容和用户体验")
        if summary.get("avg_time_on_page", 0) < 120:
            suggestions.append("平均停留时间较短，考虑增加更有吸引力的内容")

        return interpretation, suggestions

    def _interpret_trend(self, data: Dict, query: str) -> Tuple[str, List[str]]:
        """解释趋势数据"""
        trend = data.get("trend", [])
        summary = data.get("summary", {})

        if not trend:
            return "暂无趋势数据", []

        first_value = trend[0]["sessions"] if trend else 0
        last_value = trend[-1]["sessions"] if trend else 0
        growth = ((last_value - first_value) / first_value * 100) if first_value > 0 else 0

        interpretation = (
            f"根据{query}的查询结果，以下是流量趋势分析：\n\n"
            f"**整体趋势**:\n"
            f"- 期间总会话数：{summary.get('total_sessions', 0):,}\n"
            f"- 日均会话数：{summary.get('avg_daily_sessions', 0):,}\n"
            f"- 整体增长率：{growth:+.1f}%\n\n"
            f"**趋势解读**:\n"
            f"流量呈现{'上升' if growth > 0 else '下降' if growth < 0 else '平稳'}趋势，"
            f"建议结合具体事件（如营销活动、产品更新）分析波动原因。"
        )

        suggestions = []
        if growth > 20:
            suggestions.append("流量增长显著，建议分析增长来源并考虑如何保持")
        elif growth < -20:
            suggestions.append("流量下降明显，建议进行根因分析并采取补救措施")

        return interpretation, suggestions

    def _interpret_ranking(self, data: Dict, query: str) -> Tuple[str, List[str]]:
        """解释排行数据"""
        pages = data.get("pages", [])

        if not pages:
            return "暂无页面数据", []

        top_page = pages[0]
        interpretation = (
            f"根据{query}的查询结果，以下是页面流量排行分析：\n\n"
            f"**TOP 3 页面**:\n"
        )

        for i, page in enumerate(pages[:3], 1):
            interpretation += (
                f"{i}. `{page['page_path']}`\n"
                f"   - PV: {page['pv']:,} | UV: {page['uv']:,} | 跳出率：{page['bounce_rate']*100:.1f}%\n"
            )

        interpretation += (
            f"\n**洞察**:\n"
            f"最受欢迎的页面是 `{top_page['page_path']}`，"
            f"占总 PV 的{top_page['pv']/sum(p['pv'] for p in pages)*100:.1f}%。\n"
            f"建议分析高流量页面的成功要素，并复制到其他页面。"
        )

        suggestions = []
        low_performers = [p for p in pages if p["bounce_rate"] > 0.5]
        if low_performers:
            suggestions.append(
                f"以下页面跳出率偏高，建议优化：{', '.join(p['page_path'] for p in low_performers)}"
            )

        return interpretation, suggestions

    def _interpret_comparison(self, data: Dict, query: str) -> Tuple[str, List[str]]:
        """解释对比数据"""
        current = data.get("current_period", {})
        previous = data.get("previous_period", {})
        change = data.get("change", {})

        interpretation = (
            f"根据{query}的查询结果，以下是环比对比分析：\n\n"
            f"**本期数据**:\n"
            f"- 会话数：{current.get('sessions', 0):,} ({change.get('sessions', 0)*100:+.1f}%)\n"
            f"- PV: {current.get('pv', 0):,} ({change.get('pv', 0)*100:+.1f}%)\n"
            f"- UV: {current.get('uv', 0):,} ({change.get('uv', 0)*100:+.1f}%)\n"
            f"- 转化率：{current.get('conversion_rate', 0)*100:.2f}% ({change.get('conversion_rate', 0)*100:+.2f}%)\n\n"
            f"**对比解读**:\n"
        )

        # 判断整体表现
        metrics_improved = sum(1 for v in change.values() if v > 0)
        metrics_declined = sum(1 for v in change.values() if v < 0)

        if metrics_improved > metrics_declined:
            interpretation += "整体表现良好，大部分指标呈现增长趋势。"
        elif metrics_declined > metrics_improved:
            interpretation += "需要关注，多个指标出现下滑。"
        else:
            interpretation += "表现平稳，各指标变化不大。"

        suggestions = []
        if change.get("conversion_rate", 0) < 0:
            suggestions.append("转化率下降，建议检查转化漏斗各节点的转化情况")
        if change.get("sessions", 0) < -0.1:
            suggestions.append("流量下滑超过 10%，建议进行根因分析")

        return interpretation, suggestions

    def _interpret_anomaly(self, data: Dict, query: str) -> Tuple[str, List[str]]:
        """解释异常数据"""
        anomalies = data.get("anomalies", [])
        causes = data.get("possible_causes", [])

        if not anomalies:
            return "未检测到明显异常", ["继续监控数据变化"]

        anomaly = anomalies[0]
        interpretation = (
            f"根据{query}的查询结果，检测到以下异常：\n\n"
            f"**异常详情**:\n"
            f"- 指标：{anomaly.get('metric', 'sessions')}\n"
            f"- 日期：{anomaly.get('date', 'N/A')}\n"
            f"- 预期值：{anomaly.get('expected', 0):,}\n"
            f"- 实际值：{anomaly.get('actual', 0):,}\n"
            f"- 偏差：{anomaly.get('deviation', 0)*100:+.1f}%\n"
            f"- 严重程度：{anomaly.get('severity', 'medium')}\n\n"
            f"**可能原因**:\n"
        )

        suggestions = []
        for i, cause in enumerate(causes[:3], 1):
            interpretation += f"{i}. {cause.get('description')} (影响度：{cause.get('impact', 0)*100:.0f}%)\n"
            suggestions.append(f"针对{cause.get('factor', '该因素')}进行详细排查")

        return interpretation, suggestions

    def _interpret_recommendations(self, data: Dict, query: str) -> Tuple[str, List[str]]:
        """解释推荐数据"""
        recommendations = data.get("recommendations", [])

        if not recommendations:
            return "暂无推荐建议", []

        interpretation = (
            f"根据{query}的查询结果，为您生成以下优化建议：\n\n"
        )

        suggestions = []
        for i, rec in enumerate(recommendations, 1):
            interpretation += (
                f"**{i}. {rec.get('title')}** (优先级：{rec.get('priority', 'medium')})\n"
                f"   - {rec.get('description')}\n"
                f"   - 预期影响：{rec.get('expected_impact', 0)*100:.0f}% 提升\n"
                f"   - 实施难度：{rec.get('effort', 'medium')}\n\n"
            )
            suggestions.append(rec.get("title", ""))

        return interpretation, suggestions

    def _interpret_general(self, data: Dict, query: str) -> Tuple[str, List[str]]:
        """通用解释"""
        return (
            f"根据您的查询「{query}」，以下是数据分析结果：\n\n"
            f"数据已为您整理完成，如需更详细的分析，"
            f"可以尝试更具体的查询，如「上周流量趋势如何」或「哪个页面流量最高」。"
        ), ["尝试使用更具体的查询条件"]


class QueryAssistantService:
    """
    AI 查询助手服务

    整合解析、执行、解释能力，提供完整的自然语言查询服务
    """

    def __init__(self, db_path: str = "ai_traffic_booster.db"):
        self._repository = QueryAssistantRepository(db_path)
        self._parser = NaturalLanguageParser()
        self._executor = QueryExecutor(mock_mode=True)
        self._interpreter = ResultInterpreter()

    def ask(self, query_text: str, user_id: Optional[str] = None,
            session_id: Optional[str] = None) -> QueryResult:
        """
        自然语言查询入口

        Args:
            query_text: 自然语言查询
            user_id: 用户 ID（可选）
            session_id: 会话 ID（可选）

        Returns:
            查询结果
        """
        import uuid

        # 生成或使用现有会话 ID
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:16]}"

        # 创建查询历史记录
        query = QueryHistory.create(
            query_text=query_text,
            session_id=session_id,
            user_id=user_id
        )

        start_time = time.time()

        try:
            # 1. 解析自然语言
            parsed = self._parser.parse(query_text)
            query.query_intent = parsed.intent
            query.query_entities = parsed.entities
            query.status = QueryStatus.EXECUTING

            # 2. 执行查询
            data = self._executor.execute(parsed.entities, parsed.intent)

            # 3. 解释结果
            interpretation, suggestions = self._interpreter.interpret(
                data, parsed.intent, query_text
            )

            # 更新查询记录
            execution_time = int((time.time() - start_time) * 1000)
            query.result_summary = data
            query.ai_interpretation = interpretation
            query.execution_time_ms = execution_time
            query.status = QueryStatus.COMPLETED

            # 保存到历史
            self._repository.save_query(query)

            return QueryResult(
                query=query,
                data=data,
                interpretation=interpretation,
                suggestions=suggestions
            )

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            query.status = QueryStatus.FAILED
            query.error_message = str(e)
            self._repository.save_query(query)
            raise

    def get_history(self, session_id: str, limit: int = 50) -> List[QueryHistory]:
        """获取查询历史"""
        return self._repository.get_queries_by_session(session_id, limit)

    def get_user_history(self, user_id: str, limit: int = 100) -> List[QueryHistory]:
        """获取用户查询历史"""
        return self._repository.get_queries_by_user(user_id, limit)

    def add_favorite(self, query_id: str, query_text: str, user_id: str,
                    custom_name: Optional[str] = None) -> QueryFavorite:
        """添加收藏"""
        favorite = QueryFavorite.create(
            query_text=query_text,
            user_id=user_id,
            query_id=query_id,
            custom_name=custom_name
        )
        self._repository.save_favorite(favorite)
        return favorite

    def get_favorites(self, user_id: str) -> List[QueryFavorite]:
        """获取用户收藏"""
        return self._repository.get_favorites_by_user(user_id)

    def remove_favorite(self, favorite_id: str, user_id: str) -> bool:
        """移除收藏"""
        return self._repository.delete_favorite(favorite_id, user_id)

    def get_templates(self, category: Optional[str] = None) -> List[QueryTemplate]:
        """获取查询模板"""
        return self._repository.get_templates(category)

    def get_suggested_queries(self, context: Optional[Dict] = None) -> List[Dict]:
        """获取推荐查询"""
        # 基于上下文推荐查询
        templates = self._repository.get_templates()

        # 简单推荐：按使用次数排序
        suggested = []
        for template in templates[:5]:
            suggested.append({
                "template_id": template.template_id,
                "text": template.template_text,
                "category": template.category,
                "usage_count": template.usage_count
            })

        return suggested

    def save_report(self, report_title: str, report_type: str,
                   report_content: Dict, user_id: str,
                   query_ids: Optional[List[str]] = None) -> SavedReport:
        """保存报告"""
        report = SavedReport.create(
            report_title=report_title,
            report_type=report_type,
            report_content=report_content,
            user_id=user_id
        )
        if query_ids:
            report.query_ids = query_ids
        self._repository.save_report(report)
        return report

    def get_user_reports(self, user_id: str) -> List[SavedReport]:
        """获取用户报告"""
        return self._repository.get_reports_by_user(user_id)

    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        return self._repository.get_query_stats(user_id)


# 全局服务实例
query_assistant_service = QueryAssistantService()
