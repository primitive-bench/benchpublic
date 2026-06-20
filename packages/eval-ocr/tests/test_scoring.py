"""Unit tests for the olmOCR-bench pass@test evaluators (pure, no network/tesseract)."""
from __future__ import annotations

from eval_ocr.scoring import normalize_text, score_test, strip_chatter

PAGE = (
    "Primitive Bench: Evaluating OCR Systems\n"
    "Abstract. We benchmark optical character recognition across document types.\n"
    "1. Introduction\n"
    "The reading order of a multi-column page matters for retrieval."
)


# --- normalization -------------------------------------------------------
def test_normalize_collapses_whitespace_and_folds_fancy_chars():
    assert normalize_text("a   b\n\tc") == "a b c"
    assert normalize_text("“quote”  ‘x’ – y") == '"quote" \'x\' - y'


def test_strip_chatter_removes_fence_and_preamble():
    assert strip_chatter("```\nHELLO\n```") == "HELLO"
    assert strip_chatter("```markdown\nHELLO\n```") == "HELLO"
    assert strip_chatter("Here is the transcription:\nHELLO") == "HELLO"
    assert strip_chatter("plain text") == "plain text"


# --- present / absent ----------------------------------------------------
def test_present_hit():
    out = score_test({"type": "present", "text": "benchmark optical character recognition"}, PAGE)
    assert out.correct is True and out.score == 1.0


def test_present_miss_is_absent():
    out = score_test({"type": "present", "text": "wholly unrelated sentence here"}, PAGE)
    assert out.correct is False and out.miss_reason == "absent"


def test_absent_hit_when_text_not_present():
    out = score_test({"type": "absent", "text": "CONFIDENTIAL DRAFT"}, PAGE)
    assert out.correct is True


def test_absent_miss_when_text_present():
    out = score_test({"type": "absent", "text": "Introduction"}, PAGE)
    assert out.correct is False and out.miss_reason == "unexpected_present"


def test_max_diffs_tolerates_typos():
    typoed = "benchmark optcal charcter recogniton"  # 3 deletions
    strict = score_test({"type": "present", "text": typoed, "max_diffs": 0}, PAGE)
    lenient = score_test({"type": "present", "text": typoed, "max_diffs": 6}, PAGE)
    assert strict.correct is False
    assert lenient.correct is True


def test_case_sensitivity():
    cs = score_test({"type": "present", "text": "PRIMITIVE BENCH", "case_sensitive": True}, PAGE)
    ci = score_test({"type": "present", "text": "PRIMITIVE BENCH", "case_sensitive": False}, PAGE)
    assert cs.correct is False
    assert ci.correct is True


# --- order ---------------------------------------------------------------
def test_order_hit():
    out = score_test({"type": "order", "before": "Abstract", "after": "Introduction"}, PAGE)
    assert out.correct is True


def test_order_wrong_direction():
    out = score_test({"type": "order", "before": "Introduction", "after": "Abstract"}, PAGE)
    assert out.correct is False and out.miss_reason == "wrong_order"


def test_order_fragment_missing():
    out = score_test({"type": "order", "before": "Abstract", "after": "nonexistent fragment"}, PAGE)
    assert out.correct is False and out.miss_reason == "fragment_missing"


# --- baseline ------------------------------------------------------------
def test_baseline_ok():
    assert score_test({"type": "baseline"}, PAGE).correct is True


def test_baseline_empty():
    out = score_test({"type": "baseline"}, "   ")
    assert out.correct is False and out.miss_reason == "empty"


def test_baseline_repetition_loop():
    out = score_test({"type": "baseline"}, "spam " * 60)
    assert out.correct is False and out.miss_reason == "repetition_loop"


# --- deferred / unknown --------------------------------------------------
def test_deferred_type_is_uncharged():
    out = score_test({"type": "math", "math": "x^2"}, PAGE)
    assert out.correct is None and out.miss_reason == "deferred_test_type"


def test_unknown_type_is_uncharged():
    out = score_test({"type": "wat"}, PAGE)
    assert out.correct is None and out.miss_reason == "unknown_test_type"
