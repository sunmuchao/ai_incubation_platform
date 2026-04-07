"""
Community Tools - 社区治理工具集

这些工具供 AI Agent 调用，执行具体的社区治理操作。
每个工具都记录审计日志，支持追溯和问责。
"""

import logging
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ==================== 工具注册表 ====================

TOOLS_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(name: str, description: str, input_schema: Dict[str, Any]):
    """
    工具注册装饰器工厂

    用法:
    @register_tool(name="tool_name", description="...", input_schema={...})
    async def tool_handler(input_data):
        ...
    """
    def decorator(handler: Callable):
        TOOLS_REGISTRY[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "handler": handler,
        }
        logger.info(f"Tool registered: {name}")
        return handler
    return decorator


def get_tool(name: str) -> Optional[Dict[str, Any]]:
    """获取工具定义"""
    return TOOLS_REGISTRY.get(name)


def list_tools() -> List[Dict[str, Any]]:
    """列出所有可用工具"""
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"],
        }
        for tool in TOOLS_REGISTRY.values()
    ]


async def execute_tool(name: str, **input_data) -> Dict[str, Any]:
    """执行工具"""
    tool = get_tool(name)
    if not tool:
        return {"error": f"Tool not found: {name}"}

    try:
        handler = tool["handler"]
        result = await handler(input_data)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Tool execution failed: {name}: {e}")
        return {"success": False, "error": str(e)}


# ==================== 内容治理工具 ====================

@register_tool(
    name="analyze_content",
    description="分析内容风险，检测违规内容。用于 AI 版主巡查时评估内容合规性。",
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "待分析的内容文本"},
            "content_type": {"type": "string", "enum": ["post", "comment"], "description": "内容类型"},
            "author_id": {"type": "string", "description": "作者 ID"},
            "context": {"type": "string", "description": "可选的上下文信息"},
        },
        "required": ["content"],
    },
)
async def analyze_content_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """分析内容风险"""
    content = input_data.get("content", "")
    content_type = input_data.get("content_type", "post")
    author_id = input_data.get("author_id")

    # 风险分析
    risk_indicators = []
    risk_score = 0.0

    # 关键词检测
    spam_keywords = ["加微信", "转账", "点击链接", "免费", "赚钱", "刷单", "兼职"]
    violence_keywords = ["杀人", "暴力", "打架", "武器", "炸弹"]
    hate_keywords = ["傻逼", "废物", "去死", "垃圾", "蠢货"]

    for keyword in spam_keywords:
        if keyword in content:
            risk_indicators.append({"type": "spam", "keyword": keyword})
            risk_score += 0.15

    for keyword in violence_keywords:
        if keyword in content:
            risk_indicators.append({"type": "violence", "keyword": keyword})
            risk_score += 0.25

    for keyword in hate_keywords:
        if keyword in content:
            risk_indicators.append({"type": "hate_speech", "keyword": keyword})
            risk_score += 0.2

    # 链接检测
    link_count = content.count("http://") + content.count("https://") + content.count("www.")
    if link_count > 3:
        risk_indicators.append({"type": "excessive_links", "count": link_count})
        risk_score += 0.2

    # 内容长度异常
    if len(content) < 5:
        risk_indicators.append({"type": "too_short", "length": len(content)})
        risk_score += 0.1
    elif len(content) > 10000:
        risk_indicators.append({"type": "too_long", "length": len(content)})
        risk_score += 0.1

    # 全大写/重复字符检测（垃圾内容特征）
    if content.isupper() and len(content) > 10:
        risk_indicators.append({"type": "all_caps"})
        risk_score += 0.1

    return {
        "risk_score": min(1.0, risk_score),
        "risk_level": "high" if risk_score >= 0.7 else "medium" if risk_score >= 0.3 else "low",
        "indicators": risk_indicators,
        "summary": f"检测到 {len(risk_indicators)} 个风险指标" if risk_indicators else "内容无明显风险",
        "recommendation": "reject" if risk_score >= 0.8 else "flag" if risk_score >= 0.3 else "approve",
    }


