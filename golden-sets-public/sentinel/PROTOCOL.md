# Planted-pages protocol (freshness primitives)

Referenced by Stage 3a of the playbook. Planted pages are assets **we deploy and
control** so the lag clock has an authoritative T0. This protocol exists so that
"how fresh is vendor X" is measured against a timestamp no vendor can dispute.

> **Deploy planted assets before anything else in Stage 3. The lag clock starts at
> deploy** — any delay between generation and the rest of the stage is lost signal.

## The 24-cell matrix

Plant one asset in every cell so lag is comparable across conditions:

| Axis | Cells |
|---|---|
| Content type | listing · article · careers-page delta · price change (4) |
| Region | us · eu · apac (3) |
| Discoverability | linked-from-sitemap · orphan (2) |

4 × 3 × 2 = 24 cells. Each cell gets ≥1 planted asset per snapshot window.

## Per-asset record (authoritative T0)

Every planted asset logs, at deploy time, to `golden/planted_pages/<primitive>/manifest.jsonl`:

```json
{"asset_id": "pp-us-listing-linked-0007",
 "cell": {"content_type": "listing", "region": "us", "discoverable": true},
 "url": "https://golden.wrodium.example/pp/0007",
 "t0_deployed_at": "2026-06-10T00:00:00Z",   // the lag clock origin — never backfilled
 "expected_fields": {"title": "...", "price": 0.0},
 "page_hash": "…", "split": "public|holdout"}
```

Lag for a vendor = `first_observed_at - t0_deployed_at`, where `first_observed_at`
is the earliest call in which the vendor returns the planted content correctly.
`no_coverage` (never observed within the window) renders `-`, per the metric's
dash_semantics — it is not a lag of zero or infinity.

## Rules

- T0 is stamped by the deploy job, server-side. Never edit it afterward.
- Orphan assets must be genuinely unlinked (no sitemap, no inbound link) — they
  measure crawl breadth, not sitemap-following.
- Rotate 25% of planted cells each quarter (the rotation plan in the primitive YAML).
- **Lag crawlers never pause.** Gaps in a lag curve are permanent and publicly visible.
