"""
v1.9 竞品分析增强 API

提供竞品追踪、市场份额分析、竞品策略解读功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import date, timedelta
from pydantic import BaseModel, Field

from db import get_db
from core.response import Response, ErrorCode
from services.competitor_service import CompetitorService

router = APIRouter(prefix="/competitor", tags=["竞品分析"])


# ==================== 请求/响应模型 ====================

class CompetitorTrackRequest(BaseModel):
    """追踪竞品请求"""
    domain: str = Field(..., description="竞品域名")
    auto_track: bool = Field(default=True, description="是否自动追踪")


class CompetitorMetricResponse(BaseModel):
    """竞品指标响应"""
    domain: str
    traffic: int
    traffic_growth: float
    keywords_count: int
    keywords_top3: int
    keywords_top10: int
    backlinks: int
    domain_authority: int
    market_share: float
    content_count: int
    avg_position: float


class MarketShareResponse(BaseModel):
    """市场份额响应"""
    period: str
    total_market_size: int
    competitors: Dict[str, float]
    top_gainers: List[Dict]
    top_losers: List[Dict]
    market_trends: List[str]


class CompetitorStrategyResponse(BaseModel):
    """竞品策略响应"""
    competitor: str
    strategy_type: str
    description: str
    evidence: List[str]
    impact_level: str
    confidence: float
    recommended_action: str


class CompetitorAlertResponse(BaseModel):
    """竞品告警响应"""
    type: str
    level: str
    competitor: str
    message: str
    suggested_action: str


class CompetitorInsightResponse(BaseModel):
    """竞品洞察响应"""
    market_overview: Dict
    key_findings: List[str]
    opportunities: List[Dict]
    threats: List[Dict]
    recommended_actions: List[Dict]


# ==================== API 端点 ====================

@router.post("/track", summary="追踪竞品", description="开始追踪指定竞品的数据")
async def track_competitor(
    request: CompetitorTrackRequest,
    db: Session = Depends(get_db)
) -> Response:
    """
    追踪竞品数据

    开始追踪指定竞品的关键指标，包括流量、关键词、外链等
    """
    try:
        service = CompetitorService(db)
        metrics = service.track_competitor(request.domain)

        return Response.success(
            data=metrics,
            message=f"成功开始追踪竞品：{request.domain}"
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"追踪竞品失败：{e}")
        return Response.error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"追踪竞品失败：{str(e)}"
        )


@router.get("/comparison", summary="竞品对比", description="获取我方与竞品的对比分析")
async def get_competitor_comparison(
    start_date: Optional[date] = Query(default=None, description="开始日期"),
    end_date: Optional[date] = Query(default=None, description="结束日期"),
    db: Session = Depends(get_db)
) -> Response:
    """
    获取竞品对比分析

    对比我方与多个竞品的关键指标，计算排名
    """
    try:
        service = CompetitorService(db)
        comparison = service.get_competitor_comparison(start_date, end_date)

        return Response.success(
            data=comparison,
            message="获取竞品对比成功"
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"获取竞品对比失败：{e}")
        return Response.error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取竞品对比失败：{str(e)}"
        )


@router.get("/market-share", summary="市场份额分析", description="分析市场份额分布和趋势")
async def analyze_market_share(
    period: str = Query(default="current_month", description="时间段")
) -> Response:
    """
    分析市场份额

    返回：
    - 各竞品市场份额占比
    - 增长最快/下滑最快的竞品
    - 市场趋势分析
    """
    try:
        service = CompetitorService()
        market_share = service.analyze_market_share(period)

        data = {
            "period": market_share.period,
            "total_market_size": market_share.total_market_size,
            "competitors": market_share.competitors,
            "top_gainers": market_share.top_gainers,
            "top_losers": market_share.top_losers,
            "market_trends": market_share.market_trends
        }

        return Response.success(
            data=data,
            message="市场份额分析成功"
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"市场份额分析失败：{e}")
        return Response.error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"市场份额分析失败：{str(e)}"
        )


@router.get("/strategy/{domain}", summary="竞品策略解读", description="深度解读指定竞品的策略")
async def analyze_competitor_strategy(
    domain: str,
    db: Session = Depends(get_db)
) -> Response:
    """
    解读竞品策略

    分析竞品的内容策略、SEO 策略、外链策略等
    """
    try:
        service = CompetitorService(db)
        strategies = service.analyze_competitor_strategy(domain)

        data = [
            {
                "competitor": s.competitor,
                "strategy_type": s.strategy_type,
                "description": s.description,
                "evidence": s.evidence,
                "impact_level": s.impact_level,
                "confidence": s.confidence,
                "recommended_action": s.recommended_action
            }
            for s in strategies
        ]

        return Response.success(
            data=data,
            message=f"成功分析 {domain} 的竞争策略"
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"竞品策略分析失败：{e}")
        return Response.error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"竞品策略分析失败：{str(e)}"
        )


@router.get("/alerts", summary="竞品告警", description="获取竞品动态告警")
async def get_competitor_alerts(
    db: Session = Depends(get_db)
) -> Response:
    """
    获取竞品告警

    监控竞品的重要动态，如流量激增、关键词超越等
    """
    try:
        service = CompetitorService(db)
        alerts = service.get_competitor_alerts()

        return Response.success(
            data=alerts,
            message="获取竞品告警成功"
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"获取竞品告警失败：{e}")
        return Response.error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取竞品告警失败：{str(e)}"
        )


@router.get("/insights", summary="竞品洞察", description="获取 AI 生成的竞品洞察报告")
async def get_competitor_insights(
    db: Session = Depends(get_db)
) -> Response:
    """
    获取竞品洞察

    AI 生成的综合竞品分析报告，包括：
    - 市场概览
    - 关键发现
    - 机会识别
    - 威胁预警
    - 行动建议
    """
    try:
        service = CompetitorService(db)
        insights = service.get_competitor_insights()

        return Response.success(
            data=insights,
            message="获取竞品洞察成功"
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"获取竞品洞察失败：{e}")
        return Response.error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取竞品洞察失败：{str(e)}"
        )


@router.get("/tracked", summary="已追踪竞品列表", description="获取正在追踪的竞品列表")
async def get_tracked_competitors(
    db: Session = Depends(get_db)
) -> Response:
    """获取已追踪的竞品列表"""
    try:
        service = CompetitorService(db)

        return Response.success(
            data={
                "competitors": service.tracked_competitors,
                "count": len(service.tracked_competitors)
            },
            message="获取已追踪竞品列表成功"
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"获取已追踪竞品列表失败：{e}")
        return Response.error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取已追踪竞品列表失败：{str(e)}"
        )


@router.delete("/tracked/{domain}", summary="停止追踪竞品", description="停止追踪指定竞品")
async def remove_tracked_competitor(
    domain: str,
    db: Session = Depends(get_db)
) -> Response:
    """停止追踪指定竞品"""
    try:
        service = CompetitorService(db)

        if domain in service.tracked_competitors:
            service.tracked_competitors.remove(domain)
            return Response.success(
                message=f"已停止追踪竞品：{domain}"
            )
        else:
            return Response.error(
                code=ErrorCode.NOT_FOUND,
                message=f"未找到追踪的竞品：{domain}"
            )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"停止追踪竞品失败：{e}")
        return Response.error(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"停止追踪竞品失败：{str(e)}"
        )
