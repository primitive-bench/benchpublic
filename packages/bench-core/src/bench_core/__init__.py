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

__all__ = ["Task", "Scorer", "run_task", "RunDir"]
