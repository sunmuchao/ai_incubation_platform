"""
代码导航增强 API
提供 LSP 风格的代码导航功能端点
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import os

router = APIRouter(prefix="/api/code-nav", tags=["代码导航"])

# 数据模型


class NavigationRequest(BaseModel):
    """导航请求"""
    file_path: str = Field(..., description="文件路径")
    line: int = Field(..., description="行号 (1-based)", ge=1)
    column: int = Field(..., description="列号 (1-based)", ge=1)
    project_root: Optional[str] = Field(None, description="项目根目录")


class RenameRequest(BaseModel):
    """重命名请求"""
    file_path: str = Field(..., description="文件路径")
    line: int = Field(..., description="行号 (1-based)", ge=1)
    column: int = Field(..., description="列号 (1-based)", ge=1)
    new_name: str = Field(..., description="新名称")
    project_root: Optional[str] = Field(None, description="项目根目录")
    dry_run: bool = Field(True, description="是否仅模拟运行")


class SymbolLocation(BaseModel):
    """符号位置"""
    file_path: str
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    content_preview: Optional[str] = None


class GoToDefinitionResponse(BaseModel):
    """跳转定义响应"""
    success: bool
    symbol_name: Optional[str] = None
    definition: Optional[SymbolLocation] = None
    message: Optional[str] = None


class FindReferencesResponse(BaseModel):
    """查找引用响应"""
    success: bool
    symbol_name: Optional[str] = None
    references: List[SymbolLocation] = []
    total_references: int = 0
    message: Optional[str] = None


class RenameResponse(BaseModel):
    """重命名响应"""
    success: bool
    changed_files: List[str] = []
    total_changes: int = 0
    error: Optional[str] = None
    preview: Optional[List[Dict[str, Any]]] = None


class DocumentSymbolsRequest(BaseModel):
    """文档符号请求"""
    file_path: str = Field(..., description="文件路径")


class DocumentSymbolsResponse(BaseModel):
    """文档符号响应"""
    file_path: str
    symbols: List[Dict[str, Any]] = []
    total_symbols: int = 0
    language: Optional[str] = None
    error: Optional[str] = None


class FileOverviewResponse(BaseModel):
    """文件概览响应"""
    file_path: str
    language: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    symbols_summary: Optional[Dict[str, Any]] = None
    total_symbols: int = 0
    error: Optional[str] = None


# 服务实例缓存
_navigation_service = None


def get_navigation_service():
    """获取导航服务单例"""
    global _navigation_service
    if _navigation_service is None:
        from services.code_navigation_service import CodeNavigationService
        _navigation_service = CodeNavigationService()
    return _navigation_service


# API 端点

@router.post("/go-to-definition", response_model=GoToDefinitionResponse)
async def go_to_definition(request: NavigationRequest):
    """
    跳转到定义位置

    根据文件路径和光标位置，找到符号的定义位置

    **示例**:
    ```bash
    curl -X POST http://localhost:8011/api/code-nav/go-to-definition \\
      -H "Content-Type: application/json" \\
      -d '{
        "file_path": "src/main.py",
        "line": 10,
        "column": 5,
        "project_root": "/path/to/project"
      }'
    ```
    """
    try:
        service = get_navigation_service()

        # 验证文件存在
        if not os.path.exists(request.file_path):
            return GoToDefinitionResponse(
                success=False,
                message=f"文件不存在：{request.file_path}"
            )

        # 获取符号名称（用于返回）
        content = None
        try:
            with open(request.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
            if request.line <= len(lines):
                symbol_name = lines[request.line - 1]
                # 提取符号
                import re
                match = re.search(r'\b\w+\b', symbol_name)
                if match:
                    symbol_name = match.group()
                else:
                    symbol_name = None
            else:
                symbol_name = None
        except Exception:
            symbol_name = None

        # 跳转定义
        definition = service.go_to_definition(
            request.file_path,
            request.line,
            request.column,
            request.project_root
        )

        if definition:
            return GoToDefinitionResponse(
                success=True,
                symbol_name=symbol_name,
                definition=SymbolLocation(
                    file_path=definition.file_path,
                    line=definition.line,
                    column=definition.column,
                    end_line=definition.end_line,
                    end_column=definition.end_column,
                    content_preview=definition.content_preview
                ),
                message="找到定义位置"
            )
        else:
            return GoToDefinitionResponse(
                success=False,
                symbol_name=symbol_name,
                message="未找到定义位置"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/find-references", response_model=FindReferencesResponse)
async def find_references(request: NavigationRequest):
    """
    查找所有引用位置

    找到符号在项目中所有被使用的位置

    **示例**:
    ```bash
    curl -X POST http://localhost:8011/api/code-nav/find-references \\
      -H "Content-Type: application/json" \\
      -d '{
        "file_path": "src/main.py",
        "line": 10,
        "column": 5,
        "project_root": "/path/to/project"
      }'
    ```
    """
    try:
        service = get_navigation_service()

        # 验证文件存在
        if not os.path.exists(request.file_path):
            return FindReferencesResponse(
                success=False,
                message=f"文件不存在：{request.file_path}"
            )

        # 获取符号名称
        content = None
        try:
            with open(request.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
            if request.line <= len(lines):
                import re
                match = re.search(r'\b\w+\b', lines[request.line - 1])
                symbol_name = match.group() if match else None
            else:
                symbol_name = None
        except Exception:
            symbol_name = None

        # 查找引用
        references = service.find_all_references(
            request.file_path,
            request.line,
            request.column,
            request.project_root
        )

        ref_locations = [
            SymbolLocation(
                file_path=ref.file_path,
                line=ref.line,
                column=ref.column,
                end_line=ref.end_line,
                end_column=ref.end_column,
                content_preview=ref.content_preview
            )
            for ref in references
        ]

        return FindReferencesResponse(
            success=True,
            symbol_name=symbol_name,
            references=ref_locations,
            total_references=len(ref_locations),
            message=f"找到 {len(ref_locations)} 处引用"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rename-symbol", response_model=RenameResponse)
async def rename_symbol(request: RenameRequest):
    """
    重命名符号

    安全地重命名符号，更新所有引用位置

    **示例**:
    ```bash
    curl -X POST http://localhost:8011/api/code-nav/rename-symbol \\
      -H "Content-Type: application/json" \\
      -d '{
        "file_path": "src/main.py",
        "line": 10,
        "column": 5,
        "new_name": "newFunctionName",
        "project_root": "/path/to/project",
        "dry_run": true
      }'
    ```
    """
    try:
        service = get_navigation_service()

        # 验证文件存在
        if not os.path.exists(request.file_path):
            return RenameResponse(
                success=False,
                error=f"文件不存在：{request.file_path}"
            )

        # 执行重命名
        result = service.rename_symbol(
            request.file_path,
            request.line,
            request.column,
            request.new_name,
            request.project_root,
            request.dry_run
        )

        response = RenameResponse(
            success=result.success,
            changed_files=result.changed_files,
            total_changes=result.total_changes,
            error=result.error
        )

        # 如果是 dry run，提供预览信息
        if request.dry_run and result.success:
            response.preview = [
                {"file": f, "changes": "待更新"}
                for f in result.changed_files
            ]

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document-symbols", response_model=DocumentSymbolsResponse)
async def get_document_symbols(request: DocumentSymbolsRequest):
    """
    获取文档中的所有符号

    返回文件中定义的所有符号（类、函数、变量等）

    **示例**:
    ```bash
    curl -X POST http://localhost:8011/api/code-nav/document-symbols \\
      -H "Content-Type: application/json" \\
      -d '{
        "file_path": "src/main.py"
      }'
    ```
    """
    try:
        service = get_navigation_service()

        # 验证文件存在
        if not os.path.exists(request.file_path):
            return DocumentSymbolsResponse(
                file_path=request.file_path,
                error=f"文件不存在：{request.file_path}"
            )

        # 获取符号
        result = service.get_document_symbols(request.file_path)

        return DocumentSymbolsResponse(
            file_path=result.get("file_path", request.file_path),
            symbols=result.get("symbols", []),
            total_symbols=result.get("total_symbols", 0),
            language=result.get("language"),
            error=result.get("error")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file-overview", response_model=FileOverviewResponse)
async def get_file_overview(request: DocumentSymbolsRequest):
    """
    获取文件概览信息

    返回文件的统计信息和符号摘要

    **示例**:
    ```bash
    curl -X POST http://localhost:8011/api/code-nav/file-overview \\
      -H "Content-Type: application/json" \\
      -d '{
        "file_path": "src/main.py"
      }'
    ```
    """
    try:
        service = get_navigation_service()

        # 验证文件存在
        if not os.path.exists(request.file_path):
            return FileOverviewResponse(
                file_path=request.file_path,
                error=f"文件不存在：{request.file_path}"
            )

        # 获取概览
        result = service.get_file_overview(request.file_path)

        return FileOverviewResponse(
            file_path=result.get("file_path", request.file_path),
            language=result.get("language"),
            stats=result.get("stats"),
            symbols_summary=result.get("symbols_summary"),
            total_symbols=result.get("total_symbols", 0),
            error=result.get("error")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "code-navigation",
        "version": "1.8.0"
    }
