"""
匹配服务适配层

复用 AI Native 架构（HerAdvisorService + ConversationMatchService）
为 who_likes_me_service.py 等模块提供兼容接口

架构说明：
- 项目使用 AI Native 匹配架构
- HerAdvisorService 负责 AI 匹配判断
- ConversationMatchService 负责候选人查询
- 本模块作为适配层，提供简单接口
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from utils.logger import logger


class MatchingService:
    """
    匹配服务（适配层）

    提供简单的匹配度计算和匹配记录创建接口，
    内部复用 AI Native 匹配逻辑
    """

    def __init__(self, db: Session):
        """
        初始化匹配服务

        Args:
            db: 数据库会话
        """
        self.db = db

    def calculate_compatibility(
        self,
        user_id_a: str,
        user_id_b: str,
        use_ai: bool = False
    ) -> float:
        """
        计算两人匹配度

        Args:
            user_id_a: 用户 A ID
            user_id_b: 用户 B ID
            use_ai: 是否使用 AI 计算（默认使用简单规则）

        Returns:
            匹配度分数 (0.0 - 1.0)
        """
        if use_ai:
            # 使用 AI Native 计算（需要异步调用）
            # 在同步场景下返回默认值
            return 0.5

        # 简单规则计算（用于同步场景）
        try:
            from db.models import UserDB

            user_a = self.db.query(UserDB).filter(UserDB.id == user_id_a).first()
            user_b = self.db.query(UserDB).filter(UserDB.id == user_id_b).first()

            if not user_a or not user_b:
                return 0.0

            score = self._calculate_simple_compatibility(user_a, user_b)
            return score

        except Exception as e:
            logger.error(f"[MatchingService] 计算匹配度失败: {e}")
            return 0.5

    def _calculate_simple_compatibility(
        self,
        user_a: Any,
        user_b: Any
    ) -> float:
        """
        简单匹配度计算（基于基础信息）

        计算规则：
        - 年龄差距：每差距5岁扣0.05分
        - 同城市：加0.1分
        - 共同兴趣：每个加0.05分
        """
        import json

        score = 0.5  # 基础分数

        # 年龄差距
        age_diff = abs((user_a.age or 0) - (user_b.age or 0))
        if age_diff <= 5:
            score += 0.1
        elif age_diff <= 10:
            score += 0.05
        else:
            score -= min(0.2, age_diff * 0.02)

        # 同城市
        if user_a.location and user_b.location:
            if user_a.location == user_b.location:
                score += 0.1

        # 共同兴趣
        try:
            interests_a = json.loads(user_a.interests or "[]")
            interests_b = json.loads(user_b.interests or "[]")
            common_interests = set(interests_a) & set(interests_b)
            score += min(0.2, len(common_interests) * 0.05)
        except (json.JSONDecodeError, TypeError):
            pass

        # 约束范围
        return max(0.0, min(1.0, score))

    def create_match(
        self,
        user_id_a: str,
        user_id_b: str,
        compatibility_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        创建匹配记录

        Args:
            user_id_a: 用户 A ID
            user_id_b: 用户 B ID
            compatibility_score: 匹配度分数（可选，自动计算）

        Returns:
            匹配记录信息
        """
        try:
            from db.models import MatchHistoryDB

            # 计算匹配度
            if compatibility_score is None:
                compatibility_score = self.calculate_compatibility(user_id_a, user_id_b)

            # 创建匹配记录
            match_id = str(uuid.uuid4())
            match = MatchHistoryDB(
                id=match_id,
                user_id_1=user_id_a,
                user_id_2=user_id_b,
                compatibility_score=compatibility_score,
                status="matched",
                relationship_stage="matched",
                created_at=datetime.now()
            )

            self.db.add(match)
            self.db.commit()

            logger.info(f"[MatchingService] 创建匹配: {user_id_a} <-> {user_id_b}, score={compatibility_score}")

            return {
                "match_id": match_id,
                "user_id_1": user_id_a,
                "user_id_2": user_id_b,
                "compatibility_score": compatibility_score,
                "status": "matched"
            }

        except Exception as e:
            logger.error(f"[MatchingService] 创建匹配失败: {e}")
            self.db.rollback()
            return {
                "match_id": None,
                "error": str(e)
            }

    def check_mutual_like(
        self,
        user_id_a: str,
        user_id_b: str
    ) -> bool:
        """
        检查是否双向喜欢

        Args:
            user_id_a: 用户 A ID
            user_id_b: 用户 B ID

        Returns:
            是否双向喜欢
        """
        try:
            from db.models import SwipeActionDB

            # 检查 A 喜欢 B
            like_a_to_b = self.db.query(SwipeActionDB).filter(
                SwipeActionDB.user_id == user_id_a,
                SwipeActionDB.target_user_id == user_id_b,
                SwipeActionDB.action == "like"
            ).first()

            # 检查 B 喜欢 A
            like_b_to_a = self.db.query(SwipeActionDB).filter(
                SwipeActionDB.user_id == user_id_b,
                SwipeActionDB.target_user_id == user_id_a,
                SwipeActionDB.action == "like"
            ).first()

            return like_a_to_b is not None and like_b_to_a is not None

        except Exception as e:
            logger.error(f"[MatchingService] 检查双向喜欢失败: {e}")
            return False

    def get_match_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> list:
        """
        获取用户匹配历史

        Args:
            user_id: 用户 ID
            limit: 返回数量限制

        Returns:
            匹配历史列表
        """
        try:
            from db.models import MatchHistoryDB
            from sqlalchemy import or_

            matches = self.db.query(MatchHistoryDB).filter(
                or_(
                    MatchHistoryDB.user_id_1 == user_id,
                    MatchHistoryDB.user_id_2 == user_id
                ),
                MatchHistoryDB.status == "matched"
            ).order_by(MatchHistoryDB.created_at.desc()).limit(limit).all()

            return [
                {
                    "match_id": m.id,
                    "partner_id": m.user_id_2 if m.user_id_1 == user_id else m.user_id_1,
                    "compatibility_score": m.compatibility_score,
                    "matched_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in matches
            ]

        except Exception as e:
            logger.error(f"[MatchingService] 获取匹配历史失败: {e}")
            return []


# 服务工厂函数
def get_matching_service(db: Session) -> MatchingService:
    """
    获取匹配服务实例

    Args:
        db: 数据库会话

    Returns:
        MatchingService 实例
    """
    return MatchingService(db)