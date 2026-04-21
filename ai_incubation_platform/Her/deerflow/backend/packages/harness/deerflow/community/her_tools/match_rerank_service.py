"""
Rerank service for DeerFlow match tools.
"""

from __future__ import annotations

from typing import Any, Dict, List


class MatchRerankService:
    """
    Two-stage lightweight reranker:
    1) utility_score for broad ordering
    2) final_score for top-N output
    """

    def __init__(self, pre_rank_n: int = 15, final_top_n: int = 3):
        self.pre_rank_n = max(1, int(pre_rank_n))
        self.final_top_n = max(1, int(final_top_n))

    def rerank(self, user_prefs: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        staged: List[Dict[str, Any]] = []
        for candidate in candidates:
            vector_score = float(candidate.get("vector_score", 0.0))
            confidence_score = float(candidate.get("confidence_score", 0.0)) / 100.0
            same_city = 1.0 if candidate.get("is_same_city") else 0.0

            goal_match = 0.0
            user_goal = (user_prefs.get("relationship_goal") or "").strip().lower()
            cand_goal = (candidate.get("relationship_goal") or "").strip().lower()
            if user_goal and cand_goal and user_goal == cand_goal:
                goal_match = 1.0

            utility_score = 0.55 * vector_score + 0.25 * confidence_score + 0.15 * same_city + 0.05 * goal_match

            enriched = dict(candidate)
            enriched["utility_score"] = round(utility_score, 6)
            staged.append(enriched)

        staged.sort(key=lambda item: item.get("utility_score", 0.0), reverse=True)
        pre_ranked = staged[: self.pre_rank_n]

        for candidate in pre_ranked:
            utility_score = float(candidate.get("utility_score", 0.0))
            reasons_bonus = min(len(candidate.get("match_reasons") or []), 4) * 0.01
            candidate["rerank_score"] = round(utility_score + reasons_bonus, 6)

        pre_ranked.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
        return pre_ranked[: self.final_top_n]
