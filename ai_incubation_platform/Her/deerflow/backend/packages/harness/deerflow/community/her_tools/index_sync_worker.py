"""
Index sync worker for Her match hybrid retrieval.

Provides lightweight in-process cache with fingerprint-based incremental refresh.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, List, Tuple

from .embedding_builder import build_candidate_vector


def _fingerprint_candidate(candidate: Dict[str, Any]) -> str:
    core = {
        "user_id": candidate.get("user_id"),
        "location": candidate.get("location"),
        "relationship_goal": candidate.get("relationship_goal"),
        "interests": candidate.get("interests") or [],
        "occupation": candidate.get("occupation"),
        "education": candidate.get("education"),
        "income_range": candidate.get("income_range"),
        "bio": candidate.get("bio"),
    }
    raw = json.dumps(core, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class CandidateVectorIndexCache:
    """Thread-safe in-process cache for candidate vectors."""

    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = max(30, int(ttl_seconds))
        self._lock = threading.Lock()
        self._store: Dict[str, Dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0
        self._last_sync_updates = 0
        self._last_sync_unchanged = 0
        self._last_purged = 0

    def get_or_build(self, candidate: Dict[str, Any]) -> List[float]:
        user_id = str(candidate.get("user_id") or "")
        if not user_id:
            return build_candidate_vector(candidate)

        now = time.time()
        fp = _fingerprint_candidate(candidate)
        with self._lock:
            item = self._store.get(user_id)
            if item:
                if item.get("fingerprint") == fp and (now - float(item.get("updated_at", 0))) <= self.ttl_seconds:
                    self._hits += 1
                    return item.get("vector") or []

            self._misses += 1
            vector = build_candidate_vector(candidate)
            self._store[user_id] = {
                "fingerprint": fp,
                "vector": vector,
                "updated_at": now,
            }
            return vector

    def sync_batch(self, candidates: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Returns (insert_or_update_count, unchanged_count)."""
        updates = 0
        unchanged = 0
        for candidate in candidates:
            user_id = str(candidate.get("user_id") or "")
            if not user_id:
                continue
            fp = _fingerprint_candidate(candidate)
            now = time.time()
            with self._lock:
                item = self._store.get(user_id)
                if item and item.get("fingerprint") == fp and (now - float(item.get("updated_at", 0))) <= self.ttl_seconds:
                    unchanged += 1
                    continue
                self._store[user_id] = {
                    "fingerprint": fp,
                    "vector": build_candidate_vector(candidate),
                    "updated_at": now,
                }
                updates += 1
        self._last_sync_updates = updates
        self._last_sync_unchanged = unchanged
        return updates, unchanged

    def purge_expired(self) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            keys = list(self._store.keys())
            for key in keys:
                item = self._store.get(key) or {}
                if (now - float(item.get("updated_at", 0))) > self.ttl_seconds:
                    self._store.pop(key, None)
                    removed += 1
        self._last_purged = removed
        return removed

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total else 0.0
        return {
            "ttl_seconds": self.ttl_seconds,
            "size": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "last_sync_updates": self._last_sync_updates,
            "last_sync_unchanged": self._last_sync_unchanged,
            "last_purged": self._last_purged,
        }


_default_ttl = int(os.environ.get("HER_MATCH_INDEX_CACHE_TTL_SECONDS", "900") or 900)
_candidate_vector_cache = CandidateVectorIndexCache(ttl_seconds=_default_ttl)


def get_candidate_vector_cache() -> CandidateVectorIndexCache:
    return _candidate_vector_cache
