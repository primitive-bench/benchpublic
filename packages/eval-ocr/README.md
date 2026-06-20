# eval-ocr

Primitive Bench vertical for **OCR**: hand a vendor a document-page image, get back
the transcription, and score it by **pass@test** against the
[olmOCR-bench](https://huggingface.co/datasets/allenai/olmOCR-bench) unit tests.

> Status: **live**. Six adapters (tesseract + five hosted), the full pass@test
> scorer/runner/report, and a self-owned example dev set. The `table`/`format`/
> `footnote`/`math` test evaluators are a deferred second pass (scored as uncharged
> non-attempts until they land).

## Why pass@test, not a single CER number

The leaderboard is built on the **separability gate** (`bench_stats.separable`,
McNemar) — which needs a *paired binary* outcome per item. olmOCR-bench provides
exactly that: each test case is a rule applied to the transcription, and the cell
is a HIT iff the rule passes. So the headline metric is the **pass rate** per slice
with Wilson CIs, and a winner is named only when it is Wilson-clear **and**
McNemar-separable from the runner-up — otherwise a TIE band. (A continuous CER/WER
lane can be added later for sources that ship a full reference transcription.)

Pass rules are ported from `allenai/olmocr` (`olmocr/bench/tests.py`, Apache-2.0)
using the same libraries the benchmark uses — `rapidfuzz.partial_ratio` for
presence (threshold `1 - max_diffs/len`) and `fuzzysearch` for reading order — so
our numbers stay comparable to the published olmOCR-bench leaderboard.

## The methodology highlight: the OCR miss taxonomy

A bare pass rate hides the mechanism the same way a single CER number does.
`ScorerOutput.miss_reason` decomposes *why* a test failed:

- `absent` / `fuzzy_miss` — an expected fragment is missing entirely vs. present but
  past the `max_diffs` fuzzy tolerance.
- `unexpected_present` — text that should have been excluded (a header/footer/page
  number) leaked into the transcription.
- `wrong_order` / `fragment_missing` — a reading-order rule found both spans out of
  order, or couldn't find one of them.
- `empty` / `repetition_loop` — page-sanity (baseline) failures.

`refused` (a vision LLM declined) and `truncated` (hit the output cap) are surfaced
as **uncharged non-attempts** (`correct=None`), never counted against the accuracy
denominator — charging a guardrail or a length cap as illiteracy would slander the
model.

## Adapters (two shapes, one fairness control)

- **Prompted VLMs** — `claude-sonnet-ocr` (official `anthropic` SDK), `gpt-ocr`,
  `gemini-ocr` — share one **version-pinned transcription prompt** (recorded in the
  manifest) so prompt phrasing isn't a confound.
- **Native OCR** — `tesseract` (local, free, the regression **sentinel** — expected
  stable and to lose; a `bench_stats.cusum` alarm on its anchor pass-rate flags
  harness drift vs. vendor drift), `mistral-ocr` (dedicated OCR API), `deepseek-ocr`
  (self-host only) — transcribe with no prompt.

Keys + model overrides: see `packages/bench-adapters/README.md`.

## Slices

`doc_type:*` (arxiv / old_scan / table / multi_column / math) × `test_type:*`
(present / absent / order / baseline), assigned deterministically — see
`slices.yaml`. **Coverage caveat:** olmOCR-bench is English arXiv + scans + tables,
so the README-era `handwritten` / `non_latin` slices aren't populated by this
corpus; fill them later from another permissively-licensed source.

## Modules

- `scoring.py` — the olmOCR-bench test-runner + `normalize_text`/`strip_chatter`.
- `task.py` — `Task` / `Scorer` (subclass `bench_core`), `primitive = Primitive.OCR`.
- `loader.py` — read the public split (skips the canary `#` header), resolve images.
- `runner.py` — page-grouped OCR (one call per adapter/page), truncation/refusal
  guard, reps majority vote, `RunManifest` + `RunDir` (D-13/D-14).
- `report.py` — per-slice pass@test board, Wilson/McNemar separability, `SliceResult`.
- `tools/` — `make_example_devset.py` (self-owned example) and
  `ingest_olmocr_bench.py` (full split, generated locally).

## Run it

```bash
# keyless (local tesseract only) — proves the loop, no API spend:
uv run python - <<'PY'
import bench_core.config  # loads .env
from eval_ocr.loader import load_rows
from eval_ocr.runner import run_sync
rows = load_rows("golden-sets-public/ocr/dev.example.jsonl")
run_sync(rows, "demo", vendors=["tesseract"])
PY

# full six-adapter run on the real corpus (needs keys in .env; costs API budget):
uv run python packages/eval-ocr/tools/ingest_olmocr_bench.py --limit 150
# then run_sync(load_rows("golden-sets-public/ocr/dev.jsonl"), "run1")  # all vendors
```

Outputs land in `runs/<run_id>/{manifest.json, items.jsonl, slices.jsonl}`.

## Provenance

Corpus: olmOCR-bench (ODC-BY-1.0). Pass rules ported from `allenai/olmocr`
(Apache-2.0). The miss-taxonomy framing is ported in spirit from the extraction
vertical.
