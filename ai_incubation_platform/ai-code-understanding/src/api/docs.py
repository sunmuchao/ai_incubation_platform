"""
自动文档生成 API
提供 API 文档生成、架构图绘制、数据流图生成、README 补全、文档追踪等功能
"""
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from services.doc_generation_service import DocGenerationService, create_doc_service, generate_docs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/docs", tags=["documentation"])


# ==================== 请求模型 ====================

class GenerateAPIDocsRequest(BaseModel):
    """生成 API 文档请求"""
    project_path: str = Field(..., description="项目路径")
    source_dirs: Optional[List[str]] = Field(
        None,
        description="源代码目录列表，默认为 ['src', 'api', 'routes', 'controllers']"
    )
    format: str = Field("markdown", description="输出格式：markdown, openapi")


class GenerateArchitectureRequest(BaseModel):
    """生成架构图请求"""
    project_path: str = Field(..., description="项目路径")
    format: str = Field("mermaid", description="输出格式：mermaid, graphviz")
    include_details: bool = Field(True, description="是否包含详细信息")


class GenerateDataFlowRequest(BaseModel):
    """生成数据流图请求"""
    project_path: str = Field(..., description="项目路径")
    entry_points: Optional[List[str]] = Field(None, description="入口点文件列表")
    max_depth: int = Field(5, description="最大追踪深度")
    format: str = Field("mermaid", description="输出格式：mermaid, graphviz")


class GenerateReadmeRequest(BaseModel):
    """生成 README 请求"""
    project_path: str = Field(..., description="项目路径")
    include_sections: Optional[List[str]] = Field(
        None,
        description="要包含的章节列表"
    )


class TrackDocsRequest(BaseModel):
    """追踪文档更新请求"""
    project_path: str = Field(..., description="项目路径")
    doc_paths: Optional[List[str]] = Field(None, description="文档路径列表")
    git_diff: Optional[Dict[str, Any]] = Field(None, description="Git 变更 Diff")


class ExportDocsRequest(BaseModel):
    """导出文档请求"""
    project_path: str = Field(..., description="项目路径")
    output_dir: str = Field("docs/generated", description="输出目录")
    doc_types: Optional[List[str]] = Field(
        None,
        description="要导出的文档类型：api, architecture, dataflow, readme, openapi"
    )


# ==================== 缓存管理 ====================

# 缓存已创建的服务实例
_service_cache: Dict[str, DocGenerationService] = {}


def get_service(project_path: str) -> DocGenerationService:
    """获取或创建文档生成服务实例"""
    if project_path not in _service_cache:
        _service_cache[project_path] = create_doc_service(project_path)
    return _service_cache[project_path]


# ==================== API 端点 ====================

@router.post("/generate/api")
async def generate_api_docs(request: GenerateAPIDocsRequest):
    """
    从代码自动生成 API 文档

    支持从 FastAPI、Flask 等框架的路由装饰器中提取 API 端点信息，
    生成 Markdown 或 OpenAPI/Swagger 格式的文档。
    """
    try:
        service = get_service(request.project_path)

        # 生成 API 文档
        entries = service.generate_api_docs(request.source_dirs)

        # 根据格式导出
        if request.format == "openapi":
            result = service.export_api_docs_openapi()
            return {"success": True, "data": result, "format": "openapi"}
        else:
            markdown = service.export_api_docs_markdown()
            return {"success": True, "data": markdown, "format": "markdown", "count": len(entries)}

    except Exception as e:
        logger.exception("Failed to generate API docs")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-docs/{project_path:path}")
async def get_api_docs(
    project_path: str,
    format: str = Query("markdown", description="输出格式：markdown, openapi")
):
    """获取 API 文档（简化接口）"""
    try:
        # 将路径分隔符从 URL 编码恢复
        project_path = os.path.normpath(project_path)
        service = get_service(project_path)

        if not service._api_docs:
            service.generate_api_docs()

        if format == "openapi":
            result = service.export_api_docs_openapi()
            return JSONResponse(content=result)
        else:
            markdown = service.export_api_docs_markdown()
            return PlainTextResponse(content=markdown, media_type="text/markdown")

    except Exception as e:
        logger.exception("Failed to get API docs")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/architecture")
