import math

import deerflow.community.her_tools.vector_recall_service as recall_module
from deerflow.community.her_tools.embedding_builder import (
    build_candidate_vector,
    build_query_vector,
    cosine_similarity,
)
from deerflow.community.her_tools.index_sync_worker import CandidateVectorIndexCache
from deerflow.community.her_tools.match_rerank_service import MatchRerankService
from deerflow.community.her_tools.vector_recall_service import VectorRecallService


def test_embedding_vectors_have_same_dimension():
    user_prefs = {"location": "北京", "interests": ["旅行", "阅读"], "relationship_goal": "serious"}
    candidate = {"location": "北京", "interests": ["旅行"], "relationship_goal": "serious"}

    query_vec = build_query_vector(user_prefs)
    cand_vec = build_candidate_vector(candidate)

    assert len(query_vec) == len(cand_vec) == 128
    assert math.isfinite(cosine_similarity(query_vec, cand_vec))


def test_vector_recall_orders_by_vector_score():
    service = VectorRecallService(top_k=2)
    user_prefs = {"location": "上海", "interests": ["电影", "旅行"], "relationship_goal": "serious"}
    candidates = [
        {"user_id": "u1", "location": "上海", "interests": ["电影"], "relationship_goal": "serious"},
        {"user_id": "u2", "location": "广州", "interests": ["健身"], "relationship_goal": "casual"},
        {"user_id": "u3", "location": "上海", "interests": ["电影", "旅行"], "relationship_goal": "serious"},
    ]

    result = service.recall(user_prefs=user_prefs, candidates=candidates)

    assert len(result) == 2
    assert result[0]["vector_score"] >= result[1]["vector_score"]
    assert "vector_score" in result[0]


def test_rerank_returns_top_n_with_scores():
    service = MatchRerankService(pre_rank_n=3, final_top_n=2)
    user_prefs = {"relationship_goal": "serious"}
    candidates = [
        {
            "user_id": "u1",
            "vector_score": 0.9,
            "confidence_score": 70,
            "is_same_city": True,
            "relationship_goal": "serious",
            "match_reasons": ["同城", "目标一致"],
        },
        {
            "user_id": "u2",
            "vector_score": 0.8,
            "confidence_score": 95,
            "is_same_city": False,
            "relationship_goal": "casual",
            "match_reasons": ["资料完整"],
        },
        {
            "user_id": "u3",
            "vector_score": 0.4,
            "confidence_score": 40,
            "is_same_city": True,
            "relationship_goal": "serious",
            "match_reasons": [],
        },
    ]

    result = service.rerank(user_prefs=user_prefs, candidates=candidates)

    assert len(result) == 2
    assert result[0]["rerank_score"] >= result[1]["rerank_score"]
    assert "utility_score" in result[0]


def test_vector_recall_falls_back_to_local_when_qdrant_disabled():
    service = VectorRecallService(top_k=2, use_qdrant=False)
    result = service.recall(
        user_prefs={"location": "杭州", "interests": ["阅读"]},
        candidates=[
            {"user_id": "u1", "location": "杭州", "interests": ["阅读"]},
            {"user_id": "u2", "location": "深圳", "interests": ["游戏"]},
        ],
    )
    assert len(result) == 2
    assert service.last_source == "local"
    assert "cache" in service.last_metrics


def test_vector_recall_uses_qdrant_when_available(monkeypatch):
    class FakePoint:
        def __init__(self, id, vector, payload):
            self.id = id
            self.vector = vector
            self.payload = payload

    class FakeCollection:
        def __init__(self, name):
            self.name = name

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self._created = False

        def get_collections(self):
            return type("C", (), {"collections": [FakeCollection("her_match_candidates")]})()

        def create_collection(self, *args, **kwargs):
            self._created = True

        def upsert(self, *args, **kwargs):
            return None

        def search(self, *args, **kwargs):
            return [
                type("R", (), {"score": 0.91, "payload": {"candidate": {"user_id": "u3", "location": "上海"}}})(),
                type("R", (), {"score": 0.62, "payload": {"candidate": {"user_id": "u1", "location": "上海"}}})(),
            ]

    monkeypatch.setattr(recall_module, "QDRANT_AVAILABLE", True)
    monkeypatch.setattr(recall_module, "QdrantClient", FakeClient)
    monkeypatch.setattr(recall_module, "PointStruct", FakePoint)
    monkeypatch.setattr(recall_module, "VectorParams", lambda size, distance: {"size": size, "distance": distance})
    monkeypatch.setattr(recall_module, "Distance", type("D", (), {"COSINE": "cosine"}))

    service = VectorRecallService(top_k=2, use_qdrant=True)
    result = service.recall(
        user_prefs={"location": "上海", "interests": ["电影"]},
        candidates=[
            {"user_id": "u1", "location": "上海", "interests": ["电影"]},
            {"user_id": "u3", "location": "上海", "interests": ["电影", "旅行"]},
        ],
    )
    assert len(result) == 2
    assert result[0]["user_id"] == "u3"
    assert "vector_score" in result[0]
    assert service.last_source == "qdrant"


def test_candidate_vector_index_cache_reuses_vector():
    cache = CandidateVectorIndexCache(ttl_seconds=120)
    candidate = {"user_id": "u-cache", "location": "北京", "interests": ["电影"], "relationship_goal": "serious"}
    v1 = cache.get_or_build(candidate)
    v2 = cache.get_or_build(candidate)

    assert v1 == v2
    updates, unchanged = cache.sync_batch([candidate])
    assert updates == 0
    assert unchanged == 1
    stats = cache.get_stats()
    assert "hit_rate" in stats
    assert stats["size"] >= 1
