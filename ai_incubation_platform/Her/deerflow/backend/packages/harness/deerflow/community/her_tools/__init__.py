"""
Her Tools - DeerFlow Tools for Her Project

【Agent Native 架构】
DeerFlow Agent 是唯一的决策大脑，负责意图理解、数据解读、建议生成。
her_tools 只做数据查询，不包含任何业务逻辑或模板！

正确的执行循环：
```
用户消息 → Agent 思考(Thinking) → 选择工具 → 执行工具(纯数据查询) → 返回原始数据
                                                                      ↓
                                    Agent 解读数据(Thinking) → 生成个性化建议
                                                                      ↓
                                    输出回复 → 完成
```

工具列表（全部为纯数据查询）：
- her_find_matches: 查询数据库匹配对象（返回候选人列表）
- her_daily_recommend: 查询今日推荐（返回活跃用户列表）
- her_analyze_compatibility: 查询用户画像对比（返回双方原始数据）
- her_analyze_relationship: 查询关系数据（返回匹配记录和互动数据）
- her_suggest_topics: 查询用户画像和对话历史（让 Agent 自己生成话题）
- her_get_icebreaker: 查询双方画像（让 Agent 自己生成开场白）
- her_plan_date: 查询双方画像和活动选项（让 Agent 自己生成约会方案）
- her_collect_profile: 查询用户信息缺失字段

设计原则（Agent Native）：
- 所有工具只返回原始数据（JSON）
- 工具内部不包含业务判断、不生成建议、不返回模板
- Agent 根据返回的数据自主思考、解读、生成个性化建议
- 模板和硬编码逻辑已全部移除，Agent 应根据具体情况创造建议

版本历史：
- v1.0: 硬编码模板（如 interest_topics 字典）
- v2.0: Agent Native 重构，工具只返回数据，Agent 自己生成建议
"""

import logging
import json
from typing import Optional, Type, Dict, Any, List
from pydantic import BaseModel, Field

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


# ==================== Output Schemas ====================

class MatchResult(BaseModel):
    """单个匹配结果"""
    user_id: str = Field(description="用户 ID")
    name: str = Field(description="姓名")
    age: int = Field(default=0, description="年龄")
    location: str = Field(default="", description="所在地")
    gender: str = Field(default="", description="性别")
    interests: List[str] = Field(default_factory=list, description="兴趣爱好")
    bio: str = Field(default="", description="简介")


class ToolResult(BaseModel):
    """工具统一返回格式"""
    success: bool = Field(description="是否成功")
    data: Dict[str, Any] = Field(default_factory=dict, description="结构化数据")
    summary: str = Field(default="", description="一句话总结，用于 Agent 理解")
    error: str = Field(default="", description="错误信息")


# ==================== Input Schemas ====================

class HerFindMatchesInput(BaseModel):
    """查找匹配对象的输入参数"""
    user_id: str = Field(description="用户 ID")
    intent: str = Field(default="", description="用户意图描述")
    limit: int = Field(default=5, description="返回数量")


class HerDailyRecommendInput(BaseModel):
    """每日推荐的输入参数"""
    user_id: str = Field(description="用户 ID")


class HerAnalyzeCompatibilityInput(BaseModel):
    """兼容性分析的输入参数"""
    user_id: str = Field(description="用户 ID")
    target_user_id: str = Field(description="目标用户 ID")


class HerAnalyzeRelationshipInput(BaseModel):
    """关系分析的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(description="匹配记录 ID")


class HerSuggestTopicsInput(BaseModel):
    """话题推荐的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(default="", description="匹配记录 ID")
    context: str = Field(default="", description="对话上下文")


class HerGetIcebreakerInput(BaseModel):
    """破冰建议的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(default="", description="匹配记录 ID")
    target_name: str = Field(default="TA", description="目标用户姓名")


class HerPlanDateInput(BaseModel):
    """约会策划的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(default="", description="匹配记录 ID")
    target_name: str = Field(default="TA", description="约会对象姓名")
    location: str = Field(default="", description="约会地点")
    preferences: str = Field(default="", description="偏好设置")


class HerCollectProfileInput(BaseModel):
    """信息收集的输入参数"""
    user_id: str = Field(description="用户 ID")
    trigger_reason: str = Field(default="user_intent", description="触发原因")


# ==================== Helper Functions ====================

def get_her_root() -> str:
    """获取 Her 项目根目录"""
    import os
    return os.environ.get("HER_PROJECT_ROOT", os.getcwd())


