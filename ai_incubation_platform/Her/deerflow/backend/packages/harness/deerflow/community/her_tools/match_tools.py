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
from __future__ import annotations

import logging
import json
import uuid
import time
import re
import os
import threading
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from typing import Type, Dict, Any, List, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel
from sqlalchemy import or_, func

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
from .vector_recall_service import VectorRecallService
from .match_rerank_service import MatchRerankService

logger = logging.getLogger(__name__)

# 查询上限（性能优化 + Agent 上下文保护）
MAX_CANDIDATES_SCAN = 30
DEFAULT_VECTOR_TOPK = 50
DEFAULT_RERANK_PRE_N = 15
DEFAULT_RERANK_TOPN = 3
DEFAULT_REASON_TOPN = 3
DEFAULT_REASON_TIMEOUT_SECONDS = 12
DEFAULT_REASON_TOTAL_BUDGET_SECONDS = 30
DEFAULT_REASON_WORKERS = 3

_REASON_ASYNC_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="her-reason-async")
_REASON_CACHE_LOCK = threading.Lock()
_ASYNC_REASON_CACHE: Dict[str, Dict[str, Any]] = {}


def _is_hybrid_enabled() -> bool:
    return os.environ.get("HER_MATCH_RETRIEVAL_MODE", "legacy").strip().lower() == "hybrid"


def _normalize_retrieval_mode(mode: Optional[str]) -> str:
    value = (mode or "").strip().lower()
    if value in {"hybrid", "db_only", "auto"}:
        return value
    return "auto"


def _safe_int_env(key: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(key, default)))
    except (TypeError, ValueError):
        return default


def _reason_topn() -> int:
    try:
        return max(0, int(os.environ.get("HER_MATCH_REASON_TOPN", DEFAULT_REASON_TOPN)))
    except (TypeError, ValueError):
        return DEFAULT_REASON_TOPN


def _reason_timeout_seconds() -> int:
    try:
        return max(3, int(os.environ.get("HER_MATCH_REASON_TIMEOUT_SECONDS", DEFAULT_REASON_TIMEOUT_SECONDS)))
    except (TypeError, ValueError):
        return DEFAULT_REASON_TIMEOUT_SECONDS


def _reason_total_budget_seconds() -> int:
    try:
        return max(2, int(os.environ.get("HER_MATCH_REASON_TOTAL_BUDGET_SECONDS", DEFAULT_REASON_TOTAL_BUDGET_SECONDS)))
    except (TypeError, ValueError):
        return DEFAULT_REASON_TOTAL_BUDGET_SECONDS


def _reason_workers() -> int:
    try:
        return max(1, int(os.environ.get("HER_MATCH_REASON_WORKERS", DEFAULT_REASON_WORKERS)))
    except (TypeError, ValueError):
        return DEFAULT_REASON_WORKERS


def _reason_async_enabled() -> bool:
    value = str(os.environ.get("HER_MATCH_REASON_ASYNC", "true")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_async_reason_result(query_request_id: str) -> Dict[str, Any]:
    """读取异步推荐理由状态（供 API 层查询）。"""
    key = (query_request_id or "").strip()
    if not key:
        return {"status": "not_found", "reasons_by_user_id": {}}
    with _REASON_CACHE_LOCK:
        cached = _ASYNC_REASON_CACHE.get(key)
        if not cached:
            return {"status": "not_found", "reasons_by_user_id": {}}
        return {
            "status": cached.get("status", "pending"),
            "updated_at": cached.get("updated_at"),
            "elapsed_ms": cached.get("elapsed_ms", 0),
            "reasons_by_user_id": dict(cached.get("reasons_by_user_id") or {}),
        }


def _city_tokens_for_location_filter(user_location: Optional[str]) -> List[str]:
    """
    从用户常住地字符串提取用于 SQL LIKE/contains 的城市关键词（长名优先，减少误匹配）。
    解决：仅按 created_at 取前 30 人时，同城用户可能完全不在候选池内的问题。
    """
    if not user_location or not str(user_location).strip():
        return []
    raw = str(user_location).strip()
    try:
        ensure_her_in_path()
        from agent.tools.geo_tool import GeoService

        keys = sorted(GeoService.CHINA_CITIES.keys(), key=len, reverse=True)
        for k in keys:
            if k and k in raw:
                return [k]
    except Exception as e:
        logger.warning(f"[_city_tokens_for_location_filter] geo 解析降级: {e}")
    # 兜底：常见「省+市」后缀去掉后取末尾短串
    compact = raw.replace("省", "").replace("市辖区", "").replace("自治区", "")
    if "市" in compact:
        parts = compact.split("市")
        tail = parts[-1].strip() if parts else ""
        if len(tail) >= 2:
            return [tail[:8]]
    if len(raw) >= 2:
        return [raw[:8]]
    return []


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


def _parse_reason_list(text: str) -> List[str]:
    """尽量从 LLM 输出中提取 JSON 数组 reasons。"""
    if not text:
        return []
    raw = text.strip()
    # 先尝试直接 JSON
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()][:4]
        if isinstance(data, dict) and isinstance(data.get("reasons"), list):
            return [str(x).strip() for x in data["reasons"] if str(x).strip()][:4]
    except Exception:
        pass
    # 再尝试从 markdown code fence 里提取 JSON
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", raw)
    if m:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()][:4]
            if isinstance(data, dict) and isinstance(data.get("reasons"), list):
                return [str(x).strip() for x in data["reasons"] if str(x).strip()][:4]
        except Exception:
            pass
    return []


