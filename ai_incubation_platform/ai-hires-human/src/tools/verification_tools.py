"""
验证工具集 - 供 AI Agent 调用的验证和反作弊工具
"""
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def verify_delivery(
    task_id: str,
    content: str,
    attachments: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    验证交付物质量

    Args:
        task_id: 任务 ID
        content: 交付内容
        attachments: 附件列表

    Returns:
        验证结果（包含置信度）
    """
    from database import AsyncSessionLocal
    from models.db_models import TaskDB
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            # 获取任务详情
            result = await db.execute(select(TaskDB).where(TaskDB.id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                return {
                    "verified": False,
                    "error": f"任务 {task_id} 不存在"
                }

            # 基础验证
            verification_result = {
                "task_id": task_id,
                "verified": True,
                "checks": {}
            }

            # 1. 内容长度检查
            content_length = len(content) if content else 0
            min_expected = 50  # 最小期望长度
            length_ok = content_length >= min_expected
            verification_result["checks"]["content_length"] = {
                "passed": length_ok,
                "actual": content_length,
                "expected_min": min_expected
            }

            # 2. 内容重复性检查（与任务描述比较）
            if task.description:
                content_hash = hashlib.md5(content.encode()).hexdigest()
                desc_hash = hashlib.md5(task.description.encode()).hexdigest()
                is_duplicate = content_hash == desc_hash
                verification_result["checks"]["duplicate_content"] = {
                    "passed": not is_duplicate,
                    "is_duplicate": is_duplicate
                }

            # 3. 关键词匹配检查（验收标准）
            acceptance_criteria = task.acceptance_criteria or []
            if acceptance_criteria:
                matched_criteria = []
                for criterion in acceptance_criteria:
                    if str(criterion).lower() in content.lower():
                        matched_criteria.append(criterion)

                criteria_match_rate = len(matched_criteria) / len(acceptance_criteria)
                verification_result["checks"]["acceptance_criteria"] = {
                    "passed": criteria_match_rate >= 0.5,
                    "matched": matched_criteria,
                    "total": len(acceptance_criteria),
                    "match_rate": round(criteria_match_rate, 2)
                }

            # 4. 附件检查（如果有要求）
            if attachments is not None:
                verification_result["checks"]["attachments"] = {
                    "passed": True,
                    "count": len(attachments)
                }

            # 计算整体置信度
            passed_checks = sum(1 for check in verification_result["checks"].values() if check.get("passed", False))
            total_checks = len(verification_result["checks"])
            confidence = passed_checks / total_checks if total_checks > 0 else 0.5

            verification_result["confidence"] = round(confidence, 2)
            verification_result["passed"] = confidence >= 0.6

            return verification_result

    except Exception as e:
        logger.error(f"Failed to verify delivery: {e}")
        return {
            "verified": False,
            "error": str(e)
        }


async def check_anti_cheat(
    task_id: str,
    worker_id: str,
    content: str
) -> Dict[str, Any]:
    """
    反作弊检查

    Args:
        task_id: 任务 ID
        worker_id: 工人 ID
        content: 交付内容

    Returns:
        检查结果
    """
    from database import AsyncSessionLocal
    from models.db_models import TaskDB
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            # 获取任务
            result = await db.execute(select(TaskDB).where(TaskDB.id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                return {
                    "cheat_detected": False,
                    "error": f"任务 {task_id} 不存在"
                }

            cheat_checks = {
                "task_id": task_id,
                "worker_id": worker_id,
                "cheat_detected": False,
                "checks": {}
            }

            # 1. 频繁提交检查
            now = datetime.now()
            if task.last_submitted_at:
                time_diff = now - task.last_submitted_at.replace(tzinfo=None) if task.last_submitted_at.tzinfo else now - task.last_submitted_at
                if time_diff < timedelta(minutes=1):
                    cheat_checks["checks"]["frequent_submission"] = {
                        "passed": False,
                        "message": "提交过于频繁",
                        "time_diff_seconds": time_diff.total_seconds()
                    }
                    cheat_checks["cheat_detected"] = True
                else:
                    cheat_checks["checks"]["frequent_submission"] = {
                        "passed": True,
                        "time_diff_seconds": time_diff.total_seconds()
                    }

            # 2. 重复内容检查
            if task.delivery_content:
                current_hash = hashlib.md5(content.encode()).hexdigest()
                previous_hash = task.delivery_content_hash
                if current_hash == previous_hash:
                    cheat_checks["checks"]["duplicate_delivery"] = {
                        "passed": False,
                        "message": "交付内容重复"
                    }
                    cheat_checks["cheat_detected"] = True
                else:
                    cheat_checks["checks"]["duplicate_delivery"] = {
                        "passed": True
                    }

            # 3. 提交次数检查
            if task.submission_count >= 5:
                cheat_checks["checks"]["excessive_submissions"] = {
                    "passed": False,
                    "message": f"提交次数过多：{task.submission_count}"
                }
                cheat_checks["cheat_detected"] = True
            else:
                cheat_checks["checks"]["excessive_submissions"] = {
                    "passed": True,
                    "count": task.submission_count
                }

            return cheat_checks

    except Exception as e:
        logger.error(f"Failed to check anti-cheat: {e}")
        return {
            "cheat_detected": False,
            "error": str(e)
        }


async def approve_task(
    task_id: str,
    reason: str = ""
) -> Dict[str, Any]:
    """
    批准任务完成

    Args:
        task_id: 任务 ID
        reason: 批准原因

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

            if task.status != "review":
                return {
                    "success": False,
                    "message": f"任务状态为 {task.status}，不可批准"
                }

            stmt = update(TaskDB).where(TaskDB.id == task_id).values(
                status="completed",
                review_reason=reason,
                updated_at=datetime.now()
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"Task {task_id} approved: {reason}")

            return {
                "success": True,
                "message": "任务已批准完成",
                "task_id": task_id
            }

    except Exception as e:
        logger.error(f"Failed to approve task: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def reject_task(
    task_id: str,
    reason: str
) -> Dict[str, Any]:
    """
    拒绝任务交付

    Args:
        task_id: 任务 ID
        reason: 拒绝原因

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

            if task.status != "review":
                return {
                    "success": False,
                    "message": f"任务状态为 {task.status}，不可拒绝"
                }

            stmt = update(TaskDB).where(TaskDB.id == task_id).values(
                status="in_progress",
                review_reason=reason,
                worker_id=None,  # 释放工人
                updated_at=datetime.now()
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"Task {task_id} rejected: {reason}")

            return {
                "success": True,
                "message": "任务已拒绝，重新开放接单",
                "task_id": task_id
            }

    except Exception as e:
        logger.error(f"Failed to reject task: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def request_manual_review(
    task_id: str,
    reason: str,
    reviewer_id: str = "system"
) -> Dict[str, Any]:
    """
    请求人工复核

    Args:
        task_id: 任务 ID
        reason: 请求原因
        reviewer_id: 审核人 ID

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

            stmt = update(TaskDB).where(TaskDB.id == task_id).values(
                status="manual_review",
                review_reason=reason,
                reviewer_id=reviewer_id,
                updated_at=datetime.now()
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"Task {task_id} requested manual review: {reason}")

            return {
                "success": True,
                "message": "已请求人工复核",
                "task_id": task_id,
                "reviewer_id": reviewer_id
            }

    except Exception as e:
        logger.error(f"Failed to request manual review: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_quality_score(task_id: str) -> Dict[str, Any]:
    """
    获取任务质量评分

    Args:
        task_id: 任务 ID

    Returns:
        质量评分详情
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
                    "success": False,
                    "message": f"任务 {task_id} 不存在"
                }

            # 计算质量分数
            quality_score = {
                "task_id": task_id,
                "scores": {}
            }

            # 1. 基于验收标准完成度
            acceptance_criteria = task.acceptance_criteria or []
            if acceptance_criteria:
                # 简化计算，实际应该对比交付内容
                quality_score["scores"]["criteria_completion"] = 0.8  # 默认 80%

            # 2. 基于提交质量（无作弊）
            quality_score["scores"]["submission_quality"] = 1.0 if not task.cheating_flag else 0.3

            # 3. 基于时效性
            if task.deadline and task.submitted_at:
                submitted_at = task.submitted_at.replace(tzinfo=None) if task.submitted_at.tzinfo else task.submitted_at
                deadline = task.deadline.replace(tzinfo=None) if task.deadline.tzinfo else task.deadline
                if submitted_at <= deadline:
                    quality_score["scores"]["timeliness"] = 1.0
                else:
                    quality_score["scores"]["timeliness"] = 0.5
            else:
                quality_score["scores"]["timeliness"] = 0.7

            # 计算总体分数
            scores = list(quality_score["scores"].values())
            overall_score = sum(scores) / len(scores) if scores else 0.5

            quality_score["overall_score"] = round(overall_score, 2)
            quality_score["level"] = (
                "excellent" if overall_score >= 0.9 else
                "good" if overall_score >= 0.7 else
                "fair" if overall_score >= 0.5 else "poor"
            )

            return {
                "success": True,
                "quality_score": quality_score
            }

    except Exception as e:
        logger.error(f"Failed to get quality score: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# 工具注册表
TOOLS_REGISTRY = {
    "verify_delivery": {
        "name": "verify_delivery",
        "description": "验证任务交付物的质量和完整性，返回置信度评分",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"},
                "content": {"type": "string", "description": "交付内容"},
                "attachments": {"type": "array", "items": {"type": "string"}, "description": "附件列表"}
            },
            "required": ["task_id", "content"]
        },
        "handler": verify_delivery
    },
    "check_anti_cheat": {
        "name": "check_anti_cheat",
        "description": "执行反作弊检查，检测频繁提交、重复内容等作弊行为",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"},
                "worker_id": {"type": "string", "description": "工人 ID"},
                "content": {"type": "string", "description": "交付内容"}
            },
            "required": ["task_id", "worker_id", "content"]
        },
        "handler": check_anti_cheat
    },
    "approve_task": {
        "name": "approve_task",
        "description": "批准任务完成，将任务状态设为 completed",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"},
                "reason": {"type": "string", "description": "批准原因"}
            },
            "required": ["task_id"]
        },
        "handler": approve_task
    },
    "reject_task": {
        "name": "reject_task",
        "description": "拒绝任务交付，将任务重新开放给其他工人",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"},
                "reason": {"type": "string", "description": "拒绝原因"}
            },
            "required": ["task_id", "reason"]
        },
        "handler": reject_task
    },
    "request_manual_review": {
        "name": "request_manual_review",
        "description": "请求人工复核任务，当 AI 无法确定验收结果时使用",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"},
                "reason": {"type": "string", "description": "请求原因"},
                "reviewer_id": {"type": "string", "description": "审核人 ID"}
            },
            "required": ["task_id", "reason"]
        },
        "handler": request_manual_review
    },
    "get_quality_score": {
        "name": "get_quality_score",
        "description": "获取任务的质量评分，包括多个维度的评估",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务 ID"}
            },
            "required": ["task_id"]
        },
        "handler": get_quality_score
    }
}
