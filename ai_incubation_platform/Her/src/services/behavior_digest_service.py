"""
从用户近期行为事件（DB）中，由 LLM 选择性提炼可长期记录的偏好/意图摘要，并写入 behavior_digest.jsonl。

原始全量行为仍以 behavior_raw.jsonl + behavior_events 表为准；本模块只做「压缩与解读」，避免把噪声全部写进画像。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import settings
from db.models import BehaviorEventDB
from llm.client import call_llm
from utils.behavior_raw_log import append_behavior_digest_line
from utils.logger import logger


def _events_to_prompt_lines(rows: List[BehaviorEventDB], max_lines: int = 120) -> str:
    lines: List[str] = []
    for r in rows[:max_lines]:
        ts = r.created_at.isoformat() if r.created_at else ""
        extra = json.dumps(r.event_data or {}, ensure_ascii=False, default=str)[:400]
        tid = r.target_id or "-"
        lines.append(f"- {ts} | {r.event_type} | target={tid} | data={extra}")
    return "\n".join(lines)


_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.I)


def _parse_llm_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    t = text.strip()
    m = _JSON_FENCE.search(t)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return None


def run_behavior_digest(db: Session, user_id: str, limit: int = 150) -> Dict[str, Any]:
    """
    读取最近行为 → LLM 提炼 → 写入 behavior_digest.jsonl，并返回结构化结果。
    LLM 关闭时仅返回统计与提示，不写 digest 文件。
    """
    rows = (
        db.query(BehaviorEventDB)
        .filter(BehaviorEventDB.user_id == user_id)
        .order_by(desc(BehaviorEventDB.created_at))
        .limit(limit)
        .all()
    )

    if not rows:
        return {"success": True, "user_id": user_id, "event_count": 0, "digest": None, "message": "无行为记录"}

    if not settings.llm_enabled or not (settings.llm_api_key or "").strip():
        return {
            "success": True,
            "user_id": user_id,
            "event_count": len(rows),
            "digest": None,
            "message": "LLM 未启用或未配置密钥，跳过 AI 整理；原始行为仍记录在 behavior_raw.jsonl / 数据库",
        }

    lines = _events_to_prompt_lines(rows)
    system = (
        "你是用户行为分析助手。下面是一段时间内的用户行为流水（已脱敏/截断）。"
        "请只做「选择性整理」：输出严格 JSON，不要 markdown 正文。"
        "规则：忽略明显重复与噪声；合并同类意图；不要臆造未出现的事实；不要输出任何密钥或个人敏感原文。"
        'JSON schema: {"summary": string, "preference_signals": string[], '
        '"interaction_style_notes": string|null, "candidates_of_interest": string[] (user id 列表，仅从 target 字段出现过的 id 中选), '
        '"confidence": "low"|"medium"|"high", "discard": string[] }'
    )
    user_prompt = f"用户 id: {user_id}\n近期行为（从新到旧，最多 {len(rows)} 条）:\n{lines}"

    try:
        raw = call_llm(user_prompt, system_prompt=system, temperature=0.2, max_tokens=1200, timeout=90)
    except Exception as e:
        logger.warning("[behavior_digest] LLM 调用失败: %s", e)
        return {"success": False, "user_id": user_id, "event_count": len(rows), "error": str(e)}

    parsed = _parse_llm_json(raw) or {"summary": raw[:2000], "preference_signals": [], "confidence": "low"}

    append_behavior_digest_line(
        {
            "user_id": user_id,
            "source_event_count": len(rows),
            "digest": parsed,
        }
    )
    logger.info("[BEHAVIOR_DIGEST] user=%s events=%s confidence=%s", user_id, len(rows), parsed.get("confidence"))

    return {
        "success": True,
        "user_id": user_id,
        "event_count": len(rows),
        "digest": parsed,
        "message": "已写入 logs/behavior_digest.jsonl",
    }
