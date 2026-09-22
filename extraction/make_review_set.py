"""PB-M3: build the stratified manual-review set (brief §11 B).

Deterministic selection (first matches by ascending case id) across
strata: explicit replace (single/multi), glass replace, open question
(single/multi), repair-feasibility, LLM-only light/medium/heavy, glass,
Hagel multi-zone, Wildunfall.

Run: uv run make_review_set.py
"""

from __future__ import annotations

import re

from src.extraction import data as d

from src.reasoning.explicit import F1_RE, F2_RE, F3_RE, F4_RE

STRATA: list[tuple[str, int]] = [
    ("f1_single", 2),
    ("f1_multi", 2),
    ("f2_glass", 1),
    ("f4_single", 2),
    ("f4_multi", 2),
    ("f3_repair", 2),
    ("llm_light", 3),
    ("llm_medium", 3),
    ("llm_heavy", 3),
    ("llm_glass", 2),
    ("llm_hagel_multi", 2),
    ("llm_wild", 1),
]


def _in_stratum(case, gt, name: str) -> bool:
    t = case.freitext
    if name == "f1_single":
        return F1_RE.search(t) and len(gt.zones) == 1
    if name == "f1_multi":
        return F1_RE.search(t) and len(gt.zones) > 1
    if name == "f2_glass":
        return F2_RE.search(t) and not F1_RE.search(t)
    if name == "f4_single":
        return F4_RE.search(t) and len(gt.zones) == 1
    if name == "f4_multi":
        return F4_RE.search(t) and len(gt.zones) > 1
    if name == "f3_repair":
        return F3_RE.search(t)
    if name == "llm_light":
        return gt.severity == "leicht" and not any(
            f.search(t) for f in (F1_RE, F2_RE, F3_RE, F4_RE)
        )
    if name == "llm_medium":
        return gt.severity == "mittel" and not any(
            f.search(t) for f in (F1_RE, F2_RE, F3_RE, F4_RE)
        )
    if name == "llm_heavy":
        return gt.severity == "schwer" and not any(
            f.search(t) for f in (F1_RE, F2_RE, F3_RE, F4_RE)
        )
    if name == "llm_glass":
        return (
            gt.case_kind == "Steinschlag"
            and not any(f.search(t) for f in (F1_RE, F2_RE, F3_RE, F4_RE))
        )
    if name == "llm_hagel_multi":
        return (
            gt.case_kind == "Hagelschaden"
            and len(gt.zones) > 1
            and not any(f.search(t) for f in (F1_RE, F2_RE, F3_RE, F4_RE))
        )
    if name == "llm_wild":
        return gt.case_kind == "Wildunfall" and not any(
            f.search(t) for f in (F1_RE, F2_RE, F3_RE, F4_RE)
        )
    return False


def main() -> None:
    cases, gts = d.load_dataset()
    damage = [(c, g) for c, g in zip(cases, gts) if g.case_type == "damage"]
    damage.sort(key=lambda cg: cg[0].id)

    picked: set[int] = set()
    for name, n in STRATA:
        chosen = []
        for c, g in damage:
            if c.id in picked:
                continue
            if _in_stratum(c, g, name):
                chosen.append(c.id)
                picked.add(c.id)
                if len(chosen) == n:
                    break
        print(f"# {name}: {chosen}")
    print()
    print("REVIEW_SET_IDS =", sorted(picked))


if __name__ == "__main__":
    main()
