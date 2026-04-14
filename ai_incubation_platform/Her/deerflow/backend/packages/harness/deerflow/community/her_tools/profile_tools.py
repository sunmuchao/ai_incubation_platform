"""
Her Tools - Profile Tools Module

资料相关工具：信息收集、偏好更新
"""
import logging
import json
import re
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import (
    ToolResult,
    HerCollectProfileInput,
    HerUpdatePreferenceInput,
)
from .helpers import (
    ensure_her_in_path,
    run_async,
    get_current_user_id,
    get_db_user,
)

logger = logging.getLogger(__name__)


# ==================== Her Collect Profile Tool ====================

class HerCollectProfileTool(BaseTool):
    """Her 信息收集工具 - 查询用户信息缺失"""

    name: str = "her_collect_profile"
    description: str = """
查询用户信息缺失情况。返回需要收集的字段列表。

参数：user_id, trigger_reason
返回：{ need_collection: true/false, missing_fields: [...], user_profile: {...} }
"""
    args_schema: Type[BaseModel] = HerCollectProfileInput

    def _run(self, user_id: str, trigger_reason: str = "user_intent") -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, trigger_reason))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, trigger_reason: str = "user_intent") -> ToolResult:
        """
        查询用户信息缺失

        检查两类信息：
        1. 基本信息（必须）：name, age, gender, location
        2. 匹配偏好（关键维度）：地点偏好、年龄偏好、关系目标
        """
        user = get_db_user(user_id)

        if not user:
            return ToolResult(
                success=True,
                data={
                    "need_collection": True,
                    "missing_fields": ["name", "age", "gender", "location"],
                    "missing_preferences": ["preferred_location", "preferred_age", "relationship_goal"],
                    "user_profile": {},
                    "preference_status": "incomplete",
                },
                summary="新用户需要收集信息"
            )

        # ===== 检查基本字段 =====
        required_fields = ["name", "age", "gender", "location"]
        missing_fields = []

        for field in required_fields:
            if not user.get(field):
                missing_fields.append(field)

        # ===== 检查关键偏好维度 =====
        missing_preferences = []

        # 地点偏好
        has_location_preference = user.get("preferred_location") or user.get("accept_remote")
        if not has_location_preference:
            missing_preferences.append("location_preference (关键)")

        # 年龄偏好
        has_age_preference = user.get("preferred_age_min") and user.get("preferred_age_max")
        if not has_age_preference:
            missing_preferences.append("age_preference (关键)")

        # 关系目标
        if not user.get("relationship_goal"):
            missing_preferences.append("relationship_goal (关键)")

        # ===== 推荐字段 =====
        recommended_fields = ["occupation", "education", "interests"]
        for field in recommended_fields:
            if not user.get(field):
                missing_fields.append(f"{field} (推荐)")

        # ===== 偏好完整性状态 =====
        if len(missing_preferences) == 0:
            preference_status = "complete"
        elif len(missing_preferences) < 3:
            preference_status = "partial"
        else:
            preference_status = "incomplete"

        return ToolResult(
            success=True,
            data={
                "need_collection": len(missing_fields) > 0 or len(missing_preferences) > 0,
                "missing_fields": missing_fields,
                "missing_preferences": missing_preferences,
                "user_profile": user,
                "preference_status": preference_status,
                "critical_dimensions": {
                    "location_preference": has_location_preference,
                    "age_preference": has_age_preference,
                    "relationship_goal": user.get("relationship_goal") is not None,
                },
            },
            summary=f"基本信息缺失 {len(missing_fields)} 项，偏好缺失 {len(missing_preferences)} 项"
        )


# ==================== Her Update Preference Tool ====================