@register_tool(
    name="check_community_rules",
    description="检查内容是否违反社区规则。返回匹配的规则列表和违规程度。",
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "待检查的内容"},
            "rule_category": {"type": "string", "enum": ["spam", "violence", "hate", "adult", "all"], "description": "规则类别"},
        },
        "required": ["content"],
    },
)
async def check_rules_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """检查社区规则违反"""
    content = input_data.get("content", "").lower()
    rule_category = input_data.get("rule_category", "all")

    # 规则定义（实际实现应从数据库加载）
    rules = {
        "spam": {
            "name": "反垃圾广告规则",
            "patterns": ["加微信", "qq:", "点击链接", "免费领取", "限时优惠"],
            "severity": 0.7,
        },
        "violence": {
            "name": "反暴力内容规则",
            "patterns": ["杀人", "打死", "暴力", "武器", "炸弹"],
            "severity": 0.9,
        },
        "hate": {
            "name": "反仇恨言论规则",
            "patterns": ["傻逼", "废物", "去死", "垃圾", "蠢货", "脑残"],
            "severity": 0.8,
        },
        "adult": {
            "name": "反色情内容规则",
            "patterns": ["色情", "裸体", "成人", "性"],
            "severity": 0.9,
        },
    }

    matched_rules = []
    max_severity = 0.0

    categories_to_check = list(rules.keys()) if rule_category == "all" else [rule_category]

    for category in categories_to_check:
        if category not in rules:
            continue

        rule = rules[category]
        matched_patterns = []

        for pattern in rule["patterns"]:
            if pattern.lower() in content:
                matched_patterns.append(pattern)
                max_severity = max(max_severity, rule["severity"])

        if matched_patterns:
            matched_rules.append({
                "rule_id": category,
                "rule_name": rule["name"],
                "matched_patterns": matched_patterns,
                "severity": rule["severity"],
            })

    return {
        "violated": len(matched_rules) > 0,
        "matched_rules": matched_rules,
        "max_severity": max_severity,
        "recommendation": "reject" if max_severity >= 0.8 else "flag" if max_severity >= 0.5 else "approve",
    }


@register_tool(
    name="get_user_history",
    description="获取用户历史行为记录，用于评估用户可信度。",
    input_schema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "用户 ID"},
            "history_type": {"type": "string", "enum": ["posts", "comments", "violations", "all"], "description": "历史类型"},
            "limit": {"type": "integer", "description": "返回记录数量", "default": 50},
        },
        "required": ["user_id"],
    },
)
async def get_user_history_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """获取用户历史"""
    user_id = input_data.get("user_id")
    history_type = input_data.get("history_type", "all")
    limit = input_data.get("limit", 50)

    # 占位实现（实际应从数据库查询）
    # 这里返回模拟数据
    return {
        "user_id": user_id,
        "total_posts": 0,
        "total_comments": 0,
        "total_violations": 0,
        "violation_rate": 0.0,
        "account_age_days": 0,
        "reputation_score": 1.0,
        "recent_activity": [],
    }


@register_tool(
    name="make_moderation_decision",
    description="基于分析和规则检查结果，做出内容审核决策。",
    input_schema={
        "type": "object",
        "properties": {
            "content_id": {"type": "string", "description": "内容 ID"},
            "analysis_result": {"type": "object", "description": "内容分析结果"},
            "rule_check_result": {"type": "object", "description": "规则检查结果"},
            "user_history": {"type": "object", "description": "用户历史记录"},
            "auto_action_threshold": {"type": "number", "description": "自主行动阈值", "default": 0.9},
        },
        "required": ["content_id", "analysis_result"],
    },
)
async def make_moderation_decision_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """做出审核决策"""
    content_id = input_data.get("content_id")
    analysis_result = input_data.get("analysis_result", {})
    rule_check_result = input_data.get("rule_check_result", {})
    user_history = input_data.get("user_history", {})
    auto_threshold = input_data.get("auto_action_threshold", 0.9)

    # 计算综合风险分数
    analysis_risk = analysis_result.get("risk_score", 0)
    rule_severity = rule_check_result.get("max_severity", 0)
    user_violation_rate = user_history.get("violation_rate", 0)

    # 加权计算
    composite_risk = (analysis_risk * 0.4) + (rule_severity * 0.4) + (user_violation_rate * 0.2)

    # 调整因子：用户历史良好可降低风险
    if user_history.get("reputation_score", 1.0) > 4.0:
        composite_risk *= 0.8
    # 调整因子：用户有多次违规可提高风险
    if user_history.get("total_violations", 0) > 5:
        composite_risk *= 1.2

    composite_risk = min(1.0, composite_risk)

    # 决策
    if composite_risk >= auto_threshold:
        action = "remove"
        confidence = composite_risk
        reasoning = f"综合风险分数 {composite_risk:.2f} >= {auto_threshold}，自主删除"
    elif composite_risk >= 0.5:
        action = "flag"
        confidence = composite_risk
        reasoning = f"综合风险分数 {composite_risk:.2f} >= 0.5，标记人工审核"
    else:
        action = "approve"
        confidence = 1.0 - composite_risk
        reasoning = f"综合风险分数 {composite_risk:.2f} < 0.5，审核通过"

    return {
        "content_id": content_id,
        "action": action,
        "confidence": confidence,
        "composite_risk": composite_risk,
        "reasoning": reasoning,
        "requires_human_review": action == "flag",
    }


