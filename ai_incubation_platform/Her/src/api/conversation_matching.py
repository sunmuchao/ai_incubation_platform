"""
对话式匹配 API

提供 AI Native 的对话式交互接口，替代传统的表单筛选模式。
用户通过自然语言表达需求，AI 理解并执行匹配操作。
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from db.database import get_db
from db.repositories import UserRepository
from db.audit import log_audit, get_audit_logger
from utils.logger import logger
from auth.jwt import get_current_user, get_current_user_optional
from agent.workflows.autonomous_workflows import (
    AutoMatchRecommendWorkflow,
    RelationshipHealthCheckWorkflow,
    AutoIcebreakerWorkflow,
    run_workflow
)
from agent.tools.autonomous_tools import (
    CompatibilityAnalysisTool,
    TopicSuggestionTool,
    RelationshipTrackingTool
)

router = APIRouter(prefix="/api/conversation-matching", tags=["conversation-matching"])


# ============= 请求/响应模型 =============

class ConversationMatchRequest(BaseModel):
    """对话式匹配请求"""
    user_intent: str  # 用户自然语言意图
    context: Optional[Dict[str, Any]] = None  # 上下文信息


class ConversationMatchResponse(BaseModel):
    """对话式匹配响应"""
    success: bool
    message: str  # AI 生成的自然语言回复
    matches: Optional[List[dict]] = None
    suggestions: Optional[List[str]] = None
    next_actions: Optional[List[str]] = None  # 建议的下一步操作
    # 新增：Generative UI 问题卡片
    question_card: Optional[dict] = None  # AI 生成的个人信息收集卡片
    need_profile_collection: Optional[bool] = None  # 是否需要收集信息


class RelationshipAnalysisRequest(BaseModel):
    """关系分析请求"""
    match_id: str
    analysis_type: str = "health_check"  # health_check, stage_progress, issue_detection


class RelationshipAnalysisResponse(BaseModel):
    """关系分析响应"""
    success: bool
    report: dict
    ai_summary: str  # AI 生成的自然语言总结
    recommendations: List[str]


class TopicSuggestionRequest(BaseModel):
    """话题建议请求"""
    match_id: str
    context: Optional[str] = "first_chat"


class TopicSuggestionResponse(BaseModel):
    """话题建议响应"""
    success: bool
    topics: List[dict]
    conversation_tips: List[str]
    ai_message: str  # AI 生成的引导语


# ============= 对话式匹配接口 =============

@router.post("/match", response_model=ConversationMatchResponse)
async def conversation_match(
    request: ConversationMatchRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    对话式匹配接口

    用户通过自然语言表达匹配需求，AI 理解意图并执行匹配。

    支持的意图：
    - "帮我找对象" -> 执行自主匹配推荐
    - "我想找喜欢旅行的女生" -> 带偏好的匹配
    - "看看今天有什么推荐" -> 每日推荐
    - "我想认真谈恋爱" -> 基于关系的匹配
    """
    user_id = current_user["user_id"]
    is_anonymous = current_user.get("is_anonymous", False)
    logger.info(f"[ConversationMatch] START: user_id={user_id}, is_anonymous={is_anonymous}, intent={request.user_intent[:50]}...")
    logger.info(f"[ConversationMatch] current_user dict: {current_user}")

    try:
        # Step 1: 检查用户画像缺口（AI Native 设计）
        # 如果用户缺乏关键信息，优先触发信息收集而非直接匹配
        profile_gaps = await _check_profile_gaps(user_id)

        # 如果有重要的信息缺口（如关系目标、性格等），触发信息收集
        if profile_gaps and len(profile_gaps) > 0:
            # 检查是否是高优先级的缺口（关系目标、性格特点等）
            high_priority_gaps = [g for g in profile_gaps if g.get("importance") == "high"]

            if high_priority_gaps or len(profile_gaps) >= 3:
                # 触发 ProfileCollectionSkill
                question_result = await _trigger_profile_collection(
                    user_id=user_id,
                    user_intent=request.user_intent,
                    gaps=profile_gaps
                )

                if question_result.get("question_card"):
                    return ConversationMatchResponse(
                        success=True,
                        message=question_result.get("ai_message", "让我先了解一下你的偏好~"),
                        question_card=question_result["question_card"],
                        need_profile_collection=True,
                        suggestions=["回答问题", "稍后再说"],
                        next_actions=["继续"]
                    )

        # Step 2: AI 意图理解
        logger.info(f"[ConversationMatch] Calling _parse_user_intent...")
        intent_result = _parse_user_intent(request.user_intent, user_id)
        logger.info(f"[ConversationMatch] Parsed intent: {intent_result}")

        # Step 2: 根据意图类型执行不同操作
        if intent_result["intent_type"] == "icebreaker":
            # 破冰建议 - 返回如何开始聊天的建议
            ai_message = _generate_icebreaker_advice(user_id)
            next_actions = ["查看示例", "继续提问"]

            return ConversationMatchResponse(
                success=True,
                message=ai_message,
                matches=[],
                suggestions=intent_result.get("suggestions", []),
                next_actions=next_actions
            )

        # 其他意图类型：执行匹配工作流
        logger.info(f"[ConversationMatch] Creating AutoMatchRecommendWorkflow...")
        workflow = AutoMatchRecommendWorkflow()
        logger.info(f"[ConversationMatch] Executing workflow with user_id={user_id}, limit={intent_result.get('limit', 5)}, min_score={intent_result.get('min_score', 0.6)}")
        workflow_result = workflow.execute(
            user_id=user_id,
            limit=intent_result.get("limit", 5),
            min_score=intent_result.get("min_score", 0.6),
            include_deep_analysis=True
        )
        logger.info(f"[ConversationMatch] Workflow result: {workflow_result}")

        if workflow_result.get("errors"):
            error_msg = workflow_result["errors"][0]
            logger.error(f"[ConversationMatch] Workflow error: {error_msg}")
            # 开发环境匿名用户没有匹配数据，返回友好提示
            if ("No candidates" in error_msg or "User is not active" in error_msg):
                return ConversationMatchResponse(
                    success=True,
                    message="你好！我是你的 AI 红娘助手 🌸\n\n开发环境暂无真实用户数据，无法进行匹配演示。\n\n建议你：\n• 先注册一个真实账号\n• 或者导入一些测试用户数据\n• 或者使用其他功能如'关系分析'、'话题建议'等",
                    matches=[],
                    suggestions=["注册账号", "导入测试数据", "尝试其他功能"],
                    next_actions=["查看详情", "稍后再说"]
                )
            raise HTTPException(status_code=500, detail=error_msg)

        # Step 3: 生成自然语言回复
        ai_message = _generate_match_message(intent_result, workflow_result)

        # Step 4: 生成建议的下一步操作
        next_actions = _suggest_next_actions(workflow_result)

        # 审计日志
        log_audit(
            actor=user_id,
            action="conversation_match",
            status="success",
            actor_type="user",
            resource_type="match_session",
            request={"intent": request.user_intent},
            response={"matches_count": len(workflow_result.get("recommendations", []))},
            metadata={"intent_parsed": intent_result}
        )

        return ConversationMatchResponse(
            success=True,
            message=ai_message,
            matches=workflow_result.get("recommendations", []),
            suggestions=intent_result.get("suggestions", []),
            next_actions=next_actions
        )

    except Exception as e:
        import traceback
        logger.error(f"[ConversationMatch] FAILED: user_id={user_id}, intent={request.user_intent[:50]}...")
        logger.error(f"[ConversationMatch] Exception type: {type(e).__name__}")
        logger.error(f"[ConversationMatch] Exception message: {str(e)}")
        logger.error(f"[ConversationMatch] Stack trace: {traceback.format_exc()}")
        log_audit(
            actor=user_id,
            action="conversation_match",
            status="failure",
            actor_type="user",
            request={"intent": request.user_intent},
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-recommend", response_model=ConversationMatchResponse)
async def daily_recommend(
    current_user: dict = Depends(get_current_user_optional)
):
    """
    每日自主推荐

    AI 主动分析用户状态，推送每日匹配推荐。
    """
    user_id = current_user["user_id"]
    logger.info(f"DailyRecommend: user={user_id}")

    try:
        # 执行自主匹配工作流
        workflow = AutoMatchRecommendWorkflow()
        result = workflow.execute(
            user_id=user_id,
            limit=5,
            min_score=0.65,
            include_deep_analysis=True
        )

        if result.get("errors"):
            raise HTTPException(status_code=500, detail=result["errors"][0])

        # 生成 AI 消息
        matches = result.get("recommendations", [])
        if not matches:
            ai_message = "今天暂时没有新的推荐，保持耐心，好的缘分值得等待。建议你完善一下个人资料，增加曝光机会哦~"
        else:
            top_match = matches[0]
            ai_message = f"今天为你找到{len(matches)}位潜在匹配对象！最匹配的是{top_match.get('user', {}).get('name', 'TA')}，"
            ai_message += f"你们有{len(top_match.get('common_interests', []))}个共同兴趣，匹配度{top_match.get('score', 0) * 100:.0f}%。"
            if top_match.get("reasoning"):
                ai_message += f"\n\n推荐理由：{top_match['reasoning']}"

        # 审计日志
        log_audit(
            actor=user_id,
            action="daily_recommend",
            status="success",
            actor_type="ai_agent",
            response={"matches_count": len(matches)}
        )

        return ConversationMatchResponse(
            success=True,
            message=ai_message,
            matches=matches,
            next_actions=["查看详情", "发起对话", "稍后再说"]
        )

    except Exception as e:
        logger.error(f"DailyRecommend failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 关系分析接口 =============

@router.post("/relationship/analyze", response_model=RelationshipAnalysisResponse)
async def relationship_analyze(
    request: RelationshipAnalysisRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    关系健康度分析

    AI 主动分析关系状态，提供改进建议。
    """
    user_id = current_user["user_id"]
    logger.info(f"RelationshipAnalyze: user={user_id}, match_id={request.match_id}, type={request.analysis_type}")

    try:
        # 执行关系健康度工作流
        workflow = RelationshipHealthCheckWorkflow()
        result = workflow.execute(
            match_id=request.match_id,
            period="weekly",
            auto_push=False
        )

        if result.get("errors"):
            raise HTTPException(status_code=500, detail=result["errors"][0])

        health_report = result.get("health_report", {})

        # 生成 AI 总结
        ai_summary = _generate_health_summary(health_report)

        # 审计日志
        log_audit(
            actor=user_id,
            action="relationship_health_check",
            status="success",
            actor_type="user",
            resource_type="relationship",
            resource_id=request.match_id,
            request={"analysis_type": request.analysis_type},
            response={"health_score": health_report.get("health_score")}
        )

        return RelationshipAnalysisResponse(
            success=True,
            report=health_report,
            ai_summary=ai_summary,
            recommendations=health_report.get("recommendations", [])
        )

    except Exception as e:
        logger.error(f"RelationshipAnalyze failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationship/{match_id}/status")
async def relationship_status(
    match_id: str,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    获取关系状态摘要

    快速查看当前关系的进展和健康度。
    """
    user_id = current_user["user_id"]

    try:
        # 使用关系追踪工具
        result = RelationshipTrackingTool.handle(match_id=match_id, period="weekly")

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        # 生成简短摘要
        stage = result.get("current_stage", "unknown")
        health_score = result.get("health_score", 0)

        stage_names = {
            "matched": "匹配成功",
            "chatting": "聊天中",
            "exchanged_contacts": "已交换联系方式",
            "first_date": "已首次约会",
            "dating": "交往中",
            "in_relationship": "确定关系"
        }

        status_text = f"当前关系阶段：{stage_names.get(stage, stage)}\n"
        status_text += f"关系健康度：{health_score * 100:.0f}%\n"

        if health_score >= 0.8:
            status_text += "你们的关系发展很好，继续保持！"
        elif health_score >= 0.6:
            status_text += "关系稳定，可以多创造一些互动机会。"
        else:
            status_text += "关系可能需要更多关注和投入。"

        return {
            "success": True,
            "match_id": match_id,
            "stage": stage,
            "stage_name": stage_names.get(stage, stage),
            "health_score": health_score,
            "status_text": status_text,
            "interaction_summary": result.get("interaction_summary", {}),
            "issues": result.get("potential_issues", [])
        }

    except Exception as e:
        logger.error(f"RelationshipStatus failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 破冰话题接口 =============

@router.post("/topics/suggest", response_model=TopicSuggestionResponse)
async def suggest_topics(
    request: TopicSuggestionRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    智能话题推荐

    AI 分析双方特征，推荐个性化破冰话题。
    """
    user_id = current_user["user_id"]
    logger.info(f"SuggestTopics: user={user_id}, match_id={request.match_id}, context={request.context}")

    try:
        # 执行破冰工作流
        workflow = AutoIcebreakerWorkflow()
        result = workflow.execute(
            match_id=request.match_id,
            trigger_type="manual",
            auto_push=False
        )

        if result.get("errors"):
            raise HTTPException(status_code=500, detail=result["errors"][0])

        topics = result.get("recommendations", [])
        tips = result.get("conversation_tips", [])

        # 生成 AI 引导语
        ai_message = _generate_topic_message(topics, request.context)

        # 审计日志
        log_audit(
            actor=user_id,
            action="topic_suggestion",
            status="success",
            actor_type="user",
            resource_type="match",
            resource_id=request.match_id,
            request={"context": request.context},
            response={"topics_count": len(topics)}
        )

        return TopicSuggestionResponse(
            success=True,
            topics=topics,
            conversation_tips=tips,
            ai_message=ai_message
        )

    except Exception as e:
        logger.error(f"SuggestTopics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compatibility/{user_id_2}")
async def compatibility_analysis(
    user_id_2: str,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    兼容性分析

    深度分析与特定用户的兼容性。
    """
    user_id_1 = current_user["user_id"]
    logger.info(f"CompatibilityAnalysis: {user_id_1} <-> {user_id_2}")

    try:
        result = CompatibilityAnalysisTool.handle(
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            dimensions=["interests", "personality", "lifestyle", "goals"]
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        # 生成 AI 解读
        ai_interpretation = _generate_compatibility_interpretation(result)

        return {
            "success": True,
            "analysis": result,
            "ai_interpretation": ai_interpretation
        }

    except Exception as e:
        logger.error(f"CompatibilityAnalysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 辅助函数 =============

def _parse_user_intent(intent: str, user_id: str) -> dict:
    """
    解析用户意图

    使用 ConversationMatchmakerSkill 进行 AI 驱动的意图理解，
    而非硬编码的关键词匹配。
    """
    from agent.skills.conversation_matchmaker_skill import get_conversation_matchmaker_skill

    logger.info(f"_parse_user_intent: Using AI skill to parse intent: {intent[:50]}...")

    try:
        # 获取 skill 实例
        skill = get_conversation_matchmaker_skill()

        # 调用 skill 的意图解析方法
        # _parse_intent 接收 context 字典，其中包含 user_intent
        intent_analysis = skill._parse_intent({
            "user_intent": intent,
            "user_id": user_id
        })

        logger.info(f"_parse_user_intent: Parsed intent type: {intent_analysis.get('intent_type', 'unknown')}")

        return intent_analysis

    except Exception as e:
        logger.error(f"_parse_user_intent: Skill-based parsing failed: {e}")
        # 降级处理：返回简单的通用意图
        return {
            "limit": 5,
            "min_score": 0.6,
            "suggestions": ["AI 意图识别失败，使用通用匹配"],
            "intent_type": "general"
        }


def _generate_match_message(intent: dict, workflow_result: dict) -> str:
    """生成匹配结果的 AI 消息"""
    matches = workflow_result.get("recommendations", [])

    if not matches:
        return "抱歉，今天暂时没有特别匹配的人选。缘分需要耐心等待，建议你完善个人资料，增加曝光机会~"

    top_match = matches[0]
    match_name = top_match.get("user", {}).get("name", "TA")
    score = top_match.get("score", 0) * 100

    message = f"为你找到{len(matches)}位潜在匹配对象！\n\n"
    message += f"最匹配的是{match_name}，匹配度{score:.0f}%。\n"

    if top_match.get("reasoning"):
        message += f"\n推荐理由：{top_match['reasoning']}\n"

    if top_match.get("common_interests"):
        interests = top_match["common_interests"][:3]
        message += f"\n共同兴趣：{', '.join(interests)}\n"

    return message


def _generate_icebreaker_advice(user_id: str) -> str:
    """生成破冰建议"""
    return """💡 开启对话的技巧：

1. **从兴趣入手**：聊聊对方的爱好，比如"你也喜欢旅行吗？去过最难忘的地方是哪里？"

2. **从简介找话题**：注意 TA 的个人介绍，找到可以深入的点

3. **从地区聊起**：问问当地的美食、景点，如"XX 是个好地方，有什么当地人爱去的地方推荐吗？"

4. **真诚最重要**：不用刻意讨好，做真实的自己

**示例开场白**：
• "嗨，看到你也喜欢 XX，我最近正好想了解，有什么推荐吗？"
• "你的照片拍得真好，是自己拍的吗？"
• "嗨！感觉我们挺有缘分的，想认识一下~"

记住：好的开始是成功的一半，但保持自然和真诚更重要！✨"""


def _suggest_next_actions(workflow_result: dict) -> List[str]:
    """建议下一步操作"""
    actions = []

    matches = workflow_result.get("recommendations", [])
    if matches:
        actions.append("查看最匹配的对象")
        actions.append("发起对话")
        actions.append("浏览更多推荐")

    return actions


def _generate_health_summary(report: dict) -> str:
    """生成关系健康报告的 AI 总结"""
    health_score = report.get("health_score", 0)
    stage = report.get("current_stage", "unknown")
    issues = report.get("potential_issues", [])

    stage_names = {
        "matched": "匹配成功",
        "chatting": "聊天中",
        "exchanged_contacts": "已交换联系方式",
        "first_date": "已首次约会",
        "dating": "交往中",
        "in_relationship": "确定关系"
    }

    summary = f"你们目前处于{stage_names.get(stage, stage)}阶段。\n"
    summary += f"关系健康度：{health_score * 100:.0f}%。\n\n"

    if health_score >= 0.8:
        summary += "你们的关系发展非常健康，互动频繁且稳定。继续保持真诚的沟通，关系有望更进一步！"
    elif health_score >= 0.6:
        summary += "你们的关系整体稳定，但还有提升空间。可以尝试增加一些互动频率，或者安排一次线下见面。"
    else:
        summary += "你们的关系可能需要更多关注。近期互动较少，建议主动联系对方，重新建立连接。"

    if issues:
        summary += f"\n\n注意：发现{len(issues)}个潜在问题：\n"
        for issue in issues[:2]:
            summary += f"- {issue.get('description', '未知问题')}\n"

    return summary


def _generate_topic_message(topics: List[dict], context: str) -> str:
    """生成话题建议的 AI 引导语"""
    if not topics:
        return "暂时没有合适的话题建议，可以先从简单的问候开始聊起~"

    context_names = {
        "first_chat": "初次聊天",
        "follow_up": "后续跟进",
        "date_plan": "约会计划",
        "deep_connection": "深度交流"
    }

    message = f"为你们的{context_names.get(context, '对话')}准备了以下话题：\n\n"

    for i, topic in enumerate(topics[:3], 1):
        message += f"{i}. {topic.get('topic', '')}\n"
        if topic.get("context"):
            message += f"   （{topic['context']}）\n"

    message += "\n小建议：保持真诚和好奇心，不要急于表现自己。问开放式问题，鼓励对方分享更多~"

    return message


def _generate_compatibility_interpretation(analysis: dict) -> str:
    """生成兼容性分析的 AI 解读"""
    overall_score = analysis.get("overall_score", 0) * 100
    conflicts = analysis.get("potential_conflicts", [])

    interpretation = f"你们的整体兼容性为{overall_score:.0f}%。\n\n"

    # 维度分析
    dimension_analysis = analysis.get("dimension_analysis", {})
    for dim_name, dim_data in dimension_analysis.items():
        score = dim_data.get("score", 0) * 100
        dim_names = {
            "interests": "兴趣匹配",
            "personality": "性格匹配",
            "lifestyle": "生活方式",
            "values": "价值观",
            "goals": "关系目标"
        }
        interpretation += f"{dim_names.get(dim_name, dim_name)}：{score:.0f}%\n"

    interpretation += "\n"

    if overall_score >= 80:
        interpretation += "你们是非常匹配的一对！在多个维度上都有很好的契合度。"
    elif overall_score >= 60:
        interpretation += "你们有不错的匹配度，在一些重要维度上比较契合。"
    else:
        interpretation += "你们的匹配度一般，可能需要更多时间来了解彼此。"

    if conflicts:
        interpretation += f"\n\n需要注意：\n"
        for conflict in conflicts:
            interpretation += f"- {conflict.get('description', '潜在冲突')}\n"

    return interpretation


# ============= 用户画像收集辅助函数 =============

async def _check_profile_gaps(user_id: str) -> List[Dict]:
    """
    检查用户画像缺口

    使用 ProfileCollectionSkill 分析用户缺少哪些关键信息。
    返回缺口列表，包含维度、重要性等信息。
    """
    try:
        from agent.skills.profile_collection_skill import get_profile_collection_skill

        skill = get_profile_collection_skill()

        # 获取用户当前画像
        profile = await _get_user_profile(user_id)

        # 分析缺口
        gaps = skill._analyze_profile_gaps(profile)

        logger.info(f"[ConversationMatch] Profile gaps for user={user_id}: {len(gaps)} gaps found")

        return gaps

    except Exception as e:
        logger.error(f"[ConversationMatch] Failed to check profile gaps: {e}")
        return []


async def _get_user_profile(user_id: str) -> Dict[str, Any]:
    """获取用户画像"""
    try:
        from utils.db_session_manager import db_session
        from db.models import UserDB

        with db_session() as db:
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if user:
                return {
                    "relationship_goal": getattr(user, "goal", None),
                    "age_preference": {
                        "min": getattr(user, "preferred_age_min", None),
                        "max": getattr(user, "preferred_age_max", None),
                    } if getattr(user, "preferred_age_min", None) else None,
                    "location_preference": getattr(user, "location", None),
                    "interests": getattr(user, "interests", None),
                    "lifestyle": None,
                    "values": None,
                    "deal_breakers": None,
                    "personality": None,
                }
    except Exception as e:
        logger.debug(f"Failed to get user profile: {e}")

    return {}


async def _trigger_profile_collection(
    user_id: str,
    user_intent: str,
    gaps: List[Dict]
) -> Dict:
    """
    触发个人信息收集流程

    当用户缺乏关键信息时，AI 生成问题卡片收集信息，
    而非直接进行匹配（AI Native 设计）。

    Returns:
        包含 question_card 和 ai_message 的字典
    """
    try:
        from agent.skills.profile_collection_skill import get_profile_collection_skill

        skill = get_profile_collection_skill()

        # 构建对话上下文
        conversation_context = [
            {"role": "user", "content": user_intent}
        ]

        # 获取当前画像
        profile = await _get_user_profile(user_id)

        # 调用 Skill 生成问题
        result = await skill.execute(
            user_id=user_id,
            conversation_context=conversation_context,
            current_profile=profile,
            trigger_reason="matching_need"  # 匹配需要信息
        )

        logger.info(f"[ConversationMatch] Profile collection triggered for user={user_id}")

        return {
            "question_card": result.get("question_card"),
            "ai_message": result.get("ai_message", "为了更好地帮你找到合适的对象，让我先了解一下你的偏好~"),
            "profile_gaps": result.get("profile_gaps", [])
        }

    except Exception as e:
        logger.error(f"[ConversationMatch] Failed to trigger profile collection: {e}")
        return {}


# ============= AI 主动推送接口 =============

@router.get("/ai/push/recommendations")
async def get_ai_push_recommendations(
    current_user: dict = Depends(get_current_user_optional)
):
    """
    获取 AI 主动推送的推荐

    AI 定期分析用户状态，主动推送匹配建议。
    """
    user_id = current_user.get("user_id")

    # 匿名用户返回空结果
    if current_user.get("is_anonymous"):
        return {
            "has_push": False,
            "message": "登录后获取更多推荐"
        }

    try:
        # 检查是否有新的推荐
        workflow = AutoMatchRecommendWorkflow()
        result = workflow.execute(
            user_id=user_id,
            limit=3,
            min_score=0.65,  # 降低阈值以获取更多推荐
            include_deep_analysis=True
        )

        matches = result.get("recommendations", [])

        if not matches:
            return {
                "has_push": False,
                "message": "暂时没有新的推荐"
            }

        # 为每个匹配添加用户信息
        from db.repositories import UserRepository
        from api.users import _from_db

        db = next(get_db())
        user_repo = UserRepository(db)

        enriched_matches = []
        for match in matches:
            target_user_id = match.get("user_id")
            db_target = user_repo.get_by_id(target_user_id)
            if db_target:
                user_dict = _from_db(db_target).model_dump()
                match["user"] = user_dict
                enriched_matches.append(match)

        matches = enriched_matches

        # 生成推送消息
        push_message = f"AI 为你找到{len(matches)}位新的匹配对象！"
        if matches:
            top = matches[0]
            push_message += f"\n最匹配的是{top.get('user', {}).get('name', 'TA')}，"
            push_message += f"匹配度{top.get('score', 0) * 100:.0f}%"

        return {
            "has_push": True,
            "message": push_message,
            "matches": matches,
            "pushed_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"GetAiPushRecommendations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))