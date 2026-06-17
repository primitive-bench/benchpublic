"""eval-ocr — Primitive Bench vertical.

OCR — six-model adapters, three-loop change-detection, per-doc-type slices

Implements bench_core.Task + bench_core.Scorer for this primitive. The public
golden DEV split lives in golden-sets-public/ocr/; the held-out test split lives
only behind the private eval server. Slice definitions: slices.yaml.

STATUS: scaffold. Cloned from eval-ocr once the OCR loop proves end-to-end.
"""

from eval_ocr.task import Task  # reference implementation — template for all other verticals

__all__ = ["Task"]
