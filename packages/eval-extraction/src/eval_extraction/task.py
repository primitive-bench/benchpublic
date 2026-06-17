"""extraction Task + Scorer. Scaffold — wire golden set, scorer, and slices here."""

from __future__ import annotations

from typing import Any, Iterable

from bench_core import Scorer as _Scorer, Task as _Task
from bench_schemas import Primitive, ScorerOutput


class Scorer(_Scorer):
    def score(self, item: dict[str, Any], raw: dict[str, Any]) -> ScorerOutput:
        raise NotImplementedError("eval-extraction scorer not yet implemented")


class Task(_Task):
    primitive = Primitive.EXTRACTION
    task_version = "extraction@0"
    dataset_version = "extraction-unreleased"

    def items(self) -> Iterable[dict[str, Any]]:
        raise NotImplementedError("eval-extraction golden set not yet wired")

    def scorer(self) -> _Scorer:
        return Scorer()