def ensure_her_in_path():
    """确保 Her 项目在 Python 路径中"""
    import sys
    her_root = get_her_root()
    src_path = her_root + "/src"
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def get_current_user_id() -> str:
    """
    获取当前用户 ID（支持用户隔离）

    优先级：
    1. 从 LangGraph configurable 中获取（DeerFlowClient 传入的 user_id）
    2. 从用户独立的 memory 文件中读取
    3. 从全局 memory.json 中读取（降级）
    """
    import os
    import json

    try:
        # 方式1：从 LangGraph configurable 中获取（最高优先级）
        from langgraph.config import get_config
        config = get_config()
        user_id = config.get("configurable", {}).get("user_id")
        if user_id:
            logger.info(f"[get_current_user_id] 从 configurable 获取: {user_id}")
            return user_id

        # 方式2：从用户独立的 memory 文件中读取
        her_root = get_her_root()
        users_dir = os.path.join(her_root, "deerflow", "backend", ".deer-flow", "users")

        if os.path.exists(users_dir):
            # 找到所有用户目录
            user_dirs = [d for d in os.listdir(users_dir) if os.path.isdir(os.path.join(users_dir, d))]
            if user_dirs:
                # 取最近更新的用户目录（假设只有一个活跃用户）
                latest_user = None
                latest_mtime = 0
                for user_dir in user_dirs:
                    user_memory_path = os.path.join(users_dir, user_dir, "memory.json")
                    if os.path.exists(user_memory_path):
                        mtime = os.path.getmtime(user_memory_path)
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                            latest_user = user_dir

                if latest_user:
                    logger.info(f"[get_current_user_id] 从用户独立文件获取: {latest_user}")
                    return latest_user

        # 方式3：从全局 memory.json 中读取（降级）
        memory_path = os.path.join(her_root, "deerflow", "backend", ".deer-flow", "memory.json")

        if os.path.exists(memory_path):
            with open(memory_path, "r") as f:
                memory_data = json.load(f)

            facts = memory_data.get("facts", [])
            for fact in facts:
                fact_id = fact.get("id", "")
                if fact_id.startswith("user-id-"):
                    return fact_id.replace("user-id-", "")

                content = fact.get("content", "")
                if "用户ID：" in content:
                    import re
                    match = re.search(r'用户ID[:\s：]+([a-f0-9-]+)', content)
                    if match:
                        return match.group(1)

    except Exception as e:
        logger.warning(f"[get_current_user_id] 提取失败: {e}")

    return "user-anonymous-dev"


def run_async(coro):
    """安全执行异步协程"""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=30.0)
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()


def _get_db_user(user_id: str) -> Optional[Dict[str, Any]]:
    """从数据库获取用户信息（包含偏好字段）"""
    ensure_her_in_path()
    from utils.db_session_manager import db_session
    from db.models import UserDB

    with db_session() as db:
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if user:
            interests = []
            if user.interests:
                try:
                    interests = json.loads(user.interests)
                except:
                    interests = user.interests.split(",")

            # 基本信息
            user_data = {
                "id": user.id,
                "name": user.name or "",
                "age": user.age or 0,
                "gender": user.gender or "",
                "location": user.location or "",
                "interests": interests[:5],
                "bio": user.bio or "",
                "relationship_goal": getattr(user, 'relationship_goal', None) or "",
            }

            # ===== 偏好字段（用于匹配筛选）=====
            user_data["preferred_age_min"] = getattr(user, 'preferred_age_min', None)
            user_data["preferred_age_max"] = getattr(user, 'preferred_age_max', None)
            user_data["preferred_location"] = getattr(user, 'preferred_location', None)
            user_data["accept_remote"] = getattr(user, 'accept_remote', None)  # 是否接受异地
            user_data["want_children"] = getattr(user, 'want_children', None)
            user_data["spending_style"] = getattr(user, 'spending_style', None)

            # ===== 扩展偏好 =====
            user_data["family_importance"] = getattr(user, 'family_importance', None)
            user_data["work_life_balance"] = getattr(user, 'work_life_balance', None)
            user_data["migration_willingness"] = getattr(user, 'migration_willingness', None)
            user_data["sleep_type"] = getattr(user, 'sleep_type', None)

            return user_data
    return None


# ==================== Tools ====================

