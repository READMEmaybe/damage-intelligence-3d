"""Phase B pipeline: Phase A facts -> per-zone decisions -> CaseReasoning.

Flow per case (brief §13):
  freitext -> Phase A rule engine -> per zone: explicit pass -> else
  DeepSeek -> CaseReasoning (viewer contract).
"""

from __future__ import annotations

from src.extraction.approaches.rule_based import RuleBasedApproach
from src.extraction.data import Case

from .contract import CaseReasoning, ZoneAction
from .explicit import resolve_explicit
from .llm import DeepSeekReasoner


class PhaseBPipeline:
    def __init__(self, reasoner: DeepSeekReasoner | None = None):
        self.extractor = RuleBasedApproach()
        self.reasoner = reasoner

    def run_case(self, case: Case) -> CaseReasoning:
        result = self.extractor.extract(case)
        if result.case_type != "damage" or not result.zones:
            return CaseReasoning(
                case_id=case.id,
                case_type=result.case_type,
                case_kind=result.case_kind,
                severity=result.severity,
                status="valid",
                damages=[],
            )

        zones = result.zones
        explicit_actions, notes = resolve_explicit(case, zones)
        by_zone: dict[str, ZoneAction] = {a.zone: a for a in explicit_actions}

        status = "needs_review" if notes else "valid"  # e.g. F1 multi-zone binding (D-PB-04)

        for zone in zones:
            if zone in by_zone:
                continue
            if self.reasoner is None:
                by_zone[zone] = ZoneAction(
                    zone=zone,
                    action="assess",
                    action_source="insufficient_information",
                    confidence=0.3,
                    reason="No reasoning engine configured; conservative default.",
                    evidence="",
                )
                continue
            action, s = self.reasoner.reason(
                case, zone, result.severity, result.case_kind, result.insurance_type, zones
            )
            by_zone[zone] = action
            if s == "failed":
                status = "failed"
            elif s == "needs_review" and status != "failed":
                status = "needs_review"

        return CaseReasoning(
            case_id=case.id,
            case_type=result.case_type,
            case_kind=result.case_kind,
            severity=result.severity,
            status=status,
            damages=[by_zone[z] for z in zones],
        )
