"""
v1.9 竞品分析增强服务

提供竞品追踪、市场份额分析、竞品策略解读功能
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import random

logger = logging.getLogger(__name__)


@dataclass
class CompetitorMetric:
    """竞品指标数据"""
    domain: str
    traffic: int  # 月流量
    traffic_growth: float  # 流量增长率
    keywords_count: int  # 关键词数量
    keywords_top3: int  # 前 3 名关键词数
    keywords_top10: int  # 前 10 名关键词数
    backlinks: int  # 反向链接数
    domain_authority: int  # 域名权重
    market_share: float  # 市场份额
    content_count: int  # 内容数量
    avg_position: float  # 平均排名


@dataclass
class CompetitorStrategy:
    """竞品策略解读"""
    competitor: str
    strategy_type: str  # content/seo/paid/partnership
    description: str
    evidence: List[str]
    impact_level: str  # high/medium/low
    confidence: float
    recommended_action: str


@dataclass
class MarketShareData:
    """市场份额数据"""
    period: str
    total_market_size: int
    competitors: Dict[str, float]  # domain -> share percentage
    top_gainers: List[Dict]
    top_losers: List[Dict]
    market_trends: List[str]


class CompetitorService:
    """竞品分析服务"""

    def __init__(self, db_session=None):
        self.db = db_session
        self.tracked_competitors = self._load_tracked_competitors()

    def _load_tracked_competitors(self) -> List[str]:
        """加载追踪的竞品列表"""
        # 默认竞品列表，实际应从数据库或配置加载
        return [
            "competitor1.com",
            "competitor2.com",
            "competitor3.com",
            "industry-leader.com"
        ]

    def track_competitor(self, domain: str) -> Dict:
        """
        追踪竞品数据

        Args:
            domain: 竞品域名

        Returns:
            竞品指标数据
        """
        logger.info(f"开始追踪竞品：{domain}")

        # 模拟竞品数据抓取
        # 实际应集成 SimilarWeb/Ahrefs/SEMrush API
        metrics = self._fetch_competitor_metrics(domain)

        # 保存到数据库
        self._save_competitor_metrics(domain, metrics)

        logger.info(f"竞品追踪完成：{domain}, 流量={metrics['traffic']}")
        return metrics

    def _fetch_competitor_metrics(self, domain: str) -> Dict:
        """获取竞品指标数据（模拟）"""
        base_traffic = random.randint(100000, 10000000)
        base_keywords = random.randint(1000, 50000)

        return {
            "domain": domain,
            "traffic": base_traffic,
            "traffic_growth": round(random.uniform(-0.3, 0.5), 2),
            "keywords_count": base_keywords,
            "keywords_top3": int(base_keywords * random.uniform(0.05, 0.15)),
            "keywords_top10": int(base_keywords * random.uniform(0.15, 0.30)),
            "backlinks": random.randint(10000, 1000000),
            "domain_authority": random.randint(30, 90),
            "market_share": round(random.uniform(0.01, 0.25), 3),
            "content_count": random.randint(100, 10000),
            "avg_position": round(random.uniform(15, 45), 1)
        }

    def _save_competitor_metrics(self, domain: str, metrics: Dict):
        """保存竞品指标到数据库"""
        # 实际实现应写入数据库
        pass

    def get_competitor_comparison(self, start_date: date = None, end_date: date = None) -> Dict:
        """
        获取竞品对比分析

        Returns:
            竞品对比数据
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        logger.info(f"获取竞品对比分析：{start_date} 到 {end_date}")

        comparison_data = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "our_domain": "yourdomain.com",
            "our_metrics": self._fetch_competitor_metrics("yourdomain.com"),
            "competitors": []
        }

        for competitor in self.tracked_competitors:
            metrics = self._fetch_competitor_metrics(competitor)
            comparison_data["competitors"].append(metrics)

        # 计算排名
        comparison_data["rankings"] = self._calculate_rankings(comparison_data)

        return comparison_data

    def _calculate_rankings(self, comparison_data: Dict) -> Dict:
        """计算各项指标的排名"""
        all_domains = [comparison_data["our_metrics"]] + comparison_data["competitors"]

        rankings = {
            "traffic": sorted(all_domains, key=lambda x: x["traffic"], reverse=True),
            "traffic_growth": sorted(all_domains, key=lambda x: x["traffic_growth"], reverse=True),
            "keywords_count": sorted(all_domains, key=lambda x: x["keywords_count"], reverse=True),
            "domain_authority": sorted(all_domains, key=lambda x: x["domain_authority"], reverse=True),
        }

        # 添加排名位置
        for metric, ranked_list in rankings.items():
            for i, item in enumerate(ranked_list):
                item[f"{metric}_rank"] = i + 1

        return rankings

    def analyze_market_share(self, period: str = "current_month") -> MarketShareData:
        """
        分析市场份额

        Args:
            period: 时间段

        Returns:
            市场份额数据
        """
        logger.info(f"分析市场份额：{period}")

        # 获取所有竞品数据
        all_metrics = []
        for competitor in self.tracked_competitors:
            metrics = self._fetch_competitor_metrics(competitor)
            all_metrics.append(metrics)

        # 计算总市场规模
        total_traffic = sum(m["traffic"] for m in all_metrics)

        # 计算各竞品市场份额
        market_shares = {}
        for m in all_metrics:
            share = m["traffic"] / total_traffic if total_traffic > 0 else 0
            market_shares[m["domain"]] = round(share * 100, 2)

        # 找出增长最快和下滑最快
        sorted_by_growth = sorted(all_metrics, key=lambda x: x["traffic_growth"], reverse=True)
        top_gainers = [
            {"domain": m["domain"], "growth": m["traffic_growth"]}
            for m in sorted_by_growth[:3] if m["traffic_growth"] > 0
        ]
        top_losers = [
            {"domain": m["domain"], "growth": m["traffic_growth"]}
            for m in sorted_by_growth[-3:] if m["traffic_growth"] < 0
        ]

        # 市场趋势分析
        trends = self._analyze_market_trends(all_metrics)

        return MarketShareData(
            period=period,
            total_market_size=total_traffic,
            competitors=market_shares,
            top_gainers=top_gainers,
            top_losers=top_losers,
            market_trends=trends
        )

    def _analyze_market_trends(self, all_metrics: List[Dict]) -> List[str]:
        """分析市场趋势"""
        trends = []

        avg_growth = sum(m["traffic_growth"] for m in all_metrics) / len(all_metrics)
        if avg_growth > 0.2:
            trends.append("市场整体快速增长，平均增长率超过 20%")
        elif avg_growth < 0:
            trends.append("市场整体萎缩，需警惕")
        else:
            trends.append("市场保持稳定增长")

        # 分析竞争集中度
        market_shares = [m["market_share"] for m in all_metrics]
        hhi = sum(s ** 2 for s in market_shares)  # HHI 指数
        if hhi > 0.4:
            trends.append("市场集中度高，头部效应明显")
        else:
            trends.append("市场竞争分散，机会较多")

        return trends

    def analyze_competitor_strategy(self, domain: str) -> List[CompetitorStrategy]:
        """
        解读竞品策略

        Args:
            domain: 竞品域名

        Returns:
            竞品策略列表
        """
        logger.info(f"分析竞品策略：{domain}")

        metrics = self._fetch_competitor_metrics(domain)
        strategies = []

        # 内容策略分析
        if metrics["content_count"] > 1000:
            strategies.append(CompetitorStrategy(
                competitor=domain,
                strategy_type="content",
                description=f"{domain} 采用内容营销战略，发布大量内容吸引流量",
                evidence=[
                    f"内容数量达{metrics['content_count']}篇",
                    f"关键词覆盖{metrics['keywords_count']}个"
                ],
                impact_level="high",
                confidence=0.85,
                recommended_action="增加内容产出，重点关注长尾关键词"
            ))

        # SEO 策略分析
        if metrics["keywords_top3"] > metrics["keywords_count"] * 0.1:
            strategies.append(CompetitorStrategy(
                competitor=domain,
                strategy_type="seo",
                description=f"{domain} 采用激进的 SEO 优化策略",
                evidence=[
                    f"TOP3 关键词占比{metrics['keywords_top3']/metrics['keywords_count']*100:.1f}%",
                    f"域名权重达{metrics['domain_authority']}"
                ],
                impact_level="high",
                confidence=0.9,
                recommended_action="加强技术 SEO，提升页面质量得分"
            ))

        # 外链策略分析
        if metrics["backlinks"] > 500000:
            strategies.append(CompetitorStrategy(
                competitor=domain,
                strategy_type="partnership",
                description=f"{domain} 建立了强大的外链网络",
                evidence=[
                    f"反向链接数达{metrics['backlinks']:,}"
                ],
                impact_level="medium",
                confidence=0.8,
                recommended_action="开展外链建设，寻找高质量链接机会"
            ))

        return strategies

    def get_competitor_alerts(self) -> List[Dict]:
        """
        获取竞品告警

        Returns:
            竞品动态告警列表
        """
        alerts = []

        for competitor in self.tracked_competitors:
            metrics = self._fetch_competitor_metrics(competitor)

            # 流量大幅增长告警
            if metrics["traffic_growth"] > 0.3:
                alerts.append({
                    "type": "traffic_surge",
                    "level": "warning",
                    "competitor": competitor,
                    "message": f"{competitor} 流量大幅增长{metrics['traffic_growth']*100:.1f}%",
                    "suggested_action": "分析其流量来源，找出增长原因"
                })

            # 关键词排名超越告警
            if metrics["keywords_top3"] > 1000:
                alerts.append({
                    "type": "keyword_overtake",
                    "level": "info",
                    "competitor": competitor,
                    "message": f"{competitor} 有{metrics['keywords_top3']}个关键词进入 TOP3",
                    "suggested_action": "检查核心关键词排名变化"
                })

        return alerts

    def get_competitor_insights(self) -> Dict:
        """
        获取竞品洞察

        Returns:
            竞品洞察数据
        """
        market_share = self.analyze_market_share()
        comparison = self.get_competitor_comparison()

        insights = {
            "market_overview": {
                "total_size": market_share.total_market_size,
                "our_share": market_share.competitors.get("yourdomain.com", 0),
                "market_position": self._calculate_market_position(market_share)
            },
            "key_findings": self._generate_key_findings(market_share, comparison),
            "opportunities": self._identify_opportunities(market_share, comparison),
            "threats": self._identify_threats(market_share, comparison),
            "recommended_actions": self._generate_recommendations(market_share, comparison)
        }

        return insights

    def _calculate_market_position(self, market_share: MarketShareData) -> str:
        """计算市场地位"""
        shares = sorted(market_share.competitors.values(), reverse=True)
        our_share = market_share.competitors.get("yourdomain.com", 0)

        if our_share == shares[0]:
            return "leader"
        elif our_share > sum(shares) / len(shares):
            return "challenger"
        elif our_share > shares[-1]:
            return "follower"
        else:
            return "niche"

    def _generate_key_findings(self, market_share: MarketShareData,
                                comparison: Dict) -> List[str]:
        """生成关键发现"""
        findings = []

        # 市场地位
        position = self._calculate_market_position(market_share)
        findings.append(f"当前市场地位：{position}")

        # 增长趋势
        our_growth = comparison["our_metrics"]["traffic_growth"]
        if our_growth > 0:
            findings.append(f"我方流量增长{our_growth*100:.1f}%，高于市场平均")
        else:
            findings.append(f"我方流量下滑{our_growth*100:.1f}%，需引起重视")

        return findings

    def _identify_opportunities(self, market_share: MarketShareData,
                                 comparison: Dict) -> List[Dict]:
        """识别市场机会"""
        opportunities = []

        # 找出竞品薄弱环节
        for comp in comparison["competitors"]:
            if comp["avg_position"] > 30:
                opportunities.append({
                    "type": "content_gap",
                    "description": f"{comp['domain']} 平均排名较低，可在相关关键词上超越",
                    "priority": "medium"
                })

        return opportunities

    def _identify_threats(self, market_share: MarketShareData,
                          comparison: Dict) -> List[Dict]:
        """识别市场威胁"""
        threats = []

        # 找出增长强劲的竞品
        for comp in comparison["competitors"]:
            if comp["traffic_growth"] > 0.3:
                threats.append({
                    "type": "fast_growing_competitor",
                    "description": f"{comp['domain']} 增长迅猛 ({comp['traffic_growth']*100:.1f}%)",
                    "priority": "high"
                })

        return threats

    def _generate_recommendations(self, market_share: MarketShareData,
                                   comparison: Dict) -> List[Dict]:
        """生成建议"""
        recommendations = []

        our_metrics = comparison["our_metrics"]

        # 基于差距生成建议
        if our_metrics["keywords_top3"] < 500:
            recommendations.append({
                "action": "加强关键词优化",
                "description": "提升核心关键词排名至 TOP3",
                "expected_impact": "流量提升 20-30%"
            })

        if our_metrics["domain_authority"] < 50:
            recommendations.append({
                "action": "提升域名权重",
                "description": "通过高质量内容和外链建设提升 DA",
                "expected_impact": "整体排名提升"
            })

        return recommendations
