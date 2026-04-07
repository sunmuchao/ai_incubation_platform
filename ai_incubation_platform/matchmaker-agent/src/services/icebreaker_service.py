"""
v1.3 破冰问题服务

基于用户画像和兴趣，生成个性化的破冰问题。
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import json
import random

from db.models import IcebreakerQuestionDB, UserDB


class IcebreakerService:
    """破冰问题服务"""

    # 内置问题库（初始种子数据）
    BUILTIN_QUESTIONS = [
        # 轻松话题 (casual)
        {"question": "你最近看过什么好看的电影或电视剧吗？", "category": "casual", "depth_level": 1},
        {"question": "你平时喜欢做什么运动？", "category": "casual", "depth_level": 1},
        {"question": "如果你可以去世界上任何地方旅行，你会选择哪里？", "category": "casual", "depth_level": 2},
        {"question": "你有什么特别的爱好或技能吗？", "category": "casual", "depth_level": 1},
        {"question": "你最喜欢的食物是什么？有没有特别推荐的餐厅？", "category": "casual", "depth_level": 1},

        # 深入话题 (deep)
        {"question": "你认为什么是一段好的关系最重要的特质？", "category": "deep", "depth_level": 4},
        {"question": "你的人生目标是什么？", "category": "deep", "depth_level": 4},
        {"question": "你最近学到的最有意思的东西是什么？", "category": "deep", "depth_level": 3},
        {"question": "什么事情会让你感到最有成就感？", "category": "deep", "depth_level": 3},

        # 趣味话题 (fun)
        {"question": "如果你可以拥有任何一种超能力，你会选择什么？", "category": "fun", "depth_level": 2},
        {"question": "如果你可以和任何历史人物共进晚餐，你会选择谁？", "category": "fun", "depth_level": 2},
        {"question": "你有没有什么奇怪但有趣的小习惯？", "category": "fun", "depth_level": 2},
        {"question": "如果你可以立即学会任何一种乐器，你会选择什么？", "category": "fun", "depth_level": 2},

        # 价值观话题 (values)
        {"question": "你对婚姻的看法是什么？", "category": "values", "depth_level": 5},
        {"question": "你认为家庭在生活中的重要性如何？", "category": "values", "depth_level": 5},
        {"question": "你理想中的生活方式是什么样的？", "category": "values", "depth_level": 4},
        {"question": "你认为两个人在一起最重要的是什么？", "category": "values", "depth_level": 5},
    ]

    def __init__(self, db: Session):
        self.db = db
        self._init_builtin_questions()

    def _init_builtin_questions(self):
        """初始化内置问题库"""
        existing_count = self.db.query(IcebreakerQuestionDB).count()
        if existing_count > 0:
            return  # 已有数据，跳过初始化

        for q in self.BUILTIN_QUESTIONS:
            question = IcebreakerQuestionDB(
                id=str(hash(q["question"]) & 0xFFFFFFFF),
                question=q["question"],
                category=q["category"],
                depth_level=q["depth_level"],
                suitable_scenarios=json.dumps(["first_date"]),
            )
            self.db.add(question)

        self.db.commit()

    def get_questions(
        self,
        category: Optional[str] = None,
        depth_level: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取破冰问题"""
        query = self.db.query(IcebreakerQuestionDB)

        if category:
            query = query.filter(IcebreakerQuestionDB.category == category)

        if depth_level:
            query = query.filter(IcebreakerQuestionDB.depth_level == depth_level)

        # 随机选择
        questions = query.order_by(func.random()).limit(limit).all()

        return [
            {
                "id": q.id,
                "question": q.question,
                "category": q.category,
                "depth_level": q.depth_level,
                "usage_count": q.usage_count,
            }
            for q in questions
        ]

    def get_personalized_questions(
        self,
        user_id_1: str,
        user_id_2: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """基于用户画像获取个性化问题"""
        # 获取用户信息
        user1 = self.db.query(UserDB).filter(UserDB.id == user_id_1).first()
        user2 = self.db.query(UserDB).filter(UserDB.id == user_id_2).first()

        if not user1 or not user2:
            return self.get_questions(limit=limit)

        # 解析兴趣
        user1_interests = json.loads(user1.interests) if user1.interests else []
        user2_interests = json.loads(user2.interests) if user2.interests else []

        # 查找共同兴趣
        common_interests = set(user1_interests) & set(user2_interests)

        # 根据共同兴趣选择问题策略
        if common_interests:
            # 有共同兴趣，优先返回轻松话题
            questions = self.get_questions(category="casual", limit=limit)
        elif user1.age and user2.age and abs(user1.age - user2.age) <= 3:
            # 年龄相仿，可以深入一些
            questions = self.get_questions(category="fun", limit=limit)
        else:
            # 默认混合返回
            questions = self.get_questions(limit=limit)

        return questions

    def get_category_progression(self, date_id: str, games_played: int = 0) -> str:
        """
        根据约会进展推荐问题类别

        约会初期：casual -> fun
        约会中期：deep
        约会后期：values
        """
        if games_played <= 2:
            return "casual"
        elif games_played <= 4:
            return "fun"
        elif games_played <= 6:
            return "deep"
        else:
            return "values"

    def record_feedback(self, question_id: str, is_positive: bool) -> bool:
        """记录问题反馈"""
        question = self.db.query(IcebreakerQuestionDB).filter(
            IcebreakerQuestionDB.id == question_id
        ).first()

        if not question:
            return False

        # 更新使用统计
        question.usage_count += 1

        # 更新好评率（移动平均）
        total = question.usage_count
        if is_positive:
            # 新好评
            question.positive_feedback_rate = (
                (question.positive_feedback_rate * (total - 1) + 1) / total
            )
        else:
            # 新差评
            question.positive_feedback_rate = (
                (question.positive_feedback_rate * (total - 1)) / total
            )

        self.db.commit()
        return True

    def get_question_stats(self) -> Dict[str, Any]:
        """获取问题统计"""
        total = self.db.query(IcebreakerQuestionDB).count()
        by_category = self.db.query(
            IcebreakerQuestionDB.category, func.count(IcebreakerQuestionDB.id)
        ).group_by(IcebreakerQuestionDB.category).all()

        most_used = self.db.query(IcebreakerQuestionDB).order_by(
            IcebreakerQuestionDB.usage_count.desc()
        ).limit(5).all()

        return {
            "total_questions": total,
            "by_category": {cat: cnt for cat, cnt in by_category},
            "most_used": [
                {"question": q.question, "usage_count": q.usage_count}
                for q in most_used
            ],
        }
