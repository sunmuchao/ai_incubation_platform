"""
P11 感官洞察服务层实现

包含：
1. AI 视频面诊（情感翻译官）- 微表情捕捉、语音情感分析、情感报告生成
2. 物理安全守护神 - 位置安全监测、语音异常检测、分级响应机制

注意：SafetyMonitoringService 已拆分到 p11_safety_service.py
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from models.p11_models import (
    EmotionAnalysisDB, EmotionReportDB, EmotionalTrendDB,
    SensoryInsightDB, MicroExpressionPatternDB, VoicePatternDB
)

from utils.logger import logger
from utils.db_session_manager import db_session, db_session_readonly

# 从拆分文件导入安全监控服务
from services.p11_safety_service import SafetyMonitoringService, safety_monitoring_service


# ============= P11-001: AI 视频面诊/情感分析服务 =============

class EmotionAnalysisService:
    """情感分析服务 - AI 视频面诊核心"""

    # 支持的情感列表
    SUPPORTED_EMOTIONS = [
        "happiness", "sadness", "anger", "fear", "surprise", "disgust",
        "contempt", "nervousness", "excitement", "confidence", "comfort",
        "interest", "boredom", "attraction", "repulsion"
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

    def __init__(self) -> None:
        pass

    def analyze_micro_expression(
        self,
        user_id: str,
        session_id: str,
        facial_data: Dict[str, Any],
        db_session_param: Optional[Session] = None,
        session_type: str = "video_interview"
    ) -> str:
        """
        分析微表情数据

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            facial_data: 面部识别数据（来自计算机视觉模型）
            db_session_param: 数据库会话
            session_type: 会话类型 (video_interview, date_review, check_in)

        Returns:
            分析记录 ID
        """
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._analyze_micro_expression_internal(user_id, session_id, facial_data, db, session_type)
            else:
                return self._analyze_micro_expression_internal(user_id, session_id, facial_data, db_session_param, session_type)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _analyze_micro_expression_internal(
        self,
        user_id: str,
        session_id: str,
        facial_data: Dict[str, Any],
        db: Session,
        session_type: str = "video_interview"
    ) -> str:
        """内部方法：分析微表情数据"""
        # 提取微表情特征
        detected_emotions = self._extract_emotions_from_facial_data(facial_data)
        facial_action_units = facial_data.get("action_units", [])

        # 计算主导情感
        dominant_emotion = max(detected_emotions, key=lambda x: x.get("confidence", 0)) if detected_emotions else None

        # 计算情绪强度
        emotional_intensity = sum(e.get("confidence", 0) for e in detected_emotions) / max(len(detected_emotions), 1)

        # 计算真实性评分（基于微笑的真诚度、眼神接触等）
        authenticity_score = self._calculate_authenticity_score(facial_data, detected_emotions)

        # 检测不一致性
        inconsistency_flags = self._detect_inconsistencies(facial_data, detected_emotions)

        # 创建分析记录
        analysis_id = str(uuid.uuid4())
        analysis = EmotionAnalysisDB(
            id=analysis_id,
            user_id=user_id,
            session_id=session_id,
            session_type=session_type,
            analysis_type="micro_expression",
            micro_expressions={
                "detected_emotions": detected_emotions,
                "facial_action_units": facial_action_units,
                "dominant_emotion": dominant_emotion["emotion"] if dominant_emotion else None,
                "emotional_intensity": emotional_intensity,
                "authenticity_score": authenticity_score
            },
            combined_emotion=dominant_emotion["emotion"] if dominant_emotion else None,
            emotion_confidence=dominant_emotion.get("confidence", 0) if dominant_emotion else 0,
            authenticity_score=authenticity_score,
            inconsistency_flags=inconsistency_flags,
            ai_insights=self._generate_micro_expression_insights(detected_emotions, facial_data),
            analyzed_at=datetime.utcnow()
        )

        db.add(analysis)
        # auto-commits

        logger.info(f"Micro expression analysis completed: {analysis_id}, user: {user_id}")
        return analysis_id

    def analyze_voice_emotion(
        self,
        user_id: str,
        session_id: str,
        voice_data: Dict[str, Any],
        db_session_param: Optional[Session] = None,
        session_type: str = "video_interview"
    ) -> str:
        """
        分析语音情感

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            voice_data: 语音特征数据（来自语音分析模型）
            db_session_param: 数据库会话
            session_type: 会话类型

        Returns:
            分析记录 ID
        """
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._analyze_voice_emotion_internal(user_id, session_id, voice_data, db, session_type)
            else:
                return self._analyze_voice_emotion_internal(user_id, session_id, voice_data, db_session_param, session_type)
        finally:
            if use_context:
                pass  # Context manager handles cleanup

    def _analyze_voice_emotion_internal(
        self,
        user_id: str,
        session_id: str,
        voice_data: Dict[str, Any],
        db: Session,
        session_type: str = "video_interview"
    ) -> str:
        """内部方法：分析语音情感"""
        # 提取语音情感
        detected_emotions = self._extract_emotions_from_voice_data(voice_data)

        # 计算主导情感
        dominant_emotion = max(detected_emotions, key=lambda x: x.get("confidence", 0)) if detected_emotions else None

        # 计算情感稳定性
        emotional_stability = self._calculate_emotional_stability(voice_data)

        # 创建分析记录
        analysis_id = str(uuid.uuid4())
        analysis = EmotionAnalysisDB(
            id=analysis_id,
            user_id=user_id,
            session_id=session_id,
            session_type=session_type,
            analysis_type="voice_emotion",
            voice_emotions={
                "detected_emotions": detected_emotions,
                "voice_features": voice_data.get("features", {}),
                "dominant_emotion": dominant_emotion["emotion"] if dominant_emotion else None,
                "emotional_stability": emotional_stability
            },
            combined_emotion=dominant_emotion["emotion"] if dominant_emotion else None,
            emotion_confidence=dominant_emotion.get("confidence", 0) if dominant_emotion else 0,
            ai_insights=self._generate_voice_emotion_insights(detected_emotions, voice_data),
            analyzed_at=datetime.utcnow()
        )

        db.add(analysis)
        # auto-commits

        logger.info(f"Voice emotion analysis completed: {analysis_id}, user: {user_id}")
        return analysis_id

    def combined_analysis(
        self,
        user_id: str,
        session_id: str,
        facial_data: Dict[str, Any],
        voice_data: Dict[str, Any],
        db_session_param: Optional[Session] = None,
        session_type: str = "video_interview"
    ) -> str:
        """
        综合分析（微表情 + 语音）

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            facial_data: 面部数据
            voice_data: 语音数据
            db_session_param: 数据库会话
            session_type: 会话类型

        Returns:
            分析记录 ID
        """
        with db_session() as db:
            # 分别分析
            face_emotions = self._extract_emotions_from_facial_data(facial_data)
            voice_emotions = self._extract_emotions_from_voice_data(voice_data)

            # 合并情感
            all_emotions = self._merge_emotion_lists(face_emotions, voice_emotions)
            dominant_emotion = max(all_emotions, key=lambda x: x.get("confidence", 0)) if all_emotions else None

            # 检测不一致性（语音和面部表情不匹配）
            inconsistency_flags = self._detect_cross_modal_inconsistencies(face_emotions, voice_emotions)

            # 生成综合洞察
            ai_insights = self._generate_combined_insights(all_emotions, facial_data, voice_data)

            # 创建综合分析记录
            analysis_id = str(uuid.uuid4())
            analysis = EmotionAnalysisDB(
                id=analysis_id,
                user_id=user_id,
                session_id=session_id,
                session_type=session_type,
                analysis_type="combined_analysis",
                micro_expressions={
                    "detected_emotions": face_emotions,
                    "dominant_emotion": face_emotions[0]["emotion"] if face_emotions else None
                },
                voice_emotions={
                    "detected_emotions": voice_emotions,
                    "dominant_emotion": voice_emotions[0]["emotion"] if voice_emotions else None
                },
                combined_emotion=dominant_emotion["emotion"] if dominant_emotion else None,
                emotion_confidence=dominant_emotion.get("confidence", 0) if dominant_emotion else 0,
                emotional_state_summary=self._generate_emotional_state_summary(all_emotions),
                inconsistency_flags=inconsistency_flags,
                ai_insights=ai_insights,
                emotional_intelligence_tips=self._generate_eq_tips(all_emotions, facial_data, voice_data),
                analyzed_at=datetime.utcnow()
            )

            db.add(analysis)
            # auto-commits

            logger.info(f"Combined emotion analysis completed: {analysis_id}, user: {user_id}")
            return analysis_id

    def get_analysis_by_session(
        self,
        session_id: str,
        db_session_param: Optional[Session] = None
    ) -> Optional[EmotionAnalysisDB]:
        """获取会话的情感分析记录"""
        with db_session_readonly() as db:
            analysis = db.query(EmotionAnalysisDB).filter(
                EmotionAnalysisDB.session_id == session_id
            ).order_by(desc(EmotionAnalysisDB.created_at)).first()
            return analysis

    def get_user_analyses(
        self,
        user_id: str,
        limit: int = 10,
        db_session_param: Optional[Session] = None
    ) -> List[EmotionAnalysisDB]:
        """获取用户的情感分析历史"""
        with db_session_readonly() as db:
            return db.query(EmotionAnalysisDB).filter(
                EmotionAnalysisDB.user_id == user_id
            ).order_by(desc(EmotionAnalysisDB.created_at)).limit(limit).all()

    # ========== 辅助方法 ==========

    def _extract_emotions_from_facial_data(self, facial_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从面部数据提取情感"""
        detected = []
        expressions = facial_data.get("expressions", [])

        for expr in expressions:
            expr_type = expr.get("type", "")
            confidence = expr.get("confidence", 0.5)
            duration_ms = expr.get("duration_ms", 0)

            emotion = self.MICRO_EXPRESSION_TO_EMOTION.get(expr_type, None)
            if emotion:
                detected.append({
                    "emotion": emotion,
                    "confidence": confidence,
                    "duration_ms": duration_ms,
                    "source": "facial"
                })

        # 按置信度排序
        return sorted(detected, key=lambda x: x["confidence"], reverse=True)

    def _extract_emotions_from_voice_data(self, voice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从语音数据提取情感"""
        detected = []
        features = voice_data.get("features", {})
        emotions = voice_data.get("detected_emotions", [])

        for emo in emotions:
            detected.append({
                "emotion": emo.get("emotion", "unknown"),
                "confidence": emo.get("confidence", 0.5),
                "source": "voice"
            })

        # 基于语音特征推断情感
        pitch = features.get("pitch_avg", 200)
        speech_rate = features.get("speech_rate", 4.0)
        volume_var = features.get("volume_variance", 10)

        # 高音调 + 快语速 = 兴奋/紧张
        if pitch > 250 and speech_rate > 5:
            detected.append({
                "emotion": "excitement",
                "confidence": 0.6,
                "source": "voice_features"
            })

        # 低音调 + 慢语速 = 悲伤/不适
        if pitch < 150 and speech_rate < 3:
            detected.append({
                "emotion": "sadness",
                "confidence": 0.5,
                "source": "voice_features"
            })

        return sorted(detected, key=lambda x: x["confidence"], reverse=True)

    def _merge_emotion_lists(
        self,
        face_emotions: List[Dict[str, Any]],
        voice_emotions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并两个情感列表，聚合相同情感"""
        emotion_map = {}

        for emo in face_emotions + voice_emotions:
            emotion = emo["emotion"]
            if emotion not in emotion_map:
                emotion_map[emotion] = {
                    "emotion": emotion,
                    "confidence": emo["confidence"],
                    "sources": [emo.get("source", "unknown")]
                }
            else:
                # 平均置信度
                emotion_map[emotion]["confidence"] = (emotion_map[emotion]["confidence"] + emo["confidence"]) / 2
                emotion_map[emotion]["sources"].append(emo.get("source", "unknown"))

        return sorted(emotion_map.values(), key=lambda x: x["confidence"], reverse=True)

    def _calculate_authenticity_score(self, facial_data: Dict[str, Any], emotions: List[Dict[str, Any]]) -> float:
        """计算真实性评分"""
        score = 0.5  # 基础分

        # 检查是否有真诚的微笑（眼睛周围的皱纹）
        if facial_data.get("crow_feet", False):
            score += 0.2

        # 检查眼神接触
        eye_contact = facial_data.get("eye_contact_duration", 0)
        if eye_contact > 0.6:  # 60% 的时间有眼神接触
            score += 0.15

        # 检查情感一致性
        if len(emotions) > 0:
            dominant = emotions[0]
            if dominant["emotion"] == "happiness" and dominant["confidence"] > 0.7:
                score += 0.1

        return min(score, 1.0)

    def _calculate_emotional_stability(self, voice_data: Dict[str, Any]) -> float:
        """计算情感稳定性"""
        features = voice_data.get("features", {})

        # 基于音调和音量的方差计算稳定性
        pitch_var = features.get("pitch_variance", 0)
        volume_var = features.get("volume_variance", 0)

        # 方差越小越稳定
        stability = 1.0 - (pitch_var / 100 + volume_var / 50) / 2
        return max(0.0, min(1.0, stability))

    def _detect_inconsistencies(self, facial_data: Dict[str, Any], emotions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测不一致性"""
        flags = []

        # 检测微笑但眼神回避
        has_smile = any(e["emotion"] == "happiness" for e in emotions)
        eye_avoidance = facial_data.get("eye_avoidance", False)

        if has_smile and eye_avoidance:
            flags.append({
                "type": "smile_eye_mismatch",
                "description": "微笑但眼神回避，可能是勉强或紧张",
                "severity": "medium"
            })

        return flags

    def _detect_cross_modal_inconsistencies(
        self,
        face_emotions: List[Dict[str, Any]],
        voice_emotions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """检测跨模态不一致性"""
        flags = []

        if not face_emotions or not voice_emotions:
            return flags

        face_dominant = face_emotions[0]["emotion"]
        voice_dominant = voice_emotions[0]["emotion"]

        # 对立情感检测
        opposite_pairs = [
            ("happiness", "sadness"),
            ("anger", "comfort"),
            ("excitement", "boredom")
        ]

        for pair in opposite_pairs:
            if (face_dominant in pair and voice_dominant in pair and face_dominant != voice_dominant):
                flags.append({
                    "type": "voice_face_mismatch",
                    "description": f"面部表情显示{face_dominant}，但语音显示{voice_dominant}",
                    "severity": "high"
                })
                break

        return flags

    def _generate_micro_expression_insights(self, emotions: List[Dict[str, Any]], facial_data: Dict[str, Any]) -> str:
        """生成微表情分析洞察"""
        if not emotions:
            return "未能检测到明显的情感表达"

        dominant = emotions[0]
        insights = []

        if dominant["emotion"] == "happiness":
            insights.append(f"检测到真诚的喜悦情绪（置信度：{dominant['confidence']:.0%}）")
        elif dominant["emotion"] == "nervousness":
            insights.append("可能处于紧张或不安状态，建议适当放松")
        elif dominant["emotion"] == "interest":
            insights.append("对话题表现出浓厚兴趣")
        elif dominant["emotion"] == "attraction":
            insights.append("检测到吸引力信号")

        return json.dumps({
            "dominant_emotion": dominant["emotion"],
            "confidence": dominant["confidence"],
            "insights": insights,
            "all_detected": [e["emotion"] for e in emotions]
        }, ensure_ascii=False)

    def _generate_voice_emotion_insights(self, emotions: List[Dict[str, Any]], voice_data: Dict[str, Any]) -> str:
        """生成语音情感洞察"""
        if not emotions:
            return "未能从语音中检测到明显的情感"

        dominant = emotions[0]
        features = voice_data.get("features", {})

        insights = []
        if dominant["emotion"] == "excitement":
            insights.append("语音中带有明显的兴奋情绪")
        elif dominant["emotion"] == "confidence":
            insights.append("语音表现出自信")
        elif dominant["emotion"] == "nervousness":
            insights.append("语音可能透露出紧张感")

        speech_rate = features.get("speech_rate", 4.0)
        if speech_rate > 5:
            insights.append("语速较快，可能反映兴奋或紧张")
        elif speech_rate < 3:
            insights.append("语速较慢，可能反映深思或不适")

        return json.dumps({
            "dominant_emotion": dominant["emotion"],
            "confidence": dominant["confidence"],
            "insights": insights
        }, ensure_ascii=False)

    def _generate_combined_insights(
        self,
        emotions: List[Dict[str, Any]],
        facial_data: Dict[str, Any],
        voice_data: Dict[str, Any]
    ) -> str:
        """生成综合分析洞察"""
        if not emotions:
            return "未能生成综合分析结果"

        dominant = emotions[0]
        sources = dominant.get("sources", [])

        # 多模态一致性检查
        if len(sources) > 1:
            consistency_msg = "面部表情和语音情感一致，可信度高"
        else:
            consistency_msg = f"主要基于{sources[0]}的情感分析"

        insights = {
            "dominant_emotion": dominant["emotion"],
            "confidence": dominant["confidence"],
            "consistency": consistency_msg,
            "recommendation": self._get_interaction_recommendation(dominant["emotion"])
        }

        return json.dumps(insights, ensure_ascii=False)

    def _get_interaction_recommendation(self, emotion: str) -> str:
        """根据情感给出互动建议"""
        recommendations = {
            "happiness": "保持当前的积极互动节奏",
            "nervousness": "可以适当放缓节奏，给予更多安全感",
            "interest": "继续深入当前话题，探索共同兴趣",
            "excitement": "利用当前的积极情绪，推进关系发展",
            "sadness": "表达关心和支持，给予情感安慰",
            "anger": "暂缓敏感话题，等情绪平复后再沟通",
            "boredom": "尝试引入新话题或活动建议",
            "attraction": "可以适度表达好感，观察对方反应"
        }
        return recommendations.get(emotion, "保持自然，继续观察")

    def _generate_emotional_state_summary(self, emotions: List[Dict[str, Any]]) -> str:
        """生成情感状态总结"""
        if not emotions:
            return "无明显情感"

        dominant = emotions[0]
        intensity = "强烈" if dominant["confidence"] > 0.8 else "中等" if dominant["confidence"] > 0.5 else "轻微"

        emotion_cn = {
            "happiness": "喜悦",
            "sadness": "悲伤",
            "anger": "愤怒",
            "fear": "恐惧",
            "surprise": "惊讶",
            "nervousness": "紧张",
            "excitement": "兴奋",
            "interest": "兴趣",
            "attraction": "吸引",
            "boredom": "无聊",
            "comfort": "舒适"
        }

        return f"主导情感：{emotion_cn.get(dominant['emotion'], dominant['emotion'])}（{intensity}）"

    def _generate_eq_tips(
        self,
        emotions: List[Dict[str, Any]],
        facial_data: Dict[str, Any],
        voice_data: Dict[str, Any]
    ) -> str:
        """生成情商建议"""
        if not emotions:
            return "保持自然表达即可"

        dominant = emotions[0]
        tips = []

        if dominant["emotion"] == "nervousness":
            tips.append("尝试深呼吸放松，紧张是约会中的正常反应")
        if dominant["emotion"] == "excitement":
            tips.append("保持兴奋的同时，注意倾听对方")
        if facial_data.get("eye_avoidance"):
            tips.append("适当的眼神接触可以增进连接感")
        if voice_data.get("features", {}).get("speech_rate", 4) > 5:
            tips.append("语速稍快，可以尝试放慢语速以便更好沟通")

        return json.dumps(tips, ensure_ascii=False) if tips else "情感状态良好，继续保持"


# ============= P11-003: 情感报告服务 =============

class EmotionReportService:
    """情感报告生成服务"""

    def __init__(self, emotion_analysis_service: Optional[EmotionAnalysisService] = None):
        self.emotion_analysis_service = emotion_analysis_service or EmotionAnalysisService()

    def generate_session_report(
        self,
        user_id: str,
        session_id: str,
        db_session: Optional[Session] = None
    ) -> str:
        """
        生成会话情感报告

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            db_session: 数据库会话

        Returns:
            报告 ID
        """
        db = db_session if db_session else SessionLocal()
        should_close = db_session is None

        try:
            # 获取会话的分析记录
            analyses = db.query(EmotionAnalysisDB).filter(
                and_(
                    EmotionAnalysisDB.user_id == user_id,
                    EmotionAnalysisDB.session_id == session_id
                )
            ).all()

            if not analyses:
                raise ValueError(f"No analyses found for session {session_id}")

            # 汇总情感数据
            all_emotions = []
            for analysis in analyses:
                if analysis.micro_expressions:
                    emotions = analysis.micro_expressions.get("detected_emotions", [])
                    all_emotions.extend(emotions)
                if analysis.voice_emotions:
                    emotions = analysis.voice_emotions.get("detected_emotions", [])
                    all_emotions.extend(emotions)

            # 计算情感分布
            emotion_distribution = self._calculate_emotion_distribution(all_emotions)

            # 生成报告
            report_id = str(uuid.uuid4())
            report = EmotionReportDB(
                id=report_id,
                user_id=user_id,
                session_id=session_id,
                report_type="session_summary",
                title=f"情感分析报告 - {session_id}",
                summary=self._generate_report_summary(emotion_distribution),
                detailed_analysis=json.dumps({
                    "emotion_distribution": emotion_distribution,
                    "dominant_emotions": sorted(emotion_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
                    "analysis_count": len(analyses)
                }, ensure_ascii=False),
                emotional_metrics={
                    "overall_positivity": self._calculate_positivity(emotion_distribution),
                    "emotional_diversity": len(emotion_distribution) / 10.0,
                    "dominant_emotion": max(emotion_distribution, key=emotion_distribution.get) if emotion_distribution else None
                },
                action_items=json.dumps(self._generate_action_items(emotion_distribution), ensure_ascii=False)
            )

            db.add(report)
            db.commit()
            db.refresh(report)

            logger.info(f"Emotion report generated: {report_id}")
            return report_id

        except Exception as e:
            db.rollback()
            logger.error(f"Error generating emotion report: {e}")
            raise
        finally:
            if should_close:
                db.close()

    def get_user_reports(
        self,
        user_id: str,
        limit: int = 10,
        db_session: Optional[Session] = None
    ) -> List[EmotionReportDB]:
        """获取用户的情感报告"""
        db = db_session if db_session else SessionLocal()
        should_close = db_session is None

        try:
            return db.query(EmotionReportDB).filter(
                EmotionReportDB.user_id == user_id
            ).order_by(desc(EmotionReportDB.created_at)).limit(limit).all()
        finally:
            if should_close:
                db.close()

    def _calculate_emotion_distribution(self, emotions: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算情感分布"""
        distribution = {}
        total_weight = 0

        for emo in emotions:
            emotion = emo.get("emotion", "unknown")
            confidence = emo.get("confidence", 0.5)
            if emotion not in distribution:
                distribution[emotion] = 0
            distribution[emotion] += confidence
            total_weight += confidence

        # 归一化
        if total_weight > 0:
            for emotion in distribution:
                distribution[emotion] /= total_weight

        return distribution

    def _generate_report_summary(self, distribution: Dict[str, float]) -> str:
        """生成报告摘要"""
        if not distribution:
            return "未检测到明显的情感模式"

        dominant = max(distribution, key=distribution.get)
        dominant_pct = distribution[dominant] * 100

        emotion_cn = {
            "happiness": "喜悦",
            "excitement": "兴奋",
            "interest": "兴趣",
            "attraction": "吸引",
            "nervousness": "紧张",
            "comfort": "舒适",
            "sadness": "悲伤",
            "anger": "愤怒"
        }

        return f"本次会话中，主导情感为{emotion_cn.get(dominant, dominant)}（{dominant_pct:.0f}%）"

    def _calculate_positivity(self, distribution: Dict[str, float]) -> float:
        """计算积极度"""
        positive_emotions = {"happiness", "excitement", "interest", "attraction", "comfort"}
        negative_emotions = {"sadness", "anger", "fear", "disgust", "boredom"}

        positive = sum(distribution.get(e, 0) for e in positive_emotions)
        negative = sum(distribution.get(e, 0) for e in negative_emotions)

        if positive + negative == 0:
            return 0.5

        return positive / (positive + negative)

    def _generate_action_items(self, distribution: Dict[str, float]) -> List[str]:
        """生成行动建议"""
        items = []

        if distribution.get("nervousness", 0) > 0.3:
            items.append("检测到紧张情绪，可以尝试深呼吸或放松技巧")
        if distribution.get("sadness", 0) > 0.2:
            items.append("情绪较为低落，建议与信任的人交流")
        if distribution.get("happiness", 0) > 0.5:
            items.append("情绪积极，是深化关系的好时机")
        if distribution.get("interest", 0) > 0.4:
            items.append("对话题表现出兴趣，可以继续深入探讨")

        return items if items else ["保持自然，享受当下"]


# 服务实例
emotion_analysis_service = EmotionAnalysisService()
safety_monitoring_service = SafetyMonitoringService()
emotion_report_service = EmotionReportService()
