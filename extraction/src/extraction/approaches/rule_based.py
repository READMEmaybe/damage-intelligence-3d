"""Rule-based / deterministic extraction baseline (Phase A, M1).

Design notes (see DECISIONS.md D-M1-*):
- zones: longest-match-first with masking; corpus shows verbatim zone names.
- case_kind damage: verbatim kind words (never co-occur in this corpus).
- case_kind service: ordered signal checks (inspektion > öl > hu/tüv >
  brems > tire terms); "Kontrollleuchte Reifendruck" is explicit noise.
- insurance: ordered signals (vollkasko > teilkasko > gesteuert >
  haftpflicht_gegner > selbstzahler); TK/VK matched with plate-safe
  boundaries ("XQ-TK 8105" must not fire teilkasko).
- severity: cue scoring. The severity words themselves never appear in
  the notes; damage-description words are the signal.
- lifecycle: derived from case metadata (canceled_at, completion_date_time,
  in_open_list, reparation_start_date_time), not from freitext.
"""

from __future__ import annotations

import re

from ..data import Case
from ..evidence import find_zone_mentions
from ..ontology import ZONES, ExtractionResult
from .base import Approach

ZONES_INDEX = {z: i for i, z in enumerate(ZONES)}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_BOUND_LEFT = r"(?<![a-zäöüß-])"
_BOUND_RIGHT = r"(?![a-zäöüß-])"


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text) is not None


