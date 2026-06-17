"""eval-retrieval — Primitive Bench vertical.

Embeddings/retrieval — BEIR/MTEB-style per-domain slices

Implements bench_core.Task + bench_core.Scorer for this primitive. The public
golden DEV split lives in golden-sets-public/retrieval/; the held-out test split lives
only behind the private eval server. Slice definitions: slices.yaml.

STATUS: scaffold. Cloned from eval-ocr once the OCR loop proves end-to-end.
"""

from eval_retrieval.task import Task

__all__ = ["Task"]
