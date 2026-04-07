"""
P6 对话 AI 分析升级 API

多模态情感分析、关系进展预测等功能。
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB, ConversationDB, RelationshipProgressDB
from services.conversation_analysis_service import ConversationAnalysisService


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# 情感分析增强
@router.post("/analyze/sentiment")
async def analyze_message_sentiment(
    content: str = Body(..., embed=True),
    context_messages: Optional[List[str]] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    多模态情感分析

    分析消息的情感倾向、情绪类型、强度等
    """
    # 基础情感分析
    sentiment_score = _compute_sentiment_score(content)
    emotion = _detect_emotion(content)
    intensity = _compute_emotion_intensity(content)

    # 上下文感知分析
    context_adjustment = 0.0
    if context_messages:
        context_sentiment = sum(_compute_sentiment_score(m) for m in context_messages[-3:]) / len(context_messages[-3:])
        # 情感变化趋势
        sentiment_shift = sentiment_score - context_sentiment
        context_adjustment = sentiment_shift * 0.1  # 小幅度调整

    adjusted_sentiment = max(-1.0, min(1.0, sentiment_score + context_adjustment))

    # 关系影响分析
    relationship_impact = _analyze_relationship_impact(content, emotion, sentiment_score)

    return {
        "success": True,
        "data": {
            "sentiment": {
                "score": round(sentiment_score, 3),
                "adjusted_score": round(adjusted_sentiment, 3),
                "label": _sentiment_label(adjusted_sentiment),
            },
            "emotion": {
                "primary": emotion,
                "intensity": round(intensity, 2),
                "secondary": _detect_secondary_emotion(content),
            },
            "relationship_impact": relationship_impact,
            "suggestions": _generate_communication_suggestions(content, emotion, adjusted_sentiment),
        }
    }


