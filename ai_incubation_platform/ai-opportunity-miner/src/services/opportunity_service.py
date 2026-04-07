"""
商机挖掘服务 - 支持数据库持久化
"""
from typing import List, Optional, Dict
from datetime import datetime
import uuid
import logging

from models.opportunity import (
    BusinessOpportunity, MarketTrend, OpportunityType, OpportunityStatus,
    RiskLabel, SourceType
)
from models.db_models import BusinessOpportunityDB, MarketTrendDB
from config.database import get_db, SessionLocal, init_db
from mining.opportunity_miner import opportunity_miner
from analysis.trend_analyzer import trend_analyzer
from analysis.trend_predictor import trend_predictor
from nlp.event_detector import event_detector
from nlp.graph_builder import graph_builder
from services.alert_engine import alert_engine
from utils.report_exporter import report_exporter
from crawler.news_crawler import news_crawler
from crawler.report_crawler import report_crawler

logger = logging.getLogger(__name__)


class OpportunityMinerService:
    """商机挖掘服务 - 支持数据库持久化"""

    def __init__(self, use_db: bool = True):
        self.use_db = use_db
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        if self.use_db:
            try:
                init_db()
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                self.use_db = False

    def _get_db(self):
        """获取数据库会话"""
        return SessionLocal()

    def _to_domain_opportunity(self, db_opp: BusinessOpportunityDB) -> BusinessOpportunity:
        """将数据库模型转换为领域模型"""
        return BusinessOpportunity(
            id=db_opp.id,
            title=db_opp.title,
            description=db_opp.description,
            type=OpportunityType(db_opp.opportunity_type),
            confidence_score=db_opp.confidence_score,
            potential_value=db_opp.potential_value,
            potential_value_currency=db_opp.potential_value_currency,
            source_type=SourceType(db_opp.source_type),
            source_name=db_opp.source_name,
            source_url=db_opp.source_url,
            source_publish_date=db_opp.source_publish_date,
            risk_labels=[RiskLabel(l) for l in (db_opp.risk_labels or [])],
            risk_score=db_opp.risk_score,
            risk_description=db_opp.risk_description,
            validation_steps=db_opp.validation_steps or [],
            validation_status=db_opp.validation_status,
            validation_notes=db_opp.validation_notes,
            related_entities=db_opp.related_entities or [],
            tags=db_opp.tags or [],
            status=OpportunityStatus(db_opp.status),
            created_at=db_opp.created_at,
            updated_at=db_opp.updated_at,
        )

    def _to_domain_trend(self, db_trend: MarketTrendDB) -> MarketTrend:
        """将数据库模型转换为领域模型"""
        return MarketTrend(
            id=db_trend.id,
            keyword=db_trend.keyword,
            trend_score=db_trend.trend_score,
            growth_rate=db_trend.growth_rate,
            related_keywords=db_trend.related_keywords or [],
            data_points=db_trend.data_points or [],
            extra=db_trend.extra or {},
            created_at=db_trend.created_at,
        )

    def add_opportunity(self, opp: BusinessOpportunity) -> BusinessOpportunity:
        """添加商机"""
        if self.use_db:
            db = self._get_db()
            try:
                db_opp = BusinessOpportunityDB.from_dict({
                    "id": opp.id,
                    "title": opp.title,
                    "description": opp.description,
                    "type": opp.type.value,
                    "status": opp.status.value,
                    "confidence_score": opp.confidence_score,
                    "potential_value": opp.potential_value,
                    "potential_value_currency": opp.potential_value_currency,
                    "source_type": opp.source_type.value,
                    "source_name": opp.source_name,
                    "source_url": opp.source_url,
                    "source_publish_date": opp.source_publish_date,
                    "risk_labels": [l.value for l in opp.risk_labels],
                    "risk_score": opp.risk_score,
                    "risk_description": opp.risk_description,
                    "validation_steps": opp.validation_steps,
                    "validation_status": opp.validation_status,
                    "validation_notes": opp.validation_notes,
                    "related_entities": opp.related_entities,
                    "tags": opp.tags,
                })
                db.add(db_opp)
                db.commit()
                db.refresh(db_opp)
                logger.info(f"Opportunity added to database: {opp.id}")
                return opp
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to add opportunity to database: {e}")
                raise e
            finally:
                db.close()
        else:
            # 内存模式（向后兼容）
            self._opportunities[opp.id] = opp
            return opp

    def list_opportunities(self, status: Optional[OpportunityStatus] = None) -> List[BusinessOpportunity]:
        """获取商机列表"""
        if self.use_db:
            db = self._get_db()
            try:
                query = db.query(BusinessOpportunityDB)
                if status:
                    query = query.filter(BusinessOpportunityDB.status == status.value)
                db_opps = query.order_by(BusinessOpportunityDB.created_at.desc()).all()
                return [self._to_domain_opportunity(opp) for opp in db_opps]
            finally:
                db.close()
        else:
            # 内存模式（向后兼容）
            if status:
                return [o for o in self._opportunities.values() if o.status == status]
            return list(self._opportunities.values())

    def get_opportunity(self, opp_id: str) -> Optional[BusinessOpportunity]:
        """获取商机详情"""
        if self.use_db:
            db = self._get_db()
            try:
                db_opp = db.query(BusinessOpportunityDB).filter(BusinessOpportunityDB.id == opp_id).first()
                if db_opp:
                    return self._to_domain_opportunity(db_opp)
                return None
            finally:
                db.close()
        else:
            # 内存模式（向后兼容）
            return self._opportunities.get(opp_id)

    def update_opportunity(self, opp_id: str, update_data: dict) -> Optional[BusinessOpportunity]:
        """更新商机信息"""
        if self.use_db:
            db = self._get_db()
            try:
                db_opp = db.query(BusinessOpportunityDB).filter(BusinessOpportunityDB.id == opp_id).first()
                if not db_opp:
                    return None

                for key, value in update_data.items():
                    if key == "type":
                        setattr(db_opp, "opportunity_type", value.value if hasattr(value, 'value') else value)
                    elif key == "status":
                        setattr(db_opp, key, value.value if hasattr(value, 'value') else value)
                    elif key == "source_type":
                        setattr(db_opp, key, value.value if hasattr(value, 'value') else value)
                    elif key == "risk_labels":
                        setattr(db_opp, key, [l.value if hasattr(l, 'value') else l for l in value])
                    else:
                        setattr(db_opp, key, value)

                db_opp.updated_at = datetime.now()
                db.commit()
                db.refresh(db_opp)
                return self._to_domain_opportunity(db_opp)
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to update opportunity: {e}")
                raise e
            finally:
                db.close()
        else:
            # 内存模式（向后兼容）
            opp = self._opportunities.get(opp_id)
            if opp:
                for key, value in update_data.items():
                    setattr(opp, key, value)
                opp.updated_at = datetime.now()
                return opp
            return None

    def delete_opportunity(self, opp_id: str) -> bool:
        """删除商机"""
        if self.use_db:
            db = self._get_db()
            try:
                db_opp = db.query(BusinessOpportunityDB).filter(BusinessOpportunityDB.id == opp_id).first()
                if db_opp:
                    db.delete(db_opp)
                    db.commit()
                    logger.info(f"Opportunity deleted: {opp_id}")
                    return True
                return False
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to delete opportunity: {e}")
                raise e
            finally:
                db.close()
        else:
            # 内存模式（向后兼容）
            if opp_id in self._opportunities:
                del self._opportunities[opp_id]
                return True
            return False

    def add_trend(self, trend: MarketTrend) -> MarketTrend:
        """添加趋势"""
        if self.use_db:
            db = self._get_db()
            try:
                db_trend = MarketTrendDB.from_dict({
                    "id": trend.id,
                    "keyword": trend.keyword,
                    "trend_score": trend.trend_score,
                    "growth_rate": trend.growth_rate,
                    "related_keywords": trend.related_keywords,
                    "data_points": trend.data_points,
                    "extra": trend.extra,
                })
                db.add(db_trend)
                db.commit()
                db.refresh(db_trend)
                return trend
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to add trend to database: {e}")
                raise e
            finally:
                db.close()
        else:
            # 内存模式（向后兼容）
            self._trends[trend.keyword] = trend
            return trend

    def list_trends(self, min_score: float = 0) -> List[MarketTrend]:
        """获取趋势列表"""
        if self.use_db:
            db = self._get_db()
            try:
                db_trends = db.query(MarketTrendDB).filter(MarketTrendDB.trend_score >= min_score).all()
                return [self._to_domain_trend(trend) for trend in db_trends]
            finally:
                db.close()
        else:
            # 内存模式（向后兼容）
            return [t for t in self._trends.values() if t.trend_score >= min_score]

    def discover_opportunities(self) -> List[BusinessOpportunity]:
        """发现新商机（初始化演示数据）"""
        # 检查是否已有数据，避免重复添加
        existing = self.list_opportunities()
        if existing:
            logger.info(f"Skipping demo data initialization, {len(existing)} opportunities exist")
            return existing

        sample_opps = [
            BusinessOpportunity(
                id=str(uuid.uuid4()),
                title="新能源储能市场爆发式增长",
                description="随着可再生能源装机量持续提升，电网侧和用户侧储能需求呈现爆发式增长，预计未来 3 年复合增长率超过 40%",
                type=OpportunityType.MARKET,
                confidence_score=0.89,
                potential_value=12000000,
                potential_value_currency="CNY",
                source_type=SourceType.INDUSTRY_REPORT,
                source_name="中国能源研究会 2026 年储能行业白皮书",
                source_url="https://example.com/reports/energy-storage-2026",
                source_publish_date=datetime(2026, 3, 15),
                risk_labels=[RiskLabel.MEDIUM_RISK, RiskLabel.COMPETITIVE],
                risk_score=0.35,
                risk_description="市场竞争激烈，头部企业已占据 60% 以上市场份额",
                validation_steps=[
                    "1. 核实行业报告数据来源的权威性",
                    "2. 调研储能产业链上游核心供应商的产能情况",
                    "3. 访谈 3-5 家储能集成商了解实际订单情况",
                    "4. 分析政策补贴的持续性和落地情况"
                ],
                validation_status="pending",
                related_entities=[
                    {"name": "宁德时代", "type": "company", "relation": "核心供应商"},
                    {"name": "比亚迪", "type": "company", "relation": "核心供应商"},
                    {"name": "国家能源局", "type": "government", "relation": "政策制定方"}
                ],
                tags=["新能源", "储能", "双碳", "电网"],
                status=OpportunityStatus.NEW,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            BusinessOpportunity(
                id=str(uuid.uuid4()),
                title="企业级 AI 应用部署需求激增",
                description="AI 大模型技术成熟推动各行业企业加速 AI 应用落地，企业对 AI 基础设施、定制化模型开发、AI 培训等需求快速上升",
                type=OpportunityType.PRODUCT,
                confidence_score=0.92,
                potential_value=8500000,
                potential_value_currency="CNY",
                source_type=SourceType.RECRUITMENT,
                source_name="各大招聘平台 AI 相关岗位数据分析",
                source_url="https://example.com/analysis/ai-jobs-trend-2026",
                source_publish_date=datetime(2026, 3, 28),
                risk_labels=[RiskLabel.LOW_RISK, RiskLabel.TECHNOLOGICAL],
                risk_score=0.25,
                risk_description="技术迭代快，需要持续跟进最新 AI 技术进展",
                validation_steps=[
                    "1. 提取近 3 个月招聘平台 AI 相关岗位的增长数据",
                    "2. 分析不同行业 AI 招聘需求的结构差异",
                    "3. 访谈 5 家正在进行 AI 转型的企业 CIO 了解实际需求",
                    "4. 验证 AI 应用部署的平均客单价和付费意愿"
                ],
                validation_status="pending",
                related_entities=[
                    {"name": "OpenAI", "type": "company", "relation": "技术提供商"},
                    {"name": "百度文心一言", "type": "product", "relation": "技术提供商"},
                    {"name": "阿里通义千问", "type": "product", "relation": "技术提供商"}
                ],
                tags=["AI", "大模型", "企业服务", "数字化转型"],
                status=OpportunityStatus.NEW,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            BusinessOpportunity(
                id=str(uuid.uuid4()),
                title="银发经济健康管理市场机遇",
                description="人口老龄化加速，60 岁以上人口占比超过 20%，老年人对健康管理、慢病监测、居家养老服务的需求持续增长",
                type=OpportunityType.MARKET,
                confidence_score=0.87,
                potential_value=15000000,
                potential_value_currency="CNY",
                source_type=SourceType.GOVERNMENT_DATA,
                source_name="国家统计局第七次人口普查及相关政策文件",
                source_url="https://example.gov.cn/data/aging-population-2026",
                source_publish_date=datetime(2026, 2, 20),
                risk_labels=[RiskLabel.MEDIUM_RISK, RiskLabel.REGULATORY],
                risk_score=0.4,
                risk_description="医疗健康行业监管严格，相关产品需要获得资质审批",
                validation_steps=[
                    "1. 核实老龄人口相关统计数据的准确性",
                    "2. 调研现有健康管理产品的市场渗透率",
                    "3. 分析医保政策对相关产品的覆盖情况",
                    "4. 访谈老年人及家属了解实际消费意愿"
                ],
                validation_status="pending",
                related_entities=[
                    {"name": "国家卫健委", "type": "government", "relation": "监管机构"},
                    {"name": "医保局", "type": "government", "relation": "政策制定方"},
                    {"name": "平安好医生", "type": "company", "relation": "现有参与者"}
                ],
                tags=["银发经济", "健康管理", "养老", "医疗"],
                status=OpportunityStatus.NEW,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

        for opp in sample_opps:
            self.add_opportunity(opp)

        # 初始化趋势数据
        self._init_demo_trends()

        logger.info(f"Initialized {len(sample_opps)} demo opportunities")
        return sample_opps

    def _init_demo_trends(self):
        """初始化演示趋势数据"""
        demo_trends = [
            MarketTrend(
                id=str(uuid.uuid4()),
                keyword="储能技术",
                trend_score=0.95,
                growth_rate=0.45,
                related_keywords=["新能源", "锂电池", "电网调度"],
                data_points=[{"month": "2026-01", "value": 100}, {"month": "2026-02", "value": 132}, {"month": "2026-03", "value": 178}]
            ),
            MarketTrend(
                id=str(uuid.uuid4()),
                keyword="AI 大模型",
                trend_score=0.98,
                growth_rate=0.68,
                related_keywords=["生成式 AI", "多模态", "企业应用"],
                data_points=[{"month": "2026-01", "value": 100}, {"month": "2026-02", "value": 156}, {"month": "2026-03", "value": 245}]
            ),
            MarketTrend(
                id=str(uuid.uuid4()),
                keyword="银发经济",
                trend_score=0.88,
                growth_rate=0.32,
                related_keywords=["养老", "健康管理", "适老化改造"],
                data_points=[{"month": "2026-01", "value": 100}, {"month": "2026-02", "value": 122}, {"month": "2026-03", "value": 148}]
            )
        ]
        for trend in demo_trends:
            self.add_trend(trend)

    async def discover_opportunities_from_keywords(self, keywords: List[str], days: int = 30) -> List[BusinessOpportunity]:
        """从关键词发现新商机"""
        opportunities = await opportunity_miner.discover_from_keywords(keywords, days)
        for opp in opportunities:
            self.add_opportunity(opp)

        # 增强：构建知识图谱并触发预警
        await self._process_events_and_graph(keywords, days)

        return opportunities

    async def _process_events_and_graph(self, keywords: List[str], days: int = 30):
        """处理事件检测、图谱构建和预警"""
        try:
            # 获取新闻数据
            news_articles = await news_crawler.fetch_news(keywords, days)

            # 检测事件
            events = event_detector.detect_from_articles(news_articles)

            # 触发预警
            if events:
                alerts = alert_engine.process_events(events)
                if alerts:
                    logger.info(f"Triggered {len(alerts)} alerts from {len(events)} events")

            # 构建图谱
            if news_articles:
                graph_result = graph_builder.build_from_articles(news_articles)
                logger.info(f"Built graph: {graph_result['total_entities']} entities, {graph_result['total_relations']} relations")
        except Exception as e:
            logger.error(f"Failed to process events and graph: {e}")

    async def discover_opportunities_by_industry(self, industry: str, days: int = 60) -> List[BusinessOpportunity]:
        """按行业发现新商机"""
        opportunities = await opportunity_miner.discover_by_industry(industry, days)
        for opp in opportunities:
            self.add_opportunity(opp)
        return opportunities

    async def generate_trend_analysis(self, keyword: str, days: int = 30) -> MarketTrend:
        """生成趋势分析报告"""
        # 获取相关数据
        news_articles = await news_crawler.fetch_news([keyword], days)
        industry_reports = await report_crawler.fetch_reports([keyword])

        # 生成趋势分析
        trend = await trend_analyzer.generate_trend_report(keyword, news_articles, industry_reports)
        self.add_trend(trend)
        return trend

    async def analyze_competition(self, industry: str, days: int = 60) -> Dict:
        """竞争格局分析"""
        news_articles = await news_crawler.fetch_industry_news(industry, days)
        industry_reports = await report_crawler.fetch_industry_reports(industry)
        return await trend_analyzer.analyze_competitive_landscape(industry, news_articles, industry_reports)

    def export_opportunity_report(self, opp_id: str, format: str = "markdown") -> Dict:
        """导出商机报告"""
        opp = self.get_opportunity(opp_id)
        if not opp:
            return {"success": False, "message": "Opportunity not found"}

        try:
            if format.lower() == "pdf":
                file_path = report_exporter.export_opportunity_pdf(opp)
                file_type = "application/pdf"
            else:
                md_content = report_exporter.export_opportunity_markdown(opp)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"opportunity_{opp.id}_{timestamp}.md"
                file_path = report_exporter.save_markdown(md_content, filename)
                file_type = "text/markdown"

            return {
                "success": True,
                "file_path": str(file_path),
                "file_type": file_type,
                "file_size": len(md_content) if format.lower() != "pdf" else 0
            }
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {"success": False, "message": f"Export failed: {str(e)}"}

    def export_batch_report(self, opp_ids: List[str] = None, format: str = "markdown") -> Dict:
        """批量导出商机报告"""
        if opp_ids:
            opportunities = [self.get_opportunity(opp_id) for opp_id in opp_ids]
            opportunities = [opp for opp in opportunities if opp]
        else:
            opportunities = self.list_opportunities()

        if not opportunities:
            return {"success": False, "message": "No opportunities found"}

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            title = f"商机汇总报告_{timestamp}"

            if format.lower() == "pdf":
                md_content = report_exporter.export_batch_opportunities_markdown(opportunities, title)
                md_path = report_exporter.save_markdown(md_content, f"{title}.md")
                file_path = md_path
                file_type = "text/markdown"
            else:
                md_content = report_exporter.export_batch_opportunities_markdown(opportunities, title)
                file_path = report_exporter.save_markdown(md_content, title)
                file_type = "text/markdown"

            return {
                "success": True,
                "file_path": str(file_path),
                "file_type": file_type,
                "file_size": len(md_content),
                "opportunity_count": len(opportunities),
            }
        except Exception as e:
            logger.error(f"Batch export failed: {e}")
            return {"success": False, "message": f"Export failed: {str(e)}"}

    def export_trend_report(self, min_score: float = 0, format: str = "markdown") -> Dict:
        """导出趋势报告"""
        trends = self.list_trends(min_score)
        if not trends:
            return {"success": False, "message": "No trends found"}

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            title = f"市场趋势分析报告_{timestamp}"

            md_content = report_exporter.export_trend_report_markdown(trends, title)
            file_path = report_exporter.save_markdown(md_content, title)

            return {
                "success": True,
                "file_path": str(file_path),
                "file_type": "text/markdown",
                "file_size": len(md_content),
                "trend_count": len(trends),
            }
        except Exception as e:
            logger.error(f"Trend export failed: {e}")
            return {"success": False, "message": f"Export failed: {str(e)}"}

    async def get_news_data(self, keywords: List[str], days: int = 7) -> Dict:
        """获取新闻数据"""
        articles = await news_crawler.fetch_news(keywords, days)
        return {
            "count": len(articles),
            "articles": articles
        }

    async def get_industry_reports(self, keywords: List[str]) -> Dict:
        """获取行业报告数据"""
        reports = await report_crawler.fetch_reports(keywords)
        return {
            "count": len(reports),
            "reports": reports
        }


# 全局服务实例
opportunity_service = OpportunityMinerService(use_db=True)
