"""bench-core — the harness engine for Primitive Bench.

Responsibilities:
  * deterministic seeding (PYTHONHASHSEED=0 + per-run master seed)
  * the run loop: dataset -> adapter -> scorer -> ItemResult (streamed JSONL)
  * per-run result directory layout (ann-benchmarks pattern)
  * manifest writer

Architecture mirrors Inspect AI / lm-eval: dataset -> Task -> Solver -> Scorer.
v0.1.0 ships frozen interfaces (Task, Scorer, run_task) so the eval-* lanes can
build against them. See DECISIONS.md D-05.
"""

from bench_core.engine import Scorer, Task, run_task
from bench_core.runlayout import RunDir

# Shared infrastructure ported from arlenk2021/GoldenEvalsWebSearch.
# These submodules are the public surface other lanes import (see INTERPACKAGE.md):
#   from bench_core.urls import EquivalenceClass, normalize_url
#   from bench_core.http import fetch, FetchResult
#   from bench_core.split import hmac_split
#   from bench_core.verify import liveness_gate, Liveness
#   from bench_core.goldgen import ...   (registry-delta pump adapters)
from bench_core import goldgen, http, split, urls, verify

__all__ = [
    "Task",
    "Scorer",
    "run_task",
    "RunDir",
    "urls",
    "http",
    "split",
    "verify",
    "goldgen",
]
