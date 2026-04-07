"""
Git 变更自动同步器

功能:
1. Git Hook 监听文件变更
2. 文件系统监听 (不依赖 Git commit)
3. 增量更新知识图谱索引
4. 自动同步触发机制
"""
from __future__ import annotations

import os
import json
import logging
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

try:
    import watchfiles
    WATCHFILES_AVAILABLE = True
except ImportError:
    WATCHFILES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("watchfiles 不可用，文件系统监听功能将被禁用。请运行: pip install watchfiles")

from .diff_indexer import GitIntegration, DiffIndexer

logger = logging.getLogger(__name__)


class SyncMode(str, Enum):
    """同步模式"""
    GIT_HOOK = "git_hook"           # Git Hook 触发
    FILE_WATCH = "file_watch"       # 文件系统监听
    HYBRID = "hybrid"               # 混合模式 (默认)


class ChangeType(str, Enum):
    """变更类型"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class FileChange:
    """文件变更信息"""
    file_path: str
    change_type: ChangeType
    timestamp: float = field(default_factory=time.time)
    old_path: Optional[str] = None
    git_status: Optional[str] = None  # A/M/D/R
    requires_reindex: bool = True     # 是否需要重新索引
    requires_graph_update: bool = True  # 是否需要更新知识图谱

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "change_type": self.change_type.value,
            "timestamp": self.timestamp,
            "old_path": self.old_path,
            "git_status": self.git_status
        }


@dataclass
class SyncEvent:
    """同步事件"""
    event_id: str
    trigger_type: str  # git_hook, file_watch, manual
    changes: List[FileChange]
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trigger_type": self.trigger_type,
            "changes": [c.to_dict() for c in self.changes],
            "timestamp": self.timestamp,
            "status": self.status,
            "error": self.error,
            "stats": self.stats
        }


class GitHookManager:
    """Git Hook 管理器"""

    HOOK_SCRIPTS = {
        "post-commit": """#!/bin/bash
# AI Code Understanding - Post Commit Hook
# 自动触发索引同步

REPO_ROOT="$(git rev-parse --show-toplevel)"
SYNC_SCRIPT="$REPO_ROOT/.ai-code-sync/trigger_sync.py"

if [ -f "$SYNC_SCRIPT" ]; then
    python "$SYNC_SCRIPT" --trigger git_hook --commit "$1"
fi
""",
        "post-merge": """#!/bin/bash
# AI Code Understanding - Post Merge Hook
# 自动触发索引同步

REPO_ROOT="$(git rev-parse --show-toplevel)"
SYNC_SCRIPT="$REPO_ROOT/.ai-code-sync/trigger_sync.py"

if [ -f "$SYNC_SCRIPT" ]; then
    python "$SYNC_SCRIPT" --trigger git_hook --event merge
fi
""",
        "post-checkout": """#!/bin/bash
# AI Code Understanding - Post Checkout Hook
# 自动触发索引同步 (分支切换时)

REPO_ROOT="$(git rev-parse --show-toplevel)"
SYNC_SCRIPT="$REPO_ROOT/.ai-code-sync/trigger_sync.py"

if [ -f "$SYNC_SCRIPT" ]; then
    python "$SYNC_SCRIPT" --trigger git_hook --event checkout
