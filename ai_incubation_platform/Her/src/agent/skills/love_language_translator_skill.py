"""
爱之语翻译 Skill - 解读真实需求，促进理解

AI 关系翻译官核心 Skill - 爱之语识别、需求解读、回应建议
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger
import re


class LoveLanguageTranslatorSkill(BaseSkill):
    """
    AI 爱之语翻译官 Skill - 帮助伴侣理解彼此的真实需求

    核心能力:
    - 爱之语识别：5 种爱之语类型检测
    - 需求解读：表面话语背后的真实意图
    - 回应建议：提供有效的回应方式
    - 沟通模式分析：识别健康/不健康的表达模式

    自主触发:
    - 检测到抱怨/抱怨升级
    - 用户主动寻求翻译帮助
    - 对话中出现误解信号
    """

    name = "love_language_translator"
    version = "1.0.0"
    description = """
    AI 爱之语翻译官，帮助伴侣理解彼此的真实需求

    能力:
    - 爱之语识别：5 种类型（肯定言辞、精心时刻、接受礼物、服务行动、身体接触）
    - 需求解读：从抱怨中识别真实需求
    - 回应建议：提供温暖有效的回应方式
    - 沟通辅导：改善表达和倾听技巧
    """

    # 五种爱之语
    LOVE_LANGUAGES = {
        "words": {
            "name": "肯定的言辞",
            "description": "通过赞美、感谢、肯定的话语表达爱",
            "keywords": ["喜欢", "爱", "欣赏", "赞美", "谢谢", "感谢", "很棒", "骄傲"]
        },
        "time": {
            "name": "精心时刻",
            "description": "通过专注的陪伴和共处表达爱",
            "keywords": ["一起", "陪伴", "时间", "见面", "约会", "聊天", "说话"]
        },
        "gifts": {
            "name": "接受礼物",
            "description": "通过礼物和惊喜表达爱",
            "keywords": ["送", "礼物", "买", "准备", "惊喜", "收到", "快递"]
        },
        "acts": {
            "name": "服务的行动",
            "description": "通过实际行动和分担表达爱",
            "keywords": ["帮你", "为你", "替你", "帮忙", "照顾", "处理", "做饭"]
        },
        "touch": {
            "name": "身体的接触",
            "description": "通过身体接触表达爱",
            "keywords": ["拥抱", "牵手", "亲吻", "摸", "靠", "抱抱", "亲密"]
        }
    }

    # 需求模式：表面表达 → 真实需求
    NEED_PATTERNS = {
        "words": {
            "surface_patterns": [
                r"你都不.*我",
                r"你从来不.*我",
                r"你有多久.*我",
                r"你都没.*我"
            ],
            "true_intention": "希望得到更多的肯定和赞美",
            "suggested_response": "我真的很欣赏你{quality}，谢谢你一直以来的{contribution}",
            "example": "你是不是觉得我不够欣赏你？让我告诉你我有多感激你..."
        },
        "time": {
            "surface_patterns": [
                r"你总是.*忙",
                r"你都没时间.*我",
                r"我们好久没.*一起",
                r"你都不陪我"
            ],
            "true_intention": "渴望更多的陪伴和关注",
            "suggested_response": "你说得对，我确实应该花更多时间陪你。我们{activity}怎么样？",
            "example": "你是不是觉得我最近陪你的时间太少了？我们来安排一个约会吧..."
        },
        "gifts": {
            "surface_patterns": [
                r"你都不.*惊喜",
                r"别人都有.*礼物",
                r"你记得.*日子",
                r"你都没准备"
            ],
            "true_intention": "希望被重视和用心对待",
            "suggested_response": "我想为你准备一个惊喜，你最近有想要什么特别的东西吗？",
            "example": "你是不是觉得我不够用心？让我为你准备一个小惊喜..."
        },
        "acts": {
            "surface_patterns": [
                r"都是.*我做",
                r"你从来不.*家务",
                r"你就不能.*一下",
                r"什么都是我"
            ],
            "true_intention": "希望分担和体贴",
            "suggested_response": "我来处理{task}吧，你休息一下。还有什么我可以帮你的？",
            "example": "你是不是觉得家务都是你在做？让我来帮忙..."
        },
        "touch": {
            "surface_patterns": [
                r"你都不.*抱我",
                r"我们好久没.*亲密",
                r"你离我.*远",
                r"你都不碰我"
            ],
            "true_intention": "渴望身体接触和亲密感",
            "suggested_response": "过来让我抱抱你。（主动的身体接触）",
            "example": "你是不是觉得我们最近不够亲密？来，让我抱抱你..."
        }
    }

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "表达者用户 ID"
                },
                "target_user_id": {
                    "type": "string",
                    "description": "接收者用户 ID"
                },
                "expression": {
                    "type": "string",
                    "description": "需要翻译的表达内容"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "relationship_stage": {"type": "string"},
                        "conversation_id": {"type": "string"},
                        "recent_interactions": {"type": "array"}
                    }
                },
                "translation_type": {
                    "type": "string",
                    "enum": ["expression", "complaint", "request", "appreciation"],
                    "description": "翻译类型"
                }
            },
            "required": ["user_id", "target_user_id", "expression"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "translation_result": {
                    "type": "object",
                    "properties": {
                        "original_expression": {"type": "string"},
                        "detected_love_language": {"type": "string"},
                        "love_language_name": {"type": "string"},
                        "true_intention": {"type": "string"},
                        "surface_meaning": {"type": "string"},
                        "deeper_need": {"type": "string"},
                        "suggested_response": {"type": "string"},
                        "response_examples": {"type": "array"},
                        "confidence": {"type": "number"}
                    }
                },
                "generative_ui": {
                    "type": "object",
                    "properties": {
                        "component_type": {"type": "string"},
                        "props": {"type": "object"}
                    }
                },
                "suggested_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "action_type": {"type": "string"},
                            "params": {"type": "object"}
                        }
                    }
                }
            },
            "required": ["success", "ai_message", "translation_result"]
        }

    async def execute(
        self,
        user_id: str,
        target_user_id: str,
        expression: str,
        translation_type: str = "expression",
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行爱之语翻译 Skill

        Args:
            user_id: 表达者 ID
            target_user_id: 接收者 ID
            expression: 需要翻译的表达
            translation_type: 翻译类型
            context: 上下文信息
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"LoveLanguageTranslatorSkill: Executing for user={user_id}, expression='{expression[:30]}...'")

        start_time = datetime.now()

        # Step 1: 分析爱之语类型
        love_language_analysis = self._analyze_love_language(expression)

        # Step 2: 解读真实需求
        need_analysis = self._decode_need(expression, love_language_analysis)

        # Step 3: 生成回应建议
        response_suggestions = self._generate_response_suggestions(
            love_language_analysis,
            need_analysis,
            context
        )

        # Step 4: 构建翻译结果
        translation_result = {
            "original_expression": expression,
            "detected_love_language": love_language_analysis.get("primary_type"),
            "love_language_name": self._get_love_language_name(love_language_analysis.get("primary_type")),
            "true_intention": need_analysis.get("true_intention"),
            "surface_meaning": need_analysis.get("surface_meaning"),
            "deeper_need": need_analysis.get("deeper_need"),
            "suggested_response": response_suggestions.get("primary_suggestion"),
            "response_examples": response_suggestions.get("examples", []),
            "confidence": love_language_analysis.get("confidence", 0)
        }

        # Step 5: 生成自然语言解读
        ai_message = self._generate_message(translation_result, translation_type)

        # Step 6: 构建 Generative UI
        generative_ui = self._build_ui(translation_result)

        # Step 7: 生成建议操作
        suggested_actions = self._generate_actions(translation_result)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "translation_result": translation_result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time),
                "detected_love_language": translation_result.get("detected_love_language")
            }
        }

    def _analyze_love_language(self, expression: str) -> Dict[str, Any]:
        """分析表达中的爱之语类型"""
        detected_types = []
        type_scores = {}

        # 检测每种爱之语的关键词
        for love_type, info in self.LOVE_LANGUAGES.items():
            score = 0
            for keyword in info["keywords"]:
                if keyword in expression:
                    score += 1
                    detected_types.append(love_type)

            if score > 0:
                type_scores[love_type] = score

        # 确定主要类型
        primary_type = max(type_scores, key=type_scores.get) if type_scores else None
        confidence = min(type_scores.get(primary_type, 0) / 3.0, 1.0) if primary_type else 0.3

        return {
            "primary_type": primary_type,
            "detected_types": list(set(detected_types)),
            "type_scores": type_scores,
            "confidence": confidence
        }

    def _decode_need(self, expression: str, love_language_analysis: Dict) -> Dict[str, Any]:
        """解读表面表达背后的真实需求"""
        primary_type = love_language_analysis.get("primary_type")

        # 检查是否匹配需求模式
        if primary_type and primary_type in self.NEED_PATTERNS:
            pattern_info = self.NEED_PATTERNS[primary_type]

            for pattern in pattern_info["surface_patterns"]:
                if re.search(pattern, expression):
                    return {
                        "is_complaint": True,
                        "surface_meaning": self._get_surface_meaning(expression),
                        "true_intention": pattern_info["true_intention"],
                        "deeper_need": self._explain_deeper_need(primary_type),
                        "pattern_matched": pattern
                    }

        # 如果没有匹配到需求模式，进行一般性解读
        return {
            "is_complaint": False,
            "surface_meaning": expression,
            "true_intention": f"表达{self._get_love_language_name(primary_type)}相关的需求",
            "deeper_need": self._explain_deeper_need(primary_type) if primary_type else "希望被理解和关爱"
        }

    def _get_surface_meaning(self, expression: str) -> str:
        """获取表面含义"""
        # 简化实现：直接返回原始表达
        return expression

    def _explain_deeper_need(self, love_type: Optional[str]) -> str:
        """解释深层需求"""
        explanations = {
            "words": "深层需求：希望被肯定、被欣赏、被认可",
            "time": "深层需求：希望被重视、被关注、有归属感",
            "gifts": "深层需求：希望被用心对待、被惦记、有惊喜感",
            "acts": "深层需求：希望被体贴、被照顾、分担压力",
            "touch": "深层需求：希望被接纳、亲密连接、有安全感"
        }
        return explanations.get(love_type, "深层需求：希望被爱、被理解")

    def _generate_response_suggestions(
        self,
        love_language_analysis: Dict,
        need_analysis: Dict,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """生成回应建议"""
        primary_type = love_language_analysis.get("primary_type")

        # 获取建议回应模板
        if primary_type and primary_type in self.NEED_PATTERNS:
            template = self.NEED_PATTERNS[primary_type]["suggested_response"]
            example = self.NEED_PATTERNS[primary_type]["example"]
        else:
            template = "我理解你的感受，让我用你需要的方式爱你"
            example = "谢谢你告诉我你的感受，我想更好地了解你需要什么"

        # 生成具体建议
        suggestions = {
            "primary_suggestion": self._customize_response(template, primary_type, context),
            "examples": [
                example,
                self._generate_alternative_response(primary_type)
            ],
            "do's": self._get_positive_actions(primary_type),
            "don'ts": self._get_negative_actions(primary_type)
        }

        return suggestions

    def _customize_response(self, template: str, love_type: Optional[str], context: Optional[Dict]) -> str:
        """定制回应"""
        # 填充模板中的占位符
        if love_type == "words":
            return template.replace("{quality}", "的善良和体贴").replace("{contribution}", "付出")
        elif love_type == "time":
            return template.replace("{activity}", "周末一起去看电影")
        elif love_type == "acts":
            return template.replace("{task}", "晚饭和家务")
        return template

    def _generate_alternative_response(self, love_type: Optional[str]) -> str:
        """生成替代回应"""
        alternatives = {
            "words": "我可能没有经常表达，但我真的很感激你为这段关系做的一切",
            "time": "让我调整一下时间安排，保证每周都有专属我们的约会时间",
            "gifts": "我会更用心地为你准备小惊喜，让你知道我有多在乎你",
            "acts": "以后这些家务我来分担，你不用一个人承担所有",
            "touch": "来，让我抱抱你。有时候行动比语言更能表达我的爱"
        }
        return alternatives.get(love_type, "我想用你需要的方式爱你，告诉我什么对你最重要")

    def _get_positive_actions(self, love_type: Optional[str]) -> List[str]:
        """获取应该做的事"""
        actions = {
            "words": [
                "每天至少说一次赞美的话",
                "写小纸条表达感谢",
                "公开表达对 TA 的欣赏"
            ],
            "time": [
                "安排每周约会夜",
                "放下手机专心倾听",
                "一起规划未来活动"
            ],
            "gifts": [
                "记住重要纪念日",
                "准备小惊喜",
                "送有意义的礼物"
            ],
            "acts": [
                "主动分担家务",
                "帮 TA 处理烦心事",
                "为 TA 准备早餐"
            ],
            "touch": [
                "每天拥抱",
                "牵手散步",
                "轻拍肩膀表示关心"
            ]
        }
        return actions.get(love_type, ["真诚地表达你的爱"])

    def _get_negative_actions(self, love_type: Optional[str]) -> List[str]:
        """获取应该避免的事"""
        actions = {
            "words": [
                "批评多于赞美",
                "把 TA 的付出视为理所当然",
                "在别人面前说 TA 的坏话"
            ],
            "time": [
                "和 TA 在一起时一直看手机",
                "取消约会",
                "心不在焉地倾听"
            ],
            "gifts": [
                "忘记重要日子",
                "送敷衍的礼物",
                "说'你不配'这类话"
            ],
            "acts": [
                "把家务都推给 TA",
                "说'这不是我的事'",
                "挑剔 TA 做的家务"
            ],
            "touch": [
                "拒绝身体接触",
                "在公共场合保持距离",
                "忽视 TA 的亲密需求"
            ]
        }
        return actions.get(love_type, ["忽视 TA 的感受"])

    def _get_love_language_name(self, love_type: Optional[str]) -> str:
        """获取爱之语中文名称"""
        if not love_type:
            return "未识别"
        return self.LOVE_LANGUAGES.get(love_type, {}).get("name", love_type)

    def _generate_message(self, translation_result: Dict, translation_type: str) -> str:
        """生成自然语言解读"""
        love_language_name = translation_result.get("love_language_name", "未知")
        true_intention = translation_result.get("true_intention", "")
        suggested_response = translation_result.get("suggested_response", "")
        is_complaint = translation_result.get("is_complaint", False)

        if is_complaint:
            message = f"💡 这是一个以「{love_language_name}」为主的表达\n\n"
            message += f"表面意思：「{translation_result.get('surface_meaning', '')}」\n\n"
            message += f"真实需求：{true_intention}\n\n"
            message += f"建议回应：{suggested_response}"
        else:
            message = f"💕 检测到{love_language_name}的表达\n\n"
            message += f"表达内容：「{translation_result.get('original_expression', '')}」\n\n"
            message += f"{translation_result.get('deeper_need', '')}\n\n"
            message += f"回应建议：{suggested_response}"

        return message

    def _build_ui(self, translation_result: Dict) -> Dict[str, Any]:
        """构建 UI"""
        love_language = translation_result.get("detected_love_language")
        love_language_name = translation_result.get("love_language_name")

        return {
            "component_type": "love_language_translation_card",
            "props": {
                "original_expression": translation_result.get("original_expression", ""),
                "love_language": {
                    "type": love_language,
                    "name": love_language_name,
                    "description": self.LOVE_LANGUAGES.get(love_language, {}).get("description", "")
                },
                "true_intention": translation_result.get("true_intention", ""),
                "suggested_response": translation_result.get("suggested_response", ""),
                "examples": translation_result.get("response_examples", []),
                "confidence": translation_result.get("confidence", 0)
            }
        }

    def _generate_actions(self, translation_result: Dict) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []

        # 使用建议回应
        actions.append({
            "label": "使用建议回应",
            "action_type": "use_suggested_response",
            "params": {
                "response": translation_result.get("suggested_response", "")
            }
        })

        # 了解爱之语
        actions.append({
            "label": "了解爱之语理论",
            "action_type": "learn_love_languages",
            "params": {}
        })

        # 测试爱之语
        actions.append({
            "label": "测试我的爱之语",
            "action_type": "take_love_language_quiz",
            "params": {}
        })

        return actions

    async def autonomous_trigger(
        self,
        user_id: str,
        target_user_id: str,
        trigger_type: str,
        expression: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> dict:
        """
        自主触发爱之语翻译

        Args:
            user_id: 用户 ID
            target_user_id: 目标用户 ID
            trigger_type: 触发类型 (complaint_detected, misunderstanding, user_request)
            expression: 表达内容
            context: 上下文信息

        Returns:
            触发结果
        """
        logger.info(f"LoveLanguageTranslatorSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        # 检查触发条件
        should_trigger = False

        if trigger_type == "complaint_detected":
            # 检测到抱怨
            should_trigger = self._is_complaint(expression) if expression else False
        elif trigger_type == "misunderstanding":
            # 检测到误解
            should_trigger = self._is_misunderstanding(context) if context else False
        elif trigger_type == "user_request":
            # 用户主动请求
            should_trigger = True

        if should_trigger and expression:
            result = await self.execute(
                user_id=user_id,
                target_user_id=target_user_id,
                expression=expression,
                context=context
            )
            return {
                "triggered": True,
                "result": result,
                "should_push": result.get("translation_result", {}).get("is_complaint", False)
            }

        return {"triggered": False, "reason": "not_needed"}

    def _is_complaint(self, expression: str) -> bool:
        """判断是否是抱怨"""
        complaint_indicators = [
            "你都不", "你从来不", "你总是", "每次都是",
            "凭什么", "你就不能", "都是我来"
        ]
        return any(indicator in expression for indicator in complaint_indicators)

    def _is_misunderstanding(self, context: Dict) -> bool:
        """判断是否存在误解"""
        # 简化实现
        return context.get("has_misunderstanding", False)


# 全局 Skill 实例
_love_language_translator_skill_instance: Optional[LoveLanguageTranslatorSkill] = None


def get_love_language_translator_skill() -> LoveLanguageTranslatorSkill:
    """获取爱之语翻译 Skill 单例实例"""
    global _love_language_translator_skill_instance
    if _love_language_translator_skill_instance is None:
        _love_language_translator_skill_instance = LoveLanguageTranslatorSkill()
    return _love_language_translator_skill_instance
