"""
商机 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.opportunity import (
    BusinessOpportunity, MarketTrend, OpportunityStatus, OpportunityType,
    RiskLabel, SourceType
)
from services.opportunity_service import opportunity_service

router = APIRouter(prefix="/api", tags=["opportunity"])


class OpportunityUpdateRequest(BaseModel):
    """商机更新请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[OpportunityType] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    potential_value: Optional[float] = None
    potential_value_currency: Optional[str] = None
    source_type: Optional[SourceType] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    risk_labels: Optional[List[RiskLabel]] = None
    risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    risk_description: Optional[str] = None
    validation_steps: Optional[List[str]] = None
    validation_status: Optional[str] = None
    validation_notes: Optional[str] = None
    related_entities: Optional[List[dict]] = None
    tags: Optional[List[str]] = None
    status: Optional[OpportunityStatus] = None


class KeywordDiscoverRequest(BaseModel):
    """关键词发现商机请求"""
    keywords: List[str] = Field(min_length=1)
    days: Optional[int] = 30


class IndustryDiscoverRequest(BaseModel):
    """行业发现商机请求"""
    industry: str
    days: Optional[int] = 60


class TrendAnalysisRequest(BaseModel):
    """趋势分析请求"""
    keyword: str
    days: Optional[int] = Field(default=30, ge=1, le=365)


class CompetitionAnalysisRequest(BaseModel):
    """竞争分析请求"""
    industry: str
    days: Optional[int] = 60


class ReportExportRequest(BaseModel):
    """报告导出请求"""
    format: Literal["markdown", "pdf"] = "markdown"
    opp_ids: Optional[List[str]] = None


class DataFetchRequest(BaseModel):
    """数据获取请求"""
    keywords: List[str]
    days: Optional[int] = 7


class CompetitorAnalysisRequest(BaseModel):
    """竞品分析请求"""
    company_name: str


@router.get("/opportunities", response_model=List[BusinessOpportunity])
async def list_opportunities(status: Optional[OpportunityStatus] = Query(None)):
    """获取商机列表"""
    return opportunity_service.list_opportunities(status)


@router.post("/opportunities/discover")
async def discover_opportunities():
    """AI 发现新商机"""
    opps = opportunity_service.discover_opportunities()
    return {"message": f"Discovered {len(opps)} opportunities", "opportunities": opps}


@router.get("/opportunities/{opp_id}", response_model=BusinessOpportunity)
async def get_opportunity(opp_id: str):
    """获取商机详情"""
    opp = opportunity_service.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp


@router.get("/trends", response_model=List[MarketTrend])
async def list_trends(min_score: float = Query(0.0, ge=0.0, le=1.0)):
    """获取市场趋势"""
    return opportunity_service.list_trends(min_score)


@router.post("/trends")
async def add_trend(trend: MarketTrend):
    """添加趋势数据"""
    return opportunity_service.add_trend(trend)


@router.put("/opportunities/{opp_id}", response_model=BusinessOpportunity)
async def update_opportunity(opp_id: str, request: OpportunityUpdateRequest):
    """更新商机信息"""
    opp = opportunity_service.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # 更新字段
    update_data = request.dict(exclude_unset=True)

    # 转换枚举类型
    if "type" in update_data and update_data["type"]:
        update_data["type"] = OpportunityType(update_data["type"])
    if "status" in update_data and update_data["status"]:
        update_data["status"] = OpportunityStatus(update_data["status"])
    if "source_type" in update_data and update_data["source_type"]:
        update_data["source_type"] = SourceType(update_data["source_type"])
    if "risk_labels" in update_data and update_data["risk_labels"]:
        update_data["risk_labels"] = [RiskLabel(l) for l in update_data["risk_labels"]]

    result = opportunity_service.update_opportunity(opp_id, update_data)
    return result


@router.delete("/opportunities/{opp_id}")
async def delete_opportunity(opp_id: str):
    """删除商机"""
    opp = opportunity_service.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    success = opportunity_service.delete_opportunity(opp_id)
    if success:
        return {"message": "Opportunity deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete opportunity")


