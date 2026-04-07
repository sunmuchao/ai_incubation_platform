"""
工人工具集 - 供 AI Agent 调用的工人相关工具
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def search_workers(
    skills: Optional[str] = None,
    location: Optional[str] = None,
    min_level: int = 0,
    min_rating: float = 0.0,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    搜索工人

    Args:
        skills: 技能标签，逗号分隔
        location: 地点
        min_level: 最低等级
        min_rating: 最低评分
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        工人列表
    """
    from database import AsyncSessionLocal
    from models.db_models import WorkerProfileDB
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            query = select(WorkerProfileDB)

            if location:
                query = query.where(WorkerProfileDB.location.contains(location))

            if min_level > 0:
                query = query.where(WorkerProfileDB.level >= min_level)

            if min_rating > 0:
                query = query.where(WorkerProfileDB.average_rating >= min_rating)

            query = query.offset(offset).limit(limit)

            result = await db.execute(query)
            workers = result.scalars().all()

            # 技能过滤（在内存中进行，因为技能是 JSON 字段）
            if skills:
                skill_list = [s.strip().lower() for s in skills.split(",")]
                filtered_workers = []
                for w in workers:
                    worker_skills = w.skills or {}
                    skill_names = [k.lower() for k in worker_skills.keys()]
                    if any(s in skill_names or any(s in str(v).lower() for v in worker_skills.values()) for s in skill_list):
                        filtered_workers.append(w)
                workers = filtered_workers

            return {
                "workers": [
                    {
                        "id": w.worker_id,
                        "name": w.name,
                        "skills": w.skills,
                        "level": w.level,
                        "rating": w.average_rating,
                        "completed_tasks": w.completed_tasks,
                        "location": w.location,
                        "success_rate": w.success_rate,
                    }
                    for w in workers
                ],
                "total": len(workers),
                "limit": limit,
                "offset": offset
            }

    except Exception as e:
        logger.error(f"Failed to search workers: {e}")
        return {
            "workers": [],
            "error": str(e)
        }


async def get_worker_profile(worker_id: str) -> Dict[str, Any]:
    """
    获取工人详细画像

    Args:
        worker_id: 工人 ID

    Returns:
        工人详情
    """
    from database import AsyncSessionLocal
    from models.db_models import WorkerProfileDB
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(WorkerProfileDB).where(WorkerProfileDB.worker_id == worker_id))
            worker = result.scalar_one_or_none()

            if not worker:
                return {
                    "found": False,
                    "message": f"工人 {worker_id} 不存在"
                }

            return {
                "found": True,
                "worker": {
                    "id": worker.worker_id,
                    "name": worker.name,
                    "email": worker.email,
                    "skills": worker.skills,
                    "level": worker.level,
                    "rating": worker.average_rating,
                    "completed_tasks": worker.completed_tasks,
                    "total_earnings": worker.total_earnings,
                    "location": worker.location,
                    "success_rate": worker.success_rate,
                    "joined_at": worker.created_at.isoformat() if worker.created_at else None,
                }
            }

    except Exception as e:
        logger.error(f"Failed to get worker profile: {e}")
        return {
            "found": False,
            "error": str(e)
        }


