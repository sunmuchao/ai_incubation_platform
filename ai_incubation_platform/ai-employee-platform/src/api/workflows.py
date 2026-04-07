"""
P9-002: 自动化工作流 API

API 端点:
- POST /api/workflows - 创建工作流
- GET /api/workflows - 获取工作流列表
- GET /api/workflows/{id} - 获取工作流详情
- PUT /api/workflows/{id} - 更新工作流
- DELETE /api/workflows/{id} - 删除工作流
- POST /api/workflows/{id}/execute - 执行工作流
- GET /api/workflows/{id}/executions - 获取执行历史
- GET /api/workflows/{id}/executions/{execution_id} - 获取执行详情
- GET /api/workflow-templates - 获取模板列表
- POST /api/workflow-templates - 创建模板
"""

import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from datetime import datetime

from models.p9_models import (
    Workflow,
    WorkflowStatus,
    WorkflowExecution,
    ExecutionStatus,
    ExecuteWorkflowRequest,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowExecutionResponse,
    WorkflowExecutionListResponse,
    WorkflowTemplate,
    WorkflowTemplateResponse,
    WorkflowTemplateListResponse,
)
from services.workflow_engine import workflow_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["自动化工作流"])


# ==================== 工作流管理 API ====================

@router.post("", response_model=WorkflowResponse)
async def create_workflow(
    workflow_data: dict = Body(..., description="工作流定义数据"),
    tenant_id: str = Body(..., description="租户 ID"),
    created_by: str = Body(..., description="创建者 ID")
):
    """
    创建工作流

    请求体:
    - **name**: 工作流名称
    - **description**: 工作流描述
    - **nodes**: 节点列表
    - **edges**: 边列表
    - **input_schema**: 输入参数定义
    - **output_schema**: 输出参数定义
    """
    try:
        # 创建工作流对象
        workflow = Workflow(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            created_by=created_by,
            name=workflow_data.get("name", "Unnamed Workflow"),
            description=workflow_data.get("description", ""),
            version=workflow_data.get("version", "1.0.0"),
            nodes=workflow_data.get("nodes", []),
            edges=workflow_data.get("edges", []),
            input_schema=workflow_data.get("input_schema", {}),
            output_schema=workflow_data.get("output_schema", {}),
            timeout_seconds=workflow_data.get("timeout_seconds", 3600),
            error_handling=workflow_data.get("error_handling", "fail_fast"),
        )

        # 保存工作流
        success, message = workflow_engine.save_workflow(workflow)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return WorkflowResponse(
            success=True,
            workflow=workflow,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建工作流失败：{e}")
        raise HTTPException(status_code=500, detail=f"创建工作流失败：{str(e)}")


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    tenant_id: str = Query(..., description="租户 ID"),
    status: Optional[WorkflowStatus] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取工作流列表

    - **tenant_id**: 租户 ID
    - **status**: 可选，状态筛选
    """
    try:
        workflows = workflow_engine.list_workflows(tenant_id, status)

        # 分页
        total = len(workflows)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_workflows = workflows[start:end]

        return WorkflowListResponse(
            success=True,
            workflows=paginated_workflows,
            total=total,
            page=page,
            page_size=page_size,
            message=f"成功获取 {len(paginated_workflows)} 个工作流"
        )
    except Exception as e:
        logger.error(f"获取工作流列表失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取工作流列表失败：{str(e)}")


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str):
    """
    获取工作流详情

    - **workflow_id**: 工作流 ID
    """
    workflow = workflow_engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流不存在：{workflow_id}")

    return WorkflowResponse(
        success=True,
        workflow=workflow,
        message="成功获取工作流详情"
    )


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    workflow_data: dict = Body(..., description="工作流更新数据")
):
    """
    更新工作流

    - **workflow_id**: 工作流 ID
    """
    workflow = workflow_engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流不存在：{workflow_id}")

    try:
        # 更新字段
        workflow.name = workflow_data.get("name", workflow.name)
        workflow.description = workflow_data.get("description", workflow.description)
        workflow.nodes = workflow_data.get("nodes", workflow.nodes)
        workflow.edges = workflow_data.get("edges", workflow.edges)
        workflow.input_schema = workflow_data.get("input_schema", workflow.input_schema)
        workflow.output_schema = workflow_data.get("output_schema", workflow.output_schema)
        workflow.timeout_seconds = workflow_data.get("timeout_seconds", workflow.timeout_seconds)
        workflow.error_handling = workflow_data.get("error_handling", workflow.error_handling)
        workflow.version = workflow_data.get("version", workflow.version)
        workflow.updated_at = datetime.now()

        # 验证并保存
        success, message = workflow_engine.save_workflow(workflow)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return WorkflowResponse(
            success=True,
            workflow=workflow,
            message="工作流更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新工作流失败：{e}")
        raise HTTPException(status_code=500, detail=f"更新工作流失败：{str(e)}")


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """
    删除工作流

    - **workflow_id**: 工作流 ID
    """
    workflow = workflow_engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流不存在：{workflow_id}")

    # 只能删除草稿或归档状态的工作流
    if workflow.status == WorkflowStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="不能删除激活状态的工作流，请先归档"
        )

    try:
        del workflow_engine._workflows[workflow_id]
        return {"success": True, "message": f"工作流 {workflow_id} 已删除"}
    except Exception as e:
        logger.error(f"删除工作流失败：{e}")
        raise HTTPException(status_code=500, detail=f"删除工作流失败：{str(e)}")


@router.post("/{workflow_id}/activate")
async def activate_workflow(workflow_id: str):
    """
    激活工作流

    - **workflow_id**: 工作流 ID
    """
    workflow = workflow_engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流不存在：{workflow_id}")

    success, message = workflow_engine.activate_workflow(workflow_id)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@router.post("/{workflow_id}/archive")
async def archive_workflow(workflow_id: str):
    """
    归档工作流

    - **workflow_id**: 工作流 ID
    """
    workflow = workflow_engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流不存在：{workflow_id}")

    success, message = workflow_engine.archive_workflow(workflow_id)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


# ==================== 工作流执行 API ====================

@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    tenant_id: str = Query(..., description="租户 ID"),
    triggered_by: str = Query(..., description="触发者 ID")
):
    """
    执行工作流

    - **workflow_id**: 工作流 ID
    - **input_data**: 输入数据
    - **trigger_type**: 触发类型 (manual, api, scheduled, event)
    """
    import asyncio

    workflow = workflow_engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail=f"工作流不存在：{workflow_id}")

    try:
        # 异步执行工作流
        execution = await workflow_engine.execute_workflow(
            workflow_id,
            request,
            tenant_id,
            triggered_by
        )

        return WorkflowExecutionResponse(
            success=True,
            execution=execution,
            message=f"工作流执行{'完成' if execution.status == ExecutionStatus.COMPLETED else '失败'}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"执行工作流失败：{e}")
        raise HTTPException(status_code=500, detail=f"执行工作流失败：{str(e)}")


@router.get("/{workflow_id}/executions", response_model=WorkflowExecutionListResponse)
async def list_workflow_executions(
    workflow_id: str,
    tenant_id: str = Query(..., description="租户 ID"),
    status: Optional[ExecutionStatus] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取工作流执行历史

    - **workflow_id**: 工作流 ID
    - **tenant_id**: 租户 ID
    - **status**: 可选，状态筛选
    """
    try:
        executions = workflow_engine.list_executions(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            status=status
        )

        # 分页
        total = len(executions)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_executions = executions[start:end]

        return WorkflowExecutionListResponse(
            success=True,
            executions=paginated_executions,
            total=total,
            message=f"成功获取 {len(paginated_executions)} 条执行记录"
        )
    except Exception as e:
        logger.error(f"获取执行历史失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取执行历史失败：{str(e)}")


@router.get("/{workflow_id}/executions/{execution_id}")
async def get_workflow_execution(
    workflow_id: str,
    execution_id: str
):
    """
    获取执行详情

    - **workflow_id**: 工作流 ID
    - **execution_id**: 执行 ID
    """
    execution = workflow_engine.get_execution(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"执行记录不存在：{execution_id}")

    if execution.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="执行记录不属于该工作流")

    return {
        "success": True,
        "execution": execution
    }


