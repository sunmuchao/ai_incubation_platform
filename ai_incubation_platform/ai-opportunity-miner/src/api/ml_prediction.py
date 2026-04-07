"""
ML 预测 API

提供趋势预测、事件分类和投资机会评分接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from services.ml_prediction_service import ml_prediction_service

router = APIRouter(prefix="/api/ml", tags=["ml-prediction"])


class ForecastRequest(BaseModel):
    """预测请求"""
    industry: str
    forecast_months: int = 6


class NewsClassificationRequest(BaseModel):
    """新闻分类请求"""
    news_items: List[Dict[str, Any]]


@router.get("/forecast/industries")
async def get_all_industries_forecast(
    forecast_months: int = Query(6, description="预测月数", ge=1, le=12)
):
    """获取所有行业的投资预测"""
    try:
        forecasts = ml_prediction_service.get_all_industries_forecast(forecast_months)
        return {
            "success": True,
            "data": forecasts,
            "count": len(forecasts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast/industry/{industry}")
async def get_industry_forecast(
    industry: str,
    forecast_months: int = Query(6, description="预测月数", ge=1, le=12)
):
    """获取特定行业的投资预测"""
    result = ml_prediction_service.get_industry_forecast(industry, forecast_months)
    if not result:
        raise HTTPException(status_code=404, detail=f"No forecast available for industry: {industry}")

    return {
        "success": True,
        "data": result
    }


@router.get("/forecast/hot-industries")
async def get_hot_industries(
    top_n: int = Query(5, description="返回前 N 个热门行业", ge=1, le=20)
):
    """获取热门行业预测"""
    hot_industries = ml_prediction_service.get_hot_industries(top_n)
    return {
        "success": True,
        "data": hot_industries
    }


@router.get("/trending-investors")
async def get_trending_investors():
    """获取活跃投资人预测"""
    investors = ml_prediction_service.get_trending_investors()
    return {
        "success": True,
        "data": investors
    }


@router.post("/classify/news")
async def classify_news(request: NewsClassificationRequest):
    """分类新闻事件"""
    results = ml_prediction_service.classify_news_events(request.news_items)
    return {
        "success": True,
        "data": results,
        "count": len(results)
    }


@router.get("/sentiment")
async def get_market_sentiment():
    """获取市场情绪分析"""
    sentiment = ml_prediction_service.get_market_sentiment()
    return {
        "success": True,
        "data": sentiment
    }


@router.get("/opportunity-score/{industry}")
async def get_opportunity_score(
    industry: str,
    company_name: Optional[str] = Query(None, description="公司名称")
):
    """获取投资机会评分"""
    score = ml_prediction_service.get_investment_opportunity_score(industry, company_name)
    return {
        "success": True,
        "data": score
    }


@router.get("/model-comparison/{industry}")
async def get_model_comparison(
    industry: str
):
    """获取模型对比结果"""
    from ml.trend_predictor import trend_predictor

    comparison = trend_predictor.get_model_comparison("industry", industry)
    return {
        "success": True,
        "data": comparison
    }
