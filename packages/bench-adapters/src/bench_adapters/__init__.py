"""bench-adapters — provider/primitive adapter SDK (lm-eval registry pattern).

Adapters wrap a system-under-test behind a uniform `invoke(item) -> dict`. They
are registered by name so configs/CLI can reference them as strings.

OCR reference adapters (lane B first deliverable):
  claude-sonnet-ocr, gemini-ocr, gpt5-ocr, mistral-ocr, deepseek-ocr,
  tesseract (regression sentinel — expected stable, not to win).

Register a new adapter:

    from bench_adapters import register, Adapter

    @register("qdrant")
    class QdrantAdapter(Adapter):
        ...

See DECISIONS.md D-06.
"""

from bench_adapters.registry import Adapter, get, register, registry

__all__ = ["Adapter", "register", "get", "registry"]
