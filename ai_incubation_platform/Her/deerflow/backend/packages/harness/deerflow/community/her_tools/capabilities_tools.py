"""
产品能力开关（单一真相来源）

返回结构化 JSON，供 Agent 在描述「提醒 / 通知」等能力时引用，避免口径漂移。
"""
import json
import logging
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import ToolResult, HerGetProductCapabilitiesInput

logger = logging.getLogger(__name__)

# 与客户端/运营配置对齐时可改为读环境变量或远程配置
HER_PRODUCT_CAPABILITIES = {
    "version": "1.0",
    "capabilities": [
        {
            "id": "match_pool_subscription",
            "user_visible_name_zh": "匹配池条件订阅提醒",
            "enabled": True,
            "description_zh": "当库中出现满足你当前筛选条件的新用户时，主动推送提醒。",
        },
        {
            "id": "social_interest_notifications",
            "user_visible_name_zh": "社交互动通知",
            "enabled": True,
            "description_zh": "当其他用户对你表达兴趣（如喜欢/点赞）或发送消息时，App 内消息或系统推送可提醒你（以客户端通知权限与设置为准）。",
        },
    ],
}


class HerGetProductCapabilitiesTool(BaseTool):
    """返回产品能力开关（提醒/通知等），仅原始数据。"""

    name: str = "her_get_product_capabilities"
    description: str = """
获取产品能力开关状态。

【能力】
返回通知/提醒等能力的开关状态（enabled 字段）。

【返回】
- product_capabilities: 能力列表，每个包含 enabled 状态

【使用场景】
当用户询问通知能力时（"会不会通知我"、"有没有提醒"）调用此工具。

【注意】
enabled 字段是唯一真相，描述能力时必须与之一致。
"""
    args_schema: Type[BaseModel] = HerGetProductCapabilitiesInput

    def _run(self, unused: str = "") -> str:
        return json.dumps(
            ToolResult(
                success=True,
                data={"product_capabilities": HER_PRODUCT_CAPABILITIES}
            ).model_dump(),
            ensure_ascii=False,
        )


her_get_product_capabilities_tool = HerGetProductCapabilitiesTool()

__all__ = [
    "HER_PRODUCT_CAPABILITIES",
    "HerGetProductCapabilitiesTool",
    "her_get_product_capabilities_tool",
]
