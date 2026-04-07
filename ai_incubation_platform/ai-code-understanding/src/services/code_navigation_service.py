"""
代码导航增强服务
提供 LSP 风格的代码导航功能：跳转定义、查找引用、符号重命名

功能:
1. 跳转到定义 (Go to Definition)
2. 查找所有引用 (Find All References)
3. 符号重命名 (Rename Symbol)
4. 代码层次结构 (Document Symbols)
5. 实现/类型定义 (Go to Implementation/Type Definition)
"""
import os
import re
import ast
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NavigationLocation:
    """导航位置"""
    file_path: str
    line: int  # 1-based
    column: int  # 1-based
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    content_preview: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "content_preview": self.content_preview
        }


@dataclass
class RenameResult:
    """重命名结果"""
    success: bool
    changed_files: List[str] = field(default_factory=list)
    total_changes: int = 0
    error: Optional[str] = None


class CodeNavigationService:
    """
    代码导航服务

    提供 LSP 风格的代码导航功能
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.max_file_size = self.config.get('max_file_size', 1024 * 1024)  # 1MB
        self._index_cache: Dict[str, Dict[str, List[NavigationLocation]]] = {}
        logger.info("CodeNavigationService initialized")

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
            '.rs': 'rust',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext)

    def _read_file(self, file_path: str) -> Optional[str]:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(self.max_file_size)
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return None

    def go_to_definition(
        self,
        file_path: str,
        line: int,
        column: int,
        project_root: Optional[str] = None
    ) -> Optional[NavigationLocation]:
        """
        跳转到定义位置

        Args:
            file_path: 当前文件路径
            line: 光标所在行 (1-based)
            column: 光标所在列 (1-based)
            project_root: 项目根目录

        Returns:
            定义位置，如果找不到则返回 None
        """
        language = self._detect_language(file_path)
        if not language:
            return None

        content = self._read_file(file_path)
        if not content:
            return None

        # 获取光标下的符号名称
        symbol_name = self._get_symbol_at_position(content, line, column, language)
        if not symbol_name:
            return None

        # 查找定义
        definition = self._find_definition(symbol_name, file_path, project_root, language)
        if definition:
            # 添加内容预览
            definition.content_preview = self._get_line_preview(content, definition.line)

        return definition

    def _get_symbol_at_position(
        self,
        content: str,
        line: int,
        column: int,
        language: str
    ) -> Optional[str]:
        """获取指定位置的符号名称"""
        lines = content.split('\n')
        if line < 1 or line > len(lines):
            return None

        target_line = lines[line - 1]
        if column < 1 or column > len(target_line) + 1:
            return None

        # 提取符号名称（字母数字和下划线）
        char = target_line[column - 1] if column <= len(target_line) else ''
        if not (char.isalnum() or char == '_'):
            return None

        # 向左右扩展获取完整符号名
        left = column - 1
        right = column

        while left > 0 and (target_line[left - 1].isalnum() or target_line[left - 1] == '_'):
            left -= 1
        while right < len(target_line) and (target_line[right].isalnum() or target_line[right] == '_'):
            right += 1

        return target_line[left:right]

    def _find_definition(
        self,
        symbol_name: str,
        current_file: str,
        project_root: Optional[str],
        language: str
    ) -> Optional[NavigationLocation]:
        """查找符号定义"""
        # 1. 首先在当前文件中查找
        definition = self._find_definition_in_file(symbol_name, current_file, language)
        if definition:
            return definition

        # 2. 在项目范围内查找
        if project_root:
            definition = self._find_definition_in_project(
                symbol_name, project_root, language
            )
            if definition:
                return definition

        return None

    def _find_definition_in_file(
        self,
        symbol_name: str,
        file_path: str,
        language: str
    ) -> Optional[NavigationLocation]:
        """在文件中查找符号定义"""
        content = self._read_file(file_path)
        if not content:
            return None

        patterns = self._get_definition_patterns(language)

        for pattern_name, pattern in patterns.items():
            for match in pattern.finditer(content):
                if match.group(1) == symbol_name:
                    line_num = content.count('\n', 0, match.start()) + 1
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    col_num = match.start() - line_start + 1

                    # 计算结束位置
                    end_pos = content.find('\n', match.start())
                    if end_pos == -1:
                        end_pos = len(content)
                    end_line = line_num + 1 if '\n' in content[match.start():end_pos] else line_num
                    end_col = end_pos - content.rfind('\n', 0, match.start())

                    return NavigationLocation(
                        file_path=file_path,
                        line=line_num,
                        column=col_num,
                        end_line=end_line,
                        end_column=end_col
                    )

        return None

    def _find_definition_in_project(
        self,
        symbol_name: str,
        project_root: str,
        language: str
    ) -> Optional[NavigationLocation]:
        """在项目中查找符号定义"""
        patterns = self._get_definition_patterns(language)

        for root, dirs, files in os.walk(project_root):
            # 跳过排除目录
            if any(excluded in root for excluded in [
                '__pycache__', 'node_modules', '.git', 'dist',
                'build', '.pytest_cache', 'venv', 'env'
            ]):
                continue

            for file in files:
                file_ext = Path(file).suffix.lower()
                file_language = self._detect_language(os.path.join(root, file))
                if file_language != language:
                    continue

                file_path = os.path.join(root, file)
                content = self._read_file(file_path)
                if not content:
                    continue

                for pattern_name, pattern in patterns.items():
                    for match in pattern.finditer(content):
                        if match.group(1) == symbol_name:
                            line_num = content.count('\n', 0, match.start()) + 1
                            line_start = content.rfind('\n', 0, match.start()) + 1
                            col_num = match.start() - line_start + 1

                            return NavigationLocation(
                                file_path=file_path,
                                line=line_num,
                                column=col_num
                            )

        return None

    def _get_definition_patterns(self, language: str) -> Dict[str, re.Pattern]:
        """获取定义模式的正则表达式"""
        patterns = {
            "python": {
                "class": re.compile(r'^class\s+(\w+)(?:\([^)]*\))?\s*:', re.MULTILINE),
                "function": re.compile(r'^(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE),
                "method": re.compile(r'^\s+(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE),
                "variable": re.compile(r'^(\w+)\s*=\s*(?![^\n]*\})', re.MULTILINE),
            },
            "javascript": {
                "class": re.compile(r'(?:export\s+)?class\s+(\w+)', re.MULTILINE),
                "function": re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.MULTILINE),
                "arrow": re.compile(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(', re.MULTILINE),
                "method": re.compile(r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE),
            },
            "typescript": {
                "class": re.compile(r'(?:export\s+)?class\s+(\w+)', re.MULTILINE),
                "interface": re.compile(r'(?:export\s+)?interface\s+(\w+)', re.MULTILINE),
                "function": re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.MULTILINE),
                "type": re.compile(r'(?:export\s+)?type\s+(\w+)\s*=', re.MULTILINE),
            },
            "java": {
                "class": re.compile(r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)', re.MULTILINE),
                "interface": re.compile(r'(?:public\s+)?interface\s+(\w+)', re.MULTILINE),
                "method": re.compile(r'(?:public|private|protected)[^\w]+\w+\s+(\w+)\s*\(', re.MULTILINE),
            },
            "go": {
                "func": re.compile(r'^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(', re.MULTILINE),
                "type": re.compile(r'^type\s+(\w+)\s+', re.MULTILINE),
            },
        }
        return patterns.get(language, {})

    def find_all_references(
        self,
        file_path: str,
        line: int,
        column: int,
        project_root: Optional[str] = None
    ) -> List[NavigationLocation]:
        """
        查找所有引用位置

        Args:
            file_path: 当前文件路径
            line: 光标所在行 (1-based)
            column: 光标所在列 (1-based)
            project_root: 项目根目录

        Returns:
            引用位置列表
        """
        language = self._detect_language(file_path)
        if not language:
            return []

        content = self._read_file(file_path)
        if not content:
            return []

        # 获取符号名称
        symbol_name = self._get_symbol_at_position(content, line, column, language)
        if not symbol_name:
            return []

        references = []

        # 确定搜索范围
        if project_root and os.path.isdir(project_root):
            search_paths = [project_root]
        else:
            search_paths = [os.path.dirname(file_path)]

        # 在范围内查找所有引用
        for search_path in search_paths:
            refs = self._find_references_in_path(
                symbol_name, search_path, language
            )
            references.extend(refs)

        # 为每个引用添加内容预览
        for ref in references:
            if os.path.exists(ref.file_path):
                ref_content = self._read_file(ref.file_path)
                if ref_content:
                    ref.content_preview = self._get_line_preview(ref_content, ref.line)

        return references

    def _find_references_in_path(
        self,
        symbol_name: str,
        path: str,
        language: str
    ) -> List[NavigationLocation]:
        """在路径中查找符号引用"""
        references = []

        if os.path.isfile(path):
            refs = self._find_references_in_file(symbol_name, path, language)
            references.extend(refs)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                if any(excluded in root for excluded in [
                    '__pycache__', 'node_modules', '.git', 'dist', 'build'
                ]):
                    continue

                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = Path(file).suffix.lower()
                    file_language = self._detect_language(file_path)
                    if file_language == language:
                        refs = self._find_references_in_file(
                            symbol_name, file_path, language
                        )
                        references.extend(refs)

        return references

    def _find_references_in_file(
        self,
        symbol_name: str,
        file_path: str,
        language: str
    ) -> List[NavigationLocation]:
        """在文件中查找符号引用"""
        references = []
        content = self._read_file(file_path)
        if not content:
            return references

        # 引用模式（排除定义位置）
        ref_pattern = re.compile(rf'\b{re.escape(symbol_name)}\b')

        # 获取定义位置（用于排除）
        definition = self._find_definition_in_file(symbol_name, file_path, language)
        definition_lines = set()
        if definition:
            definition_lines.add(definition.line)

        for match in ref_pattern.finditer(content):
            line_num = content.count('\n', 0, match.start()) + 1
            line_start = content.rfind('\n', 0, match.start()) + 1
            col_num = match.start() - line_start + 1

            # 排除定义位置
            if line_num in definition_lines:
                continue

            references.append(NavigationLocation(
                file_path=file_path,
                line=line_num,
                column=col_num
            ))

        return references

    def _get_line_preview(self, content: str, line: int) -> Optional[str]:
        """获取指定行的内容预览"""
        lines = content.split('\n')
        if line < 1 or line > len(lines):
            return None
        return lines[line - 1].strip()

    def rename_symbol(
        self,
        file_path: str,
        line: int,
        column: int,
        new_name: str,
        project_root: Optional[str] = None,
        dry_run: bool = True
    ) -> RenameResult:
        """
        重命名符号

        Args:
            file_path: 当前文件路径
            line: 光标所在行 (1-based)
            column: 光标所在列 (1-based)
            new_name: 新名称
            project_root: 项目根目录
            dry_run: 是否只是模拟运行（不实际修改）

        Returns:
            重命名结果
        """
        language = self._detect_language(file_path)
        if not language:
            return RenameResult(
                success=False,
                error=f"不支持的文件类型：{file_path}"
            )

        content = self._read_file(file_path)
        if not content:
            return RenameResult(
                success=False,
                error=f"无法读取文件：{file_path}"
            )

        # 获取符号名称
        symbol_name = self._get_symbol_at_position(content, line, column, language)
        if not symbol_name:
            return RenameResult(
                success=False,
                error="未在指定位置找到符号"
            )

        # 验证新名称合法性
        if not re.match(r'^[a-zA-Z_]\w*$', new_name):
            return RenameResult(
                success=False,
                error=f"无效的符号名称：{new_name}"
            )

        # 查找所有引用
        references = self.find_all_references(file_path, line, column, project_root)

        changed_files: Set[str] = set()
        total_changes = 0

        # 按文件分组引用
        refs_by_file: Dict[str, List[NavigationLocation]] = {}
        for ref in references:
            if ref.file_path not in refs_by_file:
                refs_by_file[ref.file_path] = []
            refs_by_file[ref.file_path].append(ref)

        # 处理每个文件
        for ref_file, file_refs in refs_by_file.items():
            file_content = self._read_file(ref_file)
            if not file_content:
                continue

            # 按行号降序排序，从后往前替换以保持行号正确
            file_refs.sort(key=lambda x: x.line, reverse=True)

            lines = file_content.split('\n')
            changes_made = 0

            for ref in file_refs:
                if ref.line <= len(lines):
                    old_line = lines[ref.line - 1]
                    # 替换符号名称
                    new_line = re.sub(
                        rf'\b{re.escape(symbol_name)}\b',
                        new_name,
                        old_line,
                        count=1
                    )
                    if new_line != old_line:
                        lines[ref.line - 1] = new_line
                        changes_made += 1
                        changed_files.add(ref_file)

            total_changes += changes_made

            # 如果不是 dry run，写入文件
            if not dry_run and changes_made > 0:
                try:
                    with open(ref_file, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                    logger.info(f"已更新文件 {ref_file}: {changes_made} 处修改")
                except Exception as e:
                    logger.error(f"写入文件失败 {ref_file}: {e}")

        return RenameResult(
            success=True,
            changed_files=list(changed_files),
            total_changes=total_changes
        )

    def get_document_symbols(self, file_path: str) -> Dict[str, Any]:
        """
        获取文档中的所有符号

        Args:
            file_path: 文件路径

        Returns:
            符号列表和统计信息
        """
        language = self._detect_language(file_path)
        if not language:
            return {"symbols": [], "error": "不支持的文件类型"}

        content = self._read_file(file_path)
        if not content:
            return {"symbols": [], "error": "无法读取文件"}

        patterns = self._get_definition_patterns(language)
        symbols = []

        for symbol_type, pattern in patterns.items():
            for match in pattern.finditer(content):
                symbol_name = match.group(1)
                line_num = content.count('\n', 0, match.start()) + 1
                line_start = content.rfind('\n', 0, match.start()) + 1
                col_num = match.start() - line_start + 1

                symbols.append({
                    "name": symbol_name,
                    "kind": symbol_type,
                    "line": line_num,
                    "column": col_num,
                    "language": language
                })

        # 按行号排序
        symbols.sort(key=lambda x: x["line"])

        return {
            "file_path": file_path,
            "symbols": symbols,
            "total_symbols": len(symbols),
            "language": language
        }

    def get_file_overview(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件概览信息

        Args:
            file_path: 文件路径

        Returns:
            文件概览信息
        """
        language = self._detect_language(file_path)
        if not language:
            return {"error": "不支持的文件类型"}

        content = self._read_file(file_path)
        if not content:
            return {"error": "无法读取文件"}

        lines = content.split('\n')
        symbols = self.get_document_symbols(file_path)

        # 统计信息
        stats = {
            "total_lines": len(lines),
            "code_lines": sum(1 for line in lines if line.strip() and not line.strip().startswith('#')),
            "blank_lines": sum(1 for line in lines if not line.strip()),
            "comment_lines": sum(1 for line in lines if line.strip().startswith('#')),
        }

        # 符号统计
        symbol_stats = {}
        for sym in symbols.get("symbols", []):
            kind = sym["kind"]
            symbol_stats[kind] = symbol_stats.get(kind, 0) + 1

        return {
            "file_path": file_path,
            "language": language,
            "stats": stats,
            "symbols_summary": symbol_stats,
            "total_symbols": symbols.get("total_symbols", 0)
        }


# 便捷函数
def create_code_navigation_service(
    config: Optional[Dict[str, Any]] = None
) -> CodeNavigationService:
    """创建代码导航服务实例"""
    return CodeNavigationService(config=config)
