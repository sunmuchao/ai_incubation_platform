"""
知识图谱构建器

从索引结果和代码分析构建知识图谱，支持：
1. 基于索引结果构建基础结构
2. 基于 Tree-sitter 解析构建符号关系
3. 基于 AST 分析构建调用关系
4. 增量更新
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import logging

from .models import KGNode, KGEdge, NodeType, EdgeType
from .graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """
    知识图谱构建器

    采用分层构建策略：
    1. 文件/模块层：基于项目扫描
    2. 符号层：基于 Tree-sitter 解析
    3. 关系层：基于导入语句和调用分析
    """

    # 语言特定的导入语句模式
    IMPORT_PATTERNS = {
        "python": {
            "import": re.compile(r'^import\s+([a-zA-Z_][\w.]*)'),
            "from_import": re.compile(r'^from\s+([a-zA-Z_][\w.]*)\s+import\s+(.+)'),
            "relative_import": re.compile(r'^from\s+(\.+\w*)\s+import\s+(.+)'),
            "class_def": re.compile(r'^class\s+(\w+)(?:\(([^)]*)\))?'),
            "function_def": re.compile(r'^(?:async\s+)?def\s+(\w+)\s*\('),
        },
        "javascript": {
            "import": re.compile(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'),
            "require": re.compile(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'),
            "class_def": re.compile(r'^(?:export\s+)?class\s+(\w+)'),
            "function_def": re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)'),
            "arrow_func": re.compile(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'),
        },
        "typescript": {
            "import": re.compile(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'),
            "class_def": re.compile(r'^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)'),
            "interface_def": re.compile(r'^(?:export\s+)?interface\s+(\w+)'),
            "function_def": re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)'),
        },
        "java": {
            "import": re.compile(r'^import\s+([a-zA-Z_][\w.]*);'),
            "class_def": re.compile(r'^(?:public\s+)?(?:abstract\s+)?class\s+(\w+)'),
            "interface_def": re.compile(r'^(?:public\s+)?interface\s+(\w+)'),
            "method_def": re.compile(r'^(?:public|private|protected)?\s+(?:static\s+)?\w+\s+(\w+)\s*\('),
        },
        "go": {
            "import": re.compile(r'^import\s+\(?[^)]*\)?'),
            "func_def": re.compile(r'^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\('),
            "type_def": re.compile(r'^type\s+(\w+)\s+(?:struct|interface)'),
        },
    }

    # 文件扩展名到语言的映射
    EXT_TO_LANGUAGE = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.c': 'c',
        '.h': 'cpp',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
    }

    def __init__(self, project_name: str, config: Optional[Dict[str, Any]] = None):
        self.project_name = project_name
        self.config = config or {}
        self.exclude_patterns = self.config.get('exclude_patterns', [
            '__pycache__', 'node_modules', '.git', 'dist', 'build', 'venv',
            '.venv', 'third_party', 'vendor', '.pytest_cache', 'coverage'
        ])
        self.max_file_size = self.config.get('max_file_size', 1024 * 1024)  # 1MB

        # 构建结果缓存
        self._graph: Optional[KnowledgeGraph] = None
        self._file_symbols: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def _should_exclude(self, file_path: str) -> bool:
        """检查文件是否应该被排除"""
        for pattern in self.exclude_patterns:
            if pattern in file_path:
                return True
        return False

    def _detect_language(self, file_path: str) -> Optional[str]:
        """检测文件语言"""
        ext = Path(file_path).suffix.lower()
        return self.EXT_TO_LANGUAGE.get(ext)

    def _parse_symbols(self, file_path: str, content: str, language: str) -> List[Dict[str, Any]]:
        """
        解析文件中的符号定义

        Returns:
            [{type, name, line, end_line, content}, ...]
        """
        symbols = []
        patterns = self.IMPORT_PATTERNS.get(language, {})

        if not patterns:
            return symbols

        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # 类定义
            class_match = patterns.get("class_def", re.compile(r'^$')).match(line)
            if class_match:
                symbols.append({
                    "type": "class",
                    "name": class_match.group(1),
                    "line": line_num,
                    "end_line": line_num,
                    "content": line[:200],
                    "parent_class": class_match.group(2) if class_match.lastindex >= 2 else None
                })

            # 接口定义
            interface_match = patterns.get("interface_def")
            if interface_match:
                match = interface_match.match(line)
                if match:
                    symbols.append({
                        "type": "interface",
                        "name": match.group(1),
                        "line": line_num,
                        "end_line": line_num,
                        "content": line[:200]
                    })

            # 函数定义
            func_match = patterns.get("function_def", re.compile(r'^$')).match(line)
            if func_match:
                symbols.append({
                    "type": "function",
                    "name": func_match.group(1),
                    "line": line_num,
                    "end_line": line_num,
                    "content": line[:200]
                })

            # TypeScript/JavaScript 箭头函数
            if language in ["javascript", "typescript"]:
                arrow_match = patterns.get("arrow_func")
                if arrow_match:
                    match = arrow_match.search(line)
                    if match:
                        symbols.append({
                            "type": "function",
                            "name": match.group(1),
                            "line": line_num,
                            "end_line": line_num,
                            "content": line[:200]
                        })

            # Go 函数定义
            if language == "go":
                func_match = patterns.get("func_def")
                if func_match:
                    match = func_match.match(line)
                    if match:
                        symbols.append({
                            "type": "function",
                            "name": match.group(1),
                            "line": line_num,
                            "end_line": line_num,
                            "content": line[:200]
                        })

                type_match = patterns.get("type_def")
                if type_match:
                    match = type_match.match(line)
                    if match:
                        symbols.append({
                            "type": "class",
                            "name": match.group(1),
                            "line": line_num,
                            "end_line": line_num,
                            "content": line[:200]
                        })

        return symbols

    def _parse_imports(self, file_path: str, content: str, language: str) -> List[Dict[str, Any]]:
        """
        解析文件的导入语句

        Returns:
            [{module, symbols, type, line}, ...]
        """
        imports = []
        patterns = self.IMPORT_PATTERNS.get(language, {})

        if not patterns:
            return imports

        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()

            # Python import
            if language == "python":
                match = patterns.get("from_import", re.compile(r'^$')).match(line)
                if match:
                    module = match.group(1)
                    imported_symbols = [s.strip() for s in match.group(2).split(',')]
                    imports.append({
                        "module": module,
                        "symbols": imported_symbols,
                        "type": "from_import",
                        "line": line_num
                    })

                match = patterns.get("import", re.compile(r'^$')).match(line)
                if match:
                    imports.append({
                        "module": match.group(1),
                        "symbols": [],
                        "type": "import",
                        "line": line_num
                    })

            # JavaScript/TypeScript import
            elif language in ["javascript", "typescript"]:
                match = patterns.get("import", re.compile(r'')).search(line)
                if match:
                    imports.append({
                        "module": match.group(1),
                        "symbols": [],
                        "type": "import",
                        "line": line_num
                    })

        return imports

    def _resolve_module_path(self, import_path: str, current_file: str, project_root: str) -> Optional[str]:
        """解析导入路径到实际文件路径"""
        current_dir = Path(current_file).parent
        project_root = Path(project_root)

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

    def _extract_function_calls(self, content: str, language: str) -> List[str]:
        """
        提取函数调用

        简单实现：匹配 function_name(...) 模式
        """
        calls = []

        if language == "python":
            # 匹配 function_name( 但不匹配 def function_name(
            pattern = re.compile(r'(?<!def\s)(?<!\.)([a-zA-Z_]\w*)\s*\(')
            for match in pattern.finditer(content):
                func_name = match.group(1)
                # 排除关键字
                if func_name not in ['if', 'for', 'while', 'with', 'def', 'class', 'return', 'import', 'from']:
                    calls.append(func_name)

        elif language in ["javascript", "typescript"]:
            pattern = re.compile(r'([a-zA-Z_]\w*)\s*\(')
            for match in pattern.finditer(content):
                func_name = match.group(1)
                if func_name not in ['if', 'for', 'while', 'function', 'class', 'return', 'import', 'export', 'const', 'let', 'var']:
                    calls.append(func_name)

        return calls

    def build(self, project_root: str, file_results: Optional[List[Any]] = None) -> KnowledgeGraph:
        """
        构建知识图谱

        Args:
            project_root: 项目根目录
            file_results: 可选的索引结果列表（如果有，优先使用）

        Returns:
            构建完成的知识图谱
        """
        project_root = Path(project_root).resolve()
        self._graph = KnowledgeGraph(project_name=self.project_name)
        self._file_symbols.clear()

        logger.info(f"开始构建知识图谱：{project_root}")

        # ========== 第 1 层：构建文件/模块节点 ==========
        logger.info("第 1 层：扫描文件并创建模块节点...")

        files_by_language = defaultdict(list)

        if file_results:
            # 使用索引结果
            for result in file_results:
                if hasattr(result, 'file_path'):
                    file_path = result.file_path
                    language = getattr(result, 'language', self._detect_language(file_path))
                    files_by_language[language].append(file_path)

                    # 创建模块节点
                    module_node = KGNode(
                        node_type=NodeType.MODULE,
                        name=Path(file_path).name,
                        file_path=file_path,
                        language=language or "unknown"
                    )
                    self._graph.add_node(module_node)
        else:
            # 扫描项目目录
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

                    files_by_language[language].append(str(file_path))

                    # 创建模块节点
                    module_node = KGNode(
                        node_type=NodeType.MODULE,
                        name=str(file_path.relative_to(project_root)),
                        file_path=str(file_path),
                        language=language
                    )
                    self._graph.add_node(module_node)

        # ========== 第 2 层：解析符号并创建符号节点 ==========
        logger.info("第 2 层：解析符号并创建符号节点...")

        for language, file_paths in files_by_language.items():
            for file_path in file_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(self.max_file_size)

                    # 解析符号
                    symbols = self._parse_symbols(file_path, content, language)
                    self._file_symbols[file_path] = symbols

                    # 为每个符号创建节点
                    for symbol in symbols:
                        node_type = NodeType.CLASS if symbol['type'] == 'class' else NodeType.FUNCTION
                        if symbol['type'] == 'interface':
                            node_type = NodeType.INTERFACE

                        symbol_node = KGNode(
                            node_type=node_type,
                            name=symbol['name'],
                            file_path=file_path,
                            symbol_name=symbol['name'],
                            start_line=symbol['line'],
                            end_line=symbol['end_line'],
                            language=language,
                            content=symbol.get('content'),
                            metadata={
                                'parent_class': symbol.get('parent_class')
                            }
                        )
                        self._graph.add_node(symbol_node)

                        # 添加 belongs_to 边（符号属于文件）
                        module_node_id = KGNode(
                            node_type=NodeType.MODULE,
                            name=Path(file_path).name,
                            file_path=file_path,
                            language=language
                        ).id
                        belongs_edge = KGEdge(
                            source=symbol_node.id,
                            target=module_node_id,
                            edge_type=EdgeType.BELONGS_TO
                        )
                        self._graph.add_edge(belongs_edge)

                except Exception as e:
                    logger.debug(f"解析符号失败 {file_path}: {e}")

        # ========== 第 3 层：构建导入/依赖关系 ==========
        logger.info("第 3 层：构建导入依赖关系...")

        for language, file_paths in files_by_language.items():
            for file_path in file_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(self.max_file_size)

                    imports = self._parse_imports(file_path, content, language)

                    for imp in imports:
                        module_path = self._resolve_module_path(imp['module'], file_path, str(project_root))

                        if module_path and module_path in [str(p) for p in files_by_language.get(language, [])]:
                            # 创建模块节点（如果不存在）
                            target_module_node = KGNode(
                                node_type=NodeType.MODULE,
                                name=Path(module_path).name,
                                file_path=module_path,
                                language=language
                            )
                            # 确保目标节点存在
                            if not self._graph.get_node(target_module_node.id):
                                self._graph.add_node(target_module_node)

                            # 创建导入边
                            source_module_node = KGNode(
                                node_type=NodeType.MODULE,
                                name=Path(file_path).name,
                                file_path=file_path,
                                language=language
                            )

                            import_edge = KGEdge(
                                source=source_module_node.id,
                                target=target_module_node.id,
                                edge_type=EdgeType.IMPORTS,
                                metadata={
                                    'imported_symbols': imp['symbols'],
                                    'import_type': imp['type']
                                }
                            )
                            self._graph.add_edge(import_edge)

                            # 如果导入了特定符号，创建符号级引用
                            for symbol_name in imp.get('symbols', []):
                                # 查找目标符号
                                target_symbols = self._graph.find_nodes_by_symbol(symbol_name)
                                for target_symbol in target_symbols:
                                    if target_symbol.file_path == module_path:
                                        ref_edge = KGEdge(
                                            source=source_module_node.id,
                                            target=target_symbol.id,
                                            edge_type=EdgeType.REFERENCES,
                                            metadata={'import_type': imp['type']}
                                        )
                                        self._graph.add_edge(ref_edge)

                except Exception as e:
                    logger.debug(f"解析导入失败 {file_path}: {e}")

        # ========== 第 4 层：构建调用关系 ==========
        logger.info("第 4 层：分析函数调用关系...")

        for language, file_paths in files_by_language.items():
            for file_path in file_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(self.max_file_size)

                    # 获取文件中定义的函数
                    file_symbols = self._file_symbols.get(file_path, [])
                    defined_functions = [s for s in file_symbols if s['type'] == 'function']

                    # 提取函数调用
                    calls = self._extract_function_calls(content, language)

                    # 创建调用关系
                    for func_symbol in defined_functions:
                        func_node = KGNode(
                            node_type=NodeType.FUNCTION,
                            name=func_symbol['name'],
                            file_path=file_path,
                            symbol_name=func_symbol['name'],
                            language=language
                        )

                        for call_name in calls:
                            # 查找被调用的函数
                            called_symbols = self._graph.find_nodes_by_symbol(call_name)
                            for called_symbol in called_symbols:
                                if called_symbol.node_type == NodeType.FUNCTION:
                                    # 避免自调用
                                    if called_symbol.id != func_node.id:
                                        call_edge = KGEdge(
                                            source=func_node.id,
                                            target=called_symbol.id,
                                            edge_type=EdgeType.CALLS,
                                            metadata={'caller_file': file_path}
                                        )
                                        self._graph.add_edge(call_edge)

                except Exception as e:
                    logger.debug(f"分析调用失败 {file_path}: {e}")

        # ========== 第 5 层：构建继承关系 ==========
        logger.info("第 5 层：分析继承关系...")

        for file_path, symbols in self._file_symbols.items():
            for symbol in symbols:
                if symbol['type'] == 'class' and symbol.get('parent_class'):
                    parent_name = symbol['parent_class'].split(',')[0].strip()  # 支持多继承，取第一个

                    # 查找父类节点
                    parent_symbols = self._graph.find_nodes_by_symbol(parent_name)

                    class_node = KGNode(
                        node_type=NodeType.CLASS,
                        name=symbol['name'],
                        file_path=file_path,
                        symbol_name=symbol['name'],
                        language=self._detect_language(file_path) or "unknown"
                    )

                    for parent_symbol in parent_symbols:
                        if parent_symbol.node_type == NodeType.CLASS:
                            extends_edge = KGEdge(
                                source=class_node.id,
                                target=parent_symbol.id,
                                edge_type=EdgeType.EXTENDS
                            )
                            self._graph.add_edge(extends_edge)

        logger.info(f"知识图谱构建完成：{len(self._graph)} 个节点，{len(self._graph._edge_index)} 条边")

        return self._graph

    def build_incremental(self, changed_files: List[str]) -> KnowledgeGraph:
        """
        增量构建/更新图谱

        Args:
            changed_files: 变更文件列表
        """
        if not self._graph:
            raise ValueError("必须先调用 build() 创建基础图谱")

        logger.info(f"增量更新 {len(changed_files)} 个文件...")

        for file_path in changed_files:
            # 移除旧的节点和边
            old_nodes = self._graph.get_nodes_by_file(file_path)
            for node in old_nodes:
                self._graph.remove_node(node.id)

            # 重新解析并添加
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(self.max_file_size)

                language = self._detect_language(file_path)
                if not language:
                    continue

                # 创建模块节点
                module_node = KGNode(
                    node_type=NodeType.MODULE,
                    name=Path(file_path).name,
                    file_path=file_path,
                    language=language
                )
                self._graph.add_node(module_node)

                # 解析符号
                symbols = self._parse_symbols(file_path, content, language)
                self._file_symbols[file_path] = symbols

                for symbol in symbols:
                    node_type = NodeType.CLASS if symbol['type'] == 'class' else NodeType.FUNCTION
                    symbol_node = KGNode(
                        node_type=node_type,
                        name=symbol['name'],
                        file_path=file_path,
                        symbol_name=symbol['name'],
                        start_line=symbol['line'],
                        end_line=symbol['end_line'],
                        language=language,
                        content=symbol.get('content')
                    )
                    self._graph.add_node(symbol_node)

            except Exception as e:
                logger.error(f"增量更新失败 {file_path}: {e}")

        return self._graph

    def get_graph(self) -> KnowledgeGraph:
        """获取当前图谱"""
        if not self._graph:
            raise ValueError("图谱尚未构建，请先调用 build()")
        return self._graph
