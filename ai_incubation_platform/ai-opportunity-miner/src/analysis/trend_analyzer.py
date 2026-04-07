"""
趋势分析器
整合多源数据进行市场趋势分析和预测
"""
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging
from collections import defaultdict
import numpy as np
from nlp.text_analyzer import text_analyzer
from utils.llm_client import llm_client
from models.opportunity import MarketTrend

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self):
        self.text_analyzer = text_analyzer
        self.llm_client = llm_client

    def analyze_time_series(self, data_points: List[Dict]) -> Dict:
        """分析时间序列数据"""
        if not data_points:
            return {}

        # 按时间排序
        sorted_points = sorted(data_points, key=lambda x: x["month"])
        values = [p["value"] for p in sorted_points]

        # 计算增长率
        growth_rates = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                growth_rate = (values[i] - values[i-1]) / values[i-1]
                growth_rates.append(growth_rate)

        avg_growth_rate = np.mean(growth_rates) if growth_rates else 0
        volatility = np.std(growth_rates) if growth_rates else 0

        # 趋势预测（简单线性回归）
        x = np.arange(len(values))
        slope, intercept = np.polyfit(x, values, 1)
        next_month_value = slope * len(values) + intercept

        return {
            "avg_growth_rate": avg_growth_rate,
            "volatility": volatility,
            "trend_direction": "up" if slope > 0 else "down" if slope < 0 else "stable",
            "slope": slope,
            "next_month_forecast": next_month_value,
            "data_points": sorted_points
        }

    def analyze_sentiment_trend(self, articles: List[Dict]) -> Dict:
        """分析情感趋势"""
        if not articles:
            return {}

        # 按日期分组
        date_groups = defaultdict(list)
        for article in articles:
            pub_date = article["published_at"].strftime("%Y-%m")
            signals = self.text_analyzer.extract_opportunity_signals(article["content"])
            sentiment_score = len(signals["positive"]) - len(signals["negative"])
            date_groups[pub_date].append(sentiment_score)

        # 计算每月平均情感
        monthly_sentiment = []
        for date in sorted(date_groups.keys()):
            scores = date_groups[date]
            avg_score = np.mean(scores)
            monthly_sentiment.append({
                "month": date,
                "sentiment_score": avg_score,
                "article_count": len(scores)
            })

        return {
            "monthly_sentiment": monthly_sentiment,
            "overall_sentiment": np.mean([s["sentiment_score"] for s in monthly_sentiment]) if monthly_sentiment else 0
        }

    def analyze_keyword_trend(self, articles: List[Dict], window_size: int = 3) -> Dict:
        """分析关键词趋势"""
        if not articles:
            return {}

        # 按日期分组
        date_groups = defaultdict(list)
        for article in articles:
            pub_date = article["published_at"].strftime("%Y-%m")
            keywords = self.text_analyzer.extract_keywords(article["content"], top_n=20)
            date_groups[pub_date].extend([kw for kw, count in keywords])

        # 计算关键词频率趋势
        all_keywords = set()
        for keywords in date_groups.values():
            all_keywords.update(keywords)

        keyword_trends = {}
        for keyword in all_keywords:
            trend = []
            for date in sorted(date_groups.keys()):
                count = date_groups[date].count(keyword)
                total = len(date_groups[date])
                frequency = count / total if total > 0 else 0
                trend.append({
                    "month": date,
                    "frequency": frequency,
                    "count": count
                })
            keyword_trends[keyword] = trend

        # 计算增长率，找出增长最快的关键词
        growing_keywords = []
        for keyword, trend in keyword_trends.items():
            if len(trend) >= window_size:
                recent = trend[-window_size:]
                old_freq = np.mean([t["frequency"] for t in recent[:window_size//2]])
                new_freq = np.mean([t["frequency"] for t in recent[window_size//2:]])
                if old_freq > 0:
                    growth_rate = (new_freq - old_freq) / old_freq
                    if growth_rate > 0.2:  # 增长超过20%
                        growing_keywords.append({
                            "keyword": keyword,
                            "growth_rate": growth_rate,
                            "trend": trend
                        })

        growing_keywords.sort(key=lambda x: x["growth_rate"], reverse=True)

        return {
            "keyword_trends": keyword_trends,
            "growing_keywords": growing_keywords[:10],  # 前10个增长最快的关键词
            "hot_keywords": sorted(all_keywords, key=lambda k: sum(t["count"] for t in keyword_trends[k]), reverse=True)[:20]
        }

    async def generate_trend_report(self, keyword: str, articles: List[Dict], reports: List[Dict]) -> MarketTrend:
        """生成趋势报告"""
        # 基础分析
        all_text = "\n".join([a["content"] for a in articles] + [r["summary"] for r in reports])
        indicators = self.text_analyzer.extract_indicators(all_text)
        signals = self.text_analyzer.extract_opportunity_signals(all_text)

        # 提取数据点（模拟）
        current_month = datetime.now().strftime("%Y-%m")
        data_points = []
        for i in range(6):
            month = (datetime.now() - timedelta(days=30*i)).strftime("%Y-%m")
            base_value = 100
            growth = indicators.get("growth_rate", {}).get("value", 0.3)
            value = base_value * (1 + growth) ** i
            data_points.append({
                "month": month,
                "value": int(value)
            })
        data_points.reverse()

        # LLM深度分析
        llm_analysis = await self.llm_client.analyze_trend(keyword, articles + reports)

        # 综合计算趋势分数
        base_score = indicators.get("growth_rate", {}).get("value", 0)
        sentiment_score = len(signals["positive"]) / max(len(signals["positive"]) + len(signals["negative"]), 1)
        llm_score = llm_analysis.get("trend_score", 0.5)

        trend_score = (base_score * 0.4 + sentiment_score * 0.2 + llm_score * 0.4)
        trend_score = max(0, min(1, trend_score))

        # 生成相关关键词
        keywords = self.text_analyzer.extract_keywords(all_text, top_n=10)
        related_keywords = [kw for kw, count in keywords if kw != keyword][:5]

        # 创建趋势对象
        trend = MarketTrend(
            keyword=keyword,
            trend_score=trend_score,
            growth_rate=indicators.get("growth_rate", {}).get("value", llm_analysis.get("growth_rate", 0.3)),
            related_keywords=related_keywords,
            data_points=data_points,
            extra=llm_analysis  # 额外的分析结果
        )

        return trend

    async def analyze_competitive_landscape(self, industry: str, articles: List[Dict], reports: List[Dict]) -> Dict:
        """分析竞争格局"""
        all_text = "\n".join([a["content"] for a in articles] + [r["summary"] for r in reports])
        entities = self.text_analyzer.extract_entities(all_text)

        # LLM竞品分析
        llm_analysis = await self.llm_client.analyze_competitors(industry, articles + reports)

        return {
            "industry": industry,
            "companies": entities["companies"],
            "products": entities["products"],
            "llm_analysis": llm_analysis,
            "analysis_time": datetime.now()
        }

trend_analyzer = TrendAnalyzer()
