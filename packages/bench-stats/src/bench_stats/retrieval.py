"""BEIR/MTEB-standard IR metrics for the search/retrieval/reranker primitives.

`relevances` is the graded relevance of each returned item in rank order
(0 = irrelevant). `n_relevant` is the total number of relevant items in the
corpus for the query (needed for recall-style denominators).
"""

from __future__ import annotations

import math
from typing import Sequence


def hit_at_k(relevances: Sequence[float], k: int) -> float:
    """1.0 if any of the top-k results is relevant, else 0.0."""
    return 1.0 if any(r > 0 for r in relevances[:k]) else 0.0


def mrr_at_k(relevances: Sequence[float], k: int) -> float:
    """Reciprocal rank of the first relevant item within top-k."""
    for i, r in enumerate(relevances[:k], start=1):
        if r > 0:
            return 1.0 / i
    return 0.0


def _dcg(relevances: Sequence[float], k: int) -> float:
    return sum(rel / math.log2(i + 1) for i, rel in enumerate(relevances[:k], start=1))


def ndcg_at_k(relevances: Sequence[float], k: int) -> float:
    """Normalized DCG@k against the ideal ranking of the same relevances."""
    ideal = sorted(relevances, reverse=True)
    idcg = _dcg(ideal, k)
    return _dcg(relevances, k) / idcg if idcg > 0 else 0.0


def map_at_k(relevances: Sequence[float], k: int, n_relevant: int | None = None) -> float:
    """Average precision @k (binary relevance: rel>0)."""
    hits = 0
    precision_sum = 0.0
    for i, r in enumerate(relevances[:k], start=1):
        if r > 0:
            hits += 1
            precision_sum += hits / i
    denom = n_relevant if n_relevant is not None else hits
    return precision_sum / denom if denom > 0 else 0.0
