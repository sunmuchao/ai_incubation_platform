"""
P17 终极共振服务层

包含：
1. 压力测试服务
2. 成长计划服务
3. 信任背书服务
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from db.models import UserDB
from models.p17_models import (
    StressTestScenarioDB,
    CoupleStressTestDB,
    GrowthPlanDB,
    GrowthResourceDB,
    GrowthResourceRecommendationDB,
    TrustScoreDB,
    TrustEndorsementDB,
    TrustEndorsementSummaryDB
)
from utils.logger import logger


class StressTestService:
    """压力测试服务"""

    # 默认危机场景库
    DEFAULT_SCENARIOS = {
        "unemployment": {
            "name": "突发失业",
            "description": "其中一方突然失去工作，面临经济压力",
            "details": {
                "background": "你们正在规划未来，但突然收到 TA 失业的消息",
                "trigger_event": "公司裁员，TA 被列入名单",
                "constraints": ["房贷压力", "生活开支", "情绪波动"]
            },
            "evaluation": {
                "value_alignment": "对财务优先级的看法",
                "problem_solving": "如何应对经济困难",
                "emotional_support": "情绪支持能力"
            }
        },
        "family_emergency": {
            "name": "家庭急事",
            "description": "一方家庭出现紧急情况需要支持",
            "details": {
                "background": "TA 的父母突然生病住院",
                "trigger_event": "深夜接到医院电话",
                "constraints": ["时间冲突", "经济负担", "情感压力"]
            },
            "evaluation": {
                "value_alignment": "家庭责任观念",
                "problem_solving": "协调资源能力",
                "emotional_support": "陪伴和支持"
            }
        },
        "long_distance": {
            "name": "异地考验",
            "description": "因工作原因需要异地恋一段时间",
            "details": {
                "background": "TA 获得了一个很好的工作机会，但在另一个城市",
                "trigger_event": "需要决定是否接受 offer",
                "constraints": ["沟通频率", "信任考验", "未来规划"]
            },
            "evaluation": {
                "value_alignment": "事业与感情的优先级",
                "problem_solving": "异地维系方案",
                "emotional_support": "远距离情感支持"
            }
        }
    }

    def __init__(self):
        self._initialized = False

    def _ensure_initialized(self, db_session):
        """初始化默认场景"""
        if self._initialized:
            return

        for scenario_type, scenario_data in self.DEFAULT_SCENARIOS.items():
            existing = db_session.query(StressTestScenarioDB).filter(
                StressTestScenarioDB.scenario_type == scenario_type
            ).first()
            if not existing:
                scenario = StressTestScenarioDB(
                    id=f"scenario_{scenario_type}",
                    scenario_name=scenario_data["name"],
                    scenario_type=scenario_type,
                    description=scenario_data["description"],
                    scenario_details=scenario_data["details"],
                    evaluation_criteria=scenario_data["evaluation"]
                )
                db_session.add(scenario)

        db_session.commit()
        self._initialized = True

    def start_stress_test(
        self,
        user_a_id: str,
        user_b_id: str,
        scenario_id: str,
        test_mode: str = "separate",
        db_session=None
    ) -> CoupleStressTestDB:
        """开始压力测试"""
        self._ensure_initialized(db_session)

        test_id = f"stress_test_{user_a_id}_{user_b_id}_{datetime.utcnow().timestamp()}"
        test = CoupleStressTestDB(
            id=test_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            scenario_id=scenario_id,
            test_mode=test_mode
        )

        if db_session:
            db_session.add(test)
            db_session.commit()
            db_session.refresh(test)

        return test

    def submit_test_response(
        self,
        test_id: str,
        user_id: str,
        response: str,
        decision: Dict[str, Any],
        db_session
    ) -> bool:
        """提交测试反应"""
        test = db_session.query(CoupleStressTestDB).filter(
            CoupleStressTestDB.id == test_id
        ).first()

        if not test:
            return False

        if test.user_a_id == user_id:
            test.user_a_response = response
            test.user_a_decision = decision
        elif test.user_b_id == user_id:
            test.user_b_response = response
            test.user_b_decision = decision

        db_session.commit()
        return True

    def complete_stress_test(
        self,
        test_id: str,
        db_session
    ) -> CoupleStressTestDB:
        """完成压力测试并生成分析"""
        test = db_session.query(CoupleStressTestDB).filter(
            CoupleStressTestDB.id == test_id
        ).first()

        if not test:
            raise ValueError("测试不存在")

        # 分析兼容性
        compatibility = self._analyze_compatibility(
            test.user_a_response, test.user_b_response,
            test.user_a_decision, test.user_b_decision
        )

        test.compatibility_analysis = compatibility

        # 确定测试结果
        test.test_result = self._determine_test_result(compatibility)

        # 生成 AI 分析
        test.ai_analysis = self._generate_ai_analysis(
            test.test_result, compatibility
        )

        # 生成建议
        test.recommendations = self._generate_recommendations(compatibility)

        test.is_completed = True
        test.completed_at = datetime.utcnow()

        db_session.commit()
        db_session.refresh(test)

        return test

    def _analyze_compatibility(
        self,
        response_a: str,
        response_b: str,
        decision_a: Dict,
        decision_b: Dict
    ) -> Dict[str, Any]:
        """分析兼容性"""
        # 简化实现：基于关键词和决策相似度

        # 价值观一致性
        value_alignment = self._calculate_value_alignment(
            decision_a.get("priorities", []),
            decision_b.get("priorities", [])
        )

        # 问题解决方式
        problem_solving = self._calculate_problem_solving_compatibility(
            response_a, response_b
        )

        # 情感支持
        emotional_support = random.uniform(0.6, 0.9)  # 简化

        return {
            "value_alignment": value_alignment,
            "problem_solving": problem_solving,
            "emotional_support": emotional_support,
            "overall_compatibility": (value_alignment + problem_solving + emotional_support) / 3
        }

    def _calculate_value_alignment(
        self,
        priorities_a: List[str],
        priorities_b: List[str]
    ) -> float:
        """计算价值观一致性"""
        if not priorities_a or not priorities_b:
            return 0.5

        common = set(priorities_a) & set(priorities_b)
        total = set(priorities_a) | set(priorities_b)

        return len(common) / max(1, len(total))

    def _calculate_problem_solving_compatibility(
        self,
        response_a: str,
        response_b: str
    ) -> float:
        """计算问题解决兼容性"""
        # 简化：基于回应长度和关键词
        positive_keywords = ["一起", "面对", "支持", "理解", "沟通", "解决"]

        score_a = sum(1 for kw in positive_keywords if kw in response_a)
        score_b = sum(1 for kw in positive_keywords if kw in response_b)

        return min(1.0, (score_a + score_b) / 10)

    def _determine_test_result(self, compatibility: Dict) -> str:
        """确定测试结果"""
        overall = compatibility.get("overall_compatibility", 0.5)

        if overall >= 0.8:
            return "excellent"
        elif overall >= 0.6:
            return "good"
        elif overall >= 0.4:
            return "fair"
        else:
            return "poor"

    def _generate_ai_analysis(
        self,
        test_result: str,
        compatibility: Dict
    ) -> str:
        """生成 AI 分析"""
        result_descriptions = {
            "excellent": "你们在压力测试中表现出色，展现了很强的一致性",
            "good": "你们的表现良好，大部分方面能够达成共识",
            "fair": "你们存在一些分歧，需要更多的沟通和理解",
            "poor": "你们在关键问题上有较大分歧，建议深入沟通"
        }

        return result_descriptions.get(test_result, "测试结果")

    def _generate_recommendations(self, compatibility: Dict) -> List[Dict]:
        """生成建议"""
        recommendations = []

        if compatibility.get("value_alignment", 0.5) < 0.6:
            recommendations.append({
                "area": "价值观",
                "suggestion": "建议深入讨论彼此的人生优先级和价值观"
            })

        if compatibility.get("problem_solving", 0.5) < 0.6:
            recommendations.append({
                "area": "问题解决",
                "suggestion": "学习更有效的沟通和问题解决方式"
            })

        return recommendations


class GrowthPlanService:
    """成长计划服务"""

    def create_growth_plan(
        self,
        user_a_id: str,
        user_b_id: str,
        plan_name: str,
        growth_goals: List[Dict],
        db_session=None
    ) -> GrowthPlanDB:
        """创建成长计划"""
        plan_id = f"growth_plan_{user_a_id}_{user_b_id}_{datetime.utcnow().timestamp()}"
        plan = GrowthPlanDB(
            id=plan_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            plan_name=plan_name,
            growth_goals=growth_goals,
            growth_areas=list(set(g["area"] for g in growth_goals)),
            milestones=[
                {"name": g["name"], "description": g.get("description", ""), "achieved": False}
                for g in growth_goals
            ]
        )

        if db_session:
            db_session.add(plan)
            db_session.commit()
            db_session.refresh(plan)

        return plan

    def recommend_resources(
        self,
        user_a_id: str,
        user_b_id: str,
        growth_areas: List[str],
        db_session
    ) -> List[GrowthResourceDB]:
        """推荐成长资源"""
        resources = db_session.query(GrowthResourceDB).filter(
            GrowthResourceDB.growth_areas.overlaps(growth_areas) if hasattr(GrowthResourceDB.growth_areas, 'overlaps')
            else True  # 简化
        ).limit(5).all()

        return resources or []


class TrustService:
    """信任服务"""

    def calculate_trust_score(
        self,
        user_id: str,
        db_session
    ) -> TrustScoreDB:
        """计算用户信任分"""
        # 获取或创建信任分记录
        score = db_session.query(TrustScoreDB).filter(
            TrustScoreDB.user_id == user_id
        ).first()

        if not score:
            score = TrustScoreDB(
                id=f"trust_{user_id}",
                user_id=user_id
            )
            db_session.add(score)

        # 基于行为统计更新分数
        score = self._update_scores_from_behavior(score, db_session)

        db_session.commit()
        db_session.refresh(score)

        return score

    def _update_scores_from_behavior(
        self,
        score: TrustScoreDB,
        db_session
    ) -> TrustScoreDB:
        """基于行为更新分数"""
        # 简化实现
        score.overall_trust_score = 75.0
        score.trust_level = "gold"

        return score

    def add_endorsement(
        self,
        endorsed_user_id: str,
        endorser_user_id: str,
        endorsement_type: str,
        endorsement_text: str,
        relationship_context: str,
        db_session=None
    ) -> TrustEndorsementDB:
        """添加信任背书"""
        endorsement_id = f"endorsement_{endorsed_user_id}_{datetime.utcnow().timestamp()}"
        endorsement = TrustEndorsementDB(
            id=endorsement_id,
            endorsed_user_id=endorsed_user_id,
            endorser_user_id=endorser_user_id,
            endorsement_type=endorsement_type,
            endorsement_text=endorsement_text,
            relationship_context=relationship_context
        )

        if db_session:
            db_session.add(endorsement)
            db_session.commit()
            db_session.refresh(endorsement)

        return endorsement


# 创建全局服务实例
stress_test_service = StressTestService()
growth_plan_service = GrowthPlanService()
trust_service = TrustService()
