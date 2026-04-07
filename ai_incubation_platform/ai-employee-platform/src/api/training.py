"""
P4 训练数据版本化 API

提供:
- 训练数据版本管理
- 增量训练支持
- A/B 测试
- 版本回溯
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from config.database import get_db
from middleware.auth import get_current_user_id, get_current_tenant_id
from services.training_service import (
    TrainingService,
    TrainingDataVersionDB,
    TrainingJobDB,
    ABTestDB,
    TrainingStatus
)

router = APIRouter(prefix="/api/training", tags=["Training"])


def get_training_service(db: Session) -> TrainingService:
    """获取训练服务实例"""
    return TrainingService(db)


# ============== 版本管理 ==============

@router.post("/versions", summary="创建训练版本", response_model=dict)
async def create_version(
    employee_id: str = Body(..., description="AI 员工 ID"),
    version_name: Optional[str] = Body(None, description="版本名称"),
    parent_version_id: Optional[str] = Body(None, description="父版本 ID"),
    training_config: Optional[dict] = Body(None, description="训练配置"),
    description: Optional[str] = Body(None, description="版本描述"),
    changes: Optional[List[str]] = Body(None, description="版本变更内容"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """创建新的训练数据版本"""
    service = get_training_service(db)
    version = service.create_version(
        employee_id=employee_id,
        tenant_id=tenant_id,
        user_id=user_id,
        parent_version_id=parent_version_id,
        version_name=version_name,
        training_config=training_config,
        description=description,
        changes=changes
    )
    return {"version": version.to_dict()}


@router.get("/versions/{version_id}", summary="获取版本详情", response_model=dict)
async def get_version(
    version_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取训练数据版本详情"""
    service = get_training_service(db)
    version = service.get_version(version_id, tenant_id)

    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {"version": version.to_dict()}


