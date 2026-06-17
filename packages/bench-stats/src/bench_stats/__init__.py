"""bench-stats — the statistics library for Primitive Bench.

Canonical, citable methods only. These produce the StatTest objects carried on
SliceResult, and the `separable` trust gate the leaderboard depends on.

  mcnemar(...)        — paired comparison on the same test set (McNemar 1947, w/ continuity correction)
  wilson(...)         — CI for a single proportion (Wilson 1927; preferred over CLT for eval-sized n)
  bootstrap_ci(...)   — seeded bootstrap CI for non-proportion metrics (nDCG, MCC, AUROC)
  hit_at_k(...)       — retrieval hit@k
  ndcg_at_k / map_at_k / mrr_at_k  — BEIR/MTEB-standard IR metrics
  separable(...)      — McNemar-based separability decision for two adapters on a slice

Implementations are stubs in v0.1.0 — signatures are frozen against bench-schemas
so downstream lanes can code against them. See DECISIONS.md D-04.
"""

from bench_stats.proportions import mcnemar, wilson, separable
from bench_stats.resampling import bootstrap_ci
from bench_stats.retrieval import hit_at_k, ndcg_at_k, map_at_k, mrr_at_k

__all__ = [
    "mcnemar",
    "wilson",
    "separable",
    "bootstrap_ci",
    "hit_at_k",
    "ndcg_at_k",
    "map_at_k",
    "mrr_at_k",
]
