"""
注册对话服务

实现 AI 红娘与注册用户的深度沟通，通过对话收集用户信息并完善画像。
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from utils.logger import logger
import json


class RegistrationConversationService:
    """
    注册对话服务

    通过多轮对话收集用户关键信息：
    1. 关系期望（认真恋爱/婚姻/交友）
    2. 理想型描述
    3. 核心价值观
    4. 兴趣爱好
    5. 生活方式偏好
    """

    # 对话阶段定义
    STAGES = {
        "welcome": {
            "order": 0,
            "name": "欢迎破冰",
            "question": None,
            "extract_field": None,
        },
        "relationship_goal": {
            "order": 1,
            "name": "关系期望",
            "question": "很高兴认识你，{name}～ 🌸 我想先了解一下，你希望通过这个平台找到什么样的关系呢？是认真恋爱、走向婚姻，还是先交个朋友？",
            "extract_field": "goal",
        },
        "ideal_partner": {
            "order": 2,
            "name": "理想型",
            "question": "明白了～ 那你能描述一下你理想中的另一半是什么样的吗？比如性格、年龄、或者一些特质？",
            "extract_field": "ideal_partner_desc",
        },
        "values": {
            "order": 3,
            "name": "核心价值观",
            "question": "很好～ 我很好奇，在感情中最看重对方什么呢？比如真诚、责任心、共同爱好，还是其他？",
            "extract_field": "values_priority",
        },
        "lifestyle": {
            "order": 4,
            "name": "生活方式",
            "question": "嗯嗯～ 那你的业余时间一般喜欢做什么呢？有什么兴趣爱好或者经常做的事？",
            "extract_field": "interests",
        },
        "final": {
            "order": 5,
            "name": "结束语",
            "question": None,
            "extract_field": None,
        },
    }

    # 欢迎语
    WELCOME_MESSAGES = [
        "你好呀，{name}～ 很高兴认识你！",
        "欢迎！让我慢慢了解你吧～",
        "嗨，{name}！让我先了解一下你吧 ✨",
    ]

    # 关键词映射
    GOAL_KEYWORDS = {
        "serious": ["认真", "恋爱", "稳定", "长期", "专一", "真诚"],
        "marriage": ["结婚", "婚姻", "成家", "家庭", "生子"],
        "casual": ["交友", "朋友", " casual", "随意", "看看"],
    }

    VALUES_KEYWORDS = {
        "family": ["家庭", "家人", "孝顺", "亲情"],
        "career": ["事业", "工作", "上进", "努力"],
        "lifestyle": ["生活", "品味", "情趣", "浪漫"],
        "social": ["社交", "朋友", "外向", "开朗"],
    }

    def __init__(self):
        pass

    def create_conversation_session(self, user_id: str, user_name: str) -> Dict:
        """
        创建对话会话

        Args:
            user_id: 用户 ID
            user_name: 用户名称

        Returns:
            会话信息
        """
        welcome_msg = self.WELCOME_MESSAGES[0].format(name=user_name)

        session = {
            "user_id": user_id,
            "user_name": user_name,
            "current_stage": "welcome",
            "stage_order": 0,
            "conversation_history": [],
            "collected_data": {},
            "created_at": datetime.now().isoformat(),
            "ai_message": welcome_msg,
            "is_completed": False,
        }

        logger.info(f"Created conversation session for user {user_id}")
        return session

    def process_user_response(
        self,
        session: Dict,
        user_response: str
    ) -> Dict:
        """
        处理用户回答

        Args:
            session: 当前会话
            user_response: 用户回答

        Returns:
            更新后的会话和 AI 回复
        """
        current_stage = session["current_stage"]
        stage_order = session["stage_order"]

        # 记录对话历史
        session["conversation_history"].append({
            "stage": current_stage,
            "question": self.STAGES[current_stage].get("question"),
            "user_response": user_response,
            "timestamp": datetime.now().isoformat(),
        })

        # 提取信息
        extracted = self._extract_information(current_stage, user_response)
        if extracted:
            session["collected_data"].update(extracted)
            logger.info(f"Extracted data from stage {current_stage}: {extracted}")

        # 进入下一阶段
        next_stage = self._get_next_stage(current_stage)

        if next_stage:
            session["current_stage"] = next_stage
            session["stage_order"] = self.STAGES[next_stage]["order"]

            # 如果进入 final 阶段，标记对话完成
            if next_stage == "final":
                session["is_completed"] = True
                session["ai_message"] = self._generate_final_message(session["collected_data"])
            else:
                # 生成 AI 回复和下一个问题
                ai_response = self._generate_ai_response(session, next_stage, user_response, session["collected_data"])
                session["ai_message"] = ai_response
        else:
            # 对话完成
            session["is_completed"] = True
            session["ai_message"] = self._generate_final_message(session["collected_data"])

        return session

    def _extract_information(self, stage: str, response: str) -> Optional[Dict]:
        """
        从用户回答中提取信息

        Args:
            stage: 当前阶段
            response: 用户回答

        Returns:
            提取的数据
        """
        response_lower = response.lower()

        if stage == "relationship_goal":
            # 提取关系期望
            for goal, keywords in self.GOAL_KEYWORDS.items():
                if any(kw in response_lower for kw in keywords):
                    goal_map = {
                        "serious": "serious",
                        "marriage": "marriage",
                        "casual": "casual",
                    }
                    return {"goal": goal_map.get(goal, "serious")}
            return {"goal": "serious"}  # 默认

        elif stage == "values":
            # 提取价值观优先级
            values_scores = {}
            for value, keywords in self.VALUES_KEYWORDS.items():
                count = sum(1 for kw in keywords if kw in response_lower)
                if count > 0:
                    values_scores[value] = min(0.5 + count * 0.15, 0.95)

            if values_scores:
                return {"values": values_scores}
            return None

        elif stage == "lifestyle":
            # 提取兴趣爱好（简单关键词提取）
            # 这里可以做更复杂的 NLP 处理，暂时返回空，让用户手动完善
            return None

        elif stage == "ideal_partner":
            # 保存理想型描述
            return {"ideal_partner_desc": response}

        return None

    def _get_next_stage(self, current_stage: str) -> Optional[str]:
        """
        获取下一阶段

        Args:
            current_stage: 当前阶段

        Returns:
            下一阶段名称
        """
        current_order = self.STAGES[current_stage]["order"]

        for stage_name, stage_info in self.STAGES.items():
            if stage_info["order"] == current_order + 1:
                return stage_name

        return None

    def _generate_ai_response(
        self,
        session: Dict,
        stage: str,
        user_response: str,
        collected_data: Dict
    ) -> str:
        """
        生成 AI 回复和下一个问题

        Args:
            session: 当前会话（包含 user_name）
            stage: 下一阶段
            user_response: 用户刚才的回答
            collected_data: 已收集的数据

        Returns:
            AI 回复消息
        """
        # 共情回复
        empathy_responses = {
            "relationship_goal": {
                "serious": "我懂你～ 认真的感情最让人安心 💕",
                "marriage": "真好～ 以结婚为目标的感情最珍贵了 ✨",
                "casual": "没问题～ 先从朋友做起也挺好的 😊",
            },
            "ideal_partner": "听起来很棒～ 能感受到你对感情的期待 💭",
            "values": "嗯嗯～ 这些品质确实很重要 👍",
            "lifestyle": "你的生活很有趣呢～ 🌈",
        }

        # 根据阶段获取共情回复
        empathy_data = empathy_responses.get(stage, "谢谢你的分享～")

        # 如果是 relationship_goal 阶段，根据收集的 goal 选择回复
        if stage == "relationship_goal" and isinstance(empathy_data, dict):
            goal = collected_data.get("goal", "serious")
            empathy = empathy_data.get(goal, empathy_data.get("serious", "谢谢你的分享～"))
        else:
            empathy = empathy_data

        # 获取下一个问题，并格式化 name
        next_question = self.STAGES[stage].get("question", "")
        if next_question and "{name}" in next_question:
            user_name = session.get("user_name", "你")
            next_question = next_question.format(name=user_name)

        return f"{empathy}\n\n{next_question}"

    def _generate_final_message(self, collected_data: Dict) -> str:
        """
        生成结束语

        Args:
            collected_data: 收集的数据

        Returns:
            结束语
        """
        goal_text = {
            "serious": "认真恋爱",
            "marriage": "走向婚姻",
            "casual": "结交朋友",
        }.get(collected_data.get("goal", "serious"), "认真恋爱")

        return f"""太好了～ 我已经对你有了初步的了解 💕