class HerFindMatchesTool(BaseTool):
    """Her 匹配工具 - 直接查询数据库"""

    name: str = "her_find_matches"
    description: str = """
查找匹配对象。从数据库查询候选用户。

参数：
- user_id: 用户 ID（可选，默认使用当前用户）
- intent: 用户意图描述（可选，Agent 会解读）
- limit: 返回数量（默认 5）

返回：{ matches: [...], total: N }
"""
    args_schema: Type[BaseModel] = HerFindMatchesInput

    def _run(self, user_id: str, intent: str = "", limit: int = 5) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, intent, limit))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, intent: str = "", limit: int = 5) -> ToolResult:
        """
        查询数据库匹配对象，使用用户偏好进行筛选

        筛选逻辑：
        1. 年龄范围：preferred_age_min ~ preferred_age_max
        2. 地点：preferred_location（同城优先）
        3. 异地：accept_remote（是否接受异地）
        4. 性别：异性
        5. 关系目标：匹配
        """
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        from db.models import UserDB

        # ===== 第一步：获取用户偏好 =====
        user_prefs = _get_db_user(user_id)
        if not user_prefs:
            return ToolResult(
                success=False,
                error="用户不存在",
                summary="无法获取用户信息"
            )

        # 提取关键偏好
        preferred_age_min = user_prefs.get("preferred_age_min") or 18
        preferred_age_max = user_prefs.get("preferred_age_max") or 60
        preferred_location = user_prefs.get("preferred_location") or user_prefs.get("location")
        accept_remote = user_prefs.get("accept_remote")  # "同城优先", "接受异地", "只找同城"
        user_gender = user_prefs.get("gender")
        user_relationship_goal = user_prefs.get("relationship_goal")

        logger.info(f"[her_find_matches] 用户偏好: age={preferred_age_min}-{preferred_age_max}, "
                    f"location={preferred_location}, accept_remote={accept_remote}, "
                    f"gender={user_gender}, goal={user_relationship_goal}")

        # ===== 第二步：构建查询条件 =====
        matches = []
        with db_session() as db:
            query = db.query(UserDB).filter(
                UserDB.id != user_id,
                UserDB.is_active == True,
                UserDB.is_permanently_banned == False
            )

            # 年龄范围筛选
            if preferred_age_min and preferred_age_max:
                query = query.filter(
                    UserDB.age >= preferred_age_min,
                    UserDB.age <= preferred_age_max
                )

            # 性别筛选（异性）
            if user_gender:
                opposite_gender = "female" if user_gender == "male" else "male"
                query = query.filter(UserDB.gender == opposite_gender)

            # 关系目标筛选（可选，宽松匹配）
            # 注：不强制要求完全匹配，让 Agent 自己判断

            # ===== 第三步：执行查询 =====
            # 先查询所有符合条件的用户
            candidates = query.order_by(UserDB.created_at.desc()).limit(limit * 3).all()

            # ===== 第四步：地点筛选（分两轮）=====
            # 第一轮：同城优先
            same_city_matches = []
            remote_matches = []

            for u in candidates:
                interests = u.interests.split(",")[:5] if u.interests else []
                match_data = {
                    "user_id": u.id,
                    "name": u.name or "匿名用户",
                    "age": u.age or 0,
                    "gender": u.gender or "",
                    "location": u.location or "",
                    "interests": interests,
                    "bio": u.bio or "",
                    "relationship_goal": getattr(u, 'relationship_goal', '') or "",
                    "want_children": getattr(u, 'want_children', None),
                }

                # 判断是否同城
                is_same_city = False
                if preferred_location and u.location:
                    # 简单的城市匹配（可以后续优化为地理距离计算）
                    is_same_city = preferred_location == u.location or \
                                   preferred_location in u.location or \
                                   u.location in preferred_location

                if is_same_city:
                    same_city_matches.append(match_data)
                else:
                    remote_matches.append(match_data)

            # ===== 第五步：根据异地偏好组合结果 =====
            if accept_remote == "只找同城":
                # 只返回同城
                matches = same_city_matches[:limit]
            elif accept_remote == "接受异地":
                # 同城 + 异地混合
                matches = same_city_matches + remote_matches[:limit - len(same_city_matches)]
            else:
                # 默认：同城优先，不足时补充异地
                matches = same_city_matches[:limit]
                if len(matches) < limit:
                    matches.extend(remote_matches[:limit - len(matches)])

            # 如果没有同城匹配，但用户没说"只找同城"，可以补充异地
            if len(matches) == 0 and len(remote_matches) > 0 and accept_remote != "只找同城":
                matches = remote_matches[:limit]

        # ===== 第六步：返回结果（包含筛选信息）=====
        result_data = {
            "matches": matches,
            "total": len(matches),
            "filter_applied": {
                "age_range": f"{preferred_age_min}-{preferred_age_max}",
                "preferred_location": preferred_location,
                "accept_remote": accept_remote,
                "same_city_count": len(same_city_matches),
                "remote_count": len(remote_matches),
            },
            "user_preferences": {
                "preferred_age_min": preferred_age_min,
                "preferred_age_max": preferred_age_max,
                "preferred_location": preferred_location,
                "accept_remote": accept_remote,
                "relationship_goal": user_relationship_goal,
            }
        }

        summary = f"找到 {len(matches)} 位候选对象"
        if len(same_city_matches) == 0 and len(remote_matches) > 0:
            summary += "（均为异地，请确认是否接受）"

        return ToolResult(
            success=True,
            data=result_data,
            summary=summary
        )


class HerDailyRecommendTool(BaseTool):
    """Her 每日推荐工具 - 查询数据库"""

    name: str = "her_daily_recommend"
    description: str = """
获取每日精选推荐。查询最新活跃用户。

参数：user_id: 用户 ID（可选，默认使用当前用户）
返回：{ recommendations: [...], total: N }
"""
    args_schema: Type[BaseModel] = HerDailyRecommendInput

    def _run(self, user_id: str) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str) -> ToolResult:
        """查询数据库"""
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        from db.models import UserDB

        recommendations = []
        with db_session() as db:
            query = db.query(UserDB).filter(
                UserDB.id != user_id,
                UserDB.is_active == True,
            ).order_by(UserDB.last_login.desc() if hasattr(UserDB, 'last_login') else UserDB.created_at.desc())

            users = query.limit(3).all()

            for u in users:
                recommendations.append({
                    "user_id": u.id,
                    "name": u.name or "匿名",
                    "age": u.age or 0,
                    "location": u.location or "",
                    "interests": u.interests.split(",")[:3] if u.interests else [],
                })

        return ToolResult(
            success=True,
            data={"recommendations": recommendations, "total": len(recommendations)},
            summary=f"今日精选 {len(recommendations)} 位"
        )


