"""
Git 变更增量索引器

功能:
1. 基于 Git diff 获取变更文件列表
2. 增量索引变更文件，避免全量重新索引
3. 支持多 commit 范围查询
4. 提供变更文件的影响范围分析
"""
from __future__ import annotations

import os
import subprocess
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class GitDiffInfo:
    """Git 变更文件信息"""
    def __init__(
        self,
        file_path: str,
        status: str,  # A=added, M=modified, D=deleted, R=renamed
        old_path: Optional[str] = None,  # 重命名时的旧路径
        additions: int = 0,
        deletions: int = 0,
        diff: Optional[str] = None
    ):
        self.file_path = file_path
        self.status = status
        self.old_path = old_path
        self.additions = additions
        self.deletions = deletions
        self.diff = diff
        self.change_type = self._infer_change_type()

    def _infer_change_type(self) -> str:
        """推断变更类型"""
        if self.status == 'A':
            return 'new_file'
        elif self.status == 'D':
            return 'deletion'
        elif self.status == 'M':
            if self.additions > 50 or self.deletions > 50:
                return 'major_change'
            return 'minor_change'
        elif self.status == 'R':
            return 'rename'
        return 'unknown'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "status": self.status,
            "old_path": self.old_path,
            "additions": self.additions,
            "deletions": self.deletions,
            "change_type": self.change_type
        }


