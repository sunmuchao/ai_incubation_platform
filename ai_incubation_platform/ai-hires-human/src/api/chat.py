"""
对话式 API - 自然语言交互端点
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """对话消息请求体"""
    message: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """对话响应"""
    message: str
    action: str
    data: Optional[Dict[str, Any]] = None
    suggestions: list = []


@router.post("/", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    对话式交互端点

    用户可以用自然语言与平台交互，AI 将解析意图并执行相应操作
    """
    user_id = message.user_id or "anonymous"
    user_message = message.message
    context = message.context or {}

    logger.info(f"Chat message from {user_id}: {user_message[:100]}...")

    try:
        from agents.task_agent import task_agent

        # 解析用户意图
        intent = await _classify_intent(user_message)

        # 根据意图执行相应操作
        if intent["action"] == "post_task":
            result = await _handle_post_task(user_id, user_message, context)
        elif intent["action"] == "search_tasks":
            result = await _handle_search_tasks(user_message, context)
        elif intent["action"] == "search_workers":
            result = await _handle_search_workers(user_message, context)
        elif intent["action"] == "get_task_status":
            result = await _handle_get_task_status(user_message, context)
        elif intent["action"] == "match_workers":
            result = await _handle_match_workers(user_message, context)
        elif intent["action"] == "verify_delivery":
            result = await _handle_verify_delivery(user_message, context)
        elif intent["action"] == "get_stats":
            result = await _handle_get_stats(context)
        else:
            result = {
                "message": f"抱歉，我还不太理解您的需求：{user_message}。您可以尝试：\n"
                          "- 发布任务：'帮我发布一个线下采集任务，需要到北京现场拍照'\n"
                          "- 搜索任务：'查找报酬高于 100 元的任务'\n"
                          "- 搜索工人：'找会数据标注的工人'\n"
                          "- 查询状态：'查询任务 task-123 的状态'\n"
                          "- 匹配工人：'为任务 task-123 匹配合适的工人'\n"
                          "- 验收交付：'验收任务 task-123 的交付物'\n"
                          "- 查看统计：'查看平台统计数据'",
                "action": "help",
                "data": None,
                "suggestions": [
                    "发布一个线下采集任务",
                    "搜索数据标注相关的任务",
                    "找评分高的工人",
                    "查看我的任务状态"
                ]
            }

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _classify_intent(message: str) -> Dict[str, Any]:
    """
    分类用户意图

    使用关键词匹配和简单规则进行分类
    """
    message_lower = message.lower()

    # 发布任务相关
    if any(kw in message_lower for kw in ["发布", "创建", "新建", "post", "create"]):
        if any(kw in message_lower for kw in ["任务", "task"]):
            return {"action": "post_task", "confidence": 0.9}

    # 搜索任务相关
    if any(kw in message_lower for kw in ["搜索", "查找", "找任务", "search"]):
        if any(kw in message_lower for kw in ["任务", "task"]):
            return {"action": "search_tasks", "confidence": 0.9}

    # 搜索工人相关
    if any(kw in message_lower for kw in ["工人", "师傅", "接单", "worker"]):
        if any(kw in message_lower for kw in ["搜索", "查找", "找", "search"]):
            return {"action": "search_workers", "confidence": 0.8}

    # 查询任务状态
    if any(kw in message_lower for kw in ["状态", "进度", "status", "progress"]):
        if "task" in message_lower or "任务" in message_lower:
            return {"action": "get_task_status", "confidence": 0.85}

    # 匹配工人
    if any(kw in message_lower for kw in ["匹配", "推荐", "match", "recommend"]):
        if any(kw in message_lower for kw in ["工人", "师傅", "worker"]):
            return {"action": "match_workers", "confidence": 0.85}

    # 验收交付
    if any(kw in message_lower for kw in ["验收", "审核", "批准", "verify", "approve"]):
        if any(kw in message_lower for kw in ["交付", "提交", "delivery", "submit"]):
            return {"action": "verify_delivery", "confidence": 0.85}

    # 统计信息
    if any(kw in message_lower for kw in ["统计", "数据", "报表", "stats", "report"]):
        return {"action": "get_stats", "confidence": 0.8}

    return {"action": "unknown", "confidence": 0.5}


