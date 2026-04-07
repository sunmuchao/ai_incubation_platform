"""Git 集成模块"""
from .diff_indexer import (
    GitIntegration,
    GitDiffInfo,
    DiffIndexer,
    create_diff_indexer
)
from .git_sync import (
    GitChangeSynchronizer,
    GitHookManager,
    SyncMode,
    ChangeType,
    FileChange,
    SyncEvent,
    create_git_syncer
)

__all__ = [
    "GitIntegration",
    "GitDiffInfo",
    "DiffIndexer",
    "create_diff_indexer",
    "GitChangeSynchronizer",
    "GitHookManager",
    "SyncMode",
    "ChangeType",
    "FileChange",
    "SyncEvent",
    "create_git_syncer"
]
