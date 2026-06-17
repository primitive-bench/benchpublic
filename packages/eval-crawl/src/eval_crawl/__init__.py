"""eval-crawl — Primitive Bench vertical.

Crawl/scrape — greenfield golden sets

Implements bench_core.Task + bench_core.Scorer for this primitive. The public
golden DEV split lives in golden-sets-public/crawl/; the held-out test split lives
only behind the private eval server. Slice definitions: slices.yaml.

STATUS: scaffold. Cloned from eval-ocr once the OCR loop proves end-to-end.
"""

from eval_crawl.task import Task

__all__ = ["Task"]
