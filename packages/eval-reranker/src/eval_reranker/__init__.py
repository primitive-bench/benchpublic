"""eval-reranker — Primitive Bench vertical.

Reranker — MRR/MAP/nDCG + latency-vs-quality slices

Implements bench_core.Task + bench_core.Scorer for this primitive. The public
golden DEV split lives in golden-sets-public/reranker/; the held-out test split lives
only behind the private eval server. Slice definitions: slices.yaml.

STATUS: scaffold. Cloned from eval-ocr once the OCR loop proves end-to-end.
"""

from eval_reranker.task import Task

__all__ = ["Task"]