def _post_filter_reason_list(reasons: List[str]) -> List[str]:
    """
    过滤空话/套话，尽量保留带有具体信息锚点的理由。
    """
    generic_tokens = ["感觉不错", "比较合适", "挺好", "匹配度高", "可以试试", "建议了解", "有潜力"]
    signal_tokens = [
        "岁", "同城", "都在", "地点", "兴趣", "关系目标", "孩子", "消费", "职业", "学历", "收入",
        "认证", "置信度", "high", "very_high"
    ]
    out: List[str] = []
    for r in reasons:
        s = (r or "").strip()
        if not s:
            continue
        if any(t in s for t in generic_tokens) and not any(k in s for k in signal_tokens):
            continue
        out.append(s)
    # 去重保序
    dedup: List[str] = []
    seen = set()
    for r in out:
        if r not in seen:
            seen.add(r)
            dedup.append(r)
    return dedup[:4]


def _fallback_match_reasons(candidate: Dict[str, Any]) -> List[str]:
    """LLM 失败时的最小兜底，保证前端不出现空白。"""
    reasons: List[str] = []
    if (candidate.get("location") or "").strip():
        reasons.append(f"地点在{candidate.get('location')}，便于进一步了解")
    if (candidate.get("relationship_goal") or "").strip():
        reasons.append(f"关系目标为{candidate.get('relationship_goal')}")
    if candidate.get("confidence_level") in ["very_high", "high"]:
        reasons.append("资料可信度较高")
    if not reasons:
        reasons.append("画像信息较完整，建议先聊聊看感觉")
    return reasons[:4]


def _async_enrich_match_reasons(
    query_request_id: str,
    user_prefs: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    reason_budget: int,
    reason_workers: int,
) -> None:
    """
    后台异步生成推荐理由，不阻塞主请求。
    生成结果放入内存缓存，供后续增量拉取/推送使用。
    """
    started = time.time()
    if not candidates:
        return

    results: Dict[str, List[str]] = {}
    future_to_candidate: Dict[Any, Dict[str, Any]] = {}
    local_executor = ThreadPoolExecutor(max_workers=max(1, min(reason_workers, len(candidates))))
    timed_out = False
    try:
        for candidate in candidates:
            future = local_executor.submit(_calculate_match_reasons, user_prefs, deepcopy(candidate))
            future_to_candidate[future] = candidate

        try:
            for future in as_completed(future_to_candidate, timeout=reason_budget):
                candidate = future_to_candidate[future]
                uid = str(candidate.get("user_id") or "")
                if not uid:
                    continue
                try:
                    results[uid] = future.result()
                except Exception:
                    results[uid] = _fallback_match_reasons(candidate)
        except FuturesTimeoutError:
            timed_out = True
            logger.warning(
                "[her_find_candidates][async] 推荐理由后台任务超出预算 %ss，未完成项将保留兜底",
                reason_budget,
            )
    finally:
        if timed_out:
            local_executor.shutdown(wait=False, cancel_futures=True)
        else:
            local_executor.shutdown(wait=True, cancel_futures=False)

    with _REASON_CACHE_LOCK:
        _ASYNC_REASON_CACHE[query_request_id] = {
            "status": "completed",
            "updated_at": int(time.time()),
            "elapsed_ms": int((time.time() - started) * 1000),
            "reasons_by_user_id": results,
        }
    logger.info(
        "[her_find_candidates][async] 推荐理由后台任务完成: query=%s, count=%s, cost=%sms",
        query_request_id,
        len(results),
        int((time.time() - started) * 1000),
    )


