"""One-off: dataset car-model/archetype inventory -> markdown report.

Groups all 49 manufacturer x model pairs into body-style archetypes
(useful for picking 3D viewer meshes) and reports damage-case share,
registration years and most-damaged zones per archetype.

Run: uv run car_archetypes.py   (writes ../../car_archetypes.md)
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from src.extraction.data import DATA_DIR
from src.extraction.ontology import ZONES_LONGEST_FIRST

OUT = Path(__file__).resolve().parents[1] / "car_archetypes.md"

# (manufacturer, model) -> archetype. Order matters for display.
ARCHETYPES: dict[tuple[str, str], str] = {
    # Kleinwagen (B-segment hatchback)
    ("VW", "Polo"): "Kleinwagen",
    ("Skoda", "Fabia"): "Kleinwagen",
    ("Seat", "Ibiza"): "Kleinwagen",
    ("Ford", "Fiesta"): "Kleinwagen",
    ("Opel", "Corsa"): "Kleinwagen",
    ("Audi", "A1 Sportback"): "Kleinwagen",
    # Kompaktklasse (C-segment hatchback)
    ("VW", "Golf"): "Kompaktklasse",
    ("Seat", "Leon"): "Kompaktklasse",
    ("Skoda", "Scala"): "Kompaktklasse",
    ("Audi", "A3 Sportback"): "Kompaktklasse",
    ("Mercedes", "A-Klasse"): "Kompaktklasse",
    ("BMW", "1er"): "Kompaktklasse",
    # Limousine
    ("BMW", "5er Limousine"): "Limousine",
    ("Mercedes", "E-Klasse"): "Limousine",
    # Kombi
    ("BMW", "3er Touring"): "Kombi",
    ("Audi", "A4 Avant"): "Kombi",
    ("Audi", "A6 Avant"): "Kombi",
    ("Ford", "Focus Turnier"): "Kombi",
    ("Skoda", "Octavia Combi"): "Kombi",
    ("Skoda", "Superb Combi"): "Kombi",
    ("VW", "Passat Variant"): "Kombi",
    ("VW", "Golf Variant"): "Kombi",
    ("Opel", "Astra Sports Tourer"): "Kombi",
    ("Mercedes", "C-Klasse T-Modell"): "Kombi",
    # Kleines SUV / Crossover (B-SUV)
    ("VW", "T-Roc"): "Kleines SUV / Crossover",
    ("Audi", "Q2"): "Kleines SUV / Crossover",
    ("Seat", "Arona"): "Kleines SUV / Crossover",
    ("Ford", "Puma"): "Kleines SUV / Crossover",
    ("Opel", "Mokka"): "Kleines SUV / Crossover",
    # Kompakt-SUV (C-SUV)
    ("VW", "Tiguan"): "Kompakt-SUV",
    ("Audi", "Q3"): "Kompakt-SUV",
    ("Skoda", "Karoq"): "Kompakt-SUV",
    ("Seat", "Ateca"): "Kompakt-SUV",
    ("Ford", "Kuga"): "Kompakt-SUV",
    ("Mercedes", "GLC"): "Kompakt-SUV",
    ("BMW", "X1"): "Kompakt-SUV",
    ("Opel", "Grandland"): "Kompakt-SUV",
    # Grosses SUV (D-SUV)
    ("BMW", "X3"): "Grosses SUV",
    ("Audi", "Q5"): "Grosses SUV",
    ("Skoda", "Kodiaq"): "Grosses SUV",
    # Van (MPV)
    ("VW", "Touran"): "Van (MPV)",
    ("Mercedes", "B-Klasse"): "Van (MPV)",
    ("BMW", "2er Active Tourer"): "Van (MPV)",
    # Transporter
    ("Mercedes", "Vito"): "Transporter",
    ("Mercedes", "Sprinter"): "Transporter",
    ("Opel", "Vivaro"): "Transporter",
    ("VW", "T6.1 Transporter"): "Transporter",
    ("Ford", "Transit Custom"): "Transporter",
    ("VW", "Caddy"): "Transporter",
}

ORDER = [
    "Kleinwagen",
    "Kompaktklasse",
    "Limousine",
    "Kombi",
    "Kleines SUV / Crossover",
    "Kompakt-SUV",
    "Grosses SUV",
    "Van (MPV)",
    "Transporter",
]


def main() -> None:
    raw = json.loads((DATA_DIR / "da-cases.json").read_text(encoding="utf-8"))
    for c in raw:
        c["_archetype"] = ARCHETYPES.get((c["manufacturer"], c["model"]), "???")
        c["_damage"] = c["ground_truth"]["case_type"] == "damage"

    n = len(raw)
    n_damage = sum(1 for c in raw if c["_damage"])

    mf = Counter(c["manufacturer"] for c in raw)
    models = Counter((c["manufacturer"], c["model"]) for c in raw)
    models_damage = Counter(
        (c["manufacturer"], c["model"]) for c in raw if c["_damage"]
    )
    arch = Counter(c["_archetype"] for c in raw)
    arch_damage = Counter(c["_archetype"] for c in raw if c["_damage"])

    years = sorted({int(c["first_registration"][:4]) for c in raw if c["first_registration"]})
    mts = Counter(
        (a, c["model_type"]) for a, c in
        ((ARCHETYPES.get((c["manufacturer"], c["model"]), "???"), c) for c in raw)
    )

    def zones_of(case) -> list[str]:
        return list(case["ground_truth"].get("zones") or [])

    lines: list[str] = []
    w = lines.append
    w("# Car Archetypes: Wolf Day Track B dataset")
    w("")
    w("Generated from `data/kit/dataset/da-cases.json` (1,000 cases) by `extraction/car_archetypes.py`.")
    w("")
    w(f"- Total cases: **{n}** ({n_damage} damage, {n - n_damage} service)")
    w(f"- Distinct manufacturer x model pairs: **{len(models)}**")
    w(f"- Manufacturers: **{len(mf)}**")
    w(f"- First registration: **{years[0]}–{years[-1]}**")
    w(f"- Archetypes: **{len(arch)}**")
    w("")

    w("## Manufacturer distribution")
    w("")
    w("| Manufacturer | Cases |")
    w("|---|---|")
    for k, v in mf.most_common():
        w(f"| {k} | {v} |")
    w("")

    w("## Archetype distribution")
    w("")
    w("| Archetype | Cases | Damage cases | % of damage cases |")
    w("|---|---|---|---|")
    for a in ORDER:
        v = arch[a]
        dv = arch_damage[a]
        pct = 100 * dv / n_damage
        w(f"| {a} | {v} | {dv} | {pct:.1f}% |")
    w("")

    w("## Full model inventory by archetype")
    w("")
    for a in ORDER:
        w(f"### {a}: {arch[a]} cases ({arch_damage[a]} damage)")
        w("")
        w("| Manufacturer | Model | Generation (`model_type`) | Cases | Damage cases |")
        w("|---|---|---|---|---|")
        for (m, mo), v in sorted(models.items(), key=lambda x: -x[1]):
            if ARCHETYPES.get((m, mo)) != a:
                continue
            gens = sorted({c["model_type"] for c in raw if c["manufacturer"] == m and c["model"] == mo})
            w(f"| {m} | {mo} | {', '.join(gens)} | {v} | {models_damage[(m, mo)]} |")
        # most-damaged zones in this archetype
        zone_counts: Counter = Counter()
        for c in raw:
            if c["_archetype"] == a and c["_damage"]:
                zone_counts.update(zones_of(c))
        top = zone_counts.most_common(5)
        if top:
            w("")
            w("Most-damaged zones: " + ", ".join(f"{z} ({v})" for z, v in top))
        w("")

    w("## Notes")
    w("")
    w("- `model_type` is the internal generation code (e.g. VW Tiguan `5N`), not a body style.")
    w("- Caddy and the commercial vans are grouped as Transporter, but Caddy is a compact city van.")
    w("- Ford Puma and Seat Arona are subcompact crossovers (B-SUV) grouped under Kleines SUV / Crossover.")
    w("- Mercedes E-Klasse appears only as Limousine; the wagon variant is labeled C-Klasse T-Modell.")
    w("")
    w("## Viewer implication (3D)")
    w("")
    w("The 22 damage zones map onto 9 visually distinct body shapes; a viewer that only ships one sedan mesh will misrepresent Kombi/SUV/Van damage. Suggested minimum mesh set, by damage-case share:")
    w("")
    w("| Priority | Archetype | Damage share |")
    w("|---|---|---|")
    for i, (a, dv) in enumerate(arch_damage.most_common(), start=1):
        pct = 100 * dv / n_damage
        w(f"| {i} | {a} | {pct:.1f}% |")
    w("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"archetype check sum: {sum(arch.values())} (expect {n})")


if __name__ == "__main__":
    main()
