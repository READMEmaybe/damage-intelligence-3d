"""Canonical ontology for the extraction layer.

Fixed vocabulary from data/kit/dataset/schema.json and the project brief §4.
Ground-truth severity values are German (`leicht`/`mittel`/`schwer`), kept
as canonical here instead of the English names in brief §3, so predictions
and ground truth share one vocabulary (DECISIONS.md, M0 decision).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

ZONES: tuple[str, ...] = (
    "Außenspiegel links",
    "Außenspiegel rechts",
    "Beifahrertür",
    "Dach",
    "Fahrertür",
    "Heckklappe",
    "Kotflügel hinten links",
    "Kotflügel hinten rechts",
    "Kotflügel vorne links",
    "Kotflügel vorne rechts",
    "Motorhaube",
    "Schweller links",
    "Schweller rechts",
    "Stoßstange hinten",
    "Stoßstange hinten links",
    "Stoßstange hinten rechts",
    "Stoßstange vorne",
    "Stoßstange vorne links",
    "Stoßstange vorne rechts",
    "Tür hinten links",
    "Tür hinten rechts",
    "Windschutzscheibe",
)

CASE_TYPES: tuple[str, ...] = ("service", "damage")

CASE_KINDS: tuple[str, ...] = (
    "Parkschaden",
    "Auffahrunfall",
    "Hagelschaden",
    "Steinschlag",
    "Vandalismus",
    "Wildunfall",
    "Rangierschaden",
    "Inspektion",
    "Ölwechsel",
    "HU/AU",
    "Räder und Reifen",
    "Bremsen",
)

SEVERITIES: tuple[str, ...] = ("leicht", "mittel", "schwer")

INSURANCE_TYPES: tuple[str, ...] = (
    "teilkasko",
    "selbstzahler",
    "vollkasko",
    "haftpflicht_gegner",
    "gesteuert",
)

LIFECYCLE_STAGES: tuple[str, ...] = (
    "laufend",
    "abgeschlossen",
    "neu",
    "fertig",
    "storniert",
)

# Zones sorted longest-first so child zones ("Stoßstange vorne links")
# are matched before their parents ("Stoßstange vorne").
ZONES_LONGEST_FIRST: tuple[str, ...] = tuple(sorted(ZONES, key=len, reverse=True))

ZONE_SET = frozenset(ZONES)
CASE_KIND_SET = frozenset(CASE_KINDS)


class ExtractionResult(BaseModel):
    """Structured prediction for one case (Phase A contract).

    `status` follows the brief §16 failure-handling vocabulary.
    `evidence` maps each field to the phrase that caused the decision
    (brief §11). `confidence` is optional per-field model confidence.
    """

    case_id: int
    case_type: str | None = None
    case_kind: str | None = None
    zones: list[str] = Field(default_factory=list)
    severity: str | None = None
    insurance_type: str | None = None
    lifecycle_stage: str | None = None
    status: str = "accepted"  # accepted | needs_review | failed
    evidence: dict[str, str] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    def validate_against_ontology(self) -> list[str]:
        problems: list[str] = []
        if self.case_type is not None and self.case_type not in CASE_TYPES:
            problems.append(f"case_type {self.case_type!r} not in {CASE_TYPES}")
        if self.case_kind is not None and self.case_kind not in CASE_KIND_SET:
            problems.append(f"case_kind {self.case_kind!r} not in CASE_KINDS")
        unknown_zones = [z for z in self.zones if z not in ZONE_SET]
        if unknown_zones:
            problems.append(f"zones {unknown_zones} not in ZONES")
        if self.severity is not None and self.severity not in SEVERITIES:
            problems.append(f"severity {self.severity!r} not in {SEVERITIES}")
        if self.insurance_type is not None and self.insurance_type not in INSURANCE_TYPES:
            problems.append(f"insurance_type {self.insurance_type!r} not in {INSURANCE_TYPES}")
        if self.lifecycle_stage is not None and self.lifecycle_stage not in LIFECYCLE_STAGES:
            problems.append(f"lifecycle_stage {self.lifecycle_stage!r} not in {LIFECYCLE_STAGES}")
        return problems