@router.get("/versions", summary="列出训练版本", response_model=dict)
async def list_versions(
    employee_id: str = Query(..., description="AI 员工 ID"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """列出 AI 员工的所有训练版本"""
    service = get_training_service(db)
    versions = service.list_versions(employee_id, tenant_id, limit)

    return {
        "versions": [v.to_dict() for v in versions],
        "total": len(versions)
    }


@router.delete("/versions/{version_id}", summary="删除版本", response_model=dict)
async def delete_version(
    version_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """删除训练数据版本（软删除）"""
    service = get_training_service(db)
    success = service.delete_version(version_id, tenant_id)

    if not success:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {"message": "版本已删除"}


@router.post("/versions/{version_id}/activate", summary="激活版本", response_model=dict)
async def activate_version(
    version_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """激活训练数据版本"""
    service = get_training_service(db)
    version = service.activate_version(version_id, tenant_id)

    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {"version": version.to_dict()}


@router.get("/employees/{employee_id}/active-version", summary="获取激活版本", response_model=dict)
async def get_active_version(
    employee_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取 AI 员工当前激活的训练版本"""
    service = get_training_service(db)
    version = service.get_active_version(employee_id, tenant_id)

    return {"version": version.to_dict() if version else None}


# ============== 版本比较与回溯 ==============

@router.post("/versions/compare", summary="比较版本", response_model=dict)
async def compare_versions(
    version_a_id: str = Body(..., description="版本 A ID"),
    version_b_id: str = Body(..., description="版本 B ID"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """比较两个训练版本的差异"""
    service = get_training_service(db)
    comparison = service.compare_versions(version_a_id, version_b_id, tenant_id)

    if not comparison:
        raise HTTPException(status_code=404, detail="一个或两个版本不存在")

    return {"comparison": comparison}


@router.post("/versions/{version_id}/rollback", summary="回滚版本", response_model=dict)
async def rollback_version(
    version_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """回滚到指定版本"""
    service = get_training_service(db)
    version = service.rollback_to_version(version_id, tenant_id, user_id)

    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {"version": version.to_dict()}


@router.get("/versions/{version_id}/lineage", summary="获取版本谱系", response_model=dict)
async def get_version_lineage(
    version_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取版本的祖先和后代"""
    service = get_training_service(db)
    lineage = service.get_version_lineage(version_id, tenant_id)

    if not lineage:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {"lineage": lineage}


# ============== 训练任务管理 ==============

@router.post("/jobs", summary="创建训练任务", response_model=dict)
async def create_training_job(
    version_id: str = Body(..., description="版本 ID"),
    job_name: str = Body(..., description="任务名称"),
    job_type: str = Body(..., description="任务类型 (full_training/fine_tuning/incremental)"),
    training_config: dict = Body(..., description="训练配置"),
    resource_config: Optional[dict] = Body(None, description="资源配置"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """创建训练任务"""
    service = get_training_service(db)
    job = service.create_training_job(
        version_id=version_id,
        tenant_id=tenant_id,
        user_id=user_id,
        job_name=job_name,
        job_type=job_type,
        training_config=training_config,
        resource_config=resource_config
    )
    return {"job": job.to_dict()}


@router.get("/jobs/{job_id}", summary="获取训练任务详情", response_model=dict)
async def get_training_job(
    job_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取训练任务详情"""
    service = get_training_service(db)
    job = service.db.query(TrainingJobDB).filter(
        TrainingJobDB.id == job_id,
        TrainingJobDB.tenant_id == tenant_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    return {"job": job.to_dict()}


@router.post("/jobs/{job_id}/progress", summary="更新训练进度", response_model=dict)
async def update_job_progress(
    job_id: str,
    progress_percent: int = Body(..., ge=0, le=100, description="进度百分比"),
    current_step: Optional[str] = Body(None, description="当前步骤"),
    training_metrics: Optional[dict] = Body(None, description="训练指标"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """更新训练任务进度"""
    service = get_training_service(db)
    job = service.update_job_progress(job_id, tenant_id, progress_percent, current_step, training_metrics)
    return {"job": job.to_dict()}


@router.post("/jobs/{job_id}/complete", summary="完成训练任务", response_model=dict)
async def complete_training_job(
    job_id: str,
    success: bool = Body(..., description="是否成功"),
    final_metrics: Optional[dict] = Body(None, description="最终指标"),
    model_artifact_path: Optional[str] = Body(None, description="模型路径"),
    error_message: Optional[str] = Body(None, description="错误信息"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """完成训练任务"""
    service = get_training_service(db)
    job = service.complete_job(job_id, tenant_id, success, final_metrics, model_artifact_path, error_message)
    return {"job": job.to_dict()}


@router.get("/employees/{employee_id}/jobs", summary="列出训练任务", response_model=dict)
async def list_training_jobs(
    employee_id: str,
    status: Optional[TrainingStatus] = Query(None, description="任务状态"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """列出 AI 员工的训练任务"""
    service = get_training_service(db)
    query = service.db.query(TrainingJobDB).filter(
        TrainingJobDB.employee_id == employee_id,
        TrainingJobDB.tenant_id == tenant_id
    )

    if status:
        query = query.filter(TrainingJobDB.status == status)

    jobs = query.order_by(TrainingJobDB.created_at.desc()).limit(limit).all()

    return {
        "jobs": [j.to_dict() for j in jobs],
        "total": len(jobs)
    }


# ============== A/B 测试 ==============

@router.post("/ab-tests", summary="创建 A/B 测试", response_model=dict)
async def create_ab_test(
    test_name: str = Body(..., description="测试名称"),
    employee_id: str = Body(..., description="AI 员工 ID"),
    variant_a_version_id: str = Body(..., description="版本 A ID"),
    variant_b_version_id: str = Body(..., description="版本 B ID"),
    traffic_split_percent: int = Body(50, ge=0, le=100, description="流量分配百分比"),
    target_metric: Optional[str] = Body(None, description="目标指标"),
    min_sample_size: int = Body(100, ge=10, description="最小样本量"),
    confidence_level: float = Body(0.95, ge=0.9, le=0.99, description="置信水平"),
    description: Optional[str] = Body(None, description="测试描述"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """创建 A/B 测试"""
    service = get_training_service(db)
    test = service.create_ab_test(
        employee_id=employee_id,
        tenant_id=tenant_id,
        user_id=user_id,
        test_name=test_name,
        variant_a_version_id=variant_a_version_id,
        variant_b_version_id=variant_b_version_id,
        traffic_split_percent=traffic_split_percent,
        target_metric=target_metric,
        min_sample_size=min_sample_size,
        confidence_level=confidence_level,
        description=description
    )
    return {"ab_test": test.to_dict()}


@router.get("/ab-tests/{test_id}", summary="获取 A/B 测试详情", response_model=dict)
async def get_ab_test(
    test_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取 A/B 测试详情"""
    service = get_training_service(db)
    test = service.get_ab_test(test_id, tenant_id)

    if not test:
        raise HTTPException(status_code=404, detail="A/B 测试不存在")

    return {"ab_test": test.to_dict()}


@router.get("/employees/{employee_id}/ab-tests", summary="列出 A/B 测试", response_model=dict)
async def list_ab_tests(
    employee_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """列出 AI 员工的 A/B 测试"""
    service = get_training_service(db)
    tests = service.list_ab_tests(employee_id, tenant_id)

    return {
        "ab_tests": [t.to_dict() for t in tests],
        "total": len(tests)
    }


@router.post("/ab-tests/{test_id}/complete", summary="完成 A/B 测试", response_model=dict)
async def complete_ab_test(
    test_id: str,
    variant_a_metrics: dict = Body(..., description="版本 A 指标"),
    variant_b_metrics: dict = Body(..., description="版本 B 指标"),
    winner_version_id: str = Body(..., description="获胜版本 ID"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """完成 A/B 测试"""
    service = get_training_service(db)
    test = service.complete_ab_test(test_id, tenant_id, variant_a_metrics, variant_b_metrics, winner_version_id)
    return {"ab_test": test.to_dict()}


# ============== 统计面板 ==============

@router.get("/dashboard", summary="训练数据看板", response_model=dict)
async def get_training_dashboard(
    employee_id: Optional[str] = Query(None, description="AI 员工 ID"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取训练数据看板"""
    service = get_training_service(db)

    # 版本统计
    if employee_id:
        versions = service.list_versions(employee_id, tenant_id, limit=100)
    else:
        # 租户下所有 AI 员工的版本
        versions = service.db.query(TrainingDataVersionDB).filter(
            TrainingDataVersionDB.tenant_id == tenant_id,
            TrainingDataVersionDB.is_deleted == False
        ).all()

    # 状态统计
    status_counts = {}
    for v in versions:
        status = v.training_status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    # 训练任务统计
    employee_ids = list(set(v.employee_id for v in versions))
    jobs = service.db.query(TrainingJobDB).filter(
        TrainingJobDB.tenant_id == tenant_id,
        TrainingJobDB.employee_id.in_(employee_ids) if employee_ids else TrainingJobDB.id.isnot(None)
    ).all()

    job_status_counts = {}
    for j in jobs:
        status = j.status.value
        job_status_counts[status] = job_status_counts.get(status, 0) + 1

    # A/B 测试统计
    ab_tests = service.db.query(ABTestDB).filter(
        ABTestDB.tenant_id == tenant_id,
        ABTestDB.employee_id.in_(employee_ids) if employee_ids else ABTestDB.id.isnot(None)
    ).all()

    ab_status_counts = {}
    for t in ab_tests:
        status = t.status
        ab_status_counts[status] = ab_status_counts.get(status, 0) + 1

    return {
        "dashboard": {
            "tenant_id": tenant_id,
            "total_versions": len(versions),
            "version_status_breakdown": status_counts,
            "total_jobs": len(jobs),
            "job_status_breakdown": job_status_counts,
            "total_ab_tests": len(ab_tests),
            "ab_test_status_breakdown": ab_status_counts,
            "active_versions": sum(1 for v in versions if v.is_active)
        }
    }
