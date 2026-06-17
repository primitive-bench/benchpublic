# golden-sets-public / extraction

PUBLIC dev split for the extraction primitive. Canary-marked; reproducible by anyone.

**Held-out test answers NEVER live here** — they sit behind the private eval
server (primitivebench-platform/apps/eval-server) with HMAC-keyed split integrity.

- `dev.jsonl` — public golden items (canary GUID embedded)
- `CANARY` — the canary GUID for contamination detection (BIG-bench convention)
