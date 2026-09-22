"""PB-M1 smoke check for the explicit-action pass.

Runs resolve_explicit over the whole corpus and verifies it against the
measured phrase-family expectations (DECISIONS.md D-PB-02). Print-based
assertions, consistent with the repo's no-test-framework style.

Run: uv run check_explicit.py
"""

from __future__ import annotations

import re
from collections import Counter

from src.extraction import data as d
from src.extraction.evidence import normalize
from src.extraction.ontology import ZONE_SET

from src.reasoning.explicit import (
    F1_RE,
    F2_RE,
    F3_RE,
    F4_RE,
    CONF_ASSESS,
    CONF_REPAIR,
    CONF_REPAIR_ASK,
    CONF_REPLACE_MULTI,
    CONF_REPLACE_SINGLE,
    resolve_explicit,
)

FAILURES: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"  {'OK ' if cond else 'FAIL'} {label}" + (f": {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(f"{label}: {detail}")


def main() -> None:
    cases, gts = d.load_dataset()
    damage = [(c, g) for c, g in zip(cases, gts) if g.case_type == "damage"]
    service = [(c, g) for c, g in zip(cases, gts) if g.case_type == "service"]

    n_actions = 0
    n_notes = 0
    n_cases_touched = 0
    action_counter: Counter = Counter()
    source_counter: Counter = Counter()
    conf_counter: Counter = Counter()
    family_counter: Counter = Counter()
    evidence_bad = 0
    zone_bad = 0

    f1 = {c.id for c, _ in damage if F1_RE.search(c.freitext)}
    f2 = {c.id for c, _ in damage if F2_RE.search(c.freitext)}
    f3 = {c.id for c, _ in damage if F3_RE.search(c.freitext)}
    f4 = {c.id for c, _ in damage if F4_RE.search(c.freitext)}

    for c, g in damage:
        actions, notes = resolve_explicit(c, list(g.zones))
        n_notes += len(notes)
        if actions:
            n_cases_touched += 1
        seen_zones: set[str] = set()
        for a in actions:
            n_actions += 1
            action_counter[a.action] += 1
            source_counter[a.action_source] += 1
            conf_counter[round(a.confidence, 2)] += 1
            if a.zone not in seen_zones:
                seen_zones.add(a.zone)
            else:
                check(f"one action per zone (case {c.id})", False, f"duplicate zone {a.zone}")
            if a.zone not in g.zones:
                zone_bad += 1
                check(f"zone in ontology (case {c.id})", False, f"{a.zone!r} not in GT zones")
            if normalize(a.evidence) not in normalize(c.freitext):
                evidence_bad += 1
                check(f"evidence verbatim (case {c.id})", False, f"{a.evidence!r}")
            if a.action == "replace" and a.action_source == "explicit":
                family_counter["replace_explicit"] += 1
            if a.action == "repair" and a.action_source == "inferred":
                family_counter["repair_inferred"] += 1
            if a.action == "assess":
                family_counter["assess"] += 1

    # service cases must produce nothing
    for c, g in service:
        actions, notes = resolve_explicit(c, list(g.zones))
        if actions:
            check(f"service case clean (case {c.id})", False, f"{len(actions)} actions")

    print(f"damage cases with explicit signal: {n_cases_touched} (expect 100)")
    print(f"total ZoneActions: {n_actions} (expect 134)")
    print(f"action distribution: {dict(action_counter)}")
    print(f"source distribution: {dict(source_counter)}")
    print(f"review notes: {n_notes} (expect 16 = F1 multi-zone)")

    # family coverage: every F1/F2 case gets exactly one replace-explicit zone
    replace_cases: dict[str, int] = {}
    for c, g in damage:
        actions, _ = resolve_explicit(c, list(g.zones))
        for a in actions:
            if a.action == "replace" and a.action_source == "explicit":
                replace_cases[c.id] = replace_cases.get(c.id, 0) + 1

    check("F1: 28 cases -> replace explicit", len(f1) == 28)
    check("F2: 8 cases -> replace explicit", len(f2) == 8)
    check("F3: 25 cases -> repair inferred", len(f3) == 25)
    check("F4: 46 cases -> assess", len(f4) == 46)
    check("F1+F2 replace-explicit zones = 35", family_counter["replace_explicit"] == 35,
          f"got {family_counter['replace_explicit']}")
    check("F3 repair-inferred zones = 25", family_counter["repair_inferred"] == 25,
          f"got {family_counter['repair_inferred']}")
    check("F4 assess zones = 74", family_counter["assess"] == 74, f"got {family_counter['assess']}")
    check("confidence 0.97 = 19 (12 F1 single + 8 F2 - 1 overlap)", conf_counter[CONF_REPLACE_SINGLE] == 19,
          f"got {conf_counter[CONF_REPLACE_SINGLE]}")
    check("confidence 0.9 = 16 (F1 multi)", conf_counter[CONF_REPLACE_MULTI] == 16,
          f"got {conf_counter[CONF_REPLACE_MULTI]}")
    check("confidence 0.75 = 23 (F3 without F4)", conf_counter[CONF_REPAIR] == 23,
          f"got {conf_counter[CONF_REPAIR]}")
    check("confidence 0.65 = 2 (F3 with F4)", conf_counter[CONF_REPAIR_ASK] == 2,
          f"got {conf_counter[CONF_REPAIR_ASK]}")
    check("confidence 0.4 = 74 (F4 assess)", conf_counter[CONF_ASSESS] == 74,
          f"got {conf_counter[CONF_ASSESS]}")
    check("evidence verbatim in all actions", evidence_bad == 0, f"{evidence_bad} bad")
    check("all zones in ontology/GT", zone_bad == 0, f"{zone_bad} bad")
    check("zero actions on service cases", all(not resolve_explicit(c, list(g.zones))[0] for c, g in service))

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} checks failed")
        for f in FAILURES:
            print("  -", f)
        raise SystemExit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
