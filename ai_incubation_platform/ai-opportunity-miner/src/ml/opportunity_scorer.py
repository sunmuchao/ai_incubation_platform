"""
增强的商机评分模型

提供可解释的 AI 驱动商机评分
支持多因子分析和置信度评估
"""
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class ScoreFactor(str, Enum):
    """评分因子类型"""
    INDUSTRY_GROWTH = "industry_growth"
    INVESTMENT_ACTIVITY = "investment_activity"
    INVESTOR_DIVERSITY = "investor_diversity"
    INVESTMENT_SCALE = "investment_scale"
    MARKET_SENTIMENT = "market_sentiment"
    COMPETITIVE_DENSITY = "competitive_density"
    TECHNOLOGY_MATURITY = "technology_maturity"
    REGULATORY_RISK = "regulatory_risk"
    TEAM_STRENGTH = "team_strength"
    MARKET_SIZE = "market_size"


class ConfidenceLevel(str, Enum):
    """置信度等级"""
    HIGH = "high"      # 置信度 >= 0.8
    MEDIUM = "medium"  # 0.5 <= 置信度 < 0.8
    LOW = "low"        # 置信度 < 0.5


@dataclass
class FactorAnalysis:
    """因子分析结果"""
    factor: ScoreFactor
    score: float  # 0-100
    weight: float  # 权重 0-1
    contribution: float  # 对总分的贡献
    trend: str  # "up", "down", "stable"
    description: str
    data_points: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0  # 该因子评估的置信度


@dataclass
class OpportunityScore:
    """商机评分结果"""
    # 基本信息
    opportunity_id: str
    industry: str
    company_name: Optional[str]

    # 评分结果
    total_score: float  # 0-100
    rating: str  # A+, A, B+, B, C
    recommendation: str  # 强烈推荐，推荐，谨慎推荐，观望，不推荐

    # 置信度
    confidence_score: float  # 0-1
    confidence_level: ConfidenceLevel
    confidence_factors: List[str] = field(default_factory=list)

    # 因子分析
    factor_analyses: List[FactorAnalysis] = field(default_factory=list)
    top_positive_factors: List[str] = field(default_factory=list)
    top_negative_factors: List[str] = field(default_factory=list)

    # 可解释性
    explanation: str = ""  # 评分原因解释
    key_insights: List[str] = field(default_factory=list)

    # 预测信息
    predicted_growth_rate: float = 0.0
    predicted_time_window: str = "6 months"

    # 元信息
    generated_at: datetime = field(default_factory=datetime.now)
    model_version: str = "v2.0"


