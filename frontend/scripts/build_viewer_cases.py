"""Phase C M0: join Phase B reasoning output with vehicle metadata and
archetype mapping -> frontend/public/data/viewer_cases.json

Run: python3 frontend/scripts/build_viewer_cases.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIONS = ROOT / "extraction" / "results" / "reasoning" / "actions_full.json"
CASES = ROOT / "data" / "kit" / "dataset" / "da-cases.json"
OUT = ROOT / "frontend" / "public" / "data" / "viewer_cases.json"

# (manufacturer, model) -> 9-way archetype (from extraction/car_archetypes.py)
ARCHETYPES_9 = {
    ("VW", "Polo"): "Kleinwagen",
    ("Skoda", "Fabia"): "Kleinwagen",
    ("Seat", "Ibiza"): "Kleinwagen",
    ("Ford", "Fiesta"): "Kleinwagen",
    ("Opel", "Corsa"): "Kleinwagen",
    ("Audi", "A1 Sportback"): "Kleinwagen",
    ("VW", "Golf"): "Kompaktklasse",
    ("Seat", "Leon"): "Kompaktklasse",
    ("Skoda", "Scala"): "Kompaktklasse",
    ("Audi", "A3 Sportback"): "Kompaktklasse",
    ("Mercedes", "A-Klasse"): "Kompaktklasse",
    ("BMW", "1er"): "Kompaktklasse",
    ("BMW", "5er Limousine"): "Limousine",
    ("Mercedes", "E-Klasse"): "Limousine",
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
    ("VW", "T-Roc"): "Kleines SUV / Crossover",
    ("Audi", "Q2"): "Kleines SUV / Crossover",
    ("Seat", "Arona"): "Kleines SUV / Crossover",
    ("Ford", "Puma"): "Kleines SUV / Crossover",
    ("Opel", "Mokka"): "Kleines SUV / Crossover",
    ("VW", "Tiguan"): "Kompakt-SUV",
    ("Audi", "Q3"): "Kompakt-SUV",
    ("Skoda", "Karoq"): "Kompakt-SUV",
    ("Seat", "Ateca"): "Kompakt-SUV",
    ("Ford", "Kuga"): "Kompakt-SUV",
    ("Mercedes", "GLC"): "Kompakt-SUV",
    ("BMW", "X1"): "Kompakt-SUV",
    ("Opel", "Grandland"): "Kompakt-SUV",
    ("BMW", "X3"): "Grosses SUV",
    ("Audi", "Q5"): "Grosses SUV",
    ("Skoda", "Kodiaq"): "Grosses SUV",
    ("VW", "Touran"): "Van (MPV)",
    ("Mercedes", "B-Klasse"): "Van (MPV)",
    ("BMW", "2er Active Tourer"): "Van (MPV)",
    ("Mercedes", "Vito"): "Transporter",
    ("Mercedes", "Sprinter"): "Transporter",
    ("Opel", "Vivaro"): "Transporter",
    ("VW", "T6.1 Transporter"): "Transporter",
    ("Ford", "Transit Custom"): "Transporter",
    ("VW", "Caddy"): "Transporter",
}

# 9-way archetype -> 5-way visual archetype
VISUAL = {
    "Kleinwagen": "hatchback",
    "Kompaktklasse": "hatchback",
    "Limousine": "wagon",
    "Kombi": "wagon",
    "Kleines SUV / Crossover": "suv",
    "Kompakt-SUV": "suv",
    "Grosses SUV": "suv",
    "Van (MPV)": "mpv",
    "Transporter": "transporter",
}

ZONES = {
    "Motorhaube", "Heckklappe", "Dach", "Windschutzscheibe",
    "Fahrertür", "Beifahrertür", "Tür hinten links", "Tür hinten rechts",
    "Kotflügel vorne links", "Kotflügel vorne rechts",
    "Kotflügel hinten links", "Kotflügel hinten rechts",
    "Stoßstange vorne", "Stoßstange hinten",
    "Stoßstange vorne links", "Stoßstange vorne rechts",
    "Stoßstange hinten links", "Stoßstange hinten rechts",
    "Schweller links", "Schweller rechts",
    "Außenspiegel links", "Außenspiegel rechts",
}


def main() -> None:
    actions = json.loads(ACTIONS.read_text(encoding="utf-8"))
    raw = json.loads(CASES.read_text(encoding="utf-8"))
    meta = {c["id"]: c for c in raw}

    out = []
    problems = {"missing_meta": 0, "unknown_archetype": 0, "unknown_zone": set(),
                "dupes": 0}
    for a in actions:
        m = meta.get(a["case_id"])
        if m is None:
            problems["missing_meta"] += 1
            continue
        arch9 = ARCHETYPES_9.get((m["manufacturer"], m["model"]), "???")
        if arch9 == "???":
            problems["unknown_archetype"] += 1
            continue
        damages = []
        seen = set()
        for d in a["damages"]:
            if d["zone"] not in ZONES:
                problems["unknown_zone"].add(d["zone"])
                continue
            if d["zone"] in seen:
                problems["dupes"] += 1
                continue
            seen.add(d["zone"])
            damages.append({
                "zone": d["zone"],
                "action": d["action"],
                "action_source": d["action_source"],
                "confidence": d["confidence"],
                "reason": d["reason"],
                "evidence": d["evidence"],
            })
        out.append({
            "id": f"case_{a['case_id']}",
            "case_id": a["case_id"],
            "vehicle_make": m["manufacturer"],
            "vehicle_model": m["model"],
            "vehicle_archetype": VISUAL[arch9],
            "case_type": a["case_type"],
            "case_kind": a["case_kind"],
            "severity": a["severity"],
            "reasoning_status": a["status"],
            "created_at": m["created_at"],
            "freitext": m["freitext"],
            "damages": damages,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    n_damage = sum(1 for c in out if c["case_type"] == "damage")
    from collections import Counter
    archs = Counter(c["vehicle_archetype"] for c in out if c["case_type"] == "damage")
    print(f"wrote {len(out)} cases ({n_damage} damage) -> {OUT}")
    print(f"damage cases per visual archetype: {dict(archs)}")
    print("problems:", {k: v for k, v in problems.items()})


if __name__ == "__main__":
    main()
