"""
P6 - 商机质量评分模型

实现多维度商机质量评分系统，包括：
1. 置信度评分 - 基于数据源可信度和 AI 分析置信度
2. 风险评分 - 多维度风险评估
3. 价值评分 - 潜在商业价值评估
4. 紧迫性评分 - 时机紧迫程度评估
5. ML 评分模型 - 机器学习综合评分
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScoreDimension(str, Enum):
    """评分维度"""
    CONFIDENCE = "confidence"  # 置信度
    RISK = "risk"  # 风险
    VALUE = "value"  # 价值
    URGENCY = "urgency"  # 紧迫性
    FEASIBILITY = "feasibility"  # 可行性
    STRATEGIC_FIT = "strategic_fit"  # 战略匹配度


class DataSourceReliability(Enum):
    """数据源可靠性等级"""
    GOVERNMENT = 0.95  # 政府数据（最高可信）
    ENTERPRISE_API = 0.90  # 企业数据 API（天眼查等）
    PATENT_OFFICE = 0.92  # 专利局数据
    FINANCING_PLATFORM = 0.85  # 融资平台（IT 桔子等）
    NEWS_MEDIA = 0.75  # 新闻媒体
    INDUSTRY_REPORT = 0.80  # 行业报告
    SOCIAL_MEDIA = 0.60  # 社交媒体
    INTERNAL_DATA = 0.85  # 内部数据
    AI_ANALYSIS = 0.70  # AI 分析结果


class OpportunityScore(BaseModel):
    """商机综合评分模型"""
    opportunity_id: str
    overall_score: float = Field(ge=0.0, le=100.0)  # 综合评分 0-100
    grade: str  # 等级：S/A/B/C/D

    # 各维度评分
    confidence_score: float = Field(ge=0.0, le=100.0)  # 置信度
    risk_score: float = Field(ge=0.0, le=100.0)  # 风险分（越低越好）
    value_score: float = Field(ge=0.0, le=100.0)  # 价值分
    urgency_score: float = Field(ge=0.0, le=100.0)  # 紧迫性
    feasibility_score: float = Field(ge=0.0, le=100.0)  # 可行性
    strategic_fit_score: float = Field(ge=0.0, le=100.0)  # 战略匹配度

    # 评分详情
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    scoring_factors: List[str] = Field(default_factory=list)  # 影响评分的关键因素
    recommendations: List[str] = Field(default_factory=list)  # 基于评分的建议

    created_at: datetime = Field(default_factory=datetime.now)


class OpportunityScoringModel:
    """商机评分模型"""

    def __init__(self):
        # 评分权重配置
        self.weights = {
            ScoreDimension.CONFIDENCE: 0.20,
            ScoreDimension.RISK: 0.20,
            ScoreDimension.VALUE: 0.25,
            ScoreDimension.URGENCY: 0.15,
            ScoreDimension.FEASIBILITY: 0.10,
            ScoreDimension.STRATEGIC_FIT: 0.10,
        }

        # 风险因子权重
        self.risk_weights = {
            "regulatory": 0.25,  # 监管风险
            "competitive": 0.20,  # 竞争风险
            "technological": 0.20,  # 技术风险
            "market": 0.20,  # 市场风险
            "financial": 0.15,  # 财务风险
        }

        # 价值评估阈值
        self.value_thresholds = {
            "high": 10000000,  # 1000 万以上
            "medium": 1000000,  # 100 万以上
            "low": 100000,  # 10 万以上
        }

        # 紧迫性时间阈值（天）
        self.urgency_thresholds = {
            "critical": 7,  # 7 天内
            "high": 30,  # 30 天内
            "medium": 90,  # 90 天内
            "low": 180,  # 180 天内
        }

    def calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """
        计算综合评分
        使用加权平均法
        """
        overall = 0.0
        for dimension, weight in self.weights.items():
            if dimension.value in scores:
                overall += scores[dimension.value] * weight

        return min(100.0, max(0.0, overall))

    def calculate_confidence_score(
        self,
        source_type: str,
        source_reliability: Optional[float] = None,
        ai_confidence: float = 0.5,
        data_completeness: float = 0.5,
        cross_validation_count: int = 0
    ) -> float:
        """
        计算置信度评分

        Args:
            source_type: 数据源类型
            source_reliability: 数据源可靠性（可选，自动从枚举获取）
            ai_confidence: AI 分析置信度 0-1
            data_completeness: 数据完整性 0-1
            cross_validation_count: 交叉验证的数据源数量

        Returns:
            置信度评分 0-100
        """
        # 获取数据源可靠性
        if source_reliability is None:
            try:
                reliability = DataSourceReliability[source_type.upper()].value
            except KeyError:
                reliability = 0.5  # 默认中等可靠性
        else:
            reliability = source_reliability

        # 基础置信度 = 数据源可靠性
        base_confidence = reliability * 100

        # AI 置信度加成
        ai_bonus = ai_confidence * 20

        # 数据完整性加成
        completeness_bonus = data_completeness * 15

        # 交叉验证加成（每多一个数据源加 3 分，最多加 15 分）
        validation_bonus = min(cross_validation_count * 3, 15)

        total = base_confidence + ai_bonus + completeness_bonus + validation_bonus
        return min(100.0, max(0.0, total))

    def calculate_risk_score(
        self,
        risk_factors: Dict[str, float],
        risk_description: str = ""
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算风险评分（分数越低表示风险越小）

        Args:
            risk_factors: 风险因子字典，如 {"regulatory": 0.8, "competitive": 0.3}
            risk_description: 风险描述

        Returns:
            (风险评分 0-100, 风险详情)
        """
        risk_breakdown = {}
        total_risk = 0.0

        for factor, weight in self.risk_weights.items():
            factor_score = risk_factors.get(factor, 0.0)
            weighted_risk = factor_score * weight
            risk_breakdown[factor] = {
                "score": factor_score * 100,
                "weight": weight,
                "weighted_score": weighted_risk * 100
            }
            total_risk += weighted_risk

        # 风险评分 = 100 - 风险程度（风险越高，评分越低）
        risk_score = 100 - (total_risk * 100)

        return (
            min(100.0, max(0.0, risk_score)),
            {
                "total_risk_level": total_risk,
                "breakdown": risk_breakdown,
                "description": risk_description
            }
        )

    def calculate_value_score(
        self,
        estimated_value: float,
        value_currency: str = "CNY",
        value_confidence: float = 0.5,
        value_timeframe_months: int = 12
    ) -> Tuple[float, str]:
        """
        计算价值评分

        Args:
            estimated_value: 预估价值
            value_currency: 货币单位
            value_confidence: 价值评估置信度
            value_timeframe_months: 价值实现时间框（月）

        Returns:
            (价值评分 0-100, 价值等级)
        """
        # 转换为 CNY（简化处理，实际应使用汇率）
        value_cny = estimated_value if value_currency == "CNY" else estimated_value * 7

        # 基于阈值计算基础分数
        if value_cny >= self.value_thresholds["high"]:
            base_score = 90
            value_grade = "high"
        elif value_cny >= self.value_thresholds["medium"]:
            base_score = 70 + (value_cny - self.value_thresholds["medium"]) / \
                         (self.value_thresholds["high"] - self.value_thresholds["medium"]) * 20
            value_grade = "medium"
        elif value_cny >= self.value_thresholds["low"]:
            base_score = 50 + (value_cny - self.value_thresholds["low"]) / \
                         (self.value_thresholds["medium"] - self.value_thresholds["low"]) * 20
            value_grade = "low"
        else:
            base_score = value_cny / self.value_thresholds["low"] * 50
            value_grade = "very_low"

        # 置信度调整
        confidence_adjustment = value_confidence * 10

        # 时间折现（越早实现价值越高）
        time_discount = max(0.5, 1.0 - (value_timeframe_months / 60))  # 5 年以上折现 50%

        final_score = (base_score + confidence_adjustment) * time_discount

        return (
            min(100.0, max(0.0, final_score)),
            value_grade
        )

    def calculate_urgency_score(
        self,
        opportunity_window_days: Optional[int] = None,
        competitive_pressure: float = 0.5,
        market_readiness: float = 0.5,
        internal_readiness: float = 0.5
    ) -> Tuple[float, str]:
        """
        计算紧迫性评分

        Args:
            opportunity_window_days: 机会窗口剩余天数
            competitive_pressure: 竞争压力 0-1
            market_readiness: 市场准备度 0-1
            internal_readiness: 内部准备度 0-1

        Returns:
            (紧迫性评分 0-100, 紧迫等级)
        """
        # 基于时间窗口的紧迫性
        if opportunity_window_days is not None:
            if opportunity_window_days <= self.urgency_thresholds["critical"]:
                time_urgency = 100
                urgency_grade = "critical"
            elif opportunity_window_days <= self.urgency_thresholds["high"]:
                time_urgency = 80 + (1 - opportunity_window_days / 30) * 20
                urgency_grade = "high"
            elif opportunity_window_days <= self.urgency_thresholds["medium"]:
                time_urgency = 50 + (1 - opportunity_window_days / 90) * 30
                urgency_grade = "medium"
            elif opportunity_window_days <= self.urgency_thresholds["low"]:
                time_urgency = 20 + (1 - opportunity_window_days / 180) * 30
                urgency_grade = "low"
            else:
                time_urgency = 20
                urgency_grade = "very_low"
        else:
            time_urgency = 50
            urgency_grade = "unknown"

        # 竞争压力加成
        competitive_bonus = competitive_pressure * 15

        # 市场准备度加成
        market_bonus = market_readiness * 10

        # 内部准备度调整（内部越准备充分，越应该抓紧）
        readiness_multiplier = 0.8 + internal_readiness * 0.4

        final_score = (time_urgency + competitive_bonus + market_bonus) * readiness_multiplier

        return (
            min(100.0, max(0.0, final_score)),
            urgency_grade
        )

    def calculate_feasibility_score(
        self,
        technical_feasibility: float = 0.5,
        resource_availability: float = 0.5,
        time_feasibility: float = 0.5,
        regulatory_feasibility: float = 0.5,
        partner_dependency: float = 0.5
    ) -> float:
        """
        计算可行性评分

        Args:
            technical_feasibility: 技术可行性 0-1
            resource_availability: 资源可用性 0-1
            time_feasibility: 时间可行性 0-1
            regulatory_feasibility: 监管可行性 0-1
            partner_dependency: 合作伙伴依赖度 0-1（越高表示越不依赖外部）

        Returns:
            可行性评分 0-100
        """
        weights = {
            "technical": 0.30,
            "resource": 0.25,
            "time": 0.20,
            "regulatory": 0.15,
            "partner": 0.10
        }

        scores = {
            "technical": technical_feasibility,
            "resource": resource_availability,
            "time": time_feasibility,
            "regulatory": regulatory_feasibility,
            "partner": partner_dependency
        }

        total = sum(scores[k] * weights[k] for k in weights)
        return min(100.0, max(0.0, total * 100))

    def calculate_strategic_fit_score(
        self,
        strategic_alignment: float = 0.5,
        core_competency_match: float = 0.5,
        brand_fit: float = 0.5,
        long_term_vision_alignment: float = 0.5
    ) -> float:
        """
        计算战略匹配度评分

        Args:
            strategic_alignment: 战略对齐度 0-1
            core_competency_match: 核心能力匹配度 0-1
            brand_fit: 品牌匹配度 0-1
            long_term_vision_alignment: 长期愿景对齐度 0-1

        Returns:
            战略匹配度评分 0-100
        """
        weights = {
            "strategic": 0.35,
            "competency": 0.30,
            "brand": 0.15,
            "vision": 0.20
        }

        scores = {
            "strategic": strategic_alignment,
            "competency": core_competency_match,
            "brand": brand_fit,
            "vision": long_term_vision_alignment
        }

        total = sum(scores[k] * weights[k] for k in weights)
        return min(100.0, max(0.0, total * 100))

    def grade_opportunity(self, overall_score: float) -> str:
        """
        根据综合评分定级

        Returns:
            S/A/B/C/D 等级
        """
        if overall_score >= 90:
            return "S"  # 极佳商机
        elif overall_score >= 75:
            return "A"  # 优秀商机
        elif overall_score >= 60:
            return "B"  # 良好商机
        elif overall_score >= 40:
            return "C"  # 一般商机
        else:
            return "D"  # 较差商机

    def generate_recommendations(
        self,
        score: OpportunityScore
    ) -> List[str]:
        """
        基于评分生成建议
        """
        recommendations = []

        # 基于置信度的建议
        if score.confidence_score < 60:
            recommendations.append("建议增加数据源交叉验证，提高置信度")

        # 基于风险的建议
        if score.risk_score < 50:
            recommendations.append("风险较高，建议进行详细风险评估并制定风险缓解计划")

        # 基于价值的建议
        if score.value_score >= 80:
            recommendations.append("高价值商机，建议优先投入资源")
        elif score.value_score < 40:
            recommendations.append("价值有限，建议评估投入产出比")

        # 基于紧迫性的建议
        if score.urgency_score >= 70:
            recommendations.append("机会窗口紧迫，建议快速决策")

        # 基于可行性的建议
        if score.feasibility_score < 50:
            recommendations.append("可行性较低，建议先解决关键技术/资源瓶颈")

        # 基于战略匹配的建议
        if score.strategic_fit_score >= 80:
            recommendations.append("与公司战略高度匹配，建议纳入战略规划")

        return recommendations

    def score_opportunity(
        self,
        opportunity_data: Dict[str, Any]
    ) -> OpportunityScore:
        """
        对商机进行全面评分

        Args:
            opportunity_data: 商机数据字典，包含所有必要字段

        Returns:
            OpportunityScore 综合评分对象
        """
        # 计算各维度评分
        confidence_score = self.calculate_confidence_score(
            source_type=opportunity_data.get("source_type", "AI_ANALYSIS"),
            source_reliability=opportunity_data.get("source_reliability"),
            ai_confidence=opportunity_data.get("confidence_score", 0.5),
            data_completeness=opportunity_data.get("data_completeness", 0.5),
            cross_validation_count=opportunity_data.get("cross_validation_count", 0)
        )

        risk_score, risk_breakdown = self.calculate_risk_score(
            risk_factors=opportunity_data.get("risk_factors", {}),
            risk_description=opportunity_data.get("risk_description", "")
        )

        value_score, value_grade = self.calculate_value_score(
            estimated_value=opportunity_data.get("potential_value", 0),
            value_currency=opportunity_data.get("potential_value_currency", "CNY"),
            value_confidence=opportunity_data.get("value_confidence", 0.5),
            value_timeframe_months=opportunity_data.get("value_timeframe_months", 12)
        )

        urgency_score, urgency_grade = self.calculate_urgency_score(
            opportunity_window_days=opportunity_data.get("opportunity_window_days"),
            competitive_pressure=opportunity_data.get("competitive_pressure", 0.5),
            market_readiness=opportunity_data.get("market_readiness", 0.5),
            internal_readiness=opportunity_data.get("internal_readiness", 0.5)
        )

        feasibility_score = self.calculate_feasibility_score(
            technical_feasibility=opportunity_data.get("technical_feasibility", 0.5),
            resource_availability=opportunity_data.get("resource_availability", 0.5),
            time_feasibility=opportunity_data.get("time_feasibility", 0.5),
            regulatory_feasibility=opportunity_data.get("regulatory_feasibility", 0.5),
            partner_dependency=opportunity_data.get("partner_dependency", 0.5)
        )

        strategic_fit_score = self.calculate_strategic_fit_score(
            strategic_alignment=opportunity_data.get("strategic_alignment", 0.5),
            core_competency_match=opportunity_data.get("core_competency_match", 0.5),
            brand_fit=opportunity_data.get("brand_fit", 0.5),
            long_term_vision_alignment=opportunity_data.get("long_term_vision_alignment", 0.5)
        )

        # 计算综合评分
        dimension_scores = {
            "confidence": confidence_score,
            "risk": risk_score,
            "value": value_score,
            "urgency": urgency_score,
            "feasibility": feasibility_score,
            "strategic_fit": strategic_fit_score,
        }

        overall_score = self.calculate_overall_score(dimension_scores)
        grade = self.grade_opportunity(overall_score)

        # 创建评分对象
        score = OpportunityScore(
            opportunity_id=opportunity_data.get("id", "unknown"),
            overall_score=round(overall_score, 2),
            grade=grade,
            confidence_score=round(confidence_score, 2),
            risk_score=round(risk_score, 2),
            value_score=round(value_score, 2),
            urgency_score=round(urgency_score, 2),
            feasibility_score=round(feasibility_score, 2),
            strategic_fit_score=round(strategic_fit_score, 2),
            score_breakdown={
                "risk": risk_breakdown,
                "value_grade": value_grade,
                "urgency_grade": urgency_grade,
            },
            scoring_factors=self._identify_key_factors(dimension_scores),
            recommendations=[]
        )

        # 生成建议
        score.recommendations = self.generate_recommendations(score)

        return score

    def _identify_key_factors(self, dimension_scores: Dict[str, float]) -> List[str]:
        """识别影响评分的关键因素"""
        factors = []

        # 找出最高和最低的维度
        sorted_scores = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)

        # 高分因素（优势）
        if sorted_scores[0][1] >= 80:
            factors.append(f"优势领域：{sorted_scores[0][0]} (得分：{sorted_scores[0][1]:.1f})")

        # 低分因素（需改进）
        if sorted_scores[-1][1] < 50:
            factors.append(f"需改进：{sorted_scores[-1][0]} (得分：{sorted_scores[-1][1]:.1f})")

        # 显著差异
        if sorted_scores[0][1] - sorted_scores[-1][1] > 40:
            factors.append(f"评分差异显著，建议平衡发展")

        return factors


