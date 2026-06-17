# bench-core

The harness engine for Primitive Bench, plus the shared web-search infrastructure
(URL normalization, async main-content fetch, HMAC split-integrity, the liveness
gate, and the registry-delta golden-set pump).

Provenance: the shared infrastructure here was ported from
arlenk2021/GoldenEvalsWebSearch.

## Public surface (see ../../INTERPACKAGE.md)

- `from bench_core import Task, Scorer, run_task, RunDir`
- `from bench_core.urls import EquivalenceClass, normalize_url`
- `from bench_core.http import fetch, FetchResult`
- `from bench_core.split import hmac_split`  (exact-quota 70/30 per stratum; salt from `HMAC_SALT`)
- `from bench_core.verify import liveness_gate, Liveness`
- `from bench_core.goldgen import ...`  (SEC EDGAR, Federal Register, NVD CVE, GitHub Releases)
