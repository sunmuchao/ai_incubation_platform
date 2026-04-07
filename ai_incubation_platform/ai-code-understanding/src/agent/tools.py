"""
AI 代码理解助手 - DeerFlow Tools 集成

将核心能力封装为 DeerFlow 2.0 可调用的工具：
1. index_project - 索引项目代码
2. global_map - 生成全局地图
3. task_guide - 生成任务阅读路径
4. explain_code - 解释代码片段
5. summarize_module - 生成模块摘要
6. ask_codebase - 代码库问答
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.understanding_service import understanding_service


class CodeUnderstandingTools:
    """
    代码理解工具集 - 封装为 DeerFlow Tools

    使用方式:
        tools = CodeUnderstandingTools()
        result = tools.global_map(project_name="my_project", repo_hint="/path/to/repo")
    """

    def __init__(self, project_name: Optional[str] = None):
        """
        初始化工具集

        Args:
            project_name: 默认项目名称，用于后续工具调用的上下文
        """
        self.default_project = project_name
        self.service = understanding_service

    def index_project(
        self,
        project_name: str,
        repo_path: str,
        incremental: bool = True
    ) -> Dict[str, Any]:
        """
        索引项目代码，构建向量索引与全局地图

        Args:
            project_name: 项目标识
            repo_path: 本地仓库路径
            incremental: 是否增量索引

        Returns:
            {
                "success": bool,
                "stats": {
                    "total_files": int,
                    "success_files": int,
                    "failed_files": int,
                    "skipped_files": int,
                    "total_chunks": int,
                    "total_symbols": int
                },
                "project_name": str,
                "repo_path": str
            }
        """
        return self.service.index_project(
            project_name=project_name,
            repo_path=repo_path,
            incremental=incremental
        )

    def global_map(
        self,
        project_name: str,
        repo_hint: str,
        stack_hint: Optional[str] = None,
        regenerate: bool = False,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        生成项目全局地图 - 缓解大仓库黑盒问题

        Args:
            project_name: 项目标识
            repo_hint: 仓库路径或 URL
            stack_hint: 技术栈提示，如 Python+FastAPI
            regenerate: 是否强制重新生成
            format: 返回格式 (json/markdown)

        Returns:
            {
                "project": str,
                "repo_path": str,
                "tech_stack": {"languages": [], "frameworks": [], "databases": []},
                "layers": [{"name": str, "description": str, "paths": [], "responsibilities": []}],
                "module_tree": {...},
                "entrypoints": [{"name": str, "path": str, "type": str}],
                "conventions": [],
                "dependencies": {...},
                "key_symbols": [],
                "generated_at": str
            }
        """
        return self.service.global_map(
            project_name=project_name,
            repo_hint=repo_hint,
            stack_hint=stack_hint,
            regenerate=regenerate,
            format=format
        )

    def task_guide(
        self,
        task_description: str,
        project_name: Optional[str] = None,
        optional_paths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        生成任务导向的阅读路径

        Args:
            task_description: 任务描述，如「排查登录失败」「加一个新的导出接口」
            project_name: 项目名称（可选，使用默认值如果未提供）
            optional_paths: 已知的模块路径，可缩小检索范围

        Returns:
            {
                "task": str,
                "task_type": str,  # bug_fix, feature_add, refactor, performance
                "scope": [],
                "estimated_reading_time_minutes": int,
                "related_files_count": int,
                "suggested_reading_order": [
                    {
                        "order": int,
                        "file_path": str,
                        "file_name": str,
                        "module": str,
                        "start_line": int,
                        "end_line": int,
                        "relevance_score": float,
                        "layer": str,
                        "reading_goal": str,
                        "key_points": [],
                        "symbols": [],
                        "chunk_type": str,
                        "is_dependency": bool,
                        "references": [{"chunk_id": str, "file_path": str, "start_line": int, "end_line": int, "similarity": float, "snippet": str}]
                    }
                ],
                "citations": [],
                "questions_to_clarify": [],
                "potential_risks": []
            }
        """
        project = project_name or self.default_project
        return self.service.task_guide(
            task_description=task_description,
            optional_paths=optional_paths,
            project_name=project
        )

    def explain_code(
        self,
        code: str,
        language: str = "python",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        解释代码片段

        Args:
            code: 待解释的代码片段
            language: 语言标识 (python, typescript, etc.)
            context: 额外上下文，如所属模块说明

        Returns:
            {
                "language": str,
                "summary": str,
                "code_preview": str,
                "context_used": bool,
                "symbols": [],
                "chunk_count": int,
                "validation": {
                    "confidence": float,
                    "is_valid": bool,
                    "warnings": [],
                    "errors": [],
                    "citations": [],
                    "corrected_content": str
                }
            }
        """
        return self.service.explain(
            code=code,
            language=language,
            context=context
        )

    def summarize_module(
        self,
        module_name: str,
        symbols: Optional[List[str]] = None,
        raw_outline: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成模块高层摘要

        Args:
            module_name: 模块或路径标识
            symbols: 关心的符号列表（可选）
            raw_outline: 静态分析产出的提纲/AST 摘要（可选）

        Returns:
            {
                "module": str,
                "role": str,
                "public_api": [],
                "outline_present": bool,
                "dependencies": str,
                "citations": [],
                "validation": {
                    "confidence": float,
                    "is_valid": bool,
                    "warnings": [],
                    "errors": [],
                    "citations": [],
                    "corrected_content": str
                }
            }
        """
        return self.service.summarize_module(
            module_name=module_name,
            symbols=symbols,
            raw_outline=raw_outline
        )

    def ask_codebase(
        self,
        question: str,
        scope_paths: Optional[List[str]] = None,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        针对代码库的问答（需结合向量索引）

        Args:
            question: 关于代码库的自然语言问题
            scope_paths: 限定检索的目录或文件
            project_name: 项目名称（可选，使用默认值如果未提供）

        Returns:
            {
                "question": str,
                "scope": [],
                "answer": str,
                "citations": [
                    {
                        "file_path": str,
                        "start_line": int,
                        "end_line": int,
                        "similarity": float,
                        "content": str
                    }
                ],
                "related_chunks_count": int
            }
        """
        # 注意：当前 service.ask 不使用 project_name，但为了未来扩展保留参数
        _ = project_name  # 预留
        return self.service.ask(
            question=question,
            scope_paths=scope_paths
        )

    def search_code(
        self,
        query: str,
        project_name: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        语义搜索代码

        Args:
            query: 搜索查询
            project_name: 项目名称（用于指定 collection）
            top_k: 返回结果数量

        Returns:
            [
                {
                    "chunk_id": str,
                    "file_path": str,
                    "language": str,
                    "content": str,
                    "start_line": int,
                    "end_line": int,
                    "chunk_type": str,
                    "symbols": [],
                    "metadata": {"similarity": float},
                    "embedding": null
                }
            ]
        """
        collection_name = project_name or self.default_project
        chunks = self.service.index_pipeline.search_code(
            query=query,
            collection_name=collection_name,
            top_k=top_k
        )
        return [
            {
                "chunk_id": chunk.chunk_id,
                "file_path": chunk.file_path,
                "language": chunk.language,
                "content": chunk.content,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_type": chunk.chunk_type,
                "symbols": chunk.symbols,
                "metadata": chunk.metadata,
                "embedding": None  # 不返回向量数据
            }
            for chunk in chunks
        ]


# 导出工具实例（方便直接使用）
tools = CodeUnderstandingTools()

# 导出工具方法（方便 DeerFlow 工具注册）
__all__ = [
    "CodeUnderstandingTools",
    "tools",
    "index_project",
    "global_map",
    "task_guide",
    "explain_code",
    "summarize_module",
    "ask_codebase",
    "search_code",
]


# 顶层函数包装（方便 DeerFlow 工具调用）
def index_project(project_name: str, repo_path: str, incremental: bool = True) -> Dict[str, Any]:
    return tools.index_project(project_name, repo_path, incremental)

def global_map(project_name: str, repo_hint: str, stack_hint: Optional[str] = None, regenerate: bool = False, format: str = "json") -> Dict[str, Any]:
    return tools.global_map(project_name, repo_hint, stack_hint, regenerate, format)

def task_guide(task_description: str, project_name: Optional[str] = None, optional_paths: Optional[List[str]] = None) -> Dict[str, Any]:
    return tools.task_guide(task_description, project_name, optional_paths)

def explain_code(code: str, language: str = "python", context: Optional[str] = None) -> Dict[str, Any]:
    return tools.explain_code(code, language, context)

def summarize_module(module_name: str, symbols: Optional[List[str]] = None, raw_outline: Optional[str] = None) -> Dict[str, Any]:
    return tools.summarize_module(module_name, symbols, raw_outline)

def ask_codebase(question: str, scope_paths: Optional[List[str]] = None, project_name: Optional[str] = None) -> Dict[str, Any]:
    return tools.ask_codebase(question, scope_paths, project_name)

def search_code(query: str, project_name: Optional[str] = None, top_k: int = 10) -> List[Dict[str, Any]]:
    return tools.search_code(query, project_name, top_k)
