"""
匹配模块

已废弃的模块（均已删除）：
- matcher.py：数值计算匹配算法
- engine_switch.py：双引擎切换逻辑
- rule_engine.py：规则引擎（依赖已删除的 matcher.py）
- agentic_engine.py：许愿模式引擎（依赖已删除的 rule_engine.py）
- engine_base.py：引擎基类

新架构：AI Native 匹配
- DeerFlow → her_tools → ConversationMatchService
- HerAdvisorService（AI）直接判断匹配度
- 候选人从数据库查询，无需内存池
- 详见 HER_ADVISOR_ARCHITECTURE.md

匹配功能入口：
- API: /api/matching/{user_id}/matches
- DeerFlow: her_find_matches_tool
- Service: ConversationMatchService.execute_matching()
"""

# 当前模块为空，匹配逻辑在 ConversationMatchService 中

__all__ = []