async def match_workers(
    task_id: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    为任务匹配工人

    Args:
        task_id: 任务 ID
        limit: 返回匹配数量

    Returns:
        匹配的工人列表（带置信度）
    """
    from database import AsyncSessionLocal
    from models.db_models import TaskDB, WorkerProfileDB
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            # 获取任务详情
            result = await db.execute(select(TaskDB).where(TaskDB.id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                return {
                    "matches": [],
                    "error": f"任务 {task_id} 不存在"
                }

            # 获取所有可用工人
            workers_result = await db.execute(select(WorkerProfileDB))
            workers = workers_result.scalars().all()

            # 计算匹配度
            matches = []
            task_skills = set(k.lower() for k in (task.required_skills or {}).keys())
            task_location = (task.location_hint or "").lower()

            for worker in workers:
                # 技能匹配分数
                worker_skills = set(k.lower() for k in (worker.skills or {}).keys())
                skill_overlap = len(task_skills & worker_skills)
                skill_score = skill_overlap / len(task_skills) if task_skills else 0.5

                # 地点匹配分数
                location_score = 0.0
                if task_location:
                    if task_location in (worker.location or "").lower():
                        location_score = 1.0
                else:
                    location_score = 0.5  # 无地点要求时给中等分数

                # 评分和等级分数
                rating_score = worker.average_rating / 5.0 if worker.average_rating else 0.5
                level_score = min(worker.level / 10.0, 1.0) if worker.level else 0.5

                # 综合置信度
                confidence = (
                    skill_score * 0.4 +
                    location_score * 0.2 +
                    rating_score * 0.25 +
                    level_score * 0.15
                )

                matches.append({
                    "worker_id": worker.worker_id,
                    "worker_name": worker.name or worker.worker_id,
                    "confidence": round(confidence, 3),
                    "skill_match": round(skill_score, 3),
                    "location_match": round(location_score, 3),
                    "rating": worker.average_rating,
                    "level": worker.level,
                    "completed_tasks": worker.completed_tasks,
                })

            # 按置信度排序
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            matches = matches[:limit]

            return {
                "task_id": task_id,
                "matches": matches,
                "total_candidates": len(workers)
            }

    except Exception as e:
        logger.error(f"Failed to match workers: {e}")
        return {
            "matches": [],
            "error": str(e)
        }


async def assign_worker(
    task_id: str,
    worker_id: str,
    auto_assigned: bool = False
) -> Dict[str, Any]:
    """
    为任务分配工人

    Args:
        task_id: 任务 ID
        worker_id: 工人 ID
        auto_assigned: 是否自动分配

    Returns:
        分配结果
    """
    from database import AsyncSessionLocal
    from models.db_models import TaskDB
    from sqlalchemy import select, update
    from datetime import datetime

    try:
        async with AsyncSessionLocal() as db:
            # 获取任务
            result = await db.execute(select(TaskDB).where(TaskDB.id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                return {
                    "success": False,
                    "message": f"任务 {task_id} 不存在"
                }

            if task.status != "published":
                return {
                    "success": False,
                    "message": f"任务状态为 {task.status}，不可分配"
                }

            # 分配工人
            stmt = update(TaskDB).where(TaskDB.id == task_id).values(
                worker_id=worker_id,
                status="in_progress",
                updated_at=datetime.now()
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(
                f"Worker {worker_id} assigned to task {task_id}"
                f"{' (auto)' if auto_assigned else ''}"
            )

            return {
                "success": True,
                "message": f"工人 {worker_id} 已分配到任务",
                "task_id": task_id,
                "worker_id": worker_id,
                "auto_assigned": auto_assigned
            }

    except Exception as e:
        logger.error(f"Failed to assign worker: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_worker_stats(worker_id: Optional[str] = None) -> Dict[str, Any]:
    """
    获取工人统计信息

    Args:
        worker_id: 可选的工人 ID

    Returns:
        统计数据
    """
    from database import AsyncSessionLocal
    from models.db_models import WorkerProfileDB, TaskDB
    from sqlalchemy import select, func

    try:
        async with AsyncSessionLocal() as db:
            if worker_id:
                result = await db.execute(
                    select(WorkerProfileDB).where(WorkerProfileDB.worker_id == worker_id)
                )
                worker = result.scalar_one_or_none()

                if not worker:
                    return {
                        "success": False,
                        "message": f"工人 {worker_id} 不存在"
                    }

                # 获取该工人的任务统计
                task_query = select(TaskDB.status, func.count(TaskDB.id).label('count')).where(
                    TaskDB.worker_id == worker_id
                ).group_by(TaskDB.status)

                task_result = await db.execute(task_query)
                task_stats = {row.status: row.count for row in task_result.all()}

                return {
                    "success": True,
                    "worker_id": worker_id,
                    "profile": {
                        "name": worker.name,
                        "level": worker.level,
                        "rating": worker.average_rating,
                        "completed_tasks": worker.completed_tasks,
                    },
                    "task_stats": task_stats
                }
            else:
                # 平台整体统计
                total_workers_query = await db.execute(select(func.count(WorkerProfileDB.worker_id)))
                avg_rating_query = await db.execute(select(func.avg(WorkerProfileDB.average_rating)))

                return {
                    "success": True,
                    "platform_stats": {
                        "total_workers": total_workers_query.scalar() or 0,
                        "avg_rating": round(avg_rating_query.scalar() or 0, 2)
                    }
                }

    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# 工具注册表
TOOLS_REGISTRY = {
    "search_workers": {
        "name": "search_workers",
        "description": "搜索平台上的工人，支持技能、地点、等级、评分等筛选条件",
        "input_schema": {
            "type": "object",
            "properties": {
                "skills": {"type": "string", "description": "技能标签，逗号分隔"},
                "location": {"type": "string", "description": "地点"},
                "min_level": {"type": "integer", "default": 0, "description": "最低等级"},
                "min_rating": {"type": "number", "default": 0.0, "description": "最低评分"},
                "limit": {"type": "integer", "default": 20, "description": "返回数量限制"},
                "offset": {"type": "integer", "default": 0, "description": "偏移量"}
            }
        },
        "handler": search_workers
    },
    "get_worker_profile": {
        "name": "get_worker_profile",
        "description": "获取指定工人的详细画像信息",
        "input_schema": {
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "工人 ID"}
            },
            "required": ["worker_id"]
        },
        "handler": get_worker_profile
    },
    "match_workers": {
        "name": "match_workers",
        "description": "为指定任务智能匹配最合适的工人，返回带置信度的匹配列表",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"},
                "limit": {"type": "integer", "default": 10, "description": "返回匹配数量"}
            },
            "required": ["task_id"]
        },
        "handler": match_workers
    },
    "assign_worker": {
        "name": "assign_worker",
        "description": "为任务分配工人，支持 AI 自主分配",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"},
                "worker_id": {"type": "string", "description": "工人 ID"},
                "auto_assigned": {"type": "boolean", "default": False, "description": "是否自动分配"}
            },
            "required": ["task_id", "worker_id"]
        },
        "handler": assign_worker
    },
    "get_worker_stats": {
        "name": "get_worker_stats",
        "description": "获取工人或平台整体的统计信息",
        "input_schema": {
            "type": "object",
            "properties": {
                "worker_id": {"type": "string", "description": "工人 ID（可选）"}
            }
        },
        "handler": get_worker_stats
    }
}
