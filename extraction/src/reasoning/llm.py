"""DeepSeek per-zone repair/replace/assess reasoning (Phase B, PB-M2).

One narrow call per damaged zone (brief §7). Reuses the Phase A client
pattern (JSON mode, temperature 0, 1 retry with feedback, 429/5xx backoff,
thread-safe counters). Validation: enum check, evidence must be a
normalized substring of the note unless source is insufficient_information,
confidence clamped per source. Failures never become confident
recommendations (brief §16).
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path

from openai import OpenAI

from src.extraction.data import Case
from src.extraction.evidence import normalize

from . import prompt
from .cache import ReasonCache
from .contract import ZoneAction

ACTION_SYNONYMS = {
    "repair": "repair",
    "reparatur": "repair",
    "reparieren": "repair",
    "instandsetzen": "repair",
    "instandsetzung": "repair",
    "replace": "replace",
    "ersetzen": "replace",
    "austausch": "replace",
    "austauschen": "replace",
    "erneuern": "replace",
    "assess": "assess",
    "prüfen": "assess",
    "begutachten": "assess",
    "unklar": "assess",
}

SOURCE_SYNONYMS = {
    "explicit": "explicit",
    "explizit": "explicit",
    "inferred": "inferred",
    "abgeleitet": "inferred",
    "insufficient_information": "insufficient_information",
    "insufficient": "insufficient_information",
    "insufficient information": "insufficient_information",
    "unklar": "insufficient_information",
}

CONF_CAP = {"explicit": 0.99, "inferred": 0.8, "insufficient_information": 0.5}


def _conservative_fallback(zone: str) -> ZoneAction:
    return ZoneAction(
        zone=zone,
        action="assess",
        action_source="insufficient_information",
        confidence=0.1,
        reason="Reasoning call failed; conservative default.",
        evidence="",
    )


class DeepSeekReasoner:
    max_workers = 8

    def __init__(self, api_key: str | None = None):
        if api_key is None:
            env_file = Path(__file__).resolve().parents[2].parent / ".env"
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            if not api_key and env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("DEEPSEEK_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set (env or ../.env)")
        self.client = OpenAI(api_key=api_key, base_url=prompt.BASE_URL)
        self.cache = ReasonCache(prompt.PROMPT_VERSION, prompt.MODEL)
        self._lock = threading.Lock()
        self.tokens_in = 0
        self.tokens_out = 0
        self.api_calls = 0
        self.api_retries = 0
        self.invalid_outputs = 0
        self.needs_review = 0
        self.failed = 0

    def reason(
        self,
        case: Case,
        zone: str,
        severity: str | None,
        case_kind: str | None,
        insurance: str | None,
        all_zones: list[str] | None = None,
    ) -> tuple[ZoneAction, str]:
        """Returns (action, status) with status in valid|needs_review|failed."""
        cached = self.cache.get(case.freitext, zone, severity, case_kind)
        if cached is not None:
            return cached, "valid"

        user = prompt.build_user_prompt(zone, severity, case_kind, insurance, case.freitext, all_zones)
        data, problems = self._call(user, case.freitext)
        if data is None:
            with self._lock:
                self.failed += 1
            return _conservative_fallback(zone), "failed"

        action, status = self._build_action(case, zone, data, problems)
        if status != "failed":
            self.cache.put(case.freitext, zone, severity, case_kind, action)
        return action, status

    # -- internals ----------------------------------------------------------

    def _call(self, user: str, freitext: str) -> tuple[dict | None, list[str]]:
        messages = [
            {"role": "system", "content": prompt.SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]
        ntext = normalize(freitext)
        last_problems: list[str] = []
        for _attempt in range(2):
            try:
                content = self._api_call(messages)
                data = self._parse(content)
                if data is None:
                    last_problems = ["kein gültiges JSON"]
                else:
                    problems = self._validate_payload(data, ntext)
                    if not problems:
                        return data, []
                    last_problems = problems
                messages.append({"role": "assistant", "content": content or ""})
                messages.append(
                    {
                        "role": "user",
                        "content": prompt.RETRY_PROMPT.format(error="; ".join(last_problems[:3])),
                    }
                )
            except RuntimeError:
                return None, []
        with self._lock:
            self.invalid_outputs += 1
        return None, last_problems

    def _api_call(self, messages: list[dict]) -> str:
        delay = 1.0
        for _attempt in range(5):
            try:
                resp = self.client.chat.completions.create(
                    model=prompt.MODEL,
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

    @staticmethod
    def _validate_payload(data: dict, ntext: str) -> list[str]:
        problems: list[str] = []
        action = str(data.get("action") or "").lower().strip()
        if ACTION_SYNONYMS.get(action) is None:
            problems.append(f"unbekannte action {action!r}")
        source = str(data.get("source") or "").lower().strip()
        if SOURCE_SYNONYMS.get(source) is None and source:
            problems.append(f"unbekannte source {source!r}")
        evidence = str(data.get("evidence") or "")
        if evidence and normalize(evidence) not in ntext:
            problems.append("evidence ist kein wörtlicher Substring der Notiz")
        return problems

    def _build_action(self, case: Case, zone: str, data: dict, problems: list[str]) -> tuple[ZoneAction, str]:
        ntext = normalize(case.freitext)
        action_raw = str(data.get("action") or "").lower().strip()
        action = ACTION_SYNONYMS.get(action_raw, "assess")
        source_raw = str(data.get("source") or "").lower().strip()
        source = SOURCE_SYNONYMS.get(source_raw, "insufficient_information")
        if action == "assess":
            source = "insufficient_information"
        try:
            confidence = float(data.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))
        confidence = min(confidence, CONF_CAP[source])
        reason = str(data.get("reason") or "").strip()
        evidence = str(data.get("evidence") or "").strip()

        status = "valid"
        if problems or (source != "insufficient_information" and normalize(evidence) not in ntext):
            status = "needs_review"
            evidence = ""
            confidence = min(confidence, 0.5)
            if source == "explicit":
                source = "inferred"

        with self._lock:
            if status == "needs_review":
                self.needs_review += 1

        return (
            ZoneAction(
                zone=zone,
                action=action,
                action_source=source,
                confidence=round(confidence, 2),
                reason=reason or "No reason given.",
                evidence=evidence,
            ),
            status,
        )

    def op_stats(self) -> dict:
        return {
            "model": prompt.MODEL,
            "prompt_version": prompt.PROMPT_VERSION,
            "api_calls": self.api_calls,
            "api_retries": self.api_retries,
            "invalid_outputs": self.invalid_outputs,
            "needs_review": self.needs_review,
            "failed": self.failed,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "estimated_cost_usd": round(
                self.tokens_in * prompt.COST_IN_PER_1M / 1e6
                + self.tokens_out * prompt.COST_OUT_PER_1M / 1e6,
                4,
            ),
            "cache_hits": self.cache.stats()["hits"],
            "cache_misses": self.cache.stats()["misses"],
        }
