"""
数据质量 API

提供数据质量检查和监控的 HTTP 接口
"""
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.data_quality_service import data_quality_service
from utils.logger import logger

router = APIRouter(prefix="/api/quality", tags=["Data Quality"])


# ==================== 请求/响应模型 ====================

class CreateRuleRequest(BaseModel):
    """创建规则请求"""
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    column_name: Optional[str] = Field(None, description="列名")
    rule_type: str = Field(..., description="规则类型")
    rule_expression: str = Field(..., description="规则表达式")
    threshold: Optional[float] = Field(None, description="阈值")
    severity: str = Field(default="warning", description="严重级别")
    schedule_enabled: bool = Field(default=False, description="是否启用调度")
    schedule_cron: Optional[str] = Field(None, description="Cron 表达式")


class RuleResponse(BaseModel):
    """规则响应"""
    id: str
    name: str
    description: Optional[str]
    datasource: str
    table_name: str
    column_name: Optional[str]
    rule_type: str
    is_active: bool
    created_at: str


class CompletenessCheckRequest(BaseModel):
    """完整性检查请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    columns: Optional[List[str]] = Field(None, description="列列表")
    threshold: float = Field(default=0.95, ge=0, le=1, description="完整性阈值")


class AccuracyCheckRequest(BaseModel):
    """准确性检查请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    rules: List[Dict[str, Any]] = Field(..., description="规则列表")


class ConsistencyCheckRequest(BaseModel):
    """一致性检查请求"""
    source_datasource: str = Field(..., description="源数据源")
    target_datasource: str = Field(..., description="目标数据源")
    table_name: str = Field(..., description="表名")
    key_columns: List[str] = Field(..., description="关键列")


class TimelinessCheckRequest(BaseModel):
    """及时性检查请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    timestamp_column: str = Field(..., description="时间戳列")
    max_delay_hours: int = Field(default=24, ge=1, description="最大延迟小时数")


class AnomalyDetectionRequest(BaseModel):
    """异常检测请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    column: str = Field(..., description="列名")
    time_range_days: int = Field(default=7, ge=1, description="时间范围（天）")


class CheckResultResponse(BaseModel):
    """检查结果响应"""
    status: str
    metrics: Dict[str, Any]
    execution_time_ms: int
    error: Optional[str] = None


class ExecuteRuleRequest(BaseModel):
    """执行规则请求"""
    rule_id: str = Field(..., description="规则 ID")


# ==================== 端点 ====================

@router.post("/rules", response_model=Dict[str, str])
async def create_rule(request: CreateRuleRequest):
    """创建质量规则"""
    try:
        rule_id = await data_quality_service.create_rule(
            name=request.name,
            description=request.description,
            datasource=request.datasource,
            table_name=request.table_name,
            column_name=request.column_name,
            rule_type=request.rule_type,
            rule_expression=request.rule_expression,
            threshold=request.threshold,
            severity=request.severity,
            schedule_enabled=request.schedule_enabled,
            schedule_cron=request.schedule_cron
        )
        return {"id": rule_id, "status": "created"}
    except Exception as e:
        logger.error(f"Create rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules")
