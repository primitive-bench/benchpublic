"""eval-extraction — Primitive Bench vertical.

Structured extraction — forms/tables -> JSON, human-verified

Implements bench_core.Task + bench_core.Scorer for this primitive. The public
golden DEV split lives in golden-sets-public/extraction/; the held-out test split lives
only behind the private eval server. Slice definitions: slices.yaml.

STATUS: scaffold. Cloned from eval-ocr once the OCR loop proves end-to-end.
"""

from eval_extraction.task import Task

__all__ = ["Task"]
