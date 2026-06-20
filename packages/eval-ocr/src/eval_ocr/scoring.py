"""pass@test scoring for the OCR primitive (olmOCR-bench rules).

The OCR vertical scores a vendor's page transcription against the olmOCR-bench
**unit tests** rather than a single CER number: each test case is a rule applied
to the transcription and the cell is a HIT iff the rule passes. pass@test is a
*paired binary* outcome, which is exactly what the leaderboard's McNemar/Wilson
separability gate consumes (`bench_stats`).

The matching rules below are ported from allenai/olmocr (`olmocr/bench/tests.py`,
Apache-2.0) so our pass@test numbers stay comparable to the published
olmOCR-bench leaderboard. We use the same libraries the benchmark uses —
`rapidfuzz.fuzz.partial_ratio` for presence and `fuzzysearch.find_near_matches`
for reading order — so the threshold semantics match.

Test types (the `type` field on each case):
  * present / absent  — a 1–3 sentence fragment is / is not in the transcription
                        (fuzzy, threshold = 1 - max_diffs/len(fragment)).
  * order             — fragment `before` precedes fragment `after`.
  * baseline          — page-sanity: non-blank, no degenerate repetition.
  * table / format / footnote / math — deferred (second pass); scored as an
                        *uncharged non-attempt* (correct=None) so they never
                        pollute the board until their evaluators land.

`miss_reason` decomposes WHY a test failed (absent vs fuzzy_miss vs wrong_order …)
mirroring the extraction vertical's miss taxonomy.

Markdown structure is PRESERVED (the table/format tests parse it); the only
output cleanup is `strip_chatter`, which removes the wrapping ```fences and
"Here is the transcription:" preambles that prompted vision LLMs add despite the
instruction — so the rules judge OCR content, not chat formatting.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from rapidfuzz import fuzz

try:  # fuzzysearch is a hard dep; guard only so import never hard-fails in odd envs
    from fuzzysearch import find_near_matches
except Exception:  # pragma: no cover
    find_near_matches = None  # type: ignore[assignment]

from bench_schemas import ScorerOutput

# Test types with a real evaluator below. Everything else is deferred (uncharged).
SUPPORTED_TYPES = frozenset({"present", "absent", "order", "baseline"})
DEFERRED_TYPES = frozenset({"table", "format", "footnote", "math"})

_WS = re.compile(r"\s+")
# A vision LLM sometimes wraps output in a fenced block and/or a preamble line.
_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*\n(.*?)\n?```\s*$", re.DOTALL)
_PREAMBLE = re.compile(
    r"^\s*(here(?:'s| is)[^\n:]*:|transcription:|the (?:transcribed )?text[^\n:]*:)\s*\n",
    re.IGNORECASE,
)
# NFC plus the handful of "fancy" replacements olmOCR-bench normalizes away.
_FANCY = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", " ": " ",
    "ﬁ": "fi", "ﬂ": "fl",
}


def strip_chatter(text: str) -> str:
    """Remove a wrapping ```fence and a leading 'Here is the transcription:' line.

    Preserves all markdown *inside* the fence (tables/formatting), so only the
    chat scaffolding a prompted VLM adds is removed — never document structure.
    """
    if not text:
        return ""
    m = _FENCE.match(text.strip())
    if m:
        text = m.group(1)
    text = _PREAMBLE.sub("", text, count=1)
    return text


def normalize_text(s: str) -> str:
    """NFC + whitespace collapse + fancy-character folding (case preserved).

    Casing is handled per-test via `case_sensitive`, not here — matching the
    olmOCR-bench `normalize_text` contract.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    for k, v in _FANCY.items():
        s = s.replace(k, v)
    return _WS.sub(" ", s).strip()


def _partial_ratio(needle: str, haystack: str) -> float:
    """rapidfuzz partial_ratio in [0,1] (best substring alignment of needle)."""
    if not needle:
        return 1.0
    if not haystack:
        return 0.0
    return fuzz.partial_ratio(needle, haystack) / 100.0


def _presence_ratio(test: dict[str, Any], text: str) -> tuple[float, float]:
    """Return (ratio, threshold) for a present/absent test against `text`."""
    needle = normalize_text(str(test.get("text", "")))
    hay = text
    first_n, last_n = test.get("first_n"), test.get("last_n")
    if first_n:
        hay = hay[: int(first_n)]
    if last_n:
        hay = hay[-int(last_n):]
    if not test.get("case_sensitive", True):
        needle, hay = needle.lower(), hay.lower()
    ratio = _partial_ratio(needle, hay)
    threshold = 1.0 - (int(test.get("max_diffs", 0)) / max(1, len(needle)))
    return ratio, threshold


def _score_presence(test: dict[str, Any], text: str, *, want: bool) -> ScorerOutput:
    ratio, threshold = _presence_ratio(test, text)
    found = ratio >= threshold
    correct = found if want else (not found)
    metrics = {"partial_ratio": round(ratio, 4), "threshold": round(threshold, 4)}
    if correct:
        return ScorerOutput(correct=True, score=1.0, metrics=metrics)
    if want:  # expected present, but missing
        reason = "absent" if ratio < 0.5 else "fuzzy_miss"
    else:  # expected absent, but present
        reason = "unexpected_present"
    return ScorerOutput(correct=False, score=0.0, miss_reason=reason, metrics=metrics)


def _score_order(test: dict[str, Any], text: str) -> ScorerOutput:
    if find_near_matches is None:  # pragma: no cover - dep always present in practice
        return ScorerOutput(correct=None, miss_reason="deferred_test_type",
                            rationale="fuzzysearch unavailable")
    md = int(test.get("max_diffs", 0))
    before = normalize_text(str(test.get("before", "")))
    after = normalize_text(str(test.get("after", "")))
    bm = find_near_matches(before, text, max_l_dist=md) if before else []
    am = find_near_matches(after, text, max_l_dist=md) if after else []
    if not bm or not am:
        return ScorerOutput(correct=False, score=0.0, miss_reason="fragment_missing")
    ok = min(m.start for m in bm) < max(m.start for m in am)
    if ok:
        return ScorerOutput(correct=True, score=1.0)
    return ScorerOutput(correct=False, score=0.0, miss_reason="wrong_order")


_REPEAT = re.compile(r"(.{1,40}?)\1{29,}", re.DOTALL)  # ~30x repeat of a short run


def _score_baseline(test: dict[str, Any], text: str) -> ScorerOutput:
    """Page-sanity: non-blank, not a degenerate repetition loop."""
    max_length = test.get("max_length")
    alnum = sum(c.isalnum() for c in text)
    if max_length is not None:  # blank-page assertion
        ok = alnum <= int(max_length)
        return ScorerOutput(correct=ok, score=1.0 if ok else 0.0,
                            miss_reason=None if ok else "not_blank")
    if alnum < 1:
        return ScorerOutput(correct=False, score=0.0, miss_reason="empty")
    if _REPEAT.search(text):
        return ScorerOutput(correct=False, score=0.0, miss_reason="repetition_loop")
    return ScorerOutput(correct=True, score=1.0)


def score_test(test: dict[str, Any], text: str) -> ScorerOutput:
    """Score one olmOCR-bench test case against a page transcription.

    `text` is the vendor's raw transcription; it is de-chattered and normalized
    here. Deferred test types return an *uncharged* non-attempt (correct=None).
    """
    ttype = str(test.get("type", "")).lower()
    if ttype in DEFERRED_TYPES:
        return ScorerOutput(correct=None, miss_reason="deferred_test_type",
                            rationale=f"{ttype} evaluator not yet implemented")
    norm = normalize_text(strip_chatter(text))
    if ttype == "present":
        return _score_presence(test, norm, want=True)
    if ttype == "absent":
        return _score_presence(test, norm, want=False)
    if ttype == "order":
        return _score_order(test, norm)
    if ttype == "baseline":
        return _score_baseline(test, norm)
    return ScorerOutput(correct=None, miss_reason="unknown_test_type",
                        rationale=f"unrecognized test type {ttype!r}")
