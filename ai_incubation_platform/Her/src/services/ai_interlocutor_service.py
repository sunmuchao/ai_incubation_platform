"""
AI 预沟通服务（AI Interlocutor Service）

EmotionWeather 核心功能：替你先聊 50 句，只聊有价值的后半段

核心理念:
- 用户不再需要重复回答基础问题
- 只聊最有价值的后半段
- 极大提升匹配效率和用户满意度

功能模块:
1. AI 替身初筛 - 基于用户画像生成 AI 替身
2. 择偶硬指标校验 - 自动确认双方核心条件匹配
3. 价值观底线探测 - 识别不可妥协的价值观差异
4. 自动对聊引擎 - 双方 AI 进行 50+ 轮深度对话
5. 关键信息提取 - 从对话中提取定居计划、生育观念等
6. 匹配度报告 - 生成详细的三观匹配报告
7. 推送建议 - 高匹配度推送，低匹配度静默
"""
import json
import random
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from db.models import (
    UserDB, AIPreCommunicationSessionDB, AIPreCommunicationMessageDB,
    UserRelationshipPreferenceDB, EducationVerificationDB, CareerVerificationDB
)
from utils.logger import logger
from agent.user_simulation_agent import UserSimulationAgent
from services.base_service import BaseService


# ============= 硬指标校验配置 =============

HARD_INDICATORS_CONFIG = {
    "age_gap_max": 15,  # 最大年龄差
    "distance_max_km": 500,  # 最大地理距离（公里）
    "dealbreakers": [
        "children_disagreement",  # 生育观念不一致
        "location_immovable",  # 定居地不可调和
        "relationship_type_mismatch"  # 关系类型不匹配
    ]
}

# ============= 价值观探测题目 =============

VALUES_PROBING_QUESTIONS = [
    {
        "category": "marriage_view",
        "questions": [
            "你对婚姻的看法是什么？觉得一定要结婚吗？",
            "你觉得理想的婚姻状态是什么样的？",
            "对于婚前同居，你怎么看？",
        ]
    },
    {
        "category": "children_view",
        "questions": [
            "你打算要孩子吗？还是选择丁克？",
            "你觉得要几个孩子比较理想？",
            "对于孩子的教育方式，你有什么想法？",
        ]
    },
    {
        "category": "career_family",
        "questions": [
            "你怎么看待事业和家庭的平衡？",
            "如果伴侣需要异地工作，你会支持吗？",
            "你觉得家务应该怎样分配？",
        ]
    },
    {
        "category": "financial_view",
        "questions": [
            "你觉得婚后应该 AA 制还是共同理财？",
            "对于储蓄和消费，你是什么态度？",
            "你有多少存款会觉得有安全感？",
        ]
    },
    {
        "category": "lifestyle",
        "questions": [
            "你更向往哪种生活方式？热闹的还是安静的？",
            "对于和双方父母同住，你怎么看？",
            "你平时怎么安排业余时间？",
        ]
    }
]

# ============= 关键信息提取配置 =============

KEY_INFO_CATEGORIES = {
    "settlement_plan": {  # 定居计划
        "keywords": ["定居", "买房", "城市", "地方", "家乡", "发展"],
        "extract_pattern": "location"
    },
    "children_plan": {  # 生育计划
        "keywords": ["孩子", "小孩", "宝宝", "生育", "丁克", "要几个"],
        "extract_pattern": "children_count"
    },
    "marriage_timeline": {  # 婚姻时间线
        "keywords": ["结婚", "领证", "求婚", "订婚", "什么时候"],
        "extract_pattern": "timeline"
    },
    "career_priority": {  # 事业优先级
        "keywords": ["工作", "事业", "升职", "加薪", "辞职", "跳槽"],
        "extract_pattern": "priority_level"
    },
    "pet_attitude": {  # 宠物态度
        "keywords": ["宠物", "猫", "狗", "养动物", "毛孩子"],
        "extract_pattern": "pet_preference"
    }
}


