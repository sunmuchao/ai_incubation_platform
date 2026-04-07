"""
数据治理 API

提供数据分类、标签、敏感数据识别、脱敏策略和治理仪表板的 HTTP 接口
"""
from fastapi import APIRouter, HTTPException, Query, Body, Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.data_governance_service import data_governance_service
from utils.logger import logger

router = APIRouter(prefix="/api/governance", tags=["Data Governance"])


# ==================== 请求/响应模型 ====================

class CreateClassificationRequest(BaseModel):
    """创建分类请求"""
    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    parent_id: Optional[str] = Field(None, description="父分类 ID")
    level: int = Field(default=1, ge=1, le=4, description="分类级别 (1-4)")
    tags: Optional[List[str]] = Field(None, description="分类标签")


class AddLabelRequest(BaseModel):
    """添加标签请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    column_name: Optional[str] = Field(None, description="列名")
    label_type: str = Field(..., description="标签类型 (classification/sensitivity/business/custom)")
    label_key: str = Field(..., description="标签键")
    label_value: Optional[str] = Field(None, description="标签值")


class ScanSensitiveDataRequest(BaseModel):
    """扫描敏感数据请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    columns: Optional[List[str]] = Field(None, description="指定列列表")
    sample_size: int = Field(default=1000, ge=100, le=10000, description="采样数量")


