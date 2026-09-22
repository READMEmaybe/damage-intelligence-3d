"""Disk cache for Phase B per-zone reasoning (brief §14).

Key = sha256(freitext + zone + severity + case_kind + prompt_version + model).
Stores validated ZoneAction objects; failed API calls are never cached.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contract import ZoneAction

CACHE_DIR = Path(__file__).resolve().parents[2] / "results" / "reasoning_cache"


def cache_key(
    freitext: str,
    zone: str,
    severity: str | None,
    case_kind: str | None,
    prompt_version: str,
    model: str,
) -> str:
    raw = "\x00".join((freitext, zone, severity or "", case_kind or "", prompt_version, model))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ReasonCache:
    def __init__(self, prompt_version: str, model: str, cache_dir: Path | None = None):
        self.prompt_version = prompt_version
        self.model = model
        self.dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def _path(self, freitext: str, zone: str, severity: str | None, case_kind: str | None) -> Path:
        key = cache_key(freitext, zone, severity, case_kind, self.prompt_version, self.model)
        return self.dir / f"{key}.json"

    def get(self, freitext: str, zone: str, severity: str | None, case_kind: str | None) -> ZoneAction | None:
        p = self._path(freitext, zone, severity, case_kind)
        if not p.exists():
            self.misses += 1
            return None
        try:
            data: dict = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.misses += 1
            return None
        self.hits += 1
        return ZoneAction.model_validate(data)

    def put(self, freitext: str, zone: str, severity: str | None, case_kind: str | None, action: ZoneAction) -> None:
        self._path(freitext, zone, severity, case_kind).write_text(
            action.model_dump_json(indent=1), encoding="utf-8"
        )

    def stats(self) -> dict:
        return {"hits": self.hits, "misses": self.misses}
