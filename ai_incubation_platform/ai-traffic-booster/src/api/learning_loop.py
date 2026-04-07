"""
from pydantic import BaseModel, Field
AI 持续学习闭环 API - P3 持续学习闭环

提供优化效果追踪、反馈和学习功能
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Body

from services.learning_loop_service import learning_loop_service, EffectRating


router = APIRouter(prefix="/ai/learning", tags=["AI Learning Loop"])


# ==================== Schema 定义 ====================

class ExecutionRecordRequest(BaseModel):
    """执行记录请求"""
    suggestion_id: str
    suggestion_type: str
    suggestion_title: str
    domain: Optional[str] = None
    page_url: Optional[str] = None
    executed_by: Optional[str] = None
    pre_metrics: Dict[str, float]


class EffectUpdateRequest(BaseModel):
    """效果更新请求"""
    record_id: str
    post_metrics: Dict[str, float]
    feedback_notes: Optional[str] = None


# ==================== API 端点 ====================

@router.post("/execution")
async def record_execution(
    request: ExecutionRecordRequest,
):
    """
    记录优化执行

    当用户执行了一个优化建议后，调用此接口记录执行情况
    """
    record = learning_loop_service.record_execution(
        suggestion_id=request.suggestion_id,
        suggestion_type=request.suggestion_type,
        suggestion_title=request.suggestion_title,
        pre_metrics=request.pre_metrics,
        domain=request.domain,
        page_url=request.page_url,
        executed_by=request.executed_by,
    )

    return {
        "status": "recorded",
        "record_id": record.record_id,
        "message": "执行记录已保存，请在 7-30 天后更新效果数据",
    }


@router.put("/effect")
async def update_effect(
    request: EffectUpdateRequest,
):
    """
    更新优化效果

    在执行优化后一段时间（如 7-30 天），调用此接口更新效果数据
    """
    try:
        record = learning_loop_service.update_effect(
            record_id=request.record_id,
            post_metrics=request.post_metrics,
            feedback_notes=request.feedback_notes,
        )

        return {
            "status": "updated",
            "record_id": record.record_id,
            "effect_rating": record.effect_rating.value if record.effect_rating else None,
            "effects": record.calculate_effect(),
            "insights": record.learned_insights,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/success-rate")
async def get_success_rate(
    suggestion_type: Optional[str] = Query(None, description="建议类型"),
    days: int = Query(30, ge=1, le=365, description="统计天数"),
):
    """
    获取建议成功率

    返回指定类型建议的历史成功率统计
    """
    stats = learning_loop_service.get_success_rate(
        suggestion_type=suggestion_type,
        days=days,
    )

    return {
        "suggestion_type": suggestion_type,
        "days": days,
        "statistics": stats,
    }


@router.get("/best-practices")
async def get_best_practices(
    min_success_rate: float = Query(0.7, ge=0, le=1, description="最小成功率"),
):
    """
    获取最佳实践

    基于历史数据返回高成功率的优化模式
    """
    practices = learning_loop_service.get_best_practices(
        min_success_rate=min_success_rate,
    )

    return {
        "best_practices": practices,
        "total": len(practices),
    }


@router.get("/similar-cases")
async def get_similar_cases(
    suggestion_type: str = Query(..., description="建议类型"),
    suggestion_title: str = Query(..., description="建议标题"),
    limit: int = Query(5, ge=1, le=20, description="返回数量"),
):
    """
    获取相似案例

    返回历史上相似的优化案例及其效果
    """
    cases = learning_loop_service.get_similar_cases(
        suggestion_type=suggestion_type,
        suggestion_title=suggestion_title,
        limit=limit,
    )

    return {
        "similar_cases": cases,
        "total": len(cases),
    }


@router.get("/insights")
async def get_learning_insights(
    days: int = Query(30, ge=1, le=365, description="天数"),
):
    """
    获取学习洞察

    从历史优化案例中提取的洞察和模式
    """
    # 获取最佳实践
    best_practices = learning_loop_service.get_best_practices(min_success_rate=0.7)

    # 获取成功率统计
    success_rate = learning_loop_service.get_success_rate(days=days)

    # 生成洞察
    insights = []

    if best_practices:
        top_practice = best_practices[0]
        insights.append({
            "type": "best_performer",
            "title": f"最佳优化类型：{top_practice['suggestion_type']}",
            "description": f"成功率 {top_practice['success_rate']}%，基于 {top_practice['sample_count']} 个案例",
        })

    if success_rate["total"] > 0:
        insights.append({
            "type": "overall_stats",
            "title": f"总体优化效果",
            "description": f"共记录 {success_rate['total']} 次优化，成功率 {success_rate['success_rate']}%，平均提升 {success_rate['average_improvement']}%",
        })

    return {
        "days": days,
        "insights": insights,
    }


@router.get("/feedback/templates")
async def get_feedback_templates():
    """
    获取反馈模板

    提供标准化的反馈模板，帮助用户提供有效反馈
    """
    templates = [
        {
            "type": "seo_optimization",
            "template": {
                "metrics_to_track": ["organic_traffic", "keyword_rankings", "ctr"],
                "measurement_period": "14-30 天",
                "feedback_questions": [
                    "优化后搜索引擎排名是否有变化？",
                    "自然搜索流量是否增加？",
                    "点击率 (CTR) 是否有提升？"
                ]
            }
        },
        {
            "type": "performance_optimization",
            "template": {
                "metrics_to_track": ["page_load_time", "first_contentful_paint", "bounce_rate"],
                "measurement_period": "7-14 天",
                "feedback_questions": [
                    "页面加载速度是否加快？",
                    "跳出率是否下降？",
                    "用户体验评分是否提升？"
                ]
            }
        },
        {
            "type": "conversion_optimization",
            "template": {
                "metrics_to_track": ["conversion_rate", "cart_abandonment_rate", "revenue"],
                "measurement_period": "14-30 天",
                "feedback_questions": [
                    "转化率是否有提升？",
                    "购物车放弃率是否下降？",
                    "收入是否增长？"
                ]
            }
        }
    ]

    return {"templates": templates}


@router.post("/feedback/submit")
async def submit_feedback(
    record_id: str = Query(..., description="记录 ID"),
    rating: int = Query(..., ge=1, le=5, description="评分 1-5"),
    comments: Optional[str] = Body(None, description="评价内容"),
    would_recommend: bool = Body(True, description="是否愿意推荐此优化方法"),
):
    """
    提交用户反馈

    收集用户对优化建议的满意度反馈
    """
    # 获取记录
    record = learning_loop_service._get_record(record_id)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # 将反馈转换为效果评级
    rating_map = {
        5: EffectRating.EXCELLENT,
        4: EffectRating.GOOD,
        3: EffectRating.NEUTRAL,
        2: EffectRating.NEGATIVE,
        1: EffectRating.NEGATIVE,
    }

    effect_rating = rating_map.get(rating, EffectRating.NEUTRAL)

    # 更新记录
    record.effect_rating = effect_rating
    record.feedback_notes = comments
    record.learned_insights = learning_loop_service._extract_insights(record)

    return {
        "status": "submitted",
        "record_id": record_id,
        "rating": rating,
        "effect_rating": effect_rating.value,
        "message": "感谢您的反馈！这将帮助我们改进建议质量",
    }
