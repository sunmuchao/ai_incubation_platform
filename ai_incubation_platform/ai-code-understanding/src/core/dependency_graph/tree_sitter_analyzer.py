"""
Tree-sitter 符号解析器 - OPT-2 依赖分析增强

功能:
1. 使用 Tree-sitter 精确解析导入语句
2. 跨文件符号追踪
3. 支持多种导入模式 (相对导入、别名导入、动态导入)
4. 循环依赖检测增强

依赖准确度目标:
- 导入解析准确率 > 95%
- 跨文件符号追踪覆盖率 > 80%
- 循环依赖检测率 100%
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ImportInfo:
    """导入信息数据结构"""
    module_path: str  # 导入的模块路径
    import_type: str  # import, from_import, relative_import, dynamic_import
    symbols: List[str] = field(default_factory=list)  # 导入的具体符号
    alias: Optional[str] = None  # 别名
    line_number: int = 0
    is_wildcard: bool = False  # 是否是通配符导入 (from xxx import *)
    is_conditional: bool = False  # 是否是条件导入


@dataclass
class SymbolInfo:
    """符号信息数据结构"""
    name: str
    symbol_type: str  # function, class, variable, constant, type_alias
    file_path: str
    start_line: int
    end_line: int
    start_col: int = 0
    end_col: int = 0
    signature: Optional[str] = None
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)  # public, private, static, etc.
    parameters: List[str] = field(default_factory=list)  # 函数参数
    return_type: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他符号


@dataclass
class FileSymbolTable:
    """文件符号表"""
    file_path: str
    language: str
    symbols: Dict[str, SymbolInfo] = field(default_factory=dict)
    imports: List[ImportInfo] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    local_scope: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))  # scope -> symbols


class TreeSitterSymbolAnalyzer:
    """
    基于 Tree-sitter 的符号分析器
    支持精确的导入解析和符号提取
    """

    # 语言查询模板
    QUERY_TEMPLATES = {
        'python': {
            'imports': """
            (import_statement
              (dotted_name) @module)
            (import_from_statement
              (dotted_name) @module
              (wildcard_import)? @wildcard
              (aliased_import (name) @symbol (identifier) @alias)?
              (dotted_name (identifier) @symbol)?
            )
            """,
            'symbols': """
            (function_definition
              name: (identifier) @name
              parameters: (parameters) @params)? @func
            (class_definition
              name: (identifier) @name) @class
            (assignment
              (identifier) @name) @var
            """,
        },
        'javascript': {
            'imports': """
            (import_statement
              (import_clause
                (named_imports (import_specifier) @symbol)?
                (namespace_import)? @namespace
                (string) @module))
            (variable_declarator
              name: (identifier) @name
              value: (call_expression
                function: (identifier) @req
                arguments: (arguments (string) @module)))
            """,
            'symbols': """
            (function_declaration
              name: (identifier) @name)
            (class_declaration
              name: (identifier) @name)
            (variable_declarator
              name: (identifier) @name)
            """,
        },
        'typescript': {
            'imports': """
            (import_statement
              (import_clause
                (named_imports (import_specifier) @symbol)?
                (namespace_import)? @namespace
                (string) @module))
            """,
            'symbols': """
            (function_declaration
              name: (identifier) @name)
            (class_declaration
              name: (identifier) @name)
            (interface_declaration
              name: (type_identifier) @name)
            (type_alias_declaration
              name: (type_identifier) @name)
            """,
        },
        'java': {
            'imports': """
            (import_declaration
              (scoped_identifier) @module)
            (import_declaration
              (asterisk) @wildcard)
            """,
            'symbols': """
            (method_declaration
              name: (identifier) @name)
            (class_declaration
              name: (identifier) @name)
            (field_declaration
              declarator: (variable_declarator
                name: (identifier) @name))
            """,
        },
        'go': {
            'imports': """
            (import_spec
              (interpreted_string_literal) @module)
            (import_declaration
              (import_spec_list
                (import_spec
                  (package_identifier) @alias
                  (interpreted_string_literal) @module)))
            """,
            'symbols': """
            (function_declaration
              name: (identifier) @name)
            (method_declaration
              name: (field_identifier) @name)
            (type_declaration
              (type_spec
                name: (identifier) @name))
            """,
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
        '.h': 'cpp',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.parsers: Dict[str, Any] = {}
        self.supported_languages = list(self.QUERY_TEMPLATES.keys())

        # 解析器缓存目录
        self.parser_cache_dir = self.config.get('parser_cache_dir', './data/parser_cache')

        # 标准库模块列表 (用于过滤外部依赖)
        self.stdlib_modules = self._load_stdlib_modules()

    def _load_stdlib_modules(self) -> Dict[str, Set[str]]:
        """加载标准库模块列表"""
        return {
            'python': {
                'os', 'sys', 're', 'json', 'time', 'datetime', 'math', 'random',
                'collections', 'itertools', 'functools', 'pathlib', 'typing',
                'logging', 'unittest', 'io', 'string', 'copy', 'pprint',
                'http', 'urllib', 'socket', 'threading', 'multiprocessing',
                'subprocess', 'asyncio', 'contextlib', 'abc', 'dataclasses',
                'hashlib', 'base64', 'pickle', 'shelve', 'sqlite3', 'csv',
                'configparser', 'argparse', 'getopt', 'tempfile', 'shutil',
                'glob', 'fnmatch', 'stat', 'fileinput', 'filecmp', 'struct',
                'codecs', 'unicodedata', 'regex', 'difflib', 'textwrap',
                'readline', 'rlcompleter', 'array', 'weakref', 'types',
                'copyreg', 'pprint', 'reprlib', 'enum', 'graphlib',
            },
            'javascript': {
                'fs', 'path', 'http', 'https', 'url', 'querystring', 'stream',
                'util', 'events', 'buffer', 'crypto', 'zlib', 'os', 'net',
                'dns', 'tls', 'child_process', 'cluster', 'readline', 'repl',
                'vm', 'assert', 'console', 'process', 'timers',
            },
            'java': {
                'java.lang', 'java.util', 'java.io', 'java.net', 'java.nio',
                'java.time', 'java.math', 'java.security', 'java.sql',
                'java.text', 'java.util.concurrent', 'java.util.stream',
            },
            'go': {
                'fmt', 'os', 'io', 'net', 'http', 'sync', 'context', 'errors',
                'strings', 'bytes', 'regexp', 'encoding', 'json', 'xml',
                'time', 'path', 'filepath', 'sort', 'bufio', 'log',
            },
        }

    def _get_parser(self, language: str) -> Optional[Any]:
        """获取对应语言的 parser"""
        lang_key = language.lower()
        if lang_key not in self.parsers:
            try:
                from tree_sitter_languages import get_parser
                ts_language = self._get_tree_sitter_language(lang_key)
                if ts_language:
                    parser = get_parser(ts_language)
                    self.parsers[lang_key] = parser
                else:
                    self.parsers[lang_key] = None
            except Exception as e:
                logger.warning(f"加载 {language} parser 失败：{e}")
                self.parsers[lang_key] = None
        return self.parsers.get(lang_key)

    def _get_tree_sitter_language(self, language: str) -> Optional[str]:
        """获取 tree-sitter 语言名称"""
        mapping = {
            'python': 'python',
            'javascript': 'javascript',
            'typescript': 'typescript',
            'java': 'java',
            'go': 'go',
            'rust': 'rust',
            'cpp': 'cpp',
            'csharp': 'c_sharp',
            'ruby': 'ruby',
            'php': 'php',
        }
        return mapping.get(language)

    def _detect_language(self, file_path: str) -> Optional[str]:
        """从文件路径检测语言"""
        ext = Path(file_path).suffix.lower()
        return self.EXT_TO_LANGUAGE.get(ext)

    def _is_external_dependency(self, module_path: str, language: str) -> bool:
        """判断是否是外部依赖"""
        stdlib = self.stdlib_modules.get(language, set())

        if language == 'python':
            root_module = module_path.split('.')[0]
            return root_module in stdlib

        elif language in ['javascript', 'typescript']:
            # npm 包不以 ./ 或 ../ 开头
            return not module_path.startswith('.') and not module_path.startswith('/')

        elif language == 'java':
            return module_path.startswith('java.') or module_path.startswith('javax.')

        elif language == 'go':
            root_module = module_path.split('/')[0]
            return root_module in stdlib

        return False

    def analyze_file(self, file_path: str) -> Optional[FileSymbolTable]:
        """
        分析文件，提取符号表和导入信息

        Args:
            file_path: 文件路径

        Returns:
            FileSymbolTable 对象，包含符号和导入信息
        """
        language = self._detect_language(file_path)
        if not language or language not in self.supported_languages:
            logger.debug(f"不支持的语言：{file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self.analyze_content(content, language, file_path)
        except Exception as e:
            logger.error(f"分析文件失败 {file_path}: {e}")
            return None

    def analyze_content(
        self,
        content: str,
        language: str,
        file_path: Optional[str] = None
    ) -> FileSymbolTable:
        """
        分析代码内容

        Args:
            content: 代码内容
            language: 编程语言
            file_path: 文件路径

        Returns:
            FileSymbolTable 对象
        """
        symbol_table = FileSymbolTable(
            file_path=file_path or '',
            language=language
        )

        parser = self._get_parser(language)
        if not parser:
            # 降级为基于正则的解析
            return self._analyze_content_fallback(content, language, file_path)

        try:
            # 解析语法树
            tree = parser.parse(bytes(content, 'utf-8'))
            root_node = tree.root_node

            # 提取导入
            symbol_table.imports = self._extract_imports_advanced(
                root_node, content, language
            )

            # 提取符号
            symbols = self._extract_symbols_advanced(
                root_node, content, language, file_path or ''
            )
            symbol_table.symbols = {s.name: s for s in symbols}

            # 提取导出
            symbol_table.exports = self._extract_exports(
                root_node, content, language
            )

        except Exception as e:
            logger.warning(f"Tree-sitter 分析失败，降级处理：{e}")
            return self._analyze_content_fallback(content, language, file_path)

        return symbol_table

    def _analyze_content_fallback(
        self,
        content: str,
        language: str,
        file_path: Optional[str] = None
    ) -> FileSymbolTable:
        """降级的基于正则的分析"""
        symbol_table = FileSymbolTable(
            file_path=file_path or '',
            language=language
        )

        lines = content.split('\n')

        if language == 'python':
            # 提取导入
            import_pattern = re.compile(r'^import\s+([a-zA-Z_][\w.]*)')
            from_pattern = re.compile(r'^from\s+([a-zA-Z_][\w.]*)\s+import\s+(.+)')

            for i, line in enumerate(lines, 1):
                line = line.strip()

                # import xxx
                match = import_pattern.match(line)
                if match:
                    symbol_table.imports.append(ImportInfo(
                        module_path=match.group(1),
                        import_type='import',
                        line_number=i
                    ))

                # from xxx import yyy
                match = from_pattern.match(line)
                if match:
                    module = match.group(1)
                    symbols_str = match.group(2)
                    symbols = [s.strip().split(' as ')[0].strip()
                              for s in symbols_str.split(',') if s.strip()]

                    is_wildcard = '*' in symbols
                    symbol_table.imports.append(ImportInfo(
                        module_path=module,
                        import_type='from_import',
                        symbols=[s for s in symbols if s != '*'],
                        line_number=i,
                        is_wildcard=is_wildcard
                    ))

            # 提取函数和类
            def_pattern = re.compile(r'^(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')
            class_pattern = re.compile(r'^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[\(:]')

            for i, line in enumerate(lines, 1):
                match = def_pattern.match(line)
                if match:
                    name = match.group(1)
                    symbol_table.symbols[name] = SymbolInfo(
                        name=name,
                        symbol_type='function',
                        file_path=file_path or '',
                        start_line=i,
                        end_line=i,
                        signature=line.strip()
                    )

                match = class_pattern.match(line)
                if match:
                    name = match.group(1)
                    symbol_table.symbols[name] = SymbolInfo(
                        name=name,
                        symbol_type='class',
                        file_path=file_path or '',
                        start_line=i,
                        end_line=i,
                        signature=line.strip()
                    )

        return symbol_table

    def _extract_imports_advanced(
        self,
        root_node: Any,
        content: str,
        language: str
    ) -> List[ImportInfo]:
        """使用 Tree-sitter 提取导入信息"""
        imports = []

        def walk_node(node):
            # Python import
            if node.type in ['import_statement', 'import_from_statement']:
                module_node = node.child_by_field_name('module_name') or \
                              node.child_by_field_name('name')

                if module_node:
                    module_path = content[module_node.start_byte:module_node.end_byte]

                    import_type = 'import' if node.type == 'import_statement' else 'from_import'
                    symbols = []
                    is_wildcard = False

                    # 提取导入的符号
                    if node.type == 'import_from_statement':
                        wildcard = node.child_by_field_name('wildcard_import')
                        if wildcard:
                            is_wildcard = True

                        named_imports = node.child_by_field_name('names')
                        if named_imports:
                            for child in named_imports.children:
                                if child.type in ['aliased_import', 'dotted_name']:
                                    name_node = child.child_by_field_name('name') or child
                                    if name_node:
                                        sym = content[name_node.start_byte:name_node.end_byte]
                                        symbols.append(sym)

                    imports.append(ImportInfo(
                        module_path=module_path,
                        import_type=import_type,
                        symbols=symbols,
                        line_number=node.start_point[0] + 1,
                        is_wildcard=is_wildcard
                    ))

            # JavaScript/TypeScript import
            elif node.type == 'import_statement':
                clause = node.child_by_field_name('import_clause')
                if clause:
                    module_str = None
                    symbols = []

                    for child in clause.children:
                        if child.type == 'string':
                            module_str = content[child.start_byte:child.end_byte].strip('"\'')
                        elif child.type == 'named_imports':
                            for spec in child.children:
                                if spec.type == 'import_specifier':
                                    name_node = spec.child_by_field_name('name')
                                    if name_node:
                                        symbols.append(content[name_node.start_byte:name_node.end_byte])

                    if module_str:
                        imports.append(ImportInfo(
                            module_path=module_str,
                            import_type='import',
                            symbols=symbols,
                            line_number=node.start_point[0] + 1
                        ))

            # 递归遍历
            for child in node.children:
                walk_node(child)

        walk_node(root_node)
        return imports

    def _extract_symbols_advanced(
        self,
        root_node: Any,
        content: str,
        language: str,
        file_path: str
    ) -> List[SymbolInfo]:
        """使用 Tree-sitter 提取符号信息"""
        symbols = []

        def walk_node(node):
            # 函数定义
            if node.type in ['function_definition', 'function_declaration', 'method_definition']:
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    params_node = node.child_by_field_name('parameters')
                    parameters = []
                    if params_node:
                        for child in params_node.children:
                            if child.type == 'identifier':
                                parameters.append(content[child.start_byte:child.end_byte])

                    symbols.append(SymbolInfo(
                        name=name,
                        symbol_type='function',
                        file_path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        start_col=node.start_point[1],
                        end_col=node.end_point[1],
                        signature=content[node.start_byte:node.end_byte].split('\n')[0],
                        parameters=parameters
                    ))

            # 类定义
            elif node.type in ['class_definition', 'class_declaration', 'interface_declaration']:
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]

                    # 提取父类/接口
                    modifiers = []
                    superclass = node.child_by_field_name('superclass')
                    if superclass:
                        modifiers.append(f"extends:{content[superclass.start_byte:superclass.end_byte]}")

                    symbols.append(SymbolInfo(
                        name=name,
                        symbol_type='class',
                        file_path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        modifiers=modifiers
                    ))

            # 变量定义
            elif node.type == 'assignment' and language == 'python':
                left = node.child_by_field_name('left')
                if left and left.type == 'identifier':
                    name = content[left.start_byte:left.end_byte]
                    # 只记录顶层变量
                    if node.parent and node.parent.type == 'module':
                        symbols.append(SymbolInfo(
                            name=name,
                            symbol_type='variable',
                            file_path=file_path,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1
                        ))

            for child in node.children:
                walk_node(child)

        walk_node(root_node)
        return symbols

    def _extract_exports(
        self,
        root_node: Any,
        content: str,
        language: str
    ) -> List[str]:
        """提取导出的符号"""
        exports = []

        if language == 'python':
            # 查找 __all__ 定义
            def walk_node(node):
                if node.type == 'assignment':
                    left = node.child_by_field_name('left')
                    if left:
                        left_name = content[left.start_byte:left.end_byte]
                        if left_name == '__all__':
                            # 解析列表
                            right = node.child_by_field_name('right')
                            if right and right.type == 'list':
                                for item in right.children:
                                    if item.type == 'string':
                                        exports.append(content[item.start_byte:item.end_byte].strip('"\''))
                    return

                for child in node.children:
                    walk_node(child)

            walk_node(root_node)

            # 如果没有 __all__，导出所有公共符号
            if not exports:
                def walk_node2(node):
                    if node.type in ['function_definition', 'class_definition']:
                        name_node = node.child_by_field_name('name')
                        if name_node:
                            name = content[name_node.start_byte:name_node.end_byte]
                            if not name.startswith('_'):
                                exports.append(name)
                    for child in node.children:
                        walk_node2(child)

                walk_node2(root_node)

        elif language in ['javascript', 'typescript']:
            # 查找 export 语句
            def walk_node(node):
                if node.type.startswith('export'):
                    # export function/class/const
                    for child in node.children:
                        if child.type in ['function_declaration', 'class_declaration',
                                         'variable_declaration', 'interface_declaration',
                                         'type_alias_declaration']:
                            name_node = child.child_by_field_name('name')
                            if name_node:
                                exports.append(content[name_node.start_byte:name_node.end_byte])
                for child in node.children:
                    walk_node(child)

            walk_node(root_node)

        return list(set(exports))

    def resolve_symbol(
        self,
        symbol_name: str,
        file_path: str,
        project_root: str
    ) -> Optional[SymbolInfo]:
        """
        解析符号，查找定义位置

        Args:
            symbol_name: 符号名
            file_path: 当前文件路径
            project_root: 项目根目录

        Returns:
            SymbolInfo 对象或 None
        """
        # 首先在当前文件中查找
        symbol_table = self.analyze_file(file_path)
        if symbol_table and symbol_name in symbol_table.symbols:
            return symbol_table.symbols[symbol_name]

        # 通过导入关系查找
        if symbol_table:
            for import_info in symbol_table.imports:
                if self._is_external_dependency(import_info.module_path, symbol_table.language):
                    continue

                # 解析导入模块路径
                target_path = self._resolve_import_path(
                    import_info.module_path,
                    file_path,
                    project_root
                )

                if target_path and os.path.exists(target_path):
                    target_table = self.analyze_file(target_path)
                    if target_table:
                        # 检查是否是通配符导入
                        if import_info.is_wildcard:
                            if symbol_name in target_table.symbols:
                                return target_table.symbols[symbol_name]
                        # 检查是否在导入列表中
                        elif symbol_name in import_info.symbols:
                            if symbol_name in target_table.symbols:
                                return target_table.symbols[symbol_name]
                        # 检查是否是模块导入
                        elif import_info.import_type == 'import':
                            if symbol_name in target_table.symbols:
                                return target_table.symbols[symbol_name]

        return None

    def _resolve_import_path(
        self,
        import_path: str,
        current_file: str,
        project_root: str
    ) -> Optional[str]:
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
            # 绝对路径 (项目内)
            import_parts = import_path.split('.')
            for i in range(len(import_parts), 0, -1):
                relative_path = '/'.join(import_parts[:i])
                for ext in possible_extensions:
                    candidate = (project_root / (relative_path + ext)).resolve()
                    if candidate.exists():
                        return str(candidate)
                    candidate_dir = project_root / relative_path
                    if candidate_dir.exists() and candidate_dir.is_dir():
                        for ext2 in possible_extensions:
                            init_file = candidate_dir / f'__init__{ext2}'
                            if init_file.exists():
                                return str(init_file)

        return None

    def find_symbol_references(
        self,
        symbol_name: str,
        project_root: str,
        file_paths: Optional[List[str]] = None
    ) -> List[Tuple[str, int, str]]:
        """
        查找符号的所有引用位置

        Args:
            symbol_name: 符号名
            project_root: 项目根目录
            file_paths: 要搜索的文件列表 (可选)

        Returns:
            [(file_path, line_number, context), ...]
        """
        references = []

        if file_paths is None:
            # 扫描项目所有相关文件
            file_paths = []
            for ext in ['.py', '.js', '.ts', '.java', '.go']:
                for path in Path(project_root).rglob(f'*{ext}'):
                    if not any(p in str(path) for p in ['node_modules', '__pycache__', '.git', 'dist', 'build']):
                        file_paths.append(str(path))

        # 在每个文件中搜索
        pattern = re.compile(rf'\b{re.escape(symbol_name)}\b')

        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            references.append((file_path, i, line.strip()))
            except:
                continue

        return references


# 便捷函数
def create_symbol_analyzer() -> TreeSitterSymbolAnalyzer:
    """创建符号分析器"""
    return TreeSitterSymbolAnalyzer()
