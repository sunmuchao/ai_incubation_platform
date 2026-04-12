"""
情感调解 Skill - 吵架预警 + 爱之语翻译 + 关系气象

AI 关系调解员核心 Skill - 争吵检测、爱之语翻译、关系天气报告
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from agent.skills.base import BaseSkill
from utils.logger import logger
import json
import re


class EmotionMediatorSkill(BaseSkill):
    """
    AI 情感调解员 Skill - 化解矛盾，促进理解

    核心能力:
    - 吵架预警（检测争吵升级、提供冷静建议）
    - 爱之语翻译（解读表面话语背后的真实需求）
    - 关系气象报告（生成关系健康度分析）
    - 降温锦囊（提供缓和冲突的具体方法）

    自主触发:
    - 检测到争吵升级模式
    - 负面情绪达到阈值
    - 定期生成关系气象报告
    - 用户主动寻求调解建议
    """

    name = "emotion_mediator"
    version = "1.0.0"
    description = """
    AI 情感调解员，帮助情侣化解矛盾、增进理解

    能力:
    - 吵架预警：检测争吵升级，及时介入
    - 爱之语翻译：解读表面话语背后的真实需求
    - 关系气象报告：定期生成关系健康度分析
    - 降温锦囊：提供缓和冲突的具体方法
    """

    # 预警级别
    LEVEL_LOW = "low"
    LEVEL_MEDIUM = "medium"
    LEVEL_HIGH = "high"
    LEVEL_CRITICAL = "critical"

    # 爱之语类型
    LOVE_LANGUAGES = {
        "words": "肯定的言辞",
        "time": "精心时刻",
        "gifts": "接受礼物",
        "acts": "服务的行动",
        "touch": "身体的接触"
    }

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "对话 ID"
                },
                "user_a_id": {
                    "type": "string",
                    "description": "用户 A ID"
                },
                "user_b_id": {
                    "type": "string",
                    "description": "用户 B ID"
                },
                "service_type": {
                    "type": "string",
                    "enum": ["conflict_detection", "love_language_translation", "weather_report", "calming_suggestions"],
                    "description": "服务类型"
                },
                "expression": {
                    "type": "string",
                    "description": "需要翻译的表达内容"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "relationship_stage": {"type": "string"},
                        "conflict_history": {"type": "array"},
                        "recent_interaction_quality": {"type": "string"}
                    }
                },
                "conversation_history": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "对话历史"
                }
            },
            "required": ["conversation_id", "user_a_id", "user_b_id", "service_type"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "mediation_result": {
                    "type": "object",
                    "properties": {
                        "warning_level": {"type": "string"},
                        "warning_score": {"type": "number"},
                        "detected_issues": {"type": "array"},
                        "love_language_analysis": {"type": "object"},
                        "relationship_weather": {"type": "string"},
                        "calming_suggestions": {"type": "array"}
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
                },
                "alert_triggered": {"type": "boolean"}
            },
            "required": ["success", "ai_message", "mediation_result"]
        }

    async def execute(
        self,
        conversation_id: str,
        user_a_id: str,
        user_b_id: str,
        service_type: str,
        expression: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> dict:
        """
        执行情感调解 Skill

        Args:
            conversation_id: 对话 ID
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            service_type: 服务类型
            expression: 需要翻译的表达
            context: 上下文信息
            conversation_history: 对话历史
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"EmotionMediatorSkill: Executing for conversation={conversation_id}, type={service_type}")

        start_time = datetime.now()

        # Step 1: 根据服务类型执行相应分析
        mediation_result = await self._perform_mediation(
            service_type=service_type,
            conversation_id=conversation_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            expression=expression,
            conversation_history=conversation_history,
            context=context
        )

        # Step 2: 生成自然语言响应
        ai_message = self._generate_message(mediation_result, service_type)

        # Step 3: 构建 Generative UI
        generative_ui = self._build_ui(mediation_result, service_type)

        # Step 4: 生成建议操作
        suggested_actions = self._generate_actions(mediation_result, service_type)

        # Step 5: 检查是否需要预警
        alert_info = self._check_alert(mediation_result)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "mediation_result": mediation_result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "alert_triggered": alert_info.get("triggered", False),
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time),
                "service_type": service_type
            }
        }

    async def _perform_mediation(
        self,
        service_type: str,
        conversation_id: str,
        user_a_id: str,
        user_b_id: str,
        expression: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """执行调解分析"""
        from db.database import SessionLocal
        from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
        from services.emotion_mediation_service import emotion_mediation_service

        db = SessionLocal()
        result = {
            "warning_level": None,
            "warning_score": 0,
            "detected_issues": [],
            "love_language_analysis": None,
            "relationship_weather": None,
            "calming_suggestions": []
        }

        try:
            if service_type == "conflict_detection":
                # 争吵检测
                if conversation_history:
                    warning_info = self._detect_conflict(conversation_history)
                    result["warning_level"] = warning_info.get("level")
                    result["warning_score"] = warning_info.get("score")
                    result["detected_issues"] = warning_info.get("issues", [])
                    result["calming_suggestions"] = warning_info.get("suggestions", [])

            elif service_type == "love_language_translation" and expression:
                # 爱之语翻译
                translation = self._translate_love_language(
                    expression=expression,
                    user_id=user_a_id,
                    target_user_id=user_b_id,
                    context=context
                )
                result["love_language_analysis"] = translation

            elif service_type == "weather_report":
                # 关系气象报告
                weather = self._generate_weather_report(
                    user_a_id=user_a_id,
                    user_b_id=user_b_id,
                    conversation_history=conversation_history,
                    context=context
                )
                result["relationship_weather"] = weather

            elif service_type == "calming_suggestions":
                # 降温建议
                suggestions = self._generate_calming_suggestions(
                    conversation_history=conversation_history,
                    context=context
                )
                result["calming_suggestions"] = suggestions

            return result

        except Exception as e:
            logger.error(f"EmotionMediatorSkill: Mediation failed: {e}")
            return result
        finally:
            db.close()

    def _detect_conflict(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """检测争吵升级"""
        # 负面情绪关键词
        NEGATIVE_KEYWORDS = {
            "anger": ["生气", "愤怒", "烦", "讨厌", "恨", "滚", "闭嘴", "够了", "受不了"],
            "frustration": ["失望", "无奈", "算了", "随便", "无所谓", "呵呵"],
            "sadness": ["难过", "伤心", "委屈", "哭", "泪", "心痛", "受伤"],
            "defensiveness": ["又不是我", "你才", "你总是", "你从来", "凭什么"],
            "contempt": ["真可笑", "呵呵", "就你", "也不看看自己", "拜托"]
        }

        # 升级模式
        ESCALATION_PATTERNS = [
            r"你总是.*",
            r"你从来.*",
            r"每次都是.*",
            r"就不能.*吗",
            r"有必要.*吗"
        ]

        issues = []
        emotion_counts = defaultdict(int)
        intensity = 0.0

        # 分析最近消息
        for msg in conversation_history[-20:]:
            content = msg.get("content", "")

            # 检测负面情绪
            for emotion, keywords in NEGATIVE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in content:
                        emotion_counts[emotion] += 1
                        intensity += 0.1

            # 检测升级模式
            for pattern in ESCALATION_PATTERNS:
                if re.search(pattern, content):
                    issues.append(f"升级模式：{content[:20]}...")
                    intensity += 0.15

            # 检测感叹号/问号（情绪强度）
            intensity += content.count('!') * 0.05 + content.count('?') * 0.03

        # 限制强度
        intensity = min(intensity, 1.0)

        # 确定预警级别
        if intensity >= 0.8:
            level = self.LEVEL_CRITICAL
        elif intensity >= 0.6:
            level = self.LEVEL_HIGH
        elif intensity >= 0.4:
            level = self.LEVEL_MEDIUM
        elif intensity >= 0.2:
            level = self.LEVEL_LOW
        else:
            level = None

        # 生成降温建议
        suggestions = self._generate_calming_suggestions_based_on_emotions(
            emotion_counts=emotion_counts,
            level=level
        )

        return {
            "level": level,
            "score": intensity,
            "issues": issues[:5],
            "emotion_counts": dict(emotion_counts),
            "suggestions": suggestions
        }

    def _translate_love_language(
        self,
        expression: str,
        user_id: str,
        target_user_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """翻译爱之语表达"""
        # 爱之语模式
        EXPRESSION_PATTERNS = {
            "words": [r"喜欢.*你", r"爱.*你", r"你.*好", r"欣赏", r"赞美", r"谢谢", r"感谢"],
            "time": [r"一起", r"陪伴", r"时间", r"见面", r"约会", r"聊天"],
            "gifts": [r"送.*你", r"礼物", r"买.*给", r"准备.*惊喜", r"收到"],
            "acts": [r"帮你", r"为你", r"替你", r"帮忙", r"照顾", r"处理"],
            "touch": [r"拥抱", r"牵手", r"亲吻", r"摸", r"靠", r"抱抱"]
        }

        # 需求模式
        NEED_PATTERNS = {
            "words": {
                "patterns": [r"你都不.*我", r"你从来不.*我"],
                "true_intention": "希望得到更多的肯定和赞美",
                "response_template": "我真的很欣赏你{quality}，谢谢你一直以来的{contribution}"
            },
            "time": {
                "patterns": [r"你总是.*忙", r"你都没时间.*我"],
                "true_intention": "渴望更多的陪伴和关注",
                "response_template": "你说得对，我确实应该花更多时间陪你。我们{activity}怎么样？"
            },
            "gifts": {
                "patterns": [r"你都不.*惊喜", r"别人都有.*礼物"],
                "true_intention": "希望被重视和用心对待",
                "response_template": "我想为你准备一个惊喜"
            },
            "acts": {
                "patterns": [r"都是.*我做", r"你从来不.*家务"],
                "true_intention": "希望分担和体贴",
                "response_template": "我来处理{task}吧，你休息一下"
            },
            "touch": {
                "patterns": [r"你都不.*抱我", r"我们好久没.*亲密"],
                "true_intention": "渴望身体接触和亲密感",
                "response_template": "过来让我抱抱你"
            }
        }

        # 检测表达类型
        detected_types = []
        for love_type, patterns in EXPRESSION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, expression):
                    detected_types.append(love_type)
                    break

        # 检测潜在需求
        need_analysis = None
        for love_type, need_info in NEED_PATTERNS.items():
            for pattern in need_info["patterns"]:
                if re.search(pattern, expression):
                    need_analysis = {
                        "surface_expression": expression,
                        "true_intention": need_info["true_intention"],
                        "love_language": self.LOVE_LANGUAGES.get(love_type, love_type),
                        "suggested_response": need_info["response_template"]
                    }
                    break
            if need_analysis:
                break

        return {
            "expression": expression,
            "detected_love_languages": detected_types,
            "primary_love_language": detected_types[0] if detected_types else None,
            "need_analysis": need_analysis,
            "interpretation": self._generate_love_language_interpretation(detected_types, need_analysis)
        }

    def _generate_love_language_interpretation(
        self,
        detected_types: List[str],
        need_analysis: Optional[Dict]
    ) -> str:
        """生成爱之语解读"""
        if need_analysis:
            return f"表面表达：「{need_analysis['surface_expression']}」\n" \
                   f"真实需求：{need_analysis['true_intention']}\n" \
                   f"爱之语类型：{need_analysis['love_language']}"

        if detected_types:
            types_cn = [self.LOVE_LANGUAGES.get(t, t) for t in detected_types]
            return f"这是一个以{types_cn[0]}为主的爱的表达"

        return "请继续真诚地表达你的感受"

    def _generate_weather_report(
        self,
        user_a_id: str,
        user_b_id: str,
        conversation_history: Optional[List[Dict]],
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """生成关系气象报告"""
        # 简化实现：基于对话历史分析关系状态
        if not conversation_history:
            return {
                "weather": "unknown",
                "temperature": 50,
                "description": "暂无足够数据生成关系报告",
                "trend": "stable"
            }

        # 分析情感倾向
        positive_count = 0
        negative_count = 0

        POSITIVE_WORDS = ["喜欢", "爱", "开心", "快乐", "幸福", "温暖", "感动", "谢谢", "辛苦了"]
        NEGATIVE_WORDS = ["生气", "烦", "讨厌", "难过", "失望", "算了", "随便", "呵呵"]

        for msg in conversation_history[-50:]:
            content = msg.get("content", "")
            for word in POSITIVE_WORDS:
                if word in content:
                    positive_count += 1
            for word in NEGATIVE_WORDS:
                if word in content:
                    negative_count += 1

        # 计算关系温度
        total = positive_count + negative_count
        if total > 0:
            temperature = 50 + (positive_count - negative_count) / total * 50
        else:
            temperature = 50

        # 确定天气
        if temperature >= 80:
            weather = "sunny"
            weather_cn = "晴朗"
        elif temperature >= 60:
            weather = "cloudy"
            weather_cn = "多云"
        elif temperature >= 40:
            weather = "overcast"
            weather_cn = "阴天"
        elif temperature >= 20:
            weather = "rainy"
            weather_cn = "小雨"
        else:
            weather = "stormy"
            weather_cn = "暴风雨"

        # 趋势
        recent_positive = sum(1 for msg in conversation_history[-10:] if any(w in msg.get("content", "") for w in POSITIVE_WORDS))
        recent_negative = sum(1 for msg in conversation_history[-10:] if any(w in msg.get("content", "") for w in NEGATIVE_WORDS))

        if recent_positive > recent_negative + 2:
            trend = "improving"
            trend_cn = "升温"
        elif recent_negative > recent_positive + 2:
            trend = "declining"
            trend_cn = "降温"
        else:
            trend = "stable"
            trend_cn = "稳定"

        return {
            "weather": weather,
            "weather_cn": weather_cn,
            "temperature": round(temperature, 1),
            "description": f"当前关系{weather_cn}，温度{temperature:.1f}°C",
            "trend": trend,
            "trend_cn": trend_cn,
            "positive_count": positive_count,
            "negative_count": negative_count
        }

    def _generate_calming_suggestions(
        self,
        conversation_history: Optional[List[Dict]],
        context: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """生成降温建议"""
        suggestions = []

        # 基础建议
        base_suggestions = [
            {
                "type": "pause",
                "title": "暂停对话",
                "content": "暂时离开一下，给自己和对方冷静的时间",
                "urgency": "high"
            },
            {
                "type": "breathe",
                "title": "深呼吸练习",
                "content": "做 3 次深呼吸，吸气 4 秒，屏息 4 秒，呼气 6 秒",
                "urgency": "medium"
            },
            {
                "type": "perspective",
                "title": "换位思考",
                "content": "试着从对方的角度理解这个问题",
                "urgency": "low"
            },
            {
                "type": "express",
                "title": "使用「我」陈述",
                "content": "用「我感到...」代替「你总是...」来表达",
                "urgency": "medium"
            },
            {
                "type": "listen",
                "title": "积极倾听",
                "content": "先听完对方的话，不要打断或辩解",
                "urgency": "medium"
            }
        ]

        # 根据情绪类型调整
        if conversation_history:
            emotions = self._detect_conflict(conversation_history).get("emotion_counts", {})

            if emotions.get("anger", 0) > 2:
                suggestions.append({
                    "type": "anger_management",
                    "title": "愤怒管理",
                    "content": "愤怒时不要做决定或说狠话，先冷静 20 分钟",
                    "urgency": "high"
                })

            if emotions.get("sadness", 0) > 2:
                suggestions.append({
                    "type": "comfort",
                    "title": "安慰方式",
                    "content": "给对方一个拥抱，或者安静地陪伴",
                    "urgency": "medium"
                })

        return suggestions + base_suggestions[:3]

    def _generate_calming_suggestions_based_on_emotions(
        self,
        emotion_counts: Dict[str, int],
        level: Optional[str]
    ) -> List[Dict[str, Any]]:
        """根据情绪生成降温建议"""
        suggestions = []

        if level in [self.LEVEL_HIGH, self.LEVEL_CRITICAL]:
            suggestions.append({
                "type": "immediate_pause",
                "title": "立即暂停",
                "content": "⚠️ 检测到激烈情绪，建议立即暂停对话，冷静 20 分钟",
                "urgency": "critical"
            })

        if emotion_counts.get("anger", 0) > 0:
            suggestions.append({
                "type": "anger_cooling",
                "title": "冷静愤怒",
                "content": "愤怒时说的话往往会后悔。深呼吸，数到 10 再回应。",
                "urgency": "high"
            })

        if emotion_counts.get("contempt", 0) > 0:
            suggestions.append({
                "type": "respect_reminder",
                "title": "尊重提醒",
                "content": "轻蔑是关系的毒药。试着用尊重的方式表达不同意见。",
                "urgency": "high"
            })

        if emotion_counts.get("defensiveness", 0) > 0:
            suggestions.append({
                "type": "ownership",
                "title": "承担责任",
                "content": "尝试承认自己的部分责任，而不是完全防御。",
                "urgency": "medium"
            })

        return suggestions

    def _generate_message(self, mediation_result: Dict, service_type: str) -> str:
        """生成自然语言响应"""
        if service_type == "conflict_detection":
            level = mediation_result.get("warning_level")
            issues = mediation_result.get("detected_issues", [])

            if not level:
                return "对话氛围良好，继续保持~\n"

            message = f"⚠️ 检测到关系紧张，预警级别：{self._translate_level(level)}\n"
            if issues:
                message += f"\n检测到的问题：\n"
                for issue in issues[:3]:
                    message += f"- {issue}\n"

            suggestions = mediation_result.get("calming_suggestions", [])
            if suggestions:
                message += f"\n建议：\n"
                for sug in suggestions[:2]:
                    message += f"- {sug['title']}: {sug['content']}\n"

            return message

        elif service_type == "love_language_translation":
            analysis = mediation_result.get("love_language_analysis")
            if not analysis:
                return "无法分析该表达的爱之语类型"

            interpretation = analysis.get("interpretation", "")
            need = analysis.get("need_analysis")

            message = f"{interpretation}\n"
            if need:
                message += f"\n真实需求：{need['true_intention']}\n"
                message += f"建议回应：{need['response_template']}"

            return message

        elif service_type == "weather_report":
            weather = mediation_result.get("relationship_weather")
            if not weather:
                return "暂无足够数据生成关系报告"

            message = f"关系气象报告：{weather.get('description')}\n"
            message += f"趋势：{weather.get('trend_cn', '稳定')}\n"
            message += f"\n小贴士：保持积极互动，让关系更加温暖~"

            return message

        elif service_type == "calming_suggestions":
            suggestions = mediation_result.get("calming_suggestions", [])
            message = "降温建议：\n"
            for sug in suggestions[:4]:
                message += f"- {sug['title']}: {sug['content']}\n"
            return message

        return "情感调解服务已就绪"

    def _translate_level(self, level: str) -> str:
        """翻译预警级别"""
        translation = {
            self.LEVEL_LOW: "低",
            self.LEVEL_MEDIUM: "中",
            self.LEVEL_HIGH: "高",
            self.LEVEL_CRITICAL: "严重"
        }
        return translation.get(level, level)

    def _build_ui(self, mediation_result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        if service_type == "conflict_detection":
            level = mediation_result.get("warning_level")
            return {
                "component_type": "conflict_meter",
                "props": {
                    "level": level,
                    "score": mediation_result.get("warning_score", 0),
                    "issues": mediation_result.get("detected_issues", [])[:3],
                    "suggestions": mediation_result.get("calming_suggestions", [])[:3]
                }
            }

        elif service_type == "love_language_translation":
            analysis = mediation_result.get("love_language_analysis")
            return {
                "component_type": "love_language_card",
                "props": {
                    "expression": analysis.get("expression") if analysis else "",
                    "love_languages": analysis.get("detected_love_languages") if analysis else [],
                    "interpretation": analysis.get("interpretation") if analysis else ""
                }
            }

        elif service_type == "weather_report":
            weather = mediation_result.get("relationship_weather")
            return {
                "component_type": "relationship_weather",
                "props": {
                    "weather": weather.get("weather") if weather else "unknown",
                    "temperature": weather.get("temperature", 50),
                    "trend": weather.get("trend") if weather else "stable"
                }
            }

        return {"component_type": "mediation_empty", "props": {}}

    def _generate_actions(self, mediation_result: Dict, service_type: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []

        if service_type == "conflict_detection":
            actions.append({
                "label": "启动冷静模式",
                "action_type": "start_calm_mode",
                "params": {}
            })
            actions.append({
                "label": "获取专业建议",
                "action_type": "request_coach_help",
                "params": {}
            })

        elif service_type == "love_language_translation":
            actions.append({
                "label": "使用建议回应",
                "action_type": "use_suggested_response",
                "params": {}
            })
            actions.append({
                "label": "了解爱之语",
                "action_type": "learn_love_languages",
                "params": {}
            })

        elif service_type == "weather_report":
            actions.append({
                "label": "查看详细报告",
                "action_type": "view_full_weather_report",
                "params": {}
            })
            actions.append({
                "label": "获取关系建议",
                "action_type": "get_relationship_advice",
                "params": {}
            })

        return actions

    def _check_alert(self, mediation_result: Dict) -> Dict[str, Any]:
        """检查是否需要触发警报"""
        level = mediation_result.get("warning_level")
        if level in [self.LEVEL_HIGH, self.LEVEL_CRITICAL]:
            return {
                "triggered": True,
                "level": level
            }
        return {"triggered": False}

    async def autonomous_trigger(
        self,
        conversation_id: str,
        user_a_id: str,
        user_b_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """
        自主触发情感调解

        Args:
            conversation_id: 对话 ID
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            trigger_type: 触发类型 (conflict_detected, negative_spiral, periodic_check)
            context: 上下文信息

        Returns:
            触发结果
        """
        logger.info(f"EmotionMediatorSkill: Autonomous trigger for conversation={conversation_id}, type={trigger_type}")

        # 获取对话历史
        from db.database import SessionLocal
        from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
        from db.models import ChatMessageDB

        db = SessionLocal()
        try:
            messages = db.query(ChatMessageDB).filter(
                ChatMessageDB.conversation_id == conversation_id
            ).order_by(ChatMessageDB.created_at.desc()).limit(30).all()

            conversation_history = [
                {"content": m.content, "sender_id": m.sender_id, "created_at": m.created_at}
                for m in messages
            ][::-1]

            # 判断是否需要触发
            should_trigger = False
            if trigger_type == "conflict_detected":
                conflict_info = self._detect_conflict(conversation_history)
                should_trigger = conflict_info.get("level") in [self.LEVEL_HIGH, self.LEVEL_CRITICAL]
            elif trigger_type == "negative_spiral":
                # 检测负面螺旋
                pass
            elif trigger_type == "periodic_check":
                # 定期检查
                should_trigger = True

            if should_trigger:
                result = await self.execute(
                    conversation_id=conversation_id,
                    user_a_id=user_a_id,
                    user_b_id=user_b_id,
                    service_type="conflict_detection",
                    conversation_history=conversation_history,
                    context=context
                )
                return {
                    "triggered": True,
                    "result": result,
                    "should_push": result.get("alert_triggered", False)
                }

            return {"triggered": False, "reason": "not_needed"}

        finally:
            db.close()


# 全局 Skill 实例
_emotion_mediator_skill_instance: Optional[EmotionMediatorSkill] = None


def get_emotion_mediator_skill() -> EmotionMediatorSkill:
    """获取情感调解 Skill 单例实例"""
    global _emotion_mediator_skill_instance
    if _emotion_mediator_skill_instance is None:
        _emotion_mediator_skill_instance = EmotionMediatorSkill()
    return _emotion_mediator_skill_instance