# ==================== 工作流模板 API ====================

@router.get("/templates", response_model=WorkflowTemplateListResponse)
async def list_workflow_templates(
    category: Optional[str] = Query(None, description="类别筛选"),
    is_public: bool = Query(True, description="是否只看公共模板")
):
    """
    获取工作流模板列表

    - **category**: 可选，类别筛选
    - **is_public**: 是否只看公共模板
    """
    # 预定义模板
    templates = get_builtin_templates()

    if category:
        templates = [t for t in templates if t.category == category]

    if is_public:
        templates = [t for t in templates if t.is_public]

    return WorkflowTemplateListResponse(
        success=True,
        templates=templates,
        total=len(templates),
        message=f"成功获取 {len(templates)} 个模板"
    )


@router.post("/templates", response_model=WorkflowTemplateResponse)
async def create_workflow_template(
    template_data: dict = Body(..., description="模板数据"),
    author_id: str = Body(..., description="作者 ID")
):
    """
    创建工作流模板

    请求体:
    - **name**: 模板名称
    - **description**: 模板描述
    - **category**: 模板类别
    - **workflow**: 工作流定义
    - **is_public**: 是否公开
    - **tags**: 标签列表
    """
    try:
        workflow_data = template_data.get("workflow", {})

        # 创建工作流
        workflow = Workflow(
            id=str(uuid.uuid4()),
            tenant_id="template",  # 模板属于系统
            created_by=author_id,
            name=workflow_data.get("name", template_data.get("name", "Template")),
            description=workflow_data.get("description", ""),
            version=workflow_data.get("version", "1.0.0"),
            status=WorkflowStatus.ACTIVE,
            nodes=workflow_data.get("nodes", []),
            edges=workflow_data.get("edges", []),
            input_schema=workflow_data.get("input_schema", {}),
            output_schema=workflow_data.get("output_schema", {}),
        )

        # 创建模板
        template = WorkflowTemplate(
            id=str(uuid.uuid4()),
            name=template_data.get("name", "Unnamed Template"),
            description=template_data.get("description", ""),
            category=template_data.get("category", "general"),
            workflow=workflow,
            is_public=template_data.get("is_public", False),
            author_id=author_id,
            tags=template_data.get("tags", []),
        )

        # 保存到引擎（实际应保存到数据库）
        workflow_engine._workflows[f"template_{template.id}"] = workflow

        return WorkflowTemplateResponse(
            success=True,
            template=template,
            message="模板创建成功"
        )
    except Exception as e:
        logger.error(f"创建工作流模板失败：{e}")
        raise HTTPException(status_code=500, detail=f"创建工作流模板失败：{str(e)}")


