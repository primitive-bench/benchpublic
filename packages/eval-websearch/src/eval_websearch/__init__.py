"""eval-websearch — Primitive Bench vertical.

Web search — three-tier ground truth, query-form strata, McNemar separability

Implements bench_core.Task + bench_core.Scorer for this primitive. The public
golden DEV split lives in golden-sets-public/websearch/; the held-out test split lives
only behind the private eval server. Slice definitions: slices.yaml.

STATUS: scaffold. Cloned from eval-ocr once the OCR loop proves end-to-end.
"""

from eval_websearch.task import Task

__all__ = ["Task"]
