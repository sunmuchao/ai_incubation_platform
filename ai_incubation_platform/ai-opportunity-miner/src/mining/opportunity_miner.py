"""
商机挖掘引擎
整合多源数据和分析能力，自动发现商机
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid
import logging
from crawler.news_crawler import news_crawler
from crawler.report_crawler import report_crawler
from nlp.text_analyzer import text_analyzer
from analysis.trend_analyzer import trend_analyzer
from utils.llm_client import llm_client
from models.opportunity import BusinessOpportunity, OpportunityType, RiskLabel, SourceType, OpportunityStatus

logger = logging.getLogger(__name__)

class OpportunityMiner:
    """商机挖掘引擎"""

    def __init__(self):
        self.news_crawler = news_crawler
        self.report_crawler = report_crawler
        self.text_analyzer = text_analyzer
        self.trend_analyzer = trend_analyzer
        self.llm_client = llm_client

    async def discover_from_keywords(self, keywords: List[str], days: int = 30) -> List[BusinessOpportunity]:
        """从关键词发现商机"""
        opportunities = []

        # 获取多源数据
        news_articles = await self.news_crawler.fetch_news(keywords, days)
        industry_reports = await self.report_crawler.fetch_reports(keywords)

        # 合并所有文本
        all_text = "\n".join([a["content"] for a in news_articles] + [r["summary"] for r in industry_reports])

        # 文本分析
        indicators = self.text_analyzer.extract_indicators(all_text)
        entities = self.text_analyzer.extract_entities(all_text)
        signals = self.text_analyzer.extract_opportunity_signals(all_text)

        # 计算置信度（演示场景下避免过强的正负信号数量门槛）
        confidence = self.text_analyzer.calculate_confidence(indicators, "ai_analysis")
        # 让后续生成阶段使用同一套置信度指标
        indicators["confidence"] = confidence

        if confidence >= 0.6:  # 置信度阈值
            opportunity = await self._generate_opportunity(
                keywords=keywords,
                indicators=indicators,
                entities=entities,
                signals=signals,
                news_articles=news_articles,
                reports=industry_reports
            )
            opportunities.append(opportunity)

        return opportunities

    async def discover_by_industry(self, industry: str, days: int = 60) -> List[BusinessOpportunity]:
        """按行业发现商机"""
        keywords = [
            industry,
            f"{industry}发展",
            f"{industry}政策",
            f"{industry}技术",
            f"{industry}市场",
            f"{industry}投资"
        ]
        return await self.discover_from_keywords(keywords, days)

    async def discover_from_trends(self, trends: List[str]) -> List[BusinessOpportunity]:
        """从趋势关键词发现商机"""
        opportunities = []
        for trend in trends:
            opps = await self.discover_from_keywords([trend])
            opportunities.extend(opps)
        return opportunities

    async def _generate_opportunity(self, keywords: List[str], indicators: Dict, entities: Dict,
                                  signals: Dict, news_articles: List[Dict], reports: List[Dict]) -> BusinessOpportunity:
        """生成商机对象"""
        main_keyword = keywords[0]

        # 确定商机类型
        opportunity_type = self._determine_opportunity_type(signals["opportunity_type"])

        # 计算风险标签
        risk_labels, risk_score = self._calculate_risk(signals, indicators)

        # 生成验证步骤
        validation_steps = self._generate_validation_steps(main_keyword, opportunity_type)

        # 获取最相关的来源
        primary_source = reports[0] if reports else news_articles[0] if news_articles else None

        # LLM生成摘要和建议
        opportunity_data = {
            "keyword": main_keyword,
            "indicators": indicators,
            "signals": signals,
            "entities": entities
        }
        llm_summary = await self.llm_client.generate_opportunity_summary(opportunity_data)

        # 构建商机标题和描述
        title = llm_summary.get("summary", f"{main_keyword}领域市场机遇")[:100]
        description = self._generate_description(main_keyword, indicators, llm_summary)

        # 计算潜在价值
        market_size = indicators.get("market_size", {}).get("value", 0)
        unit = indicators.get("market_size", {}).get("unit", "亿")
        if unit == "亿":
            potential_value = market_size * 100000000 * 0.01  # 按1%的市场渗透率估算
        else:
            potential_value = market_size * 10000 * 0.01

        # 构建商机对象
        opportunity = BusinessOpportunity(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            type=opportunity_type,
            confidence_score=indicators.get("confidence", 0.7),
            potential_value=potential_value,
            potential_value_currency="CNY",

            source_type=SourceType.AI_ANALYSIS,
            source_name=primary_source["publisher"] if primary_source and "publisher" in primary_source else primary_source["source"] if primary_source else "AI分析",
            source_url=primary_source["url"] if primary_source else "",
            source_publish_date=primary_source["publish_date"] if primary_source and "publish_date" in primary_source else primary_source["published_at"] if primary_source else datetime.now(),

            risk_labels=risk_labels,
            risk_score=risk_score,
            risk_description=self._generate_risk_description(risk_labels, risk_score),

            validation_steps=validation_steps,
            validation_status="pending",

            related_entities=self._format_related_entities(entities),
            tags=self._generate_tags(keywords, signals, indicators),
            status=OpportunityStatus.NEW,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            extra={
                "llm_analysis": llm_summary,
                "source_count": len(news_articles) + len(reports),
                "news_count": len(news_articles),
                "report_count": len(reports)
            }
        )

        return opportunity

    def _determine_opportunity_type(self, signal_types: List[str]) -> OpportunityType:
        """确定商机类型"""
        type_mapping = {
            "market": OpportunityType.MARKET,
            "technology": OpportunityType.PRODUCT,
            "investment": OpportunityType.INVESTMENT,
            "policy": OpportunityType.MARKET
        }

        for signal_type in signal_types:
            if signal_type in type_mapping:
                return type_mapping[signal_type]

        return OpportunityType.MARKET

    def _calculate_risk(self, signals: Dict, indicators: Dict) -> Tuple[List[RiskLabel], float]:
        """计算风险标签和风险评分"""
        risk_labels = []
        risk_score = 0.0

        # 负向信号数量
        negative_count = len(signals["negative"])
        if negative_count >= 3:
            risk_score += 0.3
            risk_labels.append(RiskLabel.HIGH_RISK)
        elif negative_count >= 1:
            risk_score += 0.15
            risk_labels.append(RiskLabel.MEDIUM_RISK)
        else:
            risk_labels.append(RiskLabel.LOW_RISK)

        # 竞争风险
        if "competition" in indicators.get("tags", []):
            risk_score += 0.2
            risk_labels.append(RiskLabel.COMPETITIVE)

        # 监管风险
        if "regulatory" in signals.get("negative", []):
            risk_score += 0.2
            risk_labels.append(RiskLabel.REGULATORY)

        # 技术风险
        if "technological" in signals.get("negative", []):
            risk_score += 0.2
            risk_labels.append(RiskLabel.TECHNOLOGICAL)

        # 市场风险
        if "market" in signals.get("negative", []):
            risk_score += 0.15
            risk_labels.append(RiskLabel.MARKET)

        risk_score = min(1.0, risk_score)
        return list(set(risk_labels)), risk_score

    def _generate_validation_steps(self, keyword: str, opportunity_type: OpportunityType) -> List[str]:
        """生成验证步骤"""
        base_steps = [
            f"1. 核实{keyword}相关行业报告和统计数据的权威性",
            f"2. 调研{keyword}产业链上下游核心企业的经营情况",
            f"3. 访谈3-5家行业专家和企业负责人了解实际市场需求",
            f"4. 分析相关政策的持续性和落地执行情况"
        ]

        type_specific_steps = {
            OpportunityType.MARKET: [
                "5. 调研目标市场的用户需求和付费意愿",
                "6. 评估市场进入的门槛和竞争程度"
            ],
            OpportunityType.PRODUCT: [
                "5. 评估相关技术的成熟度和落地可行性",
                "6. 调研同类产品的市场表现和用户反馈"
            ],
            OpportunityType.INVESTMENT: [
                "5. 分析行业估值水平和投资回报周期",
                "6. 调研头部投资机构的布局方向"
            ],
            OpportunityType.PARTNERSHIP: [
                "5. 识别潜在的合作伙伴和合作模式",
                "6. 评估合作的潜在风险和收益"
            ]
        }

        steps = base_steps + type_specific_steps.get(opportunity_type, [])
        return steps

    def _generate_risk_description(self, risk_labels: List[RiskLabel], risk_score: float) -> str:
        """生成风险描述"""
        risk_level = "高" if risk_score >= 0.7 else "中" if risk_score >= 0.4 else "低"

        label_descriptions = {
            RiskLabel.LOW_RISK: "整体风险较低",
            RiskLabel.MEDIUM_RISK: "存在一定风险",
            RiskLabel.HIGH_RISK: "整体风险较高",
            RiskLabel.COMPETITIVE: "市场竞争较为激烈",
            RiskLabel.REGULATORY: "存在一定监管政策风险",
            RiskLabel.TECHNOLOGICAL: "存在技术迭代和研发风险",
            RiskLabel.MARKET: "存在市场需求不确定性风险"
        }

        descriptions = [label_descriptions.get(label, "") for label in risk_labels]
        descriptions = [d for d in descriptions if d]

        return f"风险等级：{risk_level}。{'，'.join(descriptions)}。"

    def _format_related_entities(self, entities: Dict) -> List[Dict[str, str]]:
        """格式化关联实体"""
        related = []
        for company in entities.get("companies", [])[:5]:  # 最多5个公司
            related.append({
                "name": company,
                "type": "company",
                "relation": "行业相关企业"
            })
        for product in entities.get("products", [])[:3]:  # 最多3个产品
            related.append({
                "name": product,
                "type": "product",
                "relation": "相关产品"
            })
        return related

    def _generate_tags(self, keywords: List[str], signals: Dict, indicators: Dict) -> List[str]:
        """生成标签"""
        tags = keywords.copy()
        tags.extend(signals.get("opportunity_type", []))
        tags.extend(indicators.get("tags", []))
        return list(set(tags))[:10]  # 最多10个标签

    def _generate_description(self, keyword: str, indicators: Dict, llm_summary: Dict) -> str:
        """生成商机描述"""
        market_size = indicators.get("market_size", {})
        growth_rate = indicators.get("growth_rate", {})

        description_parts = []

        if market_size:
            description_parts.append(f"市场规模约{market_size['value']}{market_size['unit']}")
        if growth_rate:
            description_parts.append(f"年增长率{growth_rate['value']*100:.1f}%")

        base_desc = f"{keyword}领域正处于快速发展阶段，"
        if description_parts:
            base_desc += "，".join(description_parts) + "。"
        else:
            base_desc += "具备良好的市场前景。"

        llm_desc = llm_summary.get("summary", "")
        if llm_desc:
            base_desc += f" {llm_desc}"

        return base_desc[:500]  # 限制长度

opportunity_miner = OpportunityMiner()