class HerAnalyzeCompatibilityTool(BaseTool):
    """Her 兼容性分析工具 - 查询用户画像对比"""

    name: str = "her_analyze_compatibility"
    description: str = """
分析两个用户的兼容性。查询双方画像数据。

参数：user_id（可选）, target_user_id
返回：{ user_a: {...}, user_b: {...}, comparison_factors: [...] }
"""
    args_schema: Type[BaseModel] = HerAnalyzeCompatibilityInput

    def _run(self, user_id: str, target_user_id: str) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, target_user_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, target_user_id: str) -> ToolResult:
        """查询双方画像"""
        user_a = _get_db_user(user_id)
        user_b = _get_db_user(target_user_id)

        if not user_a or not user_b:
            return ToolResult(success=False, error="用户不存在", summary="查询失败")

        # 简单的对比因素（让 Agent 自己解读）
        comparison_factors = []

        # 年龄差距
        if user_a.get("age") and user_b.get("age"):
            age_diff = abs(user_a["age"] - user_b["age"])
            comparison_factors.append({
                "factor": "年龄差距",
                "value": f"{age_diff}岁",
                "user_a": user_a["age"],
                "user_b": user_b["age"],
            })

        # 地点
        comparison_factors.append({
            "factor": "所在地",
            "user_a": user_a.get("location", "未知"),
            "user_b": user_b.get("location", "未知"),
            "same_city": user_a.get("location") == user_b.get("location"),
        })

        # 共同兴趣
        interests_a = set(user_a.get("interests", []))
        interests_b = set(user_b.get("interests", []))
        common_interests = list(interests_a & interests_b)
        comparison_factors.append({
            "factor": "兴趣爱好",
            "user_a": user_a.get("interests", []),
            "user_b": user_b.get("interests", []),
            "common": common_interests,
        })

        # 关系目标
        comparison_factors.append({
            "factor": "关系目标",
            "user_a": user_a.get("relationship_goal", "未设置"),
            "user_b": user_b.get("relationship_goal", "未设置"),
        })

        return ToolResult(
            success=True,
            data={
                "user_a": user_a,
                "user_b": user_b,
                "comparison_factors": comparison_factors,
            },
            summary=f"对比 {user_a.get('name')} 和 {user_b.get('name')} 的画像"
        )


class HerAnalyzeRelationshipTool(BaseTool):
    """Her 关系分析工具 - 查询关系数据"""

    name: str = "her_analyze_relationship"
    description: str = """
分析关系健康度。查询匹配记录和互动数据。

参数：user_id（可选）, match_id（对方用户 ID）
返回：{ match_info: {...}, interactions: [...] }
"""
    args_schema: Type[BaseModel] = HerAnalyzeRelationshipInput

    def _run(self, user_id: str, match_id: str) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str) -> ToolResult:
        """查询关系数据"""
        user_a = _get_db_user(user_id)
        user_b = _get_db_user(match_id)

        if not user_a or not user_b:
            return ToolResult(success=False, error="用户不存在", summary="查询失败")

        # 查询匹配记录（如果有）
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        try:
            from db.models import MatchDB
            with db_session() as db:
                match_record = db.query(MatchDB).filter(
                    (MatchDB.user_id_a == user_id) | (MatchDB.user_id_a == match_id),
                    (MatchDB.user_id_b == match_id) | (MatchDB.user_id_b == user_id),
                ).first()

                match_info = {
                    "status": match_record.status if match_record else "pending",
                    "created_at": str(match_record.created_at) if match_record else None,
                    "compatibility_score": match_record.compatibility_score if match_record else 0.5,
                }
        except:
            match_info = {"status": "unknown", "compatibility_score": 0.5}

        return ToolResult(
            success=True,
            data={
                "user_a": user_a,
                "user_b": user_b,
                "match_info": match_info,
            },
            summary=f"分析 {user_a.get('name')} 和 {user_b.get('name')} 的关系"
        )


