"""Load OCR golden rows from a public-split JSONL file.

`bench_core.storage.read_jsonl` does NOT skip the canary `#` header (it
`json.loads` every non-blank line and would crash on it), so the public OCR
splits — which carry the BIG-bench canary as a leading comment — need this
loader. It also resolves each row's `page_image` relative to the JSONL file's
directory into an absolute path the adapters can open.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    """Parse a golden JSONL split, skipping `#`/blank lines and resolving images."""
    p = Path(path)
    base = p.parent
    rows: list[dict[str, Any]] = []
    for row in _iter_jsonl(p):
        img = row.get("page_image") or row.get("image")
        if img:
            row["page_image"] = str((base / img).resolve())
        rows.append(row)
    return rows


def _iter_jsonl(p: Path) -> Iterator[dict[str, Any]]:
    if not p.exists():
        return
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):  # skip canary header + blanks
                continue
            yield json.loads(line)
