# golden-sets-public / extraction

PUBLIC dev split for the web_extraction primitive. Canary-marked; reproducible by anyone.

**Held-out test answers NEVER live here** — they sit behind the private eval
server (primitivebench-platform/apps/eval-server) with HMAC-keyed split integrity
(DECISIONS **D-07**). The public split exists so anyone can replicate the
published numbers; the holdout is what keeps the leaderboard honest.

## Files

- `dev.jsonl` — the 12-row public web_extraction sample (canary GUID embedded in
  the leading `#` header line). The first line is a comment, not JSON; skip lines
  starting with `#` when parsing.
- `../CANARY` — the canary GUID for contamination detection (BIG-bench convention,
  **D-08**). Exclude any document containing it from training corpora.

### Header note (carried over from the source sample)

The upstream sample (`AgentsBenchmark/golden/web_extraction/rows.sample.jsonl`)
shipped these leading comment lines, preserved here for provenance:

> Sample golden dataset for web_extraction (public split shipped here; holdout
> would live in the private repo). 12 rows, 4 strata x 3, 33% holdout, stratified.
> Real cohorts are 300 rows assembled per Stage 3a. Validate with:
> `python -m wrodium validate primitives/web_extraction.yaml --golden golden/web_extraction/rows.sample.jsonl`

Note: this public sample includes a few rows tagged `"split": "holdout"` so the
stratification (4 strata x 3 regions) is visible end-to-end; in the real pipeline
those holdout *answers* are withheld. The `golden` payloads here are illustrative
fixtures against `golden.wrodium.example`, not scraped from live retailers.

## Schema (per row)

Each non-comment line is one JSON object:

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable row id (`we-NNNN`). |
| `stratum` | string | Difficulty kind — one of the 4 strata below. |
| `region` | string | `us` \| `eu` \| `apac` (locale of the page). |
| `split` | string | `public` (replicable) or `holdout` (answer withheld in prod). |
| `verified_at` | string | ISO-8601 timestamp the golden was hand-verified. |
| `source_url` | string | URL of the page the fields were extracted from. |
| `page_hash` | string | Content hash, for drift detection on re-fetch. |
| `golden` | object | The verified extraction target: `title`, `price`, `in_stock`, `tags[]`. |

> The published web_search golden set uses a different, richer row shape
> (`row_id`, `query`, `canonical_url`, `truth_token`, `slices`, ...) — see
> `../websearch/README.md`. The fields named in the task brief
> (`golden_url`/`canonical_url`, `truth_token`, `source`, `slices`) belong to that
> web_search/`GoldenRow` contract; the extraction sample above predates it and
> carries the simpler product-extraction schema shown here.

## The 4 strata

Extraction difficulty is stratified by how the target fields are rendered:

1. **static_html** — fields present in the initial HTML; baseline.
2. **js_rendered** — fields populated by client-side JS after load.
3. **ambiguous_layout** — multiple plausible candidates (e.g. sale vs. list
   price) requiring disambiguation.
4. **paginated_or_lazy** — fields behind pagination or lazy-loaded sections.

Each stratum appears across all three regions (`us`/`eu`/`apac`), 3 rows each =
12 rows, ~33% marked holdout.

## Ground-truth tier

These rows are **verified-external** truth (DECISIONS **D-09**, tier 1):
hand-verified against the source page at `verified_at`, with `page_hash` to catch
later drift. See the top-level `../README.md` for the three-tier model.