# ==================== 成员匹配工具 ====================

@register_tool(
    name="analyze_member_interests",
    description="分析成员的兴趣爱好和专长领域，用于匹配推荐。",
    input_schema={
        "type": "object",
        "properties": {
            "member_id": {"type": "string", "description": "成员 ID"},
            "include_posts": {"type": "boolean", "description": "是否分析发帖历史", "default": True},
            "include_interactions": {"type": "boolean", "description": "是否分析互动历史", "default": True},
        },
        "required": ["member_id"],
    },
)
async def analyze_member_interests_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """分析成员兴趣"""
    member_id = input_data.get("member_id")

    # 占位实现（实际应分析用户发帖、评论、点赞等行为）
    return {
        "member_id": member_id,
        "interests": [
            {"topic": "人工智能", "confidence": 0.9},
            {"topic": "Python 编程", "confidence": 0.8},
            {"topic": "数据科学", "confidence": 0.7},
        ],
        "expertise_areas": ["机器学习", "自然语言处理"],
        "activity_level": "high",
        "preferred_content_types": ["技术文章", "教程", "讨论"],
    }


@register_tool(
    name="find_matching_members",
    description="根据兴趣和专长，找到匹配的成员。用于 AI 主动推荐志同道合的人。",
    input_schema={
        "type": "object",
        "properties": {
            "member_id": {"type": "string", "description": "请求匹配的成员 ID"},
            "match_criteria": {"type": "object", "description": "匹配条件"},
            "limit": {"type": "integer", "description": "返回匹配数量", "default": 10},
        },
        "required": ["member_id"],
    },
)
async def find_matching_members_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """查找匹配成员"""
    member_id = input_data.get("member_id")
    limit = input_data.get("limit", 10)

    # 占位实现（实际应基于兴趣图谱和社交网络进行匹配）
    return {
        "member_id": member_id,
        "matches": [
            {
                "matched_member_id": f"member_{i}",
                "match_score": 0.9 - (i * 0.05),
                "common_interests": ["人工智能", "Python 编程"],
                "complementary_skills": ["深度学习", "数据可视化"],
                "reason": f"与你有 {2} 个共同兴趣，技能互补",
            }
            for i in range(limit)
        ],
    }


