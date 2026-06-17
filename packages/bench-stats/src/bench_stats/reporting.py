"""Richer reporting statistics for the leaderboard — the corrected stance.

Ported from arlenk2021/GoldenEvalsWebSearch (src/reporting/stats.py + slices.py).

- Wilson score intervals everywhere (never normal-approx on proportions) — the
  Wilson interval itself lives in `proportions.wilson`; this module reuses it for
  the tied-rank band logic.
- McNemar on a PRE-REGISTERED primary pair (not blanket Holm across 15 pairs,
  which silently destroys the power the n target assumes). Exact binomial for
  small discordance, continuity-corrected chi-square otherwise.
- A global Cochran–Mantel–Haenszel across vendors as the omnibus test.
- Discordance + post-hoc power helpers so n is DERIVED from a pilot, not assumed.
- CUSUM on a stable anchor set for overfit/regression detection.
- Tied-rank bands so a slice names a winner only when its Wilson interval clears
  the runner-up's — otherwise a TIE band.

Unlike the dependency-light `proportions`/`resampling`/`retrieval` modules, this
module depends on scipy/statsmodels (as the source does) for the exact binomial
McNemar, the Connor power approximation, and the StratifiedTable CMH test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy import stats
from statsmodels.stats.contingency_tables import StratifiedTable, mcnemar as _sm_mcnemar


def mcnemar_pair(b: int, c: int) -> tuple[float, float]:
    """Paired test on discordant counts b (A hit, B miss) and c (A miss, B hit).

    Returns (statistic, p_value). Uses exact binomial for small discordance
    (b + c < 25), otherwise the continuity-corrected chi-square form. The
    cutoff matters: the chi-square approximation is unreliable when discordance
    is small, where the exact binomial is both available and correct.
    """
    table = [[0, b], [c, 0]]
    exact = (b + c) < 25
    res = _sm_mcnemar(table, exact=exact, correction=not exact)
    return float(res.statistic), float(res.pvalue)


def discordance_rate(b: int, c: int, n: int) -> float:
    """Fraction of paired items on which the two systems disagree."""
    return (b + c) / n if n else 0.0


def mcnemar_power(n: int, b_rate: float, c_rate: float, alpha: float = 0.05) -> float:
    """Approximate power of McNemar's test (Connor 1987 normal approx).

    b_rate, c_rate are the two discordant-cell probabilities (b_rate+c_rate is
    the discordance). Use the pilot's observed rates to size the real cohort.
    """
    psi = b_rate + c_rate
    if psi == 0:
        return 0.0
    diff = abs(b_rate - c_rate)
    z_a = stats.norm.ppf(1 - alpha / 2)
    # noncentrality under the alternative
    num = diff * math.sqrt(n) - z_a * math.sqrt(psi)
    return float(stats.norm.cdf(num / math.sqrt(psi - diff**2)) if psi > diff**2 else 1.0)


def required_n(b_rate: float, c_rate: float, power: float = 0.8, alpha: float = 0.05) -> int:
    """Smallest n reaching `power` for McNemar given pilot discordant rates.

    For a fixed marginal gap, the required n scales as discordance / gap**2:
    the more the systems disagree (larger psi), the larger n must be. This is
    why n is DERIVED from a pilot's observed discordance, never assumed.
    """
    psi = b_rate + c_rate
    diff = abs(b_rate - c_rate)
    if diff == 0:
        return math.inf  # type: ignore[return-value]
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    n = ((z_a * math.sqrt(psi) + z_b * math.sqrt(psi - diff**2)) / diff) ** 2
    return math.ceil(n)


def cmh_global(tables: list[list[list[int]]]) -> tuple[float, float]:
    """Cochran–Mantel–Haenszel omnibus across strata/vendors. Returns (stat, p).

    The omnibus test over all 2x2 strata — preferred over a blanket family of
    pairwise McNemar tests, which would require multiplicity control that eats
    the power the n target was sized for.
    """
    st = StratifiedTable(tables)
    res = st.test_null_odds()
    return float(res.statistic), float(res.pvalue)


def cusum(values: list[float], target: float, k: float = 0.5) -> list[float]:
    """One-sided upper CUSUM of (value - target). Run on the anchor set only.

    Accumulates positive excursions above target (with slack k) so a slow drift
    on a stable anchor set is flagged as overfit/regression before any single
    point would trip a threshold.
    """
    out, acc = [], 0.0
    for v in values:
        acc = max(0.0, acc + (v - target - k))
        out.append(acc)
    return out


@dataclass
class RankBand:
    """A tied-rank band: the leader plus everyone whose interval overlaps it.

    `winner` is set only when the band is a single vendor (its Wilson interval
    clears the runner-up's); otherwise `band` is the tie group and `winner` is
    None. This is what lets the benchmark say "Firecrawl wins government_registry"
    instead of forcing a single #1 onto a statistical tie.
    """

    band: list[str]
    winner: str | None


def tied_rank_band(rates: list[tuple[str, float, float, float]]) -> RankBand:
    """Tied-rank band from (name, point, low, high) tuples.

    A winner is named only when its Wilson interval clears the runner-up's;
    otherwise a TIE band of every entry whose upper bound overlaps the leader's
    lower bound. `rates` need not be pre-sorted — the leader is taken as the
    highest point estimate.

    Returns a RankBand whose `band` lists the tie group (leader first) and whose
    `winner` is the single name when the band has exactly one member, else None.
    """
    if not rates:
        return RankBand(band=[], winner=None)
    ordered = sorted(rates, key=lambda x: -x[1])
    _, _top_p, top_lo, _top_hi = ordered[0]
    band: list[str] = []
    for name, _p, _lo, hi in ordered:
        if hi >= top_lo:  # overlaps the leader's interval
            band.append(name)
        else:
            break
    winner = band[0] if len(band) == 1 else None
    return RankBand(band=band, winner=winner)