class HerSuggestTopicsTool(BaseTool):
    """
    Her 话题推荐工具 - 纯数据查询

    【Agent Native 设计】
    此工具只返回原始数据，不生成话题模板。
    Agent（LLM）根据返回的用户画像自主生成个性化话题。

    返回数据：
    - 用户画像（兴趣、性格、沟通风格）
    - 目标用户画像（如果有 match_id）
    - 对话历史（已聊话题，用于避免重复）

    Agent 的职责：
    - 分析双方的共同点和差异
    - 考虑关系阶段控制话题深度
    - 避免已聊过的重复话题
    - 根据具体情况创造话题
    """

    name: str = "her_suggest_topics"
    description: str = """
获取话题推荐所需的数据。返回用户画像和目标用户画像。

此工具只返回原始数据，不生成话题。Agent 需要根据数据自主创造话题。

参数：
- user_id: 用户 ID（可选，默认使用当前用户）
- match_id: 匹配对象 ID（可选）
- context: 对话上下文（可选）

返回：{ user_profile: {...}, target_profile: {...}, conversation_history: [...] }

Agent 应该：
1. 分析双方画像，找出共同点
2. 考虑关系阶段（初识/熟悉/亲密）
3. 避免已聊过的话题
4. 根据具体情况创造个性化话题
"""
    args_schema: Type[BaseModel] = HerSuggestTopicsInput

    def _run(self, user_id: str, match_id: str = "", context: str = "") -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id, context))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str = "", context: str = "") -> ToolResult:
        """
        返回用户画像数据（不生成话题模板）

        Agent 根据这些数据自主创造话题：
        - 用户兴趣 → 可作为话题切入点
        - 目标用户兴趣 → 找共同点
        - 对话历史 → 避免重复
        """
        # 获取用户画像
        user = _get_db_user(user_id) or {}

        # 获取目标用户画像（如果有）
        target_user = _get_db_user(match_id) if match_id else None

        # 获取对话历史（已聊话题）
        conversation_history = []
        if match_id:
            conversation_history = await self._get_conversation_history(user_id, match_id)

        # 分析共同兴趣
        user_interests = set(user.get("interests", []))
        target_interests = set(target_user.get("interests", []) if target_user else [])
        common_interests = list(user_interests & target_interests)

        # 分析兴趣差异
        unique_user_interests = list(user_interests - target_interests)
        unique_target_interests = list(target_interests - user_interests)

        # 只返回数据，让 Agent 自己生成话题
        result_data = {
            "user_profile": {
                "interests": user.get("interests", []),
                "location": user.get("location", ""),
                "age": user.get("age", 0),
                "bio": user.get("bio", ""),
            },
            "target_profile": target_user if target_user else None,
            "conversation_history": conversation_history,
            "analysis": {
                "common_interests": common_interests,
                "unique_user_interests": unique_user_interests,
                "unique_target_interests": unique_target_interests,
                "history_count": len(conversation_history),
            },
            "hint": "Agent 应根据数据自主生成话题，考虑：共同点、关系阶段、避免重复",
        }

        return ToolResult(
            success=True,
            data=result_data,
            summary=f"用户有 {len(user_interests)} 个兴趣，共同兴趣 {len(common_interests)} 个"
        )

    async def _get_conversation_history(self, user_id: str, match_id: str) -> List[Dict]:
        """获取对话历史（已聊话题）"""
        ensure_her_in_path()
        try:
            from utils.db_session_manager import db_session
            from db.models import MessageDB

            with db_session() as db:
                messages = db.query(MessageDB).filter(
                    ((MessageDB.sender_id == user_id) & (MessageDB.receiver_id == match_id)) |
                    ((MessageDB.sender_id == match_id) & (MessageDB.receiver_id == user_id))
                ).order_by(MessageDB.created_at.desc()).limit(20).all()

                return [
                    {
                        "content": m.content,
                        "sender": m.sender_id,
                        "created_at": str(m.created_at),
                    }
                    for m in messages
                ]
        except Exception as e:
            logger.warning(f"[her_suggest_topics] 获取对话历史失败: {e}")
            return []


