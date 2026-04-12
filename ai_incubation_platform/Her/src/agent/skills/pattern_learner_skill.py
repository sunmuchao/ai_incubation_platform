"""
行为模式学习 Skill

DigitalTwin 功能：从用户历史行为中学习行为模式，识别规律和习惯
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class PatternLearnerSkill:
    """
    行为模式学习 Skill

    核心能力:
    - 活跃时间模式识别
    - 回复风格模式学习
    - 匹配偏好模式分析
    - 沟通习惯模式提取
    - 模式验证与更新

    自主触发条件:
    - 行为数据积累到阈值
    - 检测到新行为模式
    - 定期模式更新
    """

    name = "pattern_learner"
    version = "1.0.0"
    description = """
    行为模式学习专家

    能力:
    - 活跃时间模式识别 (在线时间规律)
    - 回复风格模式学习 (回复速度、长度、表情使用)
    - 匹配偏好模式分析 (浏览、点赞偏好)
    - 沟通习惯模式提取 (主动/被动、话题偏好)
    - 模式验证 (显式/隐式)
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
                    "enum": ["learn", "get", "validate", "list", "analyze"],
                    "description": "操作类型"
                },
                "pattern_type": {
                    "type": "string",
                    "enum": ["online_time", "response_style", "matching_preference", "communication_habit", "dating_preference"],
                    "description": "模式类型"
                },
                "pattern_data": {
                    "type": "object",
                    "description": "模式数据"
                },
                "analysis_window_days": {
                    "type": "integer",
                    "description": "分析窗口天数",
                    "default": 30
                },
                "validation_result": {
                    "type": "string",
                    "enum": ["confirmed", "rejected", "modified"],
                    "description": "验证结果"
                }
            },
            "required": ["user_id", "action"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "patterns": {"type": "array"},
                "pattern_count": {"type": "integer"},
                "analysis_result": {"type": "object"}
            }
        }

    async def execute(
        self,
        user_id: str,
        action: str = "learn",
        pattern_type: Optional[str] = None,
        pattern_data: Optional[Dict] = None,
        analysis_window_days: int = 30,
        validation_result: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行行为模式学习

        Args:
            user_id: 用户 ID
            action: 操作类型
            pattern_type: 模式类型
            pattern_data: 模式数据
            analysis_window_days: 分析窗口
            validation_result: 验证结果

        Returns:
            学习结果
        """
        logger.info(f"PatternLearner: {action} for user={user_id}, type={pattern_type}")

        try:
            if action == "learn":
                return self._learn_pattern(user_id, pattern_type, pattern_data)
            elif action == "get":
                return self._get_pattern(user_id, pattern_type)
            elif action == "validate":
                return self._validate_pattern(user_id, pattern_type, validation_result)
            elif action == "list":
                return self._list_patterns(user_id, pattern_type)
            elif action == "analyze":
                return self._analyze_patterns(user_id, analysis_window_days)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "ai_message": "未知的操作类型",
                }

        except Exception as e:
            logger.error(f"PatternLearner execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "模式学习失败，请稍后再试"
            }

    def _learn_pattern(
        self,
        user_id: str,
        pattern_type: Optional[str],
        pattern_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """学习模式"""
        from services.ai_learning_service import ai_learning_service

        if not pattern_type or not pattern_data:
            return {
                "success": False,
                "error": "pattern_type and pattern_data are required",
                "ai_message": "请提供模式类型和数据",
            }

        # 学习模式
        success, message, pattern = ai_learning_service.learn_pattern(
            user_id=user_id,
            pattern_type=pattern_type,
            pattern_data=pattern_data,
            pattern_strength=pattern_data.get("pattern_strength", 0.5),
            is_validated=False,  # 新模式需要验证
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
            progress_delta=3,
            validated_patterns_delta=0,
        )

        return {
            "success": True,
            "data": {
                "pattern_id": pattern.id,
                "pattern_type": pattern.pattern_type,
                "pattern_strength": pattern.pattern_strength,
                "is_validated": pattern.is_validated,
            },
            "ai_message": f"已学习{self._get_pattern_name(pattern_type)}模式",
        }

    def _get_pattern(
        self,
        user_id: str,
        pattern_type: Optional[str]
    ) -> Dict[str, Any]:
        """获取模式"""
        from services.ai_learning_service import ai_learning_service

        patterns = ai_learning_service.get_user_patterns(
            user_id=user_id,
            pattern_type=pattern_type,
            min_strength=0.3,
        )

        if patterns:
            # 返回最强的模式
            pattern = max(patterns, key=lambda p: p.pattern_strength)
            return {
                "success": True,
                "data": {
                    "pattern": pattern.to_dict(),
                    "pattern_name": self._get_pattern_name(pattern.pattern_type),
                    "pattern_description": self._get_pattern_description(pattern.pattern_type, pattern.pattern_data),
                },
                "ai_message": f"获取{self._get_pattern_name(pattern.pattern_type)}模式成功",
            }
        else:
            return {
                "success": True,
                "data": None,
                "ai_message": f"尚未记录{pattern_type or '任何'}行为模式",
            }

    def _validate_pattern(
        self,
        user_id: str,
        pattern_type: Optional[str],
        validation_result: Optional[str]
    ) -> Dict[str, Any]:
        """验证模式"""
        from services.ai_learning_service import ai_learning_service

        if not pattern_type:
            return {
                "success": False,
                "error": "pattern_type is required",
                "ai_message": "请指定模式类型",
            }

        # 验证模式
        validation_source = "explicit" if validation_result else "implicit"
        success, message = ai_learning_service.validate_pattern(
            user_id=user_id,
            pattern_type=pattern_type,
            validation_source=validation_source,
        )

        if validation_result == "confirmed":
            # 更新学习进度
            ai_learning_service.update_learning_progress(
                user_id=user_id,
                progress_delta=10,
                validated_patterns_delta=1,
            )

        return {
            "success": success,
            "message": message,
            "ai_message": f"模式验证{'成功' if success else '失败'}：{message}",
        }

    def _list_patterns(
        self,
        user_id: str,
        pattern_type: Optional[str]
    ) -> Dict[str, Any]:
        """列出模式"""
        from services.ai_learning_service import ai_learning_service

        patterns = ai_learning_service.get_user_patterns(
            user_id=user_id,
            pattern_type=pattern_type,
            min_strength=0.1,
        )

        return {
            "success": True,
            "data": {
                "patterns": [
                    {
                        "pattern_type": p.pattern_type,
                        "pattern_name": self._get_pattern_name(p.pattern_type),
                        "pattern_strength": p.pattern_strength,
                        "is_validated": p.is_validated,
                        "observation_count": p.observation_count,
                    }
                    for p in patterns
                ],
                "pattern_count": len(patterns),
                "validated_count": sum(1 for p in patterns if p.is_validated),
            },
            "ai_message": f"共找到{len(patterns)}个行为模式，其中{sum(1 for p in patterns if p.is_validated)}个已验证",
        }

    def _analyze_patterns(
        self,
        user_id: str,
        analysis_window_days: int
    ) -> Dict[str, Any]:
        """分析模式"""
        from services.ai_learning_service import ai_learning_service

        # 获取所有模式
        all_patterns = ai_learning_service.get_user_patterns(
            user_id=user_id,
            min_strength=0.1,
        )

        # 分析结果
        analysis_result = {
            "strong_patterns": [],
            "emerging_patterns": [],
            "pattern_summary": {},
            "recommendations": [],
        }

        for pattern in all_patterns:
            pattern_info = {
                "type": pattern.pattern_type,
                "name": self._get_pattern_name(pattern.pattern_type),
                "strength": pattern.pattern_strength,
                "is_validated": pattern.is_validated,
            }

            if pattern.pattern_strength >= 0.7:
                analysis_result["strong_patterns"].append(pattern_info)
            elif pattern.pattern_strength >= 0.3:
                analysis_result["emerging_patterns"].append(pattern_info)

        # 生成建议
        if len(analysis_result["strong_patterns"]) >= 3:
            analysis_result["recommendations"].append({
                "type": "pattern_leverage",
                "message": "AI 已经充分了解您的行为习惯，将提供更精准的服务",
            })

        if len([p for p in all_patterns if p.is_validated]) < len(all_patterns) / 2:
            analysis_result["recommendations"].append({
                "type": "validation_needed",
                "message": "部分行为模式等待您的确认，帮助 AI 更准确了解您",
            })

        return {
            "success": True,
            "data": {
                "analysis_window_days": analysis_window_days,
                "total_patterns": len(all_patterns),
                "analysis_result": analysis_result,
            },
            "ai_message": f"分析完成！发现{len(analysis_result['strong_patterns'])}个显著模式，{len(analysis_result['emerging_patterns'])}个潜在模式",
        }

    # ========== 辅助函数 ==========

    def _get_pattern_name(self, pattern_type: str) -> str:
        """获取模式名称"""
        names = {
            "online_time": "活跃时间",
            "response_style": "回复风格",
            "matching_preference": "匹配偏好",
            "communication_habit": "沟通习惯",
            "dating_preference": "约会偏好",
        }
        return names.get(pattern_type, pattern_type)

    def _get_pattern_description(
        self,
        pattern_type: str,
        pattern_data: Dict
    ) -> str:
        """获取模式描述"""
        descriptions = {
            "online_time": f"用户活跃时间规律：{pattern_data.get('peak_hours', [])}",
            "response_style": f"回复风格：平均{pattern_data.get('avg_response_time', 0)}分钟回复，平均长度{pattern_data.get('avg_length', 0)}字",
            "matching_preference": f"匹配偏好：偏好{pattern_data.get('preferred_age_range', '未知')}年龄段",
            "communication_habit": f"沟通习惯：{pattern_data.get('initiates_conversation', '未知')}",
            "dating_preference": f"约会偏好：{pattern_data.get('preferred_day', '未知')}",
        }
        return descriptions.get(pattern_type, "行为模式描述")


# 全局单例获取函数
_skill_instance: Optional[PatternLearnerSkill] = None


def get_pattern_learner_skill() -> PatternLearnerSkill:
    """获取行为模式学习 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = PatternLearnerSkill()
    return _skill_instance
