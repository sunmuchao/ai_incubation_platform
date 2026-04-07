"""
Schema 推荐 API

提供智能 Schema 推荐的 HTTP 接口
"""
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import timedelta

from services.schema_recommendation_service import schema_recommendation_service
from utils.logger import logger

router = APIRouter(prefix="/api/schema", tags=["Schema Recommendation"])


# ==================== 请求/响应模型 ====================

class AnalyzeRequest(BaseModel):
    """分析请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    time_range_days: int = Field(default=7, ge=1, le=90, description="分析时间范围（天）")


class AnalyzeResponse(BaseModel):
    """分析响应"""
    datasource: str
    table_name: str
    total_patterns: int
    patterns_by_type: Dict[str, Any]
    summary: Dict[str, int]


class IndexRecommendationRequest(BaseModel):
    """索引推荐请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")


class PartitionRecommendationRequest(BaseModel):
    """分区推荐请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")


class RedundancyDetectionRequest(BaseModel):
    """冗余检测请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")


class RecommendationItem(BaseModel):
    """推荐项"""
    type: str
    title: str
    description: str
    suggested_sql: Optional[str]
    impact_score: float
    effort_level: str
    priority: str


class ApplyRecommendationRequest(BaseModel):
    """应用推荐请求"""
    recommendation_id: str = Field(..., description="推荐 ID")
    dry_run: bool = Field(default=True, description="是否dry run 模式")


class RejectRecommendationRequest(BaseModel):
    """拒绝推荐请求"""
    recommendation_id: str = Field(..., description="推荐 ID")
    reason: str = Field(..., description="拒绝原因")


class CreateRecommendationRequest(BaseModel):
    """创建推荐请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    recommendation_type: str = Field(..., description="推荐类型")
    title: str = Field(..., description="推荐标题")
    description: str = Field(..., description="推荐描述")
    suggested_sql: Optional[str] = Field(None, description="建议 SQL")
    column_name: Optional[str] = Field(None, description="列名")
    rationale: Optional[str] = Field(None, description="推荐理由")
    priority: str = Field(default="medium", description="优先级")


# ==================== 端点 ====================

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_schema(request: AnalyzeRequest):
    """分析 Schema 和查询模式"""
    try:
        result = await schema_recommendation_service.analyze_query_patterns(
            datasource=request.datasource,
            table_name=request.table_name,
            time_range=timedelta(days=request.time_range_days)
        )
        return AnalyzeResponse(**result)
    except Exception as e:
        logger.error(f"Schema analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/indexes")
async def recommend_indexes(request: IndexRecommendationRequest):
    """推荐索引"""
    try:
        recommendations = await schema_recommendation_service.recommend_indexes(
            datasource=request.datasource,
            table_name=request.table_name
        )
        return {
            "datasource": request.datasource,
            "table_name": request.table_name,
            "recommendations": recommendations,
            "total": len(recommendations)
        }
    except Exception as e:
        logger.error(f"Index recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/partition")
async def recommend_partition(request: PartitionRecommendationRequest):
    """推荐分区策略"""
    try:
        recommendation = await schema_recommendation_service.recommend_partitioning(
            datasource=request.datasource,
            table_name=request.table_name
        )
        return {
            "datasource": request.datasource,
            "table_name": request.table_name,
            "recommendation": recommendation
        }
    except Exception as e:
        logger.error(f"Partition recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/redundancy")
async def detect_redundancy(request: RedundancyDetectionRequest):
    """检测冗余"""
    try:
        findings = await schema_recommendation_service.detect_redundancy(
            datasource=request.datasource,
            table_name=request.table_name
        )
        return {
            "datasource": request.datasource,
            "table_name": request.table_name,
            "findings": findings,
            "total": len(findings)
        }
    except Exception as e:
        logger.error(f"Redundancy detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recommendations(
    datasource: Optional[str] = Query(None, description="数据源过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量")
):
    """获取所有推荐"""
    try:
        recommendations = await schema_recommendation_service.get_all_recommendations(
            datasource=datasource,
            status=status,
            limit=limit
        )
        return {
            "recommendations": recommendations,
            "total": len(recommendations)
        }
    except Exception as e:
        logger.error(f"Get recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations")
async def create_recommendation(request: CreateRecommendationRequest):
    """创建推荐"""
    try:
        rec_id = await schema_recommendation_service.create_recommendation(
            datasource=request.datasource,
            table_name=request.table_name,
            recommendation_type=request.recommendation_type,
            title=request.title,
            description=request.description,
            suggested_sql=request.suggested_sql,
            column_name=request.column_name,
            rationale=request.rationale,
            priority=request.priority
        )
        return {"id": rec_id, "status": "created"}
    except Exception as e:
        logger.error(f"Create recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{id}/apply")
async def apply_recommendation(id: str, request: ApplyRecommendationRequest = None):
    """应用推荐"""
    try:
        dry_run = request.dry_run if request else True
        result = await schema_recommendation_service.apply_recommendation(
            recommendation_id=id,
            dry_run=dry_run
        )
        return result
    except Exception as e:
        logger.error(f"Apply recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{id}/reject")
async def reject_recommendation(id: str, request: RejectRecommendationRequest):
    """拒绝推荐"""
    try:
        success = await schema_recommendation_service.reject_recommendation(
            recommendation_id=id,
            reason=request.reason
        )
        return {"success": success, "recommendation_id": id}
    except Exception as e:
        logger.error(f"Reject recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def schema_recommendation_info():
    """获取 Schema 推荐服务信息"""
    return {
        "service": "Schema Recommendation Service",
        "status": "running" if schema_recommendation_service._initialized else "not initialized",
        "endpoints": {
            "analyze": "/api/schema/analyze",
            "recommend_indexes": "/api/schema/recommend/indexes",
            "recommend_partition": "/api/schema/recommend/partition",
            "detect_redundancy": "/api/schema/detect/redundancy",
            "recommendations": "/api/schema/recommendations"
        }
    }
