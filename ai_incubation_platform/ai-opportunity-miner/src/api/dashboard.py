"""
可视化仪表板 API
提供仪表板所需的数据聚合和图表数据接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from crawler.enterprise_crawler import enterprise_crawler
from crawler.patent_crawler import patent_crawler
from crawler.social_media_crawler import social_media_crawler
from crawler.news_crawler import news_crawler
from crawler.report_crawler import report_crawler

router = APIRouter(prefix="/api/dashboard", tags=["可视化仪表板"])


# === 仪表板概览数据 ===

@router.get("/overview", response_model=Dict)
async def get_dashboard_overview():
    """获取仪表板概览数据"""
    # 获取各类数据源的统计信息
    try:
        # 模拟统计数据（实际应该从数据库聚合）
        now = datetime.now()
        last_7_days = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)][::-1]

        overview = {
            "summary": {
                "total_opportunities": 156,
                "new_this_week": 23,
                "validated_opportunities": 45,
                "high_confidence_count": 38,
                "total_trends_tracked": 89,
                "active_alerts": 12
            },
            "data_sources": {
                "news": {"count": 1250, "status": "active"},
                "enterprise": {"count": 580, "status": "active"},
                "patent": {"count": 320, "status": "active"},
                "social_media": {"count": 2100, "status": "active"},
                "industry_reports": {"count": 95, "status": "active"}
            },
            "trend_chart": {
                "labels": last_7_days,
                "datasets": {
                    "opportunities_discovered": [12, 18, 15, 22, 19, 25, 23],
                    "news_analyzed": [150, 180, 160, 200, 190, 220, 210],
                    "social_mentions": [800, 950, 880, 1100, 1050, 1200, 1150]
                }
            }
        }
        return {"success": True, "data": overview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === 市场地图数据 ===

@router.get("/market-map", response_model=Dict)
async def get_market_map(
    industry: str = Query("科技", description="行业类别")
):
    """获取市场地图数据 - 用于可视化竞争格局"""
    try:
        # 获取企业数据
        companies = await enterprise_crawler.search_company(industry, limit=50)

        # 构建市场地图数据
        market_map = {
            "industry": industry,
            "total_companies": len(companies),
            "segments": {
                "领导者": [],
                "挑战者": [],
                "追随者": [],
                "补缺者": []
            },
            "companies": []
        }

        # 按注册资本和成立时间分类
        for company in companies:
            # 解析注册资本
            capital_str = company.get("registered_capital", "0 万")
            try:
                capital = float(''.join(filter(str.isdigit, capital_str)))
            except:
                capital = 0

            # 计算成立年限
            establish_date = company.get("establish_date", "")
            try:
                years = (datetime.now() - datetime.strptime(establish_date, "%Y-%m-%d")).days // 365
            except:
                years = 0

            company_data = {
                "id": company["company_id"],
                "name": company["name"],
                "capital": capital,
                "years": years,
                "status": company.get("status", "存续"),
                "x": len(market_map["companies"]) % 10,  # 用于可视化的坐标
                "y": len(market_map["companies"]) // 10
            }

            # 按规模和年限分类
            if capital > 1000 and years > 5:
                market_map["segments"]["领导者"].append(company_data)
            elif capital > 500 and years > 3:
                market_map["segments"]["挑战者"].append(company_data)
            elif capital > 200:
                market_map["segments"]["追随者"].append(company_data)
            else:
                market_map["segments"]["补缺者"].append(company_data)

            market_map["companies"].append(company_data)

        # 计算市场集中度
        total_capital = sum(c["capital"] for c in market_map["companies"])
        top3_capital = sum(sorted([c["capital"] for c in market_map["companies"]], reverse=True)[:3])
        market_map["concentration"] = {
            "cr3": round(top3_capital / total_capital * 100, 2) if total_capital > 0 else 0,
            "hhi": calculate_hhi([c["capital"] for c in market_map["companies"]])
        }

        return {"success": True, "data": market_map}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def calculate_hhi(capitals: List[float]) -> float:
    """计算赫芬斯基 - 赫希曼指数 (HHI)"""
    total = sum(capitals)
    if total == 0:
        return 0
    shares = [(c / total) * 100 for c in capitals]
    return round(sum(s ** 2 for s in shares), 2)


# === 趋势图表数据 ===

@router.get("/trend-chart", response_model=Dict)
async def get_trend_chart(
    keyword: str = Query(..., description="关键词"),
    days: int = Query(30, description="天数", ge=1, le=365)
):
    """获取趋势图表数据"""
    try:
        now = datetime.now()
        dates = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)][::-1]

        # 生成模拟趋势数据
        chart_data = {
            "keyword": keyword,
            "period_days": days,
            "labels": dates,
            "datasets": {
                "news_count": [],
                "social_mentions": [],
                "patent_count": [],
                "enterprise_count": []
            },
            "trend_indicators": {
                "direction": "up",
                "momentum": "strong",
                "growth_rate": 0
            }
        }

        # 生成趋势数据（实际应该从数据库查询）
        base_news = 10
        base_social = 50
        for i in range(days):
            # 添加一些波动和趋势
            trend_factor = 1 + (i / days) * 0.5  # 上升趋势
            noise = 0.8 + (i % 5) * 0.1

            chart_data["datasets"]["news_count"].append(int(base_news * trend_factor * noise))
            chart_data["datasets"]["social_mentions"].append(int(base_social * trend_factor * noise))
            chart_data["datasets"]["patent_count"].append(int(5 * trend_factor))
            chart_data["datasets"]["enterprise_count"].append(int(3 * trend_factor))

        # 计算趋势指标
        recent_avg = sum(chart_data["datasets"]["news_count"][-7:]) / 7
        previous_avg = sum(chart_data["datasets"]["news_count"][-14:-7]) / 7
        growth_rate = (recent_avg - previous_avg) / previous_avg if previous_avg > 0 else 0

        chart_data["trend_indicators"]["growth_rate"] = round(growth_rate * 100, 2)
        chart_data["trend_indicators"]["direction"] = "up" if growth_rate > 0.1 else ("down" if growth_rate < -0.1 else "stable")
        chart_data["trend_indicators"]["momentum"] = "strong" if abs(growth_rate) > 0.3 else ("moderate" if abs(growth_rate) > 0.1 else "weak")

        return {"success": True, "data": chart_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === 事件时间线数据 ===

@router.get("/event-timeline", response_model=Dict)
async def get_event_timeline(
    days: int = Query(30, description="天数", ge=1, le=90),
    event_type: Optional[str] = Query(None, description="事件类型过滤")
):
    """获取事件时间线数据"""
    try:
        now = datetime.now()
        events = []

        # 模拟生成各类事件
        event_templates = [
            {"type": "financing", "title": "{company} 完成{amount}融资", "icon": "💰"},
            {"type": "product", "title": "{company} 发布新产品{product}", "icon": "🚀"},
            {"type": "partnership", "title": "{company1} 与{company2} 达成战略合作", "icon": "🤝"},
            {"type": "executive", "title": "{company} 任命新 CEO", "icon": "👔"},
            {"type": "patent", "title": "{company} 获得重要专利授权", "icon": "📜"},
            {"type": "market", "title": "{company} 进入新市场", "icon": "🌍"},
            {"type": "acquisition", "title": "{company1} 收购{company2}", "icon": "🔄"},
            {"type": "ipo", "title": "{company} 启动 IPO 进程", "icon": "📈"},
        ]

        company_names = ["未来科技", "智能创新", "数据云图", "AI 前沿", "数字先锋"]

        for i in range(min(days, 50)):  # 最多生成 50 个事件
            event_template = event_templates[i % len(event_templates)]
            event_date = now - timedelta(days=i * 0.5)

            event = {
                "id": f"event_{i}",
                "type": event_template["type"],
                "title": event_template["title"].format(
                    company=company_names[i % len(company_names)],
                    amount=f"{(i % 10 + 1) * 1000}万",
                    product=f"产品{i+1}",
                    company1=company_names[i % len(company_names)],
                    company2=company_names[(i+1) % len(company_names)]
                ),
                "date": event_date.strftime("%Y-%m-%d"),
                "timestamp": event_date.isoformat(),
                "icon": event_template["icon"],
                "source": ["news", "enterprise", "social_media"][i % 3],
                "importance": (i % 5) + 1  # 1-5 的重要性评分
            }
            events.append(event)

        # 按日期排序
        events.sort(key=lambda x: x["timestamp"], reverse=True)

        return {"success": True, "data": {"events": events, "total": len(events)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === 关系图谱数据 ===

@router.get("/knowledge-graph", response_model=Dict)
async def get_knowledge_graph(
    keyword: str = Query(..., description="搜索关键词"),
    depth: int = Query(1, description="关联深度", ge=1, le=3)
):
    """获取知识图谱数据 - 用于关系网络可视化"""
    try:
        # 获取相关企业
        companies = await enterprise_crawler.search_company(keyword, limit=20)

        graph_data = {
            "keyword": keyword,
            "depth": depth,
            "nodes": [],
            "links": [],
            "categories": [
                {"name": "公司"},
                {"name": "人物"},
                {"name": "产品"},
                {"name": "投资事件"}
            ]
        }

        # 添加中心节点（关键词）
        graph_data["nodes"].append({
            "id": f"keyword_{keyword}",
            "name": keyword,
            "category": 0,
            "size": 50,
            "symbolSize": 50
        })

        # 添加公司节点
        for i, company in enumerate(companies[:10]):
            company_node = {
                "id": company["company_id"],
                "name": company["name"],
                "category": 0,
                "size": 30,
                "symbolSize": 30,
                "value": company.get("registered_capital", "")
            }
            graph_data["nodes"].append(company_node)

            # 添加到关键词的链接
            graph_data["links"].append({
                "source": f"keyword_{keyword}",
                "target": company["company_id"],
                "value": "相关",
                "label": {"formatter": "相关"}
            })

            # 添加法人代表节点
            if company.get("legal_representative"):
                person_id = f"person_{company['legal_representative']}_{i}"
                graph_data["nodes"].append({
                    "id": person_id,
                    "name": company["legal_representative"],
                    "category": 1,
                    "size": 20,
                    "symbolSize": 20
                })
                graph_data["links"].append({
                    "source": company["company_id"],
                    "target": person_id,
                    "value": "法人代表",
                    "label": {"formatter": "法人代表"}
                })

        return {"success": True, "data": graph_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === 词云数据 ===

@router.get("/word-cloud", response_model=Dict)
async def get_word_cloud(
    industry: str = Query("科技", description="行业"),
    days: int = Query(30, description="天数", ge=1, le=90)
):
    """获取词云数据"""
    try:
        # 模拟词云数据
        word_cloud = {
            "industry": industry,
            "period_days": days,
            "words": [
                {"name": "人工智能", "value": 95},
                {"name": "大模型", "value": 88},
                {"name": "机器学习", "value": 82},
                {"name": "数字化转型", "value": 76},
                {"name": "云计算", "value": 72},
                {"name": "物联网", "value": 68},
                {"name": "区块链", "value": 64},
                {"name": "5G", "value": 60},
                {"name": "边缘计算", "value": 55},
                {"name": "智能制造", "value": 52},
                {"name": "自动驾驶", "value": 48},
                {"name": "元宇宙", "value": 45},
                {"name": "Web3.0", "value": 42},
                {"name": "SaaS", "value": 40},
                {"name": "数据分析", "value": 38},
                {"name": "机器人", "value": 35},
                {"name": "新能源", "value": 32},
                {"name": "生物技术", "value": 30},
                {"name": "量子计算", "value": 28},
                {"name": "网络安全", "value": 25}
            ]
        }
        return {"success": True, "data": word_cloud}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === 仪表板配置 ===

@router.get("/config", response_model=Dict)
async def get_dashboard_config():
    """获取仪表板配置"""
    try:
        config = {
            "refresh_interval": 60,  # 刷新间隔（秒）
            "available_charts": [
                {"id": "trend", "name": "趋势图", "enabled": True},
                {"id": "market_map", "name": "市场地图", "enabled": True},
                {"id": "timeline", "name": "事件时间线", "enabled": True},
                {"id": "graph", "name": "关系图谱", "enabled": True},
                {"id": "word_cloud", "name": "词云", "enabled": True}
            ],
            "default_layout": [
                {"chart": "overview", "position": "top", "size": "full"},
                {"chart": "trend", "position": "middle", "size": "half"},
                {"chart": "market_map", "position": "middle", "size": "half"},
                {"chart": "timeline", "position": "bottom", "size": "full"},
                {"chart": "graph", "position": "bottom", "size": "full"}
            ]
        }
        return {"success": True, "data": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
