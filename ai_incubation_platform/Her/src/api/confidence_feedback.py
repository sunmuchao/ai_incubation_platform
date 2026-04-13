"""
置信度反馈 API

提供置信度评估的反馈闭环接口，用于：
- 收集用户对匹配对象的置信度反馈
- 统计反馈数据
- 规则优化（管理员）
- 误报补偿（管理员）
"""

from services.confidence.feedback_loop import router

__all__ = ["router"]