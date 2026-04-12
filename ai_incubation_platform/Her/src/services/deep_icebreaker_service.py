"""
深度破冰话题服务

扩展基础 IcebreakerService，提供：
- AI 生成个性化话题（基于双方画像）
- 话题深度递进（从轻松到深入）
- 话题效果预测
- 话题使用历史追踪
- 话题优化反馈
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from utils.logger import logger
from services.base_service import BaseService


class DeepIcebreakerService(BaseService):
    """深度破冰话题服务"""

    # 话题深度层级
    DEPTH_LEVELS = {
        1: "轻松开场 - 简单的自我介绍",
        2: "兴趣探索 - 发现共同兴趣",
        3: "经历分享 - 分享有趣经历",
        4: "价值观交流 - 深入想法和观念",
        5: "关系期望 - 对未来关系的想法"
    }

    # 话题类型
    TOPIC_TYPES = [
        "question",      # 提问式
        "story_share",   # 故事分享式
        "game",          # 游戏互动式
        "challenge",     # 挑战式
        "reflection",    # 反思式
    ]

    # 话题效果标签
    EFFECT_TAGS = [
        "建立信任",
        "引发共鸣",
        "激发好奇",
        "促进分享",
        "深度理解",
        "轻松愉快",
    ]

    def __init__(self, db: Session):
        super().__init__(db)
        self.db = db

    async def generate_personalized_topics(
        self,
        user_profile: Dict[str, Any],
        partner_profile: Dict[str, Any],
        conversation_context: Optional[List[Dict]] = None,
        depth_level: int = 1
    ) -> List[Dict[str, Any]]:
        """
        AI 生成个性化破冰话题

        基于双方画像和对话上下文，生成最适合的话题

        Args:
            user_profile: 用户资料
            partner_profile: 对方资料
            conversation_context: 对话上下文（可选）
            depth_level: 期望的话题深度（1-5）

        Returns:
            话题列表
        """
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        # 分析共同点
        common_interests = self._find_common_interests(
            user_profile.get("interests", []),
            partner_profile.get("interests", [])
        )

        # 构建上下文
        context = f"""
用户 A：
- 年龄：{user_profile.get('age')}
- 兴趣：{user_profile.get('interests', [])}
- 简介：{user_profile.get('bio', '')}
- 交友目的：{user_profile.get('goal', '')}

用户 B：
- 年龄：{partner_profile.get('age')}
- 兴趣：{partner_profile.get('interests', [])}
- 简介：{partner_profile.get('bio', '')}
- 交友目的：{partner_profile.get('goal', '')}

共同兴趣：{common_interests}
"""

        if conversation_context:
            recent_messages = conversation_context[-5:]
            context += "\n最近对话：\n" + "\n".join([
                f"{m.get('sender')}: {m.get('content')}"
                for m in recent_messages
            ])

        prompt = f"""请为这两位用户生成 {3-5} 个个性化破冰话题：

{context}

话题深度要求：{self.DEPTH_LEVELS.get(depth_level, "轻松开场")}

请生成以下类型的话题：
1. 提问式 - 通过问题引发对方分享
2. 故事分享式 - 先分享自己的故事，邀请对方回应
3. 游戏互动式 - 有趣的小游戏或挑战

每个话题请给出：
- 话题内容
- 话题类型
- 适用场景
- 预期效果
- 为什么这个话题适合这两位用户

