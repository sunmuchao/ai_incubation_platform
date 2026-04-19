"""
Her Tools - Feedback Tools Module

候选人反馈工具：记录用户反馈、查询反馈历史、分析偏好模式

【Agent Native 设计】
- 工具只做数据记录和查询
- 不做反馈分析逻辑（由 Agent 或后续服务处理）
- 返回原始数据供 Agent 解读

版本：v1.0
"""
import logging
import json
import uuid
from typing import Type, Optional, Dict, Any, List

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import ToolResult, HerRecordFeedbackInput, HerGetFeedbackHistoryInput
from .helpers import ensure_her_in_path, run_async, get_current_user_id, get_db_user

logger = logging.getLogger(__name__)

# 预设不喜欢原因列表
PRESET_DISLIKE_REASONS = [
    "年龄差距太大",
    "距离太远",
    "兴趣不匹配",
    "没有眼缘",
    "关系目标不一致",
    "其他",
]


# ==================== Her Record Feedback Tool ====================

class HerRecordFeedbackTool(BaseTool):
    """
    候选人反馈记录工具

    记录用户对推荐候选人的反馈，建立反馈闭环。
    """

    name: str = "her_record_feedback"
    description: str = """
记录用户对候选人的反馈。

【能力】
记录用户对推荐候选人的反馈（喜欢/不喜欢/中性），用于优化后续推荐。

【参数】
- candidate_id: 候选人 ID（display_id 如 candidate_001，或 user_id UUID）
- feedback_type: 反馈类型（like/dislike/neutral/skip）
- reason: 不喜欢原因（仅 dislike 时需要，预设选项）
- detail: 用户自定义原因（可选）

【预设不喜欢原因】
- "年龄差距太大"
- "距离太远"
- "兴趣不匹配"
- "没有眼缘"
- "关系目标不一致"
- "其他"

【返回】
- recorded: 是否成功记录
- feedback_id: 反馈记录 ID
- message: 反馈已记录的提示

【使用场景】
当用户表达对候选人的反馈时调用：
- "不喜欢他，换一个"
- "这个还行，先看看"
- "这个不错，我想联系他"

【Agent 行为指导】
1. 用户说"不喜欢"时，先询问原因（可选）
2. 记录反馈后，告知用户"已记住您的偏好"
3. 后续推荐会避开用户不喜欢的原因

【重要】
如果用户没有明确说明不喜欢原因，Agent 应主动询问：
"能告诉我为什么吗？年龄差距太大？距离太远？还是其他原因？"
"""
    args_schema: Type[BaseModel] = HerRecordFeedbackInput

    def _run(
        self,
        user_id: str = "me",
        candidate_id: str = "",
        feedback_type: str = "",
        reason: str = "",
        detail: str = ""
    ) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, candidate_id, feedback_type, reason, detail))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)

        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(
        self,
        user_id: str,
        candidate_id: str,
        feedback_type: str,
        reason: str,
        detail: str
    ) -> ToolResult:
        """
        记录候选人反馈

        【硬约束】
        - feedback_type 必须是 like/dislike/neutral/skip
        - dislike 时 reason 必填
        - reason 必须是预设选项之一
        """
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        from db.models import CandidateFeedbackDB, UserDB

        # ===== 参数校验 =====
        valid_feedback_types = ["like", "dislike", "neutral", "skip"]
        if feedback_type not in valid_feedback_types:
            return ToolResult(
                success=False,
                error=f"无效的反馈类型：{feedback_type}。可选值：{valid_feedback_types}"
            )

        if feedback_type == "dislike" and not reason:
            return ToolResult(
                success=False,
                error="不喜欢反馈必须填写原因。可选原因：" + ", ".join(PRESET_DISLIKE_REASONS)
            )

        if reason and reason not in PRESET_DISLIKE_REASONS:
            # 如果用户输入的自定义原因不在预设列表，自动归类为"其他"
            if reason != "其他":
                detail = reason
                reason = "其他"

        # ===== 解析 candidate_id =====
        # 支持 display_id（如 candidate_001）或 user_id（UUID）
        actual_candidate_id = candidate_id
        if candidate_id.startswith("candidate_"):
            # display_id 需要从数据库查询对应的 user_id
            # 这里简化处理：假设 Agent 传入的是正确的 user_id
            # 实际应从查询结果中获取
            pass

        # ===== 检查候选人是否存在 =====
        with db_session() as db:
            candidate = db.query(UserDB).filter(UserDB.id == actual_candidate_id).first()
            if not candidate:
                # 尝试按 display_id 查询（如果 candidate_id 是 display_id）
                # 由于 display_id 是动态生成的，这里简化处理
                # 实际应该从 her_find_candidates 的缓存中获取映射
                logger.warning(f"[her_record_feedback] 候选人可能不存在或 ID 格式不正确：{candidate_id}")

        # ===== 检查是否已反馈（避免重复）=====
        with db_session() as db:
            existing = db.query(CandidateFeedbackDB).filter(
                CandidateFeedbackDB.user_id == user_id,
                CandidateFeedbackDB.candidate_id == actual_candidate_id
            ).first()

            feedback_id = str(uuid.uuid4())
            action = "created"

            if existing:
                # 更新现有反馈
                existing.feedback_type = feedback_type
                existing.dislike_reason = reason if feedback_type == "dislike" else None
                existing.dislike_detail = detail
                feedback_id = existing.id
                action = "updated"
            else:
                # 创建新反馈
                feedback = CandidateFeedbackDB(
                    id=feedback_id,
                    user_id=user_id,
                    candidate_id=actual_candidate_id,
                    feedback_type=feedback_type,
                    dislike_reason=reason if feedback_type == "dislike" else None,
                    dislike_detail=detail,
                )
                db.add(feedback)

        # ===== 更新统计表 =====
        await self._update_statistics(user_id)

        # ===== 返回结果 =====
        message = self._generate_message(feedback_type, reason, action)

        return ToolResult(
            success=True,
            data={
                "recorded": True,
                "feedback_id": feedback_id,
                "action": action,
                "message": message,
            }
        )

    async def _update_statistics(self, user_id: str):
        """更新用户反馈统计表"""
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        from db.models import FeedbackStatisticsDB, CandidateFeedbackDB

        with db_session() as db:
            # 查询用户所有反馈
            feedbacks = db.query(CandidateFeedbackDB).filter(
                CandidateFeedbackDB.user_id == user_id
            ).all()

            # 统计
            like_count = sum(1 for f in feedbacks if f.feedback_type == "like")
            dislike_count = sum(1 for f in feedbacks if f.feedback_type == "dislike")
            neutral_count = sum(1 for f in feedbacks if f.feedback_type == "neutral")
            skip_count = sum(1 for f in feedbacks if f.feedback_type == "skip")

            # 不喜欢原因分布
            reason_distribution = {}
            for f in feedbacks:
                if f.feedback_type == "dislike" and f.dislike_reason:
                    reason_distribution[f.dislike_reason] = reason_distribution.get(f.dislike_reason, 0) + 1

            # 更新或创建统计记录
            stats = db.query(FeedbackStatisticsDB).filter(
                FeedbackStatisticsDB.user_id == user_id
            ).first()

            if stats:
                stats.total_feedbacks = len(feedbacks)
                stats.like_count = like_count
                stats.dislike_count = dislike_count
                stats.neutral_count = neutral_count
                stats.skip_count = skip_count
                stats.dislike_reason_distribution = reason_distribution
            else:
                stats = FeedbackStatisticsDB(
                    user_id=user_id,
                    total_feedbacks=len(feedbacks),
                    like_count=like_count,
                    dislike_count=dislike_count,
                    neutral_count=neutral_count,
                    skip_count=skip_count,
                    dislike_reason_distribution=reason_distribution,
                )
                db.add(stats)

    def _generate_message(self, feedback_type: str, reason: str, action: str) -> str:
        """生成反馈确认消息"""
        if feedback_type == "like":
            return "已记录您的喜欢反馈！后续会优先推荐类似的人～"
        elif feedback_type == "dislike":
            return f"已记录您的不喜欢反馈（原因：{reason}）。后续推荐会避开这类候选人～"
        elif feedback_type == "neutral":
            return "已记录您的反馈。后续会根据您的偏好优化推荐～"
        elif feedback_type == "skip":
            return "已记录跳过。需要我推荐下一个吗？"
        return "反馈已记录"


