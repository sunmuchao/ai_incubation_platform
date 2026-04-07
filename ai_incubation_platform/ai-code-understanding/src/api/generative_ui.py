"""
Generative UI API

动态生成可视化界面，根据 AI 分析结果和用户意图选择最佳视图
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import json
import os
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.code_tools import get_tools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generative-ui", tags=["generative-ui"])


class UIViewRequest(BaseModel):
    """UI 视图生成请求"""
    intent: str  # explore, understand, modify, debug
    data_type: str  # flow, dependency, call, dataflow
    context: Optional[Dict[str, Any]] = None


class GenerativeUIEngine:
    """
    动态 UI 生成引擎

    根据用户意图和数据类型，选择最佳视图模板
    """

    VIEW_TEMPLATES = {
        ("explore", "flow"): "code_flow_view",
        ("explore", "dependency"): "dependency_graph_view",
        ("explore", "call"): "call_graph_view",
        ("explore", "dataflow"): "data_lineage_view",
        ("understand", "flow"): "sequence_diagram_view",
        ("understand", "dependency"): "architecture_map_view",
        ("understand", "call"): "call_hierarchy_view",
        ("understand", "dataflow"): "data_transform_view",
        ("modify", "flow"): "impact_analysis_view",
        ("modify", "dependency"): "dependency_impact_view",
        ("modify", "call"): "caller_callee_view",
        ("modify", "dataflow"): "data_change_view",
        ("debug", "flow"): "execution_trace_view",
        ("debug", "dependency"): "error_propagation_view",
        ("debug", "call"): "stack_trace_view",
        ("debug", "dataflow"): "data_anomaly_view",
    }

    def generate_view_config(self, intent: str, data_type: str, context: Dict) -> Dict:
        """生成视图配置"""
        template_key = (intent, data_type)
        view_type = self.VIEW_TEMPLATES.get(template_key, "generic_view")

        return {
            "view_type": view_type,
            "config": self._get_view_config(view_type),
            "data": self._prepare_data(view_type, context),
        }

    def _get_view_config(self, view_type: str) -> Dict:
        """获取视图配置"""
        configs = {
            "code_flow_view": {
                "title": "代码流程图",
                "layout": "horizontal",
                "node_style": "box",
                "edge_style": "arrow",
            },
            "dependency_graph_view": {
                "title": "依赖关系图",
                "layout": "force_directed",
                "node_style": "circle",
                "edge_style": "line",
            },
            "architecture_map_view": {
                "title": "架构图",
                "layout": "hierarchical",
                "node_style": "box",
                "edge_style": "arrow",
            },
            "impact_analysis_view": {
                "title": "影响分析图",
                "layout": "radial",
                "node_style": "circle",
                "highlight": "affected_nodes",
            },
            "sequence_diagram_view": {
                "title": "序列图",
                "layout": "sequence",
                "participant_style": "box",
                "message_style": "arrow",
            },
            "generic_view": {
                "title": "通用视图",
                "layout": "grid",
                "node_style": "box",
                "edge_style": "line",
            },
        }
        return configs.get(view_type, configs["generic_view"])

    def _prepare_data(self, view_type: str, context: Dict) -> Dict:
        """准备视图数据"""
        tools = get_tools()

        if "dependency" in view_type:
            # 获取依赖数据
            try:
                project_name = context.get("project_name", "default")
                dep_graph = tools.get_dependency_graph(project_name=project_name)
                return self._format_dependency_data(dep_graph)
            except Exception as e:
                return {"error": str(e), "nodes": [], "edges": []}

        elif "flow" in view_type or "sequence" in view_type:
            # 获取流程数据
            return self._format_flow_data(context)

        elif "impact" in view_type:
            # 获取影响分析数据
            try:
                file_path = context.get("file_path", "")
                project_name = context.get("project_name", "default")
                impact = tools.analyze_change_impact(file_path=file_path, project_name=project_name)
                return self._format_impact_data(impact)
            except Exception as e:
                return {"error": str(e), "center": None, "affected": []}

        return {"raw_context": context}

    def _format_dependency_data(self, dep_graph: Dict) -> Dict:
        """格式化依赖数据"""
        nodes = []
        edges = []

        modules = dep_graph.get("modules", {})
        for module_id, module_info in modules.items():
            nodes.append({
                "id": module_id,
                "label": module_info.get("name", module_id),
                "type": "module",
                "size": module_info.get("size", 1),
            })

        dependencies = dep_graph.get("dependencies", [])
        for dep in dependencies:
            edges.append({
                "source": dep.get("from"),
                "target": dep.get("to"),
                "type": "import",
            })

        return {"nodes": nodes, "edges": edges}

    def _format_flow_data(self, context: Dict) -> Dict:
        """格式化流程数据"""
        # 基于上下文生成简单的流程数据
        steps = context.get("steps", [])
        return {
            "steps": steps,
            "entry_point": context.get("entry_point"),
            "exit_point": context.get("exit_point"),
        }

    def _format_impact_data(self, impact: Dict) -> Dict:
        """格式化影响分析数据"""
        return {
            "center": {
                "file": impact.get("file_path"),
                "name": Path(impact.get("file_path", "")).name,
            },
            "affected": impact.get("affected_files", []),
            "risk_level": impact.get("risk_level", "medium"),
        }


# 全局引擎实例
_ui_engine = GenerativeUIEngine()


@router.post("/generate")
async def generate_ui(request: UIViewRequest):
    """
    生成动态 UI 视图

    根据用户意图和数据类型，返回最适合的可视化配置
    """
    try:
        view_config = _ui_engine.generate_view_config(
            intent=request.intent,
            data_type=request.data_type,
            context=request.context or {}
        )

        return {
            "success": True,
            "view_config": view_config,
        }
    except Exception as e:
        logger.error(f"UI 生成失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/view/{view_type}")
async def get_view_template(view_type: str):
    """获取视图模板配置"""
    templates = {
        "code_flow_view": {
            "component": "CodeFlowView",
            "props": ["nodes", "edges", "highlight"],
            "style": {"minHeight": "400px"},
        },
        "dependency_graph_view": {
            "component": "DependencyGraphView",
            "props": ["nodes", "edges", "layout"],
            "style": {"minHeight": "500px"},
        },
        "architecture_map_view": {
            "component": "ArchitectureMapView",
            "props": ["layers", "modules", "entrypoints"],
            "style": {"minHeight": "600px"},
        },
        "impact_analysis_view": {
            "component": "ImpactAnalysisView",
            "props": ["center", "affected", "riskLevel"],
            "style": {"minHeight": "400px"},
        },
        "sequence_diagram_view": {
            "component": "SequenceDiagramView",
            "props": ["participants", "messages"],
            "style": {"minHeight": "400px"},
        },
    }

    if view_type not in templates:
        raise HTTPException(status_code=404, detail=f"视图模板不存在：{view_type}")

    return {
        "success": True,
        "template": templates[view_type],
    }


@router.get("/visualizer")
async def visualizer_page():
    """可视化中心页面"""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    visualizer_path = frontend_dir / "visualizer.html"

    if visualizer_path.exists():
        return FileResponse(str(visualizer_path))

    # 返回简化的内置页面
    return HTMLResponse(content=_get_builtin_visualizer())


def _get_builtin_visualizer() -> str:
    """返回内置的简化可视化页面"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>代码可视化中心</title>
    <style>
        body { font-family: system-ui; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #00d9ff; }
        .view-selector { display: flex; gap: 10px; margin: 20px 0; }
        .view-btn {
            padding: 10px 20px;
            background: #16213e;
            border: 1px solid #0f3460;
            color: #eee;
            border-radius: 6px;
            cursor: pointer;
        }
        .view-btn:hover { background: #0f3460; }
        .view-btn.active { background: #e94560; }
        .view-container {
            background: #16213e;
            border-radius: 8px;
            padding: 20px;
            min-height: 500px;
        }
        .placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 400px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 代码可视化中心</h1>
        <div class="view-selector">
            <button class="view-btn active" data-view="architecture">架构图</button>
            <button class="view-btn" data-view="dependency">依赖图</button>
            <button class="view-btn" data-view="flow">流程图</button>
            <button class="view-btn" data-view="impact">影响分析</button>
        </div>
        <div class="view-container">
            <div class="placeholder">
                <p>选择一个视图类型开始探索代码</p>
            </div>
        </div>
    </div>
    <script>
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                // TODO: 加载对应的视图
            });
        });
    </script>
</body>
</html>
"""