回复格式：
[
  {
    "topic_content": "话题内容",
    "topic_type": "question",
    "depth_level": {depth_level},
    "suitable_scenario": "首次对话",
    "expected_effect": "建立信任",
    "personalization_reason": "基于共同兴趣...",
    "confidence": 0.85
  },
  ...
]"""

        try:
            result = await llm_service.generate(prompt)
            import json
            topics = json.loads(result)

            # 记录生成历史
            await self._record_generation_history(
                user_profile.get("id", ""),
                partner_profile.get("id", ""),
                topics,
                depth_level
            )

            return topics
        except Exception as e:
            logger.error(f"Failed to generate personalized topics: {e}")
            # 返回默认话题
            return self._get_default_topics(depth_level)

    def _find_common_interests(
        self,
        interests_a: List[str],
        interests_b: List[str]
    ) -> List[str]:
        """发现共同兴趣"""
        if not interests_a or not interests_b:
            return []

        return list(set(interests_a) & set(interests_b))

    async def _record_generation_history(
        self,
        user_id: str,
        partner_id: str,
        topics: List[Dict],
        depth_level: int
    ):
        """记录话题生成历史"""
        from models.deep_icebreaker import IcebreakerTopicHistoryDB

        for topic in topics:
            history = IcebreakerTopicHistoryDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                partner_id=partner_id,
                topic_content=topic.get("topic_content"),
                topic_type=topic.get("topic_type"),
                depth_level=depth_level,
                generation_method="ai_generated",
                created_at=datetime.now()
            )
            self.db.add(history)

        self.db.commit()

    def _get_default_topics(self, depth_level: int) -> List[Dict]:
        """获取默认话题（AI 失败时的备用）"""
        default_topics = {
            1: [
                {"topic_content": "你最近有什么有趣的事情发生吗？", "topic_type": "question", "depth_level": 1},
                {"topic_content": "我最近学了一个新技能，想分享给你...", "topic_type": "story_share", "depth_level": 1},
            ],
            2: [
                {"topic_content": "我注意到你也喜欢[兴趣]，你是从什么时候开始接触的？", "topic_type": "question", "depth_level": 2},
            ],
            3: [
                {"topic_content": "有什么经历让你印象特别深刻吗？", "topic_type": "question", "depth_level": 3},
            ],
            4: [
                {"topic_content": "你觉得什么是一段好关系最重要的特质？", "topic_type": "question", "depth_level": 4},
            ],
            5: [
                {"topic_content": "你对未来的关系有什么期望？", "topic_type": "question", "depth_level": 5},
            ]
        }

        return default_topics.get(depth_level, default_topics[1])

    def get_topic_progression_suggestions(
        self,
        conversation_length: int,
        engagement_level: float
    ) -> Dict[str, Any]:
        """
        根据对话进展推荐话题深度

        Args:
            conversation_length: 对话轮数
            engagement_level: 互动程度（0-1）

        Returns:
            推荐的深度层级和说明
        """
        # 基础规则
        if conversation_length <= 5:
            recommended_level = 1
            reason = "对话刚开始，建议轻松开场"
        elif conversation_length <= 15:
            recommended_level = 2
            reason = "可以探索共同兴趣了"
        elif conversation_length <= 30:
            recommended_level = 3
            reason = "对话气氛不错，可以分享更多经历"
        elif engagement_level > 0.7:
            recommended_level = 4
            reason = "互动积极，可以深入交流价值观"
        else:
            recommended_level = 3
            reason = "保持当前深度，不要急于深入"

        return {
            "recommended_depth": recommended_level,
            "reason": reason,
            "depth_description": self.DEPTH_LEVELS.get(recommended_level),
            "next_level_hint": self.DEPTH_LEVELS.get(recommended_level + 1) if recommended_level < 5 else None
        }

    async def optimize_topic_based_on_feedback(
        self,
        topic_id: str,
        feedback_type: str,  # positive/negative/neutral
        feedback_detail: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据反馈优化话题

        Args:
            topic_id: 话题 ID
            feedback_type: 反馈类型
            feedback_detail: 反馈详情

        Returns:
            优化建议
        """
        from models.deep_icebreaker import IcebreakerTopicFeedbackDB

        # 记录反馈
        feedback = IcebreakerTopicFeedbackDB(
            id=str(uuid.uuid4()),
            topic_id=topic_id,
            feedback_type=feedback_type,
            feedback_detail=feedback_detail,
            created_at=datetime.now()
        )
        self.db.add(feedback)
        self.db.commit()

        # 如果是负面反馈，生成改进建议
        if feedback_type == "negative":
            # AI 改进建议生成（当前使用预设建议，后续可集成 LLM 生成个性化建议）
            return {
                "feedback_recorded": True,
                "optimization_suggestion": "话题可能太直接，建议更委婉地表达"
            }

        return {"feedback_recorded": True}

    def get_topic_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的话题使用统计

        Args:
            user_id: 用户 ID

        Returns:
            统计数据
        """
        from models.deep_icebreaker import IcebreakerTopicHistoryDB

        # 统计各深度话题使用次数
        stats = {}
        for level in range(1, 6):
            count = self.db.query(IcebreakerTopicHistoryDB).filter(
                IcebreakerTopicHistoryDB.user_id == user_id,
                IcebreakerTopicHistoryDB.depth_level == level
            ).count()
            stats[f"depth_{level}_count"] = count

        # 统计话题类型使用次数
        for topic_type in self.TOPIC_TYPES:
            count = self.db.query(IcebreakerTopicHistoryDB).filter(
                IcebreakerTopicHistoryDB.user_id == user_id,
                IcebreakerTopicHistoryDB.topic_type == topic_type
            ).count()
            stats[f"type_{topic_type}_count"] = count

        # 总使用次数
        stats["total_count"] = self.db.query(IcebreakerTopicHistoryDB).filter(
            IcebreakerTopicHistoryDB.user_id == user_id
        ).count()

        return stats


# 服务工厂函数
def get_deep_icebreaker_service(db: Session) -> DeepIcebreakerService:
    """获取深度破冰话题服务实例"""
    return DeepIcebreakerService(db)