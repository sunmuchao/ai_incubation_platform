"""
依赖关系图生成器

功能:
1. 基于代码导入语句构建模块间依赖关系
2. 生成有向依赖图，支持循环依赖检测
3. 输出 Graphviz DOT 格式或 JSON 格式
4. 支持依赖深度过滤和子图生成
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import json


class DependencyNode:
    """依赖图节点"""
    def __init__(self, file_path: str, module_name: str, node_type: str = "module"):
        self.file_path = file_path
        self.module_name = module_name
        self.node_type = node_type  # module, package, entrypoint
        self.in_degree = 0  # 被依赖数
        self.out_degree = 0  # 依赖他人数
        self.symbols: List[str] = []  # 导出的符号

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "module_name": self.module_name,
            "node_type": self.node_type,
            "in_degree": self.in_degree,
            "out_degree": self.out_degree,
            "symbols": self.symbols
        }


class DependencyEdge:
    """依赖边"""
    def __init__(self, source: str, target: str, edge_type: str = "import", symbols: Optional[List[str]] = None):
        self.source = source  # 源模块
        self.target = target  # 目标模块
        self.edge_type = edge_type  # import, from_import, relative_import
        self.symbols = symbols or []  # 导入的具体符号

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "symbols": self.symbols
        }


class DependencyGraph:
    """依赖关系图"""
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.nodes: Dict[str, DependencyNode] = {}
        self.edges: List[DependencyEdge] = []
        self.adjacency_list: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency_list: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: DependencyNode) -> None:
        """添加节点"""
        if node.file_path not in self.nodes:
            self.nodes[node.file_path] = node

    def add_edge(self, edge: DependencyEdge) -> None:
        """添加边"""
        self.edges.append(edge)
        self.adjacency_list[edge.source].add(edge.target)
        self.reverse_adjacency_list[edge.target].add(edge.source)

        # 更新节点度数
        if edge.source in self.nodes:
            self.nodes[edge.source].out_degree += 1
        if edge.target in self.nodes:
            self.nodes[edge.target].in_degree += 1

    def get_dependencies(self, file_path: str, recursive: bool = False, max_depth: int = -1) -> Set[str]:
        """获取模块的依赖（直接依赖或递归依赖）"""
        if file_path not in self.nodes:
            return set()

        visited = set()
        queue = [(file_path, 0)]

        while queue:
            current, depth = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if max_depth >= 0 and depth >= max_depth:
                continue

            for dep in self.adjacency_list.get(current, []):
                if dep not in visited:
                    queue.append((dep, depth + 1))

        visited.discard(file_path)
        return visited

    def get_dependents(self, file_path: str, recursive: bool = False) -> Set[str]:
        """获取依赖该模块的所有模块（反向依赖）"""
        if file_path not in self.nodes:
            return set()

        visited = set()
        queue = [file_path]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for dep in self.reverse_adjacency_list.get(current, []):
                if dep not in visited:
                    queue.append(dep)

        visited.discard(file_path)
        return visited

    def detect_cycles(self) -> List[List[str]]:
        """检测循环依赖"""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.adjacency_list.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                dfs(node)

        return cycles

    def get_top_dependencies(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取被依赖最多的模块（核心模块）"""
        sorted_nodes = sorted(
            self.nodes.values(),
            key=lambda x: x.in_degree,
            reverse=True
        )[:n]
        return [node.to_dict() for node in sorted_nodes]

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "project_name": self.project_name,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "cycle_count": len(self.detect_cycles()),
            "top_dependencies": self.get_top_dependencies(10)
        }

    def to_dot(self, max_depth: int = 2, focus_modules: Optional[List[str]] = None) -> str:
        """
        导出为 Graphviz DOT 格式

        Args:
            max_depth: 最大深度（从入口点开始）
            focus_modules: 关注的模块列表，只生成这些模块相关的子图
        """
        lines = ["digraph DependencyGraph {"]
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box, fontname="Helvetica"];')
        lines.append('  edge [fontname="Helvetica", fontsize=10];')
        lines.append("")

        # 确定要包含的节点
        included_nodes = set()
        if focus_modules:
            for module in focus_modules:
                included_nodes.add(module)
                included_nodes.update(self.get_dependencies(module, max_depth=max_depth))
                included_nodes.update(self.get_dependents(module))
        else:
            included_nodes = set(self.nodes.keys())

        # 生成节点
        for node_id, node in self.nodes.items():
            if node_id not in included_nodes:
                continue
            color = "lightblue" if node.in_degree > 5 else "lightgray"
            style = "filled"
            label = f"{node.module_name}\\n(in:{node.in_degree}, out:{node.out_degree})"
            lines.append(f'  "{node_id}" [label="{label}", style="{style}", fillcolor="{color}"];')

        lines.append("")

        # 生成边
        for edge in self.edges:
            if edge.source not in included_nodes or edge.target not in included_nodes:
                continue
            label = ", ".join(edge.symbols[:3]) if edge.symbols else ""
            if len(edge.symbols) > 3:
                label += f"... ({len(edge.symbols)})"
            if label:
                lines.append(f'  "{edge.source}" -> "{edge.target}" [label="{label}"];')
            else:
                lines.append(f'  "{edge.source}" -> "{edge.target}";')

        lines.append("}")
        return "\n".join(lines)


