"""
LSP 符号引用解析器

功能:
1. 解析代码中的符号引用（函数、类、变量等）
2. 支持跳转到符号定义
3. 查找符号的所有引用位置
4. 提供符号层次结构信息
"""
from __future__ import annotations

import os
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SymbolKind(Enum):
    """符号类型"""
    FILE = "file"
    MODULE = "module"
    NAMESPACE = "namespace"
    PACKAGE = "package"
    CLASS = "class"
    METHOD = "method"
    PROPERTY = "property"
    FIELD = "field"
    CONSTRUCTOR = "constructor"
    ENUM = "enum"
    INTERFACE = "interface"
    FUNCTION = "function"
    VARIABLE = "variable"
    CONSTANT = "constant"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    KEY = "key"
    NULL = "null"
    ENUM_MEMBER = "enumMember"
    STRUCT = "struct"
    EVENT = "event"
    OPERATOR = "operator"
    TYPE_PARAMETER = "typeParameter"


@dataclass
class Location:
    """位置信息"""
    file_path: str
    line: int  # 1-based
    column: int  # 1-based
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column
        }
        if self.end_line:
            result["end_line"] = self.end_line
        if self.end_column:
            result["end_column"] = self.end_column
        return result

    def to_lsp_range(self) -> Dict[str, Any]:
        """转换为 LSP Range 格式"""
        return {
            "start": {
                "line": self.line - 1,  # LSP uses 0-based
                "character": self.column - 1
            },
            "end": {
                "line": (self.end_line or self.line) - 1,
                "character": (self.end_column or self.column) - 1
            }
        }


@dataclass
class Symbol:
    """符号信息"""
    name: str
    kind: SymbolKind
    location: Location
    container_name: Optional[str] = None  # 所属容器（如类名）
    detail: Optional[str] = None  # 详细信息
    documentation: Optional[str] = None  # 文档字符串
    children: List[Symbol] = field(default_factory=list)
    references: List[Location] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "location": self.location.to_dict(),
            "container_name": self.container_name,
            "detail": self.detail,
            "documentation": self.documentation,
            "children": [c.to_dict() for c in self.children],
            "references_count": len(self.references)
        }


