"""
大五人格测试工具

基于心理学的大五人格理论（Big Five / OCEAN），提供用户性格评估功能。
参考 OkCupid 的详细问卷机制，帮助用户和匹配系统更深入地了解用户性格。

大五人格维度：
- O (Openness): 开放性 - 对新经验的开放程度
- C (Conscientiousness): 尽责性 - 组织性、责任感
- E (Extraversion): 外向性 - 社交倾向
- A (Agreeableness): 宜人性 - 合作性、同理心
- N (Neuroticism): 神经质 - 情绪稳定性
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import random
from utils.logger import logger


@dataclass
class PersonalityScore:
    """人格维度评分"""
    openness: float  # 开放性 0-1
    conscientiousness: float  # 尽责性 0-1
    extraversion: float  # 外向性 0-1
    agreeableness: float  # 宜人性 0-1
    neuroticism: float  # 神经质 0-1


@dataclass
class PersonalityResult:
    """性格测试结果"""
    scores: PersonalityScore
    dimension_labels: Dict[str, str]  # 各维度的等级标签
    description: str  # 整体性格描述
    strength_traits: List[str]  # 优势特质
    growth_areas: List[str]  # 可发展领域


class BigFiveAssessment:
    """
    大五人格评估器

    基于简化版量表，提供快速性格评估
    """

    # 简化版测试题目（每个维度 3 题，共 15 题）
    # 评分：1=非常不同意，2=不同意，3=中立，4=同意，5=非常同意
    QUESTIONS = [
        # 开放性 (Openness)
        {
            "id": 1,
            "dimension": "openness",
            "text": "我喜欢尝试新的事物和体验",
            "reverse": False
        },
        {
            "id": 2,
            "dimension": "openness",
            "text": "我对抽象思考和理论讨论感兴趣",
            "reverse": False
        },
        {
            "id": 3,
            "dimension": "openness",
            "text": "我更倾向于遵循熟悉的常规，而非尝试新方法",
            "reverse": True
        },
        # 尽责性 (Conscientiousness)
        {
            "id": 4,
            "dimension": "conscientiousness",
            "text": "我做事有条理，喜欢提前计划",
            "reverse": False
        },
        {
            "id": 5,
            "dimension": "conscientiousness",
            "text": "我会把任务拖延到最后一刻",
            "reverse": True
        },
        {
            "id": 6,
            "dimension": "conscientiousness",
            "text": "我注重细节，追求完美",
            "reverse": False
        },
        # 外向性 (Extraversion)
        {
            "id": 7,
            "dimension": "extraversion",
            "text": "我在社交场合感到充满活力",
            "reverse": False
        },
        {
            "id": 8,
            "dimension": "extraversion",
            "text": "我更享受独处的时光",
            "reverse": True
        },
        {
            "id": 9,
            "dimension": "extraversion",
            "text": "我喜欢成为关注的焦点",
            "reverse": False
        },
        # 宜人性 (Agreeableness)
        {
            "id": 10,
            "dimension": "agreeableness",
            "text": "我容易与他人产生共鸣",
            "reverse": False
        },
        {
            "id": 11,
            "dimension": "agreeableness",
            "text": "我倾向于质疑他人的动机",
            "reverse": True
        },
        {
            "id": 12,
            "dimension": "agreeableness",
            "text": "我愿意花时间帮助他人",
            "reverse": False
        },
        # 神经质 (Neuroticism)
        {
            "id": 13,
            "dimension": "neuroticism",
            "text": "我经常感到焦虑或不安",
            "reverse": False
        },
        {
            "id": 14,
            "dimension": "neuroticism",
            "text": "我的情绪波动比较大",
            "reverse": False
        },
        {
            "id": 15,
            "dimension": "neuroticism",
            "text": "我很少感到沮丧或情绪低落",
            "reverse": True
        },
    ]

    # 维度描述
    DIMENSION_DESCRIPTIONS = {
        "openness": {
            "name": "开放性",
            "high": "你富有创造力和好奇心，喜欢尝试新事物，接受新观念",
            "low": "你更偏好熟悉的事物，注重实际，做事有条理"
        },
        "conscientiousness": {
            "name": "尽责性",
            "high": "你做事认真负责，有条理，能够坚持完成任务",
            "low": "你更随性灵活，不喜欢被规则束缚"
        },
        "extraversion": {
            "name": "外向性",
            "high": "你外向活泼，从社交中获得能量，喜欢与人互动",
            "low": "你内向沉静，从独处中获得能量，偏好深度交流"
        },
        "agreeableness": {
            "name": "宜人性",
            "high": "你善解人意，乐于助人，容易与人相处",
            "low": "你更具批判性思维，不轻易妥协，坚持己见"
        },
        "neuroticism": {
            "name": "情绪稳定性",
            "high": "你情绪敏感，容易感到压力和焦虑",
            "low": "你情绪稳定，能够冷静应对压力"
        }
    }

    # 匹配建议 - 基于性格维度的兼容性
    COMPATIBILITY_INSIGHTS = {
        "extraversion": {
            "similar": "你们的外向程度相近，社交需求匹配",
            "complementary": "一个外向一个内向，可以互补但也需要理解彼此的社交需求"
        },
        "neuroticism": {
            "similar": "你们的情绪稳定性相近，能理解彼此的情绪反应",
            "complementary": "情绪稳定的一方可以为敏感的一方提供安全感"
        },
        "openness": {
            "similar": "你们对新事物的态度相近，生活方式契合",
            "complementary": "开放的一方可以带动另一方尝试新体验"
        }
    }

    @staticmethod
    def calculate_scores(answers: Dict[int, int]) -> PersonalityScore:
        """
        根据答案计算人格维度评分

        Args:
            answers: 题目 ID -> 答案 (1-5) 的映射

        Returns:
            各维度评分 (0-1)
        """
        dimension_scores = {dim: [] for dim in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]}

        for question in BigFiveAssessment.QUESTIONS:
            q_id = question["id"]
            if q_id not in answers:
                continue

            score = answers[q_id]
            if question["reverse"]:
                score = 6 - score  # 反向题转换

            # 转换为 0-1 范围
            normalized_score = (score - 1) / 4.0
            dimension_scores[question["dimension"]].append(normalized_score)

        # 计算各维度平均分
        return PersonalityScore(
            openness=sum(dimension_scores["openness"]) / len(dimension_scores["openness"]) if dimension_scores["openness"] else 0.5,
            conscientiousness=sum(dimension_scores["conscientiousness"]) / len(dimension_scores["conscientiousness"]) if dimension_scores["conscientiousness"] else 0.5,
            extraversion=sum(dimension_scores["extraversion"]) / len(dimension_scores["extraversion"]) if dimension_scores["extraversion"] else 0.5,
            agreeableness=sum(dimension_scores["agreeableness"]) / len(dimension_scores["agreeableness"]) if dimension_scores["agreeableness"] else 0.5,
            neuroticism=sum(dimension_scores["neuroticism"]) / len(dimension_scores["neuroticism"]) if dimension_scores["neuroticism"] else 0.5
        )

    @staticmethod
    def get_dimension_label(score: float, dimension: str) -> str:
        """获取维度等级标签"""
        if dimension == "neuroticism":
            # 神经质维度，低分更好
            if score < 0.33:
                return "情绪稳定"
            elif score < 0.66:
                return "情绪适中"
            else:
                return "情绪敏感"
        else:
            # 其他维度，高分更好
            if score < 0.33:
                return f"偏低"
            elif score < 0.66:
                return "适中"
            else:
                return "偏高"

    @staticmethod
    def generate_description(scores: PersonalityScore) -> str:
        """生成性格描述"""
        descriptions = []

        # 找出最突出的特质
        sorted_dims = sorted(
            [("openness", scores.openness), ("conscientiousness", scores.conscientiousness),
             ("extraversion", scores.extraversion), ("agreeableness", scores.agreeableness)],
            key=lambda x: x[1],
            reverse=True
        )

        top_dim = sorted_dims[0]
        desc = BigFiveAssessment.DIMENSION_DESCRIPTIONS[top_dim[0]]

        if top_dim[1] > 0.66:
            descriptions.append(desc["high"])
        elif top_dim[1] < 0.33:
            descriptions.append(desc["low"])

        # 添加情绪稳定性描述
        neuro_desc = BigFiveAssessment.DIMENSION_DESCRIPTIONS["neuroticism"]
        if scores.neuroticism < 0.33:
            descriptions.append(neuro_desc["low"])
        elif scores.neuroticism > 0.66:
            descriptions.append(neuro_desc["high"])

        return "。".join(descriptions) if descriptions else "你的性格特征比较均衡"

    @staticmethod
    def get_strength_traits(scores: PersonalityScore) -> List[str]:
        """识别优势特质"""
        traits = []

        if scores.openness > 0.66:
            traits.append("创造力和好奇心强")
        if scores.conscientiousness > 0.66:
            traits.append("做事认真负责")
        if scores.extraversion > 0.66:
            traits.append("善于社交和沟通")
        if scores.agreeableness > 0.66:
            traits.append("善解人意，乐于助人")
        if scores.neuroticism < 0.33:
            traits.append("情绪稳定，抗压能力强")

        return traits if traits else ["性格均衡，适应性强"]

    @staticmethod
    def get_growth_areas(scores: PersonalityScore) -> List[str]:
        """识别可发展领域"""
        areas = []

        if scores.openness < 0.33:
            areas.append("可以尝试更多新体验，拓展视野")
        if scores.conscientiousness < 0.33:
            areas.append("可以培养更好的时间管理和规划习惯")
        if scores.extraversion < 0.33:
            areas.append("可以尝试更多社交活动，扩大人际圈")
        if scores.agreeableness < 0.33:
            areas.append("可以多练习换位思考和同理心")
        if scores.neuroticism > 0.66:
            areas.append("可以学习压力管理和情绪调节技巧")

        return areas if areas else ["保持现有优势，持续发展"]

    @staticmethod
    def assess(answers: Dict[int, int]) -> PersonalityResult:
        """
        完整评估流程

        Args:
            answers: 题目答案

        Returns:
            完整评估结果
        """
        scores = BigFiveAssessment.calculate_scores(answers)

        dimension_labels = {
            "openness": BigFiveAssessment.get_dimension_label(scores.openness, "openness"),
            "conscientiousness": BigFiveAssessment.get_dimension_label(scores.conscientiousness, "conscientiousness"),
            "extraversion": BigFiveAssessment.get_dimension_label(scores.extraversion, "extraversion"),
            "agreeableness": BigFiveAssessment.get_dimension_label(scores.agreeableness, "agreeableness"),
            "neuroticism": BigFiveAssessment.get_dimension_label(scores.neuroticism, "neuroticism")
        }

        return PersonalityResult(
            scores=scores,
            dimension_labels=dimension_labels,
            description=BigFiveAssessment.generate_description(scores),
            strength_traits=BigFiveAssessment.get_strength_traits(scores),
            growth_areas=BigFiveAssessment.get_growth_areas(scores)
        )


class PersonalityTool:
    """
    性格测试工具 - Agent 工具封装

    功能：
    - 获取测试题目
    - 提交答案并获取结果
    - 性格兼容性分析
    """

    name = "personality_assessment"
    description = "大五人格测试和性格分析工具"
    tags = ["personality", "assessment", "psychology"]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["get_questions", "submit_answers", "analyze_compatibility"]
                },
                "answers": {
                    "type": "object",
                    "description": "题目答案 {题目 ID: 答案}",
                    "additionalProperties": {"type": "integer"}
                },
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "target_user_id": {
                    "type": "string",
                    "description": "目标用户 ID（用于兼容性分析）"
                }
            },
            "required": ["action"]
        }

    @staticmethod
    def handle(
        action: str,
        answers: Dict[int, int] = None,
        user_id: str = None,
        target_user_id: str = None
    ) -> dict:
        """处理性格测试请求"""
        logger.info(f"PersonalityTool: Executing action={action}")

        try:
            if action == "get_questions":
                # 返回测试题目
                questions = [
                    {
                        "id": q["id"],
                        "dimension": q["dimension"],
                        "text": q["text"]
                    }
                    for q in BigFiveAssessment.QUESTIONS
                ]
                return {
                    "questions": questions,
                    "instruction": "请对以下陈述进行评价：1=非常不同意，2=不同意，3=中立，4=同意，5=非常同意",
                    "total_questions": len(questions)
                }

            elif action == "submit_answers":
                if not answers:
                    return {"error": "answers is required"}

                # 验证答案
                valid_ids = {q["id"] for q in BigFiveAssessment.QUESTIONS}
                for q_id in answers.keys():
                    if q_id not in valid_ids:
                        return {"error": f"Invalid question id: {q_id}"}
                    if not 1 <= answers[q_id] <= 5:
                        return {"error": f"Answer for question {q_id} must be between 1 and 5"}

                # 计算结果
                result = BigFiveAssessment.assess(answers)

                return {
                    "scores": asdict(result.scores),
                    "dimension_labels": result.dimension_labels,
                    "description": result.description,
                    "strength_traits": result.strength_traits,
                    "growth_areas": result.growth_areas
                }

            elif action == "analyze_compatibility":
                if not user_id or not target_user_id:
                    return {"error": "user_id and target_user_id are required"}

                from db.database import get_db
                from db.repositories import UserRepository

                db = next(get_db())
                user_repo = UserRepository(db)

                db_user = user_repo.get_by_id(user_id)
                db_target = user_repo.get_by_id(target_user_id)

                if not db_user or not db_target:
                    return {"error": "User not found"}

                from api.users import _from_db
                user = _from_db(db_user)
                target = _from_db(db_target)

                # 获取双方性格评分
                user_scores = user.values or {}
                target_scores = target.values or {}

                # 计算维度差异
                dimensions = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
                compatibility_analysis = []

                for dim in dimensions:
                    user_score = user_scores.get(dim, 0.5)
                    target_score = target_scores.get(dim, 0.5)
                    diff = abs(user_score - target_score)

                    insight = BigFiveAssessment.COMPATIBILITY_INSIGHTS.get(dim, {})
                    if diff < 0.2:
                        message = insight.get("similar", f"你们的{dim}相近")
                    else:
                        message = insight.get("complementary", f"你们的{dim}有差异")

                    compatibility_analysis.append({
                        "dimension": dim,
                        "user_score": user_score,
                        "target_score": target_score,
                        "difference": round(diff, 3),
                        "insight": message
                    })

                # 计算总体性格兼容性
                avg_diff = sum(abs(user_scores.get(d, 0.5) - target_scores.get(d, 0.5)) for d in dimensions) / len(dimensions)
                personality_compatibility = 1 - avg_diff

                return {
                    "compatibility_score": round(personality_compatibility, 3),
                    "dimension_analysis": compatibility_analysis,
                    "summary": "性格高度兼容" if personality_compatibility > 0.8 else "性格较为兼容" if personality_compatibility > 0.6 else "性格有差异，需要相互理解"
                }

            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"PersonalityTool: Failed to execute action {action}: {e}")
            return {"error": str(e)}