class DependencyGraphGenerator:
    """依赖关系图生成器"""

    # 语言特定的导入语句模式
    IMPORT_PATTERNS = {
        "python": {
            "import": re.compile(r'^import\s+([a-zA-Z_][\w.]*)'),
            "from_import": re.compile(r'^from\s+([a-zA-Z_][\w.]*)\s+import\s+(.+)'),
            "relative_import": re.compile(r'^from\s+(\.+\w*)\s+import\s+(.+)'),
        },
        "javascript": {
            "import": re.compile(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'),
            "require": re.compile(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'),
        },
        "typescript": {
            "import": re.compile(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'),
            "require": re.compile(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'),
        },
        "java": {
            "import": re.compile(r'^import\s+([a-zA-Z_][\w.]*);'),
            "static_import": re.compile(r'^import\s+static\s+([a-zA-Z_][\w.]*\.\w+);'),
        },
        "go": {
            "import": re.compile(r'^import\s+\(?[^)]*\)?'),
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.exclude_patterns = self.config.get('exclude_patterns', [
            '__pycache__', 'node_modules', '.git', 'dist', 'build', 'venv',
            '.venv', 'third_party', 'vendor'
        ])
        self.max_file_size = self.config.get('max_file_size', 1024 * 1024)  # 1MB

    def _should_exclude(self, file_path: str) -> bool:
        """检查文件是否应该被排除"""
        for pattern in self.exclude_patterns:
            if pattern in file_path:
                return True
        return False

    def _get_relative_module(self, file_path: str, import_path: str, language: str) -> str:
        """将相对导入转换为绝对模块路径"""
        if language == "python":
            if import_path.startswith('.'):
                # 计算相对层级
                base_dir = Path(file_path).parent
                dots = len(import_path) - len(import_path.lstrip('.'))
                for _ in range(dots):
                    base_dir = base_dir.parent
                module_name = import_path.lstrip('.')
                if module_name:
                    return str(base_dir / module_name.replace('.', '/'))
                return str(base_dir)
        return import_path

    def _resolve_module_path(self, import_path: str, current_file: str, project_root: str) -> Optional[str]:
        """解析导入路径到实际文件路径"""
        current_dir = Path(current_file).parent
        project_root = Path(project_root)

        # 尝试直接解析
        possible_extensions = ['.py', '.js', '.ts', '.java', '.go']

        # 相对路径
        if import_path.startswith('.'):
            for ext in possible_extensions:
                candidate = (current_dir / (import_path.replace('.', '/') + ext)).resolve()
                if candidate.exists():
                    return str(candidate)
            # 尝试目录下的 __init__ 文件
            for ext in possible_extensions:
                candidate = (current_dir / import_path.replace('.', '/') / f'__init__{ext}').resolve()
                if candidate.exists():
                    return str(candidate)
        else:
            # 绝对路径（项目内）
            import_parts = import_path.split('.')
            for i in range(len(import_parts), 0, -1):
                relative_path = '/'.join(import_parts[:i])
                for ext in possible_extensions:
                    candidate = (project_root / (relative_path + ext)).resolve()
                    if candidate.exists():
                        return str(candidate)
                    # 尝试目录
                    candidate_dir = project_root / relative_path
                    if candidate_dir.exists() and candidate_dir.is_dir():
                        for ext2 in possible_extensions:
                            init_file = candidate_dir / f'__init__{ext2}'
                            if init_file.exists():
                                return str(init_file)

        return None

    def _parse_imports(self, file_path: str, content: str, language: str) -> List[Tuple[str, str, List[str]]]:
        """
        解析文件的导入语句

        Returns:
            [(import_path, edge_type, [symbols]), ...]
        """
        imports = []
        patterns = self.IMPORT_PATTERNS.get(language, {})

        for line in content.split('\n'):
            line = line.strip()

            # Python import
            if language == "python":
                # import xxx
                match = patterns.get("import", re.compile(r'^')).match(line)
                if match:
                    imports.append((match.group(1), "import", []))

                # from xxx import yyy
                match = patterns.get("from_import", re.compile(r'^')).match(line)
                if match:
                    module = match.group(1)
                    symbols = [s.strip() for s in match.group(2).split(',')]
                    imports.append((module, "from_import", symbols))

            # JavaScript/TypeScript import
            elif language in ["javascript", "typescript"]:
                match = patterns.get("import", re.compile(r'')).search(line)
                if match:
                    imports.append((match.group(1), "import", []))

                match = patterns.get("require", re.compile(r'')).search(line)
                if match:
                    imports.append((match.group(1), "require", []))

        return imports

    def _detect_language(self, file_path: str) -> Optional[str]:
        """检测文件语言"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext)

    def generate(
        self,
        project_name: str,
        project_root: str,
        file_results: Optional[List[Any]] = None
    ) -> DependencyGraph:
        """
        生成依赖关系图

        Args:
            project_name: 项目名称
            project_root: 项目根目录
            file_results: 可选的索引结果列表（如果有，优先使用）
        """
        graph = DependencyGraph(project_name)
        project_root = Path(project_root).resolve()

        # 如果有索引结果，优先使用
        if file_results:
            for result in file_results:
                if hasattr(result, 'file_path') and hasattr(result, 'symbols'):
                    node = DependencyNode(
                        file_path=result.file_path,
                        module_name=Path(result.file_path).stem,
                        node_type="module"
                    )
                    node.symbols = [s.name for s in result.symbols]
                    graph.add_node(node)
        else:
            # 扫描项目文件
            for root, dirs, files in os.walk(project_root):
                # 排除目录
                dirs[:] = [d for d in dirs if not self._should_exclude(d)]

                for file in files:
                    file_path = Path(root) / file
                    if self._should_exclude(str(file_path)):
                        continue

                    language = self._detect_language(str(file_path))
                    if not language:
                        continue

                    node = DependencyNode(
                        file_path=str(file_path),
                        module_name=str(file_path.relative_to(project_root)),
                        node_type="module"
                    )
                    graph.add_node(node)

        # 解析导入关系
        for file_path in list(graph.nodes.keys()):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(self.max_file_size)

                language = self._detect_language(file_path)
                if not language:
                    continue

                imports = self._parse_imports(file_path, content, language)

                for import_path, edge_type, symbols in imports:
                    # 跳过标准库和外部依赖
                    if self._is_external_dependency(import_path, language):
                        continue

                    # 解析目标文件路径
                    target_path = self._resolve_module_path(import_path, file_path, str(project_root))

                    if target_path and target_path in graph.nodes:
                        edge = DependencyEdge(
                            source=file_path,
                            target=target_path,
                            edge_type=edge_type,
                            symbols=symbols
                        )
                        graph.add_edge(edge)

            except Exception as e:
                # 解析失败不影响其他文件
                continue

        # 识别入口点（被依赖但不依赖他人的模块）
        for file_path, node in graph.nodes.items():
            if node.in_degree > 0 and node.out_degree == 0:
                node.node_type = "entrypoint"
            elif node.in_degree > 5:
                node.node_type = "core_module"

        return graph

    def _is_external_dependency(self, import_path: str, language: str) -> bool:
        """判断是否是外部依赖"""
        if language == "python":
            # Python 标准库模块
            stdlib_modules = {
                'os', 'sys', 're', 'json', 'time', 'datetime', 'math', 'random',
                'collections', 'itertools', 'functools', 'pathlib', 'typing',
                'logging', 'unittest', 'io', 'string', 'copy', 'pprint',
                'http', 'urllib', 'socket', 'threading', 'multiprocessing',
                'subprocess', 'asyncio', 'contextlib', 'abc', 'dataclasses',
            }
            root_module = import_path.split('.')[0]
            return root_module in stdlib_modules

        elif language in ["javascript", "typescript"]:
            # npm 包通常不以 ./ 或 ../ 开头
            return not import_path.startswith('.')

        elif language == "java":
            # Java 标准库
            return import_path.startswith('java.') or import_path.startswith('javax.')

        elif language == "go":
            # Go 标准库
            stdlib_prefixes = ['fmt', 'os', 'io', 'net', 'http', 'sync', 'context', 'errors']
            return import_path.split('/')[0] in stdlib_prefixes

        return False


# 便捷函数
def generate_dependency_graph(
    project_name: str,
    project_root: str,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    生成项目依赖关系图

    Args:
        project_name: 项目名称
        project_root: 项目根目录
        output_format: 输出格式 (json/dot)

    Returns:
        依赖图数据
    """
    generator = DependencyGraphGenerator()
    graph = generator.generate(project_name, project_root)

    if output_format == "dot":
        return {"dot": graph.to_dot()}
    else:
        return graph.to_dict()
