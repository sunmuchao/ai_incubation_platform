"""
置信度子包（精简入口）

活跃实现：
- `services.confidence.feedback_loop` — 由 `api/confidence_feedback` 挂载 HTTP 路由
- `services.confidence.dynamic_weights` — 由 `feedback_loop` 间接使用

已移除：综合编排器与扩展校验 / LLM 深度分析 / 实时更新模块（见仓库根目录 `deprecated_archive` 历史快照，若目录已删除则以 Git 历史为准）。
"""

# 保持为可导入的 Python 包；勿再从此处隐式聚合已归档子模块。

__all__: list = []