fi
"""
    }

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.git_dir = self.repo_path / '.git'
        self.hooks_dir = self.git_dir / 'hooks'
        self.sync_dir = self.repo_path / '.ai-code-sync'

    def install_hooks(self) -> Dict[str, Any]:
        """安装 Git Hooks"""
        result = {
            "success": True,
            "installed": [],
            "failed": [],
            "message": ""
        }

        try:
            # 创建同步目录
            self.sync_dir.mkdir(exist_ok=True)

            # 创建触发脚本
            trigger_script = self.sync_dir / "trigger_sync.py"
            trigger_script.write_text(self._get_trigger_script())
            trigger_script.chmod(0o755)
            result["installed"].append(str(trigger_script))

            # 确保 hooks 目录存在
            if not self.hooks_dir.exists():
                self.hooks_dir.mkdir(exist_ok=True)

            # 安装各个 hook
            for hook_name, script_content in self.HOOK_SCRIPTS.items():
                hook_path = self.hooks_dir / hook_name
                try:
                    hook_path.write_text(script_content)
                    hook_path.chmod(0o755)
                    result["installed"].append(hook_name)
                except Exception as e:
                    result["failed"].append(hook_name)
                    result["success"] = False
                    logger.error(f"安装 hook 失败 {hook_name}: {e}")

            result["message"] = f"成功安装 {len(result['installed'])} 个 hooks"
            logger.info(result["message"])

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["message"] = f"安装失败：{e}"
            logger.error(result["message"])

        return result

    def uninstall_hooks(self) -> Dict[str, Any]:
        """卸载 Git Hooks"""
        result = {
            "success": True,
            "removed": [],
            "failed": [],
            "message": ""
        }

        try:
            # 删除 hooks
            for hook_name in self.HOOK_SCRIPTS.keys():
                hook_path = self.hooks_dir / hook_name
                if hook_path.exists():
                    try:
                        hook_path.unlink()
                        result["removed"].append(hook_name)
                    except Exception as e:
                        result["failed"].append(hook_name)
                        logger.error(f"删除 hook 失败 {hook_name}: {e}")

            # 删除同步目录
            if self.sync_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(self.sync_dir)
                    result["removed"].append(str(self.sync_dir))
                except Exception as e:
                    logger.error(f"删除同步目录失败：{e}")

            result["message"] = f"成功移除 {len(result['removed'])} 个 hooks"
            logger.info(result["message"])

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["message"] = f"卸载失败：{e}"
            logger.error(result["message"])

        return result

    def check_hooks_installed(self) -> Dict[str, bool]:
        """检查 hooks 是否已安装"""
        status = {}
        for hook_name in self.HOOK_SCRIPTS.keys():
            hook_path = self.hooks_dir / hook_name
            status[hook_name] = hook_path.exists()
        return status

    def _get_trigger_script(self) -> str:
        """获取触发脚本内容"""
        return '''#!/usr/bin/env python3
"""Git Hook 触发同步脚本"""
import sys
import os

# 添加项目路径
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, 'src'))

from core.git_integration.git_sync import GitChangeSynchronizer

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--trigger', default='git_hook')
    parser.add_argument('--commit', default=None)
    parser.add_argument('--event', default=None)
    args = parser.parse_args()

    syncer = GitChangeSynchronizer(repo_root)
    syncer.trigger_sync(trigger_type=args.trigger, commit_hash=args.commit)

if __name__ == '__main__':
    main()
'''


class GitChangeSynchronizer:
    """
    Git 变更同步器

    核心功能:
    1. 监听 Git 变更 (通过 hook 或轮询)
    2. 监听文件系统变更
    3. 增量更新索引
    4. 增量更新知识图谱
    """

    def __init__(
        self,
        repo_path: str,
        project_name: Optional[str] = None,
        index_pipeline: Optional[Any] = None,
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.repo_path = Path(repo_path).resolve()
        self.project_name = project_name or self.repo_path.name
        self.config = config or {}

        # 核心组件
        self.index_pipeline = index_pipeline
        self.knowledge_graph = knowledge_graph

        # Git 集成
        try:
            self.git = GitIntegration(str(self.repo_path))
            self.diff_indexer = DiffIndexer(
                index_pipeline=self.index_pipeline,
                repo_path=str(self.repo_path),
                project_name=self.project_name
            )
        except ValueError as e:
            logger.warning(f"Git 集成不可用：{e}")
            self.git = None
            self.diff_indexer = None

        # Hook 管理器
        if self.git:
            self.hook_manager = GitHookManager(str(self.repo_path))
        else:
            self.hook_manager = None

        # 文件系统监听
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_watching = threading.Event()
        self._pending_changes: Dict[str, FileChange] = {}
        self._changes_lock = threading.Lock()

        # 回调函数
        self._on_change_callbacks: List[Callable] = []

        # 配置
        self.debounce_seconds = self.config.get('debounce_seconds', 2)
        self.batch_size = self.config.get('batch_size', 10)
        self.auto_sync = self.config.get('auto_sync', True)

        # 同步历史
        self._sync_history: List[SyncEvent] = []
        self._max_history = 100

        # 状态文件
        self._state_file = self.repo_path / '.ai-code-sync' / 'sync_state.json'
        self._load_state()

    def _load_state(self) -> None:
        """加载同步状态"""
        if self._state_file.exists():
            try:
                with open(self._state_file, 'r') as f:
                    self._state = json.load(f)
            except Exception:
                self._state = {}
        else:
            self._state = {}

    def _save_state(self) -> None:
        """保存同步状态"""
        try:
            self._state_file.parent.mkdir(exist_ok=True)
            with open(self._state_file, 'w') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.error(f"保存状态失败：{e}")

    def register_callback(self, callback: Callable[[SyncEvent], None]) -> None:
        """注册变更回调"""
        self._on_change_callbacks.append(callback)

    def _notify_callbacks(self, event: SyncEvent) -> None:
        """通知所有回调"""
        for callback in self._on_change_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"回调执行失败：{e}")

    def install(self) -> Dict[str, Any]:
        """安装 Git 变更同步"""
        result = {"success": True, "steps": []}

        # 安装 Git Hooks
        if self.hook_manager:
            hook_result = self.hook_manager.install_hooks()
            result["hooks"] = hook_result
            result["steps"].append("Git Hooks 安装完成")
        else:
            result["hooks"] = {"skipped": True, "reason": "Git 不可用"}
            result["steps"].append("Git Hooks 跳过 (非 Git 仓库)")

        # 初始化状态
        self._state.setdefault("last_sync", None)
        self._state.setdefault("last_commit", None)
        self._state.setdefault("sync_count", 0)
        self._save_state()
        result["steps"].append("同步状态初始化完成")

        return result

    def uninstall(self) -> Dict[str, Any]:
        """卸载 Git 变更同步"""
        result = {"success": True, "steps": []}

        # 停止监听
        self.stop_watching()
        result["steps"].append("文件监听已停止")

        # 卸载 Hooks
        if self.hook_manager:
            hook_result = self.hook_manager.uninstall_hooks()
            result["hooks"] = hook_result
            result["steps"].append("Git Hooks 已移除")

        return result

    def trigger_sync(
        self,
        trigger_type: str = "manual",
        commit_hash: Optional[str] = None
    ) -> SyncEvent:
        """
        触发同步

        Args:
            trigger_type: git_hook, file_watch, manual
            commit_hash: Git commit hash (仅 git_hook 模式)
        """
        logger.info(f"触发同步：type={trigger_type}, commit={commit_hash}")

        event = SyncEvent(
            event_id=f"sync_{int(time.time())}",
            trigger_type=trigger_type,
            changes=[]
        )

        try:
            event.status = "processing"

            # 获取变更
            changes = self._detect_changes(commit_hash)
            event.changes = changes

            if not changes:
                event.status = "completed"
                event.stats["message"] = "无变更需要同步"
                logger.info("无变更需要同步")
                return event

            # 执行同步
            sync_stats = self._sync_changes(changes)
            event.stats = sync_stats
            event.status = "completed"

            # 更新状态
            self._state["last_sync"] = datetime.now().isoformat()
            if commit_hash:
                self._state["last_commit"] = commit_hash
            self._state["sync_count"] = self._state.get("sync_count", 0) + 1
            self._save_state()

            # 记录历史
            self._sync_history.append(event)
            if len(self._sync_history) > self._max_history:
                self._sync_history = self._sync_history[-self._max_history:]

        except Exception as e:
            event.status = "failed"
            event.error = str(e)
            logger.error(f"同步失败：{e}")

        # 通知回调
        self._notify_callbacks(event)

        return event

    def _detect_changes(self, commit_hash: Optional[str] = None) -> List[FileChange]:
        """检测变更"""
        changes = []

        # 从 pending changes 获取
        with self._changes_lock:
            if self._pending_changes:
                changes.extend(self._pending_changes.values())
                self._pending_changes.clear()

        # 如果是 Git hook 触发，获取 commit 变更
        if commit_hash and self.git:
            try:
                diff_files = self.git.get_diff_files(f"{commit_hash}~1", commit_hash)
                for file_info in diff_files:
                    change = FileChange(
                        file_path=file_info.file_path,
                        change_type=ChangeType.MODIFIED,
                        git_status=file_info.status
                    )
                    if file_info.status == 'A':
                        change.change_type = ChangeType.CREATED
                    elif file_info.status == 'D':
                        change.change_type = ChangeType.DELETED
                    elif file_info.status == 'R':
                        change.change_type = ChangeType.RENAMED
                        change.old_path = file_info.old_path
                    changes.append(change)
            except Exception as e:
                logger.error(f"获取 Git 变更失败：{e}")

        return changes

    def _sync_changes(self, changes: List[FileChange]) -> Dict[str, Any]:
        """执行同步"""
        stats = {
            "total_changes": len(changes),
            "indexed": 0,
            "graph_updated": 0,
            "deleted": 0,
            "skipped": 0,
            "failed": 0
        }

        # 按文件分组
        files_to_index = []
        files_to_delete = []
        files_to_update_graph = []

        for change in changes:
            if change.change_type == ChangeType.DELETED:
                files_to_delete.append(change.file_path)
            else:
                files_to_index.append(change.file_path)
                if change.requires_graph_update:
                    files_to_update_graph.append(change.file_path)

        # 索引变更文件
        if self.index_pipeline and files_to_index:
            for file_path in files_to_index:
                try:
                    full_path = self.repo_path / file_path
                    if full_path.exists():
                        self.index_pipeline.index_file(
                            file_path=str(full_path),
                            collection_name=self.project_name,
                            incremental=True
                        )
                        stats["indexed"] += 1
                except Exception as e:
                    logger.error(f"索引失败 {file_path}: {e}")
                    stats["failed"] += 1

        # 删除文件索引
        if self.index_pipeline and files_to_delete:
            for file_path in files_to_delete:
                try:
                    self.index_pipeline.vector_store.delete_by_file(
                        self.project_name,
                        str(self.repo_path / file_path)
                    )
                    stats["deleted"] += 1
                except Exception as e:
                    logger.error(f"删除索引失败 {file_path}: {e}")
                    stats["failed"] += 1

        # 更新知识图谱
        if self.knowledge_graph and files_to_update_graph:
            try:
                # 使用增量更新
                from core.knowledge_graph.builder import KnowledgeGraphBuilder
                builder = KnowledgeGraphBuilder(self.project_name)
                self.knowledge_graph = builder.build_incremental(
                    [str(self.repo_path / f) for f in files_to_update_graph]
                )
                stats["graph_updated"] = len(files_to_update_graph)
            except Exception as e:
                logger.error(f"更新知识图谱失败：{e}")
                stats["failed"] += 1

        return stats

    # ========== 文件系统监听 ==========

    def start_watching(self, background: bool = True) -> Dict[str, Any]:
        """启动文件监听"""
        if not WATCHFILES_AVAILABLE:
            return {
                "success": False,
                "error": "watchfiles 不可用，请运行：pip install watchfiles"
            }

        if self._watch_thread and self._watch_thread.is_alive():
            return {
                "success": True,
                "message": "监听已在运行"
            }

        self._stop_watching.clear()

        if background:
            self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._watch_thread.start()
            return {
                "success": True,
                "message": "文件监听已启动 (后台模式)"
            }
        else:
            self._watch_loop()
            return {
                "success": True,
                "message": "文件监听已启动 (阻塞模式)"
            }

    def stop_watching(self) -> Dict[str, Any]:
        """停止文件监听"""
        if not self._watch_thread:
            return {"success": True, "message": "监听未启动"}

        self._stop_watching.set()
        self._watch_thread.join(timeout=5)
        self._watch_thread = None

        return {"success": True, "message": "文件监听已停止"}

    def _watch_loop(self) -> None:
        """文件监听循环"""
        from watchfiles import watch, Change as WatchChange

        logger.info(f"开始监听文件变更：{self.repo_path}")

        # 监听的文件类型
        target_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs'}

        def filter_func(change: WatchChange, path: str) -> bool:
            return Path(path).suffix in target_extensions

        try:
            for changes in watch(
                str(self.repo_path),
                watch_filter=filter_func,
                debounce=self.debounce_seconds * 1000,
                stop_event=self._stop_watching
            ):
                batch_changes = []
                for change_type, path in changes:
                    rel_path = str(Path(path).relative_to(self.repo_path))

                    # 跳过内部目录
                    if '.ai-code-sync' in rel_path or '__pycache__' in rel_path:
                        continue

                    change = FileChange(
                        file_path=rel_path,
                        change_type=ChangeType.MODIFIED,
                        git_status=None
                    )

                    if change_type == WatchChange.added:
                        change.change_type = ChangeType.CREATED
                    elif change_type == WatchChange.deleted:
                        change.change_type = ChangeType.DELETED

                    batch_changes.append(change)

                # 批量处理
                if batch_changes:
                    self._process_batch_changes(batch_changes)

        except Exception as e:
            logger.error(f"文件监听错误：{e}")

    def _process_batch_changes(self, changes: List[FileChange]) -> None:
        """批量处理文件变更"""
        with self._changes_lock:
            for change in changes:
                self._pending_changes[change.file_path] = change

        logger.info(f"检测到 {len(changes)} 个文件变更")

        # 如果启用自动同步，触发同步
        if self.auto_sync:
            event = self.trigger_sync(trigger_type="file_watch")
            logger.info(f"自动同步完成：{event.stats}")

    # ========== 状态查询 ==========

    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            "project_name": self.project_name,
            "repo_path": str(self.repo_path),
            "git_available": self.git is not None,
            "hooks_installed": self.hook_manager.check_hooks_installed() if self.hook_manager else {},
            "watching": self._watch_thread is not None and self._watch_thread.is_alive(),
            "last_sync": self._state.get("last_sync"),
            "last_commit": self._state.get("last_commit"),
            "sync_count": self._state.get("sync_count", 0),
            "pending_changes": len(self._pending_changes)
        }

    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取同步历史"""
        events = self._sync_history[-limit:]
        return [e.to_dict() for e in reversed(events)]


# 便捷函数
def create_git_syncer(
    repo_path: str,
    project_name: Optional[str] = None,
    **kwargs
) -> GitChangeSynchronizer:
    """创建 Git 变更同步器"""
    return GitChangeSynchronizer(
        repo_path=repo_path,
        project_name=project_name,
        **kwargs
    )