def _safe_parse_json_object(raw: Any) -> Dict[str, Any]:
    """安全解析 JSON 对象，失败时返回空 dict。"""
    if not raw or not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _build_vector_match_highlights(self_profile_json: str, desire_profile_json: str) -> Dict[str, Any]:
    """
    从画像 JSON 中提取匹配解释常用维度，减少上层重复解析。
    """
    self_data = _safe_parse_json_object(self_profile_json)
    desire_data = _safe_parse_json_object(desire_profile_json)
    self_vector = self_data.get("vector_dimensions", {}) if isinstance(self_data, dict) else {}
    desire_vector = desire_data.get("vector_dimensions", {}) if isinstance(desire_data, dict) else {}

    values = self_vector.get("values", {}) if isinstance(self_vector, dict) else {}
    communication = self_vector.get("communication", {}) if isinstance(self_vector, dict) else {}
    interests = desire_vector.get("interests", {}) if isinstance(desire_vector, dict) else {}
    hard_constraints = desire_vector.get("hard_constraints", {}) if isinstance(desire_vector, dict) else {}

    return {
        "relationship_goal": values.get("relationship_goal"),
        "want_children": values.get("want_children"),
        "spending_style": values.get("spending_style"),
        "conflict_style": communication.get("conflict_style"),
        "repair_willingness": communication.get("repair_willingness"),
        "declared_interests": interests.get("declared_interests", []),
        "hard_constraints": hard_constraints,
    }


# 🚀 [场景升级] LLM 实时生成具体匹配原因
def _calculate_match_reasons(
    user_prefs: Dict[str, Any],
    candidate: Dict[str, Any]
) -> List[str]:
    """
    使用 LLM 实时分析为什么推荐该候选人（纯 AI 路径）。
    """
    try:
        ensure_her_in_path()
        from llm.client import call_llm

        prompt_payload = {
            "user_profile": {
                "age": user_prefs.get("age"),
                "gender": user_prefs.get("gender"),
                "location": user_prefs.get("location"),
                "interests": user_prefs.get("interests") or [],
                "relationship_goal": user_prefs.get("relationship_goal"),
                "preferred_age_min": user_prefs.get("preferred_age_min"),
                "preferred_age_max": user_prefs.get("preferred_age_max"),
                "preferred_location": user_prefs.get("preferred_location"),
                "accept_remote": user_prefs.get("accept_remote"),
                "want_children": user_prefs.get("want_children"),
                "spending_style": user_prefs.get("spending_style"),
            },
            "candidate_profile": candidate,
        }
        system_prompt = (
            "你是一位温暖、专业的恋爱顾问，请写“为什么推荐TA”的理由。"
            "必须输出 2-4 条中文短句，每条 10-26 字。"
            "每条必须引用至少一个输入里的具体锚点（如年龄段、同城/地点、共同兴趣、关系目标、生育观、消费观、职业/学历/收入、置信度）。"
            "禁止空话：例如“感觉不错/比较合适/可以试试/匹配度高”。"
            "禁止编造输入中不存在的事实；不要使用编号、emoji、括号解释。"
            "只输出严格 JSON：{\"reasons\":[\"...\",\"...\"]}"
        )
        llm_text = call_llm(
            prompt=json.dumps(prompt_payload, ensure_ascii=False),
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=220,
            timeout=_reason_timeout_seconds(),
        )
        reasons = _post_filter_reason_list(_parse_reason_list(llm_text))
        if reasons:
            return reasons[:4]
        logger.warning("[her_find_candidates] LLM 返回无法解析的 reasons，使用兜底")
        return _fallback_match_reasons(candidate)
    except Exception as e:
        logger.warning(f"[her_find_candidates] LLM 生成推荐理由失败，使用兜底: {e}")
        return _fallback_match_reasons(candidate)


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
- retrieval_mode: 检索模式（可选，建议由 Agent 根据用户语义自主判断）
  - db_only: 仅数据库结构化筛选（年龄/地点/目标等硬条件）
  - hybrid: 向量召回 + 重排（适合“按感觉找人”）
  - auto: 自动（回落到系统默认配置）
- retrieval_reason: 本次模式选择理由（可选，建议一句话，便于日志审计）

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

