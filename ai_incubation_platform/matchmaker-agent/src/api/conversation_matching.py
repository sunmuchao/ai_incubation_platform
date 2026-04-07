"""
对话式匹配 API

提供 AI Native 的对话式交互接口，替代传统的表单筛选模式。
用户通过自然语言表达需求，AI 理解并执行匹配操作。
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_db
from db.repositories import UserRepository
from db.audit import log_audit, get_audit_logger
from utils.logger import logger
from auth.jwt import get_current_user
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
    current_user: dict = Depends(get_current_user)
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
    logger.info(f"ConversationMatch: user={user_id}, intent={request.user_intent[:50]}...")

    try:
        # Step 1: AI 意图理解
        intent_result = _parse_user_intent(request.user_intent, user_id)
        logger.info(f"Parsed intent: {intent_result}")

        # Step 2: 执行匹配工作流
        workflow = AutoMatchRecommendWorkflow()
        workflow_result = workflow.execute(
            user_id=user_id,
            limit=intent_result.get("limit", 5),
            min_score=intent_result.get("min_score", 0.6),
            include_deep_analysis=True
        )

        if workflow_result.get("errors"):
            raise HTTPException(status_code=500, detail=workflow_result["errors"][0])

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
        logger.error(f"ConversationMatch failed: {e}")
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
    current_user: dict = Depends(get_current_user)
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
    current_user: dict = Depends(get_current_user)
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
    current_user: dict = Depends(get_current_user)
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
    current_user: dict = Depends(get_current_user)
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
    current_user: dict = Depends(get_current_user)
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

    将自然语言转换为匹配参数。
    """
    intent_lower = intent.lower()

    result = {
        "limit": 5,
        "min_score": 0.6,
        "suggestions": [],
        "intent_type": "general"
    }

    # 识别意图类型
    if any(word in intent_lower for word in ["找对象", "找男女朋友", "谈恋爱", "认真"]):
        result["intent_type"] = "serious_relationship"
        result["min_score"] = 0.7  # 更严格匹配
        result["suggestions"].append("基于关系目标的匹配")

    if any(word in intent_lower for word in ["看看", "推荐", "今日", "每天"]):
        result["intent_type"] = "daily_browse"
        result["suggestions"].append("每日精选推荐")

    if any(word in intent_lower for word in ["喜欢旅行", "爱旅游", "旅行"]):
        result["intent_type"] = "interest_based"
        result["suggestions"].append("基于旅行兴趣的匹配")

    if any(word in intent_lower for word in [" nearby", "附近", "同城", "本地"]):
        result["intent_type"] = "location_based"
        result["suggestions"].append("基于地理位置的匹配")

    # 提取数量意图
    if "三个" in intent or "3 个" in intent:
        result["limit"] = 3
    elif "五个" in intent or "5 个" in intent:
        result["limit"] = 5
    elif "十个" in intent or "10 个" in intent:
        result["limit"] = 10

    return result


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


# ============= AI 主动推送接口 =============

@router.get("/ai/push/recommendations")
async def get_ai_push_recommendations(
    current_user: dict = Depends(get_current_user)
):
    """
    获取 AI 主动推送的推荐

    AI 定期分析用户状态，主动推送匹配建议。
    """
    user_id = current_user["user_id"]

    try:
        # 检查是否有新的推荐
        workflow = AutoMatchRecommendWorkflow()
        result = workflow.execute(
            user_id=user_id,
            limit=3,
            min_score=0.75,  # 只推送高质量匹配
            include_deep_analysis=True
        )

        matches = result.get("recommendations", [])

        if not matches:
            return {
                "has_push": False,
                "message": "暂时没有新的推荐"
            }

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