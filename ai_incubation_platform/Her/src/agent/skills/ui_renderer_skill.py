"""
自适应 UI 渲染 Skill

P2 功能：根据情境动态选择和渲染最适合的 UI 组件
"""
from typing import Dict, Any, Optional, List
from agent.skills.base import BaseSkill
from utils.logger import logger


class UIRendererSkill:
    """
    自适应 UI 渲染 Skill

    核心能力:
    - 情境感知 UI 选择
    - 动态组件渲染
    - 个性化 UI 配置
    - 响应式布局
    - UI 状态管理

    自主触发条件:
    - 情境变化时
    - 用户交互需要 UI 反馈
    - 数据类型变化时
    """

    name = "ui_renderer"
    version = "1.0.0"
    description = """
    自适应 UI 渲染专家

    能力:
    - 基于情境动态选择 UI 组件
    - 12+ 种 UI 组件类型支持
    - 个性化 UI 配置生成
    - 响应式布局适配
    - UI 组件状态管理
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "context_type": {
                    "type": "string",
                    "description": "情境类型"
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型"
                },
                "data": {
                    "type": "object",
                    "description": "渲染数据"
                },
                "user_preferences": {
                    "type": "object",
                    "description": "用户 UI 偏好"
                },
                "device_type": {
                    "type": "string",
                    "enum": ["mobile", "tablet", "desktop"],
                    "description": "设备类型"
                }
            },
            "required": ["context_type"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "component_type": {"type": "string"},
                "component_name": {"type": "string"},
                "props": {"type": "object"},
                "layout": {"type": "object"},
                "style": {"type": "object"}
            }
        }

    async def execute(
        self,
        context_type: str,
        data_type: Optional[str] = None,
        data: Optional[Dict] = None,
        user_preferences: Optional[Dict] = None,
        device_type: str = "mobile",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 UI 渲染

        Args:
            context_type: 情境类型
            data_type: 数据类型
            data: 渲染数据
            user_preferences: 用户偏好
            device_type: 设备类型

        Returns:
            UI 配置
        """
        logger.info(f"UIRenderer: Rendering for context={context_type}, device={device_type}")

        try:
            # 选择组件
            component_config = self._select_component(
                context_type, data_type, data, user_preferences
            )

            # 应用设备适配
            layout_config = self._adapt_layout(component_config, device_type)

            # 应用用户偏好
            if user_preferences:
                component_config = self._apply_user_preferences(
                    component_config, user_preferences
                )

            # 添加数据
            if data:
                component_config["props"]["data"] = data

            # 构建响应
            return self._build_response(
                component_config, layout_config, context_type
            )

        except Exception as e:
            logger.error(f"UIRenderer execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "UI 渲染失败，请稍后再试"
            }

    def _select_component(
        self,
        context_type: str,
        data_type: Optional[str],
        data: Optional[Dict],
        user_preferences: Optional[Dict]
    ) -> Dict:
        """选择 UI 组件"""
        # 情境 -> 组件映射
        context_component_map = {
            "silence": {
                "component_type": "silence_breaker",
                "component_name": "沉默打破器",
                "default_props": {
                    "activity_type": "topic",
                    "urgency": "normal",
                    "suggested_topics": [],
                },
            },
            "silence_critical": {
                "component_type": "silence_breaker",
                "component_name": "沉默打破器",
                "default_props": {
                    "activity_type": "game",
                    "urgency": "high",
                    "show_countdown": True,
                },
            },
            "conflict": {
                "component_type": "conflict_mediator",
                "component_name": "冲突调解器",
                "default_props": {
                    "show_tips": True,
                    "calm_mode": True,
                    "mediation_tips": [],
                },
            },
            "conflict_severe": {
                "component_type": "emotion_mediator",
                "component_name": "情感调解员",
                "default_props": {
                    "emergency_mode": True,
                    "calming_exercise": True,
                },
            },
            "deep_conversation": {
                "component_type": "deep_chat_input",
                "component_name": "深度聊天输入",
                "default_props": {
                    "placeholder": "深入聊聊...",
                    "show_deep_topics": True,
                    "enable_voice": True,
                },
            },
            "first_contact": {
                "component_type": "chat_input_with_suggestions",
                "component_name": "带建议的聊天输入",
                "default_props": {
                    "placeholder": "打个招呼吧~",
                    "suggested_replies": [],
                    "show_profile_highlights": True,
                },
            },
            "pre_date": {
                "component_type": "date_prep_panel",
                "component_name": "约会准备面板",
                "default_props": {
                    "checklist": [],
                    "tips": [],
                    "countdown": True,
                },
            },
            "breakthrough": {
                "component_type": "celebration_card",
                "component_name": "庆祝卡片",
                "default_props": {
                    "animation": "confetti",
                    "milestone_type": "breakthrough",
                },
            },
        }

        # 获取基础组件配置
        base_config = context_component_map.get(context_type, {
            "component_type": "chat_input",
            "component_name": "聊天输入",
            "default_props": {
                "placeholder": "输入消息...",
                "enable_voice": True,
                "enable_emoji": True,
            },
        })

        # 根据数据类型调整
        if data_type:
            base_config = self._adjust_for_data_type(base_config, data_type)

        return {
            "component_type": base_config["component_type"],
            "component_name": base_config["component_name"],
            "props": base_config["default_props"].copy(),
        }

    def _adjust_for_data_type(
        self,
        base_config: Dict,
        data_type: str
    ) -> Dict:
        """根据数据类型调整组件"""
        data_type_adjustments = {
            "match": {
                "component_type": "match_card_list",
                "component_name": "匹配卡片列表",
                "default_props": {
                    "layout": "swipe",
                    "show_details": True,
                },
            },
            "gift": {
                "component_type": "gift_grid",
                "component_name": "礼物网格",
                "default_props": {
                    "layout": "grid",
                    "columns": 2,
                },
            },
            "date": {
                "component_type": "date_spot_list",
                "component_name": "约会地点列表",
                "default_props": {
                    "show_map": True,
                    "show_reviews": True,
                },
            },
            "profile": {
                "component_type": "profile_card",
                "component_name": "个人资料卡片",
                "default_props": {
                    "show_badges": True,
                    "show_verification": True,
                },
            },
            "report": {
                "component_type": "report_card",
                "component_name": "报告卡片",
                "default_props": {
                    "show_summary": True,
                    "expandable_sections": True,
                },
            },
        }

        adjustment = data_type_adjustments.get(data_type)
        if adjustment:
            # 保留原始 props，合并调整后的 props
            merged_props = {**base_config.get("props", {}), **adjustment["default_props"]}
            return {
                "component_type": adjustment["component_type"],
                "component_name": adjustment["component_name"],
                "props": merged_props,
            }

        return base_config

    def _adapt_layout(
        self,
        component_config: Dict,
        device_type: str
    ) -> Dict:
        """适配设备布局"""
        layouts = {
            "mobile": {
                "width": "100%",
                "padding": "12px",
                "font_size": "14px",
                "button_size": "large",
                "grid_columns": 1,
            },
            "tablet": {
                "width": "90%",
                "padding": "16px",
                "font_size": "15px",
                "button_size": "medium",
                "grid_columns": 2,
            },
            "desktop": {
                "width": "80%",
                "padding": "20px",
                "font_size": "16px",
                "button_size": "medium",
                "grid_columns": 3,
            },
        }

        return layouts.get(device_type, layouts["mobile"])

    def _apply_user_preferences(
        self,
        component_config: Dict,
        preferences: Dict
    ) -> Dict:
        """应用用户偏好"""
        # 主题偏好
        if preferences.get("theme"):
            component_config["props"]["theme"] = preferences["theme"]

        # 颜色偏好
        if preferences.get("color_scheme"):
            component_config["props"]["colorScheme"] = preferences["color_scheme"]

        # 动画偏好
        if preferences.get("enable_animations") is False:
            component_config["props"]["enableAnimations"] = False

        # 字体大小偏好
        if preferences.get("font_size"):
            component_config["props"]["fontSize"] = preferences["font_size"]

        return component_config

    def _build_response(
        self,
        component_config: Dict,
        layout_config: Dict,
        context_type: str
    ) -> Dict[str, Any]:
        """构建响应"""
        ai_message = f"已为{context_type}情境选择{component_config['component_name']}组件"

        return {
            "success": True,
            "data": {
                "component_type": component_config["component_type"],
                "component_name": component_config["component_name"],
                "props": component_config["props"],
                "layout": layout_config,
                "render_mode": "adaptive",
            },
            "ai_message": ai_message,
        }


# 全局单例获取函数
_skill_instance: Optional[UIRendererSkill] = None


def get_ui_renderer_skill() -> UIRendererSkill:
    """获取自适应 UI 渲染 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = UIRendererSkill()
    return _skill_instance
