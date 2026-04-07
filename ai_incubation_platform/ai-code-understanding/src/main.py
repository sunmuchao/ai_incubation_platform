"""
AI 代码理解助手 - 主入口
帮助开发者与 AI 更好地理解系统代码结构、语义与调用关系。
"""
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from api.understanding import router as understanding_router
from api.docs import router as docs_router
from api.doc_qa import router as doc_qa_router
from api.code_navigation import router as code_nav_router
from api.chat import router as chat_router
from api.generative_ui import router as generative_ui_router
from middleware.auth import get_api_key, verify_api_key_optional, check_api_key_health
from middleware.observability import TraceMiddleware, TraceContext, get_metrics_summary, global_metrics
import time
import os

app = FastAPI(
    title="AI Code Understanding (AI Native)",
    description="AI 代码理解助手 — 对话式交互 + 动态生成 UI + 自主代码分析",
    version="1.0.0-AI-Native",
)

# 挂载静态文件目录（frontend）
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

app.include_router(understanding_router)
app.include_router(docs_router)
app.include_router(doc_qa_router)
app.include_router(code_nav_router)
app.include_router(chat_router)
app.include_router(generative_ui_router)

# 添加可观测性中间件（在认证中间件之前）
app.add_middleware(TraceMiddleware)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    全局认证中间件

    对所有 /api/* 请求进行 API Key 认证
    白名单路径：/、/health、/docs、/openapi.json
    """
    # 白名单路径不需要认证
    whitelist_paths = ["/", "/health", "/docs", "/docs/", "/openapi.json"]
    if request.url.path in whitelist_paths:
        return await call_next(request)

    # API 路径需要认证
    if request.url.path.startswith("/api/"):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "缺少 API Key",
                    "detail": "请在请求头中提供 X-API-Key",
                    "help": "访问 /api/auth/health 查看 API Key 管理信息"
                }
            )

        # 验证 Key（这里简单验证，详细验证在 get_api_key 中）
        from middleware.auth import api_key_manager
        key_info = api_key_manager.validate_key(api_key)
        if not key_info:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "无效的 API Key",
                    "detail": "API Key 无效、已过期或被撤销"
                }
            )

        # 更新使用记录
        api_key_manager.update_usage(api_key)

    return await call_next(request)


@app.get("/")
async def root():
    return {
        "message": "欢迎使用 AI 代码理解助手 (AI Native v1.0)",
        "status": "running",
        "version": "1.0.0-AI-Native",
        "ai_native_features": [
            "对话式交互 (Chat-first API)",
            "动态生成 UI (Generative UI)",
            "多 Agent 协作 (DeerFlow 2.0)",
            "自主代码探索 (Autonomous Exploration)",
            "工作流编排 (Multi-step Workflows)",
        ],
        "features": [
            "代码片段解释（已集成 tree-sitter 语法解析）",
            "模块摘要生成（已集成引用溯源）",
            "代码库语义问答（已集成向量检索）",
            "全局代码地图（已实现自动生成）",
            "任务导向阅读路径（已实现智能排序）",
            "幻觉控制与引用溯源（已集成校验机制）",
            "API Key 认证（已实现）",
            "CLI 命令行工具（P5 新增）",
            "Markdown 格式化输出（P5 新增）",
            "可视化界面（P5 新增）",
            "监控指标与链路追踪（P5 新增）",
            "自动文档生成（P8/v1.6 新增）",
            "智能文档问答（P9/v1.7 新增）",
            "文档语义搜索（P9/v1.7 新增）",
            "答案溯源引用（P9/v1.7 新增）",
            "代码导航辅助（P9/v1.7 新增）",
            "LSP 代码导航增强（v1.8 新增）",
            "跳转定义/查找引用（v1.8 新增）",
            "符号重命名（v1.8 新增）",
        ],
        "endpoints": {
            "chat_sync": "/api/chat/sync",
            "chat_stream": "/api/chat/",
            "generative_ui": "/api/generative-ui/generate",
            "visualizer": "/api/generative-ui/visualizer",
            "explain": "/api/understanding/explain",
            "summarize": "/api/understanding/summarize",
            "ask": "/api/understanding/ask",
            "global_map": "/api/understanding/global-map",
            "task_guide": "/api/understanding/task-guide",
            "index_project": "/api/understanding/index-project",
            "dependency_graph": "/api/understanding/dependency-graph",
            "analyze_change_impact": "/api/understanding/analyze-change-impact",
            "resolve_symbols": "/api/understanding/resolve-symbols",
            "find_symbol_references": "/api/understanding/find-symbol-references",
            "generate_api_docs": "/api/docs/generate/api",
            "generate_architecture": "/api/docs/generate/architecture",
            "generate_dataflow": "/api/docs/generate/dataflow",
            "generate_readme": "/api/docs/generate/readme",
            "export_all_docs": "/api/docs/export/all",
            "search_documents": "/api/doc-qa/search",
            "ask_question": "/api/doc-qa/ask",
            "explain_code": "/api/doc-qa/explain",
            "code_navigation": "/api/doc-qa/navigate",
            "go_to_definition": "/api/code-nav/go-to-definition",
            "find_references": "/api/code-nav/find-references",
            "rename_symbol": "/api/code-nav/rename-symbol",
            "document_symbols": "/api/code-nav/document-symbols",
            "file_overview": "/api/code-nav/file-overview",
            "auth_manage": "/api/auth/manage",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
            "visualizer": "/visualizer",
            "metrics_ui": "/metrics-ui"
        },
        "ui_pages": {
            "api_debug": "/docs-ui",
            "visualizer": "/visualizer",
            "metrics_dashboard": "/metrics-ui",
            "generative_ui_demo": "/api/generative-ui/visualizer"
        },
        "cli": {
            "help": "运行 python src/cli.py --help",
            "quick_start": "python src/cli.py explain --code 'def hello(): return \"world\"'"
        },
        "auth": {
            "required": True,
            "header": "X-API-Key",
            "help": "访问 /api/auth/health 查看 API Key 管理信息"
        },
        "deerflow_integration": {
            "agents": ["CodeUnderstandingAgent"],
            "tools": ["index_project", "global_map", "explain_code", "summarize_module", "search_code", "ask_codebase"],
            "workflows": ["code_understanding", "code_exploration", "impact_analysis"],
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/metrics")
async def get_metrics():
    """
    获取监控指标

    返回系统性能指标、API 调用统计、链路追踪信息等
    """
    return get_metrics_summary()


@app.get("/visualizer")
async def visualizer():
    """可视化中心页面"""
    return FileResponse(os.path.join(frontend_dir, "visualizer.html"))


@app.get("/metrics-ui")
async def metrics_ui():
    """监控指标 UI 页面"""
    return FileResponse(os.path.join(frontend_dir, "metrics.html"))


@app.get("/docs-ui")
async def docs_ui():
    """API 调试 UI 页面"""
    return FileResponse(os.path.join(frontend_dir, "index.html"))


# ============= API Key 管理端点 =============

@app.get("/api/auth/health")
async def auth_health():
    """
    查看 API Key 认证健康状态

    无需认证即可访问此端点，用于首次配置
    """
    return check_api_key_health()


@app.post("/api/auth/manage")
async def manage_api_keys(
    request: Request,
    api_key: str = Depends(get_api_key)
):
    """
    API Key 管理端点

    需要有效的 API Key 才能访问

    支持操作:
    - POST {"action": "create", "name": "Key 名称", "expires_in_days": 30}
    - POST {"action": "revoke", "key": "要撤销的 Key"}
    - POST {"action": "list"}
    """
    from middleware.auth import api_key_manager, generate_api_key

    body = await request.json()
    action = body.get("action")

    if action == "create":
        name = body.get("name", "Unnamed")
        expires_in_days = body.get("expires_in_days")
        new_key = generate_api_key(name=name, expires_in_days=expires_in_days)
        return {
            "success": True,
            "action": "create",
            "api_key": new_key,
            "message": "请妥善保管此 API Key，它只会显示一次"
        }

    elif action == "revoke":
        key_to_revoke = body.get("key")
        if not key_to_revoke:
            return {"success": False, "error": "缺少 key 参数"}
        result = api_key_manager.revoke_key(key_to_revoke)
        return {"success": result, "action": "revoke"}

    elif action == "list":
        return {"success": True, "action": "list", "keys": api_key_manager.list_keys()}

    elif action == "delete":
        key_to_delete = body.get("key")
        if not key_to_delete:
            return {"success": False, "error": "缺少 key 参数"}
        result = api_key_manager.delete_key(key_to_delete)
        return {"success": result, "action": "delete"}

    else:
        return {
            "success": False,
            "error": f"未知操作：{action}",
            "supported_actions": ["create", "revoke", "list", "delete"]
        }


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8008))
    uvicorn.run(app, host="0.0.0.0", port=port)