@register_tool(
    name="get_content_recommendations",
    description="根据成员兴趣推荐相关内容和活动。",
    input_schema={
        "type": "object",
        "properties": {
            "member_id": {"type": "string", "description": "成员 ID"},
            "recommendation_type": {"type": "string", "enum": ["posts", "discussions", "events", "all"], "description": "推荐类型"},
            "limit": {"type": "integer", "description": "返回推荐数量", "default": 10},
        },
        "required": ["member_id"],
    },
)
async def get_content_recommendations_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """获取内容推荐"""
    member_id = input_data.get("member_id")
    limit = input_data.get("limit", 10)
    rec_type = input_data.get("recommendation_type", "all")

    # 占位实现
    recommendations = []

    if rec_type in ["posts", "all"]:
        for i in range(limit // 2):
            recommendations.append({
                "type": "post",
                "item_id": f"post_{i}",
                "title": f"推荐文章 {i + 1}",
                "relevance_score": 0.9 - (i * 0.08),
                "reason": "与你感兴趣的 人工智能 相关",
            })

    if rec_type in ["discussions", "all"]:
        for i in range(limit // 2):
            recommendations.append({
                "type": "discussion",
                "item_id": f"discussion_{i}",
                "title": f"讨论话题 {i + 1}",
                "relevance_score": 0.85 - (i * 0.08),
                "reason": "与你感兴趣的 Python 编程 相关",
            })

    return {
        "member_id": member_id,
        "recommendations": sorted(recommendations, key=lambda x: x["relevance_score"], reverse=True)[:limit],
    }


# ==================== 通知工具 ====================

@register_tool(
    name="send_notification",
    description="发送通知给用户。用于 AI 自主决策后的用户通知。",
    input_schema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "接收通知的用户 ID"},
            "notification_type": {"type": "string", "enum": ["content_removed", "content_flagged", "match_suggestion", "recommendation"], "description": "通知类型"},
            "title": {"type": "string", "description": "通知标题"},
            "message": {"type": "string", "description": "通知内容"},
            "action_url": {"type": "string", "description": "可选的操作链接"},
        },
        "required": ["user_id", "notification_type", "title", "message"],
    },
)
async def send_notification_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """发送通知"""
    user_id = input_data.get("user_id")
    notification_type = input_data.get("notification_type")
    title = input_data.get("title")
    message = input_data.get("message")
    action_url = input_data.get("action_url")

    # 占位实现（实际应调用通知服务）
    return {
        "success": True,
        "notification_id": f"notif_{datetime.now().timestamp()}",
        "user_id": user_id,
        "type": notification_type,
        "delivered": True,
    }


# ==================== 透明度工具 ====================

@register_tool(
    name="get_decision_explanation",
    description="获取 AI 决策的详细解释。用于透明度展示和用户申诉。",
    input_schema={
        "type": "object",
        "properties": {
            "decision_id": {"type": "string", "description": "决策 ID 或追溯 ID"},
            "content_id": {"type": "string", "description": "相关内容 ID"},
        },
        "required": ["decision_id"],
    },
)
async def get_decision_explanation_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """获取决策解释"""
    decision_id = input_data.get("decision_id")
    content_id = input_data.get("content_id")

    # 占位实现（实际应从追溯链中查询）
    return {
        "decision_id": decision_id,
        "agent_name": "AI 版主小安",
        "decision_type": "content_removal",
        "decision_steps": [
            {"step": "关键词检测", "result": "匹配 3 个垃圾广告关键词", "confidence": 0.85},
            {"step": "内容特征分析", "result": "包含 5 个外部链接", "confidence": 0.6},
            {"step": "用户历史考量", "result": "过去 24 小时发布 15 条内容", "confidence": 0.7},
        ],
        "final_decision": "remove",
        "confidence_score": 0.78,
        "reasoning": "综合风险分数 0.78，超过阈值 0.7，判定为垃圾内容",
        "appeal_url": f"/appeal/{decision_id}",
    }


@register_tool(
    name="generate_transparency_report",
    description="生成 AI 治理透明度报告。用于定期公示 AI 的决策统计。",
    input_schema={
        "type": "object",
        "properties": {
            "period_start": {"type": "string", "format": "date", "description": "报告开始日期"},
            "period_end": {"type": "string", "format": "date", "description": "报告结束日期"},
            "agent_id": {"type": "string", "description": "可选的特定 Agent ID"},
        },
        "required": ["period_start", "period_end"],
    },
)
async def generate_transparency_report_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """生成透明度报告"""
    period_start = input_data.get("period_start")
    period_end = input_data.get("period_end")
    agent_id = input_data.get("agent_id")

    # 占位实现
    return {
        "report_id": f"report_{period_start}_{period_end}",
        "period": {"start": period_start, "end": period_end},
        "total_decisions": 156,
        "decision_distribution": {
            "approved": 98,
            "flagged": 42,
            "removed": 16,
        },
        "average_confidence": 0.82,
        "appeal_count": 5,
        "appeal_success_rate": 0.2,
        "ai_content_ratio": 0.42,
    }


# ==================== 初始化时注册所有工具 ====================

def initialize_tools():
    """初始化工具注册表（装饰器已自动注册）"""
    logger.info(f"Initialized {len(TOOLS_REGISTRY)} tools")
    return TOOLS_REGISTRY


# 自动初始化
initialize_tools()
