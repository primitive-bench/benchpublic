"""Adapter base class + name registry (lm-eval pattern)."""

from __future__ import annotations

from typing import Any, Callable, Type

from bench_schemas import AdapterSpec

registry: dict[str, Type["Adapter"]] = {}


class Adapter:
    """Base adapter. Subclass and implement invoke(). spec describes the SUT."""

    spec: AdapterSpec

    def __init__(self, spec: AdapterSpec):
        self.spec = spec

    def invoke(self, item: dict[str, Any]) -> dict[str, Any]:
        """Run the system-under-test on one item.

        Returns at least: {'raw_output': str, 'latency_ms': float, 'cost_usd': float}.
        Adapter-specific extras (retrieved_ids, relevances, ...) pass through.
        """
        raise NotImplementedError


def register(name: str) -> Callable[[Type[Adapter]], Type[Adapter]]:
    def deco(cls: Type[Adapter]) -> Type[Adapter]:
        if name in registry:
            raise ValueError(f"adapter {name!r} already registered")
        registry[name] = cls
        return cls

    return deco


def get(name: str) -> Type[Adapter]:
    return registry[name]