class CreateMaskingPolicyRequest(BaseModel):
    """创建脱敏策略请求"""
    name: str = Field(..., description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    masking_type: str = Field(..., description="脱敏类型 (full/partial/hash/encrypt/redact)")
    sensitivity_level: Optional[str] = Field(None, description="适用敏感级别")
    data_type: Optional[str] = Field(None, description="适用数据类型")
    column_pattern: Optional[str] = Field(None, description="列名匹配模式")
    masking_params: Optional[Dict[str, Any]] = Field(None, description="脱敏参数")
    priority: int = Field(default=100, ge=1, description="优先级")


class ApplyMaskingRequest(BaseModel):
    """应用脱敏请求"""
    policy_id: str = Field(..., description="策略 ID")
    value: Any = Field(..., description="要脱敏的值")


class ReviewSensitiveRecordRequest(BaseModel):
    """审核敏感记录请求"""
    is_confirmed: bool = Field(..., description="是否确认敏感")
    review_notes: Optional[str] = Field(None, description="审核备注")


# ==================== 分类管理 ====================

@router.post("/classifications")
async def create_classification(request: CreateClassificationRequest, user_id: str = Query(None)):
    """创建数据分类"""
    try:
        classification_id = await data_governance_service.create_classification(
            name=request.name,
            description=request.description,
            parent_id=request.parent_id,
            level=request.level,
            tags=request.tags,
            created_by=user_id
        )
        return {"id": classification_id, "status": "created"}
    except Exception as e:
        logger.error(f"Create classification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classifications")
async def list_classifications(
    parent_id: Optional[str] = Query(None),
    level: Optional[int] = Query(None),
    is_active: bool = Query(True)
):
    """列出数据分类"""
    try:
        classifications = await data_governance_service.list_classifications(
            parent_id=parent_id,
            level=level,
            is_active=is_active
        )
        return {
            "classifications": [c.to_dict() for c in classifications],
            "total": len(classifications)
        }
    except Exception as e:
        logger.error(f"List classifications failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classifications/tree")
async def get_classification_tree():
    """获取分类树"""
    try:
        tree = await data_governance_service.get_classification_tree()
        return {"tree": tree}
    except Exception as e:
        logger.error(f"Get classification tree failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/classifications/{classification_id}")
async def delete_classification(classification_id: str = Path(...)):
    """删除分类"""
    try:
        success = await data_governance_service.delete_classification(classification_id)
        return {"success": success, "id": classification_id}
    except Exception as e:
        logger.error(f"Delete classification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 标签管理 ====================

@router.post("/labels")
async def add_label(request: AddLabelRequest, user_id: str = Query(None)):
    """添加数据标签"""
    try:
        label_id = await data_governance_service.add_label(
            datasource=request.datasource,
            table_name=request.table_name,
            column_name=request.column_name,
            label_type=request.label_type,
            label_key=request.label_key,
            label_value=request.label_value,
            created_by=user_id
        )
        return {"id": label_id, "status": "created"}
    except Exception as e:
        logger.error(f"Add label failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/labels")
async def get_labels(
    datasource: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    column_name: Optional[str] = Query(None),
    label_type: Optional[str] = Query(None)
):
    """获取标签列表"""
    try:
        labels = await data_governance_service.get_labels(
            datasource=datasource,
            table_name=table_name,
            column_name=column_name,
            label_type=label_type
        )
        return {
            "labels": [l.to_dict() for l in labels],
            "total": len(labels)
        }
    except Exception as e:
        logger.error(f"Get labels failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/labels/{label_id}")
async def remove_label(label_id: str = Path(...)):
    """移除标签"""
    try:
        success = await data_governance_service.remove_label(label_id)
        return {"success": success, "id": label_id}
    except Exception as e:
        logger.error(f"Remove label failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 敏感级别管理 ====================

@router.get("/sensitivity-levels")
async def list_sensitivity_levels():
    """获取敏感级别列表"""
    try:
        levels = await data_governance_service.list_sensitivity_levels()
        return {
            "sensitivity_levels": [l.to_dict() for l in levels]
        }
    except Exception as e:
        logger.error(f"List sensitivity levels failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 敏感数据识别 ====================

@router.post("/scan-sensitive")
async def scan_sensitive_data(request: ScanSensitiveDataRequest, user_id: str = Query(None)):
    """扫描敏感数据"""
    try:
        results = await data_governance_service.scan_sensitive_data(
            datasource=request.datasource,
            table_name=request.table_name,
            columns=request.columns,
            sample_size=request.sample_size
        )
        return {
            "results": results,
            "total": len(results),
            "scanned_by": user_id
        }
    except Exception as e:
        logger.error(f"Scan sensitive data failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sensitive-records")
async def get_sensitive_records(
    datasource: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    sensitivity_level: Optional[str] = Query(None),
    is_masked: Optional[bool] = Query(None),
    is_reviewed: Optional[bool] = Query(None),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """获取敏感数据记录"""
    try:
        records = await data_governance_service.get_sensitive_records(
            datasource=datasource,
            table_name=table_name,
            sensitivity_level=sensitivity_level,
            is_masked=is_masked,
            is_reviewed=is_reviewed,
            limit=limit
        )
        return {
            "records": [r.to_dict() for r in records],
            "total": len(records)
        }
    except Exception as e:
        logger.error(f"Get sensitive records failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sensitive-records/{record_id}/review")
async def review_sensitive_record(
    record_id: str = Path(...),
    request: ReviewSensitiveRecordRequest = Body(...),
    user_id: str = Query(None)
):
    """审核敏感数据记录"""
    try:
        success = await data_governance_service.review_sensitive_record(
            record_id=record_id,
            is_confirmed=request.is_confirmed,
            reviewed_by=user_id,
            review_notes=request.review_notes
        )
        return {"success": success, "record_id": record_id}
    except Exception as e:
        logger.error(f"Review sensitive record failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 脱敏策略 ====================

@router.post("/masking-policies")
async def create_masking_policy(request: CreateMaskingPolicyRequest, user_id: str = Query(None)):
    """创建脱敏策略"""
    try:
        policy_id = await data_governance_service.create_masking_policy(
            name=request.name,
            description=request.description,
            masking_type=request.masking_type,
            sensitivity_level=request.sensitivity_level,
            data_type=request.data_type,
            column_pattern=request.column_pattern,
            masking_params=request.masking_params,
            priority=request.priority,
            created_by=user_id
        )
        return {"id": policy_id, "status": "created"}
    except Exception as e:
        logger.error(f"Create masking policy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/masking-policies")
async def list_masking_policies(
    sensitivity_level: Optional[str] = Query(None),
    is_active: bool = Query(True)
):
    """列出脱敏策略"""
    try:
        policies = await data_governance_service.list_masking_policies(
            sensitivity_level=sensitivity_level,
            is_active=is_active
        )
        return {
            "policies": [p.to_dict() for p in policies],
            "total": len(policies)
        }
    except Exception as e:
        logger.error(f"List masking policies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/masking/apply")
async def apply_masking(request: ApplyMaskingRequest):
    """应用脱敏"""
    try:
        # 获取策略
        policies = await data_governance_service.list_masking_policies()
        policy = None
        for p in policies:
            if p.id == request.policy_id:
                policy = p
                break

        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        masked_value = await data_governance_service.apply_masking(
            value=request.value,
            policy=policy
        )
        return {
            "original": str(request.value)[:20] + "..." if len(str(request.value)) > 20 else request.value,
            "masked": masked_value,
            "policy": policy.name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Apply masking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/masking-policies/{policy_id}")
async def delete_masking_policy(policy_id: str = Path(...)):
    """删除脱敏策略"""
    try:
        success = await data_governance_service.delete_masking_policy(policy_id)
        return {"success": success, "id": policy_id}
    except Exception as e:
        logger.error(f"Delete masking policy failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 治理指标 ====================

@router.get("/score")
async def get_governance_score(datasource: Optional[str] = Query(None)):
    """获取治理分数"""
    try:
        scores = await data_governance_service.calculate_governance_score(datasource)
        return scores
    except Exception as e:
        logger.error(f"Get governance score failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics")
async def record_metric(
    metric_type: str = Query(...),
    metric_value: float = Query(...),
    datasource: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    target_value: Optional[float] = Query(None),
    period_type: str = Query(default="day"),
    user_id: str = Query(None)
):
    """记录治理指标"""
    try:
        metric_id = await data_governance_service.record_governance_metric(
            metric_type=metric_type,
            metric_value=metric_value,
            datasource=datasource,
            table_name=table_name,
            target_value=target_value,
            period_type=period_type,
            created_by=user_id
        )
        return {"id": metric_id, "status": "recorded"}
    except Exception as e:
        logger.error(f"Record metric failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 治理仪表板 ====================

@router.get("/dashboard")
async def get_governance_dashboard(datasource: Optional[str] = Query(None)):
    """获取治理仪表板"""
    try:
        dashboard = await data_governance_service.get_governance_dashboard(datasource)
        return dashboard
    except Exception as e:
        logger.error(f"Get governance dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 服务信息 ====================

@router.get("/")
async def data_governance_info():
    """获取数据治理服务信息"""
    return {
        "service": "Data Governance Service",
        "status": "running" if data_governance_service._initialized else "not initialized",
        "features": [
            "数据分类管理",
            "数据标签管理",
            "敏感数据识别",
            "脱敏策略管理",
            "治理指标统计",
            "治理仪表板"
        ],
        "endpoints": {
            "classifications": "/api/governance/classifications",
            "labels": "/api/governance/labels",
            "sensitivity-levels": "/api/governance/sensitivity-levels",
            "scan-sensitive": "/api/governance/scan-sensitive",
            "sensitive-records": "/api/governance/sensitive-records",
            "masking-policies": "/api/governance/masking-policies",
            "score": "/api/governance/score",
            "dashboard": "/api/governance/dashboard"
        }
    }
