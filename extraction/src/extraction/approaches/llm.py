"""LLM extraction via DeepSeek (Phase A, M3).

Design (see DECISIONS.md D-M3-*):
- German system prompt, full 22-zone ontology, strict JSON schema.
- JSON mode, temperature 0, one retry with error feedback on invalid
  output; evidence must be a verbatim substring of the note.
- lifecycle_stage is NOT requested from the LLM; it is filled by the
  metadata decision tree (D-M0-02), keeping the comparison text-only.
- Disk cache keyed by hash(note + approach + version + schema version).
- Threaded execution (max_workers) with 429/5xx backoff; token usage and
  estimated cost are tracked for the operational metrics.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path

from openai import OpenAI

from ..cache import ResultCache
from ..data import Case
from ..ontology import CASE_KINDS, ZONES, ExtractionResult
from .base import Approach
from .rule_based import _detect_lifecycle

_ZONES_LOWER = {z.lower(): z for z in ZONES}
_CASE_KINDS_LOWER = {k.lower(): k for k in CASE_KINDS}

PROMPT_VERSION = "1"
MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"

# estimated pricing per 1M tokens (deepseek-chat, list price)
COST_IN_PER_1M = 0.27
COST_OUT_PER_1M = 1.10

SYSTEM_PROMPT = """Du bist ein Extraktionssystem für freie Werkstattnotizen einer deutschen Kfz-Werkstatt.
Extrahiere strukturierte Fakten aus der Notiz. Antworte AUSSCHLIESSLICH mit einem JSON-Objekt nach diesem Schema:

{
  "case_type": "service" | "damage",
  "case_kind": "<erlaubter Wert>",
  "zones": [{"zone": "<erlaubter Wert>", "evidence": "<wörtliches Zitat aus der Notiz>"}],
  "severity": "leicht" | "mittel" | "schwer" | null,
  "insurance_type": "teilkasko" | "selbstzahler" | "vollkasko" | "haftpflicht_gegner" | "gesteuert" | null
}

Erlaubte case_kind-Werte:
Inspektion, Ölwechsel, HU/AU, Räder und Reifen, Bremsen,
Parkschaden, Auffahrunfall, Hagelschaden, Steinschlag, Vandalismus, Wildunfall, Rangierschaden

Erlaubte zones (exakt diese 22 Werte):
""" + "\n".join(ZONES) + """

Regeln:
1. "zone" muss exakt einem der 22 erlaubten Werte entsprechen. Nenne jede beschädigte Zone genau so, wie sie im Text steht.
2. "evidence" muss ein wörtliches Zitat aus der Notiz sein (exakter Substring), das die Zone belegt.
3. case_type "service" bedeutet: "zones" ist [], "severity" ist null, "insurance_type" ist null.
4. "severity" nur bei Schadensfällen. Schätze aus der Schadensbeschreibung:
   kleine Delle, Kratzer, Lackabrieb, Druckstelle, Schrammen => leicht;
   Delle, Beule, Riss im Lack, Halterung gebrochen, eingedrückt, Lack abgeplatzt => mittel;
   verformt, deformiert, durchgebrochen, abgerissen, großflächig, Blech verzogen => schwer.
