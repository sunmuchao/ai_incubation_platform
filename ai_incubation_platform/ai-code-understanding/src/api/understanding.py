"""
代码理解 API
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from services.understanding_service import understanding_service

router = APIRouter(prefix="/api/understanding", tags=["understanding"])


class ExplainRequest(BaseModel):
    code: str = Field(..., description="待解释的代码片段")
    language: str = Field("python", description="语言标识，如 python、typescript")
    context: Optional[str] = Field(None, description="额外上下文，如所属模块说明")


class SummarizeRequest(BaseModel):
    module_name: str = Field(..., description="模块或路径标识")
    symbols: Optional[List[str]] = Field(None, description="关心的符号列表，可选")
    raw_outline: Optional[str] = Field(None, description="静态分析产出的提纲/AST 摘要，可选")


class AskRequest(BaseModel):
    question: str = Field(..., description="关于代码库的自然语言问题")
    scope_paths: Optional[List[str]] = Field(None, description="限定检索的目录或文件")


class GlobalMapRequest(BaseModel):
    project_name: str = Field(..., description="项目名或仓库标识")
    repo_hint: Optional[str] = Field(
        None, description="仓库路径或 URL，便于后续克隆/扫描"
    )
    stack_hint: Optional[str] = Field(
        None, description="技术栈提示，如 Python+FastAPI、Node+React"
    )
    regenerate: bool = Field(False, description="是否强制重新生成，忽略缓存")
    format: str = Field("json", description="返回格式，支持 json 或 markdown")


class TaskGuideRequest(BaseModel):
    task_description: str = Field(
        ..., description="你想完成的任务，如「排查登录失败」「加一个新的导出接口」"
    )
    optional_paths: Optional[List[str]] = Field(
        None, description="已知的模块路径，可缩小检索范围"
    )
    project_name: Optional[str] = Field(
        None, description="项目名称，用于获取已索引的项目上下文"
    )


class IndexProjectRequest(BaseModel):
    project_name: str = Field(..., description="项目名或仓库标识")
    repo_path: str = Field(..., description="本地仓库路径")
    incremental: bool = Field(True, description="是否增量索引")


# ============= P3 新增 API =============

class DependencyGraphRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="项目根目录")
    output_format: str = Field("json", description="输出格式：json 或 dot")


class IndexGitDiffRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="Git 仓库路径")
    base: str = Field("HEAD~1", description="基准 commit")
    target: str = Field("HEAD", description="目标 commit")


class AnalyzeChangeImpactRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="项目根目录")
    changed_files: Optional[List[Dict[str, Any]]] = Field(
        None, description="变更文件列表，不提供则从 Git 获取"
    )
    base: str = Field("HEAD~1", description="基准 commit")
    target: str = Field("HEAD", description="目标 commit")


class ResolveSymbolsRequest(BaseModel):
    file_path: str = Field(..., description="文件路径")
    symbol_name: Optional[str] = Field(None, description="符号名称，不提供则返回所有符号")


class FindSymbolReferencesRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="项目根目录")
    symbol_name: str = Field(..., description="符号名称")
    scope_paths: Optional[List[str]] = Field(None, description="搜索范围")


# ============= P6 知识图谱 API =============

class BuildKnowledgeGraphRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="项目根目录")
    save: bool = Field(True, description="是否保存图谱到文件")


class QueryKnowledgeGraphRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    query_type: str = Field(..., description="查询类型")
    params: Optional[Dict[str, Any]] = Field(None, description="查询参数")


class GraphImpactAnalysisRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    node_id: Optional[str] = Field(None, description="节点 ID")
    file_path: Optional[str] = Field(None, description="文件路径")


# ============= P7 可视化增强 API =============

class KnowledgeGraphVizRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="项目根目录")
    layout: str = Field("force", description="布局算法：force, dag, circular")
    max_nodes: int = Field(100, description="最大节点数，避免渲染过慢")


# ============= P8 代码审查 API =============

class ReviewCodeRequest(BaseModel):
    code: str = Field(..., description="待审查的代码")
    language: str = Field("python", description="语言标识")
    file_path: Optional[str] = Field(None, description="文件路径")
    config: Optional[Dict[str, Any]] = Field(None, description="审查配置")


class ReviewFileRequest(BaseModel):
    file_path: str = Field(..., description="文件路径")
    language: Optional[str] = Field(None, description="语言标识")
    config: Optional[Dict[str, Any]] = Field(None, description="审查配置")


@router.post("/explain")
async def explain_code(request: ExplainRequest) -> Dict[str, Any]:
    """对代码片段生成解释（可对接 LLM / 规则引擎）。"""
    return understanding_service.explain(
        request.code, request.language, request.context
    )


@router.post("/summarize")
async def summarize_module(request: SummarizeRequest) -> Dict[str, Any]:
    """对模块生成高层摘要：职责、主要入口、依赖关系等。"""
    return understanding_service.summarize_module(
        request.module_name, request.symbols, request.raw_outline
    )


@router.post("/ask")
async def ask_codebase(request: AskRequest) -> Dict[str, Any]:
    """针对代码库的问答（需结合向量索引 / 检索增强生成）。"""
    return understanding_service.ask(request.question, request.scope_paths)


@router.get("/global-map")
async def global_map_help() -> Dict[str, Any]:
    """浏览器 GET 时返回说明；实际生成全局地图请用 POST。"""
    return {
        "message": "全局地图需使用 POST 调用，请打开 /docs 试用或发送 JSON body。",
        "post": "/api/understanding/global-map",
        "body_schema": GlobalMapRequest.model_json_schema(),
    }


@router.post("/global-map")
async def global_map(request: GlobalMapRequest) -> Dict[str, Any]:
    """
    全局地图：缓解大仓库 + IDE AI 局部编辑带来的「黑盒感」。
    自动扫描目录结构、识别架构分层、提取入口点与技术栈。
    """
    return understanding_service.global_map(
        request.project_name, request.repo_hint, request.stack_hint, request.regenerate, request.format
    )


@router.post("/index-project")
async def index_project(request: IndexProjectRequest) -> Dict[str, Any]:
    """
    索引整个项目代码，构建向量索引与全局地图。
    支持增量索引，默认只索引变更的文件。
    """
    return understanding_service.index_project(
        request.project_name, request.repo_path, request.incremental
    )


@router.post("/task-guide")
async def task_guide(request: TaskGuideRequest) -> Dict[str, Any]:
    """
    任务级阅读路径：给定要做的事情，建议从哪些层次、按什么顺序读代码。
    基于语义检索、依赖分析和架构分层综合排序。
    """
    return understanding_service.task_guide(
        request.task_description, request.optional_paths, request.project_name
    )


# ============= P3 新增 API =============

@router.post("/dependency-graph")
async def get_dependency_graph(request: DependencyGraphRequest) -> Dict[str, Any]:
    """
    P3: 生成项目依赖关系图。
    基于代码导入语句构建模块间依赖关系，支持循环依赖检测。
    """
    return understanding_service.dependency_graph(
        project_name=request.project_name,
        repo_path=request.repo_path,
        output_format=request.output_format
    )


@router.post("/index-git-diff")
async def index_git_diff(request: IndexGitDiffRequest) -> Dict[str, Any]:
    """
    P3: 索引 Git 变更文件。
    基于 Git diff 获取变更文件列表，增量索引变更文件，避免全量重新索引。
    """
    return understanding_service.index_git_diff(
        project_name=request.project_name,
        repo_path=request.repo_path,
        base=request.base,
        target=request.target
    )


@router.post("/analyze-change-impact")
async def analyze_change_impact(request: AnalyzeChangeImpactRequest) -> Dict[str, Any]:
    """
    P3: 分析代码变更的影响。
    基于依赖图识别受影响的模块，提供测试建议和风险评估。
    """
    return understanding_service.analyze_change_impact(
        project_name=request.project_name,
        repo_path=request.repo_path,
        changed_files=request.changed_files,
        base=request.base,
        target=request.target
    )


@router.post("/resolve-symbols")
async def resolve_symbols(request: ResolveSymbolsRequest) -> Dict[str, Any]:
    """
    P3: 解析文件符号或查找符号定义。
    支持解析代码中的符号引用（函数、类、变量等）。
    """
    return understanding_service.resolve_symbols(
        file_path=request.file_path,
        symbol_name=request.symbol_name
    )


@router.post("/find-symbol-references")
async def find_symbol_references(request: FindSymbolReferencesRequest) -> Dict[str, Any]:
    """
    P3: 查找符号的所有引用位置。
    支持跳转到符号定义，查找符号的所有引用位置。
    """
    return understanding_service.find_symbol_references(
        project_name=request.project_name,
        repo_path=request.repo_path,
        symbol_name=request.symbol_name,
        scope_paths=request.scope_paths
    )


# ============= P6 知识图谱 API =============

@router.post("/build-knowledge-graph")
async def build_knowledge_graph(request: BuildKnowledgeGraphRequest) -> Dict[str, Any]:
    """
    P6: 构建代码知识图谱。
    从代码库构建包含模块、类、函数、调用关系、依赖关系的知识图谱。
    """
    return understanding_service.build_knowledge_graph(
        project_name=request.project_name,
        repo_path=request.repo_path,
        save=request.save
    )


@router.post("/query-knowledge-graph")
async def query_knowledge_graph(request: QueryKnowledgeGraphRequest) -> Dict[str, Any]:
    """
    P6: 查询知识图谱。
    支持多种查询类型：impact_analysis, call_chain, dependency_tree, search, symbol_info 等
    """
    return understanding_service.query_knowledge_graph(
        project_name=request.project_name,
        query_type=request.query_type,
        params=request.params
    )


@router.post("/graph-impact-analysis")
async def graph_impact_analysis(request: GraphImpactAnalysisRequest) -> Dict[str, Any]:
    """
    P6: 基于知识图谱的影响分析。
    分析修改某个节点或文件会影响的范围
    """
    return understanding_service.graph_impact_analysis(
        project_name=request.project_name,
        node_id=request.node_id,
        file_path=request.file_path
    )


# ============= F-008 Git 变更自动同步 API =============

class GitSyncInstallRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="Git 仓库路径")


class GitSyncStatusRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="Git 仓库路径")


class GitSyncTriggerRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="Git 仓库路径")
    trigger_type: str = Field("manual", description="触发类型：manual, git_hook, file_watch")
    base: Optional[str] = Field("HEAD~1", description="基准 commit (可选)")
    target: Optional[str] = Field("HEAD", description="目标 commit (可选)")


class GitWatchStartRequest(BaseModel):
    project_name: str = Field(..., description="项目名称")
    repo_path: str = Field(..., description="Git 仓库路径")
    background: bool = Field(True, description="是否后台运行")


@router.post("/git-sync/install")
async def git_sync_install(request: GitSyncInstallRequest) -> Dict[str, Any]:
    """
    F-008: 安装 Git 变更自动同步。
    安装 Git Hooks 和触发脚本。
    """
    return understanding_service.git_sync_install(
        project_name=request.project_name,
        repo_path=request.repo_path
    )


@router.post("/git-sync/uninstall")
async def git_sync_uninstall(request: GitSyncInstallRequest) -> Dict[str, Any]:
    """
    F-008: 卸载 Git 变更自动同步。
    移除 Git Hooks 和触发脚本。
    """
    return understanding_service.git_sync_uninstall(
        project_name=request.project_name,
        repo_path=request.repo_path
    )


@router.get("/git-sync/status")
async def git_sync_status(
    project_name: str,
    repo_path: str
) -> Dict[str, Any]:
    """
    F-008: 获取 Git 变更同步状态。
    """
    return understanding_service.git_sync_status(
        project_name=project_name,
        repo_path=repo_path
    )


@router.post("/git-sync/trigger")
async def git_sync_trigger(request: GitSyncTriggerRequest) -> Dict[str, Any]:
    """
    F-008: 手动触发 Git 变更同步。
    """
    return understanding_service.git_sync_trigger(
        project_name=request.project_name,
        repo_path=request.repo_path,
        trigger_type=request.trigger_type,
        base=request.base,
        target=request.target
    )


@router.post("/git-sync/watch/start")
async def git_sync_watch_start(request: GitWatchStartRequest) -> Dict[str, Any]:
    """
    F-008: 启动文件系统监听。
    监听文件变更并自动同步。
    """
    return understanding_service.git_sync_watch_start(
        project_name=request.project_name,
        repo_path=request.repo_path,
        background=request.background
    )


@router.post("/git-sync/watch/stop")
async def git_sync_watch_stop(request: GitSyncStatusRequest) -> Dict[str, Any]:
    """
    F-008: 停止文件系统监听。
    """
    return understanding_service.git_sync_watch_stop(
        project_name=request.project_name,
        repo_path=request.repo_path
    )


@router.get("/git-sync/history")
async def git_sync_history(
    project_name: str,
    repo_path: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    F-008: 获取 Git 变更同步历史。
    """
    return understanding_service.git_sync_history(
        project_name=project_name,
        repo_path=repo_path,
        limit=limit
    )


