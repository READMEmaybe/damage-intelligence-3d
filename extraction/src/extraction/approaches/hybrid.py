"""Hybrid approach (Phase A, M4).

Variant A (implemented): rules for every field; the LLM is consulted only
for the field where rules are least confident (severity), and only when
rule confidence is low. Everything else stays rule-based, so evidence and
100%-solved fields keep the deterministic provenance.

Variant B (LLM first + deterministic validation) is not implemented as a
separate class: the LLM approach already validates every output against
the ontology and evidence constraints (accept/retry/review), so its
measured numbers are variant B's numbers.
"""

from __future__ import annotations

from ..data import Case
from ..ontology import ExtractionResult
from .base import Approach
from .llm import LLMApproach
from .rule_based import RuleBasedApproach

SEVERITY_CONFIDENCE_FLOOR = 0.4


class HybridApproach(Approach):
    name = "hybrid"
    version = "1"
    max_workers = 8

    def __init__(self):
        self.rules = RuleBasedApproach()
        self.llm = LLMApproach()
        self.llm_delegations = 0

    def extract(self, case: Case) -> ExtractionResult:
        r = self.rules.extract(case)
        if r.case_type != "damage":
            return r
        if r.confidence.get("severity", 0.0) < SEVERITY_CONFIDENCE_FLOOR:
            llm = self.llm.extract(case)
            self.llm_delegations += 1
            if llm.severity:
                r.severity = llm.severity
                r.evidence["severity"] = "llm: " + llm.evidence.get("severity", "")
                r.notes.append("severity delegated to LLM (low rule confidence)")
            else:
                r.notes.append("severity delegation failed, kept rule value")
        return r

    def op_stats(self) -> dict:
        stats = self.llm.op_stats()
        stats["llm_delegations"] = self.llm_delegations
        return stats