@router.post("/analyze/conversation-flow")
async def analyze_conversation_flow(
    user_id_1: str = Body(...),
    user_id_2: str = Body(...),
    limit: int = Body(default=50),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    分析对话流程和情感变化趋势
    """
    # 获取对话历史
    conversations = db.query(ConversationDB).filter(
        ((ConversationDB.user_id_1 == user_id_1) & (ConversationDB.user_id_2 == user_id_2)) |
        ((ConversationDB.user_id_1 == user_id_2) & (ConversationDB.user_id_2 == user_id_1))
    ).order_by(ConversationDB.created_at.desc()).limit(limit).all()

    if not conversations:
        return {
            "success": True,
            "data": None,
            "message": "暂无对话记录"
        }

    # 分析情感变化趋势
    sentiment_timeline = []
    for conv in reversed(conversations):
        sentiment = _compute_sentiment_score(conv.message_content)
        sentiment_timeline.append({
            "timestamp": conv.created_at.isoformat(),
            "sentiment": round(sentiment, 3),
            "sender": "user1" if conv.sender_id == user_id_1 else "user2",
        })

    # 计算整体趋势
    sentiments = [t["sentiment"] for t in sentiment_timeline]
    trend = "improving" if len(sentiments) > 1 and sentiments[-1] > sentiments[0] else \
            "declining" if len(sentiments) > 1 and sentiments[-1] < sentiments[0] else "stable"

    # 对话平衡分析
    user1_count = sum(1 for t in sentiment_timeline if t["sender"] == "user1")
    user2_count = len(sentiment_timeline) - user1_count
    balance_ratio = min(user1_count, user2_count) / max(user1_count, user2_count) if max(user1_count, user2_count) > 0 else 0

    return {
        "success": True,
        "data": {
            "timeline": sentiment_timeline,
            "trend": trend,
            "average_sentiment": round(sum(sentiments) / len(sentiments), 3) if sentiments else 0,
            "conversation_balance": {
                "user1_count": user1_count,
                "user2_count": user2_count,
                "balance_ratio": round(balance_ratio, 2),
                "balanced": balance_ratio > 0.7,
            },
            "insights": _generate_conversation_insights(sentiment_timeline, trend, balance_ratio),
        }
    }


@router.get("/predict/relationship-progress")
async def predict_relationship_progress(
    user_id_1: str,
    user_id_2: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    关系进展预测

    基于对话历史和互动数据预测关系发展阶段
    """
    # 获取对话统计
    conversation_count = db.query(ConversationDB).filter(
        ((ConversationDB.user_id_1 == user_id_1) & (ConversationDB.user_id_2 == user_id_2)) |
        ((ConversationDB.user_id_1 == user_id_2) & (ConversationDB.user_id_2 == user_id_1))
    ).count()

    # 获取关系进展记录
    progress_records = db.query(RelationshipProgressDB).filter(
        ((RelationshipProgressDB.user_id_1 == user_id_1) & (RelationshipProgressDB.user_id_2 == user_id_2)) |
        ((RelationshipProgressDB.user_id_1 == user_id_2) & (RelationshipProgressDB.user_id_2 == user_id_1))
    ).order_by(RelationshipProgressDB.created_at.desc()).all()

    # 计算关系分数
    relationship_score = _calculate_relationship_score(
        conversation_count=conversation_count,
        progress_count=len(progress_records),
    )

    # 预测关系阶段
    current_stage = _predict_relationship_stage(relationship_score, len(progress_records))
    next_stage = _predict_next_stage(current_stage)

    # 计算进展概率
    progression_probability = _calculate_progression_probability(
        current_stage=current_stage,
        sentiment_trend="stable",
        interaction_frequency=conversation_count,
    )

    return {
        "success": True,
        "data": {
            "current_stage": current_stage,
            "next_stage": next_stage,
            "relationship_score": round(relationship_score, 2),
            "progression_probability": round(progression_probability, 2),
            "recommendations": _generate_relationship_recommendations(current_stage, progression_probability),
        }
    }


@router.post("/analyze/topic-evolution")
async def analyze_topic_evolution(
    user_id: str = Body(...),
    days: int = Body(default=30),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    分析话题演变趋势

    追踪用户对话题的兴趣变化
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # 获取对话记录
    conversations = db.query(ConversationDB).filter(
        ConversationDB.user_id_1 == user_id,
        ConversationDB.created_at >= cutoff_date
    ).order_by(ConversationDB.created_at).all()

    if not conversations:
        return {
            "success": True,
            "data": None,
            "message": "暂无对话记录"
        }

    # 分析话题演变
    topic_timeline = []
    for conv in conversations:
        topics = json.loads(conv.topic_tags) if conv.topic_tags else []
        if topics:
            topic_timeline.append({
                "date": conv.created_at.date().isoformat(),
                "topics": topics,
                "sentiment": conv.sentiment_score,
            })

    # 聚合话题频率
    topic_frequency = {}
    for item in topic_timeline:
        for topic in item["topics"]:
            if topic not in topic_frequency:
                topic_frequency[topic] = {"count": 0, "sentiments": []}
            topic_frequency[topic]["count"] += 1
            if item["sentiment"]:
                topic_frequency[topic]["sentiments"].append(item["sentiment"])

    # 计算话题平均情感
    for topic, data in topic_frequency.items():
        if data["sentiments"]:
            data["avg_sentiment"] = round(sum(data["sentiments"]) / len(data["sentiments"]), 3)
        else:
            data["avg_sentiment"] = 0
        del data["sentiments"]

    # 识别新兴话题（最近 7 天新增或频率上升）
    recent_cutoff = datetime.utcnow() - timedelta(days=7)
    recent_topics = set()
    older_topics = set()

    for item in topic_timeline:
        if datetime.fromisoformat(item["date"]).date() >= recent_cutoff.date():
            recent_topics.update(item["topics"])
        else:
            older_topics.update(item["topics"])

    emerging_topics = list(recent_topics - older_topics)

    return {
        "success": True,
        "data": {
            "topic_frequency": topic_frequency,
            "emerging_topics": emerging_topics,
            "timeline_sample": topic_timeline[-10:],  # 最近 10 条
            "insights": _generate_topic_insights(topic_frequency, emerging_topics),
        }
    }


# === 辅助函数 ===

def _compute_sentiment_score(text: str) -> float:
    """计算情感得分"""
    positive_words = ["开心", "高兴", "好", "棒", "喜欢", "爱", "快乐", "幸福", "美好", "期待", "哈哈", "嘻嘻", "不错", "优秀", "厉害"]
    negative_words = ["难过", "伤心", "痛苦", "讨厌", "恨", "糟糕", "差", "失望", "绝望", "累", "烦", "郁闷", "无语", "呵呵"]

    score = 0.0
    for word in positive_words:
        if word in text:
            score += 0.15
    for word in negative_words:
        if word in text:
            score -= 0.15

    return max(-1.0, min(1.0, score))


def _sentiment_label(score: float) -> str:
    """情感标签"""
    if score >= 0.5:
        return "positive"
    elif score <= -0.5:
        return "negative"
    elif score >= 0.2:
        return "slightly_positive"
    elif score <= -0.2:
        return "slightly_negative"
    else:
        return "neutral"


def _detect_emotion(text: str) -> str:
    """检测主要情绪"""
    emotion_keywords = {
        "happy": ["开心", "高兴", "快乐", "笑", "哈哈", "嘻嘻", "爽", "棒"],
        "sad": ["难过", "伤心", "哭", "痛苦", "悲伤", "泪", "郁闷"],
        "anxious": ["害怕", "担心", "焦虑", "紧张", "恐惧", "不安"],
        "angry": ["生气", "愤怒", "恼火", "烦", "讨厌", "气", "滚"],
        "excited": ["兴奋", "激动", "期待", "哇", "太", "超级"],
        "surprised": ["惊讶", "震惊", "居然", "竟然", "没想到"],
    }

    max_count = 0
    primary_emotion = "neutral"

    for emotion, keywords in emotion_keywords.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > max_count:
            max_count = count
            primary_emotion = emotion

    return primary_emotion


def _detect_secondary_emotion(text: str) -> Optional[str]:
    """检测次要情绪"""
    # 简化实现
    return None


def _compute_emotion_intensity(text: str) -> float:
    """计算情绪强度"""
    intensity_markers = ["!!!", "！！！", "???", "？？？", "太", "超级", "非常", "特别", "极其", "..."]
    count = sum(1 for marker in intensity_markers if marker in text)
    return min(1.0, 0.3 + count * 0.15)


def _analyze_relationship_impact(content: str, emotion: str, sentiment: float) -> Dict[str, Any]:
    """分析对关系的潜在影响"""
    impact_type = "neutral"
    description = "这条消息对关系影响中性"

    if sentiment > 0.5 and emotion in ["happy", "excited"]:
        impact_type = "positive"
        description = "这条消息有助于增进关系"
    elif sentiment < -0.5 and emotion in ["angry", "sad"]:
        impact_type = "negative"
        description = "这条消息可能对关系产生负面影响"
    elif emotion == "anxious":
        impact_type = "uncertain"
        description = "这条消息表达了不确定性，可能需要进一步沟通"

    return {
        "type": impact_type,
        "description": description,
        "suggestion": _get_impact_suggestion(impact_type),
    }


def _get_impact_suggestion(impact_type: str) -> str:
    """获取沟通建议"""
    suggestions = {
        "positive": "保持这种积极的沟通方式！",
        "negative": "建议冷静一下，换种方式表达",
        "uncertain": "可以更明确地表达自己的想法",
        "neutral": "可以尝试增加一些情感表达",
    }
    return suggestions.get(impact_type, "")


def _generate_communication_suggestions(content: str, emotion: str, sentiment: float) -> List[str]:
    """生成沟通建议"""
    suggestions = []

    if sentiment < -0.3:
        suggestions.append("当前情绪较低落，建议先调整心情再交流")
    if emotion == "angry":
        suggestions.append("检测到愤怒情绪，建议冷静 5 分钟后再回复")
    if len(content) < 10:
        suggestions.append("回复较短，可以适当多分享一些想法")
    if "?" in content or "？" in content:
        suggestions.append("提出了问题，这是促进对话的好方式")

    if not suggestions:
        suggestions.append("继续保持良好的沟通！")

    return suggestions


def _calculate_relationship_score(conversation_count: int, progress_count: int) -> float:
    """计算关系分数"""
    # 基础分数：对话次数
    conv_score = min(50, conversation_count * 2)

    # 进展分数：里程碑数量
    progress_score = min(30, progress_count * 10)

    # 其他因素（简化）
    other_score = 20  # 假设其他因素得分

    return conv_score + progress_score + other_score


def _predict_relationship_stage(score: float, progress_count: int) -> str:
    """预测关系阶段"""
    if score >= 80 or progress_count >= 5:
        return "in_relationship"
    elif score >= 60 or progress_count >= 3:
        return "dating"
    elif score >= 40 or progress_count >= 1:
        return "getting_to_know"
    else:
        return "initial_contact"


def _predict_next_stage(current_stage: str) -> str:
    """预测下一阶段"""
    stages = ["initial_contact", "getting_to_know", "dating", "in_relationship"]
    current_idx = stages.index(current_stage) if current_stage in stages else 0
    next_idx = min(current_idx + 1, len(stages) - 1)
    return stages[next_idx]


def _calculate_progression_probability(current_stage: str, sentiment_trend: str,
                                       interaction_frequency: int) -> float:
    """计算进展概率"""
    base_prob = 0.5

    # 阶段调整
    stage_adjustment = {
        "initial_contact": 0.1,
        "getting_to_know": 0.15,
        "dating": 0.1,
        "in_relationship": 0.05,
    }
    base_prob += stage_adjustment.get(current_stage, 0)

    # 情感趋势调整
    if sentiment_trend == "improving":
        base_prob += 0.2
    elif sentiment_trend == "declining":
        base_prob -= 0.2

    # 互动频率调整
    if interaction_frequency > 100:
        base_prob += 0.1
    elif interaction_frequency > 50:
        base_prob += 0.05

    return min(0.95, max(0.05, base_prob))


def _generate_relationship_recommendations(stage: str, probability: float) -> List[str]:
    """生成关系建议"""
    recommendations = []

    if stage == "initial_contact":
        recommendations.append("多了解对方的兴趣爱好，寻找共同话题")
        recommendations.append("保持适度的联系频率，不要过于急切")
    elif stage == "getting_to_know":
        recommendations.append("可以尝试邀请对方参加一些轻松的活动")
        recommendations.append("分享一些个人经历，加深彼此了解")
    elif stage == "dating":
        recommendations.append("考虑安排一些有意义的约会")
        recommendations.append("坦诚沟通彼此期待和界限")
    elif stage == "in_relationship":
        recommendations.append("持续经营关系，保持新鲜感")
        recommendations.append("一起规划未来，建立共同目标")

    if probability < 0.4:
        recommendations.append("近期进展较慢，可以尝试主动一些")
    elif probability > 0.7:
        recommendations.append("关系发展良好，继续保持！")

    return recommendations


def _generate_conversation_insights(timeline: List, trend: str, balance_ratio: float) -> List[str]:
    """生成对话洞察"""
    insights = []

    if trend == "improving":
        insights.append("你们的情感交流呈上升趋势，关系在积极发展")
    elif trend == "declining":
        insights.append("近期情感交流有所下降，建议关注对方感受")
    else:
        insights.append("你们的情感交流保持稳定")

    if balance_ratio > 0.8:
        insights.append("对话参与度很平衡，双方都很投入")
    elif balance_ratio < 0.5:
        insights.append("对话参与度不太平衡，建议多关注对方的回应")

    return insights


def _generate_topic_insights(topic_frequency: Dict, emerging_topics: List) -> List[str]:
    """生成话题洞察"""
    insights = []

    # 找到最常讨论的话题
    if topic_frequency:
        top_topic = max(topic_frequency.items(), key=lambda x: x[1]["count"])
        insights.append(f"最常讨论的话题是：{top_topic[0]}")

    # 新兴话题
    if emerging_topics:
        insights.append(f"近期新话题：{', '.join(emerging_topics)}")

    # 情感倾向
    positive_topics = [t for t, d in topic_frequency.items() if d.get("avg_sentiment", 0) > 0.3]
    if positive_topics:
        insights.append(f"积极话题：{', '.join(positive_topics[:3])}")

    return insights