class MLScoreModel:
    """
    机器学习评分模型

    使用历史数据训练模型，预测商机成功率
    """

    def __init__(self):
        self.model = None
        self.is_trained = False
        self.training_data = []

        # 特征权重（基于经验或训练得到）
        self.feature_weights = {
            "confidence_score": 0.15,
            "risk_score": -0.20,  # 负相关
            "value_score": 0.20,
            "urgency_score": 0.10,
            "feasibility_score": 0.15,
            "strategic_fit_score": 0.15,
            "market_size": 0.10,
            "competition_level": -0.10,  # 负相关
            "team_experience": 0.15,
        }

    def train(self, historical_data: List[Dict[str, Any]]) -> bool:
        """
        训练模型（简化版，实际应使用 sklearn 等库）

        Args:
            historical_data: 历史商机数据，包含特征和结果标签

        Returns:
            训练是否成功
        """
        if len(historical_data) < 10:
            logger.warning("训练数据不足，使用默认权重")
            return False

        # 简化处理：基于历史数据调整权重
        # 实际应使用逻辑回归、随机森林等算法

        self.training_data = historical_data
        self.is_trained = True

        logger.info(f"模型训练完成，使用 {len(historical_data)} 条历史数据")
        return True

    def predict_success_probability(
        self,
        opportunity_data: Dict[str, Any]
    ) -> float:
        """
        预测商机成功概率

        Args:
            opportunity_data: 商机特征数据

        Returns:
            成功概率 0-1
        """
        # 提取特征
        features = {
            "confidence_score": opportunity_data.get("confidence_score", 0.5) * 100,
            "risk_score": (1 - opportunity_data.get("risk_factors", {}).get("overall", 0.5)) * 100,
            "value_score": min(100, opportunity_data.get("potential_value", 0) / 100000),
            "urgency_score": opportunity_data.get("urgency_score", 0.5) * 100,
            "feasibility_score": opportunity_data.get("feasibility_score", 0.5) * 100,
            "strategic_fit_score": opportunity_data.get("strategic_fit_score", 0.5) * 100,
            "market_size": min(100, opportunity_data.get("market_size", 1000000) / 10000000),
            "competition_level": opportunity_data.get("competition_level", 0.5) * 100,
            "team_experience": opportunity_data.get("team_experience", 0.5) * 100,
        }

        # 计算加权和
        weighted_sum = sum(
            features.get(k, 0) * v
            for k, v in self.feature_weights.items()
        )

        # Sigmoid 转换到 0-1
        probability = 1 / (1 + np.exp(-weighted_sum / 20))

        return min(1.0, max(0.0, probability))

    def explain_prediction(
        self,
        opportunity_data: Dict[str, Any]
    ) -> List[str]:
        """
        解释预测结果
        """
        explanations = []

        # 分析各特征的贡献
        for feature, weight in self.feature_weights.items():
            value = opportunity_data.get(feature, 0.5)
            if isinstance(value, dict):
                value = value.get("overall", 0.5)

            contribution = value * weight

            if contribution > 0.1:
                explanations.append(f"{feature}: 正向贡献 ({contribution:.2f})")
            elif contribution < -0.1:
                explanations.append(f"{feature}: 负向影响 ({contribution:.2f})")

        return explanations


# 全局单例
opportunity_scorer = OpportunityScoringModel()
ml_score_model = MLScoreModel()
