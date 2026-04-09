"""
偏好学习 Skill

P2 功能：从用户行为中学习偏好，支持显式和隐式学习
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class PreferenceLearnerSkill:
    """
    偏好学习 Skill

    核心能力:
    - 显式偏好收集
    - 隐式偏好推断
    - 偏好强度计算
    - 偏好冲突解决
    - 学习进度追踪

    自主触发条件:
    - 用户产生新行为时
    - 偏好置信度达到阈值
    - 定期偏好汇总
    """

    name = "preference_learner"
    version = "1.0.0"
    description = """
    偏好学习专家

    能力:
    - 显式偏好收集 (用户直接表达)
    - 隐式偏好推断 (从行为学习)
    - 偏好强度动态计算
    - 偏好冲突检测与解决
    - 5 大类别偏好管理
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "action": {
                    "type": "string",
                    "enum": ["learn", "get", "update", "remove", "list"],
                    "description": "操作类型"
                },
                "preference_data": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "key": {"type": "string"},
                        "value": {"type": "any"},
                        "preference_type": {"type": "string"},
                        "confidence": {"type": "number"}
                    }
                },
                "category": {
                    "type": "string",
                    "description": "偏好类别"
                },
                "source": {
                    "type": "string",
                    "enum": ["explicit", "implicit", "inferred"],
                    "description": "偏好来源"
                }
            },
            "required": ["user_id", "action"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "preferences": {"type": "array"},
                "preference_count": {"type": "integer"},
                "learning_progress": {"type": "object"}
            }
        }

    async def execute(
        self,
        user_id: str,
        action: str = "learn",
        preference_data: Optional[Dict] = None,
        category: Optional[str] = None,
        source: str = "implicit",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行偏好学习

        Args:
            user_id: 用户 ID
            action: 操作类型
            preference_data: 偏好数据
            category: 偏好类别
            source: 偏好来源

        Returns:
            学习结果
        """
        logger.info(f"PreferenceLearner: {action} for user={user_id}")

        try:
            if action == "learn":
                return self._learn_preference(user_id, preference_data, source)
            elif action == "get":
                return self._get_preference(user_id, category)
            elif action == "update":
                return self._update_preference(user_id, preference_data)
            elif action == "remove":
                return self._remove_preference(user_id, preference_data)
            elif action == "list":
                return self._list_preferences(user_id, category)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "ai_message": "未知的操作类型",
                }

        except Exception as e:
            logger.error(f"PreferenceLearner execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "偏好学习失败，请稍后再试"
            }

    def _learn_preference(
        self,
        user_id: str,
        preference_data: Optional[Dict],
        source: str
    ) -> Dict[str, Any]:
        """学习偏好"""
        from services.ai_learning_service import ai_learning_service

        if not preference_data:
            return {
                "success": False,
                "error": "preference_data is required",
                "ai_message": "请提供偏好数据",
            }

        # 添加偏好
        success, message, preference = ai_learning_service.add_preference(
            user_id=user_id,
            category=preference_data.get("category", "general"),
            preference_key=preference_data.get("key", ""),
            preference_value=preference_data.get("value"),
            preference_type=preference_data.get("preference_type", "like"),
            confidence_score=preference_data.get("confidence", 0.5),
            inference_method=source,
        )

        if not success:
            return {
                "success": False,
                "error": message,
                "ai_message": message,
            }

        # 更新学习进度
        ai_learning_service.update_learning_progress(
            user_id=user_id,
            progress_delta=5,
            learned_preferences_delta=1,
        )

        return {
            "success": True,
            "data": {
                "preference_id": preference.id,
                "category": preference.category,
                "key": preference.preference_key,
                "value": preference.preference_value,
                "confidence": preference.confidence_score,
            },
            "ai_message": f"已学习新偏好：{preference.preference_key}",
        }

    def _get_preference(
        self,
        user_id: str,
        category: Optional[str]
    ) -> Dict[str, Any]:
        """获取偏好"""
        from services.ai_learning_service import ai_learning_service

        if not category:
            return {
                "success": False,
                "error": "category is required",
                "ai_message": "请指定偏好类别",
            }

        preference = ai_learning_service.get_preference(
            user_id=user_id,
            category=category,
            preference_key=category,
        )

        if preference:
            return {
                "success": True,
                "data": preference.to_dict(),
                "ai_message": f"获取{category}偏好成功",
            }
        else:
            return {
                "success": True,
                "data": None,
                "ai_message": f"尚未记录{category}偏好",
            }

    def _update_preference(
        self,
        user_id: str,
        preference_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """更新偏好"""
        from services.ai_learning_service import ai_learning_service

        if not preference_data:
            return {
                "success": False,
                "error": "preference_data is required",
                "ai_message": "请提供偏好数据",
            }

        # 先移除旧偏好，再添加新偏好
        ai_learning_service.remove_preference(
            user_id=user_id,
            category=preference_data.get("category", "general"),
            preference_key=preference_data.get("key", ""),
        )

        return self._learn_preference(user_id, preference_data, "explicit")

    def _remove_preference(
        self,
        user_id: str,
        preference_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """移除偏好"""
        from services.ai_learning_service import ai_learning_service

        if not preference_data:
            return {
                "success": False,
                "error": "preference_data is required",
                "ai_message": "请提供偏好数据",
            }

        success, message = ai_learning_service.remove_preference(
            user_id=user_id,
            category=preference_data.get("category", "general"),
            preference_key=preference_data.get("key", ""),
        )

        return {
            "success": success,
            "message": message,
            "ai_message": message if success else f"移除偏好失败：{message}",
        }

    def _list_preferences(
        self,
        user_id: str,
        category: Optional[str]
    ) -> Dict[str, Any]:
        """列出偏好"""
        from services.ai_learning_service import ai_learning_service

        preferences = ai_learning_service.get_user_preferences(
            user_id=user_id,
            category=category,
            min_confidence=0.3,
        )

        return {
            "success": True,
            "data": {
                "preferences": [p.to_dict() for p in preferences],
                "preference_count": len(preferences),
                "category": category or "all",
            },
            "ai_message": f"共找到{len(preferences)}条偏好记录",
        }


# 全局单例获取函数
_skill_instance: Optional[PreferenceLearnerSkill] = None


def get_preference_learner_skill() -> PreferenceLearnerSkill:
    """获取偏好学习 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = PreferenceLearnerSkill()
    return _skill_instance
