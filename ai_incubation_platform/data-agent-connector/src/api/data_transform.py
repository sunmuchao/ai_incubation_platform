"""
数据转换和 dbt 集成 API
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from services.transform_service import (
    TransformConfig, TransformType, TransformJob,
    QualityRule, QualityCheckType, DataQualityChecker,
    TransformTemplateLibrary, TransformConfig,
    start_transform_service, stop_transform_service
)
from services.dbt_service import (
    DbtIntegrationService,
    start_dbt_service, stop_dbt_service
)
from services.cdc_service import (
    CDCConfig, CDCService, ChangeEventType,
    cdc_service
)
from utils.logger import logger

router = APIRouter(prefix="/api/data", tags=["数据转换与 dbt 集成"])

# 全局服务实例
quality_checker = DataQualityChecker()
dbt_service = DbtIntegrationService()
cdc_service = CDCService()


# ==================== CDC API ====================

class CreateCDCJobRequest(BaseModel):
    name: str
    source_type: str = Field(..., description="数据源类型：mysql 或 postgresql")
    source_host: str
    source_port: int
    source_user: str
    source_password: str
    source_database: str
    tables: List[str] = Field(default_factory=list)
    exclude_tables: List[str] = Field(default_factory=list)
    batch_size: int = Field(default=100)


class CreateCDCJobResponse(BaseModel):
    job_name: str
    status: str
    message: str


@router.post("/cdc/jobs", response_model=CreateCDCJobResponse)
async def create_cdc_job(request: CreateCDCJobRequest):
    """创建 CDC 数据复制任务"""
    try:
        config = CDCConfig(
            name=request.name,
            source_type=request.source_type,
            source_host=request.source_host,
            source_port=request.source_port,
            source_user=request.source_user,
            source_password=request.source_password,
            source_database=request.source_database,
            tables=request.tables,
            exclude_tables=request.exclude_tables,
            batch_size=request.batch_size
        )

        job_name = await cdc_service.create_job(config)

        return CreateCDCJobResponse(
            job_name=job_name,
            status="created",
            message=f"CDC job '{job_name}' created successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create CDC job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cdc/jobs/{job_name}/start")
async def start_cdc_job(job_name: str):
    """启动 CDC 任务"""
    try:
        await cdc_service.start_job(job_name)
        return {"status": "started", "job_name": job_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start CDC job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cdc/jobs/{job_name}/stop")
async def stop_cdc_job(job_name: str):
    """停止 CDC 任务"""
    try:
        await cdc_service.stop_job(job_name)
        return {"status": "stopped", "job_name": job_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to stop CDC job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cdc/jobs/{job_name}")
async def delete_cdc_job(job_name: str):
    """删除 CDC 任务"""
    try:
        await cdc_service.delete_job(job_name)
        return {"status": "deleted", "job_name": job_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete CDC job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cdc/jobs")
async def list_cdc_jobs():
    """列出所有 CDC 任务"""
    try:
        jobs = await cdc_service.list_jobs()
        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Failed to list CDC jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cdc/jobs/{job_name}/status")
async def get_cdc_job_status(job_name: str):
    """获取 CDC 任务状态"""
    try:
        status = await cdc_service.get_job_status(job_name)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get CDC job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据转换 API ====================

class CreateTransformJobRequest(BaseModel):
    name: str
    transform_type: TransformType
    source_tables: List[str]
    target_table: str
    config: Dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = None


class TransformExecuteRequest(BaseModel):
    data: List[Dict[str, Any]]


@router.post("/transform/jobs")
async def create_transform_job(request: CreateTransformJobRequest):
    """创建数据转换任务"""
    try:
        config = TransformConfig(
            name=request.name,
            transform_type=request.transform_type,
            source_tables=request.source_tables,
            target_table=request.target_table,
            config=request.config,
            schedule=request.schedule
        )

        job = TransformJob(config, quality_checker)

        return {
            "status": "created",
            "job_name": request.name,
            "transform_type": request.transform_type.value
        }
    except Exception as e:
        logger.error(f"Failed to create transform job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transform/jobs/{job_name}/execute")
async def execute_transform_job(job_name: str, request: TransformExecuteRequest):
    """执行数据转换任务"""
    # 注意：实际实现需要从存储中获取 job
    # 这里是简化演示
    try:
        config = TransformConfig(
            name=job_name,
            transform_type=TransformType.PYTHON,
            source_tables=[],
            target_table=""
        )
        job = TransformJob(config, quality_checker)

        result, execution = await job.execute(request.data)

        return {
            "status": execution.status.value,
            "result": result,
            "execution": {
                "input_rows": execution.input_rows,
                "output_rows": execution.output_rows,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "ended_at": execution.ended_at.isoformat() if execution.ended_at else None,
                "error_message": execution.error_message
            }
        }
    except Exception as e:
        logger.error(f"Failed to execute transform job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transform/quality-check")
async def execute_quality_check(
    data: List[Dict[str, Any]],
    rules: Optional[List[str]] = Query(None)
):
    """执行数据质量检查"""
    try:
        results = await quality_checker.check(data, rules)
        return {
            "results": [
                {
                    "rule_name": r.rule_name,
                    "table_name": r.table_name,
                    "column_name": r.column_name,
                    "passed": r.passed,
                    "checked_rows": r.checked_rows,
                    "failed_rows": r.failed_rows,
                    "error_rate": r.error_rate,
                    "error_message": r.error_message
                }
                for r in results
            ],
            "summary": {
                "total_rules": len(results),
                "passed_rules": sum(1 for r in results if r.passed),
                "failed_rules": sum(1 for r in results if not r.passed)
            }
        }
    except Exception as e:
        logger.error(f"Failed to execute quality check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transform/templates")
async def list_transform_templates():
    """列出所有转换模板"""
    templates = TransformTemplateLibrary.list_templates()
    return {"templates": templates}


@router.post("/transform/jobs/from-template/{template_name}")
async def create_job_from_template(
    template_name: str,
    job_name: str,
    source_tables: List[str],
    target_table: str
):
    """从模板创建转换任务"""
    try:
        job = TransformTemplateLibrary.create_job_from_template(
            template_name=template_name,
            job_name=job_name,
            source_tables=source_tables,
            target_table=target_table
        )

        return {
            "status": "created",
            "job_name": job_name,
            "template_name": template_name
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create job from template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== dbt 集成 API ====================

class RegisterDbtProjectRequest(BaseModel):
    project_root: str
    project_name: Optional[str] = None


class RegisterDbtCloudProjectRequest(BaseModel):
    project_name: str
    api_key: str
    account_id: int
    dbt_project_id: int


class TriggerDbtJobRequest(BaseModel):
    project_name: str
    job_id: int
    cause: str = Field(default="API trigger", description="触发原因")


@router.post("/dbt/projects/register")
async def register_dbt_project(request: RegisterDbtProjectRequest):
    """注册本地 dbt 项目"""
    try:
        project_name = await dbt_service.register_project(
            request.project_root,
            request.project_name
        )
        return {
            "status": "registered",
            "project_name": project_name
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register dbt project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dbt/projects/cloud/register")
async def register_dbt_cloud_project(request: RegisterDbtCloudProjectRequest):
    """注册 dbt Cloud 项目"""
    try:
        project_name = await dbt_service.register_cloud_project(
            request.project_name,
            request.api_key,
            request.account_id,
            request.dbt_project_id
        )
        return {
            "status": "registered",
            "project_name": project_name
        }
    except Exception as e:
        logger.error(f"Failed to register dbt Cloud project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dbt/projects/{project_name}/models")
async def get_dbt_project_models(project_name: str):
    """获取 dbt 项目模型列表"""
    try:
        models = await dbt_service.get_project_models(project_name)
        return {"models": models}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get dbt models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dbt/projects/{project_name}/sources")
async def get_dbt_project_sources(project_name: str):
    """获取 dbt 项目源列表"""
    try:
        sources = await dbt_service.get_project_sources(project_name)
        return {"sources": sources}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get dbt sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dbt/projects/{project_name}/lineage")
async def get_dbt_lineage(
    project_name: str,
    node_id: str = Query(..., description="节点 ID")
):
    """获取 dbt 节点血缘关系"""
    try:
        lineage = await dbt_service.get_lineage(project_name, node_id)
        return lineage
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get lineage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dbt/projects/{project_name}/lineage/summary")
async def get_dbt_lineage_summary(project_name: str):
    """获取 dbt 项目血缘统计"""
    try:
        summary = await dbt_service.get_lineage_summary(project_name)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get lineage summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dbt/jobs/trigger")
async def trigger_dbt_job(request: TriggerDbtJobRequest):
    """触发 dbt Cloud 任务"""
    try:
        result = await dbt_service.trigger_job(
            request.project_name,
            request.job_id,
            request.cause
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to trigger dbt job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dbt/runs/{run_id}/status")
async def get_dbt_run_status(run_id: int):
    """获取 dbt 运行状态"""
    try:
        status = await dbt_service.get_run_status(run_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get run status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dbt/projects/{project_name}/search")
async def search_dbt_models(
    project_name: str,
    q: str = Query(..., description="搜索关键词")
):
    """搜索 dbt 模型"""
    try:
        results = await dbt_service.search_models(project_name, q)
        return {"results": results, "total": len(results)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to search models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 服务生命周期 ====================

@router.on_event("startup")
async def startup():
    """服务启动"""
    await start_transform_service()
    await start_dbt_service()
    await cdc_service.start()
    logger.info("Data transform and dbt service started")


@router.on_event("shutdown")
async def shutdown():
    """服务关闭"""
    await stop_transform_service()
    await stop_dbt_service()
    await cdc_service.stop()
    logger.info("Data transform and dbt service stopped")