class SymbolResolver:
    """
    符号解析器

    不依赖外部 LSP 服务器，基于正则和 AST 解析实现符号解析
    支持 Python、JavaScript、TypeScript、Java、Go 等语言
    """

    # 各语言的符号定义模式
    SYMBOL_PATTERNS = {
        "python": {
            "class": re.compile(r'^class\s+(\w+)(?:\([^)]*\))?\s*:', re.MULTILINE),
            "function": re.compile(r'^(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE),
            "method": re.compile(r'^\s+(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE),
            "variable": re.compile(r'^(\w+)\s*=\s*', re.MULTILINE),
            "import": re.compile(r'^(?:from\s+([\w.]+)\s+)?import\s+(.+)', re.MULTILINE),
        },
        "javascript": {
            "class": re.compile(r'(?:export\s+)?class\s+(\w+)', re.MULTILINE),
            "function": re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.MULTILINE),
            "arrow": re.compile(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(', re.MULTILINE),
            "method": re.compile(r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*{', re.MULTILINE),
            "variable": re.compile(r'(?:const|let|var)\s+(\w+)\s*=', re.MULTILINE),
        },
        "typescript": {
            "class": re.compile(r'(?:export\s+)?class\s+(\w+)', re.MULTILINE),
            "interface": re.compile(r'(?:export\s+)?interface\s+(\w+)', re.MULTILINE),
            "function": re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.MULTILINE),
            "type": re.compile(r'(?:export\s+)?type\s+(\w+)\s*=', re.MULTILINE),
            "variable": re.compile(r'(?:const|let|var)\s+(\w+)\s*:', re.MULTILINE),
        },
        "java": {
            "class": re.compile(r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)', re.MULTILINE),
            "interface": re.compile(r'(?:public\s+)?interface\s+(\w+)', re.MULTILINE),
            "method": re.compile(r'(?:public|private|protected)?\s+\w+\s+(\w+)\s*\(', re.MULTILINE),
            "field": re.compile(r'(?:public|private|protected)?\s+\w+\s+(\w+)\s*;', re.MULTILINE),
        },
        "go": {
            "func": re.compile(r'^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(', re.MULTILINE),
            "type": re.compile(r'^type\s+(\w+)\s+', re.MULTILINE),
            "struct": re.compile(r'^type\s+(\w+)\s+struct', re.MULTILINE),
            "interface": re.compile(r'^type\s+(\w+)\s+interface', re.MULTILINE),
        },
    }

    # 符号引用模式（用于查找引用）
    REFERENCE_PATTERNS = {
        "python": {
            "call": re.compile(r'\b(\w+)\s*\('),
            "attribute": re.compile(r'\.(\w+)'),
            "import_use": re.compile(r'(?:from\s+[\w.]+\s+)?import\s+.*?\b(\w+)\b'),
        },
        "javascript": {
            "call": re.compile(r'\b(\w+)\s*\('),
            "property": re.compile(r'\.(\w+)'),
            "import_use": re.compile(r'import\s+.*?\b(\w+)\b'),
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.max_file_size = self.config.get('max_file_size', 1024 * 1024)  # 1MB
        self._symbol_cache: Dict[str, List[Symbol]] = {}

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

    def resolve_symbols(
        self,
        file_path: str,
        content: Optional[str] = None
    ) -> List[Symbol]:
        """
        解析文件中的所有符号

        Args:
            file_path: 文件路径
            content: 文件内容（可选，不提供则读取文件）
        """
        # 检查缓存
        if file_path in self._symbol_cache:
            return self._symbol_cache[file_path]

        language = self._detect_language(file_path)
        if not language:
            return []

        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(self.max_file_size)
            except Exception as e:
                logger.error(f"读取文件失败 {file_path}: {e}")
                return []

        patterns = self.SYMBOL_PATTERNS.get(language, {})
        symbols = []

        # 解析各类符号
        for symbol_type, pattern in patterns.items():
            if symbol_type == 'import':
                continue  # 导入语句单独处理

            for match in pattern.finditer(content):
                symbol_name = match.group(1)
                start_pos = match.start()

                # 计算行号和列号
                line_start = content.rfind('\n', 0, start_pos) + 1
                line_num = content.count('\n', 0, start_pos) + 1
                col_num = start_pos - line_start + 1

                # 计算结束位置
                end_match = content.find('\n', start_pos)
                if end_match == -1:
                    end_pos = len(content)
                else:
                    end_pos = end_match
                end_line = line_num + 1 if '\n' in content[start_pos:end_pos] else line_num
                end_col = end_pos - line_start + 1

                symbol = Symbol(
                    name=symbol_name,
                    kind=self._get_symbol_kind(symbol_type, language),
                    location=Location(
                        file_path=file_path,
                        line=line_num,
                        column=col_num,
                        end_line=end_line,
                        end_column=end_col
                    ),
                    container_name=self._get_container_name(content, start_pos, language)
                )
                symbols.append(symbol)

        # 缓存结果
        self._symbol_cache[file_path] = symbols
        return symbols

    def _get_symbol_kind(self, symbol_type: str, language: str) -> SymbolKind:
        """将符号类型映射到 SymbolKind"""
        kind_map = {
            "python": {
                "class": SymbolKind.CLASS,
                "function": SymbolKind.FUNCTION,
                "method": SymbolKind.METHOD,
                "variable": SymbolKind.VARIABLE,
            },
            "javascript": {
                "class": SymbolKind.CLASS,
                "function": SymbolKind.FUNCTION,
                "arrow": SymbolKind.FUNCTION,
                "method": SymbolKind.METHOD,
                "variable": SymbolKind.VARIABLE,
            },
            "typescript": {
                "class": SymbolKind.CLASS,
                "interface": SymbolKind.INTERFACE,
                "function": SymbolKind.FUNCTION,
                "type": SymbolKind.TYPE_PARAMETER,
                "variable": SymbolKind.VARIABLE,
            },
            "java": {
                "class": SymbolKind.CLASS,
                "interface": SymbolKind.INTERFACE,
                "method": SymbolKind.METHOD,
                "field": SymbolKind.FIELD,
            },
            "go": {
                "func": SymbolKind.FUNCTION,
                "type": SymbolKind.TYPE_PARAMETER,
                "struct": SymbolKind.STRUCT,
                "interface": SymbolKind.INTERFACE,
            },
        }
        return kind_map.get(language, {}).get(symbol_type, SymbolKind.VARIABLE)

    def _get_container_name(
        self,
        content: str,
        pos: int,
        language: str
    ) -> Optional[str]:
        """获取符号的容器名称（如类名）"""
        if language != "python":
            return None

        # Python 中查找类定义
        lines_before = content[:pos].split('\n')
        indent_stack = []

        for i, line in enumerate(reversed(lines_before[:-1]), 1):
            stripped = line.lstrip()
            if stripped.startswith('class '):
                match = re.search(r'class\s+(\w+)', stripped)
                if match:
                    return match.group(1)
            elif stripped.startswith('def '):
                # 继续向上查找类
                continue

        return None

    def find_symbol_definition(
        self,
        symbol_name: str,
        scope_paths: Optional[List[str]] = None
    ) -> List[Symbol]:
        """
        查找符号的定义位置

        Args:
            symbol_name: 符号名称
            scope_paths: 搜索范围（文件路径列表）
        """
        definitions = []

        # 如果指定了范围，在范围内搜索
        if scope_paths:
            for path in scope_paths:
                if os.path.isfile(path):
                    symbols = self.resolve_symbols(path)
                    for sym in symbols:
                        if sym.name == symbol_name:
                            definitions.append(sym)
                elif os.path.isdir(path):
                    # 递归搜索目录
                    definitions.extend(self._find_in_directory(symbol_name, path))
        else:
            # 在缓存中查找
            for file_path, symbols in self._symbol_cache.items():
                for sym in symbols:
                    if sym.name == symbol_name:
                        definitions.append(sym)

        return definitions

    def _find_in_directory(self, symbol_name: str, dir_path: str) -> List[Symbol]:
        """在目录中搜索符号定义"""
        results = []
        for root, _, files in os.walk(dir_path):
            # 跳过常见排除目录
            if any(excluded in root for excluded in ['__pycache__', 'node_modules', '.git', 'dist', 'build']):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                language = self._detect_language(file_path)
                if not language:
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(self.max_file_size)

                    patterns = self.SYMBOL_PATTERNS.get(language, {})
                    for symbol_type, pattern in patterns.items():
                        if symbol_type == 'import':
                            continue
                        for match in pattern.finditer(content):
                            if match.group(1) == symbol_name:
                                symbols = self.resolve_symbols(file_path, content)
                                for sym in symbols:
                                    if sym.name == symbol_name:
                                        results.append(sym)
                                        break
                except Exception:
                    continue

        return results

    def find_references(
        self,
        symbol: Symbol,
        scope_paths: Optional[List[str]] = None
    ) -> List[Location]:
        """
        查找符号的所有引用位置

        Args:
            symbol: 符号对象
            scope_paths: 搜索范围
        """
        references = []
        language = self._detect_language(symbol.location.file_path)

        patterns = self.REFERENCE_PATTERNS.get(language, {})
        call_pattern = patterns.get('call', re.compile(rf'\b{re.escape(symbol.name)}\s*\('))

        # 确定搜索范围
        search_paths = scope_paths or [str(Path(symbol.location.file_path).parent)]

        for path in search_paths:
            if os.path.isfile(path):
                refs = self._find_references_in_file(symbol.name, call_pattern, path)
                references.extend(refs)
            elif os.path.isdir(path):
                refs = self._find_references_in_directory(symbol.name, call_pattern, path)
                references.extend(refs)

        # 移除定义位置本身
        references = [
            ref for ref in references
            if not (ref.file_path == symbol.location.file_path and
                   ref.line == symbol.location.line)
        ]

        return references

    def _find_references_in_file(
        self,
        symbol_name: str,
        pattern: re.Pattern,
        file_path: str
    ) -> List[Location]:
        """在文件中查找符号引用"""
        references = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(self.max_file_size)

            for match in pattern.finditer(content):
                if match.group(1) == symbol_name:
                    start_pos = match.start()
                    line_num = content.count('\n', 0, start_pos) + 1
                    line_start = content.rfind('\n', 0, start_pos) + 1
                    col_num = start_pos - line_start + 1

                    references.append(Location(
                        file_path=file_path,
                        line=line_num,
                        column=col_num
                    ))

        except Exception:
            pass

        return references

    def _find_references_in_directory(
        self,
        symbol_name: str,
        pattern: re.Pattern,
        dir_path: str
    ) -> List[Location]:
        """在目录中查找符号引用"""
        references = []

        for root, _, files in os.walk(dir_path):
            if any(excluded in root for excluded in ['__pycache__', 'node_modules', '.git', 'dist', 'build']):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                refs = self._find_references_in_file(symbol_name, pattern, file_path)
                references.extend(refs)

        return references

    def get_document_symbols(self, file_path: str) -> Dict[str, Any]:
        """
        获取文档符号层次结构

        返回带有父子关系的符号树
        """
        symbols = self.resolve_symbols(file_path)

        # 构建层次结构
        top_level = []
        container_map: Dict[str, Symbol] = {}

        for symbol in symbols:
            if symbol.container_name:
                # 子符号，添加到容器
                if symbol.container_name in container_map:
                    container_map[symbol.container_name].children.append(symbol)
            else:
                # 顶层符号
                top_level.append(symbol)
                if symbol.kind in [SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.STRUCT]:
                    container_map[symbol.name] = symbol

        return {
            "file_path": file_path,
            "symbols": [s.to_dict() for s in top_level],
            "total_symbols": len(symbols)
        }

    def clear_cache(self, file_path: Optional[str] = None) -> None:
        """清除符号缓存"""
        if file_path:
            self._symbol_cache.pop(file_path, None)
        else:
            self._symbol_cache.clear()


# 便捷函数
def create_symbol_resolver(config: Optional[Dict[str, Any]] = None) -> SymbolResolver:
    """创建符号解析器实例"""
    return SymbolResolver(config=config)


def resolve_file_symbols(file_path: str) -> List[Dict[str, Any]]:
    """解析文件符号并返回字典列表"""
    resolver = SymbolResolver()
    symbols = resolver.resolve_symbols(file_path)
    return [s.to_dict() for s in symbols]