async def _handle_post_task(user_id: str, message: str, context: Dict) -> Dict:
    """处理发布任务意图"""
    from agents.task_agent import task_agent

    result = await task_agent.post_task_from_natural_language(
        user_id=user_id,
        natural_language=message,
        context=context
    )

    task_id = result.get("task_id")

    return {
        "message": f"任务已成功发布！任务 ID: {task_id}\n"
                  f"系统已自动为您匹配工人，请稍后查看匹配结果。",
        "action": "post_task",
        "data": result,
        "suggestions": [
            f"查看任务 {task_id} 的状态",
            f"为任务 {task_id} 匹配工人",
            "发布另一个任务"
        ]
    }


async def _handle_search_tasks(message: str, context: Dict) -> Dict:
    """处理搜索任务意图"""
    from tools.task_tools import search_tasks

    # 简单提取搜索参数
    import re

    # 提取报酬范围
    reward_match = re.search(r'(\d+)\s*(?:元 | 块)?(?:以上 | 以上)', message)
    min_reward = float(reward_match.group(1)) if reward_match else 0

    # 提取地点
    location_keywords = ["北京", "上海", "广州", "深圳", "杭州"]
    location = next((kw for kw in location_keywords if kw in message), None)

    # 提取交互类型
    interaction_type = None
    if "线下" in message or "实地" in message:
        interaction_type = "physical"
    elif "线上" in message or "远程" in message:
        interaction_type = "digital"

    result = await search_tasks(
        keyword=message,
        interaction_type=interaction_type,
        min_reward=min_reward,
        location=location,
        limit=10
    )

    tasks = result.get("tasks", [])

    if not tasks:
        return {
            "message": "未找到匹配的任务，您可以尝试调整搜索条件。",
            "action": "search_tasks",
            "data": {"tasks": [], "total": 0},
            "suggestions": ["放宽搜索条件", "发布新任务"]
        }

    task_list = "\n".join([
        f"- {t['title']} (报酬：{t['reward_amount']}元，优先级：{t['priority']})"
        for t in tasks[:5]
    ])

    return {
        "message": f"找到 {len(tasks)} 个匹配的任务：\n{task_list}",
        "action": "search_tasks",
        "data": result,
        "suggestions": [
            f"查看任务 {tasks[0]['id']} 的详情" if tasks else [],
            "查看更多任务"
        ]
    }


async def _handle_search_workers(message: str, context: Dict) -> Dict:
    """处理搜索工人意图"""
    from tools.worker_tools import search_workers

    # 提取技能
    skill_keywords = ["数据标注", "线下采集", "文案写作", "翻译", "客服", "拍照"]
    skills = next((kw for kw in skill_keywords if kw in message), None)

    # 提取地点
    location_keywords = ["北京", "上海", "广州", "深圳", "杭州"]
    location = next((kw for kw in location_keywords if kw in message), None)

    result = await search_workers(
        skills=skills,
        location=location,
        min_rating=4.0 if "高评分" in message or "优质" in message else 0,
        limit=10
    )

    workers = result.get("workers", [])

    if not workers:
        return {
            "message": "未找到匹配的工人，您可以尝试放宽搜索条件。",
            "action": "search_workers",
            "data": {"workers": [], "total": 0},
            "suggestions": ["放宽搜索条件", "降低评分要求"]
        }

    worker_list = "\n".join([
        f"- {w['name']} (评分：{w['rating']}, 等级：{w['level']}, 完成：{w['completed_tasks']}单)"
        for w in workers[:5]
    ])

    return {
        "message": f"找到 {len(workers)} 个匹配的工人：\n{worker_list}",
        "action": "search_workers",
        "data": result,
        "suggestions": [
            f"查看工人 {workers[0]['id']} 的详情" if workers else [],
            "查看更多工人"
        ]
    }


async def _handle_get_task_status(message: str, context: Dict) -> Dict:
    """处理查询任务状态意图"""
    from tools.task_tools import get_task

    # 提取任务 ID
    import re
    task_id_match = re.search(r'(task-[\w-]+|[\w-]{36})', message, re.IGNORECASE)
    task_id = task_id_match.group(1) if task_id_match else context.get("last_task_id")

    if not task_id:
        return {
            "message": "请提供任务 ID，例如：'查询任务 task-123 的状态'",
            "action": "get_task_status",
            "data": None,
            "suggestions": ["提供任务 ID"]
        }

    result = await get_task(task_id)

    if not result.get("found"):
        return {
            "message": f"未找到任务 {task_id}",
            "action": "get_task_status",
            "data": None,
            "suggestions": ["检查任务 ID 是否正确"]
        }

    task = result.get("task", {})

    return {
        "message": f"任务状态：{task.get('status')}\n"
                  f"标题：{task.get('title')}\n"
                  f"当前工人：{task.get('worker_id') or '暂无'}",
        "action": "get_task_status",
        "data": result,
        "suggestions": [
            "查看任务详情",
            "取消任务"
        ]
    }