class HerGetIcebreakerTool(BaseTool):
    """
    Her 破冰建议工具 - 纯数据查询

    【Agent Native 设计】
    此工具只返回原始数据，不生成破冰模板。
    Agent（LLM）根据返回的用户画像自主生成个性化开场白。

    返回数据：
    - 用户画像（兴趣、简介）
    - 目标用户画像（兴趣、简介、照片描述）
    - 双方的匹配点分析

    Agent 的职责：
    - 分析目标用户特点
    - 找到可以切入的匹配点
    - 考虑目标用户的性格选择开场风格
    - 创造个性化的开场白（避免通用模板）
    """

    name: str = "her_get_icebreaker"
    description: str = """
获取破冰开场所需的数据。返回用户和目标用户画像。

此工具只返回原始数据，不生成开场白。Agent 需要根据数据自主创造开场白。

参数：
- user_id: 用户 ID（可选，默认使用当前用户）
- match_id: 目标用户 ID（可选）
- target_name: 目标用户姓名（可选，用于显示）

返回：{ user_profile: {...}, target_profile: {...}, match_points: [...] }

Agent 应该：
1. 分析目标用户的兴趣、简介、照片
2. 找到可以切入的匹配点（共同兴趣等）
3. 考虑目标用户性格选择开场风格
4. 创造个性化开场白（避免"Hi你好"等通用模板）
"""
    args_schema: Type[BaseModel] = HerGetIcebreakerInput

    def _run(self, user_id: str, match_id: str = "", target_name: str = "TA") -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id, target_name))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str = "", target_name: str = "TA") -> ToolResult:
        """
        返回用户画像数据（不生成破冰模板）

        Agent 根据这些数据自主创造开场白：
        - 目标用户兴趣 → 可以作为切入点
        - 目标用户简介 → 了解对方特点
        - 双方共同点 → 有针对性的开场
        """
        # 获取用户画像
        user = _get_db_user(user_id) or {}

        # 获取目标用户画像
        target_user = _get_db_user(match_id) if match_id else None

        if not target_user:
            # 没有目标用户，只返回用户自己的数据
            return ToolResult(
                success=True,
                data={
                    "user_profile": user,
                    "target_profile": None,
                    "match_points": [],
                    "hint": "缺少目标用户信息，Agent 可以询问用户想和谁破冰",
                },
                summary="缺少目标用户信息"
            )

        # 分析匹配点
        user_interests = set(user.get("interests", []))
        target_interests = set(target_user.get("interests", []))
        common_interests = list(user_interests & target_interests)

        # 地点匹配
        same_location = user.get("location") == target_user.get("location")

        # 构建匹配点列表
        match_points = []
        if common_interests:
            match_points.append({
                "type": "interest",
                "content": common_interests,
                "hint": "可以围绕共同兴趣开场",
            })
        if same_location:
            match_points.append({
                "type": "location",
                "content": user.get("location"),
                "hint": "可以围绕同城开场",
            })

        # 目标用户独特特点（可以作为话题）
        unique_target_interests = list(target_interests - user_interests)
        if unique_target_interests:
            match_points.append({
                "type": "target_unique",
                "content": unique_target_interests,
                "hint": "可以围绕对方的独特兴趣开场（显示你看了对方资料）",
            })

        # 只返回数据，让 Agent 自己生成开场白
        result_data = {
            "user_profile": {
                "interests": user.get("interests", []),
                "location": user.get("location", ""),
                "bio": user.get("bio", ""),
            },
            "target_profile": {
                "name": target_user.get("name", target_name),
                "interests": target_user.get("interests", []),
                "location": target_user.get("location", ""),
                "bio": target_user.get("bio", ""),
                "age": target_user.get("age", 0),
            },
            "match_points": match_points,
            "hint": "Agent 应根据匹配点创造个性化开场白，避免'Hi你好'等通用模板",
        }

        return ToolResult(
            success=True,
            data=result_data,
            summary=f"目标用户 {target_user.get('name', target_name)} 有 {len(target_interests)} 个兴趣，共同兴趣 {len(common_interests)} 个"
        )