# ==================== 预定义模板 ====================

def get_builtin_templates() -> List[WorkflowTemplate]:
    """获取内置模板"""

    # 模板 1: 数据分析工作流
    data_analysis_workflow = Workflow(
        id="template-data-analysis",
        name="数据分析工作流",
        description="自动执行数据清洗、分析、可视化",
        version="1.0.0",
        status=WorkflowStatus.ACTIVE,
        tenant_id="system",
        created_by="system",
        nodes=[
            {
                "id": "node1",
                "name": "数据清洗",
                "node_type": "ai_task",
                "ai_employee_id": "emp-001",
                "task_description": "清洗输入数据，处理缺失值和异常值",
                "dependencies": [],
            },
            {
                "id": "node2",
                "name": "数据分析",
                "node_type": "ai_task",
                "ai_employee_id": "emp-001",
                "task_description": "执行统计分析",
                "dependencies": ["node1"],
            },
            {
                "id": "node3",
                "name": "可视化",
                "node_type": "ai_task",
                "ai_employee_id": "emp-001",
                "task_description": "生成可视化图表",
                "dependencies": ["node2"],
            },
        ],
        edges=[
            {"source_id": "node1", "target_id": "node2"},
            {"source_id": "node2", "target_id": "node3"},
        ],
        input_schema={"type": "object", "properties": {"data": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"result": {"type": "object"}}},
    )

    # 模板 2: 内容生成工作流
    content_generation_workflow = Workflow(
        id="template-content-generation",
        name="内容生成工作流",
        description="自动生成文章、报告等内容",
        version="1.0.0",
        status=WorkflowStatus.ACTIVE,
        tenant_id="system",
        created_by="system",
        nodes=[
            {
                "id": "node1",
                "name": "大纲生成",
                "node_type": "ai_task",
                "ai_employee_id": "emp-002",
                "task_description": "根据主题生成文章大纲",
                "dependencies": [],
            },
            {
                "id": "node2",
                "name": "内容撰写",
                "node_type": "ai_task",
                "ai_employee_id": "emp-002",
                "task_description": "根据大纲撰写内容",
                "dependencies": ["node1"],
            },
            {
                "id": "node3",
                "name": "编辑校对",
                "node_type": "ai_task",
                "ai_employee_id": "emp-002",
                "task_description": "校对和润色内容",
                "dependencies": ["node2"],
            },
        ],
        edges=[
            {"source_id": "node1", "target_id": "node2"},
            {"source_id": "node2", "target_id": "node3"},
        ],
        input_schema={"type": "object", "properties": {"topic": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"content": {"type": "string"}}},
    )

    # 模板 3: 客服工单处理工作流
    customer_service_workflow = Workflow(
        id="template-customer-service",
        name="客服工单处理工作流",
        description="自动处理和分类客服工单",
        version="1.0.0",
        status=WorkflowStatus.ACTIVE,
        tenant_id="system",
        created_by="system",
        nodes=[
            {
                "id": "node1",
                "name": "工单分类",
                "node_type": "ai_task",
                "ai_employee_id": "emp-003",
                "task_description": "分析工单内容并分类",
                "dependencies": [],
            },
            {
                "id": "node2",
                "name": "自动回复",
                "node_type": "ai_task",
                "ai_employee_id": "emp-003",
                "task_description": "生成回复内容",
                "dependencies": ["node1"],
            },
        ],
        edges=[
            {"source_id": "node1", "target_id": "node2"},
        ],
        input_schema={"type": "object", "properties": {"ticket": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"response": {"type": "string"}}},
    )

    return [
        WorkflowTemplate(
            id=data_analysis_workflow.id,
            name="数据分析工作流",
            description="自动执行数据清洗、分析、可视化",
            category="analytics",
            workflow=data_analysis_workflow,
            is_public=True,
            author_id="system",
            usage_count=100,
            rating=4.8,
            tags=["数据分析", "可视化", "自动化"],
        ),
        WorkflowTemplate(
            id=content_generation_workflow.id,
            name="内容生成工作流",
            description="自动生成文章、报告等内容",
            category="content",
            workflow=content_generation_workflow,
            is_public=True,
            author_id="system",
            usage_count=150,
            rating=4.7,
            tags=["内容生成", "写作", "自动化"],
        ),
        WorkflowTemplate(
            id=customer_service_workflow.id,
            name="客服工单处理工作流",
            description="自动处理和分类客服工单",
            category="customer_service",
            workflow=customer_service_workflow,
            is_public=True,
            author_id="system",
            usage_count=200,
            rating=4.9,
            tags=["客服", "工单", "自动化"],
        ),
    ]
