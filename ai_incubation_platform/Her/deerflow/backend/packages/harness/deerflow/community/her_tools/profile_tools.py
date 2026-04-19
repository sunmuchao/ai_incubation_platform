"""
Her Tools - Profile Tools Module (精简版 v4.2)

资料相关工具：获取用户画像、更新用户偏好、创建用户档案

【Agent Native 设计】
- her_get_profile: 返回用户画像原始数据 + 缺失字段提示
- her_update_preference: 写操作，更新用户偏好到数据库
- her_create_profile: 创建新用户档案（当用户不存在时调用）

【Anthropic 建议】
- 返回高信号信息（name > UUID）
- 错误提示给修正方向
"""
import logging
import json
import re
import uuid as uuid_module
from typing import Type, Optional, Dict, Any
from datetime import datetime

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import (
    ToolResult,
    HerGetProfileInput,
    HerUpdatePreferenceInput,
    HerCreateProfileInput,
)
from .helpers import (
    ensure_her_in_path,
    run_async,
    get_current_user_id,
    get_db_user,
)

logger = logging.getLogger(__name__)


# ==================== Her Get Profile Tool ====================

class HerGetProfileTool(BaseTool):
    """
    Her 用户画像查询工具 - 获取任意用户画像（Agent Native 设计）

    返回用户画像原始数据 + 缺失字段提示，Agent 自行分析用户特点。
    """

    name: str = "her_get_profile"
    description: str = """
获取用户画像数据。

【能力】
返回用户的完整资料信息（兴趣、偏好等原始数据），并提示缺失字段。

【参数】
- user_id: 用户 ID（可选）
  - 不传或传 'me' → 返回当前用户
  - 传具体 ID → 返回该用户画像

【返回】
- display_id: 语义化标识符（如 'user_001'，方便你引用）
- user_profile: 用户完整画像（name、age、gender、location、interests 等）
- missing_fields: 缺失字段列表（用于引导用户补充资料）
- preference_status: 偏好完整性状态（complete/partial/incomplete）

【使用场景】
- 了解用户特点（话题推荐、开场白生成等）
- 了解匹配对象详情
- 检查用户资料完整性

【重要】
此工具只返回原始数据，你需要：
1. 自主分析用户特点并生成回复
2. 使用 display_id 或 name 来标识用户（不要用 user_id）
"""
    args_schema: Type[BaseModel] = HerGetProfileInput

    def _run(self, user_id: str = "me") -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id))
        except Exception as e:
            # Anthropic 建议：错误提示给修正方向
            error_msg = self._format_error(str(e), user_id)
            return json.dumps(ToolResult(success=False, error=error_msg).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    def _format_error(self, error: str, user_id: str) -> str:
        """格式化错误信息（Anthropic 建议：给修正方向）"""
        if "用户不存在" in error:
            return f"""用户不存在。

传入的 user_id: '{user_id}'

建议：
1. 如果你想查询当前用户，不传 user_id 或传 'me'
2. 如果你想查询某个候选人，请先调用 her_find_candidates 获取候选人列表，然后从中选择

示例：
- her_get_profile()  # 获取当前用户
- her_get_profile(user_id='me')  # 获取当前用户
- her_find_candidates() → 选择 candidate_001 → her_get_profile(user_id='candidate_001 的 user_id')"""
        return error

    async def _arun(self, user_id: str) -> ToolResult:
        """返回用户画像数据 + 缺失字段"""
        user = get_db_user(user_id)

        if not user:
            # Anthropic 建议：错误提示给修正方向
            return ToolResult(
                success=False,
                error=self._format_error("用户不存在", user_id)
            )

        # ===== 检查缺失字段 =====
        required_fields = ["name", "age", "gender", "location"]
        missing_fields = []
        for field in required_fields:
            if not user.get(field):
                missing_fields.append(field)

        # 检查关键偏好维度
        missing_preferences = []
        if not (user.get("preferred_location") or user.get("accept_remote")):
            missing_preferences.append("地点偏好")
        if not (user.get("preferred_age_min") and user.get("preferred_age_max")):
            missing_preferences.append("年龄偏好")
        if not user.get("relationship_goal"):
            missing_preferences.append("关系目标")

        # 偏好完整性状态
        if len(missing_preferences) == 0:
            preference_status = "complete"
        elif len(missing_preferences) < 3:
            preference_status = "partial"
        else:
            preference_status = "incomplete"

        # Anthropic 建议：添加 display_id（语义化标识符）
        # 使用用户 name 或简短 ID 作为 display_id
        display_id = user.get("name", "user_001")
        if not display_id or display_id == "匿名用户":
            # 如果没有名字，使用简短 ID
            short_id = user.get("id", "unknown")[:8]
            display_id = f"user_{short_id}"

        return ToolResult(
            success=True,
            data={
                "display_id": display_id,  # 语义化标识符
                "user_id": user.get("id"),  # 保留 UUID（用于后续操作）
                "user_profile": user,
                "missing_fields": missing_fields,
                "missing_preferences": missing_preferences,
                "preference_status": preference_status,
            }
        )


# ==================== Her Update Preference Tool ====================

class HerUpdatePreferenceTool(BaseTool):
    """
    Her 偏好更新工具 - 将用户回答写入数据库

    【Agent Native 设计】
    当用户在对话中表达偏好时，Agent 调用此工具写入数据库。
    """

    name: str = "her_update_preference"
    description: str = """
更新用户偏好到数据库。

【能力】
将用户在对话中表达的偏好写入数据库。

【参数】
- user_id: 用户 ID（可选，默认当前用户）
- dimension: 偏好维度
- value: 偏好值

【支持的维度】
- accept_remote: 异地接受度（"只找同城"/"同城优先"/"接受异地"）
- relationship_goal: 关系目标（"serious"/"marriage"/"dating"/"casual"）
- preferred_age_min: 年龄下限（数字）
- preferred_age_max: 年龄上限（数字）
- preferred_location: 偏好地点（城市名）

【使用场景】
当用户在对话中表达偏好时（如"只找同城"、"奔着结婚去"），调用此工具记录。

【返回】
- updated_dimension: 更新的维度
- updated_value: 更新后的值

【注意】
如果参数格式错误，工具会返回详细错误信息，请根据提示修正。
"""
    args_schema: Type[BaseModel] = HerUpdatePreferenceInput

    def _run(self, user_id: str = "me", dimension: str = "", value: str = "") -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, dimension, value))
        except Exception as e:
            # Anthropic 建议：错误提示给修正方向
            error_msg = self._format_update_error(str(e), dimension, value, user_id)
            return json.dumps(ToolResult(success=False, error=error_msg).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    def _format_update_error(self, error: str, dimension: str, value: str, user_id: str = "") -> str:
        """格式化更新错误信息（Anthropic 建议：给修正方向）"""
        if "不支持的维度" in error:
            return f"""不支持的维度。

传入的 dimension: '{dimension}'
支持的维度列表：
- accept_remote: 异地接受度
- relationship_goal: 关系目标
- preferred_age_min: 年龄下限
- preferred_age_max: 年龄上限
- preferred_location: 偏好地点

建议：请使用上述支持的维度名称。

示例：her_update_preference(dimension='accept_remote', value='只找同城')"""
        if "无法解析年龄值" in error:
            return f"""无法解析年龄值。

传入的 value: '{value}'
预期格式：数字（如 25、30）

建议：请直接传入数字年龄值。

示例：her_update_preference(dimension='preferred_age_min', value='25')"""
        if "用户不存在" in error:
            return f"""用户不存在。

传入的 user_id: '{user_id}'

建议：不传 user_id 或传 'me' 使用当前用户。

示例：her_update_preference(dimension='accept_remote', value='只找同城')"""
        return error

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
            # Anthropic 建议：错误提示给修正方向
            return ToolResult(
                success=False,
                error=self._format_update_error(f"不支持的维度: {dimension}", dimension, value, user_id)
            )

        # 值转换
        converted_value = value
        if db_field == "accept_remote":
            value_mapping = {
                "只找同城": "只找同城",
                "不接受异地": "只找同城",
                "同城优先": "同城优先",
                "接受异地": "接受异地",
                "可以接受异地": "接受异地",
                "视情况而定": "视情况而定",
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
                    # Anthropic 建议：错误提示给修正方向
                    return ToolResult(
                        success=False,
                        error=self._format_update_error(f"无法解析年龄值: {value}", dimension, value, user_id)
                    )

        # 更新数据库
        try:
            with db_session() as db:
                user = db.query(UserDB).filter(UserDB.id == user_id).first()
                if not user:
                    return ToolResult(
                        success=False,
                        error=self._format_update_error("用户不存在", dimension, value, user_id)
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
                    }
                )

        except Exception as e:
            logger.error(f"[her_update_preference] 更新失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )


# ==================== Her Create Profile Tool ====================

class HerCreateProfileTool(BaseTool):
    """
    Her 用户档案创建工具 - 创建新用户档案（Agent Native 设计）

    当 her_get_profile 返回"用户不存在"时，Agent 调用此工具创建用户档案。
    """

    name: str = "her_create_profile"
    description: str = """
创建新用户档案。

【能力】
将用户提供的基本信息写入数据库，创建用户档案。

【参数】
- name: 用户姓名（必填）
- age: 用户年龄（必填，18-150）
- gender: 用户性别（必填，male/female）
- location: 用户所在地（可选）
- occupation: 用户职业（可选）
- interests: 兴趣爱好列表（可选）
- relationship_goal: 关系目标（可选）
- bio: 个人简介（可选）
- accept_remote: 异地接受度（可选）
- preferred_age_min: 偏好年龄下限（可选）
- preferred_age_max: 偏好年龄上限（可选）

【返回】
- user_id: 创建的用户 ID（UUID 格式）
- user_profile: 创建的用户档案
- message: 创建成功提示

【使用场景】
- 当 her_get_profile 返回"用户不存在"时调用
- 新用户注册时调用

【重要】
此工具只创建用户档案，Agent 需要：
1. 从对话中提取用户信息
2. 调用此工具创建档案
3. 告知用户"您的档案已创建"
"""
    args_schema: Type[BaseModel] = HerCreateProfileInput

    def _run(
        self,
        name: str,
        age: int,
        gender: str,
        location: str = "",
        occupation: str = "",
        interests: list = [],
        relationship_goal: str = "",
        bio: str = "",
        accept_remote: str = "",
        preferred_age_min: int = 0,
        preferred_age_max: int = 0,
    ) -> str:
        try:
            result = run_async(self._arun(
                name=name,
                age=age,
                gender=gender,
                location=location,
                occupation=occupation,
                interests=interests,
                relationship_goal=relationship_goal,
                bio=bio,
                accept_remote=accept_remote,
                preferred_age_min=preferred_age_min,
                preferred_age_max=preferred_age_max,
            ))
        except Exception as e:
            error_msg = f"创建用户档案失败: {str(e)}"
            return json.dumps(ToolResult(success=False, error=error_msg).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(
        self,
        name: str,
        age: int,
        gender: str,
        location: str = "",
        occupation: str = "",
        interests: list = [],
        relationship_goal: str = "",
        bio: str = "",
        accept_remote: str = "",
        preferred_age_min: int = 0,
        preferred_age_max: int = 0,
    ) -> ToolResult:
        """创建用户档案"""
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        from db.models import UserDB

        # 参数校验
        if not name:
            return ToolResult(
                success=False,
                error="用户姓名不能为空"
            )
        if age < 18 or age > 150:
            return ToolResult(
                success=False,
                error="年龄必须在 18-150 之间"
            )
        if gender not in ["male", "female"]:
            return ToolResult(
                success=False,
                error="性别必须是 male 或 female"
            )

        # 生成 UUID
        user_id = str(uuid_module.uuid4())

        # 创建用户
        try:
            with db_session() as db:
                # 检查是否已存在同名用户（防止重复创建）
                existing = db.query(UserDB).filter(UserDB.name == name, UserDB.age == age).first()
                if existing:
                    # 已存在，返回现有用户信息
                    logger.info(f"[her_create_profile] 用户已存在: {existing.id}")
                    return ToolResult(
                        success=True,
                        data={
                            "user_id": existing.id,
                            "user_profile": {
                                "id": existing.id,
                                "name": existing.name,
                                "age": existing.age,
                                "gender": existing.gender,
                                "location": existing.location or "",
                                "occupation": existing.occupation or "",
                                "interests": json.loads(existing.interests) if existing.interests else [],
                                "relationship_goal": existing.relationship_goal or "",
                                "bio": existing.bio or "",
                                "accept_remote": existing.accept_remote or "",
                                "preferred_age_min": existing.preferred_age_min or 0,
                                "preferred_age_max": existing.preferred_age_max or 0,
                            },
                            "message": f"用户档案已存在，ID: {existing.id}",
                            "component_type": "UserProfileCard",
                        }
                    )

                # 创建新用户
                interests_json = json.dumps(interests) if interests else "[]"

                new_user = UserDB(
                    id=user_id,
                    name=name,
                    age=age,
                    gender=gender,
                    location=location,
                    occupation=occupation,
                    interests=interests_json,
                    relationship_goal=relationship_goal,
                    bio=bio,
                    accept_remote=accept_remote,
                    preferred_age_min=preferred_age_min,
                    preferred_age_max=preferred_age_max,
                    created_at=datetime.now(),
                )

                db.add(new_user)
                db.commit()

                logger.info(f"[her_create_profile] 用户档案创建成功: {user_id}")

                return ToolResult(
                    success=True,
                    data={
                        "user_id": user_id,
                        "user_profile": {
                            "id": user_id,
                            "name": name,
                            "age": age,
                            "gender": gender,
                            "location": location,
                            "occupation": occupation,
                            "interests": interests,
                            "relationship_goal": relationship_goal,
                            "bio": bio,
                            "accept_remote": accept_remote,
                            "preferred_age_min": preferred_age_min,
                            "preferred_age_max": preferred_age_max,
                        },
                        "message": f"用户档案创建成功，ID: {user_id}",
                        "component_type": "UserProfileCard",
                    }
                )

        except Exception as e:
            logger.error(f"[her_create_profile] 创建失败: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )


# ==================== Exports ====================

__all__ = [
    "HerGetProfileTool",
    "HerUpdatePreferenceTool",
    "HerCreateProfileTool",
]

# Tool instances for registration
her_get_profile_tool = HerGetProfileTool()
her_update_preference_tool = HerUpdatePreferenceTool()
her_create_profile_tool = HerCreateProfileTool()