你希望找到{goal_text}的对象，我会根据你的 preferences 为你筛选合适的人选。

现在你可以：
• 完善个人资料，增加曝光机会
• 开始查看为你推荐的人选
• 继续完善兴趣爱好等信息

祝你在这里找到属于自己的缘分～ 🌸"""

    def apply_collected_data(self, session: Dict, user_data: Dict) -> Dict:
        """
        将收集的数据应用到用户资料

        Args:
            session: 对话会话
            user_data: 当前用户数据

        Returns:
            更新后的用户数据
        """
        collected = session.get("collected_data", {})

        # 更新目标
        if "goal" in collected:
            user_data["goal"] = collected["goal"]

        # 更新价值观
        if "values" in collected:
            existing_values = user_data.get("values", {})
            existing_values.update(collected["values"])
            user_data["values"] = existing_values

        # 更新理想型描述
        if "ideal_partner_desc" in collected:
            user_data["ideal_partner_desc"] = collected["ideal_partner_desc"]

        return user_data

    def get_session_summary(self, session: Dict) -> Dict:
        """
        获取会话摘要

        Args:
            session: 对话会话

        Returns:
            会话摘要
        """
        return {
            "user_id": session["user_id"],
            "user_name": session["user_name"],
            "is_completed": session["is_completed"],
            "current_stage": session["current_stage"],
            "conversation_count": len(session["conversation_history"]),
            "collected_data": session["collected_data"],
            "completed_at": session.get("completed_at"),
        }


# 全局服务实例
registration_conversation_service = RegistrationConversationService()
