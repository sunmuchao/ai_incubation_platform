"""
自动文档生成服务
提供 API 文档自动生成、架构图绘制、数据流图生成、README 智能补全、文档更新追踪等功能
"""
import os
import re
import ast
import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocType(Enum):
    """文档类型"""
    API = "api"              # API 文档
    ARCHITECTURE = "architecture"  # 架构图
    DATAFLOW = "dataflow"    # 数据流图
    README = "readme"        # README
    CHANGELOG = "changelog"  # 变更日志


class DiagramFormat(Enum):
    """图表格式"""
    MERMAID = "mermaid"
    GRAPHVIZ = "graphviz"
    PLANTUML = "plantuml"


@dataclass
class APIDocEntry:
    """API 文档条目"""
    path: str
    method: str
    summary: str
    description: str
    parameters: List[Dict[str, Any]]
    responses: Dict[str, Any]
    source_file: str
    line_number: int
    docstring: str = ""


@dataclass
class ArchitectureDiagram:
    """架构图"""
    title: str
    description: str
    layers: List[Dict[str, Any]]
    connections: List[Dict[str, str]]
    diagram_mermaid: str
    diagram_graphviz: Optional[str] = None


@dataclass
class DataFlowDiagram:
    """数据流图"""
    title: str
    description: str
    nodes: List[Dict[str, Any]]
    flows: List[Dict[str, Any]]
    diagram_mermaid: str


@dataclass
class DocUpdateRecord:
    """文档更新记录"""
    doc_path: str
    last_updated: datetime
    last_code_change: datetime
    is_outdated: bool
    changed_files: List[str]
    sync_status: str  # synced, outdated, missing


