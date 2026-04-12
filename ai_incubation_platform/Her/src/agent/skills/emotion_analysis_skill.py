"""
情感分析 Skill - AI 视频面诊

AI 情感翻译官核心 Skill - 微表情捕捉、语音情感分析、情感报告生成
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger
import json


class EmotionAnalysisSkill:
    """
    AI 情感翻译官 Skill - 实时解读 TA 的情绪

    核心能力:
    - 微表情捕捉与解读（7 种基础情绪 + 8 种社交情绪）
    - 语音情感分析（语调、语速、颤抖检测）
    - 多模态情感融合（面部 + 语音）
    - 生成情感报告与自然语言解读

    自主触发:
    - 视频约会中检测到情绪波动
    - 语音异常（紧张/焦虑/颤抖）
    - 情感一致性检测（言行不一）
    """

    name = "emotion_translator"
    version = "1.0.0"
    description = """
    AI 情感翻译官，实时解读 TA 的微表情和语音情绪

    能力:
    - 微表情捕捉：识别 7 种基础情绪（喜、怒、哀、惧、惊、厌、蔑）
    - 语音情感分析：检测紧张、焦虑、兴奋等状态
    - 多模态融合：综合面部 + 语音 + 上下文生成情感报告
    - 自主预警：检测到异常情绪时主动提醒
    """

    # 支持的情感列表
    SUPPORTED_EMOTIONS = [
        "happiness", "sadness", "anger", "fear", "surprise", "disgust", "contempt",
        "nervousness", "excitement", "confidence", "comfort", "interest",
        "boredom", "attraction", "repulsion"
    ]

    # 微表情到情感的映射
    MICRO_EXPRESSION_TO_EMOTION = {
        "genuine_smile": "happiness",
        "tight_lips": "nervousness",
        "raised_eyebrows": "surprise",
        "furrowed_brow": "anger",
        "lip_corner_pull": "attraction",
        "nose_wrinkle": "disgust",
        "eye_avoidance": "discomfort",
        "prolonged_eye_contact": "interest"
    }

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话 ID（视频约会/语音通话）"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["micro_expression", "voice_emotion", "combined"],
                    "description": "分析类型"
                },
                "facial_data": {
                    "type": "object",
                    "description": "面部识别数据（action_units, landmarks 等）"
                },
                "voice_data": {
                    "type": "object",
                    "description": "语音特征数据（pitch, volume, speech_rate 等）"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "partner_id": {"type": "string"},
                        "conversation_topic": {"type": "string"},
                        "relationship_stage": {"type": "string"}
                    }
                }
            },
            "required": ["session_id", "analysis_type"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "analysis_result": {
                    "type": "object",
                    "properties": {
                        "dominant_emotion": {"type": "string"},
                        "emotion_confidence": {"type": "number"},
                        "emotional_intensity": {"type": "number"},
                        "detected_emotions": {"type": "array"},
                        "authenticity_score": {"type": "number"},
                        "ai_insights": {"type": "string"}
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
                "alert_triggered": {"type": "boolean"},
                "alert_level": {"type": "string"}
            },
            "required": ["success", "ai_message", "analysis_result"]
        }

    async def execute(
        self,
        session_id: str,
        analysis_type: str = "combined",
        facial_data: Optional[Dict[str, Any]] = None,
        voice_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行情感分析 Skill

        Args:
            session_id: 会话 ID
            analysis_type: 分析类型 (micro_expression, voice_emotion, combined)
            facial_data: 面部识别数据
            voice_data: 语音特征数据
            context: 上下文信息
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"EmotionAnalysisSkill: Executing for session={session_id}, type={analysis_type}")

        start_time = datetime.now()
        user_id = context.get("user_id") if context else "unknown"

        # Step 1: 执行情感分析
        analysis_result = await self._analyze_emotion(
            session_id=session_id,
            analysis_type=analysis_type,
            facial_data=facial_data,
            voice_data=voice_data,
            user_id=user_id
        )

        # Step 2: 检测是否需要预警
        alert_info = self._check_alert_needed(analysis_result)

        # Step 3: 生成自然语言解读
        ai_message = self._generate_interpretation(analysis_result, context)

        # Step 4: 构建 Generative UI（情绪曲线图）
        generative_ui = self._build_emotion_ui(analysis_result)

        # Step 5: 生成建议操作
        suggested_actions = self._generate_actions(analysis_result, alert_info)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "analysis_result": analysis_result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "alert_triggered": alert_info.get("triggered", False),
            "alert_level": alert_info.get("level"),
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time),
                "analysis_type": analysis_type
            }
        }

    async def _analyze_emotion(
        self,
        session_id: str,
        analysis_type: str,
        facial_data: Optional[Dict] = None,
        voice_data: Optional[Dict] = None,
        user_id: str = "unknown"
    ) -> Dict[str, Any]:
        """执行情感分析"""
        from db.database import SessionLocal
        from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
        from services.emotion_analysis_service import emotion_analysis_service

        db = SessionLocal()
        result = {
            "dominant_emotion": None,
            "emotion_confidence": 0,
            "emotional_intensity": 0,
            "detected_emotions": [],
            "authenticity_score": 0,
            "ai_insights": ""
        }

        try:
            if analysis_type in ["micro_expression", "combined"] and facial_data:
                # 微表情分析
                analysis_id = emotion_analysis_service.analyze_micro_expression(
                    user_id=user_id,
                    session_id=session_id,
                    facial_data=facial_data,
                    db_session_param=db
                )
                # 从数据库获取分析结果
                from models.emotion_analysis_models import EmotionAnalysisDB
                analysis = db.query(EmotionAnalysisDB).filter(EmotionAnalysisDB.id == analysis_id).first()
                if analysis:
                    result["dominant_emotion"] = analysis.combined_emotion
                    result["emotion_confidence"] = analysis.emotion_confidence
                    result["ai_insights"] = analysis.ai_insights or ""

            if analysis_type in ["voice_emotion", "combined"] and voice_data:
                # 语音情感分析
                analysis_id = emotion_analysis_service.analyze_voice_emotion(
                    user_id=user_id,
                    session_id=session_id,
                    voice_data=voice_data,
                    db_session_param=db
                )
                # 合并结果
                from models.emotion_analysis_models import EmotionAnalysisDB
                analysis = db.query(EmotionAnalysisDB).filter(EmotionAnalysisDB.id == analysis_id).first()
                if analysis:
                    if not result["dominant_emotion"]:
                        result["dominant_emotion"] = analysis.combined_emotion
                    result["emotion_confidence"] = max(result["emotion_confidence"], analysis.emotion_confidence or 0)

            # 填充检测结果
            result["detected_emotions"] = self._extract_detected_emotions(facial_data, voice_data)
            result["emotional_intensity"] = self._calculate_intensity(result["detected_emotions"])
            result["authenticity_score"] = self._calculate_authenticity(facial_data) if facial_data else 0.8

            return result

        except Exception as e:
            logger.error(f"EmotionAnalysisSkill: Analysis failed: {e}")
            # 返回默认结果
            return result
        finally:
            db.close()

    def _extract_detected_emotions(
        self,
        facial_data: Optional[Dict],
        voice_data: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """提取检测到的情感列表"""
        emotions = []

        # 从面部数据提取
        if facial_data and "action_units" in facial_data:
            for au in facial_data.get("action_units", []):
                if au.get("emotion") in self.MICRO_EXPRESSION_TO_EMOTION.values():
                    emotions.append({
                        "emotion": au["emotion"],
                        "confidence": au.get("confidence", 0.5),
                        "source": "facial"
                    })

        # 从语音数据提取
        if voice_data:
            if voice_data.get("tremor", False):
                emotions.append({"emotion": "nervousness", "confidence": 0.7, "source": "voice"})
            if voice_data.get("volume", 50) > 80:
                emotions.append({"emotion": "excitement", "confidence": 0.6, "source": "voice"})
            if voice_data.get("speech_rate", 150) < 100:
                emotions.append({"emotion": "sadness", "confidence": 0.5, "source": "voice"})

        return emotions

    def _calculate_intensity(self, emotions: List[Dict]) -> float:
        """计算情感强度"""
        if not emotions:
            return 0
        return sum(e.get("confidence", 0) for e in emotions) / len(emotions)

    def _calculate_authenticity(self, facial_data: Optional[Dict]) -> float:
        """计算真实性评分（基于微笑的真诚度）"""
        if not facial_data:
            return 0.8

        # 检测真诚微笑（Duchenne smile）：眼轮匝肌 + 颧大肌同时激活
        action_units = facial_data.get("action_units", [])
        has_eye_crinkle = any(au.get("code") == "AU6" for au in action_units)
        has_mouth_lift = any(au.get("code") == "AU12" for au in action_units)

        if has_eye_crinkle and has_mouth_lift:
            return 0.95  # 真诚微笑
        elif has_mouth_lift:
            return 0.6  # 社交性微笑
        return 0.8

    def _check_alert_needed(self, analysis_result: Dict) -> Dict[str, Any]:
        """检查是否需要触发预警"""
        dominant = analysis_result.get("dominant_emotion")
        confidence = analysis_result.get("emotion_confidence", 0)
        intensity = analysis_result.get("emotional_intensity", 0)

        # 高置信度的负面情绪触发预警
        negative_emotions = ["anger", "fear", "disgust", "contempt", "sadness"]
        if dominant in negative_emotions and confidence > 0.8 and intensity > 0.7:
            return {
                "triggered": True,
                "level": "high",
                "reason": f"检测到强烈的{self._translate_emotion(dominant)}情绪"
            }

        # 紧张/焦虑触发中等级别预警
        if dominant in ["nervousness", "fear"] and confidence > 0.7:
            return {
                "triggered": True,
                "level": "medium",
                "reason": "检测到紧张或焦虑情绪"
            }

        return {"triggered": False, "level": None}

    def _generate_interpretation(self, analysis_result: Dict, context: Optional[Dict]) -> str:
        """生成自然语言情感解读"""
        dominant = analysis_result.get("dominant_emotion", "unknown")
        confidence = analysis_result.get("emotion_confidence", 0) * 100
        intensity = analysis_result.get("emotional_intensity", 0) * 100
        insights = analysis_result.get("ai_insights", "")

        emotion_cn = self._translate_emotion(dominant)

        # 基础解读
        message = f"检测到{emotion_cn}情绪，置信度{confidence:.0f}%，强度{intensity:.0f}%。\n"

        # 添加 AI 洞察
        if insights:
            message += f"\nAI 洞察：{insights}\n"

        # 根据情绪类型添加建议
        if dominant == "happiness":
            message += "\nTA 现在心情很好，是深入交流的好时机！"
        elif dominant == "nervousness":
            message += "\nTA 似乎有些紧张，可以聊些轻松的话题缓解气氛。"
        elif dominant == "anger":
            message += "\n注意：TA 可能感到不悦，建议放慢节奏，避免敏感话题。"
        elif dominant == "sadness":
            message += "\nTA 情绪低落，给予倾听和支持会让关系更亲近。"
        elif dominant == "attraction":
            message += "\nTA 对你表现出兴趣信号，可以继续当前互动！"

        return message

    def _build_emotion_ui(self, analysis_result: Dict) -> Dict[str, Any]:
        """构建情感分析 UI"""
        emotions = analysis_result.get("detected_emotions", [])

        if not emotions:
            return {
                "component_type": "emotion_empty",
                "props": {"message": "暂无情感数据"}
            }

        # 情绪雷达图
        return {
            "component_type": "emotion_radar",
            "props": {
                "emotions": [
                    {"name": self._translate_emotion(e["emotion"]), "value": e["confidence"]}
                    for e in emotions[:5]  # 最多显示 5 种情绪
                ],
                "dominant_emotion": self._translate_emotion(analysis_result.get("dominant_emotion", "unknown")),
                "intensity": analysis_result.get("emotional_intensity", 0)
            }
        }

    def _generate_actions(self, analysis_result: Dict, alert_info: Dict) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []
        dominant = analysis_result.get("dominant_emotion")

        # 如果有预警，添加处理建议
        if alert_info.get("triggered"):
            if alert_info["level"] == "high":
                actions.append({
                    "label": "启动冷静对话",
                    "action_type": "start_calm_conversation",
                    "params": {"emotion": dominant}
                })
                actions.append({
                    "label": "寻求红娘建议",
                    "action_type": "request_coach_help",
                    "params": {}
                })
            else:
                actions.append({
                    "label": "切换轻松话题",
                    "action_type": "change_topic",
                    "params": {"tone": "relaxed"}
                })

        # 根据情绪类型添加操作
        if dominant == "happiness":
            actions.append({
                "label": "发起约会邀请",
                "action_type": "suggest_date",
                "params": {}
            })
        elif dominant == "attraction" or dominant == "interest":
            actions.append({
                "label": "加深互动",
                "action_type": "deepen_interaction",
                "params": {}
            })

        # 默认操作
        actions.append({
            "label": "查看详细报告",
            "action_type": "view_full_report",
            "params": {}
        })

        return actions

    def _translate_emotion(self, emotion: str) -> str:
        """将英文情感翻译成中文"""
        translation = {
            "happiness": "开心",
            "sadness": "悲伤",
            "anger": "愤怒",
            "fear": "恐惧",
            "surprise": "惊讶",
            "disgust": "厌恶",
            "contempt": "轻蔑",
            "nervousness": "紧张",
            "excitement": "兴奋",
            "confidence": "自信",
            "comfort": "舒适",
            "interest": "兴趣",
            "boredom": "无聊",
            "attraction": "吸引",
            "repulsion": "排斥",
            "discomfort": "不适"
        }
        return translation.get(emotion, emotion)

    async def autonomous_trigger(
        self,
        user_id: str,
        session_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """
        自主触发情感分析

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            trigger_type: 触发类型 (emotion_spike, anomaly_detected, relationship_tension)
            context: 上下文信息

        Returns:
            触发结果
        """
        logger.info(f"EmotionAnalysisSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        # 检查触发条件
        if trigger_type == "emotion_spike":
            # 情绪突增检测
            pass  # 从实时流检测
        elif trigger_type == "anomaly_detected":
            # 异常检测（言行不一）
            pass
        elif trigger_type == "relationship_tension":
            # 关系紧张期（基于历史数据）
            pass

        # 执行分析
        result = await self.execute(
            session_id=session_id,
            analysis_type="combined",
            context={**context, "user_id": user_id} if context else {"user_id": user_id}
        )

        if result.get("alert_triggered"):
            # 需要推送预警
            return {
                "triggered": True,
                "result": result,
                "should_push": True,
                "alert_level": result.get("alert_level")
            }

        return {"triggered": False, "result": result}

    async def analyze_text_emotion(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析文本情绪（AI 驱动）

        统一的文本情绪分析方法，替代硬编码的关键词匹配。

        Args:
            text: 待分析的文本内容
            context: 上下文信息（对话历史、用户信息等）

        Returns:
            {
                "emotion": str,           # 主要情绪：happiness/sadness/anger/fear/neutral
                "mood": str,              # 心情倾向：positive/negative/neutral
                "confidence": float,      # 置信度 0-1
                "intensity": float,       # 情绪强度 0-1
                "secondary_emotions": [], # 次要情绪列表
                "ai_insights": str,       # AI 洞察（可选）
            }
        """
        logger.info(f"EmotionAnalysisSkill: Analyzing text emotion, length={len(text)}")

        # 尝试 AI 分析
        ai_result = await self._analyze_text_with_ai(text, context)
        if ai_result:
            return ai_result

        # 降级：基于规则的简单分析（仅作为 fallback）
        return self._analyze_text_fallback(text)

    async def _analyze_text_with_ai(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """使用 AI 分析文本情绪"""
        try:
            from services.llm_semantic_service import get_llm_semantic_service

            llm_service = get_llm_semantic_service()
            if not llm_service.enabled:
                return None

            prompt = f'''分析以下文本的情绪状态，返回 JSON 格式结果。

文本内容：{text}

返回格式：
{{
    "emotion": "happiness/sadness/anger/fear/surprise/neutral",
    "mood": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "intensity": 0.0-1.0,
    "secondary_emotions": [],
    "insights": "简短的情绪洞察（可选）"
}}

分析要点：
1. emotion 是主要情绪类型
2. mood 是情绪的整体倾向（正面/负面/中性）
3. confidence 是分析的确定程度
4. intensity 是情绪的强烈程度
5. secondary_emotions 是同时存在的其他情绪

只返回 JSON，不要其他内容。'''

            # 直接 await 异步调用（当前已在异步上下文中）
            response = await llm_service._call_llm(prompt)

            if response and not response.startswith('{"fallback"'):
                return self._parse_emotion_response(response)

            return None

        except Exception as e:
            logger.debug(f"EmotionAnalysisSkill: AI text analysis failed: {e}")
            return None

    def _parse_emotion_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 AI 返回的情绪 JSON"""
        import re

        # 清理响应
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()

        try:
            data = json.loads(response)
            return {
                "emotion": data.get("emotion", "neutral"),
                "mood": data.get("mood", "neutral"),
                "confidence": min(1.0, max(0.0, float(data.get("confidence", 0.5)))),
                "intensity": min(1.0, max(0.0, float(data.get("intensity", 0.5)))),
                "secondary_emotions": data.get("secondary_emotions", []),
                "ai_insights": data.get("insights", ""),
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"EmotionAnalysisSkill: Failed to parse emotion response: {e}")
            return None

    def _analyze_text_fallback(self, text: str) -> Dict[str, Any]:
        """
        降级：基于规则的简单情绪分析

        注意：这是 LLM 不可用时的 fallback 方案，
        不应作为主要分析方法。
        """
        text_lower = text.lower()

        # 简化的情绪词汇（仅用于降级场景）
        emotion_indicators = {
            "happiness": ["开心", "高兴", "快乐", "幸福", "哈哈", "嘻嘻", "太好了", "棒"],
            "sadness": ["难过", "伤心", "哭", "悲伤", "心碎", "失落", "唉"],
            "anger": ["生气", "愤怒", "烦", "讨厌", "气死", "恼火"],
            "fear": ["害怕", "担心", "焦虑", "紧张", "恐惧", "不安"],
            "surprise": ["惊讶", "没想到", "天哪", "哇", "居然"],
        }

        # 统计各情绪出现次数
        emotion_counts = {}
        for emotion, keywords in emotion_indicators.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                emotion_counts[emotion] = count

        # 确定主要情绪
        if emotion_counts:
            dominant = max(emotion_counts, key=emotion_counts.get)
            confidence = min(0.7, 0.4 + emotion_counts[dominant] * 0.1)
        else:
            dominant = "neutral"
            confidence = 0.5

        # 确定 mood
        positive_emotions = {"happiness", "surprise"}
        negative_emotions = {"sadness", "anger", "fear"}

        if dominant in positive_emotions:
            mood = "positive"
        elif dominant in negative_emotions:
            mood = "negative"
        else:
            mood = "neutral"

        return {
            "emotion": dominant,
            "mood": mood,
            "confidence": confidence,
            "intensity": 0.5,
            "secondary_emotions": list(emotion_counts.keys())[:2] if len(emotion_counts) > 1 else [],
            "ai_insights": "",
        }


# 同步接口（方便非异步代码调用）
def analyze_text_emotion_sync(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    同步版本的文本情绪分析

    用于非异步环境中调用情绪分析。
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    skill = get_emotion_analysis_skill()

    try:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                skill.analyze_text_emotion(text, context)
            )
            return future.result(timeout=15)
    except RuntimeError:
        return asyncio.run(skill.analyze_text_emotion(text, context))


# 全局 Skill 实例
_emotion_analysis_skill_instance: Optional[EmotionAnalysisSkill] = None


def get_emotion_analysis_skill() -> EmotionAnalysisSkill:
    """获取情感分析 Skill 单例实例"""
    global _emotion_analysis_skill_instance
    if _emotion_analysis_skill_instance is None:
        _emotion_analysis_skill_instance = EmotionAnalysisSkill()
    return _emotion_analysis_skill_instance