5. "insurance_type" nur wenn erkennbar: Teilkasko/TK, Vollkasko/VK, Selbstzahler/"ohne Versicherung"/"zahlt selbst", Haftpflicht Gegner/"Unfallgegner"/"Haftung dem Grunde", "Schadensteuerer"/"Steuerung"/"gesteuerter Auftrag".
6. Erfinde nichts. Nicht ableitbare Felder => null bzw. [].
7. Kein Text außerhalb des JSON. Kein Markdown."""

RETRY_PROMPT = "Deine letzte Antwort war ungültig ({error}). Antworte erneut, ausschließlich mit einem korrekten JSON-Objekt gemäß dem Schema. Kein Markdown, kein Text außerhalb des JSON."

SYNONYM_MAP = {
    "case_type": {"schaden": "damage", "unfall": "damage", "service": "service", "damage": "damage"},
    "severity": {
        "light": "leicht", "medium": "mittel", "heavy": "schwer",
        "leicht": "leicht", "mittel": "mittel", "schwer": "schwer",
        "leichte": "leicht", "mittlere": "mittel", "schwere": "schwer",
    },
    "insurance_type": {
        "haftpflicht": "haftpflicht_gegner", "haftpflicht gegner": "haftpflicht_gegner",
        "haftpflicht_gegner": "haftpflicht_gegner",
        "kasko": "teilkasko", "vollkasko": "vollkasko", "teilkasko": "teilkasko",
        "selbstzahler": "selbstzahler", "gesteuert": "gesteuert",
    },
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


class LLMApproach(Approach):
    name = "llm"
    version = "1"
    max_workers = 8

    def __init__(self):
        env_file = Path(__file__).resolve().parents[3].parent / ".env"
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key and env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set (env or ../.env)")
        self.client = OpenAI(api_key=api_key, base_url=BASE_URL)
        self.cache = ResultCache(self.name, self.version)
        self._lock = threading.Lock()
        self.tokens_in = 0
        self.tokens_out = 0
        self.api_calls = 0
        self.api_retries = 0
        self.needs_review = 0

    def extract(self, case: Case) -> ExtractionResult:
        cached = self.cache.get(case.freitext)
        if cached is not None:
            return cached

        data = self._call_with_retries(case.freitext)
        if data is None:
            return self._failed(case)

        result = self._validate(case, data)
        self.cache.put(case.freitext, result)
        return result

    # -- internals ----------------------------------------------------------

    def _call_with_retries(self, text: str) -> dict | None:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        for attempt in range(2):
            try:
                resp = self._api_call(messages)
                data = self._parse(resp)
                if data is not None:
                    return data
                messages.append({"role": "assistant", "content": resp})
                messages.append({"role": "user", "content": RETRY_PROMPT.format(error="kein JSON gefunden")})
            except Exception as exc:  # noqa: BLE001
                messages.append({"role": "user", "content": RETRY_PROMPT.format(error=str(exc)[:200])})
        return None

    def _api_call(self, messages: list[dict]) -> str:
        delay = 1.0
        for attempt in range(5):
            try:
                resp = self.client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
                with self._lock:
                    self.api_calls += 1
                    usage = resp.usage
                    if usage:
                        self.tokens_in += usage.prompt_tokens or 0
                        self.tokens_out += usage.completion_tokens or 0
                return resp.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001
                code = getattr(getattr(exc, "status_code", None), "__int__", lambda: 0)()
                if code in (429, 500, 502, 503, 504) or "rate" in str(exc).lower():
                    with self._lock:
                        self.api_retries += 1
                    time.sleep(delay)
                    delay = min(delay * 2, 30)
                    continue
                raise
        raise RuntimeError("API retries exhausted")

    @staticmethod
    def _parse(content: str) -> dict | None:
        if not content:
            return None
        content = content.strip()
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.M)
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _validate(self, case: Case, data: dict) -> ExtractionResult:
        notes: list[str] = []
        status = "accepted"
        text_norm = _norm(case.freitext)

        case_type = SYNONYM_MAP["case_type"].get(str(data.get("case_type", "")).lower())
        if case_type is None:
            status, notes = "needs_review", notes + ["invalid case_type"]

        kind = str(data.get("case_kind") or "")
        if kind.lower() not in _CASE_KINDS_LOWER:
            status, notes = "needs_review", notes + [f"unknown case_kind {kind!r}"]
        else:
            kind = _CASE_KINDS_LOWER[kind.lower()]

        zones = []
        for entry in data.get("zones") or []:
            zone = str(entry.get("zone") or "")
            if zone.lower() not in _ZONES_LOWER:
                status, notes = "needs_review", notes + [f"unknown zone {zone!r}"]
                continue
            zone = _ZONES_LOWER[zone.lower()]
            evidence = str(entry.get("evidence") or "")
            if not evidence or _norm(evidence) not in text_norm:
                status, notes = "needs_review", notes + [f"evidence not verbatim for {zone}"]
                evidence = ""
            zones.append({"zone": zone, "evidence": evidence})

        severity = None
        raw_sev = data.get("severity")
        if raw_sev not in (None, "", "null"):
            severity = SYNONYM_MAP["severity"].get(str(raw_sev).lower())
            if severity is None:
                status, notes = "needs_review", notes + [f"unknown severity {raw_sev!r}"]

        insurance = None
        raw_ins = data.get("insurance_type")
        if raw_ins not in (None, "", "null"):
            insurance = SYNONYM_MAP["insurance_type"].get(str(raw_ins).lower())
            if insurance is None:
                status, notes = "needs_review", notes + [f"unknown insurance {raw_ins!r}"]

        if case_type == "service":
            zones, severity, insurance = [], None, None
        elif case_type is None:
            zones, severity, insurance = [], None, None

        lifecycle, lc_ev = _detect_lifecycle(case)
        if status == "needs_review":
            with self._lock:
                self.needs_review += 1

        evidence: dict[str, str] = {"lifecycle_stage": lc_ev}
        for z in zones:
            if z["evidence"]:
                evidence[f"zone:{z['zone']}"] = z["evidence"]

        return ExtractionResult(
            case_id=case.id,
            case_type=case_type,
            case_kind=kind or None,
            zones=[z["zone"] for z in zones],
            severity=severity,
            insurance_type=insurance,
            lifecycle_stage=lifecycle,
            status=status,
            evidence=evidence,
            confidence={"source": 1.0} if status == "accepted" else {"source": 0.0},
            notes=notes,
        )

    def _failed(self, case: Case) -> ExtractionResult:
        lifecycle, lc_ev = _detect_lifecycle(case)
        with self._lock:
            self.needs_review += 1
        return ExtractionResult(
            case_id=case.id,
            lifecycle_stage=lifecycle,
            status="failed",
            evidence={"lifecycle_stage": lc_ev},
            notes=["llm output invalid after retries"],
        )

    def op_stats(self) -> dict:
        return {
            "llm_model": MODEL,
            "prompt_version": PROMPT_VERSION,
            "api_calls": self.api_calls,
            "api_retries": self.api_retries,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "estimated_cost_usd": round(
                self.tokens_in * COST_IN_PER_1M / 1e6 + self.tokens_out * COST_OUT_PER_1M / 1e6, 4
            ),
            "cache_hits": self.cache.stats()["hits"],
            "cache_misses": self.cache.stats()["misses"],
        }