# ==================== Her Get Feedback History Tool ====================

class HerGetFeedbackHistoryTool(BaseTool):
    """
    获取用户反馈历史工具

    用于分析用户偏好模式。
    """

    name: str = "her_get_feedback_history"
    description: str = """
获取用户的反馈历史。

【能力】
查询用户对候选人的反馈记录，用于分析偏好模式。

【参数】
- feedback_type: 筛选类型（可选）
- limit: 返回数量限制（默认 20）

【返回】
- feedbacks: 反馈列表
- statistics: 用户反馈统计汇总

【使用场景】
当需要了解用户偏好模式时调用：
- 分析用户为什么不喜欢某些候选人
- 了解用户喜欢什么样的人
"""
    args_schema: Type[BaseModel] = HerGetFeedbackHistoryInput

    def _run(self, user_id: str = "me", feedback_type: str = "", limit: int = 20) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, feedback_type, limit))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)

        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, feedback_type: str, limit: int) -> ToolResult:
        """查询反馈历史"""
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        from db.models import CandidateFeedbackDB, FeedbackStatisticsDB, UserDB

        with db_session() as db:
            # 查询反馈列表
            query = db.query(CandidateFeedbackDB).filter(
                CandidateFeedbackDB.user_id == user_id
            )

            if feedback_type:
                query = query.filter(CandidateFeedbackDB.feedback_type == feedback_type)

            feedbacks = query.order_by(CandidateFeedbackDB.created_at.desc()).limit(limit).all()

            # 获取候选人信息
            feedback_list = []
            for f in feedbacks:
                candidate = db.query(UserDB).filter(UserDB.id == f.candidate_id).first()
                feedback_list.append({
                    "feedback_id": f.id,
                    "candidate_id": f.candidate_id,
                    "candidate_name": candidate.name if candidate else "未知用户",
                    "candidate_age": candidate.age if candidate else 0,
                    "candidate_location": candidate.location if candidate else "",
                    "feedback_type": f.feedback_type,
                    "dislike_reason": f.dislike_reason,
                    "dislike_detail": f.dislike_detail,
                    "created_at": f.created_at.isoformat() if f.created_at else "",
                })

            # 获取统计汇总
            stats = db.query(FeedbackStatisticsDB).filter(
                FeedbackStatisticsDB.user_id == user_id
            ).first()

            statistics = {}
            if stats:
                statistics = {
                    "total_feedbacks": stats.total_feedbacks,
                    "like_count": stats.like_count,
                    "dislike_count": stats.dislike_count,
                    "neutral_count": stats.neutral_count,
                    "skip_count": stats.skip_count,
                    "dislike_reason_distribution": stats.dislike_reason_distribution,
                    "learned_preferences": stats.learned_preferences,
                }

        return ToolResult(
            success=True,
            data={
                "feedbacks": feedback_list,
                "statistics": statistics,
            }
        )


# ==================== Exports ====================

__all__ = [
    "HerRecordFeedbackTool",
    "HerGetFeedbackHistoryTool",
    "PRESET_DISLIKE_REASONS",
]

# Tool instances for registration
her_record_feedback_tool = HerRecordFeedbackTool()
her_get_feedback_history_tool = HerGetFeedbackHistoryTool()