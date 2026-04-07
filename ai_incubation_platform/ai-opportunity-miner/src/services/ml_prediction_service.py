"""
ML 预测服务

整合趋势预测和事件分类能力
提供 6 个月预测和置信度评分
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

from ml.trend_predictor import trend_predictor, ForecastResult
from ml.event_classifier import event_classifier, ClassifiedEvent, EventType
from services.investment_chain_service import investment_chain_service

logger = logging.getLogger(__name__)


class MLPredictionService:
    """ML 预测服务"""

    def __init__(self):
        self._initialized = False
        self._forecast_cache: Dict[str, ForecastResult] = {}

    def initialize(self):
        """初始化 ML 服务，加载历史数据"""
        if self._initialized:
            return

        logger.info("Initializing ML prediction service...")

        # 从投资数据加载历史数据
        investments = investment_chain_service.get_all_investments()
        trend_predictor.load_from_investment_data(investments)

        self._initialized = True
        logger.info(f"ML service initialized with {len(investments)} investment records")

    def get_industry_forecast(
        self,
        industry: str,
        forecast_months: int = 6
    ) -> Optional[Dict[str, Any]]:
        """
        获取行业投资预测

        Args:
            industry: 行业名称
            forecast_months: 预测月数

        Returns:
            预测结果字典
        """
        if not self._initialized:
            self.initialize()

        cache_key = f"industry:{industry}:{forecast_months}"
        if cache_key in self._forecast_cache:
            logger.info(f"Returning cached forecast for {industry}")
            return self._format_forecast_result(
                self._forecast_cache[cache_key],
                dimension="industry",
                dimension_value=industry
            )

        # 执行预测
        result = trend_predictor.forecast(
            dimension="industry",
            dimension_value=industry,
            forecast_periods=forecast_months,
            model="auto"
        )

        if result:
            self._forecast_cache[cache_key] = result
            return self._format_forecast_result(result, "industry", industry)

        return None

    def get_all_industries_forecast(
        self,
        forecast_months: int = 6
    ) -> List[Dict[str, Any]]:
        """获取所有行业的投资预测"""
        if not self._initialized:
            self.initialize()

        # 获取所有行业
        industries = set()
        for inv in investment_chain_service.get_all_investments():
            if inv.investee_industry:
                industries.add(inv.investee_industry)

        results = []
        for industry in industries:
            forecast = self.get_industry_forecast(industry, forecast_months)
            if forecast:
                results.append(forecast)

        # 按预测增长率排序
        results.sort(key=lambda x: x.get('growth_rate', 0), reverse=True)
        return results

    def get_hot_industries(
        self,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """获取热门行业预测（增长率最高的行业）"""
        forecasts = self.get_all_industries_forecast()
        return forecasts[:top_n]

    def get_trending_investors(self) -> List[Dict[str, Any]]:
        """获取活跃投资人预测"""
        if not self._initialized:
            self.initialize()

        investor_trends = []
        investments = investment_chain_service.get_all_investments()

        # 按投资方分组
        investor_data = defaultdict(list)
        for inv in investments:
            if inv.investment_date:
                investor_data[inv.investor_name].append(inv)

        for investor, invs in investor_data.items():
            if len(invs) >= 2:
                # 计算投资活跃度
                recent = [i for i in invs if i.investment_date and
                          i.investment_date > datetime.now() - timedelta(days=180)]
                older = [i for i in invs if i.investment_date and
                         i.investment_date <= datetime.now() - timedelta(days=180)]

                recent_count = len(recent)
                older_count = len(older)

                # 计算活跃度趋势
                if older_count > 0:
                    growth = (recent_count - older_count) / older_count * 100
                else:
                    growth = 100 if recent_count > 0 else 0

                # 预测未来活跃度
                if recent_count >= 2:
                    predicted_activity = "high" if recent_count >= 3 else "medium"
                else:
                    predicted_activity = "low"

                investor_trends.append({
                    "investor_name": investor,
                    "total_investments": len(invs),
                    "recent_investments": recent_count,
                    "growth_rate": growth,
                    "predicted_activity": predicted_activity,
                    "industries": list(set(i.investee_industry for i in invs if i.investee_industry))
                })

        # 按增长率排序
        investor_trends.sort(key=lambda x: x['growth_rate'], reverse=True)
        return investor_trends

    def classify_news_events(
        self,
        news_items: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        分类新闻事件

        Args:
            news_items: 新闻列表，每项包含 title, content, source 等

        Returns:
            分类结果列表
        """
        results = []
        for news in news_items:
            classified = event_classifier.classify(
                title=news.get('title', ''),
                content=news.get('content', ''),
                source=news.get('source', 'unknown'),
                source_url=news.get('url', ''),
                published_date=news.get('published_date')
            )
            results.append(self._format_classified_event(classified))
        return results

    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪分析"""
        if not self._initialized:
            self.initialize()

        investments = investment_chain_service.get_all_investments()

        # 按月份统计投资活跃度
        monthly_activity = defaultdict(lambda: {"count": 0, "amount": 0})
        for inv in investments:
            if inv.investment_date:
                month_key = inv.investment_date.strftime("%Y-%m")
                monthly_activity[month_key]["count"] += 1
                monthly_activity[month_key]["amount"] += inv.amount or 0

        # 计算情绪
        if len(monthly_activity) >= 2:
            sorted_months = sorted(monthly_activity.keys())
            recent_month = sorted_months[-1]
            previous_month = sorted_months[-2]

            recent_count = monthly_activity[recent_month]["count"]
            previous_count = monthly_activity[previous_month]["count"]

            if recent_count > previous_count * 1.2:
                sentiment = "bullish"
                confidence = min(0.95, 0.5 + (recent_count - previous_count) / previous_count * 0.5)
            elif recent_count < previous_count * 0.8:
                sentiment = "bearish"
                confidence = min(0.95, 0.5 + (previous_count - recent_count) / previous_count * 0.5)
            else:
                sentiment = "neutral"
                confidence = 0.6
        else:
            sentiment = "neutral"
            confidence = 0.5

        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "recent_activity": monthly_activity.get(sorted_months[-1], {}) if monthly_activity else {},
            "trend": "up" if sentiment == "bullish" else "down" if sentiment == "bearish" else "stable"
        }

    def get_investment_opportunity_score(
        self,
        industry: str,
        company_name: str = None
    ) -> Dict[str, Any]:
        """
        计算投资机会分数

        Args:
            industry: 行业名称
            company_name: 公司名称（可选）

        Returns:
            包含投资机会评分的字典
        """
        if not self._initialized:
            self.initialize()

        score = 0.0
        factors = {}

        # 因素 1: 行业增长趋势 (0-30 分)
        forecast = self.get_industry_forecast(industry)
        if forecast:
            growth_rate = forecast.get('growth_rate', 0)
            if growth_rate > 20:
                trend_score = 30
            elif growth_rate > 10:
                trend_score = 20
            elif growth_rate > 0:
                trend_score = 10
            else:
                trend_score = 5
            factors['industry_growth'] = {
                'score': trend_score,
                'growth_rate': growth_rate
            }
            score += trend_score

        # 因素 2: 投资活跃度 (0-25 分)
        trend_data = investment_chain_service.analyze_investment_trend(industry=industry)
        if trend_data.total_investments > 10:
            activity_score = 25
        elif trend_data.total_investments > 5:
            activity_score = 15
        elif trend_data.total_investments > 2:
            activity_score = 10
        else:
            activity_score = 5
        factors['investment_activity'] = {
            'score': activity_score,
            'total_investments': trend_data.total_investments
        }
        score += activity_score

        # 因素 3: 投资者多样性 (0-20 分)
        industry_investments = investment_chain_service.get_investments_by_industry(industry)
        unique_investors = set(inv.investor_name for inv in industry_investments)
        if len(unique_investors) > 5:
            diversity_score = 20
        elif len(unique_investors) > 3:
            diversity_score = 15
        elif len(unique_investors) > 1:
            diversity_score = 10
        else:
            diversity_score = 5
        factors['investor_diversity'] = {
            'score': diversity_score,
            'unique_investors': len(unique_investors)
        }
        score += diversity_score

        # 因素 4: 平均投资规模 (0-15 分)
        if industry_investments:
            avg_amount = sum(inv.amount or 0 for inv in industry_investments) / len(industry_investments)
            if avg_amount > 100000000:  # 1 亿
                scale_score = 15
            elif avg_amount > 50000000:
                scale_score = 10
            elif avg_amount > 10000000:
                scale_score = 5
            else:
                scale_score = 3
        else:
            scale_score = 0
        factors['investment_scale'] = {
            'score': scale_score,
            'avg_amount': avg_amount if industry_investments else 0
        }
        score += scale_score

        # 因素 5: 市场情绪 (0-10 分)
        sentiment = self.get_market_sentiment()
        if sentiment['sentiment'] == 'bullish':
            sentiment_score = 10 * sentiment['confidence']
        elif sentiment['sentiment'] == 'bearish':
            sentiment_score = 3 * (1 - sentiment['confidence'])
        else:
            sentiment_score = 5
        factors['market_sentiment'] = {
            'score': sentiment_score,
            'sentiment': sentiment['sentiment']
        }
        score += sentiment_score

        # 评级
        if score >= 80:
            rating = "A+"
            recommendation = "强烈推荐"
        elif score >= 70:
            rating = "A"
            recommendation = "推荐"
        elif score >= 60:
            rating = "B+"
            recommendation = "谨慎推荐"
        elif score >= 50:
            rating = "B"
            recommendation = "观望"
        else:
            rating = "C"
            recommendation = "不推荐"

        return {
            "industry": industry,
            "company_name": company_name,
            "total_score": round(score, 2),
            "rating": rating,
            "recommendation": recommendation,
            "factors": factors,
            "generated_at": datetime.now().isoformat()
        }

    def _format_forecast_result(
        self,
        result: ForecastResult,
        dimension: str,
        dimension_value: str
    ) -> Dict[str, Any]:
        """格式化预测结果"""
        # 构建预测数据点
        forecast_points = []
        for i, date in enumerate(result.dates):
            forecast_points.append({
                "date": date,
                "prediction": round(result.predictions[i], 2),
                "lower_bound": round(result.lower_bound[i], 2),
                "upper_bound": round(result.upper_bound[i], 2)
            })

        return {
            "dimension": dimension,
            "dimension_value": dimension_value,
            "forecast_periods": len(result.dates),
            "forecast_data": forecast_points,
            "trend_direction": result.trend_direction,
            "growth_rate": round(result.growth_rate, 2),
            "confidence_score": round(result.confidence_score, 3),
            "model_type": result.model_type,
            "model_metrics": result.model_metrics,
            "generated_at": datetime.now().isoformat()
        }

    def _format_classified_event(
        self,
        event: ClassifiedEvent
    ) -> Dict[str, Any]:
        """格式化分类事件"""
        return {
            "id": event.id,
            "title": event.title,
            "content": event.content[:200] + "..." if len(event.content) > 200 else event.content,
            "event_type": event.event_type.value,
            "confidence": round(event.confidence, 3),
            "source": event.source,
            "source_url": event.source_url,
            "published_date": event.published_date.isoformat() if event.published_date else None,
            "entities": event.entities,
            "keywords": event.keywords,
            "sentiment": event.sentiment
        }


# 全局 ML 服务实例
ml_prediction_service = MLPredictionService()