async def list_rules(
    datasource: Optional[str] = Query(None, description="数据源过滤"),
    table_name: Optional[str] = Query(None, description="表名过滤"),
    rule_type: Optional[str] = Query(None, description="规则类型过滤"),
    is_active: bool = Query(True, description="是否仅活跃规则")
):
    """列出质量规则"""
    try:
        rules = await data_quality_service.list_rules(
            datasource=datasource,
            table_name=table_name,
            rule_type=rule_type,
            is_active=is_active
        )
        return {
            "rules": [rule.to_dict() for rule in rules],
            "total": len(rules)
        }
    except Exception as e:
        logger.error(f"List rules failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """获取规则详情"""
    try:
        rule = await data_quality_service.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        return rule.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """删除规则"""
    try:
        success = await data_quality_service.delete_rule(rule_id)
        return {"success": success, "rule_id": rule_id}
    except Exception as e:
        logger.error(f"Delete rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check/completeness", response_model=CheckResultResponse)
async def check_completeness(request: CompletenessCheckRequest):
    """完整性检查"""
    try:
        result = await data_quality_service.check_completeness(
            datasource=request.datasource,
            table_name=request.table_name,
            columns=request.columns,
            threshold=request.threshold
        )
        return CheckResultResponse(
            status=result.get("status", "unknown"),
            metrics=result.get("metrics", {}),
            execution_time_ms=result.get("execution_time_ms", 0),
            error=result.get("error")
        )
    except Exception as e:
        logger.error(f"Completeness check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check/accuracy", response_model=CheckResultResponse)
async def check_accuracy(request: AccuracyCheckRequest):
    """准确性检查"""
    try:
        result = await data_quality_service.check_accuracy(
            datasource=request.datasource,
            table_name=request.table_name,
            rules=request.rules
        )
        return CheckResultResponse(
            status=result.get("status", "unknown"),
            metrics=result.get("metrics", {}),
            execution_time_ms=result.get("execution_time_ms", 0),
            error=result.get("error")
        )
    except Exception as e:
        logger.error(f"Accuracy check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check/consistency", response_model=CheckResultResponse)
async def check_consistency(request: ConsistencyCheckRequest):
    """一致性检查"""
    try:
        result = await data_quality_service.check_consistency(
            source_datasource=request.source_datasource,
            target_datasource=request.target_datasource,
            table_name=request.table_name,
            key_columns=request.key_columns
        )
        return CheckResultResponse(
            status=result.get("status", "unknown"),
            metrics=result.get("metrics", {}),
            execution_time_ms=result.get("execution_time_ms", 0),
            error=result.get("error")
        )
    except Exception as e:
        logger.error(f"Consistency check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check/timeliness", response_model=CheckResultResponse)
async def check_timeliness(request: TimelinessCheckRequest):
    """及时性检查"""
    try:
        result = await data_quality_service.check_timeliness(
            datasource=request.datasource,
            table_name=request.table_name,
            timestamp_column=request.timestamp_column,
            max_delay_hours=request.max_delay_hours
        )
        return CheckResultResponse(
            status=result.get("status", "unknown"),
            metrics=result.get("metrics", {}),
            execution_time_ms=result.get("execution_time_ms", 0),
            error=result.get("error")
        )
    except Exception as e:
        logger.error(f"Timeliness check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/anomalies")
async def detect_anomalies(request: AnomalyDetectionRequest):
    """异常检测"""
    try:
        from datetime import timedelta
        anomalies = await data_quality_service.detect_anomalies(
            datasource=request.datasource,
            table_name=request.table_name,
            column=request.column,
            time_range=timedelta(days=request.time_range_days)
        )
        return {
            "anomalies": anomalies,
            "total": len(anomalies)
        }
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/execute")
async def execute_rule(request: ExecuteRuleRequest):
    """执行质量规则"""
    try:
        result = await data_quality_service.execute_rule(request.rule_id)
        return result
    except Exception as e:
        logger.error(f"Rule execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results")
async def get_results(
    rule_id: Optional[str] = Query(None, description="规则 ID 过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    hours: int = Query(default=24, ge=1, description="时间范围（小时）"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回数量")
):
    """获取检查结果"""
    try:
        results = await data_quality_service.get_results(
            rule_id=rule_id,
            status=status,
            hours=hours,
            limit=limit
        )
        return {
            "results": [r.to_dict() for r in results],
            "total": len(results)
        }
    except Exception as e:
        logger.error(f"Get results failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies")
async def get_anomalies(
    datasource: Optional[str] = Query(None, description="数据源过滤"),
    table_name: Optional[str] = Query(None, description="表名过滤"),
    is_resolved: bool = Query(False, description="是否已解决"),
    hours: int = Query(default=24, ge=1, description="时间范围（小时）"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回数量")
):
    """获取异常记录"""
    try:
        anomalies = await data_quality_service.get_anomalies(
            datasource=datasource,
            table_name=table_name,
            is_resolved=is_resolved,
            hours=hours,
            limit=limit
        )
        return {
            "anomalies": [a.to_dict() for a in anomalies],
            "total": len(anomalies)
        }
    except Exception as e:
        logger.error(f"Get anomalies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def data_quality_info():
    """获取数据质量服务信息"""
    return {
        "service": "Data Quality Service",
        "status": "running" if data_quality_service._initialized else "not initialized",
        "endpoints": {
            "rules": "/api/quality/rules",
            "check_completeness": "/api/quality/check/completeness",
            "check_accuracy": "/api/quality/check/accuracy",
            "check_consistency": "/api/quality/check/consistency",
            "check_timeliness": "/api/quality/check/timeliness",
            "detect_anomalies": "/api/quality/detect/anomalies",
            "execute_rule": "/api/quality/rules/execute",
            "results": "/api/quality/results",
            "anomalies": "/api/quality/anomalies"
        }
    }
