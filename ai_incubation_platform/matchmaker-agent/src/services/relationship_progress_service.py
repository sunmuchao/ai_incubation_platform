"""
关系进展追踪服务 - P3

基于互动历史生成关系发展可视化数据：
- 关系阶段识别（匹配 -> 聊天 -> 约会 -> 恋爱）
- 互动频率趋势
- 关键里程碑记录
- 关系健康度评估
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from db.database import SessionLocal
from db.models import (
    RelationshipProgressDB, MatchHistoryDB, ConversationDB,
    UserDB, BehaviorEventDB
)
from utils.logger import logger


# 关系阶段定义
RELATIONSHIP_STAGES = {
    "matched": {"order": 1, "label": "已匹配", "description": "系统匹配成功"},
    "chatting": {"order": 2, "label": "聊天中", "description": "开始互动交流"},
    "exchanged_contact": {"order": 3, "label": "交换联系方式", "description": "交换微信/电话等"},
    "first_date": {"order": 4, "label": "首次约会", "description": "完成第一次线下见面"},
    "dating": {"order": 5, "label": "约会中", "description": "定期约会阶段"},
    "exclusive": {"order": 6, "label": "确定关系", "description": "确立排他性关系"},
    "in_relationship": {"order": 7, "label": "恋爱中", "description": "稳定恋爱关系"}
}

# 里程碑类型
MILESTONE_TYPES = {
    "first_message": "第一条消息",
    "first_like": "第一次点赞",
    "deep_conversation": "深度对话",
    "contact_exchange": "交换联系方式",
    "first_date": "第一次约会",
    "anniversary": "纪念日",
    "relationship_status_change": "关系状态变更"
}


class RelationshipProgressService:
    """关系进展追踪服务"""

    def __init__(self):
        self._stage_progression_weights = {
            "message_count": 0.3,
            "conversation_depth": 0.3,
            "interaction_frequency": 0.2,
            "milestone_achievement": 0.2
        }

    def record_progress(
        self,
        user_id_1: str,
        user_id_2: str,
        progress_type: str,
        description: str,
        progress_score: int = 5,
        related_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录关系进展

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            progress_type: 进展类型
            description: 进展描述
            progress_score: 进展评分 (1-10)
            related_data: 相关数据

        Returns:
            记录 ID
        """
        progress_id = str(__import__('uuid').uuid4())

        db = SessionLocal()
        try:
            progress = RelationshipProgressDB(
                id=progress_id,
                user_id_1=user_id_1,
                user_id_2=user_id_2,
                progress_type=progress_type,
                description=description,
                progress_score=progress_score,
                related_data=related_data or {}
            )
            db.add(progress)

            # 更新匹配历史中的关系阶段
            self._update_relationship_stage(user_id_1, user_id_2, progress_type, db)

            db.commit()
            db.refresh(progress)

            logger.info(f"Recorded relationship progress: {progress_type} for {user_id_1} & {user_id_2}")
            return progress_id
        except Exception as e:
            db.rollback()
            logger.error(f"Error recording relationship progress: {e}")
            raise
        finally:
            db.close()

    def _update_relationship_stage(
        self,
        user_id_1: str,
        user_id_2: str,
        progress_type: str,
        db
    ):
        """根据进展类型更新关系阶段"""
        # 查找匹配记录
        match = db.query(MatchHistoryDB).filter(
            ((MatchHistoryDB.user_id_1 == user_id_1) & (MatchHistoryDB.user_id_2 == user_id_2)) |
            ((MatchHistoryDB.user_id_1 == user_id_2) & (MatchHistoryDB.user_id_2 == user_id_1))
        ).first()

        if not match:
            return

        current_stage = match.relationship_stage
        new_stage = self._infer_stage_from_progress(progress_type)

        # 阶段升级
        if new_stage and RELATIONSHIP_STAGES.get(new_stage, {}).get("order", 0) > RELATIONSHIP_STAGES.get(current_stage, {}).get("order", 0):
            match.relationship_stage = new_stage
            db.commit()
            logger.info(f"Relationship stage updated from {current_stage} to {new_stage}")

    def _infer_stage_from_progress(self, progress_type: str) -> Optional[str]:
        """从进展类型推断关系阶段"""
        stage_mapping = {
            "first_message": "chatting",
            "contact_exchange": "exchanged_contact",
            "first_date": "first_date",
            "relationship_milestone": "dating"
        }
        return stage_mapping.get(progress_type)

    def get_progress_timeline(
        self,
        user_id_1: str,
        user_id_2: str
    ) -> Dict[str, Any]:
        """
        获取关系进展时间线

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2

        Returns:
            时间线数据
        """
        db = SessionLocal()
        try:
            progresses = db.query(RelationshipProgressDB).filter(
                ((RelationshipProgressDB.user_id_1 == user_id_1) & (RelationshipProgressDB.user_id_2 == user_id_2)) |
                ((RelationshipProgressDB.user_id_1 == user_id_2) & (RelationshipProgressDB.user_id_2 == user_id_1))
            ).order_by(RelationshipProgressDB.created_at).all()

            timeline = []
            for p in progresses:
                timeline.append({
                    "id": p.id,
                    "type": p.progress_type,
                    "label": MILESTONE_TYPES.get(p.progress_type, p.progress_type),
                    "description": p.description,
                    "score": p.progress_score,
                    "timestamp": p.created_at.isoformat(),
                    "related_data": p.related_data
                })

            # 获取当前关系阶段
            match = db.query(MatchHistoryDB).filter(
                ((MatchHistoryDB.user_id_1 == user_id_1) & (MatchHistoryDB.user_id_2 == user_id_2)) |
                ((MatchHistoryDB.user_id_1 == user_id_2) & (MatchHistoryDB.user_id_2 == user_id_1))
            ).first()

            current_stage = match.relationship_stage if match else "unknown"

            return {
                "user_ids": [user_id_1, user_id_2],
                "current_stage": current_stage,
                "current_stage_label": RELATIONSHIP_STAGES.get(current_stage, {}).get("label", "未知"),
                "timeline": timeline,
                "total_milestones": len(timeline)
            }
        finally:
            db.close()

    def get_relationship_health_score(
        self,
        user_id_1: str,
        user_id_2: str
    ) -> Dict[str, Any]:
        """
        计算关系健康度评分

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2

        Returns:
            健康度评分
        """
        db = SessionLocal()
        try:
            # 获取进展记录
            progresses = db.query(RelationshipProgressDB).filter(
                ((RelationshipProgressDB.user_id_1 == user_id_1) & (RelationshipProgressDB.user_id_2 == user_id_2)) |
                ((RelationshipProgressDB.user_id_1 == user_id_2) & (RelationshipProgressDB.user_id_2 == user_id_1))
            ).all()

            if not progresses:
                return self._empty_health_score()

            # 计算各维度得分
            message_count_score = self._calculate_message_activity(user_id_1, user_id_2, db)
            milestone_score = self._calculate_milestone_score(progresses)
            stage_score = self._calculate_stage_score(progresses)

            # 加权综合得分
            overall_score = (
                message_count_score * 0.4 +
                milestone_score * 0.3 +
                stage_score * 0.3
            )

            return {
                "overall_score": round(overall_score, 2),
                "dimensions": {
                    "message_activity": round(message_count_score, 2),
                    "milestone_progress": round(milestone_score, 2),
                    "relationship_stage": round(stage_score, 2)
                },
                "health_level": self._get_health_level(overall_score),
                "suggestions": self._generate_health_suggestions(overall_score, progresses)
            }
        finally:
            db.close()

    def _calculate_message_activity(
        self,
        user_id_1: str,
        user_id_2: str,
        db
    ) -> float:
        """计算消息活跃度得分"""
        # 查询对话数量
        conv_count = db.query(ConversationDB).filter(
            ((ConversationDB.user_id_1 == user_id_1) & (ConversationDB.user_id_2 == user_id_2)) |
            ((ConversationDB.user_id_1 == user_id_2) & (ConversationDB.user_id_2 == user_id_1))
        ).count()

        # 最近 7 天的消息数
        week_ago = datetime.now() - timedelta(days=7)
        recent_count = db.query(ConversationDB).filter(
            ((ConversationDB.user_id_1 == user_id_1) & (ConversationDB.user_id_2 == user_id_2)) |
            ((ConversationDB.user_id_1 == user_id_2) & (ConversationDB.user_id_2 == user_id_1)),
            ConversationDB.created_at >= week_ago
        ).count()

        # 得分计算：总数 + 近期活跃度
        base_score = min(5, conv_count / 20)  # 最多 5 分
        recent_bonus = min(5, recent_count / 10)  # 最多 5 分

        return base_score + recent_bonus

    def _calculate_milestone_score(self, progresses: List[RelationshipProgressDB]) -> float:
        """计算里程碑得分"""
        if not progresses:
            return 0

        # 平均进展评分
        avg_score = sum(p.progress_score for p in progresses) / len(progresses)

        # 里程碑数量加分
        count_bonus = min(2, len(progresses) / 5)

        return (avg_score / 10) * 8 + count_bonus  # 归一化到 0-10

    def _calculate_stage_score(self, progresses: List[RelationshipProgressDB]) -> float:
        """计算关系阶段得分"""
        if not progresses:
            return 0

        # 获取最高阶段
        max_stage_order = max(
            RELATIONSHIP_STAGES.get(self._infer_stage_from_progress(p.progress_type), {}).get("order", 0)
            for p in progresses
        )

        # 归一化到 0-10
        return (max_stage_order / 7) * 10

    def _get_health_level(self, score: float) -> str:
        """根据得分返回健康等级"""
        if score >= 8:
            return "excellent"  # 优秀
        elif score >= 6:
            return "good"  # 良好
        elif score >= 4:
            return "fair"  # 一般
        else:
            return "needs_attention"  # 需要关注

    def _generate_health_suggestions(
        self,
        score: float,
        progresses: List[RelationshipProgressDB]
    ) -> List[str]:
        """生成健康建议"""
        suggestions = []

        if score < 4:
            suggestions.append("互动较少，建议多交流了解彼此")
        if score < 6:
            suggestions.append("可以尝试安排线下见面，加深了解")

        # 检查是否缺少关键里程碑
        progress_types = [p.progress_type for p in progresses]
        if "first_date" not in progress_types and len(progresses) > 3:
            suggestions.append("已经聊了一段时间，可以考虑见面了")

        if "contact_exchange" not in progress_types and len(progresses) > 2:
            suggestions.append("可以考虑交换联系方式，方便日常沟通")

        return suggestions

    def _empty_health_score(self) -> Dict[str, Any]:
        """返回空的健康评分"""
        return {
            "overall_score": 0,
            "dimensions": {
                "message_activity": 0,
                "milestone_progress": 0,
                "relationship_stage": 0
            },
            "health_level": "no_data",
            "suggestions": ["开始互动，建立你们的关系里程碑吧！"]
        }

    def get_visualization_data(
        self,
        user_id_1: str,
        user_id_2: str
    ) -> Dict[str, Any]:
        """
        获取可视化数据（用于前端图表）

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2

        Returns:
            可视化数据
        """
        db = SessionLocal()
        try:
            # 获取时间线
            timeline = self.get_progress_timeline(user_id_1, user_id_2)

            # 按日期分组统计
            daily_activity = {}
            for item in timeline["timeline"]:
                date = item["timestamp"][:10]  # YYYY-MM-DD
                daily_activity[date] = daily_activity.get(date, 0) + 1

            # 构建图表数据
            chart_data = {
                "labels": sorted(daily_activity.keys()),
                "activity_data": [daily_activity[d] for d in sorted(daily_activity.keys())],
                "stage_changes": [
                    {
                        "date": item["timestamp"][:10],
                        "stage": item.get("stage", "milestone")
                    }
                    for item in timeline["timeline"]
                    if "stage" in item.get("type", "")
                ]
            }

            return {
                "timeline": timeline,
                "chart_data": chart_data,
                "health_score": self.get_relationship_health_score(user_id_1, user_id_2)
            }
        finally:
            db.close()


# 全局服务实例
relationship_progress_service = RelationshipProgressService()
