"""eval-websearch — Primitive Bench vertical.

Web search — three-tier ground truth, query-form strata, McNemar separability.

Implements bench_core.Task + bench_core.Scorer for this primitive. The public
golden DEV split lives in golden-sets-public/websearch/; the held-out test split
lives only behind the private eval server. Slice definitions: slices.yaml.

Ported from arlenk2021/GoldenEvalsWebSearch (the web_search probe runner, query
forms, hit@k + miss taxonomy + sentinel verdict scoring, and the 10-slice
per-intent wins matrix).
"""

from eval_websearch.queries import DEFAULT_FORM, QUERY_FORMS, build_variants, strip_token
from eval_websearch.scoring import (
    MISS_MIRROR_PROMOTED,
    MISS_NOT_FOUND,
    MISS_RANKED_BELOW_K,
    SENTINEL_NOT_INDEXED,
    SENTINEL_RANKED_BELOW_K,
    classify_miss,
    find_promotions,
    first_correct_rank,
    hit_at_k,
)
from eval_websearch.slices import SLICES, assign_slices, wins_matrix
from eval_websearch.task import Scorer, Task

__all__ = [
    "Task",
    "Scorer",
    # query forms
    "QUERY_FORMS",
    "DEFAULT_FORM",
    "build_variants",
    "strip_token",
    # scoring
    "hit_at_k",
    "first_correct_rank",
    "classify_miss",
    "find_promotions",
    "MISS_RANKED_BELOW_K",
    "MISS_MIRROR_PROMOTED",
    "MISS_NOT_FOUND",
    "SENTINEL_RANKED_BELOW_K",
    "SENTINEL_NOT_INDEXED",
    # slices
    "SLICES",
    "assign_slices",
    "wins_matrix",
]
