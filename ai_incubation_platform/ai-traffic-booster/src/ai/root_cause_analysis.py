"""
AI 根因分析服务

功能:
- 多维度归因分析
- 根因定位与解释
- 决策树分析
- 关联因素识别
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from enum import Enum
import logging
from collections import defaultdict

from .anomaly_detection import AnomalyDetectionResult, AnomalyType, AnomalySeverity
from analytics.service import analytics_service
from schemas.analytics import TrafficOverviewRequest, TrafficSource

logger = logging.getLogger(__name__)


class RootCauseCategory(str, Enum):
    """根因类别"""
    TRAFFIC_SOURCE = "traffic_source"      # 流量来源问题
    KEYWORD_RANKING = "keyword_ranking"    # 关键词排名问题
    PAGE_PERFORMANCE = "page_performance"  # 页面性能问题
    DEVICE_ISSUE = "device_issue"          # 设备兼容问题
    GEO_ISSUE = "geo_issue"                # 地域问题
    CONTENT_ISSUE = "content_issue"        # 内容问题
    TECHNICAL_ISSUE = "technical_issue"    # 技术问题
    SEASONAL = "seasonal"                  # 季节性波动
    COMPETITOR = "competitor"              # 竞品影响


class RootCauseConfidence(str, Enum):
    """根因置信度"""
    HIGH = "high"      # 高置信度 (>80%)
    MEDIUM = "medium"  # 中置信度 (50-80%)
    LOW = "low"        # 低置信度 (<50%)


class RootCause:
    """根因分析结果"""
    def __init__(
        self,
        category: RootCauseCategory,
        description: str,
        confidence: RootCauseConfidence,
        evidence: List[str],
        impact_score: float,  # 影响程度 0-1
        contributing_factors: List[Dict[str, Any]],
        recommended_actions: List[str]
    ):
        self.category = category
        self.description = description
        self.confidence = confidence
        self.evidence = evidence
        self.impact_score = impact_score
        self.contributing_factors = contributing_factors
        self.recommended_actions = recommended_actions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "description": self.description,
            "confidence": self.confidence.value,
            "evidence": self.evidence,
            "impact_score": round(self.impact_score, 2),
            "contributing_factors": self.contributing_factors,
            "recommended_actions": self.recommended_actions
        }


class RootCauseAnalysisResult:
    """根因分析完整结果"""
    def __init__(
        self,
        anomaly: AnomalyDetectionResult,
        root_causes: List[RootCause],
        primary_cause: Optional[RootCause],
        analysis_summary: str,
        analyzed_at: datetime = None
    ):
        self.anomaly = anomaly
        self.root_causes = root_causes
        self.primary_cause = primary_cause
        self.analysis_summary = analysis_summary
        self.analyzed_at = analyzed_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly": self.anomaly.to_dict(),
            "root_causes": [rc.to_dict() for rc in self.root_causes],
            "primary_cause": self.primary_cause.to_dict() if self.primary_cause else None,
            "analysis_summary": self.analysis_summary,
            "analyzed_at": self.analyzed_at.isoformat()
        }


class RootCauseAnalysisService:
    """
    AI 根因分析服务

    使用多维度分析方法定位问题根因:
    - 流量来源维度分析
    - 关键词排名维度分析
    - 页面性能维度分析
    - 设备/地域维度分析
    - 时间序列模式分析
    """

    def __init__(self):
        # 影响阈值配置
        self.significant_change_threshold = 0.15  # 显著变化阈值 15%
        self.major_change_threshold = 0.30        # 重大变化阈值 30%

    def analyze(
        self,
        anomaly: AnomalyDetectionResult,
        domain: Optional[str] = None,
        check_date: Optional[date] = None
    ) -> RootCauseAnalysisResult:
        """
        执行根因分析

        Args:
            anomaly: 异常检测结果
            domain: 域名
            check_date: 检查日期

        Returns:
            根因分析结果
        """
        if check_date is None:
            check_date = date.today()

        root_causes = []

        # 根据异常类型选择分析策略
        if anomaly.anomaly_type in [AnomalyType.TRAFFIC_DROP, AnomalyType.TRAFFIC_SPIKE]:
            root_causes.extend(self._analyze_traffic_sources(domain, check_date))
            root_causes.extend(self._analyze_keyword_rankings(domain, check_date))
            root_causes.extend(self._analyze_page_performance(domain, check_date))
            root_causes.extend(self._analyze_device_distribution(domain, check_date))
            root_causes.extend(self._analyze_geo_distribution(domain, check_date))

        elif anomaly.anomaly_type in [AnomalyType.CONVERSION_DROP, AnomalyType.CONVERSION_SPIKE]:
            root_causes.extend(self._analyze_conversion_funnel(domain, check_date))
            root_causes.extend(self._analyze_page_performance(domain, check_date))

        elif anomaly.anomaly_type == AnomalyType.BOUNCE_RATE_SPIKE:
            root_causes.extend(self._analyze_page_performance(domain, check_date))
            root_causes.extend(self._analyze_traffic_quality(domain, check_date))

        elif anomaly.anomaly_type == AnomalyType.RANKING_DROP:
            root_causes.extend(self._analyze_seo_factors(domain, check_date))

        # 按影响分数排序
        root_causes.sort(key=lambda x: x.impact_score, reverse=True)

        # 确定主要原因
        primary_cause = root_causes[0] if root_causes else None

        # 生成分析摘要
        analysis_summary = self._generate_analysis_summary(anomaly, root_causes)

        return RootCauseAnalysisResult(
            anomaly=anomaly,
            root_causes=root_causes,
            primary_cause=primary_cause,
            analysis_summary=analysis_summary
        )

    def _analyze_traffic_sources(
        self,
        domain: Optional[str],
        check_date: date
    ) -> List[RootCause]:
        """分析流量来源维度的根因"""
        causes = []

        # 获取历史数据
        end_date = check_date - timedelta(days=1)
        start_date = end_date - timedelta(days=14)

        try:
            # 获取历史流量来源分布
            historical_request = TrafficOverviewRequest(
                start_date=start_date,
                end_date=end_date,
                domain=domain
            )
            historical = analytics_service.get_traffic_overview(historical_request)

            # 获取当前流量来源分布
            current_request = TrafficOverviewRequest(
                start_date=check_date,
                end_date=check_date,
                domain=domain
            )
            current = analytics_service.get_traffic_overview(current_request)

            # 对比各来源变化
            historical_sources = {s.source.value: s.percentage for s in historical.sources}
            current_sources = {s.source.value: s.percentage for s in current.sources}

            for source in historical_sources:
                if source in current_sources:
                    change = current_sources[source] - historical_sources[source]
                    abs_change = abs(change)

                    if abs_change >= self.significant_change_threshold:
                        confidence = (
                            RootCauseConfidence.HIGH
                            if abs_change >= self.major_change_threshold
                            else RootCauseConfidence.MEDIUM
                        )

                        if change < 0:
                            description = f"{self._get_source_name(source)}流量占比显著下降{abs_change*100:.1f}%"
                        else:
                            description = f"{self._get_source_name(source)}流量占比显著上升{abs_change*100:.1f}%"

                        causes.append(RootCause(
                            category=RootCauseCategory.TRAFFIC_SOURCE,
                            description=description,
                            confidence=confidence,
                            evidence=[
                                f"历史占比：{historical_sources[source]*100:.1f}%",
                                f"当前占比：{current_sources[source]*100:.1f}%",
                                f"变化幅度：{change*100:+.1f}%"
                            ],
                            impact_score=abs_change,
                            contributing_factors=[{
                                "source": source,
                                "historical": historical_sources[source],
                                "current": current_sources[source],
                                "change": change
                            }],
                            recommended_actions=self._get_source_actions(source, change)
                        ))

        except Exception as e:
            logger.error(f"流量来源分析失败：{e}")

        return causes

    def _analyze_keyword_rankings(
        self,
        domain: Optional[str],
        check_date: date
    ) -> List[RootCause]:
        """分析关键词排名维度的根因"""
        causes = []

        try:
            # 获取关键词排名数据
            end_date = check_date
            start_date = end_date - timedelta(days=7)

            ranking_data = analytics_service.get_keyword_ranking(start_date, end_date)

            # 分析排名下降的关键词
            if ranking_data.declined:
                total_rank_drop = sum(
                    (k.previous_position or k.current_position) - k.current_position
                    for k in ranking_data.declined
                )

                if len(ranking_data.declined) >= 3 or total_rank_drop > 10:
                    # 计算影响程度
                    top_declined = ranking_data.declined[:5]
                    evidence = [
                        f"共{len(ranking_data.declined)}个关键词排名下降",
                        f"Top 下降关键词：{', '.join([k.keyword for k in top_declined])}"
                    ]

                    causes.append(RootCause(
                        category=RootCauseCategory.KEYWORD_RANKING,
                        description=f"核心关键词排名普遍下滑，影响自然搜索流量",
                        confidence=RootCauseConfidence.HIGH if len(ranking_data.declined) > 5 else RootCauseConfidence.MEDIUM,
                        evidence=evidence,
                        impact_score=min(1.0, len(ranking_data.declined) / 10.0),
                        contributing_factors=[
                            {"keyword": k.keyword, "current": k.current_position, "previous": k.previous_position}
                            for k in top_declined
                        ],
                        recommended_actions=[
                            "检查下降关键词对应页面的内容质量",
                            "分析竞品排名上升的原因",
                            "考虑更新优化相关页面内容",
                            "检查是否有 Google 算法更新影响"
                        ]
                    ))

            # 分析新掉出排名的关键词
            if ranking_data.dropped:
                causes.append(RootCause(
                    category=RootCauseCategory.KEYWORD_RANKING,
                    description=f"{len(ranking_data.dropped)}个关键词掉出前 30 名",
                    confidence=RootCauseConfidence.MEDIUM,
                    evidence=[f"掉出关键词：{', '.join([k.keyword for k in ranking_data.dropped[:5]])}"],
                    impact_score=min(1.0, len(ranking_data.dropped) / 5.0),
                    contributing_factors=[
                        {"keyword": k.keyword, "last_position": k.current_position}
                        for k in ranking_data.dropped[:5]
                    ],
                    recommended_actions=[
                        "检查页面是否被删除或修改",
                        "分析关键词竞争度变化",
                        "考虑重新优化这些关键词"
                    ]
                ))

        except Exception as e:
            logger.error(f"关键词排名分析失败：{e}")

        return causes

    def _analyze_page_performance(
        self,
        domain: Optional[str],
        check_date: date
    ) -> List[RootCause]:
        """分析页面性能维度的根因"""
        causes = []

        try:
            end_date = check_date
            start_date = end_date - timedelta(days=1)

            perf_data = analytics_service.get_page_performance(start_date, end_date, domain)

            # 分析表现不佳的页面
            if perf_data.underperforming:
                low_seo_pages = [p for p in perf_data.underperforming if p.seo_score < 60]

                if low_seo_pages:
                    causes.append(RootCause(
                        category=RootCauseCategory.PAGE_PERFORMANCE,
                        description=f"{len(low_seo_pages)}个核心页面 SEO 分数偏低",
                        confidence=RootCauseConfidence.MEDIUM,
                        evidence=[
                            f"页面：{p.url}, SEO 分数：{p.seo_score:.1f}, 退出率：{p.exit_rate*100:.1f}%"
                            for p in low_seo_pages[:3]
                        ],
                        impact_score=min(1.0, len(low_seo_pages) / 5.0),
                        contributing_factors=[
                            {"url": p.url, "seo_score": p.seo_score, "exit_rate": p.exit_rate}
                            for p in low_seo_pages[:5]
                        ],
                        recommended_actions=[
                            "优化页面标题和 Meta 描述",
                            "提升内容质量和原创性",
                            "改善页面加载速度",
                            "增加内部链接"
                        ]
                    ))

        except Exception as e:
            logger.error(f"页面性能分析失败：{e}")

        return causes

    def _analyze_device_distribution(
        self,
        domain: Optional[str],
        check_date: date
    ) -> List[RootCause]:
        """分析设备分布维度的根因"""
        causes = []

        try:
            end_date = check_date - timedelta(days=1)
            start_date = end_date - timedelta(days=14)

            historical = analytics_service.get_traffic_overview(
                TrafficOverviewRequest(start_date=start_date, end_date=end_date, domain=domain)
            )
            current = analytics_service.get_traffic_overview(
                TrafficOverviewRequest(start_date=check_date, end_date=check_date, domain=domain)
            )

            # 对比设备分布变化
            for device, current_pct in current.device_distribution.items():
                historical_pct = historical.device_distribution.get(device, 0)
                change = current_pct - historical_pct

                if abs(change) >= 0.1:  # 10% 变化
                    causes.append(RootCause(
                        category=RootCauseCategory.DEVICE_ISSUE,
                        description=f"{device.value}设备流量占比变化{change*100:+.1f}%",
                        confidence=RootCauseConfidence.LOW,
                        evidence=[
                            f"历史占比：{historical_pct*100:.1f}%",
                            f"当前占比：{current_pct*100:.1f}%"
                        ],
                        impact_score=abs(change),
                        contributing_factors=[{
                            "device": device.value,
                            "historical": historical_pct,
                            "current": current_pct
                        }],
                        recommended_actions=[
                            f"检查{device.value}端的用户体验",
                            "确保移动端适配良好",
                            "测试不同设备的页面兼容性"
                        ]
                    ))

        except Exception as e:
            logger.error(f"设备分布分析失败：{e}")

        return causes

    def _analyze_geo_distribution(
        self,
        domain: Optional[str],
        check_date: date
    ) -> List[RootCause]:
        """分析地域分布维度的根因"""
        # 当前简化实现，后续可扩展
        return []

    def _analyze_conversion_funnel(
        self,
        domain: Optional[str],
        check_date: date
    ) -> List[RootCause]:
        """分析转化漏斗维度的根因"""
        # 可结合 funnel_analysis 服务实现
        return []

    def _analyze_traffic_quality(
        self,
        domain: Optional[str],
        check_date: date
    ) -> List[RootCause]:
        """分析流量质量维度的根因"""
        causes = []

        try:
            # 分析跳出率变化
            end_date = check_date - timedelta(days=1)
            start_date = end_date - timedelta(days=14)

            historical = analytics_service.get_traffic_overview(
                TrafficOverviewRequest(start_date=start_date, end_date=end_date, domain=domain)
            )
            current = analytics_service.get_traffic_overview(
                TrafficOverviewRequest(start_date=check_date, end_date=check_date, domain=domain)
            )

            historical_bounce = historical.total.bounce_rate
            current_bounce = current.total.bounce_rate
            change = current_bounce - historical_bounce

            if change > 0.1:  # 跳出率上升 10%
                causes.append(RootCause(
                    category=RootCauseCategory.CONTENT_ISSUE,
                    description=f"跳出率显著上升{change*100:.1f}%, 流量质量可能下降",
                    confidence=RootCauseConfidence.MEDIUM,
                    evidence=[
                        f"历史跳出率：{historical_bounce*100:.1f}%",
                        f"当前跳出率：{current_bounce*100:.1f}%"
                    ],
                    impact_score=min(1.0, change / 0.3),
                    contributing_factors=[{
                        "metric": "bounce_rate",
                        "historical": historical_bounce,
                        "current": current_bounce,
                        "change": change
                    }],
                    recommended_actions=[
                        "检查流量来源质量，是否存在低质引流",
                        "优化落地页内容与用户意图匹配度",
                        "改善页面加载速度",
                        "增加页面互动元素提升参与度"
                    ]
                ))

        except Exception as e:
            logger.error(f"流量质量分析失败：{e}")

        return causes

    def _analyze_seo_factors(
        self,
        domain: Optional[str],
        check_date: date
    ) -> List[RootCause]:
        """分析 SEO 因素维度的根因"""
        # 可扩展 SEO 专项分析
        return []

    def _get_source_name(self, source: str) -> str:
        """获取流量来源的中文名称"""
        names = {
            "organic_search": "自然搜索",
            "direct": "直接访问",
            "social_media": "社交媒体",
            "referral": "引荐流量",
            "paid_ad": "付费广告",
            "email": "邮件营销",
            "other": "其他"
        }
        return names.get(source, source)

    def _get_source_actions(self, source: str, change: float) -> List[str]:
        """获取针对流量来源变化的建议行动"""
        actions = {
            "organic_search": [
                "检查 Google Search Console 是否有异常通知",
                "分析下降关键词的排名变化",
                "检查网站是否有技术问题影响抓取"
            ],
            "direct": [
                "检查品牌曝光度是否下降",
                "确认直接访问 URL 是否可正常访问"
            ],
            "social_media": [
                "检查社交媒体账号是否有异常",
                "分析各社交平台流量变化",
                "回顾近期社交媒体发布内容"
            ],
            "referral": [
                "检查主要引荐来源是否失效",
                "确认外部链接是否仍然有效"
            ],
            "paid_ad": [
                "检查广告账户状态",
                "确认广告预算是否充足",
                "分析广告 ROI 变化"
            ],
            "email": [
                "检查邮件发送成功率",
                "分析邮件打开率和点击率"
            ]
        }
        base_actions = actions.get(source, ["分析该渠道的具体变化原因"])

        if change < 0:
            return ["调查" + self._get_source_name(source) + "下降的原因"] + base_actions
        else:
            return ["总结" + self._get_source_name(source) + "增长的经验"] + base_actions

    def _generate_analysis_summary(
        self,
        anomaly: AnomalyDetectionResult,
        root_causes: List[RootCause]
    ) -> str:
        """生成分析摘要"""
        if not root_causes:
            return f"未找到明确的异常根因，建议持续监控{anomaly.metric_name}指标变化"

        primary = root_causes[0]
        summary_parts = [
            f"检测到{anomaly.metric_name}异常：{anomaly.description}",
            f"\n\n主要根因：{primary.description}",
            f"\n置信度：{primary.confidence.value}",
            f"\n\n共发现{len(root_causes)}个潜在影响因素"
        ]

        if len(root_causes) > 1:
            summary_parts.append(f"\n其他因素：")
            for i, cause in enumerate(root_causes[1:4], 1):
                summary_parts.append(f"\n  {i}. {cause.description} (影响度：{cause.impact_score:.2f})")

        return "".join(summary_parts)


# 全局服务实例
root_cause_analysis_service = RootCauseAnalysisService()
