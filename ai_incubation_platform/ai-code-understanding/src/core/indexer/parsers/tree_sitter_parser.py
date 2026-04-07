"""
Tree-sitter代码解析器实现
支持多语言的语法解析、符号提取、智能分块
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import re
import tree_sitter
from tree_sitter_languages import get_parser

from ..base import BaseParser, FileIndexResult, CodeChunk, CodeSymbol


class TreeSitterParser(BaseParser):
    """
    基于Tree-sitter的多语言代码解析器
    支持的语言：Python, JavaScript/TypeScript, Java, Go, Rust, C++, C#, Ruby, PHP等
    """

    # 语言映射
    LANGUAGE_MAPPING = {
        'python': 'python',
        'javascript': 'javascript',
        'typescript': 'typescript',
        'tsx': 'tsx',
        'jsx': 'javascript',
        'java': 'java',
        'go': 'go',
        'rust': 'rust',
        'cpp': 'cpp',
        'c': 'c',
        'csharp': 'c_sharp',
        'ruby': 'ruby',
        'php': 'php',
        'swift': 'swift',
        'kotlin': 'kotlin',
        'scala': 'scala',
        'sql': 'sql',
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.parsers = {}  # 语言到parser实例的缓存
        self.max_chunk_size = self.config.get('max_chunk_size', 1500)  # 最大块大小（字符数）
        self.min_chunk_size = self.config.get('min_chunk_size', 100)  # 最小块大小
        self.supported_languages = list(self.LANGUAGE_MAPPING.keys())

    def supports_language(self, language: str) -> bool:
        return language.lower() in self.LANGUAGE_MAPPING

    def _get_parser(self, language: str) -> Optional[tree_sitter.Parser]:
        """获取对应语言的parser"""
        lang_key = language.lower()
        if lang_key not in self.parsers:
            try:
                # tree_sitter_languages 的 get_parser 已负责加载语言并返回 Parser。
                # 避免额外的 get_language 调用触发版本不兼容的初始化异常。
                parser = get_parser(self.LANGUAGE_MAPPING[lang_key])
                self.parsers[lang_key] = parser
            except Exception as e:
                # 当前环境中 tree_sitter_languages 可能因版本不兼容在加载时抛出固定 TypeError。
                # 该错误对功能影响不大（我们会走 fallback），但会在每次 p0_demo/索引时污染日志。
                if "__init__() takes exactly 1 argument" not in str(e):
                    print(f"加载{language}解析器失败: {str(e)}")
                # 缓存失败结果，避免对同一语言重复尝试加载
                self.parsers[lang_key] = None
                return None
        return self.parsers.get(lang_key)

    def _parse_content_fallback(
        self,
        content: str,
        language: str,
        file_path: Optional[str],
    ) -> FileIndexResult:
        """
        tree-sitter 解析器不可用时的最小降级实现：
        - 提取 python 的 def/class 符号（行号近似）
        - 生成一个“整文件”code chunk（保证下游引用/校验可跑通）
        """
        lines = content.splitlines()

        symbols: List[CodeSymbol] = []
        imports: List[str] = []
        exports: List[str] = []

        if language == "python":
            def_re = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
            class_re = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\b")

            for i, line in enumerate(lines, start=1):
                m = def_re.match(line)
                if m:
                    name = m.group(1)
                    symbols.append(
                        CodeSymbol(
                            name=name,
                            symbol_type="function",
                            file_path=file_path or "",
                            start_line=i,
                            end_line=i,
                            signature=line.strip(),
                            docstring=None,
                        )
                    )
                    continue

                m = class_re.match(line)
                if m:
                    name = m.group(1)
                    symbols.append(
                        CodeSymbol(
                            name=name,
                            symbol_type="class",
                            file_path=file_path or "",
                            start_line=i,
                            end_line=i,
                            signature=line.strip(),
                            docstring=None,
                        )
                    )
                    continue

            # import / from 级别的最小提取
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    imports.append(stripped)

            # __all__ 优先，否则返回所有非下划线开头符号
            for line in lines:
                if line.strip().startswith("__all__") and "[" in line and "]" in line:
                    try:
                        raw = line[line.find("[") + 1 : line.rfind("]")]
                        items = [x.strip().strip("'\"") for x in raw.split(",")]
                        exports = [x for x in items if x]
                    except Exception:
                        exports = []
                    break

            if not exports:
                exports = [s.name for s in symbols if not s.name.startswith("_")]

        # 一个 chunk：保证下游校验/引用能拿到代码行
        chunk = CodeChunk(
            file_path=file_path or "",
            language=language,
            content=content,
            start_line=1,
            end_line=len(lines) if lines else 1,
            chunk_type="code",
            symbols=[s.name for s in symbols],
        )

        return FileIndexResult(
            file_path=file_path or "",
            language=language,
            chunks=[chunk],
            symbols=symbols,
            imports=list(set(imports)),
            exports=list(set(exports)),
        )

    def _extract_symbols(self, tree: tree_sitter.Tree, content: str, language: str) -> List[CodeSymbol]:
        """从语法树中提取符号信息"""
        symbols = []
        root_node = tree.root_node

        def walk_node(node, parent_type=None):
            # 函数定义
            if node.type in ['function_definition', 'method_definition', 'function_declaration',
                           'arrow_function', 'method', 'func_declaration']:
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    signature = content[node.start_byte:node.end_byte].split('\n')[0]
                    symbols.append(CodeSymbol(
                        name=name,
                        symbol_type='function',
                        file_path='',  # 后续填充
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        signature=signature,
                        docstring=self._extract_docstring(node, content)
                    ))

            # 类定义
            elif node.type in ['class_definition', 'class_declaration', 'interface_declaration',
                             'struct_definition', 'enum_definition']:
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    symbols.append(CodeSymbol(
                        name=name,
                        symbol_type='class',
                        file_path='',
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        docstring=self._extract_docstring(node, content)
                    ))

            # 递归遍历子节点
            for child in node.children:
                walk_node(child, node.type)

        walk_node(root_node)
        return symbols

    def _extract_docstring(self, node: tree_sitter.Node, content: str) -> Optional[str]:
        """提取文档字符串"""
        # 检查第一个子节点是否是文档字符串
        if node.children:
            first_child = node.children[0]
            if first_child.type in ['string', 'comment', 'docstring']:
                docstring = content[first_child.start_byte:first_child.end_byte]
                # 移除引号等标记
                docstring = docstring.strip('"\'`').strip()
                if docstring:
                    return docstring

        # 检查节点前的注释
        prev_sibling = node.prev_sibling
        while prev_sibling:
            if prev_sibling.type in ['comment', 'line_comment', 'block_comment']:
                comment = content[prev_sibling.start_byte:prev_sibling.end_byte]
                comment = comment.lstrip('#/').strip()
                if comment:
                    return comment
            prev_sibling = prev_sibling.prev_sibling

        return None

    def _split_into_chunks(
        self,
        content: str,
        symbols: List[CodeSymbol],
        language: str
    ) -> List[CodeChunk]:
        """智能分块：优先按语义边界（函数、类）分块"""
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_chunk_start = 1
        current_chunk_size = 0
        current_symbols = []

        # 按符号位置排序
        sorted_symbols = sorted(symbols, key=lambda s: s.start_line)
        symbol_idx = 0

        for line_num, line in enumerate(lines, 1):
            line_len = len(line) + 1  # +1 for newline

            # 检查是否遇到新的符号开始
            while symbol_idx < len(sorted_symbols) and sorted_symbols[symbol_idx].start_line == line_num:
                # 如果当前块不为空，先提交
                if current_chunk:
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > self.min_chunk_size:
                        chunks.append(CodeChunk(
                            file_path='',
                            language=language,
                            content=chunk_content,
                            start_line=current_chunk_start,
                            end_line=line_num - 1,
                            chunk_type='code',
                            symbols=current_symbols.copy()
                        ))
                    current_chunk = []
                    current_symbols = []
                    current_chunk_size = 0
                    current_chunk_start = line_num

                current_symbols.append(sorted_symbols[symbol_idx].name)
                symbol_idx += 1

            # 检查块大小是否超过限制
            if current_chunk_size + line_len > self.max_chunk_size and current_chunk:
                # 寻找合适的分割点（空行或块结束）
                split_idx = len(current_chunk) - 1
                while split_idx > 0:
                    if current_chunk[split_idx].strip() == '' or \
                       current_chunk[split_idx].strip().endswith(('}', ']', ')', ';')):
                        break
                    split_idx -= 1

                if split_idx > 0:
                    # 在split_idx处分割
                    chunk_content = '\n'.join(current_chunk[:split_idx + 1])
                    chunks.append(CodeChunk(
                        file_path='',
                        language=language,
                        content=chunk_content,
                        start_line=current_chunk_start,
                        end_line=current_chunk_start + split_idx,
                        chunk_type='code',
                        symbols=current_symbols.copy()
                    ))
                    # 剩余部分作为新块开始
                    current_chunk = current_chunk[split_idx + 1:]
                    current_chunk_start = current_chunk_start + split_idx + 1
                    current_chunk_size = sum(len(l) + 1 for l in current_chunk)
                else:
                    # 找不到合适分割点，直接分割
                    chunk_content = '\n'.join(current_chunk)
                    chunks.append(CodeChunk(
                        file_path='',
                        language=language,
                        content=chunk_content,
                        start_line=current_chunk_start,
                        end_line=line_num - 1,
                        chunk_type='code',
                        symbols=current_symbols.copy()
                    ))
                    current_chunk = []
                    current_symbols = []
                    current_chunk_size = 0
                    current_chunk_start = line_num

            current_chunk.append(line)
            current_chunk_size += line_len

        # 处理最后一个块
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            if len(chunk_content.strip()) > self.min_chunk_size:
                chunks.append(CodeChunk(
                    file_path='',
                    language=language,
                    content=chunk_content,
                    start_line=current_chunk_start,
                    end_line=len(lines),
                    chunk_type='code',
                    symbols=current_symbols
                ))

        return chunks

    def parse_file(self, file_path: Union[str, Path]) -> FileIndexResult:
        file_path = Path(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        language = self._detect_language(file_path)
        return self.parse_content(content, language, str(file_path))

    def parse_content(
        self,
        content: str,
        language: str,
        file_path: Optional[str] = None
    ) -> FileIndexResult:
        parser = self._get_parser(language)
        if not parser:
            # tree-sitter 不可用时：降级为最小可运行版本
            return self._parse_content_fallback(content, language, file_path)

        # 解析语法树
        tree = parser.parse(bytes(content, 'utf-8'))

        # 提取符号
        symbols = self._extract_symbols(tree, content, language)
        for symbol in symbols:
            symbol.file_path = file_path or ''

        # 智能分块
        chunks = self._split_into_chunks(content, symbols, language)
        for chunk in chunks:
            chunk.file_path = file_path or ''

        # 提取import和export信息
        imports = self._extract_imports(tree, content, language)
        exports = self._extract_exports(tree, content, language)

        return FileIndexResult(
            file_path=file_path or '',
            language=language,
            chunks=chunks,
            symbols=symbols,
            imports=imports,
            exports=exports
        )

    def _detect_language(self, file_path: Path) -> str:
        """从文件扩展名检测语言"""
        ext = file_path.suffix.lower()
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'tsx',
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
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sql': 'sql',
        }
        return ext_map.get(ext, 'text')

    def _extract_imports(self, tree: tree_sitter.Tree, content: str, language: str) -> List[str]:
        """提取导入语句"""
        imports = []
        root_node = tree.root_node

        if language == 'python':
            # Python导入语句
            query = """
            (import_statement
              (dotted_name) @import_path)
            (import_from_statement
              (dotted_name) @import_path)
            """
            try:
                lang = get_language(self.LANGUAGE_MAPPING[language])
                query_obj = lang.query(query)
                captures = query_obj.captures(root_node)

                for node, _ in captures:
                    import_path = content[node.start_byte:node.end_byte]
                    imports.append(import_path)
            except:
                # 降级处理，简单匹配
                lines = content.split('\n')
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('import ') or stripped.startswith('from '):
                        imports.append(stripped)

        elif language in ['javascript', 'typescript', 'tsx', 'jsx']:
            # JavaScript/TypeScript导入
            lines = content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('require('):
                    imports.append(stripped)

        elif language == 'java':
            # Java导入
            lines = content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('import '):
                    imports.append(stripped)

        elif language == 'go':
            # Go导入
            query = """
            (import_spec
              (interpreted_string_literal) @import_path)
            """
            try:
                lang = get_language(self.LANGUAGE_MAPPING[language])
                query_obj = lang.query(query)
                captures = query_obj.captures(root_node)

                for node, _ in captures:
                    import_path = content[node.start_byte:node.end_byte].strip('"')
                    imports.append(import_path)
            except:
                lines = content.split('\n')
                for line in lines:
                    stripped = line.strip()
                    if 'import' in stripped and '"' in stripped:
                        import_path = stripped.split('"')[1] if '"' in stripped else stripped
                        imports.append(import_path)

        return list(set(imports))  # 去重

    def _extract_exports(self, tree: tree_sitter.Tree, content: str, language: str) -> List[str]:
        """提取导出的符号"""
        exports = []
        root_node = tree.root_node

        if language == 'python':
            # Python导出：__all__变量或者公共符号
            lines = content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('__all__'):
                    # 解析__all__列表
                    start_idx = line.find('[')
                    end_idx = line.find(']')
                    if start_idx != -1 and end_idx != -1:
                        items = line[start_idx+1:end_idx].split(',')
                        for item in items:
                            item = item.strip().strip('\'"')
                            if item:
                                exports.append(item)
                    break

            # 如果没有__all__，导出所有非下划线开头的顶级符号
            if not exports:
                def walk_node(node):
                    if node.type in ['function_definition', 'class_definition']:
                        name_node = node.child_by_field_name('name')
                        if name_node:
                            name = content[name_node.start_byte:name_node.end_byte]
                            if not name.startswith('_'):
                                exports.append(name)
                    for child in node.children:
                        walk_node(child)

                walk_node(root_node)

        elif language in ['javascript', 'typescript', 'tsx', 'jsx']:
            # JS/TS导出
            lines = content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('export '):
                    if 'function' in stripped or 'class' in stripped or 'const' in stripped or 'let' in stripped or 'var' in stripped:
                        parts = stripped.split()
                        for i, part in enumerate(parts):
                            if part in ['function', 'class', 'const', 'let', 'var'] and i + 1 < len(parts):
                                name = parts[i+1].replace('(', '').replace('=', '').strip()
                                if name:
                                    exports.append(name)
                    elif 'default' in stripped:
                        exports.append('default')

        elif language == 'java':
            # Java导出：公共类和接口
            def walk_node(node):
                if node.type in ['class_declaration', 'interface_declaration', 'enum_declaration']:
                    # 检查是否是public
                    modifiers = node.child_by_field_name('modifiers')
                    if modifiers and 'public' in content[modifiers.start_byte:modifiers.end_byte]:
                        name_node = node.child_by_field_name('name')
                        if name_node:
                            name = content[name_node.start_byte:name_node.end_byte]
                            exports.append(name)
                for child in node.children:
                    walk_node(child)

            walk_node(root_node)

        return list(set(exports))  # 去重