class HerPlanDateTool(BaseTool):
    """
    Her 约会策划工具 - 纯数据查询

    【Agent Native 设计】
    此工具只返回原始数据，不生成约会模板。
    Agent（LLM）根据返回的用户画像和地点信息自主生成约会方案。

    返回数据：
    - 用户画像（兴趣、预算偏好）
    - 目标用户画像（兴趣、地点）
    - 常见约会地点类型和活动类型

    Agent 的职责：
    - 分析双方共同兴趣和地点
    - 考虑关系阶段选择约会类型
    - 考虑预算和时间偏好
    - 创造具体的约会方案（避免"附近咖啡厅"等模糊建议）
    """

    name: str = "her_plan_date"
    description: str = """
获取约会策划所需的数据。返回用户画像和地点信息。

此工具只返回原始数据，不生成约会方案。Agent 需要根据数据自主创造约会方案。

参数：
- user_id: 用户 ID（可选，默认使用当前用户）
- match_id: 约会对象 ID（可选）
- target_name: 约会对象姓名（可选）
- location: 约会地点范围（可选）
- preferences: 偏好设置（可选）

返回：{ user_profile: {...}, target_profile: {...}, activity_options: [...] }

Agent 应该：
1. 分析双方共同兴趣
2. 考虑关系阶段选择约会类型（初次约会 vs 熟悉约会）
3. 考虑地点和预算
4. 创造具体的约会方案（避免"附近咖啡厅"等模糊建议）
"""
    args_schema: Type[BaseModel] = HerPlanDateInput

    def _run(self, user_id: str, match_id: str = "", target_name: str = "TA", location: str = "", preferences: str = "") -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id, target_name, location, preferences))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str = "", target_name: str = "TA", location: str = "", preferences: str = "") -> ToolResult:
        """
        返回用户画像数据（不生成约会模板）

        Agent 根据这些数据自主创造约会方案：
        - 双方兴趣 → 约会活动选择
        - 双方地点 → 约会地点范围
        - 预算偏好 → 约会消费档次
        """
        # 获取用户画像
        user = _get_db_user(user_id) or {}

        # 获取目标用户画像
        target_user = _get_db_user(match_id) if match_id else None

        # 分析共同兴趣
        user_interests = set(user.get("interests", []))
        target_interests = set(target_user.get("interests", []) if target_user else [])
        common_interests = list(user_interests & target_interests)

        # 地点信息
        user_location = user.get("location", "")
        target_location = target_user.get("location", "") if target_user else ""

        # 确定约会地点范围
        date_location = location or user_location or target_location

        # 常见约会活动类型（供 Agent 参考，不是模板）
        activity_categories = {
            "美食": ["餐厅", "咖啡厅", "甜品店", "酒吧"],
            "娱乐": ["电影院", "演出", "展览", "游乐园"],
            "运动": ["健身房", "攀岩", "保龄球", "户外徒步"],
            "文化": ["书店", "博物馆", "图书馆", "艺术展"],
            "自然": ["公园", "植物园", "海滩", "山景"],
            "休闲": ["SPA", "按摩", "茶馆", "棋牌"],
        }

        # 根据共同兴趣筛选可能的活动类型
        relevant_categories = []
        for interest in common_interests:
            if interest in activity_categories:
                relevant_categories.append({
                    "interest": interest,
                    "activities": activity_categories[interest],
                })

        # 如果没有共同兴趣，提供所有类别供 Agent 选择
        if not relevant_categories:
            relevant_categories = [
                {"interest": cat, "activities": activities}
                for cat, activities in activity_categories.items()
            ]

        # 只返回数据，让 Agent 自己生成约会方案
        result_data = {
            "user_profile": {
                "interests": user.get("interests", []),
                "location": user_location,
                "spending_style": user.get("spending_style", ""),  # 消费偏好
            },
            "target_profile": target_user if target_user else None,
            "date_context": {
                "location": date_location,
                "common_interests": common_interests,
                "user_preferences": preferences,
            },
            "activity_options": relevant_categories,
            "hint": "Agent 应根据数据创造具体约会方案，避免'附近咖啡厅'等模糊建议，给出具体的地点和安排",
        }

        return ToolResult(
            success=True,
            data=result_data,
            summary=f"双方共同兴趣 {len(common_interests)} 个，约会地点范围 {date_location}"
        )


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
        user = _get_db_user(user_id)

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

        # ===== 检查关键偏好维度（匹配前必须确认）=====
        # 根据 SOUL.md：地点偏好、年龄偏好、关系目标 是关键维度
        missing_preferences = []

        # 地点偏好（是否接受异地）
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

        # ===== 推荐字段（加分维度）=====
        recommended_fields = ["occupation", "education", "interests"]
        for field in recommended_fields:
            if not user.get(field):
                missing_fields.append(f"{field} (推荐)")

        # ===== 偏好完整性状态 =====
        if len(missing_preferences) == 0:
            preference_status = "complete"  # 所有关键维度都有
        elif len(missing_preferences) < 3:
            preference_status = "partial"  # 部分关键维度有
        else:
            preference_status = "incomplete"  # 所有关键维度缺失

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


# ==================== 新增 Agent Native 工具 ====================

class HerGetUserInput(BaseModel):
    """获取用户画像的输入参数"""
    user_id: str = Field(description="用户 ID")


class HerGetTargetUserInput(BaseModel):
    """获取目标用户画像的输入参数"""
    target_user_id: str = Field(description="目标用户 ID")


class HerGetConversationHistoryInput(BaseModel):
    """获取对话历史的输入参数"""
    user_id: str = Field(description="用户 ID")
    match_id: str = Field(description="匹配对象 ID")
    limit: int = Field(default=20, description="返回消息数量")


class HerGetUserTool(BaseTool):
    """
    Her 用户画像查询工具 - 纯数据查询

    【Agent Native 设计】
    返回用户的完整画像数据，不做任何解读。
    Agent 根据返回数据自主分析用户特点。
    """

    name: str = "her_get_user"
    description: str = """
获取用户画像数据。返回用户的完整资料信息。

此工具只返回原始数据，不做解读。Agent 需要根据数据自主分析用户特点。

参数：
- user_id: 用户 ID（可选，默认使用当前用户）

返回：{ user_profile: {...} }

Agent 应该：
- 根据用户的兴趣、性格等数据，理解用户的特点
- 用于话题推荐、开场白生成、约会策划等场景
"""
    args_schema: Type[BaseModel] = HerGetUserInput

    def _run(self, user_id: str) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str) -> ToolResult:
        """返回用户画像数据"""
        user = _get_db_user(user_id)

        if not user:
            return ToolResult(
                success=False,
                error="用户不存在",
                summary="无法获取用户信息"
            )

        return ToolResult(
            success=True,
            data={"user_profile": user},
            summary=f"获取用户 {user.get('name', user_id)} 的画像"
        )