async def generate_architecture(request: GenerateArchitectureRequest):
    """
    生成项目架构图

    基于代码目录结构和依赖关系，自动识别架构分层，
    生成 Mermaid 或 Graphviz 格式的架构图。
    """
    try:
        service = get_service(request.project_path)

        diagram = service.generate_architecture_diagram(
            format=request.format
        )

        return {
            "success": True,
            "data": {
                "title": diagram.title,
                "description": diagram.description,
                "layers": diagram.layers,
                "connections": diagram.connections,
                "diagram_mermaid": diagram.diagram_mermaid,
                "diagram_graphviz": diagram.diagram_graphviz
            }
        }

    except Exception as e:
        logger.exception("Failed to generate architecture diagram")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/dataflow")
async def generate_dataflow(request: GenerateDataFlowRequest):
    """
    生成数据流图

    从代码入口点开始，追踪导入关系和函数调用链，
    生成数据流向图。
    """
    try:
        service = get_service(request.project_path)

        diagram = service.generate_dataflow_diagram(
            entry_points=request.entry_points,
            format=request.format
        )

        return {
            "success": True,
            "data": {
                "title": diagram.title,
                "description": diagram.description,
                "nodes": diagram.nodes,
                "flows": diagram.flows,
                "diagram_mermaid": diagram.diagram_mermaid
            }
        }

    except Exception as e:
        logger.exception("Failed to generate dataflow diagram")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/readme")
async def generate_readme(request: GenerateReadmeRequest):
    """
    智能生成 README

    基于项目结构分析、技术栈检测、代码特征等，
    自动生成完整的 README 文档。
    """
    try:
        service = get_service(request.project_path)

        readme = service.generate_readme()

        return {
            "success": True,
            "data": readme,
            "format": "markdown"
        }

    except Exception as e:
        logger.exception("Failed to generate README")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track/updates")
async def track_doc_updates(request: TrackDocsRequest):
    """
    追踪文档更新状态

    分析文档与代码变更的关系，识别需要更新的文档。
    """
    try:
        service = get_service(request.project_path)

        records = service.track_doc_updates(
            doc_paths=request.doc_paths,
            git_diff=request.git_diff
        )

        report = service.get_doc_status_report()

        return {
            "success": True,
            "data": report
        }

    except Exception as e:
        logger.exception("Failed to track doc updates")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/all")
async def export_all_docs(request: ExportDocsRequest):
    """
    一键导出所有文档

    生成 API 文档、架构图、数据流图、README 等所有文档，
    并保存到指定目录。
    """
    try:
        service = get_service(request.project_path)

        # 先生成 API 文档
        service.generate_api_docs()

        # 导出所有文档
        generated = service.export_all_docs(request.output_dir)

        return {
            "success": True,
            "data": generated,
            "message": f"Generated {len(generated)} documentation files"
        }

    except Exception as e:
        logger.exception("Failed to export all docs")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_path:path}")
async def get_doc_status(project_path: str):
    """获取文档生成状态"""
    try:
        project_path = os.path.normpath(project_path)

        # 检查服务是否在缓存中
        if project_path in _service_cache:
            service = _service_cache[project_path]
            report = service.get_doc_status_report()
            return {"success": True, "data": report}
        else:
            return {
                "success": True,
                "data": {
                    "total": 0,
                    "synced": 0,
                    "outdated": 0,
                    "missing": 0,
                    "records": []
                },
                "message": "No documentation generated yet"
            }

    except Exception as e:
        logger.exception("Failed to get doc status")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/all")
async def generate_all_docs(project_path: str, output_dir: str = "docs/generated"):
    """
    一键生成所有文档（简化接口）

    只需提供项目路径，自动生成所有类型的文档。
    """
    try:
        project_path = os.path.normpath(project_path)
        generated = generate_docs(project_path, output_dir)

        return {
            "success": True,
            "data": generated,
            "message": f"Generated {len(generated)} documentation files"
        }

    except Exception as e:
        logger.exception("Failed to generate all docs")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "doc-generation",
        "cached_projects": len(_service_cache)
    }
