"""
AI 反馈闭环服务

功能:
- 记录用户对 AI 建议的反馈（采纳/忽略）
- 追踪采纳建议后的聊天结果
- 基于反馈优化 AI 策略
- A/B 测试支持

使用场景:
- 用户点击"AI 帮我回"后选择某个建议
- 用户忽略 AI 建议自己回复
- 采纳建议后对话是否继续/升温
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from utils.logger import logger

# 数据库模型
from db.models import UserDB, ChatMessageDB, ChatConversationDB
from models.ai_feedback_models import AIFeedbackDB, AIFeedbackOutcomeDB
from sqlalchemy import and_, or_


class AIFeedbackService:
    """AI 反馈闭环服务"""

    # 反馈类型
    FEEDBACK_ADOPTED = "adopted"      # 采纳建议
    FEEDBACK_IGNORED = "ignored"      # 忽略建议
    FEEDBACK_MODIFIED = "modified"    # 修改后发送
    FEEDBACK_HELPFUL = "helpful"      # 标记有用
    FEEDBACK_NOT_HELPFUL = "not_helpful"  # 标记无用

    # 聊天结果
    OUTCOME_CONTINUED = "continued"       # 对话继续
    OUTCOME_STOPPED = "stopped"           # 对话中断
    OUTCOME_WARMED = "warmed"             # 关系升温
    OUTCOME_DATE_REQUESTED = "date_requested"  # 邀约成功

    def __init__(self, db: Optional[Session] = None, data_dir: Optional[str] = None):
        """
        初始化 AI 反馈服务

        Args:
            db: 数据库会话（如果不提供，会在使用时创建临时会话）
            data_dir: 数据目录路径（可选，默认使用 src/data）

        推荐用法:
            with db_session() as db:
                service = AIFeedbackService(db=db)
                service.record_feedback(...)
        """
        self._db = db
        self._should_close_db = db is None  # 如果自己创建的，需要负责关闭
        self.data_dir = data_dir

    def _get_db(self) -> Session:
        """
        获取数据库会话

        注意：推荐在构造函数中传入 db session，避免延迟创建。
        """
        if self._db is None:
            self._db = SessionLocal()
            self._should_close_db = True
        return self._db

    def close(self):
        """关闭数据库会话（如果是自己创建的）"""
        if self._should_close_db and self._db is not None:
            try:
                self._db.commit()
                self._db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")
            finally:
                self._db = None
                self._should_close_db = False

    def record_feedback(
        self,
        user_id: str,
        partner_id: str,
        suggestion_id: str,
        feedback_type: str,
        suggestion_content: str,
        suggestion_style: str,
        user_actual_reply: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        记录用户对 AI 建议的反馈

        Args:
            user_id: 用户 ID
            partner_id: 聊天对象 ID
            suggestion_id: 建议 ID（用于追踪）
            feedback_type: 反馈类型 (adopted/ignored/modified)
            suggestion_content: AI 建议内容
            suggestion_style: 建议风格（幽默/真诚/延续话题）
            user_actual_reply: 用户实际发送的内容
            metadata: 额外元数据

        Returns:
            反馈记录 ID
        """
        db = self._get_db()
        try:
            import uuid
            feedback_id = str(uuid.uuid4())

            # 创建反馈记录
            feedback = AIFeedbackDB(
                id=feedback_id,
                user_id=user_id,
                partner_id=partner_id,
                suggestion_id=suggestion_id,
                feedback_type=feedback_type,
                suggestion_content=suggestion_content,
                suggestion_style=suggestion_style,
                user_actual_reply=user_actual_reply,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            db.add(feedback)
            db.commit()

            logger.info(
                f"Recorded AI feedback: {feedback_type} - "
                f"user {user_id} with partner {partner_id}"
            )

            return feedback_id

        except Exception as e:
            db.rollback()
            logger.error(f"Record feedback failed: {e}")
            return ""
        finally:
            self.close()

    def get_feedback_history(
        self,
        user_id: str,
        limit: int = 50,
        feedback_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户反馈历史

        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            feedback_type: 反馈类型筛选

        Returns:
            反馈记录列表
        """
        db = self._get_db()
        try:
            query = db.query(AIFeedbackDB).filter(AIFeedbackDB.user_id == user_id)

            if feedback_type:
                query = query.filter(AIFeedbackDB.feedback_type == feedback_type)

            feedbacks = query.order_by(desc(AIFeedbackDB.created_at)).limit(limit).all()

            return [fb.to_dict() for fb in feedbacks]

        finally:
            self.close()

    def get_feedback_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取用户反馈统计

        Args:
            user_id: 用户 ID
            days: 统计天数

        Returns:
            统计数据
        """
        db = self._get_db()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # 查询各类型反馈数量
            query = db.query(AIFeedbackDB).filter(
                AIFeedbackDB.user_id == user_id,
                AIFeedbackDB.created_at >= cutoff_date
            )

            total = query.count()
            adopted = query.filter(AIFeedbackDB.feedback_type == self.FEEDBACK_ADOPTED).count()
            ignored = query.filter(AIFeedbackDB.feedback_type == self.FEEDBACK_IGNORED).count()
            modified = query.filter(AIFeedbackDB.feedback_type == self.FEEDBACK_MODIFIED).count()

            return {
                "total": total,
                "adopted": adopted,
                "ignored": ignored,
                "modified": modified,
                "adoption_rate": adopted / total if total > 0 else 0,
                "period_days": days
            }

        finally:
            self.close()

    def record_outcome(
        self,
        user_id: str,
        partner_id: str,
        feedback_id: str,
        outcome_type: str,
        outcome_data: Optional[Dict] = None,
    ) -> None:
        """
        记录采纳建议后的聊天结果

        Args:
            user_id: 用户 ID
            partner_id: 聊天对象 ID
            feedback_id: 反馈记录 ID
            outcome_type: 结果类型
            outcome_data: 结果详情
        """
        try:
            outcome_data = {
                "feedback_id": feedback_id,
                "outcome_type": outcome_type,
                "outcome_data": outcome_data or {},
                "created_at": datetime.now().isoformat(),
            }

            # 追加到反馈记录
            self._append_outcome(feedback_id, outcome_data)

            logger.info(
                f"Recorded AI outcome: {outcome_type} - "
                f"feedback {feedback_id}"
            )

        except Exception as e:
            logger.error(f"Record outcome failed: {e}")

    def _append_outcome(self, feedback_id: str, outcome_data: Dict):
        """追加结果到反馈记录"""
        import os

        # 使用实例的 data_dir 或默认路径
        if self.data_dir:
            data_dir = self.data_dir
        else:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

        outcomes_file = os.path.join(data_dir, "ai_outcomes.jsonl")

        with open(outcomes_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(outcome_data, ensure_ascii=False) + "\n")

    def get_adoption_rate(
        self,
        user_id: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取用户 AI 建议采纳率

        Args:
            user_id: 用户 ID
            days: 统计天数

        Returns:
            采纳率统计
        """
        try:
            feedbacks = self._load_feedbacks(user_id, days)

            if not feedbacks:
                return {
                    "adoption_rate": 0,
                    "total_suggestions": 0,
                    "adopted": 0,
                    "ignored": 0,
                    "modified": 0,
                    "period_days": days,
                }

            adopted = sum(1 for f in feedbacks if f.get("feedback_type") == self.FEEDBACK_ADOPTED)
            ignored = sum(1 for f in feedbacks if f.get("feedback_type") == self.FEEDBACK_IGNORED)
            modified = sum(1 for f in feedbacks if f.get("feedback_type") == self.FEEDBACK_MODIFIED)

            total = len(feedbacks)
            adoption_rate = (adopted + modified * 0.5) / total if total > 0 else 0

            return {
                "adoption_rate": round(adoption_rate, 3),
                "total_suggestions": total,
                "adopted": adopted,
                "ignored": ignored,
                "modified": modified,
                "period_days": days,
            }

        except Exception as e:
            logger.error(f"Get adoption rate failed: {e}")
            return {
                "adoption_rate": 0,
                "total_suggestions": 0,
                "adopted": 0,
                "ignored": 0,
                "modified": 0,
                "period_days": days,
            }

    def get_style_preference(
        self,
        user_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        获取用户偏好的 AI 建议风格

        Args:
            user_id: 用户 ID
            days: 统计天数

        Returns:
            风格偏好统计
        """
        try:
            feedbacks = self._load_feedbacks(user_id, days)

            if not feedbacks:
                return {}

            # 统计各风格的采纳率
            style_stats = defaultdict(lambda: {"adopted": 0, "total": 0})

            for f in feedbacks:
                style = f.get("suggestion_style", "unknown")
                style_stats[style]["total"] += 1
                if f.get("feedback_type") in [self.FEEDBACK_ADOPTED, self.FEEDBACK_MODIFIED]:
                    style_stats[style]["adopted"] += 1

            # 计算各风格的采纳率
            style_preferences = {}
            for style, stats in style_stats.items():
                style_preferences[style] = {
                    "adoption_rate": round(stats["adopted"] / stats["total"], 3) if stats["total"] > 0 else 0,
                    "total": stats["total"],
                    "adopted": stats["adopted"],
                }

            # 找出最佳风格
            best_style = max(style_preferences.items(), key=lambda x: x[1]["adoption_rate"])[0] if style_preferences else None

            return {
                "style_preferences": style_preferences,
                "best_style": best_style,
            }

        except Exception as e:
            logger.error(f"Get style preference failed: {e}")
            return {}

    def analyze_suggestion_effectiveness(
        self,
        style: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        分析 AI 建议的有效性（全局）

        Args:
            style: 建议风格（可选）
            days: 统计天数

        Returns:
            有效性分析
        """
        try:
            # 加载所有反馈
            all_feedbacks = self._load_all_feedbacks(days)

            if not all_feedbacks:
                return {"effectiveness_score": 0, "sample_size": 0}

            # 过滤风格
            if style:
                all_feedbacks = [f for f in all_feedbacks if f.get("suggestion_style") == style]

            # 计算有效性分数
            adopted = sum(1 for f in all_feedbacks if f.get("feedback_type") == self.FEEDBACK_ADOPTED)
            modified = sum(1 for f in all_feedbacks if f.get("feedback_type") == self.FEEDBACK_MODIFIED)
            total = len(all_feedbacks)

            effectiveness_score = (adopted + modified * 0.5) / total if total > 0 else 0

            # 分析结果
            outcomes = self._load_outcomes(days)
            continued_count = sum(1 for o in outcomes if o.get("outcome_type") == self.OUTCOME_CONTINUED)
            warmed_count = sum(1 for o in outcomes if o.get("outcome_type") == self.OUTCOME_WARMED)

            return {
                "effectiveness_score": round(effectiveness_score, 3),
                "total_suggestions": total,
                "adopted": adopted,
                "modified": modified,
                "conversation_continued_rate": round(continued_count / total, 3) if total > 0 else 0,
                "relationship_warmed_rate": round(warmed_count / total, 3) if total > 0 else 0,
                "sample_size": total,
                "style": style,
            }

        except Exception as e:
            logger.error(f"Analyze suggestion effectiveness failed: {e}")
            return {"effectiveness_score": 0, "sample_size": 0}

    def _load_feedbacks(self, user_id: str, days: int) -> List[Dict]:
        """加载用户反馈"""
        import os

        # 使用实例的 data_dir 或默认路径
        if self.data_dir:
            data_dir = self.data_dir
        else:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

        feedback_file = os.path.join(data_dir, "ai_feedback.jsonl")

        if not os.path.exists(feedback_file):
            return []

        feedbacks = []
        cutoff = datetime.now() - timedelta(days=days)

        with open(feedback_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    feedback = json.loads(line.strip())
                    # 检查是否是指定用户
                    if feedback.get("user_id") == user_id:
                        # 检查时间
                        created_at = datetime.fromisoformat(feedback.get("created_at"))
                        if created_at >= cutoff:
                            feedbacks.append(feedback)
                except (json.JSONDecodeError, ValueError):
                    continue

        return feedbacks

    def _load_all_feedbacks(self, days: int) -> List[Dict]:
        """加载所有反馈"""
        import os

        # 使用实例的 data_dir 或默认路径
        if self.data_dir:
            data_dir = self.data_dir
        else:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

        feedback_file = os.path.join(data_dir, "ai_feedback.jsonl")

        if not os.path.exists(feedback_file):
            return []

        feedbacks = []
        cutoff = datetime.now() - timedelta(days=days)

        with open(feedback_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    feedback = json.loads(line.strip())
                    created_at = datetime.fromisoformat(feedback.get("created_at"))
                    if created_at >= cutoff:
                        feedbacks.append(feedback)
                except (json.JSONDecodeError, ValueError):
                    continue

        return feedbacks

    def _load_outcomes(self, days: int) -> List[Dict]:
        """加载结果数据"""
        import os

        # 使用实例的 data_dir 或默认路径
        if self.data_dir:
            data_dir = self.data_dir
        else:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

        outcomes_file = os.path.join(data_dir, "ai_outcomes.jsonl")

        if not os.path.exists(outcomes_file):
            return []

        outcomes = []
        cutoff = datetime.now() - timedelta(days=days)

        with open(outcomes_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    outcome = json.loads(line.strip())
                    created_at = datetime.fromisoformat(outcome.get("created_at"))
                    if created_at >= cutoff:
                        outcomes.append(outcome)
                except (json.JSONDecodeError, ValueError):
                    continue

        return outcomes


# 全局服务实例
_ai_feedback_service: Optional[AIFeedbackService] = None


def get_ai_feedback_service() -> AIFeedbackService:
    """获取 AI 反馈服务单例"""
    global _ai_feedback_service
    if _ai_feedback_service is None:
        _ai_feedback_service = AIFeedbackService()
    return _ai_feedback_service
