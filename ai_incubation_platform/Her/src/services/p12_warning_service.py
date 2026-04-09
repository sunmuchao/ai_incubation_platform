"""
P12 行为实验室 - 吵架预警服务

吵架预警服务（灭火器）- 情绪分析、争吵检测、降级建议
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import re
import json

from db.database import SessionLocal
from db.models import ConversationDB, ChatMessageDB, UserDB
from models.p12_models import EmotionWarningDB, CalmingKitDB
from utils.logger import logger
from utils.db_session_manager import db_session, db_session_readonly


class EmotionWarningService:
    """吵架预警服务（灭火器）"""

    # 预警级别
    LEVEL_LOW = "low"
    LEVEL_MEDIUM = "medium"
    LEVEL_HIGH = "high"
    LEVEL_CRITICAL = "critical"

    # 负面情绪关键词
    NEGATIVE_EMOTION_KEYWORDS = {
        "anger": ["生气", "愤怒", "烦", "讨厌", "恨", "滚", "闭嘴", "够了", "受不了"],
        "frustration": ["失望", "无奈", "算了", "随便", "无所谓", "呵呵"],
        "sadness": ["难过", "伤心", "委屈", "哭", "泪", "心痛", "受伤"],
        "defensiveness": ["又不是我", "你才", "你总是", "你从来", "凭什么"],
        "contempt": ["真可笑", "呵呵", "就你", "也不看看自己", "拜托"],
    }

    # 升级模式
    ESCALATION_PATTERNS = [
        r"你总是.*",  # 绝对化
        r"你从来.*",  # 绝对化
        r"每次都是.*",  # 绝对化
        r"就不能.*吗",  # 反问质问
        r"有必要.*吗",  # 反问质问
    ]

    def __init__(self):
        self._calming_kits_initialized = False

    def _analyze_message_emotion(self, content: str) -> Dict[str, Any]:
        """分析单条消息的情绪"""
        emotions = {}
        intensity = 0.0
        is_escalation_pattern = False

        # 检查负面情绪关键词
        for emotion, keywords in self.NEGATIVE_EMOTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content:
                    emotions[emotion] = emotions.get(emotion, 0) + 1
                    intensity += 0.1

        # 检查升级模式
        for pattern in self.ESCALATION_PATTERNS:
            if re.search(pattern, content):
                emotions["escalation"] = emotions.get("escalation", 0) + 1
                intensity += 0.15
                is_escalation_pattern = True

        # 检查感叹号和问号（情绪强度指标）
        exclamation_count = content.count('!') + content.count('！')
        question_count = content.count('?') + content.count('？')
        intensity += (exclamation_count * 0.05) + (question_count * 0.03)

        # 限制强度在 0-1 之间
        intensity = min(intensity, 1.0)

        return {
            "emotions": emotions,
            "intensity": intensity,
            "is_escalation_pattern": is_escalation_pattern
        }

    def _detect_escalation_pattern(self, messages: List[Any]) -> Dict[str, Any]:
        """检测对话升级模式"""
        # 按发送者分组消息
        user_messages = defaultdict(list)
        for msg in messages:
            user_messages[msg.sender_id].append(msg)

        # 分析情绪趋势
        trends = {}
        for user_id, user_msgs in user_messages.items():
            emotions_over_time = []
            for msg in user_msgs[-10:]:  # 分析最近 10 条
                emotion = self._analyze_message_emotion(msg.content)
                emotions_over_time.append(emotion["intensity"])

            # 计算趋势（简单线性回归）
            if len(emotions_over_time) >= 2:
                trend = sum(emotions_over_time[-3:]) / len(emotions_over_time[-3:]) - \
                        sum(emotions_over_time[:3]) / len(emotions_over_time[:3])
                trends[user_id] = {
                    "trend": "escalating" if trend > 0.1 else "deescalating" if trend < -0.1 else "stable",
                    "avg_intensity": sum(emotions_over_time) / len(emotions_over_time)
                }

        return trends

    def _get_calming_suggestions(self, emotion: str, intensity: float) -> List[Dict[str, str]]:
        """获取冷静建议"""
        suggestions_map = {
            "anger": [
                "试着深呼吸三次，暂时离开对话场景",
                "用'我语句'表达感受，而非指责对方",
                "提醒自己：我们的关系比这个分歧更重要"
            ],
            "frustration": [
                "暂停对话，等情绪平复后再继续",
                "思考：我真正想要表达的需求是什么",
                "尝试换位思考，理解对方的立场"
            ],
            "sadness": [
                "允许自己感受这份情绪，不需要压抑",
                "向对方表达你的感受，而非指责",
                "寻求安慰和支持是完全可以的"
            ],
            "defensiveness": [
                "尝试倾听对方话语中的合理部分",
                "避免'你总是/你从来'的表达方式",
                "承认自己的责任，即使很小"
            ],
            "contempt": [
                "回想对方的优点和你们的美好回忆",
                "避免讽刺和轻蔑的语气",
                "以尊重的态度表达不同意见"
            ]
        }

        # 返回主导情绪的建议
        if emotion in suggestions_map:
            return [{"type": "calming", "content": s} for s in suggestions_map[emotion][:3]]

        return [{"type": "general", "content": "暂时冷静一下，深呼吸，换个角度思考"}]

    def analyze_conversation_emotion(
        self,
        conversation_id: str,
        user_a_id: str,
        user_b_id: str,
        window_messages: int = 20,
        db_session_param: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        分析对话情绪，检测是否存在争吵风险

        Args:
            conversation_id: 对话 ID
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            window_messages: 分析最近多少条消息
            db_session_param: 可选的数据库会话

        Returns:
            情绪分析结果，包括预警级别和建议
        """
        with db_session_readonly() as db:
            # 获取最近消息
            messages = db.query(ChatMessageDB).filter(
                ChatMessageDB.conversation_id == conversation_id
            ).order_by(ChatMessageDB.created_at.desc()).limit(window_messages).all()

            if not messages:
                return None

            messages = list(reversed(messages))

            # 分析每条消息的情绪
            message_emotions = []
            for msg in messages:
                emotion = self._analyze_message_emotion(msg.content)
                message_emotions.append({
                    "message_id": msg.id,
                    "sender_id": msg.sender_id,
                    "content": msg.content[:100],
                    "emotions": emotion["emotions"],
                    "intensity": emotion["intensity"],
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                })

            # 计算整体情绪强度
            avg_intensity = sum(m["intensity"] for m in message_emotions) / len(message_emotions)

            # 检测升级模式
            escalation_trends = self._detect_escalation_pattern(messages)

            # 确定预警级别
            warning_level = self._determine_warning_level(avg_intensity, escalation_trends)

            # 生成冷静建议
            dominant_emotion = max(
                [(e, sum(m["emotions"].get(e, 0) for m in message_emotions))
                 for e in ["anger", "frustration", "sadness", "defensiveness", "contempt"]],
                key=lambda x: x[1]
            )[0] if any(any(m["emotions"].values()) for m in message_emotions) else None

            calming_suggestions = self._get_calming_suggestions(
                dominant_emotion, avg_intensity
            ) if dominant_emotion else []

            return {
                "conversation_id": conversation_id,
                "warning_level": warning_level,
                "avg_emotion_intensity": round(avg_intensity, 2),
                "dominant_emotion": dominant_emotion,
                "escalation_trends": escalation_trends,
                "message_emotions": message_emotions,
                "calming_suggestions": calming_suggestions,
                "analyzed_at": datetime.now().isoformat()
            }

    def _determine_warning_level(self, avg_intensity: float, escalation_trends: Dict) -> str:
        """确定预警级别"""
        # 基于平均强度
        if avg_intensity >= 0.7:
            return self.LEVEL_HIGH
        elif avg_intensity >= 0.4:
            return self.LEVEL_MEDIUM

        # 基于升级趋势
        escalating_users = sum(
            1 for trend in escalation_trends.values()
            if trend.get("trend") == "escalating"
        )

        if escalating_users >= 2:
            return self.LEVEL_HIGH
        elif escalating_users >= 1:
            return self.LEVEL_MEDIUM

        return self.LEVEL_LOW

    def create_warning(
        self,
        conversation_id: str,
        user_id: str,
        warning_level: str,
        trigger_reason: str,
        detected_emotions: Dict[str, int],
        calming_suggestions: List[Dict],
        db_session_param: Optional[Any] = None
    ) -> str:
        """创建吵架预警记录"""
        with db_session() as db:
            warning = EmotionWarningDB(
                id=f"warn_{datetime.now().timestamp()}_{user_id[:8]}",
                conversation_id=conversation_id,
                user_id=user_id,
                warning_level=warning_level,
                trigger_reason=trigger_reason,
                detected_emotions=json.dumps(detected_emotions),
                calming_suggestions=json.dumps(calming_suggestions),
                is_acknowledged=False,
                is_resolved=False,
                created_at=datetime.now()
            )
            db.add(warning)
            return warning.id

    def get_conversation_warnings(
        self,
        conversation_id: str,
        limit: int = 10,
        db_session_param: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """获取对话的预警历史"""
        with db_session_readonly() as db:
            warnings = db.query(EmotionWarningDB).filter(
                EmotionWarningDB.conversation_id == conversation_id
            ).order_by(EmotionWarningDB.created_at.desc()).limit(limit).all()

            return [self._warning_to_dict(w) for w in warnings]

    def acknowledge_warning(self, warning_id: str, db_session_param: Optional[Any] = None) -> bool:
        """确认预警（支持 db_session 参数）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._acknowledge_warning_internal(warning_id, db)
            else:
                return self._acknowledge_warning_internal(warning_id, db_session_param)
        finally:
            if use_context:
                pass

    def resolve_warning(self, warning_id: str, relationship_improvement: Optional[float] = None, db_session_param: Optional[Any] = None) -> bool:
        """解决预警（支持 db_session 参数）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._resolve_warning_internal(warning_id, relationship_improvement, db)
            else:
                return self._resolve_warning_internal(warning_id, relationship_improvement, db_session_param)
        finally:
            if use_context:
                pass

    def _acknowledge_warning_internal(self, warning_id: str, db: Any) -> bool:
        """确认预警内部方法"""
        warning = db.query(EmotionWarningDB).filter(EmotionWarningDB.id == warning_id).first()
        if not warning:
            return False
        warning.is_acknowledged = True
        warning.acknowledged_at = datetime.now()
        warning.acknowledged_by = "user"
        return True

    def _resolve_warning_internal(self, warning_id: str, relationship_improvement: Optional[float], db: Any) -> bool:
        """解决预警内部方法"""
        warning = db.query(EmotionWarningDB).filter(EmotionWarningDB.id == warning_id).first()
        if not warning:
            return False
        warning.is_resolved = True
        warning.resolved_at = datetime.now()
        if relationship_improvement is not None:
            warning.resolution_note = f"关系改善度：{relationship_improvement}"
        return True

    def get_user_warnings(self, user_id: str, days: int = 7, only_unresolved: bool = False, db_session_param: Optional[Any] = None) -> List[Dict[str, Any]]:
        """获取用户预警历史（支持 db_session 参数）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session_readonly() as db:
                    return self._get_user_warnings_internal(user_id, days, only_unresolved, db)
            else:
                return self._get_user_warnings_internal(user_id, days, only_unresolved, db_session_param)
        finally:
            if use_context:
                pass

    def _get_user_warnings_internal(self, user_id: str, days: int, only_unresolved: bool, db: Any) -> List[Dict[str, Any]]:
        """获取用户预警历史内部方法"""
        since = datetime.now() - timedelta(days=days)
        query = db.query(EmotionWarningDB).filter(
            ((EmotionWarningDB.user_a_id == user_id) | (EmotionWarningDB.user_b_id == user_id)),
            EmotionWarningDB.created_at >= since
        )

        if only_unresolved:
            query = query.filter(EmotionWarningDB.is_resolved == False)

        warnings = query.order_by(EmotionWarningDB.created_at.desc()).all()
        return [self._warning_to_dict(w) for w in warnings]

    def _warning_to_dict(self, warning: EmotionWarningDB) -> Dict[str, Any]:
        """将预警对象转换为字典"""
        detected_emotions = warning.detected_emotions
        if isinstance(detected_emotions, str):
            detected_emotions = json.loads(detected_emotions) if warning.detected_emotions else {}
        elif detected_emotions is None:
            detected_emotions = {}

        calming_suggestions = warning.calming_suggestions
        if isinstance(calming_suggestions, str):
            calming_suggestions = json.loads(calming_suggestions) if warning.calming_suggestions else []
        elif calming_suggestions is None:
            calming_suggestions = []

        return {
            "id": warning.id,
            "conversation_id": warning.conversation_id,
            "warning_level": warning.warning_level,
            "trigger_reason": warning.trigger_reason,
            "detected_emotions": detected_emotions,
            "calming_suggestions": calming_suggestions,
            "is_acknowledged": warning.is_acknowledged,
            "is_resolved": warning.is_resolved,
            "created_at": warning.created_at.isoformat() if warning.created_at else None,
            "resolved_at": warning.resolved_at.isoformat() if warning.resolved_at else None
        }

    # ========== 测试兼容方法 ==========
    # 以下为测试兼容添加的辅助方法

    def _calculate_overall_emotion(self, message_emotions: List[Dict], user_a_id: str, user_b_id: str) -> Dict[str, Any]:
        """计算整体情绪状态（测试兼容）"""
        user_a_emotions = defaultdict(float)
        user_b_emotions = defaultdict(float)

        for msg in message_emotions:
            sender = msg.get("sender_id", "")
            emotions = msg.get("emotions", {})
            intensity = msg.get("intensity", 0)

            target_dict = user_a_emotions if sender == user_a_id else user_b_emotions
            for emotion, value in emotions.items():
                target_dict[emotion] += value * intensity

        # 归一化
        total_a = sum(user_a_emotions.values()) or 1
        total_b = sum(user_b_emotions.values()) or 1

        return {
            "emotion_distribution": {
                "user_a": dict(user_a_emotions),
                "user_b": dict(user_b_emotions)
            },
            "user_a_emotions": {k: v / total_a for k, v in user_a_emotions.items()},
            "user_b_emotions": {k: v / total_b for k, v in user_b_emotions.items()},
            "overall_intensity": (total_a + total_b) / (2 * len(message_emotions)) if message_emotions else 0,
            "message_count": len(message_emotions)
        }

    def _assess_escalation_risk(self, message_emotions: List[Dict], overall_analysis: Dict) -> Dict[str, Any]:
        """评估升级风险（测试兼容）"""
        risk_score = 0.0
        reasons = []

        # 检查升级模式
        escalation_count = sum(1 for msg in message_emotions if msg.get("is_escalation_pattern", False))
        if escalation_count >= 2:
            risk_score += 0.4
            reasons.append("检测到多条升级模式消息")

        # 检查整体强度
        intensity = overall_analysis.get("overall_intensity", 0)
        if intensity >= 0.7:
            risk_score += 0.3
            reasons.append("情绪强度过高")

        # 检查轻蔑情绪
        emotion_dist = overall_analysis.get("emotion_distribution", {})
        if "contempt" in emotion_dist:
            contempt_score = emotion_dist["contempt"]
            if isinstance(contempt_score, dict):
                contempt_score = sum(contempt_score.values())
            if contempt_score >= 0.3:
                risk_score += 0.3
                reasons.append("检测到轻蔑情绪")

        # 确定风险级别
        if risk_score >= 0.7:
            risk_level = self.LEVEL_HIGH
        elif risk_score >= 0.4:
            risk_level = self.LEVEL_MEDIUM
        else:
            risk_level = self.LEVEL_LOW

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "reason": "; ".join(reasons) if reasons else "风险较低"
        }

    def _generate_calming_suggestions(self, overall_analysis: Dict, escalation_risk: Dict) -> List[Dict[str, Any]]:
        """生成冷静锦囊（测试兼容）"""
        suggestions = []
        risk_level = escalation_risk.get("risk_level", self.LEVEL_LOW)
        emotion_dist = overall_analysis.get("emotion_distribution", {})

        # 高风险：建议暂停
        if risk_level in [self.LEVEL_HIGH, self.LEVEL_CRITICAL]:
            suggestions.append({
                "type": "timeout",
                "content": "建议暂时停止对话，深呼吸三次，等情绪平复后再继续"
            })

        # 轻蔑情绪：建议重新理解对方
        if "contempt" in emotion_dist:
            suggestions.append({
                "type": "reframe",
                "content": "尝试从对方的角度理解问题，回想对方的优点"
            })

        # 防御性：建议共情
        if "defensiveness" in emotion_dist:
            suggestions.append({
                "type": "empathy",
                "content": "尝试倾听对方的感受，而非急于辩解"
            })

        # 愤怒：建议冷静表达
        if "anger" in emotion_dist:
            suggestions.append({
                "type": "i_statement",
                "content": "用'我感到...'代替'你总是...'来表达感受"
            })

        if not suggestions:
            suggestions.append({
                "type": "general",
                "content": "保持冷静，理性沟通"
            })

        return suggestions

    def acknowledge_warning(self, warning_id: str, db_session_param: Optional[Any] = None) -> bool:
        """确认预警（测试兼容 - 接受 db_session 参数）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._acknowledge_warning_internal(warning_id, db)
            else:
                return self._acknowledge_warning_internal(warning_id, db_session_param)
        finally:
            if use_context:
                pass

    def _acknowledge_warning_internal(self, warning_id: str, db: Any) -> bool:
        """确认预警内部方法"""
        warning = db.query(EmotionWarningDB).filter(EmotionWarningDB.id == warning_id).first()
        if not warning:
            return False
        warning.is_acknowledged = True
        warning.acknowledged_at = datetime.now()
        warning.acknowledged_by = "user"
        return True

    def resolve_warning(self, warning_id: str, relationship_improvement: Optional[float] = None, db_session_param: Optional[Any] = None) -> bool:
        """解决预警（测试兼容 - 接受 db_session 参数）"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._resolve_warning_internal(warning_id, relationship_improvement, db)
            else:
                return self._resolve_warning_internal(warning_id, relationship_improvement, db_session_param)
        finally:
            if use_context:
                pass

    def _resolve_warning_internal(self, warning_id: str, relationship_improvement: Optional[float], db: Any) -> bool:
        """解决预警内部方法"""
        warning = db.query(EmotionWarningDB).filter(EmotionWarningDB.id == warning_id).first()
        if not warning:
            return False
        warning.is_resolved = True
        warning.resolved_at = datetime.now()
        if relationship_improvement is not None:
            warning.resolution_note = f"关系改善度：{relationship_improvement}"
        return True


# 全局服务实例
emotion_warning_service = EmotionWarningService()