class OpportunityScorer:
    """
    商机评分器

    使用多因子加权评分模型
    提供可解释的评分结果
    """

    # 因子权重配置 (总和为 1.0)
    FACTOR_WEIGHTS = {
        ScoreFactor.INDUSTRY_GROWTH: 0.20,
        ScoreFactor.INVESTMENT_ACTIVITY: 0.15,
        ScoreFactor.INVESTOR_DIVERSITY: 0.12,
        ScoreFactor.INVESTMENT_SCALE: 0.10,
        ScoreFactor.MARKET_SENTIMENT: 0.10,
        ScoreFactor.COMPETITIVE_DENSITY: 0.08,
        ScoreFactor.TECHNOLOGY_MATURITY: 0.08,
        ScoreFactor.REGULATORY_RISK: 0.07,
        ScoreFactor.MARKET_SIZE: 0.06,
        ScoreFactor.TEAM_STRENGTH: 0.04,
    }

    def __init__(self):
        self._historical_scores: Dict[str, List[OpportunityScore]] = {}
        self._factor_cache: Dict[str, FactorAnalysis] = {}

    def score(
        self,
        industry: str,
        company_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> OpportunityScore:
        """
        计算商机评分

        Args:
            industry: 行业名称
            company_name: 公司名称（可选）
            context: 上下文信息（投资数据、市场数据等）

        Returns:
            OpportunityScore 评分结果
        """
        import uuid

        opportunity_id = str(uuid.uuid4())

        # 1. 收集各因子数据
        factor_analyses = self._analyze_all_factors(industry, context)

        # 2. 计算加权总分
        total_score = sum(
            fa.score * fa.weight for fa in factor_analyses
        )
        total_score = min(100, max(0, total_score))  # 限制在 0-100

        # 3. 计算置信度
        confidence_score, confidence_factors = self._calculate_confidence(factor_analyses)
        confidence_level = self._get_confidence_level(confidence_score)

        # 4. 确定评级和推荐
        rating, recommendation = self._get_rating_and_recommendation(total_score)

        # 5. 生成解释
        explanation, key_insights = self._generate_explanation(
            total_score, factor_analyses, confidence_score
        )

        # 6. 识别正负面因素
        top_positive = self._get_top_factors(factor_analyses, positive=True, top_n=3)
        top_negative = self._get_top_factors(factor_analyses, positive=False, top_n=3)

        # 7. 预测增长率（基于行业增长因子）
        growth_factor = next(
            (fa for fa in factor_analyses if fa.factor == ScoreFactor.INDUSTRY_GROWTH),
            None
        )
        predicted_growth_rate = growth_factor.contribution if growth_factor else 0.0

        score_result = OpportunityScore(
            opportunity_id=opportunity_id,
            industry=industry,
            company_name=company_name,
            total_score=round(total_score, 2),
            rating=rating,
            recommendation=recommendation,
            confidence_score=round(confidence_score, 3),
            confidence_level=confidence_level,
            confidence_factors=confidence_factors,
            factor_analyses=factor_analyses,
            top_positive_factors=top_positive,
            top_negative_factors=top_negative,
            explanation=explanation,
            key_insights=key_insights,
            predicted_growth_rate=round(predicted_growth_rate, 2),
        )

        return score_result

    def _analyze_all_factors(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> List[FactorAnalysis]:
        """分析所有评分因子"""
        analyses = []

        # 1. 行业增长分析
        analyses.append(self._analyze_industry_growth(industry, context))

        # 2. 投资活跃度分析
        analyses.append(self._analyze_investment_activity(industry, context))

        # 3. 投资者多样性分析
        analyses.append(self._analyze_investor_diversity(industry, context))

        # 4. 投资规模分析
        analyses.append(self._analyze_investment_scale(industry, context))

        # 5. 市场情绪分析
        analyses.append(self._analyze_market_sentiment(industry, context))

        # 6. 竞争密度分析
        analyses.append(self._analyze_competitive_density(industry, context))

        # 7. 技术成熟度分析
        analyses.append(self._analyze_technology_maturity(industry, context))

        # 8. 监管风险分析
        analyses.append(self._analyze_regulatory_risk(industry, context))

        # 9. 市场规模分析
        analyses.append(self._analyze_market_size(industry, context))

        # 10. 团队实力分析（如果有公司名）
        if context and context.get('company_data'):
            analyses.append(self._analyze_team_strength(industry, context))

        return analyses

    def _analyze_industry_growth(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析行业增长因子"""
        # 从上下文获取增长数据
        growth_rate = 0.0
        trend = "stable"
        data_points = []
        confidence = 0.7

        if context and context.get('forecast'):
            forecast = context['forecast']
            growth_rate = forecast.get('growth_rate', 0)
            if forecast.get('trend_direction') == 'up':
                trend = "up"
            elif forecast.get('trend_direction') == 'down':
                trend = "down"
            data_points = forecast.get('forecast_data', [])
            confidence = forecast.get('confidence_score', 0.7)

        # 计算分数 (增长率越高分数越高)
        if growth_rate > 30:
            score = 95
        elif growth_rate > 20:
            score = 85
        elif growth_rate > 10:
            score = 70
        elif growth_rate > 0:
            score = 55
        else:
            score = 30

        description = f"行业预计增长率为{round(growth_rate, 1)}%，趋势{self._trend_to_cn(trend)}"

        return FactorAnalysis(
            factor=ScoreFactor.INDUSTRY_GROWTH,
            score=score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.INDUSTRY_GROWTH],
            contribution=score * self.FACTOR_WEIGHTS[ScoreFactor.INDUSTRY_GROWTH],
            trend=trend,
            description=description,
            data_points=data_points,
            confidence=confidence
        )

    def _analyze_investment_activity(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析投资活跃度因子"""
        total_investments = 0
        recent_investments = 0
        trend = "stable"
        confidence = 0.8

        if context and context.get('investment_data'):
            investments = context['investment_data']
            total_investments = len(investments)
            recent_investments = len([
                i for i in investments
                if i.get('date') and
                datetime.fromisoformat(i['date']) > datetime.now() - timedelta(days=180)
            ])

            # 判断趋势
            if recent_investments > total_investments * 0.6:
                trend = "up"
            elif recent_investments < total_investments * 0.3:
                trend = "down"

        # 计算分数
        if total_investments > 20:
            score = 90
        elif total_investments > 10:
            score = 75
        elif total_investments > 5:
            score = 60
        elif total_investments > 2:
            score = 45
        else:
            score = 30

        description = f"行业共有{total_investments}起投资事件，近期{recent_investments}起，活跃度{self._trend_to_cn(trend)}"

        return FactorAnalysis(
            factor=ScoreFactor.INVESTMENT_ACTIVITY,
            score=score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.INVESTMENT_ACTIVITY],
            contribution=score * self.FACTOR_WEIGHTS[ScoreFactor.INVESTMENT_ACTIVITY],
            trend=trend,
            description=description,
            confidence=confidence
        )

    def _analyze_investor_diversity(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析投资者多样性因子"""
        unique_investors = set()
        confidence = 0.85

        if context and context.get('investment_data'):
            for inv in context['investment_data']:
                if inv.get('investor_name'):
                    unique_investors.add(inv['investor_name'])

        num_investors = len(unique_investors)

        # 计算分数
        if num_investors > 10:
            score = 90
        elif num_investors > 5:
            score = 75
        elif num_investors > 3:
            score = 60
        elif num_investors > 1:
            score = 45
        else:
            score = 30

        trend = "up" if num_investors > 5 else "stable" if num_investors > 2 else "down"
        description = f"行业有{num_investors}家不同投资机构参与，投资者多样性{self._trend_to_cn(trend)}"

        return FactorAnalysis(
            factor=ScoreFactor.INVESTOR_DIVERSITY,
            score=score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.INVESTOR_DIVERSITY],
            contribution=score * self.FACTOR_WEIGHTS[ScoreFactor.INVESTOR_DIVERSITY],
            trend=trend,
            description=description,
            confidence=confidence
        )

    def _analyze_investment_scale(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析投资规模因子"""
        avg_amount = 0
        total_amount = 0
        confidence = 0.75

        if context and context.get('investment_data'):
            amounts = [
                inv.get('amount', 0) for inv in context['investment_data']
                if inv.get('amount')
            ]
            if amounts:
                avg_amount = sum(amounts) / len(amounts)
                total_amount = sum(amounts)

        # 计算分数（金额单位假设为万元）
        if avg_amount > 100000:  # 10 亿+
            score = 90
        elif avg_amount > 50000:  # 5 亿+
            score = 75
        elif avg_amount > 10000:  # 1 亿+
            score = 60
        elif avg_amount > 5000:  # 5000 万+
            score = 45
        else:
            score = 30

        trend = "up" if avg_amount > 10000 else "stable"
        description = f"行业平均投资金额{round(avg_amount/10000, 1)}亿元，总规模{round(total_amount/10000, 1)}亿元"

        return FactorAnalysis(
            factor=ScoreFactor.INVESTMENT_SCALE,
            score=score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.INVESTMENT_SCALE],
            contribution=score * self.FACTOR_WEIGHTS[ScoreFactor.INVESTMENT_SCALE],
            trend=trend,
            description=description,
            confidence=confidence
        )

    def _analyze_market_sentiment(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析市场情绪因子"""
        sentiment = "neutral"
        sentiment_score = 0.5
        confidence = 0.6

        if context and context.get('market_sentiment'):
            sentiment_data = context['market_sentiment']
            sentiment = sentiment_data.get('sentiment', 'neutral')
            sentiment_score = sentiment_data.get('confidence', 0.5)
            confidence = sentiment_score

        # 计算分数
        if sentiment == "bullish":
            score = 70 + sentiment_score * 30
        elif sentiment == "bearish":
            score = 30 + (1 - sentiment_score) * 20
        else:
            score = 50

        trend = "up" if sentiment == "bullish" else "down" if sentiment == "bearish" else "stable"
        description = f"市场情绪{self._sentiment_to_cn(sentiment)}，置信度{round(sentiment_score*100)}%"

        return FactorAnalysis(
            factor=ScoreFactor.MARKET_SENTIMENT,
            score=score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.MARKET_SENTIMENT],
            contribution=score * self.FACTOR_WEIGHTS[ScoreFactor.MARKET_SENTIMENT],
            trend=trend,
            description=description,
            confidence=confidence
        )

    def _analyze_competitive_density(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析竞争密度因子"""
        # 竞争适度是好事，过度竞争是坏事
        num_companies = 0
        confidence = 0.7

        if context and context.get('company_count'):
            num_companies = context['company_count']

        # 倒 U 型评分曲线 - 适度竞争最好
        if 10 <= num_companies <= 50:
            score = 85  # 适度竞争
        elif 5 <= num_companies < 10 or 50 < num_companies <= 100:
            score = 65  # 竞争偏少或偏多
        elif num_companies < 5:
            score = 50  # 市场可能太小
        else:
            score = 35  # 竞争过度

        trend = "stable"
        description = f"行业约有{num_companies}家竞争公司，竞争密度{'适中' if 10 <= num_companies <= 50 else '偏高' if num_companies > 50 else '偏低'}"

        return FactorAnalysis(
            factor=ScoreFactor.COMPETITIVE_DENSITY,
            score=score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.COMPETITIVE_DENSITY],
            contribution=score * self.FACTOR_WEIGHTS[ScoreFactor.COMPETITIVE_DENSITY],
            trend=trend,
            description=description,
            confidence=confidence
        )

    def _analyze_technology_maturity(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析技术成熟度因子"""
        maturity_level = "growth"  # emergence, growth, maturity, decline
        confidence = 0.65

        if context and context.get('technology_maturity'):
            maturity_level = context['technology_maturity']

        # 成长期最好
        maturity_scores = {
            "emergence": 60,   # 早期，风险高
            "growth": 85,      # 成长期，最佳
            "maturity": 70,    # 成熟期，稳定
            "decline": 40      # 衰退期，避免
        }

        score = maturity_scores.get(maturity_level, 60)
        trend = "up" if maturity_level == "growth" else "down" if maturity_level == "decline" else "stable"
        description = f"行业技术处于{self._maturity_to_cn(maturity_level)}阶段"

        return FactorAnalysis(
            factor=ScoreFactor.TECHNOLOGY_MATURITY,
            score=score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.TECHNOLOGY_MATURITY],
            contribution=score * self.FACTOR_WEIGHTS[ScoreFactor.TECHNOLOGY_MATURITY],
            trend=trend,
            description=description,
            confidence=confidence
        )

    def _analyze_regulatory_risk(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析监管风险因子"""
        risk_level = "medium"  # low, medium, high
        confidence = 0.6

        # 高风险行业标记
        high_risk_industries = ['金融科技', '区块链', '加密货币', '医疗', '教育', '游戏']
        low_risk_industries = ['企业服务', '制造业', '消费升级', '农业']

        if industry in high_risk_industries:
            risk_level = "high"
        elif industry in low_risk_industries:
            risk_level = "low"

        if context and context.get('regulatory_risk'):
            risk_level = context['regulatory_risk']

        # 风险越低分数越高
        risk_scores = {
            "low": 90,
            "medium": 60,
            "high": 30
        }

        score = risk_scores.get(risk_level, 60)
        trend = "stable"
        description = f"行业监管风险{self._risk_to_cn(risk_level)}"

        return FactorAnalysis(
            factor=ScoreFactor.REGULATORY_RISK,
            score=score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.REGULATORY_RISK],
            contribution=score * self.FACTOR_WEIGHTS[ScoreFactor.REGULATORY_RISK],
            trend=trend,
            description=description,
            confidence=confidence
        )

    def _analyze_market_size(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析市场规模因子"""
        market_size = 0  # 单位：亿元
        confidence = 0.7

        if context and context.get('market_size'):
            market_size = context['market_size']

        # 计算分数
        if market_size > 10000:  # 万亿级
            score = 95
        elif market_size > 1000:  # 千亿级
            score = 80
        elif market_size > 100:  # 百亿级
            score = 65
        elif market_size > 10:  # 十亿级
            score = 50
        else:
            score = 35

        trend = "up" if market_size > 100 else "stable"
        description = f"行业市场规模约{round(market_size, 1)}亿元"

        return FactorAnalysis(
            factor=ScoreFactor.MARKET_SIZE,
            score=score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.MARKET_SIZE],
            contribution=score * self.FACTOR_WEIGHTS[ScoreFactor.MARKET_SIZE],
            trend=trend,
            description=description,
            confidence=confidence
        )

    def _analyze_team_strength(
        self,
        industry: str,
        context: Optional[Dict[str, Any]]
    ) -> FactorAnalysis:
        """分析团队实力因子"""
        team_score = 50  # 默认中等
        confidence = 0.5

        if context and context.get('company_data'):
            company_data = context['company_data']

            # 评估团队因素
            if company_data.get('founder_background') == 'top':
                team_score += 20
            if company_data.get('team_size', 0) > 50:
                team_score += 15
            if company_data.get('previous_funding'):
                team_score += 15

            team_score = min(100, team_score)

        trend = "up" if team_score > 60 else "stable"
        description = f"团队实力评估{'强' if team_score > 70 else '中等' if team_score > 50 else '待观察'}"

        return FactorAnalysis(
            factor=ScoreFactor.TEAM_STRENGTH,
            score=team_score,
            weight=self.FACTOR_WEIGHTS[ScoreFactor.TEAM_STRENGTH],
            contribution=team_score * self.FACTOR_WEIGHTS[ScoreFactor.TEAM_STRENGTH],
            trend=trend,
            description=description,
            confidence=confidence
        )

    def _calculate_confidence(
        self,
        factor_analyses: List[FactorAnalysis]
    ) -> Tuple[float, List[str]]:
        """计算总体置信度"""
        if not factor_analyses:
            return 0.5, ["无分析数据"]

        # 基于因子数量和置信度计算总体置信度
        num_factors = len(factor_analyses)
        avg_confidence = sum(fa.confidence for fa in factor_analyses) / num_factors

        # 因子数量越多，置信度越高（但有上限）
        quantity_bonus = min(0.2, num_factors * 0.02)

        overall_confidence = min(0.95, avg_confidence + quantity_bonus)

        # 生成置信度影响因素
        confidence_factors = []
        if num_factors >= 8:
            confidence_factors.append(f"分析了{num_factors}个维度")
        if avg_confidence > 0.8:
            confidence_factors.append("数据质量高")
        elif avg_confidence < 0.6:
            confidence_factors.append("部分数据缺失")

        # 检查关键因子是否有数据
        critical_factors = [
            ScoreFactor.INDUSTRY_GROWTH,
            ScoreFactor.INVESTMENT_ACTIVITY,
            ScoreFactor.MARKET_SENTIMENT
        ]
        missing_critical = [
            f.factor.value for f in factor_analyses
            if f.factor in critical_factors and f.confidence < 0.5
        ]
        if missing_critical:
            confidence_factors.append(f"关键因子数据不足：{', '.join(missing_critical)}")
            overall_confidence -= 0.1

        return overall_confidence, confidence_factors

    def _get_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """获取置信度等级"""
        if confidence_score >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _get_rating_and_recommendation(
        self,
        total_score: float
    ) -> Tuple[str, str]:
        """获取评级和推荐"""
        if total_score >= 85:
            return "A+", "强烈推荐"
        elif total_score >= 75:
            return "A", "推荐"
        elif total_score >= 65:
            return "B+", "谨慎推荐"
        elif total_score >= 50:
            return "B", "观望"
        else:
            return "C", "不推荐"

    def _generate_explanation(
        self,
        total_score: float,
        factor_analyses: List[FactorAnalysis],
        confidence_score: float
    ) -> Tuple[str, List[str]]:
        """生成评分解释"""
        # 排序因子按贡献度
        sorted_factors = sorted(
            factor_analyses,
            key=lambda f: f.contribution,
            reverse=True
        )

        # 获取 top 3 正面和负面因素
        top_positive = sorted_factors[:3]
        top_negative = sorted_factors[-3:] if len(sorted_factors) >= 3 else []

        # 生成关键洞察
        key_insights = []

        # 基于最高分因子的洞察
        if top_positive:
            best = top_positive[0]
            key_insights.append(f"主要优势：{best.description}")

        # 基于最低分因子的洞察
        if top_negative:
            worst = min(top_negative, key=lambda f: f.score)
            key_insights.append(f"主要风险：{worst.description}")

        # 基于置信度的洞察
        if confidence_score >= 0.8:
            key_insights.append("评估置信度高，数据充分")
        elif confidence_score < 0.5:
            key_insights.append("评估置信度低，建议补充数据")

        # 基于总分的总体评价
        if total_score >= 75:
            overall = "这是一个高质量的投资机会，多个维度表现优异"
        elif total_score >= 60:
            overall = "这是一个中等质量的机会，存在一定风险和不确定性"
        else:
            overall = "这个机会风险较高，建议谨慎对待"

        explanation = f"{overall}。"

        return explanation, key_insights

    def _get_top_factors(
        self,
        factor_analyses: List[FactorAnalysis],
        positive: bool,
        top_n: int
    ) -> List[str]:
        """获取 top 因素"""
        if positive:
            sorted_factors = sorted(
                factor_analyses,
                key=lambda f: f.score,
                reverse=True
            )
        else:
            sorted_factors = sorted(
                factor_analyses,
                key=lambda f: f.score
            )

        return [f.description for f in sorted_factors[:top_n]]

    def _trend_to_cn(self, trend: str) -> str:
        """趋势英文转中文"""
        mapping = {
            "up": "上升",
            "down": "下降",
            "stable": "稳定"
        }
        return mapping.get(trend, "未知")

    def _sentiment_to_cn(self, sentiment: str) -> str:
        """情绪英文转中文"""
        mapping = {
            "bullish": "乐观",
            "bearish": "悲观",
            "neutral": "中性"
        }
        return mapping.get(sentiment, "未知")

    def _maturity_to_cn(self, maturity: str) -> str:
        """成熟度英文转中文"""
        mapping = {
            "emergence": "萌芽期",
            "growth": "成长期",
            "maturity": "成熟期",
            "decline": "衰退期"
        }
        return mapping.get(maturity, "未知")

    def _risk_to_cn(self, risk: str) -> str:
        """风险英文转中文"""
        mapping = {
            "low": "低",
            "medium": "中等",
            "high": "高"
        }
        return mapping.get(risk, "未知")


# 全局评分器实例
opportunity_scorer = OpportunityScorer()
