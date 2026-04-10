"""
游戏化人格测试服务 - 渐进式智能收集架构

通过游戏化的方式收集用户画像维度：
1. 人格测试：大五人格 16 维
2. 依恋类型测试：依恋类型 16 维
3. 价值观测试：价值观 16 维

设计原则：
- 不是枯燥的问卷，而是有趣的体验
- 用户可以选择跳过，但完成有奖励
- 自动填充向量维度
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import random

from models.profile_vector_models import (
    UserVectorProfile,
    DimensionValue,
    GameTestResult,
    DataSource,
    DIMENSION_DEFINITIONS,
)
from utils.logger import logger


class TestType(str, Enum):
    """测试类型"""
    PERSONALITY = "personality"  # 大五人格测试
    ATTACHMENT = "attachment"  # 依恋类型测试
    VALUES = "values"  # 价值观测试


@dataclass
class Question:
    """测试问题"""
    id: str
    question: str
    subtitle: Optional[str] = None
    options: List[Dict[str, Any]] = None
    dimension_mapping: Dict[str, List[Tuple[int, float]]] = None  # 选项 -> [(维度索引, 分数)]

    def __post_init__(self):
        if self.options is None:
            self.options = []
        if self.dimension_mapping is None:
            self.dimension_mapping = {}


@dataclass
class TestProgress:
    """测试进度"""
    test_type: TestType
    current_question: int
    total_questions: int
    answers: List[Dict[str, Any]]
    started_at: datetime
    estimated_remaining_seconds: int

    @property
    def progress_ratio(self) -> float:
        return self.current_question / self.total_questions if self.total_questions > 0 else 0.0


# 人格测试问题库
PERSONALITY_QUESTIONS = [
    Question(
        id="p1",
        question="周末你更想怎么过？",
        subtitle="选最符合你真实想法的",
        options=[
            {"value": "home", "label": "宅家看剧、打游戏", "icon": "🏠"},
            {"value": "outdoor", "label": "户外徒步、运动", "icon": "🌲"},
            {"value": "social", "label": "和朋友聚会", "icon": "🎉"},
            {"value": "explore", "label": "探索新地方", "icon": "🗺️"},
        ],
        dimension_mapping={
            "home": [(34, 0.2), (40, 0.2)],  # 内向、低社交活跃度
            "outdoor": [(34, 0.4), (40, 0.5)],
            "social": [(34, 0.8), (40, 0.8)],  # 外向、高社交活跃度
            "explore": [(32, 0.8), (34, 0.7)],  # 高开放性、外向
        }
    ),
    Question(
        id="p2",
        question="当你遇到困难时，你通常会？",
        options=[
            {"value": "alone", "label": "自己想办法解决", "icon": "💪"},
            {"value": "research", "label": "上网查资料研究", "icon": "🔍"},
            {"value": "ask", "label": "向朋友或家人求助", "icon": "🤝"},
            {"value": "avoid", "label": "先放一放再说", "icon": "⏳"},
        ],
        dimension_mapping={
            "alone": [(36, 0.6), (45, 0.6)],  # 情绪稳定、独立
            "research": [(33, 0.8), (32, 0.7)],  # 高尽责性、高开放性
            "ask": [(44, 0.7), (45, 0.7)],  # 高信任、合作意愿
            "avoid": [(33, 0.3), (36, 0.4)],  # 低尽责性、情绪不稳定
        }
    ),
    Question(
        id="p3",
        question="在社交场合，你更像是？",
        options=[
            {"value": "center", "label": "话题的中心，活跃气氛", "icon": "🌟"},
            {"value": "participant", "label": "积极参与，但不是主角", "icon": "😊"},
            {"value": "observer", "label": "安静观察，偶尔发言", "icon": "👁️"},
            {"value": "uncomfortable", "label": "不太自在，想早点离开", "icon": "😅"},
        ],
        dimension_mapping={
            "center": [(34, 0.9), (42, 0.8)],  # 高外向、高自信
            "participant": [(34, 0.6), (44, 0.6)],
            "observer": [(34, 0.3), (32, 0.5)],  # 内向、高开放性
            "uncomfortable": [(34, 0.2), (36, 0.4)],  # 高内向、情绪不稳定
        }
    ),
    Question(
        id="p4",
        question="对于计划，你的态度是？",
        options=[
            {"value": "strict", "label": "必须按计划执行", "icon": "📋"},
            {"value": "flexible", "label": "有计划但也接受变化", "icon": "🔄"},
            {"value": "loose", "label": "大致有个方向就行", "icon": "🎯"},
            {"value": "none", "label": "随性而为，不喜欢计划", "icon": "🎲"},
        ],
        dimension_mapping={
            "strict": [(33, 0.9), (36, 0.7)],  # 高尽责性、高自律
            "flexible": [(33, 0.7), (44, 0.6)],
            "loose": [(33, 0.5), (32, 0.6)],
            "none": [(33, 0.2), (32, 0.8)],  # 低尽责性、高开放性
        }
    ),
    Question(
        id="p5",
        question="当伴侣和你意见不一致时，你更倾向于？",
        options=[
            {"value": "discuss", "label": "好好沟通，找到双方都能接受的方案", "icon": "💬"},
            {"value": "persuade", "label": "说服对方接受我的观点", "icon": "🗣️"},
            {"value": "compromise", "label": "各退一步，谁对听谁的", "icon": "🤝"},
            {"value": "avoid", "label": "避免争执，随TA去吧", "icon": "🙈"},
        ],
        dimension_mapping={
            "discuss": [(44, 0.8), (134, 0.9)],  # 高宜人性、高冲突修复意愿
            "persuade": [(42, 0.7), (44, 0.4)],  # 高自信、低宜人性
            "compromise": [(44, 0.7), (65, 0.7)],  # 高宜人性、高妥协意愿
            "avoid": [(133, 0.8), (44, 0.3)],  # 高冷战倾向、低宜人性
        }
    ),
    # 更多问题...
]

# 依恋类型测试问题库
ATTACHMENT_QUESTIONS = [
    Question(
        id="a1",
        question="当伴侣没有及时回复消息时，你会？",
        options=[
            {"value": "secure", "label": "相信TA在忙，等TA回复", "icon": "😊"},
            {"value": "anxious", "label": "担心TA是不是不想理我", "icon": "😰"},
            {"value": "avoidant", "label": "无所谓，我也经常不回", "icon": "🤷"},
            {"value": "fearful", "label": "既担心又不想主动问", "icon": "😢"},
        ],
        dimension_mapping={
            "secure": [(48, 0.9), (54, 0.8)],  # 高安全型、高安全感需求满足
            "anxious": [(49, 0.8), (54, 0.9)],  # 高焦虑型、高安全感需求
            "avoidant": [(50, 0.8), (53, 0.8)],  # 高回避型、高独立需求
            "fearful": [(51, 0.8), (49, 0.5)],  # 高恐惧型
        }
    ),
    Question(
        id="a2",
        question="对于亲密关系，你更担心的是？",
        options=[
            {"value": "secure", "label": "不太担心，相信会遇到对的人", "icon": "✨"},
            {"value": "abandonment", "label": "担心TA会离开我", "icon": "💔"},
            {"value": "engulfment", "label": "担心失去自由和自我", "icon": "🔒"},
            {"value": "both", "label": "两种担心都有", "icon": "⚡"},
        ],
        dimension_mapping={
            "secure": [(48, 0.8)],
            "abandonment": [(49, 0.7), (54, 0.9)],
            "engulfment": [(50, 0.7), (53, 0.9)],
            "both": [(51, 0.7)],
        }
    ),
    Question(
        id="a3",
        question="吵架后，你通常需要多久冷静下来？",
        options=[
            {"value": "quick", "label": "很快，几个小时就好", "icon": "⚡"},
            {"value": "normal", "label": "一天左右", "icon": "🌅"},
            {"value": "slow", "label": "要好几天", "icon": "📅"},
            {"value": "avoid", "label": "倾向于冷战，等对方先低头", "icon": "❄️"},
        ],
        dimension_mapping={
            "quick": [(48, 0.7), (61, 0.9)],  # 安全型、快速恢复
            "normal": [(61, 0.7)],
            "slow": [(49, 0.5), (61, 0.4)],  # 可能有焦虑倾向、慢恢复
            "avoid": [(50, 0.6), (133, 0.9)],  # 回避型、高冷战倾向
        }
    ),
    # 更多问题...
]

# 价值观测试问题库
VALUES_QUESTIONS = [
    Question(
        id="v1",
        question="对于孩子，你的态度是？",
        options=[
            {"value": "want", "label": "想要孩子，家庭才完整", "icon": "👶"},
            {"value": "maybe", "label": "看情况，不强求", "icon": "🤔"},
            {"value": "not_want", "label": "不想要孩子", "icon": "🚫"},
            {"value": "unsure", "label": "还没想好", "icon": "❓"},
        ],
        dimension_mapping={
            "want": [(17, 0.9)],
            "maybe": [(17, 0.5)],
            "not_want": [(17, 0.1)],
            "unsure": [(17, 0.5)],
        }
    ),
    Question(
        id="v2",
        question="对于金钱，你更倾向于？",
        options=[
            {"value": "thrifty", "label": "精打细算，未雨绸缪", "icon": "💰"},
            {"value": "balanced", "label": "该花就花，量入为出", "icon": "⚖️"},
            {"value": "enjoy", "label": "人生苦短，及时行乐", "icon": "🎉"},
            {"value": "invest", "label": "投资自己，追求回报", "icon": "📈"},
        ],
        dimension_mapping={
            "thrifty": [(27, 0.2), (30, 0.8)],  # 节俭、高储蓄习惯
            "balanced": [(27, 0.5), (28, 0.6)],
            "enjoy": [(27, 0.8), (30, 0.3)],  # 享受型、低储蓄
            "invest": [(27, 0.6), (29, 0.7)],  # 投资、高风险偏好
        }
    ),
    Question(
        id="v3",
        question="事业和家庭，你更看重哪个？",
        options=[
            {"value": "career", "label": "事业第一，趁年轻多打拼", "icon": "💼"},
            {"value": "family", "label": "家庭为重，工作是为了生活", "icon": "👨‍👩‍👧"},
            {"value": "balance", "label": "努力平衡两者", "icon": "⚖️"},
            {"value": "freedom", "label": "追求自由，不想被束缚", "icon": "🕊️"},
        ],
        dimension_mapping={
            "career": [(16, 0.4), (22, 0.9)],  # 家庭导向低、事业导向高
            "family": [(16, 0.9), (22, 0.4)],  # 家庭导向高、事业导向低
            "balance": [(16, 0.7), (22, 0.7), (23, 0.8)],  # 平衡
            "freedom": [(16, 0.5), (22, 0.3), (32, 0.7)],  # 自由
        }
    ),
    # 更多问题...
]


class GamifiedTestService:
    """
    游戏化测试服务

    提供：
    1. 人格测试（15道题）→ 大五人格16维
    2. 依恋类型测试（10道题）→ 依恋类型16维
    3. 价值观测试（10道题）→ 价值观16维
    """

    # 测试配置
    TEST_CONFIG = {
        TestType.PERSONALITY: {
            "name": "恋爱人格测试",
            "description": "测测你在恋爱中的性格特点",
            "total_questions": 15,
            "estimated_minutes": 5,
            "reward": "解锁精准匹配",
            "dimensions_filled": 16,  # 填充的维度数量
            "questions": PERSONALITY_QUESTIONS,
        },
        TestType.ATTACHMENT: {
            "name": "依恋类型测试",
            "description": "了解你的亲密关系模式",
            "total_questions": 10,
            "estimated_minutes": 4,
            "reward": "解锁治愈关系匹配",
            "dimensions_filled": 16,
            "questions": ATTACHMENT_QUESTIONS,
        },
        TestType.VALUES: {
            "name": "价值观测试",
            "description": "探索你的核心价值观",
            "total_questions": 10,
            "estimated_minutes": 3,
            "reward": "解锁价值观匹配",
            "dimensions_filled": 16,
            "questions": VALUES_QUESTIONS,
        },
    }

    def __init__(self):
        # 用户测试进度缓存
        self._progress_cache: Dict[str, Dict[TestType, TestProgress]] = {}
        # 用户答案缓存
        self._answers_cache: Dict[str, Dict[TestType, List[Dict[str, Any]]]] = {}

    def start_test(
        self,
        user_id: str,
        test_type: TestType
    ) -> Dict[str, Any]:
        """
        开始测试

        Args:
            user_id: 用户ID
            test_type: 测试类型

        Returns:
            测试信息和第一道题
        """
        logger.info(f"GamifiedTestService: Starting {test_type} test for user {user_id}")

        config = self.TEST_CONFIG[test_type]
        questions = config["questions"]

        # 初始化进度
        if user_id not in self._progress_cache:
            self._progress_cache[user_id] = {}
        if user_id not in self._answers_cache:
            self._answers_cache[user_id] = {}

        self._progress_cache[user_id][test_type] = TestProgress(
            test_type=test_type,
            current_question=0,
            total_questions=len(questions),
            answers=[],
            started_at=datetime.now(),
            estimated_remaining_seconds=config["estimated_minutes"] * 60
        )
        self._answers_cache[user_id][test_type] = []

        # 返回测试信息和第一道题
        first_question = questions[0] if questions else None

        return {
            "test_type": test_type.value,
            "test_name": config["name"],
            "description": config["description"],
            "total_questions": len(questions),
            "estimated_minutes": config["estimated_minutes"],
            "reward": config["reward"],
            "current_question": 1,
            "question": self._format_question(first_question) if first_question else None,
        }

    def submit_answer(
        self,
        user_id: str,
        test_type: TestType,
        question_id: str,
        answer: str
    ) -> Dict[str, Any]:
        """
        提交答案

        Args:
            user_id: 用户ID
            test_type: 测试类型
            question_id: 问题ID
            answer: 答案值

        Returns:
            下一道题或结果
        """
        logger.info(f"GamifiedTestService: User {user_id} answered {question_id} with {answer}")

        progress = self._progress_cache.get(user_id, {}).get(test_type)
        if not progress:
            return {"error": "测试未开始"}

        # 记录答案
        self._answers_cache[user_id][test_type].append({
            "question_id": question_id,
            "answer": answer,
            "answered_at": datetime.now().isoformat()
        })

        # 更新进度
        progress.current_question += 1
        progress.answers.append({"question_id": question_id, "answer": answer})

        config = self.TEST_CONFIG[test_type]
        questions = config["questions"]

        # 检查是否完成
        if progress.current_question >= len(questions):
            # 测试完成
            return self._complete_test(user_id, test_type)

        # 返回下一道题
        next_question = questions[progress.current_question]

        return {
            "status": "continue",
            "progress": progress.progress_ratio,
            "current_question": progress.current_question + 1,
            "total_questions": len(questions),
            "question": self._format_question(next_question),
        }

    def _complete_test(
        self,
        user_id: str,
        test_type: TestType
    ) -> Dict[str, Any]:
        """
        完成测试

        Args:
            user_id: 用户ID
            test_type: 测试类型

        Returns:
            测试结果
        """
        logger.info(f"GamifiedTestService: Test {test_type} completed for user {user_id}")

        answers = self._answers_cache.get(user_id, {}).get(test_type, [])
        config = self.TEST_CONFIG[test_type]
        questions = config["questions"]

        # 计算维度分数
        dimension_scores = self._calculate_dimension_scores(questions, answers)

        # 生成测试报告
        report = self._generate_test_report(test_type, dimension_scores)

        # 计算奖励
        reward = {
            "type": "unlock_feature",
            "feature": "precise_match" if test_type == TestType.PERSONALITY else "advanced_match",
            "dimensions_filled": config["dimensions_filled"],
        }

        return {
            "status": "completed",
            "test_type": test_type.value,
            "dimension_scores": dimension_scores,
            "report": report,
            "reward": reward,
            "completed_at": datetime.now().isoformat(),
        }

    def _calculate_dimension_scores(
        self,
        questions: List[Question],
        answers: List[Dict[str, Any]]
    ) -> Dict[int, float]:
        """
        计算维度分数

        Args:
            questions: 问题列表
            answers: 答案列表

        Returns:
            维度分数字典
        """
        # 收集所有维度分数
        dimension_values: Dict[int, List[float]] = {}

        for answer in answers:
            question_id = answer["question_id"]
            answer_value = answer["answer"]

            # 找到对应问题
            question = next((q for q in questions if q.id == question_id), None)
            if not question:
                continue

            # 获取维度映射
            mapping = question.dimension_mapping.get(answer_value, [])
            for dim_idx, score in mapping:
                if dim_idx not in dimension_values:
                    dimension_values[dim_idx] = []
                dimension_values[dim_idx].append(score)

        # 计算平均分
        result = {}
        for dim_idx, scores in dimension_values.items():
            result[dim_idx] = sum(scores) / len(scores) if scores else 0.5

        return result

    def _generate_test_report(
        self,
        test_type: TestType,
        dimension_scores: Dict[int, float]
    ) -> str:
        """
        生成测试报告

        Args:
            test_type: 测试类型
            dimension_scores: 维度分数

        Returns:
            测试报告文本
        """
        if test_type == TestType.PERSONALITY:
            return self._generate_personality_report(dimension_scores)
        elif test_type == TestType.ATTACHMENT:
            return self._generate_attachment_report(dimension_scores)
        elif test_type == TestType.VALUES:
            return self._generate_values_report(dimension_scores)
        return ""

    def _generate_personality_report(self, scores: Dict[int, float]) -> str:
        """生成人格测试报告"""
        # 大五人格维度
        extraversion = scores.get(34, 0.5)
        openness = scores.get(32, 0.5)
        conscientiousness = scores.get(33, 0.5)
        agreeableness = scores.get(44, 0.5)

        traits = []
        if extraversion > 0.6:
            traits.append("外向活泼")
        elif extraversion < 0.4:
            traits.append("内向温和")

        if openness > 0.6:
            traits.append("开放好奇")
        elif openness < 0.4:
            traits.append("稳重务实")

        if conscientiousness > 0.6:
            traits.append("有计划性")
        elif conscientiousness < 0.4:
            traits.append("随性灵活")

        if agreeableness > 0.6:
            traits.append("善解人意")
        elif agreeableness < 0.4:
            traits.append("独立自主")

        report = f"你的恋爱人格特点：{', '.join(traits)}。"
        report += "这些特质将帮助系统为你找到更匹配的伴侣。"

        return report

    def _generate_attachment_report(self, scores: Dict[int, float]) -> str:
        """生成依恋类型测试报告"""
        secure = scores.get(48, 0.5)
        anxious = scores.get(49, 0.5)
        avoidant = scores.get(50, 0.5)

        if secure > 0.6:
            return "你是安全型依恋，在亲密关系中能保持健康平衡，给伴侣安全感。"
        elif anxious > 0.6:
            return "你可能有焦虑型倾向，在关系中渴望亲密但也容易担心。适合找一个稳定的安全型伴侣。"
        elif avoidant > 0.6:
            return "你可能有回避型倾向，在关系中保持独立但有时显得疏离。适合找一个能理解你的伴侣。"
        else:
            return "你的依恋类型比较复杂，系统会综合考虑为你匹配。"

    def _generate_values_report(self, scores: Dict[int, float]) -> str:
        """生成价值观测试报告"""
        family_oriented = scores.get(16, 0.5)
        career_oriented = scores.get(22, 0.5)
        spending = scores.get(27, 0.5)

        report = "你的核心价值观："
        if family_oriented > 0.6:
            report += "重视家庭，"
        if career_oriented > 0.6:
            report += "事业心强，"
        if spending > 0.6:
            report += "享受当下，"
        elif spending < 0.4:
            report += "注重储蓄，"

        report += "系统会为你匹配价值观相似的人。"

        return report

    def _format_question(self, question: Question) -> Dict[str, Any]:
        """格式化问题"""
        return {
            "id": question.id,
            "question": question.question,
            "subtitle": question.subtitle,
            "options": question.options,
        }

    def apply_test_results_to_profile(
        self,
        user_id: str,
        test_type: TestType,
        dimension_scores: Dict[int, float],
        profile: UserVectorProfile
    ) -> UserVectorProfile:
        """
        将测试结果应用到用户画像

        Args:
            user_id: 用户ID
            test_type: 测试类型
            dimension_scores: 维度分数
            profile: 用户画像

        Returns:
            更新后的画像
        """
        for dim_idx, score in dimension_scores.items():
            profile.set_dimension(
                index=dim_idx,
                value=score,
                confidence=0.8,  # 测试结果置信度较高
                source=DataSource.GAME_TEST,
                evidence=f"{test_type.value}测试结果"
            )

        # 计算完整度
        profile.calculate_completeness()

        return profile

    def get_test_progress(
        self,
        user_id: str,
        test_type: TestType
    ) -> Optional[TestProgress]:
        """获取测试进度"""
        return self._progress_cache.get(user_id, {}).get(test_type)

    def skip_test(
        self,
        user_id: str,
        test_type: TestType
    ) -> Dict[str, Any]:
        """
        跳过测试

        Args:
            user_id: 用户ID
            test_type: 测试类型

        Returns:
            跳过结果
        """
        # 清理缓存
        if user_id in self._progress_cache and test_type in self._progress_cache[user_id]:
            del self._progress_cache[user_id][test_type]
        if user_id in self._answers_cache and test_type in self._answers_cache[user_id]:
            del self._answers_cache[user_id][test_type]

        return {
            "status": "skipped",
            "message": "你可以随时回来完成测试",
            "alternative": "继续使用基础匹配功能"
        }


# 全局实例
_gamified_test_service: Optional[GamifiedTestService] = None


def get_gamified_test_service() -> GamifiedTestService:
    """获取游戏化测试服务单例"""
    global _gamified_test_service
    if _gamified_test_service is None:
        _gamified_test_service = GamifiedTestService()
    return _gamified_test_service