"""
代码分析工具集

将代码理解能力封装为 DeerFlow 2.0 Tools 格式
"""
import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.understanding_service import understanding_service

logger = logging.getLogger(__name__)


class CodeTools:
    """
    代码理解工具集

    所有工具都遵循 DeerFlow 2.0 Tools 规范：
    - name: 工具名称
    - description: 工具用途描述（供 AI 理解）
    - input_schema: JSON Schema 格式的输入定义
    - handler: 执行函数
    """

    def __init__(self, project_name: Optional[str] = None):
        self.default_project = project_name or "default"

    # ========== 工具实现方法 ==========

    def index_project(self, project_name: str, repo_path: str, incremental: bool = True) -> Dict[str, Any]:
        """索引项目代码"""
        return understanding_service.index_project(
            project_name=project_name,
            repo_path=repo_path,
            incremental=incremental
        )

    def global_map(self, project_name: str, repo_hint: str, format: str = "json") -> Dict[str, Any]:
        """生成全局代码地图"""
        return understanding_service.global_map(
            project_name=project_name,
            repo_hint=repo_hint,
            format=format
        )

    def explain_code(self, code: str, language: str = "python", context: Optional[str] = None) -> Dict[str, Any]:
        """解释代码片段"""
        return understanding_service.explain(code=code, language=language, context=context)

    def summarize_module(self, module_name: str) -> Dict[str, Any]:
        """生成模块摘要"""
        return understanding_service.summarize_module(module_name=module_name)

    def search_code(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """语义搜索代码"""
        chunks = understanding_service.index_pipeline.search_code(
            query=query,
            collection_name=self.default_project,
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
            }
            for chunk in chunks
        ]

    def ask_codebase(self, question: str) -> Dict[str, Any]:
        """代码库问答"""
        return understanding_service.ask(question=question)

    def get_dependency_graph(self, project_name: str) -> Dict[str, Any]:
        """获取依赖图谱"""
        return understanding_service.dependency_graph(project_name=project_name)

    def analyze_change_impact(self, file_path: str, project_name: str) -> Dict[str, Any]:
        """分析变更影响"""
        return understanding_service.analyze_change_impact(
            file_path=file_path,
            project_name=project_name
        )


# ========== DeerFlow 2.0 Tools 注册表 ==========

TOOLS_REGISTRY = {
    "index_project": {
        "name": "index_project",
        "description": "索引项目代码，构建向量索引和知识图谱。当用户需要分析一个新项目或代码库时调用此工具。",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "项目标识符，用于后续检索"
                },
                "repo_path": {
                    "type": "string",
                    "description": "代码仓库的本地路径或 URL"
                },
                "incremental": {
                    "type": "boolean",
                    "description": "是否增量索引（默认 true）",
                    "default": True
                }
            },
            "required": ["project_name", "repo_path"]
        },
        "handler": None  # 运行时绑定
    },
    "global_map": {
        "name": "global_map",
        "description": "生成项目全局代码地图，包括技术栈、分层架构、核心模块、入口点等。当用户想了解项目整体结构时调用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "项目标识符"
                },
                "repo_hint": {
                    "type": "string",
                    "description": "仓库路径或 URL 提示"
                },
                "format": {
                    "type": "string",
                    "description": "返回格式：json 或 markdown",
                    "enum": ["json", "markdown"],
                    "default": "json"
                }
            },
            "required": ["project_name", "repo_hint"]
        },
        "handler": None
    },
    "explain_code": {
        "name": "explain_code",
        "description": "解释代码片段的功能、逻辑和实现细节。当用户提供代码并询问其含义时调用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "待解释的代码片段"
                },
                "language": {
                    "type": "string",
                    "description": "编程语言",
                    "default": "python"
                },
                "context": {
                    "type": "string",
                    "description": "额外上下文，如所属模块说明",
                    "default": None
                }
            },
            "required": ["code"]
        },
        "handler": None
    },
    "summarize_module": {
        "name": "summarize_module",
        "description": "生成模块或文件的高层摘要，包括职责、公开 API、依赖关系等。当用户想了解某个模块的作用时调用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "模块名称或文件路径"
                }
            },
            "required": ["module_name"]
        },
        "handler": None
    },
    "search_code": {
        "name": "search_code",
        "description": "语义搜索代码库，找到与查询相关的代码片段。当用户需要查找实现特定功能的代码时调用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询（自然语言或关键词）"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 10
                }
            },
            "required": ["query"]
        },
        "handler": None
    },
    "ask_codebase": {
        "name": "ask_codebase",
        "description": "针对代码库进行自然语言问答，自动检索相关代码并生成回答。当用户有关于代码的问题时调用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "关于代码库的问题"
                }
            },
            "required": ["question"]
        },
        "handler": None
    },
    "get_dependency_graph": {
        "name": "get_dependency_graph",
        "description": "获取项目的依赖图谱，展示模块间的导入和调用关系。当用户想了解模块间依赖时调用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "项目标识符"
                }
            },
            "required": ["project_name"]
        },
        "handler": None
    },
    "analyze_change_impact": {
        "name": "analyze_change_impact",
        "description": "分析代码变更的影响范围，找出所有受影响的模块和函数。当用户计划修改代码时调用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "待修改的文件路径"
                },
                "project_name": {
                    "type": "string",
                    "description": "项目标识符"
                }
            },
            "required": ["file_path", "project_name"]
        },
        "handler": None
    },
}


# 绑定 handler
_tools_instance: Optional[CodeTools] = None


def get_tools() -> CodeTools:
    """获取工具实例"""
    global _tools_instance
    if _tools_instance is None:
        _tools_instance = CodeTools()
    return _tools_instance


def bind_handlers():
    """绑定工具 handler"""
    tools = get_tools()
    TOOLS_REGISTRY["index_project"]["handler"] = tools.index_project
    TOOLS_REGISTRY["global_map"]["handler"] = tools.global_map
    TOOLS_REGISTRY["explain_code"]["handler"] = tools.explain_code
    TOOLS_REGISTRY["summarize_module"]["handler"] = tools.summarize_module
    TOOLS_REGISTRY["search_code"]["handler"] = tools.search_code
    TOOLS_REGISTRY["ask_codebase"]["handler"] = tools.ask_codebase
    TOOLS_REGISTRY["get_dependency_graph"]["handler"] = tools.get_dependency_graph
    TOOLS_REGISTRY["analyze_change_impact"]["handler"] = tools.analyze_change_impact


# 自动绑定
bind_handlers()
