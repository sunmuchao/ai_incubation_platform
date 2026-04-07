"""
任务工具集 - 供 AI Agent 调用的任务相关工具
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def post_task(
    ai_employer_id: str,
    title: str,
    description: str,
    capability_gap: str = "",
    interaction_type: str = "digital",
    required_skills: Optional[Dict[str, str]] = None,
    priority: str = "medium",
    location_hint: Optional[str] = None,
    reward_amount: float = 100.0,
    reward_currency: str = "CNY",
    deadline: Optional[str] = None,
    acceptance_criteria: Optional[List[str]] = None,
    callback_url: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    发布任务到平台

    Args:
        ai_employer_id: AI 雇主 ID
        title: 任务标题
        description: 任务描述
        capability_gap: AI 能力缺口说明
        interaction_type: 交互类型 (digital/physical/hybrid)
        required_skills: 所需技能
        priority: 优先级 (low/medium/high/urgent)
        location_hint: 地点提示
        reward_amount: 报酬金额
        reward_currency: 报酬货币
        deadline: 截止时间
        acceptance_criteria: 验收标准
        callback_url: 回调 URL

    Returns:
        {"task_id": str, "status": str, "message": str}
    """
    from database import AsyncSessionLocal
    from models.db_models import TaskDB
    from sqlalchemy import insert

    try:
        async with AsyncSessionLocal() as db:
            import uuid
            task_id = str(uuid.uuid4())

            # 准备数据
            task_data = {
                "id": task_id,
                "ai_employer_id": ai_employer_id,
                "title": title,
                "description": description,
                "capability_gap": capability_gap or "AI 无法完成此类任务，需要真人协助",
                "interaction_type": interaction_type,
                "required_skills": required_skills or {},
                "priority": priority,
                "location_hint": location_hint,
                "reward_amount": reward_amount,
                "reward_currency": reward_currency,
                "acceptance_criteria": acceptance_criteria or [],
                "requirements": kwargs.get("requirements", []),
                "callback_url": callback_url,
                "status": "published",
            }

            if deadline:
                try:
                    task_data["deadline"] = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                except ValueError:
                    pass

            # 插入数据库
            stmt = insert(TaskDB).values(**task_data)
            await db.execute(stmt)
            await db.commit()

            logger.info(f"Task created: {task_id} by {ai_employer_id}")

            return {
                "task_id": task_id,
                "status": "published",
                "message": f"任务 '{title}' 已成功发布",
                "task_url": f"/api/tasks/{task_id}"
            }

    except Exception as e:
        logger.error(f"Failed to post task: {e}")
        return {
            "task_id": None,
            "status": "error",
            "message": str(e)
        }


