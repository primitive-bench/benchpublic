# golden-sets-public / websearch

PUBLIC dev split for the web_search primitive. Canary-marked; reproducible by anyone.

**Held-out test answers NEVER live here** — they sit behind the private eval
server (primitivebench-platform/apps/eval-server) with HMAC-keyed split integrity
(DECISIONS **D-07**). The HMAC salt is never published.

## Why there is no committed `dev.jsonl`

The upstream engine (GoldenEvalsWebSearch) deliberately keeps generated golden
data **out of git** — the data directories carry only a `.gitkeep`. Golden rows
are produced on demand by the registry-delta pump and verified before scoring, so
there is no static committed golden file to copy here. Instead this directory
ships:

- `dev.example.jsonl` — **4 hand-written illustrative rows** (clearly marked
  `"example": true`, canary-stamped) showing the `GoldenRow` shape with real
  public identifiers (an SEC accession number, an NVD CVE id, a Federal Register
  document number, a GitHub release tag). These are NOT scored rows and NOT the
  published cohort — they exist only to document the schema.
- `../CANARY` — the contamination canary GUID (BIG-bench convention, **D-08**).

The actual public-split rows that back a published leaderboard are exported per
snapshot by `src/export_public.py` as `<snapshot>-rows.json` (a smaller public
projection of the row, no salt, no holdout) alongside `<snapshot>-results.json`.

## How rows are generated (registry-delta pump, `bench_core.goldgen`)

A golden web_search row is **a fact frozen before any vendor is queried**:
`query` + an equivalence class of golden URLs + a `truth_token` + an
authoritative timestamp. Rows are produced deterministically, no model in the
loop:

1. **Pump (delta poll).** Adapters poll authoritative registries for recent
   deltas and emit `Candidate` rows: `fed_register`, `sec_edgar`, `nvd_cve`,
   `github_releases`. Each picks a single defensible canonical URL and a unique
   `truth_token` that must literally appear on that page (FR document number, SEC
   accession number, CVE id, release tag). The authoritative timestamp comes from
   the source of truth — never backfilled.
2. **Query forms (the honest discriminator).** For each candidate two query forms
   are built (see `src/probe/queries.py`):
   - `token_in_query` — the identifier appears verbatim (navigational; saturates,
     **D-11**).
   - `descriptive` — the identifier is stripped out, leaving a natural-language
     description. This is the form actually scored, so vendors must *find* the
     document, not string-match its id.
3. **Verify + split.** `src/verify` fetches each candidate (≥2 timestamps,
   recorded in `verified_at`), measures `token_depth` / `canonical_chars`, and
   assigns a split. `row_id` is a salt-independent sha256 of
   `stratum \x1f golden_url \x1f truth_token`, so the same fact always lands in
   the same HMAC split bucket and re-running the pump never reshuffles
   assignments (**D-07**).

`row_id` is stable and public; the split *secret* (HMAC salt) is not.

## Row schema (`GoldenRow`, see `src/shared/models.py`)

| Field | Type | Meaning |
|---|---|---|
| `row_id` | string | Stable id (24-hex), derived from `(stratum, golden_url, truth_token)`. |
| `query` | string | The descriptive (token-free) query actually sent to vendors. |
| `canonical_url` | string | The single canonical golden URL. |
| `equivalence_members` | string[] | All normalized URLs that count as the one correct answer (mirrors, govinfo, etc.). |
| `truth_token` | string | Identifier that must appear on the fetched page (CVE / FR docnum / SEC accession / release tag). |
| `authoritative_timestamp` | string | ISO-8601 from the source of truth. |
| `stratum` | string | `navigational` \| `long_tail` \| `fresh` \| `sentinel` \| `sos`. |
| `source` | string | Registry adapter: `sec_edgar`, `nvd_cve`, `fed_register`, `github_releases`, `sentinel`. |
| `split` | string | `public` or `holdout`. |
| `verified_at` | string[] | The ≥2 verification-fetch timestamps. |
| `token_depth` | int | Char offset of the truth token in the canonical main content. |
| `canonical_chars` | int | Length of the canonical main content. |
| `query_variants` | object | `descriptive` and `token_in_query` forms. |
| `slices` | string[] | Cross-cutting intent tags (below). |

The public *export* projection (`export_public.py`) carries a safe subset:
`row_id, query, query_variants, canonical_url, equivalence_members, truth_token,
token_depth, canonical_chars, stratum, source, slices` — no salt, no
split-internal material.

> The example rows add two non-schema keys (`"example": true` and `"canary"`) so
> they can never be mistaken for real scored rows. Strip them before validating
> against the `GoldenRow` contract.

## The 10 intent slices (`src/slices.py`)

A **slice** is a cross-cutting intent/domain tag, orthogonal to `stratum`
(difficulty) and `source` (registry). Slices turn one leaderboard into many
(**D-01**). The frozen vocabulary:

`government_registry`, `company_lookup`, `technical_docs`, `docs_lookup`,
`fresh_news`, `b2b_tools`, `local_regional`, `pricing_pages`, `long_tail`,
`citation_needed`.

Slices are assigned deterministically (no model, no fetch): a union of per-source
defaults (e.g. `sec_edgar` → company_lookup + government_registry +
citation_needed; `nvd_cve` → technical_docs + government_registry +
citation_needed) plus conservative keyword content rules on the query text, plus
a long-tail proxy for short specific queries.

## Ground-truth tiers (D-09)

web_search rows span all three tiers:

- **verified-external** — `navigational` / `long_tail` rows hand-verified against
  the live page.
- **authoritative-registry** — `fresh` rows from the delta pump (the examples
  here).
- **sentinel-planted** — `sentinel` rows we publish ourselves so T0 is
  authoritative; see `../sentinel/PROTOCOL.md`. Sentinels also detect index drift.
