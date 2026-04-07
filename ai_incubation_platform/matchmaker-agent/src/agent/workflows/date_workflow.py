"""
约会工作流

编排约会流程：活动推荐 -> 约见提议 -> 合规校验 -> 跟进记录
"""
from typing import Dict, List, Optional, Any
from utils.logger import logger
from agent.tools.activity_recommend_tool import ActivityRecommendTool
from agent.tools.date_proposal_tool import DateProposalTool
from agent.tools.compliance_tool import ComplianceTool
from agent.tools.followup_tool import FollowupTool


class DateWorkflow:
    """
    约会工作流

    执行步骤：
    1. 基于共同兴趣推荐活动
    2. 生成约见提议
    3. 合规校验
    4. 记录约会历史
    """

    def __init__(self):
        self.tools = {
            "activity_recommend": ActivityRecommendTool,
            "date_proposal": DateProposalTool,
            "compliance": ComplianceTool,
            "followup": FollowupTool
        }

    def execute(
        self,
        user_id: str,
        target_user_id: str,
        user_interests: List[str],
        target_interests: List[str],
        custom_message: Optional[str] = None,
        skip_compliance: bool = False
    ) -> dict:
        """
        执行约会工作流

        Args:
            user_id: 用户 ID
            target_user_id: 对象 ID
            user_interests: 用户兴趣列表
            target_interests: 对象兴趣列表
            custom_message: 自定义消息
            skip_compliance: 是否跳过合规校验

        Returns:
            约会工作流结果
        """
        logger.info(f"DateWorkflow: Starting for {user_id} -> {target_user_id}")

        result = {
            "workflow": "date",
            "user_id": user_id,
            "target_user_id": target_user_id,
            "steps": {},
            "errors": []
        }

        # 步骤 1: 活动推荐
        logger.info("DateWorkflow: Step 1 - Recommending activities")
        activity_result = ActivityRecommendTool.handle(
            user_interests=user_interests,
            target_interests=target_interests
        )
        result["steps"]["activity_recommend"] = activity_result

        if "error" in activity_result:
            result["errors"].append(f"Activity recommendation failed: {activity_result['error']}")
            return result

        # 步骤 2: 生成约见提议
        logger.info("DateWorkflow: Step 2 - Creating date proposal")
        suggested_activity = activity_result["recommendations"][0]["activity"] if activity_result["recommendations"] else "咖啡厅"
        location_type = suggested_activity.split()[0] if suggested_activity else "咖啡厅"

        proposal_result = DateProposalTool.handle(
            user_id=user_id,
            target_user_id=target_user_id,
            location_type=location_type,
            custom_message=custom_message
        )
        result["steps"]["date_proposal"] = proposal_result
        result["proposal"] = proposal_result

        # 步骤 3: 合规校验（可选）
        if not skip_compliance and custom_message:
            logger.info("DateWorkflow: Step 3 - Compliance check")
            compliance_result = ComplianceTool.handle(custom_message)
            result["steps"]["compliance_check"] = compliance_result

            if not compliance_result["passed"]:
                result["errors"].append(f"Compliance check failed: {compliance_result['issues']}")
                result["compliance_blocked"] = True
                return result
        else:
            result["steps"]["compliance_check"] = {"skipped": True}

        # 步骤 4: 记录约会提议历史
        logger.info("DateWorkflow: Step 4 - Recording followup")
        followup_result = FollowupTool.handle(
            user_id=user_id,
            target_user_id=target_user_id,
            action="date_proposal",
            notes=f"提议活动：{location_type}"
        )
        result["steps"]["followup_record"] = followup_result

        logger.info(f"DateWorkflow: Completed, proposal generated: {proposal_result.get('proposal_id')}")
        return result

    def get_workflow_schema(self) -> dict:
        """获取工作流 Schema"""
        return {
            "name": "date_workflow",
            "description": "约会工作流：活动推荐 -> 约见提议 -> 合规校验 -> 跟进记录",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "用户 ID"},
                    "target_user_id": {"type": "string", "description": "对象 ID"},
                    "user_interests": {"type": "array", "items": {"type": "string"}, "description": "用户兴趣"},
                    "target_interests": {"type": "array", "items": {"type": "string"}, "description": "对象兴趣"},
                    "custom_message": {"type": "string", "description": "自定义消息"},
                    "skip_compliance": {"type": "boolean", "description": "是否跳过合规校验", "default": False}
                },
                "required": ["user_id", "target_user_id", "user_interests", "target_interests"]
            },
            "steps": [
                {"name": "activity_recommend", "tool": "ActivityRecommendTool"},
                {"name": "date_proposal", "tool": "DateProposalTool"},
                {"name": "compliance_check", "tool": "ComplianceTool", "optional": True},
                {"name": "followup_record", "tool": "FollowupTool"}
            ]
        }
