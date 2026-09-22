"""One-off corpus inventory for Phase B PB-M0 (explicit action phrases).

Verifies the measured reality that shapes explicit.py (PB-M1):
- "Austausch statt Instandsetzung" -> explicit replace
- "Kunde möchte wissen ob Instandsetzung reicht" -> open question -> assess
- no explicit repair-instruction phrases exist.

Run: uv run inventory_phrases.py
"""

from __future__ import annotations

import re
from collections import Counter

from src.extraction import data as d


def _ctx(text: str, m: re.Match, pad: int = 45) -> str:
    s = max(0, m.start() - pad)
    e = min(len(text), m.end() + pad)
    return ("..." if s else "") + text[s:e] + ("..." if e < len(text) else "")


def main() -> None:
    cases, gts = d.load_dataset()
    damage = [(c, g) for c, g in zip(cases, gts) if g.case_type == "damage"]

    rep = re.compile(r"austausch statt instandsetzung", re.I)
    ask = re.compile(r"ob instandsetzung reicht", re.I)
    any_ins = re.compile(r"instandsetz", re.I)
    any_sig = re.compile(
        r"austausch|ersetzen|ersetze|erneuern|erneuert|instandsetz|reparier"
        r"|nicht reparierbar|ersatzteil|neu lackier",
        re.I,
    )

    n_rep = sum(1 for c, _ in damage if rep.search(c.freitext))
    n_ask = sum(1 for c, _ in damage if ask.search(c.freitext))
    n_ins = sum(1 for c, _ in damage if any_ins.search(c.freitext))
    n_sig = sum(1 for c, _ in damage if any_sig.search(c.freitext))
    n_overlap = sum(1 for c, _ in damage if rep.search(c.freitext) and ask.search(c.freitext))

    print(f"damage cases: {len(damage)}")
    print(f"any action-signal word:                                {n_sig}")
    print(f"  'Austausch statt Instandsetzung' (explicit replace): {n_rep}")
    print(f"  'ob Instandsetzung reicht' (open question):          {n_ask}")
    print(f"  any 'instandsetz':                                   {n_ins}")
    print(f"  overlap (both patterns):                             {n_overlap}")
    print(f"  cases covered by one of the two families:            {n_rep + n_ask - n_overlap}")

    print("\n'instandsetz' outside the two known families:")
    leftovers = 0
    for c, _ in damage:
        if rep.search(c.freitext) or ask.search(c.freitext):
            continue
        for m in any_ins.finditer(c.freitext):
            leftovers += 1
            print(f"  [{c.id}] {_ctx(c.freitext, m)}")
    print(f"total leftover instandsetz mentions: {leftovers}")

    other = re.compile(
        r"austausch(?! statt instandsetzung)|ersetzen|ersetze|erneuern|erneuert"
        r"|reparier|nicht reparierbar|neu lackier",
        re.I,
    )
    print("\nother signal words (case counts, first context each):")
    seen_cases: dict[str, set[int]] = {}
    contexts: dict[str, list[tuple[int, str]]] = {}
    for c, _ in damage:
        done: set[str] = set()
        for m in other.finditer(c.freitext):
            key = m.group(0).lower()
            if key in done:
                continue
            done.add(key)
            seen_cases.setdefault(key, set()).add(c.id)
            if len(contexts.setdefault(key, [])) < 5:
                contexts[key].append((c.id, _ctx(c.freitext, m)))
    for key in sorted(seen_cases, key=lambda k: -len(seen_cases[k])):
        print(f"  {key:20s} {len(seen_cases[key])}")
    for key, ctxs in contexts.items():
        print(f"\n  -- {key} --")
        for cid, ctx in ctxs:
            print(f"    [{cid}] {ctx}")


if __name__ == "__main__":
    main()
