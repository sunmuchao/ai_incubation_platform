"""
Her Tools - Match Tools Module (精简版 v4.1)

匹配相关工具：查找候选匹配对象

【Agent Native 设计】
- 只做硬约束过滤（安全边界 + 基础匹配逻辑）
- 返回原始候选池，Agent 自行筛选和推荐
- 不预设 UI 类型，Agent 自己决定展示方式

【Anthropic 建议】
- 返回高信号信息（name > UUID）
- 错误提示给修正方向
- 截断提示给具体建议

【性能监控】关键路径耗时日志
"""
import logging
import json
import uuid
import time
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import (
    ToolResult,
    HerFindCandidatesInput,
)
from .helpers import (
    ensure_her_in_path,
    run_async,
    get_current_user_id,
    get_db_user,
    batch_get_user_confidence,
    normalize_user_interests_field,
    should_exclude_demo_candidate_name,
    _cached_import,
)

logger = logging.getLogger(__name__)

# 查询上限（性能优化 + Agent 上下文保护）
MAX_CANDIDATES_SCAN = 30


# ==================== 辅助函数 ====================

def _format_income_range(income: int | None) -> str:
    """
    格式化收入范围为用户友好的描述

    Args:
        income: 收入（单位：万元）

    Returns:
        用户友好的收入范围描述
    """
    if income is None or income == 0:
        return ""

    if income <= 10:
        return "10万以下"
    elif income <= 20:
        return "10-20万"
    elif income <= 30:
        return "20-30万"
    elif income <= 50:
        return "30-50万"
    else:
        return "50万以上"


# ==================== Her Find Candidates Tool ====================

