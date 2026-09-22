"""Phase B canonical contract (brief §6 output schema, §12 product contract).

Schema version 1, frozen in PB-M0. The 3D viewer (Phase C) consumes this
contract and must stay independent from DeepSeek, prompts and Phase A internals
(brief §12 / D07).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.extraction.ontology import ZONE_SET

ACTIONS: tuple[str, ...] = ("repair", "replace", "assess")
ACTION_SOURCES: tuple[str, ...] = ("explicit", "inferred", "insufficient_information")
STATUSES: tuple[str, ...] = ("valid", "needs_review", "failed")

CONTRACT_VERSION = "1"

# Confidence bands for the UI (brief §10): High / Medium / Low.
# Bands are derived from source + evidence quality, not raw model logits.
HIGH_CONF = 0.8
MEDIUM_CONF = 0.5


def confidence_band(confidence: float) -> str:
    if confidence >= HIGH_CONF:
        return "high"
    if confidence >= MEDIUM_CONF:
        return "medium"
    return "low"


class ZoneAction(BaseModel):
    """One repair/replace/assess decision for one damage zone (brief §6)."""

    zone: str
    action: str
    action_source: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence: str = ""  # exact substring of freitext; "" only allowed for insufficient_information

    @field_validator("zone")
    @classmethod
    def _zone_known(cls, v: str) -> str:
        if v not in ZONE_SET:
            raise ValueError(f"zone {v!r} not in the 22-zone ontology")
        return v

    @field_validator("action")
    @classmethod
    def _action_known(cls, v: str) -> str:
        if v not in ACTIONS:
            raise ValueError(f"action {v!r} not in {ACTIONS}")
        return v

    @field_validator("action_source")
    @classmethod
    def _source_known(cls, v: str) -> str:
        if v not in ACTION_SOURCES:
            raise ValueError(f"action_source {v!r} not in {ACTION_SOURCES}")
        return v

    @field_validator("evidence")
    @classmethod
    def _evidence_rule(cls, v: str, info) -> str:
        if info.data.get("action_source") != "insufficient_information" and not v.strip():
            raise ValueError("evidence required unless action_source is insufficient_information")
        return v


class CaseReasoning(BaseModel):
    """Canonical per-case Phase B output (brief §12 product contract)."""

    case_id: int
    case_type: str | None = None
    case_kind: str | None = None
    severity: str | None = None
    status: str = "valid"
    damages: list[ZoneAction] = Field(default_factory=list)
    contract_version: str = CONTRACT_VERSION

    @field_validator("status")
    @classmethod
    def _status_known(cls, v: str) -> str:
        if v not in STATUSES:
            raise ValueError(f"status {v!r} not in {STATUSES}")
        return v
