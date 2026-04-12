"""
Behavior 行为实验室 - 爱之语翻译服务

爱之语翻译服务 - 解读真实意图、提供回应建议
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import re
from db.database import SessionLocal
from models.behavior_lab_models import LoveLanguageTranslationDB
from utils.logger import logger
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session


class LoveLanguageTranslationService:
    """爱之语翻译服务"""

    # 五种爱之语类型
    LOVE_LANGUAGES = {
        "WORDS_OF_AFFIRMATION": "words",  # 肯定的言辞
        "QUALITY_TIME": "time",  # 精心时刻
        "RECEIVING_GIFTS": "gifts",  # 接受礼物
        "ACTS_OF_SERVICE": "acts",  # 服务的行动
        "PHYSICAL_TOUCH": "touch",  # 身体的接触
    }

    # 表达方式模式
    EXPRESSION_PATTERNS = {
        "words": [
            r"喜欢.*你", r"爱.*你", r"你.*好", r"欣赏", r"赞美",
            r"谢谢", r"感谢", r"做得好", r"很棒", r"骄傲"
        ],
        "time": [
            r"一起", r"陪伴", r"时间", r"见面", r"约会",
            r"聊天", r"说话", r"待着", r"共处"
        ],
        "gifts": [
            r"送.*你", r"礼物", r"买.*给", r"准备.*惊喜",
            r"收到", r"快递", r"包裹"
        ],
        "acts": [
            r"帮你", r"为你", r"替你", r"帮你做", r"帮忙",
            r"照顾", r"处理", r"准备.*饭", r"接.*下班"
        ],
        "touch": [
            r"拥抱", r"牵手", r"亲吻", r"摸", r"靠",
            r"抱抱", r"靠.*我", r"拉手"
        ]
    }

    # 需求表达模式（表面 vs 真实意图）
    NEED_PATTERNS = {
        "words": {
            "patterns": [r"你都不.*我", r"你从来不.*我", r"你有多久.*我"],
            "true_intention": "希望得到更多的肯定和赞美",
            "suggested_response_template": "我真的很欣赏你{specific_quality}，谢谢你一直以来的{contribution}"
        },
        "time": {
            "patterns": [r"你总是.*忙", r"你都没时间.*我", r"我们好久没.*一起"],
            "true_intention": "渴望更多的陪伴和关注",
            "suggested_response_template": "你说得对，我确实应该花更多时间陪你。我们{specific_activity}怎么样？"
        },
        "gifts": {
            "patterns": [r"你都不.*惊喜", r"别人都有.*礼物", r"你记得.*日子"],
            "true_intention": "希望被重视和用心对待",
            "suggested_response_template": "我想为你准备一个惊喜，你最近有想要什么特别的东西吗？"
        },
        "acts": {
            "patterns": [r"都是.*我做", r"你从来不.*家务", r"你就不能.*一下"],
            "true_intention": "希望分担和体贴",
            "suggested_response_template": "我来处理{specific_task}吧，你休息一下。还有什么我可以帮你的？"
        },
        "touch": {
            "patterns": [r"你都不.*抱我", r"我们好久没.*亲密", r"你离我.*远"],
            "true_intention": "渴望身体接触和亲密感",
            "suggested_response_template": "过来让我抱抱你。（主动的身体接触）"
        }
    }

    def translate_expression(
        self,
        user_id: str,
        target_user_id: str,
        expression: str,
        db_session_param: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        翻译爱的表达，解读真实意图

        Args:
            user_id: 表达者 ID
            target_user_id: 接收者 ID
            expression: 原始表达
            db_session_param: 可选的数据库会话

        Returns:
            翻译结果，包括真实意图和建议回应
        """
        with optional_db_session(db_session_param) as db:
            # 分析原始表达的情感
            original_sentiment = self._analyze_sentiment(expression)

            # 识别爱之语类型
            love_language = self._identify_love_language(expression)

            # 识别潜在需求
            need_analysis = self._identify_underlying_need(expression)

            # 生成真实意图解读
            if need_analysis:
                true_intention = need_analysis["true_intention"]
                suggested_response = need_analysis["suggested_response"]
                response_explanation = f"对方可能在表达{need_analysis['love_language']}类型的需求。"
            else:
                true_intention = self._generate_true_intention(expression, love_language)
                suggested_response = self._generate_suggested_response(expression, love_language)
                response_explanation = f"这是一个{love_language}类型的表达。"

            # 获取双方的爱之语偏好（如果可用）
            user_love_language = self._get_user_love_language(user_id, db)
            target_love_language = self._get_user_love_language(target_user_id, db)

            # 计算翻译置信度
            confidence_score = self._calculate_confidence(expression, love_language, need_analysis)

            # 创建翻译记录
            translation_id = f"trans_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id[:4]}"

            translation = LoveLanguageTranslationDB(
                id=translation_id,
                user_id=user_id,
                target_user_id=target_user_id,
                original_expression=expression,
                original_sentiment=original_sentiment,
                true_intention=true_intention,
                suggested_response=suggested_response,
                response_explanation=response_explanation,
                user_love_language=user_love_language,
                target_love_language=target_love_language,
                confidence_score=confidence_score
            )

            db.add(translation)

            logger.info(f"Translated love expression: {translation_id}")

            return {
                "id": translation_id,
                "original_expression": expression,
                "original_sentiment": original_sentiment,
                "true_intention": true_intention,
                "suggested_response": suggested_response,
                "response_explanation": response_explanation,
                "identified_love_language": love_language,
                "user_love_language": user_love_language,
                "target_love_language": target_love_language,
                "confidence_score": confidence_score
            }

    def submit_feedback(
        self,
        translation_id: str,
        feedback: str,
        db_session_param: Optional[Any] = None
    ) -> bool:
        """提交翻译反馈"""
        if db_session_param:
            return self._submit_feedback_internal(translation_id, feedback, db_session_param)
        else:
            with db_session() as db:
                return self._submit_feedback_internal(translation_id, feedback, db)

    def _submit_feedback_internal(self, translation_id: str, feedback: str, db: Any) -> bool:
        """提交翻译反馈内部方法"""
        translation = db.query(LoveLanguageTranslationDB).filter(
            LoveLanguageTranslationDB.id == translation_id
        ).first()

        if not translation:
            logger.warning(f"Translation not found: {translation_id}")
            return False

        translation.user_feedback = feedback
        logger.info(f"Submitted feedback for translation: {translation_id}")
        return True

    def get_user_translations(
        self,
        user_id: str,
        limit: int = 20,
        db_session_param: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """获取用户的翻译历史"""
        if db_session_param:
            return self._get_user_translations_internal(user_id, limit, db_session_param)
        else:
            with db_session_readonly() as db:
                return self._get_user_translations_internal(user_id, limit, db)

    def _get_user_translations_internal(self, user_id: str, limit: int, db: Any) -> List[Dict[str, Any]]:
        """获取用户翻译历史内部方法"""
        translations = db.query(LoveLanguageTranslationDB).filter(
            (LoveLanguageTranslationDB.user_id == user_id) |
            (LoveLanguageTranslationDB.target_user_id == user_id)
        ).order_by(
            LoveLanguageTranslationDB.created_at.desc()
        ).limit(limit).all()

        return [self._translation_to_dict(t) for t in translations]

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """分析情感"""
        positive_words = ["开心", "喜欢", "爱", "高兴", "幸福", "温暖", "感动", "谢谢"]
        negative_words = ["难过", "生气", "失望", "伤心", "抱怨", "不满", "讨厌"]

        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        if pos_count > neg_count:
            polarity = "positive"
            score = min(1.0, pos_count * 0.2)
        elif neg_count > pos_count:
            polarity = "negative"
            score = min(1.0, neg_count * 0.2)
        else:
            polarity = "neutral"
            score = 0.0

        return {
            "polarity": polarity,
            "score": score,
            "positive_count": pos_count,
            "negative_count": neg_count
        }

    def _identify_love_language(self, text: str) -> str:
        """识别爱之语类型"""
        text_lower = text.lower()
        scores = {}

        for language_type, patterns in self.EXPRESSION_PATTERNS.items():
            score = sum(1 for pattern in patterns if re.search(pattern, text_lower))
            scores[language_type] = score

        if max(scores.values()) == 0:
            return "unknown"

        return max(scores, key=scores.get)

    def _identify_underlying_need(self, text: str) -> Optional[Dict[str, Any]]:
        """识别潜在需求"""
        text_lower = text.lower()

        for language_type, need_data in self.NEED_PATTERNS.items():
            for pattern in need_data["patterns"]:
                if re.search(pattern, text_lower):
                    return {
                        "love_language": language_type,
                        "true_intention": need_data["true_intention"],
                        "suggested_response": need_data["suggested_response_template"],
                        "matched_pattern": pattern
                    }

        return None

    def _generate_true_intention(self, expression: str, love_language: str) -> str:
        """生成真实意图解读"""
        intentions = {
            "words": "希望得到你的肯定、赞美或感谢",
            "time": "希望能和你共度时光，得到你的关注",
            "gifts": "希望能感受到你的用心和重视",
            "acts": "希望你能主动分担，体贴 ta 的辛苦",
            "touch": "渴望和你有身体接触，感受亲密",
            "unknown": "表达某种情感需求，需要进一步沟通理解"
        }
        return intentions.get(love_language, intentions["unknown"])

    def _generate_suggested_response(self, expression: str, love_language: str) -> str:
        """生成建议回应"""
        responses = {
            "words": "我真的很欣赏你，你对我来说很重要。谢谢你为我做的一切。",
            "time": "我确实应该花更多时间陪你。我们一起做些你想做的事情吧？",
            "gifts": "我想为你准备一个惊喜。你有什么特别想要的东西吗？",
            "acts": "让我来帮你处理吧，你休息一下。还有什么我可以做的？",
            "touch": "（给对方一个温暖的拥抱）我在这里陪着你。",
            "unknown": "我理解你的感受，我们好好聊聊好吗？"
        }
        return responses.get(love_language, responses["unknown"])

    def _calculate_confidence(
        self,
        expression: str,
        love_language: str,
        need_analysis: Optional[Dict[str, Any]]
    ) -> float:
        """计算翻译置信度"""
        confidence = 0.5  # 基础置信度

        # 如果识别到明确的爱之语类型
        if love_language != "unknown":
            confidence += 0.2

        # 如果匹配到需求模式
        if need_analysis:
            confidence += 0.3

        # 表达长度适中（太短可能信息不足）
        if 10 <= len(expression) <= 100:
            confidence += 0.1

        return min(0.95, confidence)

    def _get_user_love_language(self, user_id: str, db: Any) -> str:
        """获取用户的爱之语偏好（简化实现）"""
        # 实际实现应该从用户档案中读取
        # 这里从历史翻译记录中推断
        translations = db.query(LoveLanguageTranslationDB).filter(
            LoveLanguageTranslationDB.user_id == user_id
        ).limit(10).all()

        if not translations:
            return "unknown"

        language_counts = defaultdict(int)
        for t in translations:
            if t.user_love_language and t.user_love_language != "unknown":
                language_counts[t.user_love_language] += 1

        if language_counts:
            return max(language_counts, key=language_counts.get)

        return "unknown"

    def _translation_to_dict(self, translation: LoveLanguageTranslationDB) -> Dict[str, Any]:
        """将翻译对象转换为字典"""
        return {
            "id": translation.id,
            "user_id": translation.user_id,
            "target_user_id": translation.target_user_id,
            "original_expression": translation.original_expression,
            "original_sentiment": translation.original_sentiment,
            "true_intention": translation.true_intention,
            "suggested_response": translation.suggested_response,
            "response_explanation": translation.response_explanation,
            "user_love_language": translation.user_love_language,
            "target_love_language": translation.target_love_language,
            "confidence_score": translation.confidence_score,
            "user_feedback": translation.user_feedback,
            "created_at": translation.created_at.isoformat() if translation.created_at else None
        }


# 全局服务实例
love_language_service = LoveLanguageTranslationService()
