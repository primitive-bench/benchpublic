"""Terminal result states for one scored extraction cell.

Ported from arlenk2021/AgentsBenchmark (wrodium/scoring/states.py + metrics.py),
adapted to the token-survival scoring model of the web_extraction probe.

A "cell" is one (vendor, golden row) pair. Exactly one state is assigned. The
distinction between `no_coverage`/`blocked` and a genuine `incorrect` matters for
publishing: a `blocked` cell is an anti-bot capability gap, NOT a freshness or
extraction-quality miss — it must be reported separately so a vendor that is
merely being firewalled is not confused with one that extracted real content
lacking the truth token. `no_coverage` renders as `-` (never a zero) per each
metric's dash_semantics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ResultState(str, Enum):
    CORRECT = "correct"             # truth token survived extraction
    INCORRECT = "incorrect"        # extracted real content, but token absent (token_absent)
    NO_COVERAGE = "no_coverage"     # vendor returned nothing for this item -> renders as '-'
    BLOCKED = "blocked"             # anti-bot / access-wall interstitial (the bot-blocking gap)
    TIMEOUT = "timeout"
    FETCH_FAILED = "fetch_failed"

    @property
    def is_attempt(self) -> bool:
        """Did the vendor produce a scoreable answer? Only correct/incorrect count
        toward accuracy denominators; the rest are coverage/availability signals.

        BLOCKED is deliberately NOT an attempt: when Exa is firewalled on the
        Federal Register, charging it an `incorrect` would conflate an anti-bot
        wall with a genuine extraction miss — the whole point of the miss
        decomposition is to keep those apart."""
        return self in (ResultState.CORRECT, ResultState.INCORRECT)


# The probe's miss_reason vocabulary maps onto the terminal states above. This is
# the bridge between the token-survival scorer (scoring.py) and the equivalence-
# state model: a miss is classified, then projected onto a ResultState so the
# leaderboard's coverage/availability columns stay honest.
#
# blocked      -> BLOCKED       (anti-bot wall; a DIFFERENT capability gap)
# token_absent -> INCORRECT     (real content extracted, truth token not present)
# empty        -> NO_COVERAGE   (vendor returned nothing usable -> renders '-')
_MISS_TO_STATE: dict[str, ResultState] = {
    "blocked": ResultState.BLOCKED,
    "token_absent": ResultState.INCORRECT,
    "empty": ResultState.NO_COVERAGE,
}


def state_for(hit: bool, miss_reason: Optional[str], *, error: Optional[str] = None) -> ResultState:
    """Project a token-survival outcome onto exactly one ResultState.

    A transport error short-circuits to FETCH_FAILED. A hit is CORRECT. Otherwise
    the miss_reason from `scoring.classify_miss` selects the terminal state, with
    `token_absent` as the conservative default (a miss we could not otherwise
    explain is charged as a genuine extraction miss, never silently dropped)."""
    if error:
        return ResultState.FETCH_FAILED
    if hit:
        return ResultState.CORRECT
    return _MISS_TO_STATE.get(miss_reason or "", ResultState.INCORRECT)


# Sentinel: a metric with no data to compute. Publishers render it via the
# primitive's per-metric `dash_semantics`, NOT as the number 0.
DASH: Optional[float] = None


@dataclass
class VendorStates:
    """Per-vendor state tally for the equivalence-state view of one slice.

    accuracy here is token-survival over scoreable attempts (correct+incorrect);
    coverage is attempts / n. `blocked` is surfaced as its own column so the
    "anti-bot blocking, not freshness" story is legible without re-deriving it.
    """

    vendor: str
    n: int                                  # rows attempted
    accuracy: Optional[float]               # correct / (correct + incorrect)
    coverage: Optional[float]               # attempts / n
    blocked_rate: Optional[float]           # blocked / n  (the anti-bot wall rate)
    state_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "vendor": self.vendor, "n": self.n,
            "accuracy": self.accuracy, "coverage": self.coverage,
            "blocked_rate": self.blocked_rate,
            "state_counts": self.state_counts,
        }


def aggregate_states(vendor: str, states: list[ResultState]) -> VendorStates:
    """Tally ResultStates for one vendor into the equivalence-state metrics.

    Mirrors wrodium/scoring/metrics.aggregate_vendor, but specialised to the
    token-survival model: `accuracy` is token survival on scoreable attempts,
    and a `blocked_rate` column is added so the anti-bot gap is first-class.
    no-attempt cases return `None` (rendered '-'), never 0."""
    n = len(states)
    if not n:
        return VendorStates(vendor, 0, DASH, DASH, DASH)
    counts: dict[str, int] = {s.value: 0 for s in ResultState}
    for s in states:
        counts[s.value] += 1

    correct = counts[ResultState.CORRECT.value]
    attempts = correct + counts[ResultState.INCORRECT.value]
    blocked = counts[ResultState.BLOCKED.value]

    accuracy = (correct / attempts) if attempts else DASH      # no attempts -> '-'
    coverage = attempts / n if n else DASH
    blocked_rate = blocked / n if n else DASH
    return VendorStates(
        vendor=vendor, n=n, accuracy=accuracy, coverage=coverage,
        blocked_rate=blocked_rate, state_counts=counts,
    )
