"""
AI 代码理解助手 - DeerFlow 2.0 Agent 编排示例

展示如何使用 DeerFlow 2.0 编排多步阅读计划：
1. 先用 global-map 了解项目全局结构
2. 再用 task-guide 获取任务导向的阅读路径
3. 最后用 explain_code/summarize_module 深入理解具体代码
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from deerflow_integration import get_deerflow_client, is_deerflow_available

from .tools import CodeUnderstandingTools


class CodeUnderstandingAgent:
    """
    代码理解 Agent - 基于 DeerFlow 2.0 编排多步任务

    使用场景：
    1. 新项目上手：自动生成学习路径
    2. 任务开发：根据任务描述生成阅读顺序
    3. 代码审查：自动分析变更影响范围
    """

    def __init__(self, project_name: Optional[str] = None):
        """
        初始化 Agent

        Args:
            project_name: 目标项目名称
        """
        self.project_name = project_name
        self.tools = CodeUnderstandingTools(project_name=project_name)
        self.deerflow_client = None

        # 尝试初始化 DeerFlow 客户端
        if is_deerflow_available():
            self.deerflow_client = get_deerflow_client()

    def onboard_new_project(self, repo_path: str) -> Dict[str, Any]:
        """
        新项目上手工作流

        步骤：
        1. 索引项目代码
        2. 生成全局地图
        3. 生成学习建议

        Args:
            repo_path: 仓库路径

        Returns:
            包含项目地图、学习路径的综合报告
        """
        results = {
            "project_name": self.project_name,
            "repo_path": repo_path,
            "steps": []
        }

        # 步骤 1: 索引项目
        index_result = self.tools.index_project(
            project_name=self.project_name,
            repo_path=repo_path,
            incremental=True
        )
        results["steps"].append({
            "name": "index_project",
            "result": index_result
        })

        # 步骤 2: 生成全局地图
        global_map_result = self.tools.global_map(
            project_name=self.project_name,
            repo_hint=repo_path,
            format="json"
        )
        results["steps"].append({
            "name": "global_map",
            "result": global_map_result
        })

        # 步骤 3: 生成通用学习路径（如果没有具体任务）
        learning_guide = self.tools.task_guide(
            task_description="了解项目整体架构和核心功能",
            project_name=self.project_name
        )
        results["steps"].append({
            "name": "learning_guide",
            "result": learning_guide
        })

        return results

    def task_development(self, task_description: str) -> Dict[str, Any]:
        """
        任务开发工作流

        步骤：
        1. 生成任务阅读路径
        2. 识别相关模块
        3. 生成模块摘要

        Args:
            task_description: 任务描述

        Returns:
            包含阅读路径、模块摘要的开发指南
        """
        results = {
            "task": task_description,
            "steps": []
        }

        # 步骤 1: 生成任务阅读路径
        guide_result = self.tools.task_guide(
            task_description=task_description,
            project_name=self.project_name
        )
        results["steps"].append({
            "name": "task_guide",
            "result": guide_result
        })

        # 步骤 2: 提取相关模块并生成摘要
        reading_order = guide_result.get("suggested_reading_order", [])
        module_summaries = []
        for step in reading_order[:5]:  # 最多处理前 5 个模块
            # reading_order 可能包含字符串（占位文本）而不是字典
            if not isinstance(step, dict):
                continue
            # symbols 可能是列表或字符串，需要统一处理
            symbols = step.get("symbols", [])
            if isinstance(symbols, str):
                symbols = [symbols]
            if symbols:
                summary = self.tools.summarize_module(
                    module_name=step.get("module", ""),
                    symbols=symbols[:5]
                )
                module_summaries.append({
                    "module": step.get("module"),
                    "file_path": step.get("file_path"),
                    "summary": summary
                })

        results["steps"].append({
            "name": "module_summaries",
            "result": module_summaries
        })

        return results

    def code_review(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        代码审查工作流

        步骤：
        1. 获取变更文件的上下文
        2. 分析依赖影响
        3. 生成审查建议

        Args:
            file_paths: 变更文件路径列表

        Returns:
            包含依赖分析、审查建议的报告
        """
        results = {
            "changed_files": file_paths,
            "steps": []
        }

        # 步骤 1: 搜索相关文件获取上下文
        related_contexts = []
        for file_path in file_paths:
            # 提取模块名进行搜索
            module_name = file_path.replace("/", ".").replace(".py", "")
            search_result = self.tools.search_code(
                query=module_name,
                project_name=self.project_name,
                top_k=5
            )
            related_contexts.append({
                "file_path": file_path,
                "related_code": search_result
            })

        results["steps"].append({
            "name": "context_search",
            "result": related_contexts
        })

        # 步骤 2: 获取全局地图分析依赖
        global_map_result = self.tools.global_map(
            project_name=self.project_name,
            repo_hint=".",  # 使用当前目录
            regenerate=False
        )
        dependencies = global_map_result.get("dependencies", {})

        results["steps"].append({
            "name": "dependency_analysis",
            "result": {
                "file_dependencies": dependencies.get("file_dependencies", {}),
                "most_imported": dependencies.get("most_imported", [])[:10]
            }
        })

        return results

    def explain_with_context(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        带上下文的代码解释工作流

        步骤：
        1. 搜索相关代码获取上下文
        2. 解释代码（使用检索到的上下文）
        3. 幻觉校验

        Args:
            code: 待解释的代码
            language: 语言类型

        Returns:
            带引用来源的代码解释
        """
        # 步骤 1: 搜索相关代码
        search_result = self.tools.search_code(
            query=code[:200],  # 用代码开头作为查询
            project_name=self.project_name,
            top_k=3
        )

        # 步骤 2: 构建上下文
        context = ""
        if search_result:
            context = f"相关代码参考:\n"
            for i, chunk in enumerate(search_result, 1):
                context += f"\n参考{i} ({chunk['file_path']}:{chunk['start_line']}-{chunk['end_line']}):\n{chunk['content'][:300]}...\n"

        # 步骤 3: 解释代码（带上下文）
        explain_result = self.tools.explain_code(
            code=code,
            language=language,
            context=context if context else None
        )

        return {
            "search_context": search_result,
            "explanation": explain_result
        }


# 使用示例
if __name__ == "__main__":
    # 设置环境变量使用离线 embedding
    os.environ["AI_CODE_UNDERSTANDING_EMBEDDING_MODE"] = "hash"

    agent = CodeUnderstandingAgent(project_name="demo_project")

    # 示例 1: 新项目上手
    print("=== 新项目上手工作流 ===")
    onboarding = agent.onboard_new_project(repo_path=".")
    print(f"索引结果：{onboarding['steps'][0]['result'].get('success')}")
    print(f"地图层数：{len(onboarding['steps'][1]['result'].get('layers', []))}")
    print(f"阅读路径步骤：{len(onboarding['steps'][2]['result'].get('suggested_reading_order', []))}")

    # 示例 2: 任务开发
    print("\n=== 任务开发工作流 ===")
    task_result = agent.task_development("实现一个新的 API 端点")
    print(f"任务类型：{task_result['steps'][0]['result'].get('task_type')}")
    print(f"模块摘要数：{len(task_result['steps'][1]['result'])}")

    # 示例 3: 代码审查
    print("\n=== 代码审查工作流 ===")
    review_result = agent.code_review([
        "src/services/understanding_service.py",
        "src/api/understanding.py"
    ])
    print(f"变更文件数：{len(review_result['changed_files'])}")
    print(f"最常引用模块：{len(review_result['steps'][1]['result'].get('most_imported', []))}")