# ============= P7 可视化增强 API =============

@router.post("/knowledge-graph-viz")
async def knowledge_graph_viz(request: KnowledgeGraphVizRequest) -> Dict[str, Any]:
    """
    P7: 获取知识图谱可视化数据。

    返回适合前端渲染的图谱数据格式，支持多种布局算法。
    """
    return understanding_service.knowledge_graph_viz(
        project_name=request.project_name,
        repo_path=request.repo_path,
        layout=request.layout,
        max_nodes=request.max_nodes
    )


# ============= P8 代码审查 API =============

@router.post("/review-code")
async def review_code(request: ReviewCodeRequest) -> Dict[str, Any]:
    """
    P8: 智能代码审查。

    对代码片段进行全面审查，包括:
    - 代码异味检测
    - 最佳实践建议
    - 安全风险识别
    - 性能问题分析
    - 代码风格检查
    """
    return understanding_service.review_code(
        code=request.code,
        language=request.language,
        file_path=request.file_path,
        config=request.config
    )


@router.post("/review-file")
async def review_file(request: ReviewFileRequest) -> Dict[str, Any]:
    """
    P8: 审查文件。

    对文件进行智能代码审查，自动从文件扩展名推断语言。
    """
    return understanding_service.review_file(
        file_path=request.file_path,
        language=request.language,
        config=request.config
    )

