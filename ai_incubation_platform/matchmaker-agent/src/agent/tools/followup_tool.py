"""
跟进记录工具

用于记录约会进展和关系发展阶段。
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from utils.logger import logger


class FollowupTool:
    """
    跟进记录工具

    功能：
    - 记录约会进展
    - 追踪关系发展阶段
    - 提供跟进建议
    """

    name = "followup_record"
    description = "记录约会进展和关系发展阶段"
    tags = ["followup", "tracking", "relationship"]

    # 关系发展阶段
    RELATIONSHIP_STAGES = [
        {"stage": "initial", "name": "初识阶段", "description": "刚刚开始了解对方"},
        {"stage": "getting_to_know", "name": "互相了解", "description": "通过聊天和约会逐渐了解"},
        {"stage": "dating", "name": "正式约会", "description": "开始定期约会"},
        {"stage": "exclusive", "name": "专一交往", "description": "确定一对一关系"},
        {"stage": "committed", "name": "稳定关系", "description": "关系稳定，考虑长远发展"},
    ]

    # 跟进建议模板
    FOLLOWUP_SUGGESTIONS = {
        "initial": [
            "主动发起话题，了解对方兴趣爱好",
            "邀请参加轻松的活动，如咖啡厅、散步",
            "保持适度联系，避免过于频繁"
        ],
        "getting_to_know": [
            "深入交流价值观和人生目标",
            "尝试不同类型的约会活动",
            "介绍给朋友认识，扩展社交圈"
        ],
        "dating": [
            "增加约会频率，深化感情",
            "一起规划短期旅行",
            "讨论对关系的期待"
        ],
        "exclusive": [
            "建立更深的信任和理解",
            "讨论未来规划和目标",
            "处理冲突，学习有效沟通"
        ],
        "committed": [
            "考虑长期承诺",
            "一起面对生活挑战",
            "维持关系新鲜感"
        ]
    }

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
                "target_user_id": {
                    "type": "string",
                    "description": "对象 ID"
                },
                "action": {
                    "type": "string",
                    "description": "跟进动作",
                    "enum": ["message_sent", "date_completed", "gift_sent", "confession", "milestone"]
                },
                "notes": {
                    "type": "string",
                    "description": "备注信息"
                },
                "relationship_stage": {
                    "type": "string",
                    "description": "当前关系阶段",
                    "enum": ["initial", "getting_to_know", "dating", "exclusive", "committed"]
                }
            },
            "required": ["user_id", "target_user_id", "action"]
        }

    @staticmethod
    def handle(
        user_id: str,
        target_user_id: str,
        action: str,
        notes: Optional[str] = None,
        relationship_stage: Optional[str] = None
    ) -> dict:
        """
        处理跟进记录请求

        Args:
            user_id: 用户 ID
            target_user_id: 对象 ID
            action: 跟进动作
            notes: 备注信息
            relationship_stage: 关系阶段

        Returns:
            记录结果和建议
        """
        logger.info(f"FollowupTool: Recording followup for {user_id} -> {target_user_id}, action={action}")

        # 创建跟进记录
        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "target_user_id": target_user_id,
            "action": action,
            "notes": notes,
            "relationship_stage": relationship_stage,
            "timestamp": datetime.now().isoformat()
        }

        # 存储记录
        FollowupTool._record_followup(record)

        # 生成跟进建议
        stage = relationship_stage or "initial"
        suggestions = FollowupTool.FOLLOWUP_SUGGESTIONS.get(stage, [])

        result = {
            "success": True,
            "record_id": record["id"],
            "timestamp": record["timestamp"],
            "current_stage": FollowupTool._get_stage_name(stage),
            "suggestions": suggestions[:3]  # 返回 3 条建议
        }

        logger.info(f"FollowupTool: Followup recorded successfully")
        return result

    @staticmethod
    def _get_stage_name(stage: str) -> str:
        """获取阶段中文名"""
        for s in FollowupTool.RELATIONSHIP_STAGES:
            if s["stage"] == stage:
                return s["name"]
        return "未知阶段"

    # 内存存储跟进历史
    _followup_history: List[dict] = []

    @classmethod
    def _record_followup(cls, record: dict) -> None:
        """记录跟进历史"""
        cls._followup_history.append(record)
        if len(cls._followup_history) > 500:
            cls._followup_history = cls._followup_history[-200:]

    @classmethod
    def get_followup_history(cls, user_id: str, target_user_id: Optional[str] = None) -> List[dict]:
        """获取跟进历史"""
        records = [r for r in cls._followup_history if r.get("user_id") == user_id]
        if target_user_id:
            records = [r for r in records if r.get("target_user_id") == target_user_id]
        return records

    @classmethod
    def get_relationship_progress(cls, user_id: str, target_user_id: str) -> dict:
        """
        获取关系进展分析

        Args:
            user_id: 用户 ID
            target_user_id: 对象 ID

        Returns:
            关系进展分析
        """
        records = cls.get_followup_history(user_id, target_user_id)

        if not records:
            return {"status": "no_data", "message": "暂无跟进记录"}

        # 分析互动频率
        total_interactions = len(records)

        # 分析最近互动时间
        if records:
            last_interaction = records[-1]["timestamp"]
        else:
            last_interaction = None

        # 确定当前阶段
        stages = [r.get("relationship_stage") for r in records if r.get("relationship_stage")]
        current_stage = stages[-1] if stages else "initial"

        # 分析互动类型分布
        action_counts = {}
        for record in records:
            action = record.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

        return {
            "status": "active",
            "total_interactions": total_interactions,
            "last_interaction": last_interaction,
            "current_stage": cls._get_stage_name(current_stage),
            "action_distribution": action_counts,
            "relationship_trend": cls._analyze_trend(records)
        }

    @staticmethod
    def _analyze_trend(records: List[dict]) -> str:
        """分析关系趋势"""
        if len(records) < 3:
            return "数据不足，继续互动"

        recent_records = records[-5:]
        stage_progress = {s["stage"]: i for i, s in enumerate(FollowupTool.RELATIONSHIP_STAGES)}

        stages_in_recent = [r.get("relationship_stage") for r in recent_records if r.get("relationship_stage")]
        if not stages_in_recent:
            return "稳定发展中"

        # 简单趋势分析
        first_stage_idx = stage_progress.get(stages_in_recent[0], 0)
        last_stage_idx = stage_progress.get(stages_in_recent[-1], 0)

        if last_stage_idx > first_stage_idx:
            return "关系递进中，发展趋势良好"
        elif last_stage_idx < first_stage_idx:
            return "关系有所波动，建议加强沟通"
        else:
            return "关系稳定，继续保持互动"
