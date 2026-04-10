"""
P13 情感调解增强服务层

在 P12 基础上增强：
1. 爱之语画像服务 - 学习和管理用户爱之语偏好
2. 关系趋势预测服务 - 预测关系发展趋势
3. 预警分级响应服务 - 根据风险级别自动响应
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import random

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from db.models import UserDB, ConversationDB, ChatMessageDB
from models.p13_models import (
    UserLoveLanguageProfileDB,
    RelationshipTrendPredictionDB,
    WarningResponseStrategyDB,
    WarningResponseRecordDB,
    EmotionMediationStatsDB,
    LoveLanguageType
)
from models.p12_models import EmotionWarningDB, LoveLanguageTranslationDB, RelationshipWeatherReportDB
from utils.logger import logger


class LoveLanguageProfileService:
    """爱之语画像服务"""

    # 爱之语关键词映射
    LOVE_LANGUAGE_KEYWORDS = {
        LoveLanguageType.WORDS.value: [
            "喜欢", "爱", "赞美", "感谢", "鼓励", "肯定", "认可",
            "聪明", "漂亮", "厉害", "棒", "好", "谢谢", "感动"
        ],
        LoveLanguageType.TIME.value: [
            "陪伴", "时间", "一起", "约会", "共度", "看电影", "散步",
            "聊天", "呆着", "守着", "等待", "花时间"
        ],
        LoveLanguageType.GIFTS.value: [
            "礼物", "惊喜", "送", "买", "收到", "心意", "用心",
            "纪念", "特别", "珍贵", "喜欢这个"
        ],
        LoveLanguageType.ACTS.value: [
            "帮忙", "做", "分担", "照顾", "体贴", "服务", "行动",
            "解决", "处理", "准备", "安排", "操心"
        ],
        LoveLanguageType.TOUCH.value: [
            "拥抱", "牵手", "亲密", "接触", "摸", "靠", "抱",
            "亲吻", "靠近", "温暖", "触感"
        ]
    }

    def __init__(self):
        self._initialized = False

    def _ensure_initialized(self, db_session):
        """初始化默认响应策略"""
        if self._initialized:
            return

        # 初始化爱之语画像（如果不存在）
        self._initialize_default_profiles(db_session)
        self._initialized = True

    def _initialize_default_profiles(self, db_session):
        """初始化默认爱之语评估问题"""
        # 这部分可以在未来扩展为完整的评估问卷
        pass

    def analyze_user_love_language(
        self,
        user_id: str,
        db_session
    ) -> Optional[UserLoveLanguageProfileDB]:
        """
        分析用户的爱之语偏好

        通过分析用户的历史对话和翻译记录来推断爱之语偏好
        """
        # 获取用户的所有翻译记录
        translations = db_session.query(LoveLanguageTranslationDB).filter(
            LoveLanguageTranslationDB.user_id == user_id
        ).all()

        if not translations:
            # 没有数据，返回默认画像
            return self._get_default_profile(user_id, db_session)

        # 统计各爱之语类型的得分
        scores = defaultdict(int)
        expression_prefs = defaultdict(int)
        reception_prefs = defaultdict(int)

        for translation in translations:
            # 分析原始表达中的爱之语关键词
            original = translation.original_expression
            for ll_type, keywords in self.LOVE_LANGUAGE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in original:
                        scores[ll_type] += 1

            # 分析真实意图中的爱之语类型
            true_intention = translation.true_intention
            for ll_type, keywords in self.LOVE_LANGUAGE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in true_intention:
                        reception_prefs[ll_type] += 1

            # 分析建议回应中的爱之语类型
            suggested = translation.suggested_response or ""
            for ll_type, keywords in self.LOVE_LANGUAGE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in suggested:
                        expression_prefs[ll_type] += 1

        # 创建或更新画像
        profile = self._get_or_create_profile(user_id, db_session)

        # 更新得分
        profile.words_score = scores.get(LoveLanguageType.WORDS.value, 0)
        profile.time_score = scores.get(LoveLanguageType.TIME.value, 0)
        profile.gifts_score = scores.get(LoveLanguageType.GIFTS.value, 0)
        profile.acts_score = scores.get(LoveLanguageType.ACTS.value, 0)
        profile.touch_score = scores.get(LoveLanguageType.TOUCH.value, 0)

        # 确定主要和次要爱之语
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if sorted_scores:
            profile.primary_love_language = sorted_scores[0][0]
            if len(sorted_scores) > 1:
                profile.secondary_love_language = sorted_scores[1][0]

        # 更新偏好
        profile.expression_preferences = list(expression_prefs.keys())
        profile.reception_preferences = list(reception_prefs.keys())

        # 更新翻译历史
        profile.translation_history_ids = [t.id for t in translations[-50:]]  # 保留最近 50 条

        # 更新置信度（基于数据量）
        profile.assessment_count = len(translations)
        profile.confidence_score = min(1.0, len(translations) / 20.0)  # 20 条记录达到 100% 置信度

        profile.last_updated = datetime.utcnow()

        db_session.commit()
        db_session.refresh(profile)

        return profile

    def _get_or_create_profile(
        self,
        user_id: str,
        db_session
    ) -> UserLoveLanguageProfileDB:
        """获取或创建用户爱之语画像"""
        profile = db_session.query(UserLoveLanguageProfileDB).filter(
            UserLoveLanguageProfileDB.user_id == user_id
        ).first()

        if not profile:
            profile = UserLoveLanguageProfileDB(
                id=f"llp_{user_id}_{datetime.utcnow().timestamp()}",
                user_id=user_id
            )
            db_session.add(profile)
            db_session.commit()

        db_session.refresh(profile)
        return profile

    def _get_default_profile(
        self,
        user_id: str,
        db_session
    ) -> UserLoveLanguageProfileDB:
        """获取默认画像"""
        profile = self._get_or_create_profile(user_id, db_session)
        return profile

    def get_user_profile(
        self,
        user_id: str,
        db_session
    ) -> Optional[Dict[str, Any]]:
        """获取用户爱之语画像"""
        profile = db_session.query(UserLoveLanguageProfileDB).filter(
            UserLoveLanguageProfileDB.user_id == user_id
        ).first()

        if not profile:
            return None

        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "primary_love_language": profile.primary_love_language,
            "secondary_love_language": profile.secondary_love_language,
            "scores": {
                "words": profile.words_score,
                "time": profile.time_score,
                "gifts": profile.gifts_score,
                "acts": profile.acts_score,
                "touch": profile.touch_score
            },
            "expression_preferences": profile.expression_preferences,
            "reception_preferences": profile.reception_preferences,
            "confidence_score": profile.confidence_score,
            "assessment_count": profile.assessment_count,
            "last_updated": profile.last_updated.isoformat() if profile.last_updated else None
        }

    def get_love_language_description(self, love_language: str) -> str:
        """获取爱之语类型的描述"""
        descriptions = {
            LoveLanguageType.WORDS.value: "肯定的言辞 - 你通过赞美、感谢和鼓励来表达和感受爱",
            LoveLanguageType.TIME.value: "精心时刻 - 你通过专注的陪伴和共度时光来表达和感受爱",
            LoveLanguageType.GIFTS.value: "接受礼物 - 你通过礼物和惊喜来表达和感受爱",
            LoveLanguageType.ACTS.value: "服务的行动 - 你通过帮忙和分担来表达和感受爱",
            LoveLanguageType.TOUCH.value: "身体的接触 - 你通过拥抱和亲密接触来表达和感受爱"
        }
        return descriptions.get(love_language, "未知爱之语类型")


class RelationshipTrendService:
    """关系趋势预测服务"""

    # 关系发展阶段
    STAGE_MATCHED = "matched"
    STAGE_CHATTING = "chatting"
    STAGE_DATING = "dating"
    STAGE_IN_RELATIONSHIP = "in_relationship"

    # 趋势类型
    TREND_RISING = "rising"
    TREND_STABLE = "stable"
    TREND_DECLINING = "declining"

    def __init__(self):
        pass

    def generate_trend_prediction(
        self,
        user_a_id: str,
        user_b_id: str,
        prediction_period: str = "7d",
        db_session=None
    ) -> Dict[str, Any]:
        """
        生成关系趋势预测

        参数:
        - user_a_id: 用户 A ID
        - user_b_id: 用户 B ID
        - prediction_period: 预测周期 (7d, 14d, 30d)
        """
        # 获取最近的气象报告
        recent_reports = db_session.query(RelationshipWeatherReportDB).filter(
            ((RelationshipWeatherReportDB.user_a_id == user_a_id) &
             (RelationshipWeatherReportDB.user_b_id == user_b_id)) |
            ((RelationshipWeatherReportDB.user_a_id == user_b_id) &
             (RelationshipWeatherReportDB.user_b_id == user_a_id))
        ).order_by(RelationshipWeatherReportDB.report_date.desc()).limit(5).all()

        if not recent_reports:
            # 没有历史数据，返回基础预测
            return self._get_base_prediction(user_a_id, user_b_id, prediction_period)

        # 分析情感温度趋势
        temperatures = [r.emotional_temperature for r in recent_reports]
        avg_temperature = sum(temperatures) / len(temperatures)

        # 计算趋势
        if len(temperatures) >= 2:
            temp_change = temperatures[0] - temperatures[-1]  # 最近的减最早的
            if temp_change > 5:
                trend = self.TREND_RISING
            elif temp_change < -5:
                trend = self.TREND_DECLINING
            else:
                trend = self.TREND_STABLE
        else:
            trend = self.TREND_STABLE

        # 预测未来情感温度
        if trend == self.TREND_RISING:
            predicted_temp = min(100, avg_temperature + random.uniform(3, 8))
        elif trend == self.TREND_DECLINING:
            predicted_temp = max(0, avg_temperature - random.uniform(3, 8))
        else:
            predicted_temp = avg_temperature + random.uniform(-2, 2)

        # 判断当前关系阶段
        current_stage = self._infer_relationship_stage(recent_reports[0])

        # 预测可能的里程碑
        predicted_milestones = self._predict_milestones(current_stage, trend)

        # 识别风险和机会
        risk_indicators = self._identify_risks(recent_reports, trend)
        opportunity_indicators = self._identify_opportunities(recent_reports, trend)

        # 生成建议行动
        recommended_actions = self._generate_recommendations(
            current_stage, trend, risk_indicators, opportunity_indicators
        )

        # 创建预测记录
        prediction_id = f"rtp_{user_a_id}_{user_b_id}_{datetime.utcnow().timestamp()}"
        prediction = RelationshipTrendPredictionDB(
            id=prediction_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            prediction_base_date=datetime.utcnow(),
            prediction_period=prediction_period,
            current_temperature=avg_temperature,
            predicted_temperature=predicted_temp,
            temperature_trend=trend,
            current_stage=current_stage,
            predicted_stage=self._predict_stage(current_stage, trend),
            stage_change_probability=self._calculate_stage_change_probability(current_stage, trend),
            risk_indicators=risk_indicators,
            opportunity_indicators=opportunity_indicators,
            predicted_milestones=predicted_milestones,
            recommended_actions=recommended_actions,
            model_version="v1.0"
        )

        # 设置过期时间
        days = int(prediction_period.replace("d", ""))
        prediction.expires_at = datetime.utcnow() + timedelta(days=days)

        db_session.add(prediction)
        db_session.commit()
        db_session.refresh(prediction)

        return self._format_prediction(prediction)

    def _infer_relationship_stage(
        self,
        report: RelationshipWeatherReportDB
    ) -> str:
        """根据气象报告推断关系阶段"""
        temp = report.emotional_temperature

        if temp >= 80:
            return self.STAGE_IN_RELATIONSHIP
        elif temp >= 60:
            return self.STAGE_DATING
        elif temp >= 40:
            return self.STAGE_CHATTING
        else:
            return self.STAGE_MATCHED

    def _predict_milestones(
        self,
        current_stage: str,
        trend: str
    ) -> List[Dict[str, Any]]:
        """预测可能的里程碑"""
        milestones = []

        stage_progression = {
            self.STAGE_MATCHED: self.STAGE_CHATTING,
            self.STAGE_CHATTING: self.STAGE_DATING,
            self.STAGE_DATING: self.STAGE_IN_RELATIONSHIP
        }

        if trend == self.TREND_RISING and current_stage in stage_progression:
            next_stage = stage_progression[current_stage]
            milestones.append({
                "type": "stage_progression",
                "description": f"可能进入{self._get_stage_name(next_stage)}阶段",
                "probability": 0.7 if trend == self.TREND_RISING else 0.3
            })

        return milestones

    def _get_stage_name(self, stage: str) -> str:
        """获取阶段名称"""
        names = {
            self.STAGE_MATCHED: "已匹配",
            self.STAGE_CHATTING: "聊天中",
            self.STAGE_DATING: "约会中",
            self.STAGE_IN_RELATIONSHIP: "恋爱中"
        }
        return names.get(stage, stage)

    def _identify_risks(
        self,
        reports: List[RelationshipWeatherReportDB],
        trend: str
    ) -> List[Dict[str, Any]]:
        """识别风险因素"""
        risks = []

        if trend == self.TREND_DECLINING:
            risks.append({
                "type": "temperature_decline",
                "description": "情感温度呈下降趋势",
                "severity": "medium"
            })

        # 检查是否有恶劣天气
        for report in reports:
            if report.weather_description in ["stormy", "rainy"]:
                risks.append({
                    "type": "bad_weather",
                    "description": f"出现{report.weather_description}天气",
                    "severity": "high" if report.weather_description == "stormy" else "medium"
                })

        return risks

    def _identify_opportunities(
        self,
        reports: List[RelationshipWeatherReportDB],
        trend: str
    ) -> List[Dict[str, Any]]:
        """识别机会因素"""
        opportunities = []

        if trend == self.TREND_RISING:
            opportunities.append({
                "type": "temperature_rise",
                "description": "情感温度呈上升趋势",
                "impact": "positive"
            })

        # 检查是否有好天气
        for report in reports:
            if report.weather_description in ["sunny", "partly_cloudy"]:
                opportunities.append({
                    "type": "good_weather",
                    "description": f"出现{report.weather_description}天气",
                    "impact": "positive"
                })

        return opportunities

    def _generate_recommendations(
        self,
        current_stage: str,
        trend: str,
        risks: List[Dict],
        opportunities: List[Dict]
    ) -> List[Dict[str, Any]]:
        """生成建议行动"""
        recommendations = []

        if trend == self.TREND_DECLINING:
            recommendations.append({
                "action": "增加沟通频率",
                "description": "建议增加日常交流，分享生活点滴",
                "priority": "high"
            })
        elif trend == self.TREND_RISING:
            recommendations.append({
                "action": "规划特别约会",
                "description": "趁关系升温，安排一次特别的约会",
                "priority": "medium"
            })

        # 根据阶段给出建议
        if current_stage == self.STAGE_CHATTING:
            recommendations.append({
                "action": "安排首次约会",
                "description": "关系稳定，可以考虑线下见面",
                "priority": "medium"
            })

        return recommendations

    def _predict_stage(
        self,
        current_stage: str,
        trend: str
    ) -> str:
        """预测未来阶段"""
        stage_progression = {
            self.STAGE_MATCHED: self.STAGE_CHATTING,
            self.STAGE_CHATTING: self.STAGE_DATING,
            self.STAGE_DATING: self.STAGE_IN_RELATIONSHIP,
            self.STAGE_IN_RELATIONSHIP: self.STAGE_IN_RELATIONSHIP
        }

        if trend == self.TREND_RISING:
            return stage_progression.get(current_stage, current_stage)
        elif trend == self.TREND_DECLINING:
            # 下降趋势可能倒退
            stage_regression = {
                self.STAGE_IN_RELATIONSHIP: self.STAGE_DATING,
                self.STAGE_DATING: self.STAGE_CHATTING,
                self.STAGE_CHATTING: self.STAGE_MATCHED,
                self.STAGE_MATCHED: self.STAGE_MATCHED
            }
            return stage_regression.get(current_stage, current_stage)
        else:
            return current_stage

    def _calculate_stage_change_probability(
        self,
        current_stage: str,
        trend: str
    ) -> float:
        """计算阶段变化概率"""
        if current_stage == self.STAGE_IN_RELATIONSHIP:
            return 0.0  # 已经是最高阶段

        base_prob = 0.3
        if trend == self.TREND_RISING:
            return base_prob + 0.4  # 70%
        elif trend == self.TREND_DECLINING:
            return base_prob - 0.2  # 10%
        else:
            return base_prob  # 30%

    def _format_prediction(
        self,
        prediction: RelationshipTrendPredictionDB
    ) -> Dict[str, Any]:
        """格式化预测结果"""
        return {
            "id": prediction.id,
            "user_a_id": prediction.user_a_id,
            "user_b_id": prediction.user_b_id,
            "prediction_base_date": prediction.prediction_base_date.isoformat(),
            "prediction_period": prediction.prediction_period,
            "current_temperature": prediction.current_temperature,
            "predicted_temperature": prediction.predicted_temperature,
            "temperature_trend": prediction.temperature_trend,
            "current_stage": prediction.current_stage,
            "predicted_stage": prediction.predicted_stage,
            "stage_change_probability": prediction.stage_change_probability,
            "risk_indicators": prediction.risk_indicators,
            "opportunity_indicators": prediction.opportunity_indicators,
            "predicted_milestones": prediction.predicted_milestones,
            "recommended_actions": prediction.recommended_actions,
            "model_version": prediction.model_version,
            "created_at": prediction.created_at.isoformat(),
            "expires_at": prediction.expires_at.isoformat() if prediction.expires_at else None
        }

    def _get_base_prediction(
        self,
        user_a_id: str,
        user_b_id: str,
        prediction_period: str
    ) -> Dict[str, Any]:
        """获取基础预测（无历史数据时）"""
        return {
            "id": None,
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "prediction_base_date": datetime.utcnow().isoformat(),
            "prediction_period": prediction_period,
            "current_temperature": 50.0,
            "predicted_temperature": 50.0,
            "temperature_trend": self.TREND_STABLE,
            "current_stage": self.STAGE_MATCHED,
            "predicted_stage": self.STAGE_MATCHED,
            "stage_change_probability": 0.3,
            "risk_indicators": [],
            "opportunity_indicators": [],
            "predicted_milestones": [],
            "recommended_actions": [
                {
                    "action": "增加互动",
                    "description": "多进行交流，增进了解",
                    "priority": "high"
                }
            ],
            "model_version": "v1.0",
            "message": "基于有限数据的预测，随着数据积累将更准确"
        }

    def get_prediction(
        self,
        prediction_id: str,
        db_session
    ) -> Optional[Dict[str, Any]]:
        """获取预测记录"""
        prediction = db_session.query(RelationshipTrendPredictionDB).filter(
            RelationshipTrendPredictionDB.id == prediction_id
        ).first()

        if not prediction:
            return None

        return self._format_prediction(prediction)


class WarningResponseService:
    """预警分级响应服务"""

    # 预警级别
    LEVEL_LOW = "low"
    LEVEL_MEDIUM = "medium"
    LEVEL_HIGH = "high"
    LEVEL_CRITICAL = "critical"

    def __init__(self):
        self._initialized = False

    def _ensure_initialized(self, db_session):
        """初始化默认响应策略"""
        if self._initialized:
            return

        self._initialize_default_strategies(db_session)
        self._initialized = True

    def _initialize_default_strategies(self, db_session):
        """初始化默认响应策略"""
        default_strategies = [
            # Low 级别策略
            {
                "warning_level": self.LEVEL_LOW,
                "response_type": "private_suggestion",
                "trigger_conditions": {"emotion_keywords": ["烦", "累"]},
                "response_template": "看起来你们对话中有些小情绪，建议深呼吸一下，换个方式表达～",
                "expected_effect": "缓解轻微负面情绪",
                "usage_guide": "适用于日常小摩擦",
            },
            # Medium 级别策略
            {
                "warning_level": self.LEVEL_MEDIUM,
                "response_type": "cooling_technique",
                "trigger_conditions": {"escalation_risk": 40},
                "response_template": "检测到对话气氛有些紧张，建议暂停 5 分钟，做 4-7-8 呼吸法：吸气 4 秒，屏气 7 秒，呼气 8 秒。",
                "expected_effect": "降低情绪激动程度",
                "usage_guide": "适用于情绪开始升级",
            },
            # High 级别策略
            {
                "warning_level": self.LEVEL_HIGH,
                "response_type": "communication_guide",
                "trigger_conditions": {"escalation_risk": 60},
                "response_template": "检测到对话中有较强的负面情绪。建议使用'我'语句表达感受，而非指责对方。例如：'我感到...'而非'你总是...'。",
                "expected_effect": "改善沟通方式",
                "usage_guide": "适用于情绪明显升级",
            },
            # Critical 级别策略
            {
                "warning_level": self.LEVEL_CRITICAL,
                "response_type": "emergency_intervention",
                "trigger_conditions": {"escalation_risk": 80},
                "response_template": "⚠️ 检测到对话有严重冲突风险。强烈建议立即暂停对话，各自冷静。如有需要，可寻求专业情感咨询帮助。",
                "expected_effect": "防止严重冲突",
                "usage_guide": "适用于极度紧张局面",
            }
        ]

        for strategy_data in default_strategies:
            strategy = WarningResponseStrategyDB(
                id=f"strategy_{strategy_data['warning_level']}_{datetime.utcnow().timestamp()}",
                **strategy_data
            )
            db_session.add(strategy)

        db_session.commit()

    def get_response_strategy(
        self,
        warning_level: str,
        context: Optional[Dict[str, Any]] = None,
        db_session=None
    ) -> Optional[Dict[str, Any]]:
        """
        根据预警级别获取响应策略

        参数:
        - warning_level: 预警级别 (low, medium, high, critical)
        - context: 上下文信息（用于匹配最合适的策略）
        """
        self._ensure_initialized(db_session)

        # 查询适用的策略
        strategies = db_session.query(WarningResponseStrategyDB).filter(
            WarningResponseStrategyDB.warning_level == warning_level
        ).all()

        if not strategies:
            return None

        # 如果有上下文，选择最匹配的策略
        if context:
            # 简单实现：随机选择一个策略
            # 实际应该根据 trigger_conditions 进行匹配
            strategy = random.choice(strategies)
        else:
            strategy = random.choice(strategies)

        return {
            "id": strategy.id,
            "warning_level": strategy.warning_level,
            "response_type": strategy.response_type,
            "response_template": strategy.response_template,
            "expected_effect": strategy.expected_effect,
            "usage_guide": strategy.usage_guide,
            "effectiveness_rating": strategy.effectiveness_rating
        }

    def execute_response(
        self,
        warning_id: str,
        strategy_id: str,
        recipient_user_id: str,
        response_content: str,
        delivery_method: str = "push_notification",
        db_session=None
    ) -> Dict[str, Any]:
        """
        执行预警响应

        参数:
        - warning_id: 预警 ID
        - strategy_id: 策略 ID
        - recipient_user_id: 接收者 ID
        - response_content: 实际响应内容
        - delivery_method: 传递方式
        """
        # 创建响应记录
        record_id = f"wrr_{warning_id}_{datetime.utcnow().timestamp()}"
        record = WarningResponseRecordDB(
            id=record_id,
            warning_id=warning_id,
            strategy_id=strategy_id,
            response_type="executed",
            response_content=response_content,
            recipient_user_id=recipient_user_id,
            delivery_method=delivery_method
        )

        db_session.add(record)
        db_session.commit()

        # 更新策略使用统计
        if strategy_id:
            strategy = db_session.query(WarningResponseStrategyDB).filter(
                WarningResponseStrategyDB.id == strategy_id
            ).first()
            if strategy:
                strategy.usage_count += 1
                db_session.commit()

        return {
            "id": record.id,
            "warning_id": record.warning_id,
            "strategy_id": record.strategy_id,
            "response_content": record.response_content,
            "recipient_user_id": record.recipient_user_id,
            "delivery_method": record.delivery_method,
            "created_at": record.created_at.isoformat()
        }

    def submit_response_feedback(
        self,
        record_id: str,
        feedback: str,
        emotion_change: Optional[float] = None,
        relationship_improvement: Optional[float] = None,
        db_session=None
    ) -> bool:
        """
        提交响应反馈

        参数:
        - record_id: 响应记录 ID
        - feedback: 反馈 (helpful, neutral, unhelpful)
        - emotion_change: 情绪变化 (-1 到 1)
        - relationship_improvement: 关系改善程度 (0 到 1)
        """
        record = db_session.query(WarningResponseRecordDB).filter(
            WarningResponseRecordDB.id == record_id
        ).first()

        if not record:
            return False

        record.user_feedback = feedback
        if emotion_change is not None:
            record.emotion_change = emotion_change
        if relationship_improvement is not None:
            record.relationship_improvement = relationship_improvement

        # 更新策略有效性评分
        if record.strategy_id:
            strategy = db_session.query(WarningResponseStrategyDB).filter(
                WarningResponseStrategyDB.id == record.strategy_id
            ).first()
            if strategy:
                # 简单移动平均更新
                new_rating = (
                    (strategy.effectiveness_rating * strategy.usage_count +
                     (1 if feedback == "helpful" else 0 if feedback == "unhelpful" else 0.5))
                    / (strategy.usage_count + 1)
                )
                strategy.effectiveness_rating = new_rating

        db_session.commit()
        return True

    def get_response_history(
        self,
        user_id: str,
        db_session
    ) -> List[Dict[str, Any]]:
        """获取用户的响应历史"""
        records = db_session.query(WarningResponseRecordDB).filter(
            WarningResponseRecordDB.recipient_user_id == user_id
        ).order_by(WarningResponseRecordDB.created_at.desc()).limit(20).all()

        return [
            {
                "id": r.id,
                "warning_id": r.warning_id,
                "response_type": r.response_type,
                "response_content": r.response_content,
                "delivery_method": r.delivery_method,
                "is_acknowledged": r.is_acknowledged,
                "user_feedback": r.user_feedback,
                "emotion_change": r.emotion_change,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ]


# 创建全局服务实例
love_language_profile_service = LoveLanguageProfileService()
relationship_trend_service = RelationshipTrendService()
warning_response_service = WarningResponseService()
