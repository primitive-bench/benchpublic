"""Proportion-based statistics: Wilson intervals, McNemar's paired test, separability.

These back the leaderboard's confidence intervals and separability badges. The
implementations below are real and dependency-light (math only) so the harness
can run them without scipy; swap to scipy.stats for exact binomial p-values later.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from bench_schemas import StatTest


def wilson(successes: int, n: int, z: float = 1.96) -> StatTest:
    """Wilson score interval for a single proportion (Wilson 1927).

    Preferred over the normal/CLT approximation for eval-sized samples
    (arXiv:2503.01747). Default z=1.96 → 95% CI.
    """
    if n == 0:
        return StatTest(method="wilson", n=0, ci_low=0.0, ci_high=1.0)
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return StatTest(
        method="wilson",
        statistic=p,
        n=n,
        ci_low=max(0.0, center - half),
        ci_high=min(1.0, center + half),
    )


def mcnemar(n01: int, n10: int, continuity: bool = True) -> StatTest:
    """McNemar's test for two paired classifiers on the same items (McNemar 1947).

    n01 = items A wrong / B right; n10 = items A right / B wrong (discordant pairs).
    With continuity correction: chi2 = (|n01 - n10| - 1)^2 / (n01 + n10).
    """
    disc = n01 + n10
    if disc == 0:
        return StatTest(method="mcnemar", statistic=0.0, p_value=1.0, n=0)
    corr = 1 if continuity else 0
    chi2 = (abs(n01 - n10) - corr) ** 2 / disc
    p = math.erfc(math.sqrt(chi2 / 2))  # survival of chi2_1 = erfc(sqrt(x/2))
    return StatTest(method="mcnemar", statistic=chi2, p_value=p, n=disc)


@dataclass
class Separability:
    separable: bool
    test: StatTest


def separable(n01: int, n10: int, alpha: float = 0.05) -> Separability:
    """Decide whether two adapters are separable on a slice via McNemar.

    Trust gate: if not separable at this n, the leaderboard MUST NOT publish a
    single winner for the slice (raise n from measured discordance, or merge).
    """
    t = mcnemar(n01, n10)
    return Separability(separable=(t.p_value is not None and t.p_value < alpha), test=t)
