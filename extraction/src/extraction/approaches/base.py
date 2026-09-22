"""Approach interface + trivial baselines used to smoke-test the harness."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter

from ..data import Case, GroundTruth
from ..ontology import ExtractionResult


class Approach(ABC):
    name: str = "base"
    version: str = "0"
    max_workers: int = 1

    @abstractmethod
    def extract(self, case: Case) -> ExtractionResult:
        """freitext (+ metadata) -> structured result. Must never see ground truth."""

    def op_stats(self) -> dict:
        return {}

    def __str__(self) -> str:
        return f"{self.name}-v{self.version}"


class MajorityBaseline(Approach):
    """Predicts the majority class per field, independent of the text.

    Only exists to prove the metrics harness runs end-to-end.
    """

    name = "majority_baseline"

    def __init__(self, train_gts: list[GroundTruth]):
        self.case_kind = Counter(g.case_kind for g in train_gts).most_common(1)[0][0]
        self.case_type = Counter(g.case_type for g in train_gts).most_common(1)[0][0]
        sev = Counter(g.severity for g in train_gts if g.severity)
        self.severity = sev.most_common(1)[0][0] if sev else None
        ins = Counter(g.insurance_type for g in train_gts if g.insurance_type)
        self.insurance = ins.most_common(1)[0][0] if ins else None
        lc = Counter(g.lifecycle_stage for g in train_gts if g.lifecycle_stage)
        self.lifecycle = lc.most_common(1)[0][0] if lc else None

    def extract(self, case: Case) -> ExtractionResult:
        return ExtractionResult(
            case_id=case.id,
            case_type=self.case_type,
            case_kind=self.case_kind,
            severity=self.severity,
            insurance_type=self.insurance,
            lifecycle_stage=self.lifecycle,
            notes=["majority baseline"],
        )
