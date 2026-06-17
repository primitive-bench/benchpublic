"""Seeded bootstrap CIs for non-proportion metrics (nDCG, MCC, AUROC, latency).

Seed is REQUIRED and recorded in StatTest.seed for reproducibility — LMSYS-style
percentile bootstrap. Stdlib-only (random) so the harness has no scipy hard dep.
"""

from __future__ import annotations

import random
from typing import Callable, Sequence

from bench_schemas import StatTest


def bootstrap_ci(
    values: Sequence[float],
    seed: int,
    statistic: Callable[[Sequence[float]], float] = lambda v: sum(v) / len(v),
    resamples: int = 1000,
    alpha: float = 0.05,
) -> StatTest:
    """Percentile bootstrap CI. `seed` is mandatory and stored for reproducibility."""
    if not values:
        return StatTest(method="bootstrap", n=0, seed=seed)
    rng = random.Random(seed)
    n = len(values)
    point = statistic(values)
    samples = []
    for _ in range(resamples):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(statistic(resample))
    samples.sort()
    lo = samples[int((alpha / 2) * resamples)]
    hi = samples[min(resamples - 1, int((1 - alpha / 2) * resamples))]
    return StatTest(method="bootstrap", statistic=point, n=n, seed=seed, ci_low=lo, ci_high=hi)
