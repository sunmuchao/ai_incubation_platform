"""
日志记录工具

用于记录匹配操作历史，支持审计和追踪。
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from db.database import get_db
from db.repositories import MatchHistoryRepository
from utils.logger import logger


class LoggingTool:
    """
    日志记录工具

    功能：
    - 记录匹配操作历史
    - 记录用户行为日志
    - 支持审计查询
    """

    name = "log_record"
    description = "记录匹配操作历史和用户行为日志"
    tags = ["logging", "audit", "history"]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["match", "view", "like", "pass", "date_proposal"]
                },
                "target_user_id": {
                    "type": "string",
                    "description": "目标用户 ID（可选）"
                },
                "score": {
                    "type": "number",
                    "description": "匹配度分数（可选）"
                },
                "metadata": {
                    "type": "object",
                    "description": "额外元数据"
                }
            },
            "required": ["user_id", "action"]
        }

    @staticmethod
    def handle(
        user_id: str,
        action: str,
        target_user_id: Optional[str] = None,
        score: Optional[float] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        处理日志记录请求

        Args:
            user_id: 用户 ID
            action: 操作类型
            target_user_id: 目标用户 ID
            score: 匹配度分数
            metadata: 额外元数据

        Returns:
            记录结果
        """
        logger.info(f"LoggingTool: Recording action={action} for user={user_id}, target={target_user_id}")

        try:
            # 构造日志记录
            log_entry = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "action": action,
                "target_user_id": target_user_id,
                "score": score,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }

            # 如果是匹配操作，记录到匹配历史表
            if action == "match" and target_user_id and score is not None:
                try:
                    db = next(get_db())
                    match_repo = MatchHistoryRepository(db)

                    # 检查是否已存在记录
                    existing = match_repo.get_mutual_matches(user_id, target_user_id)
                    if not existing:
                        match_repo.create({
                            "id": log_entry["id"],
                            "user_id_1": user_id,
                            "user_id_2": target_user_id,
                            "compatibility_score": score,
                            "status": "pending"
                        })
                        logger.info(f"LoggingTool: Match history recorded: {log_entry['id']}")
                    else:
                        logger.info(f"LoggingTool: Match history already exists")

                except Exception as e:
                    logger.warning(f"LoggingTool: Failed to record to DB: {e}")
                    # 非致命错误，继续记录到内存日志

            # 记录到内存日志（用于临时存储和调试）
            LoggingTool._append_to_memory_log(log_entry)

            return {
                "success": True,
                "log_id": log_entry["id"],
                "timestamp": log_entry["timestamp"]
            }

        except Exception as e:
            logger.error(f"LoggingTool: Failed to record log: {e}")
            return {"error": str(e)}

    # 内存日志存储（用于测试和临时存储）
    _memory_logs: list = []

    @classmethod
    def _append_to_memory_log(cls, entry: dict) -> None:
        """添加到内存日志"""
        cls._memory_logs.append(entry)
        # 限制内存日志数量
        if len(cls._memory_logs) > 1000:
            cls._memory_logs = cls._memory_logs[-500:]

    @classmethod
    def get_logs(cls, user_id: str, limit: int = 50) -> list:
        """
        获取用户的日志记录

        Args:
            user_id: 用户 ID
            limit: 返回数量上限

        Returns:
            日志记录列表
        """
        return [
            log for log in cls._memory_logs
            if log.get("user_id") == user_id
        ][-limit:]

    @staticmethod
    def get_history(user_id: str, action_type: Optional[str] = None) -> dict:
        """
        获取用户匹配历史

        Args:
            user_id: 用户 ID
            action_type: 操作类型过滤

        Returns:
            匹配历史数据
        """
        try:
            db = next(get_db())
            match_repo = MatchHistoryRepository(db)

            matches = match_repo.get_by_user(user_id)
            result = []
            for match in matches:
                result.append({
                    "id": match.id,
                    "partner_id": match.user_id_2 if match.user_id_1 == user_id else match.user_id_1,
                    "score": match.compatibility_score,
                    "status": match.status,
                    "created_at": match.created_at.isoformat() if match.created_at else None
                })

            return {"history": result, "total": len(result)}

        except Exception as e:
            logger.error(f"LoggingTool: Failed to get history: {e}")
            return {"error": str(e)}