async def _handle_match_workers(message: str, context: Dict) -> Dict:
    """处理匹配工人意图"""
    import re
    from tools.worker_tools import match_workers

    # 提取任务 ID
    task_id_match = re.search(r'(task-[\w-]+|[\w-]{36})', message, re.IGNORECASE)
    task_id = task_id_match.group(1) if task_id_match else context.get("last_task_id")

    if not task_id:
        return {
            "message": "请提供任务 ID，例如：'为任务 task-123 匹配工人'",
            "action": "match_workers",
            "data": None,
            "suggestions": ["提供任务 ID"]
        }

    result = await match_workers(task_id=task_id, limit=5)

    matches = result.get("matches", [])

    if not matches:
        return {
            "message": f"未找到适合任务 {task_id} 的工人",
            "action": "match_workers",
            "data": result,
            "suggestions": ["调整任务要求", "提高报酬"]
        }

    match_list = "\n".join([
        f"- {m['worker_name']} (匹配度：{m['confidence']*100:.0f}%, 评分：{m['rating']})"
        for m in matches[:5]
    ])

    auto_assign_suggestion = ""
    if matches[0]["confidence"] >= 0.8:
        auto_assign_suggestion = f"\n建议自动分配给 {matches[0]['worker_name']}（匹配度超过 80%）"

    return {
        "message": f"为任务 {task_id} 匹配的工人：\n{match_list}{auto_assign_suggestion}",
        "action": "match_workers",
        "data": result,
        "suggestions": [
            f"分配给 {matches[0]['worker_name']}" if matches else [],
            "查看更多匹配"
        ]
    }


async def _handle_verify_delivery(message: str, context: Dict) -> Dict:
    """处理验收交付意图"""
    import re
    from tools.verification_tools import verify_delivery

    # 提取任务 ID
    task_id_match = re.search(r'(task-[\w-]+|[\w-]{36})', message, re.IGNORECASE)
    task_id = task_id_match.group(1) if task_id_match else context.get("last_task_id")

    if not task_id:
        return {
            "message": "请提供任务 ID，例如：'验收任务 task-123 的交付物'",
            "action": "verify_delivery",
            "data": None,
            "suggestions": ["提供任务 ID"]
        }

    # 这里简化处理，实际应该获取交付内容
    result = await verify_delivery(
        task_id=task_id,
        content=context.get("delivery_content", "")
    )

    if result.get("passed"):
        return {
            "message": f"交付物验证通过！置信度：{result.get('confidence', 0)*100:.0f}%",
            "action": "verify_delivery",
            "data": result,
            "suggestions": ["批准任务完成", "查看详细验证报告"]
        }
    else:
        return {
            "message": f"交付物验证未通过，需要进一步检查。\n"
                      f"置信度：{result.get('confidence', 0)*100:.0f}%",
            "action": "verify_delivery",
            "data": result,
            "suggestions": ["请求人工复核", "查看详细验证报告"]
        }


async def _handle_get_stats(context: Dict) -> Dict:
    """处理查看统计意图"""
    from tools.task_tools import get_task_stats
    from tools.worker_tools import get_worker_stats

    task_stats = await get_task_stats()
    worker_stats = await get_worker_stats()

    task_data = task_stats.get("stats", {})
    worker_data = worker_stats.get("platform_stats", {})

    return {
        "message": f"平台统计数据：\n"
                  f"- 总任务数：{task_data.get('total', 0)}\n"
                  f"- 总工人数：{worker_data.get('total_workers', 0)}\n"
                  f"- 工人平均评分：{worker_data.get('avg_rating', 0)}",
        "action": "get_stats",
        "data": {
            "task_stats": task_data,
            "worker_stats": worker_data
        },
        "suggestions": [
            "查看详细报表",
            "查看我的任务统计"
        ]
    }


@router.get("/history")
async def get_chat_history(user_id: Optional[str] = None):
    """获取对话历史"""
    # 简化实现，实际应该从数据库获取
    return {
        "history": [],
        "user_id": user_id
    }


@router.delete("/history")
async def clear_chat_history(user_id: Optional[str] = None):
    """清除对话历史"""
    return {
        "message": "对话历史已清除",
        "user_id": user_id
    }
