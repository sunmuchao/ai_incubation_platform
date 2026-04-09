"""
LLM 深度语义理解服务

提供基于 LLM 的深度语义分析能力：
- 隐性情绪识别（超越简单正负面，识别复杂情感状态）
- 价值观偏好提取（从对话中提取用户核心价值观）
- 沟通模式分析（识别用户的沟通风格和潜在需求）
- 语义匹配度计算（基于语义而非关键词的匹配）

架构原则：
- 语义优先：基于语义理解而非规则匹配
- 可解释性：每个分析结果都有明确的文本证据
- 隐私保护：仅分析用户授权的内容，支持删除
- 渐进式学习：持续积累用户画像
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import httpx
from sqlalchemy.orm import Session

from db.models import UserDB, ConversationDB
from utils.logger import logger
from config import settings


# ============= 价值观分类体系 =============

VALUE_CATEGORIES = {
    "家庭观念": [
        "家庭优先", "独立空间", "丁克", "要孩子", "多子多福",
        "孝顺父母", "代际同住", "核心家庭"
    ],
    "事业观念": [
        "事业为重", "家庭为重", "工作生活平衡", "创业导向",
        "稳定导向", "成就导向", "随遇而安"
    ],
    "金钱观念": [
        "节俭", "享受当下", "投资理财", "消费主义",
        "实用主义", "品质生活", "财务自由"
    ],
    "生活方式": [
        "宅家", "户外", "社交达人", "独处", "规律作息",
        "夜猫子", "健康生活", "随性"
    ],
    "情感表达": [
        "直接表达", "含蓄内敛", "行动派", "言语派",
        "需要安全感", "给予空间", "粘人", "独立"
    ],
    "成长观念": [
        "持续学习", "安于现状", "自我提升", "顺其自然",
        "目标导向", "过程导向"
    ]
}

# 情绪分类（细粒度）
EMOTION_CATEGORIES = {
    "joy": ["开心", "快乐", "兴奋", "期待", "满足", "幸福", "愉悦"],
    "trust": ["信任", "依赖", "安心", "踏实", "可靠"],
    "fear": ["害怕", "担忧", "焦虑", "不安", "恐惧"],
    "surprise": ["惊讶", "意外", "震惊"],
    "sadness": ["难过", "伤心", "失落", "沮丧", "孤独"],
    "disgust": ["厌恶", "反感", "嫌弃", "不满"],
    "anger": ["生气", "愤怒", "恼火", "烦躁"],
    "anticipation": ["期待", "盼望", "希望", "憧憬"],
    "confusion": ["困惑", "迷茫", "犹豫", "不确定"],
    "nostalgia": ["怀念", "思念", "回忆", "感慨"]
}


class LLMSemanticService:
    """
    LLM 深度语义理解服务

    使用 LLM 进行深度语义分析，包括：
    1. 隐性情绪识别
    2. 价值观偏好提取
    3. 沟通模式分析
    4. 语义匹配计算

    特性：
    - 支持降级处理（LLM 不可用时使用规则匹配）
    - 支持重试机制（网络超时时自动重试）
    - 支持限流检测（429 错误时自动降级）
    """

    def __init__(self):
        self.enabled = settings.llm_enabled
        self.provider = settings.llm_provider
        self.api_key = settings.llm_api_key
        self.api_base = settings.llm_api_base.rstrip('/') if settings.llm_api_base else ""
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens

        # 降级和重试配置
        self.fallback_enabled = True
        self.max_retries = settings.llm_retry_count if hasattr(settings, 'llm_retry_count') else 2
        self.retry_delay = 1.0  # 秒
        self.request_timeout = settings.llm_request_timeout if hasattr(settings, 'llm_request_timeout') else 30

        # 置信度阈值配置
        self.confidence_threshold = getattr(settings, 'llm_confidence_threshold', 0.6)
        self.min_confidence = 0.0  # 最低置信度
        self.max_confidence = 1.0  # 最高置信度

        # 配置 API 端点
        if not self.api_base:
            if self.provider == "openai":
                self.api_base = "https://api.openai.com/v1"
            elif self.provider == "qwen":
                self.api_base = "https://dashscope.aliyuncs.com/api/v1"
            elif self.provider == "glm":
                self.api_base = "https://open.bigmodel.cn/api/paas/v4"

        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # ==================== 置信度阈值过滤 ====================

    def _filter_by_confidence(
        self,
        values: List[Dict[str, Any]],
        min_confidence: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        根据置信度过滤价值观分析结果

        Args:
            values: 价值观分析结果列表
            min_confidence: 最低置信度阈值（不传则使用配置的阈值）

        Returns:
            过滤后的价值观列表
        """
        threshold = min_confidence if min_confidence is not None else self.confidence_threshold

        filtered = []
        for value in values:
            confidence = value.get("confidence", 0)
            if confidence >= threshold:
                filtered.append(value)

        return filtered

    def _update_overall_confidence(
        self,
        result: Dict[str, Any],
        min_confidence: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        更新总体置信度（基于过滤后的结果）

        Args:
            result: 分析结果
            min_confidence: 最低置信度阈值

        Returns:
            更新后的分析结果
        """
        threshold = min_confidence if min_confidence is not None else self.confidence_threshold

        detected_values = result.get("detected_values", [])
        filtered_values = self._filter_by_confidence(detected_values, threshold)

        # 计算过滤后的总体置信度
        if filtered_values:
            overall_confidence = sum(v.get("confidence", 0) for v in filtered_values) / len(filtered_values)
        else:
            overall_confidence = 0

        return {
            **result,
            "detected_values": filtered_values,
            "overall_confidence": max(0, min(1, overall_confidence)),
            "confidence_threshold_applied": threshold,
            "filtered_count": len(detected_values) - len(filtered_values)
        }

    # ==================== 隐性情绪识别 ====================

    async def analyze_implicit_emotions(
        self,
        text: str,
        context: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        分析隐性情绪

        超越简单的正负面分析，识别：
        - 复杂情感状态（如又期待又害怕）
        - 情绪强度
        - 情绪触发点
        - 潜在需求

        Args:
            text: 待分析文本
            context: 上下文对话列表

        Returns:
            情绪分析结果，包含：
            - primary_emotions: 主要情绪
            - secondary_emotions: 次要情绪
            - emotion_intensity: 情绪强度 (0-1)
            - emotional_conflicts: 情绪冲突（如既期待又担忧）
            - underlying_needs: 潜在需求
            - triggers: 情绪触发点
        """
        if not self.enabled:
            return self._fallback_emotion_analysis(text)

        try:
            prompt = self._build_emotion_prompt(text, context)
            response = await self._call_llm(prompt)
            result = self._parse_emotion_response(response)

            # 添加文本证据
            result["text_evidence"] = self._extract_emotion_evidence(text, result)

            return result

        except Exception as e:
            logger.error(f"LLM emotion analysis failed: {e}")
            return self._fallback_emotion_analysis(text)

    def _build_emotion_prompt(
        self,
        text: str,
        context: Optional[List[Dict[str, str]]]
    ) -> str:
        """构建情绪分析 Prompt（中文优化版）"""
        context_str = ""
        if context:
            context_str = "对话上下文：\n"
            for msg in context[-5:]:
                role = "对方" if msg.get("role") == "other" else "用户"
                context_str += f"{role}: {msg.get('content', '')}\n"
            context_str += "\n"

        return f"""
你是一位经验丰富的中文情感咨询师，擅长解读中国人含蓄的情感表达和潜台词。

请分析以下文本中蕴含的情绪状态，特别注意：

【分析要点】
1. 表层情绪 vs 深层情绪（中国人常含蓄表达，言外之意更重要）
2. 矛盾情绪（如"我没事"可能是有事但不想说）
3. 情绪强度（0-1 之间）
4. 触发情绪的潜在需求

{context_str}
待分析文本：
"{text}"

【情绪分类参考】
- 积极情绪：开心、快乐、兴奋、期待、满足、幸福、安心、感动
- 消极情绪：难过、失落、沮丧、委屈、愧疚、尴尬、无奈、疲惫
- 焦虑情绪：紧张、不安、担忧、害怕、恐慌、迷茫
- 愤怒情绪：生气、不满、烦躁、恼火、愤懑
- 复杂情绪：又爱又恨、期待又怕、哭笑不得、悲喜交加

【输出格式】请返回严格的 JSON 格式：
{{
    "primary_emotions": [{{"emotion": "情绪名称", "intensity": 0.8, "evidence": "原文片段"}}],
    "secondary_emotions": [{{"emotion": "情绪名称", "intensity": 0.3}}],
    "emotion_intensity": 0.7,
    "emotional_conflicts": [{{"conflict": "期待 vs 担忧", "explanation": "解释"}}],
    "underlying_needs": ["需求 1", "需求 2"],
    "triggers": ["触发点 1", "触发点 2"]
}}

【注意事项】
1. 注意识别反话、暗示、含蓄表达（如"还行"可能是不太满意）
2. 考虑中国人的情感表达习惯
3. 如存在歧义，在 ambiguities 中说明
"""

    def _parse_emotion_response(self, response: str) -> Dict[str, Any]:
        """解析情绪分析响应"""
        try:
            data = json.loads(response)
            return {
                "primary_emotions": data.get("primary_emotions", []),
                "secondary_emotions": data.get("secondary_emotions", []),
                "emotion_intensity": data.get("emotion_intensity", 0),
                "emotional_conflicts": data.get("emotional_conflicts", []),
                "underlying_needs": data.get("underlying_needs", []),
                "triggers": data.get("triggers", []),
                "is_analyzed": True
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse emotion response, using fallback")
            return self._fallback_emotion_analysis("")

    def _extract_emotion_evidence(
        self,
        text: str,
        analysis_result: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """从原文中提取情绪证据"""
        evidence_list = []
        for emotion in analysis_result.get("primary_emotions", []):
            if "evidence" in emotion:
                evidence_list.append({
                    "emotion": emotion["emotion"],
                    "text": emotion["evidence"]
                })
        return evidence_list

    def _fallback_emotion_analysis(self, text: str) -> Dict[str, Any]:
        """降级情绪分析（当 LLM 不可用时）"""
        result = {
            "primary_emotions": [],
            "secondary_emotions": [],
            "emotion_intensity": 0,
            "emotional_conflicts": [],
            "underlying_needs": [],
            "triggers": [],
            "is_analyzed": False
        }

        if not text:
            return result

        # 简单关键词匹配
        emotion_scores = {}
        for emotion_type, keywords in EMOTION_CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                emotion_scores[emotion_type] = score / len(keywords)

        if emotion_scores:
            sorted_emotions = sorted(
                emotion_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            result["primary_emotions"] = [
                {"emotion": em, "intensity": min(1.0, score * 2), "evidence": text[:50]}
                for em, score in sorted_emotions[:2]
            ]
            result["emotion_intensity"] = max(emotion_scores.values())

        return result

    # ==================== 价值观偏好提取 ====================

    async def extract_value_preferences(
        self,
        text: str,
        user_id: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        从文本中提取价值观偏好

        分析用户表达的：
        - 家庭观念
        - 事业观念
        - 金钱观念
        - 生活方式
        - 情感表达方式
        - 成长观念

        Args:
            text: 待分析文本
            user_id: 用户 ID（用于累积画像）
            min_confidence: 最低置信度阈值（可选，不传则使用配置的阈值）

        Returns:
            价值观分析结果，包含：
            - detected_values: 检测到的价值观（已过滤低置信度）
            - overall_confidence: 总体置信度
            - confidence_threshold_applied: 应用的置信度阈值
            - filtered_count: 被过滤掉的低置信度价值观数量
            - evidence: 文本证据
            - update_suggestions: 画像更新建议
        """
        if not self.enabled:
            result = self._fallback_value_analysis(text)
            return self._update_overall_confidence(result, min_confidence)

        try:
            prompt = self._build_value_prompt(text)
            response = await self._call_llm(prompt)
            result = self._parse_value_response(response, text)

            # 应用置信度阈值过滤
            result = self._update_overall_confidence(result, min_confidence)

            # 如果提供了 user_id，累积到用户画像
            if user_id and result.get("detected_values"):
                await self._accumulate_value_profile(user_id, result)

            return result

        except Exception as e:
            logger.error(f"LLM value analysis failed: {e}")
            result = self._fallback_value_analysis(text)
            return self._update_overall_confidence(result, min_confidence)

    def _build_value_prompt(self, text: str) -> str:
        """构建价值观分析 Prompt（中文优化版）"""
        return f"""
你是一位专业的价值观分析师，擅长从中国人的言谈举止中提取其价值观和人生偏好。

请分析以下文本，识别用户表达的价值观倾向：

【待分析文本】
"{text}"

【价值观分类参考】
- 家庭观念：家庭优先、独立空间、丁克、要孩子、多子多福、孝顺父母、代际同住、核心家庭
- 事业观念：事业为重、家庭为重、工作生活平衡、创业导向、稳定导向、成就导向、随遇而安
- 金钱观念：节俭、享受当下、投资理财、消费主义、实用主义、品质生活、财务自由
- 生活方式：宅家、户外、社交达人、独处、规律作息、夜猫子、健康生活、随性
- 情感表达：直接表达、含蓄内敛、行动派、言语派、需要安全感、给予空间、粘人、独立
- 成长观念：持续学习、安于现状、自我提升、顺其自然、目标导向、过程导向

【中国式表达特别注意】
- "我还行" → 可能是不太满意但不好意思说
- "看情况" → 可能是委婉拒绝
- "你决定就好" → 可能是真的不在乎，也可能是有想法但不想说
- "再说吧" → 可能是婉拒
- "改天" → 可能没有具体时间

【输出格式】请返回 JSON 格式：
{{
    "detected_values": [
        {{
            "category": "价值观分类",
            "value": "具体价值观",
            "confidence": 0.8,
            "evidence": "原文依据",
            "polarity": "positive/negative/neutral"
        }}
    ],
    "overall_confidence": 0.7,
    "ambiguities": ["不确定的地方"],
    "update_suggestions": [
        {{
            "field": "interests/lifestyle/preferences",
            "suggested_value": "建议值",
            "reason": "原因"
        }}
    ]
}}

【注意事项】
1. 只提取有明确文本证据的价值观
2. 标注置信度（0-1）
3. 注意识别委婉表达背后的真实想法
4. 如存在歧义或矛盾，在 ambiguities 中说明
"""

    def _parse_value_response(
        self,
        response: str,
        original_text: str
    ) -> Dict[str, Any]:
        """解析价值观分析响应"""
        try:
            data = json.loads(response)
            return {
                "detected_values": data.get("detected_values", []),
                "overall_confidence": data.get("overall_confidence", 0),
                "ambiguities": data.get("ambiguities", []),
                "update_suggestions": data.get("update_suggestions", []),
                "is_analyzed": True
            }
        except json.JSONDecodeError:
            return self._fallback_value_analysis(original_text)

    def _fallback_value_analysis(self, text: str) -> Dict[str, Any]:
        """降级价值观分析（当 LLM 不可用时）"""
        result = {
            "detected_values": [],
            "overall_confidence": 0,
            "ambiguities": [],
            "update_suggestions": [],
            "is_analyzed": False
        }

        if not text:
            return result

        # 简单关键词匹配
        for category, values in VALUE_CATEGORIES.items():
            for value in values:
                if value in text:
                    result["detected_values"].append({
                        "category": category,
                        "value": value,
                        "confidence": 0.5,
                        "evidence": text[:100],
                        "polarity": "positive"
                    })
                    result["overall_confidence"] = max(
                        result["overall_confidence"],
                        0.5
                    )

        return result

    async def _accumulate_value_profile(
        self,
        user_id: str,
        analysis_result: Dict[str, Any]
    ):
        """
        累积用户价值观画像

        将 LLM 分析的价值观结果持久化到 UserPreferenceDB，支持：
        - 多次对话结果累积
        - 置信度加权平均
        - 时间衰减因子
        """
        from db.models import UserPreferenceDB
        from db.database import SessionLocal
        from datetime import datetime
        import json

        db = SessionLocal()
        try:
            # 获取或创建用户偏好记录
            preference = db.query(UserPreferenceDB).filter(
                UserPreferenceDB.user_id == user_id
            ).first()

            if not preference:
                # 创建新记录
                preference = UserPreferenceDB(
                    id=f"pref-{user_id}-{datetime.now().timestamp()}",
                    user_id=user_id,
                    preference_weights=analysis_result.get("weights", {
                        "age": 0.2,
                        "location": 0.2,
                        "interests": 0.3,
                        "values": 0.3
                    })
                )
                db.add(preference)
            else:
                # 累积更新：使用加权平均融合新旧数据
                existing_weights = preference.preference_weights or {}
                new_weights = analysis_result.get("weights", {})

                # 时间衰减因子：旧数据权重 0.7，新数据权重 0.3
                merged_weights = {}
                all_keys = set(existing_weights.keys()) | set(new_weights.keys())
                for key in all_keys:
                    old_val = existing_weights.get(key, 0)
                    new_val = new_weights.get(key, 0)
                    merged_weights[key] = round(old_val * 0.7 + new_val * 0.3, 2)

                preference.preference_weights = merged_weights
                preference.updated_at = datetime.now()

            db.commit()
            logger.info(f"LLMSemanticService: Value profile accumulated for user={user_id}")

        except Exception as e:
            logger.error(f"LLMSemanticService: Failed to accumulate value profile: {e}")
            db.rollback()
        finally:
            db.close()

    # ==================== 沟通模式分析 ====================

    async def analyze_communication_pattern(
        self,
        conversation_history: List[Dict[str, str]],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析用户的沟通模式

        识别：
        - 沟通风格（直接/含蓄、理性/感性）
        - 响应模式（即时/延迟、长篇/简短）
        - 话题偏好
        - 互动倾向（主动/被动、提问/陈述）
        - 潜在沟通需求

        Args:
            conversation_history: 对话历史
            user_id: 用户 ID

        Returns:
            沟通模式分析结果
        """
        if not self.enabled or len(conversation_history) < 2:
            return self._fallback_communication_analysis(conversation_history)

        try:
            prompt = self._build_communication_prompt(conversation_history)
            response = await self._call_llm(prompt)
            result = self._parse_communication_response(response)

            return result

        except Exception as e:
            logger.error(f"LLM communication analysis failed: {e}")
            return self._fallback_communication_analysis(conversation_history)

    def _build_communication_prompt(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """构建沟通模式分析 Prompt"""
        history_str = ""
        for msg in conversation_history[-10:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            history_str += f"{role}: {content}\n"

        return f"""
你是一个专业的沟通分析师，请分析以下对话中用户的沟通模式：

对话历史：
{history_str}

请分析以下维度：
1. 沟通风格：直接 vs 含蓄、理性 vs 感性、正式 vs 随意
2. 响应模式：回复速度倾向、消息长度倾向
3. 话题偏好：喜欢讨论什么类型的话题
4. 互动倾向：主动发起 vs 被动回应、提问 vs 陈述、自我表露程度
5. 情感表达：情绪表达方式、是否需要情绪回应
6. 潜在需求：在沟通中可能的潜在需求

请返回 JSON 格式结果：
{{
    "communication_style": {{
        "directness": "direct/indirect/balanced",
        "rationality": "rational/emotional/balanced",
        "formality": "formal/casual/balanced",
        "description": "风格描述"
    }},
    "response_pattern": {{
        "length_preference": "short/medium/long",
        "avg_response_length": 50,
        "timing_pattern": "immediate/delayed/varied"
    }},
    "topic_preferences": ["话题 1", "话题 2"],
    "interaction_tendency": {{
        "initiation": "active/passive/balanced",
        "questioning": "high/medium/low",
        "self_disclosure": "high/medium/low"
    }},
    "emotional_expression": {{
        "style": "expressive/reserved/balanced",
        "needs_validation": true/false,
        "description": "描述"
    }},
    "potential_needs": ["需求 1", "需求 2"],
    "compatibility_tips": ["与该用户沟通的建议"]
}}
"""

    def _parse_communication_response(self, response: str) -> Dict[str, Any]:
        """解析沟通模式响应"""
        try:
            data = json.loads(response)
            return {
                "communication_style": data.get("communication_style", {}),
                "response_pattern": data.get("response_pattern", {}),
                "topic_preferences": data.get("topic_preferences", []),
                "interaction_tendency": data.get("interaction_tendency", {}),
                "emotional_expression": data.get("emotional_expression", {}),
                "potential_needs": data.get("potential_needs", []),
                "compatibility_tips": data.get("compatibility_tips", []),
                "is_analyzed": True
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse communication response")
            return self._fallback_communication_analysis([])

    def _fallback_communication_analysis(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """降级沟通模式分析"""
        if not conversation_history:
            return {
                "communication_style": {},
                "response_pattern": {},
                "topic_preferences": [],
                "interaction_tendency": {},
                "emotional_expression": {},
                "potential_needs": [],
                "compatibility_tips": [],
                "is_analyzed": False
            }

        # 简单统计
        user_messages = [m for m in conversation_history if m.get("role") == "user"]
        avg_length = sum(len(m.get("content", "")) for m in user_messages) / len(user_messages) if user_messages else 0

        return {
            "communication_style": {
                "description": "基础分析（LLM 不可用）"
            },
            "response_pattern": {
                "avg_response_length": round(avg_length, 1)
            },
            "topic_preferences": [],
            "interaction_tendency": {},
            "emotional_expression": {},
            "potential_needs": [],
            "compatibility_tips": [],
            "is_analyzed": False
        }

    # ==================== 语义匹配度计算 ====================

    async def calculate_semantic_compatibility(
        self,
        user1_profile: Dict[str, Any],
        user2_profile: Dict[str, Any],
        user1_conversation_samples: Optional[List[str]] = None,
        user2_conversation_samples: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        计算语义匹配度

        基于价值观、沟通风格、情感需求的深度匹配，
        而非简单的兴趣标签重叠。

        Args:
            user1_profile: 用户 1 画像
            user2_profile: 用户 2 画像
            user1_conversation_samples: 用户 1 对话样本
            user2_conversation_samples: 用户 2 对话样本

        Returns:
            匹配分析结果，包含：
            - overall_compatibility: 总体匹配度 (0-1)
            - value_alignment: 价值观契合度
            - communication_compatibility: 沟通兼容性
            - emotional_compatibility: 情感需求匹配
            - potential_conflicts: 潜在冲突点
            - relationship_strengths: 关系优势
            - growth_suggestions: 成长建议
        """
        if not self.enabled:
            return self._fallback_compatibility_calculation(
                user1_profile, user2_profile
            )

        try:
            prompt = self._build_compatibility_prompt(
                user1_profile, user2_profile,
                user1_conversation_samples,
                user2_conversation_samples
            )
            response = await self._call_llm(prompt)
            result = self._parse_compatibility_response(response)

            return result

        except Exception as e:
            logger.error(f"LLM compatibility calculation failed: {e}")
            return self._fallback_compatibility_calculation(
                user1_profile, user2_profile
            )

    def _build_compatibility_prompt(
        self,
        user1_profile: Dict[str, Any],
        user2_profile: Dict[str, Any],
        samples1: Optional[List[str]],
        samples2: Optional[List[str]]
    ) -> str:
        """构建匹配度分析 Prompt"""
        profile1_str = json.dumps(user1_profile, ensure_ascii=False, indent=2)
        profile2_str = json.dumps(user2_profile, ensure_ascii=False, indent=2)

        samples1_str = "\n".join(samples1[:3]) if samples1 else "无"
        samples2_str = "\n".join(samples2[:3]) if samples2 else "无"

        return f"""
你是一个专业的婚恋匹配分析师，请基于两个用户的深度画像分析他们的兼容性。

用户 1 画像：
{profile1_str}

用户 1 对话样本：
{samples1_str}

用户 2 画像：
{profile2_str}

用户 2 对话样本：
{samples2_str}

请从以下维度进行分析：
1. 价值观契合度：家庭观、事业观、金钱观、生活方式等是否兼容
2. 沟通兼容性：沟通风格是否互补或冲突
3. 情感需求匹配：情感表达方式是否能够满足彼此需求
4. 潜在冲突点：可能产生分歧的地方
5. 关系优势：这段关系的潜在优势
6. 成长建议：双方需要注意和成长的地方

请返回 JSON 格式结果：
{{
    "overall_compatibility": 0.75,
    "value_alignment": {{
        "score": 0.8,
        "aligned_values": ["共同价值观 1", "共同价值观 2"],
        "different_values": [{{"aspect": "方面", "user1": "用户 1 倾向", "user2": "用户 2 倾向", "compatibility": "compatible/complementary/conflicting"}}],
        "analysis": "分析说明"
    }},
    "communication_compatibility": {{
        "score": 0.7,
        "style_match": "complementary/similar/different",
        "strengths": ["沟通优势 1", "沟通优势 2"],
        "challenges": ["沟通挑战 1"],
        "tips": ["沟通建议"]
    }},
    "emotional_compatibility": {{
        "score": 0.65,
        "needs_match": "用户 1 需求 vs 用户 2 给予能力分析",
        "emotional_support_potential": "high/medium/low",
        "analysis": "分析"
    }},
    "potential_conflicts": [
        {{"aspect": "冲突方面", "description": "描述", "severity": "low/medium/high", "mitigation": "缓解建议"}}
    ],
    "relationship_strengths": ["优势 1", "优势 2"],
    "growth_suggestions": ["建议 1", "建议 2"],
    "match_reasoning": "综合匹配理由（可展示给用户）"
}}
"""

    def _parse_compatibility_response(self, response: str) -> Dict[str, Any]:
        """解析匹配度响应"""
        try:
            data = json.loads(response)
            return {
                "overall_compatibility": data.get("overall_compatibility", 0),
                "value_alignment": data.get("value_alignment", {}),
                "communication_compatibility": data.get("communication_compatibility", {}),
                "emotional_compatibility": data.get("emotional_compatibility", {}),
                "potential_conflicts": data.get("potential_conflicts", []),
                "relationship_strengths": data.get("relationship_strengths", []),
                "growth_suggestions": data.get("growth_suggestions", []),
                "match_reasoning": data.get("match_reasoning", ""),
                "is_analyzed": True
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse compatibility response")
            return self._fallback_compatibility_calculation({}, {})

    def _fallback_compatibility_calculation(
        self,
        user1_profile: Dict[str, Any],
        user2_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """降级匹配度计算"""
        # 简单基于兴趣重叠的计算
        interests1 = set(user1_profile.get("interests", []))
        interests2 = set(user2_profile.get("interests", []))

        if interests1 and interests2:
            common = interests1 & interests2
            union = interests1 | interests2
            jaccard = len(common) / len(union) if union else 0
        else:
            jaccard = 0.5  # 默认值

        return {
            "overall_compatibility": jaccard,
            "value_alignment": {"score": 0.5, "analysis": "需要更多数据"},
            "communication_compatibility": {"score": 0.5, "style_match": "unknown"},
            "emotional_compatibility": {"score": 0.5, "analysis": "需要更多数据"},
            "potential_conflicts": [],
            "relationship_strengths": list(interests1 & interests2) if interests1 & interests2 else ["需要进一步了解"],
            "growth_suggestions": [],
            "match_reasoning": f"你们有 {len(interests1 & interests2)} 个共同兴趣",
            "is_analyzed": False
        }

    # ==================== LLM 调用封装 ====================

    async def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM API（带重试和降级处理）

        重试策略：
        - 网络超时：指数退避重试
        - 429 限流：立即降级到 fallback
        - 5xx 错误：重试 1 次后降级

        Args:
            prompt: 提示词

        Returns:
            LLM 响应文本
        """
        import asyncio

        client = await self._get_client()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的情感分析和人际关系专家，擅长深度语义理解和价值观分析。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}
        }

        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.request_timeout
                )

                # 处理限流（429）
                if response.status_code == 429:
                    logger.warning(f"LLM API 限流，立即降级到 fallback 模式")
                    return self._get_fallback_response(prompt)

                # 处理其他错误
                response.raise_for_status()

                result = response.json()
                return result["choices"][0]["message"]["content"]

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries:
                    # 指数退避
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"LLM API 超时，{delay}秒后重试 ({attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM API 超时，重试耗尽，降级到 fallback")
                    return self._get_fallback_response(prompt)

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500 and attempt < self.max_retries:
                    # 服务端错误，重试
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"LLM API 服务端错误，{delay}秒后重试 ({attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                else:
                    # 客户端错误（4xx），直接降级
                    logger.error(f"LLM API 客户端错误 {e.response.status_code}，降级到 fallback")
                    return self._get_fallback_response(prompt)

            except Exception as e:
                last_error = e
                logger.error(f"LLM API 调用失败：{e}")
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    return self._get_fallback_response(prompt)

        # 所有重试失败
        logger.error(f"LLM API 所有重试失败，降级到 fallback: {last_error}")
        return self._get_fallback_response(prompt)

    def _get_fallback_response(self, prompt: str) -> str:
        """
        获取 fallback 响应（当 LLM 不可用时）

        返回一个简单的 JSON 结构，表示分析不可用
        """
        return json.dumps({
            "fallback": True,
            "reason": "LLM service unavailable",
            "message": "深度分析服务暂时不可用，已切换到基础模式"
        }, ensure_ascii=False)


# 全局服务实例
_llm_semantic_service: Optional[LLMSemanticService] = None


def get_llm_semantic_service() -> LLMSemanticService:
    """获取 LLM 语义服务单例实例"""
    global _llm_semantic_service
    if _llm_semantic_service is None:
        _llm_semantic_service = LLMSemanticService()
    return _llm_semantic_service