async def get_task(task_id: str) -> Dict[str, Any]:
    """
    获取任务详情

    Args:
        task_id: 任务 ID

    Returns:
        任务详情
    """
    from database import AsyncSessionLocal
    from models.db_models import TaskDB
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(TaskDB).where(TaskDB.id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                return {
                    "found": False,
                    "message": f"任务 {task_id} 不存在"
                }

            return {
                "found": True,
                "task": {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "reward_amount": task.reward_amount,
                    "worker_id": task.worker_id,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                }
            }

    except Exception as e:
        logger.error(f"Failed to get task: {e}")
        return {
            "found": False,
            "error": str(e)
        }


async def search_tasks(
    keyword: Optional[str] = None,
    interaction_type: Optional[str] = None,
    min_reward: float = 0,
    max_reward: Optional[float] = None,
    priority: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    搜索任务

    Args:
        keyword: 关键词
        interaction_type: 交互类型
        min_reward: 最低报酬
        max_reward: 最高报酬
        priority: 优先级
        location: 地点
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        任务列表
    """
    from database import AsyncSessionLocal
    from models.db_models import TaskDB
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            query = select(TaskDB).where(TaskDB.status == "published")

            if keyword:
                # SQLite 不支持 LIKE 的全文搜索，这里简化处理
                query = query.where(
                    (TaskDB.title.contains(keyword)) |
                    (TaskDB.description.contains(keyword))
                )

            if interaction_type:
                query = query.where(TaskDB.interaction_type == interaction_type)

            if priority:
                query = query.where(TaskDB.priority == priority)

            if location:
                query = query.where(TaskDB.location_hint.contains(location))

            query = query.where(TaskDB.reward_amount >= min_reward)
            if max_reward:
                query = query.where(TaskDB.reward_amount <= max_reward)

            query = query.offset(offset).limit(limit)

            result = await db.execute(query)
            tasks = result.scalars().all()

            return {
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "description": t.description[:200] + "..." if len(t.description) > 200 else t.description,
                        "reward_amount": t.reward_amount,
                        "priority": t.priority,
                        "interaction_type": t.interaction_type,
                        "location_hint": t.location_hint,
                    }
                    for t in tasks
                ],
                "total": len(tasks),
                "limit": limit,
                "offset": offset
            }

    except Exception as e:
        logger.error(f"Failed to search tasks: {e}")
        return {
            "tasks": [],
            "error": str(e)
        }


async def cancel_task(task_id: str, operator_id: str, reason: str = "") -> Dict[str, Any]:
    """
    取消任务

    Args:
        task_id: 任务 ID
        operator_id: 操作人 ID
        reason: 取消原因

    Returns:
        操作结果
    """
    from database import AsyncSessionLocal
    from models.db_models import TaskDB
    from sqlalchemy import select, update

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(TaskDB).where(TaskDB.id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                return {
                    "success": False,
                    "message": f"任务 {task_id} 不存在"
                }

            if task.status in ["completed", "cancelled"]:
                return {
                    "success": False,
                    "message": f"任务状态为 {task.status}，不可取消"
                }

            stmt = update(TaskDB).where(TaskDB.id == task_id).values(
                status="cancelled",
                review_reason=reason,
                reviewer_id=operator_id,
                updated_at=datetime.now()
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"Task {task_id} cancelled by {operator_id}")

            return {
                "success": True,
                "message": "任务已取消",
                "task_id": task_id
            }

    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_task_stats(ai_employer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    获取任务统计信息

    Args:
        ai_employer_id: 可选的 AI 雇主 ID 用于筛选

    Returns:
        统计数据
    """
    from database import AsyncSessionLocal
    from models.db_models import TaskDB
    from sqlalchemy import select, func

    try:
        async with AsyncSessionLocal() as db:
            query = select(TaskDB.status, func.count(TaskDB.id).label('count'))

            if ai_employer_id:
                query = query.where(TaskDB.ai_employer_id == ai_employer_id)

            query = query.group_by(TaskDB.status)
            result = await db.execute(query)
            rows = result.all()

            stats = {
                "total": sum(row.count for row in rows),
                "by_status": {row.status: row.count for row in rows}
            }

            return {
                "success": True,
                "stats": stats
            }

    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# 工具注册表
TOOLS_REGISTRY = {
    "post_task": {
        "name": "post_task",
        "description": "发布新任务到 AI 雇佣真人平台，当 AI 无法独立完成时雇佣真人执行",
        "input_schema": {
            "type": "object",
            "properties": {
                "ai_employer_id": {"type": "string", "description": "AI 雇主 ID"},
                "title": {"type": "string", "description": "任务标题"},
                "description": {"type": "string", "description": "任务详细描述"},
                "capability_gap": {"type": "string", "description": "AI 无法完成的原因"},
                "interaction_type": {"type": "string", "enum": ["digital", "physical", "hybrid"], "description": "交互类型"},
                "required_skills": {"type": "object", "additionalProperties": {"type": "string"}, "description": "所需技能"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "description": "优先级"},
                "location_hint": {"type": "string", "description": "地点提示（线下任务）"},
                "reward_amount": {"type": "number", "description": "报酬金额"},
                "reward_currency": {"type": "string", "description": "报酬货币"},
                "deadline": {"type": "string", "format": "date-time", "description": "截止时间"},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "description": "验收标准列表"},
                "callback_url": {"type": "string", "description": "验收后回调 URL"}
            },
            "required": ["ai_employer_id", "title", "description"]
        },
        "handler": post_task
    },
    "get_task": {
        "name": "get_task",
        "description": "获取指定任务的详细信息",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"}
            },
            "required": ["task_id"]
        },
        "handler": get_task
    },
    "search_tasks": {
        "name": "search_tasks",
        "description": "搜索平台上的任务，支持多维度筛选",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
                "interaction_type": {"type": "string", "enum": ["digital", "physical", "hybrid"], "description": "交互类型"},
                "min_reward": {"type": "number", "description": "最低报酬"},
                "max_reward": {"type": "number", "description": "最高报酬"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "description": "优先级"},
                "location": {"type": "string", "description": "地点"},
                "limit": {"type": "integer", "default": 20, "description": "返回数量限制"},
                "offset": {"type": "integer", "default": 0, "description": "偏移量"}
            }
        },
        "handler": search_tasks
    },
    "cancel_task": {
        "name": "cancel_task",
        "description": "取消已发布的任务",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"},
                "operator_id": {"type": "string", "description": "操作人 ID"},
                "reason": {"type": "string", "description": "取消原因"}
            },
            "required": ["task_id", "operator_id"]
        },
        "handler": cancel_task
    },
    "get_task_stats": {
        "name": "get_task_stats",
        "description": "获取任务统计数据",
        "input_schema": {
            "type": "object",
            "properties": {
                "ai_employer_id": {"type": "string", "description": "AI 雇主 ID（可选）"}
            }
        },
        "handler": get_task_stats
    }
}
