"""
商业情报 API
提供事件检测、知识图谱、预警系统等功能
参考 CB Insights 的 API 设计
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import sys
import os

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.event_detector import event_detector, BusinessEvent, EventType, EventSeverity
from nlp.graph_builder import graph_builder, KnowledgeGraph, EntityType, RelationType
from services.alert_engine import alert_engine, AlertRule, AlertStatus, AlertPriority
from analysis.trend_predictor import trend_predictor, technology_adoption_curve
from models.graph import GraphEntity, GraphRelation
from crawler.news_crawler import news_crawler
from crawler.report_crawler import report_crawler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


# ============================================================
# 事件检测 API
# ============================================================

@router.post("/events/detect")
async def detect_events(
    text: str = Body(..., embed=True, description="要分析的文本"),
    source: Optional[str] = Body(None, description="来源"),
    source_url: Optional[str] = Body(None, description="来源 URL")
) -> Dict[str, Any]:
    """
    从文本中检测商业事件

    - **text**: 要分析的文本内容
    - **source**: 可选，来源名称
    - **source_url**: 可选，来源 URL

    返回检测到的事件列表，包括融资、并购、IPO、产品发布等
    """
    metadata = {}
    if source:
        metadata["source"] = source
    if source_url:
        metadata["source_url"] = source_url

    events = event_detector.detect_events(text, metadata)

    return {
        "success": True,
        "count": len(events),
        "events": [e.to_dict() for e in events]
    }


@router.post("/events/detect/batch")
async def detect_events_batch(
    articles: List[Dict] = Body(..., description="文章列表，每项包含 title, content, source 等字段")
) -> Dict[str, Any]:
    """
    批量检测事件

    从多篇文章中检测事件，自动去重
    """
    events = event_detector.detect_from_articles(articles)

    return {
        "success": True,
        "count": len(events),
        "events": [e.to_dict() for e in events],
        "statistics": event_detector.get_event_statistics(events)
    }


@router.get("/events/types")
async def get_event_types() -> Dict[str, Any]:
    """获取支持的事件类型列表"""
    return {
        "success": True,
        "event_types": [
            {
                "value": et.value,
                "name": et.name,
                "description": _get_event_type_description(et.value)
            }
            for et in EventType
        ]
    }


def _get_event_type_description(event_type: str) -> str:
    """获取事件类型描述"""
    descriptions = {
        "funding": "融资事件 - 企业获得投资",
        "investment": "投资事件 - 对外投资",
        "ipo": "IPO/上市 - 企业首次公开募股",
        "acquisition": "并购/收购 - 企业被收购或收购其他企业",
        "product_launch": "产品发布 - 新产品/服务上线",
        "technology_breakthrough": "技术突破 - 重大技术进展",
        "patent": "专利 - 专利申请或授权",
        "partnership": "战略合作 - 企业间合作",
        "expansion": "业务扩张 - 新建工厂、基地等",
        "layoff": "裁员 - 人员优化/缩减",
        "bankruptcy": "破产 - 企业破产/清算",
        "executive_change": "高管变动 - CEO/董事长等变更",
        "new_hire": "重要招聘 - 关键人才引进",
        "policy_change": "政策变化 - 行业政策出台",
        "regulatory_action": "监管行动 - 监管处罚/调查",
        "market_entry": "进入新市场",
        "price_change": "价格调整"
    }
    return descriptions.get(event_type, "")


# ============================================================
# 知识图谱 API
# ============================================================

@router.post("/graph/build")
async def build_graph(
    articles: List[Dict] = Body(..., description="文章列表，用于构建图谱")
) -> Dict[str, Any]:
    """
    从文章构建知识图谱

    自动抽取实体（公司、人、产品等）和关系（投资、竞争、合作等）
    """
    result = graph_builder.build_from_articles(articles)

    return {
        "success": True,
        "result": result
    }


@router.get("/graph/summary")
async def get_graph_summary() -> Dict[str, Any]:
    """获取图谱摘要统计"""
    summary = graph_builder.get_graph_summary()
    return {
        "success": True,
        "summary": summary
    }


@router.get("/graph/entity/{entity_id}")
async def get_entity(entity_id: str) -> Dict[str, Any]:
    """获取实体详情"""
    entity = graph_builder.graph.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    relations = graph_builder.graph.get_relations(entity_id)

    return {
        "success": True,
        "entity": entity.to_dict(),
        "relations": relations
    }


@router.get("/graph/company/{company_name}")
async def get_company_profile(company_name: str) -> Dict[str, Any]:
    """
    获取公司档案

    包含公司基本信息、投资方、竞争对手、合作伙伴、产品等
    """
    profile = graph_builder.get_company_profile(company_name)

    if not profile:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "success": True,
        "profile": profile
    }


@router.get("/graph/company/{company_name}/competitors")
async def get_company_competitors(company_name: str, depth: int = Query(2, ge=1, le=3)) -> Dict[str, Any]:
    """
    获取公司竞争对手

    - **depth**: 搜索深度，1=直接竞争对手，2=竞争对手的竞争对手
    """
    competitors = graph_builder.get_competitors(company_name, depth)

    return {
        "success": True,
        "company": company_name,
        "competitors": competitors,
        "count": len(competitors)
    }


@router.get("/graph/company/{company_name}/investments")
async def get_company_investments(company_name: str) -> Dict[str, Any]:
    """获取公司投资链（投资方和被投资公司）"""
    chain = graph_builder.graph.get_investment_chain(company_name)

    if not chain:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "success": True,
        "investment_chain": chain
    }


@router.get("/graph/entities")
async def search_entities(
    entity_type: Optional[str] = Query(None, description="实体类型：company, person, product, investor"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    tags: Optional[List[str]] = Query(None, description="标签过滤")
) -> Dict[str, Any]:
    """搜索实体"""
    et = EntityType(entity_type) if entity_type else None
    entities = graph_builder.graph.find_entities(et, tags)

    # 关键词过滤
    if keyword:
        keyword_lower = keyword.lower()
        entities = [
            e for e in entities
            if keyword_lower in e.name.lower() or
            any(keyword_lower in alias.lower() for alias in e.aliases)
        ]

    return {
        "success": True,
        "entities": [e.to_dict() for e in entities[:50]],
        "count": len(entities)
    }


# ============================================================
# 预警系统 API
# ============================================================

@router.get("/alerts")
async def get_alerts(
    status: Optional[str] = Query(None, description="状态：new, acknowledged, resolved, dismissed"),
    priority: Optional[str] = Query(None, description="优先级：low, medium, high, critical"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制")
) -> Dict[str, Any]:
    """获取预警列表"""
    st = AlertStatus(status) if status else None
    pr = AlertPriority(priority) if priority else None

    alerts = alert_engine.get_alerts(st, pr, limit)

    return {
        "success": True,
        "alerts": alerts,
        "count": len(alerts)
    }


@router.get("/alerts/recent")
async def get_recent_alerts(hours: int = Query(24, ge=1, le=168, description="最近 N 小时")) -> Dict[str, Any]:
    """获取最近的预警"""
    alerts = alert_engine.get_recent_alerts(hours)

    return {
        "success": True,
        "alerts": alerts,
        "hours": hours,
        "count": len(alerts)
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user: str = Body("system", embed=True)) -> Dict[str, Any]:
    """确认预警"""
    if not alert_engine.acknowledge_alert(alert_id, user):
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "success": True,
        "message": f"Alert {alert_id} acknowledged"
    }


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, notes: str = Body("", embed=True)) -> Dict[str, Any]:
    """解决预警"""
    if not alert_engine.resolve_alert(alert_id, notes):
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "success": True,
        "message": f"Alert {alert_id} resolved"
    }


@router.get("/alerts/statistics")
async def get_alert_statistics() -> Dict[str, Any]:
    """获取预警统计"""
    stats = alert_engine.get_statistics()
    return {
        "success": True,
        "statistics": stats
    }


# ============================================================
# 预警规则 API
# ============================================================

@router.get("/alerts/rules")
async def get_alert_rules() -> Dict[str, Any]:
    """获取所有预警规则"""
    rules = [rule.to_dict() for rule in alert_engine.rules.values()]
    return {
        "success": True,
        "rules": rules,
        "count": len(rules)
    }


@router.post("/alerts/rules")
async def create_alert_rule(rule_data: Dict = Body(...)) -> Dict[str, Any]:
    """
    创建自定义预警规则

    请求体示例:
    ```json
    {
        "rule_id": "custom_rule_1",
        "name": "竞争对手融资预警",
        "description": "监测竞争对手的融资事件",
        "event_types": ["funding"],
        "keywords": ["B 轮", "C 轮"],
        "min_severity": "medium",
        "companies": ["公司 A", "公司 B"],
        "notification_channels": ["console"]
    }
    ```
    """
    # 转换事件类型
    event_types = []
    for et_value in rule_data.get("event_types", []):
        try:
            event_types.append(EventType(et_value))
        except ValueError:
            pass

    # 转换严重性
    min_severity = EventSeverity(rule_data.get("min_severity", "low"))

    rule = AlertRule(
        rule_id=rule_data.get("rule_id", f"rule_{len(alert_engine.rules)}"),
        name=rule_data.get("name", "Unnamed Rule"),
        description=rule_data.get("description", ""),
        event_types=event_types,
        keywords=rule_data.get("keywords", []),
        min_severity=min_severity,
        companies=rule_data.get("companies", []),
        min_amount=rule_data.get("min_amount"),
        enabled=rule_data.get("enabled", True),
        notification_channels=rule_data.get("notification_channels", ["console"])
    )

    alert_engine.add_rule(rule)

    return {
        "success": True,
        "rule": rule.to_dict(),
        "message": "Rule created successfully"
    }


@router.delete("/alerts/rules/{rule_id}")
async def delete_alert_rule(rule_id: str) -> Dict[str, Any]:
    """删除预警规则"""
    if rule_id not in alert_engine.rules:
        raise HTTPException(status_code=404, detail="Rule not found")

    alert_engine.remove_rule(rule_id)

    return {
        "success": True,
        "message": f"Rule {rule_id} deleted"
    }


@router.post("/alerts/rules/{rule_id}/toggle")
async def toggle_alert_rule(rule_id: str) -> Dict[str, Any]:
    """启用/禁用预警规则"""
    if rule_id not in alert_engine.rules:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule = alert_engine.rules[rule_id]
    if rule.enabled:
        alert_engine.disable_rule(rule_id)
        action = "disabled"
    else:
        alert_engine.enable_rule(rule_id)
        action = "enabled"

    return {
        "success": True,
        "rule_id": rule_id,
        "action": action
    }


# ============================================================
# 趋势分析增强 API
# ============================================================

@router.post("/trend/analyze")
async def analyze_trend(
    data_points: List[Dict] = Body(..., description="数据点列表，每项包含 month 和 value"),
    keyword: str = Body(..., description="关键词")
) -> Dict[str, Any]:
    """
    深度趋势分析

    包含线性回归、移动平均、拐点检测、增长阶段判断等
    """
    insights = trend_predictor.generate_trend_insights(data_points, keyword)

    return {
        "success": True,
        "keyword": keyword,
        "analysis": insights
    }


@router.post("/trend/market-concentration")
async def analyze_market_concentration(
    market_shares: List[float] = Body(..., description="各公司市场份额列表，以小数表示")
) -> Dict[str, Any]:
    """
    市场集中度分析

    计算 CR3, CR5, HHI 等指标
    """
    result = trend_predictor.calculate_market_concentration(market_shares)

    return {
        "success": True,
        "concentration_analysis": result
    }


@router.post("/trend/adoption-stage")
async def analyze_adoption_stage(
    penetration_rate: float = Body(..., description="市场渗透率，0-1 之间"),
    growth_rate: float = Body(..., description="增长率，0-1 之间")
) -> Dict[str, Any]:
    """
    技术采用阶段分析

    基于创新扩散理论判断当前处于哪个阶段
    """
    stage = technology_adoption_curve.identify_adoption_stage({
        "penetration_rate": penetration_rate,
        "growth_rate": growth_rate
    })

    chasm_analysis = technology_adoption_curve.predict_crossing_chasm(penetration_rate, growth_rate)

    stage_descriptions = {
        "innovators": "创新者阶段 - 技术刚起步，只有少数创新者尝试",
        "early_adopters": "早期采用者阶段 - 开始受到早期采用者关注",
        "early_majority_growth": "早期大众快速增长 - 即将跨越鸿沟，快速增长",
        "early_majority": "早期大众阶段 - 已被主流市场接受",
        "late_majority": "晚期大众阶段 - 市场趋于饱和",
        "laggards": "落后者阶段 - 只有落后者还在采用"
    }

    return {
        "success": True,
        "stage": stage,
        "stage_description": stage_descriptions.get(stage, ""),
        "chasm_analysis": chasm_analysis
    }


@router.post("/trend/keyword-momentum")
async def analyze_keyword_momentum(
    keyword_counts: Dict[str, List[int]] = Body(..., description="关键词计数，键为关键词，值为时间序列计数"),
    window: int = Body(3, description="移动窗口大小")
) -> Dict[str, Any]:
    """
    关键词动量分析

    识别增长最快的关键词
    """
    results = trend_predictor.analyze_keyword_momentum(keyword_counts, window)

    return {
        "success": True,
        "keywords": results,
        "top_growing": results[:10]  # 前 10 个增长最快的
    }


# ============================================================
# 情报简报 API
# ============================================================

@router.get("/briefing/daily")
async def get_daily_briefing(
    days: int = Query(1, ge=1, le=7, description="最近 N 天")
) -> Dict[str, Any]:
    """
    获取每日情报简报

    汇总最近的重要事件、预警、趋势
    """
    cutoff_date = datetime.now() - timedelta(days=days)

    # 获取最近预警
    recent_alerts = alert_engine.get_recent_alerts(hours=days * 24)

    # 获取图谱统计
    graph_summary = graph_builder.get_graph_summary()

    # 按事件类型分组统计
    event_type_counts = {}
    for rule_id, count in alert_engine.get_statistics().get("by_rule", {}).items():
        rule = alert_engine.rules.get(rule_id)
        if rule:
            for et in rule.event_types:
                event_type_counts[et.value] = event_type_counts.get(et.value, 0) + count

    return {
        "success": True,
        "period": {
            "days": days,
            "from": cutoff_date.isoformat(),
            "to": datetime.now().isoformat()
        },
        "summary": {
            "total_alerts": len(recent_alerts),
            "critical_alerts": sum(1 for a in recent_alerts if a["priority"] == "critical"),
            "high_priority_alerts": sum(1 for a in recent_alerts if a["priority"] == "high"),
            "total_entities": graph_summary.get("statistics", {}).get("entity_count", 0),
            "total_relations": graph_summary.get("statistics", {}).get("relation_count", 0)
        },
        "alerts": recent_alerts[:20],  # 最近 20 条预警
        "event_type_breakdown": event_type_counts,
        "generated_at": datetime.now().isoformat()
    }
