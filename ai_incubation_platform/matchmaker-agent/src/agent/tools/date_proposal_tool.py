"""
约见提议工具

用于生成和管理约见提议，包括时间、地点协商。
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from utils.logger import logger
from agent.tools.compliance_tool import ComplianceTool


class DateProposalTool:
    """
    约见提议工具

    功能：
    - 生成约见提议模板
    - 校验约见内容合规性
    - 记录约见历史
    """

    name = "date_proposal"
    description = "生成和管理约见提议"
    tags = ["date", "proposal", "meetup"]

    # 推荐活动地点类型
    DATE_LOCATION_TYPES = [
        "咖啡厅",
        "餐厅",
        "公园",
        "博物馆",
        "电影院",
        "书店",
        "健身房",
        "展览"
    ]

    # 推荐活动
    DATE_ACTIVITIES = {
        "咖啡厅": ["闲聊", "桌游", "手冲体验"],
        "餐厅": ["共进晚餐", "美食探索", "DIY 料理"],
        "公园": ["散步", "野餐", "骑行"],
        "博物馆": ["观展", "文化探索", "艺术欣赏"],
        "电影院": ["看电影", "影评交流"],
        "书店": ["选书", "阅读分享", "签售会"],
        "健身房": ["运动", "瑜伽课", "攀岩"],
        "展览": ["观展", "摄影", "艺术交流"]
    }

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "发起用户 ID"
                },
                "target_user_id": {
                    "type": "string",
                    "description": "邀请对象 ID"
                },
                "location_type": {
                    "type": "string",
                    "description": "地点类型",
                    "enum": ["咖啡厅", "餐厅", "公园", "博物馆", "电影院", "书店", "健身房", "展览"]
                },
                "preferred_time": {
                    "type": "string",
                    "description": "期望时间（ISO 格式或自然语言）"
                },
                "custom_message": {
                    "type": "string",
                    "description": "自定义消息内容"
                }
            },
            "required": ["user_id", "target_user_id"]
        }

    @staticmethod
    def handle(
        user_id: str,
        target_user_id: str,
        location_type: Optional[str] = None,
        preferred_time: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> dict:
        """
        处理约见提议请求

        Args:
            user_id: 发起用户 ID
            target_user_id: 邀请对象 ID
            location_type: 地点类型
            preferred_time: 期望时间
            custom_message: 自定义消息

        Returns:
            约见提议结果
        """
        logger.info(f"DateProposalTool: Creating proposal for {user_id} -> {target_user_id}")

        result = {
            "proposal_id": f"dp_{user_id}_{target_user_id}_{int(datetime.now().timestamp())}",
            "status": "draft",
            "compliance_passed": True,
            "issues": []
        }

        # 生成时间建议
        if preferred_time:
            result["preferred_time"] = preferred_time
        else:
            result["suggested_times"] = DateProposalTool._get_suggested_times()

        # 生成地点建议
        if location_type:
            result["location_type"] = location_type
            result["suggested_activities"] = DateProposalTool.DATE_ACTIVITIES.get(location_type, [])
        else:
            result["suggested_location_types"] = DateProposalTool.DATE_LOCATION_TYPES[:5]

        # 生成提议消息
        if custom_message:
            # 合规校验
            compliance_result = ComplianceTool.handle(custom_message, check_type="content_only")
            if not compliance_result["passed"]:
                result["compliance_passed"] = False
                result["issues"] = compliance_result["issues"]
                logger.warning(f"DateProposalTool: Content compliance check failed: {result['issues']}")

            # 脱敏处理
            sanitized_message = ComplianceTool.sanitize_content(custom_message)
            result["message"] = sanitized_message
        else:
            # 生成默认消息模板
            result["message"] = DateProposalTool._generate_default_message(
                location_type or "咖啡厅",
                result.get("preferred_time") or result.get("suggested_times", ["周末下午"])[0]
            )

        # 记录提议历史
        DateProposalTool._record_proposal({
            "user_id": user_id,
            "target_user_id": target_user_id,
            "timestamp": datetime.now().isoformat(),
            "location_type": location_type,
            "status": "draft"
        })

        logger.info(f"DateProposalTool: Proposal generated: {result['proposal_id']}")
        return result

    @staticmethod
    def _get_suggested_times() -> List[str]:
        """获取建议的约见时间"""
        now = datetime.now()
        weekend = now + timedelta(days=(5 - now.weekday()) % 7)

        suggestions = [
            f"本周六下午 2-5 点",
            f"本周日下午 2-5 点",
            f"工作日晚上 7-9 点",
        ]
        return suggestions

    @staticmethod
    def _generate_default_message(location_type: str, time: str) -> str:
        """生成默认约见消息"""
        templates = {
            "咖啡厅": f"你好呀！想邀请你一起去咖啡厅坐坐，聊聊天放松一下～ {time} 你有空吗？",
            "餐厅": f"发现一家不错的餐厅，想邀请你一起去尝尝～ {time} 方便吗？",
            "公园": f"最近天气不错，想邀请你去公园散散步，呼吸新鲜空气～ {time} 怎么样？",
            "博物馆": f"最近有个有趣的展览，想邀请你一起去看～ {time} 有空一起去吗？",
            "电影院": f"最近上了几部新电影，想邀请你一起去看～ {time} 你方便吗？",
            "书店": f"知道一家很棒的书店，想邀请你一起去逛逛～ {time} 有兴趣吗？",
            "健身房": f"想邀请你一起运动一下，健健身出出汗～ {time} 你 OK 吗？",
            "展览": f"有个不错的艺术展，想邀请你一起去参观～ {time} 有时间一起去吗？",
        }
        return templates.get(location_type, f"想邀请你一起见面聊聊～ {time} 你方便吗？")

    # 内存存储约见历史
    _proposal_history: List[dict] = []

    @classmethod
    def _record_proposal(cls, proposal: dict) -> None:
        """记录约见提议历史"""
        cls._proposal_history.append(proposal)
        if len(cls._proposal_history) > 100:
            cls._proposal_history = cls._proposal_history[-50:]

    @classmethod
    def get_proposal_history(cls, user_id: str) -> List[dict]:
        """获取用户的约见提议历史"""
        return [
            p for p in cls._proposal_history
            if p.get("user_id") == user_id or p.get("target_user_id") == user_id
        ]
