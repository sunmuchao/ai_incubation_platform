"""
增强的 ML 预测 API

提供可解释的预测和商机评分
支持趋势预警和相似案例推荐
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from ml.opportunity_scorer import opportunity_scorer, OpportunityScore
from ml.enhanced_predictor import enhanced_predictor
from ml.trend_predictor import trend_predictor
from services.ml_prediction_service import ml_prediction_service

router = APIRouter(prefix="/api/p8/ml", tags=["ml-enhanced"])


class ScoreRequest(BaseModel):
    """商机评分请求"""
    industry: str = Field(..., description="行业名称")
    company_name: Optional[str] = Field(None, description="公司名称")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class ScoreResponse(BaseModel):
    """商机评分响应"""
    success: bool
    data: Dict[str, Any]
    message: str = ""


class ExplanationRequest(BaseModel):
    """预测解释请求"""
    industry: str = Field(..., description="行业名称")
    forecast_months: int = Field(6, description="预测月数", ge=1, le=12)


class AlertResponse(BaseModel):
    """预警信号响应"""
    success: bool
    data: List[Dict[str, Any]]
    count: int


@router.post("/score", response_model=ScoreResponse)
async def get_opportunity_score(request: ScoreRequest):
    """
    获取投资机会评分（增强版）

    提供多维度的商机评分，包括：
    - 综合评分（0-100）
    - 评级（A+/A/B+/B/C）
    - 置信度评估
    - 关键驱动因素
    - 风险提示
    """
    try:
        # 获取上下文数据
        context = request.context or {}

        # 尝试从现有服务获取预测数据
        try:
            forecast = ml_prediction_service.get_industry_forecast(request.industry)
            if forecast:
                context['forecast'] = forecast
        except Exception:
            pass

        # 尝试获取投资数据
        try:
            from services.investment_chain_service import investment_chain_service
            investments = investment_chain_service.get_investments_by_industry(request.industry)
            context['investment_data'] = [
                {
                    'investor_name': inv.investor_name,
                    'amount': inv.amount,
                    'date': inv.investment_date.isoformat() if inv.investment_date else None
                }
                for inv in investments
            ]
        except Exception:
            pass

        # 获取市场情绪
        try:
            context['market_sentiment'] = ml_prediction_service.get_market_sentiment()
        except Exception:
            pass

        # 执行评分
        score_result = opportunity_scorer.score(
            industry=request.industry,
            company_name=request.company_name,
            context=context
        )

        # 格式化为响应
        response_data = {
            "industry": score_result.industry,
            "company_name": score_result.company_name,
            "total_score": score_result.total_score,
            "rating": score_result.rating,
            "recommendation": score_result.recommendation,
            "confidence": {
                "score": score_result.confidence_score,
                "level": score_result.confidence_level.value,
                "factors": score_result.confidence_factors
            },
            "explanation": score_result.explanation,
            "key_insights": score_result.key_insights,
            "top_positive_factors": score_result.top_positive_factors,
            "top_negative_factors": score_result.top_negative_factors,
            "predicted_growth_rate": score_result.predicted_growth_rate,
            "factor_analyses": [
                {
                    "factor": fa.factor.value,
                    "score": fa.score,
                    "weight": fa.weight,
                    "contribution": fa.contribution,
                    "trend": fa.trend,
                    "description": fa.description,
                    "confidence": fa.confidence
                }
                for fa in score_result.factor_analyses
            ],
            "generated_at": score_result.generated_at.isoformat(),
            "model_version": score_result.model_version
        }

        return ScoreResponse(
            success=True,
            data=response_data,
            message=f"已完成{request.industry}行业的投资机会评分"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评分失败：{str(e)}")


@router.post("/explain")
async def explain_forecast(request: ExplanationRequest):
    """
    获取预测解释

    返回：
    - 预测摘要
    - 关键驱动因素
    - 支撑数据
    - 相似历史案例
    - 风险因素
    - 置信度说明
    """
    try:
        # 执行基础预测
        forecast = ml_prediction_service.get_industry_forecast(
            request.industry,
            request.forecast_months
        )

        if not forecast:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取{request.industry}行业的预测数据"
            )

        # 生成解释
        explanation = enhanced_predictor.generate_explanation(
            industry=request.industry,
            forecast_result=forecast
        )

        response_data = {
            "industry": request.industry,
            "forecast_months": request.forecast_months,
            "summary": explanation.summary,
            "key_drivers": explanation.key_drivers,
            "supporting_data": explanation.supporting_data,
            "similar_cases": explanation.similar_cases,
            "risk_factors": explanation.risk_factors,
            "confidence_explanation": explanation.confidence_explanation,
            "base_forecast": forecast
        }

        return {
            "success": True,
            "data": response_data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成解释失败：{str(e)}")


@router.get("/alerts/{industry}")
async def get_industry_alerts(
    industry: str,
    limit: int = Query(10, description="返回结果数量上限", ge=1, le=50)
):
    """
    获取行业预警信号

    预警类型：
    - surge: 投资激增
    - decline: 投资下滑
    - anomaly: 异常波动
    - milestone: 趋势反转
    """
    try:
        # 获取预测
        forecast = ml_prediction_service.get_industry_forecast(industry)

        if not forecast:
            return {
                "success": True,
                "data": [],
                "count": 0,
                "message": f"暂无{industry}行业的预测数据"
            }

        # 生成预警
        alerts = enhanced_predictor.generate_alerts(
            industry=industry,
            forecast_result=forecast
        )

        response_data = [
            {
                "alert_id": a.alert_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "industry": a.industry,
                "triggered_at": a.triggered_at.isoformat(),
                "suggested_action": a.suggested_action
            }
            for a in alerts
        ]

        return {
            "success": True,
            "data": response_data,
            "count": len(response_data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预警失败：{str(e)}")


@router.get("/similar-cases/{industry}")
async def get_similar_cases(
    industry: str,
    trend_direction: Optional[str] = Query(None, description="趋势方向", pattern="^(up|down|stable)$")
):
    """
    获取相似历史案例

    用于参考类似市场条件下的历史表现
    """
    try:
        # 获取预测
        forecast = ml_prediction_service.get_industry_forecast(industry)

        if not forecast:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取{industry}行业的预测数据"
            )

        # 如果指定了趋势方向，覆盖预测结果
        if trend_direction:
            forecast['trend_direction'] = trend_direction

        # 查找相似案例
        similar_cases = enhanced_predictor._find_similar_cases(industry, forecast)

        return {
            "success": True,
            "data": {
                "industry": industry,
                "trend_direction": forecast.get('trend_direction', 'stable'),
                "similar_cases": similar_cases
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取相似案例失败：{str(e)}")


@router.get("/alerts/history")
async def get_alert_history(
    industry: Optional[str] = Query(None, description="行业名称"),
    alert_type: Optional[str] = Query(None, description="预警类型"),
    limit: int = Query(20, description="返回结果数量上限", ge=1, le=100)
):
    """获取预警历史记录"""
    try:
        alerts = enhanced_predictor.get_alert_history(
            industry=industry,
            alert_type=alert_type,
            limit=limit
        )

        return {
            "success": True,
            "data": alerts,
            "count": len(alerts)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预警历史失败：{str(e)}")


@router.get("/score/comparison")
async def compare_industry_scores(
    industries: List[str] = Query(..., description="要比较的行业列表", min_length=1, max_length=10)
):
    """
    比较多个行业的投资机会评分

    用于横向对比不同行业的投资价值
    """
    try:
        results = []
        for industry in industries:
            try:
                score_result = opportunity_scorer.score(industry=industry)
                results.append({
                    "industry": industry,
                    "total_score": score_result.total_score,
                    "rating": score_result.rating,
                    "recommendation": score_result.recommendation,
                    "confidence_score": score_result.confidence_score,
                    "predicted_growth_rate": score_result.predicted_growth_rate
                })
            except Exception:
                results.append({
                    "industry": industry,
                    "error": "评分失败"
                })

        # 按评分排序
        results.sort(key=lambda x: x.get('total_score', 0), reverse=True)

        return {
            "success": True,
            "data": results,
            "count": len(results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"比较评分失败：{str(e)}")


@router.get("/trending-alerts")
async def get_trending_alerts(
    severity: Optional[str] = Query(None, description="严重程度筛选", pattern="^(low|medium|high|critical)$"),
    limit: int = Query(10, description="返回结果数量上限", ge=1, le=50)
):
    """获取所有行业的热门预警信号"""
    try:
        all_alerts = enhanced_predictor._alert_history

        # 筛选
        if severity:
            all_alerts = [a for a in all_alerts if a.severity == severity]

        # 按严重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_alerts.sort(key=lambda a: (severity_order.get(a.severity, 4), a.triggered_at))

        response_data = [
            {
                "alert_id": a.alert_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "industry": a.industry,
                "triggered_at": a.triggered_at.isoformat(),
                "suggested_action": a.suggested_action
            }
            for a in all_alerts[:limit]
        ]

        return {
            "success": True,
            "data": response_data,
            "count": len(response_data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热门预警失败：{str(e)}")
