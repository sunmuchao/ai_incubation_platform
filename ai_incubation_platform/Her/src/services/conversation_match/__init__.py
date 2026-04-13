"""
对话匹配服务组件模块

从 ConversationMatchService 拆分的组件：
- IntentAnalyzer: 意图分析器（已在主文件中）
- QueryQualityChecker: 查询质量校验器（已在主文件中）
- MatchExecutor: 匹配执行器
- AdviceGenerator: 建议生成器
- UIBuilder: UI 构建器

重构说明：
- 原 ConversationMatchService 1100 行
- 拆分后每个组件 50-200 行
- 主服务类约 200 行（编排层）
"""

from services.conversation_match.match_executor import MatchExecutor, get_match_executor
from services.conversation_match.advice_generator import AdviceGenerator, get_advice_generator
from services.conversation_match.ui_builder import UIBuilder, get_ui_builder

__all__ = [
    "MatchExecutor",
    "get_match_executor",
    "AdviceGenerator",
    "get_advice_generator",
    "UIBuilder",
    "get_ui_builder",
]