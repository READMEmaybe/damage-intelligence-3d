"""Phase B prompt (v1) for per-zone repair/replace/assess reasoning.

Narrow by design (brief §7): one zone per call, structured context, strict
JSON, verbatim evidence, conservative `assess` default.
"""

from __future__ import annotations

MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"

PROMPT_VERSION = "2"

# estimated pricing per 1M tokens (deepseek-chat, list price), Phase A values
COST_IN_PER_1M = 0.27
COST_OUT_PER_1M = 1.10

SYSTEM_PROMPT = """Du bist ein Schadenbegutachtungssystem für eine deutsche Kfz-Werkstatt.
Entscheide für EINE vorgegebene Schadenzone, welche operative Maßnahme am wahrscheinlichsten folgt.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt nach diesem Schema:
{
  "action": "repair" | "replace" | "assess",
  "source": "explicit" | "inferred" | "insufficient_information",
  "confidence": 0.0,
  "reason": "<kurze Begründung>",
  "evidence": "<wörtliches Zitat aus der Notiz oder \"\">"
}

Regeln:
1. Bevorzuge explizite Anweisungen aus der Notiz (z. B. "Austausch", "ersetzen", "nicht reparierbar", "Reparatur möglich").
2. Erfinde keine fehlenden Schadensdetails.
3. Wenn repair vs. replace nicht begründbar ist, wähle "assess".
4. "source": "explicit" nur, wenn die Notiz die Maßnahme für diese Zone ausdrücklich nennt; "inferred", wenn eine starke Schadensbeschreibung die Maßnahme nahelegt; sonst "insufficient_information".
5. "evidence" muss ein wörtlicher Substring der Notiz sein. Bei "insufficient_information" darf evidence leer ("") sein.
6. "confidence" (0 bis 1) muss die Evidenzqualität widerspiegeln: explizit ≈ 0.9-0.99, starke Indizien 0.6-0.8, vage oder widersprüchlich ≤ 0.5.
7. "reason": kurze Begründung, maximal ein Satz.
8. Kein Text außerhalb des JSON. Kein Markdown."""

RETRY_PROMPT = (
    "Deine letzte Antwort war ungültig ({error}). Antworte erneut, ausschließlich "
    "mit einem korrekten JSON-Objekt gemäß dem Schema. Kein Markdown, kein Text außerhalb des JSON."
)


def build_user_prompt(
    zone: str,
    severity: str | None,
    case_kind: str | None,
    insurance: str | None,
    freitext: str,
    all_zones: list[str] | None = None,
) -> str:
    others = [z for z in (all_zones or []) if z != zone]
    zone_inventory = (
        f"\nAlle betroffenen Zonen dieser Notiz:\n{', '.join(others)}"
        if others
        else ""
    )
    return f"""Fahrzeug-Schadenzone:
{zone}
{zone_inventory}
Schweregrad (Kontext):
{severity or "unbekannt"}

Schadensart (Kontext):
{case_kind or "unbekannt"}

Versicherungskontext (Kontext):
{insurance or "keine Angabe"}

Original-Werkstattnotiz:
{freitext}

Aufgabe:
Wähle genau eine Maßnahme (repair, replace oder assess) für die oben genannte Zone.
Triff deine Entscheidung anhand der Schadensbeschreibung dieser Zone. Gleichartige Schadensbeschreibungen verschiedener Zonen derselben Notiz sind gleich zu bewerten."""