class HerGetTargetUserTool(BaseTool):
    """
    Her 目标用户画像查询工具 - 纯数据查询

    【Agent Native 设计】
    返回目标用户的完整画像数据，不做任何解读。
    Agent 根据返回数据自主分析目标用户特点，找到匹配点。
    """

    name: str = "her_get_target_user"
    description: str = """
获取目标用户画像数据。返回目标用户的完整资料信息。

此工具只返回原始数据，不做解读。Agent 需要根据数据自主分析目标用户特点。

参数：
- target_user_id: 目标用户 ID

返回：{ target_profile: {...} }

Agent 应该：
- 分析目标用户的兴趣、性格等数据
- 找到和用户的共同点，用于开场白、话题推荐等
"""
    args_schema: Type[BaseModel] = HerGetTargetUserInput

    def _run(self, target_user_id: str) -> str:
        try:
            result = run_async(self._arun(target_user_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, target_user_id: str) -> ToolResult:
        """返回目标用户画像数据"""
        target_user = _get_db_user(target_user_id)

        if not target_user:
            return ToolResult(
                success=False,
                error="目标用户不存在",
                summary="无法获取目标用户信息"
            )

        return ToolResult(
            success=True,
            data={"target_profile": target_user},
            summary=f"获取目标用户 {target_user.get('name', target_user_id)} 的画像"
        )


class HerGetConversationHistoryTool(BaseTool):
    """
    Her 对话历史查询工具 - 纯数据查询

    【Agent Native 设计】
    返回用户和匹配对象的对话历史，不做任何解读。
    Agent 根据对话历史自主分析：已聊话题、沉默状态、回复模式等。
    """

    name: str = "her_get_conversation_history"
    description: str = """
获取对话历史记录。返回用户和匹配对象的对话历史。

此工具只返回原始数据，不做解读。Agent 需要根据对话历史自主分析。

参数：
- user_id: 用户 ID（可选，默认使用当前用户）
- match_id: 匹配对象 ID
- limit: 返回消息数量（默认 20）

返回：{ messages: [...], total: N, silence_info: {...} }

Agent 应该：
- 分析已聊过的话题，避免推荐重复话题
- 分析对话频率，判断沉默时长
- 分析回复模式，判断对方意向
"""
    args_schema: Type[BaseModel] = HerGetConversationHistoryInput

    def _run(self, user_id: str, match_id: str, limit: int = 20) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id, limit))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str, limit: int = 20) -> ToolResult:
        """返回对话历史数据"""
        ensure_her_in_path()
        try:
            from utils.db_session_manager import db_session
            from db.models import MessageDB
            from datetime import datetime

            with db_session() as db:
                messages = db.query(MessageDB).filter(
                    ((MessageDB.sender_id == user_id) & (MessageDB.receiver_id == match_id)) |
                    ((MessageDB.sender_id == match_id) & (MessageDB.receiver_id == user_id))
                ).order_by(MessageDB.created_at.desc()).limit(limit).all()

                message_list = [
                    {
                        "content": m.content,
                        "sender_id": m.sender_id,
                        "is_from_user": m.sender_id == user_id,
                        "created_at": str(m.created_at),
                    }
                    for m in messages
                ]

                # 计算沉默信息（Agent 自己解读）
                silence_info = {}
                if messages:
                    last_message = messages[0]  # 最近一条消息
                    last_time = last_message.created_at
                    if isinstance(last_time, str):
                        last_time = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                    silence_seconds = (datetime.now() - last_time.replace(tzinfo=None)).total_seconds()
                    silence_info = {
                        "last_message_time": str(last_message.created_at),
                        "silence_seconds": int(silence_seconds),
                        "last_sender": last_message.sender_id,
                        "hint": "Agent 应根据沉默时长判断是否需要打破沉默",
                    }

                return ToolResult(
                    success=True,
                    data={
                        "messages": message_list,
                        "total": len(message_list),
                        "silence_info": silence_info,
                    },
                    summary=f"获取 {len(message_list)} 条对话记录"
                )
        except Exception as e:
            logger.warning(f"[her_get_conversation_history] 查询失败: {e}")
            return ToolResult(
                success=True,
                data={"messages": [], "total": 0, "silence_info": {}},
                summary="暂无对话历史"
            )


# ==================== Export ====================

__all__ = [
    "HerFindMatchesTool",
    "HerDailyRecommendTool",
    "HerAnalyzeCompatibilityTool",
    "HerAnalyzeRelationshipTool",
    "HerSuggestTopicsTool",
    "HerGetIcebreakerTool",
    "HerPlanDateTool",
    "HerCollectProfileTool",
    "HerGetUserTool",
    "HerGetTargetUserTool",
    "HerGetConversationHistoryTool",
    "ToolResult",
    "MatchResult",
]

# Tool instances for registration
her_find_matches_tool = HerFindMatchesTool()
her_daily_recommend_tool = HerDailyRecommendTool()
her_analyze_compatibility_tool = HerAnalyzeCompatibilityTool()
her_analyze_relationship_tool = HerAnalyzeRelationshipTool()
her_suggest_topics_tool = HerSuggestTopicsTool()
her_get_icebreaker_tool = HerGetIcebreakerTool()
her_plan_date_tool = HerPlanDateTool()
her_collect_profile_tool = HerCollectProfileTool()
her_get_user_tool = HerGetUserTool()
her_get_target_user_tool = HerGetTargetUserTool()
her_get_conversation_history_tool = HerGetConversationHistoryTool()