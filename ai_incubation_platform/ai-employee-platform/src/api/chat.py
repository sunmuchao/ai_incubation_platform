"""
AI 对话式 API

提供基于自然语言的交互接口，替代传统的表单搜索模式

核心端点:
- /api/chat - 主对话接口
- /api/chat/career - 职业发展对话
- /api/chat/match - 人才匹配对话
"""
import logging
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["AI Chat - 对话式交互"])


# ==================== 请求/响应模型 ====================

class ChatMessage(BaseModel):
    """对话消息"""
    role: str = Field(..., description="角色：user/assistant/system")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[str] = Field(None, description="时间戳")


class ChatRequest(BaseModel):
    """对话请求"""
    user_id: str = Field(..., description="用户 ID")
    message: str = Field(..., description="用户输入消息")
    conversation_id: Optional[str] = Field(None, description="会话 ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")


class ChatResponse(BaseModel):
    """对话响应"""
    conversation_id: str
    message: ChatMessage
    suggested_actions: Optional[List[Dict[str, Any]]] = None
    data: Optional[Dict[str, Any]] = None


# ==================== AI Agent 导入 ====================

def get_talent_agent():
    """延迟导入 TalentAgent，避免循环依赖"""
    try:
        from agents.talent_agent import get_talent_agent as _get_agent
    except ImportError:
        from ..agents.talent_agent import get_talent_agent as _get_agent
    return _get_agent()


# ==================== 意图识别 ====================

INTENT_PATTERNS = {
    "career_plan": ["职业发展", "职业规划", "怎么发展", "如何提升", "晋升", "转岗"],
    "skill_analysis": ["技能分析", "能力评估", "我会什么", "我的技能", "差距分析"],
    "performance_review": ["绩效评估", "表现如何", "工作总结", "考核", "绩效"],
    "learning_resources": ["学习资源", "课程推荐", "书籍推荐", "怎么学", "培训", "学习", "推荐学习"],
    "mentor_match": ["导师匹配", "找导师", "mentor", "指导"],
    "dashboard": ["仪表盘", "概览", "我的情况", "整体情况"],
    "opportunity_match": ["机会匹配", "有什么机会", "适合我", "找工作", "推荐"],
}


def detect_intent(message: str) -> str:
    """
    检测用户意图

    Args:
        message: 用户输入消息

    Returns:
        str: 识别的意图类型
    """
    message_lower = message.lower()

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in message_lower:
                return intent

    return "general"  # 默认通用意图


# ==================== 对话处理器 ====================