def _first_match(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


DAMAGE_KIND_SIGNALS: list[tuple[str, str]] = [
    ("Parkschaden", _BOUND_LEFT + "parkschaden"),
    ("Auffahrunfall", _BOUND_LEFT + "auffahrunfall"),
    ("Hagelschaden", _BOUND_LEFT + "hagelschaden"),
    ("Steinschlag", _BOUND_LEFT + "steinschlag"),
    ("Vandalismus", _BOUND_LEFT + "vandalismus"),
    ("Wildunfall", _BOUND_LEFT + "wildunfall"),
    ("Rangierschaden", _BOUND_LEFT + "rangierschaden"),
]

SERVICE_KIND_SIGNALS: list[tuple[str, str]] = [
    ("Inspektion", _BOUND_LEFT + "inspektion"),
    ("Ölwechsel", _BOUND_LEFT + "öl"),
    ("HU/AU", _BOUND_LEFT + r"\bhu\b"),
    ("HU/AU", _BOUND_LEFT + "tüv"),
    ("Bremsen", _BOUND_LEFT + "brems"),
    ("Räder und Reifen", _BOUND_LEFT + r"reifen(?!druck)"),
    ("Räder und Reifen", _BOUND_LEFT + "räder"),
    ("Räder und Reifen", _BOUND_LEFT + "radwechsel"),
    ("Räder und Reifen", _BOUND_LEFT + "wuchten"),
    ("Räder und Reifen", _BOUND_LEFT + "einlager"),
    ("Räder und Reifen", _BOUND_LEFT + "umrüst"),
]

INSURANCE_SIGNALS: list[tuple[str, str]] = [
    ("vollkasko", _BOUND_LEFT + "vollkasko"),
    ("vollkasko", _BOUND_LEFT + r"vk" + _BOUND_RIGHT),
    ("teilkasko", _BOUND_LEFT + "teilkasko"),
    ("teilkasko", _BOUND_LEFT + r"tk" + _BOUND_RIGHT),
    ("gesteuert", _BOUND_LEFT + "gesteuert"),
    ("gesteuert", _BOUND_LEFT + "steuerung"),
    ("gesteuert", _BOUND_LEFT + "schadensteuerer"),
    ("haftpflicht_gegner", _BOUND_LEFT + "haftpflicht"),
    ("haftpflicht_gegner", "haftung dem grunde"),
    ("haftpflicht_gegner", _BOUND_LEFT + "unfallgegner"),
    ("selbstzahler", _BOUND_LEFT + "selbstzahler"),
    ("selbstzahler", "zahlt selbst"),
    ("selbstzahler", "zahlt selber"),
    ("selbstzahler", "ohne versicherung"),
    ("selbstzahler", "ohne vers"),
    ("selbstzahler", "keine vers"),
    ("selbstzahler", "kein vers"),
]

# (pattern, weight per class); ordered: conflicting substrings first.
SEVERITY_CUES: list[tuple[str, dict[str, float]]] = [
    (r"\bdurchgebrochen\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\babgerissen\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\bdeformiert\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\bgroßflächig\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\bverformt\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\bverzogen\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\bträger\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\bblech\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\bgerissen\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\bstark\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\baufnahme\b", {"leicht": 0, "mittel": 0, "schwer": 1.0}),
    (r"\bgebrochen\b", {"leicht": 0, "mittel": 1.0, "schwer": 0}),
    (r"\bhalterung\b", {"leicht": 0, "mittel": 1.0, "schwer": 0}),
    (r"\beingedrückt\b", {"leicht": 0, "mittel": 0.75, "schwer": 0.25}),
    (r"\bkunststoff\b", {"leicht": 0, "mittel": 1.0, "schwer": 0}),
    (r"\babgeplatzt\b", {"leicht": 0, "mittel": 1.0, "schwer": 0}),
    (r"\bgrundierung\b", {"leicht": 0, "mittel": 1.0, "schwer": 0}),
    (r"\blackschaden\w*\b", {"leicht": 0, "mittel": 1.0, "schwer": 0}),
    (r"\bbeule\w*\b", {"leicht": 0, "mittel": 1.0, "schwer": 0}),
    (r"\bgeplatzt\b", {"leicht": 0, "mittel": 1.0, "schwer": 0}),
    (r"\briss\b", {"leicht": 0.2, "mittel": 0.8, "schwer": 0}),
    (r"\bdelle\w*\b", {"leicht": 0.5, "mittel": 0.5, "schwer": 0}),
    (r"\bkratz\w*\b", {"leicht": 1.0, "mittel": 0.4, "schwer": 0}),
    (r"\bfeine\w*\b", {"leicht": 1.0, "mittel": 0, "schwer": 0}),
    (r"\bkleine\w*\b", {"leicht": 1.0, "mittel": 0, "schwer": 0}),
    (r"\bklarlack\b", {"leicht": 1.0, "mittel": 0, "schwer": 0}),
    (r"\blackabrieb\b", {"leicht": 1.0, "mittel": 0, "schwer": 0}),
    (r"\bdruckstelle\b", {"leicht": 1.0, "mittel": 0, "schwer": 0}),
    (r"\bschramme\w*\b", {"leicht": 1.0, "mittel": 0, "schwer": 0}),
    ("lack nicht durch", {"leicht": 1.0, "mittel": 0, "schwer": 0}),
]

KIND_SEVERITY_PRIOR: dict[str, str] = {
    "Parkschaden": "mittel",
    "Rangierschaden": "mittel",
    "Auffahrunfall": "mittel",
    "Hagelschaden": "mittel",
    "Steinschlag": "mittel",
    "Wildunfall": "leicht",
    "Vandalismus": "leicht",
}


def _detect_case_type_and_kind(text: str) -> tuple[str | None, str | None, str]:
    tl = text.lower()
    for kind, pat in DAMAGE_KIND_SIGNALS:
        m = re.search(pat, tl)
        if m:
            return "damage", kind, m.group(0)
    for kind, pat in SERVICE_KIND_SIGNALS:
        m = re.search(pat, tl)
        if m:
            return "service", kind, m.group(0)
    return "service", None, ""


def _detect_insurance(text: str) -> tuple[str | None, str]:
    tl = text.lower()
    for ins, pat in INSURANCE_SIGNALS:
        m = re.search(pat, tl)
        if m:
            return ins, m.group(0)
    return None, ""


def _detect_severity(text: str, kind: str | None) -> tuple[str | None, dict[str, float], list[str]]:
    tl = text.lower()
    scores = {"leicht": 0.0, "mittel": 0.0, "schwer": 0.0}
    hits: list[str] = []
    for pat, weights in SEVERITY_CUES:
        if re.search(pat, tl):
            for cls, w in weights.items():
                scores[cls] += w
            hits.append(pat.strip("\\b"))
    if not hits:
        prior = KIND_SEVERITY_PRIOR.get(kind or "")
        return prior, scores, hits
    if kind == "Hagelschaden" and any(h.startswith("delle") for h in hits):
        scores["mittel"] += 0.6
    best = max(scores, key=lambda k: scores[k])
    return best, scores, hits


def _detect_lifecycle(case: Case) -> tuple[str | None, str]:
    if case.canceled_at:
        return "storniert", "canceled_at"
    if case.completion_date_time:
        return ("fertig" if case.in_open_list else "abgeschlossen"), "completion_date_time"
    if case.reparation_start_date_time:
        return "laufend", "reparation_start_date_time"
    return "neu", "no progress fields"


class RuleBasedApproach(Approach):
    name = "rule_based"
    version = "1"

    def extract(self, case: Case) -> ExtractionResult:
        text = case.freitext
        case_type, kind, kind_ev = _detect_case_type_and_kind(text)

        zone_mentions = find_zone_mentions(text)
        zones = sorted(zone_mentions.keys(), key=lambda z: ZONES_INDEX[z])

        insurance, ins_ev = (None, "") if case_type == "service" else _detect_insurance(text)
        severity, sev_scores, sev_hits = (None, {}, []) if case_type == "service" else _detect_severity(text, kind)
        lifecycle, lc_ev = _detect_lifecycle(case)

        evidence: dict[str, str] = {}
        if case_type:
            evidence["case_type"] = kind_ev
        if kind:
            evidence["case_kind"] = kind_ev
        for z in zones:
            evidence[f"zone:{z}"] = zone_mentions[z]
        if insurance:
            evidence["insurance_type"] = ins_ev
        if severity:
            evidence["severity"] = ", ".join(sev_hits)
        evidence["lifecycle_stage"] = lc_ev

        confidence: dict[str, float] = {
            "case_type": 1.0,
            "case_kind": 1.0,
            "zones": 1.0,
            "insurance_type": 1.0 if insurance else 0.0,
            "lifecycle_stage": 1.0,
        }
        if severity:
            top = max(sev_scores.values())
            second = sorted(sev_scores.values(), reverse=True)[1]
            confidence["severity"] = round((top - second) / (top or 1.0), 3)

        return ExtractionResult(
            case_id=case.id,
            case_type=case_type,
            case_kind=kind,
            zones=zones,
            severity=severity,
            insurance_type=insurance,
            lifecycle_stage=lifecycle,
            evidence=evidence,
            confidence=confidence,
            notes=[],
        )