@router.post("/opportunities/{opp_id}/validate")
async def update_validation_status(opp_id: str, status: str, notes: str = ""):
    """更新商机验证状态"""
    opp = opportunity_service.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    valid_statuses = ["pending", "in_progress", "completed", "failed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid validation status. Must be one of: {valid_statuses}")

    result = opportunity_service.update_opportunity(opp_id, {"validation_status": status, "validation_notes": notes})
    return {"message": "Validation status updated", "opportunity": result}


@router.post("/opportunities/discover/keywords")
async def discover_by_keywords(request: KeywordDiscoverRequest):
    """根据关键词发现新商机"""
    opps = await opportunity_service.discover_opportunities_from_keywords(request.keywords, request.days)
    return {"message": f"Discovered {len(opps)} opportunities from keywords", "opportunities": opps}


@router.post("/opportunities/discover/industry")
async def discover_by_industry(request: IndustryDiscoverRequest):
    """根据行业发现新商机"""
    opps = await opportunity_service.discover_opportunities_by_industry(request.industry, request.days)
    return {"message": f"Discovered {len(opps)} opportunities for industry {request.industry}", "opportunities": opps}


@router.post("/trends/analyze")
async def analyze_trend(request: TrendAnalysisRequest):
    """生成趋势分析报告"""
    trend = await opportunity_service.generate_trend_analysis(request.keyword, request.days)
    return {"message": "Trend analysis completed", "trend": trend}


@router.post("/analysis/competition")
async def analyze_competition(request: CompetitionAnalysisRequest):
    """竞争格局分析"""
    analysis = await opportunity_service.analyze_competition(request.industry, request.days)
    return {"message": "Competition analysis completed", "analysis": analysis}


@router.post("/export/opportunity/{opp_id}")
async def export_opportunity(opp_id: str, format: Literal["markdown", "pdf"] = "markdown"):
    """导出单条商机报告"""
    result = opportunity_service.export_opportunity_report(opp_id, format)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/export/opportunities")
async def export_batch_opportunities(request: ReportExportRequest):
    """批量导出商机报告"""
    result = opportunity_service.export_batch_report(request.opp_ids, request.format)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/export/trends")
async def export_trends(min_score: float = 0, format: Literal["markdown", "pdf"] = "markdown"):
    """导出趋势分析报告"""
    result = opportunity_service.export_trend_report(min_score, format)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/data/news")
async def fetch_news(request: DataFetchRequest):
    """获取新闻数据"""
    return await opportunity_service.get_news_data(request.keywords, request.days)


@router.post("/data/reports")
async def fetch_reports(request: DataFetchRequest):
    """获取行业报告数据"""
    return await opportunity_service.get_industry_reports(request.keywords)


@router.get("/trends/industry/{industry}")
async def get_trends_by_industry(industry: str, period: str = Query("30d")):
    """
    按行业获取趋势
    前端调用接口：GET /api/trends/industry/{industry}?period=30d
    """
    # 解析时间段
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(period, 30)

    # 检查是否已有该行业趋势
    existing_trends = opportunity_service.list_trends()
    industry_trends = [t for t in existing_trends if industry.lower() in t.keyword.lower()]

    if industry_trends:
        return {"trends": industry_trends, "source": "cache"}

    # 生成新趋势分析
    try:
        trend = await opportunity_service.generate_trend_analysis(industry, days)
        return {"trends": [trend], "source": "generated"}
    except Exception as e:
        return {"trends": [], "source": "error", "error": str(e)}


@router.post("/competitor/analyze")
async def analyze_competitor(request: CompetitorAnalysisRequest):
    """
    竞品分析
    前端调用接口：POST /api/competitor/analyze
    Body: {"company_name": "竞争对手名称"}
    """
    # 使用行业分析来模拟竞品分析
    analysis = await opportunity_service.analyze_competition(request.company_name, 60)
    return {
        "company_name": request.company_name,
        "analysis": analysis,
        "status": "completed"
    }
