"""
Embedding builder for DeerFlow Her match tools.

This module intentionally avoids hard dependency on external embedding APIs.
It provides deterministic, local vectors for hybrid retrieval fallback.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Dict, Iterable, List


DEFAULT_DIMENSION = 128
_TOKEN_SPLIT_RE = re.compile(r"[\s,，。.!?;:：/\\|()\[\]{}]+")


def _normalize_tokens(values: Iterable[str]) -> List[str]:
    tokens: List[str] = []
    for value in values:
        if not value:
            continue
        raw = str(value).strip().lower()
        if not raw:
            continue
        parts = [p.strip() for p in _TOKEN_SPLIT_RE.split(raw) if p.strip()]
        tokens.extend(parts if parts else [raw])
    return tokens


def _hash_bucket(token: str, dim: int) -> int:
    digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % dim


def vectorize_text_fields(values: Iterable[str], dim: int = DEFAULT_DIMENSION) -> List[float]:
    vec = [0.0] * dim
    tokens = _normalize_tokens(values)
    if not tokens:
        return vec

    for token in tokens:
        idx = _hash_bucket(token, dim)
        vec[idx] += 1.0

    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0:
        return vec
    return [v / norm for v in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def build_query_vector(user_prefs: Dict[str, Any], dim: int = DEFAULT_DIMENSION) -> List[float]:
    values = [
        user_prefs.get("location") or "",
        user_prefs.get("relationship_goal") or "",
        user_prefs.get("spending_style") or "",
        user_prefs.get("want_children") or "",
        user_prefs.get("preferred_location") or "",
    ]
    values.extend(user_prefs.get("interests") or [])
    return vectorize_text_fields(values, dim=dim)


def build_candidate_vector(candidate: Dict[str, Any], dim: int = DEFAULT_DIMENSION) -> List[float]:
    values = [
        candidate.get("location") or "",
        candidate.get("relationship_goal") or "",
        candidate.get("occupation") or "",
        candidate.get("education") or "",
        candidate.get("income_range") or "",
        candidate.get("bio") or "",
    ]
    values.extend(candidate.get("interests") or [])
    return vectorize_text_fields(values, dim=dim)
