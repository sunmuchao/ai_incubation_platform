"""
P14 实战演习服务层

核心理念：约会教练与保镖
消除见面焦虑，确保每一次见面得体，专业分工协作。

包含以下服务：
1. 约会模拟沙盒服务 - AI 分身、场景模拟、反馈
2. 约会辅助服务 - 穿搭推荐、场所策略、话题锦囊
3. 多代理协作服务 - 红娘、教练、保安 Agent 协同
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import random
import json

from db.database import SessionLocal
from db.models import UserDB
from models.p14_models import (
    AIDateAvatarDB,
    DateSimulationDB,
    SimulationFeedbackDB,
    DateOutfitRecommendationDB,
    DateVenueStrategyDB,
    DateTopicKitDB,
    AgentCollaborationRecordDB,
    MatchmakerAgentSessionDB,
    CoachAgentSessionDB,
    GuardianAgentSessionDB,
    SimulationScenarioType,
    AvatarPersonalityType,
    AgentType
)
from utils.logger import logger


# ==================== 约会模拟沙盒服务 ====================

class DateSimulationService:
    """约会模拟沙盒服务"""

    # 默认场景配置
    DEFAULT_SCENARIOS = {
        SimulationScenarioType.RESTAURANT.value: {
            "name": "浪漫餐厅",
            "description": "一家温馨的意大利餐厅，柔和的灯光，轻音乐背景",
            "atmosphere": "romantic",
            "noise_level": "quiet",
            "suitable_for": ["first_date", "anniversary"]
        },
        SimulationScenarioType.CAFE.value: {
            "name": "休闲咖啡厅",
            "description": "轻松的咖啡厅环境，适合深度交流",
            "atmosphere": "casual",
            "noise_level": "moderate",
            "suitable_for": ["first_meet", "casual_chat"]
        },
        SimulationScenarioType.PARK.value: {
            "name": "城市公园",
            "description": "阳光明媚的公园，可以散步聊天",
            "atmosphere": "relaxed",
            "noise_level": "outdoor",
            "suitable_for": ["active_date", "casual"]
        },
        SimulationScenarioType.CINEMA.value: {
            "name": "电影院",
            "description": "观看电影后讨论剧情",
            "atmosphere": "entertainment",
            "noise_level": "quiet_during_movie",
            "suitable_for": ["movie_date", "shared_experience"]
        }
    }

    # 对话开场白模板
    OPENING_LINES = [
        "嗨，很高兴见到你！这里环境还不错吧？",
        "你好！我早就想来这家店了，你觉得怎么样？",
        "哈喽！今天过得怎么样？",
        "很高兴终于见面了！一路上还顺利吗？"
    ]

    # 常见对话主题
    CONVERSATION_TOPICS = [
        "工作和职业",
        "兴趣爱好",
        "旅行经历",
        "美食偏好",
        "电影音乐",
        "家庭朋友",
        "未来规划",
        "童年回忆"
    ]

    def __init__(self):
        pass

    def create_avatar(
        self,
        user_id: str,
        avatar_name: str,
        personality: str = AvatarPersonalityType.OUTGOING.value,
        interests: Optional[List[str]] = None,
        db_session=None
    ) -> AIDateAvatarDB:
        """
        创建 AI 约会分身

        参数:
        - user_id: 用户 ID
        - avatar_name: 分身名称
        - personality: 性格类型
        - interests: 兴趣爱好列表
        """
        # 基于用户信息生成分身
        user = db_session.query(UserDB).filter(UserDB.id == user_id).first()

        # 如果没有指定兴趣，使用用户的兴趣
        if not interests and user:
            interests = getattr(user, 'interests', [])

        # 生成性格特征
        personality_traits = self._generate_personality_traits(personality)

        # 创建分身
        avatar_id = f"avatar_{user_id}_{datetime.utcnow().timestamp()}"
        avatar = AIDateAvatarDB(
            id=avatar_id,
            user_id=user_id,
            avatar_name=avatar_name,
            personality=personality,
            personality_traits=personality_traits,
            interests=interests or [],
            conversation_style=self._get_conversation_style(personality),
            is_active=True
        )

        db_session.add(avatar)
        db_session.commit()
        db_session.refresh(avatar)

        return avatar

    def _generate_personality_traits(self, personality: str) -> List[str]:
        """根据性格类型生成特征"""
        trait_map = {
            AvatarPersonalityType.OUTGOING.value: ["健谈", "热情", "主动", "外向"],
            AvatarPersonalityType.INTROVERTED.value: ["内敛", "深思", "倾听", "安静"],
            AvatarPersonalityType.HUMOROUS.value: ["幽默", "风趣", "乐观", "有趣"],
            AvatarPersonalityType.SERIOUS.value: ["认真", "稳重", "直接", "专注"],
            AvatarPersonalityType.GENTLE.value: ["温柔", "体贴", "耐心", "善解人意"],
            AvatarPersonalityType.INDEPENDENT.value: ["独立", "自信", "果断", "自主"]
        }
        return trait_map.get(personality, trait_map[AvatarPersonalityType.OUTGOING.value])

    def _get_conversation_style(self, personality: str) -> str:
        """获取对话风格"""
        style_map = {
            AvatarPersonalityType.OUTGOING.value: "casual",
            AvatarPersonalityType.INTROVERTED.value: "thoughtful",
            AvatarPersonalityType.HUMOROUS.value: "playful",
            AvatarPersonalityType.SERIOUS.value: "formal",
            AvatarPersonalityType.GENTLE.value: "warm",
            AvatarPersonalityType.INDEPENDENT.value: "direct"
        }
        return style_map.get(personality, "casual")

    def get_avatar(self, avatar_id: str, db_session) -> Optional[AIDateAvatarDB]:
        """获取 AI 分身"""
        return db_session.query(AIDateAvatarDB).filter(
            AIDateAvatarDB.id == avatar_id
        ).first()

    def get_user_avatars(self, user_id: str, db_session) -> List[AIDateAvatarDB]:
        """获取用户的所有分身"""
        return db_session.query(AIDateAvatarDB).filter(
            AIDateAvatarDB.user_id == user_id,
            AIDateAvatarDB.is_active == True
        ).all()

    def start_simulation(
        self,
        user_id: str,
        avatar_id: str,
        scenario: str,
        simulation_goal: Optional[str] = None,
        db_session=None
    ) -> DateSimulationDB:
        """
        开始约会模拟

        参数:
        - user_id: 用户 ID
        - avatar_id: AI 分身 ID
        - scenario: 约会场景
        - simulation_goal: 模拟目标
        """
        # 获取场景信息
        scenario_info = self.DEFAULT_SCENARIOS.get(scenario, {
            "name": scenario,
            "description": f"在{scenario}进行约会模拟",
            "atmosphere": "neutral"
        })

        # 创建模拟记录
        simulation_id = f"sim_{user_id}_{datetime.utcnow().timestamp()}"
        simulation = DateSimulationDB(
            id=simulation_id,
            user_id=user_id,
            avatar_id=avatar_id,
            scenario=scenario,
            scenario_description=scenario_info.get("description", ""),
            simulation_goal=simulation_goal or "练习约会对话",
            status="ongoing",
            conversation_history=[]
        )

        db_session.add(simulation)
        db_session.commit()
        db_session.refresh(simulation)

        return simulation

    def add_message_to_simulation(
        self,
        simulation_id: str,
        role: str,  # "user" or "ai"
        content: str,
        db_session=None
    ) -> bool:
        """添加消息到模拟对话"""
        simulation = db_session.query(DateSimulationDB).filter(
            DateSimulationDB.id == simulation_id
        ).first()

        if not simulation:
            return False

        # 添加消息到对话历史
        if simulation.conversation_history is None:
            simulation.conversation_history = []

        simulation.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        simulation.message_count += 1

        db_session.commit()
        return True

    def complete_simulation(
        self,
        simulation_id: str,
        self_rating: Optional[int] = None,
        db_session=None
    ) -> DateSimulationDB:
        """完成模拟"""
        simulation = db_session.query(DateSimulationDB).filter(
            DateSimulationDB.id == simulation_id
        ).first()

        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")

        simulation.is_completed = True
        simulation.status = "completed"
        simulation.completed_at = datetime.utcnow()
        simulation.self_rating = self_rating

        # 计算时长
        if simulation.created_at:
            duration = (simulation.completed_at - simulation.created_at).total_seconds()
            simulation.duration_seconds = int(duration)

        # 更新分身使用次数
        avatar = db_session.query(AIDateAvatarDB).filter(
            AIDateAvatarDB.id == simulation.avatar_id
        ).first()
        if avatar:
            avatar.usage_count += 1
            db_session.commit()

        db_session.commit()
        db_session.refresh(simulation)

        return simulation

    def generate_feedback(
        self,
        simulation_id: str,
        db_session=None
    ) -> SimulationFeedbackDB:
        """
        生成模拟反馈

        分析对话历史，生成评分和建议
        """
        simulation = db_session.query(DateSimulationDB).filter(
            DateSimulationDB.id == simulation_id
        ).first()

        if not simulation or not simulation.conversation_history:
            raise ValueError("No simulation data to analyze")

        # 分析对话
        analysis = self._analyze_conversation(simulation.conversation_history)

        # 创建反馈
        feedback_id = f"feedback_{simulation_id}"
        feedback = SimulationFeedbackDB(
            id=feedback_id,
            simulation_id=simulation_id,
            overall_score=analysis["overall_score"],
            conversation_score=analysis["conversation_score"],
            empathy_score=analysis["empathy_score"],
            humor_score=analysis["humor_score"],
            confidence_score=analysis["confidence_score"],
            listening_score=analysis["listening_score"],
            ai_comments=analysis["comments"],
            highlights=analysis["highlights"],
            improvement_suggestions=analysis["suggestions"],
            recommended_practices=analysis["recommended_practices"],
            key_moments=analysis["key_moments"]
        )

        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        return feedback

    def _analyze_conversation(
        self,
        conversation_history: List[Dict]
    ) -> Dict[str, Any]:
        """分析对话历史"""
        # 简单实现：基于规则的分析
        # 实际应该使用 LLM 进行深度分析

        user_messages = [m for m in conversation_history if m["role"] == "user"]
        ai_messages = [m for m in conversation_history if m["role"] == "ai"]

        # 计算基础分数
        message_count = len(user_messages)
        avg_message_length = sum(len(m["content"]) for m in user_messages) / max(1, len(user_messages))

        # 各维度评分（简化版）
        overall_score = min(10, max(1, int(message_count / 2) + int(avg_message_length / 20)))
        conversation_score = min(10, int(avg_message_length / 15))
        empathy_score = random.randint(5, 9)  # 简化
        humor_score = random.randint(4, 8)
        confidence_score = min(10, int(message_count / 3))
        listening_score = min(10, 5 + len(user_messages) // 2)

        # 生成评语
        comments = self._generate_comments(overall_score, conversation_history)

        # 亮点和建议
        highlights = []
        suggestions = []

        if message_count > 5:
            highlights.append("积极参与对话")
        if avg_message_length > 30:
            highlights.append("表达详细清晰")
        if len(user_messages) < len(ai_messages):
            suggestions.append("可以更主动地发起话题")

        if avg_message_length < 20:
            suggestions.append("尝试更详细地表达自己的想法")

        recommended_practices = []
        if listening_score < 7:
            recommended_practices.append("练习积极倾听，回应对方的话题")
        if confidence_score < 6:
            recommended_practices.append("增强自信，相信自己的魅力")

        return {
            "overall_score": overall_score,
            "conversation_score": conversation_score,
            "empathy_score": empathy_score,
            "humor_score": humor_score,
            "confidence_score": confidence_score,
            "listening_score": listening_score,
            "comments": comments,
            "highlights": highlights,
            "suggestions": suggestions,
            "recommended_practices": recommended_practices,
            "key_moments": self._extract_key_moments(conversation_history)
        }

    def _generate_comments(
        self,
        overall_score: int,
        conversation_history: List[Dict]
    ) -> str:
        """生成 AI 评语"""
        if overall_score >= 8:
            return "表现非常出色！你的对话自然流畅，展现了良好的沟通技巧。继续保持！"
        elif overall_score >= 6:
            return "表现不错！有一些亮点，也有一些可以改进的地方。参考具体建议继续练习。"
        else:
            return "还有进步空间。不要气馁，多练习会让你更自信。参考建议针对性训练。"

    def _extract_key_moments(
        self,
        conversation_history: List[Dict]
    ) -> List[Dict]:
        """提取关键时刻"""
        # 简化实现：返回前几个对话
        key_moments = []
        for i, msg in enumerate(conversation_history[:6]):
            if i % 2 == 0:  # 每对消息取一个
                key_moments.append({
                    "index": i,
                    "role": msg["role"],
                    "content": msg["content"][:100],  # 截取前 100 字
                    "note": "对话片段"
                })
        return key_moments

    def get_simulation(self, simulation_id: str, db_session) -> Optional[DateSimulationDB]:
        """获取模拟记录"""
        return db_session.query(DateSimulationDB).filter(
            DateSimulationDB.id == simulation_id
        ).first()

    def get_user_simulations(
        self,
        user_id: str,
        db_session,
        limit: int = 10
    ) -> List[DateSimulationDB]:
        """获取用户的模拟历史"""
        return db_session.query(DateSimulationDB).filter(
            DateSimulationDB.user_id == user_id
        ).order_by(DateSimulationDB.created_at.desc()).limit(limit).all()

    def get_simulation_feedback(
        self,
        simulation_id: str,
        db_session
    ) -> Optional[SimulationFeedbackDB]:
        """获取模拟反馈"""
        return db_session.query(SimulationFeedbackDB).filter(
            SimulationFeedbackDB.simulation_id == simulation_id
        ).first()


# 创建全局服务实例
date_simulation_service = DateSimulationService()
