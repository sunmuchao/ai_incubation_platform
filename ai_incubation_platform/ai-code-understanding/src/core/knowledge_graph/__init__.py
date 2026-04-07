"""
代码知识图谱模块

提供代码库的语义级图谱表示，支持：
1. 多层级节点：项目、包、模块、类、函数、变量
2. 多类型边：依赖、调用、继承、实现、引用、包含
3. 图谱查询：路径分析、影响范围、核心节点识别
4. 图谱持久化：JSON 导出/导入，增量更新
"""

from .models import (
    KGNode,
    KGEdge,
    NodeType,
    EdgeType,
)
from .builder import KnowledgeGraphBuilder
from .graph import KnowledgeGraph
from .query import KnowledgeGraphQuery

__all__ = [
    "KGNode",
    "KGEdge",
    "NodeType",
    "EdgeType",
    "KnowledgeGraph",
    "KnowledgeGraphBuilder",
    "KnowledgeGraphQuery",
]