class HerFindCandidatesTool(BaseTool):
    """
    Her 候选人查询工具 - 获取候选匹配对象池（Agent Native 设计）

    只做硬约束过滤，返回原始数据供 Agent 筛选和推荐。
    """

    name: str = "her_find_candidates"
    description: str = """
获取候选匹配对象池（一次调用完成所有）。

【能力】
查询数据库中符合条件的候选人，同时返回用户画像和缺失字段。

【参数】
- user_id: 用户 ID（可选，不传或传 'me' 使用当前用户）

【返回】
- candidates: 原始候选池（包含 display_id、姓名、年龄、地点、头像URL、兴趣、置信度等）
- user_profile: 用户基本信息（name、age、gender、location、interests）
- missing_fields: 缺失的基础字段（name、age、gender、location）
- missing_preferences: 缺失的偏好维度（年龄范围、地点偏好、异地接受度、关系目标）
- user_preferences: 用户偏好（年龄范围、地点偏好、异地接受度等）

【使用场景】
当用户想要找对象、推荐候选人、看看有谁时直接调用此工具。
**无需先调用 her_get_profile**，此工具已返回所有必要信息。

【重要：筛选规则】
此工具返回原始候选池（可能包含几十位候选人），你必须：

1. **只推荐 1-3 位最匹配的候选人**（禁止输出全部或大列表）
2. 根据用户偏好筛选：
   - 年龄范围（user_preferences.preferred_age_min ~ preferred_age_max）
   - 地点偏好（user_preferences.preferred_location 或 user_location 同城）
   - 关系目标匹配（relationship_goal）
   - 置信度排序（confidence_score 高的优先）
3. 为每位推荐输出 UserProfileCard（GENERATIVE_UI 格式），**必须包含 user_id 和 avatar_url 字段**
4. 使用 display_id 或 name 标识候选人

【🚀 改进：支持前端筛选】
返回 MatchCardList 时，传入以下 props：
- matches: 精选的 1-3 位候选人（Agent 推荐）
- all_candidates: 原始候选池（candidates 字段，供前端筛选使用）
- total_candidates: 候选池总数（len(candidates)）

这样用户可以在前端自主筛选（地区、年龄、排序），无需重新调用 Agent。

【输出示例】
我为你精心挑选了 3 位最匹配的候选人！

[GENERATIVE_UI]
{"component_type": "MatchCardList", "props": {"matches": [...精选3位], "all_candidates": [...全部候选池], "total_candidates": 28}}
[/GENERATIVE_UI]

【禁止行为】
- ❌ 输出全部候选池（如 8 位、30 位）
- ❌ 使用 Markdown 表格或编号列表
- ❌ 输出原始 JSON 数据
"""
    args_schema: Type[BaseModel] = HerFindCandidatesInput

    def _run(self, user_id: str = "me") -> str:
        run_start = time.time()
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()
        logger.info(f"[her_find_candidates._run] user_id 解析耗时: {time.time() - run_start:.3f}s")

        try:
            async_start = time.time()
            result = run_async(self._arun(user_id))
            logger.info(f"[her_find_candidates._run] run_async 耗时: {time.time() - async_start:.3f}s")
        except Exception as e:
            # Anthropic 建议：错误提示给修正方向
            error_msg = self._format_error(str(e), user_id)
            return json.dumps(ToolResult(success=False, error=error_msg).model_dump(), ensure_ascii=False)

        dump_start = time.time()
        output = json.dumps(result.model_dump(), ensure_ascii=False)
        logger.info(f"[her_find_candidates._run] json.dumps 耗时: {time.time() - dump_start:.3f}s")
        logger.info(f"[her_find_candidates._run] 总耗时: {time.time() - run_start:.3f}s")
        return output

    def _format_error(self, error: str, user_id: str) -> str:
        """格式化错误信息（Anthropic 建议：给修正方向）"""
        if "用户不存在" in error:
            return f"""用户不存在。

传入的 user_id: '{user_id}'

建议：
1. 如果你想查询当前用户，调用 her_get_profile(user_id='me')
2. 如果你想查询某个候选人，请先调用 her_find_candidates 获取候选人列表，从中选择

示例：her_get_profile(user_id='me')"""
        return error

    def _detect_missing_fields(self, user_prefs: dict) -> list:
        """检测缺失的基础字段"""
        required_fields = ["name", "age", "gender", "location"]
        missing = []
        for field in required_fields:
            value = user_prefs.get(field)
            if not value or (field == "age" and value == 0):
                missing.append(field)
        return missing

    def _detect_missing_preferences(self, user_prefs: dict) -> list:
        """检测缺失的偏好维度"""
        preference_fields = [
            ("preferred_age_min", "年龄范围"),
            ("preferred_age_max", "年龄范围"),
            ("preferred_location", "地点偏好"),
            ("accept_remote", "异地接受度"),
            ("relationship_goal", "关系目标"),
        ]
        missing = []
        for field, label in preference_fields:
            if not user_prefs.get(field):
                missing.append(label)
        return missing

    async def _arun(self, user_id: str) -> ToolResult:
        """
        查询候选匹配对象池
        """
        total_start = time.time()

        # ===== 发送进度事件（方案 3+4：流式 + 精确进度）=====
        try:
            from langgraph.prebuilt import StreamWriter
            writer = StreamWriter()
            if writer:
                writer.write({"progress_step": "正在加载用户信息..."})
        except:
            pass

        # ===== 模块导入（使用缓存）=====
        import_start = time.time()
        db_session = _cached_import('utils.db_session_manager', 'db_session')
        UserDB = _cached_import('db.models', 'UserDB')
        logger.info(f"[her_find_candidates] 模块导入耗时: {time.time() - import_start:.3f}s")

        # ===== 获取用户偏好 =====
        step1_start = time.time()
        user_prefs = get_db_user(user_id)
        logger.info(f"[her_find_candidates] Step1 get_db_user 耗时: {time.time() - step1_start:.3f}s")

        if not user_prefs:
            # Anthropic 建议：错误提示给修正方向
            return ToolResult(
                success=False,
                error=self._format_error("用户不存在", user_id)
            )

        # ===== 硬约束查询 =====
        step2_start = time.time()
        candidates_raw: list = []
        truncated = False
        total_before_truncate = 0

        with db_session() as db:
            # ===== 性别硬约束逻辑 =====
            user_gender = user_prefs.get("gender", "")
            sexual_orientation = getattr(user_prefs, "sexual_orientation", None) or "heterosexual"

            # 异性恋（默认）：过滤同性用户
            if sexual_orientation == "heterosexual":
                if user_gender == "male":
                    target_gender = "female"
                elif user_gender == "female":
                    target_gender = "male"
                else:
                    target_gender = None
            # 同性恋：过滤异性用户
            elif sexual_orientation == "homosexual":
                target_gender = user_gender
            # 双性恋：不做性别过滤
            elif sexual_orientation == "bisexual":
                target_gender = None
            else:
                # 默认异性恋
                if user_gender == "male":
                    target_gender = "female"
                elif user_gender == "female":
                    target_gender = "male"
                else:
                    target_gender = None

            # 构建查询
            query = db.query(UserDB).filter(
                UserDB.id != user_id,
                UserDB.is_active == True,
                UserDB.is_permanently_banned == False  # 安全边界
            )

            # 性别硬约束
            if target_gender:
                query = query.filter(UserDB.gender == target_gender)

            # 地点硬约束：用户明确不接受异地 → 只查同城
            accept_remote = user_prefs.get("accept_remote")
            user_location = user_prefs.get("location")
            no_remote_values = ["no", "只找同城", "不接受异地"]
            if accept_remote in no_remote_values and user_location:
                query = query.filter(UserDB.location == user_location)

            # 执行查询
            query_start = time.time()
            candidates_db = query.order_by(UserDB.created_at.desc()).limit(MAX_CANDIDATES_SCAN + 1).all()
            logger.info(f"[her_find_candidates] Step2 数据库查询耗时: {time.time() - query_start:.3f}s, 结果数: {len(candidates_db)}")

            # Anthropic 建议：截断提示
            total_before_truncate = len(candidates_db)
            if total_before_truncate > MAX_CANDIDATES_SCAN:
                truncated = True
                candidates_db = candidates_db[:MAX_CANDIDATES_SCAN]

            # 批量查询置信度（性能优化）
            step3_start = time.time()
            candidate_ids = [u.id for u in candidates_db]
            confidence_map = batch_get_user_confidence(candidate_ids)
            logger.info(f"[her_find_candidates] Step3 batch_get_user_confidence 耗时: {time.time() - step3_start:.3f}s")

            # Anthropic 建议：display_id 比 UUID 更语义化
            step4_start = time.time()
            for idx, u in enumerate(candidates_db, start=1):
                # 硬约束：排除测试/演示账号
                if should_exclude_demo_candidate_name(getattr(u, "name", None)):
                    continue

                # 获取置信度信息
                confidence_info = confidence_map.get(u.id, {
                    "confidence_level": "medium",
                    "confidence_score": 40,
                })

                # 构建候选数据
                # Anthropic 建议：添加 display_id（语义化标识符）
                candidates_raw.append({
                    "display_id": f"candidate_{idx:03d}",  # 语义化 ID，如 candidate_001
                    "user_id": u.id,  # 保留 UUID（用于后续操作）
                    "name": u.name or "匿名用户",
                    "age": u.age or 0,
                    "gender": u.gender or "",
                    "location": u.location or "",
                    "interests": normalize_user_interests_field(getattr(u, "interests", None))[:5],
                    "bio": u.bio or "",
                    "relationship_goal": getattr(u, 'relationship_goal', '') or "",
                    "want_children": getattr(u, 'want_children', None),
                    "avatar_url": getattr(u, 'avatar_url', None) or "",  # 🔧 [新增] 头像 URL
                    # 🚀 [改进] 补全更多信息字段
                    "occupation": getattr(u, 'occupation', None) or "",  # 职业
                    "education": getattr(u, 'education', None) or "",  # 学历
                    "income": getattr(u, 'income', None) or 0,  # 收入（万元）
                    # 收入范围描述（用户友好）
                    "income_range": _format_income_range(getattr(u, 'income', None)),
                    "confidence_level": confidence_info["confidence_level"],
                    "confidence_score": confidence_info["confidence_score"],
                })
            logger.info(f"[her_find_candidates] Step4 构建候选数据耗时: {time.time() - step4_start:.3f}s")

        step5_start = time.time()
        # ===== 返回原始数据 =====
        query_request_id = str(uuid.uuid4())

        # 构建硬约束列表
        hard_constraints_list = [
            "排除封禁用户",
            "排除测试账号",
            f"性别过滤（{target_gender or '无限制'}）",
        ]
        if accept_remote in no_remote_values and user_location:
            hard_constraints_list.append(f"地点过滤（同城：{user_location}）")

        result_data = {
            "candidates": candidates_raw,
            "query_request_id": query_request_id,
            "user_profile": {
                # 用户基本信息
                "name": user_prefs.get("name"),
                "age": user_prefs.get("age"),
                "gender": user_prefs.get("gender"),
                "location": user_prefs.get("location"),
                "interests": user_prefs.get("interests"),
            },
            "missing_fields": self._detect_missing_fields(user_prefs),
            "missing_preferences": self._detect_missing_preferences(user_prefs),
            "user_preferences": {
                # 偏好字段
                "preferred_age_min": user_prefs.get("preferred_age_min"),
                "preferred_age_max": user_prefs.get("preferred_age_max"),
                "preferred_location": user_prefs.get("preferred_location"),
                "accept_remote": user_prefs.get("accept_remote"),
                "relationship_goal": user_prefs.get("relationship_goal"),
                # 用户信息
                "user_gender": user_prefs.get("gender"),
                "user_location": user_prefs.get("location"),
                # 工具计算结果
                "target_gender": target_gender,
            },
            "filter_applied": {
                "hard_constraints": hard_constraints_list,
                "soft_constraints": "由 Agent 自行判断",
            },
        }

        # Anthropic 建议：截断提示给具体建议
        if truncated:
            result_data["truncated"] = True
            result_data["truncation_hint"] = f"""结果已截断（显示前 {MAX_CANDIDATES_SCAN} 条，共有 {total_before_truncate} 条记录）。

如需更精确的结果，你可以：
1. 根据年龄范围筛选（user_preferences.preferred_age_min ~ preferred_age_max）
2. 根据地点筛选（只看 user_location 同城的候选人）
3. 根据关系目标筛选（只看 relationship_goal 匹配的候选人）

建议：优先推荐前 5-10 位候选人，让用户选择后再深入分析。"""

        logger.info(f"[her_find_candidates] 总耗时: {time.time() - total_start:.3f}s, 候选人数: {len(candidates_raw)}")

        return ToolResult(
            success=True,
            data=result_data
        )


# ==================== Exports ====================

__all__ = [
    "HerFindCandidatesTool",
]

# Tool instance for registration
her_find_candidates_tool = HerFindCandidatesTool()