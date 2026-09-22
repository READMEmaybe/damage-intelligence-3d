"""Deterministic explicit-action pass (Phase B, PB-M1).

Measured phrase families on the corpus (DECISIONS.md D-PB-02):

- F1 "Austausch statt Instandsetzung"               -> replace, explicit
- F2 "Reparatur nicht möglich, Austausch nötig"     -> replace, explicit
- F3 "Reparatur (laut Prüfung) möglich" /
     "Harzreparatur angeboten"                      -> repair, inferred
- F4 "ob Instandsetzung reicht" (customer question) -> assess, insufficient_information

Semantics:
- F4 is a case-level open question: it sets every zone of the case to
  assess unless a stronger signal overrides a zone.
- Precedence per zone: replace (F1/F2) > repair-feasibility (F3) > open
  question (F4).
- F1/F2/F3 bind to the nearest zone mentioned before the phrase
  (measured: F2/F3 are always single-zone; F1 is multi-zone in 16/28
  cases -> confidence lowered and a review note emitted).
- Evidence is the exact verbatim substring of freitext (brief §11).
- Zero API calls; process noise ("KVA vor Reparatur abstimmen",
  "Reparaturdauer", "Ersatzteil eingetroffen") does not match any family.
"""

from __future__ import annotations

import re

from src.extraction.data import Case
from src.extraction.evidence import find_phrase, normalize
from src.extraction.ontology import ZONES_LONGEST_FIRST

from .contract import ZoneAction

F1_RE = re.compile(r"austausch statt instandsetzung", re.I)
F2_RE = re.compile(r"reparatur nicht möglich, austausch", re.I)
F3_RE = re.compile(r"reparatur (laut prüfung )?möglich|harzreparatur angeboten", re.I)
F4_RE = re.compile(r"ob instandsetzung reicht", re.I)

CONF_REPLACE_SINGLE = 0.97
CONF_REPLACE_MULTI = 0.9
CONF_REPAIR = 0.75
CONF_REPAIR_ASK = 0.65
CONF_ASSESS = 0.4


def _zone_positions(text: str) -> list[tuple[int, str]]:
    """(normalized offset, zone) per zone mention; same masking as evidence.py."""
    work = normalize(text)
    found: list[tuple[int, str]] = []
    for zone in ZONES_LONGEST_FIRST:
        needle = normalize(zone)
        idx = work.find(needle)
        if idx == -1:
            continue
        found.append((idx, zone))
        work = work[:idx] + "~" * len(needle) + work[idx + len(needle):]
    return sorted(found)


def _nearest_zone_before(positions: list[tuple[int, str]], phrase_idx: int) -> str | None:
    for idx, zone in reversed(positions):
        if idx <= phrase_idx:
            return zone
    return None


def _verbatim(text: str, matched: str) -> str:
    return find_phrase(text, matched) or matched


def resolve_explicit(case: Case, zones: list[str]) -> tuple[list[ZoneAction], list[str]]:
    """Deterministic explicit pass. Returns (per-zone actions, review notes).

    Only zones with an explicit signal get an action here; the pipeline
    routes the remaining zones to DeepSeek.
    """
    text = case.freitext
    ntext = normalize(text)
    pos = _zone_positions(text)
    by_zone: dict[str, ZoneAction] = {}
    notes: list[str] = []

    def bind(matched: str) -> str | None:
        idx = ntext.find(normalize(matched))
        return _nearest_zone_before(pos, idx)

    # F4: case-level open question -> every zone assess (weakest, applied first)
    m4 = F4_RE.search(text)
    if m4:
        for z in zones:
            by_zone[z] = ZoneAction(
                zone=z,
                action="assess",
                action_source="insufficient_information",
                confidence=CONF_ASSESS,
                reason="Customer asks whether repair suffices; the note contains no decision.",
                evidence=_verbatim(text, m4.group(0)),
            )

    # F3: repair feasibility (inspection result) -> repair, inferred
    m3 = F3_RE.search(text)
    if m3:
        zone = bind(m3.group(0))
        if zone and zone in zones:
            by_zone[zone] = ZoneAction(
                zone=zone,
                action="repair",
                action_source="inferred",
                confidence=CONF_REPAIR_ASK if m4 else CONF_REPAIR,
                reason="The note states repair is feasible (inspection result).",
                evidence=_verbatim(text, m3.group(0)),
            )

    # F2: "Reparatur nicht möglich, Austausch nötig" -> replace, explicit
    m2 = F2_RE.search(text)
    if m2:
        zone = bind(m2.group(0))
        if zone and zone in zones:
            by_zone[zone] = ZoneAction(
                zone=zone,
                action="replace",
                action_source="explicit",
                confidence=CONF_REPLACE_SINGLE,
                reason="The note states repair is not possible and replacement is required.",
                evidence=_verbatim(text, m2.group(0)),
            )

    # F1: "Austausch statt Instandsetzung" -> replace, explicit
    m1 = F1_RE.search(text)
    if m1:
        zone = bind(m1.group(0))
        if zone and zone in zones:
            if len(zones) > 1:
                notes.append(
                    "explicit replace phrase in a multi-zone note; bound to the nearest preceding zone"
                )
            by_zone[zone] = ZoneAction(
                zone=zone,
                action="replace",
                action_source="explicit",
                confidence=CONF_REPLACE_SINGLE if len(zones) == 1 else CONF_REPLACE_MULTI,
                reason="The note explicitly states replacement.",
                evidence=_verbatim(text, m1.group(0)),
            )

    return [by_zone[z] for z in zones if z in by_zone], notes
