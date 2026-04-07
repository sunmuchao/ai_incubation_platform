"""
P0 可视化仪表板增强 API - v1.7

提供 AI 驱动的可视化增强功能：
- AI 洞察卡片
- 关键词热力图
- 竞品雷达图
- 异常标注集成
- 数据导出增强
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import date, timedelta, datetime
from pydantic import BaseModel, Field
import random
import logging

from db import get_db
from core.response import Response, ErrorCode
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["可视化仪表板增强"])


# ==================== 数据模型 ====================

class InsightItem(BaseModel):
    """AI 洞察项"""
    type: str = Field(..., description="洞察类型：opportunity/risk/alert")
    title: str = Field(..., description="洞察标题")
    description: str = Field(..., description="洞察描述")
    suggestion: str = Field(..., description="可执行建议")
    impact: str = Field(..., description="影响程度：高/中/低")
    confidence: float = Field(..., description="置信度 0-1")


class KeywordHeatmapItem(BaseModel):
    """关键词热力图项"""
    keyword: str = Field(..., description="关键词")
    position: int = Field(..., description="当前排名")
    previous_position: int = Field(..., description="先前排名")
    change: int = Field(..., description="排名变化")
    search_volume: int = Field(..., description="搜索量")
    difficulty: int = Field(..., description="难度")
    heat: float = Field(..., description="热度值 0-1")
    url: str = Field(..., description="目标 URL")


class CompetitorRadarItem(BaseModel):
    """竞品雷达图项"""
    domain: str = Field(..., description="域名")
    metrics: Dict[str, float] = Field(..., description="多维度指标")


class AnomalyPoint(BaseModel):
    """异常点标注"""
    date: str = Field(..., description="日期")
    value: float = Field(..., description="数值")
    is_anomaly: bool = Field(..., description="是否异常")
    anomaly_type: Optional[str] = Field(default=None, description="异常类型：drop/spike")
    anomaly_score: Optional[float] = Field(default=None, description="异常分数")
    root_cause: Optional[str] = Field(default=None, description="可能原因")


# ==================== AI 洞察 API ====================

@router.get("/insights", summary="AI 洞察卡片", description="获取 AI 生成的关键发现和建议")
async def get_ai_insights(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    domain: Optional[str] = Query(default=None, description="域名筛选")
) -> Response:
    """
    获取 AI 洞察卡片

    返回：
    - 机会发现：关键词排名上升空间、内容优化机会
    - 风险预警：流量下跌趋势、竞品超越风险
    - 异常告警：流量异常波动、技术 SEO 问题
    """
    try:
        insights = []

        # 模拟 AI 分析生成的洞察
        # 实际应集成 AI 分析服务

        # 机会洞察
        if random.random() > 0.3:
            insights.append({
                "type": "opportunity",
                "title": "发现流量增长机会",
                "description": "关键词'SEO tools'搜索量上升 25%，当前排名有提升空间",
                "suggestion": "优化相关页面的标题和描述，增加内部链接",
                "impact": "高",
                "confidence": round(random.uniform(0.75, 0.95), 2)
            })

        # 风险洞察
        if random.random() > 0.5:
            insights.append({
                "type": "risk",
                "title": "竞品流量接近超越",
                "description": "竞品 semrush.com 近 7 天流量增长 15%，差距正在缩小",
                "suggestion": "加强核心关键词内容质量，考虑增加付费推广",
                "impact": "中",
                "confidence": round(random.uniform(0.7, 0.9), 2)
            })

        # 异常告警
        if random.random() > 0.6:
            insights.append({
                "type": "alert",
                "title": "移动端跳出率异常",
                "description": "移动端跳出率较上周上升 12%，可能影响 SEO 排名",
                "suggestion": "检查移动端页面加载速度和用户体验",
                "impact": "中",
                "confidence": round(random.uniform(0.8, 0.95), 2)
            })

        # 内容优化机会
        if random.random() > 0.4:
            insights.append({
                "type": "opportunity",
                "title": "内容优化建议",
                "description": "博客文章平均阅读时长低于行业基准 30%",
                "suggestion": "增加图表、视频等多媒体内容，提升可读性",
                "impact": "低",
                "confidence": round(random.uniform(0.65, 0.85), 2)
            })

        # 技术 SEO 告警
        if random.random() > 0.7:
            insights.append({
                "type": "alert",
                "title": "页面加载速度告警",
                "description": "核心页面 LCP（最大内容绘制）超过 2.5 秒",
                "suggestion": "优化图片压缩，启用 CDN 加速",
                "impact": "高",
                "confidence": round(random.uniform(0.85, 0.98), 2)
            })

        # 按影响程度排序
        impact_order = {"高": 0, "中": 1, "低": 2}
        insights.sort(key=lambda x: (impact_order.get(x["impact"], 3), -x["confidence"]))

        return Response(code=0, message="success", data={
            "insights": insights[:5],  # 最多返回 5 条
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "generated_at": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to get AI insights: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get AI insights: {str(e)}",
            data={}
        )


# ==================== 关键词热力图 API ====================

@router.get("/heatmap/keywords", summary="关键词热力图", description="获取关键词排名变化热力图数据")
async def get_keyword_heatmap(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    limit: int = Query(default=50, ge=10, le=200, description="返回数量限制")
) -> Response:
    """
    获取关键词热力图数据

    热力值计算逻辑：
    - 排名上升且搜索量高 -> 高热度（绿色）
    - 排名下降且搜索量高 -> 高热度（红色）
    - 排名稳定或搜索量低 -> 低热度（灰色）
    """
    try:
        keywords_pool = [
            "SEO tools", "keyword research", "analytics platform",
            "digital marketing", "traffic analysis", "competitor analysis",
            "backlink checker", "rank tracker", "content optimization",
            "search console", "google analytics", "website audit",
            "SERP analysis", "domain authority", "page speed",
            "mobile optimization", "local SEO", "voice search",
            "AI content", "conversion optimization"
        ]

        heatmap_data = []
        for kw in random.sample(keywords_pool, min(limit, len(keywords_pool))):
            position = random.randint(1, 50)
            prev_position = random.randint(1, 50)
            change = prev_position - position  # 正数表示排名上升

            search_volume = random.randint(500, 20000)
            difficulty = random.randint(20, 90)

            # 计算热力值：基于排名变化和搜索量
            if change > 0:
                # 排名上升
                heat = min(1.0, (change * 0.1) + (search_volume / 20000) * 0.5)
            elif change < 0:
                # 排名下降
                heat = min(1.0, (abs(change) * 0.1) + (search_volume / 20000) * 0.5)
            else:
                heat = 0.3

            heatmap_data.append({
                "keyword": kw,
                "position": position,
                "previous_position": prev_position,
                "change": change,
                "search_volume": search_volume,
                "difficulty": difficulty,
                "heat": round(heat, 2),
                "url": f"/products/{kw.lower().replace(' ', '-')}"
            })

        # 按搜索量排序
        heatmap_data.sort(key=lambda x: x["search_volume"], reverse=True)

        return Response(code=0, message="success", data={
            "keywords": heatmap_data,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Failed to get keyword heatmap: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get keyword heatmap: {str(e)}",
            data={}
        )


# ==================== 竞品雷达图 API ====================

@router.get("/competitors/radar", summary="竞品雷达图", description="获取竞品多维度对比数据")
async def get_competitor_radar(
    domains: str = Query(..., description="要对比的域名列表，逗号分隔"),
) -> Response:
    """
    获取竞品雷达图数据

    对比维度：
    - 流量规模 (Traffic Volume)
    - 域名权威 (Domain Authority)
    - 内容质量 (Content Quality)
    - 外链数量 (Backlinks)
    - 关键词覆盖 (Keyword Coverage)
    - 社交媒体 (Social Presence)
    """
    try:
        domain_list = [d.strip() for d in domains.split(",") if d.strip()]

        if not domain_list:
            return Response(
                code=ErrorCode.BAD_REQUEST,
                message="请提供至少一个域名",
                data={}
            )

        radar_data = []
        for domain in domain_list:
            # 生成模拟数据
            radar_data.append({
                "domain": domain,
                "metrics": {
                    "traffic_volume": round(random.uniform(50, 100), 1),
                    "domain_authority": round(random.uniform(40, 95), 1),
                    "content_quality": round(random.uniform(60, 95), 1),
                    "backlinks": round(random.uniform(30, 90), 1),
                    "keyword_coverage": round(random.uniform(40, 85), 1),
                    "social_presence": round(random.uniform(30, 80), 1)
                }
            })

        return Response(code=0, message="success", data={
            "competitors": radar_data,
            "dimensions": [
                "traffic_volume",
                "domain_authority",
                "content_quality",
                "backlinks",
                "keyword_coverage",
                "social_presence"
            ],
            "dimension_labels": [
                "流量规模",
                "域名权威",
                "内容质量",
                "外链数量",
                "关键词覆盖",
                "社交媒体"
            ]
        })

    except Exception as e:
        logger.error(f"Failed to get competitor radar: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get competitor radar: {str(e)}",
            data={}
        )


# ==================== 流量趋势增强 API（含异常标注） ====================

@router.get("/traffic/trend/enhanced", summary="增强流量趋势", description="获取带异常标注的流量趋势数据")
async def get_traffic_trend_enhanced(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
) -> Response:
    """
    获取带 AI 异常标注的流量趋势数据

    返回：
    - 基础流量数据（日期、访客数、页面浏览量、会话数）
    - 异常标注（是否异常、异常类型、异常分数、可能原因）
    """
    try:
        from datetime import timedelta

        trend_data = []
        current_date = start_date
        base_visitors = random.randint(1000, 2000)

        # 生成基础趋势数据
        daily_data = []
        while current_date <= end_date:
            is_weekend = current_date.weekday() >= 5
            multiplier = random.uniform(0.6, 0.8) if is_weekend else random.uniform(0.9, 1.2)

            visitors = int(base_visitors * multiplier)
            page_views = int(visitors * random.uniform(2.5, 4))
            sessions = int(visitors * random.uniform(1.1, 1.5))

            daily_data.append({
                "date": current_date.isoformat(),
                "visitors": visitors,
                "page_views": page_views,
                "sessions": sessions
            })

            current_date += timedelta(days=1)

        # 计算异常标注
        if len(daily_data) >= 7:
            # 计算移动平均线
            visitors_values = [d["visitors"] for d in daily_data]
            window = min(7, len(visitors_values))

            for i, day in enumerate(daily_data):
                # 计算前后窗口平均值
                start_idx = max(0, i - window // 2)
                end_idx = min(len(daily_data), i + window // 2 + 1)
                window_values = visitors_values[start_idx:end_idx]
                avg = sum(window_values) / len(window_values)
                std = (sum((v - avg) ** 2 for v in window_values) / len(window_values)) ** 0.5

                if std > 0:
                    z_score = (day["visitors"] - avg) / std

                    # 判定异常（Z-score > 2 或 < -2）
                    if abs(z_score) > 2:
                        day["is_anomaly"] = True
                        day["anomaly_type"] = "spike" if z_score > 0 else "drop"
                        day["anomaly_score"] = round(min(1.0, abs(z_score) / 3), 2)

                        # 生成可能原因
                        if z_score > 0:
                            causes = [
                                "病毒式内容传播",
                                "营销活动成功",
                                "外部链接引流",
                                "社交媒体曝光"
                            ]
                        else:
                            causes = [
                                "关键词排名下降",
                                "技术问题导致",
                                "季节性波动",
                                "竞品活动影响"
                            ]
                        day["root_cause"] = random.choice(causes)
                    else:
                        day["is_anomaly"] = False
                        day["anomaly_type"] = None
                        day["anomaly_score"] = None
                        day["root_cause"] = None
                else:
                    day["is_anomaly"] = False
                    day["anomaly_type"] = None
                    day["anomaly_score"] = None
                    day["root_cause"] = None

        return Response(code=0, message="success", data={
            "trend": daily_data,
            "anomaly_count": sum(1 for d in daily_data if d.get("is_anomaly", False)),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Failed to get enhanced traffic trend: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get enhanced traffic trend: {str(e)}",
            data={}
        )


# ==================== 数据导出增强 API ====================

class ExportRequest(BaseModel):
    """导出请求"""
    export_type: str = Field(..., description="导出类型：dashboard/traffic/seo/competitor")
    format: str = Field(default="csv", description="导出格式：csv/excel/pdf/html")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    include_charts: bool = Field(default=True, description="是否包含图表")
    include_insights: bool = Field(default=True, description="是否包含 AI 洞察")


@router.post("/export/enhanced", summary="增强数据导出", description="导出仪表板数据（支持多种格式）")
async def export_dashboard_enhanced(request: ExportRequest) -> Response:
    """
    导出仪表板数据

    支持格式：
    - CSV: 纯数据导出
    - Excel: 数据 + 基础图表
    - PDF: 完整报告（含图表和洞察）
    - HTML: 交互式报告
    """
    try:
        # 生成模拟导出内容
        export_id = f"export_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        export_data = {
            "export_id": export_id,
            "export_type": request.export_type,
            "format": request.format,
            "status": "completed",
            "file_name": f"dashboard_export_{request.start_date}_{request.end_date}.{request.format}",
            "file_size": f"{random.randint(100, 500)} KB",
            "download_url": f"/api/dashboard/export/{export_id}/download",
            "generated_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "includes": {
                "charts": request.include_charts,
                "insights": request.include_insights,
                "raw_data": True
            }
        }

        # 添加模拟数据摘要
        if request.export_type == "dashboard":
            export_data["summary"] = {
                "total_visitors": random.randint(30000, 60000),
                "total_page_views": random.randint(80000, 150000),
                "avg_session_duration": random.randint(120, 300),
                "bounce_rate": round(random.uniform(0.25, 0.5), 4),
                "insights_count": random.randint(3, 7)
            }

        return Response(code=0, message="success", data=export_data)

    except Exception as e:
        logger.error(f"Failed to export dashboard: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to export dashboard: {str(e)}",
            data={}
        )


# ==================== 仪表板概览 API ====================

@router.get("/overview", summary="仪表板概览", description="获取仪表板核心指标概览")
async def get_dashboard_overview() -> Response:
    """
    获取仪表板概览

    返回核心指标摘要，用于快速加载
    """
    try:
        # 生成模拟概览数据
        overview = {
            "traffic": {
                "current_visitors": random.randint(1000, 2000),
                "change_percentage": round(random.uniform(-15, 25), 1),
                "trend": "up" if random.random() > 0.4 else "down"
            },
            "seo": {
                "avg_position": round(random.uniform(8, 20), 1),
                "position_change": random.randint(-3, 5),
                "seo_score": random.randint(75, 95)
            },
            "alerts": {
                "active_alerts": random.randint(0, 3),
                "critical_count": random.randint(0, 1),
                "warning_count": random.randint(0, 2)
            },
            "insights": {
                "new_insights": random.randint(1, 5),
                "high_impact_count": random.randint(0, 2)
            }
        }

        return Response(code=0, message="success", data=overview)

    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get dashboard overview: {str(e)}",
            data={}
        )