class DocGenerationService:
    """
    自动文档生成服务

    功能:
    1. API 文档自动生成 - 从代码注释和函数签名生成
    2. 架构图自动绘制 - 从依赖关系生成 Mermaid/Graphviz
    3. 数据流图生成 - 从代码调用链分析
    4. README 智能补全 - 基于项目结构分析
    5. 文档更新追踪 - 与 Git 变更同步
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self._doc_records: Dict[str, DocUpdateRecord] = {}
        self._api_docs: List[APIDocEntry] = []
        logger.info(f"DocGenerationService initialized for {project_path}")

    # ==================== API 文档生成 ====================

    def generate_api_docs(self, source_dirs: Optional[List[str]] = None) -> List[APIDocEntry]:
        """
        从代码中自动生成 API 文档

        Args:
            source_dirs: 源代码目录列表，默认为 ['src', 'api', 'routes', 'controllers']

        Returns:
            API 文档条目列表
        """
        if source_dirs is None:
            source_dirs = ['src', 'api', 'routes', 'controllers', 'handlers', 'endpoints']

        self._api_docs = []

        for source_dir in source_dirs:
            dir_path = self.project_path / source_dir
            if dir_path.exists():
                self._scan_api_files(dir_path)

        logger.info(f"Generated {len(self._api_docs)} API doc entries")
        return self._api_docs

    def _scan_api_files(self, directory: Path) -> None:
        """扫描目录中的 API 文件"""
        for file_path in directory.rglob("*.py"):
            if file_path.name.startswith('_'):
                continue
            self._parse_api_file(file_path)

    def _parse_api_file(self, file_path: Path) -> None:
        """解析 Python 文件，提取 API 端点"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            # 查找 FastAPI/Flask 路由定义
            self._extract_fastapi_routes(tree, file_path, content)
            self._extract_flask_routes(tree, file_path, content)
            self._extract_class_methods(tree, file_path, content)

        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")

    def _extract_fastapi_routes(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """提取 FastAPI 路由"""
        http_methods = {'get', 'post', 'put', 'patch', 'delete', 'options'}

        for node in ast.walk(tree):
            # 查找 @app.get, @router.post 等装饰器
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    decorator_name = self._get_decorator_name(decorator)
                    if decorator_name:
                        for method in http_methods:
                            if method in decorator_name.lower():
                                docstring = ast.get_docstring(node) or ""
                                entry = APIDocEntry(
                                    path=self._extract_path_from_decorator(decorator),
                                    method=method.upper(),
                                    summary=self._extract_summary(docstring),
                                    description=docstring,
                                    parameters=self._extract_parameters(node),
                                    responses={},
                                    source_file=str(file_path.relative_to(self.project_path)),
                                    line_number=node.lineno,
                                    docstring=docstring
                                )
                                self._api_docs.append(entry)
                                break

    def _extract_flask_routes(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """提取 Flask 路由"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    decorator_name = self._get_decorator_name(decorator)
                    if decorator_name and 'route' in decorator_name.lower():
                        docstring = ast.get_docstring(node) or ""
                        entry = APIDocEntry(
                            path=self._extract_path_from_decorator(decorator),
                            method="GET",  # Flask 默认
                            summary=self._extract_summary(docstring),
                            description=docstring,
                            parameters=self._extract_parameters(node),
                            responses={},
                            source_file=str(file_path.relative_to(self.project_path)),
                            line_number=node.lineno,
                            docstring=docstring
                        )
                        self._api_docs.append(entry)
                        break

    def _extract_class_methods(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """提取类方法作为 API 端点"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_doc = ast.get_docstring(node) or ""
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                        docstring = ast.get_docstring(item) or class_doc
                        entry = APIDocEntry(
                            path=f"/{node.name.lower()}/{item.name.replace('_', '-')}",
                            method="POST",
                            summary=self._extract_summary(docstring),
                            description=docstring,
                            parameters=self._extract_parameters(item),
                            responses={},
                            source_file=str(file_path.relative_to(self.project_path)),
                            line_number=item.lineno,
                            docstring=docstring
                        )
                        self._api_docs.append(entry)

    def _get_decorator_name(self, decorator: ast.AST) -> Optional[str]:
        """获取装饰器名称"""
        if isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        elif isinstance(decorator, ast.Name):
            return decorator.id
        return None

    def _extract_path_from_decorator(self, decorator: ast.AST) -> str:
        """从装饰器提取路由路径"""
        if isinstance(decorator, ast.Call) and decorator.args:
            arg = decorator.args[0]
            if isinstance(arg, ast.Constant):
                return str(arg.value)
            elif isinstance(arg, ast.JoinedStr):  # f-string
                parts = []
                for value in arg.values:
                    if isinstance(value, ast.Constant):
                        parts.append(str(value.value))
                    elif isinstance(value, ast.FormattedValue):
                        parts.append("{param}")
                return "".join(parts)
        return "/unknown"

    def _extract_summary(self, docstring: str) -> str:
        """从文档字符串提取摘要"""
        if not docstring:
            return ""
        lines = docstring.strip().split('\n')
        return lines[0].strip() if lines else ""

    def _extract_parameters(self, func_node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """从函数签名提取参数"""
        params = []
        # 获取有默认值的参数名
        default_arg_names = set()
        if func_node.args.defaults:
            # defaults 对应的是最后 len(defaults) 个参数
            num_defaults = len(func_node.args.defaults)
            args_with_defaults = func_node.args.args[-num_defaults:] if num_defaults <= len(func_node.args.args) else []
            default_arg_names = {a.arg for a in args_with_defaults if hasattr(a, 'arg')}

        for arg in func_node.args.args:
            if arg.arg == 'self':
                continue
            has_default = arg.arg in default_arg_names
            param = {
                "name": arg.arg,
                "in": "path" if arg.arg.endswith("_id") else "query",
                "required": not has_default,
                "schema": {"type": "string"}
            }
            if arg.annotation:
                param["schema"]["type"] = self._get_type_from_annotation(arg.annotation)
            params.append(param)
        return params

    def _get_type_from_annotation(self, annotation: ast.AST) -> str:
        """从注解获取类型"""
        if isinstance(annotation, ast.Name):
            return annotation.id.lower()
        elif isinstance(annotation, ast.Constant):
            return type(annotation.value).__name__.lower()
        return "string"

    def export_api_docs_openapi(self) -> Dict[str, Any]:
        """导出为 OpenAPI/Swagger 格式"""
        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": f"{self.project_path.name} API",
                "version": "1.0.0",
                "description": "Auto-generated API documentation"
            },
            "paths": {}
        }

        for entry in self._api_docs:
            if entry.path not in openapi["paths"]:
                openapi["paths"][entry.path] = {}

            openapi["paths"][entry.path][entry.method.lower()] = {
                "summary": entry.summary,
                "description": entry.description,
                "operationId": f"{entry.method.lower()}_{entry.path.replace('/', '_')}",
                "parameters": entry.parameters,
                "responses": {
                    "200": {"description": "Successful response"},
                    "400": {"description": "Bad request"},
                    "500": {"description": "Server error"}
                }
            }

        return openapi

    def export_api_docs_markdown(self) -> str:
        """导出为 Markdown 格式"""
        md = [f"# {self.project_path.name} API Documentation\n"]
        md.append(f"Generated on: {datetime.now().isoformat()}\n")
        md.append(f"Total endpoints: {len(self._api_docs)}\n")
        md.append("---\n")

        # 按路径分组
        paths = {}
        for entry in self._api_docs:
            if entry.path not in paths:
                paths[entry.path] = []
            paths[entry.path].append(entry)

        for path, entries in sorted(paths.items()):
            md.append(f"## `{path}`\n")
            for entry in entries:
                md.append(f"### {entry.method} {path}\n")
                md.append(f"**Source**: `{entry.source_file}` (line {entry.line_number})\n")
                if entry.summary:
                    md.append(f"{entry.summary}\n")
                if entry.description and entry.description != entry.summary:
                    md.append(f"\n{entry.description}\n")
                if entry.parameters:
                    md.append("\n**Parameters**:\n")
                    for param in entry.parameters:
                        required = "required" if param.get("required") else "optional"
                        md.append(f"- `{param['name']}` ({param['in']}, {required})\n")
                md.append("\n---\n")

        return "\n".join(md)

    # ==================== 架构图生成 ====================

    def generate_architecture_diagram(
        self,
        dependency_graph: Optional[Any] = None,
        format: DiagramFormat = DiagramFormat.MERMAID
    ) -> ArchitectureDiagram:
        """
        生成项目架构图

        Args:
            dependency_graph: 依赖图对象（可选）
            format: 输出格式

        Returns:
            ArchitectureDiagram 对象
        """
        # 分析项目结构
        layers = self._detect_architecture_layers()
        connections = self._detect_layer_connections(layers)

        # 生成 Mermaid 图表
        mermaid_code = self._generate_mermaid_architecture(layers, connections)

        return ArchitectureDiagram(
            title=f"{self.project_path.name} Architecture",
            description="Auto-generated architecture diagram based on code structure analysis",
            layers=layers,
            connections=connections,
            diagram_mermaid=mermaid_code
        )

    def _detect_architecture_layers(self) -> List[Dict[str, Any]]:
        """检测项目架构分层"""
        layers = []

        # 定义常见分层模式
        layer_patterns = {
            "Presentation Layer": ["**/api/**", "**/routes/**", "**/controllers/**", "**/views/**", "**/handlers/**"],
            "Business Layer": ["**/services/**", "**/business/**", "**/domain/**", "**/usecases/**"],
            "Data Layer": ["**/models/**", "**/repositories/**", "**/dao/**", "**/db/**", "**/data/**"],
            "Core Layer": ["**/core/**", "**/utils/**", "**/common/**", "**/shared/**"],
            "Infrastructure": ["**/config/**", "**/middleware/**", "**/infrastructure/**"]
        }

        for layer_name, patterns in layer_patterns.items():
            matching_paths = []
            for pattern in patterns:
                for path in self.project_path.glob(pattern.replace("**/", "")):
                    if path.is_dir() or (path.is_file() and path.suffix == '.py'):
                        rel_path = str(path.relative_to(self.project_path))
                        matching_paths.append(rel_path)

            if matching_paths:
                layers.append({
                    "name": layer_name,
                    "paths": list(set(matching_paths))[:10],  # 限制数量
                    "count": len(matching_paths)
                })

        # 如果没有检测到分层，使用目录结构
        if not layers:
            root_dirs = [d.name for d in self.project_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
            if root_dirs:
                layers.append({
                    "name": "Project Modules",
                    "paths": root_dirs,
                    "count": len(root_dirs)
                })

        return layers

    def _detect_layer_connections(self, layers: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """检测层间连接"""
        connections = []
        layer_names = [l["name"] for l in layers]

        # 基于常见架构模式的连接
        connection_patterns = [
            ("Presentation Layer", "Business Layer"),
            ("Business Layer", "Data Layer"),
            ("Business Layer", "Core Layer"),
            ("Data Layer", "Core Layer"),
        ]

        for source, target in connection_patterns:
            if source in layer_names and target in layer_names:
                connections.append({"from": source, "to": target, "type": "depends_on"})

        return connections

    def _generate_mermaid_architecture(
        self,
        layers: List[Dict[str, Any]],
        connections: List[Dict[str, str]]
    ) -> str:
        """生成 Mermaid 架构图代码"""
        lines = ["graph TD"]

        # 添加子图表示层
        for i, layer in enumerate(layers):
            safe_name = layer["name"].replace(" ", "_")
            lines.append(f"  subgraph {safe_name}[\"{layer['name']}\"]")
            # 添加层内节点
            for j, path in enumerate(layer.get("paths", [])[:5]):
                node_name = Path(path).stem or Path(path).name
                lines.append(f"    {safe_name}_{j}[{node_name}]")
            lines.append("  end")

        # 添加连接
        layer_names = [l["name"].replace(" ", "_") for l in layers]
        for conn in connections:
            from_name = conn["from"].replace(" ", "_")
            to_name = conn["to"].replace(" ", "_")
            lines.append(f"  {from_name} --> {to_name}")

        return "\n".join(lines)

    # ==================== 数据流图生成 ====================

    def generate_dataflow_diagram(
        self,
        entry_points: Optional[List[str]] = None,
        format: DiagramFormat = DiagramFormat.MERMAID
    ) -> DataFlowDiagram:
        """
        生成数据流图

        Args:
            entry_points: 入口点文件列表
            format: 输出格式

        Returns:
            DataFlowDiagram 对象
        """
        if entry_points is None:
            entry_points = self._find_entry_points()

        # 分析数据流
        nodes = []
        flows = []
        visited = set()

        for entry in entry_points:
            self._trace_data_flow(entry, nodes, flows, visited)

        # 生成 Mermaid 代码
        mermaid_code = self._generate_mermaid_dataflow(nodes, flows)

        return DataFlowDiagram(
            title=f"{self.project_path.name} Data Flow",
            description="Auto-generated data flow diagram based on code analysis",
            nodes=nodes,
            flows=flows,
            diagram_mermaid=mermaid_code
        )

    def _find_entry_points(self) -> List[str]:
        """查找项目入口点"""
        entry_points = []
        patterns = ["main.py", "app.py", "cli.py", "server.py", "wsgi.py", "asgi.py"]

        for pattern in patterns:
            path = self.project_path / pattern
            if path.exists():
                entry_points.append(str(path.relative_to(self.project_path)))

        # 查找 src/main.py 等
        src_main = self.project_path / "src" / "main.py"
        if src_main.exists() and str(src_main.relative_to(self.project_path)) not in entry_points:
            entry_points.append(str(src_main.relative_to(self.project_path)))

        return entry_points

    def _trace_data_flow(
        self,
        file_path: str,
        nodes: List[Dict[str, Any]],
        flows: List[Dict[str, Any]],
        visited: Set[str],
        depth: int = 0
    ) -> None:
        """追踪数据流"""
        if depth > 5 or file_path in visited:
            return

        visited.add(file_path)
        full_path = self.project_path / file_path

        if not full_path.exists():
            return

        # 添加节点
        node = {
            "id": file_path,
            "name": Path(file_path).stem,
            "type": "module",
            "imports": [],
            "exports": []
        }

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            # 提取导入
            imports = self._extract_imports(tree)
            node["imports"] = imports

            # 提取导出
            exports = self._extract_exports(tree)
            node["exports"] = exports

        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")

        nodes.append(node)

        # 追踪依赖
        for imp in imports:
            imp_path = self._resolve_import_to_path(imp, file_path)
            if imp_path and imp_path not in visited:
                flows.append({
                    "from": file_path,
                    "to": imp_path,
                    "type": "imports",
                    "symbol": imp
                })
                self._trace_data_flow(imp_path, nodes, flows, visited, depth + 1)

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """提取导入语句"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        imports.append(f"{node.module}.{alias.name}")
        return imports[:10]  # 限制数量

    def _extract_exports(self, tree: ast.AST) -> List[str]:
        """提取导出的符号"""
        exports = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith('_'):
                    exports.append(node.name)
        return exports[:10]

    def _resolve_import_to_path(self, import_name: str, current_file: str) -> Optional[str]:
        """将导入解析为文件路径"""
        # 尝试解析为相对路径
        parts = import_name.split('.')
        current_dir = Path(current_file).parent

        # 尝试当前目录
        for i in range(len(parts), 0, -1):
            potential_path = current_dir / "/".join(parts[:i]) / "__init__.py"
            if (self.project_path / potential_path).exists():
                return str(potential_path)

            potential_path = current_dir / ("/".join(parts[:i]) + ".py")
            if (self.project_path / potential_path).exists():
                return str(potential_path)

        return None

    def _generate_mermaid_dataflow(
        self,
        nodes: List[Dict[str, Any]],
        flows: List[Dict[str, Any]]
    ) -> str:
        """生成 Mermaid 数据流图代码"""
        lines = ["graph LR"]

        # 添加节点
        for node in nodes:
            safe_id = node["id"].replace("/", "_").replace(".", "_")
            lines.append(f'  {safe_id}["{node["name"]}"]')

        # 添加流
        for flow in flows:
            from_id = flow["from"].replace("/", "_").replace(".", "_")
            to_id = flow["to"].replace("/", "_").replace(".", "_")
            lines.append(f'  {from_id} -.->|{flow["symbol"]}| {to_id}')

        return "\n".join(lines)

    # ==================== README 智能补全 ====================

    def generate_readme(self) -> str:
        """
        生成项目 README

        Returns:
            Markdown 格式的 README 内容
        """
        readme_sections = []

        # 标题
        project_name = self.project_path.name.replace('-', ' ').replace('_', ' ').title()
        readme_sections.append(f"# {project_name}\n")

        # 项目描述
        readme_sections.append(self._generate_project_description())

        # 快速开始
        readme_sections.append(self._generate_quick_start())

        # 项目结构
        readme_sections.append(self._generate_project_structure())

        # 架构图
        arch_diagram = self.generate_architecture_diagram()
        readme_sections.append(f"## Architecture\n")
        readme_sections.append(f"```mermaid\n{arch_diagram.diagram_mermaid}\n```\n")

        # API 文档
        if self._api_docs or self.generate_api_docs():
            readme_sections.append("## API Reference\n")
            readme_sections.append(f"See [API Documentation](docs/API.md) for details.\n")

        # 安装说明
        readme_sections.append(self._generate_installation())

        # 使用说明
        readme_sections.append(self._generate_usage())

        # 开发指南
        readme_sections.append(self._generate_development_guide())

        # 测试
        readme_sections.append(self._generate_testing())

        # 贡献
        readme_sections.append(self._generate_contributing())

        # 许可证
        readme_sections.append(self._generate_license())

        return "\n".join(readme_sections)

    def _generate_project_description(self) -> str:
        """生成项目描述"""
        # 尝试从现有 README 或文档提取
        for readme_pattern in ["README*", "docs/*.md"]:
            for doc in self.project_path.glob(readme_pattern):
                if doc.name.lower().startswith('readme'):
                    try:
                        with open(doc, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 提取第一段描述
                            if content:
                                return content.split('\n\n')[0] + "\n\n"
                    except:
                        pass

        # 基于代码分析生成描述
        tech_stack = self._detect_tech_stack()
        description = f"A Python-based project"
        if tech_stack:
            frameworks = [t for t in tech_stack if t in ['FastAPI', 'Flask', 'Django', 'PyTorch', 'TensorFlow']]
            if frameworks:
                description = f"A {frameworks[0]} based project"

        return f"{description}.\n\n"

    def _detect_tech_stack(self) -> List[str]:
        """检测技术栈"""
        tech_stack = []

        # 检查 requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            with open(req_file, 'r') as f:
                content = f.read().lower()
                if 'fastapi' in content:
                    tech_stack.append('FastAPI')
                if 'flask' in content:
                    tech_stack.append('Flask')
                if 'django' in content:
                    tech_stack.append('Django')
                if 'pytorch' in content or 'torch' in content:
                    tech_stack.append('PyTorch')
                if 'tensorflow' in content:
                    tech_stack.append('TensorFlow')
                if 'chromadb' in content:
                    tech_stack.append('ChromaDB')
                if 'openai' in content:
                    tech_stack.append('OpenAI')

        return tech_stack

    def _generate_quick_start(self) -> str:
        """生成快速开始指南"""
        has_requirements = (self.project_path / "requirements.txt").exists()
        has_setup = (self.project_path / "setup.py").exists()
        has_makefile = (self.project_path / "Makefile").exists()

        lines = ["## Quick Start\n"]

        if has_requirements:
            lines.append("```bash")
            lines.append("# Install dependencies")
            lines.append("pip install -r requirements.txt")
            lines.append("```\n")

        if has_setup:
            lines.append("```bash")
            lines.append("# Or install as package")
            lines.append("pip install -e .")
            lines.append("```\n")

        lines.append("```bash")
        lines.append("# Run the application")
        # 查找入口文件
        for entry in ["main.py", "src/main.py", "app.py"]:
            if (self.project_path / entry).exists():
                lines.append(f"python {entry}")
                break
        else:
            lines.append("python <entry_point>")
        lines.append("```\n")

        return "\n".join(lines)

    def _generate_project_structure(self) -> str:
        """生成项目结构"""
        lines = ["## Project Structure\n"]
        lines.append("```")

        def tree_structure(path: Path, prefix: str = "", is_last: bool = True) -> List[str]:
            result = []
            current_prefix = "└── " if is_last else "├── "
            result.append(f"{prefix}{current_prefix}{path.name}")

            if path.is_dir() and not path.name.startswith('.') and path.name not in ['__pycache__', 'node_modules', '.git']:
                children = list(path.iterdir())[:10]  # 限制数量
                new_prefix = prefix + ("    " if is_last else "│   ")
                for i, child in enumerate(children):
                    is_last_child = i == len(children) - 1
                    result.extend(tree_structure(child, new_prefix, is_last_child))

            return result

        # 从项目根目录开始
        for item in sorted(self.project_path.iterdir()):
            if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules']:
                continue
            lines.extend(tree_structure(item, is_last=(item == sorted(self.project_path.iterdir())[-1])))

        lines.append("```\n")
        return "\n".join(lines)

    def _generate_installation(self) -> str:
        """生成安装说明"""
        lines = ["## Installation\n"]

        if (self.project_path / "requirements.txt").exists():
            lines.append("```bash")
            lines.append("pip install -r requirements.txt")
            lines.append("```\n")

        if (self.project_path / "pyproject.toml").exists():
            lines.append("Or install with poetry:")
            lines.append("```bash")
            lines.append("poetry install")
            lines.append("```\n")

        return "\n".join(lines)

    def _generate_usage(self) -> str:
        """生成使用说明"""
        lines = ["## Usage\n"]

        # 查找示例或演示文件
        demo_files = list(self.project_path.glob("demo*.py")) + list(self.project_path.glob("example*.py"))
        if demo_files:
            lines.append("See the demo files for usage examples:\n")
            for demo in demo_files[:3]:
                lines.append(f"- `{demo.name}`")
            lines.append("")

        return "\n".join(lines)

    def _generate_development_guide(self) -> str:
        """生成开发指南"""
        lines = ["## Development\n"]
        lines.append("```bash")
        lines.append("# Clone the repository")
        lines.append("git clone <repository-url>")
        lines.append("")
        lines.append("# Install in development mode")
        lines.append("pip install -e .")
        lines.append("```\n")
        return "\n".join(lines)

    def _generate_testing(self) -> str:
        """生成测试说明"""
        lines = ["## Testing\n"]

        has_tests = (self.project_path / "tests").exists() or list(self.project_path.glob("test_*.py"))

        if has_tests:
            lines.append("```bash")
            lines.append("# Run tests")
            lines.append("pytest")
            lines.append("```\n")
        else:
            lines.append("No tests found. Consider adding tests to ensure code quality.\n")

        return "\n".join(lines)

    def _generate_contributing(self) -> str:
        """生成贡献指南"""
        lines = ["## Contributing\n"]
        lines.append("1. Fork the repository")
        lines.append("2. Create a feature branch")
        lines.append("3. Commit your changes")
        lines.append("4. Push to the branch")
        lines.append("5. Create a Pull Request\n")
        return "\n".join(lines)

    def _generate_license(self) -> str:
        """生成许可证部分"""
        lines = ["## License\n"]

        # 检查 LICENSE 文件
        for license_file in ["LICENSE", "LICENSE.txt", "LICENSE.md"]:
            if (self.project_path / license_file).exists():
                lines.append(f"See [{license_file}](/{license_file}) for details.\n")
                break
        else:
            lines.append("MIT License\n")

        return "\n".join(lines)

    # ==================== 文档更新追踪 ====================

    def track_doc_updates(
        self,
        doc_paths: Optional[List[str]] = None,
        git_diff: Optional[Dict[str, Any]] = None
    ) -> List[DocUpdateRecord]:
        """
        追踪文档更新状态

        Args:
            doc_paths: 文档路径列表
            git_diff: Git 变更 Diff（可选）

        Returns:
            文档更新记录列表
        """
        if doc_paths is None:
            doc_paths = self._find_documentation_files()

        records = []
        for doc_path in doc_paths:
            record = self._analyze_doc_status(doc_path, git_diff)
            records.append(record)
            self._doc_records[doc_path] = record

        return records

    def _find_documentation_files(self) -> List[str]:
        """查找项目中的文档文件"""
        doc_patterns = ["README*", "docs/**/*.md", "*.md", "CHANGELOG*"]
        docs = []

        for pattern in doc_patterns:
            for doc in self.project_path.glob(pattern):
                if doc.is_file():
                    docs.append(str(doc.relative_to(self.project_path)))

        return docs

    def _analyze_doc_status(
        self,
        doc_path: str,
        git_diff: Optional[Dict[str, Any]] = None
    ) -> DocUpdateRecord:
        """分析文档状态"""
        full_path = self.project_path / doc_path

        last_updated = datetime.fromtimestamp(full_path.stat().st_mtime) if full_path.exists() else datetime.now()

        # 分析相关代码变更
        related_changes = []
        if git_diff:
            related_changes = self._find_related_code_changes(doc_path, git_diff)

        is_outdated = len(related_changes) > 0
        sync_status = "outdated" if is_outdated else "synced" if full_path.exists() else "missing"

        return DocUpdateRecord(
            doc_path=doc_path,
            last_updated=last_updated,
            last_code_change=datetime.now() if related_changes else last_updated,
            is_outdated=is_outdated,
            changed_files=related_changes,
            sync_status=sync_status
        )

    def _find_related_code_changes(
        self,
        doc_path: str,
        git_diff: Dict[str, Any]
    ) -> List[str]:
        """查找与文档相关的代码变更"""
        related = []

        # 基于文档类型匹配相关代码
        doc_name = Path(doc_path).stem.lower()

        if "api" in doc_name:
            # API 文档与 API 代码关联
            for changed_file in git_diff.get("changed_files", []):
                if any(x in changed_file.lower() for x in ['api', 'route', 'controller', 'handler']):
                    related.append(changed_file)

        elif "architecture" in doc_name:
            # 架构文档与核心模块关联
            for changed_file in git_diff.get("changed_files", []):
                if any(x in changed_file.lower() for x in ['core', 'service', 'model']):
                    related.append(changed_file)

        return related

    def get_doc_status_report(self) -> Dict[str, Any]:
        """生成文档状态报告"""
        if not self._doc_records:
            self.track_doc_updates()

        total = len(self._doc_records)
        synced = sum(1 for r in self._doc_records.values() if r.sync_status == "synced")
        outdated = sum(1 for r in self._doc_records.values() if r.is_outdated)
        missing = sum(1 for r in self._doc_records.values() if r.sync_status == "missing")

        return {
            "total": total,
            "synced": synced,
            "outdated": outdated,
            "missing": missing,
            "records": [
                {
                    "path": r.doc_path,
                    "status": r.sync_status,
                    "last_updated": r.last_updated.isoformat(),
                    "changed_files": r.changed_files
                }
                for r in self._doc_records.values()
            ]
        }

    # ==================== 工具方法 ====================

    def export_all_docs(self, output_dir: str = "docs/generated") -> Dict[str, str]:
        """
        导出所有生成的文档

        Args:
            output_dir: 输出目录

        Returns:
            生成的文件路径字典
        """
        output_path = self.project_path / output_dir
        output_path.mkdir(parents=True, exist_ok=True)

        generated = {}

        # 生成 API 文档
        api_md = output_path / "API.md"
        with open(api_md, 'w', encoding='utf-8') as f:
            f.write(self.export_api_docs_markdown())
        generated["api"] = str(api_md)

        # 生成架构图
        arch_diagram = self.generate_architecture_diagram()
        arch_md = output_path / "ARCHITECTURE.md"
        with open(arch_md, 'w', encoding='utf-8') as f:
            f.write(f"# {arch_diagram.title}\n\n")
            f.write(f"{arch_diagram.description}\n\n")
            f.write(f"```mermaid\n{arch_diagram.diagram_mermaid}\n```\n")
        generated["architecture"] = str(arch_md)

        # 生成数据流图
        flow_diagram = self.generate_dataflow_diagram()
        flow_md = output_path / "DATAFLOW.md"
        with open(flow_md, 'w', encoding='utf-8') as f:
            f.write(f"# {flow_diagram.title}\n\n")
            f.write(f"{flow_diagram.description}\n\n")
            f.write(f"```mermaid\n{flow_diagram.diagram_mermaid}\n```\n")
        generated["dataflow"] = str(flow_md)

        # 生成 README
        readme_md = self.project_path / "README_AUTO.md"
        with open(readme_md, 'w', encoding='utf-8') as f:
            f.write(self.generate_readme())
        generated["readme"] = str(readme_md)

        # 生成 OpenAPI 规范
        openapi_json = output_path / "openapi.json"
        with open(openapi_json, 'w', encoding='utf-8') as f:
            json.dump(self.export_api_docs_openapi(), f, indent=2)
        generated["openapi"] = str(openapi_json)

        logger.info(f"Exported documentation to {output_path}")
        return generated


# 便捷函数
def create_doc_service(project_path: str) -> DocGenerationService:
    """创建文档生成服务实例"""
    return DocGenerationService(project_path)


def generate_docs(project_path: str, output_dir: str = "docs/generated") -> Dict[str, str]:
    """一键生成所有文档"""
    service = create_doc_service(project_path)
    service.generate_api_docs()
    return service.export_all_docs(output_dir)
