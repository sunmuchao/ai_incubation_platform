"""
用户行为原始日志：每条行为一行 JSON（append-only），与 DB 双写，便于全量审计与离线分析。

AI 选择性整理见 behavior_digest_service（读 DB / 日志摘要，调用 LLM 写入 digest 文件）。
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

_file_lock = threading.Lock()

_SENSITIVE_KEY = re.compile(r"(password|secret|token|authorization|api_key|refresh|cookie)", re.I)
_MAX_STR = 600


def _log_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "logs"


def _sanitize(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated-depth]"
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if _SENSITIVE_KEY.search(str(k)):
                out[k] = "[redacted]"
            else:
                out[k] = _sanitize(v, depth + 1)
        return out
    if isinstance(obj, list):
        return [_sanitize(x, depth + 1) for x in obj[:200]]
    if isinstance(obj, str):
        if len(obj) > _MAX_STR:
            return obj[:_MAX_STR] + "…[truncated]"
        return obj
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    return str(obj)[:_MAX_STR]


def append_behavior_raw_line(
    *,
    event_id: str,
    user_id: str,
    event_type: str,
    target_id: Optional[str],
    event_data: Optional[Dict[str, Any]],
    trace_id: Optional[str] = None,
) -> None:
    if os.getenv("BEHAVIOR_RAW_LOG_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return

    line = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id,
        "event_id": event_id,
        "user_id": user_id,
        "event_type": event_type,
        "target_id": target_id,
        "event_data": _sanitize(event_data or {}),
    }

    path = _log_dir() / "behavior_raw.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(line, ensure_ascii=False, default=str) + "\n"
        with _file_lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(payload)
    except Exception:
        # 绝不因写文件失败影响主流程
        pass


def append_behavior_digest_line(record: Dict[str, Any]) -> None:
    """LLM 整理后的摘要行（append-only）。"""
    if os.getenv("BEHAVIOR_DIGEST_LOG_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return
    path = _log_dir() / "behavior_digest.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {**record, "ts": datetime.utcnow().isoformat() + "Z"}
        payload = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
        with _file_lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(payload)
    except Exception:
        pass