class ChatProcessor:
    """对话处理器"""

    def __init__(self):
        self.talent_agent = None
        self._initialized = False

    async def initialize(self):
        """初始化 Agent"""
        if not self._initialized:
            self.talent_agent = get_talent_agent()
            await self.talent_agent.initialize()
            self._initialized = True
            logger.info("ChatProcessor 初始化完成")

    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息

        Args:
            user_id: 用户 ID
            message: 用户输入
            conversation_id: 会话 ID
            context: 上下文

        Returns:
            Dict: 对话响应
        """
        await self.initialize()

        # 检测意图
        intent = detect_intent(message)
        logger.info(f"用户 {user_id} 意图：{intent}")

        # 根据意图路由到不同处理器
        if intent == "career_plan":
            return await self._handle_career_plan(user_id, message, context)
        elif intent == "skill_analysis":
            return await self._handle_skill_analysis(user_id, message, context)
        elif intent == "opportunity_match":
            return await self._handle_opportunity_match(user_id, message, context)
        elif intent == "performance_review":
            return await self._handle_performance_review(user_id, message, context)
        elif intent == "learning_resources":
            return await self._handle_learning_resources(user_id, message, context)
        elif intent == "mentor_match":
            return await self._handle_mentor_match(user_id, message, context)
        elif intent == "dashboard":
            return await self._handle_dashboard(user_id, message, context)
        else:
            return await self._handle_general(user_id, message, context)

    async def _handle_career_plan(self, user_id: str, message: str, context: Dict) -> Dict[str, Any]:
        """处理职业规划相关对话"""
        try:
            # 使用 TalentAgent 生成职业规划
            result = await self.talent_agent.plan_career(
                employee_id=user_id,
                target_role=context.get("target_role"),
                timeframe_months=context.get("timeframe_months", 12)
            )

            if result.get("success"):
                plan = result.get("plan", {})
                response_text = self._format_career_plan(plan)
                data = plan
            else:
                response_text = f"抱歉，生成职业规划时遇到问题：{result.get('error', '未知错误')}"
                data = None

            return {
                "response_text": response_text,
                "data": data,
                "suggested_actions": [
                    {"action": "view_full_plan", "label": "查看完整计划"},
                    {"action": "set_goal", "label": "设定具体目标"},
                    {"action": "find_resources", "label": "查找学习资源"}
                ]
            }

        except Exception as e:
            logger.error(f"职业规划对话失败：{e}")
            return {
                "response_text": "抱歉，处理您的请求时遇到错误，请稍后重试。",
                "data": None,
                "suggested_actions": []
            }

    async def _handle_skill_analysis(self, user_id: str, message: str, context: Dict) -> Dict[str, Any]:
        """处理技能分析相关对话"""
        try:
            result = await self.talent_agent.analyze_employee_profile(
                employee_id=user_id,
                include_projects=True
            )

            if result.get("success"):
                profile = result.get("profile_summary", {})
                skills = result.get("skills", [])

                response_text = self._format_skill_analysis(profile, skills)
                data = result

                suggested_actions = [
                    {"action": "view_skills", "label": "查看详细技能"},
                    {"action": "analyze_gap", "label": "分析技能差距"},
                    {"action": "improve_skills", "label": "提升技能"}
                ]
            else:
                response_text = f"抱歉，分析技能时遇到问题：{result.get('error', '未知错误')}"
                data = None
                suggested_actions = []

            return {
                "response_text": response_text,
                "data": data,
                "suggested_actions": suggested_actions
            }

        except Exception as e:
            logger.error(f"技能分析对话失败：{e}")
            return {
                "response_text": "抱歉，处理您的请求时遇到错误，请稍后重试。",
                "data": None,
                "suggested_actions": []
            }

    async def _handle_opportunity_match(self, user_id: str, message: str, context: Dict) -> Dict[str, Any]:
        """处理机会匹配相关对话"""
        try:
            result = await self.talent_agent.match_opportunities(
                employee_id=user_id,
                opportunity_type="all",
                limit=5
            )

            if result.get("success"):
                opportunities = result.get("opportunities", [])
                response_text = self._format_opportunities(opportunities)
                data = result

                suggested_actions = [
                    {"action": "apply", "label": "申请职位", "available": len(opportunities) > 0},
                    {"action": "learn_more", "label": "了解更多"},
                    {"action": "save_for_later", "label": "稍后考虑"}
                ]
            else:
                response_text = f"抱歉，匹配机会时遇到问题：{result.get('error', '未知错误')}"
                data = None
                suggested_actions = []

            return {
                "response_text": response_text,
                "data": data,
                "suggested_actions": suggested_actions
            }

        except Exception as e:
            logger.error(f"机会匹配对话失败：{e}")
            return {
                "response_text": "抱歉，处理您的请求时遇到错误，请稍后重试。",
                "data": None,
                "suggested_actions": []
            }

    async def _handle_performance_review(self, user_id: str, message: str, context: Dict) -> Dict[str, Any]:
        """处理绩效评估相关对话"""
        try:
            result = await self.talent_agent.track_performance(
                employee_id=user_id,
                period=context.get("period", "quarterly")
            )

            if result.get("success"):
                performance = result.get("performance", {})
                response_text = self._format_performance_review(performance)
                data = result

                suggested_actions = [
                    {"action": "view_details", "label": "查看详情"},
                    {"action": "set_goals", "label": "设定改进目标"},
                    {"action": "share_with_manager", "label": "分享给主管"}
                ]
            else:
                response_text = f"抱歉，获取绩效评估时遇到问题：{result.get('error', '未知错误')}"
                data = None
                suggested_actions = []

            return {
                "response_text": response_text,
                "data": data,
                "suggested_actions": suggested_actions
            }

        except Exception as e:
            logger.error(f"绩效评估对话失败：{e}")
            return {
                "response_text": "抱歉，处理您的请求时遇到错误，请稍后重试。",
                "data": None,
                "suggested_actions": []
            }

    async def _handle_learning_resources(self, user_id: str, message: str, context: Dict) -> Dict[str, Any]:
        """处理学习资源相关对话"""
        try:
            from ..tools.career_tools import recommend_learning_resources_handler

            result = await recommend_learning_resources_handler(
                employee_id=user_id,
                skill_area=context.get("skill_area"),
                limit=5
            )

            if result.get("success"):
                resources = result.get("resources", [])
                response_text = self._format_learning_resources(resources)
                data = result

                suggested_actions = [
                    {"action": "start_course", "label": "开始学习"},
                    {"action": "save_resources", "label": "收藏资源"},
                    {"action": "ask_for_help", "label": "寻求指导"}
                ]
            else:
                response_text = f"抱歉，推荐学习资源时遇到问题：{result.get('error', '未知错误')}"
                data = None
                suggested_actions = []

            return {
                "response_text": response_text,
                "data": data,
                "suggested_actions": suggested_actions
            }

        except Exception as e:
            logger.error(f"学习资源对话失败：{e}")
            return {
                "response_text": "抱歉，处理您的请求时遇到错误，请稍后重试。",
                "data": None,
                "suggested_actions": []
            }

    async def _handle_mentor_match(self, user_id: str, message: str, context: Dict) -> Dict[str, Any]:
        """处理导师匹配相关对话"""
        try:
            from ..tools.career_tools import match_mentor_handler

            result = await match_mentor_handler(
                employee_id=user_id,
                development_goals=context.get("development_goals")
            )

            if result.get("success"):
                mentors = result.get("mentor_matches", [])
                response_text = self._format_mentor_matches(mentors)
                data = result

                suggested_actions = [
                    {"action": "contact_mentor", "label": "联系导师", "available": len(mentors) > 0},
                    {"action": "view_profiles", "label": "查看详细资料"},
                    {"action": "request_match", "label": "申请匹配"}
                ]
            else:
                response_text = f"抱歉，匹配导师时遇到问题：{result.get('error', '未知错误')}"
                data = None
                suggested_actions = []

            return {
                "response_text": response_text,
                "data": data,
                "suggested_actions": suggested_actions
            }

        except Exception as e:
            logger.error(f"导师匹配对话失败：{e}")
            return {
                "response_text": "抱歉，处理您的请求时遇到错误，请稍后重试。",
                "data": None,
                "suggested_actions": []
            }

    async def _handle_dashboard(self, user_id: str, message: str, context: Dict) -> Dict[str, Any]:
        """处理仪表盘相关对话"""
        try:
            # 获取综合信息
            profile_result = await self.talent_agent.analyze_employee_profile(
                employee_id=user_id,
                include_projects=True
            )

            response_text = "以下是您的职业发展概览：\n\n"

            if profile_result.get("success"):
                skills_count = len(profile_result.get("skills", []))
                performance = profile_result.get("performance_history", [])
                plans = profile_result.get("development_plans", [])

                response_text += f"📊 技能数量：{skills_count} 项\n"
                if performance:
                    latest_perf = performance[0]
                    response_text += f"📈 最新绩效：{latest_perf.get('rating', 'N/A')}\n"
                if plans:
                    response_text += f"🎯 进行中的发展计划：{len(plans)} 个\n"

                response_text += "\n您可以问我：\n- 我的技能详情\n- 职业发展建议\n- 机会匹配推荐"

                data = profile_result
            else:
                response_text = "抱歉，获取概览信息时遇到问题。"
                data = None

            return {
                "response_text": response_text,
                "data": data,
                "suggested_actions": [
                    {"action": "view_skills", "label": "查看技能"},
                    {"action": "career_advice", "label": "职业建议"},
                    {"action": "opportunities", "label": "发现机会"}
                ]
            }

        except Exception as e:
            logger.error(f"仪表盘对话失败：{e}")
            return {
                "response_text": "抱歉，处理您的请求时遇到错误，请稍后重试。",
                "data": None,
                "suggested_actions": []
            }

    async def _handle_general(self, user_id: str, message: str, context: Dict) -> Dict[str, Any]:
        """处理通用对话"""
        response_text = """