【🚀 改进：前端筛选触发实时查询】
返回 MatchCardList 时，只传入精选的 matches：
- matches: 精选的 5-8 位候选人（Agent 推荐）
- user_preferences: 用户偏好（供前端显示当前筛选状态）
- filter_options: 筛选项元数据（供前端渲染筛选控件）

**不再传入 all_candidates**（全部候选池），筛选功能改为：
- 用户点击筛选项 → 前端调用 API → 后端重新查询 → 返回新的精选结果

这样筛选是"实时查询"，而非"前端过滤已有数据"。

【输出示例】
我为你精心挑选了 5 位最匹配的候选人！

[GENERATIVE_UI]
{"component_type": "MatchCardList", "props": {"matches": [...精选5位], "user_preferences": {...}, "filter_options": {"locations": ["北京", "上海", ...], "age_ranges": ["20-25", "26-30", ...]}}}
[/GENERATIVE_UI]

【禁止行为】
- ❌ 输出全部候选池（如 8 位、30 位）
- ❌ 使用 Markdown 表格或编号列表
- ❌ 输出原始 JSON 数据
"""
    args_schema: Type[BaseModel] = HerFindCandidatesInput

    def _run(self, user_id: str = "me", retrieval_mode: str = "auto", retrieval_reason: str = "") -> str:
        run_start = time.time()
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()
        logger.info(f"[her_find_candidates._run] user_id 解析耗时: {time.time() - run_start:.3f}s")

        try:
            async_start = time.time()
            result = run_async(self._arun(user_id, retrieval_mode, retrieval_reason))
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

    def _format_age_range_selection(self, preferred_min: Any, preferred_max: Any) -> str:
        if preferred_min and preferred_max:
            return f"{preferred_min}-{preferred_max}"
        return "全部"

    def _build_filter_options(
        self,
        db: Any,
        UserDB: Any,
        user_id: str,
        target_gender: Optional[str],
        selected_location: Optional[str],
        selected_age_range: str,
        selected_relationship_goal: Optional[str],
    ) -> Dict[str, Any]:
        """
        过滤项的单一真相来源：直接来自数据库（非前端写死）。
        - all_values: 当前性别池下数据库可选全集
        - selected: 当前查询命中的筛选值
        """
        base_query = db.query(UserDB).filter(
            UserDB.id != user_id,
            UserDB.is_active == True,
            UserDB.is_permanently_banned == False,
        )
        if target_gender:
            base_query = base_query.filter(UserDB.gender == target_gender)

        locations = [
            row[0].strip()
            for row in base_query.with_entities(UserDB.location).distinct().all()
            if row and row[0] and str(row[0]).strip()
        ]
        locations = sorted(set(locations))

        goals = [
            row[0].strip()
            for row in base_query.with_entities(UserDB.relationship_goal).distinct().all()
            if row and row[0] and str(row[0]).strip()
        ]
        goals = sorted(set(goals))

        min_age, max_age = base_query.with_entities(func.min(UserDB.age), func.max(UserDB.age)).first() or (None, None)
        age_ranges: List[str] = ["全部"]
        if isinstance(min_age, int) and isinstance(max_age, int) and min_age > 0 and max_age >= min_age:
            bucket_start = (min_age // 5) * 5
            bucket_end = ((max_age + 4) // 5) * 5
            for start in range(bucket_start, bucket_end + 1, 5):
                end = start + 4
                if end < min_age:
                    continue
                if start > max_age:
                    break
                age_ranges.append(f"{start}-{end}")

        selected_location_value = (selected_location or "").strip()
        selected_goal_value = (selected_relationship_goal or "").strip()
        if selected_location_value and selected_location_value not in locations:
            locations.insert(0, selected_location_value)
        if selected_goal_value and selected_goal_value not in goals:
            goals.insert(0, selected_goal_value)
        if selected_age_range and selected_age_range not in age_ranges:
            age_ranges.append(selected_age_range)

        return {
            "locations": ["全部"] + locations,
            "age_ranges": age_ranges,
            "relationship_goals": ["全部"] + goals,
            "selected": {
                "location": selected_location_value or "全部",
                "age_range": selected_age_range or "全部",
                "relationship_goal": selected_goal_value or "全部",
            },
        }

    async def _arun(
        self,
        user_id: str,
        retrieval_mode: str = "auto",
        retrieval_reason: str = "",
        filter_overrides: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
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

        # 允许调用方（如前端筛选实时查询）临时覆盖筛选条件
        # 覆盖只影响本次查询，不改变数据库持久偏好。
        def _normalize_filter_value(value: Any) -> Optional[str]:
            text = str(value).strip() if value is not None else ""
            if not text or text == "全部":
                return None
            return text

        override_location = _normalize_filter_value((filter_overrides or {}).get("location"))
        override_age_range = _normalize_filter_value((filter_overrides or {}).get("age_range"))
        override_goal = _normalize_filter_value((filter_overrides or {}).get("relationship_goal"))

        if override_location is not None:
            user_prefs["preferred_location"] = override_location
        elif (filter_overrides or {}).get("location") == "全部":
            user_prefs["preferred_location"] = None

        if override_goal is not None:
            user_prefs["relationship_goal"] = override_goal
        elif (filter_overrides or {}).get("relationship_goal") == "全部":
            user_prefs["relationship_goal"] = None

        if override_age_range and "-" in override_age_range:
            try:
                min_text, max_text = override_age_range.split("-", 1)
                override_min = int(min_text.strip())
                override_max = int(max_text.strip())
                if override_min > 0 and override_max >= override_min:
                    user_prefs["preferred_age_min"] = override_min
                    user_prefs["preferred_age_max"] = override_max
            except ValueError:
                pass
        elif (filter_overrides or {}).get("age_range") == "全部":
            user_prefs["preferred_age_min"] = None
            user_prefs["preferred_age_max"] = None

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

            # ===== 地点策略：默认同城优先 =====
            # 用户明确不接受异地 → 只查同城（硬约束）
            # 用户没设置偏好 → 查所有，但排序时同城优先（软约束）
            accept_remote = user_prefs.get("accept_remote")
            user_location = user_prefs.get("location")
            no_remote_values = ["no", "只找同城", "不接受异地"]
            location_hard_filter = accept_remote in no_remote_values and user_location

            # 🚀 [诊断日志] 确认用户 location 是否正确传递
            logger.info(f"[her_find_candidates] 地点策略: user_location={user_location}, accept_remote={accept_remote}, location_hard_filter={location_hard_filter}")

            selected_location = user_prefs.get("preferred_location") or (user_location if location_hard_filter else None)
            selected_age_range = (
                override_age_range
                if override_age_range
                else self._format_age_range_selection(
                    user_prefs.get("preferred_age_min"),
                    user_prefs.get("preferred_age_max"),
                )
            )
            selected_relationship_goal = user_prefs.get("relationship_goal")

            filter_options = self._build_filter_options(
                db=db,
                UserDB=UserDB,
                user_id=user_id,
                target_gender=target_gender,
                selected_location=selected_location,
                selected_age_range=selected_age_range,
                selected_relationship_goal=selected_relationship_goal,
            )

            if location_hard_filter:
                query = query.filter(UserDB.location == user_location)
            # 显式地点偏好筛选：点击筛选后实时查库
            elif selected_location and selected_location != "全部":
                query = query.filter(UserDB.location == selected_location)

            preferred_age_min = user_prefs.get("preferred_age_min")
            preferred_age_max = user_prefs.get("preferred_age_max")
            if isinstance(preferred_age_min, int) and preferred_age_min > 0:
                query = query.filter(UserDB.age >= preferred_age_min)
            if isinstance(preferred_age_max, int) and preferred_age_max > 0:
                query = query.filter(UserDB.age <= preferred_age_max)

            if selected_relationship_goal and selected_relationship_goal != "全部":
                query = query.filter(UserDB.relationship_goal == selected_relationship_goal)

            # 执行查询：有常住地且非「只接受硬同城」时，先把同城/同关键词用户并入池，再按时间补足
            query_start = time.time()
            cap = MAX_CANDIDATES_SCAN + 1
            if location_hard_filter:
                candidates_db = query.order_by(UserDB.created_at.desc()).limit(cap).all()
            else:
                city_tokens = _city_tokens_for_location_filter(user_location)
                merged: list = []
                seen_ids: set = set()
                if user_location and city_tokens:
                    loc_clause = or_(*[UserDB.location.contains(t) for t in city_tokens])
                    city_first = (
                        query.filter(loc_clause)
                        .order_by(UserDB.created_at.desc())
                        .limit(cap)
                        .all()
                    )
                    for u in city_first:
                        if u.id not in seen_ids:
                            merged.append(u)
                            seen_ids.add(u.id)
                    logger.info(
                        f"[her_find_candidates] 同城关键词优先: tokens={city_tokens}, 命中 {len(merged)} 人"
                    )
                remain = cap - len(merged)
                if remain > 0:
                    q_rest = query
                    if seen_ids:
                        q_rest = q_rest.filter(~UserDB.id.in_(list(seen_ids)))
                    rest = q_rest.order_by(UserDB.created_at.desc()).limit(remain).all()
                    for u in rest:
                        if u.id not in seen_ids:
                            merged.append(u)
                            seen_ids.add(u.id)
                candidates_db = merged
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

                # 🚀 [同城优先] 判断是否同城（宽松匹配）
                # 支持：无锡/无锡市、江苏无锡/无锡、Wuxi/无锡 等变体
                candidate_location = u.location or ""
                is_same_city = False

                # 🚀 [诊断日志] 打印每个候选人的地点对比
                logger.debug(f"[her_find_candidates] 同城判断: candidate_name={u.name}, candidate_location={candidate_location}, user_location={user_location}")

                if user_location and candidate_location:
                    # 双向包含匹配：一方包含另一方即可
                    user_loc_lower = user_location.lower()
                    cand_loc_lower = candidate_location.lower()
                    is_same_city = (
                        user_loc_lower == cand_loc_lower or
                        user_loc_lower in cand_loc_lower or
                        cand_loc_lower in user_loc_lower
                    )
                    # 增加城市名映射（常见别名）
                    city_aliases = {
                        "无锡": ["wuxi", "无锡市", "江苏无锡"],
                        "北京": ["beijing", "北京市"],
                        "上海": ["shanghai", "上海市"],
                        "广州": ["guangzhou", "广州市"],
                        "深圳": ["shenzhen", "深圳市"],
                        "杭州": ["hangzhou", "杭州市"],
                        "南京": ["nanjing", "南京市"],
                    }
                    for main_city, aliases in city_aliases.items():
                        if user_loc_lower in [main_city] + aliases or main_city in user_loc_lower:
                            if cand_loc_lower in [main_city] + aliases or main_city in cand_loc_lower:
                                is_same_city = True
                                break

                # 🚀 [诊断日志] 打印 is_same_city 结果
                logger.info(f"[her_find_candidates] 同城判断结果: {u.name} ({candidate_location}) vs 用户({user_location}) → is_same_city={is_same_city}")

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
                    # 🚀 [同城优先] 新增：同城标识（用于排序）
                    "is_same_city": is_same_city,
                    "vector_dimensions": {
                        "self": _safe_parse_json_object(getattr(u, "self_profile_json", "{}") or "{}").get("vector_dimensions", {}),
                        "desire": _safe_parse_json_object(getattr(u, "desire_profile_json", "{}") or "{}").get("vector_dimensions", {}),
                    },
                    "vector_match_highlights": _build_vector_match_highlights(
                        getattr(u, "self_profile_json", "{}") or "{}",
                        getattr(u, "desire_profile_json", "{}") or "{}",
                    ),
                })
            logger.info(f"[her_find_candidates] Step4 构建候选数据耗时: {time.time() - step4_start:.3f}s")

            # 🚀 [诊断日志] 排序前打印候选人列表
            logger.info(f"[her_find_candidates] 排序前候选人数: {len(candidates_raw)}")
            before_sort_locations = [(c.get('name', ''), c.get('location', ''), c.get('is_same_city', False)) for c in candidates_raw[:10]]
            logger.info(f"[her_find_candidates] 排序前前10: {before_sort_locations}")

            # 🚀 [同城优先] 排序：同城用户优先，然后按置信度排序
            # 如果用户没设置异地偏好（accept_remote 为空），默认同城优先
            if not location_hard_filter and user_location:
                candidates_raw.sort(key=lambda c: (
                    -c.get("is_same_city", False),  # 同城优先（True=1, 排前面）
                    -c.get("confidence_score", 0),   # 置信度高优先
                ))
                same_city_count = sum(1 for c in candidates_raw if c.get('is_same_city'))
                logger.info(f"[her_find_candidates] 同城优先排序完成，同城数: {same_city_count}")
                # 🚀 [诊断日志] 显示排序后前 5 个候选人的地点
                top5_locations = [c.get('location', '无') for c in candidates_raw[:5]]
                logger.info(f"[her_find_candidates] 排序后前5地点: {top5_locations}, 用户地点: {user_location}")
                # 🚀 [诊断日志] 显示排序后前 10 个候选人详情
                after_sort_locations = [(c.get('name', ''), c.get('location', ''), c.get('is_same_city', False)) for c in candidates_raw[:10]]
                logger.info(f"[her_find_candidates] 排序后前10: {after_sort_locations}")
            else:
                # 🚀 [诊断日志] 为什么没有执行排序
                logger.info(f"[her_find_candidates] 未执行同城排序: location_hard_filter={location_hard_filter}, user_location={user_location}")

        # ===== 生成 query_request_id（供同步/异步都可追踪）=====
        query_request_id = str(uuid.uuid4())

        # ===== 仅为最终精选 TOPN 生成推荐理由 =====
        reason_topn = _reason_topn()
        # 筛选实时查询优先响应：只需要返回候选列表与筛选元数据，
        # 不需要再次生成推荐理由，避免点击筛选时被 LLM 延迟拖慢。
        if filter_overrides:
            reason_topn = 0
        if candidates_raw and reason_topn > 0:
            reason_start = time.time()
            enrich_count = min(reason_topn, len(candidates_raw))
            reason_budget = _reason_total_budget_seconds()
            reason_workers = min(_reason_workers(), enrich_count)
            async_reason_mode = _reason_async_enabled() and not filter_overrides
            if async_reason_mode:
                # 主链路 fail-fast：先给兜底理由，后台异步细化。
                for idx in range(enrich_count):
                    candidates_raw[idx]["match_reasons"] = _fallback_match_reasons(candidates_raw[idx])
                with _REASON_CACHE_LOCK:
                    _ASYNC_REASON_CACHE[query_request_id] = {
                        "status": "pending",
                        "updated_at": int(time.time()),
                        "elapsed_ms": 0,
                        "reasons_by_user_id": {},
                    }
                top_candidates = [deepcopy(candidates_raw[i]) for i in range(enrich_count)]
                _REASON_ASYNC_EXECUTOR.submit(
                    _async_enrich_match_reasons,
                    query_request_id,
                    deepcopy(user_prefs),
                    top_candidates,
                    reason_budget,
                    reason_workers,
                )
                logger.info(
                    "[her_find_candidates] Step4.5 TOP%s 推荐理由异步化: cost=%.3fs (workers=%s, budget=%ss)",
                    enrich_count,
                    time.time() - reason_start,
                    reason_workers,
                    reason_budget,
                )
            else:
                enriched_indexes = set()
                executor = ThreadPoolExecutor(max_workers=reason_workers)
                timed_out = False
                future_to_index = {
                    executor.submit(_calculate_match_reasons, user_prefs, candidates_raw[i]): i
                    for i in range(enrich_count)
                }
                try:
                    try:
                        for future in as_completed(future_to_index, timeout=reason_budget):
                            idx = future_to_index[future]
                            candidate = candidates_raw[idx]
                            try:
                                candidate["match_reasons"] = future.result()
                                enriched_indexes.add(idx)
                            except Exception as e:
                                logger.warning(f"[her_find_candidates] 推荐理由并行任务失败，使用兜底: {e}")
                                candidate["match_reasons"] = _fallback_match_reasons(candidate)
                                enriched_indexes.add(idx)
                    except FuturesTimeoutError:
                        timed_out = True
                        logger.warning(
                            "[her_find_candidates] 推荐理由生成超出总预算 %ss，未完成任务使用兜底",
                            reason_budget,
                        )
                finally:
                    if timed_out:
                        executor.shutdown(wait=False, cancel_futures=True)
                    else:
                        executor.shutdown(wait=True, cancel_futures=False)

                for idx in range(enrich_count):
                    if idx not in enriched_indexes:
                        candidate = candidates_raw[idx]
                        candidate["match_reasons"] = _fallback_match_reasons(candidate)

                logger.info(
                    "[her_find_candidates] Step4.5 TOP%s 精选候选推荐理由耗时: %.3fs (workers=%s, budget=%ss)",
                    enrich_count,
                    time.time() - reason_start,
                    reason_workers,
                    reason_budget,
                )

        step5_start = time.time()
        retrieval_mode_input = _normalize_retrieval_mode(retrieval_mode)
        if retrieval_mode_input == "hybrid":
            retrieval_mode = "hybrid"
            retrieval_decision_source = "agent"
        elif retrieval_mode_input == "db_only":
            retrieval_mode = "db_only"
            retrieval_decision_source = "agent"
        else:
            retrieval_mode = "hybrid" if _is_hybrid_enabled() else "db_only"
            retrieval_decision_source = "system_default"

        retrieval_reason_clean = (retrieval_reason or "").strip()
        retrieval_stats: Dict[str, Any] = {
            "mode": retrieval_mode,
            "mode_input": retrieval_mode_input,
            "mode_decision_source": retrieval_decision_source,
            "mode_reason": retrieval_reason_clean,
            "before_recall": len(candidates_raw),
            "after_recall": len(candidates_raw),
            "after_rerank": len(candidates_raw),
        }

        if retrieval_mode == "hybrid" and candidates_raw:
            vector_topk = _safe_int_env("HER_MATCH_VECTOR_TOPK", DEFAULT_VECTOR_TOPK)
            rerank_pre_n = _safe_int_env("HER_MATCH_RERANK_PRE_N", DEFAULT_RERANK_PRE_N)
            rerank_topn = _safe_int_env("HER_MATCH_RERANK_TOPN", DEFAULT_RERANK_TOPN)

            hybrid_start = time.time()
            recall_service = VectorRecallService(top_k=vector_topk)
            recalled_candidates = recall_service.recall(user_prefs=user_prefs, candidates=candidates_raw)

            rerank_service = MatchRerankService(pre_rank_n=rerank_pre_n, final_top_n=rerank_topn)
            reranked_top = rerank_service.rerank(user_prefs=user_prefs, candidates=recalled_candidates)

            if reranked_top:
                top_ids = {candidate.get("user_id") for candidate in reranked_top if candidate.get("user_id")}
                remaining = [candidate for candidate in recalled_candidates if candidate.get("user_id") not in top_ids]
                candidates_raw = reranked_top + remaining
            else:
                candidates_raw = recalled_candidates

            retrieval_stats.update(
                {
                    "after_recall": len(recalled_candidates),
                    "after_rerank": len(reranked_top),
                    "recall_source": recall_service.last_source,
                    "recall_metrics": recall_service.last_metrics,
                    "vector_topk": vector_topk,
                    "rerank_pre_n": rerank_pre_n,
                    "rerank_topn": rerank_topn,
                    "hybrid_latency_ms": int((time.time() - hybrid_start) * 1000),
                }
            )

            logger.info(
                "[her_find_candidates] hybrid retrieval completed: before=%s recall=%s rerank=%s cost=%sms reason=%s",
                retrieval_stats["before_recall"],
                retrieval_stats["after_recall"],
                retrieval_stats["after_rerank"],
                retrieval_stats["hybrid_latency_ms"],
                retrieval_reason_clean or "n/a",
            )
        else:
            logger.info(
                "[her_find_candidates] db_only retrieval selected: before=%s source=%s input=%s reason=%s",
                retrieval_stats["before_recall"],
                retrieval_decision_source,
                retrieval_mode_input,
                retrieval_reason_clean or "n/a",
            )

        # ===== 返回原始数据 =====
        # 构建硬约束列表
        hard_constraints_list = [
            "排除封禁用户",
            "排除测试账号",
            f"性别过滤（{target_gender or '无限制'}）",
        ]
        if location_hard_filter:
            hard_constraints_list.append(f"地点过滤（同城：{user_location}）")
        elif user_location:
            # 🚀 [同城优先] 提示用户默认同城优先
            hard_constraints_list.append(f"同城优先（{user_location}）")
        selected_location_value = (selected_location or "").strip()
        if selected_location_value and selected_location_value != "全部" and not location_hard_filter:
            hard_constraints_list.append(f"地点过滤（{selected_location_value}）")
        if isinstance(user_prefs.get("preferred_age_min"), int) and isinstance(user_prefs.get("preferred_age_max"), int):
            hard_constraints_list.append(f"年龄过滤（{user_prefs.get('preferred_age_min')}-{user_prefs.get('preferred_age_max')}）")
        selected_goal_value = (selected_relationship_goal or "").strip()
        if selected_goal_value and selected_goal_value != "全部":
            hard_constraints_list.append(f"关系目标过滤（{selected_goal_value}）")

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
                "selected_filters": filter_options.get("selected", {}),
            },
            "filter_options": filter_options,
            "filter_applied": {
                "hard_constraints": hard_constraints_list,
                "soft_constraints": "由 Agent 自行判断",
            },
            "retrieval": retrieval_stats,
        }
        if _reason_async_enabled() and not filter_overrides:
            result_data["reason_generation"] = {
                "mode": "async",
                "status": "pending",
                "query_request_id": query_request_id,
                "budget_seconds": _reason_total_budget_seconds(),
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