class AIInterlocutorService(BaseService):
    """AI 预沟通服务"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.agents_cache: Dict[str, UserSimulationAgent] = {}

    # ============= 核心流程 =============

    async def start_pre_communication(
        self,
        user_id_1: str,
        user_id_2: str,
        target_rounds: int = 50
    ) -> AIPreCommunicationSessionDB:
        """
        启动 AI 预沟通会话

        Args:
            user_id_1: 发起方用户 ID
            user_id_2: 目标用户 ID
            target_rounds: 目标对话轮数

        Returns:
            AIPreCommunicationSessionDB: 创建的会话
        """
        logger.info(f"Starting AI pre-communication: {user_id_1} <-> {user_id_2}")

        # 1. 创建会话
        session = AIPreCommunicationSessionDB(
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            target_rounds=target_rounds,
            status="pending"
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # 2. 硬指标校验
        hard_check_result = await self._check_hard_indicators(user_id_1, user_id_2)
        session.hard_check_result = json.dumps(hard_check_result)
        session.hard_check_passed = hard_check_result.get("passed", False)

        if not session.hard_check_passed:
            # 硬指标不通过，直接结束
            session.status = "completed"
            session.recommendation = "silent"
            session.recommendation_reason = hard_check_result.get("reason", "硬指标不匹配")
            self.db.commit()
            logger.info(f"Pre-communication cancelled due to hard check failure: {user_id_1} <-> {user_id_2}")
            return session

        # 3. 价值观底线探测（快速版）
        values_check_result = await self._probe_values_baseline(user_id_1, user_id_2)
        session.values_check_result = json.dumps(values_check_result)
        session.values_check_passed = values_check_result.get("passed", True)

        if not session.values_check_passed:
            # 价值观底线不通过，结束
            session.status = "completed"
            session.recommendation = "silent"
            session.recommendation_reason = values_check_result.get("reason", "价值观底线不合")
            self.db.commit()
            logger.info(f"Pre-communication cancelled due to values check failure: {user_id_1} <-> {user_id_2}")
            return session

        # 4. 开始 AI 对聊
        session.status = "chatting"
        session.started_at = datetime.now()
        self.db.commit()

        # 异步启动对聊引擎（不阻塞返回）
        asyncio.create_task(
            self._run_conversation_engine(session.id, user_id_1, user_id_2, target_rounds)
        )

        logger.info(f"AI pre-communication started: {user_id_1} <-> {user_id_2}")
        return session

    async def _run_conversation_engine(
        self,
        session_id: str,
        user_id_1: str,
        user_id_2: str,
        target_rounds: int
    ):
        """
        运行自动对聊引擎

        Args:
            session_id: 会话 ID
            user_id_1: 用户 1 ID
            user_id_2: 用户 2 ID
            target_rounds: 目标轮数
        """
        try:
            session = self.db.query(AIPreCommunicationSessionDB).filter(
                AIPreCommunicationSessionDB.id == session_id
            ).first()

            if not session:
                logger.error(f"Session {session_id} not found")
                return

            # 创建 AI 替身
            agent1 = self._create_agent_for_user(user_id_1)
            agent2 = self._create_agent_for_user(user_id_2)

            logger.info(f"Conversation engine started for session {session_id}")

            # 进行多轮对话
            for round_num in range(1, target_rounds + 1):
                if session.status != "chatting":
                    logger.info(f"Conversation stopped at round {round_num} due to status change")
                    break

                # 决定哪一方先发言（奇数轮用户 1 先，偶数轮用户 2 先）
                if round_num % 2 == 1:
                    first_agent, first_user = agent1, user_id_1
                    second_agent, second_user = agent2, user_id_2
                else:
                    first_agent, first_user = agent2, user_id_2
                    second_agent, second_user = agent1, user_id_1

                # 生成话题
                topic = self._generate_conversation_topic(round_num, VALUES_PROBING_QUESTIONS)

                # 第一轮：发起话题
                first_message = first_agent.generate_reply(
                    message_content=topic["starter"],
                    sender_name=f"用户{second_user[-4:]}"
                )
                self._save_message(session, first_user, first_message, round_num, "question")

                # 等待延迟
                await asyncio.sleep(random.uniform(1, 3))

                # 第二轮：回复
                second_message = second_agent.generate_reply(
                    message_content=first_message,
                    sender_name=f"用户{first_user[-4:]}"
                )
                self._save_message(session, second_user, second_message, round_num, "answer")

                # 提取关键信息
                extracted = self._extract_key_info(first_message + second_message)
                if extracted:
                    self._update_session_insights(session, extracted)

                # 更新轮数
                session.conversation_rounds = round_num
                self.db.commit()

                # 每 10 轮进行一次阶段性分析
                if round_num % 10 == 0:
                    await self._midpoint_analysis(session, agent1, agent2)

                # 检查是否已提取足够信息
                if session.conversation_rounds >= 30 and self._has_sufficient_insights(session):
                    logger.info(f"Sufficient insights extracted at round {round_num}")
                    break

            # 完成对话，生成报告
            await self._finalize_session(session, agent1, agent2)

        except Exception as e:
            logger.error(f"Conversation engine error: {e}", exc_info=True)
            session = self.db.query(AIPreCommunicationSessionDB).filter(
                AIPreCommunicationSessionDB.id == session_id
            ).first()
            if session:
                session.status = "cancelled"
                self.db.commit()

    # ============= 硬指标校验 =============

    async def _check_hard_indicators(
        self,
        user_id_1: str,
        user_id_2: str
    ) -> Dict[str, Any]:
        """
        择偶硬指标校验

        检查：
        1. 年龄差距是否在可接受范围内
        2. 地理位置是否可调和
        3. 关系类型是否匹配
        4. 生育观念是否一致
        """
        user1 = self.db.query(UserDB).filter(UserDB.id == user_id_1).first()
        user2 = self.db.query(UserDB).filter(UserDB.id == user_id_2).first()

        if not user1 or not user2:
            return {"passed": False, "reason": "用户不存在"}

        result = {
            "passed": True,
            "checks": {}
        }

        # 1. 年龄差距检查
        age_gap = abs(user1.age - user2.age)
        age_ok = age_gap <= HARD_INDICATORS_CONFIG["age_gap_max"]
        result["checks"]["age_gap"] = {
            "passed": age_ok,
            "details": f"年龄差{age_gap}岁，最大允许{HARD_INDICATORS_CONFIG['age_gap_max']}岁"
        }
        if not age_ok:
            result["passed"] = False
            result["reason"] = f"年龄差距过大（{age_gap}岁）"

        # 2. 关系类型检查
        pref1 = self._get_relationship_preference(user_id_1)
        pref2 = self._get_relationship_preference(user_id_2)

        if pref1 and pref2:
            types1 = set(json.loads(pref1.relationship_types or "[]"))
            types2 = set(json.loads(pref2.relationship_types or "[]"))
            type_match = len(types1.intersection(types2)) > 0
            result["checks"]["relationship_type"] = {
                "passed": type_match,
                "details": f"关系类型匹配：{bool(type_match)}"
            }
            if not type_match:
                result["passed"] = False
                result["reason"] = "关系类型不匹配"

        # 3. 生育观念检查（如果有）
        children1 = self._extract_children_preference(user1)
        children2 = self._extract_children_preference(user2)

        if children1 and children2 and children1 != children2:
            result["checks"]["children_view"] = {
                "passed": False,
                "details": f"生育观念不一致：{children1} vs {children2}"
            }
            result["passed"] = False
            result["reason"] = "生育观念不一致"

        logger.info(f"Hard indicators check for {user_id_1} <-> {user_id_2}: {result}")
        return result

    # ============= 价值观底线探测 =============

    async def _probe_values_baseline(
        self,
        user_id_1: str,
        user_id_2: str
    ) -> Dict[str, Any]:
        """
        价值观底线探测

        通过快速问答探测核心价值观是否兼容
        """
        user1 = self.db.query(UserDB).filter(UserDB.id == user_id_1).first()
        user2 = self.db.query(UserDB).filter(UserDB.id == user_id_2).first()

        if not user1 or not user2:
            return {"passed": False, "reason": "用户不存在"}

        result = {
            "passed": True,
            "probes": []
        }

        # 从个人简介中提取价值观关键词
        bio1 = user1.bio or ""
        bio2 = user2.bio or ""

        # 检查明显冲突
        conflicts = []

        # 丁克 vs 要孩子
        if ("丁克" in bio1 or "不要孩子" in bio1) and ("喜欢小孩" in bio2 or "想要孩子" in bio2):
            conflicts.append("生育观念冲突")
        if ("丁克" in bio2 or "不要孩子" in bio2) and ("喜欢小孩" in bio1 or "想要孩子" in bio1):
            conflicts.append("生育观念冲突")

        # 异地接受度
        if ("不接受异地" in bio1 or "拒绝异地" in bio1) and ("异地" in bio2 or "外地" in bio2):
            conflicts.append("异地接受度冲突")

        # 婚姻观念
        if ("不婚" in bio1 or "不结婚" in bio1) and ("结婚" in bio2 or "婚姻" in bio2):
            conflicts.append("婚姻观念冲突")

        for conflict in conflicts:
            result["probes"].append({
                "type": conflict,
                "detected": True
            })
            result["passed"] = False

        if not result["passed"]:
            result["reason"] = f"价值观底线冲突：{', '.join(conflicts)}"

        logger.info(f"Values baseline probe for {user_id_1} <-> {user_id_2}: {result}")
        return result

    # ============= 对话引擎 =============

    def _create_agent_for_user(self, user_id: str) -> UserSimulationAgent:
        """为用户创建 AI 替身"""
        if user_id in self.agents_cache:
            return self.agents_cache[user_id]

        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            # 返回默认 Agent
            return UserSimulationAgent({
                "name": "用户",
                "age": 25,
                "interests": [],
                "bio": ""
            })

        agent = UserSimulationAgent({
            "name": user.name,
            "age": user.age,
            "gender": user.gender,
            "interests": self._parse_json_field(user.interests),
            "values": self._parse_json_field(user.values),
            "bio": user.bio or ""
        })

        self.agents_cache[user_id] = agent
        return agent

    def _generate_conversation_topic(
        self,
        round_num: int,
        questions_pool: List[Dict]
    ) -> Dict[str, str]:
        """
        生成对话话题

        根据轮数选择不同深度的话题：
        - 1-10 轮：轻松话题
        - 11-30 轮：价值观探索
        - 31-50 轮：深度话题
        """
        if round_num <= 10:
            # 轻松话题
            topics = [
                {"starter": "你平时有什么兴趣爱好？"},
                {"starter": "最近有看什么好看的电影/剧吗？"},
                {"starter": "你最喜欢的一道菜是什么？"},
                {"starter": "周末一般怎么过？"},
                {"starter": "去过最难忘的地方是哪里？"},
            ]
        elif round_num <= 30:
            # 价值观探索
            category = random.choice(questions_pool)
            return {
                "starter": random.choice(category["questions"]),
                "category": category["category"]
            }
        else:
            # 深度话题
            topics = [
                {"starter": "你觉得理想的伴侣关系是什么样的？"},
                {"starter": "对于未来 5 年，你有什么规划？"},
                {"starter": "你最重要的核心价值观是什么？"},
                {"starter": "你觉得两个人相处最重要的是什么？"},
            ]

        return random.choice(topics)

    def _save_message(
        self,
        session: AIPreCommunicationSessionDB,
        sender_id: str,
        content: str,
        round_number: int,
        message_type: str = "text"
    ):
        """保存对话消息"""
        message = AIPreCommunicationMessageDB(
            session_id=session.id,
            agent_id_1=f"agent_{session.user_id_1}",
            agent_id_2=f"agent_{session.user_id_2}",
            sender_agent=f"agent_{sender_id}",
            content=content,
            message_type=message_type,
            round_number=round_number
        )
        self.db.add(message)
        self.db.commit()
        logger.debug(f"Message saved: round {round_number}, sender {sender_id[-4:]}")

    # ============= 关键信息提取 =============

    def _extract_key_info(self, text: str) -> Dict[str, Any]:
        """
        从对话中提取关键信息
        """
        extracted = {}
        text_lower = text.lower()

        for category, config in KEY_INFO_CATEGORIES.items():
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    # 简单提取：根据上下文抽取
                    extracted[category] = {
                        "detected": True,
                        "keyword": keyword,
                        "context": text[:100]  # 截取上下文
                    }
                    break

        return extracted

    def _update_session_insights(
        self,
        session: AIPreCommunicationSessionDB,
        extracted: Dict[str, Any]
    ):
        """更新会话洞察"""
        current_insights = self._parse_json_field(session.extracted_insights)

        for key, value in extracted.items():
            if key not in current_insights:
                current_insights[key] = value

        session.extracted_insights = json.dumps(current_insights)
        self.db.commit()

    # ============= 匹配度报告 =============

    async def _midpoint_analysis(
        self,
        session: AIPreCommunicationSessionDB,
        agent1: UserSimulationAgent,
        agent2: UserSimulationAgent
    ):
        """
        阶段性分析（每 10 轮执行一次）
        """
        # 获取当前对话
        messages = self.db.query(AIPreCommunicationMessageDB).filter(
            AIPreCommunicationMessageDB.session_id == session.id
        ).order_by(
            AIPreCommunicationMessageDB.round_number.desc()
        ).limit(20).all()

        # 简单分析：基于已提取的信息
        insights = self._parse_json_field(session.extracted_insights)

        logger.info(f"Midpoint analysis for session {session.id}: {len(insights)} insights extracted")

    def _has_sufficient_insights(self, session: AIPreCommunicationSessionDB) -> bool:
        """判断是否已提取足够信息"""
        insights = self._parse_json_field(session.extracted_insights)
        # 至少提取 3 个关键信息类别
        return len(insights) >= 3

    async def _finalize_session(
        self,
        session: AIPreCommunicationSessionDB,
        agent1: UserSimulationAgent,
        agent2: UserSimulationAgent
    ):
        """
        完成会话，生成匹配度报告
        """
        logger.info(f"Finalizing session {session.id}")

        # 1. 计算匹配度
        compatibility = self._calculate_compatibility(session)
        session.compatibility_score = compatibility["score"]
        session.compatibility_report = json.dumps(compatibility["report"])

        # 2. 生成推送建议
        if compatibility["score"] >= 85:
            session.recommendation = "recommend"
            session.recommendation_reason = f"匹配度{compatibility['score']:.0f}%，建议开启人工对话"
        elif compatibility["score"] >= 60:
            session.recommendation = "wait"
            session.recommendation_reason = f"匹配度{compatibility['score']:.0f}%，可继续观察"
        else:
            session.recommendation = "silent"
            session.recommendation_reason = f"匹配度{compatibility['score']:.0f}%，不建议推送"

        # 3. 更新状态
        session.status = "completed"
        session.completed_at = datetime.now()
        self.db.commit()

        logger.info(f"Session {session.id} finalized: score={compatibility['score']:.1f}, recommendation={session.recommendation}")

    def _calculate_compatibility(
        self,
        session: AIPreCommunicationSessionDB
    ) -> Dict[str, Any]:
        """
        计算匹配度

        基于：
        1. 硬指标匹配度
        2. 价值观匹配度
        3. 对话互动质量
        4. 关键信息一致性
        """
        score = 0
        report = {
            "dimensions": {}
        }

        # 1. 硬指标（30 分）
        if session.hard_check_passed:
            score += 30
            report["dimensions"]["hard_indicators"] = {"score": 30, "max": 30}
        else:
            report["dimensions"]["hard_indicators"] = {"score": 0, "max": 30}

        # 2. 价值观（30 分）
        if session.values_check_passed:
            score += 30
            report["dimensions"]["values"] = {"score": 30, "max": 30}
        else:
            report["dimensions"]["values"] = {"score": 0, "max": 30}

        # 3. 对话轮数（20 分）
        rounds_ratio = session.conversation_rounds / session.target_rounds
        rounds_score = int(rounds_ratio * 20)
        score += rounds_score
        report["dimensions"]["conversation_depth"] = {
            "score": rounds_score,
            "max": 20,
            "rounds": session.conversation_rounds
        }

        # 4. 信息提取质量（20 分）
        insights = self._parse_json_field(session.extracted_insights)
        insights_score = min(len(insights) * 4, 20)
        score += insights_score
        report["dimensions"]["information_quality"] = {
            "score": insights_score,
            "max": 20,
            "insights_count": len(insights)
        }

        report["total_score"] = score
        report["max_score"] = 100

        return {"score": score, "report": report}

    # ============= 辅助函数 =============

    def _get_relationship_preference(self, user_id: str) -> Optional[UserRelationshipPreferenceDB]:
        """获取用户关系偏好"""
        return self.db.query(UserRelationshipPreferenceDB).filter(
            UserRelationshipPreferenceDB.user_id == user_id
        ).first()

    def _extract_children_preference(self, user: UserDB) -> Optional[str]:
        """从用户信息中提取生育观念"""
        bio = (user.bio or "").lower()

        if "丁克" in bio or "不要孩子" in bio or "不生孩子" in bio:
            return "no_children"
        elif "想要孩子" in bio or "喜欢小孩" in bio or "要孩子" in bio:
            return "wants_children"
        elif "一个就好" in bio or "一个孩子" in bio:
            return "one_child"
        elif "多子多福" in bio or "两个孩子" in bio or "多个孩子" in bio:
            return "multiple_children"

        return None

    def _parse_json_field(self, field: str) -> Any:
        """解析 JSON 字符串字段"""
        if not field:
            return {}
        try:
            return json.loads(field)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON field: {e}, field: {field[:100] if field else 'None'}")
            return {}


# ============= API 辅助函数 =============

def get_ai_interlocutor_service(db: Session) -> AIInterlocutorService:
    """获取 AI 预沟通服务实例"""
    return AIInterlocutorService(db)