您好！我是您的 AI 职业发展助手，我可以帮助您：

📋 **职业规划**
- "我想做职业规划"
- "如何晋升到高级工程师"

🔍 **技能分析**
- "分析我的技能"
- "我与目标职位的差距"

💼 **机会匹配**
- "有什么适合我的机会"
- "推荐晋升/转岗机会"

📊 **绩效评估**
- "我的绩效如何"
- "生成绩效评估报告"

📚 **学习资源**
- "推荐学习资源"
- "如何提升 Python 技能"

🎓 **导师匹配**
- "帮我找导师"
- "导师推荐"

请告诉我您想了解什么？
"""
        return {
            "response_text": response_text,
            "data": None,
            "suggested_actions": [
                {"action": "career_plan", "label": "职业规划"},
                {"action": "skill_analysis", "label": "技能分析"},
                {"action": "opportunities", "label": "发现机会"}
            ]
        }

    # ==================== 格式化辅助方法 ====================

    def _format_career_plan(self, plan: Dict) -> str:
        """格式化职业规划响应"""
        if not plan:
            return "暂无职业规划数据"

        target = plan.get("target_state", {})
        phases = plan.get("development_phases", [])

        text = "📋 **您的职业发展规划**\n\n"

        if target:
            text += f"🎯 **目标职位**: {target.get('role_name', '未指定')}\n"
            text += f"📊 **匹配度**: {target.get('match_score', 0):.0%}\n"
            text += f"⏱️ **准备时间**: {plan.get('timeline', {}).get('duration_months', 12)} 个月\n\n"

        if phases:
            text += "**发展阶段**:\n"
            for phase in phases[:3]:
                text += f"\n**{phase.get('name', '阶段')}** ({phase.get('duration_months', 0)}个月)\n"
                for milestone in phase.get('milestones', []):
                    text += f"  - {milestone}\n"

        actions = plan.get("recommended_actions", [])
        if actions:
            text += "\n**推荐行动**:\n"
            for action in actions[:3]:
                text += f"  - {action.get('action', '')}\n"

        return text

    def _format_skill_analysis(self, profile: Dict, skills: List) -> str:
        """格式化技能分析响应"""
        text = "📊 **技能分析**\n\n"

        # 优势
        strengths = profile.get("strengths", [])
        if strengths:
            text += "✅ **优势**:\n"
            for s in strengths[:3]:
                text += f"  - {s}\n"

        # 技能列表
        if skills:
            text += f"\n💡 **技能数量**: {len(skills)} 项\n"
            text += "\n**主要技能**:\n"
            for skill in skills[:5]:
                name = skill.get("name", "未知")
                level = skill.get("level", "unknown")
                text += f"  - {name}: {level}\n"

        # 改进建议
        areas = profile.get("areas_for_improvement", [])
        if areas:
            text += "\n📈 **提升方向**:\n"
            for a in areas[:3]:
                text += f"  - {a}\n"

        return text

    def _format_opportunities(self, opportunities: List) -> str:
        """格式化机会匹配响应"""
        if not opportunities:
            return "暂无匹配的机会，请继续提升技能！"

        text = f"💼 **为您找到 {len(opportunities)} 个机会**\n\n"

        for i, opp in enumerate(opportunities[:5], 1):
            opp_type = opp.get("type", "unknown")
            type_icon = {"promotion": "📈", "transfer": "🔄", "project": "📁"}.get(opp_type, "💼")
            name = opp.get("role_name", opp.get("project_name", "未知"))
            score = opp.get("match_score", 0)

            text += f"{i}. {type_icon} **{name}**\n"
            text += f"   匹配度：{score:.0%}\n"
            text += f"   类型：{opp_type}\n\n"

        return text

    def _format_performance_review(self, performance: Dict) -> str:
        """格式化绩效评估响应"""
        if not performance:
            return "暂无绩效评估数据"

        text = "📊 **绩效评估**\n\n"
        text += f"🏆 **总体评级**: {performance.get('rating', 'N/A')}\n"
        text += f"📈 **综合得分**: {performance.get('overall_score', 0)}/5.0\n\n"

        dimensions = performance.get("dimensions", {})
        if dimensions:
            text += "**各维度表现**:\n"
            for dim, data in dimensions.items():
                score = data.get("score", 0)
                trend = data.get("trend", "stable")
                trend_icon = {"up": "📈", "down": "📉", "stable": "➡️"}.get(trend, "")
                text += f"  - {dim}: {score}/5 {trend_icon}\n"

        achievements = performance.get("achievements", [])
        if achievements:
            text += "\n✨ **主要成就**:\n"
            for a in achievements[:3]:
                text += f"  - {a}\n"

        return text

    def _format_learning_resources(self, resources: List) -> str:
        """格式化学习资源响应"""
        if not resources:
            return "暂无推荐的学习资源"

        text = f"📚 **推荐学习资源** ({len(resources)} 个)\n\n"

        for i, res in enumerate(resources[:5], 1):
            res_type = res.get("type", "unknown")
            type_icon = {"course": "🎓", "book": "📖", "workshop": "🏫", "project": "💼"}.get(res_type, "📚")
            title = res.get("title", "未知")
            rating = res.get("rating", 0)

            text += f"{i}. {type_icon} **{title}**\n"
            text += f"   类型：{res_type}\n"
            text += f"   评分：{'⭐' * int(rating)}\n\n"

        return text

    def _format_mentor_matches(self, mentors: List) -> str:
        """格式化导师匹配响应"""
        if not mentors:
            return "暂无匹配的导师"

        text = f"🎓 **为您匹配 {len(mentors)} 位导师**\n\n"

        for i, mentor in enumerate(mentors[:3], 1):
            name = mentor.get("mentor_name", "未知")
            score = mentor.get("match_score", 0)
            expertise = mentor.get("areas_of_expertise", [])
            availability = mentor.get("availability", "unknown")

            text += f"{i}. 👤 **{name}**\n"
            text += f"   匹配度：{score:.0%}\n"
            text += f"   专业领域：{', '.join(expertise[:3]) if expertise else 'N/A'}\n"
            text += f"   状态：{'✅ 可接受' if availability == 'available' else '⏳ 忙碌'}\n\n"

        return text


# 全局处理器实例
_chat_processor = ChatProcessor()


# ==================== API 端点 ====================

@router.post("/", response_model=Dict[str, Any])
async def chat(request: ChatRequest):
    """
    AI 对话接口

    使用自然语言与 AI 助手交互，获取职业发展建议、机会匹配、技能分析等服务

    示例:
    - "我想做职业规划"
    - "分析我的技能"
    - "有什么适合我的机会"
    - "推荐学习资源"
    """
    try:
        result = await _chat_processor.process_message(
            user_id=request.user_id,
            message=request.message,
            conversation_id=request.conversation_id,
            context=request.context
        )

        # 生成会话 ID
        conversation_id = request.conversation_id or f"conv-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": {
                "role": "assistant",
                "content": result["response_text"],
                "timestamp": datetime.now().isoformat()
            },
            "suggested_actions": result.get("suggested_actions", []),
            "data": result.get("data")
        }

    except Exception as e:
        logger.error(f"对话失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intents")
async def list_intents():
    """列出支持的意图类型"""
    return {
        "success": True,
        "intents": {
            intent: patterns
            for intent, patterns in INTENT_PATTERNS.items()
        }
    }


@router.get("/help")
async def chat_help():
    """获取对话帮助信息"""
    return {
        "success": True,
        "help": {
            "description": "AI 职业发展助手 - 对话式交互",
            "examples": [
                "我想做职业规划",
                "分析我的技能",
                "有什么适合我的机会",
                "我的绩效如何",
                "推荐学习资源",
                "帮我找导师"
            ],
            "features": [
                "职业规划建议",
                "技能差距分析",
                "机会匹配推荐",
                "绩效评估",
                "学习资源推荐",
                "导师匹配"
            ]
        }
    }
