"""
Hybrid vector recall service for her_find_candidates.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, List

from .embedding_builder import build_candidate_vector, build_query_vector, cosine_similarity
from .index_sync_worker import get_candidate_vector_cache

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, PointStruct, VectorParams

    QDRANT_AVAILABLE = True
except Exception:
    QDRANT_AVAILABLE = False
    QdrantClient = None  # type: ignore[assignment]
    Distance = PointStruct = VectorParams = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class VectorRecallService:
    """Vector recall service with Qdrant-first and local fallback."""

    def __init__(self, top_k: int = 50, use_qdrant: bool | None = None):
        self.top_k = max(1, int(top_k))
        if use_qdrant is None:
            use_qdrant = os.environ.get("HER_MATCH_QDRANT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.use_qdrant = bool(use_qdrant)
        self.collection_name = os.environ.get("HER_MATCH_QDRANT_COLLECTION", "her_match_candidates")
        self.qdrant_path = os.environ.get("HER_MATCH_QDRANT_PATH", ".deer-flow/qdrant_match")
        self.last_source = "local"
        self.fallback_count = 0
        self.last_metrics: Dict[str, Any] = {}
        self._qdrant_client = None
        self._cache = get_candidate_vector_cache()

    def _get_qdrant_client(self):
        if not self.use_qdrant or not QDRANT_AVAILABLE:
            return None
        if self._qdrant_client is None:
            self._qdrant_client = QdrantClient(path=self.qdrant_path)
        return self._qdrant_client

    def _build_point_id(self, user_id: str) -> int:
        digest = hashlib.md5((user_id or "").encode("utf-8")).hexdigest()
        # Keep it in signed 63-bit range to avoid backend differences.
        return int(digest[:15], 16)

    def _ensure_collection(self, vector_size: int) -> None:
        client = self._get_qdrant_client()
        if client is None:
            return

        try:
            existing = {c.name for c in client.get_collections().collections}
            if self.collection_name not in existing:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
        except Exception as exc:
            logger.warning("[VectorRecallService] ensure_collection failed: %s", exc)
            raise

    def _recall_with_qdrant(self, user_prefs: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        client = self._get_qdrant_client()
        if client is None:
            return []

        query_vec = build_query_vector(user_prefs)
        if not query_vec:
            return []

        self._ensure_collection(vector_size=len(query_vec))
        points: List[Any] = []
        for candidate in candidates:
            user_id = str(candidate.get("user_id") or "")
            if not user_id:
                continue
            points.append(
                PointStruct(
                    id=self._build_point_id(user_id),
                    vector=self._cache.get_or_build(candidate),
                    payload={"candidate": candidate},
                )
            )

        if points:
            client.upsert(collection_name=self.collection_name, points=points, wait=False)

        results = client.search(
            collection_name=self.collection_name,
            query_vector=query_vec,
            limit=self.top_k,
            with_payload=True,
            with_vectors=False,
        )

        recalled: List[Dict[str, Any]] = []
        for item in results:
            payload = item.payload or {}
            candidate = dict(payload.get("candidate") or {})
            if not candidate:
                continue
            candidate["vector_score"] = round(float(item.score or 0.0), 6)
            recalled.append(candidate)
        return recalled

    def recall(self, user_prefs: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        self._cache.sync_batch(candidates)
        self._cache.purge_expired()

        if self.use_qdrant:
            try:
                qdrant_result = self._recall_with_qdrant(user_prefs=user_prefs, candidates=candidates)
                if qdrant_result:
                    self.last_source = "qdrant"
                    self.last_metrics = {
                        "recall_source": self.last_source,
                        "fallback_count": self.fallback_count,
                        "cache": self._cache.get_stats(),
                    }
                    return qdrant_result
            except Exception as exc:
                logger.warning("[VectorRecallService] qdrant recall failed, fallback to local: %s", exc)
                self.fallback_count += 1

        query_vec = build_query_vector(user_prefs)
        scored: List[Dict[str, Any]] = []
        for candidate in candidates:
            cand_vec = self._cache.get_or_build(candidate)
            score = cosine_similarity(query_vec, cand_vec)
            enriched = dict(candidate)
            enriched["vector_score"] = round(score, 6)
            scored.append(enriched)

        scored.sort(key=lambda item: item.get("vector_score", 0.0), reverse=True)
        self.last_source = "local"
        self.last_metrics = {
            "recall_source": self.last_source,
            "fallback_count": self.fallback_count,
            "cache": self._cache.get_stats(),
        }
        return scored[: self.top_k]