class GitIntegration:
    """Git 集成工具类"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self._verify_git_repo()

    def _verify_git_repo(self) -> None:
        """验证是否是有效的 Git 仓库"""
        git_dir = self.repo_path / '.git'
        if not git_dir.exists():
            raise ValueError(f"{self.repo_path} 不是有效的 Git 仓库")

    def _run_git(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """运行 Git 命令"""
        try:
            result = subprocess.run(
                ['git'] + args,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=check,
                timeout=30
            )
            return result
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Git 命令超时：{' '.join(args)}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git 命令失败：{e.stderr}")

    def get_current_branch(self) -> str:
        """获取当前分支名"""
        result = self._run_git(['rev-parse', '--abbrev-ref', 'HEAD'])
        return result.stdout.strip()

    def get_current_commit(self) -> str:
        """获取当前 commit hash"""
        result = self._run_git(['rev-parse', 'HEAD'])
        return result.stdout.strip()

    def get_diff_files(
        self,
        base: str = "HEAD~1",
        target: str = "HEAD"
    ) -> List[GitDiffInfo]:
        """
        获取两个 commit 之间的变更文件

        Args:
            base: 基准 commit (如 HEAD~1, main, commit hash)
            target: 目标 commit (默认 HEAD)
        """
        try:
            # 获取变更文件列表（包含状态）
            result = self._run_git([
                'diff', '--name-status',
                base, target
            ])

            diff_info = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('\t')
                if len(parts) < 2:
                    continue

                status = parts[0]
                file_path = parts[1]
                old_path = None

                # 处理重命名
                if status.startswith('R') and len(parts) >= 3:
                    old_path = parts[1]
                    file_path = parts[2]

                diff_info.append(GitDiffInfo(
                    file_path=file_path,
                    status=status,
                    old_path=old_path
                ))

            return diff_info

        except Exception as e:
            logger.error(f"获取变更文件失败：{e}")
            return []

    def get_diff_stats(
        self,
        base: str = "HEAD~1",
        target: str = "HEAD"
    ) -> List[GitDiffInfo]:
        """获取变更文件的详细统计（包含增减行数）"""
        try:
            # 获取详细 diff
            result = self._run_git([
                'diff', '--numstat', '--name-status',
                base, target
            ])

            diff_info = []
            lines = result.stdout.strip().split('\n')

            i = 0
            while i < len(lines):
                line = lines[i]
                if not line:
                    i += 1
                    continue

                parts = line.split('\t')
                if len(parts) < 3:
                    i += 1
                    continue

                additions = int(parts[0]) if parts[0] != '-' else 0
                deletions = int(parts[1]) if parts[1] != '-' else 0
                file_path = parts[2]

                # 获取状态
                status = 'M'
                if i + 1 < len(lines):
                    status_line = lines[i + 1]
                    if '\t' not in status_line or status_line.startswith(('A', 'M', 'D', 'R')):
                        status = status_line.split('\t')[0]
                        if status in ['A', 'M', 'D', 'R']:
                            i += 1

                diff_info.append(GitDiffInfo(
                    file_path=file_path,
                    status=status,
                    additions=additions,
                    deletions=deletions
                ))

                i += 1

            return diff_info

        except Exception as e:
            logger.error(f"获取变更统计失败：{e}")
            return []

    def get_diff_content(
        self,
        base: str = "HEAD~1",
        target: str = "HEAD",
        file_path: Optional[str] = None
    ) -> Dict[str, str]:
        """
        获取变更内容

        Returns:
            {file_path: diff_content}
        """
        try:
            args = ['diff', base, target]
            if file_path:
                args.extend(['--', file_path])

            result = self._run_git(args)

            # 解析 diff 内容
            diffs = {}
            current_file = None
            current_diff = []

            for line in result.stdout.split('\n'):
                if line.startswith('diff --git'):
                    if current_file and current_diff:
                        diffs[current_file] = '\n'.join(current_diff)
                    # 提取文件名
                    parts = line.split(' ')
                    if len(parts) >= 3:
                        current_file = parts[2][2:]  # 去掉 b/ 前缀
                    current_diff = [line]
                elif current_file:
                    current_diff.append(line)

            if current_file and current_diff:
                diffs[current_file] = '\n'.join(current_diff)

            return diffs

        except Exception as e:
            logger.error(f"获取变更内容失败：{e}")
            return {}

    def get_recent_commits(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的 commit 列表"""
        try:
            result = self._run_git([
                'log', f'-{count}',
                '--format=%H|%an|%ae|%ai|%s'
            ])

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "date": parts[3],
                        "message": parts[4]
                    })

            return commits

        except Exception as e:
            logger.error(f"获取 commit 列表失败：{e}")
            return []

    def get_changed_symbols(
        self,
        base: str = "HEAD~1",
        target: str = "HEAD"
    ) -> Dict[str, List[str]]:
        """
        获取变更的符号（函数/类名）

        通过分析 diff 中的函数行来识别变更的符号
        """
        try:
            diff_info = self.get_diff_files(base, target)
            changed_symbols = {}

            for file_info in diff_info:
                if file_info.status == 'D':
                    continue

                file_path = self.repo_path / file_info.file_path
                if not file_path.exists():
                    continue

                # 获取文件的符号定义
                symbols = self._extract_symbols_from_diff(
                    file_info.file_path,
                    base,
                    target
                )
                if symbols:
                    changed_symbols[file_info.file_path] = symbols

            return changed_symbols

        except Exception as e:
            logger.error(f"获取变更符号失败：{e}")
            return {}

    def _extract_symbols_from_diff(
        self,
        file_path: str,
        base: str,
        target: str
    ) -> List[str]:
        """从 diff 中提取变更的符号"""
        symbols = []

        try:
            # 获取 diff 内容
            diffs = self.get_diff_content(base, target, file_path)
            if not diffs:
                return symbols

            diff_content = diffs.get(file_path, '')

            # 检测文件类型
            ext = Path(file_path).suffix.lower()

            # Python 函数/类定义
            if ext == '.py':
                import re
                for line in diff_content.split('\n'):
                    if line.startswith('+'):
                        # 类定义
                        match = re.match(r'\+class\s+(\w+)', line)
                        if match:
                            symbols.append(f"class:{match.group(1)}")
                        # 函数定义
                        match = re.match(r'\+(\s*)def\s+(\w+)', line)
                        if match:
                            symbols.append(f"def:{match.group(2)}")

            # JavaScript/TypeScript 函数/类
            elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                import re
                for line in diff_content.split('\n'):
                    if line.startswith('+'):
                        # 类定义
                        match = re.match(r'\+class\s+(\w+)', line)
                        if match:
                            symbols.append(f"class:{match.group(1)}")
                        # 函数定义
                        match = re.match(r'\+function\s+(\w+)', line)
                        if match:
                            symbols.append(f"function:{match.group(1)}")
                        # 箭头函数赋值
                        match = re.match(r'\+const\s+(\w+)\s*=\s*\(', line)
                        if match:
                            symbols.append(f"const:{match.group(1)}")

        except Exception as e:
            logger.debug(f"提取符号失败 {file_path}: {e}")

        return symbols

    def is_file_tracked(self, file_path: str) -> bool:
        """检查文件是否在 Git 跟踪中"""
        try:
            result = self._run_git(
                ['ls-files', '--error-unmatch', str(file_path)],
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_file_history(
        self,
        file_path: str,
        max_commits: int = 10
    ) -> List[Dict[str, Any]]:
        """获取文件的历史变更记录"""
        try:
            result = self._run_git([
                'log', f'-{max_commits}',
                '--format=%H|%an|%ai|%s',
                '--', str(file_path)
            ])

            history = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 4:
                    history.append({
                        "commit": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                        "file_path": file_path
                    })

            return history

        except Exception as e:
            logger.error(f"获取文件历史失败：{e}")
            return []


class DiffIndexer:
    """
    Git Diff 增量索引器

    基于 Git 变更进行增量索引，避免全量重新索引
    """

    def __init__(
        self,
        index_pipeline: Any,
        repo_path: str,
        project_name: str,
        config: Optional[Dict[str, Any]] = None
    ):
        self.index_pipeline = index_pipeline
        self.project_name = project_name
        self.config = config or {}

        try:
            self.git = GitIntegration(repo_path)
            self.repo_path = Path(repo_path).resolve()
        except ValueError as e:
            logger.warning(f"Git 集成不可用：{e}")
            self.git = None
            self.repo_path = Path(repo_path).resolve()

    def index_changed_files(
        self,
        base: str = "HEAD~1",
        target: str = "HEAD",
        delete_removed: bool = True
    ) -> Dict[str, Any]:
        """
        索引变更文件

        Args:
            base: 基准 commit
            target: 目标 commit
            delete_removed: 是否删除已移除文件的索引
        """
        stats = {
            "base": base,
            "target": target,
            "total_changed": 0,
            "indexed": 0,
            "deleted": 0,
            "skipped": 0,
            "failed": 0,
            "files": []
        }

        if not self.git:
            stats["error"] = "Git 仓库不可用"
            return stats

        try:
            diff_files = self.git.get_diff_stats(base, target)
            stats["total_changed"] = len(diff_files)

            for file_info in diff_files:
                file_path = self.repo_path / file_info.file_path

                if file_info.status == 'D':
                    # 删除文件
                    if delete_removed:
                        try:
                            self.index_pipeline.vector_store.delete_by_file(
                                self.project_name,
                                str(file_path)
                            )
                            stats["deleted"] += 1
                            stats["files"].append({
                                "file": str(file_path),
                                "action": "deleted"
                            })
                        except Exception as e:
                            logger.error(f"删除索引失败 {file_path}: {e}")
                            stats["failed"] += 1
                    continue

                if file_info.status == 'R' and file_info.old_path:
                    # 重命名文件：先删除旧的，再索引新的
                    old_path = self.repo_path / file_info.old_path
                    try:
                        self.index_pipeline.vector_store.delete_by_file(
                            self.project_name,
                            str(old_path)
                        )
                    except Exception:
                        pass

                # 索引新文件/修改的文件
                if file_path.exists():
                    try:
                        result = self.index_pipeline.index_file(
                            file_path=str(file_path),
                            collection_name=self.project_name,
                            incremental=True
                        )
                        if result:
                            stats["indexed"] += 1
                            stats["files"].append({
                                "file": str(file_path),
                                "action": "indexed",
                                "chunks": len(result.chunks),
                                "symbols": len(result.symbols)
                            })
                        else:
                            stats["skipped"] += 1
                    except Exception as e:
                        logger.error(f"索引失败 {file_path}: {e}")
                        stats["failed"] += 1
                else:
                    stats["skipped"] += 1

        except Exception as e:
            stats["error"] = f"索引变更失败：{str(e)}"
            logger.error(stats["error"])

        return stats

    def get_change_summary(
        self,
        base: str = "HEAD~1",
        target: str = "HEAD"
    ) -> Dict[str, Any]:
        """
        获取变更摘要

        返回变更的统计信息、影响的模块、变更的符号等
        """
        if not self.git:
            return {"error": "Git 仓库不可用"}

        try:
            diff_files = self.git.get_diff_stats(base, target)
            changed_symbols = self.git.get_changed_symbols(base, target)
            commits = self.git.get_recent_commits(5)

            # 按变更类型统计
            stats = {
                "new_files": 0,
                "deletions": 0,
                "major_changes": 0,
                "minor_changes": 0,
                "renames": 0
            }

            for file_info in diff_files:
                if file_info.change_type == 'new_file':
                    stats["new_files"] += 1
                elif file_info.change_type == 'deletion':
                    stats["deletions"] += 1
                elif file_info.change_type == 'major_change':
                    stats["major_changes"] += 1
                elif file_info.change_type == 'minor_change':
                    stats["minor_changes"] += 1
                elif file_info.change_type == 'rename':
                    stats["renames"] += 1

            # 按文件类型统计
            file_types = {}
            for file_info in diff_files:
                ext = Path(file_info.file_path).suffix
                if ext not in file_types:
                    file_types[ext] = 0
                file_types[ext] += 1

            return {
                "base": base,
                "target": target,
                "commits": commits[:3],
                "total_changed_files": len(diff_files),
                "change_type_stats": stats,
                "file_type_stats": file_types,
                "changed_symbols": changed_symbols,
                "changed_files": [f.to_dict() for f in diff_files]
            }

        except Exception as e:
            return {"error": f"获取变更摘要失败：{str(e)}"}


# 便捷函数
def create_diff_indexer(
    index_pipeline: Any,
    repo_path: str,
    project_name: str
) -> DiffIndexer:
    """创建 Diff 索引器实例"""
    return DiffIndexer(
        index_pipeline=index_pipeline,
        repo_path=repo_path,
        project_name=project_name
    )