class HerUpdatePreferenceTool(BaseTool):
    """
    Her 偏好更新工具 - 将用户回答写入数据库

    【Agent Native 设计】
    当用户在对话中表达偏好时（如"只找同城"、"奔着结婚去"），Agent 调用此工具写入数据库。
    """

    name: str = "her_update_preference"
    description: str = """
更新用户偏好。将用户在对话中表达的偏好写入数据库。

参数：
- user_id: 用户 ID（可选，默认使用当前用户）
- dimension: 偏好维度（accept_remote, relationship_goal, preferred_age_min, preferred_age_max, preferred_location）
- value: 偏好值

返回：{ success: true/false, updated_dimension: "...", updated_value: "..." }

Agent 应该：
- 当用户明确表达偏好时调用此工具（如"我只找同城的" → dimension="accept_remote", value="只找同城"）
- 更新后记住这个偏好，下次对话不要再问
"""
    args_schema: Type[BaseModel] = HerUpdatePreferenceInput

    def _run(self, user_id: str, dimension: str, value: str) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, dimension, value))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, dimension: str, value: str) -> ToolResult:
        """更新用户偏好到数据库"""
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        from db.models import UserDB

        # 支持的维度列表
        supported_dimensions = {
            "accept_remote": "accept_remote",
            "relationship_goal": "relationship_goal",
            "preferred_age_min": "preferred_age_min",
            "preferred_age_max": "preferred_age_max",
            "preferred_location": "preferred_location",
            # 兼容中文维度名
            "异地接受度": "accept_remote",
            "关系目标": "relationship_goal",
            "偏好年龄下限": "preferred_age_min",
            "偏好年龄上限": "preferred_age_max",
            "偏好地点": "preferred_location",
        }

        # 检查维度是否支持
        db_field = supported_dimensions.get(dimension)
        if not db_field:
            return ToolResult(
                success=False,
                error=f"不支持的维度: {dimension}",
                summary=f"无法更新维度 {dimension}"
            )

        # 值转换（处理用户自然语言表达）
        converted_value = value
        if db_field == "accept_remote":
            value_mapping = {
                "只找同城": "只找同城",
                "不接受异地": "只找同城",
                "同城优先": "同城优先",
                "接受异地": "接受异地",
                "可以接受异地": "接受异地",
                "视情况而定": "视情况而定",
                "有缘分可以接受": "视情况而定",
            }
            converted_value = value_mapping.get(value, value)
        elif db_field == "relationship_goal":
            goal_mapping = {
                "认真恋爱": "serious",
                "认真": "serious",
                "奔着结婚": "marriage",
                "结婚": "marriage",
                "轻松交友": "dating",
                "交友": "dating",
                "随便聊聊": "casual",
            }
            converted_value = goal_mapping.get(value, value)
        elif db_field in ["preferred_age_min", "preferred_age_max"]:
            try:
                converted_value = int(value)
            except ValueError:
                match = re.search(r'\d+', value)
                if match:
                    converted_value = int(match.group())
                else:
                    return ToolResult(
                        success=False,
                        error=f"无法解析年龄值: {value}",
                        summary=f"年龄格式错误"
                    )

        # 更新数据库
        try:
            with db_session() as db:
                user = db.query(UserDB).filter(UserDB.id == user_id).first()
                if not user:
                    return ToolResult(
                        success=False,
                        error="用户不存在",
                        summary="无法找到用户"
                    )

                setattr(user, db_field, converted_value)
                db.commit()

                logger.info(f"[her_update_preference] 已更新用户 {user_id} 的 {db_field} = {converted_value}")

                return ToolResult(
                    success=True,
                    data={
                        "updated_dimension": db_field,
                        "updated_value": converted_value,
                        "user_id": user_id,
                    },
                    summary=f"已更新 {dimension} 为 {converted_value}"
                )

        except Exception as e:
            logger.error(f"[her_update_preference] 更新失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                summary=f"更新 {dimension} 失败"
            )


# ==================== Exports ====================

__all__ = [
    "HerCollectProfileTool",
    "HerUpdatePreferenceTool",
]

# Tool instances for registration
her_collect_profile_tool = HerCollectProfileTool()
her_update_preference_tool = HerUpdatePreferenceTool()